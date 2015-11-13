__FILENAME__ = functions
# -*- coding: utf-8 -*-
import os.path
import subprocess


class CalledProcessError(subprocess.CalledProcessError):
    def __init__(self, returncode, cmd, output=None):
        super(CalledProcessError, self).__init__(returncode, cmd)
        self.output = output

    def __str__(self):
        return "Command '%s' returned non-zero exit status %d\nOutput:\n%s" \
            % (self.cmd, self.returncode, self.output)


def relpath(path, start=os.path.curdir):
    """
    Return a relative version of a path

    Backport from Python2.7
    """
    if not path:
        raise ValueError("no path specified")

    start_list = os.path.abspath(start).split(os.path.sep)
    path_list = os.path.abspath(path).split(os.path.sep)

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list) - i) + path_list[i:]
    if not rel_list:
        return os.path.curdir
    return os.path.join(*rel_list)


def check_output(*popenargs, **kwargs):
    """
    Backport from Python2.7
    """
    if 'stdout' in kwargs or 'stderr' in kwargs:
        raise ValueError('stdout or stderr argument not allowed, '
                         'it will be overridden.')

    try:
        process = subprocess.Popen(stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   *popenargs, **kwargs)
    except OSError:
        raise RuntimeError('Could not open program %s. Are the dependencies installed?' % popenargs)

    output, err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, output="%s\n%s" % (output, err))
    return output


def find_first_existing_executable(exe_list):
    """
    Accepts list of [('executable_file_path', 'options')],
    Returns first working executable_file_path
    """
    for filepath, opts in exe_list:
        try:
            proc = subprocess.Popen([filepath, opts],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            proc.communicate()
        except OSError:
            pass
        else:
            return filepath


def total_seconds(delta):
    """
    Backport timedelta.total_seconds() from Python 2.7
    """
    return delta.days * 86400.0 + delta.seconds + delta.microseconds * 1e-6

########NEW FILE########
__FILENAME__ = csslint
# -*- coding: utf-8; mode: django -*-
from optparse import make_option
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run csslint over project apps"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option('--csslint-file-output', action='store_true',
                    dest='csslint_file_output', default=False,
            help='Store csslint report in file'),
    )

    def get_task_list(self):
        return ('django_jenkins.tasks.run_csslint',)

########NEW FILE########
__FILENAME__ = flake8
# -*- coding: utf-8 -*-
from optparse import make_option
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run flake8 over project apps"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option(
            '--flake8-file-output',
            action='store_true',
            dest='flake8_file_output',
            default=False,
            help='Store flake8 report in file'),
    )

    def get_task_list(self):
        return ('django_jenkins.tasks.run_flake8',)

########NEW FILE########
__FILENAME__ = jenkins
# -*- coding: utf-8 -*-
from django.conf import settings
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run CI process"
    args = '[appname ...]'

    def get_task_list(self):
        return getattr(settings, 'JENKINS_TASKS',
                       ('django_jenkins.tasks.run_pylint',
                        'django_jenkins.tasks.with_coverage',))

########NEW FILE########
__FILENAME__ = jshint
# -*- coding: utf-8 -*-
from optparse import make_option
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run jshint over project apps"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option('--jshint-file-output', action='store_true',
                    dest='jshint_file_output', default=False,
            help='Store jshint report in file'),
    )

    def get_task_list(self):
        return ('django_jenkins.tasks.run_jshint',)

########NEW FILE########
__FILENAME__ = jtest
# -*- coding: utf-8 -*-
from optparse import make_option
from django.conf import settings
from django.utils.importlib import import_module
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run django test suite using jenkins test runner"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option('--with-reports', action='store_true',
                    dest='with_reports', default=False,
                help='Create xunit reports files'),
        make_option("--coverage-html-report",
                    dest="coverage_html_report_dir",
                    default="",
                help="Enables code coverage and creates html coverage report"),
    )

    def get_tasks(self, *test_labels, **options):
        if options.get('coverage_html_report_dir',
                       getattr(settings, 'COVERAGE_HTML_REPORT', False)):
            self.tasks_cls.append(
                    import_module('django_jenkins.tasks.with_coverage').Task)
        return [task_cls(test_labels, options) for task_cls in self.tasks_cls]

    def get_task_list(self):
        enabled_tasks = getattr(settings, 'JENKINS_TASKS', ())

        tasks = []

        if 'django_jenkins.tasks.with_local_celery' in enabled_tasks:
            tasks.append('django_jenkins.tasks.with_local_celery')

        return tasks

########NEW FILE########
__FILENAME__ = pep8
# -*- coding: utf-8 -*-
from optparse import make_option
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run pep8 over project apps"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option('--pep8-file-output', action='store_true',
                    dest='pep8_file_output', default=False,
            help='Store pep8 report in file'),
    )

    def get_task_list(self):
        return ('django_jenkins.tasks.run_pep8',)

########NEW FILE########
__FILENAME__ = pyflakes
# -*- coding: utf-8 -*-
from optparse import make_option
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run pyflakes over project apps"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option('--pyflakes-file-output', action='store_true',
                     dest='pyflakes_file_output', default=False,
            help='Store pep8 report in file'),
    )

    def get_task_list(self):
        return ('django_jenkins.tasks.run_pyflakes',)

########NEW FILE########
__FILENAME__ = pylint
# -*- coding: utf-8 -*-
from optparse import make_option
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run pylint over project apps"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option('--pylint-file-output', action='store_true',
                    dest='pylint_file_output', default=False,
            help='Store pylint report in file'),
    )

    def get_task_list(self):
        return ('django_jenkins.tasks.run_pylint',)

########NEW FILE########
__FILENAME__ = sloccount
# -*- coding: utf-8; mode: django -*-
from optparse import make_option
from django_jenkins.management.commands import TaskListCommand


class Command(TaskListCommand):
    help = "Run sloccount over project apps"
    args = '[appname ...]'
    option_list = TaskListCommand.option_list + (
        make_option('--sloccount-file-output', action='store_true',
                    dest='sloccount_file_output', default=False,
            help='Store sloccount report in file'),
    )

    def get_task_list(self):
        return ('django_jenkins.tasks.run_sloccount',)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = runner
# -*- coding: utf-8; mode: django -*-
import os
import sys
import time

from xml.etree import ElementTree as ET
from django.conf import settings
from django.utils.encoding import smart_text
from django.test.testcases import TestCase
from django.utils.unittest import TextTestResult, TextTestRunner

try:
    # Django 1.6
    from django.test.runner import DiscoverRunner
    # For those who still use django 1.5 tests on Django 1.6
    if settings.TEST_RUNNER == 'django.test.simple.DjangoTestSuiteRunner':
        from django.test.simple import DjangoTestSuiteRunner as DiscoverRunner

except ImportError:
    # Fallback to third-party app on Django 1.5
    try:
        from discover_runner.runner import DiscoverRunner
    except ImportError:
        import warnings
        warnings.warn(
            "Directory-only tests are ignored. Install django-discover-runner to enable it",
            UserWarning)
        from django.test.simple import DjangoTestSuiteRunner as DiscoverRunner

try:
    from django.test.simple import reorder_suite
except ImportError:
    from django.test.runner import reorder_suite

from django_jenkins import signals


class EXMLTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        self.case_start_time = None
        self.run_start_time = None
        self.tree = None
        super(EXMLTestResult, self).__init__(*args, **kwargs)

    def startTest(self, test):
        self.case_start_time = time.time()
        super(EXMLTestResult, self).startTest(test)

    def startTestRun(self):
        self.tree = ET.Element('testsuite')
        self.run_start_time = time.time()
        super(EXMLTestResult, self).startTestRun()

    def addSuccess(self, test):
        self.testcase = self._make_testcase_element(test)
        super(EXMLTestResult, self).addSuccess(test)

    def addFailure(self, test, err):
        self.testcase = self._make_testcase_element(test)
        test_result = ET.SubElement(self.testcase, 'failure')
        self._add_tb_to_test(test, test_result, err)
        super(EXMLTestResult, self).addFailure(test, err)

    def addError(self, test, err):
        self.testcase = self._make_testcase_element(test)
        test_result = ET.SubElement(self.testcase, 'error')
        self._add_tb_to_test(test, test_result, err)
        super(EXMLTestResult, self).addError(test, err)

    def addUnexpectedSuccess(self, test):
        self.testcase = self._make_testcase_element(test)
        test_result = ET.SubElement(self.testcase, 'skipped')
        test_result.set('message', 'Test Skipped: Unexpected Success')
        super(EXMLTestResult, self).addUnexpectedSuccess(test)

    def addSkip(self, test, reason):
        self.testcase = self._make_testcase_element(test)
        test_result = ET.SubElement(self.testcase, 'skipped')
        test_result.set('message', 'Test Skipped: %s' % reason)
        super(EXMLTestResult, self).addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.testcase = self._make_testcase_element(test)
        test_result = ET.SubElement(self.testcase, 'skipped')
        self._add_tb_to_test(test, test_result, err)
        super(EXMLTestResult, self).addExpectedFailure(test, err)

    def stopTest(self, test):
        if self.buffer:
            output = sys.stdout.getvalue() if hasattr(sys.stdout, 'getvalue') else ''
            if output:
                sysout = ET.SubElement(self.testcase, 'system-out')
                sysout.text = smart_text(output, errors='ignore')

            error = sys.stderr.getvalue() if hasattr(sys.stderr, 'getvalue') else ''
            if error:
                syserr = ET.SubElement(self.testcase, 'system-err')
                syserr.text = smart_text(error, errors='ignore')

        super(EXMLTestResult, self).stopTest(test)

    def stopTestRun(self):
        run_time_taken = time.time() - self.run_start_time
        self.tree.set('name', 'Django Project Tests')
        self.tree.set('errors', str(len(self.errors)))
        self.tree.set('failures', str(len(self.failures)))
        self.tree.set('skips', str(len(self.skipped)))
        self.tree.set('tests', str(self.testsRun))
        self.tree.set('time', "%.3f" % run_time_taken)
        super(EXMLTestResult, self).stopTestRun()

    def _make_testcase_element(self, test):
        time_taken = time.time() - self.case_start_time
        classname = ('%s.%s' % (test.__module__, test.__class__.__name__)).split('.')
        testcase = ET.SubElement(self.tree, 'testcase')
        testcase.set('time', "%.6f" % time_taken)
        testcase.set('classname', '.'.join(classname))
        testcase.set('name', test._testMethodName)
        return testcase

    def _add_tb_to_test(self, test, test_result, err):
        '''Add a traceback to the test result element'''
        exc_class, exc_value, tb = err
        tb_str = self._exc_info_to_string(err, test)
        test_result.set('type', '%s.%s' % (exc_class.__module__, exc_class.__name__))
        test_result.set('message', str(exc_value))
        test_result.text = tb_str

    def dump_xml(self, output_dir):
        """
        Dumps test result to xml
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output = ET.ElementTree(self.tree)
        output.write(os.path.join(output_dir, 'junit.xml'), encoding="utf-8")


class CITestSuiteRunner(DiscoverRunner):
    """
    Continuous integration test runner
    """
    def __init__(self, output_dir, with_reports=True, debug=False, test_all=False, **kwargs):
        super(CITestSuiteRunner, self).__init__(**kwargs)
        self.with_reports = with_reports
        self.output_dir = output_dir
        self.debug = debug
        self.test_all = test_all

    def setup_test_environment(self, **kwargs):
        super(CITestSuiteRunner, self).setup_test_environment()
        signals.setup_test_environment.send(sender=self)

    def teardown_test_environment(self, **kwargs):
        super(CITestSuiteRunner, self).teardown_test_environment()
        signals.teardown_test_environment.send(sender=self)

    def setup_databases(self):
        if 'south' in settings.INSTALLED_APPS:
            from south.management.commands import (
                patch_for_test_db_setup  # pylint: disable=F0401
            )
            patch_for_test_db_setup()
        return super(CITestSuiteRunner, self).setup_databases()

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        if not test_labels and not self.test_all:
            if hasattr(settings, 'PROJECT_APPS'):
                test_labels = settings.PROJECT_APPS

        suite = super(CITestSuiteRunner, self).build_suite(test_labels, extra_tests=None, **kwargs)
        signals.build_suite.send(sender=self, suite=suite)
        return reorder_suite(suite, getattr(self, 'reorder_by', (TestCase,)))

    def run_suite(self, suite, **kwargs):
        signals.before_suite_run.send(sender=self)
        result = TextTestRunner(buffer=not self.debug,
                                resultclass=EXMLTestResult,
                                verbosity=self.verbosity).run(suite)
        if self.with_reports:
            result.dump_xml(self.output_dir)
        signals.after_suite_run.send(sender=self)
        return result


########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
from django.dispatch import Signal

setup_test_environment = Signal()
teardown_test_environment = Signal()

before_suite_run = Signal()
after_suite_run = Signal()

build_suite = Signal(providing_args=["suite"])

test_failure = Signal(providing_args=['test', 'err'])
test_error = Signal(providing_args=['test', 'err'])
test_success = Signal(providing_args=['test'])
test_skip = Signal(providing_args=['test', 'reason'])
test_expected_failure = Signal(providing_args=['test', 'err'])
test_unexpected_success = Signal(providing_args=['test'])

########NEW FILE########
__FILENAME__ = run_csslint
# -*- coding: utf-8; mode: django -*-
import os
import subprocess
import sys
import fnmatch
import codecs
from optparse import make_option
from django.conf import settings
from django_jenkins.functions import CalledProcessError
from django_jenkins.tasks import BaseTask, get_apps_locations


class Task(BaseTask):
    option_list = [
        make_option("--csslint-with-staticdirs",
                    dest="csslint_with-staticdirs",
                    default=False, action="store_true",
                    help="Check css files located in STATIC_DIRS settings"),
        make_option("--csslint-with-mincss",
                    dest="csslint_with_mincss",
                    default=False, action="store_true",
                    help="Do not ignore .min.css files"),
        make_option("--csslint-exclude",
                    dest="csslint_exclude", default="",
                    help="Exclude patterns"),
        make_option("--csslint-static-dirname",
                    dest="csslint_static-dirname", default="static",
                    help="Name of dir with css static files"),
        make_option("--csslint-ignore",
                    dest="csslint_ignore", default="",
                    help="Ignore rules")]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.test_all = options['test_all']
        self.to_file = options.get('csslint_file_output', True)
        self.with_static_dirs = options.get('csslint_with-staticdirs', False)
        self.csslint_with_minjs = options.get('csslint_with_mincss', False)

        if self.to_file:
            output_dir = options['output_dir']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.output = codecs.open(os.path.join(output_dir, 'csslint.report'), 'w', 'utf-8')
        else:
            self.output = sys.stdout

        self.exclude = options['csslint_exclude'].split(',')
        self.ignore = options['csslint_ignore']
        self.static_dirname = options.get('csslint_static-dirname', 'static')

    def teardown_test_environment(self, **kwargs):
        files = [path for path in self.static_files_iterator()]
        if self.to_file:
            fmt = 'lint-xml'
        else:
            fmt = 'text'

        if files:
            cmd = ['csslint', '--format=%s' % fmt] + files

            if self.ignore:
                cmd += ['--ignore=%s' % self.ignore]

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            output, err = process.communicate()
            retcode = process.poll()
            if retcode not in [0, 1]:  # normal csslint return codes
                raise CalledProcessError(retcode, cmd,
                                         output=output + '\n' + err)

            self.output.write(output.decode('utf-8'))
        elif self.to_file:
            self.output.write('<?xml version="1.0" encoding='
                              '"utf-8"?><lint></lint>')

        self.output.close()

    def static_files_iterator(self):
        locations = get_apps_locations(self.test_labels, self.test_all)

        def in_tested_locations(path):
            if not self.csslint_with_minjs and path.endswith('.min.css'):
                return False

            for location in locations:
                if path.startswith(location):
                    return True
            if self.with_static_dirs:
                for location in list(settings.STATICFILES_DIRS):
                    if path.startswith(location):
                        return True
            return False

        def is_excluded(path):
            for pattern in self.exclude:
                if fnmatch.fnmatchcase(path, pattern):
                    return True
            return False

        if hasattr(settings, 'CSSLINT_CHECKED_FILES'):
            for path in settings.CSSLINT_CHECKED_FILES:
                yield path

        if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
            # use django.contrib.staticfiles
            from django.contrib.staticfiles import finders

            for finder in finders.get_finders():
                for path, storage in finder.list(self.exclude):
                    path = os.path.join(storage.location, path)
                    if path.endswith('.css') and in_tested_locations(path):
                        yield path
        else:
            # scan apps directories for static folders
            for location in locations:
                for dirpath, dirnames, filenames in \
                                os.walk(os.path.join(location, self.static_dirname)):
                    for filename in filenames:
                        path = os.path.join(dirpath, filename)
                        if filename.endswith('.css') and \
                             in_tested_locations(path) and not \
                                 is_excluded(path):
                            yield path

########NEW FILE########
__FILENAME__ = run_flake8
import os
import sys
import pep8

from flake8.engine import get_style_guide
from django_jenkins.tasks import get_apps_locations
from django_jenkins.tasks.run_pep8 import Task
from django_jenkins.functions import relpath
from optparse import make_option


class Task(Task):
    """
    Runs flake8 on python files.
    """
    option_list = [
        make_option('--max-complexity',
                    dest='max_complexity',
                    default='-1',
                    help='McCabe complexity treshold'),
        make_option("--pep8-exclude",
                    dest="pep8-exclude",
                    default=pep8.DEFAULT_EXCLUDE + ",migrations",
                    help="exclude files or directories which match these "
                    "comma separated patterns (default: %s)" %
                    pep8.DEFAULT_EXCLUDE),
        make_option("--pep8-select", dest="pep8-select",
                    help="select errors and warnings (e.g. E,W6)"),
        make_option("--pep8-ignore", dest="pep8-ignore",
                    help="skip errors and warnings (e.g. E4,W)"),
        make_option("--pep8-max-line-length",
                    dest="pep8-max-line-length", type='int',
                    help="set maximum allowed line length (default: %d)" %
                    pep8.MAX_LINE_LENGTH),
        make_option("--pep8-rcfile", dest="pep8-rcfile",
                    help="PEP8 configuration file"),
    ]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.test_all = options['test_all']

        self.max_complexity = int(options['max_complexity'])

        if options.get('flake8_file_output', True):
            output_dir = options['output_dir']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.output = open(os.path.join(output_dir, 'flake8.report'), 'w')
        else:
            self.output = sys.stdout

    def teardown_test_environment(self, **kwargs):
        locations = get_apps_locations(self.test_labels, self.test_all)

        class JenkinsReport(pep8.BaseReport):
            def error(instance, line_number, offset, text, check):
                code = super(JenkinsReport, instance).error(line_number, offset, text, check)

                if not code:
                    return
                sourceline = instance.line_offset + line_number
                self.output.write('%s:%s:%s: %s\n' % (instance.filename, sourceline, offset + 1, text))

        pep8style = get_style_guide(parse_argv=False, config_file=self.pep8_rcfile,
                                    reporter=JenkinsReport, max_complexity=self.max_complexity,
                                    **self.pep8_options)

        for location in locations:
            pep8style.input_dir(relpath(location))

        self.output.close()

########NEW FILE########
__FILENAME__ = run_graphmodels
# -*- coding: utf-8 -*-
# pylint: disable=W0201
import os
from optparse import make_option
from django.conf import settings
from django.core.management import call_command, CommandError
from django_jenkins.tasks import BaseTask, get_apps_under_test


class Task(BaseTask):
    # Using options from modelviz.py / graph_models.py, prefixed with
    # graphmodels[_-]
    option_list = [
        make_option('--graphmodels-disable-fields',
                    action='store_true', dest='graphmodels_disable_fields',
            help='Do not show the class member fields'),
        make_option('--graphmodels-group-models',
                    action='store_true', dest='graphmodels_group_models',
            help='Group models together respective to their application'),
        make_option('--graphmodels-all-applications',
                    action='store_true', dest='graphmodels_all_applications',
            help='Automatically include all applications from INSTALLED_APPS'),
        make_option('--graphmodels-output',
                    action='store', dest='graphmodels_outputfile',
            help='Render output file. Type of output dependend on file'
                     ' extensions. Use png or jpg to render graph to image.'),
        make_option('--graphmodels-layout',
                    action='store', dest='graphmodels_layout', default='dot',
            help='Layout to be used by GraphViz for visualization. Layouts: '
                 'circo dot fdp neato nop nop1 nop2 twopi'),
        make_option('--graphmodels-verbose-names',
                    action='store_true', dest='graphmodels_verbose_names',
            help='Use verbose_name of models and fields'),
        make_option('--graphmodels-language',
                    action='store', dest='graphmodels_language',
            help='Specify language used for verbose_name localization'),
        make_option('--graphmodels-exclude-columns',
                    action='store', dest='graphmodels_exclude_columns',
            help='Exclude specific column(s) from the graph. Can also load '
                 'exclude list from file.'),
        make_option('--graphmodels-exclude-models',
                    action='store', dest='graphmodels_exclude_models',
            help='Exclude specific model(s) from the graph. Can also load '
                 'exclude list from file.'),
        make_option('--graphmodels-inheritance',
                    action='store_true', dest='graphmodels_inheritance',
            help='Include inheritance arrows'),
    ]

    def checkdeps(self):
        if 'django_extensions' not in settings.INSTALLED_APPS:
            if self.options.get('fail_without_error', False):
                return False
            else:
                raise CommandError("django-extensions is required to execute"
                                   " this command")

        try:
            import pygraphviz  # noqa
        except ImportError:
            if self.options.get('fail_without_error', False):
                return False
            else:
                raise CommandError("pygraphviz is required to execute "
                                   "this command")

        return True

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.options = options

        # Rename options, for the call to the existing graph_models command
        for key, value in self.options.items():
            if key.startswith('graphmodels_'):
                newkey = key[12:]
                del self.options[key]
                self.options[newkey] = value

        # Merge in possibles settings file options, if the option is
        # unset (None)
        fromfile = getattr(settings, 'GRAPH_MODELS', {})
        fromfile.update(dict((k, v) for k, v in self.options.iteritems() if v))
        self.options.update(fromfile)

        if self.options['test_all']:
            self.options['all_applications'] = True

        # Place the file in the correct place
        output_dir = self.options['output_dir']
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.options['outputfile'] = os.path.join(output_dir, 'models.png')

        if not self.checkdeps():
            return

    def teardown_test_environment(self, **kwargs):
        # Get the list of PROJECT_APPS if nothing specified any we don't
        # want everything
        if len(self.test_labels) < 1 and not self.options['all_applications']:
            under = get_apps_under_test(self.test_labels,
                                        self.options['all_applications'])
            self.test_labels = [label.split('.')[-1] for label in under]

        call_command('graph_models', *self.test_labels, **self.options)

########NEW FILE########
__FILENAME__ = run_jshint
# -*- coding: utf-8 -*-
import os
import sys
import codecs
import fnmatch
import subprocess
from optparse import make_option
from django.conf import settings
from django_jenkins.functions import CalledProcessError
from django_jenkins.tasks import BaseTask, get_apps_locations


class Task(BaseTask):
    option_list = [
        make_option("--jshint-with-staticdirs",
                    dest="jshint-with-staticdirs",
                    default=False, action="store_true",
                    help="Check js files located in STATIC_DIRS settings"),
        make_option("--jshint-with-minjs",
                    dest="jshint_with-minjs",
                    default=False, action="store_true",
                    help="Do not ignore .min.js files"),
        make_option("--jshint-exclude",
                    dest="jshint_exclude", default="",
                    help="Exclude patterns"),
        make_option("--jshint-static-dirname",
                    dest="jshint_static-dirname", default="static",
                    help="Name of dir with js static files")]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.test_all = options['test_all']
        self.to_file = options.get('jshint_file_output', True)
        self.with_static_dirs = options.get('jshint-with-staticdirs', False)
        self.jshint_with_minjs = options.get('jshint_with-minjs', False)

        if self.to_file:
            output_dir = options['output_dir']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.output = codecs.open(os.path.join(output_dir, 'jshint.xml'), 'w', 'utf-8')
        else:
            self.output = sys.stdout

        self.exclude = options['jshint_exclude'].split(',')
        self.static_dirname = options.get('jshint_static-dirname', 'static')

    def teardown_test_environment(self, **kwargs):
        files = [path for path in self.static_files_iterator()]

        cmd = ['jshint']
        if self.to_file:
            cmd += ['--jslint-reporter']
        cmd += files

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output, err = process.communicate()
        retcode = process.poll()
        if retcode not in [0, 1, 2]:  # normal jshint return codes
            raise CalledProcessError(retcode, cmd, output='%s\n%s' % (output, err))

        self.output.write(output.decode('utf-8'))
        self.output.close()

    def static_files_iterator(self):
        locations = get_apps_locations(self.test_labels, self.test_all)

        def in_tested_locations(path):
            if not self.jshint_with_minjs and path.endswith('.min.js'):
                return False

            for location in list(locations):
                if path.startswith(location):
                    return True
            if self.with_static_dirs:
                for location in list(settings.STATICFILES_DIRS):
                    if path.startswith(location):
                        return True
            return False

        def is_excluded(path):
            for pattern in self.exclude:
                if fnmatch.fnmatchcase(path, pattern):
                    return True
            return False

        if hasattr(settings, 'JSHINT_CHECKED_FILES'):
            for path in settings.JSHINT_CHECKED_FILES:
                yield path

        if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
            # use django.contrib.staticfiles
            from django.contrib.staticfiles import finders

            for finder in finders.get_finders():
                for path, storage in finder.list(self.exclude):
                    path = os.path.join(storage.location, path)
                    if path.endswith('.js') and in_tested_locations(path):
                        yield path
        else:
            # scan apps directories for static folders
            for location in locations:
                for dirpath, dirnames, filenames in os.walk(os.path.join(location, self.static_dirname)):
                    for filename in filenames:
                        path = os.path.join(dirpath, filename)
                        if filename.endswith('.js') and in_tested_locations(path) and not is_excluded(path):
                            yield path

########NEW FILE########
__FILENAME__ = run_pep8
# -*- coding: utf-8 -*-
import os
import sys
import pep8

from optparse import make_option
from django.conf import settings

from django_jenkins.functions import relpath
from django_jenkins.tasks import BaseTask, get_apps_locations


class Task(BaseTask):
    option_list = [
        make_option("--pep8-exclude",
                    dest="pep8-exclude",
                    default=pep8.DEFAULT_EXCLUDE + ",migrations",
                    help="exclude files or directories which match these "
                    "comma separated patterns (default: %s)" %
                    pep8.DEFAULT_EXCLUDE),
        make_option("--pep8-select", dest="pep8-select",
                    help="select errors and warnings (e.g. E,W6)"),
        make_option("--pep8-ignore", dest="pep8-ignore",
                    help="skip errors and warnings (e.g. E4,W)"),
        make_option("--pep8-max-line-length",
                    dest="pep8-max-line-length", type='int',
                    help="set maximum allowed line length (default: %d)" %
                    pep8.MAX_LINE_LENGTH),
        make_option("--pep8-rcfile", dest="pep8-rcfile",
                    help="PEP8 configuration file"),
    ]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.test_all = options['test_all']

        if options.get('pep8_file_output', True):
            output_dir = options['output_dir']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.output = open(os.path.join(output_dir, 'pep8.report'), 'w')
        else:
            self.output = sys.stdout

        self.pep8_rcfile = options['pep8-rcfile'] or Task.default_config_path()
        self.pep8_options = {'exclude': options['pep8-exclude'].split(',')}
        if options['pep8-select']:
            self.pep8_options['select'] = options['pep8-select'].split(',')
        if options['pep8-ignore']:
            self.pep8_options['ignore'] = options['pep8-ignore'].split(',')
        if options['pep8-max-line-length']:
            self.pep8_options['max_line_length'] = options['pep8-max-line-length']

    def teardown_test_environment(self, **kwargs):
        locations = get_apps_locations(self.test_labels, self.test_all)

        class JenkinsReport(pep8.BaseReport):
            def error(instance, line_number, offset, text, check):
                code = super(JenkinsReport, instance).error(line_number, offset, text, check)

                if not code:
                    return
                sourceline = instance.line_offset + line_number
                self.output.write('%s:%s:%s: %s\n' %
                                  (instance.filename, sourceline, offset + 1, text))

        pep8style = pep8.StyleGuide(parse_argv=False, config_file=self.pep8_rcfile,
                                    reporter=JenkinsReport,
                                    **self.pep8_options)

        for location in locations:
            pep8style.input_dir(relpath(location))

        self.output.close()

    @staticmethod
    def default_config_path():
        rcfile = getattr(settings, 'PEP8_RCFILE', 'pep8.rc')
        return rcfile if os.path.exists(rcfile) else None

########NEW FILE########
__FILENAME__ = run_pyflakes
# -*- coding: utf-8 -*-
import os
import re
import sys
from optparse import make_option
from pyflakes.scripts import pyflakes
from django_jenkins.functions import relpath
from django_jenkins.tasks import BaseTask, get_apps_locations

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class Task(BaseTask):
    option_list = [
        make_option("--pyflakes-with-migrations",
                    action="store_true", default=False,
                    dest="pyflakes_with_migrations",
                    help="Don't check migrations with pyflakes.")]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.test_all = options['test_all']
        self.with_migrations = options['pyflakes_with_migrations']

        if options.get('pyflakes_file_output', True):
            output_dir = options['output_dir']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.output = open(os.path.join(output_dir,
                                            'pyflakes.report'), 'w')
        else:
            self.output = sys.stdout

    def teardown_test_environment(self, **kwargs):
        locations = get_apps_locations(self.test_labels, self.test_all)

        # run pyflakes tool with captured output
        old_stdout, pyflakes_output = sys.stdout, StringIO()
        sys.stdout = pyflakes_output
        try:
            for location in locations:
                if os.path.isdir(location):
                    for dirpath, dirnames, filenames in \
                                        os.walk(relpath(location)):
                        if not self.with_migrations and \
                                dirpath.endswith(os.sep + 'migrations'):
                            continue
                        for filename in filenames:
                            if filename.endswith('.py'):
                                pyflakes.checkPath(os.path.join(dirpath,
                                                                filename))
                else:
                    pyflakes.checkPath(relpath(location))
        finally:
            sys.stdout = old_stdout

        # save report
        pyflakes_output.seek(0)

        while True:
            line = pyflakes_output.readline()
            if not line:
                break
            message = re.sub(r': ', r': [E] PYFLAKES:', line)
            self.output.write(message)

        self.output.close()

########NEW FILE########
__FILENAME__ = run_pylint
# -*- coding: utf-8 -*-
# pylint: disable=W0201
import os
import sys
from optparse import make_option
from django.conf import settings
from django_jenkins.tasks import BaseTask, get_apps_under_test

from pylint import lint
from pylint.reporters.text import ParseableTextReporter


class Task(BaseTask):
    option_list = [make_option("--pylint-rcfile",
                               dest="pylint_rcfile",
                               help="pylint configuration file"),
                   make_option("--pylint-errors-only",
                               dest="pylint_errors_only",
                               action="store_true", default=False,
                               help="pylint output errors only mode")]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)

        self.test_all = options['test_all']
        self.config_path = options['pylint_rcfile'] or \
                                Task.default_config_path()
        self.errors_only = options['pylint_errors_only']

        if options.get('pylint_file_output', True):
            output_dir = options['output_dir']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.output = open(os.path.join(output_dir, 'pylint.report'), 'w')
        else:
            self.output = sys.stdout

    def teardown_test_environment(self, **kwargs):
        args = ["--rcfile=%s" % self.config_path]
        if self.errors_only:
            args += ['--errors-only']
        args += get_apps_under_test(self.test_labels, self.test_all)

        lint.Run(args, reporter=ParseableTextReporter(output=self.output),
                                                      exit=False)

        return True

    @staticmethod
    def default_config_path():
        rcfile = getattr(settings, 'PYLINT_RCFILE', 'pylint.rc')
        if os.path.exists(rcfile):
            return rcfile

        # use build-in
        root_dir = os.path.normpath(os.path.dirname(__file__))
        return os.path.join(root_dir, 'pylint.rc')

########NEW FILE########
__FILENAME__ = run_sloccount
# -*- coding: utf-8 -*-
import os
import sys
from optparse import make_option
from django_jenkins.functions import check_output
from django_jenkins.tasks import BaseTask, get_apps_locations


class Task(BaseTask):
    option_list = [
        make_option("--sloccount-with-migrations",
                    action="store_true", default=False,
                    dest="sloccount_with_migrations",
                    help="Count migrations sloc.")]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.test_all = options['test_all']
        self.with_migrations = options['sloccount_with_migrations']

        if options.get('sloccount_file_output', True):
            output_dir = options['output_dir']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.output = open(os.path.join(output_dir,
                                            'sloccount.report'), 'w')
        else:
            self.output = sys.stdout

    def teardown_test_environment(self, **kwargs):
        locations = get_apps_locations(self.test_labels, self.test_all)

        report_output = check_output(
            ['sloccount', "--duplicates", "--wide", "--details"] + locations)
        report_output = report_output.decode('utf-8')

        if self.with_migrations:
            self.output.write(report_output)
        else:
            for line in report_output.splitlines():
                if (os.sep + 'migrations' + os.sep) in line:
                    continue
                self.output.write(line)
                self.output.write('\n')
        self.output.close()

########NEW FILE########
__FILENAME__ = with_coverage
# -*- coding: utf-8 -*-
# pylint: disable=W0201
import os
from optparse import make_option
from coverage.control import coverage
from django.conf import settings
from django.utils.importlib import import_module
from django_jenkins.tasks import BaseTask, get_apps_under_test


class Task(BaseTask):
    option_list = [
           make_option("--coverage-rcfile",
                       dest="coverage_rcfile",
                       default="",
               help="Specify configuration file."),
           make_option("--coverage-html-report",
                       dest="coverage_html_report_dir",
                       default="",
               help="Directory to which HTML coverage report should be"
                    " written. If not specified, no report is generated."),
           make_option("--coverage-no-branch-measure",
                       action="store_false", default=True,
                       dest="coverage_measure_branch",
               help="Don't measure branch coverage."),
           make_option("--coverage-with-migrations",
                       action="store_true", default=False,
                       dest="coverage_with_migrations",
               help="Don't measure migrations coverage."),
           make_option("--coverage-exclude", action="append",
                       default=[], dest="coverage_excludes",
               help="Module name to exclude")]

    def __init__(self, test_labels, options):
        super(Task, self).__init__(test_labels, options)
        self.test_apps = get_apps_under_test(test_labels, options['test_all'])
        self.output_dir = options['output_dir']
        self.with_migrations = options.get('coverage_with_migrations',
                                    getattr(settings,
                                            'COVERAGE_WITH_MIGRATIONS', False))

        self.html_dir = options.get('coverage_html_report_dir') or \
                            getattr(settings,
                                    'COVERAGE_REPORT_HTML_OUTPUT_DIR', '')

        self.branch = options.get('coverage_measure_branch',
                                  getattr(settings,
                                          'COVERAGE_MEASURE_BRANCH', True))

        self.exclude_locations = []
        modnames = options.get('coverage_excludes') or \
                        getattr(settings, 'COVERAGE_EXCLUDES', [])
        for modname in modnames:
            try:
                self.exclude_locations.append(
                        os.path.dirname(
                            import_module(modname).__file__
                        )
                )
            except ImportError:
                pass

        # Extra folders to exclude. Particularly useful to specify things like
        # apps/company/migrations/*
        self.exclude_locations.extend(
                        getattr(settings, 'COVERAGE_EXCLUDES_FOLDERS', []))

        omit = self.exclude_locations
        if not omit:
            omit = None

        self.coverage = coverage(branch=self.branch,
                                 source=self.test_apps,
                                 omit=omit,
                                 config_file=options.get('coverage_rcfile') or
                                                 Task.default_config_path())

    def setup_test_environment(self, **kwargs):
        self.coverage.start()

    def teardown_test_environment(self, **kwargs):
        self.coverage.stop()
        self.coverage._harvest_data()
        morfs = [filename for filename in self.coverage.data.measured_files()
                 if self.want_file(filename)]

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.coverage.xml_report(morfs=morfs,
                                 outfile=os.path.join(
                                        self.output_dir, 'coverage.xml'))

        if self.html_dir:
            self.coverage.html_report(morfs=morfs, directory=self.html_dir)

    def want_file(self, filename):
        if not self.with_migrations and (os.sep + 'migrations' + os.sep) in filename:
            return False
        for location in self.exclude_locations:
            if filename.startswith(location):
                return False

        return True

    @staticmethod
    def default_config_path():
        rcfile = getattr(settings, 'COVERAGE_RCFILE', 'coverage.rc')
        if os.path.exists(rcfile):
            return rcfile
        return None

########NEW FILE########
__FILENAME__ = with_local_celery
# -*- coding: utf-8; mode: django -*-
from django.conf import settings
from django_jenkins.tasks import BaseTask


class Task(BaseTask):
    """
    Run all celery tasks locally, not in a worker.
    """

    def setup_test_environment(self, **kwargs):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django.test import TestCase


class SanityCheckTest(TestCase):
    def test_is_ok(self):
        pass

########NEW FILE########
__FILENAME__ = manage
# -*- coding: utf-8 -*-
import os, sys
from django.core.management import execute_from_command_line

PROJECT_ROOT = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv += ['test']

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG
ROOT_URLCONF = 'test_app.urls'
SECRET_KEY = 'nokey'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

PROJECT_APPS = (
    'django.contrib.sessions',  # just to ensure that dotted apps test works
    'django_jenkins',
    'test_app',
    'test_app_dirs',
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
) + PROJECT_APPS


DATABASE_ENGINE = 'sqlite3'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.%s' % DATABASE_ENGINE,
        }
}

JENKINS_TASKS = (
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.run_pylint',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.run_flake8',
    'django_jenkins.tasks.run_jshint',
    'django_jenkins.tasks.run_csslint',
    'django_jenkins.tasks.run_sloccount',
    'django_jenkins.tasks.with_local_celery',
)


JSHINT_CHECKED_FILES = [os.path.join(PROJECT_ROOT, 'static/js/test.js')]
CSSLINT_CHECKED_FILES = [os.path.join(PROJECT_ROOT, 'static/css/test.css')]


STATIC_URL = '/media/'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = example_steps
# -*- coding: utf-8 -*-
from lettuce import step, before

@before.each_scenario
def setup_scenario(scenario):
    scenario.numbers = []

@step('(?:Given|And|When) the number "(.*)"(?: is added to (?:it|them))?')
def given_the_number(step, number):
    step.scenario.numbers.append(int(number))

@step('Then the result should be "(.*)"')
def then_the_result_should_equal(step, result):
    actual = sum(step.scenario.numbers)
    assert int(result) == actual, "%s != %s" % (result, actual)

########NEW FILE########
__FILENAME__ = 0001_initial
from south.v2 import SchemaMigration

class Migration(SchemaMigration):
    def forwards(self, orm):
        a = 1 # pyflakes/pylint violation
        pass

    def backwards(self, orm):
        pass

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import sys
from django.core import mail
from django.test import TestCase
from django.utils.unittest import skip
from django.test import LiveServerTestCase
from selenium.webdriver.firefox.webdriver import WebDriver


class SaintyChecks(TestCase):
    #@classmethod
    #def setUpClass(cls):
    #    raise Exception("Ups, should be disabled")

    def test_mailbox_stubs_not_broken(self):
        print("Testing mailbox django stubs")
        mail.send_mail('Test subject', 'Test message', 'nobody@kenkins.com',
                       ['somewhere@nowhere.com'])
        self.assertTrue(1, len(mail.outbox))

    @skip("Check skiped test")
    def test_is_skipped(self):
        print("This test should be skipped")

    def test_junit_xml_with_utf8_stdout_and_stderr(self):
        sys.stdout.write('\xc4\x85')
        sys.stderr.write('\xc4\x85')

    def test_junit_xml_with_invalid_stdout_and_stderr_encoding(self):
        sys.stdout.write('\xc4')
        sys.stderr.write('\xc4')


    #def test_failure(self):
    #    raise Exception("Ups, should be disabled")


class SeleniumTests(LiveServerTestCase):
    fixtures = ['default_users.json']

    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(SeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(SeleniumTests, cls).tearDownClass()
        cls.selenium.quit()

    def test_login(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/test_click/'))
        self.selenium.find_element_by_id("wm_click").click()
        self.assertEqual('Button clicked', self.selenium.find_element_by_id("wm_target").text)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.views.generic.base import TemplateView

urlpatterns = patterns('',  # NOQA
     url(r'^test_click/$', TemplateView.as_view(template_name='test_app/wm_test_click.html'), name='wm_test_click')
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = test_discovery_dir_tests
# -*- coding: utf-8 -*-
from django.test import TestCase


class DirDiscoveryTest(TestCase):
    def test_should_be_dicoverd(self):
        """
        Yep!
        """

########NEW FILE########
