__FILENAME__ = compat
# This is for backwards compatibility with Python version < 2.7 only
# for Python 2.7 and 3.x the default unittest is the correct package
# to use. unittest2 is a backport of this package to be used in
# versions < 2.7.
# Use
#       from cricket.compat import unittest
#
# to make versions work with all version of Python. This will be slowly
# deprecated in the future as Python < 2.7 becomes more and mor
# obsolete.
from __future__ import absolute_import
import unittest
if not hasattr(unittest.TestCase, 'assertIsNotNone'):
    import unittest2 as unittest

########NEW FILE########
__FILENAME__ = discoverer
from __future__ import absolute_import

import unittest

from django.conf import settings
try:
    from django.test.simple import DjangoTestSuiteRunner
except ImportError:  # django.test.simple was removed in Django 1.8
    DjangoTestSuiteRunner = None
from django.test.utils import get_runner

# Dynamically retrieve the test runner class for this project.
TestRunnerClass = get_runner(settings, None)


class TestDiscoverer(TestRunnerClass):
    """A Django test runner that prints out all the test that will be run.

    Doesn't actually run any of the tests.
    """
    def _output_suite(self, suite):
        for test in suite:
            # Django 1.6 introduce the new-style test runner.
            # If that test runner is in use, we use the full test name.
            # If we're still using a pre 1.6-style runner, we need to
            # drop out all everything between the app name and the test module.
            if isinstance(test, unittest.TestSuite):
                self._output_suite(test)
            elif (DjangoTestSuiteRunner and
                  issubclass(TestRunnerClass, DjangoTestSuiteRunner)):
                parts = test.id().split('.')
                tests_index = parts.index('tests')
                print '%s.%s.%s' % (parts[tests_index - 1], parts[-2], parts[-1])
            else:
                print test.id()

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        self._output_suite(self.build_suite(test_labels))
        return 0

########NEW FILE########
__FILENAME__ = django_runtests
#!/usr/bin/env python
import os
import warnings
import argparse

from django.utils import importlib

import runtests

def django_tests(runner, labels):
    state = runtests.setup(1, labels)

    module_name, runner_class_name = runner.rsplit('.', 1)
    module = importlib.import_module(module_name)
    TestRunner = getattr(module, runner_class_name)

    runner = TestRunner(
        verbosity=1,
        interactive=False,
        failfast=False,
    )

    # Catch warnings thrown in test DB setup -- remove in Django 1.9
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore',
            "Custom SQL location '<app_label>/models/sql' is deprecated, "
            "use '<app_label>/sql' instead.",
            PendingDeprecationWarning
        )
        failures = runner.run_tests(labels or runtests.get_installed())

    runtests.teardown(state)
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--settings", help="The settings file to use.", action="store")
    parser.add_argument("--testrunner", help="The test runner to use.", action="store")
    parser.add_argument('args', nargs=argparse.REMAINDER, help='Test labels to execute.')

    options = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", options.settings)

    django_tests(options.testrunner, options.args)

########NEW FILE########
__FILENAME__ = executor
from __future__ import absolute_import

try:
    from coverage import coverage
except ImportError:
    coverage = None

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner
from django.test.utils import get_runner

from cricket.pipes import PipedTestRunner

# Dynamically retrieve the test runner class for this project.
TestRunnerClass = get_runner(settings, None)


class TestExecutor(TestRunnerClass):
    """A Django test runner that runs the test suite.

    Formats output in a machine-readable format.
    """
    def run_suite(self, suite, **kwargs):
        # Django 1.6 introduce the new-style test runner.
        # If that test runner is in use, we use the full test name.
        # If we're still using a pre 1.6-style runner, we need to
        # drop out all everything between the app name and the test module.
        use_old_discovery = issubclass(TestRunnerClass, DjangoTestSuiteRunner)

        return PipedTestRunner(use_old_discovery=use_old_discovery).run(suite)


class TestCoverageExecutor(TestExecutor):
    """A Django test runner that runs the test suite with coverage

    Formats output in a machine-readable format.
    """
    def run_suite(self, suite, **kwargs):
        cov = coverage()
        cov.start()
        result = super(TestCoverageExecutor, self).run_suite(suite, **kwargs)
        cov.stop()
        cov.save()
        return result

########NEW FILE########
__FILENAME__ = model
'''
In general, you would expect that there would only be one project class
specified in this file. It provides the interface to executing test
collecetion and execution.
'''
import os
import sys

from cricket.model import Project


class DjangoProject(Project):
    '''
    The Project is a wrapper around the command-line calls to interface
    to test collection and test execution
    '''

    def __init__(self, options=None):
        self.settings = None
        if options and hasattr(options, 'settings'):
            self.settings = options.settings
        super(DjangoProject, self).__init__()

    @classmethod
    def add_arguments(cls, parser):
        """Add Django-specific settings to the argument parser.
        """
        settings_help = ("The Python path to a settings module, e.g. "
                         "\"myproject.settings.main\". If this isn't provided, the "
                         "DJANGO_SETTINGS_MODULE environment variable will be "
                         "used.")
        parser.add_argument('--settings', help=settings_help)

    @property
    def script(self):
        if os.path.exists(os.path.join(os.getcwd(), 'manage.py')):
            # We're running the test suite on a normal Django project
            script = ['manage.py', 'test', '--noinput']
        elif os.path.exists(os.path.join(os.getcwd(), 'runtests.py')):
            # We're running Django's own test script
            script = [os.path.join(os.path.dirname(__file__), 'django_runtests.py')]
            os.environ['PYTHONPATH'] = os.getcwd()
            if self.settings is None:
                self.settings = 'test_sqlite'
        else:
            raise Exception("Can't find a Django test suite to execute.")
        return script

    def discover_commandline(self):
        "Command lineDiscover all available tests in a project."

        command = [sys.executable] + self.script

        if self.settings:
            command.append('--settings={0}'.format(self.settings))

        command.append('--testrunner=cricket.django.discoverer.TestDiscoverer')

        return command

    def execute_commandline(self, labels):
        "Return the command line to execute the specified test labels"
        command = [sys.executable] + self.script

        if self.settings:
            command.append('--settings={0}'.format(self.settings))

        if self.coverage:
            command.append('--testrunner=cricket.django.executor.TestCoverageExecutor')
        else:
            command.append('--testrunner=cricket.django.executor.TestExecutor')
        command.extend(labels)

        return command

########NEW FILE########
__FILENAME__ = __main__
'''
This is the main entry point for running Django test suites.
'''
from cricket.main import main as cricket_main
from cricket.django.model import DjangoProject


def main():
    cricket_main(DjangoProject)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = events


class EventSource(object):
    """A source of GUI events.

    An event source can receive handlers for events, and
    can emit events.
    """
    _events = {}

    @classmethod
    def bind(cls, event, handler):
        cls._events.setdefault(cls, {}).setdefault(event, []).append(handler)

    def emit(self, event, **data):
        try:
            for handler in self._events[self.__class__][event]:
                handler(self, **data)
        except KeyError:
            # No handler registered for event.
            pass

########NEW FILE########
__FILENAME__ = executor
import json
import subprocess
import sys
from threading import Thread

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

from cricket.events import EventSource
from cricket.model import TestMethod
from cricket.pipes import PipedTestResult, PipedTestRunner


def enqueue_output(out, queue):
    """A utility method for consuming piped output from a subprocess.

    Reads content from `out` one line at a time, and puts it onto
    queue for consumption in a separate thread.
    """
    for line in iter(out.readline, b''):
        queue.put(line.strip())
    out.close()


class Executor(EventSource):
    "A wrapper around the subprocess that executes tests."
    def __init__(self, project, count, labels):
        self.project = project

        self.proc = subprocess.Popen(
            self.project.execute_commandline(labels),
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            bufsize=1,
            close_fds='posix' in sys.builtin_module_names
        )

        # Piped stdout/stderr reads are blocking; therefore, we need to
        # do all our readline calls in a background thread, and use a
        # queue object to store lines that have been read.
        self.stdout = Queue()
        t = Thread(target=enqueue_output, args=(self.proc.stdout, self.stdout))
        t.daemon = True
        t.start()

        self.stderr = Queue()
        t = Thread(target=enqueue_output, args=(self.proc.stderr, self.stderr))
        t.daemon = True
        t.start()

        # The TestMethod object currently under execution.
        self.current_test = None

        # An accumulator of ouput from the tests. If buffer is None,
        # then the test suite isn't currently running - it's in suite
        # setup/teardown.
        self.buffer = None

        # An accumulator for error output from the tests.
        self.error_buffer = []

        # The timestamp when current_test started
        self.start_time = None

        # The total count of tests under execution
        self.total_count = count

        # The count of tests that have been executed.
        self.completed_count = 0

        # The count of specific test results.
        self.result_count = {}

    @property
    def is_running(self):
        "Return True if this runner currently running."
        return self.proc.poll() is None

    @property
    def any_failed(self):
        return sum(self.result_count.get(state, 0) for state in TestMethod.FAILING_STATES)

    def terminate(self):
        "Stop the executor."
        self.proc.terminate()

    def poll(self):
        "Poll the runner looking for new test output"
        stopped = False
        finished = False

        # Read from stdout, building a buffer.
        lines = []
        try:
            while True:
                lines.append(self.stdout.get(block=False))
        except Empty:
            # queue.get() raises an exception when the queue is empty.
            # This means there is no more output to consume at this time.
            pass

        # Read from stderr, building a buffer.
        try:
            while True:
                self.error_buffer.append(self.stderr.get(block=False))
        except Empty:
            # queue.get() raises an exception when the queue is empty.
            # This means there is no more output to consume at this time.
            pass

        # Check to see if the subprocess is still running.
        # If it isn't, raise an error.
        if self.proc is None:
            stopped = True
        elif self.proc.poll() is not None:
            stopped = True

        # Process all the full lines that are available
        for line in lines:
            # Look for a separator.
            if line in (PipedTestResult.RESULT_SEPARATOR, PipedTestRunner.START_TEST_RESULTS, PipedTestRunner.END_TEST_RESULTS):
                if self.buffer is None:
                    # Preamble is finished. Set up the line buffer.
                    self.buffer = []
                else:
                    # Start of new test result; record the last result
                    # Then, work out what content goes where.
                    pre = json.loads(self.buffer[0])
                    post = json.loads(self.buffer[1])

                    if post['status'] == 'OK':
                        status = TestMethod.STATUS_PASS
                        error = None
                    elif post['status'] == 's':
                        status = TestMethod.STATUS_SKIP
                        error = 'Skipped: ' + post.get('error')
                    elif post['status'] == 'F':
                        status = TestMethod.STATUS_FAIL
                        error = post.get('error')
                    elif post['status'] == 'x':
                        status = TestMethod.STATUS_EXPECTED_FAIL
                        error = post.get('error')
                    elif post['status'] == 'u':
                        status = TestMethod.STATUS_UNEXPECTED_SUCCESS
                        error = None
                    elif post['status'] == 'E':
                        status = TestMethod.STATUS_ERROR
                        error = post.get('error')

                    # Increase the count of executed tests
                    self.completed_count = self.completed_count + 1

                    # Get the start and end times for the test
                    start_time = float(pre['start_time'])
                    end_time = float(post['end_time'])

                    self.current_test.description = post['description']

                    self.current_test.set_result(
                        status=status,
                        output=post.get('output'),
                        error=error,
                        duration=end_time - start_time,
                    )

                    # Work out how long the suite has left to run (approximately)
                    if self.start_time is None:
                        self.start_time = start_time
                    total_duration = end_time - self.start_time
                    time_per_test = total_duration / self.completed_count
                    remaining_time = (self.total_count - self.completed_count) * time_per_test
                    if remaining_time > 4800:
                        remaining = '%s hours' % int(remaining_time / 2400)
                    elif remaining_time > 2400:
                        remaining = '%s hour' % int(remaining_time / 2400)
                    elif remaining_time > 120:
                        remaining = '%s mins' % int(remaining_time / 60)
                    elif remaining_time > 60:
                        remaining = '%s min' % int(remaining_time / 60)
                    else:
                        remaining = '%ss' % int(remaining_time)

                    # Update test result counts
                    self.result_count.setdefault(status, 0)
                    self.result_count[status] = self.result_count[status] + 1

                    # Notify the display to update.
                    self.emit('test_end', test_path=self.current_test.path, result=status, remaining_time=remaining)

                    # Clear the decks for the next test.
                    self.current_test = None
                    self.buffer = []

                    if line == PipedTestRunner.END_TEST_RESULTS:
                        # End of test execution.
                        # Mark the runner as finished, and move back
                        # to a pre-test state in the results.
                        finished = True
                        self.buffer = None

            else:
                # Not a separator line, so it's actual content.
                if self.buffer is None:
                    # Suite isn't running yet - just display the output
                    # as a status update line.
                    self.emit('test_status_update', update=line)
                else:
                    # Suite is running - have we got an active test?
                    # Doctest (and some other tools) output invisible escape sequences.
                    # Strip these if they exist.
                    if line.startswith('\x1b'):
                        line = line[line.find('{'):]

                    # Store the cleaned buffer
                    self.buffer.append(line)

                    # If we don't have an currently active test, this line will
                    # contain the path for the test.
                    if self.current_test is None:
                        # No active test; first line tells us which test is running.
                        pre = json.loads(line)
                        self.current_test = self.project.confirm_exists(pre['path'])
                        self.emit('test_start', test_path=pre['path'])
        # If we're not finished, requeue the event.
        if finished:
            if self.error_buffer:
                self.emit('suite_end', error='\n'.join(self.error_buffer))
            else:
                self.emit('suite_end')
            return False

        elif stopped:
            # Suite has stopped producing output.
            if self.error_buffer:
                self.emit('suite_error', error='\n'.join(self.error_buffer))
            else:
                self.emit('suite_error', error='Test output ended unexpectedly')

            # Suite has finished; don't requeue
            return False

        else:
            # Still running - requeue event.
            return True

########NEW FILE########
__FILENAME__ = main
'''
The purpose of this module is to set up the Cricket GUI,
load a "project" for discovering and executing tests, and
to initiate the GUI main loop.
'''
from argparse import ArgumentParser
import subprocess
import sys

from Tkinter import *

from cricket.view import (
    MainWindow,
    TestLoadErrorDialog,
    IgnorableTestLoadErrorDialog
)
from cricket.model import ModelLoadError


def main(Model):
    """Run the main loop of the app.

    Take the project Model as the argument. This model will be
    instantiated as part of the main loop.
    """
    parser = ArgumentParser()

    parser.add_argument("--version", help="Display version number and exit", action="store_true")

    Model.add_arguments(parser)
    options = parser.parse_args()

    # Check the shortcut options
    if options.version:
        import cricket
        print cricket.VERSION
        return

    # Set up the root Tk context
    root = Tk()

    # Construct an empty window
    view = MainWindow(root)

    # Try to load the project. If any error occurs during
    # project load, show an error dialog
    project = None
    while project is None:
        try:
            # Create the project objects
            project = Model(options)

            runner = subprocess.Popen(
                project.discover_commandline(),
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )

            test_list = []
            for line in runner.stdout:
                test_list.append(line.strip())

            errors = []
            for line in runner.stderr:
                errors.append(line.strip())

            if errors and not test_list:
                raise ModelLoadError('\n'.join(errors))

            project.refresh(test_list, errors)
        except ModelLoadError as e:
            # Load failed; destroy the project and show an error dialog.
            # If the user selects cancel, quit.
            project = None
            dialog = TestLoadErrorDialog(root, e.trace)
            if dialog.status == dialog.CANCEL:
                sys.exit(1)

    if project.errors:
        dialog = IgnorableTestLoadErrorDialog(root, '\n'.join(project.errors))
        if dialog.status == dialog.CANCEL:
            sys.exit(1)

    # Set the project for the main window.
    # This populates the tree, and sets listeners for
    # future tree modifications.
    view.project = project

    # Run the main loop
    try:
        view.mainloop()
    except KeyboardInterrupt:
        view.on_quit()

########NEW FILE########
__FILENAME__ = model
"""A module containing a data representation for the test suite.

This is the "Model" of the MVC world.

Each object in the model is an event source; views/controllers
can bind to events on the model to be notified of changes.
"""
from datetime import datetime

from cricket.events import EventSource


class ModelLoadError(Exception):
    def __init__(self, trace):
        super(ModelLoadError, self).__init__()
        self.trace = trace


class TestMethod(EventSource):
    """A data representation of an individual test method.

    Emits:
        * 'new' when a new node is added
        * 'inactive' when the test method is made inactive in the suite.
        * 'active' when the test method is made active in the suite.
        * 'status_update' when the pass/fail status of the method is updated.
    """
    STATUS_PASS = 100
    STATUS_SKIP = 200
    STATUS_FAIL = 300
    STATUS_EXPECTED_FAIL = 310
    STATUS_UNEXPECTED_SUCCESS = 320
    STATUS_ERROR = 400

    FAILING_STATES = (STATUS_FAIL, STATUS_UNEXPECTED_SUCCESS, STATUS_ERROR)

    STATUS_LABELS = {
        STATUS_PASS: 'passed',
        STATUS_SKIP: 'skipped',
        STATUS_FAIL: 'failures',
        STATUS_EXPECTED_FAIL: 'expected failures',
        STATUS_UNEXPECTED_SUCCESS: 'unexpected successes',
        STATUS_ERROR: 'errors',
    }

    def __init__(self, name, testCase):
        self.name = name
        self.description = ''
        self._active = True
        self._result = None

        # Set the parent of the TestMethod
        self.parent = testCase
        self.parent[name] = self
        self.parent._update_active()

        # Announce that there is a new test method
        self.emit('new')

    def __repr__(self):
        return u'TestMethod %s' % self.path

    @property
    def path(self):
        "The dotted-path name that identifies this test method to the test runner"
        return u'%s.%s' % (self.parent.path, self.name)

    @property
    def active(self):
        "Is this test method currently active?"
        return self._active

    def set_active(self, is_active, cascade=True):
        """Explicitly set the active state of the test method

        If cascade is True, the parent testCase will be prompted
        to check it's current active status.
        """
        if self._active:
            if not is_active:
                self._active = False
                self.emit('inactive')
                if cascade:
                    self.parent._update_active()
        else:
            if is_active:
                self._active = True
                self.emit('active')
                if cascade:
                    self.parent._update_active()

    def toggle_active(self):
        "Toggle the current active status of this test method"
        self.set_active(not self.active)

    @property
    def status(self):
        try:
            return self._result['status']
        except TypeError:
            return None

    @property
    def output(self):
        try:
            return self._result['output']
        except TypeError:
            return None

    @property
    def error(self):
        try:
            return self._result['error']
        except TypeError:
            return None

    @property
    def duration(self):
        try:
            return self._result['duration']
        except TypeError:
            return None

    def set_result(self, status, output, error, duration):
        self._result = {
            'status': status,
            'output': output,
            'error': error,
            'duration': duration,
        }
        self.emit('status_update')


class TestCase(dict, EventSource):
    """A data representation of a test case, wrapping multiple test methods.

    Emits:
        * 'new' when a new node is added
        * 'inactive' when the test method is made inactive in the suite.
        * 'active' when the test method is made active in the suite.
    """
    def __init__(self, name, testApp):
        super(TestCase, self).__init__()
        self.name = name
        self._active = True

        # Set the parent of the TestCase
        self.parent = testApp
        self.parent[name] = self
        self.parent._update_active()

        # Announce that there is a new TestCase
        self.emit('new')

    def __repr__(self):
        return u'TestCase %s' % self.path

    @property
    def path(self):
        "The dotted-path name that identifies this Test Case to the test runner"
        return u'%s.%s' % (self.parent.path, self.name)

    @property
    def active(self):
        "Is this test method currently active?"
        return self._active

    def set_active(self, is_active, cascade=True):
        """Explicitly set the active state of the test case.

        Forces all methods on this test case to set to the same
        active status.

        If cascade is True, the parent test module will be prompted
        to check it's current active status.
        """
        if self._active:
            if not is_active:
                self._active = False
                self.emit('inactive')
                if cascade:
                    self.parent._update_active()
                for testMethod in self.values():
                    testMethod.set_active(False, cascade=False)
        else:
            if is_active:
                self._active = True
                self.emit('active')
                if cascade:
                    self.parent._update_active()
                for testMethod in self.values():
                    testMethod.set_active(True, cascade=False)

    def toggle_active(self):
        "Toggle the current active status of this test case"
        self.set_active(not self.active)

    def find_tests(self, active=True, status=None, labels=None):
        """Find the test labels matching the search criteria.

        This will check:
            * active: if the method is currently an active test
            * status: if the last run status of the method is in the provided list
            * labels: if the method label is in the provided list

        Returns a count of tests found, plus the labels needed to
        execute those tests.
        """
        tests = []
        count = 0

        for testMethod_name, testMethod in self.items():
            include = True
            # If only active tests have been requested, the method
            # must be active.
            if active and not testMethod.active:
                include = False

            # If a list of statuses has been provided, the
            # method status must be in that list.
            if status and testMethod.status not in status:
                include = False

            # If a list of test labels has been provided, the method
            # must be named explicitly
            if labels and testMethod.path not in labels:
                include = False

            if include:
                count = count + 1
                tests.append(testMethod.path)

        # If all the tests are included, then just reference the test case.
        if len(self) == count:
            return len(self), self.path

        return count, tests

    def _purge(self, timestamp):
        "Purge any test method that isn't current as of the timestamp"
        for testMethod_name, testMethod in self.items():
            if testMethod.timestamp != timestamp:
                self.pop(testMethod_name)

    def _update_active(self):
        "Check the active status of all child nodes, and update the status of this node accordingly"
        for testMethod_name, testMethod in self.items():
            if testMethod.active:
                # As soon as we find an active child, this node
                # must be marked active, and no other checks are
                # required.
                self.set_active(True)
                return
        self.set_active(False)


class TestModule(dict, EventSource):
    """A data representation of a module. It may contain test cases, or other modules.

    Emits:
        * 'new' when a new node is added
        * 'inactive' when the test method is made inactive in the suite.
        * 'active' when the test method is made active in the suite.
    """
    def __init__(self, name, parent):
        super(TestModule, self).__init__()
        self.name = name
        self._active = True

        # Set the parent of the TestModule.
        self.parent = parent
        self.parent[name] = self

        # Announce that there is a new test case
        self.emit('new')

    def __repr__(self):
        return u'TestModule %s' % self.path

    @property
    def path(self):
        "The dotted-path name that identifies this app to the test runner"
        if self.parent.path:
            return u'%s.%s' % (self.parent.path, self.name)
        return self.name

    @property
    def active(self):
        "Is this test method currently active?"
        return self._active

    def set_active(self, is_active, cascade=True):
        """Explicitly set the active state of the test case.

        Forces all test cases and test modules held by this test module
        to be set to the same active status

        If cascade is True, the parent test module will be prompted
        to check it's current active status.
        """
        if self._active:
            if not is_active:
                self._active = False
                self.emit('inactive')
                if cascade:
                    self.parent._update_active()
                for testModule in self.values():
                    testModule.set_active(False, cascade=False)
        else:
            if is_active:
                self._active = True
                self.emit('active')
                if cascade:
                    self.parent._update_active()
                for testModule in self.values():
                    testModule.set_active(True, cascade=False)

    def toggle_active(self):
        "Toggle the current active status of this test case"
        self.set_active(not self.active)

    def find_tests(self, active=True, status=None, labels=None):
        """Find the test labels matching the search criteria.

        This will check:
            * active: if the method is currently an active test
            * status: if the last run status of the method is in the provided list
            * labels: if the method label is in the provided list

        Returns a count of tests found, plus the labels needed to
        execute those tests.
        """
        tests = []
        count = 0

        found_partial = False
        for testModule_name, testModule in self.items():
            include = True

            # If only active tests have been requested, the module
            # must be active.
            if active and not testModule.active:
                include = False

            # If a list of test labels has been provided, either the
            # module, or a test *in* the module, must be named explicitly.
            if labels:
                if testModule.path in labels:
                    # The module is named explicitly. Include all active
                    # subtests of this module
                    subcount, subtests = testModule.find_tests(True, status)
                else:
                    # The module isn't named. Look for all subtests.
                    # Search for subtests that match.
                    subcount, subtests = testModule.find_tests(active, status, labels)
            else:
                subcount, subtests = testModule.find_tests(active, status)

            if include:
                count = count + subcount

                if isinstance(subtests, list):
                    found_partial = True
                    tests.extend(subtests)
                else:
                    tests.append(subtests)

        # No partials found; just reference the app.
        if not found_partial:
            return count, self.path

        return count, tests

    def _purge(self, timestamp):
        """Search all submodules and test cases looking for stale test methods.

        Purge any test module without any test cases, and any test Case with no
        test methods.
        """
        for testModule_name, testModule in self.items():
            testModule._purge(timestamp)
            if len(testModule) == 0:
                self.pop(testModule_name)

    def _update_active(self):
        "Check the active status of all child nodes, and update the status of this node accordingly"
        for subModule_name, subModule in self.items():
            if subModule.active:
                self.set_active(True)
                return
        self.set_active(False)


class Project(dict, EventSource):
    """A data representation of an project, containing 1+ test apps.
    """
    def __init__(self):
        super(Project, self).__init__()
        self.errors = []
        self.coverage = False

    def __repr__(self):
        return u'Project'

    @classmethod
    def add_arguments(cls, parser):
        """Add project specific commandline arguments to the *parser*
        object. *parser* is an instance of argparse.ArgumentParser.
        """
        pass

    @property
    def path(self):
        "The dotted-path name that identifies this project to the test runner"
        return ''

    def find_tests(self, active=True, status=None, labels=None):
        """Find the test labels matching the search criteria.

        Returns a count of tests found, plus the labels needed to
        execute those tests.
        """
        tests = []
        count = 0

        found_partial = False
        for testApp_name, testApp in self.items():
            include = True

            # If only active tests have been requested, the module
            # must be active.
            if active and not testApp.active:
                include = False

            # If a list of test labels has been provided, either the
            # module, or a test *in* the module, must be named explicitly.
            if labels:
                if testApp.path in labels:
                    # The module is named explicitly. Include all active
                    # subtests of this module
                    subcount, subtests = testApp.find_tests(True, status)
                else:
                    # The module isn't named. Look for all subtests.
                    # Search for subtests that match.
                    subcount, subtests = testApp.find_tests(active, status, labels)
            else:
                subcount, subtests = testApp.find_tests(active, status)

            if include:
                count = count + subcount

                if isinstance(subtests, list):
                    found_partial = True
                    tests.extend(subtests)
                else:
                    tests.append(subtests)

        # No partials found; just reference the app.
        if not found_partial:
            return count, []

        return count, tests

    def confirm_exists(self, test_label, timestamp=None):
        """Confirm that the given test label exists in the current data model.

        If it doesn't, create a representation for it.
        """
        parts = test_label.split('.')
        if len(parts) < 2:
            return

        parentModule = self
        for testModule_name in parts[:-2]:
            try:
                testModule = parentModule[testModule_name]
            except KeyError:
                testModule = TestModule(testModule_name, parentModule)
            parentModule = testModule

        try:
            testCase = parentModule[parts[-2]]
        except KeyError:
            testCase = TestCase(parts[-2], parentModule)

        try:
            testMethod = testCase[parts[-1]]
        except KeyError:
            testMethod = TestMethod(parts[-1], testCase)

        testMethod.timestamp = timestamp
        return testMethod

    def refresh(self, test_list, errors=None):
        """Refresh the project representation so that it contains only the tests in test_list

        test_list should be a list of dotted-path test names.
        """
        timestamp = datetime.now()

        # Make sure there is a data representation for every test in the list.
        for test_label in test_list:
            self.confirm_exists(test_label, timestamp)

        for testModule_name, testModule in self.items():
            testModule._purge(timestamp)
            if len(testModule) == 0:
                self.pop(testModule_name)

        self.errors = errors if errors is not None else []

    def _update_active(self):
        "Exists for API consistency"
        pass

########NEW FILE########
__FILENAME__ = pipes
from __future__ import absolute_import

import json
from StringIO import StringIO
import sys
import time
import traceback

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


def trim_docstring(docstring):
    """Trim leading spaces in docstring indentation.

    Algorithm taken from PEP 257:
        http://www.python.org/dev/peps/pep-0257/#id20
    """
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


class PipedTestResult(unittest.result.TestResult):
    """A test result class that can print test results in a machine-parseable format.

    Used by PipedTestRunner.
    """
    RESULT_SEPARATOR = '\x1f'  # ASCII US (Unit Separator)

    def __init__(self, stream, use_old_discovery=True):
        super(PipedTestResult, self).__init__()
        self.stream = stream
        self.use_old_discovery = use_old_discovery
        self._first = True

        # Create a clean buffer for stdout content.
        self._stdout = StringIO()
        sys.stdout = self._stdout

        # The test runner is very lightly stateful. It's possible
        # for a test to raise an error before the test has actually
        # started; we need to make sure that we output a header line
        # for the misbehaving test.
        self._current_test = None

    def description(self, test):
        try:
            # Wrapped _ErrorHolder objects have their own description
            return trim_docstring(test.description)
        except AttributeError:
            # Fall back to the docstring on the method itself.
            if test._testMethodDoc:
                return trim_docstring(test._testMethodDoc)
            else:
                return 'No description'

    def startTest(self, test):
        super(PipedTestResult, self).startTest(test)
        # We know we're starting a new test - record it.
        self._current_test = test
        self._stdout = StringIO()
        sys.stdout = self._stdout

        if self.use_old_discovery:
            parts = test.id().split('.')
            tests_index = parts.index('tests')
            path = '%s.%s.%s' % (parts[tests_index - 1], parts[-2], parts[-1])
        else:
            path = test.id()

        body = {
            'path': path,
            'start_time': time.time()
        }
        if self._first:
            self.stream.write(PipedTestRunner.START_TEST_RESULTS + '\n')
            self._first = False
        else:
            self.stream.write(self.RESULT_SEPARATOR + '\n')
        self.stream.write('%s\n' % json.dumps(body))
        self.stream.flush()

    def addSuccess(self, test):
        super(PipedTestResult, self).addSuccess(test)
        body = {
            'status': 'OK',
            'end_time': time.time(),
            'description': self.description(test),
            'output': self._stdout.getvalue(),
        }
        self.stream.write('%s\n' % json.dumps(body))
        self.stream.flush()
        self._current_test = None

    def addError(self, test, err):
        # If there's no current test, the error occurred during test
        # setup. Output a test start line so the protocol isn't confused.
        if self._current_test is None:
            self.startTest(test)

        super(PipedTestResult, self).addError(test, err)
        body = {
            'status': 'E',
            'end_time': time.time(),
            'description': self.description(test),
            'error': '\n'.join(traceback.format_exception(*err)),
            'output': self._stdout.getvalue(),
        }
        self.stream.write('%s\n' % json.dumps(body))
        self.stream.flush()
        self._current_test = None

    def addFailure(self, test, err):
        super(PipedTestResult, self).addFailure(test, err)
        body = {
            'status': 'F',
            'end_time': time.time(),
            'description': self.description(test),
            'error': '\n'.join(traceback.format_exception(*err)),
            'output': self._stdout.getvalue(),
        }
        self.stream.write('%s\n' % json.dumps(body))
        self.stream.flush()
        self._current_test = None

    def addSkip(self, test, reason):
        super(PipedTestResult, self).addSkip(test, reason)
        body = {
            'status': 's',
            'end_time': time.time(),
            'description': self.description(test),
            'error': reason,
            'output': self._stdout.getvalue(),
        }
        self.stream.write('%s\n' % json.dumps(body))
        self.stream.flush()
        self._current_test = None

    def addExpectedFailure(self, test, err):
        super(PipedTestResult, self).addExpectedFailure(test, err)
        body = {
            'status': 'x',
            'end_time': time.time(),
            'description': self.description(test),
            'error': '\n'.join(traceback.format_exception(*err)),
            'output': self._stdout.getvalue(),
        }
        self.stream.write('%s\n' % json.dumps(body))
        self.stream.flush()
        self._current_test = None

    def addUnexpectedSuccess(self, test):
        super(PipedTestResult, self).addUnexpectedSuccess(test)
        body = {
            'status': 'u',
            'end_time': time.time(),
            'description': self.description(test),
            'output': self._stdout.getvalue(),
        }
        self.stream.write('%s\n' % json.dumps(body))
        self.stream.flush()
        self._current_test = None


class PipedTestRunner(unittest.TextTestRunner):
    """A test runner class that displays results in machine-parseable format.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    START_TEST_RESULTS = '\x02'  # ASCII STX (Start of Text)
    END_TEST_RESULTS = '\x03'    # ASCII ETX (End of Text)

    def __init__(self, stream=sys.stdout, use_old_discovery=False):
        self.stream = stream
        self.use_old_discovery = use_old_discovery

    def run(self, test):
        "Run the given test case or test suite."
        # Remeber stdout reference so it can be restored later
        old_stdout = sys.stdout

        # Create the result pipe, and run the tests with it.
        result = PipedTestResult(self.stream, self.use_old_discovery)
        test(result)

        # Report end of test run
        self.stream.write(self.END_TEST_RESULTS + '\n')
        self.stream.flush()

        # Restore the stdout reference
        sys.stdout = old_stdout

        return result

########NEW FILE########
__FILENAME__ = discoverer
'''
The whole purpose of this module is to generate printed output.
It should be of the form:

'module.testcase.specifictest'
'module.testcase.specifictest2'
'module2.testcase.specifictest'

etc

Its primary API is the command-line, but it can
just as easily be called programmatically (see __main__)
'''

import unittest


def consume(iterable):
    input = list(iterable)
    while input:
        item = input.pop(0)
        try:
            data = iter(item)
            input = list(data) + input
        except:
            yield item

class PyTestDiscoverer:

    def __init__(self):

        self.collected_tests = []


    def __str__(self):
        '''
        Builds the dotted namespace expected by cricket
        '''

        resultstr = '\n'.join(self.collected_tests)

        return resultstr.strip()


    def collect_tests(self):
        '''
        Collect a list of potentially runnable tests
        '''
        
        loader = unittest.TestLoader()
        suite = loader.discover('.')
        flatresults = list(consume(suite))
        named = [r.id() for r in flatresults]
        self.collected_tests = named

            
if __name__ == '__main__':

    PTD = PyTestDiscoverer()
    PTD.collect_tests()
    print str(PTD)
########NEW FILE########
__FILENAME__ = executor
'''
This is a thing which, when run, produces a stream
of well-formed test result outputs. Its processing is
initiated by the top-level Executor class.

Its main API is the command line, but it's just as sensible to
call into it. See __main__ for usage
'''
import argparse
import unittest

try:
    from coverage import coverage
except ImportError:
    coverage = None

from cricket import pipes


class PyTestExecutor(object):
    '''
    This is a thing which, when run, produces a stream
    of well-formed test result outputs. Its processing is
    initiated by the top-level Executor class
    '''

    def __init__(self):

        # Allows the executor to run a specified list of tests
        self.specified_list = None

    def run_only(self, specified_list):
        self.specified_list = specified_list

    def stream_suite(self, suite):

        pipes.PipedTestRunner().run(suite)

    def stream_results(self):
        '''
        1.) Discover all tests if necessary
        2.) Otherwise fetch specific tests
        3.) Execute-and-stream
        '''

        loader = unittest.TestLoader()

        if not self.specified_list:
            suite = loader.discover('.')
            self.stream_suite(suite)
        else:
            for module in self.specified_list:
                suite = loader.loadTestsFromName(module)
                self.stream_suite(suite)


class PyTestCoverageExecutor(PyTestExecutor):
    '''
    A version of PyTestExecutor that gathers coverage data.
    '''
    def stream_suite(self, suite):
        cov = coverage()
        cov.start()
        super(PyTestCoverageExecutor, self).stream_suite(suite)
        cov.stop()
        cov.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--coverage", help="Generate coverage data for the test run", action="store_true")
    parser.add_argument(
        'labels', nargs=argparse.REMAINDER,
        help='Test labels to run.'
    )

    options = parser.parse_args()

    if options.coverage:
        PTE = PyTestCoverageExecutor()
    else:
        PTE = PyTestExecutor()

    if options.labels:
        PTE.run_only(options.labels)
    PTE.stream_results()

########NEW FILE########
__FILENAME__ = model
import sys

from cricket.model import Project

class UnittestProject(Project):

    def __init__(self, options=None):
        super(UnittestProject, self).__init__()

    def discover_commandline(self):
        "Command line: Discover all available tests in a project."
        return [sys.executable, '-m', 'cricket.unittest.discoverer']

    def execute_commandline(self, labels):
        "Return the command line to execute the specified test labels"
        args = [sys.executable, '-m', 'cricket.unittest.executor']
        if self.coverage:
            args.append('--coverage')
        return args + labels
########NEW FILE########
__FILENAME__ = __main__
'''
This is the main entry point for running unittest test suites.
'''
from cricket.main import main as cricket_main
from cricket.unittest.model import UnittestProject


def main():
    cricket_main(UnittestProject)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = view
"""A module containing a visual representation of the testModule.

This is the "View" of the MVC world.
"""
import subprocess
from Tkinter import *
from tkFont import *
from ttk import *
import tkMessageBox
import webbrowser

# Check for the existence of coverage and duvet
try:
    import coverage
    try:
        import duvet
    except ImportError:
        duvet = None
except ImportError:
    coverage = None
    duvet = None

from tkreadonly import ReadOnlyText

from cricket import VERSION, NUM_VERSION
from cricket.model import TestMethod, TestCase, TestModule
from cricket.executor import Executor


# Display constants for test status
STATUS = {
    TestMethod.STATUS_PASS: {
        'description': u'Pass',
        'symbol': u'\u25cf',
        'tag': 'pass',
        'color': '#28C025',
    },
    TestMethod.STATUS_SKIP: {
        'description': u'Skipped',
        'symbol': u'S',
        'tag': 'skip',
        'color': '#259EBF'
    },
    TestMethod.STATUS_FAIL: {
        'description': u'Failure',
        'symbol': u'F',
        'tag': 'fail',
        'color': '#E32C2E'
    },
    TestMethod.STATUS_EXPECTED_FAIL: {
        'description': u'Expected\n  failure',
        'symbol': u'X',
        'tag': 'expected',
        'color': '#3C25BF'
    },
    TestMethod.STATUS_UNEXPECTED_SUCCESS: {
        'description': u'Unexpected\n   success',
        'symbol': u'U',
        'tag': 'unexpected',
        'color': '#C82788'
    },
    TestMethod.STATUS_ERROR: {
        'description': 'Error',
        'symbol': u'E',
        'tag': 'error',
        'color': '#E4742C'
    },
}

STATUS_DEFAULT = {
    'description': 'Not\nexecuted',
    'symbol': u'',
    'tag': None,
    'color': '#BFBFBF',
}


class MainWindow(object):
    def __init__(self, root):
        '''
        -----------------------------------------------------
        | main button toolbar                               |
        -----------------------------------------------------
        |       < ma | in content area >                    |
        |            |                                      |
        |  left      |              right                   |
        |  control   |              details frame           |
        |  tree      |              / output viewer         |
        |  area      |                                      |
        -----------------------------------------------------
        |     status bar area                               |
        -----------------------------------------------------

        '''

        self._project = None
        self.executor = None

        # Root window
        self.root = root
        self.root.title('Cricket')
        self.root.geometry('1024x768')

        # Prevent the menus from having the empty tearoff entry
        self.root.option_add('*tearOff', FALSE)
        # Catch the close button
        self.root.protocol("WM_DELETE_WINDOW", self.cmd_quit)
        # Catch the "quit" event.
        self.root.createcommand('exit', self.cmd_quit)

        # Setup the menu
        self._setup_menubar()

        # Set up the main content for the window.
        self._setup_button_toolbar()
        self._setup_main_content()
        self._setup_status_bar()

        # Now configure the weights for the root frame
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        # Set up listeners for runner events.
        Executor.bind('test_status_update', self.on_executorStatusUpdate)
        Executor.bind('test_start', self.on_executorTestStart)
        Executor.bind('test_end', self.on_executorTestEnd)
        Executor.bind('suite_end', self.on_executorSuiteEnd)
        Executor.bind('suite_error', self.on_executorSuiteError)

        # Now that we've laid out the grid, hide the error and output text
        # until we actually have an error/output to display
        self._hide_test_output()
        self._hide_test_errors()

    ######################################################
    # Internal GUI layout methods.
    ######################################################

    def _setup_menubar(self):
        # Menubar
        self.menubar = Menu(self.root)

        # self.menu_Apple = Menu(self.menubar, name='Apple')
        # self.menubar.add_cascade(menu=self.menu_Apple)

        self.menu_file = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label='File')

        self.menu_test = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_test, label='Test')

        self.menu_beeware = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_beeware, label='BeeWare')

        self.menu_help = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_help, label='Help')

        # self.menu_Apple.add_command(label='Test', command=self.cmd_dummy)

        # self.menu_file.add_command(label='New', command=self.cmd_dummy, accelerator="Command-N")
        # self.menu_file.add_command(label='Open...', command=self.cmd_dummy)
        # self.menu_file.add_command(label='Close', command=self.cmd_dummy)

        self.menu_test.add_command(label='Run all', command=self.cmd_run_all)
        self.menu_test.add_command(label='Run selected tests', command=self.cmd_run_selected)
        self.menu_test.add_command(label='Re-run failed tests', command=self.cmd_rerun)

        self.menu_beeware.add_command(label='Open Duvet...', command=self.cmd_open_duvet, state=DISABLED if duvet is None else ACTIVE)

        self.menu_help.add_command(label='Open Documentation', command=self.cmd_cricket_docs)
        self.menu_help.add_command(label='Open Cricket project page', command=self.cmd_cricket_page)
        self.menu_help.add_command(label='Open Cricket on GitHub', command=self.cmd_cricket_github)
        self.menu_help.add_command(label='Open BeeWare project page', command=self.cmd_beeware_page)

        # last step - configure the menubar
        self.root['menu'] = self.menubar

    def _setup_button_toolbar(self):
        '''
        The button toolbar runs as a horizontal area at the top of the GUI.
        It is a persistent GUI component
        '''

        # Main toolbar
        self.toolbar = Frame(self.root)
        self.toolbar.grid(column=0, row=0, sticky=(W, E))

        # Buttons on the toolbar
        self.stop_button = Button(self.toolbar, text='Stop', command=self.cmd_stop, state=DISABLED)
        self.stop_button.grid(column=0, row=0)

        self.run_all_button = Button(self.toolbar, text='Run all', command=self.cmd_run_all)
        self.run_all_button.grid(column=1, row=0)

        self.run_selected_button = Button(self.toolbar, text='Run selected',
            command=self.cmd_run_selected, state=DISABLED)
        self.run_selected_button.grid(column=2, row=0)

        self.rerun_button = Button(self.toolbar, text='Re-run', command=self.cmd_rerun, state=DISABLED)
        self.rerun_button.grid(column=3, row=0)

        self.coverage = StringVar()
        self.coverage_checkbox = Checkbutton(self.toolbar, text='Generate coverage',
                                    command=self.on_coverageChange, variable=self.coverage)
        self.coverage_checkbox.grid(column=4, row=0)

        # If coverage is available, enable it by default.
        # Otherwise, disable the widget
        if coverage:
            self.coverage.set('1')
        else:
            self.coverage.set('0')
            self.coverage_checkbox.configure(state=DISABLED)

        self.toolbar.columnconfigure(0, weight=0)
        self.toolbar.rowconfigure(0, weight=1)

    def _setup_main_content(self):
        '''
        Sets up the main content area. It is a persistent GUI component
        '''

        # Main content area
        self.content = PanedWindow(self.root, orient=HORIZONTAL)
        self.content.grid(column=0, row=1, sticky=(N, S, E, W))

        # Create the tree/control area on the left frame
        self._setup_left_frame()
        self._setup_all_tests_tree()
        self._setup_problem_tests_tree()

        # Create the output/viewer area on the right frame
        self._setup_right_frame()

        # Set up weights for the left frame's content
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.content.pane(0, weight=1)
        self.content.pane(1, weight=2)

    def _setup_left_frame(self):
        '''
        The left frame mostly consists of the tree widget
        '''

        # The left-hand side frame on the main content area
        # The tabs for the two trees
        self.tree_notebook = Notebook(self.content, padding=(0, 5, 0, 5))
        self.content.add(self.tree_notebook)

    def _setup_all_tests_tree(self):
        # The tree for all tests
        self.all_tests_tree_frame = Frame(self.content)
        self.all_tests_tree_frame.grid(column=0, row=0, sticky=(N, S, E, W))
        self.tree_notebook.add(self.all_tests_tree_frame, text='All tests')

        self.all_tests_tree = Treeview(self.all_tests_tree_frame)
        self.all_tests_tree.grid(column=0, row=0, sticky=(N, S, E, W))

        # Set up the tag colors for tree nodes.
        for status, config in STATUS.items():
            self.all_tests_tree.tag_configure(config['tag'], foreground=config['color'])
        self.all_tests_tree.tag_configure('inactive', foreground='lightgray')

        # Listen for button clicks on tree nodes
        self.all_tests_tree.tag_bind('TestModule', '<Double-Button-1>', self.on_testModuleClicked)
        self.all_tests_tree.tag_bind('TestCase', '<Double-Button-1>', self.on_testCaseClicked)
        self.all_tests_tree.tag_bind('TestMethod', '<Double-Button-1>', self.on_testMethodClicked)

        self.all_tests_tree.tag_bind('TestModule', '<<TreeviewSelect>>', self.on_testModuleSelected)
        self.all_tests_tree.tag_bind('TestCase', '<<TreeviewSelect>>', self.on_testCaseSelected)
        self.all_tests_tree.tag_bind('TestMethod', '<<TreeviewSelect>>', self.on_testMethodSelected)

        # The tree's vertical scrollbar
        self.all_tests_tree_scrollbar = Scrollbar(self.all_tests_tree_frame, orient=VERTICAL)
        self.all_tests_tree_scrollbar.grid(column=1, row=0, sticky=(N, S))

        # Tie the scrollbar to the text views, and the text views
        # to each other.
        self.all_tests_tree.config(yscrollcommand=self.all_tests_tree_scrollbar.set)
        self.all_tests_tree_scrollbar.config(command=self.all_tests_tree.yview)

        # Setup weights for the "All Tests" tree
        self.all_tests_tree_frame.columnconfigure(0, weight=1)
        self.all_tests_tree_frame.columnconfigure(1, weight=0)
        self.all_tests_tree_frame.rowconfigure(0, weight=1)

    def _setup_problem_tests_tree(self):
        # The tree for problem tests
        self.problem_tests_tree_frame = Frame(self.content)
        self.problem_tests_tree_frame.grid(column=0, row=0, sticky=(N, S, E, W))
        self.tree_notebook.add(self.problem_tests_tree_frame, text='Problems')

        self.problem_tests_tree = Treeview(self.problem_tests_tree_frame)
        self.problem_tests_tree.grid(column=0, row=0, sticky=(N, S, E, W))

        # Set up the tag colors for tree nodes.
        for status, config in STATUS.items():
            self.problem_tests_tree.tag_configure(config['tag'], foreground=config['color'])
        self.problem_tests_tree.tag_configure('inactive', foreground='lightgray')

        # Problem tree only deals with selection, not clicks.
        self.problem_tests_tree.tag_bind('TestModule', '<<TreeviewSelect>>', self.on_testModuleSelected)
        self.problem_tests_tree.tag_bind('TestCase', '<<TreeviewSelect>>', self.on_testCaseSelected)
        self.problem_tests_tree.tag_bind('TestMethod', '<<TreeviewSelect>>', self.on_testMethodSelected)

        # The tree's vertical scrollbar
        self.problem_tests_tree_scrollbar = Scrollbar(self.problem_tests_tree_frame, orient=VERTICAL)
        self.problem_tests_tree_scrollbar.grid(column=1, row=0, sticky=(N, S))

        # Tie the scrollbar to the text views, and the text views
        # to each other.
        self.problem_tests_tree.config(yscrollcommand=self.problem_tests_tree_scrollbar.set)
        self.problem_tests_tree_scrollbar.config(command=self.all_tests_tree.yview)

        # Setup weights for the problems tree
        self.problem_tests_tree_frame.columnconfigure(0, weight=1)
        self.problem_tests_tree_frame.columnconfigure(1, weight=0)
        self.problem_tests_tree_frame.rowconfigure(0, weight=1)

    def _setup_right_frame(self):
        '''
        The right frame is basically the "output viewer" space
        '''

        # The right-hand side frame on the main content area
        self.details_frame = Frame(self.content)
        self.details_frame.grid(column=0, row=0, sticky=(N, S, E, W))
        self.content.add(self.details_frame)

        # Set up the content in the details panel
        # Test Name
        self.name_label = Label(self.details_frame, text='Name:')
        self.name_label.grid(column=0, row=0, pady=5, sticky=(E,))

        self.name = StringVar()
        self.name_widget = Entry(self.details_frame, textvariable=self.name)
        self.name_widget.configure(state='readonly')
        self.name_widget.grid(column=1, row=0, pady=5, sticky=(W, E))

        # Test status
        self.test_status = StringVar()
        self.test_status_widget = Label(self.details_frame, textvariable=self.test_status, width=1, anchor=CENTER)
        f = Font(font=self.test_status_widget['font'])
        f['weight'] = 'bold'
        f['size'] = 50
        self.test_status_widget.config(font=f)
        self.test_status_widget.grid(column=2, row=0, padx=15, pady=5, rowspan=2, sticky=(N, W, E, S))

        # Test duration
        self.duration_label = Label(self.details_frame, text='Duration:')
        self.duration_label.grid(column=0, row=1, pady=5, sticky=(E,))

        self.duration = StringVar()
        self.duration_widget = Entry(self.details_frame, textvariable=self.duration)
        self.duration_widget.grid(column=1, row=1, pady=5, sticky=(E, W,))

        # Test description
        self.description_label = Label(self.details_frame, text='Description:')
        self.description_label.grid(column=0, row=2, pady=5, sticky=(N, E,))

        self.description = ReadOnlyText(self.details_frame, width=80, height=4)
        self.description.grid(column=1, row=2, pady=5, columnspan=2, sticky=(N, S, E, W,))

        self.description_scrollbar = Scrollbar(self.details_frame, orient=VERTICAL)
        self.description_scrollbar.grid(column=3, row=2, pady=5, sticky=(N, S))
        self.description.config(yscrollcommand=self.description_scrollbar.set)
        self.description_scrollbar.config(command=self.description.yview)

        # Test output
        self.output_label = Label(self.details_frame, text='Output:')
        self.output_label.grid(column=0, row=3, pady=5, sticky=(N, E,))

        self.output = ReadOnlyText(self.details_frame, width=80, height=4)
        self.output.grid(column=1, row=3, pady=5, columnspan=2, sticky=(N, S, E, W,))

        self.output_scrollbar = Scrollbar(self.details_frame, orient=VERTICAL)
        self.output_scrollbar.grid(column=3, row=3, pady=5, sticky=(N, S))
        self.output.config(yscrollcommand=self.output_scrollbar.set)
        self.output_scrollbar.config(command=self.description.yview)

        # Error message
        self.error_label = Label(self.details_frame, text='Error:')
        self.error_label.grid(column=0, row=4, pady=5, sticky=(N, E,))

        self.error = ReadOnlyText(self.details_frame, width=80)
        self.error.grid(column=1, row=4, pady=5, columnspan=2, sticky=(N, S, E, W))

        self.error_scrollbar = Scrollbar(self.details_frame, orient=VERTICAL)
        self.error_scrollbar.grid(column=3, row=4, pady=5, sticky=(N, S))
        self.error.config(yscrollcommand=self.error_scrollbar.set)
        self.error_scrollbar.config(command=self.error.yview)

        # Set up GUI weights for the details frame
        self.details_frame.columnconfigure(0, weight=0)
        self.details_frame.columnconfigure(1, weight=1)
        self.details_frame.columnconfigure(2, weight=0)
        self.details_frame.columnconfigure(3, weight=0)
        self.details_frame.columnconfigure(4, weight=0)
        self.details_frame.rowconfigure(0, weight=0)
        self.details_frame.rowconfigure(1, weight=0)
        self.details_frame.rowconfigure(2, weight=1)
        self.details_frame.rowconfigure(3, weight=5)
        self.details_frame.rowconfigure(4, weight=10)

    def _setup_status_bar(self):
        # Status bar
        self.statusbar = Frame(self.root)
        self.statusbar.grid(column=0, row=2, sticky=(W, E))

        # Current status
        self.run_status = StringVar()
        self.run_status_label = Label(self.statusbar, textvariable=self.run_status)
        self.run_status_label.grid(column=0, row=0, sticky=(W, E))
        self.run_status.set('Not running')

        # Test result summary
        self.run_summary = StringVar()
        self.run_summary_label = Label(self.statusbar, textvariable=self.run_summary)
        self.run_summary_label.grid(column=1, row=0, sticky=(W, E))
        self.run_summary.set('T:0 P:0 F:0 E:0 X:0 U:0 S:0')

        # Test progress
        self.progress_value = IntVar()
        self.progress = Progressbar(self.statusbar, orient=HORIZONTAL, length=200, mode='determinate', maximum=100, variable=self.progress_value)
        self.progress.grid(column=2, row=0, sticky=(W, E))

        # Main window resize handle
        self.grip = Sizegrip(self.statusbar)
        self.grip.grid(column=3, row=0, sticky=(S, E))

        # Set up weights for status bar frame
        self.statusbar.columnconfigure(0, weight=1)
        self.statusbar.columnconfigure(1, weight=0)
        self.statusbar.columnconfigure(2, weight=0)
        self.statusbar.columnconfigure(3, weight=0)
        self.statusbar.rowconfigure(0, weight=1)

    ######################################################
    # Utility methods for inspecting current GUI state
    ######################################################

    @property
    def current_test_tree(self):
        "Check the tree notebook to return the currently selected tree."
        current_tree_id = self.tree_notebook.select()
        if current_tree_id == self.problem_tests_tree_frame._w:
            return self.problem_tests_tree
        else:
            return self.all_tests_tree

    ######################################################
    # Handlers for setting a new project
    ######################################################

    @property
    def project(self):
        return self._project

    def _add_test_module(self, parentNode, testModule):
        testModule_node = self.all_tests_tree.insert(
            parentNode, 'end', testModule.path,
            text=testModule.name,
            tags=['TestModule', 'active'],
            open=True)

        for subModuleName, subModule in sorted(testModule.items()):
            if isinstance(subModule, TestModule):
                self._add_test_module(testModule_node, subModule)
            else:
                testCase = subModule
                testCase_node = self.all_tests_tree.insert(
                    testModule_node, 'end', testCase.path,
                    text=testCase.name,
                    tags=['TestCase', 'active'],
                    open=True
                )

                for testMethod_name, testMethod in sorted(testCase.items()):
                    self.all_tests_tree.insert(
                        testCase_node, 'end', testMethod.path,
                        text=testMethod.name,
                        tags=['TestMethod', 'active'],
                        open=True
                    )

    @project.setter
    def project(self, project):
        self._project = project

        # Get a count of active tests to display in the status bar.
        count, labels = self.project.find_tests(True)
        self.run_summary.set('T:%s P:0 F:0 E:0 X:0 U:0 S:0' % count)

        # Populate the initial tree nodes. This is recursive, because
        # the tree could be of arbitrary depth.
        for testModule_name, testModule in sorted(project.items()):
            self._add_test_module('', testModule)

        # Listen for any state changes on nodes in the tree
        TestModule.bind('active', self.on_nodeActive)
        TestCase.bind('active', self.on_nodeActive)
        TestMethod.bind('active', self.on_nodeActive)

        TestModule.bind('inactive', self.on_nodeInactive)
        TestCase.bind('inactive', self.on_nodeInactive)
        TestMethod.bind('inactive', self.on_nodeInactive)

        # Listen for new nodes added to the tree
        TestModule.bind('new', self.on_nodeAdded)
        TestCase.bind('new', self.on_nodeAdded)
        TestMethod.bind('new', self.on_nodeAdded)

        # Listen for any status updates on nodes in the tree.
        TestMethod.bind('status_update', self.on_nodeStatusUpdate)

        # Update the project to make sure coverage status matches the GUI
        self.on_coverageChange()

    ######################################################
    # TK Main loop
    ######################################################

    def mainloop(self):
        self.root.mainloop()

    ######################################################
    # User commands
    ######################################################

    def cmd_quit(self):
        "Command: Quit"
        # If the runner is currently running, kill it.
        self.stop()

        self.root.quit()

    def cmd_stop(self, event=None):
        "Command: The stop button has been pressed"
        self.stop()

    def cmd_run_all(self, event=None):
        "Command: The Run all button has been pressed"
        # If the executor isn't currently running, we can
        # start a test run.
        if not self.executor or not self.executor.is_running:
            self.run(active=True)

    def cmd_run_selected(self, event=None):
        "Command: The 'run selected' button has been pressed"
        current_tree = self.current_test_tree

        # If a node is selected, it needs to be made active
        for path in current_tree.selection():
            parts = path.split('.')
            testModule = self.project
            for part in parts:
                testModule = testModule[part]

            testModule.set_active(True)

        # If the executor isn't currently running, we can
        # start a test run.
        if not self.executor or not self.executor.is_running:
            self.run(labels=set(current_tree.selection()))

    def cmd_rerun(self, event=None):
        "Command: The run/stop button has been pressed"
        # If the executor isn't currently running, we can
        # start a test run.
        if not self.executor or not self.executor.is_running:
            self.run(status=set(TestMethod.FAILING_STATES))

    def cmd_open_duvet(self, event=None):
        "Command: Open Duvet"
        try:
            subprocess.Popen('duvet')
        except Exception, e:
            tkMessageBox.showerror('Unable to start Duvet: %s' % e)

    def cmd_cricket_page(self):
        "Show the Cricket project page"
        webbrowser.open_new('http://pybee.org/cricket/')

    def cmd_beeware_page(self):
        "Show the Beeware project page"
        webbrowser.open_new('http://pybee.org/')

    def cmd_cricket_github(self):
        "Show the Cricket GitHub repo"
        webbrowser.open_new('http://github.com/pybee/cricket')

    def cmd_cricket_docs(self):
        "Show the Cricket documentation"
        # If this is a formal release, show the docs for that
        # version. otherwise, just show the head docs.
        if len(NUM_VERSION) == 3:
            webbrowser.open_new('http://cricket.readthedocs.org/en/v%s/' % VERSION)
        else:
            webbrowser.open_new('http://cricket.readthedocs.org/')

    ######################################################
    # GUI Callbacks
    ######################################################

    def on_testModuleClicked(self, event):
        "Event handler: a module has been clicked in the tree"
        parts = event.widget.focus().split('.')
        testModule = self.project
        for part in parts:
            testModule = testModule[part]

        testModule.toggle_active()

    def on_testCaseClicked(self, event):
        "Event handler: a test case has been clicked in the tree"
        parts = event.widget.focus().split('.')
        testCase = self.project
        for part in parts:
            testCase = testCase[part]

        testCase.toggle_active()

    def on_testMethodClicked(self, event):
        "Event handler: a test case has been clicked in the tree"
        parts = event.widget.focus().split('.')
        testMethod = self.project
        for part in parts:
            testMethod = testMethod[part]

        testMethod.toggle_active()

    def on_testModuleSelected(self, event):
        "Event handler: a test module has been selected in the tree"
        self.name.set('')
        self.test_status.set('')

        self.duration.set('')
        self.description.delete('1.0', END)

        self._hide_test_output()
        self._hide_test_errors()

        # update "run selected" button enabled state
        self.set_selected_button_state()

    def on_testCaseSelected(self, event):
        "Event handler: a test case has been selected in the tree"
        self.name.set('')
        self.test_status.set('')

        self.duration.set('')
        self.description.delete('1.0', END)

        self._hide_test_output()
        self._hide_test_errors()

        # update "run selected" button enabled state
        self.set_selected_button_state()

    def on_testMethodSelected(self, event):
        "Event handler: a test case has been selected in the tree"
        if len(event.widget.selection()) == 1:
            parts = event.widget.selection()[0].split('.')

            # Find the definition for the actual test method
            # out of the project.
            testMethod = self.project
            for part in parts:
                testMethod = testMethod[part]

            self.name.set(testMethod.path)

            self.description.delete('1.0', END)
            self.description.insert('1.0', testMethod.description)

            config = STATUS.get(testMethod.status, STATUS_DEFAULT)
            self.test_status_widget.config(foreground=config['color'])
            self.test_status.set(config['symbol'])

            if testMethod._result:
                # Test has been executed
                self.duration.set('%0.2fs' % testMethod._result['duration'])

                if testMethod.output:
                    self._show_test_output(testMethod.output)
                else:
                    self._hide_test_output()

                if testMethod.error:
                    self._show_test_errors(testMethod.error)
                else:
                    self._hide_test_errors()
            else:
                # Test hasn't been executed yet.
                self.duration.set('Not executed')

                self._hide_test_output()
                self._hide_test_errors()

        else:
            # Multiple tests selected
            self.name.set('')
            self.test_status.set('')

            self.duration.set('')
            self.description.delete('1.0', END)

            self._hide_test_output()
            self._hide_test_errors()

        # update "run selected" button enabled state
        self.set_selected_button_state()

    def on_nodeAdded(self, node):
        "Event handler: a new node has been added to the tree"
        self.all_tests_tree.insert(
            node.parent.path, 'end', node.path,
            text=node.name,
            tags=[node.__class__.__name__, 'active'],
            open=True
        )

    def on_nodeActive(self, node):
        "Event handler: a node on the tree has been made active"
        self.all_tests_tree.item(node.path, tags=[node.__class__.__name__, 'active'])
        self.all_tests_tree.item(node.path, open=True)

    def on_nodeInactive(self, node):
        "Event handler: a node on the tree has been made inactive"
        self.all_tests_tree.item(node.path, tags=[node.__class__.__name__, 'inactive'])
        self.all_tests_tree.item(node.path, open=False)

    def on_nodeStatusUpdate(self, node):
        "Event handler: a node on the tree has received a status update"
        self.all_tests_tree.item(node.path, tags=['TestMethod', STATUS[node.status]['tag']])

        if node.status in TestMethod.FAILING_STATES:
            # Test is in a failing state. Make sure it is on the problem tree,
            # with the correct current status.

            parts = node.path.split('.')
            parentModule = self.project
            for pos, part in enumerate(parts):
                path = '.'.join(parts[:pos+1])
                testModule = parentModule[part]

                if not self.problem_tests_tree.exists(path):
                    self.problem_tests_tree.insert(
                        parentModule.path, 'end', testModule.path,
                        text=testModule.name,
                        tags=[testModule.__class__.__name__, 'active'],
                        open=True
                    )

                parentModule = testModule

            self.problem_tests_tree.item(node.path, tags=['TestMethod', STATUS[node.status]['tag']])
        else:
            # Test passed; if it's on the problem tree, remove it.
            if self.problem_tests_tree.exists(node.path):
                self.problem_tests_tree.delete(node.path)

                # Check all parents of this node. Recursively remove
                # any parent has no children as a result of this deletion.
                has_children = False
                node = node.parent
                while node.path and not has_children:
                    if not self.problem_tests_tree.get_children(node.path):
                        self.problem_tests_tree.delete(node.path)
                    else:
                        has_children = True
                    node = node.parent

    def on_coverageChange(self):
        "Event handler: when the coverage checkbox has been toggled"
        self.project.coverage = self.coverage.get() == '1'

    def on_testProgress(self):
        "Event handler: a periodic update to poll the runner for output, generating GUI updates"
        if self.executor and self.executor.poll():
            self.root.after(100, self.on_testProgress)

    def on_executorStatusUpdate(self, event, update):
        "The executor has some progress to report"
        # Update the status line.
        self.run_status.set(update)

    def on_executorTestStart(self, event, test_path):
        "The executor has started running a new test."
        # Update status line, and set the tree item to active.
        self.run_status.set('Running %s...' % test_path)
        self.all_tests_tree.item(test_path, tags=['TestMethod', 'active'])

    def on_executorTestEnd(self, event, test_path, result, remaining_time):
        "The executor has finished running a test."
        # Update the progress meter
        self.progress_value.set(self.progress_value.get() + 1)

        # Update the run summary
        self.run_summary.set('T:%(total)s P:%(pass)s F:%(fail)s E:%(error)s X:%(expected)s U:%(unexpected)s S:%(skip)s, ~%(remaining)s remaining' % {
                'total': self.executor.total_count,
                'pass': self.executor.result_count.get(TestMethod.STATUS_PASS, 0),
                'fail': self.executor.result_count.get(TestMethod.STATUS_FAIL, 0),
                'error': self.executor.result_count.get(TestMethod.STATUS_ERROR, 0),
                'expected': self.executor.result_count.get(TestMethod.STATUS_EXPECTED_FAIL, 0),
                'unexpected': self.executor.result_count.get(TestMethod.STATUS_UNEXPECTED_SUCCESS, 0),
                'skip': self.executor.result_count.get(TestMethod.STATUS_SKIP, 0),
                'remaining': remaining_time
            })

        # If the test that just fininshed is the one (and only one)
        # selected on the tree, update the display.
        current_tree = self.current_test_tree
        if len(current_tree.selection()) == 1:
            # One test selected.
            if current_tree.selection()[0] == test_path:
                # If the test that just finished running is the selected
                # test, force reset the selection, which will generate a
                # selection event, forcing a refresh of the result page.
                current_tree.selection_set(current_tree.selection())
        else:
            # No or Multiple tests selected
            self.name.set('')
            self.test_status.set('')

            self.duration.set('')
            self.description.delete('1.0', END)

            self._hide_test_output()
            self._hide_test_errors()

    def on_executorSuiteEnd(self, event, error=None):
        "The test suite finished running."
        # Display the final results
        self.run_status.set('Finished.')

        if error:
            TestErrorsDialog(self.root, error)

        if self.executor.any_failed:
            dialog = tkMessageBox.showerror
        else:
            dialog = tkMessageBox.showinfo

        dialog(message=', '.join(
            '%d %s' % (count, TestMethod.STATUS_LABELS[state])
            for state, count in sorted(self.executor.result_count.items()))
        )

        # Reset the running summary.
        self.run_summary.set('T:%(total)s P:%(pass)s F:%(fail)s E:%(error)s X:%(expected)s U:%(unexpected)s S:%(skip)s' % {
                'total': self.executor.total_count,
                'pass': self.executor.result_count.get(TestMethod.STATUS_PASS, 0),
                'fail': self.executor.result_count.get(TestMethod.STATUS_FAIL, 0),
                'error': self.executor.result_count.get(TestMethod.STATUS_ERROR, 0),
                'expected': self.executor.result_count.get(TestMethod.STATUS_EXPECTED_FAIL, 0),
                'unexpected': self.executor.result_count.get(TestMethod.STATUS_UNEXPECTED_SUCCESS, 0),
                'skip': self.executor.result_count.get(TestMethod.STATUS_SKIP, 0),
            })

        # Reset the buttons
        self.reset_button_states_on_end()

        # Drop the reference to the executor
        self.executor = None

    def on_executorSuiteError(self, event, error):
        "An error occurred running the test suite."
        # Display the error in a dialog
        self.run_status.set('Error running test suite.')
        FailedTestDialog(self.root, error)

        # Reset the buttons
        self.reset_button_states_on_end()

        # Drop the reference to the executor
        self.executor = None

    def reset_button_states_on_end(self):
        "A test run has ended and we should enable or disable buttons as appropriate."
        self.stop_button.configure(state=DISABLED)
        self.run_all_button.configure(state=NORMAL)
        self.set_selected_button_state()
        if self.executor and self.executor.any_failed:
            self.rerun_button.configure(state=NORMAL)
        else:
            self.rerun_button.configure(state=DISABLED)

    def set_selected_button_state(self):
        if self.executor and self.executor.is_running:
            self.run_selected_button.configure(state=DISABLED)
        elif self.current_test_tree.selection():
            self.run_selected_button.configure(state=NORMAL)
        else:
            self.run_selected_button.configure(state=DISABLED)

    ######################################################
    # GUI utility methods
    ######################################################

    def run(self, active=True, status=None, labels=None):
        """Run the test suite.

        If active=True, only active tests will be run.
        If status is provided, only tests whose most recent run
            status matches the set provided will be executed.
        If labels is provided, only tests with those labels will
            be executed
        """
        count, labels = self.project.find_tests(active, status, labels)
        self.run_status.set('Running...')
        self.run_summary.set('T:%s P:0 F:0 E:0 X:0 U:0 S:0' % count)

        self.stop_button.configure(state=NORMAL)
        self.run_all_button.configure(state=DISABLED)
        self.run_selected_button.configure(state=DISABLED)
        self.rerun_button.configure(state=DISABLED)

        self.progress['maximum'] = count
        self.progress_value.set(0)

        # Create the runner
        self.executor = Executor(self.project, count, labels)

        # Queue the first progress handling event
        self.root.after(100, self.on_testProgress)

    def stop(self):
        "Stop the test suite."
        if self.executor and self.executor.is_running:
            self.run_status.set('Stopping...')

            self.executor.terminate()
            self.executor = None

            self.run_status.set('Stopped.')

            self.reset_button_states_on_end()

    def _hide_test_output(self):
        "Hide the test output panel on the test results page"
        self.output_label.grid_remove()
        self.output.grid_remove()
        self.output_scrollbar.grid_remove()
        self.details_frame.rowconfigure(3, weight=0)

    def _show_test_output(self, content):
        "Show the test output panel on the test results page"
        self.output.delete('1.0', END)
        self.output.insert('1.0', content)

        self.output_label.grid()
        self.output.grid()
        self.output_scrollbar.grid()
        self.details_frame.rowconfigure(3, weight=5)

    def _hide_test_errors(self):
        "Hide the test error panel on the test results page"
        self.error_label.grid_remove()
        self.error.grid_remove()
        self.error_scrollbar.grid_remove()

    def _show_test_errors(self, content):
        "Show the test error panel on the test results page"
        self.error.delete('1.0', END)
        self.error.insert('1.0', content)

        self.error_label.grid()
        self.error.grid()
        self.error_scrollbar.grid()


class StackTraceDialog(Toplevel):
    OK = 1
    CANCEL = 2

    def __init__(self, parent, title, label, trace, button_text='OK',
                 cancel_text='Cancel'):
        '''Show a dialog with a scrollable stack trace.

        Arguments:

            parent -- a parent window (the application window)
            title -- the title for the stack trace window
            label -- the label describing the stack trace
            trace -- the stack trace content to display.
            button_text -- the label for the button text ("OK" by default)
            cancel_text -- the label for the cancel button ("Cancel" by default)
        '''
        Toplevel.__init__(self, parent)

        self.withdraw()  # remain invisible for now

        # If the master is not viewable, don't
        # make the child transient, or else it
        # would be opened withdrawn
        if parent.winfo_viewable():
            self.transient(parent)

        self.title(title)

        self.parent = parent

        self.frame = Frame(self)
        self.frame.grid(column=0, row=0, sticky=(N, S, E, W))

        self.label = Label(self.frame, text=label)
        self.label.grid(column=0, row=0, padx=5, pady=5, sticky=(W, E))

        self.description = ReadOnlyText(self.frame, width=80, height=20)
        self.description.grid(column=0, columnspan=2, row=1, pady=5, sticky=(N, S, E, W,))

        self.description_scrollbar = Scrollbar(self.frame, orient=VERTICAL)
        self.description_scrollbar.grid(column=1, row=1, pady=5, sticky=(N, S, E))
        self.description.config(yscrollcommand=self.description_scrollbar.set)
        self.description_scrollbar.config(command=self.description.yview)

        self.description.insert('1.0', trace)

        if cancel_text is not None:
            self.cancel_button = Button(self.frame, text=cancel_text, command=self.cancel)
            self.cancel_button.grid(column=0, row=2, padx=5, pady=5, sticky=(E,))

        self.ok_button = Button(self.frame, text=button_text, command=self.ok, default=ACTIVE)
        self.ok_button.grid(column=1, row=2, padx=5, pady=5, sticky=(E,))


        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=0)

        self.frame.rowconfigure(0, weight=0)
        self.frame.rowconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=0)

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind('<Return>', self.ok)

        if self.parent is not None:
            self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                      parent.winfo_rooty()+50))

        self.deiconify()  # become visible now

        self.ok_button.focus_set()

        # wait for window to appear on screen before calling grab_set
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def ok(self, event=None):
        self.withdraw()
        self.update_idletasks()

        if self.parent is not None:
            self.parent.focus_set()
        self.destroy()
        self.status = self.OK

    def cancel(self, event=None):
        self.withdraw()
        self.update_idletasks()

        if self.parent is not None:
            self.parent.focus_set()

        self.destroy()
        self.status = self.CANCEL


class FailedTestDialog(StackTraceDialog):
    def __init__(self, parent, trace):
        '''Report an error when running a test suite.

        Arguments:

            parent -- a parent window (the application window)
            trace -- the stack trace content to display.
        '''
        StackTraceDialog.__init__(
            self,
            parent,
            'Error running test suite',
            'The following stack trace was generated when attempting to run the test suite:',
            trace,
            button_text='OK',
            cancel_text='Quit',
        )

    def cancel(self, event=None):
        StackTraceDialog.cancel(self, event=event)
        self.parent.quit()


class TestErrorsDialog(StackTraceDialog):
    def __init__(self, parent, trace):
        '''Show a dialog with a scrollable list of errors.

        Arguments:

            parent -- a parent window (the application window)
            error -- the error content to display.
        '''
        StackTraceDialog.__init__(
            self,
            parent,
            'Errors during test suite',
            ('The following errors were generated while running the test suite:'),
            trace,
            button_text='OK',
            cancel_text=None,
        )

    def cancel(self, event=None):
        StackTraceDialog.cancel(self, event=event)
        self.parent.quit()


class TestLoadErrorDialog(StackTraceDialog):
    def __init__(self, parent, trace):
        '''Show a dialog with a scrollable stack trace.

        Arguments:

            parent -- a parent window (the application window)
            trace -- the stack trace content to display.
        '''
        StackTraceDialog.__init__(
            self,
            parent,
            'Error discovering test suite',
            ('The following stack trace was generated when attempting to '
             'discover the test suite:'),
            trace,
            button_text='Retry',
            cancel_text='Quit',
        )

    def cancel(self, event=None):
        StackTraceDialog.cancel(self, event=event)
        self.parent.quit()


class IgnorableTestLoadErrorDialog(StackTraceDialog):
    def __init__(self, parent, trace):
        '''Show a dialog with a scrollable stack trace when loading
           tests turned up errors in stderr but they can safely be ignored.

        Arguments:

            parent -- a parent window (the application window)
            trace -- the stack trace content to display.
        '''
        StackTraceDialog.__init__(
            self,
            parent,
            'Error discovering test suite',
            ('The following error where captured during test discovery '
             'but running the tests might still work:'),
            trace,
            button_text='Continue',
            cancel_text='Quit',
        )

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Cricket documentation build configuration file, created by
# sphinx-quickstart on Sat Feb  9 10:44:39 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cricket

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Cricket'
copyright = u'2013, Russell Keith-Magee'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(str(n) for n in cricket.NUM_VERSION[:2])
# The full version, including alpha/beta/rc tags.
release = cricket.VERSION

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
html_theme = 'default'

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
htmlhelp_basename = 'Cricketdoc'


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
  ('index', 'Cricket.tex', u'Cricket Documentation',
   u'Russell Keith-Magee', 'manual'),
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
    ('index', 'cricket', u'Cricket Documentation',
     [u'Russell Keith-Magee'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Cricket', u'Cricket Documentation',
   u'Russell Keith-Magee', 'Cricket', 'A graphical tool to assist running test suites.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = test_models
from cricket.compat import unittest
from cricket.model import Project, TestModule, TestCase


class TestProject(unittest.TestCase):
    """Tests for the process of converting the output of the Discoverer
    into an internal tree.
    """
    def _full_tree(self, node):
        "Internal method generating a simple tree version of a project node"
        if isinstance(node, TestCase):
            return (type(node), node.keys())
        else:
            return dict(
                ((type(sub_tree), sub_node), self._full_tree(sub_tree))
                for sub_node, sub_tree in node.items()
            )

    def test_no_tests(self):
        "If there are no tests, an empty tree is generated"
        project = Project()
        project.refresh(test_list=[])
        self.assertEquals(project.errors, [])
        self.assertItemsEqual(self._full_tree(project), {})

    def test_with_tests(self):
        "If tests are found, the right tree is created"

        project = Project()
        project.refresh([
                'tests.FunkyTestCase.test_something_unnecessary',
                'more_tests.FunkyTestCase.test_this_does_make_sense',
                'more_tests.FunkyTestCase.test_this_doesnt_make_sense',
                'more_tests.JankyTestCase.test_things',
                'deep_tests.package.DeepTestCase.test_doo_hickey',
            ])
        self.assertEquals(project.errors, [])
        self.assertItemsEqual(self._full_tree(project), {
                (TestModule, 'tests'): {
                    (TestCase, 'FunkyTestCase'): [
                        'test_something_unnecessary'
                    ]
                },
                (TestModule, 'more_tests'): {
                    (TestCase, 'FunkyTestCase'): [
                        'test_this_doesnt_make_sense',
                        'test_this_doesnt_make_sense'
                    ],
                    (TestCase, 'JankyTestCase'): [
                        'test_things'
                    ]
                },
                (TestModule, 'deep_tests'): {
                    (TestModule, 'package'): {
                        (TestCase, 'DeepTestCase'): [
                            'test_doo_hickey'
                        ]
                    }
                }
            })

    def test_with_tests_and_errors(self):
        "If tests *and* errors are found, the tree is still created."
        project = Project()
        project.refresh([
                'tests.FunkyTestCase.test_something_unnecessary',
            ],
            errors=[
                'ERROR: you broke it, fool!',
            ]
        )

        self.assertEquals(project.errors, [
            'ERROR: you broke it, fool!',
        ])
        self.assertItemsEqual(self._full_tree(project), {
                (TestModule, 'tests'): {
                    (TestCase, 'FunkyTestCase'): [
                        'test_something_unnecessary'
                    ]
                }
            })


class FindLabelTests(unittest.TestCase):
    "Check that naming tests by labels reduces to the right runtime list."
    def setUp(self):
        super(FindLabelTests, self).setUp()
        self.project = Project()
        self.project.refresh([
                'app1.TestCase.test_method',

                'app2.TestCase1.test_method',
                'app2.TestCase2.test_method1',
                'app2.TestCase2.test_method2',

                'app3.tests.TestCase.test_method',

                'app4.tests1.TestCase.test_method',
                'app4.tests2.TestCase1.test_method',
                'app4.tests2.TestCase2.test_method1',
                'app4.tests2.TestCase2.test_method2',

                'app5.package.tests.TestCase.test_method',

                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2.TestCase1.test_method',
                'app6.package2.tests2.TestCase2.test_method1',
                'app6.package2.tests2.TestCase2.test_method2',

                'app7.package.subpackage.tests.TestCase.test_method',

                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2.test_method1',
                'app8.package2.subpackage2.tests2.TestCase2.test_method2',
            ])

    def test_single_test_project(self):
        "If the project only contains a single test, the reduction is always the full suite"
        self.project = Project()
        self.project.refresh([
                'app.package.tests.TestCase.test_method',
            ])

        self.assertEquals(self.project.find_tests(labels=[
                'app.package.tests.TestCase.test_method'
            ]),
            (1, []))

        self.assertEquals(self.project.find_tests(labels=[
                'app.package.tests.TestCase'
            ]),
            (1, []))

        self.assertEquals(self.project.find_tests(labels=[
                'app.package.tests'
            ]),
            (1, []))

        self.assertEquals(self.project.find_tests(labels=[
                'app.package'
            ]),
            (1, []))

        self.assertEquals(self.project.find_tests(labels=[
                'app'
            ]),
            (1, []))

    def test_all_tests(self):
        "Without any qualifiers, all tests are run"
        self.assertEquals(self.project.find_tests(), (22, []))

    def test_method_selection(self):
        "Explicitly named test method paths may be trimmed if they are unique"
        self.assertEquals(self.project.find_tests(labels=[
                'app1.TestCase.test_method'
            ]),
            (1, ['app1']))

        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1.test_method'
            ]),
            (1, ['app2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase2.test_method1'
            ]),
            (1, ['app2.TestCase2.test_method1']))

        self.assertEquals(self.project.find_tests(labels=[
                'app3.tests.TestCase.test_method'
            ]),
            (1, ['app3']))

        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1.TestCase.test_method'
            ]),
            (1, ['app4.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase1.test_method'
            ]),
            (1, ['app4.tests2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase2.test_method1'
            ]),
            (1, ['app4.tests2.TestCase2.test_method1']))

        self.assertEquals(self.project.find_tests(labels=[
                'app5.package.tests.TestCase.test_method'
            ]),
            (1, ['app5']))

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method'
            ]),
            (1, ['app6.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests1.TestCase.test_method'
            ]),
            (1, ['app6.package2.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase1.test_method'
            ]),
            (1, ['app6.package2.tests2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase2.test_method1'
            ]),
            (1, ['app6.package2.tests2.TestCase2.test_method1']))

        self.assertEquals(self.project.find_tests(labels=[
                'app7.package.subpackage.tests.TestCase.test_method'
            ]),
            (1, ['app7']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method'
            ]),
            (1, ['app8.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage1.tests.TestCase.test_method'
            ]),
            (1, ['app8.package2.subpackage1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests1.TestCase.test_method'
            ]),
            (1, ['app8.package2.subpackage2.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase1.test_method'
            ]),
            (1, ['app8.package2.subpackage2.tests2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase2.test_method1'
            ]),
            (1, ['app8.package2.subpackage2.tests2.TestCase2.test_method1']))

    def test_testcase_selection(self):
        "Explicitly named test case paths may be trimmed if they are unique"

        self.assertEquals(self.project.find_tests(labels=[
                'app1.TestCase'
            ]),
            (1, ['app1']))

        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1'
            ]),
            (1, ['app2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase2'
            ]),
            (2, ['app2.TestCase2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app3.tests.TestCase'
            ]),
            (1, ['app3']))

        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1.TestCase'
            ]),
            (1, ['app4.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase1'
            ]),
            (1, ['app4.tests2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase2'
            ]),
            (2, ['app4.tests2.TestCase2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app5.package.tests.TestCase'
            ]),
            (1, ['app5']))

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase'
            ]),
            (1, ['app6.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests1.TestCase'
            ]),
            (1, ['app6.package2.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase1'
            ]),
            (1, ['app6.package2.tests2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase2'
            ]),
            (2, ['app6.package2.tests2.TestCase2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app7.package.subpackage.tests.TestCase'
            ]),
            (1, ['app7']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase'
            ]),
            (1, ['app8.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage1.tests.TestCase'
            ]),
            (1, ['app8.package2.subpackage1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests1.TestCase'
            ]),
            (1, ['app8.package2.subpackage2.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase1'
            ]),
            (1, ['app8.package2.subpackage2.tests2.TestCase1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase2'
            ]),
            (2, ['app8.package2.subpackage2.tests2.TestCase2']))

    def test_testmodule_selection(self):
        "Explicitly named test module paths may be trimmed if they are unique"
        self.assertEquals(self.project.find_tests(labels=[
                'app3.tests'
            ]),
            (1, ['app3']))

        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1'
            ]),
            (1, ['app4.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2'
            ]),
            (3, ['app4.tests2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app5.package.tests'
            ]),
            (1, ['app5']))

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests'
            ]),
            (1, ['app6.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests1'
            ]),
            (1, ['app6.package2.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2'
            ]),
            (3, ['app6.package2.tests2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app7.package.subpackage.tests'
            ]),
            (1, ['app7']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests'
            ]),
            (1, ['app8.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage1.tests'
            ]),
            (1, ['app8.package2.subpackage1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests1'
            ]),
            (1, ['app8.package2.subpackage2.tests1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2'
            ]),
            (3, ['app8.package2.subpackage2.tests2']))

    def test_package_selection(self):
        "Explicitly named test package paths may be trimmed if they are unique"
        self.assertEquals(self.project.find_tests(labels=[
                'app5.package'
            ]),
            (1, ['app5']))

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1'
            ]),
            (1, ['app6.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2'
            ]),
            (4, ['app6.package2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app7.package'
            ]),
            (1, ['app7']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1'
            ]),
            (1, ['app8.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2'
            ]),
            (5, ['app8.package2']))

    def test_subpackage_selection(self):
        "Explicitly named test subpackage paths may be trimmed if they are unique"
        self.assertEquals(self.project.find_tests(labels=[
                'app7.package.subpackage'
            ]),
            (1, ['app7']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage'
            ]),
            (1, ['app8.package1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage1'
            ]),
            (1, ['app8.package2.subpackage1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2'
            ]),
            (4, ['app8.package2.subpackage2']))

    def test_app_selection(self):
        "Explicitly named app paths return a count of all tests in the app"
        self.assertEquals(self.project.find_tests(labels=[
                'app1'
            ]),
            (1, ['app1']))
        self.assertEquals(self.project.find_tests(labels=[
                'app2'
            ]),
            (3, ['app2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app3'
            ]),
            (1, ['app3']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4'
            ]),
            (4, ['app4']))
        self.assertEquals(self.project.find_tests(labels=[
                'app5'
            ]),
            (1, ['app5']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6'
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app7'
            ]),
            (1, ['app7']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8'
            ]),
            (6, ['app8']))

    def test_testcase_collapse(self):
        "If all methods in a test are selected, path is trimmed to the case"
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase2.test_method1',
                'app2.TestCase2.test_method2',
            ]),
            (2, ['app2.TestCase2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase2.test_method1',
                'app4.tests2.TestCase2.test_method2',
            ]),
            (2, ['app4.tests2.TestCase2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase2.test_method1',
                'app6.package2.tests2.TestCase2.test_method2',
            ]),
            (2, ['app6.package2.tests2.TestCase2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase2.test_method1',
                'app8.package2.subpackage2.tests2.TestCase2.test_method2',
            ]),
            (2, ['app8.package2.subpackage2.tests2.TestCase2']))

    def test_testmethod_collapse(self):
        "If all test cases in a test are selected, path is trimmed to the testmethod"

        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1.test_method',
                'app2.TestCase2.test_method1',
                'app2.TestCase2.test_method2',
            ]),
            (3, ['app2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1.test_method',
                'app2.TestCase2',
            ]),
            (3, ['app2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1',
                'app2.TestCase2',
            ]),
            (3, ['app2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase1.test_method',
                'app4.tests2.TestCase2.test_method1',
                'app4.tests2.TestCase2.test_method2',
            ]),
            (3, ['app4.tests2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase1.test_method',
                'app4.tests2.TestCase2',
            ]),
            (3, ['app4.tests2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests2.TestCase1',
                'app4.tests2.TestCase2',
            ]),
            (3, ['app4.tests2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase1.test_method',
                'app6.package2.tests2.TestCase2.test_method1',
                'app6.package2.tests2.TestCase2.test_method2',
            ]),
            (3, ['app6.package2.tests2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase1.test_method',
                'app6.package2.tests2.TestCase2',
                'app6.package2.tests2',
            ]),
            (3, ['app6.package2.tests2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests2.TestCase1',
                'app6.package2.tests2.TestCase2',
            ]),
            (3, ['app6.package2.tests2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2.test_method1',
                'app8.package2.subpackage2.tests2.TestCase2.test_method2',
            ]),
            (3, ['app8.package2.subpackage2.tests2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (3, ['app8.package2.subpackage2.tests2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests2.TestCase1',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (3, ['app8.package2.subpackage2.tests2']))

    def test_package_collapse(self):
        "If all test cases in a test pacakge are selected, path is trimmed to the testmethod"

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2.TestCase1.test_method',
                'app6.package2.tests2.TestCase2.test_method1',
                'app6.package2.tests2.TestCase2.test_method2',
            ]),
            (4, ['app6.package2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2.TestCase1.test_method',
                'app6.package2.tests2.TestCase2',
            ]),
            (4, ['app6.package2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package2.tests1.TestCase',
                'app6.package2.tests2.TestCase1',
                'app6.package2.tests2.TestCase2',
            ]),
            (4, ['app6.package2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2.test_method1',
                'app8.package2.subpackage2.tests2.TestCase2.test_method2',
            ]),
            (5, ['app8.package2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (5, ['app8.package2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage1.tests.TestCase',
                'app8.package2.subpackage2.tests1.TestCase',
                'app8.package2.subpackage2.tests2.TestCase1',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (5, ['app8.package2']))

    def test_subpackage_collapse(self):
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2.test_method1',
                'app8.package2.subpackage2.tests2.TestCase2.test_method2',
            ]),
            (4, ['app8.package2.subpackage2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (4, ['app8.package2.subpackage2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package2.subpackage2.tests1.TestCase',
                'app8.package2.subpackage2.tests2.TestCase1',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (4, ['app8.package2.subpackage2']))

    def test_app_collapse(self):
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1.test_method',
                'app2.TestCase2.test_method1',
                'app2.TestCase2.test_method2',
            ]),
            (3, ['app2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1.test_method',
                'app2.TestCase2',
            ]),
            (3, ['app2']))
        self.assertEquals(self.project.find_tests(labels=[
                'app2.TestCase1',
                'app2.TestCase2',
            ]),
            (3, ['app2']))

        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1.TestCase.test_method',
                'app4.tests2.TestCase1.test_method',
                'app4.tests2.TestCase2.test_method1',
                'app4.tests2.TestCase2.test_method2',
            ]),
            (4, ['app4']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1.TestCase.test_method',
                'app4.tests2.TestCase1.test_method',
                'app4.tests2.TestCase2',
            ]),
            (4, ['app4']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1.TestCase.test_method',
                'app4.tests2.TestCase1',
                'app4.tests2.TestCase2',
            ]),
            (4, ['app4']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1.TestCase.test_method',
                'app4.tests2',
            ]),
            (4, ['app4']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1.TestCase',
                'app4.tests2',
            ]),
            (4, ['app4']))
        self.assertEquals(self.project.find_tests(labels=[
                'app4.tests1',
                'app4.tests2',
            ]),
            (4, ['app4']))

        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2.TestCase1.test_method',
                'app6.package2.tests2.TestCase2.test_method1',
                'app6.package2.tests2.TestCase2.test_method2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2.TestCase1.test_method',
                'app6.package2.tests2.TestCase2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2.TestCase1',
                'app6.package2.tests2.TestCase2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2.TestCase1',
                'app6.package2.tests2.TestCase2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase.test_method',
                'app6.package2.tests2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1.TestCase',
                'app6.package2.tests2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2.tests1',
                'app6.package2.tests2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase.test_method',
                'app6.package2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests.TestCase',
                'app6.package2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1.tests',
                'app6.package2',
            ]),
            (5, ['app6']))
        self.assertEquals(self.project.find_tests(labels=[
                'app6.package1',
                'app6.package2',
            ]),
            (5, ['app6']))


        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2.test_method1',
                'app8.package2.subpackage2.tests2.TestCase2.test_method2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1.test_method',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2.TestCase1',
                'app8.package2.subpackage2.tests2.TestCase2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase.test_method',
                'app8.package2.subpackage2.tests2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1.TestCase',
                'app8.package2.subpackage2.tests2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2.tests1',
                'app8.package2.subpackage2.tests2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase.test_method',
                'app8.package2.subpackage2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests.TestCase',
                'app8.package2.subpackage2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1.tests',
                'app8.package2.subpackage2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2.subpackage1',
                'app8.package2.subpackage2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase.test_method',
                'app8.package2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests.TestCase',
                'app8.package2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage.tests',
                'app8.package2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1.subpackage',
                'app8.package2',
            ]),
            (6, ['app8']))
        self.assertEquals(self.project.find_tests(labels=[
                'app8.package1',
                'app8.package2',
            ]),
            (6, ['app8']))

########NEW FILE########
__FILENAME__ = test_unit_integration
import subprocess
import unittest

import cricket

from cricket.unittest import discoverer
from cricket.unittest import executor

class TestCollection(unittest.TestCase):

    def test_testCollection(self):
        '''
        Confirm that the pytest discovery mechanism is capable of
        finding this test
        '''

        PTD = discoverer.PyTestDiscoverer()
        PTD.collect_tests()
        tests = str(PTD).split('\n')

        test_found = False
        for test in tests:
            test_found |= 'test_testCollection' in test
        self.assertTrue(test_found)


class TestExecutorCmdLine(unittest.TestCase):

    def test_labels(self):
        '''
        Test that the command-line API is respecting the labels
        being targetted for testing
        '''

        labels = ['tests.test_unit_integration.TestCollection']
        cmdline = ['python', '-m', 'cricket.unittest.executor'] + labels

        runner = subprocess.Popen(
            cmdline,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )  

        output = ''
        for line in runner.stdout:
            output += line

        self.assertIn('tests.test_unit_integration.TestCollection',
                       output)
        self.assertNotIn('tests.test_unit_integration.TestExecutorCmdLine',
                          output)




# This is a magic test which can be un-commented and run manually.
# It recursively calls the text executor, and fouls up normal
# output, so it had to be disabled as I am not smart enough
# to actually understand and fix the issue

# class TestExecutor(unittest.TestCase):

#     def test_suite_execution(self):
#         '''
#         Note, it's hard to test full suite discovery because
#         it will include this test and infinite loop. So just
#         testing on a single test until I can figure out something
#         smarter.
#         '''

#         run_only = [
#             'tests.test_unit_integration.TestDiscoverer'
#         ]
        
#         PTE = test_executor.PyTestExecutor()
#         PTE.run_only(run_only)
#         PTE.stream_results()

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
