__FILENAME__ = cpplint
#!/usr/bin/python
#
# Copyright (c) 2009 Google Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#    * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Here are some issues that I've had people identify in my code during reviews,
# that I think are possible to flag automatically in a lint tool.  If these were
# caught by lint, it would save time both for myself and that of my reviewers.
# Most likely, some of these are beyond the scope of the current lint framework,
# but I think it is valuable to retain these wish-list items even if they cannot
# be immediately implemented.
#
#  Suggestions
#  -----------
#  - Check for no 'explicit' for multi-arg ctor
#  - Check for boolean assign RHS in parens
#  - Check for ctor initializer-list colon position and spacing
#  - Check that if there's a ctor, there should be a dtor
#  - Check accessors that return non-pointer member variables are
#    declared const
#  - Check accessors that return non-const pointer member vars are
#    *not* declared const
#  - Check for using public includes for testing
#  - Check for spaces between brackets in one-line inline method
#  - Check for no assert()
#  - Check for spaces surrounding operators
#  - Check for 0 in pointer context (should be NULL)
#  - Check for 0 in char context (should be '\0')
#  - Check for camel-case method name conventions for methods
#    that are not simple inline getters and setters
#  - Check that base classes have virtual destructors
#    put "  // namespace" after } that closes a namespace, with
#    namespace's name after 'namespace' if it is named.
#  - Do not indent namespace contents
#  - Avoid inlining non-trivial constructors in header files
#    include base/basictypes.h if DISALLOW_EVIL_CONSTRUCTORS is used
#  - Check for old-school (void) cast for call-sites of functions
#    ignored return value
#  - Check gUnit usage of anonymous namespace
#  - Check for class declaration order (typedefs, consts, enums,
#    ctor(s?), dtor, friend declarations, methods, member vars)
#

"""Does google-lint on c++ files.

The goal of this script is to identify places in the code that *may*
be in non-compliance with google style.  It does not attempt to fix
up these problems -- the point is to educate.  It does also not
attempt to find all problems, or to ensure that everything it does
find is legitimately a problem.

In particular, we can get very confused by /* and // inside strings!
We do a small hack, which is to ignore //'s with "'s after them on the
same line, but it is far from perfect (in either direction).
"""

import codecs
import getopt
import math  # for log
import os
import re
import sre_compile
import string
import sys
import unicodedata


_USAGE = """
Syntax: cpplint.py [--verbose=#] [--output=vs7] [--filter=-x,+y,...]
                   [--counting=total|toplevel|detailed]
        <file> [file] ...

  The style guidelines this tries to follow are those in
    http://google-styleguide.googlecode.com/svn/trunk/cppguide.xml

  Every problem is given a confidence score from 1-5, with 5 meaning we are
  certain of the problem, and 1 meaning it could be a legitimate construct.
  This will miss some errors, and is not a substitute for a code review.

  To suppress false-positive errors of a certain category, add a
  'NOLINT(category)' comment to the line.  NOLINT or NOLINT(*)
  suppresses errors of all categories on that line.

  The files passed in will be linted; at least one file must be provided.
  Linted extensions are .cc, .cpp, and .h.  Other file types will be ignored.

  Flags:

    output=vs7
      By default, the output is formatted to ease emacs parsing.  Visual Studio
      compatible output (vs7) may also be used.  Other formats are unsupported.

    verbose=#
      Specify a number 0-5 to restrict errors to certain verbosity levels.

    filter=-x,+y,...
      Specify a comma-separated list of category-filters to apply: only
      error messages whose category names pass the filters will be printed.
      (Category names are printed with the message and look like
      "[whitespace/indent]".)  Filters are evaluated left to right.
      "-FOO" and "FOO" means "do not print categories that start with FOO".
      "+FOO" means "do print categories that start with FOO".

      Examples: --filter=-whitespace,+whitespace/braces
                --filter=whitespace,runtime/printf,+runtime/printf_format
                --filter=-,+build/include_what_you_use

      To see a list of all the categories used in cpplint, pass no arg:
         --filter=

    counting=total|toplevel|detailed
      The total number of errors found is always printed. If
      'toplevel' is provided, then the count of errors in each of
      the top-level categories like 'build' and 'whitespace' will
      also be printed. If 'detailed' is provided, then a count
      is provided for each category like 'build/class'.
"""

# We categorize each error message we print.  Here are the categories.
# We want an explicit list so we can list them all in cpplint --filter=.
# If you add a new error message with a new category, add it to the list
# here!  cpplint_unittest.py should tell you if you forget to do this.
# \ used for clearer layout -- pylint: disable-msg=C6013
_ERROR_CATEGORIES = [
  'build/class',
  'build/deprecated',
  'build/endif_comment',
  'build/explicit_make_pair',
  'build/forward_decl',
  'build/header_guard',
  'build/include',
  'build/include_alpha',
  'build/include_order',
  'build/include_what_you_use',
  'build/namespaces',
  'build/printf_format',
  'build/storage_class',
  'legal/copyright',
  'readability/braces',
  'readability/casting',
  'readability/check',
  'readability/constructors',
  'readability/fn_size',
  'readability/function',
  'readability/multiline_comment',
  'readability/multiline_string',
  'readability/nolint',
  'readability/streams',
  'readability/todo',
  'readability/utf8',
  'runtime/arrays',
  'runtime/casting',
  'runtime/explicit',
  'runtime/int',
  'runtime/init',
  'runtime/invalid_increment',
  'runtime/member_string_references',
  'runtime/memset',
  'runtime/operator',
  'runtime/printf',
  'runtime/printf_format',
  'runtime/references',
  'runtime/rtti',
  'runtime/sizeof',
  'runtime/string',
  'runtime/threadsafe_fn',
  'runtime/virtual',
  'whitespace/blank_line',
  'whitespace/braces',
  'whitespace/comma',
  'whitespace/comments',
  'whitespace/end_of_line',
  'whitespace/ending_newline',
  'whitespace/indent',
  'whitespace/labels',
  'whitespace/line_length',
  'whitespace/newline',
  'whitespace/operators',
  'whitespace/parens',
  'whitespace/semicolon',
  'whitespace/tab',
  'whitespace/todo'
  ]

# The default state of the category filter. This is overrided by the --filter=
# flag. By default all errors are on, so only add here categories that should be
# off by default (i.e., categories that must be enabled by the --filter= flags).
# All entries here should start with a '-' or '+', as in the --filter= flag.
_DEFAULT_FILTERS = ['-build/include_alpha']

# We used to check for high-bit characters, but after much discussion we
# decided those were OK, as long as they were in UTF-8 and didn't represent
# hard-coded international strings, which belong in a separate i18n file.

# Headers that we consider STL headers.
_STL_HEADERS = frozenset([
    'algobase.h', 'algorithm', 'alloc.h', 'bitset', 'deque', 'exception',
    'function.h', 'functional', 'hash_map', 'hash_map.h', 'hash_set',
    'hash_set.h', 'iterator', 'list', 'list.h', 'map', 'memory', 'new',
    'pair.h', 'pthread_alloc', 'queue', 'set', 'set.h', 'sstream', 'stack',
    'stl_alloc.h', 'stl_relops.h', 'type_traits.h',
    'utility', 'vector', 'vector.h',
    ])


# Non-STL C++ system headers.
_CPP_HEADERS = frozenset([
    'algo.h', 'builtinbuf.h', 'bvector.h', 'cassert', 'cctype',
    'cerrno', 'cfloat', 'ciso646', 'climits', 'clocale', 'cmath',
    'complex', 'complex.h', 'csetjmp', 'csignal', 'cstdarg', 'cstddef',
    'cstdio', 'cstdlib', 'cstring', 'ctime', 'cwchar', 'cwctype',
    'defalloc.h', 'deque.h', 'editbuf.h', 'exception', 'fstream',
    'fstream.h', 'hashtable.h', 'heap.h', 'indstream.h', 'iomanip',
    'iomanip.h', 'ios', 'iosfwd', 'iostream', 'iostream.h', 'istream',
    'istream.h', 'iterator.h', 'limits', 'map.h', 'multimap.h', 'multiset.h',
    'numeric', 'ostream', 'ostream.h', 'parsestream.h', 'pfstream.h',
    'PlotFile.h', 'procbuf.h', 'pthread_alloc.h', 'rope', 'rope.h',
    'ropeimpl.h', 'SFile.h', 'slist', 'slist.h', 'stack.h', 'stdexcept',
    'stdiostream.h', 'streambuf.h', 'stream.h', 'strfile.h', 'string',
    'strstream', 'strstream.h', 'tempbuf.h', 'tree.h', 'typeinfo', 'valarray',
    ])


# Assertion macros.  These are defined in base/logging.h and
# testing/base/gunit.h.  Note that the _M versions need to come first
# for substring matching to work.
_CHECK_MACROS = [
    'DCHECK', 'CHECK',
    'EXPECT_TRUE_M', 'EXPECT_TRUE',
    'ASSERT_TRUE_M', 'ASSERT_TRUE',
    'EXPECT_FALSE_M', 'EXPECT_FALSE',
    'ASSERT_FALSE_M', 'ASSERT_FALSE',
    ]

# Replacement macros for CHECK/DCHECK/EXPECT_TRUE/EXPECT_FALSE
_CHECK_REPLACEMENT = dict([(m, {}) for m in _CHECK_MACROS])

for op, replacement in [('==', 'EQ'), ('!=', 'NE'),
                        ('>=', 'GE'), ('>', 'GT'),
                        ('<=', 'LE'), ('<', 'LT')]:
  _CHECK_REPLACEMENT['DCHECK'][op] = 'DCHECK_%s' % replacement
  _CHECK_REPLACEMENT['CHECK'][op] = 'CHECK_%s' % replacement
  _CHECK_REPLACEMENT['EXPECT_TRUE'][op] = 'EXPECT_%s' % replacement
  _CHECK_REPLACEMENT['ASSERT_TRUE'][op] = 'ASSERT_%s' % replacement
  _CHECK_REPLACEMENT['EXPECT_TRUE_M'][op] = 'EXPECT_%s_M' % replacement
  _CHECK_REPLACEMENT['ASSERT_TRUE_M'][op] = 'ASSERT_%s_M' % replacement

for op, inv_replacement in [('==', 'NE'), ('!=', 'EQ'),
                            ('>=', 'LT'), ('>', 'LE'),
                            ('<=', 'GT'), ('<', 'GE')]:
  _CHECK_REPLACEMENT['EXPECT_FALSE'][op] = 'EXPECT_%s' % inv_replacement
  _CHECK_REPLACEMENT['ASSERT_FALSE'][op] = 'ASSERT_%s' % inv_replacement
  _CHECK_REPLACEMENT['EXPECT_FALSE_M'][op] = 'EXPECT_%s_M' % inv_replacement
  _CHECK_REPLACEMENT['ASSERT_FALSE_M'][op] = 'ASSERT_%s_M' % inv_replacement


# These constants define types of headers for use with
# _IncludeState.CheckNextIncludeOrder().
_C_SYS_HEADER = 1
_CPP_SYS_HEADER = 2
_LIKELY_MY_HEADER = 3
_POSSIBLE_MY_HEADER = 4
_OTHER_HEADER = 5


_regexp_compile_cache = {}

# Finds occurrences of NOLINT or NOLINT(...).
_RE_SUPPRESSION = re.compile(r'\bNOLINT\b(\([^)]*\))?')

# {str, set(int)}: a map from error categories to sets of linenumbers
# on which those errors are expected and should be suppressed.
_error_suppressions = {}

def ParseNolintSuppressions(filename, raw_line, linenum, error):
  """Updates the global list of error-suppressions.

  Parses any NOLINT comments on the current line, updating the global
  error_suppressions store.  Reports an error if the NOLINT comment
  was malformed.

  Args:
    filename: str, the name of the input file.
    raw_line: str, the line of input text, with comments.
    linenum: int, the number of the current line.
    error: function, an error handler.
  """
  # FIXME(adonovan): "NOLINT(" is misparsed as NOLINT(*).
  matched = _RE_SUPPRESSION.search(raw_line)
  if matched:
    category = matched.group(1)
    if category in (None, '(*)'):  # => "suppress all"
      _error_suppressions.setdefault(None, set()).add(linenum)
    else:
      if category.startswith('(') and category.endswith(')'):
        category = category[1:-1]
        if category in _ERROR_CATEGORIES:
          _error_suppressions.setdefault(category, set()).add(linenum)
        else:
          error(filename, linenum, 'readability/nolint', 5,
                'Unknown NOLINT error category: %s' % category)


def ResetNolintSuppressions():
  "Resets the set of NOLINT suppressions to empty."
  _error_suppressions.clear()


def IsErrorSuppressedByNolint(category, linenum):
  """Returns true if the specified error category is suppressed on this line.

  Consults the global error_suppressions map populated by
  ParseNolintSuppressions/ResetNolintSuppressions.

  Args:
    category: str, the category of the error.
    linenum: int, the current line number.
  Returns:
    bool, True iff the error should be suppressed due to a NOLINT comment.
  """
  return (linenum in _error_suppressions.get(category, set()) or
          linenum in _error_suppressions.get(None, set()))

def Match(pattern, s):
  """Matches the string with the pattern, caching the compiled regexp."""
  # The regexp compilation caching is inlined in both Match and Search for
  # performance reasons; factoring it out into a separate function turns out
  # to be noticeably expensive.
  if not pattern in _regexp_compile_cache:
    _regexp_compile_cache[pattern] = sre_compile.compile(pattern)
  return _regexp_compile_cache[pattern].match(s)


def Search(pattern, s):
  """Searches the string for the pattern, caching the compiled regexp."""
  if not pattern in _regexp_compile_cache:
    _regexp_compile_cache[pattern] = sre_compile.compile(pattern)
  return _regexp_compile_cache[pattern].search(s)


class _IncludeState(dict):
  """Tracks line numbers for includes, and the order in which includes appear.

  As a dict, an _IncludeState object serves as a mapping between include
  filename and line number on which that file was included.

  Call CheckNextIncludeOrder() once for each header in the file, passing
  in the type constants defined above. Calls in an illegal order will
  raise an _IncludeError with an appropriate error message.

  """
  # self._section will move monotonically through this set. If it ever
  # needs to move backwards, CheckNextIncludeOrder will raise an error.
  _INITIAL_SECTION = 0
  _MY_H_SECTION = 1
  _C_SECTION = 2
  _CPP_SECTION = 3
  _OTHER_H_SECTION = 4

  _TYPE_NAMES = {
      _C_SYS_HEADER: 'C system header',
      _CPP_SYS_HEADER: 'C++ system header',
      _LIKELY_MY_HEADER: 'header this file implements',
      _POSSIBLE_MY_HEADER: 'header this file may implement',
      _OTHER_HEADER: 'other header',
      }
  _SECTION_NAMES = {
      _INITIAL_SECTION: "... nothing. (This can't be an error.)",
      _MY_H_SECTION: 'a header this file implements',
      _C_SECTION: 'C system header',
      _CPP_SECTION: 'C++ system header',
      _OTHER_H_SECTION: 'other header',
      }

  def __init__(self):
    dict.__init__(self)
    # The name of the current section.
    self._section = self._INITIAL_SECTION
    # The path of last found header.
    self._last_header = ''

  def CanonicalizeAlphabeticalOrder(self, header_path):
    """Returns a path canonicalized for alphabetical comparison.

    - replaces "-" with "_" so they both cmp the same.
    - removes '-inl' since we don't require them to be after the main header.
    - lowercase everything, just in case.

    Args:
      header_path: Path to be canonicalized.

    Returns:
      Canonicalized path.
    """
    return header_path.replace('-inl.h', '.h').replace('-', '_').lower()

  def IsInAlphabeticalOrder(self, header_path):
    """Check if a header is in alphabetical order with the previous header.

    Args:
      header_path: Header to be checked.

    Returns:
      Returns true if the header is in alphabetical order.
    """
    canonical_header = self.CanonicalizeAlphabeticalOrder(header_path)
    if self._last_header > canonical_header:
      return False
    self._last_header = canonical_header
    return True

  def CheckNextIncludeOrder(self, header_type):
    """Returns a non-empty error message if the next header is out of order.

    This function also updates the internal state to be ready to check
    the next include.

    Args:
      header_type: One of the _XXX_HEADER constants defined above.

    Returns:
      The empty string if the header is in the right order, or an
      error message describing what's wrong.

    """
    error_message = ('Found %s after %s' %
                     (self._TYPE_NAMES[header_type],
                      self._SECTION_NAMES[self._section]))

    last_section = self._section

    if header_type == _C_SYS_HEADER:
      if self._section <= self._C_SECTION:
        self._section = self._C_SECTION
      else:
        self._last_header = ''
        return error_message
    elif header_type == _CPP_SYS_HEADER:
      if self._section <= self._CPP_SECTION:
        self._section = self._CPP_SECTION
      else:
        self._last_header = ''
        return error_message
    elif header_type == _LIKELY_MY_HEADER:
      if self._section <= self._MY_H_SECTION:
        self._section = self._MY_H_SECTION
      else:
        self._section = self._OTHER_H_SECTION
    elif header_type == _POSSIBLE_MY_HEADER:
      if self._section <= self._MY_H_SECTION:
        self._section = self._MY_H_SECTION
      else:
        # This will always be the fallback because we're not sure
        # enough that the header is associated with this file.
        self._section = self._OTHER_H_SECTION
    else:
      assert header_type == _OTHER_HEADER
      self._section = self._OTHER_H_SECTION

    if last_section != self._section:
      self._last_header = ''

    return ''


class _CppLintState(object):
  """Maintains module-wide state.."""

  def __init__(self):
    self.verbose_level = 1  # global setting.
    self.error_count = 0    # global count of reported errors
    # filters to apply when emitting error messages
    self.filters = _DEFAULT_FILTERS[:]
    self.counting = 'total'  # In what way are we counting errors?
    self.errors_by_category = {}  # string to int dict storing error counts

    # output format:
    # "emacs" - format that emacs can parse (default)
    # "vs7" - format that Microsoft Visual Studio 7 can parse
    self.output_format = 'emacs'

  def SetOutputFormat(self, output_format):
    """Sets the output format for errors."""
    self.output_format = output_format

  def SetVerboseLevel(self, level):
    """Sets the module's verbosity, and returns the previous setting."""
    last_verbose_level = self.verbose_level
    self.verbose_level = level
    return last_verbose_level

  def SetCountingStyle(self, counting_style):
    """Sets the module's counting options."""
    self.counting = counting_style

  def SetFilters(self, filters):
    """Sets the error-message filters.

    These filters are applied when deciding whether to emit a given
    error message.

    Args:
      filters: A string of comma-separated filters (eg "+whitespace/indent").
               Each filter should start with + or -; else we die.

    Raises:
      ValueError: The comma-separated filters did not all start with '+' or '-'.
                  E.g. "-,+whitespace,-whitespace/indent,whitespace/badfilter"
    """
    # Default filters always have less priority than the flag ones.
    self.filters = _DEFAULT_FILTERS[:]
    for filt in filters.split(','):
      clean_filt = filt.strip()
      if clean_filt:
        self.filters.append(clean_filt)
    for filt in self.filters:
      if not (filt.startswith('+') or filt.startswith('-')):
        raise ValueError('Every filter in --filters must start with + or -'
                         ' (%s does not)' % filt)

  def ResetErrorCounts(self):
    """Sets the module's error statistic back to zero."""
    self.error_count = 0
    self.errors_by_category = {}

  def IncrementErrorCount(self, category):
    """Bumps the module's error statistic."""
    self.error_count += 1
    if self.counting in ('toplevel', 'detailed'):
      if self.counting != 'detailed':
        category = category.split('/')[0]
      if category not in self.errors_by_category:
        self.errors_by_category[category] = 0
      self.errors_by_category[category] += 1

  def PrintErrorCounts(self):
    """Print a summary of errors by category, and the total."""
    for category, count in self.errors_by_category.iteritems():
      sys.stderr.write('Category \'%s\' errors found: %d\n' %
                       (category, count))
    sys.stderr.write('Total errors found: %d\n' % self.error_count)

_cpplint_state = _CppLintState()


def _OutputFormat():
  """Gets the module's output format."""
  return _cpplint_state.output_format


def _SetOutputFormat(output_format):
  """Sets the module's output format."""
  _cpplint_state.SetOutputFormat(output_format)


def _VerboseLevel():
  """Returns the module's verbosity setting."""
  return _cpplint_state.verbose_level


def _SetVerboseLevel(level):
  """Sets the module's verbosity, and returns the previous setting."""
  return _cpplint_state.SetVerboseLevel(level)


def _SetCountingStyle(level):
  """Sets the module's counting options."""
  _cpplint_state.SetCountingStyle(level)


def _Filters():
  """Returns the module's list of output filters, as a list."""
  return _cpplint_state.filters


def _SetFilters(filters):
  """Sets the module's error-message filters.

  These filters are applied when deciding whether to emit a given
  error message.

  Args:
    filters: A string of comma-separated filters (eg "whitespace/indent").
             Each filter should start with + or -; else we die.
  """
  _cpplint_state.SetFilters(filters)


class _FunctionState(object):
  """Tracks current function name and the number of lines in its body."""

  _NORMAL_TRIGGER = 250  # for --v=0, 500 for --v=1, etc.
  _TEST_TRIGGER = 400    # about 50% more than _NORMAL_TRIGGER.

  def __init__(self):
    self.in_a_function = False
    self.lines_in_function = 0
    self.current_function = ''

  def Begin(self, function_name):
    """Start analyzing function body.

    Args:
      function_name: The name of the function being tracked.
    """
    self.in_a_function = True
    self.lines_in_function = 0
    self.current_function = function_name

  def Count(self):
    """Count line in current function body."""
    if self.in_a_function:
      self.lines_in_function += 1

  def Check(self, error, filename, linenum):
    """Report if too many lines in function body.

    Args:
      error: The function to call with any errors found.
      filename: The name of the current file.
      linenum: The number of the line to check.
    """
    if Match(r'T(EST|est)', self.current_function):
      base_trigger = self._TEST_TRIGGER
    else:
      base_trigger = self._NORMAL_TRIGGER
    trigger = base_trigger * 2**_VerboseLevel()

    if self.lines_in_function > trigger:
      error_level = int(math.log(self.lines_in_function / base_trigger, 2))
      # 50 => 0, 100 => 1, 200 => 2, 400 => 3, 800 => 4, 1600 => 5, ...
      if error_level > 5:
        error_level = 5
      error(filename, linenum, 'readability/fn_size', error_level,
            'Small and focused functions are preferred:'
            ' %s has %d non-comment lines'
            ' (error triggered by exceeding %d lines).'  % (
                self.current_function, self.lines_in_function, trigger))

  def End(self):
    """Stop analyzing function body."""
    self.in_a_function = False


class _IncludeError(Exception):
  """Indicates a problem with the include order in a file."""
  pass


class FileInfo:
  """Provides utility functions for filenames.

  FileInfo provides easy access to the components of a file's path
  relative to the project root.
  """

  def __init__(self, filename):
    self._filename = filename

  def FullName(self):
    """Make Windows paths like Unix."""
    return os.path.abspath(self._filename).replace('\\', '/')

  def RepositoryName(self):
    """FullName after removing the local path to the repository.

    If we have a real absolute path name here we can try to do something smart:
    detecting the root of the checkout and truncating /path/to/checkout from
    the name so that we get header guards that don't include things like
    "C:\Documents and Settings\..." or "/home/username/..." in them and thus
    people on different computers who have checked the source out to different
    locations won't see bogus errors.
    """
    fullname = self.FullName()

    if os.path.exists(fullname):
      project_dir = os.path.dirname(fullname)

      if os.path.exists(os.path.join(project_dir, ".svn")):
        # If there's a .svn file in the current directory, we recursively look
        # up the directory tree for the top of the SVN checkout
        root_dir = project_dir
        one_up_dir = os.path.dirname(root_dir)
        while os.path.exists(os.path.join(one_up_dir, ".svn")):
          root_dir = os.path.dirname(root_dir)
          one_up_dir = os.path.dirname(one_up_dir)

        prefix = os.path.commonprefix([root_dir, project_dir])
        return fullname[len(prefix) + 1:]

      # Not SVN <= 1.6? Try to find a git, hg, or svn top level directory by
      # searching up from the current path.
      root_dir = os.path.dirname(fullname)
      while (root_dir != os.path.dirname(root_dir) and
             not os.path.exists(os.path.join(root_dir, ".git")) and
             not os.path.exists(os.path.join(root_dir, ".hg")) and
             not os.path.exists(os.path.join(root_dir, ".svn"))):
        root_dir = os.path.dirname(root_dir)

      if (os.path.exists(os.path.join(root_dir, ".git")) or
          os.path.exists(os.path.join(root_dir, ".hg")) or
          os.path.exists(os.path.join(root_dir, ".svn"))):
        prefix = os.path.commonprefix([root_dir, project_dir])
        return fullname[len(prefix) + 1:]

    # Don't know what to do; header guard warnings may be wrong...
    return fullname

  def Split(self):
    """Splits the file into the directory, basename, and extension.

    For 'chrome/browser/browser.cc', Split() would
    return ('chrome/browser', 'browser', '.cc')

    Returns:
      A tuple of (directory, basename, extension).
    """

    googlename = self.RepositoryName()
    project, rest = os.path.split(googlename)
    return (project,) + os.path.splitext(rest)

  def BaseName(self):
    """File base name - text after the final slash, before the final period."""
    return self.Split()[1]

  def Extension(self):
    """File extension - text following the final period."""
    return self.Split()[2]

  def NoExtension(self):
    """File has no source file extension."""
    return '/'.join(self.Split()[0:2])

  def IsSource(self):
    """File has a source file extension."""
    return self.Extension()[1:] in ('c', 'cc', 'cpp', 'cxx')


def _ShouldPrintError(category, confidence, linenum):
  """If confidence >= verbose, category passes filter and is not suppressed."""

  # There are three ways we might decide not to print an error message:
  # a "NOLINT(category)" comment appears in the source,
  # the verbosity level isn't high enough, or the filters filter it out.
  if IsErrorSuppressedByNolint(category, linenum):
    return False
  if confidence < _cpplint_state.verbose_level:
    return False

  is_filtered = False
  for one_filter in _Filters():
    if one_filter.startswith('-'):
      if category.startswith(one_filter[1:]):
        is_filtered = True
    elif one_filter.startswith('+'):
      if category.startswith(one_filter[1:]):
        is_filtered = False
    else:
      assert False  # should have been checked for in SetFilter.
  if is_filtered:
    return False

  return True


def Error(filename, linenum, category, confidence, message):
  """Logs the fact we've found a lint error.

  We log where the error was found, and also our confidence in the error,
  that is, how certain we are this is a legitimate style regression, and
  not a misidentification or a use that's sometimes justified.

  False positives can be suppressed by the use of
  "cpplint(category)"  comments on the offending line.  These are
  parsed into _error_suppressions.

  Args:
    filename: The name of the file containing the error.
    linenum: The number of the line containing the error.
    category: A string used to describe the "category" this bug
      falls under: "whitespace", say, or "runtime".  Categories
      may have a hierarchy separated by slashes: "whitespace/indent".
    confidence: A number from 1-5 representing a confidence score for
      the error, with 5 meaning that we are certain of the problem,
      and 1 meaning that it could be a legitimate construct.
    message: The error message.
  """
  if _ShouldPrintError(category, confidence, linenum):
    _cpplint_state.IncrementErrorCount(category)
    if _cpplint_state.output_format == 'vs7':
      sys.stderr.write('%s(%s):  %s  [%s] [%d]\n' % (
          filename, linenum, message, category, confidence))
    else:
      sys.stderr.write('%s:%s:  %s  [%s] [%d]\n' % (
          filename, linenum, message, category, confidence))


# Matches standard C++ escape esequences per 2.13.2.3 of the C++ standard.
_RE_PATTERN_CLEANSE_LINE_ESCAPES = re.compile(
    r'\\([abfnrtv?"\\\']|\d+|x[0-9a-fA-F]+)')
# Matches strings.  Escape codes should already be removed by ESCAPES.
_RE_PATTERN_CLEANSE_LINE_DOUBLE_QUOTES = re.compile(r'"[^"]*"')
# Matches characters.  Escape codes should already be removed by ESCAPES.
_RE_PATTERN_CLEANSE_LINE_SINGLE_QUOTES = re.compile(r"'.'")
# Matches multi-line C++ comments.
# This RE is a little bit more complicated than one might expect, because we
# have to take care of space removals tools so we can handle comments inside
# statements better.
# The current rule is: We only clear spaces from both sides when we're at the
# end of the line. Otherwise, we try to remove spaces from the right side,
# if this doesn't work we try on left side but only if there's a non-character
# on the right.
_RE_PATTERN_CLEANSE_LINE_C_COMMENTS = re.compile(
    r"""(\s*/\*.*\*/\s*$|
            /\*.*\*/\s+|
         \s+/\*.*\*/(?=\W)|
            /\*.*\*/)""", re.VERBOSE)


def IsCppString(line):
  """Does line terminate so, that the next symbol is in string constant.

  This function does not consider single-line nor multi-line comments.

  Args:
    line: is a partial line of code starting from the 0..n.

  Returns:
    True, if next character appended to 'line' is inside a
    string constant.
  """

  line = line.replace(r'\\', 'XX')  # after this, \\" does not match to \"
  return ((line.count('"') - line.count(r'\"') - line.count("'\"'")) & 1) == 1


def FindNextMultiLineCommentStart(lines, lineix):
  """Find the beginning marker for a multiline comment."""
  while lineix < len(lines):
    if lines[lineix].strip().startswith('/*'):
      # Only return this marker if the comment goes beyond this line
      if lines[lineix].strip().find('*/', 2) < 0:
        return lineix
    lineix += 1
  return len(lines)


def FindNextMultiLineCommentEnd(lines, lineix):
  """We are inside a comment, find the end marker."""
  while lineix < len(lines):
    if lines[lineix].strip().endswith('*/'):
      return lineix
    lineix += 1
  return len(lines)


def RemoveMultiLineCommentsFromRange(lines, begin, end):
  """Clears a range of lines for multi-line comments."""
  # Having // dummy comments makes the lines non-empty, so we will not get
  # unnecessary blank line warnings later in the code.
  for i in range(begin, end):
    lines[i] = '// dummy'


def RemoveMultiLineComments(filename, lines, error):
  """Removes multiline (c-style) comments from lines."""
  lineix = 0
  while lineix < len(lines):
    lineix_begin = FindNextMultiLineCommentStart(lines, lineix)
    if lineix_begin >= len(lines):
      return
    lineix_end = FindNextMultiLineCommentEnd(lines, lineix_begin)
    if lineix_end >= len(lines):
      error(filename, lineix_begin + 1, 'readability/multiline_comment', 5,
            'Could not find end of multi-line comment')
      return
    RemoveMultiLineCommentsFromRange(lines, lineix_begin, lineix_end + 1)
    lineix = lineix_end + 1


def CleanseComments(line):
  """Removes //-comments and single-line C-style /* */ comments.

  Args:
    line: A line of C++ source.

  Returns:
    The line with single-line comments removed.
  """
  commentpos = line.find('//')
  if commentpos != -1 and not IsCppString(line[:commentpos]):
    line = line[:commentpos].rstrip()
  # get rid of /* ... */
  return _RE_PATTERN_CLEANSE_LINE_C_COMMENTS.sub('', line)


class CleansedLines(object):
  """Holds 3 copies of all lines with different preprocessing applied to them.

  1) elided member contains lines without strings and comments,
  2) lines member contains lines without comments, and
  3) raw member contains all the lines without processing.
  All these three members are of <type 'list'>, and of the same length.
  """

  def __init__(self, lines):
    self.elided = []
    self.lines = []
    self.raw_lines = lines
    self.num_lines = len(lines)
    for linenum in range(len(lines)):
      self.lines.append(CleanseComments(lines[linenum]))
      elided = self._CollapseStrings(lines[linenum])
      self.elided.append(CleanseComments(elided))

  def NumLines(self):
    """Returns the number of lines represented."""
    return self.num_lines

  @staticmethod
  def _CollapseStrings(elided):
    """Collapses strings and chars on a line to simple "" or '' blocks.

    We nix strings first so we're not fooled by text like '"http://"'

    Args:
      elided: The line being processed.

    Returns:
      The line with collapsed strings.
    """
    if not _RE_PATTERN_INCLUDE.match(elided):
      # Remove escaped characters first to make quote/single quote collapsing
      # basic.  Things that look like escaped characters shouldn't occur
      # outside of strings and chars.
      elided = _RE_PATTERN_CLEANSE_LINE_ESCAPES.sub('', elided)
      elided = _RE_PATTERN_CLEANSE_LINE_SINGLE_QUOTES.sub("''", elided)
      elided = _RE_PATTERN_CLEANSE_LINE_DOUBLE_QUOTES.sub('""', elided)
    return elided


def CloseExpression(clean_lines, linenum, pos):
  """If input points to ( or { or [, finds the position that closes it.

  If lines[linenum][pos] points to a '(' or '{' or '[', finds the
  linenum/pos that correspond to the closing of the expression.

  Args:
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    pos: A position on the line.

  Returns:
    A tuple (line, linenum, pos) pointer *past* the closing brace, or
    (line, len(lines), -1) if we never find a close.  Note we ignore
    strings and comments when matching; and the line we return is the
    'cleansed' line at linenum.
  """

  line = clean_lines.elided[linenum]
  startchar = line[pos]
  if startchar not in '({[':
    return (line, clean_lines.NumLines(), -1)
  if startchar == '(': endchar = ')'
  if startchar == '[': endchar = ']'
  if startchar == '{': endchar = '}'

  num_open = line.count(startchar) - line.count(endchar)
  while linenum < clean_lines.NumLines() and num_open > 0:
    linenum += 1
    line = clean_lines.elided[linenum]
    num_open += line.count(startchar) - line.count(endchar)
  # OK, now find the endchar that actually got us back to even
  endpos = len(line)
  while num_open >= 0:
    endpos = line.rfind(')', 0, endpos)
    num_open -= 1                 # chopped off another )
  return (line, linenum, endpos + 1)


def CheckForCopyright(filename, lines, error):
  """Logs an error if no Copyright message appears at the top of the file."""

  # We'll say it should occur by line 10. Don't forget there's a
  # dummy line at the front.
  for line in xrange(1, min(len(lines), 11)):
    if re.search(r'Copyright', lines[line], re.I): break
  else:                       # means no copyright line was found
    error(filename, 0, 'legal/copyright', 5,
          'No copyright message found.  '
          'You should have a line: "Copyright [year] <Copyright Owner>"')


def GetHeaderGuardCPPVariable(filename):
  """Returns the CPP variable that should be used as a header guard.

  Args:
    filename: The name of a C++ header file.

  Returns:
    The CPP variable that should be used as a header guard in the
    named file.

  """

  # Restores original filename in case that cpplint is invoked from Emacs's
  # flymake.
  filename = re.sub(r'_flymake\.h$', '.h', filename)

  fileinfo = FileInfo(filename)
  return re.sub(r'[-./\s]', '_', fileinfo.RepositoryName()).upper() + '_'


def CheckForHeaderGuard(filename, lines, error):
  """Checks that the file contains a header guard.

  Logs an error if no #ifndef header guard is present.  For other
  headers, checks that the full pathname is used.

  Args:
    filename: The name of the C++ header file.
    lines: An array of strings, each representing a line of the file.
    error: The function to call with any errors found.
  """

  cppvar = GetHeaderGuardCPPVariable(filename)

  ifndef = None
  ifndef_linenum = 0
  define = None
  endif = None
  endif_linenum = 0
  for linenum, line in enumerate(lines):
    linesplit = line.split()
    if len(linesplit) >= 2:
      # find the first occurrence of #ifndef and #define, save arg
      if not ifndef and linesplit[0] == '#ifndef':
        # set ifndef to the header guard presented on the #ifndef line.
        ifndef = linesplit[1]
        ifndef_linenum = linenum
      if not define and linesplit[0] == '#define':
        define = linesplit[1]
    # find the last occurrence of #endif, save entire line
    if line.startswith('#endif'):
      endif = line
      endif_linenum = linenum

  if not ifndef:
    error(filename, 0, 'build/header_guard', 5,
          'No #ifndef header guard found, suggested CPP variable is: %s' %
          cppvar)
    return

  if not define:
    error(filename, 0, 'build/header_guard', 5,
          'No #define header guard found, suggested CPP variable is: %s' %
          cppvar)
    return

  # The guard should be PATH_FILE_H_, but we also allow PATH_FILE_H__
  # for backward compatibility.
  if ifndef != cppvar:
    error_level = 0
    if ifndef != cppvar + '_':
      error_level = 5

    ParseNolintSuppressions(filename, lines[ifndef_linenum], ifndef_linenum,
                            error)
    error(filename, ifndef_linenum, 'build/header_guard', error_level,
          '#ifndef header guard has wrong style, please use: %s' % cppvar)

  if define != ifndef:
    error(filename, 0, 'build/header_guard', 5,
          '#ifndef and #define don\'t match, suggested CPP variable is: %s' %
          cppvar)
    return

  if endif != ('#endif  // %s' % cppvar):
    error_level = 0
    if endif != ('#endif  // %s' % (cppvar + '_')):
      error_level = 5

    ParseNolintSuppressions(filename, lines[endif_linenum], endif_linenum,
                            error)
    error(filename, endif_linenum, 'build/header_guard', error_level,
          '#endif line should be "#endif  // %s"' % cppvar)


def CheckForUnicodeReplacementCharacters(filename, lines, error):
  """Logs an error for each line containing Unicode replacement characters.

  These indicate that either the file contained invalid UTF-8 (likely)
  or Unicode replacement characters (which it shouldn't).  Note that
  it's possible for this to throw off line numbering if the invalid
  UTF-8 occurred adjacent to a newline.

  Args:
    filename: The name of the current file.
    lines: An array of strings, each representing a line of the file.
    error: The function to call with any errors found.
  """
  for linenum, line in enumerate(lines):
    if u'\ufffd' in line:
      error(filename, linenum, 'readability/utf8', 5,
            'Line contains invalid UTF-8 (or Unicode replacement character).')


def CheckForNewlineAtEOF(filename, lines, error):
  """Logs an error if there is no newline char at the end of the file.

  Args:
    filename: The name of the current file.
    lines: An array of strings, each representing a line of the file.
    error: The function to call with any errors found.
  """

  # The array lines() was created by adding two newlines to the
  # original file (go figure), then splitting on \n.
  # To verify that the file ends in \n, we just have to make sure the
  # last-but-two element of lines() exists and is empty.
  if len(lines) < 3 or lines[-2]:
    error(filename, len(lines) - 2, 'whitespace/ending_newline', 5,
          'Could not find a newline character at the end of the file.')


def CheckForMultilineCommentsAndStrings(filename, clean_lines, linenum, error):
  """Logs an error if we see /* ... */ or "..." that extend past one line.

  /* ... */ comments are legit inside macros, for one line.
  Otherwise, we prefer // comments, so it's ok to warn about the
  other.  Likewise, it's ok for strings to extend across multiple
  lines, as long as a line continuation character (backslash)
  terminates each line. Although not currently prohibited by the C++
  style guide, it's ugly and unnecessary. We don't do well with either
  in this lint program, so we warn about both.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """
  line = clean_lines.elided[linenum]

  # Remove all \\ (escaped backslashes) from the line. They are OK, and the
  # second (escaped) slash may trigger later \" detection erroneously.
  line = line.replace('\\\\', '')

  if line.count('/*') > line.count('*/'):
    error(filename, linenum, 'readability/multiline_comment', 5,
          'Complex multi-line /*...*/-style comment found. '
          'Lint may give bogus warnings.  '
          'Consider replacing these with //-style comments, '
          'with #if 0...#endif, '
          'or with more clearly structured multi-line comments.')

  if (line.count('"') - line.count('\\"')) % 2:
    error(filename, linenum, 'readability/multiline_string', 5,
          'Multi-line string ("...") found.  This lint script doesn\'t '
          'do well with such strings, and may give bogus warnings.  They\'re '
          'ugly and unnecessary, and you should use concatenation instead".')


threading_list = (
    ('asctime(', 'asctime_r('),
    ('ctime(', 'ctime_r('),
    ('getgrgid(', 'getgrgid_r('),
    ('getgrnam(', 'getgrnam_r('),
    ('getlogin(', 'getlogin_r('),
    ('getpwnam(', 'getpwnam_r('),
    ('getpwuid(', 'getpwuid_r('),
    ('gmtime(', 'gmtime_r('),
    ('localtime(', 'localtime_r('),
    ('rand(', 'rand_r('),
    ('readdir(', 'readdir_r('),
    ('strtok(', 'strtok_r('),
    ('ttyname(', 'ttyname_r('),
    )


def CheckPosixThreading(filename, clean_lines, linenum, error):
  """Checks for calls to thread-unsafe functions.

  Much code has been originally written without consideration of
  multi-threading. Also, engineers are relying on their old experience;
  they have learned posix before threading extensions were added. These
  tests guide the engineers to use thread-safe functions (when using
  posix directly).

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """
  line = clean_lines.elided[linenum]
  for single_thread_function, multithread_safe_function in threading_list:
    ix = line.find(single_thread_function)
    # Comparisons made explicit for clarity -- pylint: disable-msg=C6403
    if ix >= 0 and (ix == 0 or (not line[ix - 1].isalnum() and
                                line[ix - 1] not in ('_', '.', '>'))):
      error(filename, linenum, 'runtime/threadsafe_fn', 2,
            'Consider using ' + multithread_safe_function +
            '...) instead of ' + single_thread_function +
            '...) for improved thread safety.')


# Matches invalid increment: *count++, which moves pointer instead of
# incrementing a value.
_RE_PATTERN_INVALID_INCREMENT = re.compile(
    r'^\s*\*\w+(\+\+|--);')


def CheckInvalidIncrement(filename, clean_lines, linenum, error):
  """Checks for invalid increment *count++.

  For example following function:
  void increment_counter(int* count) {
    *count++;
  }
  is invalid, because it effectively does count++, moving pointer, and should
  be replaced with ++*count, (*count)++ or *count += 1.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """
  line = clean_lines.elided[linenum]
  if _RE_PATTERN_INVALID_INCREMENT.match(line):
    error(filename, linenum, 'runtime/invalid_increment', 5,
          'Changing pointer instead of value (or unused value of operator*).')


class _ClassInfo(object):
  """Stores information about a class."""

  def __init__(self, name, clean_lines, linenum):
    self.name = name
    self.linenum = linenum
    self.seen_open_brace = False
    self.is_derived = False
    self.virtual_method_linenumber = None
    self.has_virtual_destructor = False
    self.brace_depth = 0

    # Try to find the end of the class.  This will be confused by things like:
    #   class A {
    #   } *x = { ...
    #
    # But it's still good enough for CheckSectionSpacing.
    self.last_line = 0
    depth = 0
    for i in range(linenum, clean_lines.NumLines()):
      line = clean_lines.lines[i]
      depth += line.count('{') - line.count('}')
      if not depth:
        self.last_line = i
        break


class _ClassState(object):
  """Holds the current state of the parse relating to class declarations.

  It maintains a stack of _ClassInfos representing the parser's guess
  as to the current nesting of class declarations. The innermost class
  is at the top (back) of the stack. Typically, the stack will either
  be empty or have exactly one entry.
  """

  def __init__(self):
    self.classinfo_stack = []

  def CheckFinished(self, filename, error):
    """Checks that all classes have been completely parsed.

    Call this when all lines in a file have been processed.
    Args:
      filename: The name of the current file.
      error: The function to call with any errors found.
    """
    if self.classinfo_stack:
      # Note: This test can result in false positives if #ifdef constructs
      # get in the way of brace matching. See the testBuildClass test in
      # cpplint_unittest.py for an example of this.
      error(filename, self.classinfo_stack[0].linenum, 'build/class', 5,
            'Failed to find complete declaration of class %s' %
            self.classinfo_stack[0].name)


def CheckForNonStandardConstructs(filename, clean_lines, linenum,
                                  class_state, error):
  """Logs an error if we see certain non-ANSI constructs ignored by gcc-2.

  Complain about several constructs which gcc-2 accepts, but which are
  not standard C++.  Warning about these in lint is one way to ease the
  transition to new compilers.
  - put storage class first (e.g. "static const" instead of "const static").
  - "%lld" instead of %qd" in printf-type functions.
  - "%1$d" is non-standard in printf-type functions.
  - "\%" is an undefined character escape sequence.
  - text after #endif is not allowed.
  - invalid inner-style forward declaration.
  - >? and <? operators, and their >?= and <?= cousins.
  - classes with virtual methods need virtual destructors (compiler warning
    available, but not turned on yet.)

  Additionally, check for constructor/destructor style violations and reference
  members, as it is very convenient to do so while checking for
  gcc-2 compliance.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    class_state: A _ClassState instance which maintains information about
                 the current stack of nested class declarations being parsed.
    error: A callable to which errors are reported, which takes 4 arguments:
           filename, line number, error level, and message
  """

  # Remove comments from the line, but leave in strings for now.
  line = clean_lines.lines[linenum]

  if Search(r'printf\s*\(.*".*%[-+ ]?\d*q', line):
    error(filename, linenum, 'runtime/printf_format', 3,
          '%q in format strings is deprecated.  Use %ll instead.')

  if Search(r'printf\s*\(.*".*%\d+\$', line):
    error(filename, linenum, 'runtime/printf_format', 2,
          '%N$ formats are unconventional.  Try rewriting to avoid them.')

  # Remove escaped backslashes before looking for undefined escapes.
  line = line.replace('\\\\', '')

  if Search(r'("|\').*\\(%|\[|\(|{)', line):
    error(filename, linenum, 'build/printf_format', 3,
          '%, [, (, and { are undefined character escapes.  Unescape them.')

  # For the rest, work with both comments and strings removed.
  line = clean_lines.elided[linenum]

  if Search(r'\b(const|volatile|void|char|short|int|long'
            r'|float|double|signed|unsigned'
            r'|schar|u?int8|u?int16|u?int32|u?int64)'
            r'\s+(auto|register|static|extern|typedef)\b',
            line):
    error(filename, linenum, 'build/storage_class', 5,
          'Storage class (static, extern, typedef, etc) should be first.')

  if Match(r'\s*#\s*endif\s*[^/\s]+', line):
    error(filename, linenum, 'build/endif_comment', 5,
          'Uncommented text after #endif is non-standard.  Use a comment.')

  if Match(r'\s*class\s+(\w+\s*::\s*)+\w+\s*;', line):
    error(filename, linenum, 'build/forward_decl', 5,
          'Inner-style forward declarations are invalid.  Remove this line.')

  if Search(r'(\w+|[+-]?\d+(\.\d*)?)\s*(<|>)\?=?\s*(\w+|[+-]?\d+)(\.\d*)?',
            line):
    error(filename, linenum, 'build/deprecated', 3,
          '>? and <? (max and min) operators are non-standard and deprecated.')

  if Search(r'^\s*const\s*string\s*&\s*\w+\s*;', line):
    # TODO(unknown): Could it be expanded safely to arbitrary references,
    # without triggering too many false positives? The first
    # attempt triggered 5 warnings for mostly benign code in the regtest, hence
    # the restriction.
    # Here's the original regexp, for the reference:
    # type_name = r'\w+((\s*::\s*\w+)|(\s*<\s*\w+?\s*>))?'
    # r'\s*const\s*' + type_name + '\s*&\s*\w+\s*;'
    error(filename, linenum, 'runtime/member_string_references', 2,
          'const string& members are dangerous. It is much better to use '
          'alternatives, such as pointers or simple constants.')

  # Track class entry and exit, and attempt to find cases within the
  # class declaration that don't meet the C++ style
  # guidelines. Tracking is very dependent on the code matching Google
  # style guidelines, but it seems to perform well enough in testing
  # to be a worthwhile addition to the checks.
  classinfo_stack = class_state.classinfo_stack
  # Look for a class declaration. The regexp accounts for decorated classes
  # such as in:
  # class LOCKABLE API Object {
  # };
  class_decl_match = Match(
      r'\s*(template\s*<[\w\s<>,:]*>\s*)?'
      '(class|struct)\s+([A-Z_]+\s+)*(\w+(::\w+)*)', line)
  if class_decl_match:
    classinfo_stack.append(_ClassInfo(
        class_decl_match.group(4), clean_lines, linenum))

  # Everything else in this function uses the top of the stack if it's
  # not empty.
  if not classinfo_stack:
    return

  classinfo = classinfo_stack[-1]

  # If the opening brace hasn't been seen look for it and also
  # parent class declarations.
  if not classinfo.seen_open_brace:
    # If the line has a ';' in it, assume it's a forward declaration or
    # a single-line class declaration, which we won't process.
    if line.find(';') != -1:
      classinfo_stack.pop()
      return
    classinfo.seen_open_brace = (line.find('{') != -1)
    # Look for a bare ':'
    if Search('(^|[^:]):($|[^:])', line):
      classinfo.is_derived = True
    if not classinfo.seen_open_brace:
      return  # Everything else in this function is for after open brace

  # The class may have been declared with namespace or classname qualifiers.
  # The constructor and destructor will not have those qualifiers.
  base_classname = classinfo.name.split('::')[-1]

  # Look for single-argument constructors that aren't marked explicit.
  # Technically a valid construct, but against style.
  args = Match(r'\s+(?:inline\s+)?%s\s*\(([^,()]+)\)'
               % re.escape(base_classname),
               line)
  if (args and
      args.group(1) != 'void' and
      not Match(r'(const\s+)?%s\s*(?:<\w+>\s*)?&' % re.escape(base_classname),
                args.group(1).strip())):
    error(filename, linenum, 'runtime/explicit', 5,
          'Single-argument constructors should be marked explicit.')

  # Look for methods declared virtual.
  if Search(r'\bvirtual\b', line):
    classinfo.virtual_method_linenumber = linenum
    # Only look for a destructor declaration on the same line. It would
    # be extremely unlikely for the destructor declaration to occupy
    # more than one line.
    if Search(r'~%s\s*\(' % base_classname, line):
      classinfo.has_virtual_destructor = True

  # Look for class end.
  brace_depth = classinfo.brace_depth
  brace_depth = brace_depth + line.count('{') - line.count('}')
  if brace_depth <= 0:
    classinfo = classinfo_stack.pop()
    # Try to detect missing virtual destructor declarations.
    # For now, only warn if a non-derived class with virtual methods lacks
    # a virtual destructor. This is to make it less likely that people will
    # declare derived virtual destructors without declaring the base
    # destructor virtual.
    if ((classinfo.virtual_method_linenumber is not None) and
        (not classinfo.has_virtual_destructor) and
        (not classinfo.is_derived)):  # Only warn for base classes
      error(filename, classinfo.linenum, 'runtime/virtual', 4,
            'The class %s probably needs a virtual destructor due to '
            'having virtual method(s), one declared at line %d.'
            % (classinfo.name, classinfo.virtual_method_linenumber))
  else:
    classinfo.brace_depth = brace_depth


def CheckSpacingForFunctionCall(filename, line, linenum, error):
  """Checks for the correctness of various spacing around function calls.

  Args:
    filename: The name of the current file.
    line: The text of the line to check.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """

  # Since function calls often occur inside if/for/while/switch
  # expressions - which have their own, more liberal conventions - we
  # first see if we should be looking inside such an expression for a
  # function call, to which we can apply more strict standards.
  fncall = line    # if there's no control flow construct, look at whole line
  for pattern in (r'\bif\s*\((.*)\)\s*{',
                  r'\bfor\s*\((.*)\)\s*{',
                  r'\bwhile\s*\((.*)\)\s*[{;]',
                  r'\bswitch\s*\((.*)\)\s*{'):
    match = Search(pattern, line)
    if match:
      fncall = match.group(1)    # look inside the parens for function calls
      break

  # Except in if/for/while/switch, there should never be space
  # immediately inside parens (eg "f( 3, 4 )").  We make an exception
  # for nested parens ( (a+b) + c ).  Likewise, there should never be
  # a space before a ( when it's a function argument.  I assume it's a
  # function argument when the char before the whitespace is legal in
  # a function name (alnum + _) and we're not starting a macro. Also ignore
  # pointers and references to arrays and functions coz they're too tricky:
  # we use a very simple way to recognize these:
  # " (something)(maybe-something)" or
  # " (something)(maybe-something," or
  # " (something)[something]"
  # Note that we assume the contents of [] to be short enough that
  # they'll never need to wrap.
  if (  # Ignore control structures.
      not Search(r'\b(if|for|while|switch|return|delete)\b', fncall) and
      # Ignore pointers/references to functions.
      not Search(r' \([^)]+\)\([^)]*(\)|,$)', fncall) and
      # Ignore pointers/references to arrays.
      not Search(r' \([^)]+\)\[[^\]]+\]', fncall)):
    if Search(r'\w\s*\(\s(?!\s*\\$)', fncall):      # a ( used for a fn call
      error(filename, linenum, 'whitespace/parens', 4,
            'Extra space after ( in function call')
    elif Search(r'\(\s+(?!(\s*\\)|\()', fncall):
      error(filename, linenum, 'whitespace/parens', 2,
            'Extra space after (')
    if (Search(r'\w\s+\(', fncall) and
        not Search(r'#\s*define|typedef', fncall)):
      error(filename, linenum, 'whitespace/parens', 4,
            'Extra space before ( in function call')
    # If the ) is followed only by a newline or a { + newline, assume it's
    # part of a control statement (if/while/etc), and don't complain
    if Search(r'[^)]\s+\)\s*[^{\s]', fncall):
      # If the closing parenthesis is preceded by only whitespaces,
      # try to give a more descriptive error message.
      if Search(r'^\s+\)', fncall):
        error(filename, linenum, 'whitespace/parens', 2,
              'Closing ) should be moved to the previous line')
      else:
        error(filename, linenum, 'whitespace/parens', 2,
              'Extra space before )')


def IsBlankLine(line):
  """Returns true if the given line is blank.

  We consider a line to be blank if the line is empty or consists of
  only white spaces.

  Args:
    line: A line of a string.

  Returns:
    True, if the given line is blank.
  """
  return not line or line.isspace()


def CheckForFunctionLengths(filename, clean_lines, linenum,
                            function_state, error):
  """Reports for long function bodies.

  For an overview why this is done, see:
  http://google-styleguide.googlecode.com/svn/trunk/cppguide.xml#Write_Short_Functions

  Uses a simplistic algorithm assuming other style guidelines
  (especially spacing) are followed.
  Only checks unindented functions, so class members are unchecked.
  Trivial bodies are unchecked, so constructors with huge initializer lists
  may be missed.
  Blank/comment lines are not counted so as to avoid encouraging the removal
  of vertical space and comments just to get through a lint check.
  NOLINT *on the last line of a function* disables this check.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    function_state: Current function name and lines in body so far.
    error: The function to call with any errors found.
  """
  lines = clean_lines.lines
  line = lines[linenum]
  raw = clean_lines.raw_lines
  raw_line = raw[linenum]
  joined_line = ''

  starting_func = False
  regexp = r'(\w(\w|::|\*|\&|\s)*)\('  # decls * & space::name( ...
  match_result = Match(regexp, line)
  if match_result:
    # If the name is all caps and underscores, figure it's a macro and
    # ignore it, unless it's TEST or TEST_F.
    function_name = match_result.group(1).split()[-1]
    if function_name == 'TEST' or function_name == 'TEST_F' or (
        not Match(r'[A-Z_]+$', function_name)):
      starting_func = True

  if starting_func:
    body_found = False
    for start_linenum in xrange(linenum, clean_lines.NumLines()):
      start_line = lines[start_linenum]
      joined_line += ' ' + start_line.lstrip()
      if Search(r'(;|})', start_line):  # Declarations and trivial functions
        body_found = True
        break                              # ... ignore
      elif Search(r'{', start_line):
        body_found = True
        function = Search(r'((\w|:)*)\(', line).group(1)
        if Match(r'TEST', function):    # Handle TEST... macros
          parameter_regexp = Search(r'(\(.*\))', joined_line)
          if parameter_regexp:             # Ignore bad syntax
            function += parameter_regexp.group(1)
        else:
          function += '()'
        function_state.Begin(function)
        break
    if not body_found:
      # No body for the function (or evidence of a non-function) was found.
      error(filename, linenum, 'readability/fn_size', 5,
            'Lint failed to find start of function body.')
  elif Match(r'^\}\s*$', line):  # function end
    function_state.Check(error, filename, linenum)
    function_state.End()
  elif not Match(r'^\s*$', line):
    function_state.Count()  # Count non-blank/non-comment lines.


_RE_PATTERN_TODO = re.compile(r'^//(\s*)TODO(\(.+?\))?:?(\s|$)?')


def CheckComment(comment, filename, linenum, error):
  """Checks for common mistakes in TODO comments.

  Args:
    comment: The text of the comment from the line in question.
    filename: The name of the current file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """
  match = _RE_PATTERN_TODO.match(comment)
  if match:
    # One whitespace is correct; zero whitespace is handled elsewhere.
    leading_whitespace = match.group(1)
    if len(leading_whitespace) > 1:
      error(filename, linenum, 'whitespace/todo', 2,
            'Too many spaces before TODO')

    username = match.group(2)
    if not username:
      error(filename, linenum, 'readability/todo', 2,
            'Missing username in TODO; it should look like '
            '"// TODO(my_username): Stuff."')

    middle_whitespace = match.group(3)
    # Comparisons made explicit for correctness -- pylint: disable-msg=C6403
    if middle_whitespace != ' ' and middle_whitespace != '':
      error(filename, linenum, 'whitespace/todo', 2,
            'TODO(my_username) should be followed by a space')


def CheckSpacing(filename, clean_lines, linenum, error):
  """Checks for the correctness of various spacing issues in the code.

  Things we check for: spaces around operators, spaces after
  if/for/while/switch, no spaces around parens in function calls, two
  spaces between code and comment, don't start a block with a blank
  line, don't end a function with a blank line, don't add a blank line
  after public/protected/private, don't have too many blank lines in a row.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """

  raw = clean_lines.raw_lines
  line = raw[linenum]

  # Before nixing comments, check if the line is blank for no good
  # reason.  This includes the first line after a block is opened, and
  # blank lines at the end of a function (ie, right before a line like '}'
  if IsBlankLine(line):
    elided = clean_lines.elided
    prev_line = elided[linenum - 1]
    prevbrace = prev_line.rfind('{')
    # TODO(unknown): Don't complain if line before blank line, and line after,
    #                both start with alnums and are indented the same amount.
    #                This ignores whitespace at the start of a namespace block
    #                because those are not usually indented.
    if (prevbrace != -1 and prev_line[prevbrace:].find('}') == -1
        and prev_line[:prevbrace].find('namespace') == -1):
      # OK, we have a blank line at the start of a code block.  Before we
      # complain, we check if it is an exception to the rule: The previous
      # non-empty line has the parameters of a function header that are indented
      # 4 spaces (because they did not fit in a 80 column line when placed on
      # the same line as the function name).  We also check for the case where
      # the previous line is indented 6 spaces, which may happen when the
      # initializers of a constructor do not fit into a 80 column line.
      exception = False
      if Match(r' {6}\w', prev_line):  # Initializer list?
        # We are looking for the opening column of initializer list, which
        # should be indented 4 spaces to cause 6 space indentation afterwards.
        search_position = linenum-2
        while (search_position >= 0
               and Match(r' {6}\w', elided[search_position])):
          search_position -= 1
        exception = (search_position >= 0
                     and elided[search_position][:5] == '    :')
      else:
        # Search for the function arguments or an initializer list.  We use a
        # simple heuristic here: If the line is indented 4 spaces; and we have a
        # closing paren, without the opening paren, followed by an opening brace
        # or colon (for initializer lists) we assume that it is the last line of
        # a function header.  If we have a colon indented 4 spaces, it is an
        # initializer list.
        exception = (Match(r' {4}\w[^\(]*\)\s*(const\s*)?(\{\s*$|:)',
                           prev_line)
                     or Match(r' {4}:', prev_line))

      if not exception:
        error(filename, linenum, 'whitespace/blank_line', 2,
              'Blank line at the start of a code block.  Is this needed?')
    # This doesn't ignore whitespace at the end of a namespace block
    # because that is too hard without pairing open/close braces;
    # however, a special exception is made for namespace closing
    # brackets which have a comment containing "namespace".
    #
    # Also, ignore blank lines at the end of a block in a long if-else
    # chain, like this:
    #   if (condition1) {
    #     // Something followed by a blank line
    #
    #   } else if (condition2) {
    #     // Something else
    #   }
    if linenum + 1 < clean_lines.NumLines():
      next_line = raw[linenum + 1]
      if (next_line
          and Match(r'\s*}', next_line)
          and next_line.find('namespace') == -1
          and next_line.find('} else ') == -1):
        error(filename, linenum, 'whitespace/blank_line', 3,
              'Blank line at the end of a code block.  Is this needed?')

    matched = Match(r'\s*(public|protected|private):', prev_line)
    if matched:
      error(filename, linenum, 'whitespace/blank_line', 3,
            'Do not leave a blank line after "%s:"' % matched.group(1))

  # Next, we complain if there's a comment too near the text
  commentpos = line.find('//')
  if commentpos != -1:
    # Check if the // may be in quotes.  If so, ignore it
    # Comparisons made explicit for clarity -- pylint: disable-msg=C6403
    if (line.count('"', 0, commentpos) -
        line.count('\\"', 0, commentpos)) % 2 == 0:   # not in quotes
      # Allow one space for new scopes, two spaces otherwise:
      if (not Match(r'^\s*{ //', line) and
          ((commentpos >= 1 and
            line[commentpos-1] not in string.whitespace) or
           (commentpos >= 2 and
            line[commentpos-2] not in string.whitespace))):
        error(filename, linenum, 'whitespace/comments', 2,
              'At least two spaces is best between code and comments')
      # There should always be a space between the // and the comment
      commentend = commentpos + 2
      if commentend < len(line) and not line[commentend] == ' ':
        # but some lines are exceptions -- e.g. if they're big
        # comment delimiters like:
        # //----------------------------------------------------------
        # or are an empty C++ style Doxygen comment, like:
        # ///
        # or they begin with multiple slashes followed by a space:
        # //////// Header comment
        match = (Search(r'[=/-]{4,}\s*$', line[commentend:]) or
                 Search(r'^/$', line[commentend:]) or
                 Search(r'^/+ ', line[commentend:]))
        if not match:
          error(filename, linenum, 'whitespace/comments', 4,
                'Should have a space between // and comment')
      CheckComment(line[commentpos:], filename, linenum, error)

  line = clean_lines.elided[linenum]  # get rid of comments and strings

  # Don't try to do spacing checks for operator methods
  line = re.sub(r'operator(==|!=|<|<<|<=|>=|>>|>)\(', 'operator\(', line)

  # We allow no-spaces around = within an if: "if ( (a=Foo()) == 0 )".
  # Otherwise not.  Note we only check for non-spaces on *both* sides;
  # sometimes people put non-spaces on one side when aligning ='s among
  # many lines (not that this is behavior that I approve of...)
  if Search(r'[\w.]=[\w.]', line) and not Search(r'\b(if|while) ', line):
    error(filename, linenum, 'whitespace/operators', 4,
          'Missing spaces around =')

  # It's ok not to have spaces around binary operators like + - * /, but if
  # there's too little whitespace, we get concerned.  It's hard to tell,
  # though, so we punt on this one for now.  TODO.

  # You should always have whitespace around binary operators.
  # Alas, we can't test < or > because they're legitimately used sans spaces
  # (a->b, vector<int> a).  The only time we can tell is a < with no >, and
  # only if it's not template params list spilling into the next line.
  match = Search(r'[^<>=!\s](==|!=|<=|>=)[^<>=!\s]', line)
  if not match:
    # Note that while it seems that the '<[^<]*' term in the following
    # regexp could be simplified to '<.*', which would indeed match
    # the same class of strings, the [^<] means that searching for the
    # regexp takes linear rather than quadratic time.
    if not Search(r'<[^<]*,\s*$', line):  # template params spill
      match = Search(r'[^<>=!\s](<)[^<>=!\s]([^>]|->)*$', line)
  if match:
    error(filename, linenum, 'whitespace/operators', 3,
          'Missing spaces around %s' % match.group(1))
  # We allow no-spaces around << and >> when used like this: 10<<20, but
  # not otherwise (particularly, not when used as streams)
  match = Search(r'[^0-9\s](<<|>>)[^0-9\s]', line)
  if match:
    error(filename, linenum, 'whitespace/operators', 3,
          'Missing spaces around %s' % match.group(1))

  # There shouldn't be space around unary operators
  match = Search(r'(!\s|~\s|[\s]--[\s;]|[\s]\+\+[\s;])', line)
  if match:
    error(filename, linenum, 'whitespace/operators', 4,
          'Extra space for operator %s' % match.group(1))

  # A pet peeve of mine: no spaces after an if, while, switch, or for
  match = Search(r' (if\(|for\(|while\(|switch\()', line)
  if match:
    error(filename, linenum, 'whitespace/parens', 5,
          'Missing space before ( in %s' % match.group(1))

  # For if/for/while/switch, the left and right parens should be
  # consistent about how many spaces are inside the parens, and
  # there should either be zero or one spaces inside the parens.
  # We don't want: "if ( foo)" or "if ( foo   )".
  # Exception: "for ( ; foo; bar)" and "for (foo; bar; )" are allowed.
  match = Search(r'\b(if|for|while|switch)\s*'
                 r'\(([ ]*)(.).*[^ ]+([ ]*)\)\s*{\s*$',
                 line)
  if match:
    if len(match.group(2)) != len(match.group(4)):
      if not (match.group(3) == ';' and
              len(match.group(2)) == 1 + len(match.group(4)) or
              not match.group(2) and Search(r'\bfor\s*\(.*; \)', line)):
        error(filename, linenum, 'whitespace/parens', 5,
              'Mismatching spaces inside () in %s' % match.group(1))
    if not len(match.group(2)) in [0, 1]:
      error(filename, linenum, 'whitespace/parens', 5,
            'Should have zero or one spaces inside ( and ) in %s' %
            match.group(1))

  # You should always have a space after a comma (either as fn arg or operator)
  if Search(r',[^\s]', line):
    error(filename, linenum, 'whitespace/comma', 3,
          'Missing space after ,')

  # You should always have a space after a semicolon
  # except for few corner cases
  # TODO(unknown): clarify if 'if (1) { return 1;}' is requires one more
  # space after ;
  if Search(r';[^\s};\\)/]', line):
    error(filename, linenum, 'whitespace/semicolon', 3,
          'Missing space after ;')

  # Next we will look for issues with function calls.
  CheckSpacingForFunctionCall(filename, line, linenum, error)

  # Except after an opening paren, or after another opening brace (in case of
  # an initializer list, for instance), you should have spaces before your
  # braces. And since you should never have braces at the beginning of a line,
  # this is an easy test.
  if Search(r'[^ ({]{', line):
    error(filename, linenum, 'whitespace/braces', 5,
          'Missing space before {')

  # Make sure '} else {' has spaces.
  if Search(r'}else', line):
    error(filename, linenum, 'whitespace/braces', 5,
          'Missing space before else')

  # You shouldn't have spaces before your brackets, except maybe after
  # 'delete []' or 'new char * []'.
  if Search(r'\w\s+\[', line) and not Search(r'delete\s+\[', line):
    error(filename, linenum, 'whitespace/braces', 5,
          'Extra space before [')

  # You shouldn't have a space before a semicolon at the end of the line.
  # There's a special case for "for" since the style guide allows space before
  # the semicolon there.
  if Search(r':\s*;\s*$', line):
    error(filename, linenum, 'whitespace/semicolon', 5,
          'Semicolon defining empty statement. Use { } instead.')
  elif Search(r'^\s*;\s*$', line):
    error(filename, linenum, 'whitespace/semicolon', 5,
          'Line contains only semicolon. If this should be an empty statement, '
          'use { } instead.')
  elif (Search(r'\s+;\s*$', line) and
        not Search(r'\bfor\b', line)):
    error(filename, linenum, 'whitespace/semicolon', 5,
          'Extra space before last semicolon. If this should be an empty '
          'statement, use { } instead.')


def CheckSectionSpacing(filename, clean_lines, class_info, linenum, error):
  """Checks for additional blank line issues related to sections.

  Currently the only thing checked here is blank line before protected/private.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    class_info: A _ClassInfo objects.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """
  # Skip checks if the class is small, where small means 25 lines or less.
  # 25 lines seems like a good cutoff since that's the usual height of
  # terminals, and any class that can't fit in one screen can't really
  # be considered "small".
  #
  # Also skip checks if we are on the first line.  This accounts for
  # classes that look like
  #   class Foo { public: ... };
  #
  # If we didn't find the end of the class, last_line would be zero,
  # and the check will be skipped by the first condition.
  if (class_info.last_line - class_info.linenum <= 24 or
      linenum <= class_info.linenum):
    return

  matched = Match(r'\s*(public|protected|private):', clean_lines.lines[linenum])
  if matched:
    # Issue warning if the line before public/protected/private was
    # not a blank line, but don't do this if the previous line contains
    # "class" or "struct".  This can happen two ways:
    #  - We are at the beginning of the class.
    #  - We are forward-declaring an inner class that is semantically
    #    private, but needed to be public for implementation reasons.
    prev_line = clean_lines.lines[linenum - 1]
    if (not IsBlankLine(prev_line) and
        not Search(r'\b(class|struct)\b', prev_line)):
      # Try a bit harder to find the beginning of the class.  This is to
      # account for multi-line base-specifier lists, e.g.:
      #   class Derived
      #       : public Base {
      end_class_head = class_info.linenum
      for i in range(class_info.linenum, linenum):
        if Search(r'\{\s*$', clean_lines.lines[i]):
          end_class_head = i
          break
      if end_class_head < linenum - 1:
        error(filename, linenum, 'whitespace/blank_line', 3,
              '"%s:" should be preceded by a blank line' % matched.group(1))


def GetPreviousNonBlankLine(clean_lines, linenum):
  """Return the most recent non-blank line and its line number.

  Args:
    clean_lines: A CleansedLines instance containing the file contents.
    linenum: The number of the line to check.

  Returns:
    A tuple with two elements.  The first element is the contents of the last
    non-blank line before the current line, or the empty string if this is the
    first non-blank line.  The second is the line number of that line, or -1
    if this is the first non-blank line.
  """

  prevlinenum = linenum - 1
  while prevlinenum >= 0:
    prevline = clean_lines.elided[prevlinenum]
    if not IsBlankLine(prevline):     # if not a blank line...
      return (prevline, prevlinenum)
    prevlinenum -= 1
  return ('', -1)


def CheckBraces(filename, clean_lines, linenum, error):
  """Looks for misplaced braces (e.g. at the end of line).

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """

  line = clean_lines.elided[linenum]        # get rid of comments and strings

  if Match(r'\s*{\s*$', line):
    # We allow an open brace to start a line in the case where someone
    # is using braces in a block to explicitly create a new scope,
    # which is commonly used to control the lifetime of
    # stack-allocated variables.  We don't detect this perfectly: we
    # just don't complain if the last non-whitespace character on the
    # previous non-blank line is ';', ':', '{', or '}'.
    prevline = GetPreviousNonBlankLine(clean_lines, linenum)[0]
    if not Search(r'[;:}{]\s*$', prevline):
      error(filename, linenum, 'whitespace/braces', 4,
            '{ should almost always be at the end of the previous line')

  # An else clause should be on the same line as the preceding closing brace.
  if Match(r'\s*else\s*', line):
    prevline = GetPreviousNonBlankLine(clean_lines, linenum)[0]
    if Match(r'\s*}\s*$', prevline):
      error(filename, linenum, 'whitespace/newline', 4,
            'An else should appear on the same line as the preceding }')

  # If braces come on one side of an else, they should be on both.
  # However, we have to worry about "else if" that spans multiple lines!
  if Search(r'}\s*else[^{]*$', line) or Match(r'[^}]*else\s*{', line):
    if Search(r'}\s*else if([^{]*)$', line):       # could be multi-line if
      # find the ( after the if
      pos = line.find('else if')
      pos = line.find('(', pos)
      if pos > 0:
        (endline, _, endpos) = CloseExpression(clean_lines, linenum, pos)
        if endline[endpos:].find('{') == -1:    # must be brace after if
          error(filename, linenum, 'readability/braces', 5,
                'If an else has a brace on one side, it should have it on both')
    else:            # common case: else not followed by a multi-line if
      error(filename, linenum, 'readability/braces', 5,
            'If an else has a brace on one side, it should have it on both')

  # Likewise, an else should never have the else clause on the same line
  if Search(r'\belse [^\s{]', line) and not Search(r'\belse if\b', line):
    error(filename, linenum, 'whitespace/newline', 4,
          'Else clause should never be on same line as else (use 2 lines)')

  # In the same way, a do/while should never be on one line
  if Match(r'\s*do [^\s{]', line):
    error(filename, linenum, 'whitespace/newline', 4,
          'do/while clauses should not be on a single line')

  # Braces shouldn't be followed by a ; unless they're defining a struct
  # or initializing an array.
  # We can't tell in general, but we can for some common cases.
  prevlinenum = linenum
  while True:
    (prevline, prevlinenum) = GetPreviousNonBlankLine(clean_lines, prevlinenum)
    if Match(r'\s+{.*}\s*;', line) and not prevline.count(';'):
      line = prevline + line
    else:
      break
  if (Search(r'{.*}\s*;', line) and
      line.count('{') == line.count('}') and
      not Search(r'struct|class|enum|\s*=\s*{', line)):
    error(filename, linenum, 'readability/braces', 4,
          "You don't need a ; after a }")


def ReplaceableCheck(operator, macro, line):
  """Determine whether a basic CHECK can be replaced with a more specific one.

  For example suggest using CHECK_EQ instead of CHECK(a == b) and
  similarly for CHECK_GE, CHECK_GT, CHECK_LE, CHECK_LT, CHECK_NE.

  Args:
    operator: The C++ operator used in the CHECK.
    macro: The CHECK or EXPECT macro being called.
    line: The current source line.

  Returns:
    True if the CHECK can be replaced with a more specific one.
  """

  # This matches decimal and hex integers, strings, and chars (in that order).
  match_constant = r'([-+]?(\d+|0[xX][0-9a-fA-F]+)[lLuU]{0,3}|".*"|\'.*\')'

  # Expression to match two sides of the operator with something that
  # looks like a literal, since CHECK(x == iterator) won't compile.
  # This means we can't catch all the cases where a more specific
  # CHECK is possible, but it's less annoying than dealing with
  # extraneous warnings.
  match_this = (r'\s*' + macro + r'\((\s*' +
                match_constant + r'\s*' + operator + r'[^<>].*|'
                r'.*[^<>]' + operator + r'\s*' + match_constant +
                r'\s*\))')

  # Don't complain about CHECK(x == NULL) or similar because
  # CHECK_EQ(x, NULL) won't compile (requires a cast).
  # Also, don't complain about more complex boolean expressions
  # involving && or || such as CHECK(a == b || c == d).
  return Match(match_this, line) and not Search(r'NULL|&&|\|\|', line)


def CheckCheck(filename, clean_lines, linenum, error):
  """Checks the use of CHECK and EXPECT macros.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """

  # Decide the set of replacement macros that should be suggested
  raw_lines = clean_lines.raw_lines
  current_macro = ''
  for macro in _CHECK_MACROS:
    if raw_lines[linenum].find(macro) >= 0:
      current_macro = macro
      break
  if not current_macro:
    # Don't waste time here if line doesn't contain 'CHECK' or 'EXPECT'
    return

  line = clean_lines.elided[linenum]        # get rid of comments and strings

  # Encourage replacing plain CHECKs with CHECK_EQ/CHECK_NE/etc.
  for operator in ['==', '!=', '>=', '>', '<=', '<']:
    if ReplaceableCheck(operator, current_macro, line):
      error(filename, linenum, 'readability/check', 2,
            'Consider using %s instead of %s(a %s b)' % (
                _CHECK_REPLACEMENT[current_macro][operator],
                current_macro, operator))
      break


def GetLineWidth(line):
  """Determines the width of the line in column positions.

  Args:
    line: A string, which may be a Unicode string.

  Returns:
    The width of the line in column positions, accounting for Unicode
    combining characters and wide characters.
  """
  if isinstance(line, unicode):
    width = 0
    for uc in unicodedata.normalize('NFC', line):
      if unicodedata.east_asian_width(uc) in ('W', 'F'):
        width += 2
      elif not unicodedata.combining(uc):
        width += 1
    return width
  else:
    return len(line)


def CheckStyle(filename, clean_lines, linenum, file_extension, class_state,
               error):
  """Checks rules from the 'C++ style rules' section of cppguide.html.

  Most of these rules are hard to test (naming, comment style), but we
  do what we can.  In particular we check for 2-space indents, line lengths,
  tab usage, spaces inside code, etc.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    file_extension: The extension (without the dot) of the filename.
    error: The function to call with any errors found.
  """

  raw_lines = clean_lines.raw_lines
  line = raw_lines[linenum]

  if line.find('\t') != -1:
    error(filename, linenum, 'whitespace/tab', 1,
          'Tab found; better to use spaces')

  # One or three blank spaces at the beginning of the line is weird; it's
  # hard to reconcile that with 2-space indents.
  # NOTE: here are the conditions rob pike used for his tests.  Mine aren't
  # as sophisticated, but it may be worth becoming so:  RLENGTH==initial_spaces
  # if(RLENGTH > 20) complain = 0;
  # if(match($0, " +(error|private|public|protected):")) complain = 0;
  # if(match(prev, "&& *$")) complain = 0;
  # if(match(prev, "\\|\\| *$")) complain = 0;
  # if(match(prev, "[\",=><] *$")) complain = 0;
  # if(match($0, " <<")) complain = 0;
  # if(match(prev, " +for \\(")) complain = 0;
  # if(prevodd && match(prevprev, " +for \\(")) complain = 0;
  initial_spaces = 0
  cleansed_line = clean_lines.elided[linenum]
  while initial_spaces < len(line) and line[initial_spaces] == ' ':
    initial_spaces += 1
  if line and line[-1].isspace():
    error(filename, linenum, 'whitespace/end_of_line', 4,
          'Line ends in whitespace.  Consider deleting these extra spaces.')
  # There are certain situations we allow one space, notably for labels
  elif ((initial_spaces == 1 or initial_spaces == 3) and
        not Match(r'\s*\w+\s*:\s*$', cleansed_line)):
    error(filename, linenum, 'whitespace/indent', 3,
          'Weird number of spaces at line-start.  '
          'Are you using a 2-space indent?')
  # Labels should always be indented at least one space.
  elif not initial_spaces and line[:2] != '//' and Search(r'[^:]:\s*$',
                                                          line):
    error(filename, linenum, 'whitespace/labels', 4,
          'Labels should always be indented at least one space.  '
          'If this is a member-initializer list in a constructor or '
          'the base class list in a class definition, the colon should '
          'be on the following line.')


  # Check if the line is a header guard.
  is_header_guard = False
  if file_extension == 'h':
    cppvar = GetHeaderGuardCPPVariable(filename)
    if (line.startswith('#ifndef %s' % cppvar) or
        line.startswith('#define %s' % cppvar) or
        line.startswith('#endif  // %s' % cppvar)):
      is_header_guard = True
  # #include lines and header guards can be long, since there's no clean way to
  # split them.
  #
  # URLs can be long too.  It's possible to split these, but it makes them
  # harder to cut&paste.
  #
  # The "$Id:...$" comment may also get very long without it being the
  # developers fault.
  if (not line.startswith('#include') and not is_header_guard and
      not Match(r'^\s*//.*http(s?)://\S*$', line) and
      not Match(r'^// \$Id:.*#[0-9]+ \$$', line)):
    line_width = GetLineWidth(line)
    if line_width > 100:
      error(filename, linenum, 'whitespace/line_length', 4,
            'Lines should very rarely be longer than 100 characters')
    elif line_width > 80:
      error(filename, linenum, 'whitespace/line_length', 2,
            'Lines should be <= 80 characters long')

  if (cleansed_line.count(';') > 1 and
      # for loops are allowed two ;'s (and may run over two lines).
      cleansed_line.find('for') == -1 and
      (GetPreviousNonBlankLine(clean_lines, linenum)[0].find('for') == -1 or
       GetPreviousNonBlankLine(clean_lines, linenum)[0].find(';') != -1) and
      # It's ok to have many commands in a switch case that fits in 1 line
      not ((cleansed_line.find('case ') != -1 or
            cleansed_line.find('default:') != -1) and
           cleansed_line.find('break;') != -1)):
    error(filename, linenum, 'whitespace/newline', 4,
          'More than one command on the same line')

  # Some more style checks
  CheckBraces(filename, clean_lines, linenum, error)
  CheckSpacing(filename, clean_lines, linenum, error)
  CheckCheck(filename, clean_lines, linenum, error)
  if class_state and class_state.classinfo_stack:
    CheckSectionSpacing(filename, clean_lines,
                        class_state.classinfo_stack[-1], linenum, error)


_RE_PATTERN_INCLUDE_NEW_STYLE = re.compile(r'#include +"[^/]+\.h"')
_RE_PATTERN_INCLUDE = re.compile(r'^\s*#\s*include\s*([<"])([^>"]*)[>"].*$')
# Matches the first component of a filename delimited by -s and _s. That is:
#  _RE_FIRST_COMPONENT.match('foo').group(0) == 'foo'
#  _RE_FIRST_COMPONENT.match('foo.cc').group(0) == 'foo'
#  _RE_FIRST_COMPONENT.match('foo-bar_baz.cc').group(0) == 'foo'
#  _RE_FIRST_COMPONENT.match('foo_bar-baz.cc').group(0) == 'foo'
_RE_FIRST_COMPONENT = re.compile(r'^[^-_.]+')


def _DropCommonSuffixes(filename):
  """Drops common suffixes like _test.cc or -inl.h from filename.

  For example:
    >>> _DropCommonSuffixes('foo/foo-inl.h')
    'foo/foo'
    >>> _DropCommonSuffixes('foo/bar/foo.cc')
    'foo/bar/foo'
    >>> _DropCommonSuffixes('foo/foo_internal.h')
    'foo/foo'
    >>> _DropCommonSuffixes('foo/foo_unusualinternal.h')
    'foo/foo_unusualinternal'

  Args:
    filename: The input filename.

  Returns:
    The filename with the common suffix removed.
  """
  for suffix in ('test.cc', 'regtest.cc', 'unittest.cc',
                 'inl.h', 'impl.h', 'internal.h'):
    if (filename.endswith(suffix) and len(filename) > len(suffix) and
        filename[-len(suffix) - 1] in ('-', '_')):
      return filename[:-len(suffix) - 1]
  return os.path.splitext(filename)[0]


def _IsTestFilename(filename):
  """Determines if the given filename has a suffix that identifies it as a test.

  Args:
    filename: The input filename.

  Returns:
    True if 'filename' looks like a test, False otherwise.
  """
  if (filename.endswith('_test.cc') or
      filename.endswith('_unittest.cc') or
      filename.endswith('_regtest.cc')):
    return True
  else:
    return False


def _ClassifyInclude(fileinfo, include, is_system):
  """Figures out what kind of header 'include' is.

  Args:
    fileinfo: The current file cpplint is running over. A FileInfo instance.
    include: The path to a #included file.
    is_system: True if the #include used <> rather than "".

  Returns:
    One of the _XXX_HEADER constants.

  For example:
    >>> _ClassifyInclude(FileInfo('foo/foo.cc'), 'stdio.h', True)
    _C_SYS_HEADER
    >>> _ClassifyInclude(FileInfo('foo/foo.cc'), 'string', True)
    _CPP_SYS_HEADER
    >>> _ClassifyInclude(FileInfo('foo/foo.cc'), 'foo/foo.h', False)
    _LIKELY_MY_HEADER
    >>> _ClassifyInclude(FileInfo('foo/foo_unknown_extension.cc'),
    ...                  'bar/foo_other_ext.h', False)
    _POSSIBLE_MY_HEADER
    >>> _ClassifyInclude(FileInfo('foo/foo.cc'), 'foo/bar.h', False)
    _OTHER_HEADER
  """
  # This is a list of all standard c++ header files, except
  # those already checked for above.
  is_stl_h = include in _STL_HEADERS
  is_cpp_h = is_stl_h or include in _CPP_HEADERS

  if is_system:
    if is_cpp_h:
      return _CPP_SYS_HEADER
    else:
      return _C_SYS_HEADER

  # If the target file and the include we're checking share a
  # basename when we drop common extensions, and the include
  # lives in . , then it's likely to be owned by the target file.
  target_dir, target_base = (
      os.path.split(_DropCommonSuffixes(fileinfo.RepositoryName())))
  include_dir, include_base = os.path.split(_DropCommonSuffixes(include))
  if target_base == include_base and (
      include_dir == target_dir or
      include_dir == os.path.normpath(target_dir + '/../public')):
    return _LIKELY_MY_HEADER

  # If the target and include share some initial basename
  # component, it's possible the target is implementing the
  # include, so it's allowed to be first, but we'll never
  # complain if it's not there.
  target_first_component = _RE_FIRST_COMPONENT.match(target_base)
  include_first_component = _RE_FIRST_COMPONENT.match(include_base)
  if (target_first_component and include_first_component and
      target_first_component.group(0) ==
      include_first_component.group(0)):
    return _POSSIBLE_MY_HEADER

  return _OTHER_HEADER



def CheckIncludeLine(filename, clean_lines, linenum, include_state, error):
  """Check rules that are applicable to #include lines.

  Strings on #include lines are NOT removed from elided line, to make
  certain tasks easier. However, to prevent false positives, checks
  applicable to #include lines in CheckLanguage must be put here.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    include_state: An _IncludeState instance in which the headers are inserted.
    error: The function to call with any errors found.
  """
  fileinfo = FileInfo(filename)

  line = clean_lines.lines[linenum]

  # "include" should use the new style "foo/bar.h" instead of just "bar.h"
  if _RE_PATTERN_INCLUDE_NEW_STYLE.search(line):
    error(filename, linenum, 'build/include', 4,
          'Include the directory when naming .h files')

  # we shouldn't include a file more than once. actually, there are a
  # handful of instances where doing so is okay, but in general it's
  # not.
  match = _RE_PATTERN_INCLUDE.search(line)
  if match:
    include = match.group(2)
    is_system = (match.group(1) == '<')
    if include in include_state:
      error(filename, linenum, 'build/include', 4,
            '"%s" already included at %s:%s' %
            (include, filename, include_state[include]))
    else:
      include_state[include] = linenum

      # We want to ensure that headers appear in the right order:
      # 1) for foo.cc, foo.h  (preferred location)
      # 2) c system files
      # 3) cpp system files
      # 4) for foo.cc, foo.h  (deprecated location)
      # 5) other google headers
      #
      # We classify each include statement as one of those 5 types
      # using a number of techniques. The include_state object keeps
      # track of the highest type seen, and complains if we see a
      # lower type after that.
      error_message = include_state.CheckNextIncludeOrder(
          _ClassifyInclude(fileinfo, include, is_system))
      if error_message:
        error(filename, linenum, 'build/include_order', 4,
              '%s. Should be: %s.h, c system, c++ system, other.' %
              (error_message, fileinfo.BaseName()))
      if not include_state.IsInAlphabeticalOrder(include):
        error(filename, linenum, 'build/include_alpha', 4,
              'Include "%s" not in alphabetical order' % include)

  # Look for any of the stream classes that are part of standard C++.
  match = _RE_PATTERN_INCLUDE.match(line)
  if match:
    include = match.group(2)
    if Match(r'(f|ind|io|i|o|parse|pf|stdio|str|)?stream$', include):
      # Many unit tests use cout, so we exempt them.
      if not _IsTestFilename(filename):
        error(filename, linenum, 'readability/streams', 3,
              'Streams are highly discouraged.')


def _GetTextInside(text, start_pattern):
  """Retrieves all the text between matching open and close parentheses.

  Given a string of lines and a regular expression string, retrieve all the text
  following the expression and between opening punctuation symbols like
  (, [, or {, and the matching close-punctuation symbol. This properly nested
  occurrences of the punctuations, so for the text like
    printf(a(), b(c()));
  a call to _GetTextInside(text, r'printf\(') will return 'a(), b(c())'.
  start_pattern must match string having an open punctuation symbol at the end.

  Args:
    text: The lines to extract text. Its comments and strings must be elided.
           It can be single line and can span multiple lines.
    start_pattern: The regexp string indicating where to start extracting
                   the text.
  Returns:
    The extracted text.
    None if either the opening string or ending punctuation could not be found.
  """
  # TODO(sugawarayu): Audit cpplint.py to see what places could be profitably
  # rewritten to use _GetTextInside (and use inferior regexp matching today).

  # Give opening punctuations to get the matching close-punctuations.
  matching_punctuation = {'(': ')', '{': '}', '[': ']'}
  closing_punctuation = set(matching_punctuation.itervalues())

  # Find the position to start extracting text.
  match = re.search(start_pattern, text, re.M)
  if not match:  # start_pattern not found in text.
    return None
  start_position = match.end(0)

  assert start_position > 0, (
      'start_pattern must ends with an opening punctuation.')
  assert text[start_position - 1] in matching_punctuation, (
      'start_pattern must ends with an opening punctuation.')
  # Stack of closing punctuations we expect to have in text after position.
  punctuation_stack = [matching_punctuation[text[start_position - 1]]]
  position = start_position
  while punctuation_stack and position < len(text):
    if text[position] == punctuation_stack[-1]:
      punctuation_stack.pop()
    elif text[position] in closing_punctuation:
      # A closing punctuation without matching opening punctuations.
      return None
    elif text[position] in matching_punctuation:
      punctuation_stack.append(matching_punctuation[text[position]])
    position += 1
  if punctuation_stack:
    # Opening punctuations left without matching close-punctuations.
    return None
  # punctuations match.
  return text[start_position:position - 1]


def CheckLanguage(filename, clean_lines, linenum, file_extension, include_state,
                  error):
  """Checks rules from the 'C++ language rules' section of cppguide.html.

  Some of these rules are hard to test (function overloading, using
  uint32 inappropriately), but we do the best we can.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    file_extension: The extension (without the dot) of the filename.
    include_state: An _IncludeState instance in which the headers are inserted.
    error: The function to call with any errors found.
  """
  # If the line is empty or consists of entirely a comment, no need to
  # check it.
  line = clean_lines.elided[linenum]
  if not line:
    return

  match = _RE_PATTERN_INCLUDE.search(line)
  if match:
    CheckIncludeLine(filename, clean_lines, linenum, include_state, error)
    return

  # Create an extended_line, which is the concatenation of the current and
  # next lines, for more effective checking of code that may span more than one
  # line.
  if linenum + 1 < clean_lines.NumLines():
    extended_line = line + clean_lines.elided[linenum + 1]
  else:
    extended_line = line

  # Make Windows paths like Unix.
  fullname = os.path.abspath(filename).replace('\\', '/')

  # TODO(unknown): figure out if they're using default arguments in fn proto.

  # Check for non-const references in functions.  This is tricky because &
  # is also used to take the address of something.  We allow <> for templates,
  # (ignoring whatever is between the braces) and : for classes.
  # These are complicated re's.  They try to capture the following:
  # paren (for fn-prototype start), typename, &, varname.  For the const
  # version, we're willing for const to be before typename or after
  # Don't check the implementation on same line.
  fnline = line.split('{', 1)[0]
  if (len(re.findall(r'\([^()]*\b(?:[\w:]|<[^()]*>)+(\s?&|&\s?)\w+', fnline)) >
      len(re.findall(r'\([^()]*\bconst\s+(?:typename\s+)?(?:struct\s+)?'
                     r'(?:[\w:]|<[^()]*>)+(\s?&|&\s?)\w+', fnline)) +
      len(re.findall(r'\([^()]*\b(?:[\w:]|<[^()]*>)+\s+const(\s?&|&\s?)[\w]+',
                     fnline))):

    # We allow non-const references in a few standard places, like functions
    # called "swap()" or iostream operators like "<<" or ">>".
    if not Search(
        r'(swap|Swap|operator[<>][<>])\s*\(\s*(?:[\w:]|<.*>)+\s*&',
        fnline):
      error(filename, linenum, 'runtime/references', 2,
            'Is this a non-const reference? '
            'If so, make const or use a pointer.')

  # Check to see if they're using an conversion function cast.
  # I just try to capture the most common basic types, though there are more.
  # Parameterless conversion functions, such as bool(), are allowed as they are
  # probably a member operator declaration or default constructor.
  match = Search(
      r'(\bnew\s+)?\b'  # Grab 'new' operator, if it's there
      r'(int|float|double|bool|char|int32|uint32|int64|uint64)\([^)]', line)
  if match:
    # gMock methods are defined using some variant of MOCK_METHODx(name, type)
    # where type may be float(), int(string), etc.  Without context they are
    # virtually indistinguishable from int(x) casts. Likewise, gMock's
    # MockCallback takes a template parameter of the form return_type(arg_type),
    # which looks much like the cast we're trying to detect.
    if (match.group(1) is None and  # If new operator, then this isn't a cast
        not (Match(r'^\s*MOCK_(CONST_)?METHOD\d+(_T)?\(', line) or
             Match(r'^\s*MockCallback<.*>', line))):
      error(filename, linenum, 'readability/casting', 4,
            'Using deprecated casting style.  '
            'Use static_cast<%s>(...) instead' %
            match.group(2))

  CheckCStyleCast(filename, linenum, line, clean_lines.raw_lines[linenum],
                  'static_cast',
                  r'\((int|float|double|bool|char|u?int(16|32|64))\)', error)

  # This doesn't catch all cases. Consider (const char * const)"hello".
  #
  # (char *) "foo" should always be a const_cast (reinterpret_cast won't
  # compile).
  if CheckCStyleCast(filename, linenum, line, clean_lines.raw_lines[linenum],
                     'const_cast', r'\((char\s?\*+\s?)\)\s*"', error):
    pass
  else:
    # Check pointer casts for other than string constants
    CheckCStyleCast(filename, linenum, line, clean_lines.raw_lines[linenum],
                    'reinterpret_cast', r'\((\w+\s?\*+\s?)\)', error)

  # In addition, we look for people taking the address of a cast.  This
  # is dangerous -- casts can assign to temporaries, so the pointer doesn't
  # point where you think.
  if Search(
      r'(&\([^)]+\)[\w(])|(&(static|dynamic|reinterpret)_cast\b)', line):
    error(filename, linenum, 'runtime/casting', 4,
          ('Are you taking an address of a cast?  '
           'This is dangerous: could be a temp var.  '
           'Take the address before doing the cast, rather than after'))

  # Check for people declaring static/global STL strings at the top level.
  # This is dangerous because the C++ language does not guarantee that
  # globals with constructors are initialized before the first access.
  match = Match(
      r'((?:|static +)(?:|const +))string +([a-zA-Z0-9_:]+)\b(.*)',
      line)
  # Make sure it's not a function.
  # Function template specialization looks like: "string foo<Type>(...".
  # Class template definitions look like: "string Foo<Type>::Method(...".
  if match and not Match(r'\s*(<.*>)?(::[a-zA-Z0-9_]+)?\s*\(([^"]|$)',
                         match.group(3)):
    error(filename, linenum, 'runtime/string', 4,
          'For a static/global string constant, use a C style string instead: '
          '"%schar %s[]".' %
          (match.group(1), match.group(2)))

  # Check that we're not using RTTI outside of testing code.
  if Search(r'\bdynamic_cast<', line) and not _IsTestFilename(filename):
    error(filename, linenum, 'runtime/rtti', 5,
          'Do not use dynamic_cast<>.  If you need to cast within a class '
          "hierarchy, use static_cast<> to upcast.  Google doesn't support "
          'RTTI.')

  if Search(r'\b([A-Za-z0-9_]*_)\(\1\)', line):
    error(filename, linenum, 'runtime/init', 4,
          'You seem to be initializing a member variable with itself.')

  if file_extension == 'h':
    # TODO(unknown): check that 1-arg constructors are explicit.
    #                How to tell it's a constructor?
    #                (handled in CheckForNonStandardConstructs for now)
    # TODO(unknown): check that classes have DISALLOW_EVIL_CONSTRUCTORS
    #                (level 1 error)
    pass

  # Check if people are using the verboten C basic types.  The only exception
  # we regularly allow is "unsigned short port" for port.
  if Search(r'\bshort port\b', line):
    if not Search(r'\bunsigned short port\b', line):
      error(filename, linenum, 'runtime/int', 4,
            'Use "unsigned short" for ports, not "short"')
  else:
    match = Search(r'\b(short|long(?! +double)|long long)\b', line)
    if match:
      error(filename, linenum, 'runtime/int', 4,
            'Use int16/int64/etc, rather than the C type %s' % match.group(1))

  # When snprintf is used, the second argument shouldn't be a literal.
  match = Search(r'snprintf\s*\(([^,]*),\s*([0-9]*)\s*,', line)
  if match and match.group(2) != '0':
    # If 2nd arg is zero, snprintf is used to calculate size.
    error(filename, linenum, 'runtime/printf', 3,
          'If you can, use sizeof(%s) instead of %s as the 2nd arg '
          'to snprintf.' % (match.group(1), match.group(2)))

  # Check if some verboten C functions are being used.
  if Search(r'\bsprintf\b', line):
    error(filename, linenum, 'runtime/printf', 5,
          'Never use sprintf.  Use snprintf instead.')
  match = Search(r'\b(strcpy|strcat)\b', line)
  if match:
    error(filename, linenum, 'runtime/printf', 4,
          'Almost always, snprintf is better than %s' % match.group(1))

  if Search(r'\bsscanf\b', line):
    error(filename, linenum, 'runtime/printf', 1,
          'sscanf can be ok, but is slow and can overflow buffers.')

  # Check if some verboten operator overloading is going on
  # TODO(unknown): catch out-of-line unary operator&:
  #   class X {};
  #   int operator&(const X& x) { return 42; }  // unary operator&
  # The trick is it's hard to tell apart from binary operator&:
  #   class Y { int operator&(const Y& x) { return 23; } }; // binary operator&
  if Search(r'\boperator\s*&\s*\(\s*\)', line):
    error(filename, linenum, 'runtime/operator', 4,
          'Unary operator& is dangerous.  Do not use it.')

  # Check for suspicious usage of "if" like
  # } if (a == b) {
  if Search(r'\}\s*if\s*\(', line):
    error(filename, linenum, 'readability/braces', 4,
          'Did you mean "else if"? If not, start a new line for "if".')

  # Check for potential format string bugs like printf(foo).
  # We constrain the pattern not to pick things like DocidForPrintf(foo).
  # Not perfect but it can catch printf(foo.c_str()) and printf(foo->c_str())
  # TODO(sugawarayu): Catch the following case. Need to change the calling
  # convention of the whole function to process multiple line to handle it.
  #   printf(
  #       boy_this_is_a_really_long_variable_that_cannot_fit_on_the_prev_line);
  printf_args = _GetTextInside(line, r'(?i)\b(string)?printf\s*\(')
  if printf_args:
    match = Match(r'([\w.\->()]+)$', printf_args)
    if match:
      function_name = re.search(r'\b((?:string)?printf)\s*\(',
                                line, re.I).group(1)
      error(filename, linenum, 'runtime/printf', 4,
            'Potential format string bug. Do %s("%%s", %s) instead.'
            % (function_name, match.group(1)))

  # Check for potential memset bugs like memset(buf, sizeof(buf), 0).
  match = Search(r'memset\s*\(([^,]*),\s*([^,]*),\s*0\s*\)', line)
  if match and not Match(r"^''|-?[0-9]+|0x[0-9A-Fa-f]$", match.group(2)):
    error(filename, linenum, 'runtime/memset', 4,
          'Did you mean "memset(%s, 0, %s)"?'
          % (match.group(1), match.group(2)))

  if Search(r'\busing namespace\b', line):
    error(filename, linenum, 'build/namespaces', 5,
          'Do not use namespace using-directives.  '
          'Use using-declarations instead.')

  # Detect variable-length arrays.
  match = Match(r'\s*(.+::)?(\w+) [a-z]\w*\[(.+)];', line)
  if (match and match.group(2) != 'return' and match.group(2) != 'delete' and
      match.group(3).find(']') == -1):
    # Split the size using space and arithmetic operators as delimiters.
    # If any of the resulting tokens are not compile time constants then
    # report the error.
    tokens = re.split(r'\s|\+|\-|\*|\/|<<|>>]', match.group(3))
    is_const = True
    skip_next = False
    for tok in tokens:
      if skip_next:
        skip_next = False
        continue

      if Search(r'sizeof\(.+\)', tok): continue
      if Search(r'arraysize\(\w+\)', tok): continue

      tok = tok.lstrip('(')
      tok = tok.rstrip(')')
      if not tok: continue
      if Match(r'\d+', tok): continue
      if Match(r'0[xX][0-9a-fA-F]+', tok): continue
      if Match(r'k[A-Z0-9]\w*', tok): continue
      if Match(r'(.+::)?k[A-Z0-9]\w*', tok): continue
      if Match(r'(.+::)?[A-Z][A-Z0-9_]*', tok): continue
      # A catch all for tricky sizeof cases, including 'sizeof expression',
      # 'sizeof(*type)', 'sizeof(const type)', 'sizeof(struct StructName)'
      # requires skipping the next token because we split on ' ' and '*'.
      if tok.startswith('sizeof'):
        skip_next = True
        continue
      is_const = False
      break
    if not is_const:
      error(filename, linenum, 'runtime/arrays', 1,
            'Do not use variable-length arrays.  Use an appropriately named '
            "('k' followed by CamelCase) compile-time constant for the size.")

  # If DISALLOW_EVIL_CONSTRUCTORS, DISALLOW_COPY_AND_ASSIGN, or
  # DISALLOW_IMPLICIT_CONSTRUCTORS is present, then it should be the last thing
  # in the class declaration.
  match = Match(
      (r'\s*'
       r'(DISALLOW_(EVIL_CONSTRUCTORS|COPY_AND_ASSIGN|IMPLICIT_CONSTRUCTORS))'
       r'\(.*\);$'),
      line)
  if match and linenum + 1 < clean_lines.NumLines():
    next_line = clean_lines.elided[linenum + 1]
    # We allow some, but not all, declarations of variables to be present
    # in the statement that defines the class.  The [\w\*,\s]* fragment of
    # the regular expression below allows users to declare instances of
    # the class or pointers to instances, but not less common types such
    # as function pointers or arrays.  It's a tradeoff between allowing
    # reasonable code and avoiding trying to parse more C++ using regexps.
    if not Search(r'^\s*}[\w\*,\s]*;', next_line):
      error(filename, linenum, 'readability/constructors', 3,
            match.group(1) + ' should be the last thing in the class')

  # Check for use of unnamed namespaces in header files.  Registration
  # macros are typically OK, so we allow use of "namespace {" on lines
  # that end with backslashes.
  if (file_extension == 'h'
      and Search(r'\bnamespace\s*{', line)
      and line[-1] != '\\'):
    error(filename, linenum, 'build/namespaces', 4,
          'Do not use unnamed namespaces in header files.  See '
          'http://google-styleguide.googlecode.com/svn/trunk/cppguide.xml#Namespaces'
          ' for more information.')


def CheckCStyleCast(filename, linenum, line, raw_line, cast_type, pattern,
                    error):
  """Checks for a C-style cast by looking for the pattern.

  This also handles sizeof(type) warnings, due to similarity of content.

  Args:
    filename: The name of the current file.
    linenum: The number of the line to check.
    line: The line of code to check.
    raw_line: The raw line of code to check, with comments.
    cast_type: The string for the C++ cast to recommend.  This is either
      reinterpret_cast, static_cast, or const_cast, depending.
    pattern: The regular expression used to find C-style casts.
    error: The function to call with any errors found.

  Returns:
    True if an error was emitted.
    False otherwise.
  """
  match = Search(pattern, line)
  if not match:
    return False

  # e.g., sizeof(int)
  sizeof_match = Match(r'.*sizeof\s*$', line[0:match.start(1) - 1])
  if sizeof_match:
    error(filename, linenum, 'runtime/sizeof', 1,
          'Using sizeof(type).  Use sizeof(varname) instead if possible')
    return True

  remainder = line[match.end(0):]

  # The close paren is for function pointers as arguments to a function.
  # eg, void foo(void (*bar)(int));
  # The semicolon check is a more basic function check; also possibly a
  # function pointer typedef.
  # eg, void foo(int); or void foo(int) const;
  # The equals check is for function pointer assignment.
  # eg, void *(*foo)(int) = ...
  # The > is for MockCallback<...> ...
  #
  # Right now, this will only catch cases where there's a single argument, and
  # it's unnamed.  It should probably be expanded to check for multiple
  # arguments with some unnamed.
  function_match = Match(r'\s*(\)|=|(const)?\s*(;|\{|throw\(\)|>))', remainder)
  if function_match:
    if (not function_match.group(3) or
        function_match.group(3) == ';' or
        ('MockCallback<' not in raw_line and
         '/*' not in raw_line)):
      error(filename, linenum, 'readability/function', 3,
            'All parameters should be named in a function')
    return True

  # At this point, all that should be left is actual casts.
  error(filename, linenum, 'readability/casting', 4,
        'Using C-style cast.  Use %s<%s>(...) instead' %
        (cast_type, match.group(1)))

  return True


_HEADERS_CONTAINING_TEMPLATES = (
    ('<deque>', ('deque',)),
    ('<functional>', ('unary_function', 'binary_function',
                      'plus', 'minus', 'multiplies', 'divides', 'modulus',
                      'negate',
                      'equal_to', 'not_equal_to', 'greater', 'less',
                      'greater_equal', 'less_equal',
                      'logical_and', 'logical_or', 'logical_not',
                      'unary_negate', 'not1', 'binary_negate', 'not2',
                      'bind1st', 'bind2nd',
                      'pointer_to_unary_function',
                      'pointer_to_binary_function',
                      'ptr_fun',
                      'mem_fun_t', 'mem_fun', 'mem_fun1_t', 'mem_fun1_ref_t',
                      'mem_fun_ref_t',
                      'const_mem_fun_t', 'const_mem_fun1_t',
                      'const_mem_fun_ref_t', 'const_mem_fun1_ref_t',
                      'mem_fun_ref',
                     )),
    ('<limits>', ('numeric_limits',)),
    ('<list>', ('list',)),
    ('<map>', ('map', 'multimap',)),
    ('<memory>', ('allocator',)),
    ('<queue>', ('queue', 'priority_queue',)),
    ('<set>', ('set', 'multiset',)),
    ('<stack>', ('stack',)),
    ('<string>', ('char_traits', 'basic_string',)),
    ('<utility>', ('pair',)),
    ('<vector>', ('vector',)),

    # gcc extensions.
    # Note: std::hash is their hash, ::hash is our hash
    ('<hash_map>', ('hash_map', 'hash_multimap',)),
    ('<hash_set>', ('hash_set', 'hash_multiset',)),
    ('<slist>', ('slist',)),
    )

_RE_PATTERN_STRING = re.compile(r'\bstring\b')

_re_pattern_algorithm_header = []
for _template in ('copy', 'max', 'min', 'min_element', 'sort', 'swap',
                  'transform'):
  # Match max<type>(..., ...), max(..., ...), but not foo->max, foo.max or
  # type::max().
  _re_pattern_algorithm_header.append(
      (re.compile(r'[^>.]\b' + _template + r'(<.*?>)?\([^\)]'),
       _template,
       '<algorithm>'))

_re_pattern_templates = []
for _header, _templates in _HEADERS_CONTAINING_TEMPLATES:
  for _template in _templates:
    _re_pattern_templates.append(
        (re.compile(r'(\<|\b)' + _template + r'\s*\<'),
         _template + '<>',
         _header))


def FilesBelongToSameModule(filename_cc, filename_h):
  """Check if these two filenames belong to the same module.

  The concept of a 'module' here is a as follows:
  foo.h, foo-inl.h, foo.cc, foo_test.cc and foo_unittest.cc belong to the
  same 'module' if they are in the same directory.
  some/path/public/xyzzy and some/path/internal/xyzzy are also considered
  to belong to the same module here.

  If the filename_cc contains a longer path than the filename_h, for example,
  '/absolute/path/to/base/sysinfo.cc', and this file would include
  'base/sysinfo.h', this function also produces the prefix needed to open the
  header. This is used by the caller of this function to more robustly open the
  header file. We don't have access to the real include paths in this context,
  so we need this guesswork here.

  Known bugs: tools/base/bar.cc and base/bar.h belong to the same module
  according to this implementation. Because of this, this function gives
  some false positives. This should be sufficiently rare in practice.

  Args:
    filename_cc: is the path for the .cc file
    filename_h: is the path for the header path

  Returns:
    Tuple with a bool and a string:
    bool: True if filename_cc and filename_h belong to the same module.
    string: the additional prefix needed to open the header file.
  """

  if not filename_cc.endswith('.cc'):
    return (False, '')
  filename_cc = filename_cc[:-len('.cc')]
  if filename_cc.endswith('_unittest'):
    filename_cc = filename_cc[:-len('_unittest')]
  elif filename_cc.endswith('_test'):
    filename_cc = filename_cc[:-len('_test')]
  filename_cc = filename_cc.replace('/public/', '/')
  filename_cc = filename_cc.replace('/internal/', '/')

  if not filename_h.endswith('.h'):
    return (False, '')
  filename_h = filename_h[:-len('.h')]
  if filename_h.endswith('-inl'):
    filename_h = filename_h[:-len('-inl')]
  filename_h = filename_h.replace('/public/', '/')
  filename_h = filename_h.replace('/internal/', '/')

  files_belong_to_same_module = filename_cc.endswith(filename_h)
  common_path = ''
  if files_belong_to_same_module:
    common_path = filename_cc[:-len(filename_h)]
  return files_belong_to_same_module, common_path


def UpdateIncludeState(filename, include_state, io=codecs):
  """Fill up the include_state with new includes found from the file.

  Args:
    filename: the name of the header to read.
    include_state: an _IncludeState instance in which the headers are inserted.
    io: The io factory to use to read the file. Provided for testability.

  Returns:
    True if a header was succesfully added. False otherwise.
  """
  headerfile = None
  try:
    headerfile = io.open(filename, 'r', 'utf8', 'replace')
  except IOError:
    return False
  linenum = 0
  for line in headerfile:
    linenum += 1
    clean_line = CleanseComments(line)
    match = _RE_PATTERN_INCLUDE.search(clean_line)
    if match:
      include = match.group(2)
      # The value formatting is cute, but not really used right now.
      # What matters here is that the key is in include_state.
      include_state.setdefault(include, '%s:%d' % (filename, linenum))
  return True


def CheckForIncludeWhatYouUse(filename, clean_lines, include_state, error,
                              io=codecs):
  """Reports for missing stl includes.

  This function will output warnings to make sure you are including the headers
  necessary for the stl containers and functions that you use. We only give one
  reason to include a header. For example, if you use both equal_to<> and
  less<> in a .h file, only one (the latter in the file) of these will be
  reported as a reason to include the <functional>.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    include_state: An _IncludeState instance.
    error: The function to call with any errors found.
    io: The IO factory to use to read the header file. Provided for unittest
        injection.
  """
  required = {}  # A map of header name to linenumber and the template entity.
                 # Example of required: { '<functional>': (1219, 'less<>') }

  for linenum in xrange(clean_lines.NumLines()):
    line = clean_lines.elided[linenum]
    if not line or line[0] == '#':
      continue

    # String is special -- it is a non-templatized type in STL.
    matched = _RE_PATTERN_STRING.search(line)
    if matched:
      # Don't warn about strings in non-STL namespaces:
      # (We check only the first match per line; good enough.)
      prefix = line[:matched.start()]
      if prefix.endswith('std::') or not prefix.endswith('::'):
        required['<string>'] = (linenum, 'string')

    for pattern, template, header in _re_pattern_algorithm_header:
      if pattern.search(line):
        required[header] = (linenum, template)

    # The following function is just a speed up, no semantics are changed.
    if not '<' in line:  # Reduces the cpu time usage by skipping lines.
      continue

    for pattern, template, header in _re_pattern_templates:
      if pattern.search(line):
        required[header] = (linenum, template)

  # The policy is that if you #include something in foo.h you don't need to
  # include it again in foo.cc. Here, we will look at possible includes.
  # Let's copy the include_state so it is only messed up within this function.
  include_state = include_state.copy()

  # Did we find the header for this file (if any) and succesfully load it?
  header_found = False

  # Use the absolute path so that matching works properly.
  abs_filename = FileInfo(filename).FullName()

  # For Emacs's flymake.
  # If cpplint is invoked from Emacs's flymake, a temporary file is generated
  # by flymake and that file name might end with '_flymake.cc'. In that case,
  # restore original file name here so that the corresponding header file can be
  # found.
  # e.g. If the file name is 'foo_flymake.cc', we should search for 'foo.h'
  # instead of 'foo_flymake.h'
  abs_filename = re.sub(r'_flymake\.cc$', '.cc', abs_filename)

  # include_state is modified during iteration, so we iterate over a copy of
  # the keys.
  header_keys = include_state.keys()
  for header in header_keys:
    (same_module, common_path) = FilesBelongToSameModule(abs_filename, header)
    fullpath = common_path + header
    if same_module and UpdateIncludeState(fullpath, include_state, io):
      header_found = True

  # If we can't find the header file for a .cc, assume it's because we don't
  # know where to look. In that case we'll give up as we're not sure they
  # didn't include it in the .h file.
  # TODO(unknown): Do a better job of finding .h files so we are confident that
  # not having the .h file means there isn't one.
  if filename.endswith('.cc') and not header_found:
    return

  # All the lines have been processed, report the errors found.
  for required_header_unstripped in required:
    template = required[required_header_unstripped][1]
    if required_header_unstripped.strip('<>"') not in include_state:
      error(filename, required[required_header_unstripped][0],
            'build/include_what_you_use', 4,
            'Add #include ' + required_header_unstripped + ' for ' + template)


_RE_PATTERN_EXPLICIT_MAKEPAIR = re.compile(r'\bmake_pair\s*<')


def CheckMakePairUsesDeduction(filename, clean_lines, linenum, error):
  """Check that make_pair's template arguments are deduced.

  G++ 4.6 in C++0x mode fails badly if make_pair's template arguments are
  specified explicitly, and such use isn't intended in any case.

  Args:
    filename: The name of the current file.
    clean_lines: A CleansedLines instance containing the file.
    linenum: The number of the line to check.
    error: The function to call with any errors found.
  """
  raw = clean_lines.raw_lines
  line = raw[linenum]
  match = _RE_PATTERN_EXPLICIT_MAKEPAIR.search(line)
  if match:
    error(filename, linenum, 'build/explicit_make_pair',
          4,  # 4 = high confidence
          'Omit template arguments from make_pair OR use pair directly OR'
          ' if appropriate, construct a pair directly')


def ProcessLine(filename, file_extension,
                clean_lines, line, include_state, function_state,
                class_state, error, extra_check_functions=[]):
  """Processes a single line in the file.

  Args:
    filename: Filename of the file that is being processed.
    file_extension: The extension (dot not included) of the file.
    clean_lines: An array of strings, each representing a line of the file,
                 with comments stripped.
    line: Number of line being processed.
    include_state: An _IncludeState instance in which the headers are inserted.
    function_state: A _FunctionState instance which counts function lines, etc.
    class_state: A _ClassState instance which maintains information about
                 the current stack of nested class declarations being parsed.
    error: A callable to which errors are reported, which takes 4 arguments:
           filename, line number, error level, and message
    extra_check_functions: An array of additional check functions that will be
                           run on each source line. Each function takes 4
                           arguments: filename, clean_lines, line, error
  """
  raw_lines = clean_lines.raw_lines
  ParseNolintSuppressions(filename, raw_lines[line], line, error)
  CheckForFunctionLengths(filename, clean_lines, line, function_state, error)
  CheckForMultilineCommentsAndStrings(filename, clean_lines, line, error)
  CheckStyle(filename, clean_lines, line, file_extension, class_state, error)
  CheckLanguage(filename, clean_lines, line, file_extension, include_state,
                error)
  CheckForNonStandardConstructs(filename, clean_lines, line,
                                class_state, error)
  CheckPosixThreading(filename, clean_lines, line, error)
  CheckInvalidIncrement(filename, clean_lines, line, error)
  CheckMakePairUsesDeduction(filename, clean_lines, line, error)
  for check_fn in extra_check_functions:
    check_fn(filename, clean_lines, line, error)

def ProcessFileData(filename, file_extension, lines, error,
                    extra_check_functions=[]):
  """Performs lint checks and reports any errors to the given error function.

  Args:
    filename: Filename of the file that is being processed.
    file_extension: The extension (dot not included) of the file.
    lines: An array of strings, each representing a line of the file, with the
           last element being empty if the file is terminated with a newline.
    error: A callable to which errors are reported, which takes 4 arguments:
           filename, line number, error level, and message
    extra_check_functions: An array of additional check functions that will be
                           run on each source line. Each function takes 4
                           arguments: filename, clean_lines, line, error
  """
  lines = (['// marker so line numbers and indices both start at 1'] + lines +
           ['// marker so line numbers end in a known way'])

  include_state = _IncludeState()
  function_state = _FunctionState()
  class_state = _ClassState()

  ResetNolintSuppressions()

  CheckForCopyright(filename, lines, error)

  if file_extension == 'h':
    CheckForHeaderGuard(filename, lines, error)

  RemoveMultiLineComments(filename, lines, error)
  clean_lines = CleansedLines(lines)
  for line in xrange(clean_lines.NumLines()):
    ProcessLine(filename, file_extension, clean_lines, line,
                include_state, function_state, class_state, error,
                extra_check_functions)
  class_state.CheckFinished(filename, error)

  CheckForIncludeWhatYouUse(filename, clean_lines, include_state, error)

  # We check here rather than inside ProcessLine so that we see raw
  # lines rather than "cleaned" lines.
  CheckForUnicodeReplacementCharacters(filename, lines, error)

  CheckForNewlineAtEOF(filename, lines, error)

def ProcessFile(filename, vlevel, extra_check_functions=[]):
  """Does google-lint on a single file.

  Args:
    filename: The name of the file to parse.

    vlevel: The level of errors to report.  Every error of confidence
    >= verbose_level will be reported.  0 is a good default.

    extra_check_functions: An array of additional check functions that will be
                           run on each source line. Each function takes 4
                           arguments: filename, clean_lines, line, error
  """

  _SetVerboseLevel(vlevel)

  try:
    # Support the UNIX convention of using "-" for stdin.  Note that
    # we are not opening the file with universal newline support
    # (which codecs doesn't support anyway), so the resulting lines do
    # contain trailing '\r' characters if we are reading a file that
    # has CRLF endings.
    # If after the split a trailing '\r' is present, it is removed
    # below. If it is not expected to be present (i.e. os.linesep !=
    # '\r\n' as in Windows), a warning is issued below if this file
    # is processed.

    if filename == '-':
      lines = codecs.StreamReaderWriter(sys.stdin,
                                        codecs.getreader('utf8'),
                                        codecs.getwriter('utf8'),
                                        'replace').read().split('\n')
    else:
      lines = codecs.open(filename, 'r', 'utf8', 'replace').read().split('\n')

    carriage_return_found = False
    # Remove trailing '\r'.
    for linenum in range(len(lines)):
      if lines[linenum].endswith('\r'):
        lines[linenum] = lines[linenum].rstrip('\r')
        carriage_return_found = True

  except IOError:
    sys.stderr.write(
        "Skipping input '%s': Can't open for reading\n" % filename)
    return

  # Note, if no dot is found, this will give the entire filename as the ext.
  file_extension = filename[filename.rfind('.') + 1:]

  # When reading from stdin, the extension is unknown, so no cpplint tests
  # should rely on the extension.
  if (filename != '-' and file_extension != 'cc' and file_extension != 'h'
      and file_extension != 'cpp'):
    sys.stderr.write('Ignoring %s; not a .cc or .h file\n' % filename)
  else:
    ProcessFileData(filename, file_extension, lines, Error,
                    extra_check_functions)
    if carriage_return_found and os.linesep != '\r\n':
      # Use 0 for linenum since outputting only one error for potentially
      # several lines.
      Error(filename, 0, 'whitespace/newline', 1,
            'One or more unexpected \\r (^M) found;'
            'better to use only a \\n')

  sys.stderr.write('Done processing %s\n' % filename)


def PrintUsage(message):
  """Prints a brief usage string and exits, optionally with an error message.

  Args:
    message: The optional error message.
  """
  sys.stderr.write(_USAGE)
  if message:
    sys.exit('\nFATAL ERROR: ' + message)
  else:
    sys.exit(1)


def PrintCategories():
  """Prints a list of all the error-categories used by error messages.

  These are the categories used to filter messages via --filter.
  """
  sys.stderr.write(''.join('  %s\n' % cat for cat in _ERROR_CATEGORIES))
  sys.exit(0)


def ParseArguments(args):
  """Parses the command line arguments.

  This may set the output format and verbosity level as side-effects.

  Args:
    args: The command line arguments:

  Returns:
    The list of filenames to lint.
  """
  try:
    (opts, filenames) = getopt.getopt(args, '', ['help', 'output=', 'verbose=',
                                                 'counting=',
                                                 'filter='])
  except getopt.GetoptError:
    PrintUsage('Invalid arguments.')

  verbosity = _VerboseLevel()
  output_format = _OutputFormat()
  filters = ''
  counting_style = ''

  for (opt, val) in opts:
    if opt == '--help':
      PrintUsage(None)
    elif opt == '--output':
      if not val in ('emacs', 'vs7'):
        PrintUsage('The only allowed output formats are emacs and vs7.')
      output_format = val
    elif opt == '--verbose':
      verbosity = int(val)
    elif opt == '--filter':
      filters = val
      if not filters:
        PrintCategories()
    elif opt == '--counting':
      if val not in ('total', 'toplevel', 'detailed'):
        PrintUsage('Valid counting options are total, toplevel, and detailed')
      counting_style = val

  if not filenames:
    PrintUsage('No files were specified.')

  _SetOutputFormat(output_format)
  _SetVerboseLevel(verbosity)
  _SetFilters(filters)
  _SetCountingStyle(counting_style)

  return filenames


def main():
  filenames = ParseArguments(sys.argv[1:])

  # Change stderr to write with replacement characters so we don't die
  # if we try to print something containing non-ASCII characters.
  sys.stderr = codecs.StreamReaderWriter(sys.stderr,
                                         codecs.getreader('utf8'),
                                         codecs.getwriter('utf8'),
                                         'replace')

  _cpplint_state.ResetErrorCounts()
  for filename in filenames:
    ProcessFile(filename, _cpplint_state.verbose_level)
  _cpplint_state.PrintErrorCounts()

  sys.exit(_cpplint_state.error_count > 0)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = cpplint_unittest
#!/usr/bin/python2.4
# -*- coding: utf-8; -*-
#
# Copyright (c) 2009 Google Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#    * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Unit test for cpplint.py."""

# TODO(unknown): Add a good test that tests UpdateIncludeState.

import codecs
import os
import random
import re
import unittest
import cpplint


# This class works as an error collector and replaces cpplint.Error
# function for the unit tests.  We also verify each category we see
# is in cpplint._ERROR_CATEGORIES, to help keep that list up to date.
class ErrorCollector:
  # These are a global list, covering all categories seen ever.
  _ERROR_CATEGORIES = cpplint._ERROR_CATEGORIES
  _SEEN_ERROR_CATEGORIES = {}

  def __init__(self, assert_fn):
    """assert_fn: a function to call when we notice a problem."""
    self._assert_fn = assert_fn
    self._errors = []
    cpplint.ResetNolintSuppressions()

  def __call__(self, unused_filename, linenum,
               category, confidence, message):
    self._assert_fn(category in self._ERROR_CATEGORIES,
                    'Message "%s" has category "%s",'
                    ' which is not in _ERROR_CATEGORIES' % (message, category))
    self._SEEN_ERROR_CATEGORIES[category] = 1
    if cpplint._ShouldPrintError(category, confidence, linenum):
      self._errors.append('%s  [%s] [%d]' % (message, category, confidence))

  def Results(self):
    if len(self._errors) < 2:
      return ''.join(self._errors)  # Most tests expect to have a string.
    else:
      return self._errors  # Let's give a list if there is more than one.

  def ResultList(self):
    return self._errors

  def VerifyAllCategoriesAreSeen(self):
    """Fails if there's a category in _ERROR_CATEGORIES - _SEEN_ERROR_CATEGORIES.

    This should only be called after all tests are run, so
    _SEEN_ERROR_CATEGORIES has had a chance to fully populate.  Since
    this isn't called from within the normal unittest framework, we
    can't use the normal unittest assert macros.  Instead we just exit
    when we see an error.  Good thing this test is always run last!
    """
    for category in self._ERROR_CATEGORIES:
      if category not in self._SEEN_ERROR_CATEGORIES:
        import sys
        sys.exit('FATAL ERROR: There are no tests for category "%s"' % category)

  def RemoveIfPresent(self, substr):
    for (index, error) in enumerate(self._errors):
      if error.find(substr) != -1:
        self._errors = self._errors[0:index] + self._errors[(index + 1):]
        break


# This class is a lame mock of codecs. We do not verify filename, mode, or
# encoding, but for the current use case it is not needed.
class MockIo:
  def __init__(self, mock_file):
    self.mock_file = mock_file

  def open(self, unused_filename, unused_mode, unused_encoding, _):  # NOLINT
    # (lint doesn't like open as a method name)
    return self.mock_file


class CpplintTestBase(unittest.TestCase):
  """Provides some useful helper functions for cpplint tests."""

  # Perform lint on single line of input and return the error message.
  def PerformSingleLineLint(self, code):
    error_collector = ErrorCollector(self.assert_)
    lines = code.split('\n')
    cpplint.RemoveMultiLineComments('foo.h', lines, error_collector)
    clean_lines = cpplint.CleansedLines(lines)
    include_state = cpplint._IncludeState()
    function_state = cpplint._FunctionState()
    class_state = cpplint._ClassState()
    cpplint.ProcessLine('foo.cc', 'cc', clean_lines, 0,
                        include_state, function_state,
                        class_state, error_collector)
    # Single-line lint tests are allowed to fail the 'unlintable function'
    # check.
    error_collector.RemoveIfPresent(
        'Lint failed to find start of function body.')
    return error_collector.Results()

  # Perform lint over multiple lines and return the error message.
  def PerformMultiLineLint(self, code):
    error_collector = ErrorCollector(self.assert_)
    lines = code.split('\n')
    cpplint.RemoveMultiLineComments('foo.h', lines, error_collector)
    lines = cpplint.CleansedLines(lines)
    class_state = cpplint._ClassState()
    for i in xrange(lines.NumLines()):
      cpplint.CheckStyle('foo.h', lines, i, 'h', class_state,
                         error_collector)
      cpplint.CheckForNonStandardConstructs('foo.h', lines, i, class_state,
                                            error_collector)
    class_state.CheckFinished('foo.h', error_collector)
    return error_collector.Results()

  # Similar to PerformMultiLineLint, but calls CheckLanguage instead of
  # CheckForNonStandardConstructs
  def PerformLanguageRulesCheck(self, file_name, code):
    error_collector = ErrorCollector(self.assert_)
    include_state = cpplint._IncludeState()
    lines = code.split('\n')
    cpplint.RemoveMultiLineComments(file_name, lines, error_collector)
    lines = cpplint.CleansedLines(lines)
    ext = file_name[file_name.rfind('.') + 1:]
    for i in xrange(lines.NumLines()):
      cpplint.CheckLanguage(file_name, lines, i, ext, include_state,
                            error_collector)
    return error_collector.Results()

  def PerformFunctionLengthsCheck(self, code):
    """Perform Lint function length check on block of code and return warnings.

    Builds up an array of lines corresponding to the code and strips comments
    using cpplint functions.

    Establishes an error collector and invokes the function length checking
    function following cpplint's pattern.

    Args:
      code: C++ source code expected to generate a warning message.

    Returns:
      The accumulated errors.
    """
    file_name = 'foo.cc'
    error_collector = ErrorCollector(self.assert_)
    function_state = cpplint._FunctionState()
    lines = code.split('\n')
    cpplint.RemoveMultiLineComments(file_name, lines, error_collector)
    lines = cpplint.CleansedLines(lines)
    for i in xrange(lines.NumLines()):
      cpplint.CheckForFunctionLengths(file_name, lines, i,
                                      function_state, error_collector)
    return error_collector.Results()

  def PerformIncludeWhatYouUse(self, code, filename='foo.h', io=codecs):
    # First, build up the include state.
    error_collector = ErrorCollector(self.assert_)
    include_state = cpplint._IncludeState()
    lines = code.split('\n')
    cpplint.RemoveMultiLineComments(filename, lines, error_collector)
    lines = cpplint.CleansedLines(lines)
    for i in xrange(lines.NumLines()):
      cpplint.CheckLanguage(filename, lines, i, '.h', include_state,
                            error_collector)
    # We could clear the error_collector here, but this should
    # also be fine, since our IncludeWhatYouUse unittests do not
    # have language problems.

    # Second, look for missing includes.
    cpplint.CheckForIncludeWhatYouUse(filename, lines, include_state,
                                      error_collector, io)
    return error_collector.Results()

  # Perform lint and compare the error message with "expected_message".
  def TestLint(self, code, expected_message):
    self.assertEquals(expected_message, self.PerformSingleLineLint(code))

  def TestMultiLineLint(self, code, expected_message):
    self.assertEquals(expected_message, self.PerformMultiLineLint(code))

  def TestMultiLineLintRE(self, code, expected_message_re):
    message = self.PerformMultiLineLint(code)
    if not re.search(expected_message_re, message):
      self.fail('Message was:\n' + message + 'Expected match to "' +
                expected_message_re + '"')

  def TestLanguageRulesCheck(self, file_name, code, expected_message):
    self.assertEquals(expected_message,
                      self.PerformLanguageRulesCheck(file_name, code))

  def TestIncludeWhatYouUse(self, code, expected_message):
    self.assertEquals(expected_message,
                      self.PerformIncludeWhatYouUse(code))

  def TestBlankLinesCheck(self, lines, start_errors, end_errors):
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData('foo.cc', 'cc', lines, error_collector)
    self.assertEquals(
        start_errors,
        error_collector.Results().count(
            'Blank line at the start of a code block.  Is this needed?'
            '  [whitespace/blank_line] [2]'))
    self.assertEquals(
        end_errors,
        error_collector.Results().count(
            'Blank line at the end of a code block.  Is this needed?'
            '  [whitespace/blank_line] [3]'))


class CpplintTest(CpplintTestBase):

  # Test get line width.
  def testGetLineWidth(self):
    self.assertEquals(0, cpplint.GetLineWidth(''))
    self.assertEquals(10, cpplint.GetLineWidth(u'x' * 10))
    self.assertEquals(16, cpplint.GetLineWidth(u'都|道|府|県|支庁'))

  def testGetTextInside(self):
    self.assertEquals('', cpplint._GetTextInside('fun()', r'fun\('))
    self.assertEquals('x, y', cpplint._GetTextInside('f(x, y)', r'f\('))
    self.assertEquals('a(), b(c())', cpplint._GetTextInside(
        'printf(a(), b(c()))', r'printf\('))
    self.assertEquals('x, y{}', cpplint._GetTextInside('f[x, y{}]', r'f\['))
    self.assertEquals(None, cpplint._GetTextInside('f[a, b(}]', r'f\['))
    self.assertEquals(None, cpplint._GetTextInside('f[x, y]', r'f\('))
    self.assertEquals('y, h(z, (a + b))', cpplint._GetTextInside(
        'f(x, g(y, h(z, (a + b))))', r'g\('))
    self.assertEquals('f(f(x))', cpplint._GetTextInside('f(f(f(x)))', r'f\('))
    # Supports multiple lines.
    self.assertEquals('\n  return loop(x);\n',
                      cpplint._GetTextInside(
                          'int loop(int x) {\n  return loop(x);\n}\n', r'\{'))
    # '^' matches the beggining of each line.
    self.assertEquals('x, y',
                      cpplint._GetTextInside(
                          '#include "inl.h"  // skip #define\n'
                          '#define A2(x, y) a_inl_(x, y, __LINE__)\n'
                          '#define A(x) a_inl_(x, "", __LINE__)\n',
                          r'^\s*#define\s*\w+\('))

  def testFindNextMultiLineCommentStart(self):
    self.assertEquals(1, cpplint.FindNextMultiLineCommentStart([''], 0))

    lines = ['a', 'b', '/* c']
    self.assertEquals(2, cpplint.FindNextMultiLineCommentStart(lines, 0))

    lines = ['char a[] = "/*";']  # not recognized as comment.
    self.assertEquals(1, cpplint.FindNextMultiLineCommentStart(lines, 0))

  def testFindNextMultiLineCommentEnd(self):
    self.assertEquals(1, cpplint.FindNextMultiLineCommentEnd([''], 0))
    lines = ['a', 'b', ' c */']
    self.assertEquals(2, cpplint.FindNextMultiLineCommentEnd(lines, 0))

  def testRemoveMultiLineCommentsFromRange(self):
    lines = ['a', '  /* comment ', ' * still comment', ' comment */   ', 'b']
    cpplint.RemoveMultiLineCommentsFromRange(lines, 1, 4)
    self.assertEquals(['a', '// dummy', '// dummy', '// dummy', 'b'], lines)

  def testSpacesAtEndOfLine(self):
    self.TestLint(
        '// Hello there ',
        'Line ends in whitespace.  Consider deleting these extra spaces.'
        '  [whitespace/end_of_line] [4]')

  # Test line length check.
  def testLineLengthCheck(self):
    self.TestLint(
        '// Hello',
        '')
    self.TestLint(
        '// ' + 'x' * 80,
        'Lines should be <= 80 characters long'
        '  [whitespace/line_length] [2]')
    self.TestLint(
        '// ' + 'x' * 100,
        'Lines should very rarely be longer than 100 characters'
        '  [whitespace/line_length] [4]')
    self.TestLint(
        '// http://g' + ('o' * 100) + 'gle.com/',
        '')
    self.TestLint(
        '//   https://g' + ('o' * 100) + 'gle.com/',
        '')
    self.TestLint(
        '//   https://g' + ('o' * 60) + 'gle.com/ and some comments',
        'Lines should be <= 80 characters long'
        '  [whitespace/line_length] [2]')
    self.TestLint(
        '// Read https://g' + ('o' * 60) + 'gle.com/' ,
        '')
    self.TestLint(
        '// $Id: g' + ('o' * 80) + 'gle.cc#1 $',
        '')
    self.TestLint(
        '// $Id: g' + ('o' * 80) + 'gle.cc#1',
        'Lines should be <= 80 characters long'
        '  [whitespace/line_length] [2]')

  # Test error suppression annotations.
  def testErrorSuppression(self):
    # Two errors on same line:
    self.TestLint(
        'long a = (int64) 65;',
        ['Using C-style cast.  Use static_cast<int64>(...) instead'
         '  [readability/casting] [4]',
         'Use int16/int64/etc, rather than the C type long'
         '  [runtime/int] [4]',
        ])
    # One category of error suppressed:
    self.TestLint(
        'long a = (int64) 65;  // NOLINT(runtime/int)',
        'Using C-style cast.  Use static_cast<int64>(...) instead'
        '  [readability/casting] [4]')
    # All categories suppressed: (two aliases)
    self.TestLint('long a = (int64) 65;  // NOLINT', '')
    self.TestLint('long a = (int64) 65;  // NOLINT(*)', '')
    # Malformed NOLINT directive:
    self.TestLint(
        'long a = 65;  // NOLINT(foo)',
        ['Unknown NOLINT error category: foo'
         '  [readability/nolint] [5]',
         'Use int16/int64/etc, rather than the C type long  [runtime/int] [4]',
        ])
    # Irrelevant NOLINT directive has no effect:
    self.TestLint(
        'long a = 65;  // NOLINT(readability/casting)',
        'Use int16/int64/etc, rather than the C type long'
         '  [runtime/int] [4]')


  # Test Variable Declarations.
  def testVariableDeclarations(self):
    self.TestLint(
        'long a = 65;',
        'Use int16/int64/etc, rather than the C type long'
        '  [runtime/int] [4]')
    self.TestLint(
        'long double b = 65.0;',
        '')
    self.TestLint(
        'long long aa = 6565;',
        'Use int16/int64/etc, rather than the C type long'
        '  [runtime/int] [4]')

  # Test C-style cast cases.
  def testCStyleCast(self):
    self.TestLint(
        'int a = (int)1.0;',
        'Using C-style cast.  Use static_cast<int>(...) instead'
        '  [readability/casting] [4]')
    self.TestLint(
        'int *a = (int *)NULL;',
        'Using C-style cast.  Use reinterpret_cast<int *>(...) instead'
        '  [readability/casting] [4]')

    self.TestLint(
        'uint16 a = (uint16)1.0;',
        'Using C-style cast.  Use static_cast<uint16>(...) instead'
        '  [readability/casting] [4]')
    self.TestLint(
        'int32 a = (int32)1.0;',
        'Using C-style cast.  Use static_cast<int32>(...) instead'
        '  [readability/casting] [4]')
    self.TestLint(
        'uint64 a = (uint64)1.0;',
        'Using C-style cast.  Use static_cast<uint64>(...) instead'
        '  [readability/casting] [4]')

    # These shouldn't be recognized casts.
    self.TestLint('u a = (u)NULL;', '')
    self.TestLint('uint a = (uint)NULL;', '')

  # Test taking address of casts (runtime/casting)
  def testRuntimeCasting(self):
    self.TestLint(
        'int* x = &static_cast<int*>(foo);',
        'Are you taking an address of a cast?  '
        'This is dangerous: could be a temp var.  '
        'Take the address before doing the cast, rather than after'
        '  [runtime/casting] [4]')

    self.TestLint(
        'int* x = &dynamic_cast<int *>(foo);',
        ['Are you taking an address of a cast?  '
         'This is dangerous: could be a temp var.  '
         'Take the address before doing the cast, rather than after'
         '  [runtime/casting] [4]',
         'Do not use dynamic_cast<>.  If you need to cast within a class '
         'hierarchy, use static_cast<> to upcast.  Google doesn\'t support '
         'RTTI.  [runtime/rtti] [5]'])

    self.TestLint(
        'int* x = &reinterpret_cast<int *>(foo);',
        'Are you taking an address of a cast?  '
        'This is dangerous: could be a temp var.  '
        'Take the address before doing the cast, rather than after'
        '  [runtime/casting] [4]')

    # It's OK to cast an address.
    self.TestLint(
        'int* x = reinterpret_cast<int *>(&foo);',
        '')

  def testRuntimeSelfinit(self):
    self.TestLint(
        'Foo::Foo(Bar r, Bel l) : r_(r_), l_(l_) { }',
        'You seem to be initializing a member variable with itself.'
        '  [runtime/init] [4]')
    self.TestLint(
        'Foo::Foo(Bar r, Bel l) : r_(r), l_(l) { }',
        '')
    self.TestLint(
        'Foo::Foo(Bar r) : r_(r), l_(r_), ll_(l_) { }',
        '')

  def testRuntimeRTTI(self):
    statement = 'int* x = dynamic_cast<int*>(&foo);'
    error_message = (
        'Do not use dynamic_cast<>.  If you need to cast within a class '
        'hierarchy, use static_cast<> to upcast.  Google doesn\'t support '
        'RTTI.  [runtime/rtti] [5]')
    # dynamic_cast is disallowed in most files.
    self.TestLanguageRulesCheck('foo.cc', statement, error_message)
    self.TestLanguageRulesCheck('foo.h', statement, error_message)
    # It is explicitly allowed in tests, however.
    self.TestLanguageRulesCheck('foo_test.cc', statement, '')
    self.TestLanguageRulesCheck('foo_unittest.cc', statement, '')
    self.TestLanguageRulesCheck('foo_regtest.cc', statement, '')

  # Test for unnamed arguments in a method.
  def testCheckForUnnamedParams(self):
    message = ('All parameters should be named in a function'
               '  [readability/function] [3]')
    self.TestLint('virtual void A(int*) const;', message)
    self.TestLint('virtual void B(void (*fn)(int*));', message)
    self.TestLint('virtual void C(int*);', message)
    self.TestLint('void *(*f)(void *) = x;', message)
    self.TestLint('void Method(char*) {', message)
    self.TestLint('void Method(char*);', message)
    self.TestLint('void Method(char* /*x*/);', message)
    self.TestLint('typedef void (*Method)(int32);', message)
    self.TestLint('static void operator delete[](void*) throw();', message)

    self.TestLint('virtual void D(int* p);', '')
    self.TestLint('void operator delete(void* x) throw();', '')
    self.TestLint('void Method(char* x) {', '')
    self.TestLint('void Method(char* /*x*/) {', '')
    self.TestLint('void Method(char* x);', '')
    self.TestLint('typedef void (*Method)(int32 x);', '')
    self.TestLint('static void operator delete[](void* x) throw();', '')
    self.TestLint('static void operator delete[](void* /*x*/) throw();', '')

    # This one should technically warn, but doesn't because the function
    # pointer is confusing.
    self.TestLint('virtual void E(void (*fn)(int* p));', '')

  # Test deprecated casts such as int(d)
  def testDeprecatedCast(self):
    self.TestLint(
        'int a = int(2.2);',
        'Using deprecated casting style.  '
        'Use static_cast<int>(...) instead'
        '  [readability/casting] [4]')

    self.TestLint(
        '(char *) "foo"',
        'Using C-style cast.  '
        'Use const_cast<char *>(...) instead'
        '  [readability/casting] [4]')

    self.TestLint(
        '(int*)foo',
        'Using C-style cast.  '
        'Use reinterpret_cast<int*>(...) instead'
        '  [readability/casting] [4]')

    # Checks for false positives...
    self.TestLint(
        'int a = int();  // Constructor, o.k.',
        '')
    self.TestLint(
        'X::X() : a(int()) {}  // default Constructor, o.k.',
        '')
    self.TestLint(
        'operator bool();  // Conversion operator, o.k.',
        '')
    self.TestLint(
        'new int64(123);  // "new" operator on basic type, o.k.',
        '')
    self.TestLint(
        'new   int64(123);  // "new" operator on basic type, weird spacing',
        '')

  # The second parameter to a gMock method definition is a function signature
  # that often looks like a bad cast but should not picked up by lint.
  def testMockMethod(self):
    self.TestLint(
        'MOCK_METHOD0(method, int());',
        '')
    self.TestLint(
        'MOCK_CONST_METHOD1(method, float(string));',
        '')
    self.TestLint(
        'MOCK_CONST_METHOD2_T(method, double(float, float));',
        '')

  # Like gMock method definitions, MockCallback instantiations look very similar
  # to bad casts.
  def testMockCallback(self):
    self.TestLint(
        'MockCallback<bool(int)>',
        '')
    self.TestLint(
        'MockCallback<int(float, char)>',
        '')

  # Test sizeof(type) cases.
  def testSizeofType(self):
    self.TestLint(
        'sizeof(int);',
        'Using sizeof(type).  Use sizeof(varname) instead if possible'
        '  [runtime/sizeof] [1]')
    self.TestLint(
        'sizeof(int *);',
        'Using sizeof(type).  Use sizeof(varname) instead if possible'
        '  [runtime/sizeof] [1]')

  # Test false errors that happened with some include file names
  def testIncludeFilenameFalseError(self):
    self.TestLint(
        '#include "foo/long-foo.h"',
        '')
    self.TestLint(
        '#include "foo/sprintf.h"',
        '')

  # Test typedef cases.  There was a bug that cpplint misidentified
  # typedef for pointer to function as C-style cast and produced
  # false-positive error messages.
  def testTypedefForPointerToFunction(self):
    self.TestLint(
        'typedef void (*Func)(int x);',
        '')
    self.TestLint(
        'typedef void (*Func)(int *x);',
        '')
    self.TestLint(
        'typedef void Func(int x);',
        '')
    self.TestLint(
        'typedef void Func(int *x);',
        '')

  def testIncludeWhatYouUseNoImplementationFiles(self):
    code = 'std::vector<int> foo;'
    self.assertEquals('Add #include <vector> for vector<>'
                      '  [build/include_what_you_use] [4]',
                      self.PerformIncludeWhatYouUse(code, 'foo.h'))
    self.assertEquals('',
                      self.PerformIncludeWhatYouUse(code, 'foo.cc'))

  def testIncludeWhatYouUse(self):
    self.TestIncludeWhatYouUse(
        """#include <vector>
           std::vector<int> foo;
        """,
        '')
    self.TestIncludeWhatYouUse(
        """#include <map>
           std::pair<int,int> foo;
        """,
        'Add #include <utility> for pair<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include <multimap>
           std::pair<int,int> foo;
        """,
        'Add #include <utility> for pair<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include <hash_map>
           std::pair<int,int> foo;
        """,
        'Add #include <utility> for pair<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include <utility>
           std::pair<int,int> foo;
        """,
        '')
    self.TestIncludeWhatYouUse(
        """#include <vector>
           DECLARE_string(foobar);
        """,
        '')
    self.TestIncludeWhatYouUse(
        """#include <vector>
           DEFINE_string(foobar, "", "");
        """,
        '')
    self.TestIncludeWhatYouUse(
        """#include <vector>
           std::pair<int,int> foo;
        """,
        'Add #include <utility> for pair<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include "base/foobar.h"
           std::vector<int> foo;
        """,
        'Add #include <vector> for vector<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include <vector>
           std::set<int> foo;
        """,
        'Add #include <set> for set<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include "base/foobar.h"
          hash_map<int, int> foobar;
        """,
        'Add #include <hash_map> for hash_map<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include "base/foobar.h"
           bool foobar = std::less<int>(0,1);
        """,
        'Add #include <functional> for less<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include "base/foobar.h"
           bool foobar = min<int>(0,1);
        """,
        'Add #include <algorithm> for min  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        'void a(const string &foobar);',
        'Add #include <string> for string  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        'void a(const std::string &foobar);',
        'Add #include <string> for string  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        'void a(const my::string &foobar);',
        '')  # Avoid false positives on strings in other namespaces.
    self.TestIncludeWhatYouUse(
        """#include "base/foobar.h"
           bool foobar = swap(0,1);
        """,
        'Add #include <algorithm> for swap  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include "base/foobar.h"
           bool foobar = transform(a.begin(), a.end(), b.start(), Foo);
        """,
        'Add #include <algorithm> for transform  '
        '[build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include "base/foobar.h"
           bool foobar = min_element(a.begin(), a.end());
        """,
        'Add #include <algorithm> for min_element  '
        '[build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """foo->swap(0,1);
           foo.swap(0,1);
        """,
        '')
    self.TestIncludeWhatYouUse(
        """#include <string>
           void a(const std::multimap<int,string> &foobar);
        """,
        'Add #include <map> for multimap<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include <queue>
           void a(const std::priority_queue<int> &foobar);
        """,
        '')
    self.TestIncludeWhatYouUse(
        """#include <assert.h>
           #include <string>
           #include <vector>
           #include "base/basictypes.h"
           #include "base/port.h"
           vector<string> hajoa;""", '')
    self.TestIncludeWhatYouUse(
        """#include <string>
           int i = numeric_limits<int>::max()
        """,
        'Add #include <limits> for numeric_limits<>'
        '  [build/include_what_you_use] [4]')
    self.TestIncludeWhatYouUse(
        """#include <limits>
           int i = numeric_limits<int>::max()
        """,
        '')

    # Test the UpdateIncludeState code path.
    mock_header_contents = ['#include "blah/foo.h"', '#include "blah/bar.h"']
    message = self.PerformIncludeWhatYouUse(
        '#include "blah/a.h"',
        filename='blah/a.cc',
        io=MockIo(mock_header_contents))
    self.assertEquals(message, '')

    mock_header_contents = ['#include <set>']
    message = self.PerformIncludeWhatYouUse(
        """#include "blah/a.h"
           std::set<int> foo;""",
        filename='blah/a.cc',
        io=MockIo(mock_header_contents))
    self.assertEquals(message, '')

    # Make sure we can find the correct header file if the cc file seems to be
    # a temporary file generated by Emacs's flymake.
    mock_header_contents = ['']
    message = self.PerformIncludeWhatYouUse(
        """#include "blah/a.h"
           std::set<int> foo;""",
        filename='blah/a_flymake.cc',
        io=MockIo(mock_header_contents))
    self.assertEquals(message, 'Add #include <set> for set<>  '
                      '[build/include_what_you_use] [4]')

    # If there's just a cc and the header can't be found then it's ok.
    message = self.PerformIncludeWhatYouUse(
        """#include "blah/a.h"
           std::set<int> foo;""",
        filename='blah/a.cc')
    self.assertEquals(message, '')

    # Make sure we find the headers with relative paths.
    mock_header_contents = ['']
    message = self.PerformIncludeWhatYouUse(
        """#include "%s/a.h"
           std::set<int> foo;""" % os.path.basename(os.getcwd()),
        filename='a.cc',
        io=MockIo(mock_header_contents))
    self.assertEquals(message, 'Add #include <set> for set<>  '
                      '[build/include_what_you_use] [4]')

  def testFilesBelongToSameModule(self):
    f = cpplint.FilesBelongToSameModule
    self.assertEquals((True, ''), f('a.cc', 'a.h'))
    self.assertEquals((True, ''), f('base/google.cc', 'base/google.h'))
    self.assertEquals((True, ''), f('base/google_test.cc', 'base/google.h'))
    self.assertEquals((True, ''),
                      f('base/google_unittest.cc', 'base/google.h'))
    self.assertEquals((True, ''),
                      f('base/internal/google_unittest.cc',
                        'base/public/google.h'))
    self.assertEquals((True, 'xxx/yyy/'),
                      f('xxx/yyy/base/internal/google_unittest.cc',
                        'base/public/google.h'))
    self.assertEquals((True, 'xxx/yyy/'),
                      f('xxx/yyy/base/google_unittest.cc',
                        'base/public/google.h'))
    self.assertEquals((True, ''),
                      f('base/google_unittest.cc', 'base/google-inl.h'))
    self.assertEquals((True, '/home/build/google3/'),
                      f('/home/build/google3/base/google.cc', 'base/google.h'))

    self.assertEquals((False, ''),
                      f('/home/build/google3/base/google.cc', 'basu/google.h'))
    self.assertEquals((False, ''), f('a.cc', 'b.h'))

  def testCleanseLine(self):
    self.assertEquals('int foo = 0;',
                      cpplint.CleanseComments('int foo = 0;  // danger!'))
    self.assertEquals('int o = 0;',
                      cpplint.CleanseComments('int /* foo */ o = 0;'))
    self.assertEquals('foo(int a, int b);',
                      cpplint.CleanseComments('foo(int a /* abc */, int b);'))
    self.assertEqual('f(a, b);',
                     cpplint.CleanseComments('f(a, /* name */ b);'))
    self.assertEqual('f(a, b);',
		     cpplint.CleanseComments('f(a /* name */, b);'))
    self.assertEqual('f(a, b);',
                     cpplint.CleanseComments('f(a, /* name */b);'))

  def testMultiLineComments(self):
    # missing explicit is bad
    self.TestMultiLineLint(
        r"""int a = 0;
            /* multi-liner
            class Foo {
            Foo(int f);  // should cause a lint warning in code
            }
            */ """,
        '')
    self.TestMultiLineLint(
        r"""/* int a = 0; multi-liner
              static const int b = 0;""",
        'Could not find end of multi-line comment'
        '  [readability/multiline_comment] [5]')
    self.TestMultiLineLint(r"""  /* multi-line comment""",
                           'Could not find end of multi-line comment'
                           '  [readability/multiline_comment] [5]')
    self.TestMultiLineLint(r"""  // /* comment, but not multi-line""", '')

  def testMultilineStrings(self):
    multiline_string_error_message = (
        'Multi-line string ("...") found.  This lint script doesn\'t '
        'do well with such strings, and may give bogus warnings.  They\'re '
        'ugly and unnecessary, and you should use concatenation instead".'
        '  [readability/multiline_string] [5]')

    file_path = 'mydir/foo.cc'

    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'cc',
                            ['const char* str = "This is a\\',
                             ' multiline string.";'],
                            error_collector)
    self.assertEquals(
        2,  # One per line.
        error_collector.ResultList().count(multiline_string_error_message))

  # Test non-explicit single-argument constructors
  def testExplicitSingleArgumentConstructors(self):
    # missing explicit is bad
    self.TestMultiLineLint(
        """class Foo {
             Foo(int f);
           };""",
        'Single-argument constructors should be marked explicit.'
        '  [runtime/explicit] [5]')
    # missing explicit is bad, even with whitespace
    self.TestMultiLineLint(
        """class Foo {
             Foo (int f);
           };""",
        ['Extra space before ( in function call  [whitespace/parens] [4]',
         'Single-argument constructors should be marked explicit.'
         '  [runtime/explicit] [5]'])
    # missing explicit, with distracting comment, is still bad
    self.TestMultiLineLint(
        """class Foo {
             Foo(int f);  // simpler than Foo(blargh, blarg)
           };""",
        'Single-argument constructors should be marked explicit.'
        '  [runtime/explicit] [5]')
    # missing explicit, with qualified classname
    self.TestMultiLineLint(
        """class Qualifier::AnotherOne::Foo {
             Foo(int f);
           };""",
        'Single-argument constructors should be marked explicit.'
        '  [runtime/explicit] [5]')
    # missing explicit for inline constructors is bad as well
    self.TestMultiLineLint(
        """class Foo {
             inline Foo(int f);
           };""",
        'Single-argument constructors should be marked explicit.'
        '  [runtime/explicit] [5]')
    # structs are caught as well.
    self.TestMultiLineLint(
        """struct Foo {
             Foo(int f);
           };""",
        'Single-argument constructors should be marked explicit.'
        '  [runtime/explicit] [5]')
    # Templatized classes are caught as well.
    self.TestMultiLineLint(
        """template<typename T> class Foo {
             Foo(int f);
           };""",
        'Single-argument constructors should be marked explicit.'
        '  [runtime/explicit] [5]')
    # inline case for templatized classes.
    self.TestMultiLineLint(
        """template<typename T> class Foo {
             inline Foo(int f);
           };""",
        'Single-argument constructors should be marked explicit.'
        '  [runtime/explicit] [5]')
    # proper style is okay
    self.TestMultiLineLint(
        """class Foo {
             explicit Foo(int f);
           };""",
        '')
    # two argument constructor is okay
    self.TestMultiLineLint(
        """class Foo {
             Foo(int f, int b);
           };""",
        '')
    # two argument constructor, across two lines, is okay
    self.TestMultiLineLint(
        """class Foo {
             Foo(int f,
                 int b);
           };""",
        '')
    # non-constructor (but similar name), is okay
    self.TestMultiLineLint(
        """class Foo {
             aFoo(int f);
           };""",
        '')
    # constructor with void argument is okay
    self.TestMultiLineLint(
        """class Foo {
             Foo(void);
           };""",
        '')
    # single argument method is okay
    self.TestMultiLineLint(
        """class Foo {
             Bar(int b);
           };""",
        '')
    # comments should be ignored
    self.TestMultiLineLint(
        """class Foo {
           // Foo(int f);
           };""",
        '')
    # single argument function following class definition is okay
    # (okay, it's not actually valid, but we don't want a false positive)
    self.TestMultiLineLint(
        """class Foo {
             Foo(int f, int b);
           };
           Foo(int f);""",
        '')
    # single argument function is okay
    self.TestMultiLineLint(
        """static Foo(int f);""",
        '')
    # single argument copy constructor is okay.
    self.TestMultiLineLint(
        """class Foo {
             Foo(const Foo&);
           };""",
        '')
    self.TestMultiLineLint(
        """class Foo {
             Foo(Foo&);
           };""",
        '')
    # templatized copy constructor is okay.
    self.TestMultiLineLint(
        """template<typename T> class Foo {
             Foo(const Foo<T>&);
           };""",
        '')

  def testSlashStarCommentOnSingleLine(self):
    self.TestMultiLineLint(
        """/* static */ Foo(int f);""",
        '')
    self.TestMultiLineLint(
        """/*/ static */  Foo(int f);""",
        '')
    self.TestMultiLineLint(
        """/*/ static Foo(int f);""",
        'Could not find end of multi-line comment'
        '  [readability/multiline_comment] [5]')
    self.TestMultiLineLint(
        """  /*/ static Foo(int f);""",
        'Could not find end of multi-line comment'
        '  [readability/multiline_comment] [5]')
    self.TestMultiLineLint(
        """  /**/ static Foo(int f);""",
        '')

  # Test suspicious usage of "if" like this:
  # if (a == b) {
  #   DoSomething();
  # } if (a == c) {   // Should be "else if".
  #   DoSomething();  // This gets called twice if a == b && a == c.
  # }
  def testSuspiciousUsageOfIf(self):
    self.TestLint(
        '  if (a == b) {',
        '')
    self.TestLint(
        '  } if (a == b) {',
        'Did you mean "else if"? If not, start a new line for "if".'
        '  [readability/braces] [4]')

  # Test suspicious usage of memset. Specifically, a 0
  # as the final argument is almost certainly an error.
  def testSuspiciousUsageOfMemset(self):
    # Normal use is okay.
    self.TestLint(
        '  memset(buf, 0, sizeof(buf))',
        '')

    # A 0 as the final argument is almost certainly an error.
    self.TestLint(
        '  memset(buf, sizeof(buf), 0)',
        'Did you mean "memset(buf, 0, sizeof(buf))"?'
        '  [runtime/memset] [4]')
    self.TestLint(
        '  memset(buf, xsize * ysize, 0)',
        'Did you mean "memset(buf, 0, xsize * ysize)"?'
        '  [runtime/memset] [4]')

    # There is legitimate test code that uses this form.
    # This is okay since the second argument is a literal.
    self.TestLint(
        "  memset(buf, 'y', 0)",
        '')
    self.TestLint(
        '  memset(buf, 4, 0)',
        '')
    self.TestLint(
        '  memset(buf, -1, 0)',
        '')
    self.TestLint(
        '  memset(buf, 0xF1, 0)',
        '')
    self.TestLint(
        '  memset(buf, 0xcd, 0)',
        '')

  def testCheckDeprecated(self):
    self.TestLanguageRulesCheck('foo.cc', '#include <iostream>',
                                'Streams are highly discouraged.'
                                '  [readability/streams] [3]')
    self.TestLanguageRulesCheck('foo_test.cc', '#include <iostream>', '')
    self.TestLanguageRulesCheck('foo_unittest.cc', '#include <iostream>', '')

  def testCheckPosixThreading(self):
    self.TestLint('sctime_r()', '')
    self.TestLint('strtok_r()', '')
    self.TestLint('  strtok_r(foo, ba, r)', '')
    self.TestLint('brand()', '')
    self.TestLint('_rand()', '')
    self.TestLint('.rand()', '')
    self.TestLint('>rand()', '')
    self.TestLint('rand()',
                  'Consider using rand_r(...) instead of rand(...)'
                  ' for improved thread safety.'
                  '  [runtime/threadsafe_fn] [2]')
    self.TestLint('strtok()',
                  'Consider using strtok_r(...) '
                  'instead of strtok(...)'
                  ' for improved thread safety.'
                  '  [runtime/threadsafe_fn] [2]')

  # Test potential format string bugs like printf(foo).
  def testFormatStrings(self):
    self.TestLint('printf("foo")', '')
    self.TestLint('printf("foo: %s", foo)', '')
    self.TestLint('DocidForPrintf(docid)', '')  # Should not trigger.
    self.TestLint('printf(format, value)', '')  # Should not trigger.
    self.TestLint('printf(format.c_str(), value)', '')  # Should not trigger.
    self.TestLint('printf(format(index).c_str(), value)', '')
    self.TestLint(
        'printf(foo)',
        'Potential format string bug. Do printf("%s", foo) instead.'
        '  [runtime/printf] [4]')
    self.TestLint(
        'printf(foo.c_str())',
        'Potential format string bug. '
        'Do printf("%s", foo.c_str()) instead.'
        '  [runtime/printf] [4]')
    self.TestLint(
        'printf(foo->c_str())',
        'Potential format string bug. '
        'Do printf("%s", foo->c_str()) instead.'
        '  [runtime/printf] [4]')
    self.TestLint(
        'StringPrintf(foo)',
        'Potential format string bug. Do StringPrintf("%s", foo) instead.'
        ''
        '  [runtime/printf] [4]')

  # Test disallowed use of operator& and other operators.
  def testIllegalOperatorOverloading(self):
    errmsg = ('Unary operator& is dangerous.  Do not use it.'
              '  [runtime/operator] [4]')
    self.TestLint('void operator=(const Myclass&)', '')
    self.TestLint('void operator&(int a, int b)', '')   # binary operator& ok
    self.TestLint('void operator&() { }', errmsg)
    self.TestLint('void operator & (  ) { }',
                  ['Extra space after (  [whitespace/parens] [2]',
                   errmsg
                   ])

  # const string reference members are dangerous..
  def testConstStringReferenceMembers(self):
    errmsg = ('const string& members are dangerous. It is much better to use '
              'alternatives, such as pointers or simple constants.'
              '  [runtime/member_string_references] [2]')

    members_declarations = ['const string& church',
                            'const string &turing',
                            'const string & godel']
    # TODO(unknown): Enable also these tests if and when we ever
    # decide to check for arbitrary member references.
    #                         "const Turing & a",
    #                         "const Church& a",
    #                         "const vector<int>& a",
    #                         "const     Kurt::Godel    &    godel",
    #                         "const Kazimierz::Kuratowski& kk" ]

    # The Good.

    self.TestLint('void f(const string&)', '')
    self.TestLint('const string& f(const string& a, const string& b)', '')
    self.TestLint('typedef const string& A;', '')

    for decl in members_declarations:
      self.TestLint(decl + ' = b;', '')
      self.TestLint(decl + '      =', '')

    # The Bad.

    for decl in members_declarations:
      self.TestLint(decl + ';', errmsg)

  # Variable-length arrays are not permitted.
  def testVariableLengthArrayDetection(self):
    errmsg = ('Do not use variable-length arrays.  Use an appropriately named '
              "('k' followed by CamelCase) compile-time constant for the size."
              '  [runtime/arrays] [1]')

    self.TestLint('int a[any_old_variable];', errmsg)
    self.TestLint('int doublesize[some_var * 2];', errmsg)
    self.TestLint('int a[afunction()];', errmsg)
    self.TestLint('int a[function(kMaxFooBars)];', errmsg)
    self.TestLint('bool a_list[items_->size()];', errmsg)
    self.TestLint('namespace::Type buffer[len+1];', errmsg)

    self.TestLint('int a[64];', '')
    self.TestLint('int a[0xFF];', '')
    self.TestLint('int first[256], second[256];', '')
    self.TestLint('int array_name[kCompileTimeConstant];', '')
    self.TestLint('char buf[somenamespace::kBufSize];', '')
    self.TestLint('int array_name[ALL_CAPS];', '')
    self.TestLint('AClass array1[foo::bar::ALL_CAPS];', '')
    self.TestLint('int a[kMaxStrLen + 1];', '')
    self.TestLint('int a[sizeof(foo)];', '')
    self.TestLint('int a[sizeof(*foo)];', '')
    self.TestLint('int a[sizeof foo];', '')
    self.TestLint('int a[sizeof(struct Foo)];', '')
    self.TestLint('int a[128 - sizeof(const bar)];', '')
    self.TestLint('int a[(sizeof(foo) * 4)];', '')
    self.TestLint('int a[(arraysize(fixed_size_array)/2) << 1];', '')
    self.TestLint('delete a[some_var];', '')
    self.TestLint('return a[some_var];', '')

  # DISALLOW_EVIL_CONSTRUCTORS should be at end of class if present.
  # Same with DISALLOW_COPY_AND_ASSIGN and DISALLOW_IMPLICIT_CONSTRUCTORS.
  def testDisallowEvilConstructors(self):
    for macro_name in (
        'DISALLOW_EVIL_CONSTRUCTORS',
        'DISALLOW_COPY_AND_ASSIGN',
        'DISALLOW_IMPLICIT_CONSTRUCTORS'):
      self.TestLanguageRulesCheck(
          'some_class.h',
          """%s(SomeClass);
          int foo_;
          };""" % macro_name,
          ('%s should be the last thing in the class' % macro_name) +
          '  [readability/constructors] [3]')
      self.TestLanguageRulesCheck(
          'some_class.h',
          """%s(SomeClass);
          };""" % macro_name,
          '')
      self.TestLanguageRulesCheck(
          'some_class.h',
          """%s(SomeClass);
          int foo_;
          } instance, *pointer_to_instance;""" % macro_name,
          ('%s should be the last thing in the class' % macro_name) +
          '  [readability/constructors] [3]')
      self.TestLanguageRulesCheck(
          'some_class.h',
          """%s(SomeClass);
          } instance, *pointer_to_instance;""" % macro_name,
          '')

  # Brace usage
  def testBraces(self):
    # Braces shouldn't be followed by a ; unless they're defining a struct
    # or initializing an array
    self.TestLint('int a[3] = { 1, 2, 3 };', '')
    self.TestLint(
        """const int foo[] =
               {1, 2, 3 };""",
        '')
    # For single line, unmatched '}' with a ';' is ignored (not enough context)
    self.TestMultiLineLint(
        """int a[3] = { 1,
                        2,
                        3 };""",
        '')
    self.TestMultiLineLint(
        """int a[2][3] = { { 1, 2 },
                         { 3, 4 } };""",
        '')
    self.TestMultiLineLint(
        """int a[2][3] =
               { { 1, 2 },
                 { 3, 4 } };""",
        '')

  # CHECK/EXPECT_TRUE/EXPECT_FALSE replacements
  def testCheckCheck(self):
    self.TestLint('CHECK(x == 42)',
                  'Consider using CHECK_EQ instead of CHECK(a == b)'
                  '  [readability/check] [2]')
    self.TestLint('CHECK(x != 42)',
                  'Consider using CHECK_NE instead of CHECK(a != b)'
                  '  [readability/check] [2]')
    self.TestLint('CHECK(x >= 42)',
                  'Consider using CHECK_GE instead of CHECK(a >= b)'
                  '  [readability/check] [2]')
    self.TestLint('CHECK(x > 42)',
                  'Consider using CHECK_GT instead of CHECK(a > b)'
                  '  [readability/check] [2]')
    self.TestLint('CHECK(x <= 42)',
                  'Consider using CHECK_LE instead of CHECK(a <= b)'
                  '  [readability/check] [2]')
    self.TestLint('CHECK(x < 42)',
                  'Consider using CHECK_LT instead of CHECK(a < b)'
                  '  [readability/check] [2]')

    self.TestLint('DCHECK(x == 42)',
                  'Consider using DCHECK_EQ instead of DCHECK(a == b)'
                  '  [readability/check] [2]')
    self.TestLint('DCHECK(x != 42)',
                  'Consider using DCHECK_NE instead of DCHECK(a != b)'
                  '  [readability/check] [2]')
    self.TestLint('DCHECK(x >= 42)',
                  'Consider using DCHECK_GE instead of DCHECK(a >= b)'
                  '  [readability/check] [2]')
    self.TestLint('DCHECK(x > 42)',
                  'Consider using DCHECK_GT instead of DCHECK(a > b)'
                  '  [readability/check] [2]')
    self.TestLint('DCHECK(x <= 42)',
                  'Consider using DCHECK_LE instead of DCHECK(a <= b)'
                  '  [readability/check] [2]')
    self.TestLint('DCHECK(x < 42)',
                  'Consider using DCHECK_LT instead of DCHECK(a < b)'
                  '  [readability/check] [2]')

    self.TestLint(
        'EXPECT_TRUE("42" == x)',
        'Consider using EXPECT_EQ instead of EXPECT_TRUE(a == b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_TRUE("42" != x)',
        'Consider using EXPECT_NE instead of EXPECT_TRUE(a != b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_TRUE(+42 >= x)',
        'Consider using EXPECT_GE instead of EXPECT_TRUE(a >= b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_TRUE_M(-42 > x)',
        'Consider using EXPECT_GT_M instead of EXPECT_TRUE_M(a > b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_TRUE_M(42U <= x)',
        'Consider using EXPECT_LE_M instead of EXPECT_TRUE_M(a <= b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_TRUE_M(42L < x)',
        'Consider using EXPECT_LT_M instead of EXPECT_TRUE_M(a < b)'
        '  [readability/check] [2]')

    self.TestLint(
        'EXPECT_FALSE(x == 42)',
        'Consider using EXPECT_NE instead of EXPECT_FALSE(a == b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_FALSE(x != 42)',
        'Consider using EXPECT_EQ instead of EXPECT_FALSE(a != b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_FALSE(x >= 42)',
        'Consider using EXPECT_LT instead of EXPECT_FALSE(a >= b)'
        '  [readability/check] [2]')
    self.TestLint(
        'ASSERT_FALSE(x > 42)',
        'Consider using ASSERT_LE instead of ASSERT_FALSE(a > b)'
        '  [readability/check] [2]')
    self.TestLint(
        'ASSERT_FALSE(x <= 42)',
        'Consider using ASSERT_GT instead of ASSERT_FALSE(a <= b)'
        '  [readability/check] [2]')
    self.TestLint(
        'ASSERT_FALSE_M(x < 42)',
        'Consider using ASSERT_GE_M instead of ASSERT_FALSE_M(a < b)'
        '  [readability/check] [2]')

    self.TestLint('CHECK(some_iterator == obj.end())', '')
    self.TestLint('EXPECT_TRUE(some_iterator == obj.end())', '')
    self.TestLint('EXPECT_FALSE(some_iterator == obj.end())', '')
    self.TestLint('CHECK(some_pointer != NULL)', '')
    self.TestLint('EXPECT_TRUE(some_pointer != NULL)', '')
    self.TestLint('EXPECT_FALSE(some_pointer != NULL)', '')

    self.TestLint('CHECK(CreateTestFile(dir, (1 << 20)));', '')
    self.TestLint('CHECK(CreateTestFile(dir, (1 >> 20)));', '')

    self.TestLint('CHECK(x<42)',
                  ['Missing spaces around <'
                   '  [whitespace/operators] [3]',
                   'Consider using CHECK_LT instead of CHECK(a < b)'
                   '  [readability/check] [2]'])
    self.TestLint('CHECK(x>42)',
                  'Consider using CHECK_GT instead of CHECK(a > b)'
                  '  [readability/check] [2]')

    self.TestLint(
        '  EXPECT_TRUE(42 < x)  // Random comment.',
        'Consider using EXPECT_LT instead of EXPECT_TRUE(a < b)'
        '  [readability/check] [2]')
    self.TestLint(
        'EXPECT_TRUE( 42 < x )',
        ['Extra space after ( in function call'
         '  [whitespace/parens] [4]',
         'Consider using EXPECT_LT instead of EXPECT_TRUE(a < b)'
         '  [readability/check] [2]'])
    self.TestLint(
        'CHECK("foo" == "foo")',
        'Consider using CHECK_EQ instead of CHECK(a == b)'
        '  [readability/check] [2]')

    self.TestLint('CHECK_EQ("foo", "foo")', '')

  # Passing and returning non-const references
  def testNonConstReference(self):
    # Passing a non-const reference as function parameter is forbidden.
    operand_error_message = ('Is this a non-const reference? '
                             'If so, make const or use a pointer.'
                             '  [runtime/references] [2]')
    # Warn of use of a non-const reference in operators and functions
    self.TestLint('bool operator>(Foo& s, Foo& f);', operand_error_message)
    self.TestLint('bool operator+(Foo& s, Foo& f);', operand_error_message)
    self.TestLint('int len(Foo& s);', operand_error_message)
    # Allow use of non-const references in a few specific cases
    self.TestLint('stream& operator>>(stream& s, Foo& f);', '')
    self.TestLint('stream& operator<<(stream& s, Foo& f);', '')
    self.TestLint('void swap(Bar& a, Bar& b);', '')
    # Returning a non-const reference from a function is OK.
    self.TestLint('int& g();', '')
    # Passing a const reference to a struct (using the struct keyword) is OK.
    self.TestLint('void foo(const struct tm& tm);', '')
    # Passing a const reference to a typename is OK.
    self.TestLint('void foo(const typename tm& tm);', '')
    # Returning an address of something is not prohibited.
    self.TestLint('return &something;', '')
    self.TestLint('if (condition) {return &something; }', '')
    self.TestLint('if (condition) return &something;', '')
    self.TestLint('if (condition) address = &something;', '')
    self.TestLint('if (condition) result = lhs&rhs;', '')
    self.TestLint('if (condition) result = lhs & rhs;', '')
    self.TestLint('a = (b+c) * sizeof &f;', '')
    self.TestLint('a = MySize(b) * sizeof &f;', '')

  def testBraceAtBeginOfLine(self):
    self.TestLint('{',
                  '{ should almost always be at the end of the previous line'
                  '  [whitespace/braces] [4]')

  def testMismatchingSpacesInParens(self):
    self.TestLint('if (foo ) {', 'Mismatching spaces inside () in if'
                  '  [whitespace/parens] [5]')
    self.TestLint('switch ( foo) {', 'Mismatching spaces inside () in switch'
                  '  [whitespace/parens] [5]')
    self.TestLint('for (foo; ba; bar ) {', 'Mismatching spaces inside () in for'
                  '  [whitespace/parens] [5]')
    self.TestLint('for (; foo; bar) {', '')
    self.TestLint('for ( ; foo; bar) {', '')
    self.TestLint('for ( ; foo; bar ) {', '')
    self.TestLint('for (foo; bar; ) {', '')
    self.TestLint('while (  foo  ) {', 'Should have zero or one spaces inside'
                  ' ( and ) in while  [whitespace/parens] [5]')

  def testSpacingForFncall(self):
    self.TestLint('if (foo) {', '')
    self.TestLint('for (foo; bar; baz) {', '')
    self.TestLint('for (;;) {', '')
    # Test that there is no warning when increment statement is empty.
    self.TestLint('for (foo; baz;) {', '')
    self.TestLint('for (foo;bar;baz) {', 'Missing space after ;'
                  '  [whitespace/semicolon] [3]')
    # we don't warn about this semicolon, at least for now
    self.TestLint('if (condition) {return &something; }',
                  '')
    # seen in some macros
    self.TestLint('DoSth();\\', '')
    # Test that there is no warning about semicolon here.
    self.TestLint('abc;// this is abc',
                  'At least two spaces is best between code'
                  ' and comments  [whitespace/comments] [2]')
    self.TestLint('while (foo) {', '')
    self.TestLint('switch (foo) {', '')
    self.TestLint('foo( bar)', 'Extra space after ( in function call'
                  '  [whitespace/parens] [4]')
    self.TestLint('foo(  // comment', '')
    self.TestLint('foo( // comment',
                  'At least two spaces is best between code'
                  ' and comments  [whitespace/comments] [2]')
    self.TestLint('foobar( \\', '')
    self.TestLint('foobar(     \\', '')
    self.TestLint('( a + b)', 'Extra space after ('
                  '  [whitespace/parens] [2]')
    self.TestLint('((a+b))', '')
    self.TestLint('foo (foo)', 'Extra space before ( in function call'
                  '  [whitespace/parens] [4]')
    self.TestLint('typedef foo (*foo)(foo)', '')
    self.TestLint('typedef foo (*foo12bar_)(foo)', '')
    self.TestLint('typedef foo (Foo::*bar)(foo)', '')
    self.TestLint('foo (Foo::*bar)(',
                  'Extra space before ( in function call'
                  '  [whitespace/parens] [4]')
    self.TestLint('typedef foo (Foo::*bar)(', '')
    self.TestLint('(foo)(bar)', '')
    self.TestLint('Foo (*foo)(bar)', '')
    self.TestLint('Foo (*foo)(Bar bar,', '')
    self.TestLint('char (*p)[sizeof(foo)] = &foo', '')
    self.TestLint('char (&ref)[sizeof(foo)] = &foo', '')
    self.TestLint('const char32 (*table[])[6];', '')

  def testSpacingBeforeBraces(self):
    self.TestLint('if (foo){', 'Missing space before {'
                  '  [whitespace/braces] [5]')
    self.TestLint('for{', 'Missing space before {'
                  '  [whitespace/braces] [5]')
    self.TestLint('for {', '')
    self.TestLint('EXPECT_DEBUG_DEATH({', '')

  def testSpacingAroundElse(self):
    self.TestLint('}else {', 'Missing space before else'
                  '  [whitespace/braces] [5]')
    self.TestLint('} else{', 'Missing space before {'
                  '  [whitespace/braces] [5]')
    self.TestLint('} else {', '')
    self.TestLint('} else if', '')

  def testSpacingWithInitializerLists(self):
    self.TestLint('int v[1][3] = {{1, 2, 3}};', '')
    self.TestLint('int v[1][1] = {{0}};', '')

  def testSpacingForBinaryOps(self):
    self.TestLint('if (foo<=bar) {', 'Missing spaces around <='
                  '  [whitespace/operators] [3]')
    self.TestLint('if (foo<bar) {', 'Missing spaces around <'
                  '  [whitespace/operators] [3]')
    self.TestLint('if (foo<bar->baz) {', 'Missing spaces around <'
                  '  [whitespace/operators] [3]')
    self.TestLint('if (foo<bar->bar) {', 'Missing spaces around <'
                  '  [whitespace/operators] [3]')
    self.TestLint('typedef hash_map<Foo, Bar', 'Missing spaces around <'
                  '  [whitespace/operators] [3]')
    self.TestLint('typedef hash_map<FoooooType, BaaaaarType,', '')

  def testSpacingBeforeLastSemicolon(self):
    self.TestLint('call_function() ;',
                  'Extra space before last semicolon. If this should be an '
                  'empty statement, use { } instead.'
                  '  [whitespace/semicolon] [5]')
    self.TestLint('while (true) ;',
                  'Extra space before last semicolon. If this should be an '
                  'empty statement, use { } instead.'
                  '  [whitespace/semicolon] [5]')
    self.TestLint('default:;',
                  'Semicolon defining empty statement. Use { } instead.'
                  '  [whitespace/semicolon] [5]')
    self.TestLint('      ;',
                  'Line contains only semicolon. If this should be an empty '
                  'statement, use { } instead.'
                  '  [whitespace/semicolon] [5]')
    self.TestLint('for (int i = 0; ;', '')

  # Static or global STL strings.
  def testStaticOrGlobalSTLStrings(self):
    self.TestLint('string foo;',
                  'For a static/global string constant, use a C style '
                  'string instead: "char foo[]".'
                  '  [runtime/string] [4]')
    self.TestLint('string kFoo = "hello";  // English',
                  'For a static/global string constant, use a C style '
                  'string instead: "char kFoo[]".'
                  '  [runtime/string] [4]')
    self.TestLint('static string foo;',
                  'For a static/global string constant, use a C style '
                  'string instead: "static char foo[]".'
                  '  [runtime/string] [4]')
    self.TestLint('static const string foo;',
                  'For a static/global string constant, use a C style '
                  'string instead: "static const char foo[]".'
                  '  [runtime/string] [4]')
    self.TestLint('string Foo::bar;',
                  'For a static/global string constant, use a C style '
                  'string instead: "char Foo::bar[]".'
                  '  [runtime/string] [4]')
    # Rare case.
    self.TestLint('string foo("foobar");',
                  'For a static/global string constant, use a C style '
                  'string instead: "char foo[]".'
                  '  [runtime/string] [4]')
    # Should not catch local or member variables.
    self.TestLint('  string foo', '')
    # Should not catch functions.
    self.TestLint('string EmptyString() { return ""; }', '')
    self.TestLint('string EmptyString () { return ""; }', '')
    self.TestLint('string VeryLongNameFunctionSometimesEndsWith(\n'
                  '    VeryLongNameType very_long_name_variable) {}', '')
    self.TestLint('template<>\n'
                  'string FunctionTemplateSpecialization<SomeType>(\n'
                  '      int x) { return ""; }', '')
    self.TestLint('template<>\n'
                  'string FunctionTemplateSpecialization<vector<A::B>* >(\n'
                  '      int x) { return ""; }', '')

    # should not catch methods of template classes.
    self.TestLint('string Class<Type>::Method() const {\n'
                  '  return "";\n'
                  '}\n', '')
    self.TestLint('string Class<Type>::Method(\n'
                  '   int arg) const {\n'
                  '  return "";\n'
                  '}\n', '')

  def testNoSpacesInFunctionCalls(self):
    self.TestLint('TellStory(1, 3);',
                  '')
    self.TestLint('TellStory(1, 3 );',
                  'Extra space before )'
                  '  [whitespace/parens] [2]')
    self.TestLint('TellStory(1 /* wolf */, 3 /* pigs */);',
                  '')
    self.TestMultiLineLint("""TellStory(1, 3
                                        );""",
                           'Closing ) should be moved to the previous line'
                           '  [whitespace/parens] [2]')
    self.TestMultiLineLint("""TellStory(Wolves(1),
                                        Pigs(3
                                        ));""",
                           'Closing ) should be moved to the previous line'
                           '  [whitespace/parens] [2]')
    self.TestMultiLineLint("""TellStory(1,
                                        3 );""",
                           'Extra space before )'
                           '  [whitespace/parens] [2]')

  def testToDoComments(self):
    start_space = ('Too many spaces before TODO'
                   '  [whitespace/todo] [2]')
    missing_username = ('Missing username in TODO; it should look like '
                        '"// TODO(my_username): Stuff."'
                        '  [readability/todo] [2]')
    end_space = ('TODO(my_username) should be followed by a space'
                 '  [whitespace/todo] [2]')

    self.TestLint('//   TODOfix this',
                  [start_space, missing_username, end_space])
    self.TestLint('//   TODO(ljenkins)fix this',
                  [start_space, end_space])
    self.TestLint('//   TODO fix this',
                  [start_space, missing_username])
    self.TestLint('// TODO fix this', missing_username)
    self.TestLint('// TODO: fix this', missing_username)
    self.TestLint('//TODO(ljenkins): Fix this',
                  'Should have a space between // and comment'
                  '  [whitespace/comments] [4]')
    self.TestLint('// TODO(ljenkins):Fix this', end_space)
    self.TestLint('// TODO(ljenkins):', '')
    self.TestLint('// TODO(ljenkins): fix this', '')
    self.TestLint('// TODO(ljenkins): Fix this', '')
    self.TestLint('#endif  // TEST_URLTODOCID_WHICH_HAS_THAT_WORD_IN_IT_H_', '')
    self.TestLint('// See also similar TODO above', '')

  def testTwoSpacesBetweenCodeAndComments(self):
    self.TestLint('} // namespace foo',
                  'At least two spaces is best between code and comments'
                  '  [whitespace/comments] [2]')
    self.TestLint('}// namespace foo',
                  'At least two spaces is best between code and comments'
                  '  [whitespace/comments] [2]')
    self.TestLint('printf("foo"); // Outside quotes.',
                  'At least two spaces is best between code and comments'
                  '  [whitespace/comments] [2]')
    self.TestLint('int i = 0;  // Having two spaces is fine.', '')
    self.TestLint('int i = 0;   // Having three spaces is OK.', '')
    self.TestLint('// Top level comment', '')
    self.TestLint('  // Line starts with two spaces.', '')
    self.TestLint('foo();\n'
                  '{ // A scope is opening.', '')
    self.TestLint('  foo();\n'
                  '  { // An indented scope is opening.', '')
    self.TestLint('if (foo) { // not a pure scope; comment is too close!',
                  'At least two spaces is best between code and comments'
                  '  [whitespace/comments] [2]')
    self.TestLint('printf("// In quotes.")', '')
    self.TestLint('printf("\\"%s // In quotes.")', '')
    self.TestLint('printf("%s", "// In quotes.")', '')

  def testSpaceAfterCommentMarker(self):
    self.TestLint('//', '')
    self.TestLint('//x', 'Should have a space between // and comment'
                  '  [whitespace/comments] [4]')
    self.TestLint('// x', '')
    self.TestLint('//----', '')
    self.TestLint('//====', '')
    self.TestLint('//////', '')
    self.TestLint('////// x', '')
    self.TestLint('/// x', '')
    self.TestLint('///', '') # Empty Doxygen comment
    self.TestLint('////x', 'Should have a space between // and comment'
                  '  [whitespace/comments] [4]')

  # Test a line preceded by empty or comment lines.  There was a bug
  # that caused it to print the same warning N times if the erroneous
  # line was preceded by N lines of empty or comment lines.  To be
  # precise, the '// marker so line numbers and indices both start at
  # 1' line was also causing the issue.
  def testLinePrecededByEmptyOrCommentLines(self):
    def DoTest(self, lines):
      error_collector = ErrorCollector(self.assert_)
      cpplint.ProcessFileData('foo.cc', 'cc', lines, error_collector)
      # The warning appears only once.
      self.assertEquals(
          1,
          error_collector.Results().count(
              'Do not use namespace using-directives.  '
              'Use using-declarations instead.'
              '  [build/namespaces] [5]'))
    DoTest(self, ['using namespace foo;'])
    DoTest(self, ['', '', '', 'using namespace foo;'])
    DoTest(self, ['// hello', 'using namespace foo;'])

  def testNewlineAtEOF(self):
    def DoTest(self, data, is_missing_eof):
      error_collector = ErrorCollector(self.assert_)
      cpplint.ProcessFileData('foo.cc', 'cc', data.split('\n'),
                              error_collector)
      # The warning appears only once.
      self.assertEquals(
          int(is_missing_eof),
          error_collector.Results().count(
              'Could not find a newline character at the end of the file.'
              '  [whitespace/ending_newline] [5]'))

    DoTest(self, '// Newline\n// at EOF\n', False)
    DoTest(self, '// No newline\n// at EOF', True)

  def testInvalidUtf8(self):
    def DoTest(self, raw_bytes, has_invalid_utf8):
      error_collector = ErrorCollector(self.assert_)
      cpplint.ProcessFileData(
          'foo.cc', 'cc',
          unicode(raw_bytes, 'utf8', 'replace').split('\n'),
          error_collector)
      # The warning appears only once.
      self.assertEquals(
          int(has_invalid_utf8),
          error_collector.Results().count(
              'Line contains invalid UTF-8'
              ' (or Unicode replacement character).'
              '  [readability/utf8] [5]'))

    DoTest(self, 'Hello world\n', False)
    DoTest(self, '\xe9\x8e\xbd\n', False)
    DoTest(self, '\xe9x\x8e\xbd\n', True)
    # This is the encoding of the replacement character itself (which
    # you can see by evaluating codecs.getencoder('utf8')(u'\ufffd')).
    DoTest(self, '\xef\xbf\xbd\n', True)

  def testIsBlankLine(self):
    self.assert_(cpplint.IsBlankLine(''))
    self.assert_(cpplint.IsBlankLine(' '))
    self.assert_(cpplint.IsBlankLine(' \t\r\n'))
    self.assert_(not cpplint.IsBlankLine('int a;'))
    self.assert_(not cpplint.IsBlankLine('{'))

  def testBlankLinesCheck(self):
    self.TestBlankLinesCheck(['{\n', '\n', '\n', '}\n'], 1, 1)
    self.TestBlankLinesCheck(['  if (foo) {\n', '\n', '  }\n'], 1, 1)
    self.TestBlankLinesCheck(
        ['\n', '// {\n', '\n', '\n', '// Comment\n', '{\n', '}\n'], 0, 0)
    self.TestBlankLinesCheck(['\n', 'run("{");\n', '\n'], 0, 0)
    self.TestBlankLinesCheck(['\n', '  if (foo) { return 0; }\n', '\n'], 0, 0)

  def testAllowBlankLineBeforeClosingNamespace(self):
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData('foo.cc', 'cc',
                            ['namespace {', '', '}  // namespace'],
                            error_collector)
    self.assertEquals(0, error_collector.Results().count(
        'Blank line at the end of a code block.  Is this needed?'
        '  [whitespace/blank_line] [3]'))

  def testAllowBlankLineBeforeIfElseChain(self):
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData('foo.cc', 'cc',
                            ['if (hoge) {',
                             '',  # No warning
                             '} else if (piyo) {',
                             '',  # No warning
                             '} else if (piyopiyo) {',
                             '  hoge = true;',  # No warning
                             '} else {',
                             '',  # Warning on this line
                             '}'],
                            error_collector)
    self.assertEquals(1, error_collector.Results().count(
        'Blank line at the end of a code block.  Is this needed?'
        '  [whitespace/blank_line] [3]'))

  def testBlankLineBeforeSectionKeyword(self):
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData('foo.cc', 'cc',
                            ['class A {',
                             ' public:',
                             ' protected:',   # warning 1
                             ' private:',     # warning 2
                             '  struct B {',
                             '   public:',
                             '   private:'] +  # warning 3
                            ([''] * 100) +  # Make A and B longer than 100 lines
                            ['  };',
                             '  struct C {',
                             '   protected:',
                             '   private:',  # C is too short for warnings
                             '  };',
                             '};',
                             'class D',
                             '    : public {',
                             ' public:',  # no warning
                             '};'],
                            error_collector)
    self.assertEquals(2, error_collector.Results().count(
        '"private:" should be preceded by a blank line'
        '  [whitespace/blank_line] [3]'))
    self.assertEquals(1, error_collector.Results().count(
        '"protected:" should be preceded by a blank line'
        '  [whitespace/blank_line] [3]'))

  def testNoBlankLineAfterSectionKeyword(self):
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData('foo.cc', 'cc',
                            ['class A {',
                             ' public:',
                             '',  # warning 1
                             ' private:',
                             '',  # warning 2
                             '  struct B {',
                             '   protected:',
                             '',  # warning 3
                             '  };',
                             '};'],
                            error_collector)
    self.assertEquals(1, error_collector.Results().count(
        'Do not leave a blank line after "public:"'
        '  [whitespace/blank_line] [3]'))
    self.assertEquals(1, error_collector.Results().count(
        'Do not leave a blank line after "protected:"'
        '  [whitespace/blank_line] [3]'))
    self.assertEquals(1, error_collector.Results().count(
        'Do not leave a blank line after "private:"'
        '  [whitespace/blank_line] [3]'))

  def testElseOnSameLineAsClosingBraces(self):
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData('foo.cc', 'cc',
                            ['if (hoge) {',
                             '',
                             '}',
                             ' else {'  # Warning on this line
                             '',
                             '}'],
                            error_collector)
    self.assertEquals(1, error_collector.Results().count(
        'An else should appear on the same line as the preceding }'
        '  [whitespace/newline] [4]'))

  def testElseClauseNotOnSameLineAsElse(self):
    self.TestLint('  else DoSomethingElse();',
                  'Else clause should never be on same line as else '
                  '(use 2 lines)  [whitespace/newline] [4]')
    self.TestLint('  else ifDoSomethingElse();',
                  'Else clause should never be on same line as else '
                  '(use 2 lines)  [whitespace/newline] [4]')
    self.TestLint('  else if (blah) {', '')
    self.TestLint('  variable_ends_in_else = true;', '')

  def testComma(self):
    self.TestLint('a = f(1,2);',
                  'Missing space after ,  [whitespace/comma] [3]')
    self.TestLint('int tmp=a,a=b,b=tmp;',
                  ['Missing spaces around =  [whitespace/operators] [4]',
                   'Missing space after ,  [whitespace/comma] [3]'])
    self.TestLint('f(a, /* name */ b);', '')
    self.TestLint('f(a, /* name */b);', '')

  def testIndent(self):
    self.TestLint('static int noindent;', '')
    self.TestLint('  int two_space_indent;', '')
    self.TestLint('    int four_space_indent;', '')
    self.TestLint(' int one_space_indent;',
                  'Weird number of spaces at line-start.  '
                  'Are you using a 2-space indent?  [whitespace/indent] [3]')
    self.TestLint('   int three_space_indent;',
                  'Weird number of spaces at line-start.  '
                  'Are you using a 2-space indent?  [whitespace/indent] [3]')
    self.TestLint(' char* one_space_indent = "public:";',
                  'Weird number of spaces at line-start.  '
                  'Are you using a 2-space indent?  [whitespace/indent] [3]')
    self.TestLint(' public:', '')
    self.TestLint('  public:', '')
    self.TestLint('   public:', '')

  def testLabel(self):
    self.TestLint('public:',
                  'Labels should always be indented at least one space.  '
                  'If this is a member-initializer list in a constructor or '
                  'the base class list in a class definition, the colon should '
                  'be on the following line.  [whitespace/labels] [4]')
    self.TestLint('  public:', '')
    self.TestLint('   public:', '')
    self.TestLint(' public:', '')
    self.TestLint('  public:', '')
    self.TestLint('   public:', '')

  def testNotALabel(self):
    self.TestLint('MyVeryLongNamespace::MyVeryLongClassName::', '')

  def testTab(self):
    self.TestLint('\tint a;',
                  'Tab found; better to use spaces  [whitespace/tab] [1]')
    self.TestLint('int a = 5;\t\t// set a to 5',
                  'Tab found; better to use spaces  [whitespace/tab] [1]')

  def testParseArguments(self):
    old_usage = cpplint._USAGE
    old_error_categories = cpplint._ERROR_CATEGORIES
    old_output_format = cpplint._cpplint_state.output_format
    old_verbose_level = cpplint._cpplint_state.verbose_level
    old_filters = cpplint._cpplint_state.filters
    try:
      # Don't print usage during the tests, or filter categories
      cpplint._USAGE = ''
      cpplint._ERROR_CATEGORIES = ''

      self.assertRaises(SystemExit, cpplint.ParseArguments, [])
      self.assertRaises(SystemExit, cpplint.ParseArguments, ['--badopt'])
      self.assertRaises(SystemExit, cpplint.ParseArguments, ['--help'])
      self.assertRaises(SystemExit, cpplint.ParseArguments, ['--v=0'])
      self.assertRaises(SystemExit, cpplint.ParseArguments, ['--filter='])
      # This is illegal because all filters must start with + or -
      self.assertRaises(SystemExit, cpplint.ParseArguments, ['--filter=foo'])
      self.assertRaises(SystemExit, cpplint.ParseArguments,
                        ['--filter=+a,b,-c'])

      self.assertEquals(['foo.cc'], cpplint.ParseArguments(['foo.cc']))
      self.assertEquals(old_output_format, cpplint._cpplint_state.output_format)
      self.assertEquals(old_verbose_level, cpplint._cpplint_state.verbose_level)

      self.assertEquals(['foo.cc'],
                        cpplint.ParseArguments(['--v=1', 'foo.cc']))
      self.assertEquals(1, cpplint._cpplint_state.verbose_level)
      self.assertEquals(['foo.h'],
                        cpplint.ParseArguments(['--v=3', 'foo.h']))
      self.assertEquals(3, cpplint._cpplint_state.verbose_level)
      self.assertEquals(['foo.cpp'],
                        cpplint.ParseArguments(['--verbose=5', 'foo.cpp']))
      self.assertEquals(5, cpplint._cpplint_state.verbose_level)
      self.assertRaises(ValueError,
                        cpplint.ParseArguments, ['--v=f', 'foo.cc'])

      self.assertEquals(['foo.cc'],
                        cpplint.ParseArguments(['--output=emacs', 'foo.cc']))
      self.assertEquals('emacs', cpplint._cpplint_state.output_format)
      self.assertEquals(['foo.h'],
                        cpplint.ParseArguments(['--output=vs7', 'foo.h']))
      self.assertEquals('vs7', cpplint._cpplint_state.output_format)
      self.assertRaises(SystemExit,
                        cpplint.ParseArguments, ['--output=blah', 'foo.cc'])

      filt = '-,+whitespace,-whitespace/indent'
      self.assertEquals(['foo.h'],
                        cpplint.ParseArguments(['--filter='+filt, 'foo.h']))
      self.assertEquals(['-', '+whitespace', '-whitespace/indent'],
                        cpplint._cpplint_state.filters)

      self.assertEquals(['foo.cc', 'foo.h'],
                        cpplint.ParseArguments(['foo.cc', 'foo.h']))
    finally:
      cpplint._USAGE = old_usage
      cpplint._ERROR_CATEGORIES = old_error_categories
      cpplint._cpplint_state.output_format = old_output_format
      cpplint._cpplint_state.verbose_level = old_verbose_level
      cpplint._cpplint_state.filters = old_filters

  def testFilter(self):
    old_filters = cpplint._cpplint_state.filters
    try:
      cpplint._cpplint_state.SetFilters('-,+whitespace,-whitespace/indent')
      self.TestLint(
          '// Hello there ',
          'Line ends in whitespace.  Consider deleting these extra spaces.'
          '  [whitespace/end_of_line] [4]')
      self.TestLint('int a = (int)1.0;', '')
      self.TestLint(' weird opening space', '')
    finally:
      cpplint._cpplint_state.filters = old_filters

  def testDefaultFilter(self):
    default_filters = cpplint._DEFAULT_FILTERS
    old_filters = cpplint._cpplint_state.filters
    cpplint._DEFAULT_FILTERS = ['-whitespace']
    try:
      # Reset filters
      cpplint._cpplint_state.SetFilters('')
      self.TestLint('// Hello there ', '')
      cpplint._cpplint_state.SetFilters('+whitespace/end_of_line')
      self.TestLint(
          '// Hello there ',
          'Line ends in whitespace.  Consider deleting these extra spaces.'
          '  [whitespace/end_of_line] [4]')
      self.TestLint(' weird opening space', '')
    finally:
      cpplint._cpplint_state.filters = old_filters
      cpplint._DEFAULT_FILTERS = default_filters

  def testUnnamedNamespacesInHeaders(self):
    self.TestLanguageRulesCheck(
        'foo.h', 'namespace {',
        'Do not use unnamed namespaces in header files.  See'
        ' http://google-styleguide.googlecode.com/svn/trunk/cppguide.xml#Namespaces'
        ' for more information.  [build/namespaces] [4]')
    # namespace registration macros are OK.
    self.TestLanguageRulesCheck('foo.h', 'namespace {  \\', '')
    # named namespaces are OK.
    self.TestLanguageRulesCheck('foo.h', 'namespace foo {', '')
    self.TestLanguageRulesCheck('foo.h', 'namespace foonamespace {', '')
    self.TestLanguageRulesCheck('foo.cc', 'namespace {', '')
    self.TestLanguageRulesCheck('foo.cc', 'namespace foo {', '')

  def testBuildClass(self):
    # Test that the linter can parse to the end of class definitions,
    # and that it will report when it can't.
    # Use multi-line linter because it performs the ClassState check.
    self.TestMultiLineLint(
        'class Foo {',
        'Failed to find complete declaration of class Foo'
        '  [build/class] [5]')
    # Don't warn on forward declarations of various types.
    self.TestMultiLineLint(
        'class Foo;',
        '')
    self.TestMultiLineLint(
        """struct Foo*
             foo = NewFoo();""",
        '')
    # Here is an example where the linter gets confused, even though
    # the code doesn't violate the style guide.
    self.TestMultiLineLint(
        """class Foo
        #ifdef DERIVE_FROM_GOO
          : public Goo {
        #else
          : public Hoo {
        #endif
          };""",
        'Failed to find complete declaration of class Foo'
        '  [build/class] [5]')

  def testBuildEndComment(self):
    # The crosstool compiler we currently use will fail to compile the
    # code in this test, so we might consider removing the lint check.
    self.TestLint('#endif Not a comment',
                  'Uncommented text after #endif is non-standard.'
                  '  Use a comment.'
                  '  [build/endif_comment] [5]')

  def testBuildForwardDecl(self):
    # The crosstool compiler we currently use will fail to compile the
    # code in this test, so we might consider removing the lint check.
    self.TestLint('class Foo::Goo;',
                  'Inner-style forward declarations are invalid.'
                  '  Remove this line.'
                  '  [build/forward_decl] [5]')

  def testBuildHeaderGuard(self):
    file_path = 'mydir/foo.h'

    # We can't rely on our internal stuff to get a sane path on the open source
    # side of things, so just parse out the suggested header guard. This
    # doesn't allow us to test the suggested header guard, but it does let us
    # test all the other header tests.
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h', [], error_collector)
    expected_guard = ''
    matcher = re.compile(
      'No \#ifndef header guard found\, suggested CPP variable is\: ([A-Z_]+) ')
    for error in error_collector.ResultList():
      matches = matcher.match(error)
      if matches:
        expected_guard = matches.group(1)
        break

    # Make sure we extracted something for our header guard.
    self.assertNotEqual(expected_guard, '')

    # Wrong guard
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef FOO_H', '#define FOO_H'], error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            '#ifndef header guard has wrong style, please use: %s'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # No define
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef %s' % expected_guard], error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            'No #define header guard found, suggested CPP variable is: %s'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # Mismatched define
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef %s' % expected_guard,
                             '#define FOO_H'],
                            error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            '#ifndef and #define don\'t match, suggested CPP variable is: %s'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # No endif
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef %s' % expected_guard,
                             '#define %s' % expected_guard],
                            error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            '#endif line should be "#endif  // %s"'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # Commentless endif
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef %s' % expected_guard,
                             '#define %s' % expected_guard,
                             '#endif'],
                            error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            '#endif line should be "#endif  // %s"'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # Commentless endif for old-style guard
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef %s_' % expected_guard,
                             '#define %s_' % expected_guard,
                             '#endif'],
                            error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            '#endif line should be "#endif  // %s"'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # No header guard errors
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef %s' % expected_guard,
                             '#define %s' % expected_guard,
                             '#endif  // %s' % expected_guard],
                            error_collector)
    for line in error_collector.ResultList():
      if line.find('build/header_guard') != -1:
        self.fail('Unexpected error: %s' % line)

    # No header guard errors for old-style guard
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef %s_' % expected_guard,
                             '#define %s_' % expected_guard,
                             '#endif  // %s_' % expected_guard],
                            error_collector)
    for line in error_collector.ResultList():
      if line.find('build/header_guard') != -1:
        self.fail('Unexpected error: %s' % line)

    old_verbose_level = cpplint._cpplint_state.verbose_level
    try:
      cpplint._cpplint_state.verbose_level = 0
      # Warn on old-style guard if verbosity is 0.
      error_collector = ErrorCollector(self.assert_)
      cpplint.ProcessFileData(file_path, 'h',
                              ['#ifndef %s_' % expected_guard,
                               '#define %s_' % expected_guard,
                               '#endif  // %s_' % expected_guard],
                              error_collector)
      self.assertEquals(
          1,
          error_collector.ResultList().count(
              '#ifndef header guard has wrong style, please use: %s'
              '  [build/header_guard] [0]' % expected_guard),
          error_collector.ResultList())
    finally:
      cpplint._cpplint_state.verbose_level = old_verbose_level

    # Completely incorrect header guard
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef FOO',
                             '#define FOO',
                             '#endif  // FOO'],
                            error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            '#ifndef header guard has wrong style, please use: %s'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            '#endif line should be "#endif  // %s"'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # incorrect header guard with nolint
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'h',
                            ['#ifndef FOO  // NOLINT',
                             '#define FOO',
                             '#endif  // FOO NOLINT'],
                            error_collector)
    self.assertEquals(
        0,
        error_collector.ResultList().count(
            '#ifndef header guard has wrong style, please use: %s'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())
    self.assertEquals(
        0,
        error_collector.ResultList().count(
            '#endif line should be "#endif  // %s"'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

    # Special case for flymake
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData('mydir/foo_flymake.h',
                            'h', [], error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(
            'No #ifndef header guard found, suggested CPP variable is: %s'
            '  [build/header_guard] [5]' % expected_guard),
        error_collector.ResultList())

  def testBuildInclude(self):
    # Test that include statements have slashes in them.
    self.TestLint('#include "foo.h"',
                  'Include the directory when naming .h files'
                  '  [build/include] [4]')

  def testBuildPrintfFormat(self):
    self.TestLint(
        r'printf("\%%d", value);',
        '%, [, (, and { are undefined character escapes.  Unescape them.'
        '  [build/printf_format] [3]')

    self.TestLint(
        r'snprintf(buffer, sizeof(buffer), "\[%d", value);',
        '%, [, (, and { are undefined character escapes.  Unescape them.'
        '  [build/printf_format] [3]')

    self.TestLint(
        r'fprintf(file, "\(%d", value);',
        '%, [, (, and { are undefined character escapes.  Unescape them.'
        '  [build/printf_format] [3]')

    self.TestLint(
        r'vsnprintf(buffer, sizeof(buffer), "\\\{%d", ap);',
        '%, [, (, and { are undefined character escapes.  Unescape them.'
        '  [build/printf_format] [3]')

    # Don't warn if double-slash precedes the symbol
    self.TestLint(r'printf("\\%%%d", value);',
                  '')

  def testRuntimePrintfFormat(self):
    self.TestLint(
        r'fprintf(file, "%q", value);',
        '%q in format strings is deprecated.  Use %ll instead.'
        '  [runtime/printf_format] [3]')

    self.TestLint(
        r'aprintf(file, "The number is %12q", value);',
        '%q in format strings is deprecated.  Use %ll instead.'
        '  [runtime/printf_format] [3]')

    self.TestLint(
        r'printf(file, "The number is" "%-12q", value);',
        '%q in format strings is deprecated.  Use %ll instead.'
        '  [runtime/printf_format] [3]')

    self.TestLint(
        r'printf(file, "The number is" "%+12q", value);',
        '%q in format strings is deprecated.  Use %ll instead.'
        '  [runtime/printf_format] [3]')

    self.TestLint(
        r'printf(file, "The number is" "% 12q", value);',
        '%q in format strings is deprecated.  Use %ll instead.'
        '  [runtime/printf_format] [3]')

    self.TestLint(
        r'snprintf(file, "Never mix %d and %1$d parameters!", value);',
        '%N$ formats are unconventional.  Try rewriting to avoid them.'
        '  [runtime/printf_format] [2]')

  def TestLintLogCodeOnError(self, code, expected_message):
    # Special TestLint which logs the input code on error.
    result = self.PerformSingleLineLint(code)
    if result != expected_message:
      self.fail('For code: "%s"\nGot: "%s"\nExpected: "%s"'
                % (code, result, expected_message))

  def testBuildStorageClass(self):
    qualifiers = [None, 'const', 'volatile']
    signs = [None, 'signed', 'unsigned']
    types = ['void', 'char', 'int', 'float', 'double',
             'schar', 'int8', 'uint8', 'int16', 'uint16',
             'int32', 'uint32', 'int64', 'uint64']
    storage_classes = ['auto', 'extern', 'register', 'static', 'typedef']

    build_storage_class_error_message = (
        'Storage class (static, extern, typedef, etc) should be first.'
        '  [build/storage_class] [5]')

    # Some explicit cases. Legal in C++, deprecated in C99.
    self.TestLint('const int static foo = 5;',
                  build_storage_class_error_message)

    self.TestLint('char static foo;',
                  build_storage_class_error_message)

    self.TestLint('double const static foo = 2.0;',
                  build_storage_class_error_message)

    self.TestLint('uint64 typedef unsigned_long_long;',
                  build_storage_class_error_message)

    self.TestLint('int register foo = 0;',
                  build_storage_class_error_message)

    # Since there are a very large number of possibilities, randomly
    # construct declarations.
    # Make sure that the declaration is logged if there's an error.
    # Seed generator with an integer for absolute reproducibility.
    random.seed(25)
    for unused_i in range(10):
      # Build up random list of non-storage-class declaration specs.
      other_decl_specs = [random.choice(qualifiers), random.choice(signs),
                          random.choice(types)]
      # remove None
      other_decl_specs = filter(lambda x: x is not None, other_decl_specs)

      # shuffle
      random.shuffle(other_decl_specs)

      # insert storage class after the first
      storage_class = random.choice(storage_classes)
      insertion_point = random.randint(1, len(other_decl_specs))
      decl_specs = (other_decl_specs[0:insertion_point]
                    + [storage_class]
                    + other_decl_specs[insertion_point:])

      self.TestLintLogCodeOnError(
          ' '.join(decl_specs) + ';',
          build_storage_class_error_message)

      # but no error if storage class is first
      self.TestLintLogCodeOnError(
          storage_class + ' ' + ' '.join(other_decl_specs),
          '')

  def testLegalCopyright(self):
    legal_copyright_message = (
        'No copyright message found.  '
        'You should have a line: "Copyright [year] <Copyright Owner>"'
        '  [legal/copyright] [5]')

    copyright_line = '// Copyright 2008 Google Inc. All Rights Reserved.'

    file_path = 'mydir/googleclient/foo.cc'

    # There should be a copyright message in the first 10 lines
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'cc', [], error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(legal_copyright_message))

    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(
        file_path, 'cc',
        ['' for unused_i in range(10)] + [copyright_line],
        error_collector)
    self.assertEquals(
        1,
        error_collector.ResultList().count(legal_copyright_message))

    # Test that warning isn't issued if Copyright line appears early enough.
    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(file_path, 'cc', [copyright_line], error_collector)
    for message in error_collector.ResultList():
      if message.find('legal/copyright') != -1:
        self.fail('Unexpected error: %s' % message)

    error_collector = ErrorCollector(self.assert_)
    cpplint.ProcessFileData(
        file_path, 'cc',
        ['' for unused_i in range(9)] + [copyright_line],
        error_collector)
    for message in error_collector.ResultList():
      if message.find('legal/copyright') != -1:
        self.fail('Unexpected error: %s' % message)

  def testInvalidIncrement(self):
    self.TestLint('*count++;',
                  'Changing pointer instead of value (or unused value of '
                  'operator*).  [runtime/invalid_increment] [5]')

class CleansedLinesTest(unittest.TestCase):
  def testInit(self):
    lines = ['Line 1',
             'Line 2',
             'Line 3 // Comment test',
             'Line 4 /* Comment test */',
             'Line 5 "foo"']


    clean_lines = cpplint.CleansedLines(lines)
    self.assertEquals(lines, clean_lines.raw_lines)
    self.assertEquals(5, clean_lines.NumLines())

    self.assertEquals(['Line 1',
                       'Line 2',
                       'Line 3',
                       'Line 4',
                       'Line 5 "foo"'],
                      clean_lines.lines)

    self.assertEquals(['Line 1',
                       'Line 2',
                       'Line 3',
                       'Line 4',
                       'Line 5 ""'],
                      clean_lines.elided)

  def testInitEmpty(self):
    clean_lines = cpplint.CleansedLines([])
    self.assertEquals([], clean_lines.raw_lines)
    self.assertEquals(0, clean_lines.NumLines())

  def testCollapseStrings(self):
    collapse = cpplint.CleansedLines._CollapseStrings
    self.assertEquals('""', collapse('""'))             # ""     (empty)
    self.assertEquals('"""', collapse('"""'))           # """    (bad)
    self.assertEquals('""', collapse('"xyz"'))          # "xyz"  (string)
    self.assertEquals('""', collapse('"\\\""'))         # "\""   (string)
    self.assertEquals('""', collapse('"\'"'))           # "'"    (string)
    self.assertEquals('"\"', collapse('"\"'))           # "\"    (bad)
    self.assertEquals('""', collapse('"\\\\"'))         # "\\"   (string)
    self.assertEquals('"', collapse('"\\\\\\"'))        # "\\\"  (bad)
    self.assertEquals('""', collapse('"\\\\\\\\"'))     # "\\\\" (string)

    self.assertEquals('\'\'', collapse('\'\''))         # ''     (empty)
    self.assertEquals('\'\'', collapse('\'a\''))        # 'a'    (char)
    self.assertEquals('\'\'', collapse('\'\\\'\''))     # '\''   (char)
    self.assertEquals('\'', collapse('\'\\\''))         # '\'    (bad)
    self.assertEquals('', collapse('\\012'))            # '\012' (char)
    self.assertEquals('', collapse('\\xfF0'))           # '\xfF0' (char)
    self.assertEquals('', collapse('\\n'))              # '\n' (char)
    self.assertEquals('\#', collapse('\\#'))            # '\#' (bad)

    self.assertEquals('StringReplace(body, "", "");',
                      collapse('StringReplace(body, "\\\\", "\\\\\\\\");'))
    self.assertEquals('\'\' ""',
                      collapse('\'"\' "foo"'))


class OrderOfIncludesTest(CpplintTestBase):
  def setUp(self):
    self.include_state = cpplint._IncludeState()
    # Cheat os.path.abspath called in FileInfo class.
    self.os_path_abspath_orig = os.path.abspath
    os.path.abspath = lambda value: value

  def tearDown(self):
    os.path.abspath = self.os_path_abspath_orig

  def testCheckNextIncludeOrder_OtherThenCpp(self):
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._OTHER_HEADER))
    self.assertEqual('Found C++ system header after other header',
                     self.include_state.CheckNextIncludeOrder(
                         cpplint._CPP_SYS_HEADER))

  def testCheckNextIncludeOrder_CppThenC(self):
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._CPP_SYS_HEADER))
    self.assertEqual('Found C system header after C++ system header',
                     self.include_state.CheckNextIncludeOrder(
                         cpplint._C_SYS_HEADER))

  def testCheckNextIncludeOrder_LikelyThenCpp(self):
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._LIKELY_MY_HEADER))
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._CPP_SYS_HEADER))

  def testCheckNextIncludeOrder_PossibleThenCpp(self):
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._POSSIBLE_MY_HEADER))
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._CPP_SYS_HEADER))

  def testCheckNextIncludeOrder_CppThenLikely(self):
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._CPP_SYS_HEADER))
    # This will eventually fail.
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._LIKELY_MY_HEADER))

  def testCheckNextIncludeOrder_CppThenPossible(self):
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._CPP_SYS_HEADER))
    self.assertEqual('', self.include_state.CheckNextIncludeOrder(
        cpplint._POSSIBLE_MY_HEADER))

  def testClassifyInclude(self):
    file_info = cpplint.FileInfo
    classify_include = cpplint._ClassifyInclude
    self.assertEqual(cpplint._C_SYS_HEADER,
                     classify_include(file_info('foo/foo.cc'),
                                      'stdio.h',
                                      True))
    self.assertEqual(cpplint._CPP_SYS_HEADER,
                     classify_include(file_info('foo/foo.cc'),
                                      'string',
                                      True))
    self.assertEqual(cpplint._CPP_SYS_HEADER,
                     classify_include(file_info('foo/foo.cc'),
                                      'typeinfo',
                                      True))
    self.assertEqual(cpplint._OTHER_HEADER,
                     classify_include(file_info('foo/foo.cc'),
                                      'string',
                                      False))

    self.assertEqual(cpplint._LIKELY_MY_HEADER,
                     classify_include(file_info('foo/foo.cc'),
                                      'foo/foo-inl.h',
                                      False))
    self.assertEqual(cpplint._LIKELY_MY_HEADER,
                     classify_include(file_info('foo/internal/foo.cc'),
                                      'foo/public/foo.h',
                                      False))
    self.assertEqual(cpplint._POSSIBLE_MY_HEADER,
                     classify_include(file_info('foo/internal/foo.cc'),
                                      'foo/other/public/foo.h',
                                      False))
    self.assertEqual(cpplint._OTHER_HEADER,
                     classify_include(file_info('foo/internal/foo.cc'),
                                      'foo/other/public/foop.h',
                                      False))

  def testTryDropCommonSuffixes(self):
    self.assertEqual('foo/foo', cpplint._DropCommonSuffixes('foo/foo-inl.h'))
    self.assertEqual('foo/bar/foo',
                     cpplint._DropCommonSuffixes('foo/bar/foo_inl.h'))
    self.assertEqual('foo/foo', cpplint._DropCommonSuffixes('foo/foo.cc'))
    self.assertEqual('foo/foo_unusualinternal',
                     cpplint._DropCommonSuffixes('foo/foo_unusualinternal.h'))
    self.assertEqual('',
                     cpplint._DropCommonSuffixes('_test.cc'))
    self.assertEqual('test',
                     cpplint._DropCommonSuffixes('test.cc'))

  def testRegression(self):
    def Format(includes):
      return ''.join(['#include %s\n' % include for include in includes])

    # Test singleton cases first.
    self.TestLanguageRulesCheck('foo/foo.cc', Format(['"foo/foo.h"']), '')
    self.TestLanguageRulesCheck('foo/foo.cc', Format(['<stdio.h>']), '')
    self.TestLanguageRulesCheck('foo/foo.cc', Format(['<string>']), '')
    self.TestLanguageRulesCheck('foo/foo.cc', Format(['"foo/foo-inl.h"']), '')
    self.TestLanguageRulesCheck('foo/foo.cc', Format(['"bar/bar-inl.h"']), '')
    self.TestLanguageRulesCheck('foo/foo.cc', Format(['"bar/bar.h"']), '')

    # Test everything in a good and new order.
    self.TestLanguageRulesCheck('foo/foo.cc',
                                Format(['"foo/foo.h"',
                                        '"foo/foo-inl.h"',
                                        '<stdio.h>',
                                        '<string>',
                                        '"bar/bar-inl.h"',
                                        '"bar/bar.h"']),
                                '')

    # Test bad orders.
    self.TestLanguageRulesCheck(
        'foo/foo.cc',
        Format(['<string>', '<stdio.h>']),
        'Found C system header after C++ system header.'
        ' Should be: foo.h, c system, c++ system, other.'
        '  [build/include_order] [4]')
    self.TestLanguageRulesCheck(
        'foo/foo.cc',
        Format(['"foo/bar-inl.h"',
                '"foo/foo-inl.h"']),
        '')
    # -inl.h headers are no longer special.
    self.TestLanguageRulesCheck('foo/foo.cc',
                                Format(['"foo/foo-inl.h"', '<string>']),
                                '')
    self.TestLanguageRulesCheck('foo/foo.cc',
                                Format(['"foo/bar.h"', '"foo/bar-inl.h"']),
                                '')
    # Test componentized header.  OK to have my header in ../public dir.
    self.TestLanguageRulesCheck('foo/internal/foo.cc',
                                Format(['"foo/public/foo.h"', '<string>']),
                                '')
    # OK to have my header in other dir (not stylistically, but
    # cpplint isn't as good as a human).
    self.TestLanguageRulesCheck('foo/internal/foo.cc',
                                Format(['"foo/other/public/foo.h"',
                                        '<string>']),
                                '')
    self.TestLanguageRulesCheck('foo/foo.cc',
                                Format(['"foo/foo.h"',
                                        '<string>',
                                        '"base/google.h"',
                                        '"base/flags.h"']),
                                'Include "base/flags.h" not in alphabetical '
                                'order  [build/include_alpha] [4]')
    # According to the style, -inl.h should come before .h, but we don't
    # complain about that.
    self.TestLanguageRulesCheck('foo/foo.cc',
                                Format(['"foo/foo-inl.h"',
                                        '"foo/foo.h"',
                                        '"base/google.h"',
                                        '"base/google-inl.h"']),
                                '')


class CheckForFunctionLengthsTest(CpplintTestBase):
  def setUp(self):
    # Reducing these thresholds for the tests speeds up tests significantly.
    self.old_normal_trigger = cpplint._FunctionState._NORMAL_TRIGGER
    self.old_test_trigger = cpplint._FunctionState._TEST_TRIGGER

    cpplint._FunctionState._NORMAL_TRIGGER = 10
    cpplint._FunctionState._TEST_TRIGGER = 25

  def tearDown(self):
    cpplint._FunctionState._NORMAL_TRIGGER = self.old_normal_trigger
    cpplint._FunctionState._TEST_TRIGGER = self.old_test_trigger

  def TestFunctionLengthsCheck(self, code, expected_message):
    """Check warnings for long function bodies are as expected.

    Args:
      code: C++ source code expected to generate a warning message.
      expected_message: Message expected to be generated by the C++ code.
    """
    self.assertEquals(expected_message,
                      self.PerformFunctionLengthsCheck(code))

  def TriggerLines(self, error_level):
    """Return number of lines needed to trigger a function length warning.

    Args:
      error_level: --v setting for cpplint.

    Returns:
      Number of lines needed to trigger a function length warning.
    """
    return cpplint._FunctionState._NORMAL_TRIGGER * 2**error_level

  def TestLines(self, error_level):
    """Return number of lines needed to trigger a test function length warning.

    Args:
      error_level: --v setting for cpplint.

    Returns:
      Number of lines needed to trigger a test function length warning.
    """
    return cpplint._FunctionState._TEST_TRIGGER * 2**error_level

  def TestFunctionLengthCheckDefinition(self, lines, error_level):
    """Generate long function definition and check warnings are as expected.

    Args:
      lines: Number of lines to generate.
      error_level:  --v setting for cpplint.
    """
    trigger_level = self.TriggerLines(cpplint._VerboseLevel())
    self.TestFunctionLengthsCheck(
        'void test(int x)' + self.FunctionBody(lines),
        ('Small and focused functions are preferred: '
         'test() has %d non-comment lines '
         '(error triggered by exceeding %d lines).'
         '  [readability/fn_size] [%d]'
         % (lines, trigger_level, error_level)))

  def TestFunctionLengthCheckDefinitionOK(self, lines):
    """Generate shorter function definition and check no warning is produced.

    Args:
      lines: Number of lines to generate.
    """
    self.TestFunctionLengthsCheck(
        'void test(int x)' + self.FunctionBody(lines),
        '')

  def TestFunctionLengthCheckAtErrorLevel(self, error_level):
    """Generate and check function at the trigger level for --v setting.

    Args:
      error_level: --v setting for cpplint.
    """
    self.TestFunctionLengthCheckDefinition(self.TriggerLines(error_level),
                                           error_level)

  def TestFunctionLengthCheckBelowErrorLevel(self, error_level):
    """Generate and check function just below the trigger level for --v setting.

    Args:
      error_level: --v setting for cpplint.
    """
    self.TestFunctionLengthCheckDefinition(self.TriggerLines(error_level)-1,
                                           error_level-1)

  def TestFunctionLengthCheckAboveErrorLevel(self, error_level):
    """Generate and check function just above the trigger level for --v setting.

    Args:
      error_level: --v setting for cpplint.
    """
    self.TestFunctionLengthCheckDefinition(self.TriggerLines(error_level)+1,
                                           error_level)

  def FunctionBody(self, number_of_lines):
    return ' {\n' + '    this_is_just_a_test();\n'*number_of_lines + '}'

  def FunctionBodyWithBlankLines(self, number_of_lines):
    return ' {\n' + '    this_is_just_a_test();\n\n'*number_of_lines + '}'

  def FunctionBodyWithNoLints(self, number_of_lines):
    return (' {\n' +
            '    this_is_just_a_test();  // NOLINT\n'*number_of_lines + '}')

  # Test line length checks.
  def testFunctionLengthCheckDeclaration(self):
    self.TestFunctionLengthsCheck(
        'void test();',  # Not a function definition
        '')

  def testFunctionLengthCheckDeclarationWithBlockFollowing(self):
    self.TestFunctionLengthsCheck(
        ('void test();\n'
         + self.FunctionBody(66)),  # Not a function definition
        '')

  def testFunctionLengthCheckClassDefinition(self):
    self.TestFunctionLengthsCheck(  # Not a function definition
        'class Test' + self.FunctionBody(66) + ';',
        '')

  def testFunctionLengthCheckTrivial(self):
    self.TestFunctionLengthsCheck(
        'void test() {}',  # Not counted
        '')

  def testFunctionLengthCheckEmpty(self):
    self.TestFunctionLengthsCheck(
        'void test() {\n}',
        '')

  def testFunctionLengthCheckDefinitionBelowSeverity0(self):
    old_verbosity = cpplint._SetVerboseLevel(0)
    self.TestFunctionLengthCheckDefinitionOK(self.TriggerLines(0)-1)
    cpplint._SetVerboseLevel(old_verbosity)

  def testFunctionLengthCheckDefinitionAtSeverity0(self):
    old_verbosity = cpplint._SetVerboseLevel(0)
    self.TestFunctionLengthCheckDefinitionOK(self.TriggerLines(0))
    cpplint._SetVerboseLevel(old_verbosity)

  def testFunctionLengthCheckDefinitionAboveSeverity0(self):
    old_verbosity = cpplint._SetVerboseLevel(0)
    self.TestFunctionLengthCheckAboveErrorLevel(0)
    cpplint._SetVerboseLevel(old_verbosity)

  def testFunctionLengthCheckDefinitionBelowSeverity1v0(self):
    old_verbosity = cpplint._SetVerboseLevel(0)
    self.TestFunctionLengthCheckBelowErrorLevel(1)
    cpplint._SetVerboseLevel(old_verbosity)

  def testFunctionLengthCheckDefinitionAtSeverity1v0(self):
    old_verbosity = cpplint._SetVerboseLevel(0)
    self.TestFunctionLengthCheckAtErrorLevel(1)
    cpplint._SetVerboseLevel(old_verbosity)

  def testFunctionLengthCheckDefinitionBelowSeverity1(self):
    self.TestFunctionLengthCheckDefinitionOK(self.TriggerLines(1)-1)

  def testFunctionLengthCheckDefinitionAtSeverity1(self):
    self.TestFunctionLengthCheckDefinitionOK(self.TriggerLines(1))

  def testFunctionLengthCheckDefinitionAboveSeverity1(self):
    self.TestFunctionLengthCheckAboveErrorLevel(1)

  def testFunctionLengthCheckDefinitionSeverity1PlusBlanks(self):
    error_level = 1
    error_lines = self.TriggerLines(error_level) + 1
    trigger_level = self.TriggerLines(cpplint._VerboseLevel())
    self.TestFunctionLengthsCheck(
        'void test_blanks(int x)' + self.FunctionBody(error_lines),
        ('Small and focused functions are preferred: '
         'test_blanks() has %d non-comment lines '
         '(error triggered by exceeding %d lines).'
         '  [readability/fn_size] [%d]')
        % (error_lines, trigger_level, error_level))

  def testFunctionLengthCheckComplexDefinitionSeverity1(self):
    error_level = 1
    error_lines = self.TriggerLines(error_level) + 1
    trigger_level = self.TriggerLines(cpplint._VerboseLevel())
    self.TestFunctionLengthsCheck(
        ('my_namespace::my_other_namespace::MyVeryLongTypeName*\n'
         'my_namespace::my_other_namespace::MyFunction(int arg1, char* arg2)'
         + self.FunctionBody(error_lines)),
        ('Small and focused functions are preferred: '
         'my_namespace::my_other_namespace::MyFunction()'
         ' has %d non-comment lines '
         '(error triggered by exceeding %d lines).'
         '  [readability/fn_size] [%d]')
        % (error_lines, trigger_level, error_level))

  def testFunctionLengthCheckDefinitionSeverity1ForTest(self):
    error_level = 1
    error_lines = self.TestLines(error_level) + 1
    trigger_level = self.TestLines(cpplint._VerboseLevel())
    self.TestFunctionLengthsCheck(
        'TEST_F(Test, Mutator)' + self.FunctionBody(error_lines),
        ('Small and focused functions are preferred: '
         'TEST_F(Test, Mutator) has %d non-comment lines '
         '(error triggered by exceeding %d lines).'
         '  [readability/fn_size] [%d]')
        % (error_lines, trigger_level, error_level))

  def testFunctionLengthCheckDefinitionSeverity1ForSplitLineTest(self):
    error_level = 1
    error_lines = self.TestLines(error_level) + 1
    trigger_level = self.TestLines(cpplint._VerboseLevel())
    self.TestFunctionLengthsCheck(
        ('TEST_F(GoogleUpdateRecoveryRegistryProtectedTest,\n'
         '    FixGoogleUpdate_AllValues_MachineApp)'  # note: 4 spaces
         + self.FunctionBody(error_lines)),
        ('Small and focused functions are preferred: '
         'TEST_F(GoogleUpdateRecoveryRegistryProtectedTest, '  # 1 space
         'FixGoogleUpdate_AllValues_MachineApp) has %d non-comment lines '
         '(error triggered by exceeding %d lines).'
         '  [readability/fn_size] [%d]')
        % (error_lines+1, trigger_level, error_level))

  def testFunctionLengthCheckDefinitionSeverity1ForBadTestDoesntBreak(self):
    error_level = 1
    error_lines = self.TestLines(error_level) + 1
    trigger_level = self.TestLines(cpplint._VerboseLevel())
    self.TestFunctionLengthsCheck(
        ('TEST_F('
         + self.FunctionBody(error_lines)),
        ('Small and focused functions are preferred: '
         'TEST_F has %d non-comment lines '
         '(error triggered by exceeding %d lines).'
         '  [readability/fn_size] [%d]')
        % (error_lines, trigger_level, error_level))

  def testFunctionLengthCheckDefinitionSeverity1WithEmbeddedNoLints(self):
    error_level = 1
    error_lines = self.TriggerLines(error_level)+1
    trigger_level = self.TriggerLines(cpplint._VerboseLevel())
    self.TestFunctionLengthsCheck(
        'void test(int x)' + self.FunctionBodyWithNoLints(error_lines),
        ('Small and focused functions are preferred: '
         'test() has %d non-comment lines '
         '(error triggered by exceeding %d lines).'
         '  [readability/fn_size] [%d]')
        % (error_lines, trigger_level, error_level))

  def testFunctionLengthCheckDefinitionSeverity1WithNoLint(self):
    self.TestFunctionLengthsCheck(
        ('void test(int x)' + self.FunctionBody(self.TriggerLines(1))
         + '  // NOLINT -- long function'),
        '')

  def testFunctionLengthCheckDefinitionBelowSeverity2(self):
    self.TestFunctionLengthCheckBelowErrorLevel(2)

  def testFunctionLengthCheckDefinitionSeverity2(self):
    self.TestFunctionLengthCheckAtErrorLevel(2)

  def testFunctionLengthCheckDefinitionAboveSeverity2(self):
    self.TestFunctionLengthCheckAboveErrorLevel(2)

  def testFunctionLengthCheckDefinitionBelowSeverity3(self):
    self.TestFunctionLengthCheckBelowErrorLevel(3)

  def testFunctionLengthCheckDefinitionSeverity3(self):
    self.TestFunctionLengthCheckAtErrorLevel(3)

  def testFunctionLengthCheckDefinitionAboveSeverity3(self):
    self.TestFunctionLengthCheckAboveErrorLevel(3)

  def testFunctionLengthCheckDefinitionBelowSeverity4(self):
    self.TestFunctionLengthCheckBelowErrorLevel(4)

  def testFunctionLengthCheckDefinitionSeverity4(self):
    self.TestFunctionLengthCheckAtErrorLevel(4)

  def testFunctionLengthCheckDefinitionAboveSeverity4(self):
    self.TestFunctionLengthCheckAboveErrorLevel(4)

  def testFunctionLengthCheckDefinitionBelowSeverity5(self):
    self.TestFunctionLengthCheckBelowErrorLevel(5)

  def testFunctionLengthCheckDefinitionAtSeverity5(self):
    self.TestFunctionLengthCheckAtErrorLevel(5)

  def testFunctionLengthCheckDefinitionAboveSeverity5(self):
    self.TestFunctionLengthCheckAboveErrorLevel(5)

  def testFunctionLengthCheckDefinitionHugeLines(self):
    # 5 is the limit
    self.TestFunctionLengthCheckDefinition(self.TriggerLines(10), 5)

  def testFunctionLengthNotDeterminable(self):
    # Macro invocation without terminating semicolon.
    self.TestFunctionLengthsCheck(
        'MACRO(arg)',
        '')

    # Macro with underscores
    self.TestFunctionLengthsCheck(
        'MACRO_WITH_UNDERSCORES(arg1, arg2, arg3)',
        '')
    
    self.TestFunctionLengthsCheck(
        'NonMacro(arg)',
        'Lint failed to find start of function body.'
        '  [readability/fn_size] [5]')


class NoNonVirtualDestructorsTest(CpplintTestBase):

  def testNoError(self):
    self.TestMultiLineLint(
        """class Foo {
             virtual ~Foo();
             virtual void foo();
           };""",
        '')

    self.TestMultiLineLint(
        """class Foo {
             virtual inline ~Foo();
             virtual void foo();
           };""",
        '')

    self.TestMultiLineLint(
        """class Foo {
             inline virtual ~Foo();
             virtual void foo();
           };""",
        '')

    self.TestMultiLineLint(
        """class Foo::Goo {
             virtual ~Goo();
             virtual void goo();
           };""",
        '')
    self.TestMultiLineLint(
        'class Foo { void foo(); };',
        'More than one command on the same line  [whitespace/newline] [4]')

    self.TestMultiLineLint(
        """class Qualified::Goo : public Foo {
              virtual void goo();
           };""",
        '')

    self.TestMultiLineLint(
        # Line-ending :
        """class Goo :
           public Foo {
              virtual void goo();
           };""",
        'Labels should always be indented at least one space.  '
        'If this is a member-initializer list in a constructor or '
        'the base class list in a class definition, the colon should '
        'be on the following line.  [whitespace/labels] [4]')

  def testNoDestructorWhenVirtualNeeded(self):
    self.TestMultiLineLintRE(
        """class Foo {
             virtual void foo();
           };""",
        'The class Foo probably needs a virtual destructor')

  def testDestructorNonVirtualWhenVirtualNeeded(self):
    self.TestMultiLineLintRE(
        """class Foo {
             ~Foo();
             virtual void foo();
           };""",
        'The class Foo probably needs a virtual destructor')

  def testNoWarnWhenDerived(self):
    self.TestMultiLineLint(
        """class Foo : public Goo {
             virtual void foo();
           };""",
        '')

  def testNoDestructorWhenVirtualNeededClassDecorated(self):
    self.TestMultiLineLintRE(
        """class LOCKABLE API Foo {
             virtual void foo();
           };""",
        'The class Foo probably needs a virtual destructor')

  def testDestructorNonVirtualWhenVirtualNeededClassDecorated(self):
    self.TestMultiLineLintRE(
        """class LOCKABLE API Foo {
             ~Foo();
             virtual void foo();
           };""",
        'The class Foo probably needs a virtual destructor')

  def testNoWarnWhenDerivedClassDecorated(self):
    self.TestMultiLineLint(
        """class LOCKABLE API Foo : public Goo {
             virtual void foo();
           };""",
        '')

  def testInternalBraces(self):
    self.TestMultiLineLintRE(
        """class Foo {
             enum Goo {
                GOO
             };
             virtual void foo();
           };""",
        'The class Foo probably needs a virtual destructor')

  def testInnerClassNeedsVirtualDestructor(self):
    self.TestMultiLineLintRE(
        """class Foo {
             class Goo {
               virtual void goo();
             };
           };""",
        'The class Goo probably needs a virtual destructor')

  def testOuterClassNeedsVirtualDestructor(self):
    self.TestMultiLineLintRE(
        """class Foo {
             class Goo {
             };
             virtual void foo();
           };""",
        'The class Foo probably needs a virtual destructor')

  def testQualifiedClassNeedsVirtualDestructor(self):
    self.TestMultiLineLintRE(
        """class Qualified::Foo {
             virtual void foo();
           };""",
        'The class Qualified::Foo probably needs a virtual destructor')

  def testMultiLineDeclarationNoError(self):
    self.TestMultiLineLintRE(
        """class Foo
             : public Goo {
            virtual void foo();
           };""",
        '')

  def testMultiLineDeclarationWithError(self):
    self.TestMultiLineLint(
        """class Foo
           {
            virtual void foo();
           };""",
        ['{ should almost always be at the end of the previous line  '
         '[whitespace/braces] [4]',
         'The class Foo probably needs a virtual destructor due to having '
         'virtual method(s), one declared at line 2.  [runtime/virtual] [4]'])

  def testSnprintfSize(self):
    self.TestLint('vsnprintf(NULL, 0, format)', '')
    self.TestLint('snprintf(fisk, 1, format)',
                  'If you can, use sizeof(fisk) instead of 1 as the 2nd arg '
                  'to snprintf.  [runtime/printf] [3]')

  def testExplicitMakePair(self):
    self.TestLint('make_pair', '')
    self.TestLint('make_pair(42, 42)', '')
    self.TestLint('make_pair<',
                  'Omit template arguments from make_pair OR use pair directly'
                  ' OR if appropriate, construct a pair directly'
                  '  [build/explicit_make_pair] [4]')
    self.TestLint('make_pair <',
                  'Omit template arguments from make_pair OR use pair directly'
                  ' OR if appropriate, construct a pair directly'
                  '  [build/explicit_make_pair] [4]')
    self.TestLint('my_make_pair<int, int>', '')

# pylint: disable-msg=C6409
def setUp():
  """Runs before all tests are executed.
  """
  # Enable all filters, so we don't miss anything that is off by default.
  cpplint._DEFAULT_FILTERS = []
  cpplint._cpplint_state.SetFilters('')


# pylint: disable-msg=C6409
def tearDown():
  """A global check to make sure all error-categories have been tested.

  The main tearDown() routine is the only code we can guarantee will be
  run after all other tests have been executed.
  """
  try:
    if _run_verifyallcategoriesseen:
      ErrorCollector(None).VerifyAllCategoriesAreSeen()
  except NameError:
    # If nobody set the global _run_verifyallcategoriesseen, then
    # we assume we shouldn't run the test
    pass


if __name__ == '__main__':
  import sys
  # We don't want to run the VerifyAllCategoriesAreSeen() test unless
  # we're running the full test suite: if we only run one test,
  # obviously we're not going to see all the error categories.  So we
  # only run VerifyAllCategoriesAreSeen() when no commandline flags
  # are passed in.
  global _run_verifyallcategoriesseen
  _run_verifyallcategoriesseen = (len(sys.argv) == 1)

  setUp()
  unittest.main()
  tearDown()

########NEW FILE########
