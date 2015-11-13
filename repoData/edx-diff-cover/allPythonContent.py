__FILENAME__ = diff_reporter
"""
Classes for querying which lines have changed based on a diff.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from diff_cover.git_diff import GitDiffError
import re


class BaseDiffReporter(object):
    """
    Query information about lines changed in a diff.
    """

    __metaclass__ = ABCMeta

    def __init__(self, name):
        """
        Provide a `name` for the diff report, which will
        be included in the diff coverage report.
        """
        self._name = name

    @abstractmethod
    def src_paths_changed(self):
        """
        Returns a list of source paths changed in this diff.

        Source paths are guaranteed to be unique.
        """
        pass

    @abstractmethod
    def lines_changed(self, src_path):
        """
        Returns a list of line numbers changed in the
        source file at `src_path`.

        Each line is guaranteed to be included only once in the list
        and in ascending order.
        """
        pass

    def name(self):
        """
        Return the name of the diff, which will be included
        in the diff coverage report.
        """
        return self._name


class GitDiffReporter(BaseDiffReporter):
    """
    Query information from a Git diff between branches.
    """

    def __init__(self, compare_branch='origin/master', git_diff=None):
        """
        Configure the reporter to use `git_diff` as the wrapper
        for the `git diff` tool.  (Should have same interface
        as `git_diff.GitDiffTool`)
        """
        name = "{branch}...HEAD, staged, and unstaged changes".format(branch=compare_branch)
        super(GitDiffReporter, self).__init__(name)

        self._compare_branch = compare_branch
        self._git_diff_tool = git_diff

        # Cache diff information as a dictionary
        # with file path keys and line number list values
        self._diff_dict = None

    def clear_cache(self):
        """
        Reset the git diff result cache.
        """
        self._diff_dict = None

    def src_paths_changed(self):
        """
        See base class docstring.
        """

        # Get the diff dictionary
        diff_dict = self._git_diff()

        # Return the changed file paths (dict keys)
        # in alphabetical order
        return sorted(diff_dict.keys(), key=lambda x: x.lower())

    def lines_changed(self, src_path):
        """
        See base class docstring.
        """

        # Get the diff dictionary (cached)
        diff_dict = self._git_diff()

        # Look up the modified lines for the source file
        # If no lines modified, return an empty list
        return diff_dict.get(src_path, [])

    def _git_diff(self):
        """
        Run `git diff` and returns a dict in which the keys
        are changed file paths and the values are lists of
        line numbers.

        Guarantees that each line number within a file
        is unique (no repeats) and in ascending order.

        Returns a cached result if called multiple times.

        Raises a GitDiffError if `git diff` has an error.
        """

        # If we do not have a cached result, execute `git diff`
        if self._diff_dict is None:

            result_dict = dict()

            for diff_str in [
                self._git_diff_tool.diff_committed(self._compare_branch),
                self._git_diff_tool.diff_staged(),
                self._git_diff_tool.diff_unstaged()
            ]:

                # Parse the output of the diff string
                diff_dict = self._parse_diff_str(diff_str)

                for src_path in diff_dict.keys():

                    added_lines, deleted_lines = diff_dict[src_path]

                    # Remove any lines from the dict that have been deleted
                    # Include any lines that have been added
                    result_dict[src_path] = [
                        line for line in result_dict.get(src_path, [])
                        if not line in deleted_lines
                    ] + added_lines

            # Eliminate repeats and order line numbers
            for (src_path, lines) in result_dict.items():
                result_dict[src_path] = self._unique_ordered_lines(lines)

            # Store the resulting dict
            self._diff_dict = result_dict

        # Return the diff cache
        return self._diff_dict

    # Regular expressions used to parse the diff output
    SRC_FILE_RE = re.compile(r'^diff --git "?a/.*"? "?b/([^ \n"]*)"?')
    MERGE_CONFLICT_RE = re.compile(r'^diff --cc ([^ \n]*)')
    HUNK_LINE_RE = re.compile(r'\+([0-9]*)')

    def _parse_diff_str(self, diff_str):
        """
        Parse the output of `git diff` into a dictionary of the form:

            { SRC_PATH: (ADDED_LINES, DELETED_LINES) }

        where `ADDED_LINES` and `DELETED_LINES` are lists of line
        numbers added/deleted respectively.

        If the output could not be parsed, raises a GitDiffError.
        """

        # Create a dict to hold results
        diff_dict = dict()

        # Parse the diff string into sections by source file
        sections_dict = self._parse_source_sections(diff_str)
        for (src_path, diff_lines) in sections_dict.items():

            # Parse the hunk information for the source file
            # to determine lines changed for the source file
            diff_dict[src_path] = self._parse_lines(diff_lines)

        return diff_dict

    def _parse_source_sections(self, diff_str):
        """
        Given the output of `git diff`, return a dictionary
        with keys that are source file paths.

        Each value is a list of lines from the `git diff` output
        related to the source file.

        Raises a `GitDiffError` if `diff_str` is in an invalid format.
        """

        # Create a dict to map source files to lines in the diff output
        source_dict = dict()

        # Keep track of the current source file
        src_path = None

        # Signal that we've found a hunk (after starting a source file)
        found_hunk = False

        # Parse the diff string into sections by source file
        for line in diff_str.split('\n'):

            # If the line starts with "diff --git"
            # or "diff --cc" (in the case of a merge conflict)
            # then it is the start of a new source file
            if line.startswith('diff --git') or line.startswith('diff --cc'):

                # Retrieve the name of the source file
                src_path = self._parse_source_line(line)

                # Create an entry for the source file, if we don't
                # already have one.
                if src_path not in source_dict:
                    source_dict[src_path] = []

                # Signal that we're waiting for a hunk for this source file
                found_hunk = False

            # Every other line is stored in the dictionary for this source file
            # once we find a hunk section
            else:

                # Only add lines if we're in a hunk section
                # (ignore index and files changed lines)
                if found_hunk or line.startswith('@@'):

                    # Remember that we found a hunk
                    found_hunk = True

                    if src_path is not None:
                        source_dict[src_path].append(line)

                    else:
                        # We tolerate other information before we have
                        # a source file defined, unless it's a hunk line
                        if line.startswith("@@"):
                            msg = "Hunk has no source file: '{0}'".format(line)
                            raise GitDiffError(msg)

        return source_dict

    def _parse_lines(self, diff_lines):
        """
        Given the diff lines output from `git diff` for a particular
        source file, return a tuple of `(ADDED_LINES, DELETED_LINES)`

        where `ADDED_LINES` and `DELETED_LINES` are lists of line
        numbers added/deleted respectively.

        Raises a `GitDiffError` if the diff lines are in an invalid format.
        """

        added_lines = []
        deleted_lines = []

        current_line_new = None
        current_line_old = None

        for line in diff_lines:

            # If this is the start of the hunk definition, retrieve
            # the starting line number
            if line.startswith('@@'):
                line_num = self._parse_hunk_line(line)
                current_line_new, current_line_old = line_num, line_num

            # This is an added/modified line, so store the line number
            elif line.startswith('+'):

                # Since we parse for source file sections before
                # calling this method, we're guaranteed to have a source
                # file specified.  We check anyway just to be safe.
                if current_line_new is not None:

                    # Store the added line
                    added_lines.append(current_line_new)

                    # Increment the line number in the file
                    current_line_new += 1

            # This is a deleted line that does not exist in the final
            # version, so skip it
            elif line.startswith('-'):

                # Since we parse for source file sections before
                # calling this method, we're guaranteed to have a source
                # file specified.  We check anyway just to be safe.
                if current_line_old is not None:

                    # Store the deleted line
                    deleted_lines.append(current_line_old)

                    # Increment the line number in the file
                    current_line_old += 1

            # This is a line in the final version that was not modified.
            # Increment the line number, but do not store this as a changed
            # line.
            else:
                if current_line_old is not None:
                    current_line_old += 1

                if current_line_new is not None:
                    current_line_new += 1

                # If we are not in a hunk, then ignore the line
                else:
                    pass

        return added_lines, deleted_lines

    def _parse_source_line(self, line):
        """
        Given a source line in `git diff` output, return the path
        to the source file.
        """
        if '--git' in line:
            regex = self.SRC_FILE_RE
        elif '--cc' in line:
            regex = self.MERGE_CONFLICT_RE
        else:
            msg = "Do not recognize format of source in line '{0}'".format(line)
            raise GitDiffError(msg)

        # Parse for the source file path
        groups = regex.findall(line)

        if len(groups) == 1:
            return groups[0]

        else:
            msg = "Could not parse source path in line '{0}'".format(line)
            raise GitDiffError(msg)

    def _parse_hunk_line(self, line):
        """
        Given a hunk line in `git diff` output, return the line number
        at the start of the hunk.  A hunk is a segment of code that
        contains changes.

        The format of the hunk line is:

            @@ -k,l +n,m @@ TEXT

        where `k,l` represent the start line and length before the changes
        and `n,m` represent the start line and length after the changes.

        `git diff` will sometimes put a code excerpt from within the hunk
        in the `TEXT` section of the line.
        """
        # Split the line at the @@ terminators (start and end of the line)
        components = line.split('@@')

        # The first component should be an empty string, because
        # the line starts with '@@'.  The second component should
        # be the hunk information, and any additional components
        # are excerpts from the code.
        if len(components) >= 2:

            hunk_info = components[1]
            groups = self.HUNK_LINE_RE.findall(hunk_info)

            if len(groups) == 1:

                try:
                    return int(groups[0])

                except ValueError:
                    msg = "Could not parse '{0}' as a line number".format(groups[0])
                    raise GitDiffError(msg)

            else:
                msg = "Could not find start of hunk in line '{0}'".format(line)
                raise GitDiffError(msg)

        else:
            msg = "Could not parse hunk in line '{0}'".format(line)
            raise GitDiffError(msg)

    @staticmethod
    def _unique_ordered_lines(line_numbers):
        """
        Given a list of line numbers, return a list in which each line
        number is included once and the lines are ordered sequentially.
        """

        if len(line_numbers) == 0:
            return []

        # Ensure lines are unique by putting them in a set
        line_set = set(line_numbers)

        # Retrieve the list from the set, sort it, and return
        return sorted([line for line in line_set])

########NEW FILE########
__FILENAME__ = git_diff
"""
Wrapper for `git diff` command.
"""
from __future__ import unicode_literals
import six
import subprocess


class GitDiffError(Exception):
    """
    `git diff` command produced an error.
    """
    pass


class GitDiffTool(object):
    """
    Thin wrapper for a subset of the `git diff` command.
    """

    def __init__(self, subprocess_mod=subprocess):
        """
        Initialize the wrapper to use `subprocess_mod` to
        execute subprocesses.
        """
        self._subprocess = subprocess_mod

    def diff_committed(self, compare_branch='origin/master'):
        """
        Returns the output of `git diff` for committed
        changes not yet in origin/master.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return self._execute([
            'git', 'diff',
            "{branch}...HEAD".format(branch=compare_branch),
            '--no-ext-diff'
        ])

    def diff_unstaged(self):
        """
        Returns the output of `git diff` with no arguments, which
        is the diff for unstaged changes.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return self._execute(['git', 'diff', '--no-ext-diff'])

    def diff_staged(self):
        """
        Returns the output of `git diff --cached`, which
        is the diff for staged changes.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return self._execute(['git', 'diff', '--cached', '--no-ext-diff'])

    def _execute(self, command):
        """
        Execute `command` (list of command components)
        and returns the output.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        stdout_pipe = self._subprocess.PIPE
        process = self._subprocess.Popen(
            command, stdout=stdout_pipe,
            stderr=stdout_pipe
        )
        stdout, stderr = process.communicate()

        # If we get a non-empty output to stderr, raise an exception
        if bool(stderr):
            raise GitDiffError(stderr)

        # Convert the output to unicode (Python < 3)
        if isinstance(stdout, six.binary_type):
            return stdout.decode('utf-8', 'replace')
        else:
            return stdout

########NEW FILE########
__FILENAME__ = git_path
"""
Converter for `git diff` paths
"""
from __future__ import unicode_literals
import os
import six
import subprocess


class GitPathTool(object):
    """
    Converts `git diff` paths to absolute paths or relative paths to cwd.
    """

    def __init__(self, cwd):
        """
        Initialize the absolute path to the git project
        """
        self._cwd = cwd
        self._root = self._git_root()

    def relative_path(self, git_diff_path):
        """
        Returns git_diff_path relative to cwd.
        """
        # Remove git_root from src_path for searching the correct filename
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `diff_cover/violations_reporter.py`
        # search for `violations_reporter.py`
        root_rel_path = os.path.relpath(self._cwd, self._root)
        if isinstance(root_rel_path, six.binary_type):
            root_rel_path = root_rel_path.decode()
        rel_path = os.path.relpath(git_diff_path, root_rel_path)
        if isinstance(rel_path, six.binary_type):
            rel_path = rel_path.decode()
        return rel_path

    def absolute_path(self, src_path):
        """
        Returns absoloute git_diff_path
        """
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `other_package/some_file.py`
        # search for `/home/user/work/diff-cover/other_package/some_file.py`
        return os.path.join(self._root, src_path)

    def _git_root(self):
        """
        Returns the output of `git rev-parse --show-toplevel`, which
        is the absolute path for the git project root.
        """
        command = ['git', 'rev-parse', '--show-toplevel']
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        return stdout.strip()


########NEW FILE########
__FILENAME__ = report_generator
"""
Classes for generating diff coverage reports.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from jinja2 import Environment, PackageLoader
from lazy import lazy
from diff_cover.snippets import Snippet
import six


class DiffViolations(object):
    """
    Class to capture violations generated by a particular diff
    """
    def __init__(self, violations, measured_lines, diff_lines):
        self.lines = set(
            violation.line for violation in violations
        ).intersection(diff_lines)

        self.violations = set(
            violation for violation in violations
            if violation.line in self.lines
        )

        # By convention, a violation reporter
        # can return `None` to indicate that all lines are "measured"
        # by default.  This is an optimization to avoid counting
        # lines in all the source files.
        if measured_lines is None:
            self.measured_lines = set(diff_lines)
        else:
            self.measured_lines = set(measured_lines).intersection(diff_lines)


class BaseReportGenerator(object):
    """
    Generate a diff coverage report.
    """

    __metaclass__ = ABCMeta

    def __init__(self, violations_reporter, diff_reporter):
        """
        Configure the report generator to build a report
        from `violations_reporter` (of type BaseViolationReporter)
        and `diff_reporter` (of type BaseDiffReporter)
        """
        self._violations = violations_reporter
        self._diff = diff_reporter

        self._cache_violations = None

    @abstractmethod
    def generate_report(self, output_file):
        """
        Write the report to `output_file`, which is a file-like
        object implementing the `write()` method.

        Concrete subclasses should access diff coverage info
        using the base class methods.
        """
        pass

    def coverage_report_name(self):
        """
        Return the name of the coverage report.
        """
        return self._violations.name()

    def diff_report_name(self):
        """
        Return the name of the diff.
        """
        return self._diff.name()

    def src_paths(self):
        """
        Return a list of source files in the diff
        for which we have coverage information.
        """
        return set(src for src, summary in self._diff_violations.items()
                   if len(summary.measured_lines) > 0)

    def percent_covered(self, src_path):
        """
        Return a float percent of lines covered for the source
        in `src_path`.

        If we have no coverage information for `src_path`, returns None
        """
        diff_violations = self._diff_violations.get(src_path)

        if diff_violations is None:
            return None

        # Protect against a divide by zero
        num_measured = len(diff_violations.measured_lines)
        if num_measured > 0:
            num_uncovered = len(diff_violations.lines)
            return 100 - float(num_uncovered) / num_measured * 100

        else:
            return None

    def violation_lines(self, src_path):
        """
        Return a list of lines in violation (integers)
        in `src_path` that were changed.

        If we have no coverage information for
        `src_path`, returns an empty list.
        """

        diff_violations = self._diff_violations.get(src_path)

        if diff_violations is None:
            return []

        return sorted(diff_violations.lines)

    def total_num_lines(self):
        """
        Return the total number of lines in the diff for
        which we have coverage info.
        """

        return sum([len(summary.measured_lines) for summary
                    in self._diff_violations.values()])

    def total_num_violations(self):
        """
        Returns the total number of lines in the diff
        that are in violation.
        """

        return sum(
            len(summary.lines)
            for summary
            in self._diff_violations.values()
        )

    def total_percent_covered(self):
        """
        Returns the float percent of lines in the diff that are covered.
        (only counting lines for which we have coverage info).
        """
        total_lines = self.total_num_lines()

        if total_lines > 0:
            num_covered = total_lines - self.total_num_violations()
            return int(float(num_covered) / total_lines * 100)

        else:
            return 100

    @lazy
    def _diff_violations(self):
        """
        Returns a dictionary of the form:

            { SRC_PATH: DiffViolations(SRC_PATH) }

        where `SRC_PATH` is the path to the source file.

        To make this efficient, we cache and reuse the result.
        """
        return dict(
            (
                src_path, DiffViolations(
                    self._violations.violations(src_path),
                    self._violations.measured_lines(src_path),
                    self._diff.lines_changed(src_path),
                )
            ) for src_path in self._diff.src_paths_changed()
        )


# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(loader=TEMPLATE_LOADER,
                           trim_blocks=True,
                           lstrip_blocks=True)
TEMPLATE_ENV.filters['iteritems'] = six.iteritems


class TemplateReportGenerator(BaseReportGenerator):
    """
    Reporter that uses a template to generate the report.
    """

    # Subclasses override this to specify the name of the template
    # If not overridden, the template reporter will raise an exception
    TEMPLATE_NAME = None

    # Subclasses should set this to True to indicate
    # that they want to include source file snippets.
    INCLUDE_SNIPPETS = False

    def generate_report(self, output_file):
        """
        See base class.
        """

        if self.TEMPLATE_NAME is not None:

            # Find the template
            template = TEMPLATE_ENV.get_template(self.TEMPLATE_NAME)

            # Render the template
            report = template.render(self._context())

            # Encode the output as a bytestring (Python < 3)
            if not isinstance(report, six.binary_type):
                report = report.encode('utf-8')

            # Write the output file
            output_file.write(report)

    def _context(self):
        """
        Return the context to pass to the template.

        The context is a dict of the form:

        {
            'report_name': REPORT_NAME,
            'diff_name': DIFF_NAME,
            'src_stats': {SRC_PATH: {
                            'percent_covered': PERCENT_COVERED,
                            'violation_lines': [LINE_NUM, ...]
                            }, ... }
            'total_num_lines': TOTAL_NUM_LINES,
            'total_num_violations': TOTAL_NUM_VIOLATIONS,
            'total_percent_covered': TOTAL_PERCENT_COVERED
        }
        """

        # Calculate the information to pass to the template
        src_stats = dict(
            (src, self._src_path_stats(src)) for src in self.src_paths()
        )

        # Include snippet style info if we're displaying
        # source code snippets
        if self.INCLUDE_SNIPPETS:
            snippet_style = Snippet.style_defs()
        else:
            snippet_style = None

        return {
            'report_name': self.coverage_report_name(),
            'diff_name': self.diff_report_name(),
            'src_stats': src_stats,
            'total_num_lines': self.total_num_lines(),
            'total_num_violations': self.total_num_violations(),
            'total_percent_covered': self.total_percent_covered(),
            'snippet_style': snippet_style
        }

    @staticmethod
    def combine_adjacent_lines(line_numbers):
        """
        Given a sorted collection of line numbers this will
        turn them to strings and combine adjacent values

        [1, 2, 5, 6, 100] -> ["1-2", "5-6", "100"]
        """
        combine_template = "{0}-{1}"
        combined_list = []

        # Add a terminating value of `None` to list
        line_numbers.append(None)
        start = line_numbers[0]
        end = None

        for line_number in line_numbers[1:]:
            # If the current number is adjacent to the previous number
            if (end if end else start) + 1 == line_number:
                end = line_number
            else:
                if end:
                    combined_list.append(combine_template.format(start, end))
                else:
                    combined_list.append(str(start))
                start = line_number
                end = None
        return combined_list

    def _src_path_stats(self, src_path):
        """
        Return a dict of statistics for the source file at `src_path`.
        """

        # Find violation lines
        violation_lines = self.violation_lines(src_path)
        violations = sorted(self._diff_violations[src_path].violations)

        # Load source snippets (if the report will display them)
        # If we cannot load the file, then fail gracefully
        if self.INCLUDE_SNIPPETS:
            try:
                snippets = Snippet.load_snippets_html(src_path, violation_lines)
            except IOError:
                snippets = []
        else:
            snippets = []

        return {
            'percent_covered': self.percent_covered(src_path),
            'violation_lines': TemplateReportGenerator.combine_adjacent_lines(violation_lines),
            'violations': violations,
            'snippets_html': snippets
        }


class StringReportGenerator(TemplateReportGenerator):
    """
    Generate a string diff coverage report.
    """
    TEMPLATE_NAME = "console_coverage_report.txt"


class HtmlReportGenerator(TemplateReportGenerator):
    """
    Generate an HTML formatted diff coverage report.
    """
    TEMPLATE_NAME = "html_coverage_report.html"
    INCLUDE_SNIPPETS = True


class StringQualityReportGenerator(TemplateReportGenerator):
    """
    Generate a string diff quality report.
    """
    TEMPLATE_NAME = "console_quality_report.txt"


class HtmlQualityReportGenerator(TemplateReportGenerator):
    """
    Generate an HTML formatted diff quality report.
    """
    TEMPLATE_NAME = "html_quality_report.html"

########NEW FILE########
__FILENAME__ = snippets
"""
Load snippets from source files to show violation lines
in HTML reports.
"""
from __future__ import unicode_literals
from os.path import basename
import pygments
from pygments.lexers import TextLexer, _iter_lexerclasses
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
import six
import fnmatch


def guess_lexer_for_filename(_fn, _text, **options):
    """
    Ripped from the tip of pygments
    It is a version of this that supports python 2 and 3.
    The 1.6 version has a python3 bug this resolves
    """
    # todo - When pygments releases a new version this should be removed.
    fn = basename(_fn)
    primary = None
    matching_lexers = set()
    for lexer in _iter_lexerclasses():
        for filename in lexer.filenames:
            if fnmatch.fnmatch(fn, filename):
                matching_lexers.add(lexer)
                primary = lexer
        for filename in lexer.alias_filenames:
            if fnmatch.fnmatch(fn, filename):
                matching_lexers.add(lexer)
    if not matching_lexers:
        raise ClassNotFound('no lexer for filename %r found' % fn)
    if len(matching_lexers) == 1:
        return matching_lexers.pop()(**options)
    result = []
    for lexer in matching_lexers:
        rv = lexer.analyse_text(_text)
        if rv == 1.0:
            return lexer(**options)
        result.append((rv, lexer))

    # since py3 can no longer sort by class name by default, here is the
    # sorting function that works in both
    def type_sort(type_):
        return (type_[0], type_[1].__name__)
    result.sort(key=type_sort)

    if not result[-1][0] and primary is not None:
        return primary(**options)
    return result[-1][1](**options)


class Snippet(object):
    """
    A source code snippet.
    """

    VIOLATION_COLOR = '#ffcccc'
    DIV_CSS_CLASS = 'snippet'

    # Number of extra lines to include before and after
    # each snippet to provide context.
    NUM_CONTEXT_LINES = 4

    # Maximum distance between two violations within
    # a snippet.  If violations are further apart,
    # should split into two snippets.
    MAX_GAP_IN_SNIPPET = 4

    def __init__(self, src_tokens, src_filename,
                 start_line, violation_lines):
        """
        Create a source code snippet.

        `src_tokens` is a list of `(token_type, value)`
        tuples, parsed from the source file.
        NOTE: `value` must be `unicode`, not a `str`

        `src_filename` is the name of the source file,
        used to determine the source file language.

        `start_line` is the line number of first line
        in `src_str`.  The first line in the file is
        line number 1.

        `violation_lines` is a list of line numbers
        to highlight as violations.

        Raises a `ValueError` if `start_line` is less than 1
        """
        if start_line < 1:
            raise ValueError('Start line must be >= 1')

        self._src_tokens = src_tokens
        self._src_filename = src_filename
        self._start_line = start_line
        self._violation_lines = violation_lines

    @classmethod
    def style_defs(cls):
        """
        Return the CSS style definitions required
        by the formatted snippet.
        """
        formatter = HtmlFormatter()
        formatter.style.highlight_color = cls.VIOLATION_COLOR
        return formatter.get_style_defs()

    def html(self):
        """
        Return an HTML representation of the snippet.
        """
        formatter = HtmlFormatter(
            cssclass=self.DIV_CSS_CLASS,
            linenos=True,
            linenostart=self._start_line,
            hl_lines=self._shift_lines(
                self._violation_lines,
                self._start_line
            ),
            lineanchors=self._src_filename
        )

        return pygments.format(self.src_tokens(), formatter)

    def src_tokens(self):
        """
        Return a list of `(token_type, value)` tokens
        parsed from the source file.
        """
        return self._src_tokens

    def line_range(self):
        """
        Return a tuple of the form `(start_line, end_line)`
        indicating the start and end line number of the snippet.
        """
        num_lines = len(self.text().split('\n'))
        end_line = self._start_line + num_lines - 1
        return (self._start_line, end_line)

    def text(self):
        """
        Return the source text for the snippet.
        """
        return ''.join([val for _, val in self._src_tokens])

    @classmethod
    def load_snippets_html(cls, src_path, violation_lines):
        """
        Load snippets from the file at `src_path` and format
        them as HTML.

        See `load_snippets()` for details.
        """
        snippet_list = cls.load_snippets(src_path, violation_lines)
        return [snippet.html() for snippet in snippet_list]

    @classmethod
    def load_snippets(cls, src_path, violation_lines):
        """
        Load snippets from the file at `src_path` to show
        violations on lines in the list `violation_lines`
        (list of line numbers, starting at index 0).

        The file at `src_path` should be a text file (not binary).

        Returns a list of `Snippet` instances.

        Raises an `IOError` if the file could not be loaded.
        """
        # Load the contents of the file
        with open(src_path) as src_file:
            contents = src_file.read()

        # Convert the source file to unicode (Python < 3)
        if isinstance(contents, six.binary_type):
            contents = contents.decode('utf-8', 'replace')

        # Construct a list of snippet ranges
        src_lines = contents.split('\n')
        snippet_ranges = cls._snippet_ranges(len(src_lines), violation_lines)

        # Parse the source into tokens
        token_stream = cls._parse_src(contents, src_path)

        # Group the tokens by snippet
        token_groups = cls._group_tokens(token_stream, snippet_ranges)

        return [
            Snippet(tokens, src_path, start, violation_lines)
            for (start, _), tokens in six.iteritems(token_groups)
        ]

    @classmethod
    def _parse_src(cls, src_contents, src_filename):
        """
        Return a stream of `(token_type, value)` tuples
        parsed from `src_contents` (str)

        Uses `src_filename` to guess the type of file
        so it can highlight syntax correctly.
        """

        # Parse the source into tokens
        try:
            lexer = guess_lexer_for_filename(src_filename, src_contents)
        except ClassNotFound:
            lexer = TextLexer()

        # Ensure that we don't strip newlines from
        # the source file when lexing.
        lexer.stripnl = False

        return pygments.lex(src_contents, lexer)

    @classmethod
    def _group_tokens(cls, token_stream, range_list):
        """
        Group tokens into snippet ranges.

        `token_stream` is a generator that produces
        `(token_type, value)` tuples,

        `range_list` is a list of `(start, end)` tuples representing
        the (inclusive) range of line numbers for each snippet.

        Assumes that `range_list` is an ascending order by start value.

        Returns a dict mapping ranges to lists of tokens:
        {
            (4, 10): [(ttype_1, val_1), (ttype_2, val_2), ...],
            (29, 39): [(ttype_3, val_3), ...],
            ...
        }

        The algorithm is slightly complicated because a single token
        can contain multiple line breaks.
        """

        # Create a map from ranges (start/end tuples) to tokens
        token_map = dict((rng, []) for rng in range_list)

        # Keep track of the current line number; we will
        # increment this as we encounter newlines in token values
        line_num = 1

        for ttype, val in token_stream:

            # If there are newlines in this token,
            # we need to split it up and check whether
            # each line within the token is within one
            # of our ranges.
            if '\n' in val:
                val_lines = val.split('\n')

                # Check if the tokens match each range
                for (start, end), filtered_tokens in six.iteritems(token_map):

                    # Filter out lines that are not in this range
                    include_vals = [
                        val_lines[i] for i in
                        range(0, len(val_lines))
                        if i + line_num in range(start, end + 1)
                    ]

                    # If we found any lines, store the tokens
                    if len(include_vals) > 0:
                        token = (ttype, '\n'.join(include_vals))
                        filtered_tokens.append(token)

                # Increment the line number
                # by the number of lines we found
                line_num += len(val_lines) - 1

            # No newline in this token
            # If we're in the line range, add it
            else:
                # Check if the tokens match each range
                for (start, end), filtered_tokens in six.iteritems(token_map):

                    # If we got a match, store the token
                    if line_num in range(start, end + 1):
                        filtered_tokens.append((ttype, val))

                    # Otherwise, ignore the token

        return token_map

    @classmethod
    def _snippet_ranges(cls, num_src_lines, violation_lines):
        """
        Given the number of source file lines and list of
        violation line numbers, return a list of snippet
        ranges of the form `(start_line, end_line)`.

        Each snippet contains a few extra lines of context
        before/after the first/last violation.  Nearby
        violations are grouped within the same snippet.
        """
        current_range = (None, None)
        lines_since_last_violation = 0
        snippet_ranges = []
        for line_num in range(1, num_src_lines + 1):

            # If we have not yet started a snippet,
            # check if we can (is this line a violation?)
            if current_range[0] is None:
                if line_num in violation_lines:

                    # Expand to include extra context, but not before line 1
                    snippet_start = max(1, line_num - cls.NUM_CONTEXT_LINES)
                    current_range = (snippet_start, None)
                    lines_since_last_violation = 0

            # If we are within a snippet, check if we
            # can end the snippet (have we gone enough
            # lines without hitting a violation?)
            elif current_range[1] is None:
                if line_num in violation_lines:
                    lines_since_last_violation = 0

                elif lines_since_last_violation > cls.MAX_GAP_IN_SNIPPET:

                    # Expand to include extra context, but not after last line
                    snippet_end = line_num - lines_since_last_violation
                    snippet_end = min(
                        num_src_lines,
                        snippet_end + cls.NUM_CONTEXT_LINES
                    )
                    current_range = (current_range[0], snippet_end)

                    # Store the snippet and start looking for the next one
                    snippet_ranges.append(current_range)
                    current_range = (None, None)

            # Another line since the last violation
            lines_since_last_violation += 1

        # If we started a snippet but didn't finish it, do so now
        if current_range[0] is not None and current_range[1] is None:
            snippet_ranges.append((current_range[0], num_src_lines))

        return snippet_ranges

    @staticmethod
    def _shift_lines(line_num_list, start_line):
        """
        Shift all line numbers in `line_num_list` so that
        `start_line` is treated as line 1.

        For example, `[5, 8, 9]` with `start_line=3` would
        become `[3, 6, 7]`.

        Assumes that all entries in `line_num_list` are greater
        than or equal to `start_line`; otherwise, they will
        be excluded from the list.
        """
        return [line_num - start_line + 1
                for line_num in line_num_list
                if line_num >= start_line]

########NEW FILE########
__FILENAME__ = snippet_src
Line 1
Line 2
Line 3
Line 4
Line 5
Line 6
Line 7
Line 8
Line 9
Line 10
Line 11
Line 12
Line 13
Line 14
Line 15
Line 16
Line 17
Line 18
Line 19
Line 20
Line 21
Line 22
Line 23
Line 24
Line 25
Line 26
Line 27
Line 28
Line 29
Line 30
Line 31
Line 32
Line 33
Line 34
Line 35
Line 36
Line 37
Line 38
Line 39
Line 40
Line 41
Line 42
Line 43
Line 44
Line 45
Line 46
Line 47
Line 48
Line 49
Line 50
Line 51
Line 52
Line 53
Line 54
Line 55
Line 56
Line 57
Line 58
Line 59
Line 60
Line 61
Line 62
Line 63
Line 64
Line 65
Line 66
Line 67
Line 68
Line 69
Line 70
Line 71
Line 72
Line 73
Line 74
Line 75
Line 76
Line 77
Line 78
Line 79
Line 80
Line 81
Line 82
Line 83
Line 84
Line 85
Line 86
Line 87
Line 88
Line 89
Line 90
Line 91
Line 92
Line 93
Line 94
Line 95
Line 96
Line 97
Line 98
Line 99
Line 100
########NEW FILE########
__FILENAME__ = violations_test_file
def func_1(apple, my_list):
    if apple<10:
        # Do something 
        my_list.append(apple)
    return my_list[1:]
def func_2(spongebob, squarepants):
    """A less messy function"""
    for char in spongebob:
        if char in squarepants:
            return char
    return None

########NEW FILE########
__FILENAME__ = helpers
"""
Test helper functions.
"""
import random
import sys
import six
import os.path
import difflib
from nose.tools import ok_

if sys.version_info[:2] <= (2, 6):
    import unittest2 as unittest
else:
    import unittest

HUNK_BUFFER = 2
MAX_LINE_LENGTH = 300
LINE_STRINGS = ['test', '+ has a plus sign', '- has a minus sign']


def assert_long_str_equal(expected, actual, strip=False):
    """
    Assert that two strings are equal and
    print the diff if they are not.

    If `strip` is True, strip both strings before comparing.
    """
    # If we've been given a byte string, we need to convert
    # it back to unicode.  Otherwise, Python3 won't
    # let us use string methods!
    if isinstance(expected, six.binary_type):
        expected = expected.decode('utf-8')
    if isinstance(actual, six.binary_type):
        actual = actual.decode('utf-8')

    if strip:
        expected = expected.strip()
        actual = actual.strip()

    if expected != actual:

        # Print a human-readable diff
        diff = difflib.Differ().compare(
            expected.split('\n'), actual.split('\n')
        )

        # Fail the test
        ok_(False, '\n\n' + '\n'.join(diff))


def fixture_path(rel_path):
    """
    Returns the absolute path to a fixture file
    given `rel_path` relative to the fixture directory.
    """
    fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    return os.path.join(fixture_dir, rel_path)


def load_fixture(rel_path, encoding=None):
    """
    Return the contents of the file at `rel_path`
    (relative path to the "fixtures" directory).

    If `encoding` is not None, attempts to decode
    the contents as `encoding` (e.g. 'utf-8').
    """
    with open(fixture_path(rel_path)) as fixture_file:
        contents = fixture_file.read()

    if encoding is not None and isinstance(contents, six.binary_type):
        contents = contents.decode('utf-8')

    return contents


def line_numbers(start, end):
    """
    Return a list of line numbers, in [start, end] (inclusive).
    """
    return [line for line in range(start, end + 1)]


def git_diff_output(diff_dict, deleted_files=None):
    """
    Construct fake output from `git diff` using the description
    defined by `diff_dict`, which is a dictionary of the form:

        {
            SRC_FILE_NAME: MODIFIED_LINES,
            ...
        }

    where `SRC_FILE_NAME` is the name of a source file in the diff,
    and `MODIFIED_LINES` is a list of lines added or changed in the
    source file.

    `deleted_files` is a list of files that have been deleted

    The content of the source files are randomly generated.

    Returns a byte string.
    """

    output = []

    # Entries for deleted files
    output.extend(_deleted_file_entries(deleted_files))

    # Entries for source files
    for (src_file, modified_lines) in diff_dict.items():

        output.extend(_source_file_entry(src_file, modified_lines))

    return '\n'.join(output)


def _deleted_file_entries(deleted_files):
    """
    Create fake `git diff` output for files that have been
    deleted in this changeset.

    `deleted_files` is a list of files deleted in the changeset.

    Returns a list of lines in the diff output.
    """

    output = []

    if deleted_files is not None:

        for src_file in deleted_files:
            # File information
            output.append('diff --git a/{0} b/{1}'.format(src_file, src_file))
            output.append('index 629e8ad..91b8c0a 100644')
            output.append('--- a/{0}'.format(src_file))
            output.append('+++ b/dev/null')

            # Choose a random number of lines
            num_lines = random.randint(1, 30)

            # Hunk information
            output.append('@@ -0,{0} +0,0 @@'.format(num_lines))
            output.extend(['-' + _random_string() for _ in range(num_lines)])

    return output


def _source_file_entry(src_file, modified_lines):
    """
    Create fake `git diff` output for added/modified lines.

    `src_file` is the source file with the changes;
    `modified_lines` is the list of modified line numbers.

    Returns a list of lines in the diff output.
    """

    output = []

    # Line for the file names
    output.append('diff --git a/{0} b/{1}'.format(src_file, src_file))

    # Index line
    output.append('index 629e8ad..91b8c0a 100644')

    # Additions/deletions
    output.append('--- a/{0}'.format(src_file))
    output.append('+++ b/{0}'.format(src_file))

    # Hunk information
    for (start, end) in _hunks(modified_lines):
        output.extend(_hunk_entry(start, end, modified_lines))

    return output


def _hunk_entry(start, end, modified_lines):
    """
    Generates fake `git diff` output for a hunk,
    where `start` and `end` are the start/end lines of the hunk
    and `modified_lines` is a list of modified lines in the hunk.

    Just as `git diff` does, this will include a few lines before/after
    the changed lines in each hunk.
    """
    output = []

    # The actual hunk usually has a few lines before/after
    start -= HUNK_BUFFER
    end += HUNK_BUFFER

    if start < 0:
        start = 0

    # Hunk definition line
    # Real `git diff` output would have different line numbers
    # for before/after the change, but since we're only interested
    # in after the change, we use the same numbers for both.
    length = end - start
    output.append('@@ -{0},{1} +{0},{1} @@'.format(start, length))

    # Output line modifications
    for line_number in range(start, end + 1):

        # This is a changed line, so prepend a + sign
        if line_number in modified_lines:

            # Delete the old line
            output.append('-' + _random_string())

            # Include the changed line
            output.append('+' + _random_string())

        # This is a line we didn't modify, so no + or - signs
        # but prepend with a space.
        else:
            output.append(' ' + _random_string())

    return output


def _hunks(modified_lines):
    """
    Given a list of line numbers, return a list of hunks represented
    as `(start, end)` tuples.
    """

    # Identify contiguous lines as hunks
    hunks = []
    last_line = None

    for line in sorted(modified_lines):

        # If this is contiguous with the last line, continue the hunk
        # We're guaranteed at this point to have at least one hunk
        if (line - 1) == last_line:
            start, _ = hunks[-1]
            hunks[-1] = (start, line)

        # If non-contiguous, start a new hunk with just the current line
        else:
            hunks.append((line, line))

        # Store the last line
        last_line = line

    return hunks


def _random_string():
    """
    Return a random byte string with length in the range
    [0, `MAX_LINE_LENGTH`] (inclusive).
    """
    return random.choice(LINE_STRINGS)

########NEW FILE########
__FILENAME__ = test_args
from __future__ import unicode_literals
from diff_cover.tool import parse_coverage_args, parse_quality_args
from diff_cover.tests.helpers import unittest


class ParseArgsTest(unittest.TestCase):

    def test_parse_with_html_report(self):
        argv = ['reports/coverage.xml',
                '--html-report', 'diff_cover.html']

        arg_dict = parse_coverage_args(argv)

        self.assertEqual(
            arg_dict.get('coverage_xml'),
            ['reports/coverage.xml']
        )

        self.assertEqual(
            arg_dict.get('html_report'),
            'diff_cover.html'
        )

    def test_parse_with_no_html_report(self):
        argv = ['reports/coverage.xml']

        arg_dict = parse_coverage_args(argv)
        self.assertEqual(
            arg_dict.get('coverage_xml'),
            ['reports/coverage.xml']
        )

    def test_parse_invalid_arg(self):

        # No coverage XML report specified
        invalid_argv = [[], ['--html-report', 'diff_cover.html']]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_coverage_args(argv)


class ParseQualityArgsTest(unittest.TestCase):

    def test_parse_with_html_report(self):
        argv = ['--violations', 'pep8',
                '--html-report', 'diff_cover.html']

        arg_dict = parse_quality_args(argv)

        self.assertEqual(arg_dict.get('violations'), 'pep8')
        self.assertEqual(arg_dict.get('html_report'), 'diff_cover.html')
        self.assertEqual(arg_dict.get('input_reports'), [])

    def test_parse_with_no_html_report(self):
        argv = ['--violations', 'pylint']

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get('violations'), 'pylint')
        self.assertEqual(arg_dict.get('input_reports'), [])

    def test_parse_with_one_input_report(self):
        argv = ['--violations', 'pylint', 'pylint_report.txt']

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get('input_reports'), ['pylint_report.txt'])

    def test_parse_with_multiple_input_reports(self):
        argv = [
            '--violations', 'pylint',
            'pylint_report_1.txt', 'pylint_report_2.txt'
        ]

        arg_dict = parse_quality_args(argv)
        self.assertEqual(
            arg_dict.get('input_reports'),
            ['pylint_report_1.txt', 'pylint_report_2.txt']
        )

    def test_parse_with_options(self):
        argv = [
            '--violations', 'pep8',
            '--options="--exclude=\'*/migrations*\'"'
        ]
        arg_dict = parse_quality_args(argv)
        self.assertEqual(
            arg_dict.get('options'),
            '"--exclude=\'*/migrations*\'"'
        )

    def test_parse_invalid_arg(self):
        # No code quality test provided
        invalid_argv = [[], ['--html-report', 'diff_cover.html']]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_quality_args(argv)

########NEW FILE########
__FILENAME__ = test_diff_reporter
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mock
from textwrap import dedent
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool, GitDiffError
from diff_cover.tests.helpers import line_numbers, git_diff_output, unittest


class GitDiffReporterTest(unittest.TestCase):

    def setUp(self):

        # Create a mock git diff wrapper
        self._git_diff = mock.MagicMock(GitDiffTool)

        # Create the diff reporter
        self.diff = GitDiffReporter(git_diff=self._git_diff)

    def test_name(self):

        # Expect that diff report is named after its compare branch
        self.assertEqual(
            self.diff.name(), 'origin/master...HEAD, staged, and unstaged changes'
        )

    def test_name_compare_branch(self):
        # Override the default branch
        self.assertEqual(
            GitDiffReporter(git_diff=self._git_diff, compare_branch='release').name(),
            'release...HEAD, staged, and unstaged changes'
        )

    def test_git_source_paths(self):

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output(dict(), deleted_files=['README.md'])
        )

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Validate the source paths
        # They should be in alphabetical order
        self.assertEqual(len(source_paths), 4)
        self.assertEqual('file3.py', source_paths[0])
        self.assertEqual('README.md', source_paths[1])
        self.assertEqual('subdir/file1.py', source_paths[2])
        self.assertEqual('subdir/file2.py', source_paths[3])

    def test_duplicate_source_paths(self):

        # Duplicate the output for committed, staged, and unstaged changes
        diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output(diff, diff, diff)

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Should see only one copy of source files
        self.assertEqual(len(source_paths), 1)
        self.assertEqual('subdir/file1.py', source_paths[0])

    def test_git_lines_changed(self):

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output(dict(), deleted_files=['README.md'])
        )

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10) + line_numbers(34, 47))

    def test_ignore_lines_outside_src(self):

        # Add some lines at the start of the diff, before any
        # source files are specified
        diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10)})
        master_diff = "\n".join(['- deleted line', '+ added line', diff])

        # Configure the git diff output
        self._set_git_diff_output(master_diff, "", "")

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10))

    def test_one_line_file(self):

        # Files with only one line have a special format
        # in which the "length" part of the hunk is not specified
        diff_str = dedent("""
            diff --git a/diff_cover/one_line.txt b/diff_cover/one_line.txt
            index 0867e73..9daeafb 100644
            --- a/diff_cover/one_line.txt
            +++ b/diff_cover/one_line.txt
            @@ -1,3 +1 @@
            test
            -test
            -test
            """).strip()

        # Configure the git diff output
        self._set_git_diff_output(diff_str, "", "")

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('one_line.txt')

        # Expect that no lines are changed
        self.assertEqual(len(lines_changed), 0)

    def test_git_deleted_lines(self):

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output(dict(), deleted_files=['README.md'])
        )

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('README.md')

        # Validate no lines changed
        self.assertEqual(len(lines_changed), 0)

    def test_git_unicode_filename(self):

        # Filenames with unicode characters have double quotes surrounding them
        # in the git diff output.
        diff_str = dedent("""
            diff --git "a/unic\303\270\342\210\202e\314\201.txt" "b/unic\303\270\342\210\202e\314\201.txt"
            new file mode 100644
            index 0000000..248ebea
            --- /dev/null
            +++ "b/unic\303\270\342\210\202e\314\201.txt"
            @@ -0,0 +1,13 @@
            +μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος
            +οὐλομένην, ἣ μυρί᾽ Ἀχαιοῖς ἄλγε᾽ ἔθηκε,
            +πολλὰς δ᾽ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν
            """).strip()

        self._set_git_diff_output(diff_str, "", "")
        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('unic\303\270\342\210\202e\314\201.txt')

        # Expect that three lines changed
        self.assertEqual(len(lines_changed), 3)

    def test_git_repeat_lines(self):

        # Same committed, staged, and unstaged lines
        diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output(diff, diff, diff)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10) + line_numbers(34, 47))

    def test_git_overlapping_lines(self):

        master_diff = git_diff_output(
            {'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}
        )

        # Overlap, extending the end of the hunk (lines 3 to 10)
        overlap_1 = git_diff_output({'subdir/file1.py': line_numbers(5, 14)})

        # Overlap, extending the beginning of the hunk (lines 34 to 47)
        overlap_2 = git_diff_output({'subdir/file1.py': line_numbers(32, 37)})

        # Lines in staged / unstaged overlap with lines in master
        self._set_git_diff_output(master_diff, overlap_1, overlap_2)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 14) + line_numbers(32, 47))

    def test_git_line_within_hunk(self):

        master_diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})

        # Surround hunk in master (lines 3 to 10)
        surround = git_diff_output({'subdir/file1.py': line_numbers(2, 11)})

        # Within hunk in master (lines 34 to 47)
        within = git_diff_output({'subdir/file1.py': line_numbers(35, 46)})

        # Lines in staged / unstaged overlap with hunks in master
        self._set_git_diff_output(master_diff, surround, within)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(2, 11) + line_numbers(34, 47))

    def test_inter_diff_conflict(self):

        # Commit changes to lines 3 through 10
        added_diff = git_diff_output({'file.py': line_numbers(3, 10)})

        # Delete the lines we modified
        deleted_lines = []
        for line in added_diff.split('\n'):

            # Any added line becomes a deleted line
            if line.startswith('+'):
                deleted_lines.append(line.replace('+', '-'))

            # No need to include lines we already deleted
            elif line.startswith('-'):
                pass

            # Keep any other line
            else:
                deleted_lines.append(line)

        deleted_diff = "\n".join(deleted_lines)

        # Try all combinations of diff conflicts
        combinations = [(added_diff, deleted_diff, ''),
                        (added_diff, '', deleted_diff),
                        ('', added_diff, deleted_diff),
                        (added_diff, deleted_diff, deleted_diff)]

        for (master_diff, staged_diff, unstaged_diff) in combinations:

            # Set up so we add lines, then delete them
            self._set_git_diff_output(master_diff, staged_diff, unstaged_diff)

            # Should have no lines changed, since
            # we deleted all the lines we modified
            fail_msg = dedent("""
            master_diff = {0}
            staged_diff = {1}
            unstaged_diff = {2}
            """).format(master_diff, staged_diff, unstaged_diff)

            self.assertEqual(self.diff.lines_changed('file.py'), [],
                             msg=fail_msg)

    def test_git_no_such_file(self):

        diff = git_diff_output({
            'subdir/file1.py': [1],
            'subdir/file2.py': [2],
            'file3.py': [3]
        })

        # Configure the git diff output
        self._set_git_diff_output(diff, "", "")

        lines_changed = self.diff.lines_changed('no_such_file.txt')
        self.assertEqual(len(lines_changed), 0)

    def test_no_diff(self):

        # Configure the git diff output
        self._set_git_diff_output('', '', '')

        # Expect no files changed
        source_paths = self.diff.src_paths_changed()
        self.assertEqual(source_paths, [])

    def test_git_diff_error(self):

        invalid_hunk_str = dedent("""
           diff --git a/subdir/file1.py b/subdir/file1.py
           @@ invalid @@ Text
        """).strip()

        no_src_line_str = "@@ -33,10 +34,13 @@ Text"

        non_numeric_lines = dedent("""
            diff --git a/subdir/file1.py b/subdir/file1.py
            @@ -1,2 +a,b @@
        """).strip()

        missing_line_num = dedent("""
            diff --git a/subdir/file1.py b/subdir/file1.py
            @@ -1,2 +  @@
        """).strip()

        missing_src_str = "diff --git "

        # List of (stdout, stderr) git diff pairs that should cause
        # a GitDiffError to be raised.
        err_outputs = [
            invalid_hunk_str, no_src_line_str,
            non_numeric_lines, missing_line_num,
            missing_src_str
        ]

        for diff_str in err_outputs:

            # Configure the git diff output
            self._set_git_diff_output(diff_str, '', '')

            # Expect that both methods that access git diff raise an error
            with self.assertRaises(GitDiffError):
                print("src_paths_changed() "
                      "should fail for {0}".format(diff_str))
                self.diff.src_paths_changed()

            with self.assertRaises(GitDiffError):
                print("lines_changed() should fail for {0}".format(diff_str))
                self.diff.lines_changed('subdir/file1.py')

    def test_plus_sign_in_hunk_bug(self):

        # This was a bug that caused a parse error
        diff_str = dedent("""
            diff --git a/file.py b/file.py
            @@ -16,16 +16,7 @@ 1 + 2
            + test
            + test
            + test
            + test
            """)

        self._set_git_diff_output(diff_str, '', '')

        lines_changed = self.diff.lines_changed('file.py')
        self.assertEqual(lines_changed, [16, 17, 18, 19])

    def test_terminating_chars_in_hunk(self):

        # Check what happens when there's an @@ symbol after the
        # first terminating @@ symbol
        diff_str = dedent("""
            diff --git a/file.py b/file.py
            @@ -16,16 +16,7 @@ and another +23,2 @@ symbol
            + test
            + test
            + test
            + test
            """)

        self._set_git_diff_output(diff_str, '', '')

        lines_changed = self.diff.lines_changed('file.py')
        self.assertEqual(lines_changed, [16, 17, 18, 19])

    def test_merge_conflict_diff(self):

        # Handle different git diff format when in the middle
        # of a merge conflict
        diff_str = dedent("""
            diff --cc subdir/src.py
            index d2034c0,e594d54..0000000
            diff --cc subdir/src.py
            index d2034c0,e594d54..0000000
            --- a/subdir/src.py
            +++ b/subdir/src.py
            @@@ -16,88 -16,222 +16,7 @@@ text
            + test
            ++<<<<<< HEAD
            + test
            ++=======
        """)

        self._set_git_diff_output(diff_str, '', '')

        lines_changed = self.diff.lines_changed('subdir/src.py')
        self.assertEqual(lines_changed, [16, 17, 18, 19])

    def _set_git_diff_output(self, committed_diff,
                             staged_diff, unstaged_diff):
        """
        Configure the git diff tool to return `committed_diff`,
        `staged_diff`, and `unstaged_diff` as outputs from
        `git diff`
        """
        self.diff.clear_cache()
        self._git_diff.diff_committed.return_value = committed_diff
        self._git_diff.diff_staged.return_value = staged_diff
        self._git_diff.diff_unstaged.return_value = unstaged_diff

########NEW FILE########
__FILENAME__ = test_git_diff
from __future__ import unicode_literals
import mock
from diff_cover.git_diff import GitDiffTool, GitDiffError
from diff_cover.tests.helpers import unittest


class TestGitDiffTool(unittest.TestCase):

    def setUp(self):

        # Create mock subprocess to simulate `git diff`
        self.subprocess = mock.Mock()
        self.process = mock.Mock()
        self.subprocess.Popen = mock.Mock(return_value=self.process)
        self.process.communicate = mock.Mock()

        # Create the git diff tool
        self.tool = GitDiffTool(subprocess_mod=self.subprocess)

    def test_diff_committed(self):

        self._set_git_diff_output('test output', '')
        output = self.tool.diff_committed()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', 'diff', 'origin/master...HEAD', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_unstaged(self):
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_unstaged()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', 'diff', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_staged(self):
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_staged()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', 'diff', '--cached', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_committed_compare_branch(self):

        # Override the default compare branch
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_committed(compare_branch='release')

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', 'diff', 'release...HEAD', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_errors(self):
        self._set_git_diff_output('test output', 'fatal error')

        with self.assertRaises(GitDiffError):
            self.tool.diff_unstaged()

        with self.assertRaises(GitDiffError):
            self.tool.diff_staged()

        with self.assertRaises(GitDiffError):
            self.tool.diff_unstaged()

    def _set_git_diff_output(self, stdout, stderr):
        """
        Configure the `git diff` mock to output `stdout`
        and `stderr` to stdout and stderr, respectively.
        """
        self.process.communicate.return_value = (stdout, stderr)

########NEW FILE########
__FILENAME__ = test_git_path
from __future__ import unicode_literals
import mock
from diff_cover.git_path import GitPathTool
from diff_cover.tests.helpers import unittest


class TestGitPathTool(unittest.TestCase):

    def setUp(self):
        # Create mock subprocess to simulate `git rev-parse`
        self.process = mock.Mock()
        self.subprocess = mock.patch('diff_cover.git_path.subprocess').start()
        self.subprocess.Popen.return_value = self.process

    def tearDown(self):
        mock.patch.stopall()

    def test_project_root_command(self):
        self._set_git_root('/phony/path')

        GitPathTool('/phony/path')

        # Expect that the correct command was executed
        expected = ['git', 'rev-parse', '--show-toplevel']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_relative_path(self):
        self._set_git_root('/home/user/work/diff-cover')
        expected = 'violations_reporter.py'
        cwd = '/home/user/work/diff-cover/diff_cover'

        tool = GitPathTool(cwd)
        path = tool.relative_path('diff_cover/violations_reporter.py')

        # Expect relative path from diff_cover
        self.assertEqual(path, expected)

    def test_absolute_path(self):
        self._set_git_root('/home/user/work/diff-cover')
        expected = '/home/user/work/diff-cover/other_package/file.py'
        cwd = '/home/user/work/diff-cover/diff_cover'

        tool = GitPathTool(cwd)
        path = tool.absolute_path('other_package/file.py')

        # Expect absolute path to file.py
        self.assertEqual(path, expected)

    def _set_git_root(self, git_root):
        """
        Configure the process mock to output `stdout`
        to a given git project root.
        """
        self.process.communicate.return_value = (git_root, '')

########NEW FILE########
__FILENAME__ = test_integration
"""
High-level integration tests of diff-cover tool.
"""
from __future__ import unicode_literals
from mock import patch, Mock
import os
import os.path
from subprocess import Popen
from io import BytesIO
import tempfile
import shutil
from diff_cover.tool import main
from diff_cover.diff_reporter import GitDiffError
from diff_cover.tests.helpers import fixture_path, \
    assert_long_str_equal, unittest


class ToolsIntegrationBase(unittest.TestCase):
    """
    Base class for diff-cover and diff-quality integration tests
    """
    _old_cwd = None

    def setUp(self):
        """
        Patch the output of `git` commands and `os.getcwd`
        set the cwd to the fixtures dir
        """
        # Set the CWD to the fixtures dir
        self._old_cwd = os.getcwd()
        os.chdir(fixture_path(''))

        self._mock_popen = patch('subprocess.Popen').start()
        self._mock_sys = patch('diff_cover.tool.sys').start()
        self._mock_getcwd = patch('diff_cover.tool.os.getcwd').start()
        self._git_root_path = '/project/path'
        self._mock_getcwd.return_value = self._git_root_path

    def tearDown(self):
        """
        Undo all patches and reset the cwd
        """
        patch.stopall()
        os.chdir(self._old_cwd)

    def _check_html_report(self, git_diff_path, expected_html_path, tool_args):
        """
        Verify that the tool produces the expected HTML report.

        `git_diff_path` is a path to a fixture containing the (patched) output of
        the call to `git diff`.

        `expected_console_path` is a path to the fixture containing
        the expected HTML output of the tool.

        `tool_args` is a list of command line arguments to pass
        to the tool.  You should include the name of the tool
        as the first argument.
        """

        # Patch the output of `git diff`
        with open(git_diff_path) as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Create a temporary directory to hold the output HTML report
        # Add a cleanup to ensure the directory gets deleted
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir))
        html_report_path = os.path.join(temp_dir, 'diff_coverage.html')

        # Patch the command-line arguments
        self._set_sys_args(tool_args + ['--html-report', html_report_path])

        # Execute the tool
        main()

        # Check the HTML report
        with open(expected_html_path) as expected_file:
            with open(html_report_path) as html_report:
                html = html_report.read()
                expected = expected_file.read()
                assert_long_str_equal(expected, html, strip=True)

    def _check_console_report(self, git_diff_path, expected_console_path, tool_args):
        """
        Verify that the tool produces the expected console report.

        `git_diff_path` is a path to a fixture containing the (patched) output of
        the call to `git diff`.

        `expected_console_path` is a path to the fixture containing
        the expected console output of the tool.

        `tool_args` is a list of command line arguments to pass
        to the tool.  You should include the name of the tool
        as the first argument.
        """

        # Patch the output of `git diff`
        with open(git_diff_path) as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Capture stdout to a string buffer
        string_buffer = BytesIO()
        self._capture_stdout(string_buffer)

        # Patch sys.argv
        self._set_sys_args(tool_args)

        # Execute the tool
        main()

        # Check the console report
        with open(expected_console_path) as expected_file:
            report = string_buffer.getvalue()
            expected = expected_file.read()
            assert_long_str_equal(expected, report, strip=True)

    def _set_sys_args(self, argv):
        """
        Patch sys.argv with the argument array `argv`.
        """
        self._mock_sys.argv = argv

    def _capture_stdout(self, string_buffer):
        """
        Redirect output sent to `sys.stdout` to the BytesIO buffer
        `string_buffer`.
        """
        self._mock_sys.stdout = string_buffer

    def _set_git_diff_output(self, stdout, stderr):
        """
        Patch the call to `git diff` to output `stdout`
        and `stderr`.
        Patch the `git rev-parse` command to output
        a phony directory.
        """
        def patch_diff(command, **kwargs):
            if command[0:2] == ['git', 'diff']:
                mock = Mock()
                mock.communicate.return_value = (stdout, stderr)
                return mock
            elif command[0:2] == ['git', 'rev-parse']:
                mock = Mock()
                mock.communicate.return_value = (self._git_root_path, '')
                return mock
            else:
                process = Popen(command, **kwargs)
                return process
        self._mock_popen.side_effect = patch_diff


class DiffCoverIntegrationTest(ToolsIntegrationBase):
    """
    High-level integration test.
    The `git diff` is a mock, but everything else is our code.
    """

    def test_added_file_html(self):
        self._check_html_report(
            'git_diff_add.txt',
            'add_html_report.html',
            ['diff-cover', 'coverage.xml']
        )

    def test_added_file_console(self):
        self._check_console_report(
            'git_diff_add.txt',
            'add_console_report.txt',
            ['diff-cover', 'coverage.xml']
        )

    def test_deleted_file_html(self):
        self._check_html_report(
            'git_diff_delete.txt',
            'delete_html_report.html',
            ['diff-cover', 'coverage.xml']
        )

    def test_deleted_file_console(self):
        self._check_console_report(
            'git_diff_delete.txt',
            'delete_console_report.txt',
            ['diff-cover', 'coverage.xml'],
        )

    def test_changed_file_html(self):
        self._check_html_report(
            'git_diff_changed.txt',
            'changed_html_report.html',
            ['diff-cover', 'coverage.xml']
        )

    def test_changed_file_console(self):
        self._check_console_report(
            'git_diff_changed.txt',
            'changed_console_report.txt',
            ['diff-cover', 'coverage.xml']
        )

    def test_moved_file_html(self):
        self._check_html_report(
            'git_diff_moved.txt',
            'moved_html_report.html',
            ['diff-cover', 'moved_coverage.xml']
        )

    def test_moved_file_console(self):
        self._check_console_report(
            'git_diff_moved.txt',
            'moved_console_report.txt',
            ['diff-cover', 'moved_coverage.xml']
        )

    def test_mult_inputs_html(self):
        self._check_html_report(
            'git_diff_mult.txt',
            'mult_inputs_html_report.html',
            ['diff-cover', 'coverage1.xml', 'coverage2.xml']
        )

    def test_mult_inputs_console(self):
        self._check_console_report(
            'git_diff_mult.txt',
            'mult_inputs_console_report.txt',
            ['diff-cover', 'coverage1.xml', 'coverage2.xml']
        )

    def test_unicode_console(self):
        self._check_console_report(
            'git_diff_unicode.txt',
            'unicode_console_report.txt',
            ['diff-cover', 'unicode_coverage.xml']
        )

    def test_unicode_html(self):
        self._check_html_report(
            'git_diff_unicode.txt',
            'unicode_html_report.html',
            ['diff-cover', 'unicode_coverage.xml']
        )

    def test_git_diff_error(self):

        # Patch sys.argv
        self._set_sys_args(['diff-cover', 'coverage.xml'])

        # Patch the output of `git diff` to return an error
        self._set_git_diff_output('', 'fatal error')

        # Expect an error
        with self.assertRaises(GitDiffError):
            main()


class DiffQualityIntegrationTest(ToolsIntegrationBase):
    """
    High-level integration test.
    """

    def test_git_diff_error_diff_quality(self):

        # Patch sys.argv
        self._set_sys_args(['diff-quality', '--violations', 'pep8'])

        # Patch the output of `git diff` to return an error
        self._set_git_diff_output('', 'fatal error')

        # Expect an error
        with self.assertRaises(GitDiffError):
            main()

    def test_added_file_pep8_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pep8_violations_report.html',
            ['diff-quality', '--violations=pep8']
        )

    def test_added_file_pylint_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pylint_violations_report.html',
            ['diff-quality', '--violations=pylint']
        )

    def test_added_file_pep8_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pep8_violations_report.txt',
            ['diff-quality', '--violations=pep8']
        )

    def test_added_file_pep8_console_exclude_file(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'empty_pep8_violations.txt',
            ['diff-quality', '--violations=pep8', '--options="--exclude=violations_test_file.py"']
        )

    def test_added_file_pylint_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pylint_violations_console_report.txt',
            ['diff-quality', '--violations=pylint'],
        )

    def test_pre_generated_pylint_report(self):

        # Pass in a pre-generated pylint report instead of letting
        # the tool call pylint itself.
        self._check_console_report(
            'git_diff_violations.txt',
            'pylint_violations_report.txt',
            ['diff-quality', '--violations=pylint', 'pylint_report.txt']
        )

    def test_pre_generated_pep8_report(self):

        # Pass in a pre-generated pep8 report instead of letting
        # the tool call pep8 itself.
        self._check_console_report(
            'git_diff_violations.txt',
            'pep8_violations_report.txt',
            ['diff-quality', '--violations=pep8', 'pep8_report.txt']
        )

########NEW FILE########
__FILENAME__ = test_report_generator
from __future__ import unicode_literals
import mock
from io import BytesIO
from textwrap import dedent
from diff_cover.diff_reporter import BaseDiffReporter
from diff_cover.violations_reporter import BaseViolationReporter, Violation
from diff_cover.report_generator import (
    BaseReportGenerator, HtmlReportGenerator,
    StringReportGenerator, TemplateReportGenerator
)
from diff_cover.tests.helpers import (
    load_fixture, assert_long_str_equal, unittest
)


class SimpleReportGenerator(BaseReportGenerator):
    """
    Bare-bones concrete implementation of a report generator.
    """

    def __init__(self, cover, diff):
        super(SimpleReportGenerator, self).__init__(cover, diff)

    def generate_report(self, output_file):
        pass


class BaseReportGeneratorTest(unittest.TestCase):
    """
    Base class for constructing test cases of report generators.
    """

    # Test data, returned by default from the mocks
    SRC_PATHS = set(['file1.py', 'subdir/file2.py'])
    LINES = [2, 3, 4, 5, 10, 11, 12, 13, 14, 15]
    VIOLATIONS = [Violation(n, None) for n in (10, 11, 20)]
    MEASURED = [1, 2, 3, 4, 7, 10, 11, 15, 20, 30]

    XML_REPORT_NAME = ["reports/coverage.xml"]
    DIFF_REPORT_NAME = "master"

    # Subclasses override this to provide the class under test
    REPORT_GENERATOR_CLASS = None

    # Snippet returned by the mock
    SNIPPET = u"<div>Snippet with \u1235 \u8292 unicode</div>"
    SNIPPET_STYLE = '.css { color:red }'

    def setUp(self):

        # Create mocks of the dependencies
        self.coverage = mock.MagicMock(BaseViolationReporter)
        self.diff = mock.MagicMock(BaseDiffReporter)

        self.addCleanup(mock.patch.stopall)

        # Patch snippet loading to always return the same string
        self._load_snippets_html = mock.patch(
            'diff_cover.snippets.Snippet.load_snippets_html'
        ).start()

        self.set_num_snippets(0)

        # Patch snippet style
        style_defs = mock.patch(
            'diff_cover.snippets.Snippet.style_defs'
        ).start()

        style_defs.return_value = self.SNIPPET_STYLE

        # Set the names of the XML and diff reports
        self.coverage.name.return_value = self.XML_REPORT_NAME
        self.diff.name.return_value = self.DIFF_REPORT_NAME

        # Configure the mocks
        self.set_src_paths_changed([])

        self._lines_dict = dict()
        self.diff.lines_changed.side_effect = self._lines_dict.get

        self._violations_dict = dict()
        self.coverage.violations.side_effect = self._violations_dict.get

        self._measured_dict = dict()
        self.coverage.measured_lines.side_effect = self._measured_dict.get

        # Create a concrete instance of a report generator
        self.report = self.REPORT_GENERATOR_CLASS(self.coverage, self.diff)

    def set_src_paths_changed(self, src_paths):
        """
        Patch the dependency `src_paths_changed()` return value
        """
        self.diff.src_paths_changed.return_value = src_paths

    def set_lines_changed(self, src_path, lines):
        """
        Patch the dependency `lines_changed()` to return
        `lines` when called with argument `src_path`.
        """
        self._lines_dict.update({src_path: lines})

    def set_violations(self, src_path, violations):
        """
        Patch the dependency `violations()` to return
        `violations` when called with argument `src_path`.
        """
        self._violations_dict.update({src_path: violations})

    def set_measured(self, src_path, measured):
        """
        Patch the dependency `measured_lines()` return
        `measured` when called with argument `src_path`.
        """
        self._measured_dict.update({src_path: measured})

    def set_num_snippets(self, num_snippets):
        """
        Patch the depdenency `Snippet.load_snippets_html()`
        to return `num_snippets` of the fake snippet HTML.
        """
        self._load_snippets_html.return_value = \
            num_snippets * [self.SNIPPET]

    def use_default_values(self):
        """
        Configure the mocks to use default values
        provided by class constants.

        All source files are given the same line, violation,
        and measured information.
        """
        self.set_src_paths_changed(self.SRC_PATHS)

        for src in self.SRC_PATHS:
            self.set_lines_changed(src, self.LINES)
            self.set_violations(src, self.VIOLATIONS)
            self.set_measured(src, self.MEASURED)
            self.set_num_snippets(0)

    def assert_report(self, expected):
        """
        Generate a report and assert that it matches
        the string `expected`.
        """
        # Create a buffer for the output
        output = BytesIO()

        # Generate the report
        self.report.generate_report(output)

        # Get the output
        output_str = output.getvalue()
        output.close()

        # Verify that we got the expected string
        assert_long_str_equal(expected, output_str, strip=True)


class SimpleReportGeneratorTest(BaseReportGeneratorTest):

    REPORT_GENERATOR_CLASS = SimpleReportGenerator

    def setUp(self):
        super(SimpleReportGeneratorTest, self).setUp()
        self.use_default_values()

    def test_src_paths(self):
        self.assertEqual(self.report.src_paths(), self.SRC_PATHS)

    def test_coverage_name(self):
        self.assertEqual(self.report.coverage_report_name(),
                         self.XML_REPORT_NAME)

    def test_diff_name(self):
        self.assertEqual(self.report.diff_report_name(),
                         self.DIFF_REPORT_NAME)

    def test_percent_covered(self):

        # Check that we get the expected coverage percentages
        # By construction, both files have the same diff line
        # and coverage information

        # There are 6 lines that are both in the diff and measured,
        # and 4 of those are covered.
        for src_path in self.SRC_PATHS:
            self.assertAlmostEqual(
                self.report.percent_covered(src_path),
                4.0 / 6 * 100)

    def test_violation_lines(self):

        # By construction, each file has the same coverage information
        expected = [10, 11]
        for src_path in self.SRC_PATHS:
            self.assertEqual(self.report.violation_lines(src_path), expected)

    def test_src_with_no_info(self):

        self.assertNotIn('unknown.py', self.report.src_paths())
        self.assertIs(self.report.percent_covered('unknown.py'), None)
        self.assertEqual(self.report.violation_lines('unknown.py'), [])

    def test_src_paths_not_measured(self):

        # Configure one of the source files to have no coverage info
        self.set_measured('file1.py', [])
        self.set_violations('file1.py', [])

        # Expect that we treat the file like it doesn't exist
        self.assertNotIn('file1.py', self.report.src_paths())
        self.assertIs(self.report.percent_covered('file1.py'), None)
        self.assertEqual(self.report.violation_lines('file1.py'), [])

    def test_total_num_lines(self):

        # By construction, each source file has the same coverage info
        num_lines_in_file = len(set(self.MEASURED).intersection(self.LINES))
        expected = len(self.SRC_PATHS) * num_lines_in_file
        self.assertEqual(self.report.total_num_lines(), expected)

    def test_total_num_missing(self):

        # By construction, each source file has the same coverage info,
        # in which 3 lines are uncovered, 2 of which are changed
        expected = len(self.SRC_PATHS) * 2
        self.assertEqual(self.report.total_num_violations(), expected)

    def test_total_percent_covered(self):

        # Since each file has the same coverage info,
        # the total percent covered is the same as each file
        # individually.
        self.assertEqual(self.report.total_percent_covered(), 66)


class TemplateReportGeneratorTest(BaseReportGeneratorTest):
    REPORT_GENERATOR_CLASS = TemplateReportGenerator

    def _test_input_expected_output(self, input_with_expected_output):
        for test_input, expected_output in input_with_expected_output:
            self.assertEqual(expected_output,
                             TemplateReportGenerator.combine_adjacent_lines(test_input))

    def test_combine_adjacent_lines_no_adjacent(self):
        in_out = [([1, 3], ["1", "3"]),
                  ([1, 5, 7, 10], ["1", "5", "7", "10"])]
        self._test_input_expected_output(in_out)

    def test_combine_adjacent_lines(self):
        in_out = [([1, 2, 3, 4, 5, 8, 10, 12, 13, 14, 15], ["1-5", "8", "10", "12-15"]),
                  ([1, 4, 5, 6, 10], ["1", "4-6", "10"]),
                  ([402, 403], ["402-403"])]
        self._test_input_expected_output(in_out)

    def test_empty_list(self):
        self.assertEqual([], TemplateReportGenerator.combine_adjacent_lines([]))

    def test_one_number(self):
        self.assertEqual(["1"], TemplateReportGenerator.combine_adjacent_lines([1]))


class StringReportGeneratorTest(BaseReportGeneratorTest):

    REPORT_GENERATOR_CLASS = StringReportGenerator

    def test_generate_report(self):

        # Generate a default report
        self.use_default_values()

        # Verify that we got the expected string
        expected = dedent("""
        -------------
        Diff Coverage
        Diff: master
        -------------
        file1.py (66.7%): Missing line(s) 10-11
        subdir/file2.py (66.7%): Missing line(s) 10-11
        -------------
        Total:   12 line(s)
        Missing: 4 line(s)
        Coverage: 66%
        -------------
        """).strip()

        self.assert_report(expected)

    def test_hundred_percent(self):

        # Have the dependencies return an empty report
        self.set_src_paths_changed(['file.py'])
        self.set_lines_changed('file.py', [line for line in range(0, 100)])
        self.set_violations('file.py', [])
        self.set_measured('file.py', [2])

        expected = dedent("""
        -------------
        Diff Coverage
        Diff: master
        -------------
        file.py (100%)
        -------------
        Total:   1 line(s)
        Missing: 0 line(s)
        Coverage: 100%
        -------------
        """).strip()

        self.assert_report(expected)

    def test_empty_report(self):

        # Have the dependencies return an empty report
        # (this is the default)

        expected = dedent("""
        -------------
        Diff Coverage
        Diff: master
        -------------
        No lines with coverage information in this diff.
        -------------
        """).strip()

        self.assert_report(expected)


class HtmlReportGeneratorTest(BaseReportGeneratorTest):

    REPORT_GENERATOR_CLASS = HtmlReportGenerator

    def test_generate_report(self):
        self.use_default_values()
        expected = load_fixture('html_report.html')
        self.assert_report(expected)

    def test_empty_report(self):

        # Have the dependencies return an empty report
        # (this is the default)

        # Verify that we got the expected string
        expected = load_fixture('html_report_empty.html')
        self.assert_report(expected)

    def test_one_snippet(self):

        self.use_default_values()

        # Have the snippet loader always report
        # provide one snippet (for every source file)
        self.set_num_snippets(1)

        # Verify that we got the expected string
        expected = load_fixture('html_report_one_snippet.html').strip()
        self.assert_report(expected)

    def test_multiple_snippets(self):

        self.use_default_values()

        # Have the snippet loader always report
        # multiple snippets for each source file
        self.set_num_snippets(2)

        # Verify that we got the expected string
        expected = load_fixture('html_report_two_snippets.html').strip()
        self.assert_report(expected)

########NEW FILE########
__FILENAME__ = test_snippets
from __future__ import unicode_literals
import os
import tempfile
from pygments.token import Token
from diff_cover.snippets import Snippet
from diff_cover.tests.helpers import load_fixture,\
    fixture_path, assert_long_str_equal, unittest
import six


class SnippetTest(unittest.TestCase):

    SRC_TOKENS = [
        (Token.Comment, u'# Test source'),
        (Token.Text, u'\n'),
        (Token.Keyword, u'def'),
        (Token.Text, u' '),
        (Token.Name.Function, u'test_func'),
        (Token.Punctuation, u'('),
        (Token.Name, u'arg'),
        (Token.Punctuation, u')'),
        (Token.Punctuation, u':'),
        (Token.Text, u'\n'),
        (Token.Text, u'    '),
        (Token.Keyword, u'print'),
        (Token.Text, u' '),
        (Token.Name, u'arg'),
        (Token.Text, u'\n'),
        (Token.Text, u'    '),
        (Token.Keyword, u'return'),
        (Token.Text, u' '),
        (Token.Name, u'arg'),
        (Token.Text, u' '),
        (Token.Operator, u'+'),
        (Token.Text, u' '),
        (Token.Literal.Number.Integer, u'5'),
        (Token.Text, u'\n'),
    ]

    FIXTURES = {
        'style': 'snippet.css',
        'default': 'snippet_default.html',
        'invalid_violations': 'snippet_invalid_violations.html',
        'no_filename_ext': 'snippet_no_filename_ext.html',
        'unicode': 'snippet_unicode.html',
    }

    def test_style_defs(self):
        style_str = Snippet.style_defs()
        expected_styles = load_fixture(self.FIXTURES['style']).strip()

        # Check that a sample of the styles are present
        # (use only a sample to make the test more robust
        # against Pygment changes).
        for expect_line in expected_styles.split('\n'):
            self.assertIn(expect_line, style_str)

    def test_format(self):
        self._assert_format(
            self.SRC_TOKENS, 'test.py',
            4, [4, 6], self.FIXTURES['default']
        )

    def test_format_with_invalid_start_line(self):
        for start_line in [-2, -1, 0]:
            with self.assertRaises(ValueError):
                Snippet('# test', 'test.py', start_line, [])

    def test_format_with_invalid_violation_lines(self):

        # Violation lines outside the range of lines in the file
        # should be ignored.
        self._assert_format(
            self.SRC_TOKENS, 'test.py',
            1, [-1, 0, 5, 6],
            self.FIXTURES['invalid_violations']
        )

    def test_no_filename_ext(self):

        # No filename extension: should default to text lexer
        self._assert_format(
            self.SRC_TOKENS, 'test',
            4, [4, 6],
            self.FIXTURES['no_filename_ext']
        )

    def test_unicode(self):

        unicode_src = [(Token.Text, u'var = \u0123 \u5872 \u3389')]

        self._assert_format(
            unicode_src, 'test.py',
            1, [], self.FIXTURES['unicode']
        )

    def _assert_format(self, src_tokens, src_filename,
                       start_line, violation_lines,
                       expected_fixture):

        snippet = Snippet(src_tokens, src_filename,
                          start_line, violation_lines)
        result = snippet.html()

        expected_str = load_fixture(expected_fixture, encoding='utf-8')

        assert_long_str_equal(expected_str, result, strip=True)
        self.assertTrue(isinstance(result, six.text_type))


class SnippetLoaderTest(unittest.TestCase):

    def setUp(self):
        """
        Create a temporary source file.
        """
        _, self._src_path = tempfile.mkstemp()

    def tearDown(self):
        """
        Delete the temporary source file.
        """
        os.remove(self._src_path)

    def test_one_snippet(self):
        self._init_src_file(10)
        violations = [2, 3, 4, 5]
        expected_ranges = [(1, 9)]
        self._assert_line_range(violations, expected_ranges)

    def test_multiple_snippets(self):
        self._init_src_file(100)
        violations = [30, 31, 32, 35, 36, 60, 62]
        expected_ranges = [(26, 40), (56, 66)]
        self._assert_line_range(violations, expected_ranges)

    def test_no_lead_line(self):
        self._init_src_file(10)
        violations = [1, 2, 3]
        expected_ranges = [(1, 7)]
        self._assert_line_range(violations, expected_ranges)

    def test_no_lag_line(self):
        self._init_src_file(10)
        violations = [9, 10]
        expected_ranges = [(5, 10)]
        self._assert_line_range(violations, expected_ranges)

    def test_one_line_file(self):
        self._init_src_file(1)
        violations = [1]
        expected_ranges = [(1, 1)]
        self._assert_line_range(violations, expected_ranges)

    def test_empty_file(self):
        self._init_src_file(0)
        violations = [0]
        expected_ranges = []
        self._assert_line_range(violations, expected_ranges)

    def test_no_violations(self):
        self._init_src_file(10)
        violations = []
        expected_ranges = []
        self._assert_line_range(violations, expected_ranges)

    def test_end_range_on_violation(self):
        self._init_src_file(40)

        # With context, the range for the snippet at 28 is 33
        # Expect that the snippet expands to include the violation
        # at the border.
        violations = [28, 33]
        expected_ranges = [(24, 37)]
        self._assert_line_range(violations, expected_ranges)

    def test_load_snippets_html(self):

        # Need to be in the fixture directory
        # so the source path is displayed correctly
        old_cwd = os.getcwd()
        self.addCleanup(lambda: os.chdir(old_cwd))
        os.chdir(fixture_path(''))

        src_path = fixture_path('snippet_src.py')
        self._init_src_file(100, src_path)

        # One higher-level test to make sure
        # the snippets are being rendered correctly
        violations = [10, 12, 13, 50, 51, 54, 55, 57]
        snippets_html = '\n\n'.join(
            Snippet.load_snippets_html('snippet_src.py', violations)
        )

        # Load the fixture for the expected contents
        expected_path = fixture_path('snippet_list.html')
        with open(expected_path) as fixture_file:
            expected = fixture_file.read()

        # Check that we got what we expected
        assert_long_str_equal(expected, snippets_html, strip=True)

    def _assert_line_range(self, violation_lines, expected_ranges):
        """
        Assert that the snippets loaded using `violation_lines`
        have the correct ranges of lines.

        `violation_lines` is a list of line numbers containing violations
        (which should get included in snippets).

        `expected_ranges` is a list of `(start, end)` tuples representing
        the starting and ending lines expected in a snippet.
        Line numbers start at 1.
        """

        # Load snippets from the source file
        snippet_list = Snippet.load_snippets(
            self._src_path, violation_lines
        )

        # Check that we got the right number of snippets
        self.assertEqual(len(snippet_list), len(expected_ranges))

        # Check that the snippets have the desired ranges
        for snippet, line_range in zip(snippet_list, expected_ranges):

            # Expect that the line range is correct
            self.assertEqual(snippet.line_range(), line_range)

            # Expect that the source contents are correct
            start, end = line_range
            self.assertEqual(snippet.text(), self._src_lines(start, end))

    def _init_src_file(self, num_src_lines, src_path=None):
        """
        Write to the temporary file "Line 1", "Line 2", etc.
        up to `num_src_lines`.
        """
        # If no source path specified, use the temp file
        if src_path is None:
            src_path = self._src_path

        with open(src_path, 'w') as src_file:
            src_file.truncate()
            src_file.write(self._src_lines(1, num_src_lines))

    def _src_lines(self, start_line, end_line):
        """
        Test lines to write to the source file
        (Line 1, Line 2, ...).
        """
        return "\n".join([
            "Line {0}".format(line_num)
            for line_num in range(start_line, end_line + 1)
        ])

########NEW FILE########
__FILENAME__ = test_violations_reporter
from __future__ import unicode_literals
from mock import Mock, patch
from subprocess import Popen
from textwrap import dedent
from six import BytesIO, StringIO
from lxml import etree
from diff_cover.violations_reporter import XmlCoverageReporter, Violation, \
    Pep8QualityReporter, PylintQualityReporter, QualityReporterError
from diff_cover.tests.helpers import unittest


class XmlCoverageReporterTest(unittest.TestCase):

    MANY_VIOLATIONS = set([Violation(3, None), Violation(7, None),
                           Violation(11, None), Violation(13, None)])
    FEW_MEASURED = set([2, 3, 5, 7, 11, 13])

    FEW_VIOLATIONS = set([Violation(3, None), Violation(11, None)])
    MANY_MEASURED = set([2, 3, 5, 7, 11, 13, 17])

    ONE_VIOLATION = set([Violation(11, None)])
    VERY_MANY_MEASURED = set([2, 3, 5, 7, 11, 13, 17, 23, 24, 25, 26, 26, 27])

    def setUp(self):
        # Paths generated by git_path are always the given argument
        self._git_path_mock = Mock()
        self._git_path_mock.relative_path = lambda path: path
        self._git_path_mock.absolute_path = lambda path: path

    def test_violations(self):

        # Construct the XML report
        file_paths = ['file1.py', 'subdir/file2.py']
        violations = self.MANY_VIOLATIONS
        measured = self.FEW_MEASURED
        xml = self._coverage_xml(file_paths, violations, measured)

        # Parse the report
        coverage = XmlCoverageReporter(xml, self._git_path_mock)

        # Expect that the name is set
        self.assertEqual(coverage.name(), "XML")

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(violations, coverage.violations('file1.py'))
        self.assertEqual(measured, coverage.measured_lines('file1.py'))

        # Try getting a smaller range
        result = coverage.violations('subdir/file2.py')
        self.assertEqual(result, violations)

        # Once more on the first file (for caching)
        result = coverage.violations('file1.py')
        self.assertEqual(result, violations)

    def test_two_inputs_first_violate(self):

        # Construct the XML report
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = self.FEW_VIOLATIONS

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)

        # Parse the report
        coverage = XmlCoverageReporter([xml, xml2], self._git_path_mock)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2,
            coverage.measured_lines('file1.py')
        )

    def test_two_inputs_second_violate(self):

        # Construct the XML report
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = self.FEW_VIOLATIONS

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)

        # Parse the report
        coverage = XmlCoverageReporter([xml2, xml], self._git_path_mock)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2,
            coverage.measured_lines('file1.py')
        )

    def test_three_inputs(self):

        # Construct the XML report
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = self.FEW_VIOLATIONS
        violations3 = self.ONE_VIOLATION

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED
        measured3 = self.VERY_MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)
        xml3 = self._coverage_xml(file_paths, violations3, measured3)

        # Parse the report
        coverage = XmlCoverageReporter([xml2, xml, xml3], self._git_path_mock)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2 & violations3,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2 | measured3,
            coverage.measured_lines('file1.py')
        )

    def test_different_files_in_inputs(self):

        # Construct the XML report
        xml_roots = [
            self._coverage_xml(['file.py'], self.MANY_VIOLATIONS, self.FEW_MEASURED),
            self._coverage_xml(['other_file.py'], self.FEW_VIOLATIONS, self.MANY_MEASURED)
        ]

        # Parse the report
        coverage = XmlCoverageReporter(xml_roots, self._git_path_mock)

        self.assertEqual(self.MANY_VIOLATIONS, coverage.violations('file.py'))
        self.assertEqual(self.FEW_VIOLATIONS, coverage.violations('other_file.py'))

    def test_empty_violations(self):
        """
        Test that an empty violations report is handled properly
        """

        # Construct the XML report
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = set()

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)

        # Parse the report
        coverage = XmlCoverageReporter([xml2, xml], self._git_path_mock)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2,
            coverage.measured_lines('file1.py')
        )

    def test_no_such_file(self):

        # Construct the XML report with no source files
        xml = self._coverage_xml([], [], [])

        # Parse the report
        coverage = XmlCoverageReporter(xml, self._git_path_mock)

        # Expect that we get no results
        result = coverage.violations('file.py')
        self.assertEqual(result, set([]))

    def _coverage_xml(self, file_paths, violations, measured):
        """
        Build an XML tree with source files specified by `file_paths`.
        Each source fill will have the same set of covered and
        uncovered lines.

        `file_paths` is a list of path strings
        `line_dict` is a dictionary with keys that are line numbers
        and values that are True/False indicating whether the line
        is covered

        This leaves out some attributes of the Cobertura format,
        but includes all the elements.
        """
        root = etree.Element('coverage')
        packages = etree.SubElement(root, 'packages')
        classes = etree.SubElement(packages, 'classes')

        violation_lines = set(violation.line for violation in violations)

        for path in file_paths:

            src_node = etree.SubElement(classes, 'class')
            src_node.set('filename', path)

            etree.SubElement(src_node, 'methods')
            lines_node = etree.SubElement(src_node, 'lines')

            # Create a node for each line in measured
            for line_num in measured:
                is_covered = line_num not in violation_lines
                line = etree.SubElement(lines_node, 'line')

                hits = 1 if is_covered else 0
                line.set('hits', str(hits))
                line.set('number', str(line_num))

        return root


class Pep8QualityReporterTest(unittest.TestCase):

    def tearDown(self):
        """
        Undo all patches
        """
        patch.stopall()

    def test_quality(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        return_string = '\n' + dedent("""
                ../new_file.py:1:17: E231 whitespace
                ../new_file.py:3:13: E225 whitespace
                ../new_file.py:7:1: E302 blank lines
            """).strip() + '\n'
        _mock_communicate.return_value = (
            (return_string.encode('utf-8'), b''))

        # Parse the report
        quality = Pep8QualityReporter('pep8', [])

        # Expect that the name is set
        self.assertEqual(quality.name(), 'pep8')

        # Measured_lines is undefined for
        # a quality reporter since all lines are measured
        self.assertEqual(quality.measured_lines('../new_file.py'), None)

        # Expect that we get the right violations
        expected_violations = [
            Violation(1, 'E231 whitespace'),
            Violation(3, 'E225 whitespace'),
            Violation(7, 'E302 blank lines')
        ]

        self.assertEqual(expected_violations, quality.violations('../new_file.py'))

    def test_no_quality_issues_newline(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (b'\n', b'')

        # Parse the report
        quality = Pep8QualityReporter('pep8', [])
        self.assertEqual([], quality.violations('file1.py'))

    def test_no_quality_issues_emptystring(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (b'', b'')

        # Parse the report
        quality = Pep8QualityReporter('pep8', [])
        self.assertEqual([], quality.violations('file1.py'))

    def test_quality_error(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (b"", b'whoops')

        # Parse the report
        quality = Pep8QualityReporter('pep8', [])

        # Expect that the name is set
        self.assertEqual(quality.name(), 'pep8')

        self.assertRaises(QualityReporterError, quality.violations, 'file1.py')

    def test_no_such_file(self):
        quality = Pep8QualityReporter('pep8', [])

        # Expect that we get no results
        result = quality.violations('')
        self.assertEqual(result, [])

    def test_no_python_file(self):
        quality = Pep8QualityReporter('pep8', [])
        file_paths = ['file1.coffee', 'subdir/file2.js']
        # Expect that we get no results because no Python files
        for path in file_paths:
            result = quality.violations(path)
            self.assertEqual(result, [])

    def test_quality_pregenerated_report(self):

        # When the user provides us with a pre-generated pep8 report
        # then use that instead of calling pep8 directly.
        pep8_reports = [
            BytesIO(('\n' + dedent("""
                path/to/file.py:1:17: E231 whitespace
                path/to/file.py:3:13: E225 whitespace
                another/file.py:7:1: E302 blank lines
            """).strip() + '\n').encode('utf-8')),

            BytesIO(('\n' + dedent(u"""
                path/to/file.py:24:2: W123 \u9134\u1912
                another/file.py:50:1: E302 blank lines
            """).strip() + '\n').encode('utf-8')),
        ]

        # Parse the report
        quality = Pep8QualityReporter('pep8', pep8_reports)

        # Measured_lines is undefined for
        # a quality reporter since all lines are measured
        self.assertEqual(quality.measured_lines('path/to/file.py'), None)

        # Expect that we get the right violations
        expected_violations = [
            Violation(1, u'E231 whitespace'),
            Violation(3, u'E225 whitespace'),
            Violation(24, u'W123 \u9134\u1912')
        ]

        # We're not guaranteed that the violations are returned
        # in any particular order.
        actual_violations = quality.violations('path/to/file.py')

        self.assertEqual(len(actual_violations), len(expected_violations))
        for expected in expected_violations:
            self.assertIn(expected, actual_violations)


class PylintQualityReporterTest(unittest.TestCase):

    def tearDown(self):
        """
        Undo all patches.
        """
        patch.stopall()

    def test_no_such_file(self):
        quality = PylintQualityReporter('pylint', [])

        # Expect that we get no results
        result = quality.violations('')
        self.assertEqual(result, [])

    def test_no_python_file(self):
        quality = PylintQualityReporter('pylint', [])
        file_paths = ['file1.coffee', 'subdir/file2.js']
        # Expect that we get no results because no Python files
        for path in file_paths:
            result = quality.violations(path)
            self.assertEqual(result, [])

    def test_quality(self):
        # Patch the output of `pylint`
        _mock_communicate = patch.object(Popen, 'communicate').start()

        _mock_communicate.return_value = (
            dedent("""
            file1.py:1: [C0111] Missing docstring
            file1.py:1: [C0111, func_1] Missing docstring
            file1.py:2: [W0612, cls_name.func] Unused variable 'd'
            file1.py:2: [W0511] TODO: Not the real way we'll store usages!
            file1.py:579: [F0401] Unable to import 'rooted_paths'
            file1.py:113: [W0613, cache_relation.clear_pk] Unused argument 'cls'
            file1.py:150: [F0010] error while code parsing ([Errno 2] No such file or directory)
            file1.py:149: [C0324, Foo.__dict__] Comma not followed by a space
                self.peer_grading._find_corresponding_module_for_location(Location('i4x','a','b','c','d'))
            file1.py:162: [R0801] Similar lines in 2 files
            ==external_auth.views:1
            ==student.views:4
            import json
            import logging
            import random
            path/to/file2.py:100: [W0212, openid_login_complete] Access to a protected member
            """).strip().encode('ascii'), ''
        )

        expected_violations = [
            Violation(1, 'C0111: Missing docstring'),
            Violation(1, 'C0111: func_1: Missing docstring'),
            Violation(2, "W0612: cls_name.func: Unused variable 'd'"),
            Violation(2, "W0511: TODO: Not the real way we'll store usages!"),
            Violation(579, "F0401: Unable to import 'rooted_paths'"),
            Violation(150, "F0010: error while code parsing ([Errno 2] No such file or directory)"),
            Violation(149, "C0324: Foo.__dict__: Comma not followed by a space"),
            Violation(162, "R0801: Similar lines in 2 files"),
            Violation(113, "W0613: cache_relation.clear_pk: Unused argument 'cls'")
        ]

        # Parse the report
        quality = PylintQualityReporter('pylint', [])

        # Expect that the name is set
        self.assertEqual(quality.name(), 'pylint')

        # Measured_lines is undefined for a
        # quality reporter since all lines are measured
        self.assertEqual(quality.measured_lines('file1.py'), None)

        # Expect that we get violations for file1.py only
        # We're not guaranteed that the violations are returned
        # in any particular order.
        actual_violations = quality.violations('file1.py')
        self.assertEqual(len(actual_violations), len(expected_violations))
        for expected in expected_violations:
            self.assertIn(expected, actual_violations)

    def test_unicode(self):
        _mock_communicate = patch.object(Popen, 'communicate').start()

        # Test non-ascii unicode characters in the filename, function name and message
        _mock_communicate.return_value = (dedent(u"""
            file_\u6729.py:616: [W1401] Anomalous backslash in string: '\u5922'. String constant might be missing an r prefix.
            file.py:2: [W0612, cls_name.func_\u9492] Unused variable '\u2920'
        """).encode('utf-8'), b'')

        quality = PylintQualityReporter('pylint', [])
        violations = quality.violations(u'file_\u6729.py')
        self.assertEqual(violations, [
            Violation(616, u"W1401: Anomalous backslash in string: '\u5922'. String constant might be missing an r prefix."),
        ])

        violations = quality.violations(u'file.py')
        self.assertEqual(violations, [Violation(2, u"W0612: cls_name.func_\u9492: Unused variable '\u2920'")])

    def test_unicode_continuation_char(self):
        _mock_communicate = patch.object(Popen, 'communicate').start()

        # Test a unicode continuation char, which pylint can produce (probably an encoding bug in pylint)
        _mock_communicate.return_value = (b"file.py:2: [W1401]"
                                          b" Invalid char '\xc3'", '')

        # Since we are replacing characters we can't interpet, this should
        # return a valid string with the char replaced with '?'
        quality = PylintQualityReporter('pylint', [])
        violations = quality.violations(u'file.py')
        self.assertEqual(violations, [Violation(2, u"W1401: Invalid char '\ufffd'")])

    def test_non_integer_line_num(self):
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (dedent(u"""
            file.py:not_a_number: C0111: Missing docstring
            file.py:\u8911: C0111: Missing docstring
        """).encode('utf-8'), '')

        # None of the violations have a valid line number, so they should all be skipped
        violations = PylintQualityReporter('pylint', []).violations(u'file.py')
        self.assertEqual(violations, [])

    def test_quality_error(self):

        # Patch the output of `pylint`
        # to output to stderr
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (b"", b'whoops')

        # Parse the report
        quality = PylintQualityReporter('pylint', [])

        # Expect an error
        self.assertRaises(QualityReporterError, quality.violations, 'file1.py')

    def test_legacy_pylint_compatibility(self):
        quality = PylintQualityReporter('pylint', [])
        _mock_communicate = patch.object(Popen, 'communicate').start()
        expected_options = [quality.MODERN_OPTIONS, quality.LEGACY_OPTIONS]

        def side_effect():
            """
            Assure that the first time we use the modern options, return a failure
            Then assert the legacy options were set, return ok
            """
            index = _mock_communicate.call_count-1
            self.assertEqual(quality.OPTIONS, expected_options[index])

            return [(b"", dedent("""
            No config file found, using default configuration
            Usage:  pylint [options] module_or_package

              Check that a module satisfies a coding standard (and more !).

                pylint --help

              Display this help message and exit.

                pylint --help-msg <msg-id>[,<msg-id>]

              Display help messages about given message identifiers and exit.


            pylint: error: no such option: --msg-template
        """).encode('utf-8')), (b'\n', b'')][index]

        _mock_communicate.side_effect = side_effect
        quality.violations('file1.py')
        self.assertEqual([], quality.violations('file1.py'))
        self.assertEqual(quality.OPTIONS, quality.LEGACY_OPTIONS)
        self.assertEqual(_mock_communicate.call_count, 2)

    def test_no_quality_issues_newline(self):

        # Patch the output of `pylint`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (b'\n', b'')

        # Parse the report
        quality = PylintQualityReporter('pylint', [])
        self.assertEqual([], quality.violations('file1.py'))

    def test_no_quality_issues_emptystring(self):

        # Patch the output of `pylint`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (b'', b'')

        # Parse the report
        quality = PylintQualityReporter('pylint', [])
        self.assertEqual([], quality.violations('file1.py'))

    def test_quality_pregenerated_report(self):

        # When the user provides us with a pre-generated pylint report
        # then use that instead of calling pylint directly.
        pylint_reports = [
            BytesIO(dedent(u"""
                path/to/file.py:1: [C0111] Missing docstring
                path/to/file.py:57: [W0511] TODO the name of this method is a little bit confusing
                another/file.py:41: [W1201, assign_default_role] Specify string format arguments as logging function parameters
                another/file.py:175: [C0322, Foo.bar] Operator not preceded by a space
                        x=2+3
                          ^
                        Unicode: \u9404 \u1239
                another/file.py:259: [C0103, bar] Invalid name "\u4920" for type variable (should match [a-z_][a-z0-9_]{2,30}$)
            """).strip().encode('utf-8')),

            BytesIO(dedent(u"""
            path/to/file.py:183: [C0103, Foo.bar.gettag] Invalid name "\u3240" for type argument (should match [a-z_][a-z0-9_]{2,30}$)
            another/file.py:183: [C0111, Foo.bar.gettag] Missing docstring
            """).strip().encode('utf-8'))
        ]

        # Generate the violation report
        quality = PylintQualityReporter('pylint', pylint_reports)

        # Expect that we get the right violations
        expected_violations = [
            Violation(1, u'C0111: Missing docstring'),
            Violation(57, u'W0511: TODO the name of this method is a little bit confusing'),
            Violation(183, u'C0103: Foo.bar.gettag: Invalid name "\u3240" for type argument (should match [a-z_][a-z0-9_]{2,30}$)')
        ]

        # We're not guaranteed that the violations are returned
        # in any particular order.
        actual_violations = quality.violations('path/to/file.py')
        self.assertEqual(len(actual_violations), len(expected_violations))
        for expected in expected_violations:
            self.assertIn(expected, actual_violations)

    def test_quality_pregenerated_report_continuation_char(self):

        # The report contains a non-ASCII continuation char
        pylint_reports = [BytesIO(b"file.py:2: [W1401] Invalid char '\xc3'")]

        # Generate the violation report
        quality = PylintQualityReporter('pylint', pylint_reports)
        violations = quality.violations('file.py')

        # Expect that the char is replaced
        self.assertEqual(violations, [Violation(2, u"W1401: Invalid char '\ufffd'")])


class SubprocessErrorTestCase(unittest.TestCase):
    def setUp(self):
        # when you create a new subprocess.Popen() object and call .communicate()
        # on it, raise an OSError
        _mock_Popen = Mock()
        _mock_Popen.return_value.communicate.side_effect = OSError
        patcher = patch("diff_cover.violations_reporter.subprocess.Popen", _mock_Popen)
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch('sys.stderr', new_callable=StringIO)
    def test_quality_reporter(self, mock_stderr):
        reporter = Pep8QualityReporter('pep8', [])
        with self.assertRaises(OSError):
            reporter.violations("path/to/file.py")

        self.assertEqual(mock_stderr.getvalue(), "pep8 path/to/file.py")

########NEW FILE########
__FILENAME__ = tool
"""
Implement the command-line tool interface.
"""
from __future__ import unicode_literals
import argparse
import os
import sys
import diff_cover
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool
from diff_cover.git_path import GitPathTool
from diff_cover.violations_reporter import (
    XmlCoverageReporter, Pep8QualityReporter, PylintQualityReporter
)
from diff_cover.report_generator import (
    HtmlReportGenerator, StringReportGenerator,
    HtmlQualityReportGenerator, StringQualityReportGenerator
)
from lxml import etree

COVERAGE_XML_HELP = "XML coverage report"
HTML_REPORT_HELP = "Diff coverage HTML output"
COMPARE_BRANCH_HELP = "Branch to compare"
VIOLATION_CMD_HELP = "Which code quality tool to use"
INPUT_REPORTS_HELP = "Pep8 or pylint reports to use"
OPTIONS_HELP = "Options to be passed to the violations tool"

QUALITY_REPORTERS = {
    'pep8': Pep8QualityReporter,
    'pylint': PylintQualityReporter
}


import logging
LOGGER = logging.getLogger(__name__)


def parse_coverage_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'coverage_xml': COVERAGE_XML,
            'html_report': None | HTML_REPORT
        }

    where `COVERAGE_XML` is a path, and `HTML_REPORT` is a path.

    The path strings may or may not exist.
    """
    parser = argparse.ArgumentParser(description=diff_cover.DESCRIPTION)

    parser.add_argument(
        'coverage_xml',
        type=str,
        help=COVERAGE_XML_HELP,
        nargs='+'
    )

    parser.add_argument(
        '--html-report',
        type=str,
        default=None,
        help=HTML_REPORT_HELP
    )

    parser.add_argument(
        '--compare-branch',
        type=str,
        default='origin/master',
        help=COMPARE_BRANCH_HELP
    )

    return vars(parser.parse_args(argv))


def parse_quality_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'violations': pep8 | pylint
            'html_report': None | HTML_REPORT
        }

    where `HTML_REPORT` is a path.
    """
    parser = argparse.ArgumentParser(
        description=diff_cover.QUALITY_DESCRIPTION
    )

    parser.add_argument(
        '--violations',
        type=str,
        help=VIOLATION_CMD_HELP,
        required=True
    )

    parser.add_argument(
        '--html-report',
        type=str,
        default=None,
        help=HTML_REPORT_HELP
    )

    parser.add_argument(
        '--compare-branch',
        type=str,
        default='origin/master',
        help=COMPARE_BRANCH_HELP
    )

    parser.add_argument(
        'input_reports',
        type=str,
        nargs="*",
        default=[],
        help=INPUT_REPORTS_HELP
    )

    parser.add_argument(
        '--options',
        type=str,
        nargs='?',
        default=None,
        help=OPTIONS_HELP
    )

    return vars(parser.parse_args(argv))


def generate_coverage_report(coverage_xml, compare_branch, html_report=None):
    """
    Generate the diff coverage report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(compare_branch, git_diff=GitDiffTool())

    xml_roots = [etree.parse(xml_root) for xml_root in coverage_xml]
    git_path = GitPathTool(os.getcwd())
    coverage = XmlCoverageReporter(xml_roots, git_path)

    # Build a report generator
    if html_report is not None:
        reporter = HtmlReportGenerator(coverage, diff)
        output_file = open(html_report, "wb")
    else:
        reporter = StringReportGenerator(coverage, diff)
        output_file = sys.stdout

    # Generate the report
    reporter.generate_report(output_file)


def generate_quality_report(tool, compare_branch, html_report=None):
    """
    Generate the quality report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(compare_branch, git_diff=GitDiffTool())

    if html_report is not None:
        reporter = HtmlQualityReportGenerator(tool, diff)
        output_file = open(html_report, "wb")
    else:
        reporter = StringQualityReportGenerator(tool, diff)
        output_file = sys.stdout

    reporter.generate_report(output_file)


def main():
    """
    Main entry point for the tool, used by setup.py
    """
    progname = sys.argv[0]

    if progname.endswith('diff-cover'):
        arg_dict = parse_coverage_args(sys.argv[1:])
        generate_coverage_report(
            arg_dict['coverage_xml'],
            arg_dict['compare_branch'],
            html_report=arg_dict['html_report'],
        )

    elif progname.endswith('diff-quality'):
        arg_dict = parse_quality_args(sys.argv[1:])
        tool = arg_dict['violations']
        user_options = arg_dict.get('options')
        if user_options:
            user_options = user_options[1:-1]  # Strip quotes
        reporter_class = QUALITY_REPORTERS.get(tool)

        if reporter_class is not None:
            # If we've been given pre-generated reports,
            # try to open the files
            input_reports = []

            for path in arg_dict['input_reports']:
                try:
                    input_reports.append(open(path, 'rb'))
                except IOError:
                    LOGGER.warning("Could not load '{0}'".format(path))

            try:
                reporter = reporter_class(tool, input_reports, user_options=user_options)
                generate_quality_report(
                    reporter,
                    arg_dict['compare_branch'],
                    arg_dict['html_report']
                )

            # Close any reports we opened
            finally:
                for file_handle in input_reports:
                    file_handle.close()
        else:
            LOGGER.error("Quality tool not recognized: '{0}'".format(tool))
            exit(1)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = violations_reporter
"""
Classes for querying the information in a test coverage report.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from collections import namedtuple, defaultdict
import re
import subprocess
import sys
import six


Violation = namedtuple('Violation', 'line, message')


class BaseViolationReporter(object):
    """
    Query information from a coverage report.
    """

    __metaclass__ = ABCMeta

    def __init__(self, name):
        """
        Provide a name for the coverage report, which will be included
        in the generated diff report.
        """
        self._name = name

    @abstractmethod
    def violations(self, src_path):
        """
        Return a list of Violations recorded in `src_path`.
        """
        pass

    def measured_lines(self, src_path):
        """
        Return a list of the lines in src_path that were measured
        by this reporter.

        Some reporters will always consider all lines in the file "measured".
        As an optimization, such violation reporters
        can return `None` to indicate that all lines are measured.
        The diff reporter generator will then use all changed lines
        provided by the diff.
        """
        return None

    def name(self):
        """
        Retrieve the name of the report, which may be
        included in the generated diff coverage report.

        For example, `name()` could return the path to the coverage
        report file or the type of reporter.
        """
        return self._name


class XmlCoverageReporter(BaseViolationReporter):
    """
    Query information from a Cobertura XML coverage report.
    """

    def __init__(self, xml_roots, git_path):
        """
        Load the Cobertura XML coverage report represented
        by the lxml.etree with root element `xml_root`.
        """
        super(XmlCoverageReporter, self).__init__("XML")
        self._xml_roots = xml_roots

        # Create a dict to cache violations dict results
        # Keys are source file paths, values are output of `violations()`
        self._info_cache = defaultdict(list)
        self._git_path = git_path

    def _get_src_path_line_nodes(self, xml_document, src_path):
        """
        Returns a list of nodes containing line information for `src_path`
        in `xml_document`.

        If file is not present in `xml_document`, return None
        """

        # Remove git_root from src_path for searching the correct filename
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `diff_cover/violations_reporter.py`
        # search for `violations_reporter.py`
        src_rel_path = self._git_path.relative_path(src_path)

        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `other_package/some_file.py`
        # search for `/home/user/work/diff-cover/other_package/some_file.py`
        src_abs_path = self._git_path.absolute_path(src_path)

        xpath_template = ".//class[@filename='{0}']/lines/line"
        xpath = None

        src_node_xpath = ".//class[@filename='{0}']".format(src_rel_path)
        if xml_document.find(src_node_xpath) is not None:
            xpath = xpath_template.format(src_rel_path)

        src_node_xpath = ".//class[@filename='{0}']".format(src_abs_path)
        if xml_document.find(src_node_xpath) is not None:
            xpath = xpath_template.format(src_abs_path)

        if xpath is None:
            return None

        return xml_document.findall(xpath)

    def _cache_file(self, src_path):
        """
        Load the data from `self._xml_roots`
        for `src_path`, if it hasn't been already.
        """
        # If we have not yet loaded this source file
        if src_path not in self._info_cache:
            # We only want to keep violations that show up in each xml source.
            # Thus, each time, we take the intersection.  However, to do this
            # we must treat the first time as a special case and just add all
            # the violations from the first xml report.
            violations = None

            # A line is measured if it is measured in any of the reports, so
            # we take set union each time and can just start with the empty set
            measured = set()

            # Loop through the files that contain the xml roots
            for xml_document in self._xml_roots:
                line_nodes = self._get_src_path_line_nodes(xml_document,
                                                           src_path)

                if line_nodes is None:
                    continue

                # First case, need to define violations initially
                if violations is None:
                    violations = set(
                        Violation(int(line.get('number')), None)
                        for line in line_nodes
                        if int(line.get('hits', 0)) == 0)

                # If we already have a violations set,
                # take the intersection of the new
                # violations set and its old self
                else:
                    violations = violations & set(
                        Violation(int(line.get('number')), None)
                        for line in line_nodes
                        if int(line.get('hits', 0)) == 0
                    )

                # Measured is the union of itself and the new measured
                measured = measured | set(
                    int(line.get('number')) for line in line_nodes
                )

            # If we don't have any information about the source file,
            # don't report any violations
            if violations is None:
                violations = set()

            self._info_cache[src_path] = (violations, measured)

    def violations(self, src_path):
        """
        See base class comments.
        """

        self._cache_file(src_path)

        # Yield all lines not covered
        return self._info_cache[src_path][0]

    def measured_lines(self, src_path):
        """
        See base class docstring.
        """
        self._cache_file(src_path)
        return self._info_cache[src_path][1]


class BaseQualityReporter(BaseViolationReporter):
    """
    Abstract class to report code quality
    information, using `COMMAND`
    (provided by subclasses).
    """
    COMMAND = ''
    OPTIONS = []

    # Encoding of the stdout from the command
    # This is application-dependent
    STDOUT_ENCODING = 'utf-8'

    # A list of filetypes to run on.
    EXTENSIONS = []

    def __init__(self, name, input_reports, user_options=None):
        """
        Create a new quality reporter.

        `name` is an identifier for the reporter
        (usually the name of the tool used to generate
        the report).

        `input_reports` is an list of
        file-like objects representing pre-generated
        violation reports.  The list can be empty.

        If these are provided, the reporter will
        use the pre-generated reports instead of invoking
        the tool directly.

        'user_options' is a string of options passed in.
        This string contains options that are passed forward
        to the reporter being used
        """
        super(BaseQualityReporter, self).__init__(name)
        self._info_cache = defaultdict(list)
        self.user_options = user_options

        # If we've been given input report files, use those
        # to get the source information
        if len(input_reports) > 0:
            self.use_tool = False
            self._load_reports(input_reports)
        else:
            self.use_tool = True

    def violations(self, src_path):
        """
        See base class comments.
        """
        # If we've been given pre-generated pylint/pep8 reports,
        # then we've already loaded everything we need into the cache.
        # Otherwise, call pylint/pep8 ourselves
        if self.use_tool:
            if not any(src_path.endswith(ext) for ext in self.EXTENSIONS):
                return []
            if src_path not in self._info_cache:
                output = self._run_command(src_path)
                violations_dict = self._parse_output(output, src_path)
                self._update_cache(violations_dict)

        # Return the cached violation info
        return self._info_cache[src_path]

    def _load_reports(self, report_files):
        """
        Load pre-generated pep8/pylint reports into
        the cache.

        `report_files` is a list of open file-like objects.
        """
        for file_handle in report_files:
            # Convert to unicode, replacing unreadable chars
            contents = file_handle.read().decode(self.STDOUT_ENCODING,
                                                 'replace')
            violations_dict = self._parse_output(contents)
            self._update_cache(violations_dict)

    def _update_cache(self, violations_dict):
        """
        Append violations in `violations_dict` to the cache.
        `violations_dict` must have the form:

            {
                SRC_PATH: [Violation, ]
            }
        """
        for src_path, violations in six.iteritems(violations_dict):
            self._info_cache[src_path].extend(violations)

    def _run_command(self, src_path):
        """
        Run the quality command and return its output as a unicode string.
        """
        # Encode the path using the filesystem encoding, determined at runtime
        encoding = sys.getfilesystemencoding()
        user_options = [self.user_options] if self.user_options is not None else []
        command = [self.COMMAND] + self.OPTIONS + user_options + [src_path.encode(encoding)]

        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
        except OSError:
            sys.stderr.write(" ".join([cmd.decode(encoding)
                                       if isinstance(cmd, bytes) else cmd
                                       for cmd in command]))
            raise

        if stderr:
            raise QualityReporterError(stderr.decode(encoding))

        return stdout.strip().decode(self.STDOUT_ENCODING, 'replace')

    @abstractmethod
    def _parse_output(self, output, src_path=None):
        """
        Parse the output of this reporter
        command into a dict of the form:

            {
                SRC_PATH: [Violation, ]
            }

        where `SRC_PATH` is the path to the source file
        containing the violations, and the value is
        a list of violations.

        If `src_path` is provided, return information
        just for that source.
        """
        pass


class Pep8QualityReporter(BaseQualityReporter):
    """
    Report PEP8 violations.
    """
    COMMAND = 'pep8'

    EXTENSIONS = ['py']
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+).*([EW]\d{3}.*)$')

    def _parse_output(self, output, src_path=None):
        """
        See base class docstring.
        """
        violations_dict = defaultdict(list)

        for line in output.split('\n'):

            match = self.VIOLATION_REGEX.match(line)

            # Ignore any line that isn't a violation
            if match is not None:
                pep8_src, line_number, message = match.groups()

                # If we're looking for a particular source,
                # filter out all other sources
                if src_path is None or src_path == pep8_src:
                    violation = Violation(int(line_number), message)
                    violations_dict[pep8_src].append(violation)

        return violations_dict


class PylintQualityReporter(BaseQualityReporter):
    """
    Report Pylint violations.
    """
    COMMAND = 'pylint'
    MODERN_OPTIONS = ['--msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"']
    LEGACY_OPTIONS = ['-f', 'parseable', '--reports=no', '--include-ids=y']
    OPTIONS = MODERN_OPTIONS
    EXTENSIONS = ['py']

    # Match lines of the form:
    # path/to/file.py:123: [C0111] Missing docstring
    # path/to/file.py:456: [C0111, Foo.bar] Missing docstring
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+): \[(\w+),? ?([^\]]*)] (.*)$')

    def _run_command(self, src_path):
        try:
            return super(PylintQualityReporter, self)._run_command(src_path)
        except QualityReporterError as report_error:
            # Support earlier pylint version (< 1)
            if "no such option: --msg-template" in report_error.message:
                self.OPTIONS = self.LEGACY_OPTIONS
                return super(PylintQualityReporter, self)._run_command(src_path)
            else:
                raise

    def _parse_output(self, output, src_path=None):
        """
        See base class docstring.
        """
        violations_dict = defaultdict(list)

        for line in output.split('\n'):
            match = self.VIOLATION_REGEX.match(line)

            # Ignore any line that isn't matched
            # (for example, snippets from the source code)
            if match is not None:

                pylint_src_path, line_number, pylint_code, function_name, message = match.groups()

                # If we're looking for a particular source file,
                # ignore any other source files.
                if src_path is None or src_path == pylint_src_path:

                    if function_name:
                        error_str = u"{0}: {1}: {2}".format(pylint_code, function_name, message)
                    else:
                        error_str = u"{0}: {1}".format(pylint_code, message)

                    violation = Violation(int(line_number), error_str)
                    violations_dict[pylint_src_path].append(violation)

        return violations_dict


class QualityReporterError(Exception):
    """
    A quality reporter command produced an error.
    """
    def __init__(self, message):
        self.message = message

########NEW FILE########
