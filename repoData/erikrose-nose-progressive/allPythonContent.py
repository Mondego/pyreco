__FILENAME__ = bar
from __future__ import with_statement
from itertools import cycle
from signal import signal, SIGWINCH


__all__ = ['ProgressBar', 'NullProgressBar']


class ProgressBar(object):
    _is_dodging = 0  # Like a semaphore

    def __init__(self, max_value, term, filled_color=8, empty_color=7):
        """``max_value`` is the highest value I will attain. Must be >0."""
        self.stream = term.stream
        self.max = max_value
        self._term = term
        self.last = ''  # The contents of the previous progress line printed
        self._measure_terminal()

        # Prepare formatting, dependent on whether we have terminal colors:
        if term.number_of_colors > max(filled_color, empty_color):
            self._fill_cap = term.on_color(filled_color)
            self._empty_cap = term.on_color(empty_color)
            self._empty_char = ' '
        else:
            self._fill_cap = term.reverse
            self._empty_cap = lambda s: s
            self._empty_char = '_'

        signal(SIGWINCH, self._handle_winch)

    def _measure_terminal(self):
        self.lines, self.cols = (self._term.height or 24,
                                 self._term.width or 80)

    def _handle_winch(self, *args):
        #self.erase()  # Doesn't seem to help.
        self._measure_terminal()
        # TODO: Reprint the bar but at the new width.

    def update(self, test_path, number):
        """Draw an updated progress bar.

        At the moment, the graph takes a fixed width, and the test identifier
        takes the rest of the row, truncated from the left to fit.

        test_path -- the selector of the test being run
        number -- how many tests have been run so far, including this one

        """
        # TODO: Play nicely with absurdly narrow terminals. (OS X's won't even
        # go small enough to hurt us.)

        # Figure out graph:
        GRAPH_WIDTH = 14
        # min() is in case we somehow get the total test count wrong. It's tricky.
        num_filled = int(round(min(1.0, float(number) / self.max) * GRAPH_WIDTH))
        graph = ''.join([self._fill_cap(' ' * num_filled),
                         self._empty_cap(self._empty_char * (GRAPH_WIDTH - num_filled))])

        # Figure out the test identifier portion:
        cols_for_path = self.cols - GRAPH_WIDTH - 2  # 2 spaces between path & graph
        if len(test_path) > cols_for_path:
            test_path = test_path[len(test_path) - cols_for_path:]
        else:
            test_path += ' ' * (cols_for_path - len(test_path))

        # Put them together, and let simmer:
        self.last = self._term.bold(test_path) + '  ' + graph
        with self._at_last_line():
            self.stream.write(self.last)
        self.stream.flush()

    def erase(self):
        """White out the progress bar."""
        with self._at_last_line():
            self.stream.write(self._term.clear_eol)
        self.stream.flush()

    def _at_last_line(self):
        """Return a context manager that positions the cursor at the last line, lets you write things, and then returns it to its previous position."""
        return self._term.location(0, self.lines)

    def dodging(bar):
        """Return a context manager which erases the bar, lets you output things, and then redraws the bar.

        It's reentrant.

        """
        class ShyProgressBar(object):
            """Context manager that implements a progress bar that gets out of the way"""

            def __enter__(self):
                """Erase the progress bar so bits of disembodied progress bar don't get scrolled up the terminal."""
                # My terminal has no status line, so we make one manually.
                bar._is_dodging += 1  # Increment before calling erase(), which
                                      # calls dodging() again.
                if bar._is_dodging <= 1:  # It *was* 0.
                    bar.erase()

            def __exit__(self, type, value, tb):
                """Redraw the last saved state of the progress bar."""
                if bar._is_dodging == 1:  # Can't decrement yet; write() could
                                          # read it.
                    # This is really necessary only because we monkeypatch
                    # stderr; the next test is about to start and will redraw
                    # the bar.
                    with bar._at_last_line():
                        bar.stream.write(bar.last)
                    bar.stream.flush()
                bar._is_dodging -= 1

        return ShyProgressBar()


class Null(object):
    def __getattr__(self, *args, **kwargs):
        """Return a boring callable for any attribute accessed."""
        return lambda *args, **kwargs: None

    # Beginning in Python 2.7, __enter__ and __exit__ aren't looked up through
    # __getattr__ or __getattribute__:
    # http://docs.python.org/reference/datamodel#specialnames
    __enter__ = __exit__ = __getattr__


class NullProgressBar(Null):
    """``ProgressBar`` workalike that does nothing

    Comes in handy when you want to have an option to hide the progress bar.

    """
    def dodging(self):
        return Null()  # So Python can call __enter__ and __exit__ on it

########NEW FILE########
__FILENAME__ = plugin
from functools import partial
from os import getcwd
import pdb
import sys
from warnings import warn

from nose.plugins import Plugin

from noseprogressive.runner import ProgressiveRunner
from noseprogressive.tracebacks import DEFAULT_EDITOR_SHORTCUT_TEMPLATE
from noseprogressive.wrapping import cmdloop, set_trace, StreamWrapper

class ProgressivePlugin(Plugin):
    """A nose plugin which has a progress bar and formats tracebacks for humans"""
    name = 'progressive'
    _totalTests = 0
    score = 10000  # Grab stdout and stderr before the capture plugin.

    def __init__(self, *args, **kwargs):
        super(ProgressivePlugin, self).__init__(*args, **kwargs)
        # Same wrapping pattern as the built-in capture plugin. The lists
        # shouldn't be necessary, but they don't cost much, and I have to
        # wonder why capture uses them.
        self._stderr, self._stdout, self._set_trace, self._cmdloop = \
            [], [], [], []

    def begin(self):
        """Make some monkeypatches to dodge progress bar.

        Wrap stderr and stdout to keep other users of them from smearing the
        progress bar. Wrap some pdb routines to stop showing the bar while in
        the debugger.

        """
        # The calls to begin/finalize end up like this: a call to begin() on
        # instance A of the plugin, then a paired begin/finalize for each test
        # on instance B, then a final call to finalize() on instance A.

        # TODO: Do only if isatty.
        self._stderr.append(sys.stderr)
        sys.stderr = StreamWrapper(sys.stderr, self)  # TODO: Any point?

        self._stdout.append(sys.stdout)
        sys.stdout = StreamWrapper(sys.stdout, self)

        self._set_trace.append(pdb.set_trace)
        pdb.set_trace = set_trace

        self._cmdloop.append(pdb.Pdb.cmdloop)
        pdb.Pdb.cmdloop = cmdloop

        # nosetests changes directories to the tests dir when run from a
        # distribution dir, so save the original cwd for relativizing paths.
        self._cwd = '' if self.conf.options.absolute_paths else getcwd()

    def finalize(self, result):
        """Put monkeypatches back as we found them."""
        sys.stderr = self._stderr.pop()
        sys.stdout = self._stdout.pop()
        pdb.set_trace = self._set_trace.pop()
        pdb.Pdb.cmdloop = self._cmdloop.pop()

    def options(self, parser, env):
        super(ProgressivePlugin, self).options(parser, env)
        parser.add_option('--progressive-editor',
                          type='string',
                          dest='editor',
                          default=env.get('NOSE_PROGRESSIVE_EDITOR',
                                          env.get('EDITOR', 'vi')),
                          help='The editor to use for the shortcuts in '
                               'tracebacks. Defaults to the value of $EDITOR '
                               'and then "vi". [NOSE_PROGRESSIVE_EDITOR]')
        parser.add_option('--progressive-abs',
                          action='store_true',
                          dest='absolute_paths',
                          default=env.get('NOSE_PROGRESSIVE_ABSOLUTE_PATHS', False),
                          help='Display paths in traceback as absolute, '
                               'rather than relative to the current working '
                               'directory. [NOSE_PROGRESSIVE_ABSOLUTE_PATHS]')
        parser.add_option('--progressive-advisories',
                          action='store_true',
                          dest='show_advisories',
                          default=env.get('NOSE_PROGRESSIVE_ADVISORIES', False),
                          help='Show skips and deprecation exceptions in '
                               'addition to failures and errors. '
                               '[NOSE_PROGRESSIVE_ADVISORIES]')
        parser.add_option('--progressive-with-styling',
                          action='store_true',
                          dest='with_styling',
                          default=env.get('NOSE_PROGRESSIVE_WITH_STYLING', False),
                          help='nose-progressive automatically omits bold and '
                               'color formatting when its output is directed '
                               'to a non-terminal. Specifying '
                               '--progressive-with-styling forces such '
                               'styling to be output regardless. '
                               '[NOSE_PROGRESSIVE_WITH_STYLING]')
        parser.add_option('--progressive-with-bar',
                          action='store_true',
                          dest='with_bar',
                          default=env.get('NOSE_PROGRESSIVE_WITH_BAR', False),
                          help='nose-progressive automatically omits the '
                               'progress bar when its output is directed to a '
                               'non-terminal. Specifying '
                               '--progressive-with-bar forces the bar to be '
                               'output regardless. This option implies '
                               '--progressive-with-styling. '
                               '[NOSE_PROGRESSIVE_WITH_BAR]')
        parser.add_option('--progressive-function-color',
                          type='int',
                          dest='function_color',
                          default=env.get('NOSE_PROGRESSIVE_FUNCTION_COLOR', 12),
                          help='Color of function names in tracebacks. An '
                               'ANSI color expressed as a number 0-15. '
                               '[NOSE_PROGRESSIVE_FUNCTION_COLOR]')
        parser.add_option('--progressive-dim-color',
                          type='int',
                          dest='dim_color',
                          default=env.get('NOSE_PROGRESSIVE_DIM_COLOR', 8),
                          help='Color of de-emphasized text (like editor '
                               'shortcuts) in tracebacks. An ANSI color '
                               'expressed as a number 0-15. '
                               '[NOSE_PROGRESSIVE_DIM_COLOR]')
        parser.add_option('--progressive-bar-filled-color',
                          type='int',
                          dest='bar_filled_color',
                          default=env.get('NOSE_PROGRESSIVE_BAR_FILLED_COLOR', 8),
                          help="Color of the progress bar's filled portion. An "
                                'ANSI color expressed as a number 0-15. '
                               '[NOSE_PROGRESSIVE_BAR_FILLED_COLOR]')
        parser.add_option('--progressive-bar-empty-color',
                          type='int',
                          dest='bar_empty_color',
                          default=env.get('NOSE_PROGRESSIVE_BAR_EMPTY_COLOR', 7),
                          help="Color of the progress bar's empty portion. An "
                                'ANSI color expressed as a number 0-15. '
                               '[NOSE_PROGRESSIVE_BAR_EMPTY_COLOR]')
        parser.add_option('--progressive-editor-shortcut-template',
                          type='string',
                          dest='editor_shortcut_template',
                          default=env.get(
                                'NOSE_PROGRESSIVE_EDITOR_SHORTCUT_TEMPLATE',
                                DEFAULT_EDITOR_SHORTCUT_TEMPLATE),
                          help='A str.format() template for the non-code lines'
                               ' of the traceback. '
                               '[NOSE_PROGRESSIVE_EDITOR_SHORTCUT_TEMPLATE]')

    def configure(self, options, conf):
        """Turn style-forcing on if bar-forcing is on.

        It'd be messy to position the bar but still have the rest of the
        terminal capabilities emit ''.

        """
        super(ProgressivePlugin, self).configure(options, conf)
        if (getattr(options, 'verbosity', 0) > 1 and
            getattr(options, 'enable_plugin_id', False)):
            # TODO: Can we forcibly disable the ID plugin?
            print ('Using --with-id and --verbosity=2 or higher with '
                   'nose-progressive causes visualization errors. Remove one '
                   'or the other to avoid a mess.')
        if options.with_bar:
            options.with_styling = True

    def prepareTestLoader(self, loader):
        """Insert ourselves into loader calls to count tests.

        The top-level loader call often returns lazy results, like a LazySuite.
        This is a problem, as we would destroy the suite by iterating over it
        to count the tests. Consequently, we monkeypatch the top-level loader
        call to do the load twice: once for the actual test running and again
        to yield something we can iterate over to do the count.

        """
        def capture_suite(orig_method, *args, **kwargs):
            """Intercept calls to the loader before they get lazy.

            Re-execute them to grab a copy of the possibly lazy suite, and
            count the tests therein.

            """
            self._totalTests += orig_method(*args, **kwargs).countTestCases()

            # Clear out the loader's cache. Otherwise, it never finds any tests
            # for the actual test run:
            loader._visitedPaths = set()

            return orig_method(*args, **kwargs)

        # TODO: If there's ever a practical need, also patch loader.suiteClass
        # or even TestProgram.createTests. createTests seems to be main top-
        # level caller of loader methods, and nose.core.collector() (which
        # isn't even called in nose) is an alternate one.
        if hasattr(loader, 'loadTestsFromNames'):
            loader.loadTestsFromNames = partial(capture_suite,
                                                loader.loadTestsFromNames)

    def prepareTestRunner(self, runner):
        """Replace TextTestRunner with something that prints fewer dots."""
        return ProgressiveRunner(self._cwd,
                                 self._totalTests,
                                 runner.stream,
                                 verbosity=self.conf.verbosity,
                                 config=self.conf)  # So we don't get a default
                                                    # NoPlugins manager

    def prepareTestResult(self, result):
        """Hang onto the progress bar so the StreamWrappers can grab it."""
        self.bar = result.bar

########NEW FILE########
__FILENAME__ = result
from __future__ import with_statement

from blessings import Terminal
from nose.plugins.skip import SkipTest
from nose.result import TextTestResult
from nose.util import isclass

from noseprogressive.bar import ProgressBar, NullProgressBar
from noseprogressive.tracebacks import format_traceback, extract_relevant_tb
from noseprogressive.utils import nose_selector, index_of_test_frame


class ProgressiveResult(TextTestResult):
    """Test result which updates a progress bar instead of printing dots

    Nose's ResultProxy will wrap it, and other plugins can still print
    stuff---but without smashing into my progress bar, care of my Plugin's
    stderr/out wrapping.

    """
    def __init__(self, cwd, total_tests, stream, config=None):
        super(ProgressiveResult, self).__init__(stream, None, 0, config=config)
        self._cwd = cwd
        self._options = config.options
        self._term = Terminal(stream=stream,
                              force_styling=config.options.with_styling)

        if self._term.is_a_tty or self._options.with_bar:
            # 1 in case test counting failed and returned 0
            self.bar = ProgressBar(total_tests or 1,
                                   self._term,
                                   config.options.bar_filled_color,
                                   config.options.bar_empty_color)
        else:
            self.bar = NullProgressBar()

        # Declare errorclass-savviness so ErrorClassPlugins don't monkeypatch
        # half my methods away:
        self.errorClasses = {}

    def startTest(self, test):
        """Update the progress bar."""
        super(ProgressiveResult, self).startTest(test)
        self.bar.update(nose_selector(test), self.testsRun)

    def _printTraceback(self, test, err):
        """Print a nicely formatted traceback.

        :arg err: exc_info()-style traceback triple
        :arg test: the test that precipitated this call

        """
        # Don't bind third item to a local var; that can create
        # circular refs which are expensive to collect. See the
        # sys.exc_info() docs.
        exception_type, exception_value = err[:2]
        # TODO: In Python 3, the traceback is attached to the exception
        # instance through the __traceback__ attribute. If the instance
        # is saved in a local variable that persists outside the except
        # block, the traceback will create a reference cycle with the
        # current frame and its dictionary of local variables. This will
        # delay reclaiming dead resources until the next cyclic garbage
        # collection pass.

        extracted_tb = extract_relevant_tb(
            err[2],
            exception_type,
            exception_type is test.failureException)
        test_frame_index = index_of_test_frame(
            extracted_tb,
            exception_type,
            exception_value,
            test)
        if test_frame_index:
            # We have a good guess at which frame is the test, so
            # trim everything until that. We don't care to see test
            # framework frames.
            extracted_tb = extracted_tb[test_frame_index:]

        with self.bar.dodging():
            self.stream.write(''.join(
                format_traceback(
                    extracted_tb,
                    exception_type,
                    exception_value,
                    self._cwd,
                    self._term,
                    self._options.function_color,
                    self._options.dim_color,
                    self._options.editor,
                    self._options.editor_shortcut_template)))

    def _printHeadline(self, kind, test, is_failure=True):
        """Output a 1-line error summary to the stream if appropriate.

        The line contains the kind of error and the pathname of the test.

        :arg kind: The (string) type of incident the precipitated this call
        :arg test: The test that precipitated this call

        """
        if is_failure or self._options.show_advisories:
            with self.bar.dodging():
                self.stream.writeln(
                        '\n' +
                        (self._term.bold if is_failure else '') +
                        '%s: %s' % (kind, nose_selector(test)) +
                        (self._term.normal if is_failure else ''))  # end bold

    def _recordAndPrintHeadline(self, test, error_class, artifact):
        """Record that an error-like thing occurred, and print a summary.

        Store ``artifact`` with the record.

        Return whether the test result is any sort of failure.

        """
        # We duplicate the errorclass handling from super rather than calling
        # it and monkeying around with showAll flags to keep it from printing
        # anything.
        is_error_class = False
        for cls, (storage, label, is_failure) in self.errorClasses.items():
            if isclass(error_class) and issubclass(error_class, cls):
                if is_failure:
                    test.passed = False
                storage.append((test, artifact))
                is_error_class = True
        if not is_error_class:
            self.errors.append((test, artifact))
            test.passed = False

        is_any_failure = not is_error_class or is_failure
        self._printHeadline(label if is_error_class else 'ERROR',
                            test,
                            is_failure=is_any_failure)
        return is_any_failure

    def addSkip(self, test, reason):
        """Catch skipped tests in Python 2.7 and above.

        Though ``addSkip()`` is deprecated in the nose plugin API, it is very
        much not deprecated as a Python 2.7 ``TestResult`` method. In Python
        2.7, this will get called instead of ``addError()`` for skips.

        :arg reason: Text describing why the test was skipped

        """
        self._recordAndPrintHeadline(test, SkipTest, reason)
        # Python 2.7 users get a little bonus: the reason the test was skipped.
        if isinstance(reason, Exception):
            reason = reason.message
        if reason and self._options.show_advisories:
            with self.bar.dodging():
                self.stream.writeln(reason)

    def addError(self, test, err):
        # We don't read this, but some other plugin might conceivably expect it
        # to be there:
        excInfo = self._exc_info_to_string(err, test)
        is_failure = self._recordAndPrintHeadline(test, err[0], excInfo)
        if is_failure:
            self._printTraceback(test, err)

    def addFailure(self, test, err):
        super(ProgressiveResult, self).addFailure(test, err)
        self._printHeadline('FAIL', test)
        self._printTraceback(test, err)

    def printSummary(self, start, stop):
        """As a final summary, print number of tests, broken down by result."""
        def renderResultType(type, number, is_failure):
            """Return a rendering like '2 failures'.

            :arg type: A singular label, like "failure"
            :arg number: The number of tests with a result of that type
            :arg is_failure: Whether that type counts as a failure

            """
            # I'd rather hope for the best with plurals than totally punt on
            # being Englishlike:
            ret = '%s %s%s' % (number, type, 's' if number != 1 else '')
            if is_failure and number:
                ret = self._term.bold(ret)
            return ret

        # Summarize the special cases:
        counts = [('test', self.testsRun, False),
                  ('failure', len(self.failures), True),
                  ('error', len(self.errors), True)]
        # Support custom errorclasses as well as normal failures and errors.
        # Lowercase any all-caps labels, but leave the rest alone in case there
        # are hard-to-read camelCaseWordBreaks.
        counts.extend([(label.lower() if label.isupper() else label,
                        len(storage),
                        is_failure)
                        for (storage, label, is_failure) in
                            self.errorClasses.values() if len(storage)])
        summary = (', '.join(renderResultType(*a) for a in counts) +
                   ' in %.1fs' % (stop - start))

        # Erase progress bar. Bash doesn't clear the whole line when printing
        # the prompt, leaving a piece of the bar. Also, the prompt may not be
        # at the bottom of the terminal.
        self.bar.erase()
        self.stream.writeln()
        if self.wasSuccessful():
            self.stream.write(self._term.bold_green('OK!  '))
        self.stream.writeln(summary)

########NEW FILE########
__FILENAME__ = runner
from time import time

import nose.core

from noseprogressive.result import ProgressiveResult


class ProgressiveRunner(nose.core.TextTestRunner):
    """Test runner that makes a lot less noise than TextTestRunner"""

    def __init__(self, cwd, totalTests, stream, **kwargs):
        super(ProgressiveRunner, self).__init__(stream, **kwargs)
        self._cwd = cwd
        self._totalTests = totalTests

    def _makeResult(self):
        """Return a Result that doesn't print dots.

        Nose's ResultProxy will wrap it, and other plugins can still print
        stuff---but without smashing into our progress bar, care of
        ProgressivePlugin's stderr/out wrapping.

        """
        return ProgressiveResult(self._cwd,
                                 self._totalTests,
                                 self.stream,
                                 config=self.config)

    def run(self, test):
        "Run the given test case or test suite...quietly."
        # These parts of Nose's pluggability are baked into
        # nose.core.TextTestRunner. Reproduce them:
        wrapper = self.config.plugins.prepareTest(test)
        if wrapper is not None:
            test = wrapper
        wrapped = self.config.plugins.setOutputStream(self.stream)
        if wrapped is not None:
            self.stream = wrapped

        result = self._makeResult()
        startTime = time()
        test(result)
        stopTime = time()

        # We don't care to hear about errors again at the end; we take care of
        # that in result.addError(), while the tests run.
        # result.printErrors()
        #
        # However, we do need to call this one useful line from
        # nose.result.TextTestResult's implementation of printErrors() to make
        # sure other plugins get a chance to report:
        self.config.plugins.report(self.stream)

        result.printSummary(startTime, stopTime)
        self.config.plugins.finalize(result)
        return result

########NEW FILE########
__FILENAME__ = test_bar
"""Tests for the progress bar"""
# TODO: Running these on a tty of type "xterm" fails.

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from blessings import Terminal
from nose.tools import eq_

from noseprogressive.bar import ProgressBar


class MockTerminal(Terminal):
    @property
    def width(self):
        return 50

    @property
    def height(self):
        return 24


class MonochromeTerminal(MockTerminal):
    """Work around color reporting never going back to 0 once it's been 256."""
    @property
    def number_of_colors(self):
        return 0


def test_color_bar_half():
    """Assert that a half-filled 16-color bar draws properly."""
    out = StringIO()
    term = MockTerminal(kind='xterm-256color', stream=out, force_styling=True)
    bar = ProgressBar(28, term)

    bar.update('HI', 14)
    eq_(out.getvalue(), ''.join([term.save,
                                 term.move(24, 0),
                                 term.bold('HI                                '),
                                 '  ',
                                 term.on_color(8)('       '),
                                 term.on_color(7)('       '),
                                 term.restore]))

def test_color_bar_full():
    """Assert that a complete 16-color bar draws properly."""
    out = StringIO()
    term = MockTerminal(kind='xterm-256color', stream=out, force_styling=True)
    bar = ProgressBar(28, term)

    bar.update('HI', 28)
    eq_(out.getvalue(), ''.join([term.save,
                                 term.move(24, 0),
                                 term.bold('HI                                '),
                                 '  ',
                                 term.on_color(8)('              '),
                                 term.on_color(7)(''),
                                 term.restore]))


def test_monochrome_bar():
    """Assert that the black-and-white bar draws properly when < 16 colors are available."""
    out = StringIO()
    term = MonochromeTerminal(kind='xterm', stream=out, force_styling=True)
    assert term.number_of_colors < 16
    bar = ProgressBar(28, term)

    bar.update('HI', 14)
    eq_(out.getvalue(), ''.join([term.save,
                                 term.move(24, 0),
                                 term.bold('HI                                '),
                                 '  ',
                                 term.reverse('       '),
                                 '_______',
                                 term.restore]))

########NEW FILE########
__FILENAME__ = test_integration
from unittest import TestCase, TestSuite

from nose import SkipTest
from nose.plugins import PluginTester
from nose.plugins.skip import Skip
from nose.tools import eq_

from noseprogressive import ProgressivePlugin


class IntegrationTestCase(PluginTester, TestCase):
    activate = '--with-progressive'
    plugins = [ProgressivePlugin(), Skip()]

    def _count_eq(self, text, count):
        """Assert `text` appears `count` times in the captured output."""
        eq_(str(self.output).count(text), count)


class HookTests(IntegrationTestCase):
    """Tests that ensure our code is getting run when expected"""
    def makeSuite(self):
        class Failure(TestCase):
            def runTest(self):
                assert False

        class Success(TestCase):
            def runTest(self):
                pass

        class Error(TestCase):
            def runTest(self):
                raise NotImplementedError

        return TestSuite([Failure(), Success(), Error()])

    def test_fail(self):
        """Make sure failed tests print a line."""
        # Grrr, we seem to get stdout here, not stderr.
        self._count_eq('FAIL: ', 1)

    def test_error(self):
        """Make sure uncaught errors print a line."""
        self._count_eq('ERROR: ', 1)

    # Proper handling of test successes is tested by the sum of the above, in
    # that no more than one failure, skip, and error is shown.

    def test_summary(self):
        """Make sure summary prints.

        Also incidentally test that addError() counts correctly.

        """
        assert '3 tests, 1 failure, 1 error in ' in self.output


class AdvisoryShowingTests(IntegrationTestCase):
    """Tests for --progressive-advisories option"""
    args = ['--progressive-advisories']

    def makeSuite(self):
        class Skip(TestCase):
            def runTest(self):
                raise SkipTest

        return TestSuite([Skip()])

    def test_skip(self):
        """Make sure skipped tests print a line."""
        self._count_eq('SKIP: ', 1)

    def test_summary(self):
        """Make sure summary prints.

        Test pluralization and the listing of custom error classes.

        """
        assert '1 test, 0 failures, 0 errors, 1 skip in ' in self.output


class SkipHidingTests(IntegrationTestCase):
    """Tests for the eliding of skips by default"""
    def makeSuite(self):
        class Skip(TestCase):
            def runTest(self):
                raise SkipTest

        return TestSuite([Skip()])

    def test_skip_invisible(self):
        """Make sure skipped tests don't show up in the output."""
        self._count_eq('SkipTest', 0)


class UnitTestFrameSkippingTests(IntegrationTestCase):
    """Tests for the skipping of (uninteresting) unittest frames"""
    def makeSuite(self):
        class Failure(TestCase):
            def runTest(self):
                # Tack a unittest frame onto the end of the traceback. There's
                # already implicitly one on the beginning.
                self.fail()

        return TestSuite([Failure()])

    def test_skipping(self):
        """Make sure no unittest frames make it into the traceback."""
        # Assert *some* traceback printed...
        assert 'self.fail()' in self.output
        # ...but not any unittest frames:
        assert 'unittest' not in self.output


# def test_slowly():
#     """Slow down so we can visually inspect the progress bar."""
#     from time import sleep
#     def failer(y):
#         print "booga"
#         sleep(0.1)
#         if y == 1:
#             assert False
#     for x in range(10):
#         yield failer, x


# def test_syntax_error():
#     x = 1
#     :bad

########NEW FILE########
__FILENAME__ = test_tracebacks
# -*- coding: utf-8 -*-
"""Tests for traceback formatting."""

from noseprogressive.tracebacks import format_traceback


syntax_error_tb = ([
     ("setup.py", 79, '?', """classifiers = ["""),
     ("/usr/lib64/python2.4/distutils/core.py", 149, 'setup', """dist.run_commands()"""),
     ("/usr/lib64/python2.4/distutils/dist.py", 946, 'run_commands', """self.run_command(cmd)"""),
     ("/usr/lib64/python2.4/distutils/dist.py", 966, 'run_command', """cmd_obj.run()"""),
     ("/usr/lib/python2.4/site-packages/setuptools/command/install.py", 76, 'run', """self.do_egg_install()"""),
     ("/usr/lib/python2.4/site-packages/setuptools/command/install.py", 100, 'do_egg_install', """cmd.run()"""),
     ("/usr/lib/python2.4/site-packages/setuptools/command/easy_install.py", 211, 'run', """self.easy_install(spec, not self.no_deps)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/command/easy_install.py", 427, 'easy_install', """return self.install_item(None, spec, tmpdir, deps, True)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/command/easy_install.py", 473, 'install_item', """self.process_distribution(spec, dist, deps)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/command/easy_install.py", 518, 'process_distribution', """distros = WorkingSet([]).resolve("""),
     ("/usr/lib/python2.4/site-packages/pkg_resources.py", 481, 'resolve', """dist = best[req.key] = env.best_match(req, self, installer)"""),
     ("/usr/lib/python2.4/site-packages/pkg_resources.py", 717, 'best_match', """return self.obtain(req, installer) # try and download/install"""),
     ("/usr/lib/python2.4/site-packages/pkg_resources.py", 729, 'obtain', """return installer(requirement)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/command/easy_install.py", 432, 'easy_install', """dist = self.package_index.fetch_distribution("""),
     ("/usr/lib/python2.4/site-packages/setuptools/package_index.py", 462, 'fetch_distribution', """self.find_packages(requirement)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/package_index.py", 303, 'find_packages', """self.scan_url(self.index_url + requirement.unsafe_name+'/')"""),
     ("/usr/lib/python2.4/site-packages/setuptools/package_index.py", 612, 'scan_url', """self.process_url(url, True)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/package_index.py", 190, 'process_url', """f = self.open_url(url)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/package_index.py", 579, 'open_url', """return open_with_auth(url)"""),
     ("/usr/lib/python2.4/site-packages/setuptools/package_index.py", 676, 'open_with_auth', """fp = urllib2.urlopen(request)"""),
     ("/usr/lib64/python2.4/urllib2.py", 130, 'urlopen', """return _opener.open(url, data)"""),
     ("/usr/lib64/python2.4/urllib2.py", 358, 'open', """response = self._open(req, data)"""),
     ("/usr/lib64/python2.4/urllib2.py", 376, '_open', """'_open', req)"""),
     ("/usr/lib64/python2.4/urllib2.py", 337, '_call_chain', """result = func(*args)"""),
     ("/usr/lib64/python2.4/urllib2.py", 573, '<lambda>', """lambda r, proxy=url, type=type, meth=self.proxy_open: \\"""),
     ("/usr/lib64/python2.4/urllib2.py", 580, 'proxy_open', """if '@' in host:""")
     # Was originally TypeError: iterable argument required
    ], SyntaxError, SyntaxError('invalid syntax', ('/Users/erose/Checkouts/nose-progress/noseprogressive/tests/test_integration.py', 97, 5, '    :bad\n')))
attr_error_tb = ([
     ("/usr/share/PackageKit/helpers/yum/yumBackend.py", 2926, 'install_signature', """self.yumbase.getKeyForPackage(pkg, askcb = lambda x, y, z: True)"""),
     ("/usr/lib/python2.6/site-packages/yum/__init__.py", 4309, 'getKeyForPackage', """result = ts.pgpImportPubkey(misc.procgpgkey(info['raw_key']))"""),
     ("/usr/lib/python2.6/site-packages/rpmUtils/transaction.py", 59, '__getattr__', """return self.getMethod(attr)"""),
     ("/usr/lib/python2.6/site-packages/rpmUtils/transaction.py", 69, 'getMethod', """return getattr(self.ts, method)""")
    ], AttributeError, AttributeError("'NoneType' object has no attribute 'pgpImportPubkey'"))


def test_syntax_error():
    """Exercise special handling of syntax errors to show it doesn't crash."""
    ''.join(format_traceback(*syntax_error_tb))


def test_non_syntax_error():
    """Exercise typical error formatting to show it doesn't crash."""
    ''.join(format_traceback(*attr_error_tb))


def test_empty_tracebacks():
    """Make sure we don't crash on empty tracebacks.

    Sometimes, stuff crashes before we even get to the test. pdbpp has been
    doing this a lot to me lately. When that happens, we receive an empty
    traceback.

    """
    list(format_traceback(
        [],
        AttributeError,
        AttributeError("'NoneType' object has no attribute 'pgpImportPubkey'")))


def test_unicode():
    """Don't have encoding explosions when a line of code contains non-ASCII."""
    unicode_tb = ([
         ("/usr/lib/whatあever.py", 69, 'getあMethod', "return u'あ'")
        ], AttributeError, AttributeError("'NoneType' object has no pants.'"))
    u''.join(format_traceback(*unicode_tb))


def test_none_members():
    """Don't crash if the attrs of an extracted traceback are None.

    This can happen when using mocking.

    """
    list(format_traceback(
        [(None, None, None, None)],
        AttributeError,
        AttributeError('I have many nasty attributes.')))

########NEW FILE########
__FILENAME__ = test_utils
from os import chdir, getcwd
from os.path import dirname, basename, realpath
from unittest import TestCase

from nose.tools import eq_
from nose.util import src

from noseprogressive.utils import human_path, index_of_test_frame


class DummyCase(TestCase):
    """A mock test to be thrown at ``index_of_test_frame()``

    Significantly, it's in the same file as the tests which use it, so the
    frame-finding heuristics can find a match.

    """
    def runTest(self):
        pass
dummy_test = DummyCase()


def test_human_path():
    chdir(dirname(__file__))
    eq_(human_path(__file__, getcwd()), basename(__file__))


def test_index_when_syntax_error_in_test_frame():
    """Make sure ``index_of_test_frame()`` returns None for SyntaxErrors in the test frame.

    When the SyntaxError is in the test frame, the test frame doesn't show up
    in the traceback. We reproduce this below by not referencing.

    """
    extracted_tb = \
        [('/nose/loader.py', 379, 'loadTestsFromName', 'addr.filename, addr.module)'),
         ('/nose/importer.py', 39, 'importFromPath', 'return self.importFromDir(dir_path, fqname)'),
         ('/nose/importer.py', 86, 'importFromDir', 'mod = load_module(part_fqname, fh, filename, desc)')]
    eq_(index_of_test_frame(extracted_tb,
                            SyntaxError,
                            SyntaxError('invalid syntax',
                                        ('tests.py', 120, 1, "{'fields': ['id'],\n")),
                            dummy_test),
        None)


def test_index_when_syntax_error_below_test_frame():
    """Make sure we manage to find the test frame if there's a SyntaxError below it.

    Here we present to ``index_of_test_frame()`` a traceback that represents
    this test raising a SyntaxError indirectly, in a function called by same
    test.

    """
    extracted_tb = [('/nose/case.py', 183, 'runTest', 'self.test(*self.arg)'),
                    # Legit path so the frame finder can compare to the address of DummyCase:
                    (src(realpath(__file__)), 34, 'test_index_when_syntax_error_below_test_frame', 'deeper()'),
                    ('/noseprogressive/tests/test_utils.py', 33, 'deeper', 'import noseprogressive.tests.syntaxerror')]
    eq_(index_of_test_frame(extracted_tb,
                            SyntaxError,
                            SyntaxError('invalid syntax',
                                        ('/tests/syntaxerror.py', 1, 1, ':bad\n')),
                            dummy_test),
        1)

########NEW FILE########
__FILENAME__ = tracebacks
"""Fancy traceback formatting"""

import os
from sys import version_info

from traceback import extract_tb, format_exception_only

from blessings import Terminal
from nose.util import src

from noseprogressive.utils import human_path


DEFAULT_EDITOR_SHORTCUT_TEMPLATE = (u'  {dim_format}{editor} '
                                     '+{line_number:<{line_number_max_width}} '
                                     '{path}{normal}'
                                     '{function_format}{hash_if_function}'
                                     '{function}{normal}')


def format_traceback(extracted_tb,
                     exc_type,
                     exc_value,
                     cwd='',
                     term=None,
                     function_color=12,
                     dim_color=8,
                     editor='vi',
                     template=DEFAULT_EDITOR_SHORTCUT_TEMPLATE):
    """Return an iterable of formatted Unicode traceback frames.

    Also include a pseudo-frame at the end representing the exception itself.

    Format things more compactly than the stock formatter, and make every
    frame an editor shortcut.

    """
    def format_shortcut(editor,
                        path,
                        line_number,
                        function=None):
        """Return a pretty-printed editor shortcut."""
        return template.format(editor=editor,
                               line_number=line_number,
                               path=path,
                               function=function or u'',
                               hash_if_function=u'  # ' if function else u'',
                               function_format=term.color(function_color),
                               # Underline is also nice and doesn't make us
                               # worry about appearance on different background
                               # colors.
                               normal=term.normal,
                               dim_format=term.color(dim_color) + term.bold,
                               line_number_max_width=line_number_max_width,
                               term=term)

    template += '\n'  # Newlines are awkward to express on the command line.
    extracted_tb = _unicode_decode_extracted_tb(extracted_tb)
    if not term:
        term = Terminal()

    if extracted_tb:
        # Shorten file paths:
        for i, (file, line_number, function, text) in enumerate(extracted_tb):
            extracted_tb[i] = human_path(src(file), cwd), line_number, function, text

        line_number_max_width = len(unicode(max(the_line for _, the_line, _, _ in extracted_tb)))

        # Stack frames:
        for i, (path, line_number, function, text) in enumerate(extracted_tb):
            text = (text and text.strip()) or u''

            yield (format_shortcut(editor, path, line_number, function) +
                   (u'    %s\n' % text))

    # Exception:
    if exc_type is SyntaxError:
        # Format a SyntaxError to look like our other traceback lines.
        # SyntaxErrors have a format different from other errors and include a
        # file path which looks out of place in our newly highlit, editor-
        # shortcutted world.
        exc_lines = [format_shortcut(editor, exc_value.filename, exc_value.lineno)]
        formatted_exception = format_exception_only(SyntaxError, exc_value)[1:]
    else:
        exc_lines = []
        formatted_exception = format_exception_only(exc_type, exc_value)
    exc_lines.extend([_decode(f) for f in formatted_exception])
    yield u''.join(exc_lines)


# Adapted from unittest:

def extract_relevant_tb(tb, exctype, is_test_failure):
    """Return extracted traceback frame 4-tuples that aren't unittest ones.

    This used to be _exc_info_to_string().

    """
    # Skip test runner traceback levels:
    while tb and _is_unittest_frame(tb):
        tb = tb.tb_next
    if is_test_failure:
        # Skip assert*() traceback levels:
        length = _count_relevant_tb_levels(tb)
        return extract_tb(tb, length)
    return extract_tb(tb)


def _decode(string):
    """Decode a string as if it were UTF-8, swallowing errors. Turn Nones into
    "None", which is more helpful than crashing.

    In Python 2, extract_tb() returns simple strings. We arbitrarily guess that
    UTF-8 is the encoding and use "replace" mode for undecodable chars. I'm
    guessing that in Python 3 we've come to our senses and everything's
    Unicode. We'll see when we add Python 3 to the tox config.

    """
    if string is None:
        return 'None'
    return string if isinstance(string, unicode) else string.decode('utf-8', 'replace')


def _unicode_decode_extracted_tb(extracted_tb):
    """Return a traceback with the string elements translated into Unicode."""
    return [(_decode(file), line_number, _decode(function), _decode(text))
            for file, line_number, function, text in extracted_tb]


def _is_unittest_frame(tb):
    """Return whether the given frame is something other than a unittest one."""
    return '__unittest' in tb.tb_frame.f_globals


def _count_relevant_tb_levels(tb):
    """Return the number of frames in ``tb`` before all that's left is unittest frames.

    Unlike its namesake in unittest, this doesn't bail out as soon as it hits a
    unittest frame, which means we don't bail out as soon as somebody uses the
    mock library, which defines ``__unittest``.

    """
    length = contiguous_unittest_frames = 0
    while tb:
        length += 1
        if _is_unittest_frame(tb):
            contiguous_unittest_frames += 1
        else:
            contiguous_unittest_frames = 0
        tb = tb.tb_next
    return length - contiguous_unittest_frames

########NEW FILE########
__FILENAME__ = utils
from os.path import abspath, realpath

from nose.tools import nottest
import nose.util


@nottest
def test_address(test):
    """Return the result of nose's test_address(), None if it's stumped."""
    try:
        return nose.util.test_address(test)
    except TypeError:  # Explodes if the function passed to @with_setup applied
                       # to a test generator has an error.
        pass


def nose_selector(test):
    """Return the string you can pass to nose to run `test`, including argument
    values if the test was made by a test generator.

    Return "Unknown test" if it can't construct a decent path.

    """
    address = test_address(test)
    if address:
        file, module, rest = address

        if module:
            if rest:
                try:
                    return '%s:%s%s' % (module, rest, test.test.arg or '')
                except AttributeError:
                    return '%s:%s' % (module, rest)
            else:
                return module
    return 'Unknown test'


class OneTrackMind(object):
    """An accurate simulation of my brain

    I can know one thing at a time, at some level of confidence. You can tell
    me other things, but if I'm not as confident of them, I'll forget them. If
    I'm more confident of them, they'll replace what I knew before.

    """
    def __init__(self):
        self.confidence = 0
        self.best = None

    def know(self, what, confidence):
        """Know something with the given confidence, and return self for chaining.

        If confidence is higher than that of what we already know, replace
        what we already know with what you're telling us.

        """
        if confidence > self.confidence:
            self.best = what
            self.confidence = confidence
        return self


@nottest  # still needed?
def index_of_test_frame(extracted_tb, exception_type, exception_value, test):
    """Return the index of the frame that points to the failed test or None.

    Sometimes this is hard. It takes its best guess. If exception_type is
    SyntaxError or it has no idea, it returns None.

    Args:
        address: The result of a call to test_address(), indicating which test
            failed
        exception_type, exception_value: Needed in case this is a SyntaxError
            and therefore doesn't have the whole story in extracted_tb
        extracted_tb: The traceback, after having been passed through
            extract_tb()

    """
    try:
        address = test_address(test)
    except TypeError:
        # Explodes if the function passed to @with_setup
        # applied to a test generator has an error.
        address = None

    # address is None if the test callable couldn't be found. No sense trying
    # to find the test frame if there's no such thing:
    if address is None:
        return None

    test_file, _, test_call = address

    # OneTrackMind helps us favor the latest frame, even if there's more than
    # one match of equal confidence.
    knower = OneTrackMind()

    if test_file is not None:
        test_file_path = realpath(test_file)

        # TODO: Perfect. Right now, I'm just comparing by function name within
        # a module. This should break only if you have two identically-named
        # functions from a single module in the call stack when your test
        # fails. However, it bothers me. I'd rather be finding the actual
        # callables and comparing them directly, but that might not work with
        # test generators.
        for i, frame in enumerate(extracted_tb):
            file, line, function, text = frame
            if file is not None and test_file_path == realpath(file):
                # TODO: Now that we're eliding until the test frame, is it
                # desirable to have this confidence-2 guess when just the file
                # path is matched?
                knower.know(i, 2)
                if (hasattr(test_call, 'rsplit') and  # test_call can be None
                    function == test_call.rsplit('.')[-1]):
                    knower.know(i, 3)
                    break
    return knower.best


def human_path(path, cwd):
    """Return the most human-readable representation of the given path.

    If an absolute path is given that's within the current directory, convert
    it to a relative path to shorten it. Otherwise, return the absolute path.

    """
    # TODO: Canonicalize the path to remove /kitsune/../kitsune nonsense.
    path = abspath(path)
    if cwd and path.startswith(cwd):
        path = path[len(cwd) + 1:]  # Make path relative. Remove leading slash.
    return path

########NEW FILE########
__FILENAME__ = wrapping
"""Facilities for wrapping stderr and stdout and dealing with the fallout"""

from __future__ import with_statement
import __builtin__
import cmd
import pdb
import sys


def cmdloop(self, *args, **kwargs):
    """Call pdb's cmdloop, making readline work.

    Patch raw_input so it sees the original stdin and stdout, lest
    readline refuse to work.

    The C implementation of raw_input uses readline functionality only if
    both stdin and stdout are from a terminal AND are FILE*s (not
    PyObject*s): http://bugs.python.org/issue5727 and
    https://bugzilla.redhat.com/show_bug.cgi?id=448864

    """
    def unwrapping_raw_input(*args, **kwargs):
        """Call raw_input(), making sure it finds an unwrapped stdout."""
        wrapped_stdout = sys.stdout
        sys.stdout = wrapped_stdout.stream

        ret = orig_raw_input(*args, **kwargs)

        sys.stdout = wrapped_stdout
        return ret

    orig_raw_input = raw_input
    if hasattr(sys.stdout, 'stream'):
        __builtin__.raw_input = unwrapping_raw_input
    # else if capture plugin has replaced it with a StringIO, don't bother.
    try:
        # Interesting things happen when you try to not reference the
        # superclass explicitly.
        ret = cmd.Cmd.cmdloop(self, *args, **kwargs)
    finally:
        __builtin__.raw_input = orig_raw_input
    return ret


def set_trace(*args, **kwargs):
    """Call pdb.set_trace, making sure it receives the unwrapped stdout.

    This is so we don't keep drawing progress bars over debugger output.

    """
    # There's no stream attr if capture plugin is enabled:
    out = sys.stdout.stream if hasattr(sys.stdout, 'stream') else None

    # Python 2.5 can't put an explicit kwarg and **kwargs in the same function
    # call.
    kwargs['stdout'] = out
    debugger = pdb.Pdb(*args, **kwargs)

    # Ordinarily (and in a silly fashion), pdb refuses to use raw_input() if
    # you pass it a stream on instantiation. Fix that:
    debugger.use_rawinput = True

    debugger.set_trace(sys._getframe().f_back)


class StreamWrapper(object):
    """Wrapper for stdout/stderr to do progress bar dodging"""
    # An outer class so isinstance() works in begin()

    def __init__(self, stream, plugin):
        self.stream = stream
        self._plugin = plugin

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def write(self, data):
        if hasattr(self._plugin, 'bar'):
            with self._plugin.bar.dodging():
                self.stream.write(data)
        else:
            # Some things write to stderr before the bar is inited.
            self.stream.write(data)

########NEW FILE########
