__FILENAME__ = calculator_spec
"""
A simple calculator specification.

"""

from ivoire import describe, context


class Calculator(object):
    def add(self, x, y):
        return x + y

    def divide(self, x, y):
        return x / y


with describe(Calculator) as it:
    @it.before
    def before(test):
        test.calc = Calculator()

    with it("adds two numbers") as test:
        test.assertEqual(test.calc.add(2, 4), 6)

    with it("multiplies two numbers") as test:
        test.assertEqual(test.calc.multiply(2, 3), 6)

    with context(Calculator.divide):
        with it("divides two numbers") as test:
            test.assertEqual(test.calc.divide(8, 4), 2)

        with it("doesn't divide by zero") as test:
            with test.assertRaises(ZeroDivisionError):
                test.calc.divide(8, 0)

########NEW FILE########
__FILENAME__ = next_spec
"""
A spec for the next() standard library function.

"""

from ivoire import describe


with describe(next) as it:
    with it("returns the next element of an iterable") as test:
        iterable = iter(range(5))
        test.assertEqual(next(iterable), 0)

    with it("raises StopIteration if no elements are found") as test:
        with test.assertRaises(StopIteration):
            next(iter([]))

    with it("returns default instead of StopIteration if given") as test:
        default = "a default"
        test.assertEqual(next(iter([]), default), default)

########NEW FILE########
__FILENAME__ = compat
"""
Various crude backports (mostly direct copying) of things from later versions.

"""

try:
    from textwrap import indent
except ImportError:
    # Copied for <3.3

    def indent(text, prefix, predicate=None):
        """Adds 'prefix' to the beginning of selected lines in 'text'.

        If 'predicate' is provided, 'prefix' will only be added to the lines
        where 'predicate(line)' is True. If 'predicate' is not provided,
        it will default to adding 'prefix' to all non-empty lines that do not
        consist solely of whitespace characters.
        """
        if predicate is None:
            def predicate(line):
                return line.strip()

        def prefixed_lines():
            for line in text.splitlines(True):
                yield (prefix + line if predicate(line) else line)
        return ''.join(prefixed_lines())


try:
    from importlib.machinery import FileFinder, SourceFileLoader
except (AttributeError, ImportError):
    FileFinder = SourceFileLoader = object
else:
    if not hasattr(SourceFileLoader, "source_to_code"):  # pre-3.4
        class SourceFileLoader(SourceFileLoader):
            def source_to_code(self, source_bytes, source_path):
                pass
finally:
    transform_possible = SourceFileLoader is not object

########NEW FILE########
__FILENAME__ = load
import fnmatch
import imp
import os


def load_by_name(name):
    """
    Load a spec from either a file path or a fully qualified name.

    """

    if os.path.exists(name):
        load_from_path(name)
    else:
        __import__(name)


def load_from_path(path):
    """
    Load a spec from a given path, discovering specs if a directory is given.

    """

    if os.path.isdir(path):
        paths = discover(path)
    else:
        paths = [path]

    for path in paths:
        name = os.path.basename(os.path.splitext(path)[0])
        imp.load_source(name, path)


def filter_specs(paths):
    """
    Filter out only the specs from the given (flat iterable of) paths.

    """

    return fnmatch.filter(paths, "*_spec.py")


def discover(path, filter_specs=filter_specs):
    """
    Discover all of the specs recursively inside ``path``.

    Successively yields the (full) relative paths to each spec.

    """

    for dirpath, _, filenames in os.walk(path):
        for spec in filter_specs(filenames):
            yield os.path.join(dirpath, spec)

########NEW FILE########
__FILENAME__ = manager
class ContextManager(object):
    def __init__(self, result=None):
        self.context_depth = 0
        self.result = result

    def create_context(self, for_target):
        name = getattr(for_target, "__name__", for_target)
        return Context(name, self)

    def enter(self, context):
        self.context_depth += 1

        enterContext = getattr(self.result, "enterContext", None)
        if enterContext is not None:
            enterContext(context, depth=self.context_depth)

    def exit(self):
        self.context_depth -= 1

        exitContext = getattr(self.result, "exitContext", None)
        if exitContext is not None:
            exitContext(depth=self.context_depth)


class Context(object):
    def __init__(self, name, manager):
        self.manager = manager
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __enter__(self):
        """
        Enter the context.

        """

        self.manager.enter(self)

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context.

        """

        self.manager.exit()

########NEW FILE########
__FILENAME__ = result
from __future__ import unicode_literals
from unittest import TestResult
import sys
import time

from ivoire.compat import indent


class ExampleResult(TestResult):
    """
    Track the outcomes of example runs.

    """

    def __init__(self, formatter):
        super(ExampleResult, self).__init__()
        self.formatter = formatter

    def startTestRun(self):
        super(ExampleResult, self).startTestRun()
        self._start = time.time()

    def enterContext(self, context, depth):
        self.formatter.show(self.formatter.enter_context(context, depth))

    def exitContext(self, depth):
        self.formatter.show(self.formatter.exit_context(depth))

    def enterGroup(self, group):
        self.formatter.show(self.formatter.enter_group(group))

    def addError(self, example, exc_info):
        super(ExampleResult, self).addError(example, exc_info)
        self.formatter.show(self.formatter.error(example, exc_info))

    def addFailure(self, example, exc_info):
        super(ExampleResult, self).addFailure(example, exc_info)
        self.formatter.show(self.formatter.failure(example, exc_info))

    def addSuccess(self, example):
        super(ExampleResult, self).addSuccess(example)
        self.formatter.show(self.formatter.success(example))

    def addSkip(self, example, reason):
        super(ExampleResult, self).addSkip(example, reason)
        self.formatter.show(self.formatter.skip(example, reason))

    def exitGroup(self, group):
        self.formatter.show(self.formatter.exit_group(group))

    def stopTestRun(self):
        super(ExampleResult, self).stopTestRun()
        self.elapsed = time.time() - self._start

        self.formatter.finished()
        self.formatter.show(self.formatter.errors(self.errors))
        self.formatter.show(self.formatter.failures(self.failures))
        self.formatter.show(
            self.formatter.statistics(elapsed=self.elapsed, result=self)
        )


class FormatterMixin(object):
    """
    Provide some higher-level formatting using the child's building blocks.

    """

    def finished(self):
        """
        The run has finished.

        """

        self.show("\n\n")

    def statistics(self, elapsed, result):
        """
        Return output for the combined time and result summary statistics.

        """

        return "\n".join((self.timing(elapsed), self.result_summary(result)))

    def errors(self, errors):
        if not errors:
            return ""

        tracebacks = (self.traceback(error, tb) for error, tb in errors)
        return "\n".join(["Errors:\n", "\n".join(tracebacks), ""])

    def failures(self, failures):
        if not failures:
            return ""

        tracebacks = (self.traceback(fail, tb) for fail, tb in failures)
        return "\n".join(["Failures:\n", "\n".join(tracebacks), ""])


class Colored(FormatterMixin):
    """
    Wrap a formatter to show colored output.

    """

    ANSI = {
        "reset" : "\x1b[0m",
        "black" : "\x1b[30m",
        "red" : "\x1b[31m",
        "green" : "\x1b[32m",
        "yellow" : "\x1b[33m",
        "blue" : "\x1b[34m",
        "magenta" : "\x1b[35m",
        "cyan" : "\x1b[36m",
        "gray" : "\x1b[37m",
    }

    def __init__(self, formatter):
        self._formatter = formatter

    def __getattr__(self, attr):
        """
        Delegate to the wrapped formatter.

        """

        return getattr(self._formatter, attr)

    def color(self, color, text):
        """
        Color some text in the given ANSI color.

        """

        return "{escape}{text}{reset}".format(
            escape=self.ANSI[color], text=text, reset=self.ANSI["reset"],
        )

    def error(self, example, exc_info):
        return self.color("red", self._formatter.error(example, exc_info))

    def failure(self, example, exc_info):
        return self.color("red", self._formatter.failure(example, exc_info))

    def success(self, example):
        return self.color("green", self._formatter.success(example))

    def traceback(self, example, traceback):
        name = str(example.group) + ": " + str(example)
        colored = "\n".join([self.color("blue", name), traceback])
        return indent(colored, 4 * " ")

    def result_summary(self, result):
        output = self._formatter.result_summary(result)

        if result.wasSuccessful():
            return self.color("green", output)
        return self.color("red", output)


class DotsFormatter(FormatterMixin):
    def __init__(self, stream=sys.stderr):
        self.stream = stream

    def show(self, text):
        """
        Write the text to the stream and flush immediately.

        """

        self.stream.write(text)
        self.stream.flush()

    def enter_context(self, context, depth):
        """
        A new context was entered.

        """

        return ""

    def exit_context(self, depth):
        """
        A context was exited.

        """

        return ""

    def enter_group(self, group):
        """
        A new example group was entered.

        """

        return ""

    def exit_group(self, group):
        """
        The example group was entered.

        """

        return ""

    def result_summary(self, result):
        """
        Return a summary of the results.

        """

        return "{} examples, {} errors, {} failures\n".format(
            result.testsRun, len(result.errors), len(result.failures),
        )

    def timing(self, elapsed):
        """
        Return output on the time taken on the examples run.

        """

        return "Finished in {:.6f} seconds.\n".format(elapsed)

    def error(self, example, exc_info):
        """
        An error was encountered.

        """

        return "E"

    def failure(self, example, exc_info):
        """
        A failure was encountered.

        """

        return "F"

    def skip(self, example, reason):
        """
        A skip was encountered.

        """

        return "S"

    def success(self, example):
        """
        A success was encountered.

        """

        return "."

    def traceback(self, example, traceback):
        """
        Format an example and its traceback.

        """

        return "\n".join((str(example), traceback))


class Verbose(FormatterMixin):
    """
    Show verbose output (including example and group descriptions).

    """

    def __init__(self, formatter):
        self._depth = 1
        self._formatter = formatter

    def __getattr__(self, attr):
        return getattr(self._formatter, attr)

    def enter_context(self, context, depth):
        self._depth = depth + 1
        return indent(context.name + "\n", depth * 4 * " ")

    def exit_context(self, depth):
        self._depth = depth + 1
        return ""

    def enter_group(self, group):
        return "{}\n".format(group)

    def finished(self):
        self.show("\n")

    def error(self, example, exc_info):
        return indent(str(example), self._depth * 4 * " ") + " - ERROR\n"

    def failure(self, example, exc_info):
        return indent(str(example), self._depth * 4 * " ") + " - FAIL\n"

    def success(self, example):
        return indent(str(example), self._depth * 4 * " ") + "\n"

########NEW FILE########
__FILENAME__ = run
"""
The implementation of the Ivoire runner.

"""

import argparse
import runpy
import sys

from ivoire import result
from ivoire.load import load_by_name
from ivoire.transform import ExampleLoader, transform_possible
import ivoire


FORMATTERS = {
    "dots" : result.DotsFormatter,
}


class _ExampleNotRunning(object):
    """
    An error occurred, but no example was running. Mimic an Example object.

    """

    failureException = None
    group = None

    def __str__(self):
        return "<not in example>"


def should_color(when):
    """
    Decide whether to color output.

    """

    if when == "auto":
        return sys.stderr.isatty()
    return when == "always"


def parse(argv=None):
    """
    Parse some arguments using the parser.

    """

    if argv is None:
        argv = sys.argv[1:]

    # Evade http://bugs.python.org/issue9253
    if not argv or argv[0] not in {"run", "transform"}:
        argv = ["run"] + argv

    arguments = _clean(_parser.parse_args(argv))
    return arguments


def _clean(arguments):
    if hasattr(arguments, "color"):
        arguments.color = should_color(arguments.color)
    return arguments


def setup(config):
    """
    Setup the environment for an example run.

    """

    formatter = config.Formatter()

    if config.verbose:
        formatter = result.Verbose(formatter)
    if config.color:
        formatter = result.Colored(formatter)

    current_result = result.ExampleResult(formatter)

    ivoire.current_result = ivoire._manager.result = current_result


def run(config):
    """
    Time to run.

    """

    setup(config)

    if config.exitfirst:
        ivoire.current_result.failfast = True

    ivoire.current_result.startTestRun()

    for spec in config.specs:
        try:
            load_by_name(spec)
        except Exception:
            ivoire.current_result.addError(
                _ExampleNotRunning(), sys.exc_info()
            )

    ivoire.current_result.stopTestRun()

    sys.exit(not ivoire.current_result.wasSuccessful())


def transform(config):
    """
    Run in transform mode.

    """

    if transform_possible:
        ExampleLoader.register()

        args, sys.argv[1:] = sys.argv[1:], config.args
        try:
            return runpy.run_path(config.runner, run_name="__main__")
        finally:
            sys.argv[1:] = args


def main(argv=None):
    arguments = parse(argv)
    arguments.func(arguments)


_parser = argparse.ArgumentParser(description="The Ivoire test runner.")
_subparsers = _parser.add_subparsers()

_run = _subparsers.add_parser(
    "run",
    help="Run Ivoire specs."
)
_run.add_argument(
    "-c", "--color",
    choices=["always", "never", "auto"],
    default="auto",
    dest="color",
    help="Format colored output.",
)
_run.add_argument(
    "-f", "--formatter",
    choices=FORMATTERS,
    default="dots",
    dest="Formatter",
    type=lambda formatter : FORMATTERS[formatter],
    help="Format output with the given formatter.",
)
_run.add_argument(
    "-v", "--verbose",
    action="store_true",
    help="Format verbose output.",
)
_run.add_argument(
    "-x", "--exitfirst",
    action="store_true",
    help="Exit after the first error or failure.",
)
_run.add_argument("specs", nargs="+")
_run.set_defaults(func=run)

_transform = _subparsers.add_parser(
    "transform",
    help="Run an Ivoire spec through another test runner by translating its "
         "source code.",
)
_transform.add_argument(
    "runner",
    help="The command to run the transformed tests with."
)
_transform.add_argument(
    "args",
    nargs=argparse.REMAINDER,
)
_transform.set_defaults(func=transform)

########NEW FILE########
__FILENAME__ = context_manager_spec
from ivoire import context, describe, ContextManager
from ivoire.manager import Context
from ivoire.spec.util import ExampleWithPatch, mock


with describe(ContextManager, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.result = mock.Mock()
        test.manager = ContextManager(test.result)
        test.context = test.manager.create_context("a test context")

    with context(context):
        with it("creates contexts") as test:
            context = test.manager.create_context("a test context")
            test.assertEqual(context, Context("a test context", test.manager))

        with it("is a bit nasty and tries to get __name__s") as test:
            def foo(): pass
            context = test.manager.create_context(foo)
            test.assertEqual(context, Context("foo", test.manager))

    with it("starts off at a global context depth of 0") as test:
        test.assertEqual(test.manager.context_depth, 0)

    with it("enters and exits contexts") as test:
        test.manager.enter(test.context)
        test.result.enterContext.assert_called_once_with(test.context, depth=1)

        test.manager.exit()
        test.result.exitContext.assert_called_once_with(depth=0)

    with it("doesn't call methods if the result doesn't know how") as test:
        del test.result.enterContext, test.result.exitContext

        test.manager.enter(test.context)
        test.manager.exit()
        test.assertFalse(test.result.method_calls)

########NEW FILE########
__FILENAME__ = context_spec
from ivoire import describe
from ivoire.manager import Context
from ivoire.spec.util import ExampleWithPatch, mock


with describe(Context, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.manager = mock.Mock()
        test.context = Context("a test context", test.manager)

    with it("calls its manager when used as a context manager") as test:
        with test.context:
            test.manager.enter.assert_called_once_with(test.context)
        test.manager.exit.assert_called_once_with()

########NEW FILE########
__FILENAME__ = describe_spec
"""
Specification for the ``describe`` function.

The rest of the specification is written as a pyUnit test case (in the
``tests``) directory, since nested ``describe``s are a bit confusing.

"""

from ivoire.standalone import ExampleGroup, describe
from ivoire.spec.util import ExampleWithPatch, mock
import ivoire


with describe(describe, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.describes = mock.Mock(__name__="DescribedThing")
        test.it = describe(test.describes)

    with it("returns the described object's name as its str") as test:
        test.assertEqual(str(test.it), test.it.describes.__name__)

    with it("shows its name and examples as its repr") as test:
        test.assertEqual(
            repr(test.it),
            "<{0.__class__.__name__} examples={0.examples}>".format(test.it),
        )

    with it("sets the described object") as test:
        test.assertEqual(test.it.describes, test.describes)

    with it("passes along failureException to Examples") as test:
        test.it.failureException = mock.Mock()
        test.assertEqual(
            test.it("Example").failureException, test.it.failureException
        )

    with it("leaves the default failureException alone") as test:
        test.assertIsNone(test.it.failureException)
        test.assertIsNotNone(test.it("Example").failureException)

    with it("yields examples when iterating") as test:
        example, another = mock.Mock(), mock.Mock()
        test.it.add_example(example)
        test.it.add_example(another)
        test.assertEqual(list(test.it), [example, another])

    with it("counts its examples") as test:
        test.assertEqual(test.it.countTestCases(), 0)
        test.it.add_example(mock.Mock(**{"countTestCases.return_value" : 3}))
        test.assertEqual(test.it.countTestCases(), 3)

    with it("can have Example specified") as test:
        OtherExample = mock.Mock()
        group = describe(ExampleGroup, Example=OtherExample)
        test.assertEqual(group.Example, OtherExample)

    with it("raises a ValueError if the global result is not set") as test:
        test.patchObject(ivoire, "current_result", None)
        with test.assertRaises(ValueError):
            with test.it:
                pass


with describe(ExampleGroup, Example=ExampleWithPatch) as it:
    with it("is aliased to describe") as test:
        test.assertEqual(describe, ExampleGroup)

########NEW FILE########
__FILENAME__ = example_spec
from ivoire.standalone import Example, describe
from ivoire.spec.util import ExampleWithPatch, mock


with describe(Example, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.name = "the name of the Example"
        test.example_group = mock.Mock()
        test.example = Example(test.name, test.example_group)

    with it("shows its name as its str") as test:
        test.assertEqual(str(test.example), test.name)

    with it("shows its class and name in its repr") as test:
        test.assertEqual(
            repr(test.example),
            "<{0.__class__.__name__}: {0}>".format(test.example),
        )

    with it("knows its group") as test:
        test.assertEqual(test.example.group, test.example_group)

    with it("prevents group from being accidentally set") as test:
        with test.assertRaises(AttributeError):
            test.example.group = 12

    with it("has the same hash for the same name and group") as test:
        same = Example(test.name, test.example_group)
        test.assertEqual(hash(test.example), hash(same))

    with it("has a different hash for other names and groups") as test:
        other = Example(test.name + " something else", test.example_group)
        another = Example(test.name, mock.Mock())

        test.assertNotEqual(hash(test.example), hash(other))
        test.assertNotEqual(hash(test.example), hash(another))

########NEW FILE########
__FILENAME__ = load_spec
from ivoire import describe, load
from ivoire.spec.util import ExampleWithPatch, mock


with describe(load.load_by_name, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.path_exists = test.patchObject(load.os.path, "exists")
        test.load_from_path = test.patchObject(load, "load_from_path")
        test.__import__ = test.patchObject(load, "__import__", create=True)

    with it("loads paths") as test:
        test.path_exists.return_value = True
        load.load_by_name("foo")
        test.load_from_path.assert_called_once_with("foo")

    with it("loads modules") as test:
        test.path_exists.return_value = False
        load.load_by_name("foo")
        test.__import__.assert_called_once_with("foo")


with describe(load.load_from_path, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.isdir = test.patchObject(load.os.path, "isdir")
        test.load_source = test.patchObject(load.imp, "load_source")
        test.path = "foo/bar"

    with it("discovers specs if given a directory") as test:
        test.isdir.return_value = True
        specs = ["foo/bar", "bar/baz", "baz/quux"]
        discover = test.patchObject(load, "discover", return_value=specs)

        load.load_from_path(test.path)

        test.assertEqual(test.load_source.mock_calls, [
            mock.call("bar", "foo/bar"),
            mock.call("baz", "bar/baz"),
            mock.call("quux", "baz/quux"),
        ])

    with it("loads paths") as test:
        test.isdir.return_value = False
        load.load_from_path(test.path)
        test.load_source.assert_called_once_with("bar", test.path)


with describe(load.filter_specs, Example=ExampleWithPatch) as it:
    with it("filters out only specs") as test:
        files = ["a.py", "dir/b.py", "dir/c_spec.py", "d_spec.py"]
        specs = load.filter_specs(files)
        test.assertEqual(specs, ["dir/c_spec.py", "d_spec.py"])


with describe(load.discover, Example=ExampleWithPatch) as it:
    with it("discovers specs") as test:
        subdirs = mock.Mock()
        files, more_files = [mock.Mock()], [mock.Mock(), mock.Mock()]

        tree = [("dir", subdirs, files), ("dir/child", subdirs, more_files)]
        walk = test.patchObject(load.os, "walk", return_value=tree)

        no_filter = mock.Mock(side_effect=lambda paths : paths)

        specs = list(load.discover("a/path", filter_specs=no_filter))

        test.assertEqual(specs, files + more_files)
        test.assertTrue(no_filter.called)
        walk.assert_called_once_with("a/path")

########NEW FILE########
__FILENAME__ = result_spec
from __future__ import unicode_literals
from io import StringIO
import sys

from ivoire import describe, result
from ivoire.compat import indent
from ivoire.spec.util import ExampleWithPatch, mock


def fake_exc_info():
    try:
        raise Exception("Used to construct exc_info")
    except Exception:
        return sys.exc_info()


with describe(result.ExampleResult, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.formatter = mock.Mock()
        test.result = result.ExampleResult(test.formatter)
        test.test = mock.Mock()
        test.exc_info = fake_exc_info()

    def assertShown(test, output):
        test.formatter.show.assert_called_with(output)

    with it("enters groups") as test:
        test.result.enterGroup(test.test.group)
        test.formatter.enter_group.assert_called_once_with(test.test.group)
        assertShown(test, test.formatter.enter_group.return_value)

    with it("exits groups") as test:
        test.result.exitGroup(test.test.group)
        test.formatter.exit_group.assert_called_once_with(test.test.group)
        assertShown(test, test.formatter.exit_group.return_value)

    with it("shows successes") as test:
        test.result.addSuccess(test.test)
        test.formatter.success.assert_called_once_with(test.test)
        assertShown(test, test.formatter.success.return_value)

    with it("shows errors") as test:
        test.result.addError(test.test, test.exc_info)
        test.formatter.error.assert_called_once_with(test.test, test.exc_info)
        assertShown(test, test.formatter.error.return_value)

    with it("shows failures") as test:
        test.result.addFailure(test.test, test.exc_info)
        test.formatter.failure.assert_called_once_with(
            test.test, test.exc_info
        )
        assertShown(test, test.formatter.failure.return_value)

    with it("shows skips") as test:
        test.result.addSkip(test.test, "a reason")
        test.formatter.skip.assert_called_once_with(test.test, "a reason")
        assertShown(test, test.formatter.skip.return_value)

    with it("shows statistics and non-successes") as test:
        test.result.startTestRun()
        test.result.stopTestRun()

        elapsed = test.result.elapsed

        test.formatter.assert_has_calls([
            mock.call.finished(),
            mock.call.errors(test.result.errors),
            mock.call.show(test.formatter.errors.return_value),
            mock.call.failures(test.result.failures),
            mock.call.show(test.formatter.failures.return_value),
            mock.call.statistics(elapsed=elapsed, result=test.result),
            mock.call.show(test.formatter.statistics.return_value),
        ])

    with it("times the example run") as test:
        start, end = [1.234567, 8.9101112]
        test.patchObject(result.time, "time", side_effect=[start, end])

        test.result.startTestRun()
        test.result.stopTestRun()

        test.assertEqual(test.result.elapsed, end - start)


with describe(result.Verbose, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.exc_info = mock.Mock()
        test.formatter = mock.Mock()
        test.result = mock.Mock()
        test.test = mock.Mock()
        test.verbose = result.Verbose(test.formatter)

    with it("delegates to the formatter") as test:
        test.assertEqual(test.verbose.foo, test.formatter.foo)

    with it("finishes with a newline") as test:
        test.verbose.finished()
        test.formatter.show.assert_called_once_with("\n")

    with it("shows group names when entered") as test:
        test.assertEqual(
            test.verbose.enter_group(test.test.group),
            "{}\n".format(test.test.group)
        )

    with it("formats successes") as test:
        test.assertEqual(
            test.verbose.success(test.test), "    {}\n".format(test.test)
        )

    with it("formats errors") as test:
        test.assertEqual(
            test.verbose.error(test.test, test.exc_info),
            "    {} - ERROR\n".format(test.test)
        )

    with it("formats failures") as test:
        test.assertEqual(
            test.verbose.failure(test.test, test.exc_info),
            "    {} - FAIL\n".format(test.test)
        )


with describe(result.DotsFormatter, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.elapsed = 1.23456789
        test.result = mock.Mock()
        test.test = mock.Mock()
        test.exc_info = fake_exc_info()

        test.stream = mock.Mock()
        test.formatter = result.DotsFormatter(test.stream)

    with it("does not format anything for entering a group") as test:
        test.assertFalse(test.formatter.enter_group(test.test.group))

    with it("does not format anything for exiting a group") as test:
        test.assertFalse(test.formatter.exit_group(test.test.group))

    with it("formats . for successes") as test:
        test.assertEqual(test.formatter.success(test.test), ".")

    with it("formats E for errors") as test:
        test.assertEqual(test.formatter.error(test.test, test.exc_info), "E")

    with it("formats F for failures") as test:
        test.assertEqual(test.formatter.failure(test.test, test.exc_info), "F")

    with it("formats S for skips") as test:
        test.assertEqual(test.formatter.skip(test.test, test.exc_info), "S")

    with it("formats a summary message") as test:
        test.result.testsRun = 20
        test.result.errors = range(8)
        test.result.failures = range(2)

        test.assertEqual(
            test.formatter.result_summary(test.result),
            "20 examples, 8 errors, 2 failures\n",
        )

    with it("formats a timing message") as test:
        test.assertEqual(
            test.formatter.timing(test.elapsed),
            "Finished in {:.6f} seconds.\n".format(test.elapsed),
        )

    with it("formats tracebacks") as test:
        example = mock.MagicMock()
        example.__str__.return_value = "Example"
        traceback = "The\nTraceback\n"

        test.assertEqual(
            test.formatter.traceback(example, traceback),
            "\n".join([str(example), traceback])
        )


with describe(result.DotsFormatter.show, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.stream = StringIO()
        test.formatter = result.DotsFormatter(test.stream)

    with it("writes to stderr by default") as test:
        test.assertEqual(result.DotsFormatter().stream, sys.stderr)

    with it("writes and flushes") as test:
        test.stream.flush = mock.Mock()
        test.formatter.show("hello\n")
        test.assertEqual(test.stream.getvalue(), "hello\n")
        test.assertTrue(test.stream.flush.called)

########NEW FILE########
__FILENAME__ = run_spec
from ivoire import describe, result, run
from ivoire.spec.util import ExampleWithPatch, mock
import ivoire


with describe(run.parse, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.specs = ["a_spec"]

    with it("sets reasonable defaults") as test:
        should_color = test.patchObject(run, "should_color")
        arguments = run.parse(test.specs)
        test.assertEqual(vars(arguments), {
            "Formatter" : result.DotsFormatter,
            "color" : should_color.return_value,
            "exitfirst" : False,
            "specs" : test.specs,
            "func" : run.run,
            "verbose" : False,
        })
        should_color.assert_called_once_with("auto")

    with it("can exitfirst") as test:
        arguments = run.parse(["--exitfirst"] + test.specs)
        test.assertTrue(arguments.exitfirst)

        arguments = run.parse(["-x"] + test.specs)
        test.assertTrue(arguments.exitfirst)

    with it("can be verbose") as test:
        arguments = run.parse(["--verbose"] + test.specs)
        test.assertTrue(arguments.verbose)

        arguments = run.parse(["-v"] + test.specs)
        test.assertTrue(arguments.verbose)

    with it("can transform") as test:
        arguments = run.parse(["transform", "foo", "bar"])
        test.assertEqual(vars(arguments), {
            "runner" : "foo",
            "args" : ["bar"],
            "func" : run.transform,
        })

    with it("runs run on empty args") as test:
        arguments = run.parse()
        test.assertEqual(arguments.func, run.run)


with describe(run.should_color, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.stderr = test.patchObject(run.sys, "stderr")

    with it("colors whenever stderr is a tty") as test:
        test.stderr.isatty.return_value = True
        test.assertTrue(run.should_color("auto"))

    with it("doesn't color otherwise") as test:
        test.stderr.isatty.return_value = False
        test.assertFalse(run.should_color("auto"))


with describe(run.setup, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.patchObject(ivoire, "current_result", None)
        test.config = mock.Mock(verbose=False, color=False)

    with it("sets a result") as test:
        test.assertIsNone(ivoire.current_result)
        run.setup(test.config)
        test.assertIsNotNone(ivoire.current_result)

    with it("makes a plain Formatter if color and verbose are False") as test:
        run.setup(test.config)
        test.assertEqual(
            ivoire.current_result.formatter, test.config.Formatter.return_value
        )

    with it("makes a verbose Formatter if verbose is True") as test:
        test.config.verbose = True
        run.setup(test.config)
        test.assertIsInstance(ivoire.current_result.formatter, result.Verbose)

    with it("makes a colored Formatter if color is True") as test:
        test.config.color = True
        run.setup(test.config)
        test.assertIsInstance(ivoire.current_result.formatter, result.Colored)


with describe(run.run, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.config = mock.Mock(specs=[])
        test.load_by_name = test.patchObject(run, "load_by_name")
        test.result = test.patch("ivoire.current_result", failfast=False)
        test.setup = test.patchObject(run, "setup")
        test.exit = test.patchObject(run.sys, "exit")

    with it("sets up the environment") as test:
        run.run(test.config)
        test.setup.assert_called_once_with(test.config)

    with it("sets failfast on the result") as test:
        test.assertFalse(test.result.failfast)
        test.config.exitfirst = True
        run.run(test.config)
        test.assertTrue(test.result.failfast)

    with it("starts and stops a test run") as test:
        run.run(test.config)
        test.result.startTestRun.assert_called_once_with()
        test.result.stopTestRun.assert_called_once_with()

    with it("loads specs") as test:
        test.config.specs = [mock.Mock(), mock.Mock(), mock.Mock()]
        run.run(test.config)
        test.assertEqual(
            test.load_by_name.mock_calls,
            [mock.call(spec) for spec in test.config.specs],
        )

    with it("succeeds with status code 0") as test:
        test.result.wasSuccessful.return_value = True
        run.run(test.config)
        test.exit.assert_called_once_with(0)

    with it("fails with status code 1") as test:
        test.result.wasSuccessful.return_value = False
        run.run(test.config)
        test.exit.assert_called_once_with(1)

    with it("logs an error to the result if an import fails") as test:
        test.config.specs = ["does.not.exist"]
        test.load_by_name.side_effect = IndexError

        run.run(test.config)

        (example, traceback), _ = test.result.addError.call_args
        test.assertEqual(str(example), "<not in example>")
        test.assertEqual(traceback[0], IndexError)


with describe(run.main, Example=ExampleWithPatch) as it:
    with it("runs the correct func with parsed args") as test:
        parse = test.patchObject(run, "parse")
        argv = mock.Mock()

        run.main(argv)

        parse.assert_called_once_with(argv)
        parse.return_value.func.assert_called_once_with(parse.return_value)


with describe(run.transform, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.patchObject(run, "transform_possible", True)
        test.ExampleLoader = test.patchObject(run, "ExampleLoader")
        test.config = mock.Mock(runner="runner", specs=["a/spec.py"], args=[])
        test.run_path = test.patchObject(run.runpy, "run_path")

    with it("sets up the path hook") as test:
        run.transform(test.config)
        test.ExampleLoader.register.assert_called_once_with()

    with it("runs the script") as test:
        run.transform(test.config)
        test.run_path.assert_called_once_with(
            test.config.runner, run_name="__main__",
        )

    with it("cleans and resets sys.argv") as test:
        test.config.args = ["foo", "bar", "baz"]
        argv = test.patchObject(run.sys, "argv", ["spam", "eggs"])

        # argv was set immediately before run_path
        test.run_path.side_effect = lambda *a, **k : (
            test.assertEqual(argv[1:], test.config.args)
        )
        run.transform(test.config)

        # ... and was restored afterwards
        test.assertEqual(argv[1:], ["eggs"])

########NEW FILE########
__FILENAME__ = transform_spec
from __future__ import print_function
from textwrap import dedent
from unittest import TestCase
import ast
import copy

from ivoire import describe, transform
from ivoire.spec.util import ExampleWithPatch, mock


def dump(node):  # pragma: no cover
    return(dedent("""
    --- Dumping Node ---

    {}

    --- End ---
    """.format(ast.dump(node))))


with describe(transform.ExampleTransformer, Example=ExampleWithPatch) as it:
    @it.before
    def before(test):
        test.transformer = transform.ExampleTransformer()

    def execute(test, source):
        test.globals, test.locals = {}, {}
        test.node = ast.parse(dedent(source))
        test.transformed = test.transformer.transform(test.node)
        compiled = compile(test.transformed, "<testing transform>", "exec")

        try:
            exec(compiled, test.globals, test.locals)
        except Exception:  # pragma: no cover
            print(dump(test.transformed))
            raise

    def assertNotTransformed(test, source):
        node = ast.parse(dedent(source))
        transformed = test.transformer.transform(copy.deepcopy(node))
        # TODO: Ugly! Fix me please. See http://bugs.python.org/issue15987
        test.assertEqual(ast.dump(node), ast.dump(transformed))

    with it("fixes missing line numbers") as test:
        fix = test.patchObject(transform.ast, "fix_missing_locations")
        node = ast.Pass()
        test.transformer.transform(node)
        fix.assert_called_once_with(node)

    with it("transforms ivoire imports to unittest imports") as test:
        execute(test, "from ivoire import describe")
        test.assertEqual(test.locals, {"TestCase" : TestCase})

    with it("leaves other imports alone") as test:
        assertNotTransformed(test, "from textwrap import dedent")

    with it("transforms uses of describe to TestCases") as test:
        test.skip_if(
            not transform.transform_possible,
            "Transform not available on this version."
        )

        execute(test, """
            from ivoire import describe
            with describe(next) as it:
                with it("returns the next element") as test:
                    test.i = [1, 2, 3]
                    test.assertEqual(next(test.i), 1)
        """)

        TestNext = test.locals["TestNext"]
        test = TestNext("test_it_returns_the_next_element")
        test.run()
        test.assertEqual(test.i, [1, 2, 3])

    with it("leaves other context managers alone") as test:
        test.skip_if(
            not transform.transform_possible,
            "Transform not available on this version."
        )

        assertNotTransformed(test, """
            from warnings import catchwarnings
            with catchwarnings() as thing:
                with catchwarnings():
                    pass
        """)

########NEW FILE########
__FILENAME__ = util
from ivoire import Example
from ivoire.tests.util import _cleanUpPatch, mock


class ExampleWithPatch(Example):
    patch = _cleanUpPatch(mock.patch)
    patchDict = _cleanUpPatch(mock.patch.dict)
    patchObject = _cleanUpPatch(mock.patch.object)

########NEW FILE########
__FILENAME__ = standalone
from __future__ import unicode_literals
from unittest import SkipTest, TestCase, TestResult
import sys

import ivoire


class _ShouldStop(Exception):
    pass


# TestCase requires the name of an existing method on creation in 2.X because 
# of the way the default implementation of .run() works. So make it shut up.
_MAKE_UNITTEST_SHUT_UP = "__init__"


class Example(TestCase):
    """
    An ``Example`` is the smallest unit in a specification.

    """

    def __init__(self, name, group, before=None, after=None):
        super(Example, self).__init__(_MAKE_UNITTEST_SHUT_UP)
        self.__after = after
        self.__before = before
        self.__group = group
        self.__name = name
        self.__result = group.result

    def __enter__(self):
        """
        Run the example.

        """

        self.__result.startTest(self)

        if self.__before is not None:
            try:
                self.__before(self)
            except Exception:
                self.__result.addError(self, sys.exc_info())
                self.__result.stopTest(self)
                raise _ShouldStop

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Finish running the example, logging any raised exceptions as results.

        """
        if exc_type is None:
            self.__result.addSuccess(self)
        elif exc_type == KeyboardInterrupt:
            return False
        elif exc_type == SkipTest:
            self.__result.addSkip(self, str(exc_value))
        elif exc_type == self.failureException:
            self.__result.addFailure(self, (exc_type, exc_value, traceback))
        else:
            self.__result.addError(self, (exc_type, exc_value, traceback))

        if self.__after is not None:
            self.__after(self)

        self.doCleanups()
        self.__result.stopTest(self)

        if self.__result.shouldStop:
            raise _ShouldStop
        return True

    def __hash__(self):
        return hash((self.__class__, self.group, self.__name))

    def __repr__(self):
        return "<{self.__class__.__name__}: {self}>".format(self=self)

    def __str__(self):
        return self.__name

    @property
    def group(self):
        return self.__group

    def skip_if(self, condition, reason):
        """
        Skip the example if the condition is set, with the provided reason.

        """

        if condition:
            raise SkipTest(reason)


class ExampleGroup(object):
    """
    ``ExampleGroup``s group together a number of ``Example``s.

    """

    _before = _after = None
    failureException = None
    result = None

    def __init__(self, describes, Example=Example):
        self.Example = Example
        self.describes = describes
        self.examples = []

    def __enter__(self):
        """
        Begin running the group.

        """

        self.result = _get_result()

        enterGroup = getattr(self.result, "enterGroup", None)
        if enterGroup is not None:
            enterGroup(self)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        exitGroup = getattr(self.result, "exitGroup", None)
        if exitGroup is not None:
            exitGroup(self)

        if exc_type == _ShouldStop:
            return True

    def __iter__(self):
        return iter(self.examples)

    def __repr__(self):
        return "<{self.__class__.__name__} examples={self.examples}>".format(
            self=self
        )

    def __str__(self):
        return self.describes.__name__

    def __call__(self, name):
        """
        Construct and return a new ``Example``.

        """

        example = self.Example(
            name=name, group=self, before=self._before, after=self._after,
        )

        if self.failureException is not None:
            example.failureException = self.failureException

        self.add_example(example)
        return example

    def add_example(self, example):
        """
        Add an existing ``Example`` to this group.

        """

        self.examples.append(example)

    def before(self, fn):
        """
        Run the given function before each example is run.

        Note: In standalone mode, it's not possible to skip a context block,
        so if a ``before`` function errors, the exception is propagated all the
        way up to the ``ExampleGroup`` (meaning the rest of the examples *will
        not run at all*, nor will they show up in the result output).

        """

        self._before = fn

    def after(self, fn):
        """
        Run the given function after each example is run.

        """

        self._after = fn

    def countTestCases(self):
        return sum(example.countTestCases() for example in self)


describe = ExampleGroup


def _get_result():
    """
    Find the global result object.

    """

    result = ivoire.current_result
    if result is None:
        raise ValueError(
            "ivoire.current_result must be set to a TestResult before "
            "execution starts!"
        )
    return result

########NEW FILE########
__FILENAME__ = test_result
from __future__ import unicode_literals
from unittest import TestCase

from ivoire import result
from ivoire.compat import indent
from ivoire.tests.util import PatchMixin, mock


class TestFormatterMixin(TestCase, PatchMixin):
    class Formatter(mock.Mock, result.FormatterMixin):
        pass

    def setUp(self):
        self.formatter = self.Formatter()

    def test_finished(self):
        self.formatter.show = mock.Mock()
        self.formatter.finished()
        self.formatter.show.assert_called_once_with("\n\n")

    def test_errors(self):
        self.formatter.traceback.side_effect = ["a\nb\n", "c\nd\n"]
        errors = [(mock.Mock(), mock.Mock()), (mock.Mock(), mock.Mock())]
        self.assertEqual(
            self.formatter.errors(errors), "Errors:\n\na\nb\n\nc\nd\n\n"
        )

    def test_failures(self):
        self.formatter.traceback.side_effect = ["a\nb\n", "c\nd\n"]
        failures = [(mock.Mock(), mock.Mock()), (mock.Mock(), mock.Mock())]
        self.assertEqual(
            self.formatter.failures(failures), "Failures:\n\na\nb\n\nc\nd\n\n"
        )

    def test_return_nothing_if_no_errors(self):
        self.assertEqual("", self.formatter.errors([]))
        self.assertFalse("", self.formatter.failures([]))

    def test_statistics(self):
        elapsed, result = mock.Mock(), mock.Mock()
        timing_output = self.formatter.timing.return_value = "timing\n"
        result_output = self.formatter.result_summary.return_value = "result\n"

        stats = self.formatter.statistics(elapsed=elapsed, result=result)
        self.assertEqual(stats, "\n".join([timing_output, result_output]))


class TestColored(TestCase, PatchMixin):
    def setUp(self):
        self.exc_info = mock.Mock()
        self.formatter = mock.Mock()
        self.result = mock.Mock()
        self.test = mock.Mock()
        self.colored = result.Colored(self.formatter)

    def test_it_delegates_to_the_formatter(self):
        self.assertEqual(self.colored.foo, self.formatter.foo)

    def test_it_can_color_things(self):
        self.assertEqual(
            self.colored.color("green", "hello"),
            self.colored.ANSI["green"] + "hello" + self.colored.ANSI["reset"],
        )

    def test_it_colors_successes_green(self):
        self.formatter.success.return_value = "S"
        self.assertEqual(
            self.colored.success(self.test), self.colored.color("green", "S"),
        )

    def test_it_colors_failures_red(self):
        self.formatter.failure.return_value = "F"
        self.assertEqual(
            self.colored.failure(self.test, self.exc_info),
            self.colored.color("red", "F"),
        )

    def test_it_colors_errors_red(self):
        self.formatter.error.return_value = "E"
        self.assertEqual(
            self.colored.error(self.test, self.exc_info),
            self.colored.color("red", "E"),
        )

    def test_it_colors_result_green_when_successful(self):
        self.result.wasSuccessful.return_value = True
        self.formatter.result_summary.return_value = "results"
        self.assertEqual(
            self.colored.result_summary(self.result),
            self.colored.color("green", "results"),
        )

    def test_it_colors_result_red_when_unsuccessful(self):
        self.result.wasSuccessful.return_value = False
        self.formatter.result_summary.return_value = "results"
        self.assertEqual(
            self.colored.result_summary(self.result),
            self.colored.color("red", "results"),
        )

    def test_it_colors_example_names_blue_in_tracebacks(self):
        example = mock.MagicMock()
        example.__str__.return_value = "Example"
        example.group.__str__.return_value = "Thing"
        traceback = "The\nTraceback\n"

        name = self.colored.color("blue", "Thing: Example")
        self.assertEqual(
            self.colored.traceback(example, traceback),
            indent(name + "\n" + traceback, 4 * " "),
        )

########NEW FILE########
__FILENAME__ = test_standalone
"""
Test the standalone running of Ivoire examples.

A **warning** about testing in this module: Testing Ivoire Examples means
testing a thing that is swallowing (and recording) *all* exceptions. Make sure
all of your assertions are outside of example blocks so that they are handled
by the surrounding test case.

"""

from __future__ import unicode_literals
from unittest import TestCase
import sys

from ivoire.standalone import describe
from ivoire.tests.util import PatchMixin, mock


class TestDescribeTests(TestCase, PatchMixin):
    def setUp(self):
        self.result = self.patch("ivoire.current_result", shouldStop=False)
        self.describes = describe
        self.it = describe(self.describes)

    def test_it_adds_an_example(self):
        with self.it as it:
            with it("does a thing") as test:
                pass
        self.assertEqual(it.examples, [test])

    def test_it_can_pass(self):
        with self.it as it:
            with it("does a thing") as test:
                pass

        self.result.assert_has_calls([
            mock.call.enterGroup(self.it),
            mock.call.startTest(test),
            mock.call.addSuccess(test),
            mock.call.stopTest(test),
            mock.call.exitGroup(self.it),
        ])

    def test_it_can_fail(self):
        with self.it as it:
            with it("does a thing") as test:
                try:
                    test.fail()
                except Exception:
                    exc_info = sys.exc_info()
                    raise

        self.result.assert_has_calls([
            mock.call.enterGroup(self.it),
            mock.call.startTest(test),
            mock.call.addFailure(test, exc_info),
            mock.call.stopTest(test),
            mock.call.exitGroup(self.it),
        ])

    def test_it_can_error(self):
        with self.it as it:
            with it("does a thing") as test:
                try:
                    raise IndexError
                except IndexError:
                    exc_info = sys.exc_info()
                    raise

        self.result.assert_has_calls([
            mock.call.enterGroup(self.it),
            mock.call.startTest(test),
            mock.call.addError(test, exc_info),
            mock.call.stopTest(test),
            mock.call.exitGroup(self.it),
        ])

    def test_it_does_not_swallow_KeyboardInterrupts(self):
        with self.assertRaises(KeyboardInterrupt):
            with self.it as it:
                with it("does a thing") as test:
                    raise KeyboardInterrupt

    def test_it_exits_the_group_if_begin_errors(self):
        self.ran_test = False

        with self.it as it:
            @it.before
            def before(test):
                raise RuntimeError("Buggy before.")

            example = it("should not be run")
            with example as test:
                self.ran_test = True

        self.assertEqual(self.result.mock_calls, [
            mock.call.enterGroup(self.it),
            mock.call.startTest(example),
            mock.call.addError(example, mock.ANY),  # traceback object
            mock.call.stopTest(example),
            mock.call.exitGroup(self.it),
        ])
        self.assertFalse(self.ran_test)

    def test_it_runs_befores(self):
        with self.it as it:
            @it.before
            def before(test):
                test.foo = 12

            with it("should have set foo") as test:
                foo = test.foo
        self.assertEqual(foo, 12)

    # XXX: There's a few more cases here that should be tested

    def test_it_runs_afters(self):
        self.foo = None

        with self.it as it:
            @it.after
            def after(test):
                self.foo = 12

            with it("should have set foo after") as test:
                foo = self.foo

        self.assertEqual(foo, None)
        self.assertEqual(self.foo, 12)

    def test_it_runs_cleanups(self):
        with self.it as it:
            with it("does a thing") as test:
                doCleanups = self.patchObject(test, "doCleanups")
        self.assertTrue(doCleanups.called)

    def test_it_respects_shouldStop(self):
        with self.it as it:
            with it("does a thing") as test:
                self.result.shouldStop = True
            self.fail("should have stopped already!")  # pragma: no cover

    def test_it_can_skip(self):
        with self.it as it:
            with it("should skip this test") as test:
                test.skip_if(False, reason="A bad one")
                test.skip_if(True, reason="A good one")
                test.fail("Should have skipped!")

        self.assertEqual(self.result.method_calls, [
            mock.call.enterGroup(self.it),
            mock.call.startTest(test),
            mock.call.addSkip(test, "A good one"),
            mock.call.stopTest(test),
            mock.call.exitGroup(self.it),
        ])

    def test_it_only_calls_enterGroup_if_result_knows_how(self):
        del self.result.enterGroup

        with self.it as it:
            pass

        self.assertEqual(
            self.result.method_calls, [mock.call.exitGroup(self.it)],
        )

    def test_it_only_calls_exitGroup_if_result_knows_how(self):
        del self.result.exitGroup

        with self.it as it:
            pass

        self.assertEqual(
            self.result.method_calls, [mock.call.enterGroup(self.it)],
        )

########NEW FILE########
__FILENAME__ = test_transform
from __future__ import print_function
from textwrap import dedent
from unittest import TestCase, skipIf
import ast

from ivoire import transform
from ivoire.tests.util import PatchMixin, mock


class TestRegistration(TestCase, PatchMixin):
    def setUp(self):
        self.FileFinder = self.patchObject(transform, "FileFinder")
        self.hooks = ()
        self.path_hooks = self.patchObject(
            transform.sys, "path_hooks", list(self.hooks)
        )

    def test_it_registers_a_file_finder(self):
        transform.ExampleLoader.register()
        self.assertEqual(
            self.path_hooks,
            list(self.hooks) + [self.FileFinder.path_hook.return_value],
        )
        self.FileFinder.path_hook.assert_called_once_with(
            (transform.ExampleLoader, ["_spec.py"]),
        )

    def test_it_unregisters_the_file_finder(self):
        transform.ExampleLoader.register()
        transform.ExampleLoader.unregister()
        self.assertEqual(self.path_hooks, list(self.hooks))


class TestExampleLoader(TestCase, PatchMixin):
    @skipIf(
        not transform.transform_possible,
        "Transformation isn't supported yet on this version.",
    )
    def test_it_transforms_the_source(self):
        trans = self.patchObject(transform.ExampleTransformer, "transform")
        parse = self.patchObject(ast, "parse")
        compile = self.patchObject(transform, "compile", create=True)

        fullname, path = mock.Mock(), mock.Mock()
        source, path = mock.Mock(), mock.Mock()

        loader = transform.ExampleLoader(fullname, path)
        code = loader.source_to_code(source, path)

        self.assertEqual(code, compile.return_value)
        compile.assert_called_once_with(
            trans.return_value, path, "exec", dont_inherit=True
        )
        trans.assert_called_once_with(parse.return_value)

########NEW FILE########
__FILENAME__ = util
from functools import wraps

try:
    from unittest import mock
except ImportError:
    import mock


def _cleanUpPatch(fn):
    @wraps(fn)
    def cleaned(self, *args, **kwargs):
        patch = fn(*args, **kwargs)
        self.addCleanup(patch.stop)
        return patch.start()
    return cleaned


class PatchMixin(object):
    patch = _cleanUpPatch(mock.patch)
    patchDict = _cleanUpPatch(mock.patch.dict)
    patchObject = _cleanUpPatch(mock.patch.object)

########NEW FILE########
__FILENAME__ = transform
import ast
import sys


from ivoire.compat import FileFinder, SourceFileLoader, transform_possible


class ExampleTransformer(ast.NodeTransformer):
    """
    Transform a module that uses Ivoire into one that uses unittest.

    This is highly experimental, and certain to have bugs (including some
    known ones). Right now it is highly strict and will not properly transform
    all possibilities. File issues if you find things that are wrong.

    Note: None of the methods on this object are public API other than the
    ``transform`` method.

    """

    def transform(self, node):
        transformed = self.visit(node)
        ast.fix_missing_locations(transformed)
        return transformed

    def visit_ImportFrom(self, node):
        if node.module == "ivoire":
            node.module = "unittest"
            node.names[0].name = "TestCase"
        return node

    def visit_With(self, node):
        """
        with describe(thing) as it:
            ...

             |
             v

        class TestThing(TestCase):
            ...

        """

        withitem, = node.items
        context = withitem.context_expr

        if context.func.id == "describe":
            describes = context.args[0].id
            example_group_name = withitem.optional_vars.id
            return self.transform_describe(node, describes, example_group_name)
        else:
            return node

    def transform_describe(self, node, describes, context_variable):
        """
        Transform a describe node into a ``TestCase``.

        ``node`` is the node object.
        ``describes`` is the name of the object being described.
        ``context_variable`` is the name bound in the context manager (usually
        "it").

        """

        body = self.transform_describe_body(node.body, context_variable)
        return ast.ClassDef(
            name="Test" + describes.title(),
            bases=[ast.Name(id="TestCase", ctx=ast.Load())],
            keywords=[],
            starargs=None,
            kwargs=None,
            body=list(body),
            decorator_list=[],
        )

    def transform_describe_body(self, body, group_var):
        """
        Transform the body of an ``ExampleGroup``.

        ``body`` is the body.
        ``group_var`` is the name bound to the example group in the context
        manager (usually "it").

        """

        for node in body:
            withitem, = node.items
            context_expr = withitem.context_expr

            name = context_expr.args[0].s
            context_var = withitem.optional_vars.id

            yield self.transform_example(node, name, context_var, group_var)

    def transform_example(self, node, name, context_variable, group_variable):
        """
        Transform an example node into a test method.

        Returns the unchanged node if it wasn't an ``Example``.

        ``node`` is the node object.
        ``name`` is the name of the example being described.
        ``context_variable`` is the name bound in the context manager (usually
        "test").
        ``group_variable`` is the name bound in the surrounding example group's
        context manager (usually "it").

        """

        test_name = "_".join(["test", group_variable] + name.split())
        body = self.transform_example_body(node.body, context_variable)

        return ast.FunctionDef(
            name=test_name,
            args=self.takes_only_self(),
            body=list(body),
            decorator_list=[],
        )

    def transform_example_body(self, body, context_variable):
        """
        Transform the body of an ``Example`` into the body of a method.

        Replaces instances of ``context_variable`` to refer to ``self``.

        ``body`` is the body.
        ``context_variable`` is the name bound in the surrounding context
        manager to the example (usually "test").

        """

        for node in body:
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    if child.id == context_variable:
                        child.id = "self"
            yield node


    def takes_only_self(self):
        """
        Return an argument list node that takes only ``self``.

        """

        return ast.arguments(
            args=[ast.arg(arg="self")],
            defaults=[],
            kw_defaults=[],
            kwonlyargs=[],
        )


class ExampleLoader(SourceFileLoader):

    suffix = "_spec.py"

    @classmethod
    def register(cls):
        """
        Register the path hook.

        """

        cls._finder = FileFinder.path_hook((cls, [cls.suffix]))
        sys.path_hooks.append(cls._finder)

    @classmethod
    def unregister(cls):
        """
        Unregister the path hook.

        """

        sys.path_hooks.remove(cls._finder)

    def source_to_code(self, source_bytes, source_path):
        """
        Transform the source code, then return the code object.

        """

        node = ast.parse(source_bytes)
        transformed = ExampleTransformer().transform(node)
        return compile(transformed, source_path, "exec", dont_inherit=True)

########NEW FILE########
