__FILENAME__ = autopep8
#!/usr/bin/env python
#
# Copyright (C) 2010-2011 Hideo Hattori
# Copyright (C) 2011-2013 Hideo Hattori, Steven Myint
# Copyright (C) 2013-2014 Hideo Hattori, Steven Myint, Bill Wendling
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Automatically formats Python code to conform to the PEP 8 style guide.

Fixes that only need be done once can be added by adding a function of the form
"fix_<code>(source)" to this module. They should return the fixed source code.
These fixes are picked up by apply_global_fixes().

Fixes that depend on pep8 should be added as methods to FixPEP8. See the class
documentation for more information.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import bisect
import codecs
import collections
import copy
import difflib
import fnmatch
import inspect
import io
import itertools
import keyword
import locale
import os
import re
import signal
import sys
import token
import tokenize

import pep8


try:
    unicode
except NameError:
    unicode = str


__version__ = '1.0.2'


CR = '\r'
LF = '\n'
CRLF = '\r\n'


PYTHON_SHEBANG_REGEX = re.compile(r'^#!.*\bpython[23]?\b\s*$')


# For generating line shortening candidates.
SHORTEN_OPERATOR_GROUPS = frozenset([
    frozenset([',']),
    frozenset(['%']),
    frozenset([',', '(', '[', '{']),
    frozenset(['%', '(', '[', '{']),
    frozenset([',', '(', '[', '{', '%', '+', '-', '*', '/', '//']),
    frozenset(['%', '+', '-', '*', '/', '//']),
])


DEFAULT_IGNORE = 'E24'
DEFAULT_INDENT_SIZE = 4


# W602 is handled separately due to the need to avoid "with_traceback".
CODE_TO_2TO3 = {
    'E721': ['idioms'],
    'W601': ['has_key'],
    'W603': ['ne'],
    'W604': ['repr'],
    'W690': ['apply',
             'except',
             'exitfunc',
             'import',
             'numliterals',
             'operator',
             'paren',
             'reduce',
             'renames',
             'standarderror',
             'sys_exc',
             'throw',
             'tuple_params',
             'xreadlines']}


def open_with_encoding(filename, encoding=None, mode='r'):
    """Return opened file with a specific encoding."""
    if not encoding:
        encoding = detect_encoding(filename)

    return io.open(filename, mode=mode, encoding=encoding,
                   newline='')  # Preserve line endings


def detect_encoding(filename):
    """Return file encoding."""
    try:
        with open(filename, 'rb') as input_file:
            from lib2to3.pgen2 import tokenize as lib2to3_tokenize
            encoding = lib2to3_tokenize.detect_encoding(input_file.readline)[0]

        # Check for correctness of encoding
        with open_with_encoding(filename, encoding) as test_file:
            test_file.read()

        return encoding
    except (LookupError, SyntaxError, UnicodeDecodeError):
        return 'latin-1'


def readlines_from_file(filename):
    """Return contents of file."""
    with open_with_encoding(filename) as input_file:
        return input_file.readlines()


def extended_blank_lines(logical_line,
                         blank_lines,
                         indent_level,
                         previous_logical):
    """Check for missing blank lines after class declaration."""
    if previous_logical.startswith('class '):
        if (
            logical_line.startswith(('def ', 'class ', '@')) or
            pep8.DOCSTRING_REGEX.match(logical_line)
        ):
            if indent_level and not blank_lines:
                yield (0, 'E309 expected 1 blank line after class declaration')
    elif previous_logical.startswith('def '):
        if blank_lines and pep8.DOCSTRING_REGEX.match(logical_line):
            yield (0, 'E303 too many blank lines ({0})'.format(blank_lines))
    elif pep8.DOCSTRING_REGEX.match(previous_logical):
        # Missing blank line between class docstring and method declaration.
        if (
            indent_level and
            not blank_lines and
            logical_line.startswith(('def ')) and
            '(self' in logical_line
        ):
            yield (0, 'E301 expected 1 blank line, found 0')
pep8.register_check(extended_blank_lines)


def continued_indentation(logical_line, tokens, indent_level, indent_char,
                          noqa):
    """Override pep8's function to provide indentation information."""
    first_row = tokens[0][2][0]
    nrows = 1 + tokens[-1][2][0] - first_row
    if noqa or nrows == 1:
        return

    # indent_next tells us whether the next block is indented. Assuming
    # that it is indented by 4 spaces, then we should not allow 4-space
    # indents on the final continuation line. In turn, some other
    # indents are allowed to have an extra 4 spaces.
    indent_next = logical_line.endswith(':')

    row = depth = 0
    valid_hangs = (
        (DEFAULT_INDENT_SIZE,)
        if indent_char != '\t' else (DEFAULT_INDENT_SIZE,
                                     2 * DEFAULT_INDENT_SIZE)
    )

    # Remember how many brackets were opened on each line.
    parens = [0] * nrows

    # Relative indents of physical lines.
    rel_indent = [0] * nrows

    # For each depth, collect a list of opening rows.
    open_rows = [[0]]
    # For each depth, memorize the hanging indentation.
    hangs = [None]

    # Visual indents.
    indent_chances = {}
    last_indent = tokens[0][2]
    indent = [last_indent[1]]

    last_token_multiline = None
    line = None
    last_line = ''
    last_line_begins_with_multiline = False
    for token_type, text, start, end, line in tokens:

        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = (not last_token_multiline and
                       token_type not in (tokenize.NL, tokenize.NEWLINE))
            last_line_begins_with_multiline = last_token_multiline

        if newline:
            # This is the beginning of a continuation line.
            last_indent = start

            # Record the initial indent.
            rel_indent[row] = pep8.expand_indent(line) - indent_level

            # Identify closing bracket.
            close_bracket = (token_type == tokenize.OP and text in ']})')

            # Is the indent relative to an opening bracket line?
            for open_row in reversed(open_rows[depth]):
                hang = rel_indent[row] - rel_indent[open_row]
                hanging_indent = hang in valid_hangs
                if hanging_indent:
                    break
            if hangs[depth]:
                hanging_indent = (hang == hangs[depth])

            visual_indent = (not close_bracket and hang > 0 and
                             indent_chances.get(start[1]))

            if close_bracket and indent[depth]:
                # Closing bracket for visual indent.
                if start[1] != indent[depth]:
                    yield (start, 'E124 {0}'.format(indent[depth]))
            elif close_bracket and not hang:
                pass
            elif indent[depth] and start[1] < indent[depth]:
                # Visual indent is broken.
                yield (start, 'E128 {0}'.format(indent[depth]))
            elif (hanging_indent or
                  (indent_next and
                   rel_indent[row] == 2 * DEFAULT_INDENT_SIZE)):
                # Hanging indent is verified.
                if close_bracket:
                    yield (start, 'E123 {0}'.format(indent_level +
                                                    rel_indent[open_row]))
                hangs[depth] = hang
            elif visual_indent is True:
                # Visual indent is verified.
                indent[depth] = start[1]
            elif visual_indent in (text, unicode):
                # Ignore token lined up with matching one from a previous line.
                pass
            else:
                one_indented = (indent_level + rel_indent[open_row] +
                                DEFAULT_INDENT_SIZE)
                # Indent is broken.
                if hang <= 0:
                    error = ('E122', one_indented)
                elif indent[depth]:
                    error = ('E127', indent[depth])
                elif hang > DEFAULT_INDENT_SIZE:
                    error = ('E126', one_indented)
                else:
                    hangs[depth] = hang
                    error = ('E121', one_indented)

                yield (start, '{0} {1}'.format(*error))

        # Look for visual indenting.
        if (parens[row] and token_type not in (tokenize.NL, tokenize.COMMENT)
                and not indent[depth]):
            indent[depth] = start[1]
            indent_chances[start[1]] = True
        # Deal with implicit string concatenation.
        elif (token_type in (tokenize.STRING, tokenize.COMMENT) or
              text in ('u', 'ur', 'b', 'br')):
            indent_chances[start[1]] = unicode
        # Special case for the "if" statement because len("if (") is equal to
        # 4.
        elif not indent_chances and not row and not depth and text == 'if':
            indent_chances[end[1] + 1] = True
        elif text == ':' and line[end[1]:].isspace():
            open_rows[depth].append(row)

        # Keep track of bracket depth.
        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                hangs.append(None)
                if len(open_rows) == depth:
                    open_rows.append([])
                open_rows[depth].append(row)
                parens[row] += 1
            elif text in ')]}' and depth > 0:
                # Parent indents should not be more than this one.
                prev_indent = indent.pop() or last_indent[1]
                hangs.pop()
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                for ind in list(indent_chances):
                    if ind >= prev_indent:
                        del indent_chances[ind]
                del open_rows[depth + 1:]
                depth -= 1
                if depth:
                    indent_chances[indent[depth]] = True
                for idx in range(row, -1, -1):
                    if parens[idx]:
                        parens[idx] -= 1
                        break
            assert len(indent) == depth + 1
            if (
                start[1] not in indent_chances and
                # This is for purposes of speeding up E121 (GitHub #90).
                not last_line.rstrip().endswith(',')
            ):
                # Allow to line up tokens.
                indent_chances[start[1]] = text

        last_token_multiline = (start[0] != end[0])
        if last_token_multiline:
            rel_indent[end[0] - first_row] = rel_indent[row]

        last_line = line

    if (
        indent_next and
        not last_line_begins_with_multiline and
        pep8.expand_indent(line) == indent_level + DEFAULT_INDENT_SIZE
    ):
        pos = (start[0], indent[0] + 4)
        yield (pos, 'E125 {0}'.format(indent_level +
                                      2 * DEFAULT_INDENT_SIZE))
del pep8._checks['logical_line'][pep8.continued_indentation]
pep8.register_check(continued_indentation)


class FixPEP8(object):

    """Fix invalid code.

    Fixer methods are prefixed "fix_". The _fix_source() method looks for these
    automatically.

    The fixer method can take either one or two arguments (in addition to
    self). The first argument is "result", which is the error information from
    pep8. The second argument, "logical", is required only for logical-line
    fixes.

    The fixer method can return the list of modified lines or None. An empty
    list would mean that no changes were made. None would mean that only the
    line reported in the pep8 error was modified. Note that the modified line
    numbers that are returned are indexed at 1. This typically would correspond
    with the line number reported in the pep8 error information.

    [fixed method list]
        - e121,e122,e123,e124,e125,e126,e127,e128,e129
        - e201,e202,e203
        - e211
        - e221,e222,e223,e224,e225
        - e231
        - e251
        - e261,e262
        - e271,e272,e273,e274
        - e301,e302,e303
        - e401
        - e502
        - e701,e702
        - e711
        - w291

    """

    def __init__(self, filename,
                 options,
                 contents=None,
                 long_line_ignore_cache=None):
        self.filename = filename
        if contents is None:
            self.source = readlines_from_file(filename)
        else:
            sio = io.StringIO(contents)
            self.source = sio.readlines()
        self.options = options
        self.indent_word = _get_indentword(''.join(self.source))

        self.long_line_ignore_cache = (
            set() if long_line_ignore_cache is None
            else long_line_ignore_cache)

        # Many fixers are the same even though pep8 categorizes them
        # differently.
        self.fix_e121 = self._fix_reindent
        self.fix_e122 = self._fix_reindent
        self.fix_e123 = self._fix_reindent
        self.fix_e124 = self._fix_reindent
        self.fix_e126 = self._fix_reindent
        self.fix_e127 = self._fix_reindent
        self.fix_e128 = self._fix_reindent
        self.fix_e129 = self._fix_reindent
        self.fix_e202 = self.fix_e201
        self.fix_e203 = self.fix_e201
        self.fix_e211 = self.fix_e201
        self.fix_e221 = self.fix_e271
        self.fix_e222 = self.fix_e271
        self.fix_e223 = self.fix_e271
        self.fix_e226 = self.fix_e225
        self.fix_e227 = self.fix_e225
        self.fix_e228 = self.fix_e225
        self.fix_e241 = self.fix_e271
        self.fix_e242 = self.fix_e224
        self.fix_e261 = self.fix_e262
        self.fix_e272 = self.fix_e271
        self.fix_e273 = self.fix_e271
        self.fix_e274 = self.fix_e271
        self.fix_e309 = self.fix_e301
        self.fix_e501 = (
            self.fix_long_line_logically if
            options and (options.aggressive >= 2 or options.experimental) else
            self.fix_long_line_physically)
        self.fix_e703 = self.fix_e702

        self._ws_comma_done = False

    def _fix_source(self, results):
        try:
            (logical_start, logical_end) = _find_logical(self.source)
            logical_support = True
        except (SyntaxError, tokenize.TokenError):  # pragma: no cover
            logical_support = False

        completed_lines = set()
        for result in sorted(results, key=_priority_key):
            if result['line'] in completed_lines:
                continue

            fixed_methodname = 'fix_' + result['id'].lower()
            if hasattr(self, fixed_methodname):
                fix = getattr(self, fixed_methodname)

                line_index = result['line'] - 1
                original_line = self.source[line_index]

                is_logical_fix = len(inspect.getargspec(fix).args) > 2
                if is_logical_fix:
                    logical = None
                    if logical_support:
                        logical = _get_logical(self.source,
                                               result,
                                               logical_start,
                                               logical_end)
                        if logical and set(range(
                            logical[0][0] + 1,
                            logical[1][0] + 1)).intersection(
                                completed_lines):
                            continue

                    modified_lines = fix(result, logical)
                else:
                    modified_lines = fix(result)

                if modified_lines is None:
                    # Force logical fixes to report what they modified.
                    assert not is_logical_fix

                    if self.source[line_index] == original_line:
                        modified_lines = []

                if modified_lines:
                    completed_lines.update(modified_lines)
                elif modified_lines == []:  # Empty list means no fix
                    if self.options.verbose >= 2:
                        print(
                            '--->  Not fixing {f} on line {l}'.format(
                                f=result['id'], l=result['line']),
                            file=sys.stderr)
                else:  # We assume one-line fix when None.
                    completed_lines.add(result['line'])
            else:
                if self.options.verbose >= 3:
                    print(
                        "--->  '{0}' is not defined.".format(fixed_methodname),
                        file=sys.stderr)

                    info = result['info'].strip()
                    print('--->  {0}:{1}:{2}:{3}'.format(self.filename,
                                                         result['line'],
                                                         result['column'],
                                                         info),
                          file=sys.stderr)

    def fix(self):
        """Return a version of the source code with PEP 8 violations fixed."""
        pep8_options = {
            'ignore': self.options.ignore,
            'select': self.options.select,
            'max_line_length': self.options.max_line_length,
        }
        results = _execute_pep8(pep8_options, self.source)

        if self.options.verbose:
            progress = {}
            for r in results:
                if r['id'] not in progress:
                    progress[r['id']] = set()
                progress[r['id']].add(r['line'])
            print('--->  {n} issue(s) to fix {progress}'.format(
                n=len(results), progress=progress), file=sys.stderr)

        if self.options.line_range:
            start, end = self.options.line_range
            results = [r for r in results
                       if start <= r['line'] <= end]

        self._fix_source(filter_results(source=''.join(self.source),
                                        results=results,
                                        aggressive=self.options.aggressive))

        if self.options.line_range:
            # If number of lines has changed then change line_range.
            count = sum(sline.count('\n')
                        for sline in self.source[start - 1:end])
            self.options.line_range[1] = start + count - 1

        return ''.join(self.source)

    def _fix_reindent(self, result):
        """Fix a badly indented line.

        This is done by adding or removing from its initial indent only.

        """
        num_indent_spaces = int(result['info'].split()[1])
        line_index = result['line'] - 1
        target = self.source[line_index]

        self.source[line_index] = ' ' * num_indent_spaces + target.lstrip()

    def fix_e112(self, result):
        """Fix under-indented comments."""
        line_index = result['line'] - 1
        target = self.source[line_index]

        if not target.lstrip().startswith('#'):
            # Don't screw with invalid syntax.
            return []

        self.source[line_index] = self.indent_word + target

    def fix_e113(self, result):
        """Fix over-indented comments."""
        line_index = result['line'] - 1
        target = self.source[line_index]

        indent = _get_indentation(target)
        stripped = target.lstrip()

        if not stripped.startswith('#'):
            # Don't screw with invalid syntax.
            return []

        self.source[line_index] = indent[1:] + stripped

    def fix_e125(self, result):
        """Fix indentation undistinguish from the next logical line."""
        num_indent_spaces = int(result['info'].split()[1])
        line_index = result['line'] - 1
        target = self.source[line_index]

        spaces_to_add = num_indent_spaces - len(_get_indentation(target))
        indent = len(_get_indentation(target))
        modified_lines = []

        while len(_get_indentation(self.source[line_index])) >= indent:
            self.source[line_index] = (' ' * spaces_to_add +
                                       self.source[line_index])
            modified_lines.append(1 + line_index)  # Line indexed at 1.
            line_index -= 1

        return modified_lines

    def fix_e201(self, result):
        """Remove extraneous whitespace."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        if is_probably_part_of_multiline(target):
            return []

        fixed = fix_whitespace(target,
                               offset=offset,
                               replacement='')

        self.source[line_index] = fixed

    def fix_e224(self, result):
        """Remove extraneous whitespace around operator."""
        target = self.source[result['line'] - 1]
        offset = result['column'] - 1
        fixed = target[:offset] + target[offset:].replace('\t', ' ')
        self.source[result['line'] - 1] = fixed

    def fix_e225(self, result):
        """Fix missing whitespace around operator."""
        target = self.source[result['line'] - 1]
        offset = result['column'] - 1
        fixed = target[:offset] + ' ' + target[offset:]

        # Only proceed if non-whitespace characters match.
        # And make sure we don't break the indentation.
        if (
            fixed.replace(' ', '') == target.replace(' ', '') and
            _get_indentation(fixed) == _get_indentation(target)
        ):
            self.source[result['line'] - 1] = fixed
        else:
            return []

    def fix_e231(self, result):
        """Add missing whitespace."""
        # Optimize for comma case. This will fix all commas in the full source
        # code in one pass. Don't do this more than once. If it fails the first
        # time, there is no point in trying again.
        if ',' in result['info'] and not self._ws_comma_done:
            self._ws_comma_done = True
            original = ''.join(self.source)
            new = refactor(original, ['ws_comma'])
            if original.strip() != new.strip():
                self.source = [new]
                return range(1, 1 + len(original))

        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column']
        fixed = target[:offset] + ' ' + target[offset:]
        self.source[line_index] = fixed

    def fix_e251(self, result):
        """Remove whitespace around parameter '=' sign."""
        line_index = result['line'] - 1
        target = self.source[line_index]

        # This is necessary since pep8 sometimes reports columns that goes
        # past the end of the physical line. This happens in cases like,
        # foo(bar\n=None)
        c = min(result['column'] - 1,
                len(target) - 1)

        if target[c].strip():
            fixed = target
        else:
            fixed = target[:c].rstrip() + target[c:].lstrip()

        # There could be an escaped newline
        #
        #     def foo(a=\
        #             1)
        if fixed.endswith(('=\\\n', '=\\\r\n', '=\\\r')):
            self.source[line_index] = fixed.rstrip('\n\r \t\\')
            self.source[line_index + 1] = self.source[line_index + 1].lstrip()
            return [line_index + 1, line_index + 2]  # Line indexed at 1

        self.source[result['line'] - 1] = fixed

    def fix_e262(self, result):
        """Fix spacing after comment hash."""
        target = self.source[result['line'] - 1]
        offset = result['column']

        code = target[:offset].rstrip(' \t#')
        comment = target[offset:].lstrip(' \t#')

        fixed = code + ('  # ' + comment if comment.strip() else '\n')

        self.source[result['line'] - 1] = fixed

    def fix_e271(self, result):
        """Fix extraneous whitespace around keywords."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        if is_probably_part_of_multiline(target):
            return []

        fixed = fix_whitespace(target,
                               offset=offset,
                               replacement=' ')

        if fixed == target:
            return []
        else:
            self.source[line_index] = fixed

    def fix_e301(self, result):
        """Add missing blank line."""
        cr = '\n'
        self.source[result['line'] - 1] = cr + self.source[result['line'] - 1]

    def fix_e302(self, result):
        """Add missing 2 blank lines."""
        add_linenum = 2 - int(result['info'].split()[-1])
        cr = '\n' * add_linenum
        self.source[result['line'] - 1] = cr + self.source[result['line'] - 1]

    def fix_e303(self, result):
        """Remove extra blank lines."""
        delete_linenum = int(result['info'].split('(')[1].split(')')[0]) - 2
        delete_linenum = max(1, delete_linenum)

        # We need to count because pep8 reports an offset line number if there
        # are comments.
        cnt = 0
        line = result['line'] - 2
        modified_lines = []
        while cnt < delete_linenum and line >= 0:
            if not self.source[line].strip():
                self.source[line] = ''
                modified_lines.append(1 + line)  # Line indexed at 1
                cnt += 1
            line -= 1

        return modified_lines

    def fix_e304(self, result):
        """Remove blank line following function decorator."""
        line = result['line'] - 2
        if not self.source[line].strip():
            self.source[line] = ''

    def fix_e401(self, result):
        """Put imports on separate lines."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        if not target.lstrip().startswith('import'):
            return []

        indentation = re.split(pattern=r'\bimport\b',
                               string=target, maxsplit=1)[0]
        fixed = (target[:offset].rstrip('\t ,') + '\n' +
                 indentation + 'import ' + target[offset:].lstrip('\t ,'))
        self.source[line_index] = fixed

    def fix_long_line_logically(self, result, logical):
        """Try to make lines fit within --max-line-length characters."""
        if (
            not logical or
            len(logical[2]) == 1 or
            self.source[result['line'] - 1].lstrip().startswith('#')
        ):
            return self.fix_long_line_physically(result)

        start_line_index = logical[0][0]
        end_line_index = logical[1][0]
        logical_lines = logical[2]

        previous_line = get_item(self.source, start_line_index - 1, default='')
        next_line = get_item(self.source, end_line_index + 1, default='')

        single_line = join_logical_line(''.join(logical_lines))

        try:
            fixed = self.fix_long_line(
                target=single_line,
                previous_line=previous_line,
                next_line=next_line,
                original=''.join(logical_lines))
        except (SyntaxError, tokenize.TokenError):
            return self.fix_long_line_physically(result)

        if fixed:
            for line_index in range(start_line_index, end_line_index + 1):
                self.source[line_index] = ''
            self.source[start_line_index] = fixed
            return range(start_line_index + 1, end_line_index + 1)
        else:
            return []

    def fix_long_line_physically(self, result):
        """Try to make lines fit within --max-line-length characters."""
        line_index = result['line'] - 1
        target = self.source[line_index]

        previous_line = get_item(self.source, line_index - 1, default='')
        next_line = get_item(self.source, line_index + 1, default='')

        try:
            fixed = self.fix_long_line(
                target=target,
                previous_line=previous_line,
                next_line=next_line,
                original=target)
        except (SyntaxError, tokenize.TokenError):
            return []

        if fixed:
            self.source[line_index] = fixed
            return [line_index + 1]
        else:
            return []

    def fix_long_line(self, target, previous_line,
                      next_line, original):
        cache_entry = (target, previous_line, next_line)
        if cache_entry in self.long_line_ignore_cache:
            return []

        if target.lstrip().startswith('#'):
            # Wrap commented lines.
            return shorten_comment(
                line=target,
                max_line_length=self.options.max_line_length,
                last_comment=not next_line.lstrip().startswith('#'))

        fixed = get_fixed_long_line(
            target=target,
            previous_line=previous_line,
            original=original,
            indent_word=self.indent_word,
            max_line_length=self.options.max_line_length,
            aggressive=self.options.aggressive,
            experimental=self.options.experimental,
            verbose=self.options.verbose)
        if fixed and not code_almost_equal(original, fixed):
            return fixed
        else:
            self.long_line_ignore_cache.add(cache_entry)
            return None

    def fix_e502(self, result):
        """Remove extraneous escape of newline."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        self.source[line_index] = target.rstrip('\n\r \t\\') + '\n'

    def fix_e701(self, result):
        """Put colon-separated compound statement on separate lines."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        c = result['column']

        fixed_source = (target[:c] + '\n' +
                        _get_indentation(target) + self.indent_word +
                        target[c:].lstrip('\n\r \t\\'))
        self.source[result['line'] - 1] = fixed_source
        return [result['line'], result['line'] + 1]

    def fix_e702(self, result, logical):
        """Put semicolon-separated compound statement on separate lines."""
        if not logical:
            return []  # pragma: no cover
        logical_lines = logical[2]

        line_index = result['line'] - 1
        target = self.source[line_index]

        if target.rstrip().endswith('\\'):
            # Normalize '1; \\\n2' into '1; 2'.
            self.source[line_index] = target.rstrip('\n \r\t\\')
            self.source[line_index + 1] = self.source[line_index + 1].lstrip()
            return [line_index + 1, line_index + 2]

        if target.rstrip().endswith(';'):
            self.source[line_index] = target.rstrip('\n \r\t;') + '\n'
            return [line_index + 1]

        offset = result['column'] - 1
        first = target[:offset].rstrip(';').rstrip()
        second = (_get_indentation(logical_lines[0]) +
                  target[offset:].lstrip(';').lstrip())

        self.source[line_index] = first + '\n' + second
        return [line_index + 1]

    def fix_e711(self, result):
        """Fix comparison with None."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        right_offset = offset + 2
        if right_offset >= len(target):
            return []

        left = target[:offset].rstrip()
        center = target[offset:right_offset]
        right = target[right_offset:].lstrip()

        if not right.startswith('None'):
            return []

        if center.strip() == '==':
            new_center = 'is'
        elif center.strip() == '!=':
            new_center = 'is not'
        else:
            return []

        self.source[line_index] = ' '.join([left, new_center, right])

    def fix_e712(self, result):
        """Fix comparison with boolean."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        # Handle very easy "not" special cases.
        if re.match(r'^\s*if \w+ == False:$', target):
            self.source[line_index] = re.sub(r'if (\w+) == False:',
                                             r'if not \1:', target, count=1)
        elif re.match(r'^\s*if \w+ != True:$', target):
            self.source[line_index] = re.sub(r'if (\w+) != True:',
                                             r'if not \1:', target, count=1)
        else:
            right_offset = offset + 2
            if right_offset >= len(target):
                return []

            left = target[:offset].rstrip()
            center = target[offset:right_offset]
            right = target[right_offset:].lstrip()

            # Handle simple cases only.
            new_right = None
            if center.strip() == '==':
                if re.match(r'\bTrue\b', right):
                    new_right = re.sub(r'\bTrue\b *', '', right, count=1)
            elif center.strip() == '!=':
                if re.match(r'\bFalse\b', right):
                    new_right = re.sub(r'\bFalse\b *', '', right, count=1)

            if new_right is None:
                return []

            if new_right[0].isalnum():
                new_right = ' ' + new_right

            self.source[line_index] = left + new_right

    def fix_e713(self, result):
        """Fix non-membership check."""
        line_index = result['line'] - 1
        target = self.source[line_index]

        # Handle very easy case only.
        if re.match(r'^\s*if not \w+ in \w+:$', target):
            self.source[line_index] = re.sub(r'if not (\w+) in (\w+):',
                                             r'if \1 not in \2:',
                                             target,
                                             count=1)

    def fix_w291(self, result):
        """Remove trailing whitespace."""
        fixed_line = self.source[result['line'] - 1].rstrip()
        self.source[result['line'] - 1] = fixed_line + '\n'


def get_fixed_long_line(target, previous_line, original,
                        indent_word='    ', max_line_length=79,
                        aggressive=False, experimental=False, verbose=False):
    """Break up long line and return result.

    Do this by generating multiple reformatted candidates and then
    ranking the candidates to heuristically select the best option.

    """
    indent = _get_indentation(target)
    source = target[len(indent):]
    assert source.lstrip() == source

    # Check for partial multiline.
    tokens = list(generate_tokens(source))

    candidates = shorten_line(
        tokens, source, indent,
        indent_word,
        max_line_length,
        aggressive=aggressive,
        experimental=experimental,
        previous_line=previous_line)

    # Also sort alphabetically as a tie breaker (for determinism).
    candidates = sorted(
        sorted(set(candidates).union([target, original])),
        key=lambda x: line_shortening_rank(x,
                                           indent_word,
                                           max_line_length,
                                           experimental))

    if verbose >= 4:
        print(('-' * 79 + '\n').join([''] + candidates + ['']),
              file=codecs.getwriter('utf-8')(sys.stderr.buffer
                                             if hasattr(sys.stderr,
                                                        'buffer')
                                             else sys.stderr))

    if candidates:
        return candidates[0]


def join_logical_line(logical_line):
    """Return single line based on logical line input."""
    indentation = _get_indentation(logical_line)

    return indentation + untokenize_without_newlines(
        generate_tokens(logical_line.lstrip())) + '\n'


def untokenize_without_newlines(tokens):
    """Return source code based on tokens."""
    text = ''
    last_row = 0
    last_column = -1

    for t in tokens:
        token_string = t[1]
        (start_row, start_column) = t[2]
        (end_row, end_column) = t[3]

        if start_row > last_row:
            last_column = 0
        if (
            (start_column > last_column or token_string == '\n') and
            not text.endswith(' ')
        ):
            text += ' '

        if token_string != '\n':
            text += token_string

        last_row = end_row
        last_column = end_column

    return text


def _find_logical(source_lines):
    # Make a variable which is the index of all the starts of lines.
    logical_start = []
    logical_end = []
    last_newline = True
    parens = 0
    for t in generate_tokens(''.join(source_lines)):
        if t[0] in [tokenize.COMMENT, tokenize.DEDENT,
                    tokenize.INDENT, tokenize.NL,
                    tokenize.ENDMARKER]:
            continue
        if not parens and t[0] in [tokenize.NEWLINE, tokenize.SEMI]:
            last_newline = True
            logical_end.append((t[3][0] - 1, t[2][1]))
            continue
        if last_newline and not parens:
            logical_start.append((t[2][0] - 1, t[2][1]))
            last_newline = False
        if t[0] == tokenize.OP:
            if t[1] in '([{':
                parens += 1
            elif t[1] in '}])':
                parens -= 1
    return (logical_start, logical_end)


def _get_logical(source_lines, result, logical_start, logical_end):
    """Return the logical line corresponding to the result.

    Assumes input is already E702-clean.

    """
    row = result['line'] - 1
    col = result['column'] - 1
    ls = None
    le = None
    for i in range(0, len(logical_start), 1):
        assert logical_end
        x = logical_end[i]
        if x[0] > row or (x[0] == row and x[1] > col):
            le = x
            ls = logical_start[i]
            break
    if ls is None:
        return None
    original = source_lines[ls[0]:le[0] + 1]
    return ls, le, original


def get_item(items, index, default=None):
    if 0 <= index < len(items):
        return items[index]
    else:
        return default


def reindent(source, indent_size):
    """Reindent all lines."""
    reindenter = Reindenter(source)
    return reindenter.run(indent_size)


def code_almost_equal(a, b):
    """Return True if code is similar.

    Ignore whitespace when comparing specific line.

    """
    split_a = split_and_strip_non_empty_lines(a)
    split_b = split_and_strip_non_empty_lines(b)

    if len(split_a) != len(split_b):
        return False

    for index in range(len(split_a)):
        if ''.join(split_a[index].split()) != ''.join(split_b[index].split()):
            return False

    return True


def split_and_strip_non_empty_lines(text):
    """Return lines split by newline.

    Ignore empty lines.

    """
    return [line.strip() for line in text.splitlines() if line.strip()]


def fix_e265(source, aggressive=False):  # pylint: disable=unused-argument
    """Format block comments."""
    if '#' not in source:
        # Optimization.
        return source

    ignored_line_numbers = multiline_string_lines(
        source,
        include_docstrings=True) | set(commented_out_code_lines(source))

    fixed_lines = []
    sio = io.StringIO(source)
    for (line_number, line) in enumerate(sio.readlines(), start=1):
        if (
            line.lstrip().startswith('#') and
            line_number not in ignored_line_numbers
        ):
            indentation = _get_indentation(line)
            line = line.lstrip()

            # Normalize beginning if not a shebang.
            if len(line) > 1:
                if (
                    # Leave multiple spaces like '#    ' alone.
                    (line.count('#') > 1 or line[1].isalnum())
                    # Leave stylistic outlined blocks alone.
                    and not line.rstrip().endswith('#')
                ):
                    line = '# ' + line.lstrip('# \t')

            fixed_lines.append(indentation + line)
        else:
            fixed_lines.append(line)

    return ''.join(fixed_lines)


def refactor(source, fixer_names, ignore=None):
    """Return refactored code using lib2to3.

    Skip if ignore string is produced in the refactored code.

    """
    from lib2to3 import pgen2
    try:
        new_text = refactor_with_2to3(source,
                                      fixer_names=fixer_names)
    except (pgen2.parse.ParseError,
            SyntaxError,
            UnicodeDecodeError,
            UnicodeEncodeError):
        return source

    if ignore:
        if ignore in new_text and ignore not in source:
            return source

    return new_text


def code_to_2to3(select, ignore):
    fixes = set()
    for code, fix in CODE_TO_2TO3.items():
        if code_match(code, select=select, ignore=ignore):
            fixes |= set(fix)
    return fixes


def fix_2to3(source, aggressive=True, select=None, ignore=None):
    """Fix various deprecated code (via lib2to3)."""
    if not aggressive:
        return source

    select = select or []
    ignore = ignore or []

    return refactor(source,
                    code_to_2to3(select=select,
                                 ignore=ignore))


def fix_w602(source, aggressive=True):
    """Fix deprecated form of raising exception."""
    if not aggressive:
        return source

    return refactor(source, ['raise'],
                    ignore='with_traceback')


def find_newline(source):
    """Return type of newline used in source.

    Input is a list of lines.

    """
    assert not isinstance(source, unicode)

    counter = collections.defaultdict(int)
    for line in source:
        if line.endswith(CRLF):
            counter[CRLF] += 1
        elif line.endswith(CR):
            counter[CR] += 1
        elif line.endswith(LF):
            counter[LF] += 1

    return (sorted(counter, key=counter.get, reverse=True) or [LF])[0]


def _get_indentword(source):
    """Return indentation type."""
    indent_word = '    '  # Default in case source has no indentation
    try:
        for t in generate_tokens(source):
            if t[0] == token.INDENT:
                indent_word = t[1]
                break
    except (SyntaxError, tokenize.TokenError):
        pass
    return indent_word


def _get_indentation(line):
    """Return leading whitespace."""
    if line.strip():
        non_whitespace_index = len(line) - len(line.lstrip())
        return line[:non_whitespace_index]
    else:
        return ''


def get_diff_text(old, new, filename):
    """Return text of unified diff between old and new."""
    newline = '\n'
    diff = difflib.unified_diff(
        old, new,
        'original/' + filename,
        'fixed/' + filename,
        lineterm=newline)

    text = ''
    for line in diff:
        text += line

        # Work around missing newline (http://bugs.python.org/issue2142).
        if text and not line.endswith(newline):
            text += newline + r'\ No newline at end of file' + newline

    return text


def _priority_key(pep8_result):
    """Key for sorting PEP8 results.

    Global fixes should be done first. This is important for things like
    indentation.

    """
    priority = [
        # Fix multiline colon-based before semicolon based.
        'e701',
        # Break multiline statements early.
        'e702',
        # Things that make lines longer.
        'e225', 'e231',
        # Remove extraneous whitespace before breaking lines.
        'e201',
        # Shorten whitespace in comment before resorting to wrapping.
        'e262'
    ]
    middle_index = 10000
    lowest_priority = [
        # We need to shorten lines last since the logical fixer can get in a
        # loop, which causes us to exit early.
        'e501'
    ]
    key = pep8_result['id'].lower()
    try:
        return priority.index(key)
    except ValueError:
        try:
            return middle_index + lowest_priority.index(key) + 1
        except ValueError:
            return middle_index


def shorten_line(tokens, source, indentation, indent_word, max_line_length,
                 aggressive=False, experimental=False, previous_line=''):
    """Separate line at OPERATOR.

    Multiple candidates will be yielded.

    """
    for candidate in _shorten_line(tokens=tokens,
                                   source=source,
                                   indentation=indentation,
                                   indent_word=indent_word,
                                   aggressive=aggressive,
                                   previous_line=previous_line):
        yield candidate

    if aggressive:
        for key_token_strings in SHORTEN_OPERATOR_GROUPS:
            shortened = _shorten_line_at_tokens(
                tokens=tokens,
                source=source,
                indentation=indentation,
                indent_word=indent_word,
                key_token_strings=key_token_strings,
                aggressive=aggressive)

            if shortened is not None and shortened != source:
                yield shortened

    if experimental:
        for shortened in _shorten_line_at_tokens_new(
                tokens=tokens,
                source=source,
                indentation=indentation,
                max_line_length=max_line_length):

            yield shortened


def _shorten_line(tokens, source, indentation, indent_word,
                  aggressive=False, previous_line=''):
    """Separate line at OPERATOR.

    The input is expected to be free of newlines except for inside multiline
    strings and at the end.

    Multiple candidates will be yielded.

    """
    for (token_type,
         token_string,
         start_offset,
         end_offset) in token_offsets(tokens):

        if (
            token_type == tokenize.COMMENT and
            not is_probably_part_of_multiline(previous_line) and
            not is_probably_part_of_multiline(source) and
            not source[start_offset + 1:].strip().lower().startswith(
                ('noqa', 'pragma:', 'pylint:'))
        ):
            # Move inline comments to previous line.
            first = source[:start_offset]
            second = source[start_offset:]
            yield (indentation + second.strip() + '\n' +
                   indentation + first.strip() + '\n')
        elif token_type == token.OP and token_string != '=':
            # Don't break on '=' after keyword as this violates PEP 8.

            assert token_type != token.INDENT

            first = source[:end_offset]

            second_indent = indentation
            if first.rstrip().endswith('('):
                second_indent += indent_word
            elif '(' in first:
                second_indent += ' ' * (1 + first.find('('))
            else:
                second_indent += indent_word

            second = (second_indent + source[end_offset:].lstrip())
            if (
                not second.strip() or
                second.lstrip().startswith('#')
            ):
                continue

            # Do not begin a line with a comma
            if second.lstrip().startswith(','):
                continue
            # Do end a line with a dot
            if first.rstrip().endswith('.'):
                continue
            if token_string in '+-*/':
                fixed = first + ' \\' + '\n' + second
            else:
                fixed = first + '\n' + second

            # Only fix if syntax is okay.
            if check_syntax(normalize_multiline(fixed)
                            if aggressive else fixed):
                yield indentation + fixed


# A convenient way to handle tokens.
Token = collections.namedtuple('Token', ['token_type', 'token_string',
                                         'spos', 'epos', 'line'])


class ReformattedLines(object):

    """The reflowed lines of atoms.

    Each part of the line is represented as an "atom." They can be moved
    around when need be to get the optimal formatting.

    """

    ###########################################################################
    # Private Classes

    class _Indent(object):

        """Represent an indentation in the atom stream."""

        def __init__(self, indent_amt):
            self._indent_amt = indent_amt

        def emit(self):
            return ' ' * self._indent_amt

        @property
        def size(self):
            return self._indent_amt

    class _Space(object):

        """Represent a space in the atom stream."""

        def emit(self):
            return ' '

        @property
        def size(self):
            return 1

    class _LineBreak(object):

        """Represent a line break in the atom stream."""

        def emit(self):
            return '\n'

        @property
        def size(self):
            return 0

    def __init__(self, max_line_length):
        self._max_line_length = max_line_length
        self._lines = []
        self._bracket_depth = 0
        self._prev_item = None
        self._prev_prev_item = None

    def __repr__(self):
        return self.emit()

    ###########################################################################
    # Public Methods

    def add(self, obj, indent_amt, break_after_open_bracket):
        if isinstance(obj, Atom):
            self._add_item(obj, indent_amt)
            return

        self._add_container(obj, indent_amt, break_after_open_bracket)

    def add_comment(self, item):
        num_spaces = 2
        if len(self._lines) > 1:
            if isinstance(self._lines[-1], self._Space):
                num_spaces -= 1
            if len(self._lines) > 2:
                if isinstance(self._lines[-2], self._Space):
                    num_spaces -= 1

        while num_spaces > 0:
            self._lines.append(self._Space())
            num_spaces -= 1
        self._lines.append(item)

    def add_indent(self, indent_amt):
        self._lines.append(self._Indent(indent_amt))

    def add_line_break(self, indent):
        self._lines.append(self._LineBreak())
        self.add_indent(len(indent))

    def add_line_break_at(self, index, indent_amt):
        self._lines.insert(index, self._LineBreak())
        self._lines.insert(index + 1, self._Indent(indent_amt))

    def add_space_if_needed(self, curr_text, equal=False):
        if (
            not self._lines or isinstance(
                self._lines[-1], (self._LineBreak, self._Indent, self._Space))
        ):
            return

        prev_text = unicode(self._prev_item)
        prev_prev_text = (
            unicode(self._prev_prev_item) if self._prev_prev_item else '')

        if (
            # The previous item was a keyword or identifier and the current
            # item isn't an operator that doesn't require a space.
            ((self._prev_item.is_keyword or self._prev_item.is_string or
              self._prev_item.is_name or self._prev_item.is_number) and
             (curr_text[0] not in '([{.,:}])' or
              (curr_text[0] == '=' and equal))) or

            # Don't place spaces around a '.', unless it's in an 'import'
            # statement.
            ((prev_prev_text != 'from' and prev_text[-1] != '.' and
              curr_text != 'import') and

             # Don't place a space before a colon.
             curr_text[0] != ':' and

             # Don't split up ending brackets by spaces.
             ((prev_text[-1] in '}])' and curr_text[0] not in '.,}])') or

              # Put a space after a colon or comma.
              prev_text[-1] in ':,' or

              # Put space around '=' if asked to.
              (equal and prev_text == '=') or

              # Put spaces around non-unary arithmetic operators.
              ((self._prev_prev_item and
                (prev_text not in '+-' and
                 (self._prev_prev_item.is_name or
                  self._prev_prev_item.is_number or
                  self._prev_prev_item.is_string)) and
                prev_text in ('+', '-', '%', '*', '/', '//', '**')))))
        ):
            self._lines.append(self._Space())

    def previous_item(self):
        """Return the previous non-whitespace item."""
        return self._prev_item

    def fits_on_current_line(self, item_extent):
        return self.current_size() + item_extent <= self._max_line_length

    def current_size(self):
        """The size of the current line minus the indentation."""
        size = 0
        for item in reversed(self._lines):
            size += item.size
            if isinstance(item, self._LineBreak):
                break

        return size

    def line_empty(self):
        return (self._lines and
                isinstance(self._lines[-1],
                           (self._LineBreak, self._Indent)))

    def emit(self):
        string = ''
        for item in self._lines:
            if isinstance(item, self._LineBreak):
                string = string.rstrip()
            string += item.emit()

        return string.rstrip() + '\n'

    ###########################################################################
    # Private Methods

    def _add_item(self, item, indent_amt):
        """Add an item to the line.

        Reflow the line to get the best formatting after the item is
        inserted. The bracket depth indicates if the item is being
        inserted inside of a container or not.

        """
        if self._prev_item and self._prev_item.is_string and item.is_string:
            # Place consecutive string literals on separate lines.
            self._lines.append(self._LineBreak())
            self._lines.append(self._Indent(indent_amt))

        item_text = unicode(item)
        if self._lines and self._bracket_depth:
            # Adding the item into a container.
            self._prevent_default_initializer_splitting(item, indent_amt)

            if item_text in '.,)]}':
                self._split_after_delimiter(item, indent_amt)

        elif self._lines and not self.line_empty():
            # Adding the item outside of a container.
            if self.fits_on_current_line(len(item_text)):
                self._enforce_space(item)

            else:
                # Line break for the new item.
                self._lines.append(self._LineBreak())
                self._lines.append(self._Indent(indent_amt))

        self._lines.append(item)
        self._prev_item, self._prev_prev_item = item, self._prev_item

        if item_text in '([{':
            self._bracket_depth += 1

        elif item_text in '}])':
            self._bracket_depth -= 1
            assert self._bracket_depth >= 0

    def _add_container(self, container, indent_amt, break_after_open_bracket):
        actual_indent = indent_amt + 1

        if (
            unicode(self._prev_item) != '=' and
            not self.line_empty() and
            not self.fits_on_current_line(
                container.size + self._bracket_depth + 2)
        ):

            if unicode(container)[0] == '(' and self._prev_item.is_name:
                # Don't split before the opening bracket of a call.
                break_after_open_bracket = True
                actual_indent = indent_amt + 4
            elif (
                break_after_open_bracket or
                unicode(self._prev_item) not in '([{'
            ):
                # If the container doesn't fit on the current line and the
                # current line isn't empty, place the container on the next
                # line.
                self._lines.append(self._LineBreak())
                self._lines.append(self._Indent(indent_amt))
                break_after_open_bracket = False
        else:
            actual_indent = self.current_size() + 1
            break_after_open_bracket = False

        if isinstance(container, (ListComprehension, IfExpression)):
            actual_indent = indent_amt

        # Increase the continued indentation only if recursing on a
        # container.
        container.reflow(self, ' ' * actual_indent,
                         break_after_open_bracket=break_after_open_bracket)

    def _prevent_default_initializer_splitting(self, item, indent_amt):
        """Prevent splitting between a default initializer.

        When there is a default initializer, it's best to keep it all on
        the same line. It's nicer and more readable, even if it goes
        over the maximum allowable line length. This goes back along the
        current line to determine if we have a default initializer, and,
        if so, to remove extraneous whitespaces and add a line
        break/indent before it if needed.

        """
        if unicode(item) == '=':
            # This is the assignment in the initializer. Just remove spaces for
            # now.
            self._delete_whitespace()
            return

        if (not self._prev_item or not self._prev_prev_item or
                unicode(self._prev_item) != '='):
            return

        self._delete_whitespace()
        prev_prev_index = self._lines.index(self._prev_prev_item)

        if (
            isinstance(self._lines[prev_prev_index - 1], self._Indent) or
            self.fits_on_current_line(item.size + 1)
        ):
            # The default initializer is already the only item on this line.
            # Don't insert a newline here.
            return

        # Replace the space with a newline/indent combo.
        if isinstance(self._lines[prev_prev_index - 1], self._Space):
            del self._lines[prev_prev_index - 1]

        self.add_line_break_at(self._lines.index(self._prev_prev_item),
                               indent_amt)

    def _split_after_delimiter(self, item, indent_amt):
        """Split the line only after a delimiter."""
        self._delete_whitespace()

        if self.fits_on_current_line(item.size):
            return

        last_space = None
        for item in reversed(self._lines):
            if (
                last_space and
                (not isinstance(item, Atom) or not item.is_colon)
            ):
                break
            else:
                last_space = None
            if isinstance(item, self._Space):
                last_space = item
            if isinstance(item, (self._LineBreak, self._Indent)):
                return

        if not last_space:
            return

        self.add_line_break_at(self._lines.index(last_space), indent_amt)

    def _enforce_space(self, item):
        """Enforce a space in certain situations.

        There are cases where we will want a space where normally we
        wouldn't put one. This just enforces the addition of a space.

        """
        if isinstance(self._lines[-1],
                      (self._Space, self._LineBreak, self._Indent)):
            return

        if not self._prev_item:
            return

        item_text = unicode(item)
        prev_text = unicode(self._prev_item)

        # Prefer a space around a '.' in an import statement, and between the
        # 'import' and '('.
        if (
            (item_text == '.' and prev_text == 'from') or
            (item_text == 'import' and prev_text == '.') or
            (item_text == '(' and prev_text == 'import')
        ):
            self._lines.append(self._Space())

    def _delete_whitespace(self):
        """Delete all whitespace from the end of the line."""
        while isinstance(self._lines[-1], (self._Space, self._LineBreak,
                                           self._Indent)):
            del self._lines[-1]


class Atom(object):

    """The smallest unbreakable unit that can be reflowed."""

    def __init__(self, atom):
        self._atom = atom

    def __repr__(self):
        return self._atom.token_string

    def __len__(self):
        return self.size

    def reflow(
        self, reflowed_lines, continued_indent, extent,
        break_after_open_bracket=False,
        is_list_comp_or_if_expr=False,
        next_is_dot=False
    ):
        if self._atom.token_type == tokenize.COMMENT:
            reflowed_lines.add_comment(self)
            return

        total_size = extent if extent else self.size

        if self._atom.token_string not in ',:([{}])':
            # Some atoms will need an extra 1-sized space token after them.
            total_size += 1

        prev_item = reflowed_lines.previous_item()
        if (
            not is_list_comp_or_if_expr and
            not reflowed_lines.fits_on_current_line(total_size) and
            not (next_is_dot and
                 reflowed_lines.fits_on_current_line(self.size + 1)) and
            not reflowed_lines.line_empty() and
            not self.is_colon and
            not (prev_item and prev_item.is_name and
                 unicode(self) == '(')
        ):
            # Start a new line if there is already something on the line and
            # adding this atom would make it go over the max line length.
            reflowed_lines.add_line_break(continued_indent)
        else:
            reflowed_lines.add_space_if_needed(unicode(self))

        reflowed_lines.add(self, len(continued_indent),
                           break_after_open_bracket)

    def emit(self):
        return self.__repr__()

    @property
    def is_keyword(self):
        return keyword.iskeyword(self._atom.token_string)

    @property
    def is_string(self):
        return self._atom.token_type == tokenize.STRING

    @property
    def is_name(self):
        return self._atom.token_type == tokenize.NAME

    @property
    def is_number(self):
        return self._atom.token_type == tokenize.NUMBER

    @property
    def is_comma(self):
        return self._atom.token_string == ','

    @property
    def is_colon(self):
        return self._atom.token_string == ':'

    @property
    def size(self):
        return len(self._atom.token_string)


class Container(object):

    """Base class for all container types."""

    def __init__(self, items):
        self._items = items

    def __repr__(self):
        string = ''
        last_was_keyword = False

        for item in self._items:
            if item.is_comma:
                string += ', '
            elif item.is_colon:
                string += ': '
            else:
                item_string = unicode(item)
                if (
                    string and
                    (last_was_keyword or
                     (not string.endswith(tuple('([{,.:}]) ')) and
                      not item_string.startswith(tuple('([{,.:}])'))))
                ):
                    string += ' '
                string += item_string

            last_was_keyword = item.is_keyword
        return string

    def __iter__(self):
        for element in self._items:
            yield element

    def __getitem__(self, idx):
        return self._items[idx]

    def reflow(self, reflowed_lines, continued_indent,
               break_after_open_bracket=False):
        last_was_container = False
        for (index, item) in enumerate(self._items):
            next_item = get_item(self._items, index + 1)

            if isinstance(item, Atom):
                is_list_comp_or_if_expr = (
                    isinstance(self, (ListComprehension, IfExpression)))
                item.reflow(reflowed_lines, continued_indent,
                            self._get_extent(index),
                            is_list_comp_or_if_expr=is_list_comp_or_if_expr,
                            next_is_dot=(next_item and
                                         unicode(next_item) == '.'))
                if last_was_container and item.is_comma:
                    reflowed_lines.add_line_break(continued_indent)
                last_was_container = False
            else:  # isinstance(item, Container)
                reflowed_lines.add(item, len(continued_indent),
                                   break_after_open_bracket)
                last_was_container = not isinstance(item, (ListComprehension,
                                                           IfExpression))

            if (
                break_after_open_bracket and index == 0 and
                # Prefer to keep empty containers together instead of
                # separating them.
                unicode(item) == self.open_bracket and
                (not next_item or unicode(next_item) != self.close_bracket) and
                (len(self._items) != 3 or not isinstance(next_item, Atom))
            ):
                reflowed_lines.add_line_break(continued_indent)
                break_after_open_bracket = False
            else:
                next_next_item = get_item(self._items, index + 2)
                if (
                    unicode(item) not in ['.', '%', 'in'] and
                    next_item and not isinstance(next_item, Container) and
                    unicode(next_item) != ':' and
                    next_next_item and (not isinstance(next_next_item, Atom) or
                                        unicode(next_item) == 'not') and
                    not reflowed_lines.line_empty() and
                    not reflowed_lines.fits_on_current_line(
                        self._get_extent(index + 1) + 2)
                ):
                    reflowed_lines.add_line_break(continued_indent)

    def _get_extent(self, index):
        """The extent of the full element.

        E.g., the length of a function call or keyword.

        """
        extent = 0
        prev_item = get_item(self._items, index - 1)
        seen_dot = prev_item and unicode(prev_item) == '.'
        while index < len(self._items):
            item = get_item(self._items, index)
            index += 1

            if isinstance(item, (ListComprehension, IfExpression)):
                break

            if isinstance(item, Container):
                if prev_item and prev_item.is_name:
                    if seen_dot:
                        extent += 1
                    else:
                        extent += item.size

                    prev_item = item
                    continue
            elif (unicode(item) not in ['.', '=', ':', 'not'] and
                  not item.is_name and not item.is_string):
                break

            if unicode(item) == '.':
                seen_dot = True

            extent += item.size
            prev_item = item

        return extent

    @property
    def is_string(self):
        return False

    @property
    def size(self):
        return len(self.__repr__())

    @property
    def is_keyword(self):
        return False

    @property
    def is_name(self):
        return False

    @property
    def is_comma(self):
        return False

    @property
    def is_colon(self):
        return False

    @property
    def open_bracket(self):
        return None

    @property
    def close_bracket(self):
        return None


class Tuple(Container):

    """A high-level representation of a tuple."""

    @property
    def open_bracket(self):
        return '('

    @property
    def close_bracket(self):
        return ')'


class List(Container):

    """A high-level representation of a list."""

    @property
    def open_bracket(self):
        return '['

    @property
    def close_bracket(self):
        return ']'


class DictOrSet(Container):

    """A high-level representation of a dictionary or set."""

    @property
    def open_bracket(self):
        return '{'

    @property
    def close_bracket(self):
        return '}'


class ListComprehension(Container):

    """A high-level representation of a list comprehension."""

    @property
    def size(self):
        length = 0
        for item in self._items:
            if isinstance(item, IfExpression):
                break
            length += item.size
        return length


class IfExpression(Container):

    """A high-level representation of an if-expression."""


def _parse_container(tokens, index, for_or_if=None):
    """Parse a high-level container, such as a list, tuple, etc."""

    # Store the opening bracket.
    items = [Atom(Token(*tokens[index]))]
    index += 1

    num_tokens = len(tokens)
    while index < num_tokens:
        tok = Token(*tokens[index])

        if tok.token_string in ',)]}':
            # First check if we're at the end of a list comprehension or
            # if-expression. Don't add the ending token as part of the list
            # comprehension or if-expression, because they aren't part of those
            # constructs.
            if for_or_if == 'for':
                return (ListComprehension(items), index - 1)

            elif for_or_if == 'if':
                return (IfExpression(items), index - 1)

            # We've reached the end of a container.
            items.append(Atom(tok))

            # If not, then we are at the end of a container.
            if tok.token_string == ')':
                # The end of a tuple.
                return (Tuple(items), index)

            elif tok.token_string == ']':
                # The end of a list.
                return (List(items), index)

            elif tok.token_string == '}':
                # The end of a dictionary or set.
                return (DictOrSet(items), index)

        elif tok.token_string in '([{':
            # A sub-container is being defined.
            (container, index) = _parse_container(tokens, index)
            items.append(container)

        elif tok.token_string == 'for':
            (container, index) = _parse_container(tokens, index, 'for')
            items.append(container)

        elif tok.token_string == 'if':
            (container, index) = _parse_container(tokens, index, 'if')
            items.append(container)

        else:
            items.append(Atom(tok))

        index += 1

    return (None, None)


def _parse_tokens(tokens):
    """Parse the tokens.

    This converts the tokens into a form where we can manipulate them
    more easily.

    """

    index = 0
    parsed_tokens = []

    num_tokens = len(tokens)
    while index < num_tokens:
        tok = Token(*tokens[index])

        assert tok.token_type != token.INDENT
        if tok.token_type == tokenize.NEWLINE:
            # There's only one newline and it's at the end.
            break

        if tok.token_string in '([{':
            (container, index) = _parse_container(tokens, index)
            if not container:
                return None
            parsed_tokens.append(container)
        else:
            parsed_tokens.append(Atom(tok))

        index += 1

    return parsed_tokens


def _reflow_lines(parsed_tokens, indentation, max_line_length,
                  start_on_prefix_line):
    """Reflow the lines so that it looks nice."""

    if unicode(parsed_tokens[0]) == 'def':
        # A function definition gets indented a bit more.
        continued_indent = indentation + ' ' * 2 * DEFAULT_INDENT_SIZE
    else:
        continued_indent = indentation + ' ' * DEFAULT_INDENT_SIZE

    break_after_open_bracket = not start_on_prefix_line

    lines = ReformattedLines(max_line_length)
    lines.add_indent(len(indentation.lstrip('\r\n')))

    if not start_on_prefix_line:
        # If splitting after the opening bracket will cause the first element
        # to be aligned weirdly, don't try it.
        first_token = get_item(parsed_tokens, 0)
        second_token = get_item(parsed_tokens, 1)

        if (
            first_token and second_token and
            unicode(second_token)[0] == '(' and
            len(indentation) + len(first_token) + 1 == len(continued_indent)
        ):
            return None

    for item in parsed_tokens:
        lines.add_space_if_needed(unicode(item), equal=True)

        save_continued_indent = continued_indent
        if start_on_prefix_line and isinstance(item, Container):
            start_on_prefix_line = False
            continued_indent = ' ' * (lines.current_size() + 1)

        item.reflow(lines, continued_indent, break_after_open_bracket)
        continued_indent = save_continued_indent

    return lines.emit()


def _shorten_line_at_tokens_new(tokens, source, indentation,
                                max_line_length):
    """Shorten the line taking its length into account.

    The input is expected to be free of newlines except for inside
    multiline strings and at the end.

    """
    # Yield the original source so to see if it's a better choice than the
    # shortened candidate lines we generate here.
    yield indentation + source

    parsed_tokens = _parse_tokens(tokens)

    if parsed_tokens:
        # Perform two reflows. The first one starts on the same line as the
        # prefix. The second starts on the line after the prefix.
        fixed = _reflow_lines(parsed_tokens, indentation, max_line_length,
                              start_on_prefix_line=True)
        if fixed and check_syntax(normalize_multiline(fixed.lstrip())):
            yield fixed

        fixed = _reflow_lines(parsed_tokens, indentation, max_line_length,
                              start_on_prefix_line=False)
        if fixed and check_syntax(normalize_multiline(fixed.lstrip())):
            yield fixed


def _shorten_line_at_tokens(tokens, source, indentation, indent_word,
                            key_token_strings, aggressive):
    """Separate line by breaking at tokens in key_token_strings.

    The input is expected to be free of newlines except for inside
    multiline strings and at the end.

    """
    offsets = []
    for (index, _t) in enumerate(token_offsets(tokens)):
        (token_type,
         token_string,
         start_offset,
         end_offset) = _t

        assert token_type != token.INDENT

        if token_string in key_token_strings:
            # Do not break in containers with zero or one items.
            unwanted_next_token = {
                '(': ')',
                '[': ']',
                '{': '}'}.get(token_string)
            if unwanted_next_token:
                if (
                    get_item(tokens,
                             index + 1,
                             default=[None, None])[1] == unwanted_next_token or
                    get_item(tokens,
                             index + 2,
                             default=[None, None])[1] == unwanted_next_token
                ):
                    continue

            if (
                index > 2 and token_string == '(' and
                tokens[index - 1][1] in ',(%['
            ):
                # Don't split after a tuple start, or before a tuple start if
                # the tuple is in a list.
                continue

            if end_offset < len(source) - 1:
                # Don't split right before newline.
                offsets.append(end_offset)
        else:
            # Break at adjacent strings. These were probably meant to be on
            # separate lines in the first place.
            previous_token = get_item(tokens, index - 1)
            if (
                token_type == tokenize.STRING and
                previous_token and previous_token[0] == tokenize.STRING
            ):
                offsets.append(start_offset)

    current_indent = None
    fixed = None
    for line in split_at_offsets(source, offsets):
        if fixed:
            fixed += '\n' + current_indent + line

            for symbol in '([{':
                if line.endswith(symbol):
                    current_indent += indent_word
        else:
            # First line.
            fixed = line
            assert not current_indent
            current_indent = indent_word

    assert fixed is not None

    if check_syntax(normalize_multiline(fixed)
                    if aggressive > 1 else fixed):
        return indentation + fixed
    else:
        return None


def token_offsets(tokens):
    """Yield tokens and offsets."""
    end_offset = 0
    previous_end_row = 0
    previous_end_column = 0
    for t in tokens:
        token_type = t[0]
        token_string = t[1]
        (start_row, start_column) = t[2]
        (end_row, end_column) = t[3]

        # Account for the whitespace between tokens.
        end_offset += start_column
        if previous_end_row == start_row:
            end_offset -= previous_end_column

        # Record the start offset of the token.
        start_offset = end_offset

        # Account for the length of the token itself.
        end_offset += len(token_string)

        yield (token_type,
               token_string,
               start_offset,
               end_offset)

        previous_end_row = end_row
        previous_end_column = end_column


def normalize_multiline(line):
    """Normalize multiline-related code that will cause syntax error.

    This is for purposes of checking syntax.

    """
    if line.startswith('def ') and line.rstrip().endswith(':'):
        return line + ' pass'
    elif line.startswith('return '):
        return 'def _(): ' + line
    elif line.startswith('@'):
        return line + 'def _(): pass'
    elif line.startswith('class '):
        return line + ' pass'
    elif line.startswith('if '):
        return line + ' pass'
    else:
        return line


def fix_whitespace(line, offset, replacement):
    """Replace whitespace at offset and return fixed line."""
    # Replace escaped newlines too
    left = line[:offset].rstrip('\n\r \t\\')
    right = line[offset:].lstrip('\n\r \t\\')
    if right.startswith('#'):
        return line
    else:
        return left + replacement + right


def _execute_pep8(pep8_options, source):
    """Execute pep8 via python method calls."""
    class QuietReport(pep8.BaseReport):

        """Version of checker that does not print."""

        def __init__(self, options):
            super(QuietReport, self).__init__(options)
            self.__full_error_results = []

        def error(self, line_number, offset, text, _):
            """Collect errors."""
            code = super(QuietReport, self).error(line_number, offset, text, _)
            if code:
                self.__full_error_results.append(
                    {'id': code,
                     'line': line_number,
                     'column': offset + 1,
                     'info': text})

        def full_error_results(self):
            """Return error results in detail.

            Results are in the form of a list of dictionaries. Each
            dictionary contains 'id', 'line', 'column', and 'info'.

            """
            return self.__full_error_results

    checker = pep8.Checker('', lines=source,
                           reporter=QuietReport, **pep8_options)
    checker.check_all()
    return checker.report.full_error_results()


def _remove_leading_and_normalize(line):
    return line.lstrip().rstrip(CR + LF) + '\n'


class Reindenter(object):

    """Reindents badly-indented code to uniformly use four-space indentation.

    Released to the public domain, by Tim Peters, 03 October 2000.

    """

    def __init__(self, input_text):
        sio = io.StringIO(input_text)
        source_lines = sio.readlines()

        self.string_content_line_numbers = multiline_string_lines(input_text)

        # File lines, rstripped & tab-expanded. Dummy at start is so
        # that we can use tokenize's 1-based line numbering easily.
        # Note that a line is all-blank iff it is a newline.
        self.lines = []
        for line_number, line in enumerate(source_lines, start=1):
            # Do not modify if inside a multiline string.
            if line_number in self.string_content_line_numbers:
                self.lines.append(line)
            else:
                # Only expand leading tabs.
                self.lines.append(_get_indentation(line).expandtabs() +
                                  _remove_leading_and_normalize(line))

        self.lines.insert(0, None)
        self.index = 1  # index into self.lines of next line
        self.input_text = input_text

    def run(self, indent_size=DEFAULT_INDENT_SIZE):
        """Fix indentation and return modified line numbers.

        Line numbers are indexed at 1.

        """
        if indent_size < 1:
            return self.input_text

        try:
            stats = _reindent_stats(tokenize.generate_tokens(self.getline))
        except (SyntaxError, tokenize.TokenError):
            return self.input_text
        # Remove trailing empty lines.
        lines = self.lines
        while lines and lines[-1] == '\n':
            lines.pop()
        # Sentinel.
        stats.append((len(lines), 0))
        # Map count of leading spaces to # we want.
        have2want = {}
        # Program after transformation.
        after = []
        # Copy over initial empty lines -- there's nothing to do until
        # we see a line with *something* on it.
        i = stats[0][0]
        after.extend(lines[1:i])
        for i in range(len(stats) - 1):
            thisstmt, thislevel = stats[i]
            nextstmt = stats[i + 1][0]
            have = _leading_space_count(lines[thisstmt])
            want = thislevel * indent_size
            if want < 0:
                # A comment line.
                if have:
                    # An indented comment line. If we saw the same
                    # indentation before, reuse what it most recently
                    # mapped to.
                    want = have2want.get(have, -1)
                    if want < 0:
                        # Then it probably belongs to the next real stmt.
                        for j in range(i + 1, len(stats) - 1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                if have == _leading_space_count(lines[jline]):
                                    want = jlevel * indent_size
                                break
                    if want < 0:            # Maybe it's a hanging
                                            # comment like this one,
                        # in which case we should shift it like its base
                        # line got shifted.
                        for j in range(i - 1, -1, -1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                want = (have + _leading_space_count(
                                        after[jline - 1]) -
                                        _leading_space_count(lines[jline]))
                                break
                    if want < 0:
                        # Still no luck -- leave it alone.
                        want = have
                else:
                    want = 0
            assert want >= 0
            have2want[have] = want
            diff = want - have
            if diff == 0 or have == 0:
                after.extend(lines[thisstmt:nextstmt])
            else:
                for line_number, line in enumerate(lines[thisstmt:nextstmt],
                                                   start=thisstmt):
                    if line_number in self.string_content_line_numbers:
                        after.append(line)
                    elif diff > 0:
                        if line == '\n':
                            after.append(line)
                        else:
                            after.append(' ' * diff + line)
                    else:
                        remove = min(_leading_space_count(line), -diff)
                        after.append(line[remove:])

        return ''.join(after)

    def getline(self):
        """Line-getter for tokenize."""
        if self.index >= len(self.lines):
            line = ''
        else:
            line = self.lines[self.index]
            self.index += 1
        return line


def _reindent_stats(tokens):
    """Return list of (lineno, indentlevel) pairs.

    One for each stmt and comment line. indentlevel is -1 for comment lines, as
    a signal that tokenize doesn't know what to do about them; indeed, they're
    our headache!

    """
    find_stmt = 1  # Next token begins a fresh stmt?
    level = 0  # Current indent level.
    stats = []

    for t in tokens:
        token_type = t[0]
        sline = t[2][0]
        line = t[4]

        if token_type == tokenize.NEWLINE:
            # A program statement, or ENDMARKER, will eventually follow,
            # after some (possibly empty) run of tokens of the form
            #     (NL | COMMENT)* (INDENT | DEDENT+)?
            find_stmt = 1

        elif token_type == tokenize.INDENT:
            find_stmt = 1
            level += 1

        elif token_type == tokenize.DEDENT:
            find_stmt = 1
            level -= 1

        elif token_type == tokenize.COMMENT:
            if find_stmt:
                stats.append((sline, -1))
                # But we're still looking for a new stmt, so leave
                # find_stmt alone.

        elif token_type == tokenize.NL:
            pass

        elif find_stmt:
            # This is the first "real token" following a NEWLINE, so it
            # must be the first token of the next program statement, or an
            # ENDMARKER.
            find_stmt = 0
            if line:   # Not endmarker.
                stats.append((sline, level))

    return stats


def _leading_space_count(line):
    """Return number of leading spaces in line."""
    i = 0
    while i < len(line) and line[i] == ' ':
        i += 1
    return i


def refactor_with_2to3(source_text, fixer_names):
    """Use lib2to3 to refactor the source.

    Return the refactored source code.

    """
    from lib2to3.refactor import RefactoringTool
    fixers = ['lib2to3.fixes.fix_' + name for name in fixer_names]
    tool = RefactoringTool(fixer_names=fixers, explicit=fixers)

    from lib2to3.pgen2 import tokenize as lib2to3_tokenize
    try:
        return unicode(tool.refactor_string(source_text, name=''))
    except lib2to3_tokenize.TokenError:
        return source_text


def check_syntax(code):
    """Return True if syntax is okay."""
    try:
        return compile(code, '<string>', 'exec')
    except (SyntaxError, TypeError, UnicodeDecodeError):
        return False


def filter_results(source, results, aggressive):
    """Filter out spurious reports from pep8.

    If aggressive is True, we allow possibly unsafe fixes (E711, E712).

    """
    non_docstring_string_line_numbers = multiline_string_lines(
        source, include_docstrings=False)
    all_string_line_numbers = multiline_string_lines(
        source, include_docstrings=True)

    commented_out_code_line_numbers = commented_out_code_lines(source)

    for r in results:
        issue_id = r['id'].lower()

        if r['line'] in non_docstring_string_line_numbers:
            if issue_id.startswith(('e1', 'e501', 'w191')):
                continue

        if r['line'] in all_string_line_numbers:
            if issue_id in ['e501']:
                continue

        # We must offset by 1 for lines that contain the trailing contents of
        # multiline strings.
        if not aggressive and (r['line'] + 1) in all_string_line_numbers:
            # Do not modify multiline strings in non-aggressive mode. Remove
            # trailing whitespace could break doctests.
            if issue_id.startswith(('w29', 'w39')):
                continue

        if aggressive <= 0:
            if issue_id.startswith(('e711', 'w6')):
                continue

        if aggressive <= 1:
            if issue_id.startswith(('e712', 'e713')):
                continue

        if r['line'] in commented_out_code_line_numbers:
            if issue_id.startswith(('e26', 'e501')):
                continue

        yield r


def multiline_string_lines(source, include_docstrings=False):
    """Return line numbers that are within multiline strings.

    The line numbers are indexed at 1.

    Docstrings are ignored.

    """
    line_numbers = set()
    previous_token_type = ''
    try:
        for t in generate_tokens(source):
            token_type = t[0]
            start_row = t[2][0]
            end_row = t[3][0]

            if token_type == tokenize.STRING and start_row != end_row:
                if (
                    include_docstrings or
                    previous_token_type != tokenize.INDENT
                ):
                    # We increment by one since we want the contents of the
                    # string.
                    line_numbers |= set(range(1 + start_row, 1 + end_row))

            previous_token_type = token_type
    except (SyntaxError, tokenize.TokenError):
        pass

    return line_numbers


def commented_out_code_lines(source):
    """Return line numbers of comments that are likely code.

    Commented-out code is bad practice, but modifying it just adds even more
    clutter.

    """
    line_numbers = []
    try:
        for t in generate_tokens(source):
            token_type = t[0]
            token_string = t[1]
            start_row = t[2][0]
            line = t[4]

            # Ignore inline comments.
            if not line.lstrip().startswith('#'):
                continue

            if token_type == tokenize.COMMENT:
                stripped_line = token_string.lstrip('#').strip()
                if (
                    ' ' in stripped_line and
                    '#' not in stripped_line and
                    check_syntax(stripped_line)
                ):
                    line_numbers.append(start_row)
    except (SyntaxError, tokenize.TokenError):
        pass

    return line_numbers


def shorten_comment(line, max_line_length, last_comment=False):
    """Return trimmed or split long comment line.

    If there are no comments immediately following it, do a text wrap.
    Doing this wrapping on all comments in general would lead to jagged
    comment text.

    """
    assert len(line) > max_line_length
    line = line.rstrip()

    # PEP 8 recommends 72 characters for comment text.
    indentation = _get_indentation(line) + '# '
    max_line_length = min(max_line_length,
                          len(indentation) + 72)

    MIN_CHARACTER_REPEAT = 5
    if (
        len(line) - len(line.rstrip(line[-1])) >= MIN_CHARACTER_REPEAT and
        not line[-1].isalnum()
    ):
        # Trim comments that end with things like ---------
        return line[:max_line_length] + '\n'
    elif last_comment and re.match(r'\s*#+\s*\w+', line):
        import textwrap
        split_lines = textwrap.wrap(line.lstrip(' \t#'),
                                    initial_indent=indentation,
                                    subsequent_indent=indentation,
                                    width=max_line_length,
                                    break_long_words=False,
                                    break_on_hyphens=False)
        return '\n'.join(split_lines) + '\n'
    else:
        return line + '\n'


def normalize_line_endings(lines, newline):
    """Return fixed line endings.

    All lines will be modified to use the most common line ending.

    """
    return [line.rstrip('\n\r') + newline for line in lines]


def mutual_startswith(a, b):
    return b.startswith(a) or a.startswith(b)


def code_match(code, select, ignore):
    if ignore:
        assert not isinstance(ignore, unicode)
        for ignored_code in [c.strip() for c in ignore]:
            if mutual_startswith(code.lower(), ignored_code.lower()):
                return False

    if select:
        assert not isinstance(select, unicode)
        for selected_code in [c.strip() for c in select]:
            if mutual_startswith(code.lower(), selected_code.lower()):
                return True
        return False

    return True


def fix_code(source, options=None):
    """Return fixed source code."""
    if not options:
        options = parse_args([''])

    if not isinstance(source, unicode):
        source = source.decode(locale.getpreferredencoding())

    sio = io.StringIO(source)
    return fix_lines(sio.readlines(), options=options)


def fix_lines(source_lines, options, filename=''):
    """Return fixed source code."""
    # Transform everything to line feed. Then change them back to original
    # before returning fixed source code.
    original_newline = find_newline(source_lines)
    tmp_source = ''.join(normalize_line_endings(source_lines, '\n'))

    # Keep a history to break out of cycles.
    previous_hashes = set()

    if options.line_range:
        fixed_source = apply_local_fixes(tmp_source, options)
    else:
        # Apply global fixes only once (for efficiency).
        fixed_source = apply_global_fixes(tmp_source, options)

    passes = 0
    long_line_ignore_cache = set()
    while hash(fixed_source) not in previous_hashes:
        if options.pep8_passes >= 0 and passes > options.pep8_passes:
            break
        passes += 1

        previous_hashes.add(hash(fixed_source))

        tmp_source = copy.copy(fixed_source)

        fix = FixPEP8(
            filename,
            options,
            contents=tmp_source,
            long_line_ignore_cache=long_line_ignore_cache)

        fixed_source = fix.fix()

    sio = io.StringIO(fixed_source)
    return ''.join(normalize_line_endings(sio.readlines(), original_newline))


def fix_file(filename, options=None, output=None):
    if not options:
        options = parse_args([filename])

    original_source = readlines_from_file(filename)

    fixed_source = original_source

    if options.in_place or output:
        encoding = detect_encoding(filename)

    if output:
        output = codecs.getwriter(encoding)(output.buffer
                                            if hasattr(output, 'buffer')
                                            else output)

        output = LineEndingWrapper(output)

    fixed_source = fix_lines(fixed_source, options, filename=filename)

    if options.diff:
        new = io.StringIO(fixed_source)
        new = new.readlines()
        diff = get_diff_text(original_source, new, filename)
        if output:
            output.write(diff)
            output.flush()
        else:
            return diff
    elif options.in_place:
        fp = open_with_encoding(filename, encoding=encoding,
                                mode='w')
        fp.write(fixed_source)
        fp.close()
    else:
        if output:
            output.write(fixed_source)
            output.flush()
        else:
            return fixed_source


def global_fixes():
    """Yield multiple (code, function) tuples."""
    for function in globals().values():
        if inspect.isfunction(function):
            arguments = inspect.getargspec(function)[0]
            if arguments[:1] != ['source']:
                continue

            code = extract_code_from_function(function)
            if code:
                yield (code, function)


def apply_global_fixes(source, options, where='global'):
    """Run global fixes on source code.

    These are fixes that only need be done once (unlike those in
    FixPEP8, which are dependent on pep8).

    """
    if code_match('E101', select=options.select, ignore=options.ignore):
        source = reindent(source,
                          indent_size=options.indent_size)

    for (code, function) in global_fixes():
        if code_match(code, select=options.select, ignore=options.ignore):
            if options.verbose:
                print('--->  Applying {0} fix for {1}'.format(where,
                                                              code.upper()),
                      file=sys.stderr)
            source = function(source,
                              aggressive=options.aggressive)

    source = fix_2to3(source,
                      aggressive=options.aggressive,
                      select=options.select,
                      ignore=options.ignore)

    return source


def apply_local_fixes(source, options):
    """Ananologus to apply_global_fixes, but runs only those which makes sense
    for the given line_range.

    Do as much as we can without breaking code.

    """
    def find_ge(a, x):
        """Find leftmost item greater than or equal to x."""
        i = bisect.bisect_left(a, x)
        if i != len(a):
            return i, a[i]
        return len(a) - 1, a[-1]

    def find_le(a, x):
        """Find rightmost value less than or equal to x."""
        i = bisect.bisect_right(a, x)
        if i:
            return i - 1, a[i - 1]
        return 0, a[0]

    def local_fix(source, start_log, end_log,
                  start_lines, end_lines, indents, last_line):
        """apply_global_fixes to the source between start_log and end_log.

        The subsource must be the correct syntax of a complete python program
        (but all lines may share an indentation). The subsource's shared indent
        is removed, fixes are applied and the indent prepended back. Taking
        care to not reindent strings.

        last_line is the strict cut off (options.line_range[1]), so that
        lines after last_line are not modified.

        """
        if end_log < start_log:
            return source

        ind = indents[start_log]
        indent = _get_indentation(source[start_lines[start_log]])

        sl = slice(start_lines[start_log], end_lines[end_log] + 1)

        subsource = source[sl]
        # Remove indent from subsource.
        if ind:
            for line_no in start_lines[start_log:end_log + 1]:
                pos = line_no - start_lines[start_log]
                subsource[pos] = subsource[pos][ind:]

        # Fix indentation of subsource.
        fixed_subsource = apply_global_fixes(''.join(subsource),
                                             options,
                                             where='local')
        fixed_subsource = fixed_subsource.splitlines(True)

        # Add back indent for non multi-line strings lines.
        msl = multiline_string_lines(''.join(fixed_subsource),
                                     include_docstrings=False)
        for i, line in enumerate(fixed_subsource):
            if not i + 1 in msl:
                fixed_subsource[i] = indent + line if line != '\n' else line

        # We make a special case to look at the final line, if it's a multiline
        # *and* the cut off is somewhere inside it, we take the fixed
        # subset up until last_line, this assumes that the number of lines
        # does not change in this multiline line.
        changed_lines = len(fixed_subsource)
        if (start_lines[end_log] != end_lines[end_log]
                and end_lines[end_log] > last_line):
            after_end = end_lines[end_log] - last_line
            fixed_subsource = (fixed_subsource[:-after_end] +
                               source[sl][-after_end:])
            changed_lines -= after_end

            options.line_range[1] = (options.line_range[0] +
                                     changed_lines - 1)

        return (source[:start_lines[start_log]] +
                fixed_subsource +
                source[end_lines[end_log] + 1:])

    def is_continued_stmt(line,
                          continued_stmts=frozenset(['else', 'elif',
                                                     'finally', 'except'])):
        return re.split('[ :]', line.strip(), 1)[0] in continued_stmts

    assert options.line_range
    start, end = options.line_range
    start -= 1
    end -= 1
    last_line = end  # We shouldn't modify lines after this cut-off.

    try:
        logical = _find_logical(source)
    except (SyntaxError, tokenize.TokenError):
        return ''.join(source)

    if not logical[0]:
        # Just blank lines, this should imply that it will become '\n' ?
        return apply_global_fixes(source, options)

    start_lines, indents = zip(*logical[0])
    end_lines, _ = zip(*logical[1])

    source = source.splitlines(True)

    start_log, start = find_ge(start_lines, start)
    end_log, end = find_le(start_lines, end)

    # Look behind one line, if it's indented less than current indent
    # then we can move to this previous line knowing that its
    # indentation level will not be changed.
    if (start_log > 0
            and indents[start_log - 1] < indents[start_log]
            and not is_continued_stmt(source[start_log - 1])):
        start_log -= 1
        start = start_lines[start_log]

    while start < end:

        if is_continued_stmt(source[start]):
            start_log += 1
            start = start_lines[start_log]
            continue

        ind = indents[start_log]
        for t in itertools.takewhile(lambda t: t[1][1] >= ind,
                                     enumerate(logical[0][start_log:])):
            n_log, n = start_log + t[0], t[1][0]
        # start shares indent up to n.

        if n <= end:
            source = local_fix(source, start_log, n_log,
                               start_lines, end_lines,
                               indents, last_line)
            start_log = n_log if n == end else n_log + 1
            start = start_lines[start_log]
            continue

        else:
            # Look at the line after end and see if allows us to reindent.
            after_end_log, after_end = find_ge(start_lines, end + 1)

            if indents[after_end_log] > indents[start_log]:
                start_log, start = find_ge(start_lines, start + 1)
                continue

            if (indents[after_end_log] == indents[start_log]
                    and is_continued_stmt(source[after_end])):
                # find n, the beginning of the last continued statement
                # Apply fix to previous block if there is one.
                only_block = True
                for n, n_ind in logical[0][start_log:end_log + 1][::-1]:
                    if n_ind == ind and not is_continued_stmt(source[n]):
                        n_log = start_lines.index(n)
                        source = local_fix(source, start_log, n_log - 1,
                                           start_lines, end_lines,
                                           indents, last_line)
                        start_log = n_log + 1
                        start = start_lines[start_log]
                        only_block = False
                        break
                if only_block:
                    end_log, end = find_le(start_lines, end - 1)
                continue

            source = local_fix(source, start_log, end_log,
                               start_lines, end_lines,
                               indents, last_line)
            break

    return ''.join(source)


def extract_code_from_function(function):
    """Return code handled by function."""
    if not function.__name__.startswith('fix_'):
        return None

    code = re.sub('^fix_', '', function.__name__)
    if not code:
        return None

    try:
        int(code[1:])
    except ValueError:
        return None

    return code


def create_parser():
    """Return command-line parser."""
    # Do import locally to be friendly to those who use autopep8 as a library
    # and are supporting Python 2.6.
    import argparse

    parser = argparse.ArgumentParser(description=docstring_summary(__doc__),
                                     prog='autopep8')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('-v', '--verbose', action='count', dest='verbose',
                        default=0,
                        help='print verbose messages; '
                        'multiple -v result in more verbose messages')
    parser.add_argument('-d', '--diff', action='store_true', dest='diff',
                        help='print the diff for the fixed source')
    parser.add_argument('-i', '--in-place', action='store_true',
                        help='make changes to files in place')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='run recursively over directories; '
                        'must be used with --in-place or --diff')
    parser.add_argument('-j', '--jobs', type=int, metavar='n', default=1,
                        help='number of parallel jobs; '
                        'match CPU count if value is less than 1')
    parser.add_argument('-p', '--pep8-passes', metavar='n',
                        default=-1, type=int,
                        help='maximum number of additional pep8 passes '
                        '(default: infinite)')
    parser.add_argument('-a', '--aggressive', action='count', default=0,
                        help='enable non-whitespace changes; '
                        'multiple -a result in more aggressive changes')
    parser.add_argument('--experimental', action='store_true',
                        help='enable experimental fixes')
    parser.add_argument('--exclude', metavar='globs',
                        help='exclude file/directory names that match these '
                        'comma-separated globs')
    parser.add_argument('--list-fixes', action='store_true',
                        help='list codes for fixes; '
                        'used by --ignore and --select')
    parser.add_argument('--ignore', metavar='errors', default='',
                        help='do not fix these errors/warnings '
                        '(default: {0})'.format(DEFAULT_IGNORE))
    parser.add_argument('--select', metavar='errors', default='',
                        help='fix only these errors/warnings (e.g. E4,W)')
    parser.add_argument('--max-line-length', metavar='n', default=79, type=int,
                        help='set maximum allowed line length '
                        '(default: %(default)s)')
    parser.add_argument('--range', metavar='line', dest='line_range',
                        default=None, type=int, nargs=2,
                        help='only fix errors found within this inclusive '
                        'range of line numbers (e.g. 1 99); '
                        'line numbers are indexed at 1')
    parser.add_argument('--indent-size', default=DEFAULT_INDENT_SIZE,
                        type=int, metavar='n',
                        help='number of spaces per indent level '
                             '(default %(default)s)')
    parser.add_argument('files', nargs='*',
                        help="files to format or '-' for standard in")

    return parser


def parse_args(arguments):
    """Parse command-line options."""
    parser = create_parser()
    args = parser.parse_args(arguments)

    if not args.files and not args.list_fixes:
        parser.error('incorrect number of arguments')

    args.files = [decode_filename(name) for name in args.files]

    if '-' in args.files:
        if len(args.files) > 1:
            parser.error('cannot mix stdin and regular files')

        if args.diff:
            parser.error('--diff cannot be used with standard input')

        if args.in_place:
            parser.error('--in-place cannot be used with standard input')

        if args.recursive:
            parser.error('--recursive cannot be used with standard input')

    if len(args.files) > 1 and not (args.in_place or args.diff):
        parser.error('autopep8 only takes one filename as argument '
                     'unless the "--in-place" or "--diff" args are '
                     'used')

    if args.recursive and not (args.in_place or args.diff):
        parser.error('--recursive must be used with --in-place or --diff')

    if args.exclude and not args.recursive:
        parser.error('--exclude is only relevant when used with --recursive')

    if args.in_place and args.diff:
        parser.error('--in-place and --diff are mutually exclusive')

    if args.max_line_length <= 0:
        parser.error('--max-line-length must be greater than 0')

    if args.select:
        args.select = args.select.split(',')

    if args.ignore:
        args.ignore = args.ignore.split(',')
    elif not args.select:
        if args.aggressive:
            # Enable everything by default if aggressive.
            args.select = ['E', 'W']
        else:
            args.ignore = DEFAULT_IGNORE.split(',')

    if args.exclude:
        args.exclude = args.exclude.split(',')
    else:
        args.exclude = []

    if args.jobs < 1:
        # Do not import multiprocessing globally in case it is not supported
        # on the platform.
        import multiprocessing
        args.jobs = multiprocessing.cpu_count()

    if args.jobs > 1 and not args.in_place:
        parser.error('parallel jobs requires --in-place')

    if args.line_range:
        if args.line_range[0] <= 0:
            parser.error('--range must be positive numbers')
        if args.line_range[0] > args.line_range[1]:
            parser.error('First value of --range should be less than or equal '
                         'to the second')

    return args


def decode_filename(filename):
    """Return Unicode filename."""
    if isinstance(filename, unicode):
        return filename
    else:
        return filename.decode(sys.getfilesystemencoding())


def supported_fixes():
    """Yield pep8 error codes that autopep8 fixes.

    Each item we yield is a tuple of the code followed by its
    description.

    """
    yield ('E101', docstring_summary(reindent.__doc__))

    instance = FixPEP8(filename=None, options=None, contents='')
    for attribute in dir(instance):
        code = re.match('fix_([ew][0-9][0-9][0-9])', attribute)
        if code:
            yield (
                code.group(1).upper(),
                re.sub(r'\s+', ' ',
                       docstring_summary(getattr(instance, attribute).__doc__))
            )

    for (code, function) in sorted(global_fixes()):
        yield (code.upper() + (4 - len(code)) * ' ',
               re.sub(r'\s+', ' ', docstring_summary(function.__doc__)))

    for code in sorted(CODE_TO_2TO3):
        yield (code.upper() + (4 - len(code)) * ' ',
               re.sub(r'\s+', ' ', docstring_summary(fix_2to3.__doc__)))


def docstring_summary(docstring):
    """Return summary of docstring."""
    return docstring.split('\n')[0]


def line_shortening_rank(candidate, indent_word, max_line_length,
                         experimental=False):
    """Return rank of candidate.

    This is for sorting candidates.

    """
    if not candidate.strip():
        return 0

    rank = 0
    lines = candidate.split('\n')

    offset = 0
    if (
        not lines[0].lstrip().startswith('#') and
        lines[0].rstrip()[-1] not in '([{'
    ):
        for (opening, closing) in ('()', '[]', '{}'):
            # Don't penalize empty containers that aren't split up. Things like
            # this "foo(\n    )" aren't particularly good.
            opening_loc = lines[0].find(opening)
            closing_loc = lines[0].find(closing)
            if opening_loc >= 0:
                if closing_loc < 0 or closing_loc != opening_loc + 1:
                    offset = max(offset, 1 + opening_loc)

    current_longest = max(offset + len(x.strip()) for x in lines)

    rank += 4 * max(0, current_longest - max_line_length)

    rank += len(lines)

    # Too much variation in line length is ugly.
    rank += 2 * standard_deviation(len(line) for line in lines)

    bad_staring_symbol = {
        '(': ')',
        '[': ']',
        '{': '}'}.get(lines[0][-1])

    if len(lines) > 1:
        if (
            bad_staring_symbol and
            lines[1].lstrip().startswith(bad_staring_symbol)
        ):
            rank += 20

    for lineno, current_line in enumerate(lines):
        current_line = current_line.strip()

        if current_line.startswith('#'):
            continue

        for bad_start in ['.', '%', '+', '-', '/']:
            if current_line.startswith(bad_start):
                rank += 100

            # Do not tolerate operators on their own line.
            if current_line == bad_start:
                rank += 1000

        if current_line.endswith(('(', '[', '{', '.')):
            # Avoid lonely opening. They result in longer lines.
            if len(current_line) <= len(indent_word):
                rank += 100

            # Avoid the ugliness of ", (\n".
            if (
                current_line.endswith('(') and
                current_line[:-1].rstrip().endswith(',')
            ):
                rank += 100

            # Also avoid the ugliness of "foo.\nbar"
            if current_line.endswith('.'):
                rank += 100

            if has_arithmetic_operator(current_line):
                rank += 100

        if current_line.endswith(('%', '(', '[', '{')):
            rank -= 20

        # Try to break list comprehensions at the "for".
        if current_line.startswith('for '):
            rank -= 50

        if current_line.endswith('\\'):
            # If a line ends in \-newline, it may be part of a
            # multiline string. In that case, we would like to know
            # how long that line is without the \-newline. If it's
            # longer than the maximum, or has comments, then we assume
            # that the \-newline is an okay candidate and only
            # penalize it a bit.
            total_len = len(current_line)
            lineno += 1
            while lineno < len(lines):
                total_len += len(lines[lineno])

                if lines[lineno].lstrip().startswith('#'):
                    total_len = max_line_length
                    break

                if not lines[lineno].endswith('\\'):
                    break

                lineno += 1

            if total_len < max_line_length:
                rank += 10
            else:
                rank += 100 if experimental else 1

        # Prefer breaking at commas rather than colon.
        if ',' in current_line and current_line.endswith(':'):
            rank += 10

        rank += 10 * count_unbalanced_brackets(current_line)

    return max(0, rank)


def standard_deviation(numbers):
    """Return standard devation."""
    numbers = list(numbers)
    if not numbers:
        return 0
    mean = sum(numbers) / len(numbers)
    return (sum((n - mean) ** 2 for n in numbers) /
            len(numbers)) ** .5


def has_arithmetic_operator(line):
    """Return True if line contains any arithmetic operators."""
    for operator in pep8.ARITHMETIC_OP:
        if operator in line:
            return True

    return False


def count_unbalanced_brackets(line):
    """Return number of unmatched open/close brackets."""
    count = 0
    for opening, closing in ['()', '[]', '{}']:
        count += abs(line.count(opening) - line.count(closing))

    return count


def split_at_offsets(line, offsets):
    """Split line at offsets.

    Return list of strings.

    """
    result = []

    previous_offset = 0
    current_offset = 0
    for current_offset in sorted(offsets):
        if current_offset < len(line) and previous_offset != current_offset:
            result.append(line[previous_offset:current_offset].strip())
        previous_offset = current_offset

    result.append(line[current_offset:])

    return result


class LineEndingWrapper(object):

    r"""Replace line endings to work with sys.stdout.

    It seems that sys.stdout expects only '\n' as the line ending, no matter
    the platform. Otherwise, we get repeated line endings.

    """

    def __init__(self, output):
        self.__output = output

    def write(self, s):
        self.__output.write(s.replace('\r\n', '\n').replace('\r', '\n'))

    def flush(self):
        self.__output.flush()


def match_file(filename, exclude):
    """Return True if file is okay for modifying/recursing."""
    base_name = os.path.basename(filename)

    if base_name.startswith('.'):
        return False

    for pattern in exclude:
        if fnmatch.fnmatch(base_name, pattern):
            return False

    if not os.path.isdir(filename) and not is_python_file(filename):
        return False

    return True


def find_files(filenames, recursive, exclude):
    """Yield filenames."""
    while filenames:
        name = filenames.pop(0)
        if recursive and os.path.isdir(name):
            for root, directories, children in os.walk(name):
                filenames += [os.path.join(root, f) for f in children
                              if match_file(os.path.join(root, f),
                                            exclude)]
                directories[:] = [d for d in directories
                                  if match_file(os.path.join(root, d),
                                                exclude)]
        else:
            yield name


def _fix_file(parameters):
    """Helper function for optionally running fix_file() in parallel."""
    if parameters[1].verbose:
        print('[file:{0}]'.format(parameters[0]), file=sys.stderr)
    try:
        fix_file(*parameters)
    except IOError as error:
        print(unicode(error), file=sys.stderr)


def fix_multiple_files(filenames, options, output=None):
    """Fix list of files.

    Optionally fix files recursively.

    """
    filenames = find_files(filenames, options.recursive, options.exclude)
    if options.jobs > 1:
        import multiprocessing
        pool = multiprocessing.Pool(options.jobs)
        pool.map(_fix_file,
                 [(name, options) for name in filenames])
    else:
        for name in filenames:
            _fix_file((name, options, output))


def is_python_file(filename):
    """Return True if filename is Python file."""
    if filename.endswith('.py'):
        return True

    try:
        with open_with_encoding(filename) as f:
            first_line = f.readlines(1)[0]
    except (IOError, IndexError):
        return False

    if not PYTHON_SHEBANG_REGEX.match(first_line):
        return False

    return True


def is_probably_part_of_multiline(line):
    """Return True if line is likely part of a multiline string.

    When multiline strings are involved, pep8 reports the error as being
    at the start of the multiline string, which doesn't work for us.

    """
    return (
        '"""' in line or
        "'''" in line or
        line.rstrip().endswith('\\')
    )


def main():
    """Tool main."""
    try:
        # Exit on broken pipe.
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except AttributeError:  # pragma: no cover
        # SIGPIPE is not available on Windows.
        pass

    try:
        args = parse_args(sys.argv[1:])

        if args.list_fixes:
            for code, description in sorted(supported_fixes()):
                print('{code} - {description}'.format(
                    code=code, description=description))
            return 0

        if args.files == ['-']:
            assert not args.in_place

            # LineEndingWrapper is unnecessary here due to the symmetry between
            # standard in and standard out.
            sys.stdout.write(fix_code(sys.stdin.read(), args))
        else:
            if args.in_place or args.diff:
                args.files = list(set(args.files))
            else:
                assert len(args.files) == 1
                assert not args.recursive

            fix_multiple_files(args.files, args, sys.stdout)
    except KeyboardInterrupt:
        return 1  # pragma: no cover


class CachedTokenizer(object):

    """A one-element cache around tokenize.generate_tokens().

    Original code written by Ned Batchelder, in coverage.py.

    """

    def __init__(self):
        self.last_text = None
        self.last_tokens = None

    def generate_tokens(self, text):
        """A stand-in for tokenize.generate_tokens()."""
        if text != self.last_text:
            string_io = io.StringIO(text)
            self.last_tokens = list(
                tokenize.generate_tokens(string_io.readline)
            )
            self.last_text = text
        return self.last_tokens

_cached_tokenizer = CachedTokenizer()
generate_tokens = _cached_tokenizer.generate_tokens


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = acid
#!/usr/bin/env python
"""Test that autopep8 runs without crashing on various Python files."""

from __future__ import print_function

import argparse
import os
import random
import shlex
import sys
import subprocess
import tempfile


try:
    basestring
except NameError:
    basestring = str


ROOT_PATH = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]

# Override system-installed version of autopep8.
sys.path = [ROOT_PATH] + sys.path
import autopep8


if sys.stdout.isatty():
    YELLOW = '\x1b[33m'
    END = '\x1b[0m'
else:
    YELLOW = ''
    END = ''


RANDOM_MAX = 1000


def colored(text, color):
    """Return color coded text."""
    return color + text + END


def run(filename, command, max_line_length=79,
        ignore='', check_ignore='', verbose=False,
        comparison_function=None,
        aggressive=0, experimental=False, line_range=None, random_range=False):
    """Run autopep8 on file at filename.

    Return True on success.

    """
    if random_range:
        if not line_range:
            line_range = [1, RANDOM_MAX]
        first = random.randint(*line_range)
        line_range = [first, random.randint(first, line_range[1])]

    command = (shlex.split(command) + (['--verbose'] if verbose else []) +
               ['--max-line-length={0}'.format(max_line_length),
                '--ignore=' + ignore, filename] +
               aggressive * ['--aggressive'] +
               (['--experimental'] if experimental else []) +
               (['--range', str(line_range[0]), str(line_range[1])]
                if line_range else []))

    print(' '.join(command), file=sys.stderr)

    with tempfile.NamedTemporaryFile(suffix='.py') as tmp_file:
        if 0 != subprocess.call(command, stdout=tmp_file):
            sys.stderr.write('autopep8 crashed on ' + filename + '\n')
            return False

        if 0 != subprocess.call(
            ['pep8',
             '--ignore=' + ','.join([x for x in ignore.split(',') +
                                     check_ignore.split(',') if x]),
             '--show-source', tmp_file.name],
                stdout=sys.stdout):
            sys.stderr.write('autopep8 did not completely fix ' +
                             filename + '\n')

        try:
            if check_syntax(filename):
                try:
                    check_syntax(tmp_file.name, raise_error=True)
                except (SyntaxError, TypeError,
                        UnicodeDecodeError) as exception:
                    sys.stderr.write('autopep8 broke ' + filename + '\n' +
                                     str(exception) + '\n')
                    return False

                if comparison_function:
                    if not comparison_function(filename, tmp_file.name):
                        return False
        except IOError as exception:
            sys.stderr.write(str(exception) + '\n')

    return True


def check_syntax(filename, raise_error=False):
    """Return True if syntax is okay."""
    with autopep8.open_with_encoding(filename) as input_file:
        try:
            compile(input_file.read(), '<string>', 'exec', dont_inherit=True)
            return True
        except (SyntaxError, TypeError, UnicodeDecodeError):
            if raise_error:
                raise
            else:
                return False


def process_args():
    """Return processed arguments (options and positional arguments)."""
    compare_bytecode_ignore = 'E71,E721,W'

    parser = argparse.ArgumentParser()
    parser.add_argument('--command',
                        default=os.path.join(ROOT_PATH, 'autopep8.py'),
                        help='autopep8 command (default: %(default)s)')
    parser.add_argument('--ignore',
                        help='comma-separated errors to ignore',
                        default='')
    parser.add_argument('--check-ignore',
                        help='comma-separated errors to ignore when checking '
                        'for completeness (default: %(default)s)',
                        default='')
    parser.add_argument('--max-line-length', metavar='n', default=79, type=int,
                        help='set maximum allowed line length '
                        '(default: %(default)s)')
    parser.add_argument('--compare-bytecode', action='store_true',
                        help='compare bytecode before and after fixes; '
                        'sets default --ignore=' + compare_bytecode_ignore)
    parser.add_argument('-a', '--aggressive', action='count', default=0,
                        help='run autopep8 in aggressive mode')
    parser.add_argument('--experimental', action='store_true',
                        help='run experimental fixes')
    parser.add_argument('--range', metavar='line', dest='line_range',
                        default=None, type=int, nargs=2,
                        help='pass --range to autope8')
    parser.add_argument('--random-range', action='store_true',
                        help='pass random --range to autope8')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print verbose messages')
    parser.add_argument('paths', nargs='*',
                        help='paths to use for testing')

    args = parser.parse_args()

    if args.compare_bytecode and not args.ignore:
        args.ignore = compare_bytecode_ignore

    return args


def compare_bytecode(filename_a, filename_b):
    try:
        import pydiff
    except ImportError:
        raise SystemExit('pydiff required for bytecode comparison; '
                         'run "pip install pydiff"')

    diff = pydiff.diff_bytecode_of_files(filename_a, filename_b)

    if diff:
        sys.stderr.write('New bytecode does not match original:\n' +
                         diff + '\n')
    return not diff


def check(paths, args):
    """Run recursively run autopep8 on directory of files.

    Return False if the fix results in broken syntax.

    """
    if paths:
        dir_paths = paths
    else:
        dir_paths = [path for path in sys.path
                     if os.path.isdir(path)]

    filenames = dir_paths
    completed_filenames = set()

    if args.compare_bytecode:
        comparison_function = compare_bytecode
    else:
        comparison_function = None

    while filenames:
        try:
            name = os.path.realpath(filenames.pop(0))
            if not os.path.exists(name):
                # Invalid symlink.
                continue

            if name in completed_filenames:
                sys.stderr.write(
                    colored(
                        '--->  Skipping previously tested ' + name + '\n',
                        YELLOW))
                continue
            else:
                completed_filenames.update(name)
            if os.path.isdir(name):
                for root, directories, children in os.walk(name):
                    filenames += [os.path.join(root, f) for f in children
                                  if f.endswith('.py') and
                                  not f.startswith('.')]

                    directories[:] = [d for d in directories
                                      if not d.startswith('.')]
            else:
                verbose_message = '--->  Testing with ' + name
                sys.stderr.write(colored(verbose_message + '\n', YELLOW))

                if not run(os.path.join(name),
                           command=args.command,
                           max_line_length=args.max_line_length,
                           ignore=args.ignore,
                           check_ignore=args.check_ignore,
                           verbose=args.verbose,
                           comparison_function=comparison_function,
                           aggressive=args.aggressive,
                           experimental=args.experimental,
                           line_range=args.line_range,
                           random_range=args.random_range):
                    return False
        except (UnicodeDecodeError, UnicodeEncodeError) as exception:
            # Ignore annoying codec problems on Python 2.
            print(exception)
            continue

    return True


def main():
    """Run main."""
    args = process_args()
    return 0 if check(args.paths, args) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = acid_github
#!/usr/bin/env python
"""Run acid test against latest repositories on Github."""

import os
import re
import subprocess
import sys

import acid


TMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                       'github_tmp')


def latest_repositories():
    """Return names of latest released repositories on Github."""
    import requests

    try:
        for result in requests.get('https://github.com/timeline.json').json():
            try:
                repository = result['repository']
                size = repository['size']
                if 0 < size < 1000 and repository['language'] == 'Python':
                    yield repository['url']
            except KeyError:
                continue
    except (requests.exceptions.RequestException, ValueError):
        # Ignore GitHub server flakiness.
        pass


def download_repository(name, output_directory):
    """Download repository to output_directory.

    Raise CalledProcessError on failure.

    """
    subprocess.check_call(['git', 'clone', name],
                          cwd=output_directory)


def interesting(repository_path):
    """Return True if interesting."""
    print(repository_path)
    process = subprocess.Popen(['git', 'log'],
                               cwd=repository_path,
                               stdout=subprocess.PIPE)
    try:
        return len(re.findall(
            'pep8',
            process.communicate()[0].decode('utf-8'))) > 2
    except UnicodeDecodeError:
        return False


def complete(repository):
    """Fill in missing paths of URL."""
    if ':' in repository:
        return repository
    else:
        assert '/' in repository
        return 'https://github.com/' + repository.strip()


def main():
    """Run main."""
    try:
        os.mkdir(TMP_DIR)
    except OSError:
        pass

    args = acid.process_args()
    if args.paths:
        names = [complete(a) for a in args.paths]
    else:
        names = None

    checked_repositories = []
    skipped_repositories = []
    interesting_repositories = []
    while True:
        if args.paths:
            if not names:
                break
        else:
            while not names:
                # Continually populate if user did not specify a repository
                # explicitly.
                names = [p for p in latest_repositories()
                         if p not in checked_repositories and
                         p not in skipped_repositories]

                if not names:
                    import time
                    time.sleep(1)

        repository_name = names.pop(0)
        print(repository_name)

        user_tmp_dir = os.path.join(
            TMP_DIR,
            os.path.basename(os.path.split(repository_name)[0]))
        try:
            os.mkdir(user_tmp_dir)
        except OSError:
            pass

        repository_tmp_dir = os.path.join(
            user_tmp_dir,
            os.path.basename(repository_name))
        try:
            os.mkdir(repository_tmp_dir)
        except OSError:
            print('Skipping already checked repository')
            skipped_repositories.append(repository_name)
            continue

        try:
            download_repository(repository_name,
                                output_directory=repository_tmp_dir)
        except subprocess.CalledProcessError:
            print('ERROR: git clone failed')
            continue

        if acid.check([repository_tmp_dir], args):
            checked_repositories.append(repository_name)

            if interesting(
                os.path.join(repository_tmp_dir,
                             os.path.basename(repository_name))):
                interesting_repositories.append(repository_name)
        else:
            return 1

    if checked_repositories:
        print('\nTested repositories:')
        for name in checked_repositories:
            print('    ' + name +
                  (' *' if name in interesting_repositories else ''))

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = acid_pypi
#!/usr/bin/env python
"""Run acid test against latest packages on PyPi."""

from __future__ import print_function

import os
import subprocess
import sys

import acid


TMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                       'pypi_tmp')


def latest_packages(last_hours):
    """Return names of latest released packages on PyPi."""
    process = subprocess.Popen(
        ['yolk', '--latest-releases={hours}'.format(hours=last_hours)],
        stdout=subprocess.PIPE)

    for line in process.communicate()[0].decode('utf-8').split('\n'):
        if line:
            yield line.split()[0]


def download_package(name, output_directory):
    """Download package to output_directory.

    Raise CalledProcessError on failure.

    """
    subprocess.check_call(['yolk', '--fetch-package={name}'.format(name=name)],
                          cwd=output_directory)


def extract_package(path, output_directory):
    """Extract package at path."""
    if path.lower().endswith('.tar.gz'):
        import tarfile
        try:
            tar = tarfile.open(path)
            tar.extractall(path=output_directory)
            tar.close()
            return True
        except (tarfile.ReadError, IOError):
            return False
    elif path.lower().endswith('.zip'):
        import zipfile
        try:
            archive = zipfile.ZipFile(path)
            archive.extractall(path=output_directory)
            archive.close()
        except (zipfile.BadZipfile, IOError):
            return False
        return True

    return False


def main():
    """Run main."""
    try:
        os.mkdir(TMP_DIR)
    except OSError:
        pass

    args = acid.process_args()
    if args.paths:
        # Copy
        names = list(args.paths)
    else:
        names = None

    checked_packages = []
    skipped_packages = []
    last_hours = 1
    while True:
        if args.paths:
            if not names:
                break
        else:
            while not names:
                # Continually populate if user did not specify a package
                # explicitly.
                names = [p for p in latest_packages(last_hours)
                         if p not in checked_packages and
                         p not in skipped_packages]

                if not names:
                    last_hours *= 2

        package_name = names.pop(0)
        print(package_name)

        package_tmp_dir = os.path.join(TMP_DIR, package_name)
        try:
            os.mkdir(package_tmp_dir)
        except OSError:
            print('Skipping already checked package')
            skipped_packages.append(package_name)
            continue

        try:
            download_package(
                package_name,
                output_directory=package_tmp_dir)
        except subprocess.CalledProcessError:
            print('ERROR: yolk fetch failed')
            continue

        for download_name in os.listdir(package_tmp_dir):
            try:
                if not extract_package(
                        os.path.join(package_tmp_dir, download_name),
                        output_directory=package_tmp_dir):
                    print('ERROR: Could not extract package')
                    continue
            except UnicodeDecodeError:
                print('ERROR: Could not extract package')
                continue

            if acid.check([package_tmp_dir], args):
                checked_packages.append(package_name)
            else:
                return 1

    if checked_packages:
        print('\nTested packages:\n    ' + '\n    '.join(checked_packages))

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = bad_encoding
# -*- coding: zlatin-1 -*-

########NEW FILE########
__FILENAME__ = bad_encoding2
﻿#coding: utf8
print('我')

########NEW FILE########
__FILENAME__ = e101_example
# -*- coding: utf-8 -*-
# From https://github.com/coto/gae-boilerplate/blob/233a88c59e46bb10de7a901ef4e6a5b60d0006a5/web/handlers.py

"""
	This example will take a long time if we don't filter innocuous E101
	errors from pep8.
"""

import models.models as models
from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError
from webapp2_extras import security
from lib import utils
from lib import captcha
from lib.basehandler import BaseHandler
from lib.basehandler import user_required
from google.appengine.api import taskqueue
import logging
import config
import webapp2
import web.forms as forms
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from lib import twitter


class LoginBaseHandler(BaseHandler):
    """
    Base class for handlers with login form.
    """
    @webapp2.cached_property
    def form(self):
        return forms.LoginForm(self)


class RegisterBaseHandler(BaseHandler):
    """
    Base class for handlers with registration and login forms.
    """
    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.RegisterMobileForm(self)
        else:
            return forms.RegisterForm(self)

    @webapp2.cached_property
    def form_login(self):
        return forms.LoginForm(self)

    @webapp2.cached_property
    def forms(self):
        return {'form_login' : self.form_login,
                'form' : self.form}

class SendEmailHandler(BaseHandler):
    """
    Handler for sending Emails
    Use with TaskQueue
    """

    def post(self):
        to = self.request.get("to")
        subject = self.request.get("subject")
        body = self.request.get("body")
        sender = self.request.get("sender")

        utils.send_email(to, subject, body, sender)


class LoginHandler(LoginBaseHandler):
    """
    Handler for authentication
    """

    def get(self):
        """ Returns a simple HTML form for login """

        if self.user:
            self.redirect_to('home', id=self.user_id)
        params = {}
        return self.render_template('boilerplate_login.html', **params)

    def post(self):
        """
        username: Get the username from POST dict
        password: Get the password from POST dict
        """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()

        try:
            if utils.is_email_valid(username):
                user = models.User.get_by_email(username)
                if user:
                    auth_id = user.auth_ids[0]
                else:
                    raise InvalidAuthIdError
            else:
                auth_id = "own:%s" % username
                user = models.User.get_by_auth_id(auth_id)

            password = self.form.password.data.strip()
            remember_me = True if str(self.request.POST.get('remember_me')) == 'on' else False

            # Password to SHA512
            password = utils.encrypt(password, config.salt)

            # Try to login user with password
            # Raises InvalidAuthIdError if user is not found
            # Raises InvalidPasswordError if provided password
            # doesn't match with specified user
            self.auth.get_user_by_password(
                auth_id, password, remember=remember_me)

            # if user account is not activated, logout and redirect to home
            if (user.activated == False):
                # logout
                self.auth.unset_session()

                # redirect to home with error message
                resend_email_uri = self.uri_for('resend-account-activation', encoded_email=utils.encode(user.email))
                message = _('Sorry, your account') + ' <strong>{0:>s}</strong>'.format(username) + " " +\
                          _('has not been activated. Please check your email to activate your account') + ". " +\
                          _('Or click') + " <a href='"+resend_email_uri+"'>" + _('this') + "</a> " + _('to resend the email')
                self.add_message(message, 'error')
                return self.redirect_to('home')

            # check twitter association in session
            twitter_helper = twitter.TwitterAuth(self)
            twitter_association_data = twitter_helper.get_association_data()
            if twitter_association_data is not None:
                if models.SocialUser.check_unique(user.key, 'twitter', str(twitter_association_data['id'])):
                    social_user = models.SocialUser(
                        user = user.key,
                        provider = 'twitter',
                        uid = str(twitter_association_data['id']),
                        extra_data = twitter_association_data
                    )
                    social_user.put()

            logVisit = models.LogVisit(
                user=user.key,
                uastring=self.request.user_agent,
                ip=self.request.remote_addr,
                timestamp=utils.get_date_time()
            )
            logVisit.put()
            self.redirect_to('home')
        except (InvalidAuthIdError, InvalidPasswordError), e:
            # Returns error message to self.response.write in
            # the BaseHandler.dispatcher
            message = _("Login invalid, Try again.") + "<br/>" + _("Don't have an account?") + \
                    '  <a href="' + self.uri_for('register') + '">' + _("Sign Up") + '</a>'
            self.add_message(message, 'error')
            return self.redirect_to('login')


class SocialLoginHandler(BaseHandler):
    """
    Handler for Social authentication
    """

    def get(self, provider_name):
        provider_display_name = models.SocialUser.PROVIDERS_INFO[provider_name]['label']
        if not config.enable_federated_login:
            message = _('Federated login is disabled.')
            self.add_message(message,'warning')
            return self.redirect_to('login')
        callback_url = "%s/social_login/%s/complete" % (self.request.host_url, provider_name)
        if provider_name == "twitter":
            twitter_helper = twitter.TwitterAuth(self, redirect_uri=callback_url)
            self.redirect(twitter_helper.auth_url())
        else:
            message = _('%s authentication is not implemented yet.') % provider_display_name
            self.add_message(message,'warning')
            self.redirect_to('edit-profile')


class CallbackSocialLoginHandler(BaseHandler):
    """
    Callback (Save Information) for Social Authentication
    """

    def get(self, provider_name):
        if not config.enable_federated_login:
            message = _('Federated login is disabled.')
            self.add_message(message,'warning')
            return self.redirect_to('login')
        if provider_name == "twitter":
            oauth_token = self.request.get('oauth_token')
            oauth_verifier = self.request.get('oauth_verifier')
            twitter_helper = twitter.TwitterAuth(self)
            user_data = twitter_helper.auth_complete(oauth_token,
                oauth_verifier)
            if self.user:
                # new association with twitter
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, 'twitter', str(user_data['id'])):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = 'twitter',
                        uid = str(user_data['id']),
                        extra_data = user_data
                    )
                    social_user.put()

                    message = _('Twitter association added!')
                    self.add_message(message,'success')
                else:
                    message = _('This Twitter account is already in use!')
                    self.add_message(message,'error')
                self.redirect_to('edit-profile')
            else:
                # login with twitter
                social_user = models.SocialUser.get_by_provider_and_uid('twitter',
                    str(user_data['id']))
                if social_user:
                    # Social user exists. Need authenticate related site account
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    # Social user does not exists. Need show login and registration forms
                    twitter_helper.save_association_data(user_data)
                    message = _('Account with association to your Twitter does not exist. You can associate it right now, if you login with existing site account or create new on Sign up page.')
                    self.add_message(message,'info')
                    self.redirect_to('login')
            # Debug Callback information provided
#            for k,v in user_data.items():
#                print(k +":"+  v )
        # google, myopenid, yahoo OpenID Providers
        elif provider_name in models.SocialUser.open_id_providers():
            provider_display_name = models.SocialUser.PROVIDERS_INFO[provider_name]['label']
            # get info passed from OpenId Provider
            from google.appengine.api import users
            current_user = users.get_current_user()
            if current_user:
                if current_user.federated_identity():
                    uid = current_user.federated_identity()
                else:
                    uid = current_user.user_id()
                email = current_user.email()
            else:
                message = _('No user authentication information received from %s.  Please ensure you are logging in from an authorized OpenID Provider (OP).' % provider_display_name)
                self.add_message(message,'error')
                return self.redirect_to('login')
            if self.user:
                # add social account to user
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, provider_name, uid):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = provider_name,
                        uid = uid
                    )
                    social_user.put()

                    message = provider_display_name + _(' association added!')
                    self.add_message(message,'success')
                else:
                    message = _('This %s account is already in use!' % provider_display_name)
                    self.add_message(message,'error')
                self.redirect_to('edit-profile')
            else:
                # login with OpenId Provider
                social_user = models.SocialUser.get_by_provider_and_uid(provider_name, uid)
                if social_user:
                    # Social user found. Authenticate the user
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    # Social user does not exist yet so create it with the federated identity provided (uid)
                    # and create prerequisite user and log the user account in
                    if models.SocialUser.check_unique_uid(provider_name, uid):
                        # create user
                        # Returns a tuple, where first value is BOOL.
                        # If True ok, If False no new user is created
                        # Assume provider has already verified email address
                        # if email is provided so set activated to True
                        auth_id = "%s:%s" % (provider_name, uid)
                        if email:
                            unique_properties = ['email']
                            user_info = self.auth.store.user_model.create_user(
                                auth_id, unique_properties, email=email,
                                activated=True
                            )
                        else:
                            user_info = self.auth.store.user_model.create_user(
                                auth_id, activated=True
                            )
                        if not user_info[0]: #user is a tuple
                            message = _('This %s account is already in use!' % provider_display_name)
                            self.add_message(message, 'error')
                            return self.redirect_to('register')

                        user = user_info[1]

                        # create social user and associate with user
                        social_user = models.SocialUser(
                            user = user.key,
                            provider = provider_name,
                            uid = uid
                        )
                        social_user.put()
                        # authenticate user
                        self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                        logVisit = models.LogVisit(
                            user = user.key,
                            uastring = self.request.user_agent,
                            ip = self.request.remote_addr,
                            timestamp = utils.get_date_time()
                        )
                        logVisit.put()
                        self.redirect_to('home')

                        message = provider_display_name + _(' association added!')
                        self.add_message(message,'success')
                        self.redirect_to('home')
                    else:
                        message = _('This %s account is already in use!' % provider_display_name)
                        self.add_message(message,'error')
                    self.redirect_to('login')
        else:
            message = _('%s authentication is not implemented yet.') % provider_display_name
            self.add_message(message,'warning')
            self.redirect_to('login')


class DeleteSocialProviderHandler(BaseHandler):
    """
    Delete Social association with an account
    """

    @user_required
    def get(self, provider_name):
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            social_user = models.SocialUser.get_by_user_and_provider(user_info.key, provider_name)
            if social_user:
                social_user.key.delete()
                message = provider_name + _(' disassociated!')
                self.add_message(message,'success')
            else:
                message = _('Social account on ') + provider_name + _(' not found for this user!')
                self.add_message(message,'error')
        self.redirect_to('edit-profile')


class LogoutHandler(BaseHandler):
    """
    Destroy user session and redirect to login
    """

    def get(self):
        if self.user:
            message = _("You've signed out successfully.  Warning: Please clear all cookies and logout \
             of OpenId providers too if you logged in on a public computer.") # Info message
            self.add_message(message, 'info')

        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            self.redirect(self.auth_config['login_url'])
        except (AttributeError, KeyError), e:
            return _("User is logged out, but there was an error "\
                     "on the redirection.")


class RegisterHandler(RegisterBaseHandler):
    """
    Handler for Sign Up Users
    """

    def get(self):
        """ Returns a simple HTML form for create a new user """

        if self.user:
            self.redirect_to('home', id=self.user_id)
        params = {}
        return self.render_template('boilerplate_register.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        email = self.form.email.data.lower()
        password = self.form.password.data.strip()
        country = self.form.country.data

        # Password to SHA512
        password = utils.encrypt(password, config.salt)

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username', 'email']
        auth_id = "own:%s" % username
        user = self.auth.store.user_model.create_user(
            auth_id, unique_properties, password_raw=password,
            username=username, name=name, last_name=last_name, email=email,
            country=country, activated=False
        )

        if not user[0]: #user is a tuple
            message = _('Sorry, This user') + ' <strong>{0:>s}</strong>'.format(username) + " " +\
                      _('is already registered.')
            self.add_message(message, 'error')
            return self.redirect_to('register')
        else:
            # User registered successfully
            # But if the user registered using the form, the user has to check their email to activate the account ???
            try:
                user_info = models.User.get_by_email(email)
                if (user_info.activated == False):
                    # send email
                    subject = config.app_name + " Account Verification Email"
                    encoded_email = utils.encode(email)
                    confirmation_url = self.uri_for("account-activation",
                        encoded_email = encoded_email,
                        _full = True)

                    # load email's template
                    template_val = {
                        "app_name": config.app_name,
                        "username": username,
                        "confirmation_url": confirmation_url,
                        "support_url": self.uri_for("contact", _full=True)
                    }
                    body_path = "emails/account_activation.txt"
                    body = self.jinja2.render_template(body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url = email_url, params={
                        'to': str(email),
                        'subject' : subject,
                        'body' : body,
                        })

                    message = _('Congratulations') + ", " + str(username) + "! " + _('You are now registered') +\
                              ". " + _('Please check your email to activate your account')
                    self.add_message(message, 'success')
                    return self.redirect_to('home')

                # If the user didn't register using registration form ???
                db_user = self.auth.get_user_by_password(user[1].auth_ids[0], password)
                # Check twitter association in session
                twitter_helper = twitter.TwitterAuth(self)
                twitter_association_data = twitter_helper.get_association_data()
                if twitter_association_data is not None:
                    if models.SocialUser.check_unique(user[1].key, 'twitter', str(twitter_association_data['id'])):
                        social_user = models.SocialUser(
                            user = user[1].key,
                            provider = 'twitter',
                            uid = str(twitter_association_data['id']),
                            extra_data = twitter_association_data
                        )
                        social_user.put()
                message = _('Welcome') + " " + str(username) + ", " + _('you are now logged in.')
                self.add_message(message, 'success')
                return self.redirect_to('home')
            except (AttributeError, KeyError), e:
                message = _('Unexpected error creating '\
                            'user') + " " + '{0:>s}.'.format(username)
                self.add_message(message, 'error')
                self.abort(403)


class AccountActivationHandler(BaseHandler):
    """
    Handler for account activation
    """

    def get(self, encoded_email):
        try:
            email = utils.decode(encoded_email)
            user = models.User.get_by_email(email)

            # activate the user's account
            user.activated = True
            user.put()

            message = _('Congratulations') + "! " + _('Your account') + " (@" + user.username + ") " +\
                _('has just been activated') + ". " + _('Please login to your account')
            self.add_message(message, "success")
            self.redirect_to('login')

        except (AttributeError, KeyError, InvalidAuthIdError), e:
            message = _('Unexpected error activating '\
                        'account') + " " + '{0:>s}.'.format(user.username)
            self.add_message(message, 'error')
            self.abort(403)


class ResendActivationEmailHandler(BaseHandler):
    """
    Handler to resend activation email
    """

    def get(self, encoded_email):
        try:
            email = utils.decode(encoded_email)
            user = models.User.get_by_email(email)

            if (user.activated == False):
                # send email
                subject = config.app_name + " Account Verification Email"
                encoded_email = utils.encode(email)
                confirmation_url = self.uri_for("account-activation",
                    encoded_email = encoded_email,
                    _full = True)

                # load email's template
                template_val = {
                    "app_name": config.app_name,
                    "username": user.username,
                    "confirmation_url": confirmation_url,
                    "support_url": self.uri_for("contact", _full=True)
                }
                body_path = "emails/account_activation.txt"
                body = self.jinja2.render_template(body_path, **template_val)

                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url = email_url, params={
                    'to': str(email),
                    'subject' : subject,
                    'body' : body,
                    })

                message = _('The verification email has been resent to') + " " + str(email) + ". " +\
                    _('Please check your email to activate your account')
                self.add_message(message, "success")
                return self.redirect_to('home')
            else:
                message = _('Your account has been activated') + ". " +\
                    _('Please login to your account')
                self.add_message(message, "warning")
                return self.redirect_to('home')

        except (KeyError, AttributeError), e:
            message = _('Sorry') + ". " + _('Some error occurred') + "."
            self.add_message(message, "error")
            return self.redirect_to('home')


class ContactHandler(BaseHandler):
    """
    Handler for Contact Form
    """

    def get(self):
        """ Returns a simple HTML for contact form """

        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            if user_info.name or user_info.last_name:
                self.form.name.data = user_info.name + " " + user_info.last_name
            if user_info.email:
                self.form.email.data = user_info.email
        params = {
            "exception" : self.request.get('exception')
            }

        return self.render_template('boilerplate_contact.html', **params)

    def post(self):
        """ validate contact form """

        if not self.form.validate():
            return self.get()
        remoteip  = self.request.remote_addr
        user_agent  = self.request.user_agent
        exception = self.request.POST.get('exception')
        name = self.form.name.data.strip()
        email = self.form.email.data.lower()
        message = self.form.message.data.strip()

        try:
            subject = _("Contact")
            body = ""
            # exceptions for error pages that redirect to contact
            if exception != "":
                body = "* Exception error: %s" % exception
            body = body + """
            * IP Address: %s
            * Web Browser: %s

            * Sender name: %s
            * Sender email: %s
            * Message: %s
            """ % (remoteip, user_agent, name, email, message)

            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url = email_url, params={
                'to': config.contact_recipient,
                'subject' : subject,
                'body' : body,
                'sender' : config.contact_sender,
                })

            message = _('Message sent successfully.')
            self.add_message(message, 'success')
            return self.redirect_to('contact')

        except (AttributeError, KeyError), e:
            message = _('Error sending the message. Please try again later.')
            self.add_message(message, 'error')
            return self.redirect_to('contact')

    @webapp2.cached_property
    def form(self):
        return forms.ContactForm(self)


class EditProfileHandler(BaseHandler):
    """
    Handler for Edit User Profile
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit profile """

        params = {}
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            self.form.username.data = user_info.username
            self.form.name.data = user_info.name
            self.form.last_name.data = user_info.last_name
            self.form.country.data = user_info.country
            providers_info = user_info.get_social_providers_info()
            params['used_providers'] = providers_info['used']
            params['unused_providers'] = providers_info['unused']
            params['country'] = user_info.country

        return self.render_template('boilerplate_edit_profile.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        country = self.form.country.data

        try:
            user_info = models.User.get_by_id(long(self.user_id))

            try:
                message=''
                # update username if it has changed and it isn't already taken
                if username != user_info.username:
                    user_info.unique_properties = ['username','email']
                    uniques = [
                               'User.username:%s' % username,
                               'User.auth_id:own:%s' % username,
                               ]
                    # Create the unique username and auth_id.
                    success, existing = Unique.create_multi(uniques)
                    if success:
                        # free old uniques
                        Unique.delete_multi(['User.username:%s' % user_info.username, 'User.auth_id:own:%s' % user_info.username])
                        # The unique values were created, so we can save the user.
                        user_info.username=username
                        user_info.auth_ids[0]='own:%s' % username
                        message+= _('Your new username is ') + '<strong>' + username + '</strong>.'

                    else:
                        message+= _('Username') + " <strong>" + username + "</strong> " + _('is already taken. It is not changed.')
                        # At least one of the values is not unique.
                        self.add_message(message,'error')
                        return self.get()
                user_info.name=name
                user_info.last_name=last_name
                user_info.country=country
                user_info.put()
                message+= " " + _('Your profile has been updated!')
                self.add_message(message,'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                message = _('Unable to update profile!')
                logging.error('Unable to update profile: ' + e)
                self.add_message(message,'error')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = _('Sorry you are not logged in!')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditProfileForm(self)


class EditPasswordHandler(BaseHandler):
    """
    Handler for Edit User Password
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for editing password """

        params = {}
        return self.render_template('boilerplate_edit_password.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        current_password = self.form.current_password.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = models.User.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username

            # Password to SHA512
            current_password = utils.encrypt(current_password, config.salt)
            try:
                user = models.User.get_by_auth_password(auth_id, current_password)
                # Password to SHA512
                password = utils.encrypt(password, config.salt)
                user.password = security.generate_password_hash(password, length=12)
                user.put()

                # send email
                subject = config.app_name + " Account Password Changed"

                # load email's template
                template_val = {
                    "app_name": config.app_name,
                    "first_name": user.name,
                    "username": user.username,
                    "email": user.email,
                    "reset_password_url": self.uri_for("password-reset", _full=True)
                }
                email_body_path = "emails/password_changed.txt"
                email_body = self.jinja2.render_template(email_body_path, **template_val)
                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url = email_url, params={
                    'to': user.email,
                    'subject' : subject,
                    'body' : email_body,
                    'sender' : config.contact_sender,
                    })

                # Login User
                self.auth.get_user_by_password(user.auth_ids[0], password)
                self.add_message(_('Password changed successfully'), 'success')
                return self.redirect_to('edit-profile')
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Your Current Password is wrong, please try again")
                self.add_message(message, 'error')
                return self.redirect_to('edit-password')
        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in!')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.EditPasswordMobileForm(self)
        else:
            return forms.EditPasswordForm(self)


class EditEmailHandler(BaseHandler):
    """
    Handler for Edit User's Email
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit email """

        params = {}
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            self.form.new_email.data = user_info.email

        return self.render_template('boilerplate_edit_email.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        new_email = self.form.new_email.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = models.User.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username
            # Password to SHA512
            password = utils.encrypt(password, config.salt)

            try:
                # authenticate user by its password
                user = models.User.get_by_auth_password(auth_id, password)

                # if the user change his/her email address
                if new_email != user.email:

                    # check whether the new email has been used by another user
                    aUser = models.User.get_by_email(new_email)
                    if aUser is not None:
                        message = _("The email %s is already registered." % new_email)
                        self.add_message(message, "error")
                        return self.redirect_to("edit-email")

                    # send email
                    subject = config.app_name + " Email Changed Notification"
                    user_token = models.User.create_auth_token(self.user_id)
                    confirmation_url = self.uri_for("email-changed-check",
                        user_id = user_info.get_id(),
                        encoded_email = utils.encode(new_email),
                        token = user_token,
                        _full = True)

                    # load email's template
                    template_val = {
                        "app_name": config.app_name,
                        "first_name": user.name,
                        "username": user.username,
                        "new_email": new_email,
                        "confirmation_url": confirmation_url,
                        "support_url": self.uri_for("contact", _full=True)
                    }

                    old_body_path = "emails/email_changed_notification_old.txt"
                    old_body = self.jinja2.render_template(old_body_path, **template_val)

                    new_body_path = "emails/email_changed_notification_new.txt"
                    new_body = self.jinja2.render_template(new_body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url = email_url, params={
                        'to': user.email,
                        'subject' : subject,
                        'body' : old_body,
                        })
                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url = email_url, params={
                        'to': new_email,
                        'subject' : subject,
                        'body' : new_body,
                        })

                    logging.error(user)

                    # display successful message
                    msg = _("Please check your new email for confirmation. Your email will be updated after confirmation.")
                    self.add_message(msg, 'success')
                    return self.redirect_to('edit-profile')

                else:
                    self.add_message(_("You didn't change your email"), "warning")
                    return self.redirect_to("edit-email")


            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Your password is wrong, please try again")
                self.add_message(message, 'error')
                return self.redirect_to('edit-email')

        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in!')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditEmailForm(self)


class PasswordResetHandler(LoginBaseHandler):
    """
    Password Reset Handler with Captcha
    """

    reCaptcha_public_key = config.captcha_public_key
    reCaptcha_private_key = config.captcha_private_key

    def get(self):
        chtml = captcha.displayhtml(
            public_key = self.reCaptcha_public_key,
            use_ssl = False,
            error = None)
        params = {
            'captchahtml': chtml,
            }
        return self.render_template('boilerplate_password_reset.html', **params)

    def post(self):
        # check captcha
        challenge = self.request.POST.get('recaptcha_challenge_field')
        response  = self.request.POST.get('recaptcha_response_field')
        remoteip  = self.request.remote_addr

        cResponse = captcha.submit(
            challenge,
            response,
            self.reCaptcha_private_key,
            remoteip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            logging.warning(cResponse.error_code)
            _message = _('Wrong image verification code. Please try again.')
            self.add_message(_message, 'error')
            return self.redirect_to('password-reset')
            # check if we got an email or username
        email_or_username = str(self.request.POST.get('email_or_username')).lower().strip()
        if utils.is_email_valid(email_or_username):
            user = models.User.get_by_email(email_or_username)
            _message = _("If the e-mail address you entered") + " (<strong>%s</strong>) " % email_or_username
        else:
            auth_id = "own:%s" % email_or_username
            user = models.User.get_by_auth_id(auth_id)
            _message = _("If the username you entered") + " (<strong>%s</strong>) " % email_or_username

        if user is not None:
            user_id = user.get_id()
            token = models.User.create_auth_token(user_id)
            email_url = self.uri_for('taskqueue-send-email')
            reset_url = self.uri_for('password-reset-check', user_id=user_id, token=token, _full=True)
            subject = _("Password reminder")
            body = _('Please click below to create a new password:') +\
                   """

                   %s
                   """ % reset_url
            taskqueue.add(url = email_url, params={
                'to': user.email,
                'subject' : subject,
                'body' : body,
                'sender' : config.contact_sender,
                })
            _message = _message + _("is associated with an account in our records, you will receive "\
                                    "an e-mail from us with instructions for resetting your password. "\
                                    "<br>If you don't receive this e-mail, please check your junk mail folder or ") +\
                       '<a href="' + self.uri_for('contact') + '">' + _('contact us') + '</a> ' +  _("for further assistance.")
            self.add_message(_message, 'success')
            return self.redirect_to('login')
        _message = _('Your email / username was not found. Please try another or ') + '<a href="' + self.uri_for('register') + '">' + _('create an account') + '</a>'
        self.add_message(_message, 'error')
        return self.redirect_to('password-reset')


class PasswordResetCompleteHandler(LoginBaseHandler):
    """
    Handler to process the link of reset password that received the user
    """

    def get(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        params = {}
        if verify[0] is None:
            message = _('There was an error or the link is outdated. Please copy and paste the link from your email or enter your details again below to get a new one.')
            self.add_message(message, 'warning')
            return self.redirect_to('password-reset')

        else:
            return self.render_template('boilerplate_password_reset_complete.html', **params)

    def post(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        user = verify[0]
        password = self.form.password.data.strip()
        if user and self.form.validate():
            # Password to SHA512
            password = utils.encrypt(password, config.salt)

            user.password = security.generate_password_hash(password, length=12)
            user.put()
            # Delete token
            models.User.delete_auth_token(int(user_id), token)
            # Login User
            self.auth.get_user_by_password(user.auth_ids[0], password)
            self.add_message(_('Password changed successfully'), 'success')
            return self.redirect_to('home')

        else:
            self.add_message(_('Please correct the form errors.'), 'error')
            return self.redirect_to('password-reset-check', user_id=user_id, token=token)

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.PasswordResetCompleteMobileForm(self)
        else:
            return forms.PasswordResetCompleteForm(self)


class EmailChangedCompleteHandler(BaseHandler):
    """
    Handler for completed email change
    Will be called when the user click confirmation link from email
    """

    def get(self, user_id, encoded_email, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        email = utils.decode(encoded_email)
        if verify[0] is None:
            self.add_message('There was an error or the link is outdated. Please copy and paste the link from your email.', 'warning')
            self.redirect_to('home')

        else:
            # save new email
            user = verify[0]
            user.email = email
            user.put()
            # delete token
            models.User.delete_auth_token(int(user_id), token)
            # add successful message and redirect
            self.add_message("Your email has been successfully updated!", "success")
            self.redirect_to('edit-profile')


class SecureRequestHandler(BaseHandler):
    """
    Only accessible to users that are logged in
    """

    @user_required
    def get(self, **kwargs):
        user_session = self.user
        user_session_object = self.auth.store.get_session(self.request)

        user_info = models.User.get_by_id(long( self.user_id ))
        user_info_object = self.auth.store.user_model.get_by_auth_token(
            user_session['user_id'], user_session['token'])

        try:
            params = {
                "user_session" : user_session,
                "user_session_object" : user_session_object,
                "user_info" : user_info,
                "user_info_object" : user_info_object,
                "userinfo_logout-url" : self.auth_config['logout_url'],
                }
            return self.render_template('boilerplate_secure_zone.html', **params)
        except (AttributeError, KeyError), e:
            return _("Secure zone error:") + " %s." % e


class HomeRequestHandler(RegisterBaseHandler):
    """
    Handler to show the home page
    """

    def get(self):
        """ Returns a simple HTML form for home """
        params = {}
        return self.render_template('boilerplate_home.html', **params)

########NEW FILE########
__FILENAME__ = example
import sys, os

def foo():
    import subprocess, argparse
    import copy; import math, email


print(1) 
print(2) # e261
d = {1: 2,# e261
     3: 4}
print(2)  ## e262
print(2)  #### e262
print(2)  #e262
print(2)  #     e262
1 /1
1 *2
1 +1
1 -1
1 **2


def dummy1 ( a ):
    print(a) 
    print(a)


def dummy2(a) :
    if 1 in a:
        print("a")
        print(1+1)   # e225
        print(1 +1)  # e225
        print(1+ 1)  # e225


        print(1  +1)  # e221+e225
        print(1  + 1)  # e221
        print(1  * 1)  # e221
        print(1 +  1)  # e222
        print(1 *    1)  # e222
    print(a)


def func1():
    print("A")
    
    return 0



def func11():
    a = (1,2, 3,"a")
    b = [1, 2, 3,"b"]
    c = 0,11/2
    return 1




# comment after too empty lines
def func2():
    pass
def func22():
    pass;


def func_oneline(): print(1)

def func_last():
    if True: print(1)
    pass


def func_e251(a, b=1, c = 3):
    pass


def func_e251_t(a, b=1, c = 3, d = 4):
    pass


# e201
(         1)
[         1]
{         1: 2}

# e202
(1        )
[1        ]
{1: 2     }

# e203
{4           : 2}
[4           , 2]

# e211
d = [1]
d  	 [0]
dummy1  	  (0)


def func_e702():
    4; 1;
    4; 1;	  
    4; 1;

    4; 1;
    print(2); print(4);          6;8
    if True:
        1; 2; 3
0; 1
2;3
4;     5;


def func_w602():
    raise ValueError, "w602 test"
    raise ValueError, "w602 test"  # my comment

    raise ValueError
    raise ValueError  # comment

    raise ValueError, 'arg'   ; print(1)
    raise ValueError, 'arg'   ; print(2) # my comment

    raise ValueError, \
        'arg no comment'
    raise ValueError, \
        'arg'  # my comment
    raise ValueError, \
        """arg"""  # my comment
    raise ValueError, \
        """arg

  """  # my comment
    raise ValueError, \
        '''multiline

'''  # my comment

    a = 'a'
    raise ValueError, "%s" % (a,)

    raise 'string'


def func_w603():
    if 1 <> 2:
        if 2 <> 2:
            print(True)
        else:
            print(False)


def func_w604():
    a = 1.1
    b = ```a```

def func_e101():
	print('abc')
	if True:
	    print('hello')

if __name__ == '__main__': func_last()
  

########NEW FILE########
__FILENAME__ = example_with_reduce
"""Package resource API
--------------------

A resource is a logical file contained within a package, or a logical
subdirectory thereof.  The package resource API expects resource names
to have their path parts separated with ``/``, *not* whatever the local
path separator is.  Do not use os.path operations to manipulate resource
names being passed into the API.

The package resource API is designed to work with normal filesystem packages,
.egg files, and unpacked .egg files.  It can also work in a limited way with
.zip files and with custom PEP 302 loaders that support the ``get_data()``
method.
"""

import sys
import os
import time
import re
import imp
import zipfile
import zipimport
import warnings
import stat
import functools
import pkgutil
import token
import symbol
import operator
import platform
from pkgutil import get_importer

try:
    from urlparse import urlparse, urlunparse
except ImportError:
    from urllib.parse import urlparse, urlunparse

try:
    frozenset
except NameError:
    from sets import ImmutableSet as frozenset
try:
    basestring
    next = lambda o: o.next()
    from cStringIO import StringIO as BytesIO
except NameError:
    basestring = str
    from io import BytesIO
    def execfile(fn, globs=None, locs=None):
        if globs is None:
            globs = globals()
        if locs is None:
            locs = globs
        exec(compile(open(fn).read(), fn, 'exec'), globs, locs)

# capture these to bypass sandboxing
from os import utime
try:
    from os import mkdir, rename, unlink
    WRITE_SUPPORT = True
except ImportError:
    # no write support, probably under GAE
    WRITE_SUPPORT = False

from os import open as os_open
from os.path import isdir, split

# Avoid try/except due to potential problems with delayed import mechanisms.
if sys.version_info >= (3, 3) and sys.implementation.name == "cpython":
    import importlib._bootstrap as importlib_bootstrap
else:
    importlib_bootstrap = None

try:
    import parser
except ImportError:
    pass

def _bypass_ensure_directory(name, mode=0x1FF):  # 0777
    # Sandbox-bypassing version of ensure_directory()
    if not WRITE_SUPPORT:
        raise IOError('"os.mkdir" not supported on this platform.')
    dirname, filename = split(name)
    if dirname and filename and not isdir(dirname):
        _bypass_ensure_directory(dirname)
        mkdir(dirname, mode)


_state_vars = {}

def _declare_state(vartype, **kw):
    g = globals()
    for name, val in kw.items():
        g[name] = val
        _state_vars[name] = vartype

def __getstate__():
    state = {}
    g = globals()
    for k, v in _state_vars.items():
        state[k] = g['_sget_'+v](g[k])
    return state

def __setstate__(state):
    g = globals()
    for k, v in state.items():
        g['_sset_'+_state_vars[k]](k, g[k], v)
    return state

def _sget_dict(val):
    return val.copy()

def _sset_dict(key, ob, state):
    ob.clear()
    ob.update(state)

def _sget_object(val):
    return val.__getstate__()

def _sset_object(key, ob, state):
    ob.__setstate__(state)

_sget_none = _sset_none = lambda *args: None


def get_supported_platform():
    """Return this platform's maximum compatible version.

    distutils.util.get_platform() normally reports the minimum version
    of Mac OS X that would be required to *use* extensions produced by
    distutils.  But what we want when checking compatibility is to know the
    version of Mac OS X that we are *running*.  To allow usage of packages that
    explicitly require a newer version of Mac OS X, we must also know the
    current version of the OS.

    If this condition occurs for any other platform with a version in its
    platform strings, this function should be extended accordingly.
    """
    plat = get_build_platform()
    m = macosVersionString.match(plat)
    if m is not None and sys.platform == "darwin":
        try:
            plat = 'macosx-%s-%s' % ('.'.join(_macosx_vers()[:2]), m.group(3))
        except ValueError:
            pass    # not Mac OS X
    return plat

__all__ = [
    # Basic resource access and distribution/entry point discovery
    'require', 'run_script', 'get_provider',  'get_distribution',
    'load_entry_point', 'get_entry_map', 'get_entry_info', 'iter_entry_points',
    'resource_string', 'resource_stream', 'resource_filename',
    'resource_listdir', 'resource_exists', 'resource_isdir',

    # Environmental control
    'declare_namespace', 'working_set', 'add_activation_listener',
    'find_distributions', 'set_extraction_path', 'cleanup_resources',
    'get_default_cache',

    # Primary implementation classes
    'Environment', 'WorkingSet', 'ResourceManager',
    'Distribution', 'Requirement', 'EntryPoint',

    # Exceptions
    'ResolutionError','VersionConflict','DistributionNotFound','UnknownExtra',
    'ExtractionError',

    # Parsing functions and string utilities
    'parse_requirements', 'parse_version', 'safe_name', 'safe_version',
    'get_platform', 'compatible_platforms', 'yield_lines', 'split_sections',
    'safe_extra', 'to_filename', 'invalid_marker', 'evaluate_marker',

    # filesystem utilities
    'ensure_directory', 'normalize_path',

    # Distribution "precedence" constants
    'EGG_DIST', 'BINARY_DIST', 'SOURCE_DIST', 'CHECKOUT_DIST', 'DEVELOP_DIST',

    # "Provider" interfaces, implementations, and registration/lookup APIs
    'IMetadataProvider', 'IResourceProvider', 'FileMetadata',
    'PathMetadata', 'EggMetadata', 'EmptyProvider', 'empty_provider',
    'NullProvider', 'EggProvider', 'DefaultProvider', 'ZipProvider',
    'register_finder', 'register_namespace_handler', 'register_loader_type',
    'fixup_namespace_packages', 'get_importer',

    # Deprecated/backward compatibility only
    'run_main', 'AvailableDistributions',
]

class ResolutionError(Exception):
    """Abstract base for dependency resolution errors"""
    def __repr__(self):
        return self.__class__.__name__+repr(self.args)

class VersionConflict(ResolutionError):
    """An already-installed version conflicts with the requested version"""

class DistributionNotFound(ResolutionError):
    """A requested distribution was not found"""

class UnknownExtra(ResolutionError):
    """Distribution doesn't have an "extra feature" of the given name"""
_provider_factories = {}

PY_MAJOR = sys.version[:3]
EGG_DIST = 3
BINARY_DIST = 2
SOURCE_DIST = 1
CHECKOUT_DIST = 0
DEVELOP_DIST = -1

def register_loader_type(loader_type, provider_factory):
    """Register `provider_factory` to make providers for `loader_type`

    `loader_type` is the type or class of a PEP 302 ``module.__loader__``,
    and `provider_factory` is a function that, passed a *module* object,
    returns an ``IResourceProvider`` for that module.
    """
    _provider_factories[loader_type] = provider_factory

def get_provider(moduleOrReq):
    """Return an IResourceProvider for the named module or requirement"""
    if isinstance(moduleOrReq,Requirement):
        return working_set.find(moduleOrReq) or require(str(moduleOrReq))[0]
    try:
        module = sys.modules[moduleOrReq]
    except KeyError:
        __import__(moduleOrReq)
        module = sys.modules[moduleOrReq]
    loader = getattr(module, '__loader__', None)
    return _find_adapter(_provider_factories, loader)(module)

def _macosx_vers(_cache=[]):
    if not _cache:
        import platform
        version = platform.mac_ver()[0]
        # fallback for MacPorts
        if version == '':
            import plistlib
            plist = '/System/Library/CoreServices/SystemVersion.plist'
            if os.path.exists(plist):
                if hasattr(plistlib, 'readPlist'):
                    plist_content = plistlib.readPlist(plist)
                    if 'ProductVersion' in plist_content:
                        version = plist_content['ProductVersion']

        _cache.append(version.split('.'))
    return _cache[0]

def _macosx_arch(machine):
    return {'PowerPC':'ppc', 'Power_Macintosh':'ppc'}.get(machine,machine)

def get_build_platform():
    """Return this platform's string for platform-specific distributions

    XXX Currently this is the same as ``distutils.util.get_platform()``, but it
    needs some hacks for Linux and Mac OS X.
    """
    try:
        # Python 2.7 or >=3.2
        from sysconfig import get_platform
    except ImportError:
        from distutils.util import get_platform

    plat = get_platform()
    if sys.platform == "darwin" and not plat.startswith('macosx-'):
        try:
            version = _macosx_vers()
            machine = os.uname()[4].replace(" ", "_")
            return "macosx-%d.%d-%s" % (int(version[0]), int(version[1]),
                _macosx_arch(machine))
        except ValueError:
            # if someone is running a non-Mac darwin system, this will fall
            # through to the default implementation
            pass
    return plat

macosVersionString = re.compile(r"macosx-(\d+)\.(\d+)-(.*)")
darwinVersionString = re.compile(r"darwin-(\d+)\.(\d+)\.(\d+)-(.*)")
get_platform = get_build_platform   # XXX backward compat


def compatible_platforms(provided,required):
    """Can code for the `provided` platform run on the `required` platform?

    Returns true if either platform is ``None``, or the platforms are equal.

    XXX Needs compatibility checks for Linux and other unixy OSes.
    """
    if provided is None or required is None or provided==required:
        return True     # easy case

    # Mac OS X special cases
    reqMac = macosVersionString.match(required)
    if reqMac:
        provMac = macosVersionString.match(provided)

        # is this a Mac package?
        if not provMac:
            # this is backwards compatibility for packages built before
            # setuptools 0.6. All packages built after this point will
            # use the new macosx designation.
            provDarwin = darwinVersionString.match(provided)
            if provDarwin:
                dversion = int(provDarwin.group(1))
                macosversion = "%s.%s" % (reqMac.group(1), reqMac.group(2))
                if dversion == 7 and macosversion >= "10.3" or \
                        dversion == 8 and macosversion >= "10.4":

                    #import warnings
                    #warnings.warn("Mac eggs should be rebuilt to "
                    #    "use the macosx designation instead of darwin.",
                    #    category=DeprecationWarning)
                    return True
            return False    # egg isn't macosx or legacy darwin

        # are they the same major version and machine type?
        if provMac.group(1) != reqMac.group(1) or \
                provMac.group(3) != reqMac.group(3):
            return False

        # is the required OS major update >= the provided one?
        if int(provMac.group(2)) > int(reqMac.group(2)):
            return False

        return True

    # XXX Linux and other platforms' special cases should go here
    return False


def run_script(dist_spec, script_name):
    """Locate distribution `dist_spec` and run its `script_name` script"""
    ns = sys._getframe(1).f_globals
    name = ns['__name__']
    ns.clear()
    ns['__name__'] = name
    require(dist_spec)[0].run_script(script_name, ns)

run_main = run_script   # backward compatibility

def get_distribution(dist):
    """Return a current distribution object for a Requirement or string"""
    if isinstance(dist,basestring): dist = Requirement.parse(dist)
    if isinstance(dist,Requirement): dist = get_provider(dist)
    if not isinstance(dist,Distribution):
        raise TypeError("Expected string, Requirement, or Distribution", dist)
    return dist

def load_entry_point(dist, group, name):
    """Return `name` entry point of `group` for `dist` or raise ImportError"""
    return get_distribution(dist).load_entry_point(group, name)

def get_entry_map(dist, group=None):
    """Return the entry point map for `group`, or the full entry map"""
    return get_distribution(dist).get_entry_map(group)

def get_entry_info(dist, group, name):
    """Return the EntryPoint object for `group`+`name`, or ``None``"""
    return get_distribution(dist).get_entry_info(group, name)


class IMetadataProvider:

    def has_metadata(name):
        """Does the package's distribution contain the named metadata?"""

    def get_metadata(name):
        """The named metadata resource as a string"""

    def get_metadata_lines(name):
        """Yield named metadata resource as list of non-blank non-comment lines

       Leading and trailing whitespace is stripped from each line, and lines
       with ``#`` as the first non-blank character are omitted."""

    def metadata_isdir(name):
        """Is the named metadata a directory?  (like ``os.path.isdir()``)"""

    def metadata_listdir(name):
        """List of metadata names in the directory (like ``os.listdir()``)"""

    def run_script(script_name, namespace):
        """Execute the named script in the supplied namespace dictionary"""


class IResourceProvider(IMetadataProvider):
    """An object that provides access to package resources"""

    def get_resource_filename(manager, resource_name):
        """Return a true filesystem path for `resource_name`

        `manager` must be an ``IResourceManager``"""

    def get_resource_stream(manager, resource_name):
        """Return a readable file-like object for `resource_name`

        `manager` must be an ``IResourceManager``"""

    def get_resource_string(manager, resource_name):
        """Return a string containing the contents of `resource_name`

        `manager` must be an ``IResourceManager``"""

    def has_resource(resource_name):
        """Does the package contain the named resource?"""

    def resource_isdir(resource_name):
        """Is the named resource a directory?  (like ``os.path.isdir()``)"""

    def resource_listdir(resource_name):
        """List of resource names in the directory (like ``os.listdir()``)"""


class WorkingSet(object):
    """A collection of active distributions on sys.path (or a similar list)"""

    def __init__(self, entries=None):
        """Create working set from list of path entries (default=sys.path)"""
        self.entries = []
        self.entry_keys = {}
        self.by_key = {}
        self.callbacks = []

        if entries is None:
            entries = sys.path

        for entry in entries:
            self.add_entry(entry)

    def add_entry(self, entry):
        """Add a path item to ``.entries``, finding any distributions on it

        ``find_distributions(entry, True)`` is used to find distributions
        corresponding to the path entry, and they are added.  `entry` is
        always appended to ``.entries``, even if it is already present.
        (This is because ``sys.path`` can contain the same value more than
        once, and the ``.entries`` of the ``sys.path`` WorkingSet should always
        equal ``sys.path``.)
        """
        self.entry_keys.setdefault(entry, [])
        self.entries.append(entry)
        for dist in find_distributions(entry, True):
            self.add(dist, entry, False)

    def __contains__(self,dist):
        """True if `dist` is the active distribution for its project"""
        return self.by_key.get(dist.key) == dist

    def find(self, req):
        """Find a distribution matching requirement `req`

        If there is an active distribution for the requested project, this
        returns it as long as it meets the version requirement specified by
        `req`.  But, if there is an active distribution for the project and it
        does *not* meet the `req` requirement, ``VersionConflict`` is raised.
        If there is no active distribution for the requested project, ``None``
        is returned.
        """
        dist = self.by_key.get(req.key)
        if dist is not None and dist not in req:
            raise VersionConflict(dist,req)     # XXX add more info
        else:
            return dist

    def iter_entry_points(self, group, name=None):
        """Yield entry point objects from `group` matching `name`

        If `name` is None, yields all entry points in `group` from all
        distributions in the working set, otherwise only ones matching
        both `group` and `name` are yielded (in distribution order).
        """
        for dist in self:
            entries = dist.get_entry_map(group)
            if name is None:
                for ep in entries.values():
                    yield ep
            elif name in entries:
                yield entries[name]

    def run_script(self, requires, script_name):
        """Locate distribution for `requires` and run `script_name` script"""
        ns = sys._getframe(1).f_globals
        name = ns['__name__']
        ns.clear()
        ns['__name__'] = name
        self.require(requires)[0].run_script(script_name, ns)

    def __iter__(self):
        """Yield distributions for non-duplicate projects in the working set

        The yield order is the order in which the items' path entries were
        added to the working set.
        """
        seen = {}
        for item in self.entries:
            if item not in self.entry_keys:
                # workaround a cache issue
                continue

            for key in self.entry_keys[item]:
                if key not in seen:
                    seen[key]=1
                    yield self.by_key[key]

    def add(self, dist, entry=None, insert=True):
        """Add `dist` to working set, associated with `entry`

        If `entry` is unspecified, it defaults to the ``.location`` of `dist`.
        On exit from this routine, `entry` is added to the end of the working
        set's ``.entries`` (if it wasn't already present).

        `dist` is only added to the working set if it's for a project that
        doesn't already have a distribution in the set.  If it's added, any
        callbacks registered with the ``subscribe()`` method will be called.
        """
        if insert:
            dist.insert_on(self.entries, entry)

        if entry is None:
            entry = dist.location
        keys = self.entry_keys.setdefault(entry,[])
        keys2 = self.entry_keys.setdefault(dist.location,[])
        if dist.key in self.by_key:
            return      # ignore hidden distros

        self.by_key[dist.key] = dist
        if dist.key not in keys:
            keys.append(dist.key)
        if dist.key not in keys2:
            keys2.append(dist.key)
        self._added_new(dist)

    def resolve(self, requirements, env=None, installer=None):
        """List all distributions needed to (recursively) meet `requirements`

        `requirements` must be a sequence of ``Requirement`` objects.  `env`,
        if supplied, should be an ``Environment`` instance.  If
        not supplied, it defaults to all distributions available within any
        entry or distribution in the working set.  `installer`, if supplied,
        will be invoked with each requirement that cannot be met by an
        already-installed distribution; it should return a ``Distribution`` or
        ``None``.
        """

        requirements = list(requirements)[::-1]  # set up the stack
        processed = {}  # set of processed requirements
        best = {}  # key -> dist
        to_activate = []

        while requirements:
            req = requirements.pop(0)   # process dependencies breadth-first
            if req in processed:
                # Ignore cyclic or redundant dependencies
                continue
            dist = best.get(req.key)
            if dist is None:
                # Find the best distribution and add it to the map
                dist = self.by_key.get(req.key)
                if dist is None:
                    if env is None:
                        env = Environment(self.entries)
                    dist = best[req.key] = env.best_match(req, self, installer)
                    if dist is None:
                        #msg = ("The '%s' distribution was not found on this "
                        #       "system, and is required by this application.")
                        #raise DistributionNotFound(msg % req)

                        # unfortunately, zc.buildout uses a str(err)
                        # to get the name of the distribution here..
                        raise DistributionNotFound(req)
                to_activate.append(dist)
            if dist not in req:
                # Oops, the "best" so far conflicts with a dependency
                raise VersionConflict(dist,req) # XXX put more info here
            requirements.extend(dist.requires(req.extras)[::-1])
            processed[req] = True

        return to_activate    # return list of distros to activate

    def find_plugins(self, plugin_env, full_env=None, installer=None,
            fallback=True):
        """Find all activatable distributions in `plugin_env`

        Example usage::

            distributions, errors = working_set.find_plugins(
                Environment(plugin_dirlist)
            )
            map(working_set.add, distributions)  # add plugins+libs to sys.path
            print 'Could not load', errors        # display errors

        The `plugin_env` should be an ``Environment`` instance that contains
        only distributions that are in the project's "plugin directory" or
        directories. The `full_env`, if supplied, should be an ``Environment``
        contains all currently-available distributions.  If `full_env` is not
        supplied, one is created automatically from the ``WorkingSet`` this
        method is called on, which will typically mean that every directory on
        ``sys.path`` will be scanned for distributions.

        `installer` is a standard installer callback as used by the
        ``resolve()`` method. The `fallback` flag indicates whether we should
        attempt to resolve older versions of a plugin if the newest version
        cannot be resolved.

        This method returns a 2-tuple: (`distributions`, `error_info`), where
        `distributions` is a list of the distributions found in `plugin_env`
        that were loadable, along with any other distributions that are needed
        to resolve their dependencies.  `error_info` is a dictionary mapping
        unloadable plugin distributions to an exception instance describing the
        error that occurred. Usually this will be a ``DistributionNotFound`` or
        ``VersionConflict`` instance.
        """

        plugin_projects = list(plugin_env)
        plugin_projects.sort()  # scan project names in alphabetic order

        error_info = {}
        distributions = {}

        if full_env is None:
            env = Environment(self.entries)
            env += plugin_env
        else:
            env = full_env + plugin_env

        shadow_set = self.__class__([])
        list(map(shadow_set.add, self))   # put all our entries in shadow_set

        for project_name in plugin_projects:

            for dist in plugin_env[project_name]:

                req = [dist.as_requirement()]

                try:
                    resolvees = shadow_set.resolve(req, env, installer)

                except ResolutionError:
                    v = sys.exc_info()[1]
                    error_info[dist] = v    # save error info
                    if fallback:
                        continue    # try the next older version of project
                    else:
                        break       # give up on this project, keep going

                else:
                    list(map(shadow_set.add, resolvees))
                    distributions.update(dict.fromkeys(resolvees))

                    # success, no need to try any more versions of this project
                    break

        distributions = list(distributions)
        distributions.sort()

        return distributions, error_info

    def require(self, *requirements):
        """Ensure that distributions matching `requirements` are activated

        `requirements` must be a string or a (possibly-nested) sequence
        thereof, specifying the distributions and versions required.  The
        return value is a sequence of the distributions that needed to be
        activated to fulfill the requirements; all relevant distributions are
        included, even if they were already activated in this working set.
        """
        needed = self.resolve(parse_requirements(requirements))

        for dist in needed:
            self.add(dist)

        return needed

    def subscribe(self, callback):
        """Invoke `callback` for all distributions (including existing ones)"""
        if callback in self.callbacks:
            return
        self.callbacks.append(callback)
        for dist in self:
            callback(dist)

    def _added_new(self, dist):
        for callback in self.callbacks:
            callback(dist)

    def __getstate__(self):
        return (
            self.entries[:], self.entry_keys.copy(), self.by_key.copy(),
            self.callbacks[:]
        )

    def __setstate__(self, e_k_b_c):
        entries, keys, by_key, callbacks = e_k_b_c
        self.entries = entries[:]
        self.entry_keys = keys.copy()
        self.by_key = by_key.copy()
        self.callbacks = callbacks[:]


class Environment(object):
    """Searchable snapshot of distributions on a search path"""

    def __init__(self, search_path=None, platform=get_supported_platform(), python=PY_MAJOR):
        """Snapshot distributions available on a search path

        Any distributions found on `search_path` are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.

        `platform` is an optional string specifying the name of the platform
        that platform-specific distributions must be compatible with.  If
        unspecified, it defaults to the current platform.  `python` is an
        optional string naming the desired version of Python (e.g. ``'3.3'``);
        it defaults to the current version.

        You may explicitly set `platform` (and/or `python`) to ``None`` if you
        wish to map *all* distributions, not just those compatible with the
        running platform or Python version.
        """
        self._distmap = {}
        self._cache = {}
        self.platform = platform
        self.python = python
        self.scan(search_path)

    def can_add(self, dist):
        """Is distribution `dist` acceptable for this environment?

        The distribution must match the platform and python version
        requirements specified when this environment was created, or False
        is returned.
        """
        return (self.python is None or dist.py_version is None
            or dist.py_version==self.python) \
            and compatible_platforms(dist.platform,self.platform)

    def remove(self, dist):
        """Remove `dist` from the environment"""
        self._distmap[dist.key].remove(dist)

    def scan(self, search_path=None):
        """Scan `search_path` for distributions usable in this environment

        Any distributions found are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.  Only distributions conforming to
        the platform/python version defined at initialization are added.
        """
        if search_path is None:
            search_path = sys.path

        for item in search_path:
            for dist in find_distributions(item):
                self.add(dist)

    def __getitem__(self,project_name):
        """Return a newest-to-oldest list of distributions for `project_name`
        """
        try:
            return self._cache[project_name]
        except KeyError:
            project_name = project_name.lower()
            if project_name not in self._distmap:
                return []

        if project_name not in self._cache:
            dists = self._cache[project_name] = self._distmap[project_name]
            _sort_dists(dists)

        return self._cache[project_name]

    def add(self,dist):
        """Add `dist` if we ``can_add()`` it and it isn't already added"""
        if self.can_add(dist) and dist.has_version():
            dists = self._distmap.setdefault(dist.key,[])
            if dist not in dists:
                dists.append(dist)
                if dist.key in self._cache:
                    _sort_dists(self._cache[dist.key])

    def best_match(self, req, working_set, installer=None):
        """Find distribution best matching `req` and usable on `working_set`

        This calls the ``find(req)`` method of the `working_set` to see if a
        suitable distribution is already active.  (This may raise
        ``VersionConflict`` if an unsuitable version of the project is already
        active in the specified `working_set`.)  If a suitable distribution
        isn't active, this method returns the newest distribution in the
        environment that meets the ``Requirement`` in `req`.  If no suitable
        distribution is found, and `installer` is supplied, then the result of
        calling the environment's ``obtain(req, installer)`` method will be
        returned.
        """
        dist = working_set.find(req)
        if dist is not None:
            return dist
        for dist in self[req.key]:
            if dist in req:
                return dist
        return self.obtain(req, installer) # try and download/install

    def obtain(self, requirement, installer=None):
        """Obtain a distribution matching `requirement` (e.g. via download)

        Obtain a distro that matches requirement (e.g. via download).  In the
        base ``Environment`` class, this routine just returns
        ``installer(requirement)``, unless `installer` is None, in which case
        None is returned instead.  This method is a hook that allows subclasses
        to attempt other ways of obtaining a distribution before falling back
        to the `installer` argument."""
        if installer is not None:
            return installer(requirement)

    def __iter__(self):
        """Yield the unique project names of the available distributions"""
        for key in self._distmap.keys():
            if self[key]: yield key

    def __iadd__(self, other):
        """In-place addition of a distribution or environment"""
        if isinstance(other,Distribution):
            self.add(other)
        elif isinstance(other,Environment):
            for project in other:
                for dist in other[project]:
                    self.add(dist)
        else:
            raise TypeError("Can't add %r to environment" % (other,))
        return self

    def __add__(self, other):
        """Add an environment or distribution to an environment"""
        new = self.__class__([], platform=None, python=None)
        for env in self, other:
            new += env
        return new


AvailableDistributions = Environment    # XXX backward compatibility


class ExtractionError(RuntimeError):
    """An error occurred extracting a resource

    The following attributes are available from instances of this exception:

    manager
        The resource manager that raised this exception

    cache_path
        The base directory for resource extraction

    original_error
        The exception instance that caused extraction to fail
    """


class ResourceManager:
    """Manage resource extraction and packages"""
    extraction_path = None

    def __init__(self):
        self.cached_files = {}

    def resource_exists(self, package_or_requirement, resource_name):
        """Does the named resource exist?"""
        return get_provider(package_or_requirement).has_resource(resource_name)

    def resource_isdir(self, package_or_requirement, resource_name):
        """Is the named resource an existing directory?"""
        return get_provider(package_or_requirement).resource_isdir(
            resource_name
        )

    def resource_filename(self, package_or_requirement, resource_name):
        """Return a true filesystem path for specified resource"""
        return get_provider(package_or_requirement).get_resource_filename(
            self, resource_name
        )

    def resource_stream(self, package_or_requirement, resource_name):
        """Return a readable file-like object for specified resource"""
        return get_provider(package_or_requirement).get_resource_stream(
            self, resource_name
        )

    def resource_string(self, package_or_requirement, resource_name):
        """Return specified resource as a string"""
        return get_provider(package_or_requirement).get_resource_string(
            self, resource_name
        )

    def resource_listdir(self, package_or_requirement, resource_name):
        """List the contents of the named resource directory"""
        return get_provider(package_or_requirement).resource_listdir(
            resource_name
        )

    def extraction_error(self):
        """Give an error message for problems extracting file(s)"""

        old_exc = sys.exc_info()[1]
        cache_path = self.extraction_path or get_default_cache()

        err = ExtractionError("""Can't extract file(s) to egg cache

The following error occurred while trying to extract file(s) to the Python egg
cache:

  %s

The Python egg cache directory is currently set to:

  %s

Perhaps your account does not have write access to this directory?  You can
change the cache directory by setting the PYTHON_EGG_CACHE environment
variable to point to an accessible directory.
""" % (old_exc, cache_path)
        )
        err.manager = self
        err.cache_path = cache_path
        err.original_error = old_exc
        raise err

    def get_cache_path(self, archive_name, names=()):
        """Return absolute location in cache for `archive_name` and `names`

        The parent directory of the resulting path will be created if it does
        not already exist.  `archive_name` should be the base filename of the
        enclosing egg (which may not be the name of the enclosing zipfile!),
        including its ".egg" extension.  `names`, if provided, should be a
        sequence of path name parts "under" the egg's extraction location.

        This method should only be called by resource providers that need to
        obtain an extraction location, and only for names they intend to
        extract, as it tracks the generated names for possible cleanup later.
        """
        extract_path = self.extraction_path or get_default_cache()
        target_path = os.path.join(extract_path, archive_name+'-tmp', *names)
        try:
            _bypass_ensure_directory(target_path)
        except:
            self.extraction_error()

        self._warn_unsafe_extraction_path(extract_path)

        self.cached_files[target_path] = 1
        return target_path

    @staticmethod
    def _warn_unsafe_extraction_path(path):
        """
        If the default extraction path is overridden and set to an insecure
        location, such as /tmp, it opens up an opportunity for an attacker to
        replace an extracted file with an unauthorized payload. Warn the user
        if a known insecure location is used.

        See Distribute #375 for more details.
        """
        if os.name == 'nt' and not path.startswith(os.environ['windir']):
            # On Windows, permissions are generally restrictive by default
            #  and temp directories are not writable by other users, so
            #  bypass the warning.
            return
        mode = os.stat(path).st_mode
        if mode & stat.S_IWOTH or mode & stat.S_IWGRP:
            msg = ("%s is writable by group/others and vulnerable to attack "
                "when "
                "used with get_resource_filename. Consider a more secure "
                "location (set with .set_extraction_path or the "
                "PYTHON_EGG_CACHE environment variable)." % path)
            warnings.warn(msg, UserWarning)

    def postprocess(self, tempname, filename):
        """Perform any platform-specific postprocessing of `tempname`

        This is where Mac header rewrites should be done; other platforms don't
        have anything special they should do.

        Resource providers should call this method ONLY after successfully
        extracting a compressed resource.  They must NOT call it on resources
        that are already in the filesystem.

        `tempname` is the current (temporary) name of the file, and `filename`
        is the name it will be renamed to by the caller after this routine
        returns.
        """

        if os.name == 'posix':
            # Make the resource executable
            mode = ((os.stat(tempname).st_mode) | 0x16D) & 0xFFF # 0555, 07777
            os.chmod(tempname, mode)

    def set_extraction_path(self, path):
        """Set the base path where resources will be extracted to, if needed.

        If you do not call this routine before any extractions take place, the
        path defaults to the return value of ``get_default_cache()``.  (Which
        is based on the ``PYTHON_EGG_CACHE`` environment variable, with various
        platform-specific fallbacks.  See that routine's documentation for more
        details.)

        Resources are extracted to subdirectories of this path based upon
        information given by the ``IResourceProvider``.  You may set this to a
        temporary directory, but then you must call ``cleanup_resources()`` to
        delete the extracted files when done.  There is no guarantee that
        ``cleanup_resources()`` will be able to remove all extracted files.

        (Note: you may not change the extraction path for a given resource
        manager once resources have been extracted, unless you first call
        ``cleanup_resources()``.)
        """
        if self.cached_files:
            raise ValueError(
                "Can't change extraction path, files already extracted"
            )

        self.extraction_path = path

    def cleanup_resources(self, force=False):
        """
        Delete all extracted resource files and directories, returning a list
        of the file and directory names that could not be successfully removed.
        This function does not have any concurrency protection, so it should
        generally only be called when the extraction path is a temporary
        directory exclusive to a single process.  This method is not
        automatically called; you must call it explicitly or register it as an
        ``atexit`` function if you wish to ensure cleanup of a temporary
        directory used for extractions.
        """
        # XXX

def get_default_cache():
    """Determine the default cache location

    This returns the ``PYTHON_EGG_CACHE`` environment variable, if set.
    Otherwise, on Windows, it returns a "Python-Eggs" subdirectory of the
    "Application Data" directory.  On all other systems, it's "~/.python-eggs".
    """
    try:
        return os.environ['PYTHON_EGG_CACHE']
    except KeyError:
        pass

    if os.name!='nt':
        return os.path.expanduser('~/.python-eggs')

    app_data = 'Application Data'   # XXX this may be locale-specific!
    app_homes = [
        (('APPDATA',), None),       # best option, should be locale-safe
        (('USERPROFILE',), app_data),
        (('HOMEDRIVE','HOMEPATH'), app_data),
        (('HOMEPATH',), app_data),
        (('HOME',), None),
        (('WINDIR',), app_data),    # 95/98/ME
    ]

    for keys, subdir in app_homes:
        dirname = ''
        for key in keys:
            if key in os.environ:
                dirname = os.path.join(dirname, os.environ[key])
            else:
                break
        else:
            if subdir:
                dirname = os.path.join(dirname,subdir)
            return os.path.join(dirname, 'Python-Eggs')
    else:
        raise RuntimeError(
            "Please set the PYTHON_EGG_CACHE enviroment variable"
        )

def safe_name(name):
    """Convert an arbitrary string to a standard distribution name

    Any runs of non-alphanumeric/. characters are replaced with a single '-'.
    """
    return re.sub('[^A-Za-z0-9.]+', '-', name)


def safe_version(version):
    """Convert an arbitrary string to a standard version string

    Spaces become dots, and all other non-alphanumeric characters become
    dashes, with runs of multiple dashes condensed to a single dash.
    """
    version = version.replace(' ','.')
    return re.sub('[^A-Za-z0-9.]+', '-', version)


def safe_extra(extra):
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub('[^A-Za-z0-9.]+', '_', extra).lower()


def to_filename(name):
    """Convert a project or version name to its filename-escaped form

    Any '-' characters are currently replaced with '_'.
    """
    return name.replace('-','_')


class MarkerEvaluation(object):
    values = {
        'os_name': lambda: os.name,
        'sys_platform': lambda: sys.platform,
        'python_full_version': lambda: sys.version.split()[0],
        'python_version': lambda:'%s.%s' % (sys.version_info[0], sys.version_info[1]),
        'platform_version': platform.version,
        'platform_machine': platform.machine,
        'python_implementation': platform.python_implementation,
    }

    @classmethod
    def is_invalid_marker(cls, text):
        """
        Validate text as a PEP 426 environment marker; return an exception
        if invalid or False otherwise.
        """
        try:
            cls.evaluate_marker(text)
        except SyntaxError:
            return cls.normalize_exception(sys.exc_info()[1])
        return False

    @staticmethod
    def normalize_exception(exc):
        """
        Given a SyntaxError from a marker evaluation, normalize the error message:
         - Remove indications of filename and line number.
         - Replace platform-specific error messages with standard error messages.
        """
        subs = {
            'unexpected EOF while parsing': 'invalid syntax',
            'parenthesis is never closed': 'invalid syntax',
        }
        exc.filename = None
        exc.lineno = None
        exc.msg = subs.get(exc.msg, exc.msg)
        return exc

    @classmethod
    def and_test(cls, nodelist):
        # MUST NOT short-circuit evaluation, or invalid syntax can be skipped!
        return functools.reduce(operator.and_, [cls.interpret(nodelist[i]) for i in range(1,len(nodelist),2)])

    @classmethod
    def test(cls, nodelist):
        # MUST NOT short-circuit evaluation, or invalid syntax can be skipped!
        return functools.reduce(operator.or_, [cls.interpret(nodelist[i]) for i in range(1,len(nodelist),2)])

    @classmethod
    def atom(cls, nodelist):
        t = nodelist[1][0]
        if t == token.LPAR:
            if nodelist[2][0] == token.RPAR:
                raise SyntaxError("Empty parentheses")
            return cls.interpret(nodelist[2])
        raise SyntaxError("Language feature not supported in environment markers")

    @classmethod
    def comparison(cls, nodelist):
        if len(nodelist)>4:
            raise SyntaxError("Chained comparison not allowed in environment markers")
        comp = nodelist[2][1]
        cop = comp[1]
        if comp[0] == token.NAME:
            if len(nodelist[2]) == 3:
                if cop == 'not':
                    cop = 'not in'
                else:
                    cop = 'is not'
        try:
            cop = cls.get_op(cop)
        except KeyError:
            raise SyntaxError(repr(cop)+" operator not allowed in environment markers")
        return cop(cls.evaluate(nodelist[1]), cls.evaluate(nodelist[3]))

    @classmethod
    def get_op(cls, op):
        ops = {
            symbol.test: cls.test,
            symbol.and_test: cls.and_test,
            symbol.atom: cls.atom,
            symbol.comparison: cls.comparison,
            'not in': lambda x, y: x not in y,
            'in': lambda x, y: x in y,
            '==': operator.eq,
            '!=': operator.ne,
        }
        if hasattr(symbol, 'or_test'):
            ops[symbol.or_test] = cls.test
        return ops[op]

    @classmethod
    def evaluate_marker(cls, text, extra=None):
        """
        Evaluate a PEP 426 environment marker on CPython 2.4+.
        Return a boolean indicating the marker result in this environment.
        Raise SyntaxError if marker is invalid.

        This implementation uses the 'parser' module, which is not implemented on
        Jython and has been superseded by the 'ast' module in Python 2.6 and
        later.
        """
        return cls.interpret(parser.expr(text).totuple(1)[1])

    @classmethod
    def _markerlib_evaluate(cls, text):
        """
        Evaluate a PEP 426 environment marker using markerlib.
        Return a boolean indicating the marker result in this environment.
        Raise SyntaxError if marker is invalid.
        """
        import _markerlib
        # markerlib implements Metadata 1.2 (PEP 345) environment markers.
        # Translate the variables to Metadata 2.0 (PEP 426).
        env = _markerlib.default_environment()
        for key in env.keys():
            new_key = key.replace('.', '_')
            env[new_key] = env.pop(key)
        try:
            result = _markerlib.interpret(text, env)
        except NameError:
            e = sys.exc_info()[1]
            raise SyntaxError(e.args[0])
        return result

    if 'parser' not in globals():
        # Fall back to less-complete _markerlib implementation if 'parser' module
        # is not available.
        evaluate_marker = _markerlib_evaluate

    @classmethod
    def interpret(cls, nodelist):
        while len(nodelist)==2: nodelist = nodelist[1]
        try:
            op = cls.get_op(nodelist[0])
        except KeyError:
            raise SyntaxError("Comparison or logical expression expected")
        return op(nodelist)

    @classmethod
    def evaluate(cls, nodelist):
        while len(nodelist)==2: nodelist = nodelist[1]
        kind = nodelist[0]
        name = nodelist[1]
        if kind==token.NAME:
            try:
                op = cls.values[name]
            except KeyError:
                raise SyntaxError("Unknown name %r" % name)
            return op()
        if kind==token.STRING:
            s = nodelist[1]
            if s[:1] not in "'\"" or s.startswith('"""') or s.startswith("'''") \
                    or '\\' in s:
                raise SyntaxError(
                    "Only plain strings allowed in environment markers")
            return s[1:-1]
        raise SyntaxError("Language feature not supported in environment markers")

invalid_marker = MarkerEvaluation.is_invalid_marker
evaluate_marker = MarkerEvaluation.evaluate_marker

class NullProvider:
    """Try to implement resources and metadata for arbitrary PEP 302 loaders"""

    egg_name = None
    egg_info = None
    loader = None

    def __init__(self, module):
        self.loader = getattr(module, '__loader__', None)
        self.module_path = os.path.dirname(getattr(module, '__file__', ''))

    def get_resource_filename(self, manager, resource_name):
        return self._fn(self.module_path, resource_name)

    def get_resource_stream(self, manager, resource_name):
        return BytesIO(self.get_resource_string(manager, resource_name))

    def get_resource_string(self, manager, resource_name):
        return self._get(self._fn(self.module_path, resource_name))

    def has_resource(self, resource_name):
        return self._has(self._fn(self.module_path, resource_name))

    def has_metadata(self, name):
        return self.egg_info and self._has(self._fn(self.egg_info,name))

    if sys.version_info <= (3,):
        def get_metadata(self, name):
            if not self.egg_info:
                return ""
            return self._get(self._fn(self.egg_info,name))
    else:
        def get_metadata(self, name):
            if not self.egg_info:
                return ""
            return self._get(self._fn(self.egg_info,name)).decode("utf-8")

    def get_metadata_lines(self, name):
        return yield_lines(self.get_metadata(name))

    def resource_isdir(self,resource_name):
        return self._isdir(self._fn(self.module_path, resource_name))

    def metadata_isdir(self,name):
        return self.egg_info and self._isdir(self._fn(self.egg_info,name))

    def resource_listdir(self,resource_name):
        return self._listdir(self._fn(self.module_path,resource_name))

    def metadata_listdir(self,name):
        if self.egg_info:
            return self._listdir(self._fn(self.egg_info,name))
        return []

    def run_script(self,script_name,namespace):
        script = 'scripts/'+script_name
        if not self.has_metadata(script):
            raise ResolutionError("No script named %r" % script_name)
        script_text = self.get_metadata(script).replace('\r\n','\n')
        script_text = script_text.replace('\r','\n')
        script_filename = self._fn(self.egg_info,script)
        namespace['__file__'] = script_filename
        if os.path.exists(script_filename):
            execfile(script_filename, namespace, namespace)
        else:
            from linecache import cache
            cache[script_filename] = (
                len(script_text), 0, script_text.split('\n'), script_filename
            )
            script_code = compile(script_text,script_filename,'exec')
            exec(script_code, namespace, namespace)

    def _has(self, path):
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _isdir(self, path):
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _listdir(self, path):
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _fn(self, base, resource_name):
        if resource_name:
            return os.path.join(base, *resource_name.split('/'))
        return base

    def _get(self, path):
        if hasattr(self.loader, 'get_data'):
            return self.loader.get_data(path)
        raise NotImplementedError(
            "Can't perform this operation for loaders without 'get_data()'"
        )

register_loader_type(object, NullProvider)


class EggProvider(NullProvider):
    """Provider based on a virtual filesystem"""

    def __init__(self,module):
        NullProvider.__init__(self,module)
        self._setup_prefix()

    def _setup_prefix(self):
        # we assume here that our metadata may be nested inside a "basket"
        # of multiple eggs; that's why we use module_path instead of .archive
        path = self.module_path
        old = None
        while path!=old:
            if path.lower().endswith('.egg'):
                self.egg_name = os.path.basename(path)
                self.egg_info = os.path.join(path, 'EGG-INFO')
                self.egg_root = path
                break
            old = path
            path, base = os.path.split(path)

class DefaultProvider(EggProvider):
    """Provides access to package resources in the filesystem"""

    def _has(self, path):
        return os.path.exists(path)

    def _isdir(self,path):
        return os.path.isdir(path)

    def _listdir(self,path):
        return os.listdir(path)

    def get_resource_stream(self, manager, resource_name):
        return open(self._fn(self.module_path, resource_name), 'rb')

    def _get(self, path):
        stream = open(path, 'rb')
        try:
            return stream.read()
        finally:
            stream.close()

register_loader_type(type(None), DefaultProvider)

if importlib_bootstrap is not None:
    register_loader_type(importlib_bootstrap.SourceFileLoader, DefaultProvider)


class EmptyProvider(NullProvider):
    """Provider that returns nothing for all requests"""

    _isdir = _has = lambda self,path: False
    _get = lambda self,path: ''
    _listdir = lambda self,path: []
    module_path = None

    def __init__(self):
        pass

empty_provider = EmptyProvider()


def build_zipmanifest(path):
    """
    This builds a similar dictionary to the zipimport directory
    caches.  However instead of tuples, ZipInfo objects are stored.

    The translation of the tuple is as follows:
      * [0] - zipinfo.filename on stock pythons this needs "/" --> os.sep
              on pypy it is the same (one reason why distribute did work
              in some cases on pypy and win32).
      * [1] - zipinfo.compress_type
      * [2] - zipinfo.compress_size
      * [3] - zipinfo.file_size
      * [4] - len(utf-8 encoding of filename) if zipinfo & 0x800
              len(ascii encoding of filename) otherwise
      * [5] - (zipinfo.date_time[0] - 1980) << 9 |
               zipinfo.date_time[1] << 5 | zipinfo.date_time[2]
      * [6] - (zipinfo.date_time[3] - 1980) << 11 |
               zipinfo.date_time[4] << 5 | (zipinfo.date_time[5] // 2)
      * [7] - zipinfo.CRC
    """
    zipinfo = dict()
    zfile = zipfile.ZipFile(path)
    #Got ZipFile has not __exit__ on python 3.1
    try:
        for zitem in zfile.namelist():
            zpath = zitem.replace('/', os.sep)
            zipinfo[zpath] = zfile.getinfo(zitem)
            assert zipinfo[zpath] is not None
    finally:
        zfile.close()
    return zipinfo


class ZipProvider(EggProvider):
    """Resource support for zips and eggs"""

    eagers = None

    def __init__(self, module):
        EggProvider.__init__(self,module)
        self.zipinfo = build_zipmanifest(self.loader.archive)
        self.zip_pre = self.loader.archive+os.sep

    def _zipinfo_name(self, fspath):
        # Convert a virtual filename (full path to file) into a zipfile subpath
        # usable with the zipimport directory cache for our target archive
        if fspath.startswith(self.zip_pre):
            return fspath[len(self.zip_pre):]
        raise AssertionError(
            "%s is not a subpath of %s" % (fspath,self.zip_pre)
        )

    def _parts(self,zip_path):
        # Convert a zipfile subpath into an egg-relative path part list
        fspath = self.zip_pre+zip_path  # pseudo-fs path
        if fspath.startswith(self.egg_root+os.sep):
            return fspath[len(self.egg_root)+1:].split(os.sep)
        raise AssertionError(
            "%s is not a subpath of %s" % (fspath,self.egg_root)
        )

    def get_resource_filename(self, manager, resource_name):
        if not self.egg_name:
            raise NotImplementedError(
                "resource_filename() only supported for .egg, not .zip"
            )
        # no need to lock for extraction, since we use temp names
        zip_path = self._resource_to_zip(resource_name)
        eagers = self._get_eager_resources()
        if '/'.join(self._parts(zip_path)) in eagers:
            for name in eagers:
                self._extract_resource(manager, self._eager_to_zip(name))
        return self._extract_resource(manager, zip_path)

    @staticmethod
    def _get_date_and_size(zip_stat):
        size = zip_stat.file_size
        date_time = zip_stat.date_time + (0, 0, -1)  # ymdhms+wday, yday, dst
        #1980 offset already done
        timestamp = time.mktime(date_time)
        return timestamp, size

    def _extract_resource(self, manager, zip_path):

        if zip_path in self._index():
            for name in self._index()[zip_path]:
                last = self._extract_resource(
                    manager, os.path.join(zip_path, name)
                )
            return os.path.dirname(last)  # return the extracted directory name

        timestamp, size = self._get_date_and_size(self.zipinfo[zip_path])

        if not WRITE_SUPPORT:
            raise IOError('"os.rename" and "os.unlink" are not supported '
                          'on this platform')
        try:

            real_path = manager.get_cache_path(
                self.egg_name, self._parts(zip_path)
            )

            if self._is_current(real_path, zip_path):
                return real_path

            outf, tmpnam = _mkstemp(".$extract", dir=os.path.dirname(real_path))
            os.write(outf, self.loader.get_data(zip_path))
            os.close(outf)
            utime(tmpnam, (timestamp,timestamp))
            manager.postprocess(tmpnam, real_path)

            try:
                rename(tmpnam, real_path)

            except os.error:
                if os.path.isfile(real_path):
                    if self._is_current(real_path, zip_path):
                        # the file became current since it was checked above,
                        #  so proceed.
                        return real_path
                    elif os.name=='nt':     # Windows, del old file and retry
                        unlink(real_path)
                        rename(tmpnam, real_path)
                        return real_path
                raise

        except os.error:
            manager.extraction_error()  # report a user-friendly error

        return real_path

    def _is_current(self, file_path, zip_path):
        """
        Return True if the file_path is current for this zip_path
        """
        timestamp, size = self._get_date_and_size(self.zipinfo[zip_path])
        if not os.path.isfile(file_path):
            return False
        stat = os.stat(file_path)
        if stat.st_size!=size or stat.st_mtime!=timestamp:
            return False
        # check that the contents match
        zip_contents = self.loader.get_data(zip_path)
        f = open(file_path, 'rb')
        file_contents = f.read()
        f.close()
        return zip_contents == file_contents

    def _get_eager_resources(self):
        if self.eagers is None:
            eagers = []
            for name in ('native_libs.txt', 'eager_resources.txt'):
                if self.has_metadata(name):
                    eagers.extend(self.get_metadata_lines(name))
            self.eagers = eagers
        return self.eagers

    def _index(self):
        try:
            return self._dirindex
        except AttributeError:
            ind = {}
            for path in self.zipinfo:
                parts = path.split(os.sep)
                while parts:
                    parent = os.sep.join(parts[:-1])
                    if parent in ind:
                        ind[parent].append(parts[-1])
                        break
                    else:
                        ind[parent] = [parts.pop()]
            self._dirindex = ind
            return ind

    def _has(self, fspath):
        zip_path = self._zipinfo_name(fspath)
        return zip_path in self.zipinfo or zip_path in self._index()

    def _isdir(self,fspath):
        return self._zipinfo_name(fspath) in self._index()

    def _listdir(self,fspath):
        return list(self._index().get(self._zipinfo_name(fspath), ()))

    def _eager_to_zip(self,resource_name):
        return self._zipinfo_name(self._fn(self.egg_root,resource_name))

    def _resource_to_zip(self,resource_name):
        return self._zipinfo_name(self._fn(self.module_path,resource_name))

register_loader_type(zipimport.zipimporter, ZipProvider)


class FileMetadata(EmptyProvider):
    """Metadata handler for standalone PKG-INFO files

    Usage::

        metadata = FileMetadata("/path/to/PKG-INFO")

    This provider rejects all data and metadata requests except for PKG-INFO,
    which is treated as existing, and will be the contents of the file at
    the provided location.
    """

    def __init__(self,path):
        self.path = path

    def has_metadata(self,name):
        return name=='PKG-INFO'

    def get_metadata(self,name):
        if name=='PKG-INFO':
            f = open(self.path,'rU')
            metadata = f.read()
            f.close()
            return metadata
        raise KeyError("No metadata except PKG-INFO is available")

    def get_metadata_lines(self,name):
        return yield_lines(self.get_metadata(name))


class PathMetadata(DefaultProvider):
    """Metadata provider for egg directories

    Usage::

        # Development eggs:

        egg_info = "/path/to/PackageName.egg-info"
        base_dir = os.path.dirname(egg_info)
        metadata = PathMetadata(base_dir, egg_info)
        dist_name = os.path.splitext(os.path.basename(egg_info))[0]
        dist = Distribution(basedir,project_name=dist_name,metadata=metadata)

        # Unpacked egg directories:

        egg_path = "/path/to/PackageName-ver-pyver-etc.egg"
        metadata = PathMetadata(egg_path, os.path.join(egg_path,'EGG-INFO'))
        dist = Distribution.from_filename(egg_path, metadata=metadata)
    """

    def __init__(self, path, egg_info):
        self.module_path = path
        self.egg_info = egg_info


class EggMetadata(ZipProvider):
    """Metadata provider for .egg files"""

    def __init__(self, importer):
        """Create a metadata provider from a zipimporter"""

        self.zipinfo = build_zipmanifest(importer.archive)
        self.zip_pre = importer.archive+os.sep
        self.loader = importer
        if importer.prefix:
            self.module_path = os.path.join(importer.archive, importer.prefix)
        else:
            self.module_path = importer.archive
        self._setup_prefix()

_declare_state('dict', _distribution_finders = {})

def register_finder(importer_type, distribution_finder):
    """Register `distribution_finder` to find distributions in sys.path items

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `distribution_finder` is a callable that, passed a path
    item and the importer instance, yields ``Distribution`` instances found on
    that path item.  See ``pkg_resources.find_on_path`` for an example."""
    _distribution_finders[importer_type] = distribution_finder


def find_distributions(path_item, only=False):
    """Yield distributions accessible via `path_item`"""
    importer = get_importer(path_item)
    finder = _find_adapter(_distribution_finders, importer)
    return finder(importer, path_item, only)

def find_in_zip(importer, path_item, only=False):
    metadata = EggMetadata(importer)
    if metadata.has_metadata('PKG-INFO'):
        yield Distribution.from_filename(path_item, metadata=metadata)
    if only:
        return  # don't yield nested distros
    for subitem in metadata.resource_listdir('/'):
        if subitem.endswith('.egg'):
            subpath = os.path.join(path_item, subitem)
            for dist in find_in_zip(zipimport.zipimporter(subpath), subpath):
                yield dist

register_finder(zipimport.zipimporter, find_in_zip)

def find_nothing(importer, path_item, only=False):
    return ()
register_finder(object,find_nothing)

def find_on_path(importer, path_item, only=False):
    """Yield distributions accessible on a sys.path directory"""
    path_item = _normalize_cached(path_item)

    if os.path.isdir(path_item) and os.access(path_item, os.R_OK):
        if path_item.lower().endswith('.egg'):
            # unpacked egg
            yield Distribution.from_filename(
                path_item, metadata=PathMetadata(
                    path_item, os.path.join(path_item,'EGG-INFO')
                )
            )
        else:
            # scan for .egg and .egg-info in directory
            for entry in os.listdir(path_item):
                lower = entry.lower()
                if lower.endswith('.egg-info') or lower.endswith('.dist-info'):
                    fullpath = os.path.join(path_item, entry)
                    if os.path.isdir(fullpath):
                        # egg-info directory, allow getting metadata
                        metadata = PathMetadata(path_item, fullpath)
                    else:
                        metadata = FileMetadata(fullpath)
                    yield Distribution.from_location(
                        path_item,entry,metadata,precedence=DEVELOP_DIST
                    )
                elif not only and lower.endswith('.egg'):
                    for dist in find_distributions(os.path.join(path_item, entry)):
                        yield dist
                elif not only and lower.endswith('.egg-link'):
                    entry_file = open(os.path.join(path_item, entry))
                    try:
                        entry_lines = entry_file.readlines()
                    finally:
                        entry_file.close()
                    for line in entry_lines:
                        if not line.strip(): continue
                        for item in find_distributions(os.path.join(path_item,line.rstrip())):
                            yield item
                        break
register_finder(pkgutil.ImpImporter,find_on_path)

if importlib_bootstrap is not None:
    register_finder(importlib_bootstrap.FileFinder, find_on_path)

_declare_state('dict', _namespace_handlers={})
_declare_state('dict', _namespace_packages={})


def register_namespace_handler(importer_type, namespace_handler):
    """Register `namespace_handler` to declare namespace packages

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `namespace_handler` is a callable like this::

        def namespace_handler(importer,path_entry,moduleName,module):
            # return a path_entry to use for child packages

    Namespace handlers are only called if the importer object has already
    agreed that it can handle the relevant path item, and they should only
    return a subpath if the module __path__ does not already contain an
    equivalent subpath.  For an example namespace handler, see
    ``pkg_resources.file_ns_handler``.
    """
    _namespace_handlers[importer_type] = namespace_handler

def _handle_ns(packageName, path_item):
    """Ensure that named package includes a subpath of path_item (if needed)"""
    importer = get_importer(path_item)
    if importer is None:
        return None
    loader = importer.find_module(packageName)
    if loader is None:
        return None
    module = sys.modules.get(packageName)
    if module is None:
        module = sys.modules[packageName] = imp.new_module(packageName)
        module.__path__ = []
        _set_parent_ns(packageName)
    elif not hasattr(module,'__path__'):
        raise TypeError("Not a package:", packageName)
    handler = _find_adapter(_namespace_handlers, importer)
    subpath = handler(importer,path_item,packageName,module)
    if subpath is not None:
        path = module.__path__
        path.append(subpath)
        loader.load_module(packageName)
        module.__path__ = path
    return subpath

def declare_namespace(packageName):
    """Declare that package 'packageName' is a namespace package"""

    imp.acquire_lock()
    try:
        if packageName in _namespace_packages:
            return

        path, parent = sys.path, None
        if '.' in packageName:
            parent = '.'.join(packageName.split('.')[:-1])
            declare_namespace(parent)
            if parent not in _namespace_packages:
                __import__(parent)
            try:
                path = sys.modules[parent].__path__
            except AttributeError:
                raise TypeError("Not a package:", parent)

        # Track what packages are namespaces, so when new path items are added,
        # they can be updated
        _namespace_packages.setdefault(parent,[]).append(packageName)
        _namespace_packages.setdefault(packageName,[])

        for path_item in path:
            # Ensure all the parent's path items are reflected in the child,
            # if they apply
            _handle_ns(packageName, path_item)

    finally:
        imp.release_lock()

def fixup_namespace_packages(path_item, parent=None):
    """Ensure that previously-declared namespace packages include path_item"""
    imp.acquire_lock()
    try:
        for package in _namespace_packages.get(parent,()):
            subpath = _handle_ns(package, path_item)
            if subpath: fixup_namespace_packages(subpath,package)
    finally:
        imp.release_lock()

def file_ns_handler(importer, path_item, packageName, module):
    """Compute an ns-package subpath for a filesystem or zipfile importer"""

    subpath = os.path.join(path_item, packageName.split('.')[-1])
    normalized = _normalize_cached(subpath)
    for item in module.__path__:
        if _normalize_cached(item)==normalized:
            break
    else:
        # Only return the path if it's not already there
        return subpath

register_namespace_handler(pkgutil.ImpImporter,file_ns_handler)
register_namespace_handler(zipimport.zipimporter,file_ns_handler)

if importlib_bootstrap is not None:
    register_namespace_handler(importlib_bootstrap.FileFinder, file_ns_handler)


def null_ns_handler(importer, path_item, packageName, module):
    return None

register_namespace_handler(object,null_ns_handler)


def normalize_path(filename):
    """Normalize a file/dir name for comparison purposes"""
    return os.path.normcase(os.path.realpath(filename))

def _normalize_cached(filename,_cache={}):
    try:
        return _cache[filename]
    except KeyError:
        _cache[filename] = result = normalize_path(filename)
        return result

def _set_parent_ns(packageName):
    parts = packageName.split('.')
    name = parts.pop()
    if parts:
        parent = '.'.join(parts)
        setattr(sys.modules[parent], name, sys.modules[packageName])


def yield_lines(strs):
    """Yield non-empty/non-comment lines of a ``basestring`` or sequence"""
    if isinstance(strs,basestring):
        for s in strs.splitlines():
            s = s.strip()
            if s and not s.startswith('#'):     # skip blank lines/comments
                yield s
    else:
        for ss in strs:
            for s in yield_lines(ss):
                yield s

LINE_END = re.compile(r"\s*(#.*)?$").match         # whitespace and comment
CONTINUE = re.compile(r"\s*\\\s*(#.*)?$").match    # line continuation
DISTRO = re.compile(r"\s*((\w|[-.])+)").match    # Distribution or extra
VERSION = re.compile(r"\s*(<=?|>=?|==|!=)\s*((\w|[-.])+)").match  # ver. info
COMMA = re.compile(r"\s*,").match               # comma between items
OBRACKET = re.compile(r"\s*\[").match
CBRACKET = re.compile(r"\s*\]").match
MODULE = re.compile(r"\w+(\.\w+)*$").match
EGG_NAME = re.compile(
    r"(?P<name>[^-]+)"
    r"( -(?P<ver>[^-]+) (-py(?P<pyver>[^-]+) (-(?P<plat>.+))? )? )?",
    re.VERBOSE | re.IGNORECASE
).match

component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
replace = {'pre':'c', 'preview':'c','-':'final-','rc':'c','dev':'@'}.get

def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part,part)
        if not part or part=='.':
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)    # pad for numeric comparison
        else:
            yield '*'+part

    yield '*final'  # ensure that alpha/beta/candidate are before final

def parse_version(s):
    """Convert a version string to a chronologically-sortable key

    This is a rough cross between distutils' StrictVersion and LooseVersion;
    if you give it versions that would work with StrictVersion, then it behaves
    the same; otherwise it acts like a slightly-smarter LooseVersion. It is
    *possible* to create pathological version coding schemes that will fool
    this parser, but they should be very rare in practice.

    The returned value will be a tuple of strings.  Numeric portions of the
    version are padded to 8 digits so they will compare numerically, but
    without relying on how numbers compare relative to strings.  Dots are
    dropped, but dashes are retained.  Trailing zeros between alpha segments
    or dashes are suppressed, so that e.g. "2.4.0" is considered the same as
    "2.4". Alphanumeric parts are lower-cased.

    The algorithm assumes that strings like "-" and any alpha string that
    alphabetically follows "final"  represents a "patch level".  So, "2.4-1"
    is assumed to be a branch or patch of "2.4", and therefore "2.4.1" is
    considered newer than "2.4-1", which in turn is newer than "2.4".

    Strings like "a", "b", "c", "alpha", "beta", "candidate" and so on (that
    come before "final" alphabetically) are assumed to be pre-release versions,
    so that the version "2.4" is considered newer than "2.4a1".

    Finally, to handle miscellaneous cases, the strings "pre", "preview", and
    "rc" are treated as if they were "c", i.e. as though they were release
    candidates, and therefore are not as new as a version string that does not
    contain them, and "dev" is replaced with an '@' so that it sorts lower than
    than any other pre-release tag.
    """
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith('*'):
            if part<'*final':   # remove '-' before a prerelease tag
                while parts and parts[-1]=='*final-': parts.pop()
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1]=='00000000':
                parts.pop()
        parts.append(part)
    return tuple(parts)
class EntryPoint(object):
    """Object representing an advertised importable object"""

    def __init__(self, name, module_name, attrs=(), extras=(), dist=None):
        if not MODULE(module_name):
            raise ValueError("Invalid module name", module_name)
        self.name = name
        self.module_name = module_name
        self.attrs = tuple(attrs)
        self.extras = Requirement.parse(("x[%s]" % ','.join(extras))).extras
        self.dist = dist

    def __str__(self):
        s = "%s = %s" % (self.name, self.module_name)
        if self.attrs:
            s += ':' + '.'.join(self.attrs)
        if self.extras:
            s += ' [%s]' % ','.join(self.extras)
        return s

    def __repr__(self):
        return "EntryPoint.parse(%r)" % str(self)

    def load(self, require=True, env=None, installer=None):
        if require: self.require(env, installer)
        entry = __import__(self.module_name, globals(),globals(), ['__name__'])
        for attr in self.attrs:
            try:
                entry = getattr(entry,attr)
            except AttributeError:
                raise ImportError("%r has no %r attribute" % (entry,attr))
        return entry

    def require(self, env=None, installer=None):
        if self.extras and not self.dist:
            raise UnknownExtra("Can't require() without a distribution", self)
        list(map(working_set.add,
            working_set.resolve(self.dist.requires(self.extras),env,installer)))

    #@classmethod
    def parse(cls, src, dist=None):
        """Parse a single entry point from string `src`

        Entry point syntax follows the form::

            name = some.module:some.attr [extra1,extra2]

        The entry name and module name are required, but the ``:attrs`` and
        ``[extras]`` parts are optional
        """
        try:
            attrs = extras = ()
            name,value = src.split('=',1)
            if '[' in value:
                value,extras = value.split('[',1)
                req = Requirement.parse("x["+extras)
                if req.specs: raise ValueError
                extras = req.extras
            if ':' in value:
                value,attrs = value.split(':',1)
                if not MODULE(attrs.rstrip()):
                    raise ValueError
                attrs = attrs.rstrip().split('.')
        except ValueError:
            raise ValueError(
                "EntryPoint must be in 'name=module:attrs [extras]' format",
                src
            )
        else:
            return cls(name.strip(), value.strip(), attrs, extras, dist)

    parse = classmethod(parse)

    #@classmethod
    def parse_group(cls, group, lines, dist=None):
        """Parse an entry point group"""
        if not MODULE(group):
            raise ValueError("Invalid group name", group)
        this = {}
        for line in yield_lines(lines):
            ep = cls.parse(line, dist)
            if ep.name in this:
                raise ValueError("Duplicate entry point", group, ep.name)
            this[ep.name]=ep
        return this

    parse_group = classmethod(parse_group)

    #@classmethod
    def parse_map(cls, data, dist=None):
        """Parse a map of entry point groups"""
        if isinstance(data,dict):
            data = data.items()
        else:
            data = split_sections(data)
        maps = {}
        for group, lines in data:
            if group is None:
                if not lines:
                    continue
                raise ValueError("Entry points must be listed in groups")
            group = group.strip()
            if group in maps:
                raise ValueError("Duplicate group name", group)
            maps[group] = cls.parse_group(group, lines, dist)
        return maps

    parse_map = classmethod(parse_map)


def _remove_md5_fragment(location):
    if not location:
        return ''
    parsed = urlparse(location)
    if parsed[-1].startswith('md5='):
        return urlunparse(parsed[:-1] + ('',))
    return location


class Distribution(object):
    """Wrap an actual or potential sys.path entry w/metadata"""
    PKG_INFO = 'PKG-INFO'

    def __init__(self, location=None, metadata=None, project_name=None,
            version=None, py_version=PY_MAJOR, platform=None,
            precedence=EGG_DIST):
        self.project_name = safe_name(project_name or 'Unknown')
        if version is not None:
            self._version = safe_version(version)
        self.py_version = py_version
        self.platform = platform
        self.location = location
        self.precedence = precedence
        self._provider = metadata or empty_provider

    #@classmethod
    def from_location(cls,location,basename,metadata=None,**kw):
        project_name, version, py_version, platform = [None]*4
        basename, ext = os.path.splitext(basename)
        if ext.lower() in _distributionImpl:
            # .dist-info gets much metadata differently
            match = EGG_NAME(basename)
            if match:
                project_name, version, py_version, platform = match.group(
                    'name','ver','pyver','plat'
                )
            cls = _distributionImpl[ext.lower()]
        return cls(
            location, metadata, project_name=project_name, version=version,
            py_version=py_version, platform=platform, **kw
        )
    from_location = classmethod(from_location)

    hashcmp = property(
        lambda self: (
            getattr(self,'parsed_version',()),
            self.precedence,
            self.key,
            _remove_md5_fragment(self.location),
            self.py_version,
            self.platform
        )
    )
    def __hash__(self): return hash(self.hashcmp)
    def __lt__(self, other):
        return self.hashcmp < other.hashcmp
    def __le__(self, other):
        return self.hashcmp <= other.hashcmp
    def __gt__(self, other):
        return self.hashcmp > other.hashcmp
    def __ge__(self, other):
        return self.hashcmp >= other.hashcmp
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            # It's not a Distribution, so they are not equal
            return False
        return self.hashcmp == other.hashcmp
    def __ne__(self, other):
        return not self == other

    # These properties have to be lazy so that we don't have to load any
    # metadata until/unless it's actually needed.  (i.e., some distributions
    # may not know their name or version without loading PKG-INFO)

    #@property
    def key(self):
        try:
            return self._key
        except AttributeError:
            self._key = key = self.project_name.lower()
            return key
    key = property(key)

    #@property
    def parsed_version(self):
        try:
            return self._parsed_version
        except AttributeError:
            self._parsed_version = pv = parse_version(self.version)
            return pv

    parsed_version = property(parsed_version)

    #@property
    def version(self):
        try:
            return self._version
        except AttributeError:
            for line in self._get_metadata(self.PKG_INFO):
                if line.lower().startswith('version:'):
                    self._version = safe_version(line.split(':',1)[1].strip())
                    return self._version
            else:
                raise ValueError(
                    "Missing 'Version:' header and/or %s file" % self.PKG_INFO, self
                )
    version = property(version)

    #@property
    def _dep_map(self):
        try:
            return self.__dep_map
        except AttributeError:
            dm = self.__dep_map = {None: []}
            for name in 'requires.txt', 'depends.txt':
                for extra,reqs in split_sections(self._get_metadata(name)):
                    if extra:
                        if ':' in extra:
                            extra, marker = extra.split(':',1)
                            if invalid_marker(marker):
                                reqs=[] # XXX warn
                            elif not evaluate_marker(marker):
                                reqs=[]
                        extra = safe_extra(extra) or None
                    dm.setdefault(extra,[]).extend(parse_requirements(reqs))
            return dm
    _dep_map = property(_dep_map)

    def requires(self,extras=()):
        """List of Requirements needed for this distro if `extras` are used"""
        dm = self._dep_map
        deps = []
        deps.extend(dm.get(None,()))
        for ext in extras:
            try:
                deps.extend(dm[safe_extra(ext)])
            except KeyError:
                raise UnknownExtra(
                    "%s has no such extra feature %r" % (self, ext)
                )
        return deps

    def _get_metadata(self,name):
        if self.has_metadata(name):
            for line in self.get_metadata_lines(name):
                yield line

    def activate(self,path=None):
        """Ensure distribution is importable on `path` (default=sys.path)"""
        if path is None: path = sys.path
        self.insert_on(path)
        if path is sys.path:
            fixup_namespace_packages(self.location)
            list(map(declare_namespace, self._get_metadata('namespace_packages.txt')))

    def egg_name(self):
        """Return what this distribution's standard .egg filename should be"""
        filename = "%s-%s-py%s" % (
            to_filename(self.project_name), to_filename(self.version),
            self.py_version or PY_MAJOR
        )

        if self.platform:
            filename += '-'+self.platform
        return filename

    def __repr__(self):
        if self.location:
            return "%s (%s)" % (self,self.location)
        else:
            return str(self)

    def __str__(self):
        try: version = getattr(self,'version',None)
        except ValueError: version = None
        version = version or "[unknown version]"
        return "%s %s" % (self.project_name,version)

    def __getattr__(self,attr):
        """Delegate all unrecognized public attributes to .metadata provider"""
        if attr.startswith('_'):
            raise AttributeError(attr)
        return getattr(self._provider, attr)

    #@classmethod
    def from_filename(cls,filename,metadata=None, **kw):
        return cls.from_location(
            _normalize_cached(filename), os.path.basename(filename), metadata,
            **kw
        )
    from_filename = classmethod(from_filename)

    def as_requirement(self):
        """Return a ``Requirement`` that matches this distribution exactly"""
        return Requirement.parse('%s==%s' % (self.project_name, self.version))

    def load_entry_point(self, group, name):
        """Return the `name` entry point of `group` or raise ImportError"""
        ep = self.get_entry_info(group,name)
        if ep is None:
            raise ImportError("Entry point %r not found" % ((group,name),))
        return ep.load()

    def get_entry_map(self, group=None):
        """Return the entry point map for `group`, or the full entry map"""
        try:
            ep_map = self._ep_map
        except AttributeError:
            ep_map = self._ep_map = EntryPoint.parse_map(
                self._get_metadata('entry_points.txt'), self
            )
        if group is not None:
            return ep_map.get(group,{})
        return ep_map

    def get_entry_info(self, group, name):
        """Return the EntryPoint object for `group`+`name`, or ``None``"""
        return self.get_entry_map(group).get(name)

    def insert_on(self, path, loc = None):
        """Insert self.location in path before its nearest parent directory"""

        loc = loc or self.location
        if not loc:
            return

        nloc = _normalize_cached(loc)
        bdir = os.path.dirname(nloc)
        npath= [(p and _normalize_cached(p) or p) for p in path]

        for p, item in enumerate(npath):
            if item==nloc:
                break
            elif item==bdir and self.precedence==EGG_DIST:
                # if it's an .egg, give it precedence over its directory
                if path is sys.path:
                    self.check_version_conflict()
                path.insert(p, loc)
                npath.insert(p, nloc)
                break
        else:
            if path is sys.path:
                self.check_version_conflict()
            path.append(loc)
            return

        # p is the spot where we found or inserted loc; now remove duplicates
        while 1:
            try:
                np = npath.index(nloc, p+1)
            except ValueError:
                break
            else:
                del npath[np], path[np]
                p = np  # ha!

        return

    def check_version_conflict(self):
        if self.key=='setuptools':
            return      # ignore the inevitable setuptools self-conflicts  :(

        nsp = dict.fromkeys(self._get_metadata('namespace_packages.txt'))
        loc = normalize_path(self.location)
        for modname in self._get_metadata('top_level.txt'):
            if (modname not in sys.modules or modname in nsp
                    or modname in _namespace_packages):
                continue
            if modname in ('pkg_resources', 'setuptools', 'site'):
                continue
            fn = getattr(sys.modules[modname], '__file__', None)
            if fn and (normalize_path(fn).startswith(loc) or
                       fn.startswith(self.location)):
                continue
            issue_warning(
                "Module %s was already imported from %s, but %s is being added"
                " to sys.path" % (modname, fn, self.location),
            )

    def has_version(self):
        try:
            self.version
        except ValueError:
            issue_warning("Unbuilt egg for "+repr(self))
            return False
        return True

    def clone(self,**kw):
        """Copy this distribution, substituting in any changed keyword args"""
        for attr in (
            'project_name', 'version', 'py_version', 'platform', 'location',
            'precedence'
        ):
            kw.setdefault(attr, getattr(self,attr,None))
        kw.setdefault('metadata', self._provider)
        return self.__class__(**kw)

    #@property
    def extras(self):
        return [dep for dep in self._dep_map if dep]
    extras = property(extras)


class DistInfoDistribution(Distribution):
    """Wrap an actual or potential sys.path entry w/metadata, .dist-info style"""
    PKG_INFO = 'METADATA'
    EQEQ = re.compile(r"([\(,])\s*(\d.*?)\s*([,\)])")

    @property
    def _parsed_pkg_info(self):
        """Parse and cache metadata"""
        try:
            return self._pkg_info
        except AttributeError:
            from email.parser import Parser
            self._pkg_info = Parser().parsestr(self.get_metadata(self.PKG_INFO))
            return self._pkg_info

    @property
    def _dep_map(self):
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._compute_dependencies()
            return self.__dep_map

    def _preparse_requirement(self, requires_dist):
        """Convert 'Foobar (1); baz' to ('Foobar ==1', 'baz')
        Split environment marker, add == prefix to version specifiers as
        necessary, and remove parenthesis.
        """
        parts = requires_dist.split(';', 1) + ['']
        distvers = parts[0].strip()
        mark = parts[1].strip()
        distvers = re.sub(self.EQEQ, r"\1==\2\3", distvers)
        distvers = distvers.replace('(', '').replace(')', '')
        return (distvers, mark)

    def _compute_dependencies(self):
        """Recompute this distribution's dependencies."""
        from _markerlib import compile as compile_marker
        dm = self.__dep_map = {None: []}

        reqs = []
        # Including any condition expressions
        for req in self._parsed_pkg_info.get_all('Requires-Dist') or []:
            distvers, mark = self._preparse_requirement(req)
            parsed = next(parse_requirements(distvers))
            parsed.marker_fn = compile_marker(mark)
            reqs.append(parsed)

        def reqs_for_extra(extra):
            for req in reqs:
                if req.marker_fn(override={'extra':extra}):
                    yield req

        common = frozenset(reqs_for_extra(None))
        dm[None].extend(common)

        for extra in self._parsed_pkg_info.get_all('Provides-Extra') or []:
            extra = safe_extra(extra.strip())
            dm[extra] = list(frozenset(reqs_for_extra(extra)) - common)

        return dm


_distributionImpl = {
    '.egg': Distribution,
    '.egg-info': Distribution,
    '.dist-info': DistInfoDistribution,
    }


def issue_warning(*args,**kw):
    level = 1
    g = globals()
    try:
        # find the first stack frame that is *not* code in
        # the pkg_resources module, to use for the warning
        while sys._getframe(level).f_globals is g:
            level += 1
    except ValueError:
        pass
    from warnings import warn
    warn(stacklevel = level+1, *args, **kw)


def parse_requirements(strs):
    """Yield ``Requirement`` objects for each specification in `strs`

    `strs` must be an instance of ``basestring``, or a (possibly-nested)
    iterable thereof.
    """
    # create a steppable iterator, so we can handle \-continuations
    lines = iter(yield_lines(strs))

    def scan_list(ITEM,TERMINATOR,line,p,groups,item_name):

        items = []

        while not TERMINATOR(line,p):
            if CONTINUE(line,p):
                try:
                    line = next(lines)
                    p = 0
                except StopIteration:
                    raise ValueError(
                        "\\ must not appear on the last nonblank line"
                    )

            match = ITEM(line,p)
            if not match:
                raise ValueError("Expected "+item_name+" in",line,"at",line[p:])

            items.append(match.group(*groups))
            p = match.end()

            match = COMMA(line,p)
            if match:
                p = match.end() # skip the comma
            elif not TERMINATOR(line,p):
                raise ValueError(
                    "Expected ',' or end-of-list in",line,"at",line[p:]
                )

        match = TERMINATOR(line,p)
        if match: p = match.end()   # skip the terminator, if any
        return line, p, items

    for line in lines:
        match = DISTRO(line)
        if not match:
            raise ValueError("Missing distribution spec", line)
        project_name = match.group(1)
        p = match.end()
        extras = []

        match = OBRACKET(line,p)
        if match:
            p = match.end()
            line, p, extras = scan_list(
                DISTRO, CBRACKET, line, p, (1,), "'extra' name"
            )

        line, p, specs = scan_list(VERSION,LINE_END,line,p,(1,2),"version spec")
        specs = [(op,safe_version(val)) for op,val in specs]
        yield Requirement(project_name, specs, extras)


def _sort_dists(dists):
    tmp = [(dist.hashcmp,dist) for dist in dists]
    tmp.sort()
    dists[::-1] = [d for hc,d in tmp]


class Requirement:
    def __init__(self, project_name, specs, extras):
        """DO NOT CALL THIS UNDOCUMENTED METHOD; use Requirement.parse()!"""
        self.unsafe_name, project_name = project_name, safe_name(project_name)
        self.project_name, self.key = project_name, project_name.lower()
        index = [(parse_version(v),state_machine[op],op,v) for op,v in specs]
        index.sort()
        self.specs = [(op,ver) for parsed,trans,op,ver in index]
        self.index, self.extras = index, tuple(map(safe_extra,extras))
        self.hashCmp = (
            self.key, tuple([(op,parsed) for parsed,trans,op,ver in index]),
            frozenset(self.extras)
        )
        self.__hash = hash(self.hashCmp)

    def __str__(self):
        specs = ','.join([''.join(s) for s in self.specs])
        extras = ','.join(self.extras)
        if extras: extras = '[%s]' % extras
        return '%s%s%s' % (self.project_name, extras, specs)

    def __eq__(self,other):
        return isinstance(other,Requirement) and self.hashCmp==other.hashCmp

    def __contains__(self,item):
        if isinstance(item,Distribution):
            if item.key != self.key: return False
            if self.index: item = item.parsed_version  # only get if we need it
        elif isinstance(item,basestring):
            item = parse_version(item)
        last = None
        compare = lambda a, b: (a > b) - (a < b) # -1, 0, 1
        for parsed,trans,op,ver in self.index:
            action = trans[compare(item,parsed)] # Indexing: 0, 1, -1
            if action=='F':
                return False
            elif action=='T':
                return True
            elif action=='+':
                last = True
            elif action=='-' or last is None:   last = False
        if last is None: last = True    # no rules encountered
        return last

    def __hash__(self):
        return self.__hash

    def __repr__(self): return "Requirement.parse(%r)" % str(self)

    #@staticmethod
    def parse(s):
        reqs = list(parse_requirements(s))
        if reqs:
            if len(reqs)==1:
                return reqs[0]
            raise ValueError("Expected only one requirement", s)
        raise ValueError("No requirements found", s)

    parse = staticmethod(parse)

state_machine = {
    #       =><
    '<': '--T',
    '<=': 'T-T',
    '>': 'F+F',
    '>=': 'T+F',
    '==': 'T..',
    '!=': 'F++',
}


def _get_mro(cls):
    """Get an mro for a type or classic class"""
    if not isinstance(cls,type):
        class cls(cls,object): pass
        return cls.__mro__[1:]
    return cls.__mro__

def _find_adapter(registry, ob):
    """Return an adapter factory for `ob` from `registry`"""
    for t in _get_mro(getattr(ob, '__class__', type(ob))):
        if t in registry:
            return registry[t]


def ensure_directory(path):
    """Ensure that the parent directory of `path` exists"""
    dirname = os.path.dirname(path)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)

def split_sections(s):
    """Split a string or iterable thereof into (section,content) pairs

    Each ``section`` is a stripped version of the section header ("[section]")
    and each ``content`` is a list of stripped lines excluding blank lines and
    comment-only lines.  If there are any such lines before the first section
    header, they're returned in a first ``section`` of ``None``.
    """
    section = None
    content = []
    for line in yield_lines(s):
        if line.startswith("["):
            if line.endswith("]"):
                if section or content:
                    yield section, content
                section = line[1:-1].strip()
                content = []
            else:
                raise ValueError("Invalid section heading", line)
        else:
            content.append(line)

    # wrap up last segment
    yield section, content

def _mkstemp(*args,**kw):
    from tempfile import mkstemp
    old_open = os.open
    try:
        os.open = os_open   # temporarily bypass sandboxing
        return mkstemp(*args,**kw)
    finally:
        os.open = old_open  # and then put it back


# Set up global resource manager (deliberately not state-saved)
_manager = ResourceManager()
def _initialize(g):
    for name in dir(_manager):
        if not name.startswith('_'):
            g[name] = getattr(_manager, name)
_initialize(globals())

# Prepare the master working set and make the ``require()`` API available
_declare_state('object', working_set = WorkingSet())
try:
    # Does the main program list any requirements?
    from __main__ import __requires__
except ImportError:
    pass # No: just use the default working set based on sys.path
else:
    # Yes: ensure the requirements are met, by prefixing sys.path if necessary
    try:
        working_set.require(__requires__)
    except VersionConflict:     # try it without defaults already on sys.path
        working_set = WorkingSet([])    # by starting with an empty path
        for dist in working_set.resolve(
            parse_requirements(__requires__), Environment()
        ):
            working_set.add(dist)
        for entry in sys.path:  # add any missing entries from sys.path
            if entry not in working_set.entries:
                working_set.add_entry(entry)
        sys.path[:] = working_set.entries   # then copy back to sys.path

require = working_set.require
iter_entry_points = working_set.iter_entry_points
add_activation_listener = working_set.subscribe
run_script = working_set.run_script
run_main = run_script   # backward compatibility
# Activate all distributions already on sys.path, and ensure that
# all distributions added to the working set in the future (e.g. by
# calling ``require()``) will get activated as well.
add_activation_listener(lambda dist: dist.activate())
working_set.entries=[]
list(map(working_set.add_entry,sys.path)) # match order

########NEW FILE########
__FILENAME__ = iso_8859_1
# -*- coding: iso-8859-1 -*-

########NEW FILE########
__FILENAME__ = E10
#: E101 W191
for a in 'abc':
    for b in 'xyz':
        print a  # indented with 8 spaces
	print b  # indented with 1 tab
#: E101 E122 W191 W191
if True:
	pass

change_2_log = \
"""Change 2 by slamb@testclient on 2006/04/13 21:46:23

	creation
"""

p4change = {
    2: change_2_log,
}


class TestP4Poller(unittest.TestCase):
    def setUp(self):
        self.setUpGetProcessOutput()
        return self.setUpChangeSource()

    def tearDown(self):
        pass

#
#: E101 W191 W191
if True:
	foo(1,
	    2)
#: E101 E101 W191 W191
def test_keys(self):
    """areas.json - All regions are accounted for."""
    expected = set([
	u'Norrbotten',
	u'V\xe4sterbotten',
    ])
#:

########NEW FILE########
__FILENAME__ = E11
#: E111
if x > 2:
  print x
#: E111
if True:
     print
#: E112
if False:
print
#: E113
print
    print
#: E111 E113
mimetype = 'application/x-directory'
     # 'httpd/unix-directory'
create_date = False

########NEW FILE########
__FILENAME__ = E12
#: E121
print "E121", (
  "dent")
#: E122
print "E122", (
"dent")
#: E123
my_list = [
    1, 2, 3,
    4, 5, 6,
    ]
#: E124
print "E124", ("visual",
               "indent_two"
              )
#: E124
print "E124", ("visual",
               "indent_five"
)
#: E124
a = (123,
)
#: E129
if (row < 0 or self.moduleCount <= row or
    col < 0 or self.moduleCount <= col):
    raise Exception("%s,%s - %s" % (row, col, self.moduleCount))
#: E126
print "E126", (
            "dent")
#: E126
print "E126", (
        "dent")
#: E127
print "E127", ("over-",
                  "over-indent")
#: E128
print "E128", ("visual",
    "hanging")
#: E128
print "E128", ("under-",
              "under-indent")
#:


#: E126
my_list = [
    1, 2, 3,
    4, 5, 6,
     ]
#: E121
result = {
   'key1': 'value',
   'key2': 'value',
}
#: E126 E126
rv.update(dict.fromkeys((
    'qualif_nr', 'reasonComment_en', 'reasonComment_fr',
    'reasonComment_de', 'reasonComment_it'),
          '?'),
          "foo")
#: E126
abricot = 3 + \
          4 + \
          5 + 6
#: E131
print "hello", (

    "there",
     # "john",
    "dude")
#: E126
part = set_mimetype((
    a.get('mime_type', 'text')),
                       'default')
#:


#: E122
if True:
    result = some_function_that_takes_arguments(
        'a', 'b', 'c',
        'd', 'e', 'f',
)
#: E122
if some_very_very_very_long_variable_name or var \
or another_very_long_variable_name:
    raise Exception()
#: E122
if some_very_very_very_long_variable_name or var[0] \
or another_very_long_variable_name:
    raise Exception()
#: E122
if True:
    if some_very_very_very_long_variable_name or var \
    or another_very_long_variable_name:
        raise Exception()
#: E122
if True:
    if some_very_very_very_long_variable_name or var[0] \
    or another_very_long_variable_name:
        raise Exception()
#: E122
dictionary = [
    "is": {
    "nested": yes(),
    },
]
#: E122
setup('',
      scripts=[''],
      classifiers=[
      'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
      ])
#:


#: E123 W291
print "E123", (   
    "bad", "hanging", "close"
    )
#
#: E123 E123 E123
result = {
    'foo': [
        'bar', {
            'baz': 'frop',
            }
        ]
    }
#: E123
result = some_function_that_takes_arguments(
    'a', 'b', 'c',
    'd', 'e', 'f',
    )
#: E124
my_list = [1, 2, 3,
           4, 5, 6,
]
#: E124
my_list = [1, 2, 3,
           4, 5, 6,
                   ]
#: E124
result = some_function_that_takes_arguments('a', 'b', 'c',
                                            'd', 'e', 'f',
)
#: E124
fooff(aaaa,
      cca(
          vvv,
          dadd
      ), fff,
)
#: E124
fooff(aaaa,
      ccaaa(
          vvv,
          dadd
      ),
      fff,
)
#: E124
d = dict('foo',
         help="exclude files or directories which match these "
              "comma separated patterns (default: %s)" % DEFAULT_EXCLUDE
              )
#: E124 E128 E128
if line_removed:
    self.event(cr, uid,
        name="Removing the option for contract",
        description="contract line has been removed",
        )
#:


#: E125
if foo is None and bar is "frop" and \
    blah == 'yeah':
    blah = 'yeahnah'
#: E125
# Further indentation required as indentation is not distinguishable


def long_function_name(
    var_one, var_two, var_three,
    var_four):
    print(var_one)
#
#: E125


def qualify_by_address(
    self, cr, uid, ids, context=None,
    params_to_check=frozenset(QUALIF_BY_ADDRESS_PARAM)):
    """ This gets called by the web server """
#: E129
if (a == 2 or
    b == "abc def ghi"
    "jkl mno"):
    return True
#:


#: E126
my_list = [
    1, 2, 3,
    4, 5, 6,
        ]
#: E126
abris = 3 + \
        4 + \
        5 + 6
#: E126
fixed = re.sub(r'\t+', ' ', target[c::-1], 1)[::-1] + \
        target[c + 1:]
#: E126 E126
rv.update(dict.fromkeys((
            'qualif_nr', 'reasonComment_en', 'reasonComment_fr',
            'reasonComment_de', 'reasonComment_it'),
        '?'),
    "foo")
#: E126
eat_a_dict_a_day({
        "foo": "bar",
})
#: E126
if (
    x == (
            3
    ) or
        y == 4):
    pass
#: E126
if (
    x == (
        3
    ) or
    x == (
            3
    ) or
        y == 4):
    pass
#: E131
troublesome_hash = {
    "hash": "value",
    "long": "the quick brown fox jumps over the lazy dog before doing a "
        "somersault",
}
#:


#: E128
# Arguments on first line forbidden when not using vertical alignment
foo = long_function_name(var_one, var_two,
    var_three, var_four)
#
#: E128
print('l.%s\t%s\t%s\t%r' %
    (token[2][0], pos, tokenize.tok_name[token[0]], token[1]))
#: E128


def qualify_by_address(self, cr, uid, ids, context=None,
        params_to_check=frozenset(QUALIF_BY_ADDRESS_PARAM)):
    """ This gets called by the web server """
#:


#: E128
foo(1, 2, 3,
4, 5, 6)
#: E128
foo(1, 2, 3,
 4, 5, 6)
#: E128
foo(1, 2, 3,
  4, 5, 6)
#: E128
foo(1, 2, 3,
   4, 5, 6)
#: E127
foo(1, 2, 3,
     4, 5, 6)
#: E127
foo(1, 2, 3,
      4, 5, 6)
#: E127
foo(1, 2, 3,
       4, 5, 6)
#: E127
foo(1, 2, 3,
        4, 5, 6)
#: E127
foo(1, 2, 3,
         4, 5, 6)
#: E127
foo(1, 2, 3,
          4, 5, 6)
#: E127
foo(1, 2, 3,
           4, 5, 6)
#: E127
foo(1, 2, 3,
            4, 5, 6)
#: E127
foo(1, 2, 3,
             4, 5, 6)
#: E128 E128
if line_removed:
    self.event(cr, uid,
              name="Removing the option for contract",
              description="contract line has been removed",
               )
#: E124 E127 E127
if line_removed:
    self.event(cr, uid,
                name="Removing the option for contract",
                description="contract line has been removed",
                )
#: E127
rv.update(d=('a', 'b', 'c'),
             e=42)
#
#: E127
rv.update(d=('a' + 'b', 'c'),
          e=42, f=42
                 + 42)
#: E127
input1 = {'a': {'calc': 1 + 2}, 'b': 1
                          + 42}
#: E128
rv.update(d=('a' + 'b', 'c'),
          e=42, f=(42
                 + 42))
#: E123
if True:
    def example_issue254():
        return [node.copy(
            (
                replacement
                # First, look at all the node's current children.
                for child in node.children
                # Replace them.
                for replacement in replace(child)
                ),
            dict(name=token.undefined)
        )]
#: E125:2:5 E125:8:5
if ("""
    """):
    pass

for foo in """
    abc
    123
    """.strip().split():
    print(foo)
#: E122:6:5 E122:7:5 E122:8:1
print dedent(
    '''
        mkdir -p ./{build}/
        mv ./build/ ./{build}/%(revision)s/
    '''.format(
    build='build',
    # more stuff
)
)
#: E701:1:8 E122:2:1 E203:4:8 E128:5:1
if True:\
print(True)

print(a
, end=' ')
#:

########NEW FILE########
__FILENAME__ = E20
#: E201:1:6
spam( ham[1], {eggs: 2})
#: E201:1:10
spam(ham[ 1], {eggs: 2})
#: E201:1:15
spam(ham[1], { eggs: 2})
#: Okay
spam(ham[1], {eggs: 2})
#:


#: E202:1:23
spam(ham[1], {eggs: 2} )
#: E202:1:22
spam(ham[1], {eggs: 2 })
#: E202:1:11
spam(ham[1 ], {eggs: 2})
#: Okay
spam(ham[1], {eggs: 2})

result = func(
    arg1='some value',
    arg2='another value',
)

result = func(
    arg1='some value',
    arg2='another value'
)

result = [
    item for item in items
    if item > 5
]
#:


#: E203:1:10
if x == 4 :
    print x, y
    x, y = y, x
#: E203:2:15 E702:2:16
if x == 4:
    print x, y ; x, y = y, x
#: E203:3:13
if x == 4:
    print x, y
    x, y = y , x
#: Okay
if x == 4:
    print x, y
    x, y = y, x
a[b1, :] == a[b1, ...]
b = a[:, b1]
#:

########NEW FILE########
__FILENAME__ = E21
#: E211
spam (1)
#: E211 E211
dict ['key'] = list [index]
#: E211
dict['key'] ['subkey'] = list[index]
#: Okay
spam(1)
dict['key'] = list[index]


# This is not prohibited by PEP8, but avoid it.
class Foo (Bar, Baz):
    pass

########NEW FILE########
__FILENAME__ = E22
#: E221
a = 12 + 3
b = 4  + 5
#: E221 E221
x             = 1
y             = 2
long_variable = 3
#: E221 E221
x[0]          = 1
x[1]          = 2
long_variable = 3
#: E221 E221
x = f(x)          + 1
y = long_variable + 2
z = x[0]          + 3
#: E221:3:14
text = """
    bar
    foo %s"""  % rofl
#: Okay
x = 1
y = 2
long_variable = 3
#:


#: E222
a = a +  1
b = b + 10
#: E222 E222
x =            -1
y =            -2
long_variable = 3
#: E222 E222
x[0] =          1
x[1] =          2
long_variable = 3
#:


#: E223
foobart = 4
a	= 3  # aligned with tab
#:


#: E224
a +=	1
b += 1000
#:


#: E225
submitted +=1
#: E225
submitted+= 1
#: E225
c =-1
#: E225
x = x /2 - 1
#: E225
c = alpha -4
#: E225
c = alpha- 4
#: E225
z = x **y
#: E225
z = (x + 1) **y
#: E225
z = (x + 1)** y
#: E225
_1kB = _1MB >>10
#: E225
_1kB = _1MB>> 10
#: E225 E225
i=i+ 1
#: E225 E225
i=i +1
#: E225 E226
i=i+1
#: E225 E226
i =i+1
#: E225 E226
i= i+1
#: E225 E226
c = (a +b)*(a - b)
#: E225 E226
c = (a+ b)*(a - b)
#:

#: E226
z = 2**30
#: E226 E226
c = (a+b) * (a-b)
#: E226
norman = True+False
#: E226
x = x*2 - 1
#: E226
x = x/2 - 1
#: E226 E226
hypot2 = x*x + y*y
#: E226
c = (a + b)*(a - b)
#: E226
def squares(n):
    return (i**2 for i in range(n))
#: E227
_1kB = _1MB>>10
#: E227
_1MB = _1kB<<10
#: E227
a = b|c
#: E227
b = c&a
#: E227
c = b^a
#: E228
a = b%c
#: E228
msg = fmt%(errno, errmsg)
#: E228
msg = "Error %d occured"%errno
#:

#: Okay
i = i + 1
submitted += 1
x = x * 2 - 1
hypot2 = x * x + y * y
c = (a + b) * (a - b)
_1MB = 2 ** 20
foo(bar, key='word', *args, **kwargs)
baz(**kwargs)
negative = -1
spam(-1)
-negative
lambda *args, **kw: (args, kw)
lambda a, b=h[:], c=0: (a, b, c)
if not -5 < x < +5:
    print >>sys.stderr, "x is out of range."
print >> sys.stdout, "x is an integer."
z = 2 ** 30
x = x / 2 - 1

if alpha[:-i]:
    *a, b = (1, 2, 3)


def squares(n):
    return (i ** 2 for i in range(n))
#:

########NEW FILE########
__FILENAME__ = E23
#: E231
a = (1,2)
#: E231
a[b1,:]
#: E231
a = [{'a':''}]
#: Okay
a = (4,)
b = (5, )
c = {'text': text[5:]}

result = {
    'key1': 'value',
    'key2': 'value',
}

########NEW FILE########
__FILENAME__ = E24
#: E241
a = (1,  2)
#: Okay
b = (1, 20)
#: E242
a = (1,	2)  # tab before 2
#: Okay
b = (1, 20)  # space before 20
#: E241 E241 E241
# issue 135
more_spaces = [a,    b,
               ef,  +h,
               c,   -d]

########NEW FILE########
__FILENAME__ = E25
#: E251 E251
def foo(bar = False):
    '''Test function with an error in declaration'''
    pass
#: E251
foo(bar= True)
#: E251
foo(bar =True)
#: E251 E251
foo(bar = True)
#: E251
y = bar(root= "sdasd")
#: E251:2:29
parser.add_argument('--long-option',
                    default=
                    "/rather/long/filesystem/path/here/blah/blah/blah")
#: E251:1:45
parser.add_argument('--long-option', default
                    ="/rather/long/filesystem/path/here/blah/blah/blah")
#: Okay
foo(bar=(1 == 1))
foo(bar=(1 != 1))
foo(bar=(1 >= 1))
foo(bar=(1 <= 1))
(options, args) = parser.parse_args()
d[type(None)] = _deepcopy_atomic

########NEW FILE########
__FILENAME__ = E26
#: E261
pass # an inline comment
#: E262
x = x + 1  #Increment x
#: E262
x = x + 1  #  Increment x
#: E262
x = y + 1  #:  Increment x
#: E265
#Block comment
a = 1
#: E265
m = 42
#! This is important
mx = 42 - 42
#: Okay
#!/usr/bin/env python

pass  # an inline comment
x = x + 1   # Increment x
y = y + 1   #: Increment x

# Block comment
a = 1

# Block comment1

# Block comment2
aaa = 1


# example of docstring (not parsed)
def oof():
    """
    #foo not parsed
    """

########NEW FILE########
__FILENAME__ = E27
#: Okay
True and False
#: E271
True and  False
#: E272
True  and False
#: E271
if   1:
#: E273
True and		False
#: E273 E274
True		and	False
#: E271
a and  b
#: E271
1 and  b
#: E271
a and  2
#: E271 E272
1  and  b
#: E271 E272
a  and  2
#: E272
this  and False
#: E273
a and	b
#: E274
a		and b
#: E273 E274
this		and	False

########NEW FILE########
__FILENAME__ = E30
#: E301:5:5
class X:

    def a():
        pass
    def b():
        pass
#: E301:6:5
class X:

    def a():
        pass
    # comment
    def b():
        pass
#:


#: E302:3:1
#!python
# -*- coding: utf-8 -*-
def a():
    pass
#: E302:2:1
"""Main module."""
def _main():
    pass
#: E302:2:1
import sys
def get_sys_path():
    return sys.path
#: E302:4:1
def a():
    pass

def b():
    pass
#: E302:6:1
def a():
    pass

# comment

def b():
    pass
#:


#: E303:5:1
print



print
#: E303:5:1
print



# comment

print
#: E303:5:5 E303:8:5
def a():
    print


    # comment


    # another comment

    print
#:


#: E304:3:1
@decorator

def function():
    pass
#: E303:5:1
#!python



"""This class docstring comes on line 5.
It gives error E303: too many blank lines (3)
"""
#:

########NEW FILE########
__FILENAME__ = E30not
#: Okay
class X:
    pass
#: Okay

def foo():
    pass
#: Okay
# -*- coding: utf-8 -*-
class X:
    pass
#: Okay
# -*- coding: utf-8 -*-
def foo():
    pass
#: Okay
class X:

    def a():
        pass

    # comment
    def b():
        pass

    # This is a
    # ... multi-line comment

    def c():
        pass


# This is a
# ... multi-line comment

@some_decorator
class Y:

    def a():
        pass

    # comment

    def b():
        pass

    @property
    def c():
        pass


try:
    from nonexistent import Bar
except ImportError:
    class Bar(object):
        """This is a Bar replacement"""


def with_feature(f):
    """Some decorator"""
    wrapper = f
    if has_this_feature(f):
        def wrapper(*args):
            call_feature(args[0])
            return f(*args)
    return wrapper


try:
    next
except NameError:
    def next(iterator, default):
        for item in iterator:
            return item
        return default


def a():
    pass


class Foo():
    """Class Foo"""

    def b():

        pass


# comment
def c():
    pass


# comment


def d():
    pass

# This is a
# ... multi-line comment

# And this one is
# ... a second paragraph
# ... which spans on 3 lines


# Function `e` is below
# NOTE: Hey this is a testcase

def e():
    pass


def a():
    print

    # comment

    print

    print

# Comment 1

# Comment 2


# Comment 3

def b():

    pass

########NEW FILE########
__FILENAME__ = E40
#: E401
import os, sys
#: Okay
import os
import sys

from subprocess import Popen, PIPE

from myclass import MyClass
from foo.bar.yourclass import YourClass

import myclass
import foo.bar.yourclass

########NEW FILE########
__FILENAME__ = E50
#: E501
a = '12345678901234567890123456789012345678901234567890123456789012345678901234567890'
#: E502
a = ('123456789012345678901234567890123456789012345678901234567890123456789'  \
     '01234567890')
#: E502
a = ('AAA  \
      BBB' \
     'CCC')
#: E502
if (foo is None and bar is "e000" and \
        blah == 'yeah'):
    blah = 'yeahnah'
#
#: Okay
a = ('AAA'
     'BBB')

a = ('AAA  \
      BBB'
     'CCC')

a = 'AAA'    \
    'BBB'    \
    'CCC'

a = ('AAA\
BBBBBBBBB\
CCCCCCCCC\
DDDDDDDDD')
#
#: Okay
if aaa:
    pass
elif bbb or \
        ccc:
    pass

ddd = \
    ccc

('\
    ' + ' \
')
('''
    ''' + ' \
')
#: E501 E225 E226
very_long_identifiers=and_terrible_whitespace_habits(are_no_excuse+for_long_lines)
#
#: E501
'''multiline string
with a long long long long long long long long long long long long long long long long line
'''
#: E501
'''same thing, but this time without a terminal newline in the string
long long long long long long long long long long long long long long long long line'''
#
# issue 224 (unavoidable long lines in docstrings)
#: Okay
"""
I'm some great documentation.  Because I'm some great documentation, I'm
going to give you a reference to some valuable information about some API
that I'm calling:

    http://msdn.microsoft.com/en-us/library/windows/desktop/aa363858(v=vs.85).aspx
"""
#: E501
"""
longnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaces"""
#: Okay
"""
This
                                                                       almost_empty_line
"""
#: E501
"""
This
                                                                        almost_empty_line
"""
#: E501
# A basic comment
# with a long long long long long long long long long long long long long long long long line

#
#: Okay
# I'm some great comment.  Because I'm so great, I'm going to give you a
# reference to some valuable information about some API that I'm calling:
#
#     http://msdn.microsoft.com/en-us/library/windows/desktop/aa363858(v=vs.85).aspx

import this

# longnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaces

#
#: Okay
# This
#                                                                      almost_empty_line

#
#: E501
# This
#                                                                       almost_empty_line

########NEW FILE########
__FILENAME__ = E70
#: E701
if a: a = False
#: E701
if not header or header[:6] != 'bytes=': return
#: E702
a = False; b = True
#: E702
import bdist_egg; bdist_egg.write_safety_flag(cmd.egg_info, safe)
#: E703
import shlex;
#: E702 E703
del a[:]; a.append(42);
#:

########NEW FILE########
__FILENAME__ = E71
#: E711
if res == None:
    pass
#: E712
if res == True:
    pass
#: E712
if res != False:
    pass

#
#: E713
if not X in Y:
    pass
#: E713
if not X.B in Y:
    pass
#: E713
if not X in Y and Z == "zero":
    pass
#: E713
if X == "zero" or not Y in Z:
    pass

#
#: E714
if not X is Y:
    pass
#: E714
if not X.B is Y:
    pass
#: Okay
if x not in y:
    pass
if not (X in Y or X is Z):
    pass
if not (X in Y):
    pass
if x is not y:
    pass
#:

########NEW FILE########
__FILENAME__ = E72
#: E721
if type(res) == type(42):
    pass
#: E721
if type(res) != type(""):
    pass
#: E721
import types

if res == types.IntType:
    pass
#: E721
import types

if type(res) is not types.ListType:
    pass
#: E721
assert type(res) == type(False) or type(res) == type(None)
#: E721
assert type(res) == type([])
#: E721
assert type(res) == type(())
#: E721
assert type(res) == type((0,))
#: E721
assert type(res) == type((0))
#: E721
assert type(res) != type((1, ))
#: E721
assert type(res) is type((1, ))
#: E721
assert type(res) is not type((1, ))
#: E211 E721
assert type(res) == type ([2, ])
#: E201 E201 E202 E721
assert type(res) == type( ( ) )
#: E201 E202 E721
assert type(res) == type( (0, ) )
#:

#: Okay
import types

if isinstance(res, int):
    pass
if isinstance(res, str):
    pass
if isinstance(res, types.MethodType):
    pass
if type(a) != type(b) or type(a) == type(ccc):
    pass

########NEW FILE########
__FILENAME__ = latin-1
# -*- coding: latin-1 -*-
# Test non-UTF8 encoding
latin1 = ('��������������������������������'
          '������������������������������')

c = ("w�")

########NEW FILE########
__FILENAME__ = long_lines
if True:
    if True:
        if True:
            self.__heap.sort()  # pylint: builtin sort probably faster than O(n)-time heapify

            if True:
                foo = '(                                                '+array[0] +'                    '

########NEW FILE########
__FILENAME__ = noqa
#: Okay
# silence E501
url = 'https://api.github.com/repos/sigmavirus24/Todo.txt-python/branches/master?client_id=xxxxxxxxxxxxxxxxxxxxxxxxxxxx&?client_secret=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'  # noqa

# silence E128
from functools import (partial, reduce, wraps,  # noqa
    cmp_to_key)

from functools import (partial, reduce, wraps,
    cmp_to_key)   # noqa

a = 1
if a == None:   # noqa
    pass
#:

########NEW FILE########
__FILENAME__ = E10
#: E101 W191
for a in 'abc':
    for b in 'xyz':
        print a  # indented with 8 spaces
        print b  # indented with 1 tab
#: E101 E122 W191 W191
if True:
    pass

change_2_log = \
    """Change 2 by slamb@testclient on 2006/04/13 21:46:23

	creation
"""

p4change = {
    2: change_2_log,
}


class TestP4Poller(unittest.TestCase):

    def setUp(self):
        self.setUpGetProcessOutput()
        return self.setUpChangeSource()

    def tearDown(self):
        pass

#
#: E101 W191 W191
if True:
    foo(1,
        2)
#: E101 E101 W191 W191


def test_keys(self):
    """areas.json - All regions are accounted for."""
    expected = set([
        u'Norrbotten',
        u'V\xe4sterbotten',
    ])
#:

########NEW FILE########
__FILENAME__ = E11
#: E111
if x > 2:
    print x
#: E111
if True:
    print
#: E112
if False:
print
#: E113
print
    print
#: E111 E113
mimetype = 'application/x-directory'
# 'httpd/unix-directory'
create_date = False

########NEW FILE########
__FILENAME__ = E12
#: E121
print "E121", (
    "dent")
#: E122
print "E122", (
    "dent")
#: E123
my_list = [
    1, 2, 3,
    4, 5, 6,
]
#: E124
print "E124", ("visual",
               "indent_two"
               )
#: E124
print "E124", ("visual",
               "indent_five"
               )
#: E124
a = (123,
     )
#: E129
if (row < 0 or self.moduleCount <= row or
        col < 0 or self.moduleCount <= col):
    raise Exception("%s,%s - %s" % (row, col, self.moduleCount))
#: E126
print "E126", (
    "dent")
#: E126
print "E126", (
    "dent")
#: E127
print "E127", ("over-",
               "over-indent")
#: E128
print "E128", ("visual",
               "hanging")
#: E128
print "E128", ("under-",
               "under-indent")
#:


#: E126
my_list = [
    1, 2, 3,
    4, 5, 6,
]
#: E121
result = {
    'key1': 'value',
    'key2': 'value',
}
#: E126 E126
rv.update(dict.fromkeys((
    'qualif_nr', 'reasonComment_en', 'reasonComment_fr',
    'reasonComment_de', 'reasonComment_it'),
    '?'),
    "foo")
#: E126
abricot = 3 + \
    4 + \
    5 + 6
#: E131
print "hello", (

    "there",
    # "john",
    "dude")
#: E126
part = set_mimetype((
    a.get('mime_type', 'text')),
    'default')
#:


#: E122
if True:
    result = some_function_that_takes_arguments(
        'a', 'b', 'c',
        'd', 'e', 'f',
    )
#: E122
if some_very_very_very_long_variable_name or var \
        or another_very_long_variable_name:
    raise Exception()
#: E122
if some_very_very_very_long_variable_name or var[0] \
        or another_very_long_variable_name:
    raise Exception()
#: E122
if True:
    if some_very_very_very_long_variable_name or var \
            or another_very_long_variable_name:
        raise Exception()
#: E122
if True:
    if some_very_very_very_long_variable_name or var[0] \
            or another_very_long_variable_name:
        raise Exception()
#: E122
dictionary = [
    "is": {
        "nested": yes(),
    },
]
#: E122
setup('',
      scripts=[''],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
      ])
#:


#: E123 W291
print "E123", (
    "bad", "hanging", "close"
)
#
#: E123 E123 E123
result = {
    'foo': [
        'bar', {
            'baz': 'frop',
        }
    ]
}
#: E123
result = some_function_that_takes_arguments(
    'a', 'b', 'c',
    'd', 'e', 'f',
)
#: E124
my_list = [1, 2, 3,
           4, 5, 6,
           ]
#: E124
my_list = [1, 2, 3,
           4, 5, 6,
           ]
#: E124
result = some_function_that_takes_arguments('a', 'b', 'c',
                                            'd', 'e', 'f',
                                            )
#: E124
fooff(aaaa,
      cca(
          vvv,
          dadd
      ), fff,
      )
#: E124
fooff(aaaa,
      ccaaa(
          vvv,
          dadd
      ),
      fff,
      )
#: E124
d = dict('foo',
         help="exclude files or directories which match these "
              "comma separated patterns (default: %s)" % DEFAULT_EXCLUDE
         )
#: E124 E128 E128
if line_removed:
    self.event(cr, uid,
               name="Removing the option for contract",
               description="contract line has been removed",
               )
#:


#: E125
if foo is None and bar is "frop" and \
        blah == 'yeah':
    blah = 'yeahnah'
#: E125
# Further indentation required as indentation is not distinguishable


def long_function_name(
        var_one, var_two, var_three,
        var_four):
    print(var_one)
#
#: E125


def qualify_by_address(
        self, cr, uid, ids, context=None,
        params_to_check=frozenset(QUALIF_BY_ADDRESS_PARAM)):
    """ This gets called by the web server """
#: E129
if (a == 2 or
        b == "abc def ghi"
        "jkl mno"):
    return True
#:


#: E126
my_list = [
    1, 2, 3,
    4, 5, 6,
]
#: E126
abris = 3 + \
    4 + \
    5 + 6
#: E126
fixed = re.sub(r'\t+', ' ', target[c::-1], 1)[::-1] + \
    target[c + 1:]
#: E126 E126
rv.update(dict.fromkeys((
    'qualif_nr', 'reasonComment_en', 'reasonComment_fr',
    'reasonComment_de', 'reasonComment_it'),
    '?'),
    "foo")
#: E126
eat_a_dict_a_day({
    "foo": "bar",
})
#: E126
if (
    x == (
        3
    ) or
        y == 4):
    pass
#: E126
if (
    x == (
        3
    ) or
    x == (
        3
    ) or
        y == 4):
    pass
#: E131
troublesome_hash = {
    "hash": "value",
    "long": "the quick brown fox jumps over the lazy dog before doing a "
    "somersault",
}
#:


#: E128
# Arguments on first line forbidden when not using vertical alignment
foo = long_function_name(var_one, var_two,
                         var_three, var_four)
#
#: E128
print('l.%s\t%s\t%s\t%r' %
      (token[2][0], pos, tokenize.tok_name[token[0]], token[1]))
#: E128


def qualify_by_address(self, cr, uid, ids, context=None,
                       params_to_check=frozenset(QUALIF_BY_ADDRESS_PARAM)):
    """ This gets called by the web server """
#:


#: E128
foo(1, 2, 3,
    4, 5, 6)
#: E128
foo(1, 2, 3,
    4, 5, 6)
#: E128
foo(1, 2, 3,
    4, 5, 6)
#: E128
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E127
foo(1, 2, 3,
    4, 5, 6)
#: E128 E128
if line_removed:
    self.event(cr, uid,
               name="Removing the option for contract",
               description="contract line has been removed",
               )
#: E124 E127 E127
if line_removed:
    self.event(cr, uid,
               name="Removing the option for contract",
               description="contract line has been removed",
               )
#: E127
rv.update(d=('a', 'b', 'c'),
          e=42)
#
#: E127
rv.update(d=('a' + 'b', 'c'),
          e=42, f=42
          + 42)
#: E127
input1 = {'a': {'calc': 1 + 2}, 'b': 1
          + 42}
#: E128
rv.update(d=('a' + 'b', 'c'),
          e=42, f=(42
                   + 42))
#: E123
if True:
    def example_issue254():
        return [node.copy(
            (
                replacement
                # First, look at all the node's current children.
                for child in node.children
                # Replace them.
                for replacement in replace(child)
            ),
            dict(name=token.undefined)
        )]
#: E125:2:5 E125:8:5
if ("""
    """):
    pass

for foo in """
    abc
    123
    """.strip().split():
    print(foo)
#: E122:6:5 E122:7:5 E122:8:1
print dedent(
    '''
        mkdir -p ./{build}/
        mv ./build/ ./{build}/%(revision)s/
    '''.format(
        build='build',
        # more stuff
    )
)
#: E701:1:8 E122:2:1 E203:4:8 E128:5:1
if True:
    print(True)

print(a, end=' ')
#:

########NEW FILE########
__FILENAME__ = E20
#: E201:1:6
spam(ham[1], {eggs: 2})
#: E201:1:10
spam(ham[1], {eggs: 2})
#: E201:1:15
spam(ham[1], {eggs: 2})
#: Okay
spam(ham[1], {eggs: 2})
#:


#: E202:1:23
spam(ham[1], {eggs: 2})
#: E202:1:22
spam(ham[1], {eggs: 2})
#: E202:1:11
spam(ham[1], {eggs: 2})
#: Okay
spam(ham[1], {eggs: 2})

result = func(
    arg1='some value',
    arg2='another value',
)

result = func(
    arg1='some value',
    arg2='another value'
)

result = [
    item for item in items
    if item > 5
]
#:


#: E203:1:10
if x == 4:
    print x, y
    x, y = y, x
#: E203:2:15 E702:2:16
if x == 4:
    print x, y
    x, y = y, x
#: E203:3:13
if x == 4:
    print x, y
    x, y = y, x
#: Okay
if x == 4:
    print x, y
    x, y = y, x
a[b1, :] == a[b1, ...]
b = a[:, b1]
#:

########NEW FILE########
__FILENAME__ = E21
#: E211
spam(1)
#: E211 E211
dict['key'] = list[index]
#: E211
dict['key']['subkey'] = list[index]
#: Okay
spam(1)
dict['key'] = list[index]


# This is not prohibited by PEP8, but avoid it.
class Foo (Bar, Baz):
    pass

########NEW FILE########
__FILENAME__ = E22
#: E221
a = 12 + 3
b = 4 + 5
#: E221 E221
x = 1
y = 2
long_variable = 3
#: E221 E221
x[0] = 1
x[1] = 2
long_variable = 3
#: E221 E221
x = f(x) + 1
y = long_variable + 2
z = x[0] + 3
#: E221:3:14
text = """
    bar
    foo %s"""  % rofl
#: Okay
x = 1
y = 2
long_variable = 3
#:


#: E222
a = a + 1
b = b + 10
#: E222 E222
x = -1
y = -2
long_variable = 3
#: E222 E222
x[0] = 1
x[1] = 2
long_variable = 3
#:


#: E223
foobart = 4
a = 3  # aligned with tab
#:


#: E224
a += 1
b += 1000
#:


#: E225
submitted += 1
#: E225
submitted += 1
#: E225
c = -1
#: E225
x = x / 2 - 1
#: E225
c = alpha - 4
#: E225
c = alpha - 4
#: E225
z = x ** y
#: E225
z = (x + 1) ** y
#: E225
z = (x + 1) ** y
#: E225
_1kB = _1MB >> 10
#: E225
_1kB = _1MB >> 10
#: E225 E225
i = i + 1
#: E225 E225
i = i + 1
#: E225 E226
i = i + 1
#: E225 E226
i = i + 1
#: E225 E226
i = i + 1
#: E225 E226
c = (a + b) * (a - b)
#: E225 E226
c = (a + b) * (a - b)
#:

#: E226
z = 2 ** 30
#: E226 E226
c = (a + b) * (a - b)
#: E226
norman = True + False
#: E226
x = x * 2 - 1
#: E226
x = x / 2 - 1
#: E226 E226
hypot2 = x * x + y * y
#: E226
c = (a + b) * (a - b)
#: E226


def squares(n):
    return (i ** 2 for i in range(n))
#: E227
_1kB = _1MB >> 10
#: E227
_1MB = _1kB << 10
#: E227
a = b | c
#: E227
b = c & a
#: E227
c = b ^ a
#: E228
a = b % c
#: E228
msg = fmt % (errno, errmsg)
#: E228
msg = "Error %d occured" % errno
#:

#: Okay
i = i + 1
submitted += 1
x = x * 2 - 1
hypot2 = x * x + y * y
c = (a + b) * (a - b)
_1MB = 2 ** 20
foo(bar, key='word', *args, **kwargs)
baz(**kwargs)
negative = -1
spam(-1)
-negative
lambda *args, **kw: (args, kw)
lambda a, b=h[:], c=0: (a, b, c)
if not -5 < x < +5:
    print >>sys.stderr, "x is out of range."
print >> sys.stdout, "x is an integer."
z = 2 ** 30
x = x / 2 - 1

if alpha[:-i]:
    *a, b = (1, 2, 3)


def squares(n):
    return (i ** 2 for i in range(n))
#:

########NEW FILE########
__FILENAME__ = E23
#: E231
a = (1, 2)
#: E231
a[b1, :]
#: E231
a = [{'a': ''}]
#: Okay
a = (4,)
b = (5, )
c = {'text': text[5:]}

result = {
    'key1': 'value',
    'key2': 'value',
}

########NEW FILE########
__FILENAME__ = E24
#: E241
a = (1, 2)
#: Okay
b = (1, 20)
#: E242
a = (1, 2)  # tab before 2
#: Okay
b = (1, 20)  # space before 20
#: E241 E241 E241
# issue 135
more_spaces = [a, b,
               ef, +h,
               c, -d]

########NEW FILE########
__FILENAME__ = E25
#: E251 E251
def foo(bar=False):
    '''Test function with an error in declaration'''
    pass
#: E251
foo(bar=True)
#: E251
foo(bar=True)
#: E251 E251
foo(bar=True)
#: E251
y = bar(root="sdasd")
#: E251:2:29
parser.add_argument('--long-option',
                    default="/rather/long/filesystem/path/here/blah/blah/blah")
#: E251:1:45
parser.add_argument(
    '--long-option',
    default="/rather/long/filesystem/path/here/blah/blah/blah")
#: Okay
foo(bar=(1 == 1))
foo(bar=(1 != 1))
foo(bar=(1 >= 1))
foo(bar=(1 <= 1))
(options, args) = parser.parse_args()
d[type(None)] = _deepcopy_atomic

########NEW FILE########
__FILENAME__ = E26
#: E261
pass  # an inline comment
#: E262
x = x + 1  # Increment x
#: E262
x = x + 1  # Increment x
#: E262
x = y + 1  # :  Increment x
#: E265
# Block comment
a = 1
#: E265
m = 42
#! This is important
mx = 42 - 42
#: Okay
#!/usr/bin/env python

pass  # an inline comment
x = x + 1   # Increment x
y = y + 1   #: Increment x

# Block comment
a = 1

# Block comment1

# Block comment2
aaa = 1


# example of docstring (not parsed)
def oof():
    """
    #foo not parsed
    """

########NEW FILE########
__FILENAME__ = E27
#: Okay
True and False
#: E271
True and False
#: E272
True and False
#: E271
if 1:
    #: E273
True and False
#: E273 E274
True and False
#: E271
a and b
#: E271
1 and b
#: E271
a and 2
#: E271 E272
1 and b
#: E271 E272
a and 2
#: E272
this and False
#: E273
a and b
#: E274
a and b
#: E273 E274
this and False

########NEW FILE########
__FILENAME__ = E30
#: E301:5:5
class X:

    def a():
        pass

    def b():
        pass
#: E301:6:5


class X:

    def a():
        pass
    # comment

    def b():
        pass
#:


#: E302:3:1
#!python
# -*- coding: utf-8 -*-
def a():
    pass
#: E302:2:1
"""Main module."""


def _main():
    pass
#: E302:2:1
import sys


def get_sys_path():
    return sys.path
#: E302:4:1


def a():
    pass


def b():
    pass
#: E302:6:1


def a():
    pass

# comment


def b():
    pass
#:


#: E303:5:1
print


print
#: E303:5:1
print


# comment

print
#: E303:5:5 E303:8:5


def a():
    print

    # comment

    # another comment

    print
#:


#: E304:3:1
@decorator
def function():
    pass
#: E303:5:1
#!python


"""This class docstring comes on line 5.
It gives error E303: too many blank lines (3)
"""
#:

########NEW FILE########
__FILENAME__ = E30not
#: Okay
class X:
    pass
#: Okay


def foo():
    pass
#: Okay
# -*- coding: utf-8 -*-


class X:
    pass
#: Okay
# -*- coding: utf-8 -*-


def foo():
    pass
#: Okay


class X:

    def a():
        pass

    # comment
    def b():
        pass

    # This is a
    # ... multi-line comment

    def c():
        pass


# This is a
# ... multi-line comment

@some_decorator
class Y:

    def a():
        pass

    # comment

    def b():
        pass

    @property
    def c():
        pass


try:
    from nonexistent import Bar
except ImportError:
    class Bar(object):

        """This is a Bar replacement"""


def with_feature(f):
    """Some decorator"""
    wrapper = f
    if has_this_feature(f):
        def wrapper(*args):
            call_feature(args[0])
            return f(*args)
    return wrapper


try:
    next
except NameError:
    def next(iterator, default):
        for item in iterator:
            return item
        return default


def a():
    pass


class Foo():

    """Class Foo"""

    def b():

        pass


# comment
def c():
    pass


# comment


def d():
    pass

# This is a
# ... multi-line comment

# And this one is
# ... a second paragraph
# ... which spans on 3 lines


# Function `e` is below
# NOTE: Hey this is a testcase

def e():
    pass


def a():
    print

    # comment

    print

    print

# Comment 1

# Comment 2


# Comment 3

def b():

    pass

########NEW FILE########
__FILENAME__ = E40
#: E401
import os
import sys
#: Okay
import os
import sys

from subprocess import Popen, PIPE

from myclass import MyClass
from foo.bar.yourclass import YourClass

import myclass
import foo.bar.yourclass

########NEW FILE########
__FILENAME__ = E50
#: E501
a = '12345678901234567890123456789012345678901234567890123456789012345678901234567890'
#: E502
a = ('123456789012345678901234567890123456789012345678901234567890123456789'
     '01234567890')
#: E502
a = ('AAA  \
      BBB'
     'CCC')
#: E502
if (foo is None and bar is "e000" and
        blah == 'yeah'):
    blah = 'yeahnah'
#
#: Okay
a = ('AAA'
     'BBB')

a = ('AAA  \
      BBB'
     'CCC')

a = 'AAA'    \
    'BBB'    \
    'CCC'

a = ('AAA\
BBBBBBBBB\
CCCCCCCCC\
DDDDDDDDD')
#
#: Okay
if aaa:
    pass
elif bbb or \
        ccc:
    pass

ddd = \
    ccc

('\
    ' + ' \
')
('''
    ''' + ' \
')
#: E501 E225 E226
very_long_identifiers = and_terrible_whitespace_habits(
    are_no_excuse +
    for_long_lines)
#
#: E501
'''multiline string
with a long long long long long long long long long long long long long long long long line
'''
#: E501
'''same thing, but this time without a terminal newline in the string
long long long long long long long long long long long long long long long long line'''
#
# issue 224 (unavoidable long lines in docstrings)
#: Okay
"""
I'm some great documentation.  Because I'm some great documentation, I'm
going to give you a reference to some valuable information about some API
that I'm calling:

    http://msdn.microsoft.com/en-us/library/windows/desktop/aa363858(v=vs.85).aspx
"""
#: E501
"""
longnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaces"""
#: Okay
"""
This
                                                                       almost_empty_line
"""
#: E501
"""
This
                                                                        almost_empty_line
"""
#: E501
# A basic comment
# with a long long long long long long long long long long long long long
# long long long line

#
#: Okay
# I'm some great comment.  Because I'm so great, I'm going to give you a
# reference to some valuable information about some API that I'm calling:
#
#     http://msdn.microsoft.com/en-us/library/windows/desktop/aa363858(v=vs.85).aspx

import this

# longnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaceslongnospaces

#
#: Okay
# This
#                                                                      almost_empty_line

#
#: E501
# This
# almost_empty_line

########NEW FILE########
__FILENAME__ = E70
#: E701
if a:
    a = False
#: E701
if not header or header[:6] != 'bytes=':
    return
#: E702
a = False
b = True
#: E702
import bdist_egg
bdist_egg.write_safety_flag(cmd.egg_info, safe)
#: E703
import shlex
#: E702 E703
del a[:]
a.append(42)
#:

########NEW FILE########
__FILENAME__ = E71
#: E711
if res is None:
    pass
#: E712
if res:
    pass
#: E712
if res:
    pass

#
#: E713
if X not in Y:
    pass
#: E713
if not X.B in Y:
    pass
#: E713
if not X in Y and Z == "zero":
    pass
#: E713
if X == "zero" or not Y in Z:
    pass

#
#: E714
if not X is Y:
    pass
#: E714
if not X.B is Y:
    pass
#: Okay
if x not in y:
    pass
if not (X in Y or X is Z):
    pass
if not (X in Y):
    pass
if x is not y:
    pass
#:

########NEW FILE########
__FILENAME__ = E72
#: E721
if isinstance(res, type(42)):
    pass
#: E721
if not isinstance(res, type("")):
    pass
#: E721
import types

if res == types.IntType:
    pass
#: E721
import types

if not isinstance(res, types.ListType):
    pass
#: E721
assert isinstance(res, type(False)) or isinstance(res, type(None))
#: E721
assert isinstance(res, type([]))
#: E721
assert isinstance(res, type(()))
#: E721
assert isinstance(res, type((0,)))
#: E721
assert isinstance(res, type((0)))
#: E721
assert not isinstance(res, type((1, )))
#: E721
assert isinstance(res, type((1, )))
#: E721
assert not isinstance(res, type((1, )))
#: E211 E721
assert isinstance(res, type([2, ]))
#: E201 E201 E202 E721
assert isinstance(res, type(()))
#: E201 E202 E721
assert isinstance(res, type((0, )))
#:

#: Okay
import types

if isinstance(res, int):
    pass
if isinstance(res, str):
    pass
if isinstance(res, types.MethodType):
    pass
if not isinstance(a, type(b)) or isinstance(a, type(ccc)):
    pass

########NEW FILE########
__FILENAME__ = latin-1
../latin-1.py
########NEW FILE########
__FILENAME__ = long_lines
if True:
    if True:
        if True:
            self.__heap.sort(
            )  # pylint: builtin sort probably faster than O(n)-time heapify

            if True:
                foo = '(                                                ' + \
                    array[0] + '                    '

########NEW FILE########
__FILENAME__ = noqa
../noqa.py
########NEW FILE########
__FILENAME__ = python3
../python3.py
########NEW FILE########
__FILENAME__ = utf-8-bom
../utf-8-bom.py
########NEW FILE########
__FILENAME__ = utf-8
# -*- coding: utf-8 -*-


class Rectangle(Blob):

    def __init__(self, width, height,
                 color='black', emphasis=None, highlight=0):
        if width == 0 and height == 0 and \
                color == 'red' and emphasis == 'strong' or \
                highlight > 100:
            raise ValueError("sorry, you lose")
        if width == 0 and height == 0 and (color == 'red' or
                                           emphasis is None):
            raise ValueError("I don't think so -- values are %s, %s" %
                             (width, height))
        Blob.__init__(self, width, height,
                      color, emphasis, highlight)


# Some random text with multi-byte characters (utf-8 encoded)
#
# Εδώ μάτσο κειμένων τη, τρόπο πιθανό διευθυντές ώρα μη. Νέων απλό παράγει ροή
# κι, το επί δεδομένη καθορίζουν. Πάντως ζητήσεις περιβάλλοντος ένα με, τη
# ξέχασε αρπάζεις φαινόμενο όλη. Τρέξει εσφαλμένη χρησιμοποίησέ νέα τι. Θα όρο
# πετάνε φακέλους, άρα με διακοπής λαμβάνουν εφαμοργής. Λες κι μειώσει
# καθυστερεί.

# 79 narrow chars
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 [79]

# 78 narrow chars (Na) + 1 wide char (W)
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8情

# 3 narrow chars (Na) + 40 wide chars (W)
# 情 情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情

# 3 narrow chars (Na) + 76 wide chars (W)
# 情 情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情

#
#: E501
# 80 narrow chars (Na)
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6  [80]
#
#: E501
# 78 narrow chars (Na) + 2 wide char (W)
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8情情
#
#: E501
# 3 narrow chars (Na) + 77 wide chars (W)
# 情 情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情
#

########NEW FILE########
__FILENAME__ = W19
#: W191
if False:
    print  # indented with 1 tab
#:


#: W191
y = x == 2 \
    or x == 3
#: E101 W191
if (
        x == (
            3
        ) or
        y == 4):
    pass
#: E101 W191
if x == 2 \
    or y > 1 \
        or x == 3:
    pass
#: E101 W191
if x == 2 \
        or y > 1 \
        or x == 3:
    pass
#:

#: E101 W191
if (foo == bar and
        baz == frop):
    pass
#: E101 W191
if (
    foo == bar and
    baz == frop
):
    pass
#:

#: E101 E101 W191 W191
if start[1] > end_col and not (
        over_indent == 4 and indent_next):
    return(0, "E121 continuation line over-"
           "indented for visual indent")
#:

#: E101 W191


def long_function_name(
        var_one, var_two, var_three,
        var_four):
    print(var_one)
#: E101 W191
if ((row < 0 or self.moduleCount <= row or
     col < 0 or self.moduleCount <= col)):
    raise Exception("%s,%s - %s" % (row, col, self.moduleCount))
#: E101 E101 E101 E101 W191 W191 W191 W191 W191 W191
if bar:
    return(
        start, 'E121 lines starting with a '
        'closing bracket should be indented '
        "to match that of the opening "
        "bracket's line"
    )
#
#: E101 W191
# you want vertical alignment, so use a parens
if ((foo.bar("baz") and
     foo.bar("frop")
     )):
    print "yes"
#: E101 W191
# also ok, but starting to look like LISP
if ((foo.bar("baz") and
     foo.bar("frop"))):
    print "yes"
#: E101 W191
if (a == 2 or
    b == "abc def ghi"
         "jkl mno"):
    return True
#: E101 W191
if (a == 2 or
    b == """abc def ghi
jkl mno"""):
    return True
#: E101 W191
if length > options.max_line_length:
    return options.max_line_length, \
        "E501 line too long (%d characters)" % length


#
#: E101 W191 W191
if os.path.exists(os.path.join(path, PEP8_BIN)):
    cmd = ([os.path.join(path, PEP8_BIN)] +
           self._pep8_options(targetfile))
#: W191
'''
	multiline string with tab in it'''
#: E101 W191
'''multiline string
	with tabs
   and spaces
'''
#: Okay
'''sometimes, you just need to go nuts in a multiline string
	and allow all sorts of crap
  like mixed tabs and spaces
      
or trailing whitespace  
or long long long long long long long long long long long long long long long long long lines
'''  # nopep8
#: Okay
'''this one
	will get no warning
even though the noqa comment is not immediately after the string
''' + foo  # noqa
#
#: E101 W191
if foo is None and bar is "frop" and \
        blah == 'yeah':
    blah = 'yeahnah'


#
#: W191 W191 W191
if True:
    foo(
        1,
        2)
#: W191 W191 W191 W191 W191


def test_keys(self):
    """areas.json - All regions are accounted for."""
    expected = set([
        u'Norrbotten',
        u'V\xe4sterbotten',
    ])
#: W191
x = [
    'abc'
]
#:

########NEW FILE########
__FILENAME__ = W29
#: Okay
# 情
#: W291
print
#: W293


class Foo(object):

    bang = 12
#: W291
'''multiline
string with trailing whitespace'''
#: W292
# This line doesn't have a linefeed

########NEW FILE########
__FILENAME__ = W39
#: W391
# The next line is blank

#: Okay
'''there is nothing wrong
with a multiline string at EOF

that happens to have a blank line in it
'''

########NEW FILE########
__FILENAME__ = W60
#: W601
if "b" in a:
    print a
#: W602
raise DummyError, "Message"
#: W602
raise ValueError, "hello %s %s" % (1, 2)
#: Okay
raise type_, val, tb
raise Exception, Exception("f"), t
#: W603
if x != 0:
    x = 0
#: W604
val = repr(1 + 2)

########NEW FILE########
__FILENAME__ = python3
#!/usr/bin/env python3


# Annotated function (Issue #29)
def foo(x: int) -> int:
    return x + 1

########NEW FILE########
__FILENAME__ = utf-8-bom
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-

hello = 'こんにちわ'

# EOF

########NEW FILE########
__FILENAME__ = utf-8
# -*- coding: utf-8 -*-


class Rectangle(Blob):

        def __init__(self, width, height,
                     color='black', emphasis=None, highlight=0):
            if width == 0 and height == 0 and \
                    color == 'red' and emphasis == 'strong' or \
                    highlight > 100:
                raise ValueError("sorry, you lose")
            if width == 0 and height == 0 and (color == 'red' or
                                               emphasis is None):
                raise ValueError("I don't think so -- values are %s, %s" %
                                 (width, height))
            Blob.__init__(self, width, height,
                          color, emphasis, highlight)


# Some random text with multi-byte characters (utf-8 encoded)
#
# Εδώ μάτσο κειμένων τη, τρόπο πιθανό διευθυντές ώρα μη. Νέων απλό παράγει ροή
# κι, το επί δεδομένη καθορίζουν. Πάντως ζητήσεις περιβάλλοντος ένα με, τη
# ξέχασε αρπάζεις φαινόμενο όλη. Τρέξει εσφαλμένη χρησιμοποίησέ νέα τι. Θα όρο
# πετάνε φακέλους, άρα με διακοπής λαμβάνουν εφαμοργής. Λες κι μειώσει
# καθυστερεί.

# 79 narrow chars
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 [79]

# 78 narrow chars (Na) + 1 wide char (W)
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8情

# 3 narrow chars (Na) + 40 wide chars (W)
# 情 情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情

# 3 narrow chars (Na) + 76 wide chars (W)
# 情 情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情

#
#: E501
# 80 narrow chars (Na)
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6  [80]
#
#: E501
# 78 narrow chars (Na) + 2 wide char (W)
# 01 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8情情
#
#: E501
# 3 narrow chars (Na) + 77 wide chars (W)
# 情 情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情情
#

########NEW FILE########
__FILENAME__ = W19
#: W191
if False:
	print  # indented with 1 tab
#:


#: W191
y = x == 2 \
	or x == 3
#: E101 W191
if (
        x == (
            3
        ) or
        y == 4):
	pass
#: E101 W191
if x == 2 \
    or y > 1 \
        or x == 3:
	pass
#: E101 W191
if x == 2 \
        or y > 1 \
        or x == 3:
	pass
#:

#: E101 W191
if (foo == bar and
        baz == frop):
	pass
#: E101 W191
if (
    foo == bar and
    baz == frop
):
	pass
#:

#: E101 E101 W191 W191
if start[1] > end_col and not (
        over_indent == 4 and indent_next):
	return(0, "E121 continuation line over-"
	       "indented for visual indent")
#:

#: E101 W191


def long_function_name(
        var_one, var_two, var_three,
        var_four):
	print(var_one)
#: E101 W191
if ((row < 0 or self.moduleCount <= row or
     col < 0 or self.moduleCount <= col)):
	raise Exception("%s,%s - %s" % (row, col, self.moduleCount))
#: E101 E101 E101 E101 W191 W191 W191 W191 W191 W191
if bar:
	return(
	    start, 'E121 lines starting with a '
	    'closing bracket should be indented '
	    "to match that of the opening "
	    "bracket's line"
	)
#
#: E101 W191
# you want vertical alignment, so use a parens
if ((foo.bar("baz") and
     foo.bar("frop")
     )):
	print "yes"
#: E101 W191
# also ok, but starting to look like LISP
if ((foo.bar("baz") and
     foo.bar("frop"))):
	print "yes"
#: E101 W191
if (a == 2 or
    b == "abc def ghi"
         "jkl mno"):
	return True
#: E101 W191
if (a == 2 or
    b == """abc def ghi
jkl mno"""):
	return True
#: E101 W191
if length > options.max_line_length:
	return options.max_line_length, \
	    "E501 line too long (%d characters)" % length


#
#: E101 W191 W191
if os.path.exists(os.path.join(path, PEP8_BIN)):
	cmd = ([os.path.join(path, PEP8_BIN)] +
	       self._pep8_options(targetfile))
#: W191
'''
	multiline string with tab in it'''
#: E101 W191
'''multiline string
	with tabs
   and spaces
'''
#: Okay
'''sometimes, you just need to go nuts in a multiline string
	and allow all sorts of crap
  like mixed tabs and spaces
      
or trailing whitespace  
or long long long long long long long long long long long long long long long long long lines
'''  # nopep8
#: Okay
'''this one
	will get no warning
even though the noqa comment is not immediately after the string
''' + foo  # noqa
#
#: E101 W191
if foo is None and bar is "frop" and \
        blah == 'yeah':
	blah = 'yeahnah'


#
#: W191 W191 W191
if True:
	foo(
		1,
		2)
#: W191 W191 W191 W191 W191
def test_keys(self):
	"""areas.json - All regions are accounted for."""
	expected = set([
		u'Norrbotten',
		u'V\xe4sterbotten',
	])
#: W191
x = [
	'abc'
]
#:

########NEW FILE########
__FILENAME__ = W29
#: Okay
# 情
#: W291
print 
#: W293
class Foo(object):
    
    bang = 12
#: W291
'''multiline
string with trailing whitespace'''   
#: W292
# This line doesn't have a linefeed
########NEW FILE########
__FILENAME__ = W39
#: W391
# The next line is blank

#: Okay
'''there is nothing wrong
with a multiline string at EOF

that happens to have a blank line in it
'''

########NEW FILE########
__FILENAME__ = W60
#: W601
if a.has_key("b"):
    print a
#: W602
raise DummyError, "Message"
#: W602
raise ValueError, "hello %s %s" % (1, 2)
#: Okay
raise type_, val, tb
raise Exception, Exception("f"), t
#: W603
if x <> 0:
    x = 0
#: W604
val = `1 + 2`

########NEW FILE########
__FILENAME__ = test_autopep8
#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import os
import re
import sys

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import contextlib
import io
import shutil
from subprocess import Popen, PIPE
from tempfile import mkstemp
import tempfile
import tokenize
import warnings

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

ROOT_DIR = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]

sys.path.insert(0, ROOT_DIR)
import autopep8


if 'AUTOPEP8_COVERAGE' in os.environ and int(os.environ['AUTOPEP8_COVERAGE']):
    AUTOPEP8_CMD_TUPLE = ('coverage', 'run', '--branch', '--parallel',
                          '--omit=*/site-packages/*',
                          os.path.join(ROOT_DIR, 'autopep8.py'),)
else:
    # We need to specify the executable to make sure the correct Python
    # interpreter gets used.
    AUTOPEP8_CMD_TUPLE = (sys.executable,
                          os.path.join(ROOT_DIR,
                                       'autopep8.py'),)  # pragma: no cover


class UnitTests(unittest.TestCase):

    maxDiff = None

    def test_find_newline_only_cr(self):
        source = ['print 1\r', 'print 2\r', 'print3\r']
        self.assertEqual(autopep8.CR, autopep8.find_newline(source))

    def test_find_newline_only_lf(self):
        source = ['print 1\n', 'print 2\n', 'print3\n']
        self.assertEqual(autopep8.LF, autopep8.find_newline(source))

    def test_find_newline_only_crlf(self):
        source = ['print 1\r\n', 'print 2\r\n', 'print3\r\n']
        self.assertEqual(autopep8.CRLF, autopep8.find_newline(source))

    def test_find_newline_cr1_and_lf2(self):
        source = ['print 1\n', 'print 2\r', 'print3\n']
        self.assertEqual(autopep8.LF, autopep8.find_newline(source))

    def test_find_newline_cr1_and_crlf2(self):
        source = ['print 1\r\n', 'print 2\r', 'print3\r\n']
        self.assertEqual(autopep8.CRLF, autopep8.find_newline(source))

    def test_find_newline_should_default_to_lf(self):
        self.assertEqual(autopep8.LF, autopep8.find_newline([]))
        self.assertEqual(autopep8.LF, autopep8.find_newline(['', '']))

    def test_detect_encoding(self):
        self.assertEqual(
            'utf-8',
            autopep8.detect_encoding(
                os.path.join(ROOT_DIR, 'setup.py')))

    def test_detect_encoding_with_cookie(self):
        self.assertEqual(
            'iso-8859-1',
            autopep8.detect_encoding(
                os.path.join(ROOT_DIR, 'test', 'iso_8859_1.py')))

    def test_readlines_from_file_with_bad_encoding(self):
        """Bad encoding should not cause an exception."""
        self.assertEqual(
            ['# -*- coding: zlatin-1 -*-\n'],
            autopep8.readlines_from_file(
                os.path.join(ROOT_DIR, 'test', 'bad_encoding.py')))

    def test_readlines_from_file_with_bad_encoding2(self):
        """Bad encoding should not cause an exception."""
        # This causes a warning on Python 3.
        with warnings.catch_warnings(record=True):
            self.assertTrue(autopep8.readlines_from_file(
                os.path.join(ROOT_DIR, 'test', 'bad_encoding2.py')))

    def test_fix_whitespace(self):
        self.assertEqual(
            'a b',
            autopep8.fix_whitespace('a    b', offset=1, replacement=' '))

    def test_fix_whitespace_with_tabs(self):
        self.assertEqual(
            'a b',
            autopep8.fix_whitespace('a\t  \t  b', offset=1, replacement=' '))

    def test_multiline_string_lines(self):
        self.assertEqual(
            set([2]),
            autopep8.multiline_string_lines(
                """\
'''
'''
"""))

    def test_multiline_string_lines_with_many(self):
        self.assertEqual(
            set([2, 7, 10, 11, 12]),
            autopep8.multiline_string_lines(
                """\
'''
'''
''''''
''''''
''''''
'''
'''

'''


'''
"""))

    def test_multiline_string_should_not_report_single_line(self):
        self.assertEqual(
            set(),
            autopep8.multiline_string_lines(
                """\
'''abc'''
"""))

    def test_multiline_string_should_not_report_docstrings(self):
        self.assertEqual(
            set([5]),
            autopep8.multiline_string_lines(
                """\
def foo():
    '''Foo.
    Bar.'''
    hello = '''
'''
"""))

    def test_supported_fixes(self):
        self.assertIn('E121', [f[0] for f in autopep8.supported_fixes()])

    def test_shorten_comment(self):
        self.assertEqual('# ' + '=' * 72 + '\n',
                         autopep8.shorten_comment('# ' + '=' * 100 + '\n',
                                                  max_line_length=79))

    def test_shorten_comment_should_not_split_numbers(self):
        line = '# ' + '0' * 100 + '\n'
        self.assertEqual(line,
                         autopep8.shorten_comment(line,
                                                  max_line_length=79))

    def test_shorten_comment_should_not_split_words(self):
        line = '# ' + 'a' * 100 + '\n'
        self.assertEqual(line,
                         autopep8.shorten_comment(line,
                                                  max_line_length=79))

    def test_shorten_comment_should_not_split_urls(self):
        line = '# http://foo.bar/' + 'abc-' * 100 + '\n'
        self.assertEqual(line,
                         autopep8.shorten_comment(line,
                                                  max_line_length=79))

    def test_shorten_comment_should_not_modify_special_comments(self):
        line = '#!/bin/blah ' + ' x' * 90 + '\n'
        self.assertEqual(line,
                         autopep8.shorten_comment(line,
                                                  max_line_length=79))

    def test_format_block_comments(self):
        self.assertEqual(
            '# abc',
            autopep8.fix_e265('#abc'))

        self.assertEqual(
            '# abc',
            autopep8.fix_e265('####abc'))

        self.assertEqual(
            '# abc',
            autopep8.fix_e265('##   #   ##abc'))

    def test_format_block_comments_should_leave_outline_alone(self):
        line = """\
###################################################################
##   Some people like these crazy things. So leave them alone.   ##
###################################################################
"""
        self.assertEqual(line, autopep8.fix_e265(line))

        line = """\
#################################################################
#   Some people like these crazy things. So leave them alone.   #
#################################################################
"""
        self.assertEqual(line, autopep8.fix_e265(line))

    def test_format_block_comments_with_multiple_lines(self):
        self.assertEqual(
            """\
# abc
  # blah blah
    # four space indentation
''' #do not modify strings
#do not modify strings
#do not modify strings
#do not modify strings'''
#
""",
            autopep8.fix_e265("""\
# abc
  #blah blah
    #four space indentation
''' #do not modify strings
#do not modify strings
#do not modify strings
#do not modify strings'''
#
"""))

    def test_format_block_comments_should_not_corrupt_special_comments(self):
        self.assertEqual(
            '#: abc',
            autopep8.fix_e265('#: abc'))

        self.assertEqual(
            '#!/bin/bash\n',
            autopep8.fix_e265('#!/bin/bash\n'))

    def test_format_block_comments_should_only_touch_real_comments(self):
        commented_out_code = '#x = 1'
        self.assertEqual(
            commented_out_code,
            autopep8.fix_e265(commented_out_code))

    def test_fix_file(self):
        self.assertIn(
            'import ',
            autopep8.fix_file(
                filename=os.path.join(ROOT_DIR, 'test', 'example.py')))

    def test_fix_file_with_diff(self):
        filename = os.path.join(ROOT_DIR, 'test', 'example.py')

        self.assertIn(
            '@@',
            autopep8.fix_file(
                filename=filename,
                options=autopep8.parse_args(['--diff', filename])))

    def test_fix_lines(self):
        self.assertEqual(
            'print(123)\n',
            autopep8.fix_lines(['print( 123 )\n'],
                               options=autopep8.parse_args([''])))

    def test_fix_code(self):
        self.assertEqual(
            'print(123)\n',
            autopep8.fix_code('print( 123 )\n'))

    def test_fix_code_with_empty_string(self):
        self.assertEqual(
            '',
            autopep8.fix_code(''))

    def test_fix_code_with_multiple_lines(self):
        self.assertEqual(
            'print(123)\nx = 4\n',
            autopep8.fix_code('print( 123 )\nx   =4'))

    def test_fix_code_byte_string(self):
        """This feature is here for friendliness to Python 2."""
        self.assertEqual(
            'print(123)\n',
            autopep8.fix_code(b'print( 123 )\n'))

    def test_normalize_line_endings(self):
        self.assertEqual(
            ['abc\n', 'def\n', '123\n', 'hello\n', 'world\n'],
            autopep8.normalize_line_endings(
                ['abc\n', 'def\n', '123\n', 'hello\r\n', 'world\r'],
                '\n'))

    def test_normalize_line_endings_with_crlf(self):
        self.assertEqual(
            ['abc\r\n', 'def\r\n', '123\r\n', 'hello\r\n', 'world\r\n'],
            autopep8.normalize_line_endings(
                ['abc\n', 'def\r\n', '123\r\n', 'hello\r\n', 'world\r'],
                '\r\n'))

    def test_normalize_multiline(self):
        self.assertEqual('def foo(): pass',
                         autopep8.normalize_multiline('def foo():'))

        self.assertEqual('def _(): return 1',
                         autopep8.normalize_multiline('return 1'))

        self.assertEqual('@decorator\ndef _(): pass',
                         autopep8.normalize_multiline('@decorator\n'))

        self.assertEqual('class A: pass',
                         autopep8.normalize_multiline('class A:'))

    def test_code_match(self):
        self.assertTrue(autopep8.code_match('E2', select=['E2', 'E3'],
                                            ignore=[]))
        self.assertTrue(autopep8.code_match('E26', select=['E2', 'E3'],
                                            ignore=[]))

        self.assertFalse(autopep8.code_match('E26', select=[], ignore=['E']))
        self.assertFalse(autopep8.code_match('E2', select=['E2', 'E3'],
                                             ignore=['E2']))
        self.assertFalse(autopep8.code_match('E26', select=['W'], ignore=['']))
        self.assertFalse(autopep8.code_match('E26', select=['W'],
                                             ignore=['E1']))

    def test_split_at_offsets(self):
        self.assertEqual([''], autopep8.split_at_offsets('', [0]))
        self.assertEqual(['1234'], autopep8.split_at_offsets('1234', [0]))
        self.assertEqual(['1', '234'], autopep8.split_at_offsets('1234', [1]))
        self.assertEqual(['12', '34'], autopep8.split_at_offsets('1234', [2]))
        self.assertEqual(['12', '3', '4'],
                         autopep8.split_at_offsets('1234', [2, 3]))

    def test_split_at_offsets_with_out_of_order(self):
        self.assertEqual(['12', '3', '4'],
                         autopep8.split_at_offsets('1234', [3, 2]))

    def test_fix_2to3(self):
        self.assertEqual(
            'try: pass\nexcept ValueError as e: pass\n',
            autopep8.fix_2to3('try: pass\nexcept ValueError, e: pass\n'))

        self.assertEqual(
            'while True: pass\n',
            autopep8.fix_2to3('while 1: pass\n'))

        self.assertEqual(
            """\
import sys
sys.maxsize
""",
            autopep8.fix_2to3("""\
import sys
sys.maxint
"""))

    def test_fix_2to3_subset(self):
        line = 'type(res) == type(42)\n'
        fixed = 'isinstance(res, type(42))\n'

        self.assertEqual(fixed, autopep8.fix_2to3(line))
        self.assertEqual(fixed, autopep8.fix_2to3(line, select=['E721']))
        self.assertEqual(fixed, autopep8.fix_2to3(line, select=['E7']))

        self.assertEqual(line, autopep8.fix_2to3(line, select=['W']))
        self.assertEqual(line, autopep8.fix_2to3(line, select=['E999']))
        self.assertEqual(line, autopep8.fix_2to3(line, ignore=['E721']))

    def test_is_python_file(self):
        self.assertTrue(autopep8.is_python_file(
            os.path.join(ROOT_DIR, 'autopep8.py')))

        with temporary_file_context('#!/usr/bin/env python') as filename:
            self.assertTrue(autopep8.is_python_file(filename))

        with temporary_file_context('#!/usr/bin/python') as filename:
            self.assertTrue(autopep8.is_python_file(filename))

        with temporary_file_context('#!/usr/bin/python3') as filename:
            self.assertTrue(autopep8.is_python_file(filename))

        with temporary_file_context('#!/usr/bin/pythonic') as filename:
            self.assertFalse(autopep8.is_python_file(filename))

        with temporary_file_context('###!/usr/bin/python') as filename:
            self.assertFalse(autopep8.is_python_file(filename))

        self.assertFalse(autopep8.is_python_file(os.devnull))
        self.assertFalse(autopep8.is_python_file('/bin/bash'))

    def test_match_file(self):
        with temporary_file_context('', suffix='.py', prefix='.') as filename:
            self.assertFalse(autopep8.match_file(filename, exclude=[]),
                             msg=filename)

        self.assertFalse(autopep8.match_file(os.devnull, exclude=[]))

        with temporary_file_context('', suffix='.py', prefix='') as filename:
            self.assertTrue(autopep8.match_file(filename, exclude=[]),
                            msg=filename)

    def test_line_shortening_rank(self):
        self.assertGreater(
            autopep8.line_shortening_rank('(1\n+1)\n',
                                          indent_word='    ',
                                          max_line_length=79),
            autopep8.line_shortening_rank('(1+\n1)\n',
                                          indent_word='    ',
                                          max_line_length=79))

        self.assertGreaterEqual(
            autopep8.line_shortening_rank('(1+\n1)\n',
                                          indent_word='    ',
                                          max_line_length=79),
            autopep8.line_shortening_rank('(1+1)\n',
                                          indent_word='    ',
                                          max_line_length=79))

        # Do not crash.
        autopep8.line_shortening_rank('\n',
                                      indent_word='    ',
                                      max_line_length=79)

        self.assertGreater(
            autopep8.line_shortening_rank('[foo(\nx) for x in y]\n',
                                          indent_word='    ',
                                          max_line_length=79),
            autopep8.line_shortening_rank('[foo(x)\nfor x in y]\n',
                                          indent_word='    ',
                                          max_line_length=79))

    def test_extract_code_from_function(self):
        def fix_e123():
            pass  # pragma: no cover
        self.assertEqual('e123', autopep8.extract_code_from_function(fix_e123))

        def foo():
            pass  # pragma: no cover
        self.assertEqual(None, autopep8.extract_code_from_function(foo))

        def fix_foo():
            pass  # pragma: no cover
        self.assertEqual(None, autopep8.extract_code_from_function(fix_foo))

        def e123():
            pass  # pragma: no cover
        self.assertEqual(None, autopep8.extract_code_from_function(e123))

        def fix_():
            pass  # pragma: no cover
        self.assertEqual(None, autopep8.extract_code_from_function(fix_))

    def test_reindenter(self):
        reindenter = autopep8.Reindenter('if True:\n  pass\n')

        self.assertEqual('if True:\n    pass\n',
                         reindenter.run())

    def test_reindenter_with_non_standard_indent_size(self):
        reindenter = autopep8.Reindenter('if True:\n  pass\n')

        self.assertEqual('if True:\n   pass\n',
                         reindenter.run(3))

    def test_reindenter_with_good_input(self):
        lines = 'if True:\n    pass\n'

        reindenter = autopep8.Reindenter(lines)

        self.assertEqual(lines,
                         reindenter.run())

    def test_reindenter_should_leave_stray_comment_alone(self):
        lines = '  #\nif True:\n  pass\n'

        reindenter = autopep8.Reindenter(lines)

        self.assertEqual('  #\nif True:\n    pass\n',
                         reindenter.run())

    def test_fix_e225_avoid_failure(self):
        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='    1\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e225({'line': 1,
                               'column': 5}))

    def test_fix_e271_ignore_redundant(self):
        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='x = 1\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e271({'line': 1,
                               'column': 2}))

    def test_fix_e401_avoid_non_import(self):
        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='    1\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e401({'line': 1,
                               'column': 5}))

    def test_fix_e711_avoid_failure(self):
        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='None == x\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e711({'line': 1,
                               'column': 6}))

        self.assertEqual(
            [],
            fix_pep8.fix_e711({'line': 1,
                               'column': 700}))

        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='x <> None\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e711({'line': 1,
                               'column': 3}))

    def test_fix_e712_avoid_failure(self):
        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='True == x\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e712({'line': 1,
                               'column': 5}))

        self.assertEqual(
            [],
            fix_pep8.fix_e712({'line': 1,
                               'column': 700}))

        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='x != True\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e712({'line': 1,
                               'column': 3}))

        fix_pep8 = autopep8.FixPEP8(filename='',
                                    options=autopep8.parse_args(['']),
                                    contents='x == False\n')

        self.assertEqual(
            [],
            fix_pep8.fix_e712({'line': 1,
                               'column': 3}))

    def test_get_diff_text(self):
        # We ignore the first two lines since it differs on Python 2.6.
        self.assertEqual(
            """\
-foo
+bar
""",
            '\n'.join(autopep8.get_diff_text(['foo\n'],
                                             ['bar\n'],
                                             '').split('\n')[3:]))

    def test_get_diff_text_without_newline(self):
        # We ignore the first two lines since it differs on Python 2.6.
        self.assertEqual(
            """\
-foo
\\ No newline at end of file
+foo
""",
            '\n'.join(autopep8.get_diff_text(['foo'],
                                             ['foo\n'],
                                             '').split('\n')[3:]))

    def test_count_unbalanced_brackets(self):
        self.assertEqual(
            0,
            autopep8.count_unbalanced_brackets('()'))

        self.assertEqual(
            1,
            autopep8.count_unbalanced_brackets('('))

        self.assertEqual(
            2,
            autopep8.count_unbalanced_brackets('(['))

        self.assertEqual(
            1,
            autopep8.count_unbalanced_brackets('[])'))

        self.assertEqual(
            1,
            autopep8.count_unbalanced_brackets(
                "'','.join(['%s=%s' % (col, col)')"))

    def test_refactor_with_2to3(self):
        self.assertEqual(
            '1 in {}\n',
            autopep8.refactor_with_2to3('{}.has_key(1)\n', ['has_key']))

    def test_refactor_with_2to3_should_handle_syntax_error_gracefully(self):
        self.assertEqual(
            '{}.has_key(1\n',
            autopep8.refactor_with_2to3('{}.has_key(1\n', ['has_key']))

    def test_commented_out_code_lines(self):
        self.assertEqual(
            [1, 4],
            autopep8.commented_out_code_lines("""\
#x = 1
#Hello
#Hello world.
#html_use_index = True
"""))

    def test_standard_deviation(self):
        self.assertAlmostEqual(
            2, autopep8.standard_deviation([2, 4, 4, 4, 5, 5, 7, 9]))

        self.assertAlmostEqual(0, autopep8.standard_deviation([]))
        self.assertAlmostEqual(0, autopep8.standard_deviation([1]))
        self.assertAlmostEqual(.5, autopep8.standard_deviation([1, 2]))

    def test_priority_key_with_non_existent_key(self):
        pep8_result = {'id': 'foobar'}
        self.assertGreater(autopep8._priority_key(pep8_result), 1)

    def test_decode_filename(self):
        self.assertEqual('foo.py', autopep8.decode_filename(b'foo.py'))

    def test_almost_equal(self):
        self.assertTrue(autopep8.code_almost_equal(
            """\
[1, 2, 3
    4, 5]
""",
            """\
[1, 2, 3
4, 5]
"""))

        self.assertTrue(autopep8.code_almost_equal(
            """\
[1,2,3
    4,5]
""",
            """\
[1, 2, 3
4,5]
"""))

        self.assertFalse(autopep8.code_almost_equal(
            """\
[1, 2, 3
    4, 5]
""",
            """\
[1, 2, 3, 4,
    5]
"""))

    def test_token_offsets(self):
        text = """\
1
"""
        string_io = io.StringIO(text)
        self.assertEqual(
            [(tokenize.NUMBER, '1', 0, 1),
             (tokenize.NEWLINE, '\n', 1, 2),
             (tokenize.ENDMARKER, '', 2, 2)],
            list(autopep8.token_offsets(
                tokenize.generate_tokens(string_io.readline))))

    def test_token_offsets_with_multiline(self):
        text = """\
x = '''
1
2
'''
"""
        string_io = io.StringIO(text)
        self.assertEqual(
            [(tokenize.NAME, 'x', 0, 1),
             (tokenize.OP, '=', 2, 3),
             (tokenize.STRING, "'''\n1\n2\n'''", 4, 15),
             (tokenize.NEWLINE, '\n', 15, 16),
             (tokenize.ENDMARKER, '', 16, 16)],
            list(autopep8.token_offsets(
                tokenize.generate_tokens(string_io.readline))))

    def test_token_offsets_with_escaped_newline(self):
        text = """\
True or \\
    False
"""
        string_io = io.StringIO(text)
        self.assertEqual(
            [(tokenize.NAME, 'True', 0, 4),
             (tokenize.NAME, 'or', 5, 7),
             (tokenize.NAME, 'False', 11, 16),
             (tokenize.NEWLINE, '\n', 16, 17),
             (tokenize.ENDMARKER, '', 17, 17)],
            list(autopep8.token_offsets(
                tokenize.generate_tokens(string_io.readline))))

    def test_shorten_line_candidates_are_valid(self):
        for text in [
            """\
[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, y] = [1, 2]
""",
            """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx, y = [1, 2]
""",
            """\
lambda xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx: line_shortening_rank(x,
                                           indent_word,
                                           max_line_length)
""",
        ]:
            indent = autopep8._get_indentation(text)
            source = text[len(indent):]
            assert source.lstrip() == source
            tokens = list(autopep8.generate_tokens(source))

            for candidate in autopep8.shorten_line(
                    tokens, source, indent,
                    indent_word='    ',
                    max_line_length=79,
                    aggressive=10,
                    experimental=True,
                    previous_line=''):

                self.assertEqual(
                    re.sub(r'\s', '', text),
                    re.sub(r'\s', '', candidate))


class SystemTests(unittest.TestCase):

    maxDiff = None

    def test_e101(self):
        line = """\
while True:
    if True:
    \t1
"""
        fixed = """\
while True:
    if True:
        1
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e101_with_indent_size_0(self):
        line = """\
while True:
    if True:
    \t1
"""
        with autopep8_context(line, options=['--indent-size=0']) as result:
            self.assertEqual(line, result)

    def test_e101_with_indent_size_1(self):
        line = """\
while True:
    if True:
    \t1
"""
        fixed = """\
while True:
 if True:
  1
"""
        with autopep8_context(line, options=['--indent-size=1']) as result:
            self.assertEqual(fixed, result)

    def test_e101_with_indent_size_2(self):
        line = """\
while True:
    if True:
    \t1
"""
        fixed = """\
while True:
  if True:
    1
"""
        with autopep8_context(line, options=['--indent-size=2']) as result:
            self.assertEqual(fixed, result)

    def test_e101_with_indent_size_3(self):
        line = """\
while True:
    if True:
    \t1
"""
        fixed = """\
while True:
   if True:
      1
"""
        with autopep8_context(line, options=['--indent-size=3']) as result:
            self.assertEqual(fixed, result)

    def test_e101_should_not_expand_non_indentation_tabs(self):
        line = """\
while True:
    if True:
    \t1 == '\t'
"""
        fixed = """\
while True:
    if True:
        1 == '\t'
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e101_should_ignore_multiline_strings(self):
        line = """\
x = '''
while True:
    if True:
    \t1
'''
"""
        fixed = """\
x = '''
while True:
    if True:
    \t1
'''
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e101_should_fix_docstrings(self):
        line = """\
class Bar(object):

    def foo():
        '''
\tdocstring
        '''
"""
        fixed = """\
class Bar(object):

    def foo():
        '''
        docstring
        '''
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e101_when_pep8_mistakes_first_tab_in_string(self):
        # pep8 will complain about this even if the tab indentation found
        # elsewhere is in a multiline string.
        line = """\
x = '''
\tHello.
'''
if True:
    123
"""
        fixed = """\
x = '''
\tHello.
'''
if True:
    123
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e101_should_ignore_multiline_strings_complex(self):
        line = """\
print(3 <> 4, '''
while True:
    if True:
    \t1
\t''', 4 <> 5)
"""
        fixed = """\
print(3 != 4, '''
while True:
    if True:
    \t1
\t''', 4 != 5)
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e101_with_comments(self):
        line = """\
while True:  # My inline comment
             # with a hanging
             # comment.
    # Hello
    if True:
    \t# My comment
    \t1
    \t# My other comment
"""
        fixed = """\
while True:  # My inline comment
             # with a hanging
             # comment.
    # Hello
    if True:
        # My comment
        1
        # My other comment
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e101_skip_if_bad_indentation(self):
        line = """\
try:
\t    pass
    except:
        pass
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e101_skip_innocuous(self):
        # pep8 will complain about this even if the tab indentation found
        # elsewhere is in a multiline string. If we don't filter the innocuous
        # report properly, the below command will take a long time.
        p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                  ['-vvv', '--select=E101', '--diff',
                   os.path.join(ROOT_DIR, 'test', 'e101_example.py')],
                  stdout=PIPE, stderr=PIPE)
        output = [x.decode('utf-8') for x in p.communicate()][0]
        self.assertEqual('', output)

    def test_e111_short(self):
        line = 'class Dummy:\n\n  def __init__(self):\n    pass\n'
        fixed = 'class Dummy:\n\n    def __init__(self):\n        pass\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e111_long(self):
        line = 'class Dummy:\n\n     def __init__(self):\n          pass\n'
        fixed = 'class Dummy:\n\n    def __init__(self):\n        pass\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e111_longer(self):
        line = """\
while True:
      if True:
            1
      elif True:
            2
"""
        fixed = """\
while True:
    if True:
        1
    elif True:
        2
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e111_multiple_levels(self):
        line = """\
while True:
    if True:
       1

# My comment
print('abc')

"""
        fixed = """\
while True:
    if True:
        1

# My comment
print('abc')
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e111_with_dedent(self):
        line = """\
def foo():
    if True:
         2
    1
"""
        fixed = """\
def foo():
    if True:
        2
    1
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e111_with_other_errors(self):
        line = """\
def foo():
    if True:
         (2 , 1)
    1
    if True:
           print('hello')\t
    2
"""
        fixed = """\
def foo():
    if True:
        (2, 1)
    1
    if True:
        print('hello')
    2
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e111_should_not_modify_string_contents(self):
        line = """\
if True:
 x = '''
 1
 '''
"""
        fixed = """\
if True:
    x = '''
 1
 '''
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e112(self):
        line = """\
if True:
# A comment.
    pass
"""
        fixed = """\
if True:
    # A comment.
    pass
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e112_should_leave_bad_syntax_alone(self):
        line = """\
if True:
pass
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e113(self):
        line = """\
      # A comment.
"""
        fixed = """\
# A comment.
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e113_should_leave_bad_syntax_alone(self):
        line = """\
    pass
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e12_reindent(self):
        line = """\
def foo_bar(baz, frop,
    fizz, bang):  # E128
    pass

if True:
    x = {
         }  # E123
#: E121
print "E121", (
  "dent")
#: E122
print "E122", (
"dent")
#: E124
print "E124", ("visual",
               "indent_two"
              )
#: E125
if (row < 0 or self.moduleCount <= row or
    col < 0 or self.moduleCount <= col):
    raise Exception("%s,%s - %s" % (row, col, self.moduleCount))
#: E126
print "E126", (
            "dent")
#: E127
print "E127", ("over-",
                  "over-indent")
#: E128
print "E128", ("under-",
              "under-indent")
"""
        fixed = """\
def foo_bar(baz, frop,
            fizz, bang):  # E128
    pass

if True:
    x = {
    }  # E123
#: E121
print "E121", (
    "dent")
#: E122
print "E122", (
    "dent")
#: E124
print "E124", ("visual",
               "indent_two"
               )
#: E125
if (row < 0 or self.moduleCount <= row or
        col < 0 or self.moduleCount <= col):
    raise Exception("%s,%s - %s" % (row, col, self.moduleCount))
#: E126
print "E126", (
    "dent")
#: E127
print "E127", ("over-",
               "over-indent")
#: E128
print "E128", ("under-",
               "under-indent")
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e12_reindent_with_multiple_fixes(self):
        line = """\

sql = 'update %s set %s %s' % (from_table,
                               ','.join(['%s=%s' % (col, col) for col in cols]),
        where_clause)
"""
        fixed = """\

sql = 'update %s set %s %s' % (from_table,
                               ','.join(['%s=%s' % (col, col)
                                         for col in cols]),
                               where_clause)
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e12_tricky(self):
        line = """\
#: E126
if (
    x == (
        3
    ) or
    x == (
    3
    ) or
        y == 4):
    pass
"""
        fixed = """\
#: E126
if (
    x == (
        3
    ) or
    x == (
        3
    ) or
        y == 4):
    pass
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e12_large(self):
        line = """\
class BogusController(controller.CementBaseController):

    class Meta:
        pass

class BogusController2(controller.CementBaseController):

    class Meta:
        pass

class BogusController3(controller.CementBaseController):

    class Meta:
        pass

class BogusController4(controller.CementBaseController):

    class Meta:
        pass

class TestBaseController(controller.CementBaseController):

    class Meta:
        pass

class TestBaseController2(controller.CementBaseController):

    class Meta:
        pass

class TestStackedController(controller.CementBaseController):

    class Meta:
        arguments = [
            ]

class TestDuplicateController(controller.CementBaseController):

    class Meta:

        config_defaults = dict(
            foo='bar',
            )

        arguments = [
            (['-f2', '--foo2'], dict(action='store'))
            ]

    def my_command(self):
        pass
"""
        fixed = """\
class BogusController(controller.CementBaseController):

    class Meta:
        pass


class BogusController2(controller.CementBaseController):

    class Meta:
        pass


class BogusController3(controller.CementBaseController):

    class Meta:
        pass


class BogusController4(controller.CementBaseController):

    class Meta:
        pass


class TestBaseController(controller.CementBaseController):

    class Meta:
        pass


class TestBaseController2(controller.CementBaseController):

    class Meta:
        pass


class TestStackedController(controller.CementBaseController):

    class Meta:
        arguments = [
        ]


class TestDuplicateController(controller.CementBaseController):

    class Meta:

        config_defaults = dict(
            foo='bar',
        )

        arguments = [
            (['-f2', '--foo2'], dict(action='store'))
        ]

    def my_command(self):
        pass
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e12_with_bad_indentation(self):
        line = r"""


def bar():
    foo(1,
      2)


def baz():
     pass

    pass
"""
        fixed = r"""


def bar():
    foo(1,
        2)


def baz():
     pass

    pass
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e121_with_multiline_string(self):
        line = """\
testing = \\
'''inputs: d c b a
'''
"""
        fixed = """\
testing = \\
    '''inputs: d c b a
'''
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e121_with_stupid_fallback(self):
        line = """\
list(''.join([
    '%d'
       % 1,
    list(''),
    ''
]))
"""
        fixed = """\
list(''.join([
    '%d'
    % 1,
    list(''),
    ''
]))
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e122_with_fallback(self):
        line = """\
foooo('',
      scripts=[''],
      classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Intended Audience :: Developers',
      ])
"""
        fixed = """\
foooo('',
      scripts=[''],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
      ])
"""
        with autopep8_context(line, options=[]) as result:
            self.assertEqual(fixed, result)

    def test_e123(self):
        line = """\
if True:
    foo = (
        )
"""
        fixed = """\
if True:
    foo = (
    )
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e123_with_escaped_newline(self):
        line = r"""
x = \
    (
)
"""
        fixed = r"""
x = \
    (
    )
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e125(self):
        line = """\
if (a and
    b in [
        'foo',
    ] or
    c):
    pass
"""
        fixed = """\
if (a and
        b in [
            'foo',
        ] or
        c):
    pass
"""
        with autopep8_context(line, options=['--select=E125']) as result:
            self.assertEqual(fixed, result)

    def test_e125_with_multiline_string(self):
        line = """\
for foo in '''
    abc
    123
    '''.strip().split():
    print(foo)
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(line, result)

    def test_e125_with_multiline_string_okay(self):
        line = """\
def bar(
    a='''a'''):
    print(foo)
"""
        fixed = """\
def bar(
        a='''a'''):
    print(foo)
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e126(self):
        line = """\
if True:
    posted = models.DateField(
            default=datetime.date.today,
            help_text="help"
    )
"""
        fixed = """\
if True:
    posted = models.DateField(
        default=datetime.date.today,
        help_text="help"
    )
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e126_should_not_interfere_with_other_fixes(self):
        line = """\
self.assertEqual('bottom 1',
    SimpleNamedNode.objects.filter(id__gt=1).exclude(
        name='bottom 3').filter(
            name__in=['bottom 3', 'bottom 1'])[0].name)
"""
        fixed = """\
self.assertEqual('bottom 1',
                 SimpleNamedNode.objects.filter(id__gt=1).exclude(
                     name='bottom 3').filter(
                     name__in=['bottom 3', 'bottom 1'])[0].name)
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e127(self):
        line = """\
if True:
    if True:
        chksum = (sum([int(value[i]) for i in xrange(0, 9, 2)]) * 7 -
                          sum([int(value[i]) for i in xrange(1, 9, 2)])) % 10
"""
        fixed = """\
if True:
    if True:
        chksum = (sum([int(value[i]) for i in xrange(0, 9, 2)]) * 7 -
                  sum([int(value[i]) for i in xrange(1, 9, 2)])) % 10
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_e127_align_visual_indent(self):
        line = """\
def draw(self):
    color = [([0.2, 0.1, 0.3], [0.2, 0.1, 0.3], [0.2, 0.1, 0.3]),
               ([0.9, 0.3, 0.5], [0.5, 1.0, 0.5], [0.3, 0.3, 0.9])  ][self._p._colored ]
    self.draw_background(color)
"""
        fixed = """\
def draw(self):
    color = [([0.2, 0.1, 0.3], [0.2, 0.1, 0.3], [0.2, 0.1, 0.3]),
             ([0.9, 0.3, 0.5], [0.5, 1.0, 0.5], [0.3, 0.3, 0.9])][self._p._colored]
    self.draw_background(color)
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e127_align_visual_indent_okay(self):
        """This is for code coverage."""
        line = """\
want = (have + _leading_space_count(
        after[jline - 1]) -
        _leading_space_count(lines[jline]))
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e127_with_backslash(self):
        line = r"""
if True:
    if True:
        self.date = meta.session.query(schedule.Appointment)\
            .filter(schedule.Appointment.id ==
                                      appointment_id).one().agenda.endtime
"""
        fixed = r"""
if True:
    if True:
        self.date = meta.session.query(schedule.Appointment)\
            .filter(schedule.Appointment.id ==
                    appointment_id).one().agenda.endtime
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e127_with_bracket_then_parenthesis(self):
        line = r"""
if True:
    foo = [food(1)
               for bar in bars]
"""
        fixed = r"""
if True:
    foo = [food(1)
           for bar in bars]
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e12_with_backslash(self):
        line = r"""
if True:
    assert reeval == parsed, \
            'Repr gives different object:\n  %r !=\n  %r' % (parsed, reeval)
"""
        fixed = r"""
if True:
    assert reeval == parsed, \
        'Repr gives different object:\n  %r !=\n  %r' % (parsed, reeval)
"""
        with autopep8_context(line, options=['--select=E12']) as result:
            self.assertEqual(fixed, result)

    def test_w191(self):
        line = """\
while True:
\tif True:
\t\t1
"""
        fixed = """\
while True:
    if True:
        1
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e201(self):
        line = '(   1)\n'
        fixed = '(1)\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e202(self):
        line = '(1   )\n[2  ]\n{3  }\n'
        fixed = '(1)\n[2]\n{3}\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e202_skip_multiline(self):
        """We skip this since pep8 reports the error as being on line 1."""
        line = """\

('''
a
b
c
''' )
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e202_skip_multiline_with_escaped_newline(self):
        line = r"""

('c\
' )
"""
        fixed = r"""

('c\
')
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e203_colon(self):
        line = '{4 : 3}\n'
        fixed = '{4: 3}\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e203_comma(self):
        line = '[1 , 2  , 3]\n'
        fixed = '[1, 2, 3]\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e203_semicolon(self):
        line = "print(a, end=' ') ; nl = 0\n"
        fixed = "print(a, end=' '); nl = 0\n"
        with autopep8_context(line, options=['--select=E203']) as result:
            self.assertEqual(fixed, result)

    def test_e203_with_newline(self):
        line = "print(a\n, end=' ')\n"
        fixed = "print(a, end=' ')\n"
        with autopep8_context(line, options=['--select=E203']) as result:
            self.assertEqual(fixed, result)

    def test_e211(self):
        line = 'd = [1, 2, 3]\nprint d  [0]\n'
        fixed = 'd = [1, 2, 3]\nprint d[0]\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e221(self):
        line = 'a = 1  + 1\n'
        fixed = 'a = 1 + 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e221_should_skip_multiline(self):
        line = '''\
def javascript(self):
    return u"""
<script type="text/javascript" src="++resource++ptg.shufflegallery/jquery.promptu-menu.js"></script>
<script type="text/javascript">
$(function(){
    $('ul.promptu-menu').promptumenu({width: %(width)i, height: %(height)i, rows: %(rows)i, columns: %(columns)i, direction: '%(direction)s', intertia: %(inertia)i, pages: %(pages)i});
\t$('ul.promptu-menu a').click(function(e) {
        e.preventDefault();
    });
    $('ul.promptu-menu a').dblclick(function(e) {
        window.location.replace($(this).attr("href"));
    });
});
</script>
    """  % {
    }
'''
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e222(self):
        line = 'a = 1 +  1\n'
        fixed = 'a = 1 + 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e223(self):
        line = 'a = 1	+ 1\n'  # include TAB
        fixed = 'a = 1 + 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e223_double(self):
        line = 'a = 1		+ 1\n'  # include TAB
        fixed = 'a = 1 + 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e223_with_tab_indentation(self):
        line = """\
class Foo():

\tdef __init__(self):
\t\tx= 1\t+ 3
"""
        fixed = """\
class Foo():

\tdef __init__(self):
\t\tx = 1 + 3
"""
        with autopep8_context(line, options=['--ignore=E1,W191']) as result:
            self.assertEqual(fixed, result)

    def test_e224(self):
        line = 'a = 11 +	1\n'    # include TAB
        fixed = 'a = 11 + 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e224_double(self):
        line = 'a = 11 +		1\n'    # include TAB
        fixed = 'a = 11 + 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e224_with_tab_indentation(self):
        line = """\
class Foo():

\tdef __init__(self):
\t\tx= \t3
"""
        fixed = """\
class Foo():

\tdef __init__(self):
\t\tx = 3
"""
        with autopep8_context(line, options=['--ignore=E1,W191']) as result:
            self.assertEqual(fixed, result)

    def test_e225(self):
        line = '1+1\n2 +2\n3+ 3\n'
        fixed = '1 + 1\n2 + 2\n3 + 3\n'
        with autopep8_context(line, options=['--select=E,W']) as result:
            self.assertEqual(fixed, result)

    def test_e225_with_indentation_fix(self):
        line = """\
class Foo(object):

  def bar(self):
    return self.elephant is not None
"""
        fixed = """\
class Foo(object):

    def bar(self):
        return self.elephant is not None
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e226(self):
        line = '1*1\n2*2\n3*3\n'
        fixed = '1 * 1\n2 * 2\n3 * 3\n'
        with autopep8_context(line, options=['--select=E22']) as result:
            self.assertEqual(fixed, result)

    def test_e227(self):
        line = '1&1\n2&2\n3&3\n'
        fixed = '1 & 1\n2 & 2\n3 & 3\n'
        with autopep8_context(line, options=['--select=E22']) as result:
            self.assertEqual(fixed, result)

    def test_e228(self):
        line = '1%1\n2%2\n3%3\n'
        fixed = '1 % 1\n2 % 2\n3 % 3\n'
        with autopep8_context(line, options=['--select=E22']) as result:
            self.assertEqual(fixed, result)

    def test_e231(self):
        line = '[1,2,3]\n'
        fixed = '[1, 2, 3]\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e231_with_many_commas(self):
        fixed = str(list(range(200))) + '\n'
        line = re.sub(', ', ',', fixed)
        with autopep8_context(line, options=['--select=E231']) as result:
            self.assertEqual(fixed, result)

    def test_e231_with_colon_after_comma(self):
        """ws_comma fixer ignores this case."""
        line = 'a[b1,:]\n'
        fixed = 'a[b1, :]\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e231_should_only_do_ws_comma_once(self):
        """If we don't check appropriately, we end up doing ws_comma multiple
        times and skipping all other fixes."""
        line = """\
print( 1 )
foo[0,:]
bar[zap[0][0]:zig[0][0],:]
"""
        fixed = """\
print(1)
foo[0, :]
bar[zap[0][0]:zig[0][0], :]
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e241(self):
        line = 'l = (1,  2)\n'
        fixed = 'l = (1, 2)\n'
        with autopep8_context(line, options=['--select=E']) as result:
            self.assertEqual(fixed, result)

    def test_e241_should_be_enabled_by_aggressive(self):
        line = 'l = (1,  2)\n'
        fixed = 'l = (1, 2)\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e241_double(self):
        line = 'l = (1,   2)\n'
        fixed = 'l = (1, 2)\n'
        with autopep8_context(line, options=['--select=E']) as result:
            self.assertEqual(fixed, result)

    def test_e242(self):
        line = 'l = (1,\t2)\n'
        fixed = 'l = (1, 2)\n'
        with autopep8_context(line, options=['--select=E']) as result:
            self.assertEqual(fixed, result)

    def test_e242_double(self):
        line = 'l = (1,\t\t2)\n'
        fixed = 'l = (1, 2)\n'
        with autopep8_context(line, options=['--select=E']) as result:
            self.assertEqual(fixed, result)

    def test_e251(self):
        line = 'def a(arg = 1):\n    print arg\n'
        fixed = 'def a(arg=1):\n    print arg\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e251_with_escaped_newline(self):
        line = '1\n\n\ndef a(arg=\\\n1):\n    print(arg)\n'
        fixed = '1\n\n\ndef a(arg=1):\n    print(arg)\n'
        with autopep8_context(line, options=['--select=E251']) as result:
            self.assertEqual(fixed, result)

    def test_e251_with_calling(self):
        line = 'foo(bar= True)\n'
        fixed = 'foo(bar=True)\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e251_with_argument_on_next_line(self):
        line = 'foo(bar\n=None)\n'
        fixed = 'foo(bar=None)\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e261(self):
        line = "print 'a b '# comment\n"
        fixed = "print 'a b '  # comment\n"
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e261_with_inline_commented_out_code(self):
        line = '1 # 0 + 0\n'
        fixed = '1  # 0 + 0\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e261_with_dictionary(self):
        line = 'd = {# comment\n1: 2}\n'
        fixed = 'd = {  # comment\n    1: 2}\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e261_with_dictionary_no_space(self):
        line = 'd = {#comment\n1: 2}\n'
        fixed = 'd = {  # comment\n    1: 2}\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e261_with_comma(self):
        line = '{1: 2 # comment\n , }\n'
        fixed = '{1: 2  # comment\n , }\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e262_more_space(self):
        line = "print 'a b '  #  comment\n"
        fixed = "print 'a b '  # comment\n"
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e262_none_space(self):
        line = "print 'a b '  #comment\n"
        fixed = "print 'a b '  # comment\n"
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e262_hash_in_string(self):
        line = "print 'a b  #string'  #comment\n"
        fixed = "print 'a b  #string'  # comment\n"
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e262_hash_in_string_and_multiple_hashes(self):
        line = "print 'a b  #string'  #comment #comment\n"
        fixed = "print 'a b  #string'  # comment #comment\n"
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e262_more_complex(self):
        line = "print 'a b '  #comment\n123\n"
        fixed = "print 'a b '  # comment\n123\n"
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e271(self):
        line = 'True and  False\n'
        fixed = 'True and False\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e272(self):
        line = 'True  and False\n'
        fixed = 'True and False\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e273(self):
        line = 'True and\tFalse\n'
        fixed = 'True and False\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e274(self):
        line = 'True\tand False\n'
        fixed = 'True and False\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e301(self):
        line = 'class k:\n    s = 0\n    def f():\n        print 1\n'
        fixed = 'class k:\n    s = 0\n\n    def f():\n        print 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e301_extended_with_docstring(self):
        line = '''\
class Foo(object):
    """Test."""
    def foo(self):



        """Test."""
        def bar():
            pass
'''
        fixed = '''\
class Foo(object):

    """Test."""

    def foo(self):
        """Test."""
        def bar():
            pass
'''
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e302(self):
        line = 'def f():\n    print 1\n\ndef ff():\n    print 2\n'
        fixed = 'def f():\n    print 1\n\n\ndef ff():\n    print 2\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e303(self):
        line = '\n\n\n# alpha\n\n1\n'
        fixed = '\n\n# alpha\n\n1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e303_extended(self):
        line = '''\
def foo():

    """Document."""
'''
        fixed = '''\
def foo():
    """Document."""
'''
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e304(self):
        line = '@contextmanager\n\ndef f():\n    print 1\n'
        fixed = '@contextmanager\ndef f():\n    print 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e304_with_comment(self):
        line = '@contextmanager\n# comment\n\ndef f():\n    print 1\n'
        fixed = '@contextmanager\n# comment\ndef f():\n    print 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e309(self):
        line = 'class Foo:\n    def bar():\n        print 1\n'
        fixed = 'class Foo:\n\n    def bar():\n        print 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e401(self):
        line = 'import os, sys\n'
        fixed = 'import os\nimport sys\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e401_with_indentation(self):
        line = 'def a():\n    import os, sys\n'
        fixed = 'def a():\n    import os\n    import sys\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e401_should_ignore_commented_comma(self):
        line = 'import bdist_egg, egg  # , not a module, neither is this\n'
        fixed = 'import bdist_egg\nimport egg  # , not a module, neither is this\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e401_should_ignore_commented_comma_with_indentation(self):
        line = 'if True:\n    import bdist_egg, egg  # , not a module, neither is this\n'
        fixed = 'if True:\n    import bdist_egg\n    import egg  # , not a module, neither is this\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e401_should_ignore_false_positive(self):
        line = 'import bdist_egg; bdist_egg.write_safety_flag(cmd.egg_info, safe)\n'
        with autopep8_context(line, options=['--select=E401']) as result:
            self.assertEqual(line, result)

    def test_e401_with_escaped_newline_case(self):
        line = 'import foo, \\\n    bar\n'
        fixed = 'import foo\nimport \\\n    bar\n'
        with autopep8_context(line, options=['--select=E401']) as result:
            self.assertEqual(fixed, result)

    def test_e501_basic(self):
        line = """\

print(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        fixed = """\

print(111, 111, 111, 111, 222, 222, 222, 222,
      222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_commas_and_colons(self):
        line = """\
foobar = {'aaaaaaaaaaaa': 'bbbbbbbbbbbbbbbb', 'dddddd': 'eeeeeeeeeeeeeeee', 'ffffffffffff': 'gggggggg'}
"""
        fixed = """\
foobar = {'aaaaaaaaaaaa': 'bbbbbbbbbbbbbbbb',
          'dddddd': 'eeeeeeeeeeeeeeee', 'ffffffffffff': 'gggggggg'}
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_inline_comments(self):
        line = """\
'                                                          '  # Long inline comments should be moved above.
if True:
    '                                                          '  # Long inline comments should be moved above.
"""
        fixed = """\
# Long inline comments should be moved above.
'                                                          '
if True:
    # Long inline comments should be moved above.
    '                                                          '
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_inline_comments_should_skip_multiline(self):
        line = """\
'''This should be left alone. -----------------------------------------------------

'''  # foo

'''This should be left alone. -----------------------------------------------------

''' \\
# foo

'''This should be left alone. -----------------------------------------------------

''' \\
\\
# foo
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(line, result)

    def test_e501_with_inline_comments_should_skip_keywords(self):
        line = """\
'                                                          '  # noqa Long inline comments should be moved above.
if True:
    '                                                          '  # pylint: disable-msgs=E0001
    '                                                          '  # pragma: no cover
    '                                                          '  # pragma: no cover
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_e501_with_inline_comments_should_skip_keywords_without_aggressive(
            self):
        line = """\
'                                                          '  # noqa Long inline comments should be moved above.
if True:
    '                                                          '  # pylint: disable-msgs=E0001
    '                                                          '  # pragma: no cover
    '                                                          '  # pragma: no cover
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e501_with_inline_comments_should_skip_edge_cases(self):
        line = """\
if True:
    x = \\
        '                                                          '  # Long inline comments should be moved above.
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e501_basic_should_prefer_balanced_brackets(self):
        line = """\
if True:
    reconstructed = iradon(radon(image), filter="ramp", interpolation="nearest")
"""
        fixed = """\
if True:
    reconstructed = iradon(
        radon(image), filter="ramp", interpolation="nearest")
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_very_long_line(self):
        line = """\
x = [3244234243234, 234234234324, 234234324, 23424234, 234234234, 234234, 234243, 234243, 234234234324, 234234324, 23424234, 234234234, 234234, 234243, 234243]
"""
        fixed = """\
x = [
    3244234243234,
    234234234324,
    234234324,
    23424234,
    234234234,
    234234,
    234243,
    234243,
    234234234324,
    234234324,
    23424234,
    234234234,
    234234,
    234243,
    234243]
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e501_shorten_at_commas_skip(self):
        line = """\
parser.add_argument('source_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('target_corpus', help='corpus name/path relative to an nltk_data directory')
"""
        fixed = """\
parser.add_argument(
    'source_corpus',
    help='corpus name/path relative to an nltk_data directory')
parser.add_argument(
    'target_corpus',
    help='corpus name/path relative to an nltk_data directory')
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_shorter_length(self):
        line = "foooooooooooooooooo('abcdefghijklmnopqrstuvwxyz')\n"
        fixed = "foooooooooooooooooo(\n    'abcdefghijklmnopqrstuvwxyz')\n"

        with autopep8_context(line,
                              options=['--max-line-length=40']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_indent(self):
        line = """\

def d():
    print(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        fixed = """\

def d():
    print(111, 111, 111, 111, 222, 222, 222, 222,
          222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_alone_with_indentation(self):
        line = """\

if True:
    print(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        fixed = """\

if True:
    print(111, 111, 111, 111, 222, 222, 222, 222,
          222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        with autopep8_context(line, options=['--select=E501']) as result:
            self.assertEqual(fixed, result)

    def test_e501_alone_with_tuple(self):
        line = """\

fooooooooooooooooooooooooooooooo000000000000000000000000 = [1,
                                                            ('TransferTime', 'FLOAT')
                                                           ]
"""
        fixed = """\

fooooooooooooooooooooooooooooooo000000000000000000000000 = [1,
                                                            ('TransferTime',
                                                             'FLOAT')
                                                           ]
"""
        with autopep8_context(line, options=['--select=E501']) as result:
            self.assertEqual(fixed, result)

    def test_e501_should_not_try_to_break_at_every_paren_in_arithmetic(self):
        line = """\
term3 = w6 * c5 * (8.0 * psi4 * (11.0 - 24.0 * t2) - 28 * psi3 * (1 - 6.0 * t2) + psi2 * (1 - 32 * t2) - psi * (2.0 * t2) + t4) / 720.0
this_should_be_shortened = ('                                                                 ', '            ')
"""
        fixed = """\
term3 = w6 * c5 * (8.0 * psi4 * (11.0 - 24.0 * t2) - 28 * psi3 *
                   (1 - 6.0 * t2) + psi2 * (1 - 32 * t2) - psi * (2.0 * t2) + t4) / 720.0
this_should_be_shortened = (
    '                                                                 ',
    '            ')
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e501_arithmetic_operator_with_indent(self):
        line = """\
def d():
    111 + 111 + 111 + 111 + 111 + 222 + 222 + 222 + 222 + 222 + 222 + 222 + 222 + 222 + 333 + 333 + 333 + 333
"""
        fixed = r"""def d():
    111 + 111 + 111 + 111 + 111 + 222 + 222 + 222 + 222 + \
        222 + 222 + 222 + 222 + 222 + 333 + 333 + 333 + 333
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_more_complicated(self):
        line = """\

blahblah = os.environ.get('blahblah') or os.environ.get('blahblahblah') or os.environ.get('blahblahblahblah')
"""
        fixed = """\

blahblah = os.environ.get('blahblah') or os.environ.get(
    'blahblahblah') or os.environ.get('blahblahblahblah')
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_skip_even_more_complicated(self):
        line = """\

if True:
    if True:
        if True:
            blah = blah.blah_blah_blah_bla_bl(blahb.blah, blah.blah,
                                              blah=blah.label, blah_blah=blah_blah,
                                              blah_blah2=blah_blah)
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e501_prefer_to_break_at_begnning(self):
        """We prefer not to leave part of the arguments hanging."""
        line = """\

looooooooooooooong = foo(one, two, three, four, five, six, seven, eight, nine, ten)
"""
        fixed = """\

looooooooooooooong = foo(
    one, two, three, four, five, six, seven, eight, nine, ten)
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_avoid_breaking_at_empty_parentheses_if_possible(self):
        line = """\
someverylongindenttionwhatnot().foo().bar().baz("and here is a long string 123456789012345678901234567890")
"""
        fixed = """\
someverylongindenttionwhatnot().foo().bar().baz(
    "and here is a long string 123456789012345678901234567890")
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_logical_fix(self):
        line = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        fixed = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa,
    bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc,
    dddddddddddddddddddddddd)
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_logical_fix_and_physical_fix(self):
        line = """\
# ------------------------------------ ------------------------------------------
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        fixed = """\
# ------------------------------------ -----------------------------------
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa,
    bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc,
    dddddddddddddddddddddddd)
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_logical_fix_and_adjacent_strings(self):
        line = """\
print('a-----------------------' 'b-----------------------' 'c-----------------------'
      'd-----------------------''e'"f"r"g")
"""
        fixed = """\
print(
    'a-----------------------'
    'b-----------------------'
    'c-----------------------'
    'd-----------------------'
    'e'
    "f"
    r"g")
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_multiple_lines(self):
        line = """\

foo_bar_zap_bing_bang_boom(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333,
                           111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333)
"""
        fixed = """\

foo_bar_zap_bing_bang_boom(
    111,
    111,
    111,
    111,
    222,
    222,
    222,
    222,
    222,
    222,
    222,
    222,
    222,
    333,
    333,
    111,
    111,
    111,
    111,
    222,
    222,
    222,
    222,
    222,
    222,
    222,
    222,
    222,
    333,
    333)
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_multiple_lines_and_quotes(self):
        line = """\

if True:
    xxxxxxxxxxx = xxxxxxxxxxxxxxxxx(xxxxxxxxxxx, xxxxxxxxxxxxxxxx={'xxxxxxxxxxxx': 'xxxxx',
                                                                   'xxxxxxxxxxx': xx,
                                                                   'xxxxxxxx': False,
                                                                   })
"""
        fixed = """\

if True:
    xxxxxxxxxxx = xxxxxxxxxxxxxxxxx(
        xxxxxxxxxxx,
        xxxxxxxxxxxxxxxx={
            'xxxxxxxxxxxx': 'xxxxx',
            'xxxxxxxxxxx': xx,
            'xxxxxxxx': False,
        })
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_do_not_break_on_keyword(self):
        # We don't want to put a newline after equals for keywords as this
        # violates PEP 8.
        line = """\

if True:
    long_variable_name = tempfile.mkstemp(prefix='abcdefghijklmnopqrstuvwxyz0123456789')
"""
        fixed = """\

if True:
    long_variable_name = tempfile.mkstemp(
        prefix='abcdefghijklmnopqrstuvwxyz0123456789')
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_do_not_begin_line_with_comma(self):
        # This fix is incomplete. (The line is still too long.) But it is here
        # just to confirm that we do not put a comma at the beginning of a
        # line.
        line = """\

def dummy():
    if True:
        if True:
            if True:
                object = ModifyAction( [MODIFY70.text, OBJECTBINDING71.text, COLON72.text], MODIFY70.getLine(), MODIFY70.getCharPositionInLine() )
"""
        fixed = """\

def dummy():
    if True:
        if True:
            if True:
                object = ModifyAction([MODIFY70.text, OBJECTBINDING71.text, COLON72.text], MODIFY70.getLine(
                ), MODIFY70.getCharPositionInLine())
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_should_not_break_on_dot(self):
        line = """\
if True:
    if True:
        raise xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx('xxxxxxxxxxxxxxxxx "{d}" xxxxxxxxxxxxxx'.format(d='xxxxxxxxxxxxxxx'))
"""

        fixed = """\
if True:
    if True:
        raise xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx(
            'xxxxxxxxxxxxxxxxx "{d}" xxxxxxxxxxxxxx'.format(d='xxxxxxxxxxxxxxx'))
"""

        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_comment(self):
        line = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        pass

# http://foo.bar/abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-

# The following is ugly commented-out code and should not be touched.
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx = 1
"""
        fixed = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will
                        # wrap it using textwrap to be within 72 characters.
                        pass

# http://foo.bar/abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-

# The following is ugly commented-out code and should not be touched.
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx = 1
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_comment_should_not_modify_docstring(self):
        line = '''\
def foo():
    """
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
    """
'''
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e501_should_only_modify_last_comment(self):
        line = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 1. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 2. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 3. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
"""
        fixed = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 1. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 2. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 3. This is a long comment that should be wrapped. I
                        # will wrap it using textwrap to be within 72
                        # characters.
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_should_not_interfere_with_non_comment(self):
        line = '''

"""
# not actually a comment %d. 12345678901234567890, 12345678901234567890, 12345678901234567890.
""" % (0,)
'''
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e501_should_cut_comment_pattern(self):
        line = """123
# -- Useless lines ----------------------------------------------------------------------
321
"""
        fixed = """123
# -- Useless lines -------------------------------------------------------
321
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_function_should_not_break_on_colon(self):
        line = r"""
class Useless(object):

    def _table_field_is_plain_widget(self, widget):
        if widget.__class__ == Widget or\
                (widget.__class__ == WidgetMeta and Widget in widget.__bases__):
            return True

        return False
"""

        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e501_should_break_before_tuple_start(self):
        line = """\
xxxxxxxxxxxxx(aaaaaaaaaaaaa, bbbbbbbbbbbbbbbbbb, cccccccccc, (dddddddddddddddddddddd, eeeeeeeeeeee, fffffffffff, gggggggggg))
"""
        fixed = """\
xxxxxxxxxxxxx(aaaaaaaaaaaaa, bbbbbbbbbbbbbbbbbb, cccccccccc,
              (dddddddddddddddddddddd, eeeeeeeeeeee, fffffffffff, gggggggggg))
"""

        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive(self):
        line = """\
models = {
    'auth.group': {
        'Meta': {'object_name': 'Group'},
        'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
    },
    'auth.permission': {
        'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
        'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
    },
}
"""
        fixed = """\
models = {
    'auth.group': {
        'Meta': {
            'object_name': 'Group'},
        'permissions': (
            'django.db.models.fields.related.ManyToManyField',
            [],
            {
                'to': "orm['auth.Permission']",
                'symmetrical': 'False',
                'blank': 'True'})},
    'auth.permission': {
        'Meta': {
            'ordering': "('content_type__app_label', 'content_type__model', 'codename')",
            'unique_together': "(('content_type', 'codename'),)",
            'object_name': 'Permission'},
        'name': (
            'django.db.models.fields.CharField',
            [],
            {
                'max_length': '50'})},
}
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_multiple_logical_lines(self):
        line = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        fixed = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa,
    bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc,
    dddddddddddddddddddddddd)
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa,
    bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc,
    dddddddddddddddddddddddd)
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_multiple_logical_lines_with_math(self):
        line = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx([-1 + 5 / 10,
                                                                            100,
                                                                            -3 - 4])
"""
        fixed = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    [-1 + 5 / 10, 100, -3 - 4])
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_import(self):
        line = """\
from . import (xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,
               yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy)
"""
        fixed = """\
from . import (
    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,
    yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy)
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_massive_number_of_logical_lines(self):
        """We do not care about results here.

        We just want to know that it doesn't take a ridiculous amount of
        time. Caching is currently required to avoid repeately trying
        the same line.

        """
        line = """\
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from provider.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Client'
        db.create_table('oauth2_client', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model_label])),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('redirect_uri', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('client_id', self.gf('django.db.models.fields.CharField')(default='37b581bdc702c732aa65', max_length=255)),
            ('client_secret', self.gf('django.db.models.fields.CharField')(default='5cf90561f7566aa81457f8a32187dcb8147c7b73', max_length=255)),
            ('client_type', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('oauth2', ['Client'])

        # Adding model 'Grant'
        db.create_table('oauth2_grant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model_label])),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oauth2.Client'])),
            ('code', self.gf('django.db.models.fields.CharField')(default='f0cda1a5f4ae915431ff93f477c012b38e2429c4', max_length=255)),
            ('expires', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2012, 2, 8, 10, 43, 45, 620301))),
            ('redirect_uri', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('scope', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('oauth2', ['Grant'])

        # Adding model 'AccessToken'
        db.create_table('oauth2_accesstoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model_label])),
            ('token', self.gf('django.db.models.fields.CharField')(default='b10b8f721e95117cb13c', max_length=255)),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oauth2.Client'])),
            ('expires', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 7, 10, 33, 45, 618854))),
            ('scope', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('oauth2', ['AccessToken'])

        # Adding model 'RefreshToken'
        db.create_table('oauth2_refreshtoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model_label])),
            ('token', self.gf('django.db.models.fields.CharField')(default='84035a870dab7c820c2c501fb0b10f86fdf7a3fe', max_length=255)),
            ('access_token', self.gf('django.db.models.fields.related.OneToOneField')(related_name='refresh_token', unique=True, to=orm['oauth2.AccessToken'])),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oauth2.Client'])),
            ('expired', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('oauth2', ['RefreshToken'])


    def backwards(self, orm):

        # Deleting model 'Client'
        db.delete_table('oauth2_client')

        # Deleting model 'Grant'
        db.delete_table('oauth2_grant')

        # Deleting model 'AccessToken'
        db.delete_table('oauth2_accesstoken')

        # Deleting model 'RefreshToken'
        db.delete_table('oauth2_refreshtoken')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'oauth2.accesstoken': {
            'Meta': {'object_name': 'AccessToken'},
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oauth2.Client']"}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 7, 10, 33, 45, 624553)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scope': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'token': ('django.db.models.fields.CharField', [], {'default': "'d5c1f65020ebdc89f20c'", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
        'oauth2.client': {
            'Meta': {'object_name': 'Client'},
            'client_id': ('django.db.models.fields.CharField', [], {'default': "'306fb26cbcc87dd33cdb'", 'max_length': '255'}),
            'client_secret': ('django.db.models.fields.CharField', [], {'default': "'7e5785add4898448d53767f15373636b918cf0e3'", 'max_length': '255'}),
            'client_type': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'redirect_uri': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
        'oauth2.grant': {
            'Meta': {'object_name': 'Grant'},
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oauth2.Client']"}),
            'code': ('django.db.models.fields.CharField', [], {'default': "'310b2c63e27306ecf5307569dd62340cc4994b73'", 'max_length': '255'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 8, 10, 43, 45, 625956)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'redirect_uri': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'scope': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
        'oauth2.refreshtoken': {
            'Meta': {'object_name': 'RefreshToken'},
            'access_token': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'refresh_token'", 'unique': 'True', 'to': "orm['oauth2.AccessToken']"}),
            'client': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oauth2.Client']"}),
            'expired': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'default': "'ef0ab76037f17769ab2975a816e8f41a1c11d25e'", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        }
    }

    complete_apps = ['oauth2']
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(''.join(line.split()),
                             ''.join(result.split()))

    def test_e501_shorten_comment_with_aggressive(self):
        line = """\
# --------- ----------------------------------------------------------------------
"""
        fixed = """\
# --------- --------------------------------------------------------------
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_escaped_newline(self):
        line = """\
if True or \\
    False:  # test test test test test test test test test test test test test test
    pass
"""
        fixed = """\
# test test test test test test test test test test test test test test
if True or False:
    pass
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_multiline_string(self):
        line = """\
print('---------------------------------------------------------------------',
      ('================================================', '====================='),
      '''--------------------------------------------------------------------------------
      ''')
"""
        fixed = """\
print(
    '---------------------------------------------------------------------',
    ('================================================',
     '====================='),
    '''--------------------------------------------------------------------------------
      ''')
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_multiline_string_with_addition(self):
        line = '''\
def f():
    email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>"""+despot["Nicholas"]+"""<br>
<b>Minion: </b>"""+serf["Dmitri"]+"""<br>
<b>Residence: </b>"""+palace["Winter"]+"""<br>
</body>
</html>"""
'''
        fixed = '''\
def f():
    email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>""" + despot["Nicholas"] + """<br>
<b>Minion: </b>""" + serf["Dmitri"] + """<br>
<b>Residence: </b>""" + palace["Winter"] + """<br>
</body>
</html>"""
'''
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_multiline_string_in_parens(self):
        line = '''\
def f():
    email_text += ("""<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>"""+despot["Nicholas"]+"""<br>
<b>Minion: </b>"""+serf["Dmitri"]+"""<br>
<b>Residence: </b>"""+palace["Winter"]+"""<br>
</body>
</html>""")
'''
        fixed = '''\
def f():
    email_text += (
        """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>""" +
        despot["Nicholas"] +
        """<br>
<b>Minion: </b>""" +
        serf["Dmitri"] +
        """<br>
<b>Residence: </b>""" +
        palace["Winter"] +
        """<br>
</body>
</html>""")
'''
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_indentation(self):
        line = """\
if True:
    # comment here
    print(aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
          bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,cccccccccccccccccccccccccccccccccccccccccc)
"""
        fixed = """\
if True:
    # comment here
    print(
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,
        cccccccccccccccccccccccccccccccccccccccccc)
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_multiple_keys_and_aggressive(self):
        line = """\
one_two_three_four_five_six = {'one two three four five': 12345, 'asdfsdflsdkfjl sdflkjsdkfkjsfjsdlkfj sdlkfjlsfjs': '343',
                               1: 1}
"""
        fixed = """\
one_two_three_four_five_six = {
    'one two three four five': 12345,
    'asdfsdflsdkfjl sdflkjsdkfkjsfjsdlkfj sdlkfjlsfjs': '343',
    1: 1}
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_aggressive_and_carriage_returns_only(self):
        """Make sure _find_logical() does not crash."""
        line = 'if True:\r    from aaaaaaaaaaaaaaaa import bbbbbbbbbbbbbbbbbbb\r    \r    ccccccccccc = None\r'
        fixed = 'if True:\r    from aaaaaaaaaaaaaaaa import bbbbbbbbbbbbbbbbbbb\r\r    ccccccccccc = None\r'
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_should_ignore_imports(self):
        line = """\
import logging, os, bleach, commonware, urllib2, json, time, requests, urlparse, re
"""
        with autopep8_context(line, options=['--select=E501']) as result:
            self.assertEqual(line, result)

    def test_e501_should_not_do_useless_things(self):
        line = """\
foo('                                                                            ')
"""
        with autopep8_context(line) as result:
            self.assertEqual(line, result)

    def test_e501_aggressive_with_percent(self):
        line = """\
raise MultiProjectException("Ambiguous workspace: %s=%s, %s" % ( varname, varname_path, os.path.abspath(config_filename)))
"""
        fixed = """\
raise MultiProjectException(
    "Ambiguous workspace: %s=%s, %s" %
    (varname, varname_path, os.path.abspath(config_filename)))
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e501_aggressive_with_def(self):
        line = """\
def foo(sldfkjlsdfsdf, kksdfsdfsf,sdfsdfsdf, sdfsdfkdk, szdfsdfsdf, sdfsdfsdfsdlkfjsdlf, sdfsdfddf,sdfsdfsfd, sdfsdfdsf):
    pass
"""
        fixed = """\
def foo(sldfkjlsdfsdf, kksdfsdfsf, sdfsdfsdf, sdfsdfkdk, szdfsdfsdf,
        sdfsdfsdfsdlkfjsdlf, sdfsdfddf, sdfsdfsfd, sdfsdfdsf):
    pass
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e501_more_aggressive_with_def(self):
        line = """\
def foobar(sldfkjlsdfsdf, kksdfsdfsf,sdfsdfsdf, sdfsdfkdk, szdfsdfsdf, sdfsdfsdfsdlkfjsdlf, sdfsdfddf,sdfsdfsfd, sdfsdfdsf):
    pass
"""
        fixed = """\


def foobar(
        sldfkjlsdfsdf,
        kksdfsdfsf,
        sdfsdfsdf,
        sdfsdfkdk,
        szdfsdfsdf,
        sdfsdfsdfsdlkfjsdlf,
        sdfsdfddf,
        sdfsdfsfd,
        sdfsdfdsf):
    pass
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_aggressive_with_tuple(self):
        line = """\
def f():
    man_this_is_a_very_long_function_name(an_extremely_long_variable_name,
                                          ('a string that is long: %s'%'bork'))
"""
        fixed = """\
def f():
    man_this_is_a_very_long_function_name(
        an_extremely_long_variable_name,
        ('a string that is long: %s' %
         'bork'))
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_aggressive_with_tuple_in_list(self):
        line = """\
def f(self):
    self._xxxxxxxx(aaaaaa, bbbbbbbbb, cccccccccccccccccc,
                   [('mmmmmmmmmm', self.yyyyyyyyyy.zzzzzzz/_DDDDD)], eee, 'ff')
"""
        fixed = """\
def f(self):
    self._xxxxxxxx(
        aaaaaa, bbbbbbbbb, cccccccccccccccccc, [
            ('mmmmmmmmmm', self.yyyyyyyyyy.zzzzzzz / _DDDDD)], eee, 'ff')
"""

        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_aggressive_decorator(self):
        line = """\
@foo(('xxxxxxxxxxxxxxxxxxxxxxxxxx', users.xxxxxxxxxxxxxxxxxxxxxxxxxx), ('yyyyyyyyyyyy', users.yyyyyyyyyyyy), ('zzzzzzzzzzzzzz', users.zzzzzzzzzzzzzz))
"""
        fixed = """\


@foo(
    ('xxxxxxxxxxxxxxxxxxxxxxxxxx',
     users.xxxxxxxxxxxxxxxxxxxxxxxxxx),
    ('yyyyyyyyyyyy',
     users.yyyyyyyyyyyy),
    ('zzzzzzzzzzzzzz',
     users.zzzzzzzzzzzzzz))
"""

        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_aggressive_long_class_name(self):
        line = """\
class AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA(BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB):
    pass
"""
        fixed = """\
class AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA(
        BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB):
    pass
"""

        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_aggressive_long_comment_and_long_line(self):
        line = """\
def foo():
    #. This is not a novel to be tossed aside lightly. It should be throw with great force.
    self.xxxxxxxxx(_('yyyyyyyyyyyyy yyyyyyyyyyyy yyyyyyyy yyyyyyyy y'), 'zzzzzzzzzzzzzzzzzzz', bork='urgent')
"""
        fixed = """\
def foo():
    #. This is not a novel to be tossed aside lightly. It should be throw with great force.
    self.xxxxxxxxx(
        _('yyyyyyyyyyyyy yyyyyyyyyyyy yyyyyyyy yyyyyyyy y'),
        'zzzzzzzzzzzzzzzzzzz',
        bork='urgent')
"""

        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_aggressive_intermingled_comments(self):
        line = """\
A = [
    # A comment
    ['aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'bbbbbbbbbbbbbbbbbbbbbb', 'cccccccccccccccccccccc']
]
"""
        fixed = """\
A = [
    # A comment
    ['aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
     'bbbbbbbbbbbbbbbbbbbbbb',
     'cccccccccccccccccccccc']
]
"""

        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e501_if_line_over_limit(self):
        line = """\
if not xxxxxxxxxxxx(aaaaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbb, cccccccccccccc, dddddddddddddddddddddd):
    return 1
"""
        fixed = """\
if not xxxxxxxxxxxx(
        aaaaaaaaaaaaaaaaaa,
        bbbbbbbbbbbbbbbb,
        cccccccccccccc,
        dddddddddddddddddddddd):
    return 1
"""
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e502(self):
        line = "print('abc'\\\n      'def')\n"
        fixed = "print('abc'\n      'def')\n"
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e701(self):
        line = 'if True: print True\n'
        fixed = 'if True:\n    print True\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e701_with_escaped_newline(self):
        line = 'if True:\\\nprint True\n'
        fixed = 'if True:\n    print True\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e701_with_escaped_newline_and_spaces(self):
        line = 'if True:    \\   \nprint True\n'
        fixed = 'if True:\n    print True\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702(self):
        line = 'print 1; print 2\n'
        fixed = 'print 1\nprint 2\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_semicolon_at_end(self):
        line = 'print 1;\n'
        fixed = 'print 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_semicolon_and_space_at_end(self):
        line = 'print 1; \n'
        fixed = 'print 1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_whitespace(self):
        line = 'print 1 ; print 2\n'
        fixed = 'print 1\nprint 2\n'
        with autopep8_context(line, options=['--select=E702']) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_non_ascii_file(self):
        line = """\
# -*- coding: utf-8 -*-
# French comment with accent é
# Un commentaire en français avec un accent é

import time

time.strftime('%d-%m-%Y');
"""

        fixed = """\
# -*- coding: utf-8 -*-
# French comment with accent é
# Un commentaire en français avec un accent é

import time

time.strftime('%d-%m-%Y')
"""

        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_escaped_newline(self):
        line = '1; \\\n2\n'
        fixed = '1\n2\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_escaped_newline_with_indentation(self):
        line = '1; \\\n    2\n'
        fixed = '1\n2\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_more_complicated(self):
        line = """\
def foo():
    if bar : bar+=1;  bar=bar*bar   ; return bar
"""
        fixed = """\
def foo():
    if bar:
        bar += 1
        bar = bar * bar
        return bar
"""
        with autopep8_context(line, options=['--select=E,W']) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_semicolon_in_string(self):
        line = 'print(";");\n'
        fixed = 'print(";")\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_semicolon_in_string_to_the_right(self):
        line = 'x = "x"; y = "y;y"\n'
        fixed = 'x = "x"\ny = "y;y"\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_indent_correctly(self):
        line = """\

(
    1,
    2,
    3); 4; 5; 5  # pyflakes
"""
        fixed = """\

(
    1,
    2,
    3)
4
5
5  # pyflakes
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_triple_quote(self):
        line = '"""\n      hello\n   """; 1\n'
        fixed = '"""\n      hello\n   """\n1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_triple_quote_and_indent(self):
        line = '    """\n      hello\n   """; 1\n'
        fixed = '    """\n      hello\n   """\n    1\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e702_with_semicolon_after_string(self):
        line = """\
raise IOError('abc '
              'def.');
"""
        fixed = """\
raise IOError('abc '
              'def.')
"""
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_e711(self):
        line = 'foo == None\n'
        fixed = 'foo is None\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e711_in_conditional(self):
        line = 'if foo == None and None == foo:\npass\n'
        fixed = 'if foo is None and None == foo:\npass\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e711_in_conditional_with_multiple_instances(self):
        line = 'if foo == None and bar == None:\npass\n'
        fixed = 'if foo is None and bar is None:\npass\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e711_with_not_equals_none(self):
        line = 'foo != None\n'
        fixed = 'foo is not None\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e712(self):
        line = 'foo == True\n'
        fixed = 'foo\n'
        with autopep8_context(line,
                              options=['-aa', '--select=E712']) as result:
            self.assertEqual(fixed, result)

    def test_e712_in_conditional_with_multiple_instances(self):
        line = 'if foo == True and bar == True:\npass\n'
        fixed = 'if foo and bar:\npass\n'
        with autopep8_context(line,
                              options=['-aa', '--select=E712']) as result:
            self.assertEqual(fixed, result)

    def test_e712_with_false(self):
        line = 'foo != False\n'
        fixed = 'foo\n'
        with autopep8_context(line,
                              options=['-aa', '--select=E712']) as result:
            self.assertEqual(fixed, result)

    def test_e712_with_special_case_equal_not_true(self):
        line = 'if foo != True:\n    pass\n'
        fixed = 'if not foo:\n    pass\n'
        with autopep8_context(line,
                              options=['-aa', '--select=E712']) as result:
            self.assertEqual(fixed, result)

    def test_e712_with_special_case_equal_false(self):
        line = 'if foo == False:\n    pass\n'
        fixed = 'if not foo:\n    pass\n'
        with autopep8_context(line,
                              options=['-aa', '--select=E712']) as result:
            self.assertEqual(fixed, result)

    def test_e712_only_if_aggressive_level_2(self):
        line = 'foo == True\n'
        with autopep8_context(line, options=['-a']) as result:
            self.assertEqual(line, result)

    def test_e711_and_e712(self):
        line = 'if (foo == None and bar == True) or (foo != False and bar != None):\npass\n'
        fixed = 'if (foo is None and bar) or (foo and bar is not None):\npass\n'
        with autopep8_context(line, options=['-aa']) as result:
            self.assertEqual(fixed, result)

    def test_e713(self):
        line = 'if not x in y:\n    pass\n'
        fixed = 'if x not in y:\n    pass\n'
        with autopep8_context(line,
                              options=['-aa', '--select=E713']) as result:
            self.assertEqual(fixed, result)

    def test_e721(self):
        line = "type('') == type('')\n"
        fixed = "isinstance('', type(''))\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e721_with_str(self):
        line = "str == type('')\n"
        fixed = "isinstance('', str)\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_e721_in_conditional(self):
        line = "if str == type(''):\n    pass\n"
        fixed = "if isinstance('', str):\n    pass\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_should_preserve_vertical_tab(self):
        line = """\
#Memory Bu\vffer Register:
"""
        fixed = """\
# Memory Bu\vffer Register:
"""

        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_w191_should_ignore_multiline_strings(self):
        line = """\
print(3 <> 4, '''
while True:
    if True:
    \t1
\t''', 4 <> 5)
if True:
\t123
"""
        fixed = """\
print(3 != 4, '''
while True:
    if True:
    \t1
\t''', 4 != 5)
if True:
    123
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w191_should_ignore_tabs_in_strings(self):
        line = """\
if True:
\tx = '''
\t\tblah
\tif True:
\t1
\t'''
if True:
\t123
else:
\t32
"""
        fixed = """\
if True:
    x = '''
\t\tblah
\tif True:
\t1
\t'''
if True:
    123
else:
    32
"""
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w291(self):
        line = "print 'a b '\t \n"
        fixed = "print 'a b '\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w291_with_comment(self):
        line = "print 'a b '  # comment\t \n"
        fixed = "print 'a b '  # comment\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w292(self):
        line = '1\n2'
        fixed = '1\n2\n'
        with autopep8_context(line, options=['--aggressive',
                                             '--select=W292']) as result:
            self.assertEqual(fixed, result)

    def test_w293(self):
        line = '1\n \n2\n'
        fixed = '1\n\n2\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w391(self):
        line = '  \n'
        fixed = ''
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w391_more_complex(self):
        line = '123\n456\n  \n'
        fixed = '123\n456\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601(self):
        line = 'a = {0: 1}\na.has_key(0)\n'
        fixed = 'a = {0: 1}\n0 in a\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_word(self):
        line = 'my_dict = {0: 1}\nmy_dict.has_key(0)\n'
        fixed = 'my_dict = {0: 1}\n0 in my_dict\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_conditional(self):
        line = 'a = {0: 1}\nif a.has_key(0):\n    print 1\n'
        fixed = 'a = {0: 1}\nif 0 in a:\n    print 1\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_self(self):
        line = 'self.a.has_key(0)\n'
        fixed = '0 in self.a\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_self_with_conditional(self):
        line = 'if self.a.has_key(0):\n    print 1\n'
        fixed = 'if 0 in self.a:\n    print 1\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_with_multiple(self):
        line = 'a.has_key(0) and b.has_key(0)\n'
        fixed = '0 in a and 0 in b\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_with_multiple_nested(self):
        line = 'alpha.has_key(nested.has_key(12)) and beta.has_key(1)\n'
        fixed = '(12 in nested) in alpha and 1 in beta\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_with_more_complexity(self):
        line = 'y.has_key(0) + x.has_key(x.has_key(0) + x.has_key(x.has_key(0) + x.has_key(1)))\n'
        fixed = '(0 in y) + ((0 in x) + ((0 in x) + (1 in x) in x) in x)\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_precedence(self):
        line = 'if self.a.has_key(1 + 2):\n    print 1\n'
        fixed = 'if 1 + 2 in self.a:\n    print 1\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w601_with_parens(self):
        line = 'foo(12) in alpha\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_w601_with_multiline(self):
        line = """\
a.has_key(
    0
)
"""
        fixed = '0 in a\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    @unittest.skipIf(sys.version_info < (2, 6, 4),
                     'older versions of 2.6 may be buggy')
    def test_w601_with_non_ascii(self):
        line = """\
# -*- coding: utf-8 -*-
## éはe
correct = dict().has_key('good syntax ?')
"""

        fixed = """\
# -*- coding: utf-8 -*-
# éはe
correct = 'good syntax ?' in dict()
"""

        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_arg_is_string(self):
        line = "raise ValueError, \"w602 test\"\n"
        fixed = "raise ValueError(\"w602 test\")\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_arg_is_string_with_comment(self):
        line = "raise ValueError, \"w602 test\"  # comment\n"
        fixed = "raise ValueError(\"w602 test\")  # comment\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_skip_ambiguous_case(self):
        line = "raise 'a', 'b', 'c'\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_w602_with_logic(self):
        line = "raise TypeError, e or 'hello'\n"
        fixed = "raise TypeError(e or 'hello')\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_triple_quotes(self):
        line = 'raise ValueError, """hello"""\n1\n'
        fixed = 'raise ValueError("""hello""")\n1\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiline(self):
        line = 'raise ValueError, """\nhello"""\n'
        fixed = 'raise ValueError("""\nhello""")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_with_complex_multiline(self):
        line = 'raise ValueError, """\nhello %s %s""" % (\n    1, 2)\n'
        fixed = 'raise ValueError("""\nhello %s %s""" % (\n    1, 2))\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiline_with_trailing_spaces(self):
        line = 'raise ValueError, """\nhello"""    \n'
        fixed = 'raise ValueError("""\nhello""")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiline_with_escaped_newline(self):
        line = 'raise ValueError, \\\n"""\nhello"""\n'
        fixed = 'raise ValueError("""\nhello""")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiline_with_escaped_newline_and_comment(self):
        line = 'raise ValueError, \\\n"""\nhello"""  # comment\n'
        fixed = 'raise ValueError("""\nhello""")  # comment\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiline_with_multiple_escaped_newlines(self):
        line = 'raise ValueError, \\\n\\\n\\\n"""\nhello"""\n'
        fixed = 'raise ValueError("""\nhello""")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiline_with_nested_quotes(self):
        line = 'raise ValueError, """hello\'\'\'blah"a"b"c"""\n'
        fixed = 'raise ValueError("""hello\'\'\'blah"a"b"c""")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_with_multiline_with_single_quotes(self):
        line = "raise ValueError, '''\nhello'''\n"
        fixed = "raise ValueError('''\nhello''')\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiline_string_stays_the_same(self):
        line = 'raise """\nhello"""\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_w602_escaped_lf(self):
        line = 'raise ValueError, \\\n"hello"\n'
        fixed = 'raise ValueError("hello")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_escaped_crlf(self):
        line = 'raise ValueError, \\\r\n"hello"\r\n'
        fixed = 'raise ValueError("hello")\r\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_indentation(self):
        line = 'def foo():\n    raise ValueError, "hello"\n'
        fixed = 'def foo():\n    raise ValueError("hello")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_escaped_cr(self):
        line = 'raise ValueError, \\\r"hello"\n\n'
        fixed = 'raise ValueError("hello")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_multiple_statements(self):
        line = 'raise ValueError, "hello";print 1\n'
        fixed = 'raise ValueError("hello")\nprint 1\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_raise_argument_with_indentation(self):
        line = 'if True:\n    raise ValueError, "error"\n'
        fixed = 'if True:\n    raise ValueError("error")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_skip_raise_argument_triple(self):
        line = 'raise ValueError, "info", traceback\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_w602_skip_raise_argument_triple_with_comment(self):
        line = 'raise ValueError, "info", traceback  # comment\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_w602_raise_argument_triple_fake(self):
        line = 'raise ValueError, "info, info2"\n'
        fixed = 'raise ValueError("info, info2")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_with_list_comprehension(self):
        line = 'raise Error, [x[0] for x in probs]\n'
        fixed = 'raise Error([x[0] for x in probs])\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w602_with_bad_syntax(self):
        line = "raise Error, 'abc\n"
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_w603(self):
        line = 'if 2 <> 2:\n    print False'
        fixed = 'if 2 != 2:\n    print False\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w604(self):
        line = '`1`\n'
        fixed = 'repr(1)\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w604_with_multiple_instances(self):
        line = '``1`` + ``b``\n'
        fixed = 'repr(repr(1)) + repr(repr(b))\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_w604_with_multiple_lines(self):
        line = '`(1\n      )`\n'
        fixed = 'repr((1\n      ))\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_trailing_whitespace_in_multiline_string(self):
        line = 'x = """ \nhello"""    \n'
        fixed = 'x = """ \nhello"""\n'
        with autopep8_context(line) as result:
            self.assertEqual(fixed, result)

    def test_trailing_whitespace_in_multiline_string_aggressive(self):
        line = 'x = """ \nhello"""    \n'
        fixed = 'x = """\nhello"""\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(fixed, result)

    def test_execfile_in_lambda_should_not_be_modified(self):
        """Modifying this to the exec() form is invalid in Python 2."""
        line = 'lambda: execfile("foo.py")\n'
        with autopep8_context(line, options=['--aggressive']) as result:
            self.assertEqual(line, result)

    def test_range(self):
        line = 'print( 1 )\nprint( 2 )\n print( 3 )\n'
        fixed = 'print( 1 )\nprint(2)\n print( 3 )\n'
        with autopep8_context(line, options=['--range', '2', '2']) as result:
            self.assertEqual(fixed, result)

    def test_range_line_number_changes_from_one_line(self):
        line = 'a=12\na=1; b=2;c=3\nd=4;\n\ndef f(a = 1):\n    pass\n'
        fixed = 'a=12\na = 1\nb = 2\nc = 3\nd=4;\n\ndef f(a = 1):\n    pass\n'
        with autopep8_context(line, options=['--range', '2', '2']) as result:
            self.assertEqual(fixed, result)

    def test_range_indent_changes_large_range(self):
        line = '\nif True:\n  (1, \n    2,\n3)\nelif False:\n  a = 1\nelse:\n  a = 2\n\nc = 1\nif True:\n  c = 2\n  a = (1,\n2)\n'
        fixed0_9 = '\nif True:\n    (1,\n     2,\n     3)\nelif False:\n    a = 1\nelse:\n    a = 2\n\nc = 1\nif True:\n  c = 2\n  a = (1,\n2)\n'
        with autopep8_context(line, options=['--range', '1', '9']) as result:
            self.assertEqual(fixed0_9, result)

    def test_range_indent_changes_small_range(self):
        line = '\nif True:\n  (1, \n    2,\n3)\nelif False:\n  a = 1\nelse:\n  a = 2\n\nc = 1\nif True:\n  c = 2\n  a = (1,\n2)\n'
        fixed2_5 = '\nif True:\n  (1,\n   2,\n   3)\nelif False:\n  a = 1\nelse:\n  a = 2\n\nc = 1\nif True:\n  c = 2\n  a = (1,\n2)\n'
        with autopep8_context(line, options=['--range', '2', '5']) as result:
            self.assertEqual(fixed2_5, result)

    def test_range_indent_changes_multiline(self):
        line = '\nif True:\n  (1, \n    2,\n3)\nelif False:\n  a = 1\nelse:\n  a = 2\n\nc = 1\nif True:\n  c = 2\n  a = (1,\n2)\n'
        fixed_11_15 = '\nif True:\n  (1, \n    2,\n3)\nelif False:\n  a = 1\nelse:\n  a = 2\n\nc = 1\nif True:\n    c = 2\n    a = (1,\n         2)\n'
        with autopep8_context(line, options=['--range', '11', '15']) as result:
            self.assertEqual(fixed_11_15, result)

    def test_range_indent_changes_partial_multiline(self):
        line = '\nif True:\n  (1, \n    2,\n3)\nelif False:\n  a = 1\nelse:\n  a = 2\n\nc = 1\nif True:\n  c = 2\n  a = (1,\n2)\n'
        fixed_11_14 = '\nif True:\n  (1, \n    2,\n3)\nelif False:\n  a = 1\nelse:\n  a = 2\n\nc = 1\nif True:\n    c = 2\n    a = (1,\n2)\n'
        with autopep8_context(line, options=['--range', '11', '14']) as result:
            self.assertEqual(fixed_11_14, result)

    def test_range_indent_long_multiline_small_range(self):
        line = '\nif True:\n  (1,\n2,\n3,\n\n4,\n\n5,\n6)'
        fixed_2_3 = '\nif True:\n    (1,\n2,\n3,\n\n4,\n\n5,\n6)\n'
        with autopep8_context(line, options=['--range', '2', '3']) as result:
            self.assertEqual(fixed_2_3, result)

    def test_range_indent_long_multiline_partial_range(self):
        line = '\nif True:\n  (1,\n2,\n3,\n\n4,\n\n5,\n6)'
        fixed_2_6 = '\nif True:\n    (1,\n     2,\n     3,\n\n4,\n\n5,\n6)\n'
        with autopep8_context(line, options=['--range', '2', '6']) as result:
            self.assertEqual(fixed_2_6, result)

    def test_range_indent_long_multiline_middle_of_multiline(self):
        line = '\nif True:\n  (1,\n2,\n3,\n\n4,\n\n5,\n6)'
        # weird-ish edge case, fixes earlier lines (up to beginning of
        # multi-line block)
        fixed_2_6 = '\nif True:\n    (1,\n     2,\n     3,\n\n     4,\n\n5,\n6)\n'
        with autopep8_context(line, options=['--range', '4', '6']) as result:
            self.assertEqual(fixed_2_6, result)

    def test_range_indent_deep_if_blocks_first_block(self):
        line = '\nif a:\n  if a = 1:\n    b = 1\n  else:\n    b = 2\nelif a == 0:\n  b = 3\nelse:\n  b = 4\n'
        with autopep8_context(line, options=['--range', '2', '5']) as result:
            self.assertEqual(line, result)

    def test_range_indent_deep_if_blocks_large_range(self):
        line = '\nif a:\n  if a = 1:\n    b = 1\n  else:\n    b = 2\nelif a == 0:\n  b = 3\nelse:\n  b = 4\n'
        fixed_2_7 = '\nif a:\n  if a = 1:\n      b = 1\n  else:\n      b = 2\nelif a == 0:\n  b = 3\nelse:\n  b = 4\n'
        with autopep8_context(line, options=['--range', '2', '7']) as result:
            self.assertEqual(fixed_2_7, result)

    def test_range_indent_deep_if_blocks_second_block(self):
        line = '\nif a:\n  if a = 1:\n    b = 1\n  else:\n    b = 2\nelif a == 0:\n  b = 3\nelse:\n  b = 4\n'
        with autopep8_context(line, options=['--range', '6', '9']) as result:
            self.assertEqual(line, result)

    def test_range_indent_continued_statements(self):
        line = '\nif a == 1:\n\ttry:\n\t  foo\n\texcept AttributeError:\n\t  pass\n\telse:\n\t  "nooo"\n\tb = 1\n'
        fixed_2_8 = '\nif a == 1:\n\ttry:\n\t    foo\n\texcept AttributeError:\n\t    pass\n\telse:\n\t    "nooo"\n\tb = 1\n'
        with autopep8_context(line, options=['--range', '2', '8']) as result:
            self.assertEqual(fixed_2_8, result)

    def test_range_indent_continued_statements_partial(self):
        line = '\nif a == 1:\n\ttry:\n\t  foo\n\texcept AttributeError:\n\t  pass\n\telse:\n\t  "nooo"\n\tb = 1\n'
        with autopep8_context(line, options=['--range', '2', '6']) as result:
            self.assertEqual(line, result)

    def test_range_indent_continued_statements_last_block(self):
        line = '\nif a == 1:\n\ttry:\n\t  foo\n\texcept AttributeError:\n\t  pass\n\telse:\n\t  "nooo"\n\tb = 1\n'
        with autopep8_context(line, options=['--range', '6', '9']) as result:
            self.assertEqual(line, result)

    def test_range_indent_neighbouring_blocks(self):
        line = '\nif a == 1:\n  b = 1\nif a == 2:\n  b = 2\nif a == 3:\n  b = 3\n'
        fixed_2_3 = '\nif a == 1:\n    b = 1\nif a == 2:\n  b = 2\nif a == 3:\n  b = 3\n'
        with autopep8_context(line, options=['--range', '2', '3']) as result:
            self.assertEqual(fixed_2_3, result)

    def test_range_indent_neighbouring_blocks_one_line(self):
        line = '\nif a == 1:\n  b = 1\nif a == 2:\n  b = 2\nif a == 3:\n  b = 3\n'
        fixed_2_3 = '\nif a == 1:\n    b = 1\nif a == 2:\n  b = 2\nif a == 3:\n  b = 3\n'
        fixed_3_3 = fixed_2_3
        with autopep8_context(line, options=['--range', '3', '3']) as result:
            self.assertEqual(fixed_3_3, result)

    def test_range_indent_above_less_indented(self):
        line = '\ndef f(x):\n  if x:\n    return x\n'
        fixed_3_4 = '\ndef f(x):\n    if x:\n        return x\n'
        with autopep8_context(line, options=['--range', '3', '4']) as result:
            self.assertEqual(fixed_3_4, result)

    def test_range_indent_docstrings_partial(self):
        line = '\ndef f(x):\n  """docstring\n  docstring"""\n  #comment\n  if x:\n    return x\n'
        # TODO this should fix the comment spacing
        fixed_2_5 = '\ndef f(x):\n  """docstring\n  docstring"""\n  #comment\n  if x:\n    return x\n'
        with autopep8_context(line, options=['--range', '2', '5']) as result:
            self.assertEqual(fixed_2_5, result)

    def test_range_indent_docstrings(self):
        line = '\ndef f(x):\n  """docstring\n  docstring"""\n  #comment\n  if x:\n    return x\n'
        fixed_2_7 = '\ndef f(x):\n    """docstring\n    docstring"""\n    # comment\n    if x:\n        return x\n'
        with autopep8_context(line, options=['--range', '2', '7']) as result:
            self.assertEqual(fixed_2_7, result)

    def test_range_indent_multiline_strings(self):
        line = '\nif True:\n  a = """multi\nline\nstring"""\n  #comment\n  a=1\na=2\n'
        fixed_2_7 = '\nif True:\n    a = """multi\nline\nstring"""\n    # comment\n    a = 1\na=2\n'
        with autopep8_context(line, options=['--range', '2', '7']) as result:
            self.assertEqual(fixed_2_7, result)

    def test_range_with_broken_syntax(self):
        line = """\
if True:
   if True:
      pass
 else:
    pass
"""
        with autopep8_context(line, options=['--range', '1', '1']) as result:
            self.assertEqual(line, result)


class CommandLineTests(unittest.TestCase):

    maxDiff = None

    def test_diff(self):
        line = "'abc'  \n"
        fixed = "-'abc'  \n+'abc'\n"
        with autopep8_subprocess(line, ['--diff']) as result:
            self.assertEqual(fixed, '\n'.join(result.split('\n')[3:]))

    def test_diff_with_empty_file(self):
        with autopep8_subprocess('', ['--diff']) as result:
            self.assertEqual('\n'.join(result.split('\n')[3:]), '')

    def test_diff_with_nonexistent_file(self):
        p = Popen(list(AUTOPEP8_CMD_TUPLE) + ['--diff', 'non_existent_file'],
                  stdout=PIPE, stderr=PIPE)
        error = p.communicate()[1].decode('utf-8')
        self.assertIn('non_existent_file', error)

    def test_diff_with_standard_in(self):
        p = Popen(list(AUTOPEP8_CMD_TUPLE) + ['--diff', '-'],
                  stdout=PIPE, stderr=PIPE)
        error = p.communicate()[1].decode('utf-8')
        self.assertIn('cannot', error)

    def test_pep8_passes(self):
        line = "'abc'  \n"
        fixed = "'abc'\n"
        with autopep8_subprocess(line, ['--pep8-passes', '0']) as result:
            self.assertEqual(fixed, result)

    def test_pep8_ignore(self):
        line = "'abc'  \n"
        with autopep8_subprocess(line, ['--ignore=E,W']) as result:
            self.assertEqual(line, result)

    def test_help(self):
        p = Popen(list(AUTOPEP8_CMD_TUPLE) + ['-h'],
                  stdout=PIPE)
        self.assertIn('usage:', p.communicate()[0].decode('utf-8').lower())

    def test_verbose(self):
        line = 'bad_syntax)'
        with temporary_file_context(line) as filename:
            p = Popen(list(AUTOPEP8_CMD_TUPLE) + [filename, '-vvv'],
                      stdout=PIPE, stderr=PIPE)
            verbose_error = p.communicate()[1].decode('utf-8')
        self.assertIn("'fix_e901' is not defined", verbose_error)

    def test_verbose_diff(self):
        line = '+'.join(100 * ['323424234234'])
        with temporary_file_context(line) as filename:
            p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                      [filename, '-vvvv', '--diff'],
                      stdout=PIPE, stderr=PIPE)
            verbose_error = p.communicate()[1].decode('utf-8')
        self.assertIn('------------', verbose_error)

    def test_in_place(self):
        line = "'abc'  \n"
        fixed = "'abc'\n"

        with temporary_file_context(line) as filename:
            p = Popen(list(AUTOPEP8_CMD_TUPLE) + [filename, '--in-place'])
            p.wait()

            with open(filename) as f:
                self.assertEqual(fixed, f.read())

    def test_parallel_jobs(self):
        line = "'abc'  \n"
        fixed = "'abc'\n"

        with temporary_file_context(line) as filename_a:
            with temporary_file_context(line) as filename_b:
                p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                          [filename_a, filename_b, '--jobs=3', '--in-place'])
                p.wait()

                with open(filename_a) as f:
                    self.assertEqual(fixed, f.read())

                with open(filename_b) as f:
                    self.assertEqual(fixed, f.read())

    def test_parallel_jobs_with_automatic_cpu_count(self):
        line = "'abc'  \n"
        fixed = "'abc'\n"

        with temporary_file_context(line) as filename_a:
            with temporary_file_context(line) as filename_b:
                p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                          [filename_a, filename_b, '--jobs=0', '--in-place'])
                p.wait()

                with open(filename_a) as f:
                    self.assertEqual(fixed, f.read())

                with open(filename_b) as f:
                    self.assertEqual(fixed, f.read())

    def test_in_place_with_empty_file(self):
        line = ''

        with temporary_file_context(line) as filename:
            p = Popen(list(AUTOPEP8_CMD_TUPLE) + [filename, '--in-place'])
            p.wait()
            self.assertEqual(0, p.returncode)

            with open(filename) as f:
                self.assertEqual(f.read(), line)

    def test_in_place_and_diff(self):
        line = "'abc'  \n"
        with temporary_file_context(line) as filename:
            p = Popen(
                list(AUTOPEP8_CMD_TUPLE) + [filename,
                                            '--in-place', '--diff'],
                stderr=PIPE)
            result = p.communicate()[1].decode('utf-8')
        self.assertIn('--in-place and --diff are mutually exclusive', result)

    def test_recursive(self):
        temp_directory = tempfile.mkdtemp(dir='.')
        try:
            with open(os.path.join(temp_directory, 'a.py'), 'w') as output:
                output.write("'abc'  \n")

            os.mkdir(os.path.join(temp_directory, 'd'))
            with open(os.path.join(temp_directory, 'd', 'b.py'),
                      'w') as output:
                output.write('123  \n')

            p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                      [temp_directory, '--recursive', '--diff'],
                      stdout=PIPE)
            result = p.communicate()[0].decode('utf-8')

            self.assertEqual(
                "-'abc'  \n+'abc'",
                '\n'.join(result.split('\n')[3:5]))

            self.assertEqual(
                '-123  \n+123',
                '\n'.join(result.split('\n')[8:10]))
        finally:
            shutil.rmtree(temp_directory)

    def test_recursive_should_not_crash_on_unicode_filename(self):
        temp_directory = tempfile.mkdtemp(dir='.')
        try:
            for filename in ['x.py', 'é.py', 'é.txt']:
                with open(os.path.join(temp_directory, filename), 'w'):
                    pass

            p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                      [temp_directory,
                       '--recursive',
                       '--diff'],
                      stdout=PIPE)
            self.assertFalse(p.communicate()[0])
            self.assertEqual(0, p.returncode)
        finally:
            shutil.rmtree(temp_directory)

    def test_recursive_should_ignore_hidden(self):
        temp_directory = tempfile.mkdtemp(dir='.')
        temp_subdirectory = tempfile.mkdtemp(prefix='.', dir=temp_directory)
        try:
            with open(os.path.join(temp_subdirectory, 'a.py'), 'w') as output:
                output.write("'abc'  \n")

            p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                      [temp_directory, '--recursive', '--diff'],
                      stdout=PIPE)
            result = p.communicate()[0].decode('utf-8')

            self.assertEqual(0, p.returncode)
            self.assertEqual('', result)
        finally:
            shutil.rmtree(temp_directory)

    def test_exclude(self):
        temp_directory = tempfile.mkdtemp(dir='.')
        try:
            with open(os.path.join(temp_directory, 'a.py'), 'w') as output:
                output.write("'abc'  \n")

            os.mkdir(os.path.join(temp_directory, 'd'))
            with open(os.path.join(temp_directory, 'd', 'b.py'),
                      'w') as output:
                output.write('123  \n')

            p = Popen(list(AUTOPEP8_CMD_TUPLE) +
                      [temp_directory, '--recursive', '--exclude=a*',
                       '--diff'],
                      stdout=PIPE)
            result = p.communicate()[0].decode('utf-8')

            self.assertNotIn('abc', result)
            self.assertIn('123', result)
        finally:
            shutil.rmtree(temp_directory)

    def test_invalid_option_combinations(self):
        line = "'abc'  \n"
        with temporary_file_context(line) as filename:
            for options in [['--recursive', filename],  # without --diff
                            ['--jobs=2', filename],  # without --diff
                            ['--exclude=foo', filename],  # without --recursive
                            ['--max-line-length=0', filename],
                            [],  # no argument
                            ['-', '--in-place'],
                            ['-', '--recursive'],
                            ['-', filename],
                            ['--range', '0', '2', filename],
                            ['--range', '2', '1', filename],
                            ['--range', '-1', '-1', filename],
                            ]:
                p = Popen(list(AUTOPEP8_CMD_TUPLE) + options,
                          stderr=PIPE)
                result = p.communicate()[1].decode('utf-8')
                self.assertNotEqual(0, p.returncode, msg=str(options))
                self.assertTrue(len(result))

    def test_list_fixes(self):
        with autopep8_subprocess('', options=['--list-fixes']) as result:
            self.assertIn('E121', result)

    def test_fixpep8_class_constructor(self):
        line = 'print 1\nprint 2\n'
        with temporary_file_context(line) as filename:
            pep8obj = autopep8.FixPEP8(filename, None)
        self.assertEqual(''.join(pep8obj.source), line)

    def test_inplace_with_multi_files(self):
        exception = None
        with disable_stderr():
            try:
                autopep8.parse_args(['test.py', 'dummy.py'])
            except SystemExit as e:
                exception = e
        self.assertTrue(exception)
        self.assertEqual(exception.code, 2)

    def test_standard_out_should_use_native_line_ending(self):
        line = '1\r\n2\r\n3\r\n'
        with temporary_file_context(line) as filename:
            process = Popen(list(AUTOPEP8_CMD_TUPLE) +
                            [filename],
                            stdout=PIPE)
            self.assertEqual(
                os.linesep.join(['1', '2', '3', '']),
                process.communicate()[0].decode('utf-8'))

    def test_standard_out_should_use_native_line_ending_with_cr_input(self):
        line = '1\r2\r3\r'
        with temporary_file_context(line) as filename:
            process = Popen(list(AUTOPEP8_CMD_TUPLE) +
                            [filename],
                            stdout=PIPE)
            self.assertEqual(
                os.linesep.join(['1', '2', '3', '']),
                process.communicate()[0].decode('utf-8'))

    def test_standard_in(self):
        line = 'print( 1 )\n'
        fixed = 'print(1)' + os.linesep
        process = Popen(list(AUTOPEP8_CMD_TUPLE) +
                        ['-'],
                        stdout=PIPE,
                        stdin=PIPE)
        self.assertEqual(
            fixed,
            process.communicate(line.encode('utf-8'))[0].decode('utf-8'))


class ExperimentalSystemTests(unittest.TestCase):

    maxDiff = None

    def test_e501_experimental_basic(self):
        line = """\
print(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        fixed = """\
print(
    111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333,
    333, 333)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_commas_and_colons(self):
        line = """\
foobar = {'aaaaaaaaaaaa': 'bbbbbbbbbbbbbbbb', 'dddddd': 'eeeeeeeeeeeeeeee', 'ffffffffffff': 'gggggggg'}
"""
        fixed = """\
foobar = {
    'aaaaaaaaaaaa': 'bbbbbbbbbbbbbbbb', 'dddddd': 'eeeeeeeeeeeeeeee',
    'ffffffffffff': 'gggggggg'}
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_inline_comments(self):
        line = """\
'                                                          '  # Long inline comments should be moved above.
if True:
    '                                                          '  # Long inline comments should be moved above.
"""
        fixed = """\
# Long inline comments should be moved above.
'                                                          '
if True:
    # Long inline comments should be moved above.
    '                                                          '
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_inline_comments_should_skip_multiline(self):
        line = """\
'''This should be left alone. -----------------------------------------------------

'''  # foo

'''This should be left alone. -----------------------------------------------------

''' \\
# foo

'''This should be left alone. -----------------------------------------------------

''' \\
\\
# foo
"""
        fixed = """\
'''This should be left alone. -----------------------------------------------------

'''  # foo

'''This should be left alone. -----------------------------------------------------

'''  # foo

'''This should be left alone. -----------------------------------------------------

'''  # foo
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_inline_comments_should_skip_keywords(self):
        line = """\
'                                                          '  # noqa Long inline comments should be moved above.
if True:
    '                                                          '  # pylint: disable-msgs=E0001
    '                                                          '  # pragma: no cover
    '                                                          '  # pragma: no cover
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(line, result)

    def test_e501_experimental_with_inline_comments_should_skip_edge_cases(self):
        line = """\
if True:
    x = \\
        '                                                          '  # Long inline comments should be moved above.
"""
        fixed = """\
if True:
    # Long inline comments should be moved above.
    x = '                                                          '
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_basic_should_prefer_balanced_brackets(self):
        line = """\
if True:
    reconstructed = iradon(radon(image), filter="ramp", interpolation="nearest")
"""
        fixed = """\
if True:
    reconstructed = iradon(
        radon(image),
        filter="ramp", interpolation="nearest")
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_very_long_line(self):
        line = """\
x = [3244234243234, 234234234324, 234234324, 23424234, 234234234, 234234, 234243, 234243, 234234234324, 234234324, 23424234, 234234234, 234234, 234243, 234243]
"""
        fixed = """\
x = [
    3244234243234, 234234234324, 234234324, 23424234, 234234234, 234234,
    234243, 234243, 234234234324, 234234324, 23424234, 234234234, 234234,
    234243, 234243]
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_shorten_at_commas_skip(self):
        line = """\
parser.add_argument('source_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('target_corpus', help='corpus name/path relative to an nltk_data directory')
"""
        fixed = """\
parser.add_argument(
    'source_corpus',
    help='corpus name/path relative to an nltk_data directory')
parser.add_argument(
    'target_corpus',
    help='corpus name/path relative to an nltk_data directory')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_shorter_length(self):
        line = """\
foooooooooooooooooo('abcdefghijklmnopqrstuvwxyz')
"""
        fixed = """\
foooooooooooooooooo(
    'abcdefghijklmnopqrstuvwxyz')
"""
        with autopep8_context(line,
                              options=['--max-line-length=40',
                                       '--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_indent(self):
        line = """\

def d():
    print(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        fixed = """\

def d():
    print(
        111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333,
        333, 333, 333)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_alone_with_indentation(self):
        line = """\
if True:
    print(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333, 333, 333)
"""
        fixed = """\
if True:
    print(
        111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333,
        333, 333, 333)
"""
        with autopep8_context(line, options=['--select=E501',
                                             '--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_alone_with_tuple(self):
        line = """\
fooooooooooooooooooooooooooooooo000000000000000000000000 = [1,
                                                            ('TransferTime', 'FLOAT')
                                                           ]
"""
        fixed = """\
fooooooooooooooooooooooooooooooo000000000000000000000000 = [
    1, ('TransferTime', 'FLOAT')]
"""
        with autopep8_context(line, options=['--select=E501',
                                             '--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_should_not_try_to_break_at_every_paren_in_arithmetic(self):
        line = """\
term3 = w6 * c5 * (8.0 * psi4 * (11.0 - 24.0 * t2) - 28 * psi3 * (1 - 6.0 * t2) + psi2 * (1 - 32 * t2) - psi * (2.0 * t2) + t4) / 720.0
this_should_be_shortened = ('                                                                 ', '            ')
"""
        fixed = """\
term3 = w6 * c5 * (
    8.0 * psi4 * (11.0 - 24.0 * t2) - 28 * psi3 * (1 - 6.0 * t2) + psi2 *
    (1 - 32 * t2) - psi * (2.0 * t2) + t4) / 720.0
this_should_be_shortened = (
    '                                                                 ',
    '            ')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_arithmetic_operator_with_indent(self):
        line = """\
def d():
    111 + 111 + 111 + 111 + 111 + 222 + 222 + 222 + 222 + 222 + 222 + 222 + 222 + 222 + 333 + 333 + 333 + 333
"""
        fixed = """\
def d():
    111 + 111 + 111 + 111 + 111 + 222 + 222 + 222 + 222 + \\
        222 + 222 + 222 + 222 + 222 + 333 + 333 + 333 + 333
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_more_complicated(self):
        line = """\
blahblah = os.environ.get('blahblah') or os.environ.get('blahblahblah') or os.environ.get('blahblahblahblah')
"""
        fixed = """\
blahblah = os.environ.get('blahblah') or os.environ.get(
    'blahblahblah') or os.environ.get('blahblahblahblah')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_skip_even_more_complicated(self):
        line = """\
if True:
    if True:
        if True:
            blah = blah.blah_blah_blah_bla_bl(blahb.blah, blah.blah,
                                              blah=blah.label, blah_blah=blah_blah,
                                              blah_blah2=blah_blah)
"""
        fixed = """\
if True:
    if True:
        if True:
            blah = blah.blah_blah_blah_bla_bl(
                blahb.blah, blah.blah, blah=blah.label, blah_blah=blah_blah,
                blah_blah2=blah_blah)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_prefer_to_break_at_beginning(self):
        """We prefer not to leave part of the arguments hanging."""
        line = """\
looooooooooooooong = foo(one, two, three, four, five, six, seven, eight, nine, ten)
"""
        fixed = """\
looooooooooooooong = foo(
    one, two, three, four, five, six, seven, eight, nine, ten)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_logical_fix(self):
        line = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        fixed = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_logical_fix_and_physical_fix(self):
        line = """\
# ------ ------------------------------------------------------------------------
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        fixed = """\
# ------ -----------------------------------------------------------------
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_logical_fix_and_adjacent_strings(self):
        line = """\
print('a-----------------------' 'b-----------------------' 'c-----------------------'
      'd-----------------------''e'"f"r"g")
"""
        fixed = """\
print(
    'a-----------------------'
    'b-----------------------'
    'c-----------------------'
    'd-----------------------'
    'e'
    "f"
    r"g")
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_multiple_lines(self):
        line = """\
foo_bar_zap_bing_bang_boom(111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333,
                           111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333)
"""
        fixed = """\
foo_bar_zap_bing_bang_boom(
    111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333,
    111, 111, 111, 111, 222, 222, 222, 222, 222, 222, 222, 222, 222, 333, 333)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_do_not_break_on_keyword(self):
        # We don't want to put a newline after equals for keywords as this
        # violates PEP 8.
        line = """\
if True:
    long_variable_name = tempfile.mkstemp(prefix='abcdefghijklmnopqrstuvwxyz0123456789')
"""
        fixed = """\
if True:
    long_variable_name = tempfile.mkstemp(
        prefix='abcdefghijklmnopqrstuvwxyz0123456789')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_do_not_begin_line_with_comma(self):
        line = """\
def dummy():
    if True:
        if True:
            if True:
                object = ModifyAction( [MODIFY70.text, OBJECTBINDING71.text, COLON72.text], MODIFY70.getLine(), MODIFY70.getCharPositionInLine() )
"""
        fixed = """\
def dummy():
    if True:
        if True:
            if True:
                object = ModifyAction(
                    [MODIFY70.text, OBJECTBINDING71.text, COLON72.text],
                    MODIFY70.getLine(),
                    MODIFY70.getCharPositionInLine())
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_should_not_break_on_dot(self):
        line = """\
if True:
    if True:
        raise xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx('xxxxxxxxxxxxxxxxx "{d}" xxxxxxxxxxxxxx'.format(d='xxxxxxxxxxxxxxx'))
"""
        fixed = """\
if True:
    if True:
        raise xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx(
            'xxxxxxxxxxxxxxxxx "{d}" xxxxxxxxxxxxxx'.format(
                d='xxxxxxxxxxxxxxx'))
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_comment(self):
        line = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        pass

# http://foo.bar/abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-

# The following is ugly commented-out code and should not be touched.
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx = 1
"""
        fixed = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will
                        # wrap it using textwrap to be within 72 characters.
                        pass

# http://foo.bar/abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-abc-

# The following is ugly commented-out code and should not be touched.
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx = 1
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_comment_should_not_modify_docstring(self):
        line = '''\
def foo():
    """
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
    """
'''
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(line, result)

    def test_e501_experimental_should_only_modify_last_comment(self):
        line = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 1. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 2. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 3. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
"""
        fixed = """123
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        # This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 1. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 2. This is a long comment that should be wrapped. I will wrap it using textwrap to be within 72 characters.
                        # 3. This is a long comment that should be wrapped. I
                        # will wrap it using textwrap to be within 72
                        # characters.
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_should_not_interfere_with_non_comment(self):
        line = '''
"""
# not actually a comment %d. 12345678901234567890, 12345678901234567890, 12345678901234567890.
""" % (0,)
'''
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(line, result)

    def test_e501_experimental_should_cut_comment_pattern(self):
        line = """123
# -- Useless lines ----------------------------------------------------------------------
321
"""
        fixed = """123
# -- Useless lines -------------------------------------------------------
321
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_function_should_not_break_on_colon(self):
        line = r"""
class Useless(object):

    def _table_field_is_plain_widget(self, widget):
        if widget.__class__ == Widget or\
                (widget.__class__ == WidgetMeta and Widget in widget.__bases__):
            return True

        return False
"""
        fixed = r"""
class Useless(object):

    def _table_field_is_plain_widget(self, widget):
        if widget.__class__ == Widget or(
                widget.__class__ == WidgetMeta and Widget in widget.__bases__):
            return True

        return False
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_experimental(self):
        # FIXME: This has really bad output.
        line = """\
models = {
    'auth.group': {
        'Meta': {'object_name': 'Group'},
        'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
    },
    'auth.permission': {
        'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
        'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
    },
}
"""
        fixed = """\
models = {
    'auth.group':
    {'Meta': {'object_name': 'Group'},
     'permissions':
     ('django.db.models.fields.related.ManyToManyField', [],
      {'to': "orm['auth.Permission']", 'symmetrical': 'False',
       'blank': 'True'})},
    'auth.permission':
    {
        'Meta':
        {
            'ordering':
            "('content_type__app_label', 'content_type__model', 'codename')",
            'unique_together': "(('content_type', 'codename'),)",
            'object_name': 'Permission'},
        'name': ('django.db.models.fields.CharField', [],
                 {'max_length': '50'})}, }
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_and_multiple_logical_lines(self):
        line = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(aaaaaaaaaaaaaaaaaaaaaaa,
                             bbbbbbbbbbbbbbbbbbbbbbbbbbbb, cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        fixed = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
xxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    aaaaaaaaaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbbbbbbbbbbbbbb,
    cccccccccccccccccccccccccccc, dddddddddddddddddddddddd)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_and_multiple_logical_lines_with_math(self):
        line = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx([-1 + 5 / -10,
                                                                            100,
                                                                            -3 - 4])
"""
        fixed = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx(
    [-1 + 5 / -10, 100, -3 - 4])
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_and_import(self):
        line = """\
from . import (xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,
               yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy)
"""
        fixed = """\
from . import (
    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx,
    yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_shorten_comment_with_experimental(self):
        line = """\
# ------ -------------------------------------------------------------------------
"""
        fixed = """\
# ------ -----------------------------------------------------------------
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_experimental_and_escaped_newline(self):
        line = """\
if True or \\
    False:  # test test test test test test test test test test test test test test
    pass
"""
        fixed = """\
# test test test test test test test test test test test test test test
if True or False:
    pass
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_experimental_and_multiline_string(self):
        line = """\
print('---------------------------------------------------------------------',
      ('================================================', '====================='),
      '''--------------------------------------------------------------------------------
      ''')
"""
        fixed = """\
print(
    '---------------------------------------------------------------------',
    ('================================================',
     '====================='),
    '''--------------------------------------------------------------------------------
      ''')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_experimental_and_multiline_string_with_addition(self):
        line = '''\
def f():
    email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>"""+despot["Nicholas"]+"""<br>
<b>Minion: </b>"""+serf["Dmitri"]+"""<br>
<b>Residence: </b>"""+palace["Winter"]+"""<br>
</body>
</html>"""
'''
        fixed = '''\
def f():
    email_text += """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>""" + despot["Nicholas"] + """<br>
<b>Minion: </b>""" + serf["Dmitri"] + """<br>
<b>Residence: </b>""" + palace["Winter"] + """<br>
</body>
</html>"""
'''
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_experimental_and_multiline_string_in_parens(self):
        line = '''\
def f():
    email_text += ("""<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>"""+despot["Nicholas"]+"""<br>
<b>Minion: </b>"""+serf["Dmitri"]+"""<br>
<b>Residence: </b>"""+palace["Winter"]+"""<br>
</body>
</html>""")
'''
        fixed = '''\
def f():
    email_text += (
        """<html>This is a really long docstring that goes over the column limit and is multi-line.<br><br>
<b>Czar: </b>""" + despot["Nicholas"] + """<br>
<b>Minion: </b>""" + serf["Dmitri"] + """<br>
<b>Residence: </b>""" + palace["Winter"] + """<br>
</body>
</html>""")
'''
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_experimental_and_indentation(self):
        line = """\
if True:
    # comment here
    print(aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
          bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,cccccccccccccccccccccccccccccccccccccccccc)
"""
        fixed = """\
if True:
    # comment here
    print(
        aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
        bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,
        cccccccccccccccccccccccccccccccccccccccccc)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_multiple_keys_and_experimental(self):
        line = """\
one_two_three_four_five_six = {'one two three four five': 12345, 'asdfsdflsdkfjl sdflkjsdkfkjsfjsdlkfj sdlkfjlsfjs': '343',
                               1: 1}
"""
        fixed = """\
one_two_three_four_five_six = {
    'one two three four five': 12345,
    'asdfsdflsdkfjl sdflkjsdkfkjsfjsdlkfj sdlkfjlsfjs': '343', 1: 1}
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_with_experimental_and_carriage_returns_only(self):
        """Make sure _find_logical() does not crash."""
        line = 'if True:\r    from aaaaaaaaaaaaaaaa import bbbbbbbbbbbbbbbbbbb\r    \r    ccccccccccc = None\r'
        fixed = 'if True:\r    from aaaaaaaaaaaaaaaa import bbbbbbbbbbbbbbbbbbb\r\r    ccccccccccc = None\r'
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_should_ignore_imports(self):
        line = """\
import logging, os, bleach, commonware, urllib2, json, time, requests, urlparse, re
"""
        with autopep8_context(line, options=['--select=E501',
                                             '--experimental']) as result:
            self.assertEqual(line, result)

    def test_e501_experimental_should_not_do_useless_things(self):
        line = """\
foo('                                                                            ')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(line, result)

    def test_e501_experimental_with_percent(self):
        line = """\
raise MultiProjectException("Ambiguous workspace: %s=%s, %s" % ( varname, varname_path, os.path.abspath(config_filename)))
"""
        fixed = """\
raise MultiProjectException(
    "Ambiguous workspace: %s=%s, %s" %
    (varname, varname_path, os.path.abspath(config_filename)))
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_def(self):
        line = """\
def foobar(sldfkjlsdfsdf, kksdfsdfsf,sdfsdfsdf, sdfsdfkdk, szdfsdfsdf, sdfsdfsdfsdlkfjsdlf, sdfsdfddf,sdfsdfsfd, sdfsdfdsf):
    pass
"""
        fixed = """\


def foobar(
        sldfkjlsdfsdf, kksdfsdfsf, sdfsdfsdf, sdfsdfkdk, szdfsdfsdf,
        sdfsdfsdfsdlkfjsdlf, sdfsdfddf, sdfsdfsfd, sdfsdfdsf):
    pass
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_tuple(self):
        line = """\
def f():
    man_this_is_a_very_long_function_name(an_extremely_long_variable_name,
                                          ('a string that is long: %s'%'bork'))
"""
        fixed = """\
def f():
    man_this_is_a_very_long_function_name(
        an_extremely_long_variable_name,
        ('a string that is long: %s' % 'bork'))
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_tuple_in_list(self):
        line = """\
def f(self):
    self._xxxxxxxx(aaaaaa, bbbbbbbbb, cccccccccccccccccc,
                   [('mmmmmmmmmm', self.yyyyyyyyyy.zzzzzzz/_DDDDD)], eee, 'ff')
"""
        fixed = """\
def f(self):
    self._xxxxxxxx(
        aaaaaa, bbbbbbbbb, cccccccccccccccccc,
        [('mmmmmmmmmm', self.yyyyyyyyyy.zzzzzzz / _DDDDD)],
        eee, 'ff')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    @unittest.skipIf(sys.version_info < (2, 7),
                     'Python 2.6 does not support dictionary comprehensions')
    def test_e501_experimental_with_complex_reformat(self):
        line = """\
bork(111, 111, 111, 111, 222, 222, 222, { 'foo': 222, 'qux': 222 }, ((['hello', 'world'], ['yo', 'stella', "how's", 'it'], ['going']), {str(i): i for i in range(10)}, {'bork':((x, x**x) for x in range(10))}), 222, 222, 222, 222, 333, 333, 333, 333)
"""
        fixed = """\
bork(
    111, 111, 111, 111, 222, 222, 222, {'foo': 222, 'qux': 222},
    ((['hello', 'world'],
      ['yo', 'stella', "how's", 'it'],
      ['going']),
     {str(i): i for i in range(10)},
     {'bork': ((x, x ** x) for x in range(10))}),
    222, 222, 222, 222, 333, 333, 333, 333)
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_multiple_lines_and_quotes(self):
        line = """\
if True:
    xxxxxxxxxxx = xxxxxxxxxxxxxxxxx(xxxxxxxxxxx, xxxxxxxxxxxxxxxx={'xxxxxxxxxxxx': 'xxxxx',
                                                                   'xxxxxxxxxxx': xx,
                                                                   'xxxxxxxx': False,
                                                                   })
"""
        fixed = """\
if True:
    xxxxxxxxxxx = xxxxxxxxxxxxxxxxx(
        xxxxxxxxxxx,
        xxxxxxxxxxxxxxxx={'xxxxxxxxxxxx': 'xxxxx', 'xxxxxxxxxxx': xx,
                          'xxxxxxxx': False, })
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_dot_calls(self):
        line = """\
if True:
    logging.info('aaaaaa bbbbb dddddd ccccccc eeeeeee fffffff gg: %s',
        xxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyy(zzzzzzzzzzzzzzzzz.jjjjjjjjjjjjjjjjj()))
"""
        fixed = """\
if True:
    logging.info(
        'aaaaaa bbbbb dddddd ccccccc eeeeeee fffffff gg: %s',
        xxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyy(
            zzzzzzzzzzzzzzzzz.jjjjjjjjjjjjjjjjj()))
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_avoid_breaking_at_empty_parentheses_if_possible(self):
        line = """\
someverylongindenttionwhatnot().foo().bar().baz("and here is a long string 123456789012345678901234567890")
"""
        fixed = """\
someverylongindenttionwhatnot().foo().bar().baz(
    "and here is a long string 123456789012345678901234567890")
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_unicode(self):
        line = """\
someverylongindenttionwhatnot().foo().bar().baz("and here is a l안녕하세요 123456789012345678901234567890")
"""
        fixed = """\
someverylongindenttionwhatnot().foo().bar().baz(
    "and here is a l안녕하세요 123456789012345678901234567890")
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_with_tuple_assignment(self):
        line = """\
if True:
    (xxxxxxx,) = xxxx.xxxxxxx.xxxxx(xxxxxxxxxxxx.xx).xxxxxx(xxxxxxxxxxxx.xxxx == xxxx.xxxx).xxxxx()
"""
        fixed = """\
if True:
    (xxxxxxx,) = xxxx.xxxxxxx.xxxxx(xxxxxxxxxxxx.xx).xxxxxx(
        xxxxxxxxxxxx.xxxx == xxxx.xxxx).xxxxx()
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_tuple_on_line(self):
        line = """\
def f():
    self.aaaaaaaaa(bbbbbb, ccccccccc, dddddddddddddddd,
                   ((x, y/eeeeeee) for x, y in self.outputs.total.iteritems()),
                   fff, 'GG')
"""
        fixed = """\
def f():
    self.aaaaaaaaa(
        bbbbbb, ccccccccc, dddddddddddddddd,
        ((x, y / eeeeeee) for x, y in self.outputs.total.iteritems()),
        fff, 'GG')
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_tuple_on_line_two_space_indent(self):
        line = """\
def f():
  self.aaaaaaaaa(bbbbbb, ccccccccc, dddddddddddddddd,
                 ((x, y/eeeeeee) for x, y in self.outputs.total.iteritems()),
                 fff, 'GG')
"""
        fixed = """\
def f():
  self.aaaaaaaaa(bbbbbb, ccccccccc, dddddddddddddddd,
                 ((x, y / eeeeeee) for x, y in self.outputs.total.iteritems()),
                 fff, 'GG')
"""
        with autopep8_context(line, options=['--experimental',
                                             '--indent-size=2']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_oversized_default_initializer(self):
        line = """\
aaaaaaaaaaaaaaaaaaaaa(lllll,mmmmmmmm,nnn,fffffffffff,ggggggggggg,hhh,ddddddddddddd=eeeeeeeee,bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb=ccccccccccccccccccccccccccccccccccccccccccccccccc,bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb=cccccccccccccccccccccccccccccccccccccccccccccccc)
"""
        fixed = """\
aaaaaaaaaaaaaaaaaaaaa(
    lllll, mmmmmmmm, nnn, fffffffffff, ggggggggggg, hhh,
    ddddddddddddd=eeeeeeeee,
    bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb=ccccccccccccccccccccccccccccccccccccccccccccccccc,
    bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb=cccccccccccccccccccccccccccccccccccccccccccccccc)
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_decorator(self):
        line = """\
@foo(('xxxxxxxxxxxxxxxxxxxxxxxxxx', users.xxxxxxxxxxxxxxxxxxxxxxxxxx), ('yyyyyyyyyyyy', users.yyyyyyyyyyyy), ('zzzzzzzzzzzzzz', users.zzzzzzzzzzzzzz))
"""
        fixed = """\


@foo(
    ('xxxxxxxxxxxxxxxxxxxxxxxxxx', users.xxxxxxxxxxxxxxxxxxxxxxxxxx),
    ('yyyyyyyyyyyy', users.yyyyyyyyyyyy),
    ('zzzzzzzzzzzzzz', users.zzzzzzzzzzzzzz))
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_long_class_name(self):
        line = """\
class AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA(BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB):
    pass
"""
        fixed = """\
class AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA(
        BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB):
    pass
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_no_line_change(self):
        line = """\
    return '<a href="javascript:;" class="copy-to-clipboard-button" data-clipboard-text="%s" title="copy url to clipboard">Copy Link</a>' % url
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(line, result)

    def test_e501_experimental_splitting_small_arrays(self):
        line = """\
def foo():
    unspecified[service] = ('# The %s brown fox jumped over the lazy, good for nothing '
                            'dog until it grew tired and set its sights upon the cat!' % adj)
"""
        fixed = """\
def foo():
    unspecified[service] = (
        '# The %s brown fox jumped over the lazy, good for nothing '
        'dog until it grew tired and set its sights upon the cat!' % adj)
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_no_splitting_in_func_call(self):
        line = """\
def foo():
    if True:
        if True:
            function.calls('%r (%s): aaaaaaaa bbbbbbbbbb ccccccc ddddddd eeeeee (%d, %d)',
                           xxxxxx.yy, xxxxxx.yyyy, len(mmmmmmmmmmmmm['fnord']),
                           len(mmmmmmmmmmmmm['asdfakjhdsfkj']))
"""
        fixed = """\
def foo():
    if True:
        if True:
            function.calls(
                '%r (%s): aaaaaaaa bbbbbbbbbb ccccccc ddddddd eeeeee (%d, %d)',
                xxxxxx.yy, xxxxxx.yyyy, len(mmmmmmmmmmmmm['fnord']),
                len(mmmmmmmmmmmmm['asdfakjhdsfkj']))
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_no_splitting_at_dot(self):
        line = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx = [yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.MMMMMM_NNNNNNN_OOOOO,
                                yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.PPPPPP_QQQQQQQ_RRRRR,
                                yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.SSSSSS_TTTTTTT_UUUUU]
"""
        fixed = """\
xxxxxxxxxxxxxxxxxxxxxxxxxxxx = [
    yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.MMMMMM_NNNNNNN_OOOOO,
    yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.PPPPPP_QQQQQQQ_RRRRR,
    yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.SSSSSS_TTTTTTT_UUUUU]
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_no_splitting_before_arg_list(self):
        line = """\
xxxxxxxxxxxx = [yyyyyy['yyyyyy'].get('zzzzzzzzzzz') for yyyyyy in x.get('aaaaaaaaaaa') if yyyyyy['yyyyyy'].get('zzzzzzzzzzz')]
"""
        fixed = """\
xxxxxxxxxxxx = [yyyyyy['yyyyyy'].get('zzzzzzzzzzz')
                for yyyyyy in x.get('aaaaaaaaaaa')
                if yyyyyy['yyyyyy'].get('zzzzzzzzzzz')]
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_dont_split_if_looks_bad(self):
        line = """\
def f():
    if True:
        BAD(('xxxxxxxxxxxxx', 42), 'I died for beauty, but was scarce / Adjusted in the tomb %s', yyyyyyyyyyyyy)
"""
        fixed = """\
def f():
    if True:
        BAD(('xxxxxxxxxxxxx', 42),
            'I died for beauty, but was scarce / Adjusted in the tomb %s',
            yyyyyyyyyyyyy)
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_list_comp(self):
        line = """\
xxxxxxxxxxxs = [xxxxxxxxxxx for xxxxxxxxxxx in xxxxxxxxxxxs if not yyyyyyyyyyyy[xxxxxxxxxxx] or not yyyyyyyyyyyy[xxxxxxxxxxx].zzzzzzzzzz]
"""
        fixed = """\
xxxxxxxxxxxs = [
    xxxxxxxxxxx for xxxxxxxxxxx in xxxxxxxxxxxs
    if not yyyyyyyyyyyy[xxxxxxxxxxx] or
    not yyyyyyyyyyyy[xxxxxxxxxxx].zzzzzzzzzz]
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

        line = """\
def f():
    xxxxxxxxxx = [f for f in yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.zzzzzzzzzzzzzzzzzzzzzzzz.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]
"""
        fixed = """\
def f():
    xxxxxxxxxx = [
        f
        for f in
        yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.zzzzzzzzzzzzzzzzzzzzzzzz.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa]
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_dict(self):
        line = """\
def f():
    zzzzzzzzzzzzz = {
        'aaaaaa/bbbbbb/ccccc/dddddddd/eeeeeeeee/fffffffffff/ggggggggg/hhhhhhhh.py':
            yyyyyyyyyyy.xxxxxxxxxxx(
                'aa/bbbbbbb/cc/ddddddd/eeeeeeeeeee/fffffffffff/ggggggggg/hhhhhhh/ggggg.py',
                '00000000',
                yyyyyyyyyyy.xxxxxxxxx.zzzz),
    }
"""
        fixed = """\
def f():
    zzzzzzzzzzzzz = {
        'aaaaaa/bbbbbb/ccccc/dddddddd/eeeeeeeee/fffffffffff/ggggggggg/hhhhhhhh.py':
        yyyyyyyyyyy.xxxxxxxxxxx(
            'aa/bbbbbbb/cc/ddddddd/eeeeeeeeeee/fffffffffff/ggggggggg/hhhhhhh/ggggg.py',
            '00000000', yyyyyyyyyyy.xxxxxxxxx.zzzz), }
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_indentation(self):
        line = """\
class Klass(object):

    '''Class docstring.'''

    def Quote(self, parameter_1, parameter_2, parameter_3, parameter_4, parameter_5):
        pass
"""
        fixed = """\
class Klass(object):

  '''Class docstring.'''

  def Quote(
      self, parameter_1, parameter_2, parameter_3, parameter_4,
          parameter_5):
    pass
"""

        with autopep8_context(line, options=['--experimental',
                                             '--indent-size=2']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_long_function_call_elements(self):
        line = """\
def g():
    pppppppppppppppppppppppppp1, pppppppppppppppppppppppp2 = (
        zzzzzzzzzzzz.yyyyyyyyyyyyyy(aaaaaaaaa=10, bbbbbbbbbbbbbbbb='2:3',
                                    cccccccc='{1:2}', dd=1, eeeee=0),
        zzzzzzzzzzzz.yyyyyyyyyyyyyy(dd=7, aaaaaaaaa=16, bbbbbbbbbbbbbbbb='2:3',
                                    cccccccc='{1:2}',
                                    eeeee=xxxxxxxxxxxxxxxxx.wwwwwwwwwwwww.vvvvvvvvvvvvvvvvvvvvvvvvv))
"""
        fixed = """\
def g():
    pppppppppppppppppppppppppp1, pppppppppppppppppppppppp2 = (
        zzzzzzzzzzzz.yyyyyyyyyyyyyy(
            aaaaaaaaa=10, bbbbbbbbbbbbbbbb='2:3', cccccccc='{1:2}', dd=1,
            eeeee=0),
        zzzzzzzzzzzz.yyyyyyyyyyyyyy(
            dd=7, aaaaaaaaa=16, bbbbbbbbbbbbbbbb='2:3', cccccccc='{1:2}',
            eeeee=xxxxxxxxxxxxxxxxx.wwwwwwwwwwwww.vvvvvvvvvvvvvvvvvvvvvvvvv))
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_long_nested_tuples_in_arrays(self):
        line = """\
def f():
    aaaaaaaaaaa.bbbbbbb([
        ('xxxxxxxxxx', 'yyyyyy', 'Heaven hath no wrath like love to hatred turned. Nor hell a fury like a woman scorned.'),
        ('xxxxxxx', 'yyyyyyyyyyy', "To the last I grapple with thee. From hell's heart I stab at thee. For hate's sake I spit my last breath at thee!")])
"""
        fixed = """\
def f():
    aaaaaaaaaaa.bbbbbbb(
        [('xxxxxxxxxx', 'yyyyyy',
          'Heaven hath no wrath like love to hatred turned. Nor hell a fury like a woman scorned.'),
         ('xxxxxxx', 'yyyyyyyyyyy',
          "To the last I grapple with thee. From hell's heart I stab at thee. For hate's sake I spit my last breath at thee!")])
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_func_call_open_paren_not_separated(self):
        # Don't separate the opening paren of a function call from the
        # function's name.
        line = """\
def f():
    owned_list = [o for o in owned_list if self.display['zzzzzzzzzzzzzz'] in aaaaaaaaaaaaaaaaa.bbbbbbbbbbbbbbbbbbbb(o.qq, ccccccccccccccccccccccccccc.ddddddddd.eeeeeee)]
"""
        fixed = """\
def f():
    owned_list = [
        o for o in owned_list
        if self.display['zzzzzzzzzzzzzz'] in aaaaaaaaaaaaaaaaa.bbbbbbbbbbbbbbbbbbbb(
            o.qq, ccccccccccccccccccccccccccc.ddddddddd.eeeeeee)]
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_long_dotted_object(self):
        # Don't separate a long dotted object too soon. Otherwise, it may end
        # up with most of its elements on separate lines.
        line = """\
def f(self):
  return self.xxxxxxxxxxxxxxx(aaaaaaa.bbbbb.ccccccc.ddd.eeeeee.fffffffff.ggggg.hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh)
"""
        fixed = """\
def f(self):
    return self.xxxxxxxxxxxxxxx(
        aaaaaaa.bbbbb.ccccccc.ddd.eeeeee.fffffffff.ggggg.
        hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh)
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_parsing_dict_with_comments(self):
        line = """\
self.display['xxxxxxxxxxxx'] = [{'title': _('Library'),  #. This is the first comment.
    'flag': aaaaaaaaaa.bbbbbbbbb.cccccccccc
    }, {'title': _('Original'),  #. This is the second comment.
    'flag': aaaaaaaaaa.bbbbbbbbb.dddddddddd
    }, {'title': _('Unknown'),  #. This is the third comment.
    'flag': aaaaaaaaaa.bbbbbbbbb.eeeeeeeeee}]
"""
        fixed = """\
self.display['xxxxxxxxxxxx'] = [{'title': _('Library'),  # . This is the first comment.
                                 'flag': aaaaaaaaaa.bbbbbbbbb.cccccccccc
                                 # . This is the second comment.
                                 }, {'title': _('Original'),
                                     'flag': aaaaaaaaaa.bbbbbbbbb.dddddddddd
                                     # . This is the third comment.
                                     }, {'title': _('Unknown'),
                                         'flag': aaaaaaaaaa.bbbbbbbbb.eeeeeeeeee}]
"""

        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)

    def test_e501_experimental_if_line_over_limit(self):
        line = """\
if not xxxxxxxxxxxx(aaaaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbb, cccccccccccccc, dddddddddddddddddddddd):
    return 1
"""
        fixed = """\
if not xxxxxxxxxxxx(
        aaaaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbb, cccccccccccccc,
        dddddddddddddddddddddd):
    return 1
"""
        with autopep8_context(line, options=['--experimental']) as result:
            self.assertEqual(fixed, result)


@contextlib.contextmanager
def autopep8_context(line, options=None):
    if not options:
        options = []

    with temporary_file_context(line) as filename:
        options = autopep8.parse_args([filename] + list(options))
        yield autopep8.fix_file(filename=filename, options=options)


@contextlib.contextmanager
def autopep8_subprocess(line, options):
    with temporary_file_context(line) as filename:
        p = Popen(list(AUTOPEP8_CMD_TUPLE) + [filename] + options,
                  stdout=PIPE)
        yield p.communicate()[0].decode('utf-8')


@contextlib.contextmanager
def temporary_file_context(text, suffix='', prefix=''):
    temporary = mkstemp(suffix=suffix, prefix=prefix)
    os.close(temporary[0])
    with autopep8.open_with_encoding(temporary[1],
                                     encoding='utf-8',
                                     mode='w') as temp_file:
        temp_file.write(text)
    yield temporary[1]
    os.remove(temporary[1])


@contextlib.contextmanager
def disable_stderr():
    sio = StringIO()
    with capture_stderr(sio):
        yield


@contextlib.contextmanager
def capture_stderr(sio):
    _tmp = sys.stderr
    sys.stderr = sio
    try:
        yield
    finally:
        sys.stderr = _tmp


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_suite
#!/usr/bin/env python

"""Run autopep8 against test file and check against expected output."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import sys

ROOT_DIR = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]

sys.path.insert(0, ROOT_DIR)
import autopep8


if sys.stdout.isatty():
    GREEN = '\x1b[32m'
    RED = '\x1b[31m'
    END = '\x1b[0m'
else:
    GREEN = ''
    RED = ''
    END = ''


def check(expected_filename, input_filename, aggressive):
    """Test and compare output.

    Return True on success.

    """
    got = autopep8.fix_file(
        input_filename,
        options=autopep8.parse_args([''] + aggressive * ['--aggressive']))

    try:
        with autopep8.open_with_encoding(expected_filename) as expected_file:
            expected = expected_file.read()
    except IOError:
        expected = None

    if expected == got:
        return True
    else:
        got_filename = expected_filename + '.err'
        encoding = autopep8.detect_encoding(input_filename)

        with autopep8.open_with_encoding(got_filename,
                                         encoding=encoding,
                                         mode='w') as got_file:
            got_file.write(got)

        print(
            '{begin}{got} does not match expected {expected}{end}'.format(
                begin=RED,
                got=got_filename,
                expected=expected_filename,
                end=END),
            file=sys.stdout)

        return False


def run(filename, aggressive):
    """Test against a specific file.

    Return True on success.

    Expected output should have the same base filename, but live in an "out"
    directory:

        foo/bar.py
        foo/out/bar.py

    Failed output will go to:

        foo/out/bar.py.err

    """
    return check(
        expected_filename=os.path.join(
            os.path.dirname(filename),
            'out',
            os.path.basename(filename)
        ),
        input_filename=filename,
        aggressive=aggressive
    )


def suite(aggressive):
    """Run against pep8 test suite."""
    result = True
    path = os.path.join(os.path.dirname(__file__), 'suite')
    for filename in os.listdir(path):
        filename = os.path.join(path, filename)

        if filename.endswith('.py'):
            print(filename, file=sys.stderr)
            result = run(filename, aggressive=aggressive) and result

    if result:
        print(GREEN + 'Okay' + END)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--aggression-level', default=2, type=int,
                        help='run autopep8 in aggression level')
    args = parser.parse_args()

    return int(not suite(aggressive=args.aggression_level))


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = vim_autopep8
"""Run autopep8 on the selected buffer in Vim.

map <C-I> :pyfile <path_to>/vim_autopep8.py<CR>

"""

import vim
if vim.eval('&syntax') == 'python':
    encoding = vim.eval('&fileencoding')
    source = '\n'.join(line.decode(encoding)
                       for line in vim.current.buffer) + '\n'

    import autopep8
    options = autopep8.parse_args(['--range',
                                   str(1 + vim.current.range.start),
                                   str(1 + vim.current.range.end),
                                   ''])

    formatted = autopep8.fix_code(source, options=options)

    if source != formatted:
        if formatted.endswith('\n'):
            formatted = formatted[:-1]

        vim.current.buffer[:] = [line.encode(encoding)
                                 for line in formatted.splitlines()]

########NEW FILE########
__FILENAME__ = update_readme
#!/usr/bin/env python
"""Update example in readme."""

import io
import sys
import textwrap

import pyflakes.api
import pyflakes.messages
import pyflakes.reporter

import autopep8


def split_readme(readme_path, before_key, after_key, options_key, end_key):
    """Return split readme."""
    with open(readme_path) as readme_file:
        readme = readme_file.read()

    top, rest = readme.split(before_key)
    before, rest = rest.split(after_key)
    _, rest = rest.split(options_key)
    _, bottom = rest.split(end_key)

    return (top.rstrip('\n'),
            before.strip('\n'),
            end_key + '\n\n' + bottom.lstrip('\n'))


def indent_line(line):
    """Indent non-empty lines."""
    if line:
        return 4 * ' ' + line
    else:
        return line


def indent(text):
    """Indent text by four spaces."""
    return '\n'.join(indent_line(line) for line in text.split('\n'))


def help_message():
    """Return help output."""
    parser = autopep8.create_parser()
    string_io = io.StringIO()
    parser.print_help(string_io)
    return string_io.getvalue()


def check(source):
    """Check code."""
    compile(source, '<string>', 'exec', dont_inherit=True)
    reporter = pyflakes.reporter.Reporter(sys.stderr, sys.stderr)
    pyflakes.api.check(source, filename='<string>', reporter=reporter)


def main():
    readme_path = 'README.rst'
    before_key = 'Before running autopep8.\n\n.. code-block:: python'
    after_key = 'After running autopep8.\n\n.. code-block:: python'
    options_key = 'Options::'

    (top, before, bottom) = split_readme(readme_path,
                                         before_key=before_key,
                                         after_key=after_key,
                                         options_key=options_key,
                                         end_key='Features\n========')

    input_code = textwrap.dedent(before)

    output_code = autopep8.fix_code(
        input_code,
        options=autopep8.parse_args(['', '-aa']))

    check(output_code)

    new_readme = '\n\n'.join([
        top,
        before_key, before,
        after_key, indent(output_code).rstrip(),
        options_key, indent(help_message()),
        bottom])

    with open(readme_path, 'w') as output_file:
        output_file.write(new_readme)


if __name__ == '__main__':
    main()

########NEW FILE########
