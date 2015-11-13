__FILENAME__ = cli
import inspect
import sys
import os

import nose
import six

from spec.utils import class_members


#
# Custom selection logic
#


def private(obj):
    return obj.__name__.startswith('_') or \
           getattr(obj, '_spec__is_private', False)


class SpecSelector(nose.selector.Selector):
    def __init__(self, *args, **kwargs):
        super(SpecSelector, self).__init__(*args, **kwargs)
        self._valid_modules = []
        # Handle --tests=
        self._valid_named_modules = map(os.path.abspath, self.config.testNames)
        self._valid_classes = []

    def wantDirectory(self, dirname):
        # Given a sane root such as tests/, we want everything.
        # Some other mechanism already allows for hidden directories using a _
        # prefix, e.g. _support.
        return True

    def wantFile(self, filename):
        # Same as with directories -- anything unhidden goes.
        # Also skip .pyc files
        is_pyc = os.path.splitext(filename)[1] == '.pyc'
        is_hidden = os.path.basename(filename).startswith('_')
        return not (is_pyc or is_hidden)

    def wantModule(self, module):
        # You guessed it -- if it's being picked up as a module, we want it.
        # However, also store it so we can tell apart "native" class/func
        # objects from ones imported *into* test modules.
        self._valid_modules.append(module)
        return True

    def wantFunction(self, function):
        # Only use locally-defined functions
        local = inspect.getmodule(function) in self._valid_modules
        # And not ones which are conventionally private
        good = local and not private(function)
        return good

    def registerGoodClass(self, class_):
        """
        Internal bookkeeping to handle nested classes
        """
        # Class itself added to "good" list
        self._valid_classes.append(class_)
        # Recurse into any inner classes
        for name, cls in class_members(class_):
            if self.isValidClass(cls):
                self.registerGoodClass(cls)

    def isValidClass(self, class_):
        """
        Needs to be its own method so it can be called from both wantClass and
        registerGoodClass.
        """
        module = inspect.getmodule(class_)
        valid = (
            module in self._valid_modules
            or module.__file__ in self._valid_named_modules
        )
        return valid and not private(class_)

    def wantClass(self, class_):
        # As with modules, track the valid ones for use in method testing.
        # Valid meaning defined locally in a valid module, and not private.
        good = self.isValidClass(class_)
        if good:
            self.registerGoodClass(class_)
        return good

    def wantMethod(self, method):
        if six.PY3:
            cls = method.__self__.__class__
        else:
            # Short-circuit on odd results
            if not hasattr(method, 'im_class'):
                return False
            cls = method.im_class

        # As with functions, we want only items defined on also-valid
        # containers (classes), and only ones not conventionally private.
        valid_class = cls in self._valid_classes
        # And ones only defined local to the class in question, not inherited
        # from its parents. Also handle oddball 'type' cases.
        if cls is type:
            return False
        # Handle 'contributed' methods not defined on class itself
        if not hasattr(cls, method.__name__):
            return False
        # Only test for mro on new-style classes. (inner old-style classes lack
        # it.)
        if hasattr(cls, 'mro') and callable(cls.mro):
            candidates = list(reversed(cls.mro()))[:-1]
            for candidate in candidates:
                if hasattr(candidate, method.__name__):
                    return False
        ok = valid_class and not private(method)
        return ok


# Plugin for loading selector & implementing some custom hooks too
# (such as appending more test cases from gathered classes)
class CustomSelector(nose.plugins.Plugin):
    name = "specselector"

    def configure(self, options, conf):
        nose.plugins.Plugin.configure(self, options, conf)

    def prepareTestLoader(self, loader):
        loader.selector = SpecSelector(loader.config)
        self.loader = loader

    def loadTestsFromTestClass(self, cls):
        """
        Manually examine test class for inner classes.
        """
        results = []
        for name, subclass in class_members(cls):
            results.extend(self.loader.loadTestsFromTestClass(subclass))
        return results


def args_contains(options):
    for opt in options:
        for arg in sys.argv[1:]:
            if arg.startswith(opt):
                return True
    return False


# Nose invocation
def main():
    defaults = [
        # Don't capture stdout
        '--nocapture',
        # Use the spec plugin
        '--with-specplugin', '--with-specselector',
        # Enable useful asserts
        '--detailed-errors',
    ]
    # Set up default test location ('tests/') and custom selector,
    # only if user isn't giving us specific options of their own.
    # FIXME: see if there's a way to do it post-optparse, this is brittle.
    good = not args_contains("--match -m -i --include -e --exclude".split())
    plugins = []
    if good and os.path.isdir('tests'):
        plugins = [CustomSelector()]
        if not args_contains(['--tests', '-w', '--where']):
            defaults.append("--where=tests")
    nose.core.main(
        argv=['nosetests'] + defaults + sys.argv[1:],
        addplugins=plugins
    )

########NEW FILE########
__FILENAME__ = plugin
import doctest
import os
import re
import types
import time
import unittest
from functools import partial
# Python 2.7: _WritelnDecorator moved.
try:
    from unittest import _WritelnDecorator
except ImportError:
    from unittest.runner import _WritelnDecorator

import six
from six import StringIO as IO
import nose
from nose.plugins import Plugin
# Python 2.7: nose uses unittest's builtin SkipTest class
try:
    SkipTest = unittest.case.SkipTest
except AttributeError:
    SkipTest = nose.SkipTest

# Use custom-as-of-nose-1.3 format_exception which bridges some annoying
# python2 vs python3 issues.
from nose.plugins.xunit import format_exception

################################################################################
## Functions for constructing specifications based on nose testing objects.
################################################################################

def dispatch_on_type(dispatch_table, instance):
    for type, func in dispatch_table:
        if type is True or isinstance(instance, type):
            return func(instance)


def remove_leading(needle, haystack):
    """Remove leading needle string (if exists).

    >>> remove_leading('Test', 'TestThisAndThat')
    'ThisAndThat'
    >>> remove_leading('Test', 'ArbitraryName')
    'ArbitraryName'
    """
    if haystack[:len(needle)] == needle:
        return haystack[len(needle):]
    return haystack


def remove_trailing(needle, haystack):
    """Remove trailing needle string (if exists).

    >>> remove_trailing('Test', 'ThisAndThatTest')
    'ThisAndThat'
    >>> remove_trailing('Test', 'ArbitraryName')
    'ArbitraryName'
    """
    if haystack[-len(needle):] == needle:
        return haystack[:-len(needle)]
    return haystack


def remove_leading_and_trailing(needle, haystack):
    return remove_leading(needle, remove_trailing(needle, haystack))


def camel2word(string):
    """Covert name from CamelCase to "Normal case".

    >>> camel2word('CamelCase')
    'Camel case'
    >>> camel2word('CaseWithSpec')
    'Case with spec'
    """
    def wordize(match):
        return ' ' + match.group(1).lower()

    return string[0] + re.sub(r'([A-Z])', wordize, string[1:])


def complete_english(string):
    """
    >>> complete_english('dont do this')
    "don't do this"
    >>> complete_english('doesnt is matched as well')
    "doesn't is matched as well"
    """
    for x, y in [("dont", "don't"),
                ("doesnt", "doesn't"),
                ("wont", "won't"),
                ("wasnt", "wasn't")]:
        string = string.replace(x, y)
    return string


def underscore2word(string):
    return string.replace('_', ' ')


def argumentsof(test):
    if test.arg:
        if len(test.arg) == 1:
            return " for %s" % test.arg[0]
        else:
            return " for %s" % (test.arg,)
    return ""


def underscored2spec(name):
    return complete_english(underscore2word(remove_trailing('_test', remove_leading('test_', name))))


def camelcase2spec(name):
    return camel2word(
        remove_trailing('_',
            remove_leading_and_trailing('Test', name)))


def camelcaseDescription(object):
    description = object.__doc__ or camelcase2spec(object.__name__)
    return description.strip()


def underscoredDescription(object):
    return object.__doc__ or underscored2spec(object.__name__).capitalize()


def doctestContextDescription(doctest):
    return doctest._dt_test.name


def noseMethodDescription(test):
    return test.method.__doc__ or underscored2spec(test.method.__name__)


def unittestMethodDescription(test):
    if test._testMethodDoc is None:
        return underscored2spec(test._testMethodName)
    else:
        description = test._testMethodDoc.split("\n")
        return "".join([text.strip() for text in description])


def noseFunctionDescription(test):
    # Special case for test generators.
    if test.descriptor is not None:
        if hasattr(test.test, 'description'):
            return test.test.description
        return "holds for %s" % ', '.join(map(six.text_type, test.arg))
    return test.test.__doc__ or underscored2spec(test.test.__name__)


# Different than other similar functions, this one returns a generator
# of specifications.
def doctestExamplesDescription(test):
    for ex in test._dt_test.examples:
        source = ex.source.replace("\n", " ")
        want = None
        if '#' in source:
            source, want = source.rsplit('#', 1)
        elif ex.exc_msg:
            want = "throws \"%s\"" % ex.exc_msg.rstrip()
        elif ex.want:
            want = "returns %s" % ex.want.replace("\n", " ")

        if want:
            yield "%s %s" % (source.strip(), want.strip())


def testDescription(test):
    supported_test_types = [
        (nose.case.MethodTestCase, noseMethodDescription),
        (nose.case.FunctionTestCase, noseFunctionDescription),
        (doctest.DocTestCase, doctestExamplesDescription),
        (unittest.TestCase, unittestMethodDescription),
    ]
    return dispatch_on_type(supported_test_types, test.test)


def contextDescription(context):
    supported_context_types = [
        (types.ModuleType, underscoredDescription),
        (types.FunctionType, underscoredDescription),
        (doctest.DocTestCase, doctestContextDescription),
        (type, camelcaseDescription),
    ]

    if not six.PY3:
        supported_context_types += [
            # Handle both old and new style classes.
            (types.ClassType, camelcaseDescription),
        ]

    return dispatch_on_type(supported_context_types, context)


def testContext(test):
    # Test generators set their own contexts.
    if isinstance(test.test, nose.case.FunctionTestCase) \
           and test.test.descriptor is not None:
        return test.test.descriptor
    # So do doctests.
    elif isinstance(test.test, doctest.DocTestCase):
        return test.test
    else:
        return test.context


################################################################################
## Output stream that can be easily enabled and disabled.
################################################################################

class OutputStream(_WritelnDecorator):
    def __init__(self, on_stream, off_stream):
        self.capture_stream = IO()
        self.on_stream = on_stream
        self.off_stream = off_stream
        self.stream = on_stream

    def on(self):
        self.stream = self.on_stream

    def off(self):
        self.stream = self.off_stream

    def capture(self):
        self.capture_stream.truncate()
        self.stream = self.capture_stream

    def get_captured(self):
        self.capture_stream.seek(0)
        return self.capture_stream.read()


def depth(context):
    level = 0
    while hasattr(context, '_parent'):
        level += 1
        context = context._parent
    return level


class SpecOutputStream(OutputStream):
    def print_text(self, text):
        self.on()
        self.write(text)
        self.off()

    def print_line(self, line=''):
        self.print_text(line + "\n")

    @property
    def _indent(self):
        return "    " * self._depth

    def print_context(self, context):
        # Ensure parents get printed too (e.g. an outer class with nothing but
        # inner classes will otherwise never get printed.)
        if (
            hasattr(context, '_parent')
            and not getattr(context._parent, '_printed', False)
        ):
            self.print_context(context._parent)
        # Adjust indentation depth
        self._depth = depth(context)
        self.print_line("\n%s%s" % (self._indent, contextDescription(context)))
        context._printed = True

    def print_spec(self, color_func, test, status=None):
        spec = testDescription(test).strip()
        if not isinstance(spec, types.GeneratorType):
            spec = [spec]
        for s in spec:
            name = "- %s" % s
            paren = (" (%s)" % status) if status else ""
            indent = getattr(self, '_indent', "")
            self.print_line(indent + color_func(name + paren))



################################################################################
## Color helpers.
################################################################################

color_end = "\x1b[1;0m"
colors = dict(
    green="32",
    red="31",
    yellow="33",
    purple="35",
    cyan="36",
    blue="34"
)

def colorize(color, text, bold=False):
    bold = 1 if bold else 0
    return "\x1b[%s;%sm%s%s" % (bold, colors[color], text, color_end)

################################################################################
## Plugin itself.
################################################################################

class SpecPlugin(Plugin):
    """Generate specification from test class/method names.
    """
    score = 1100  # must be higher than Deprecated and Skip plugins scores

    def __init__(self, *args, **kwargs):
        super(SpecPlugin, self).__init__(*args, **kwargs)
        self._failures = []
        self._errors = []
        self.color = {}

    def options(self, parser, env=os.environ):
        Plugin.options(self, parser, env)
        parser.add_option('--no-spec-color', action='store_true',
                          dest='no_spec_color',
                          default=env.get('NOSE_NO_SPEC_COLOR'),
                          help="Don't show colors with --with-spec"
                          "[NOSE_NO_SPEC_COLOR]")
        parser.add_option('--spec-doctests', action='store_true',
                          dest='spec_doctests',
                          default=env.get('NOSE_SPEC_DOCTESTS'),
                          help="Include doctests in specifications "
                          "[NOSE_SPEC_DOCTESTS]")
        parser.add_option('--no-detailed-errors', action='store_false',
                          dest='detailedErrors',
                          help="Force detailed errors off")

    def configure(self, options, config):
        # Configure
        Plugin.configure(self, options, config)
        # Set options
        if options.enable_plugin_specplugin:
            options.verbosity = max(options.verbosity, 2)
        self.spec_doctests = options.spec_doctests
        # Color setup
        for label, color in list({
            'error': 'red',
            'ok': 'green',
            'deprecated': 'yellow',
            'skipped': 'yellow',
            'failure': 'red',
            'identifier': 'cyan',
            'file': 'blue',
        }.items()):
            # No color: just print() really
            func = lambda text, bold=False: text
            if not options.no_spec_color:
                # Color: colorizes!
                func = partial(colorize, color)
            # Store in dict (slightly quicker/nicer than getattr)
            self.color[label] = func
            # Add attribute for easier hardcoded access
            setattr(self, label, func)

    def begin(self):
        self.current_context = None
        self.start_time = time.time()

    def setOutputStream(self, stream):
        self.stream = SpecOutputStream(stream, open(os.devnull, 'w'))
        return self.stream

    def beforeTest(self, test):
        context = testContext(test)
        if context != self.current_context:
            self._print_context(context)
            self.current_context = context

        self.stream.off()

    def addSuccess(self, test):
        self._print_spec('ok', test)

    def addFailure(self, test, err):
        self._print_spec('failure', test, '')
        self._failures.append((test, err))

    def addError(self, test, err):
        def blurt(color, label):
            self._print_spec(color, test, label)

        klass = err[0]
        if issubclass(klass, nose.DeprecatedTest):
            blurt('deprecated', '')
        elif issubclass(klass, SkipTest):
            blurt('skipped', '')
        else:
            self._errors.append((test, err))
            blurt('error', '')

    def afterTest(self, test):
        self.stream.capture()

    def print_tracebacks(self, label, items):
        problem_color = {
            "ERROR": "error",
            "FAIL": "failure"
        }[label]
        for item in items:
            test, trace = item
            desc = test.shortDescription() or six.text_type(test)
            self.stream.writeln("=" * 70)
            self.stream.writeln("%s: %s" % (
                self.color[problem_color](label),
                self.identifier(desc, bold=True),
            ))
            self.stream.writeln("-" * 70)
            # format_exception() is...very odd re: how it breaks into lines.
            trace = "".join(format_exception(trace)).split("\n")
            self.print_colorized_traceback(trace)

    def print_colorized_traceback(self, formatted_traceback, indent_level=0):
        indentation = "    " * indent_level
        for line in formatted_traceback:
            if line.startswith("  File"):
                m = re.match(r'  File "(.*)", line (\d*)(?:, in (.*))?$', line)
                if m:
                    filename, lineno, test = m.groups()
                    tb_lines = [
                        '  File "',
                        self.file(filename),
                        '", line ',
                        self.error(lineno),
                        ]
                    if test:
                        # this is missing for the first traceback in doctest
                        # failure report
                        tb_lines.extend([
                            ", in ",
                            self.identifier(test, bold=True)
                        ])
                    tb_lines.extend(["\n"])
                    self.stream.write(indentation)
                    self.stream.writelines(tb_lines)
                else:
                    six.print_(indentation + line, file=self.stream)
            elif line.startswith("    "):
                six.print_(self.identifier(indentation + line), file=self.stream)
            elif line.startswith("Traceback (most recent call last)"):
                six.print_(indentation + line, file=self.stream)
            else:
                six.print_(self.error(indentation + line), file=self.stream)

    def finalize(self, result):
        self.stream.on()
        six.print_("", file=self.stream)
        self.print_tracebacks("ERROR", self._errors)
        self.print_tracebacks("FAIL", self._failures)
        self.print_summary(result)

    def print_summary(self, result):
        # Setup
        num_tests = result.testsRun
        success = result.wasSuccessful()
        # How many in how long
        six.print_("Ran %s test%s in %s" % (
            (self.ok if success else self.error)(num_tests),
            "s" if num_tests > 1 else "",
            self.format_seconds(time.time() - self.start_time)
        ), file=self.stream)
        # Did we fail, and if so, how badly?
        if success:
            skipped = len(result.skipped)
            skipped_str = "(" + self.skipped("%i skipped" % skipped) + ")"
            six.print_(self.ok("OK"), skipped_str if skipped else "", file=self.stream)
        else:
            types = (
                ('failures', 'failure'),
                ('errors', 'error'),
                ('skipped', 'skipped'),
            )
            pairs = []
            for label, color in types:
                num = len(getattr(result, label))
                text = six.text_type(num)
                if num:
                    text = self.color[color](text)
                pairs.append("%s=%s" % (label, text))
            six.print_("%s (%s)" % (
                self.failure("FAILED"),
                ", ".join(pairs)
            ), file=self.stream)
        six.print_("", file=self.stream)

    def format_seconds(self, n_seconds):
        """Format a time in seconds."""
        func = self.ok
        if n_seconds >= 60:
            n_minutes, n_seconds = divmod(n_seconds, 60)
            return "%s minutes %s seconds" % (
                        func("%d" % n_minutes),
                        func("%.3f" % n_seconds))
        else:
            return "%s seconds" % (
                        func("%.3f" % n_seconds))

    def _print_context(self, context):
        if isinstance(context, doctest.DocTestCase) and not self.spec_doctests:
            return
        self.stream.print_context(context)

    def _print_spec(self, color, test, status=None):
        if isinstance(test.test, doctest.DocTestCase) and not self.spec_doctests:
            return
        self.stream.print_spec(self.color[color], test, status)

########NEW FILE########
__FILENAME__ = trap
"""
Test decorator for capturing stdout/stderr/both.

Based on original code from Fabric 1.x, specifically:

* fabric/tests/utils.py
* as of Git SHA 62abc4e17aab0124bf41f9c5f9c4bc86cc7d9412

Though modifications have been made since.
"""
import sys
from functools import wraps

import six
from six import BytesIO as IO


class CarbonCopy(IO):
    """
    An IO wrapper capable of multiplexing its writes to other buffer objects.
    """
    # NOTE: because StringIO.StringIO on Python 2 is an old-style class we
    # cannot use super() :(
    def __init__(self, buffer=b'', cc=None):
        """
        If ``cc`` is given and is a file-like object or an iterable of same,
        it/they will be written to whenever this instance is written to.
        """
        IO.__init__(self, buffer)
        if cc is None:
            cc = []
        elif hasattr(cc, 'write'):
            cc = [cc]
        self.cc = cc

    def write(self, s):
        # Ensure we always write bytes. This means that wrapped code calling
        # print(<a string object>) in Python 3 will still work. Sigh.
        if not isinstance(s, six.binary_type):
            s = s.encode('utf-8')
        # Write out to our capturing object & any CC's
        IO.write(self, s)
        for writer in self.cc:
            writer.write(s)

    # Dumb hack to deal with py3 expectations; real sys.std(out|err) in Py3
    # requires writing to a buffer attribute obj in some situations.
    @property
    def buffer(self):
        return self

    # Make sure we always hand back strings, even on Python 3
    def getvalue(self):
        ret = IO.getvalue(self)
        if six.PY3:
            ret = ret.decode('utf-8')
        return ret


def trap(func):
    """
    Replace sys.std(out|err) with a wrapper during execution, restored after.

    In addition, a new combined-streams output (another wrapper) will appear at
    ``sys.stdall``. This stream will resemble what a user sees at a terminal,
    i.e. both out/err streams intermingled.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Use another CarbonCopy even though we're not cc'ing; for our "write
        # bytes, return strings on py3" behavior. Meh.
        sys.stdall = CarbonCopy()
        my_stdout, sys.stdout = sys.stdout, CarbonCopy(cc=sys.stdall)
        my_stderr, sys.stderr = sys.stderr, CarbonCopy(cc=sys.stdall)
        try:
            ret = func(*args, **kwargs)
        finally:
            sys.stdout = my_stdout
            sys.stderr = my_stderr
            del sys.stdall
    return wrapper

########NEW FILE########
__FILENAME__ = utils
import six

from nose.util import isclass


def hide(obj):
    """
    Mark object as private.
    """
    obj._spec__is_private = True
    return obj

def is_public_class(name, value):
    return isclass(value) and not name.startswith('_')

def class_members(obj):
    return [x for x in six.iteritems(vars(obj)) if is_public_class(*x)]

def my_getattr(self, name):
    if not self._parent_inst:
        parent = self._parent()
        parent.setup()
        self._parent_inst = parent
    return getattr(self._parent_inst, name)

def flag_inner_classes(obj):
    """
    Mutates any attributes on ``obj`` which are classes, with link to ``obj``.

    Adds a convenience accessor which instantiates ``obj`` and then calls its
    ``setup`` method.

    Recurses on those objects as well.
    """
    for tup in class_members(obj):
        tup[1]._parent = obj
        tup[1]._parent_inst = None
        tup[1].__getattr__ = my_getattr
        flag_inner_classes(tup[1])

def autohide(obj):
    """
    Automatically hide setup() and teardown() methods, recursively.
    """
    # Members on obj
    for name, item in six.iteritems(vars(obj)):
        if callable(item) and name in ('setup', 'teardown'):
            item = hide(item)
    # Recurse into class members
    for name, subclass in class_members(obj):
        autohide(subclass)


class InnerClassParser(type):
    """
    Metaclass that tags inner classes with a link to the parent class.

    Allows test loading machinery to determine if a given test is part of an
    inner class or a top level one.
    """
    def __new__(cls, name, bases, attrs):
        new_class = type.__new__(cls, name, bases, attrs)
        flag_inner_classes(new_class)
        autohide(new_class)
        return new_class

########NEW FILE########
__FILENAME__ = test
def test_good():
    assert True

def test_bad():
    assert False

def test_boom():
    what

def test_skip():
    from nose.plugins.skip import SkipTest
    raise SkipTest


class Foo(object):
    def has_no_underscore(self):
        assert True

    def has_no_Test(self):
        assert True

class Foo_(object):
    def should_print_out_as_Foo(self):
        pass

########NEW FILE########
__FILENAME__ = spec_test
"""Unit tests for Spec plugin.
"""

import unittest
import nose
import six
from nose.plugins import PluginTester

from spec import Spec


def _prepend_in_each_line(string, prefix='    '):
    return ''.join([prefix + s for s in string.splitlines(True)])


class _SpecPluginTestCase(PluginTester, unittest.TestCase):
    activate = '--with-spec'
    args = ['--no-spec-color']
    plugins = [Spec()]

    def _get_suitepath(self):
        return '_spec_test_cases/%s.py' % self.suitename
    suitepath = property(_get_suitepath)

    def assertContains(self, needle, haystack):
        assert needle in haystack,\
            "Failed to find:\n\n%s\ninside\n%s\n" % \
                (_prepend_in_each_line(needle), _prepend_in_each_line(haystack))

    def assertContainsInOutput(self, string):
        self.assertContains(string, six.text_type(self.output))

    def failIfContains(self, needle, haystack):
        assert needle not in haystack,\
            "Found:\n\n%s\ninside\n%s\n" % \
                (_prepend_in_each_line(needle), _prepend_in_each_line(haystack))

    def failIfContainsInOutput(self, string):
        self.failIfContains(string, six.text_type(self.output))


class TestPluginSpecWithFoobar(_SpecPluginTestCase):
    suitename = 'foobar'
    expected_test_foobar_output = """Foobar
- can be automatically documented
- is a singleton
"""
    expected_test_bazbar_output = """Baz bar
- does this and that
"""

    def test_builds_specifications_for_test_classes(self):
        self.assertContainsInOutput(self.expected_test_foobar_output)

    def test_builds_specifications_for_unittest_test_cases(self):
        self.assertContainsInOutput(self.expected_test_bazbar_output)


class TestPluginSpecWithFoobaz(_SpecPluginTestCase):
    suitename = 'foobaz'
    expected_test_foobaz_output = """Foobaz
- behaves such and such
- causes an error (ERROR)
- fails to satisfy this specification (FAILED)
- throws deprecated exception (DEPRECATED)
- throws skip test exception (SKIPPED)
"""

    def test_marks_failed_specifications_properly(self):
        self.assertContainsInOutput(self.expected_test_foobaz_output)


# Make sure DEPRECATED and SKIPPED are still present in the output when set
# of standard nose plugins is enabled.
class TestPluginSpecWithFoobazAndStandardPluginsEnabled(TestPluginSpecWithFoobaz):
    plugins = [Spec(), nose.plugins.skip.Skip(), nose.plugins.deprecated.Deprecated()]


class TestPluginSpecWithContainers(_SpecPluginTestCase):
    suitename = 'containers'
    expected_test_containers_output = """Containers
- are marked as deprecated
- doesn't work with sets
"""

    def test_builds_specifications_for_test_modules(self):
        self.assertContainsInOutput(self.expected_test_containers_output)


class TestPluginSpecWithDocstringSpecNames(_SpecPluginTestCase):
    suitename = 'docstring_spec_names'
    expected_test_docstring_spec_modules_names_output = """This module
- uses function to do this and that
"""
    expected_test_docstring_spec_class_names_output = """Yet another class
- has a nice descriptions inside test methods
- has a lot of methods
"""

    def test_names_specifications_after_docstrings_if_present(self):
        self.assertContainsInOutput(self.expected_test_docstring_spec_modules_names_output)
        self.assertContainsInOutput(self.expected_test_docstring_spec_class_names_output)


class TestPluginSpecWithTestGenerators(_SpecPluginTestCase):
    suitename = 'generators'
    expected_test_test_generators_output = """Product of even numbers is even
- holds for 18, 8
- holds for 14, 12
- holds for 0, 4
- holds for 6, 2
- holds for 16, 10
"""

    def test_builds_specifications_for_test_generators(self):
        self.assertContainsInOutput(self.expected_test_test_generators_output)


class TestPluginSpecWithTestGeneratorsWithDescriptions(_SpecPluginTestCase):
    suitename = 'generators_with_descriptions'
    expected_test_test_generators_with_descriptions_output = """Natural numbers truths
- for even numbers 18 and 8 their product is even as well
- for even numbers 14 and 12 their product is even as well
- for even numbers 0 and 4 their product is even as well
- for even numbers 6 and 2 their product is even as well
- for even numbers 16 and 10 their product is even as well
"""

    def test_builds_specifications_for_test_generators_using_description_attribute_if_present(self):
        self.assertContainsInOutput(self.expected_test_test_generators_with_descriptions_output)


class TestPluginSpecWithDoctests(_SpecPluginTestCase):
    activate = '--with-spec'
    args = ['--with-doctest', '--doctest-tests', '--spec-doctests', '--no-spec-color']
    plugins = [Spec(), nose.plugins.doctests.Doctest()]

    suitename = 'doctests'
    expected_test_doctests_output = """doctests
- 2 + 3 returns 5
- None is nothing
- foobar throws "NameError: name 'foobar' is not defined"
"""

    def test_builds_specifications_for_doctests(self):
        self.assertContainsInOutput(self.expected_test_doctests_output)


class TestPluginSpecWithDoctestsButDisabled(_SpecPluginTestCase):
    activate = '--with-spec'

    # no --spec-doctests option
    args = ['--with-doctest', '--doctest-tests', '--no-spec-color']
    plugins = [Spec(), nose.plugins.doctests.Doctest()]
    suitename = 'doctests'

    def test_doesnt_build_specifications_for_doctests_when_spec_doctests_option_wasnt_set(self):
        self.failIfContainsInOutput("test_doctests")
        self.failIfContainsInOutput("2 + 3 returns 5")

########NEW FILE########
__FILENAME__ = containers
def test_are_marked_as_deprecated():
    pass


def test_doesnt_work_with_sets():
    pass

########NEW FILE########
__FILENAME__ = docstring_spec_names
"This module"


def test_function():
    """uses function to do this and that"""


class TestYetAnotherClass:
    def test_has_a_lot_of_methods(self):
        pass

    def test_foobared(self):
        "has a nice descriptions inside test methods"
        pass

########NEW FILE########
__FILENAME__ = doctests
"""
>>> 2 + 3
5
>>> None
>>> None # is nothing
>>> foobar
Traceback (most recent call last):
  ...
NameError: name 'foobar' is not defined
"""

########NEW FILE########
__FILENAME__ = foobar
import unittest


class TestFoobar:
    def test_can_be_automatically_documented(self):
        pass

    def test_is_a_singleton(self):
        pass


class TestBazBar(unittest.TestCase):
    def test_does_this_and_that(self):
        pass

########NEW FILE########
__FILENAME__ = foobaz
import nose


class TestFoobaz(object):
    def test_behaves_such_and_such(self):
        assert True

    def test_causes_an_error(self):
        raise NameError

    def test_fails_to_satisfy_this_specification(self):
        assert False

    def test_throws_deprecated_exception(self):
        raise nose.DeprecatedTest

    def test_throws_skip_test_exception(self):
        raise nose.SkipTest

########NEW FILE########
__FILENAME__ = generators
def is_even(n):
    return n % 2 == 0


def test_product_of_even_numbers_is_even():
    evens = [(18, 8), (14, 12), (0, 4), (6, 2), (16, 10)]
    for e1, e2 in evens:
        yield check_even, e1, e2


def check_even(e1, e2):
    assert is_even(e1 * e2)

########NEW FILE########
__FILENAME__ = generators_with_descriptions
def is_even(n):
    return n % 2 == 0


def test_product_of_even_numbers_is_even():
    "Natural numbers truths"
    evens = [(18, 8), (14, 12), (0, 4), (6, 2), (16, 10)]
    for e1, e2 in evens:
        check_even.description = "for even numbers %d and %d their product is even as well" % (e1, e2)
        yield check_even, e1, e2


def check_even(e1, e2):
    assert is_even(e1 * e2)

########NEW FILE########
__FILENAME__ = readme
from nose.plugins.skip import SkipTest


class TestMyClass(object):
    def test_has_an_attribute(self):
        assert True

    def test_should_perform_some_action(self):
        assert False

    def test_can_stand_on_its_head(self):
        raise SkipTest

########NEW FILE########
