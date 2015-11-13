__FILENAME__ = base
# -*- coding: utf-8 -*-

class Achievement(object):
    template = """
  /.–==*==–.\\
 ( |      #| ) %(announcement)s
  ):      ':(
    `·…_…·´    %(title)s
      `H´      %(subtitle)s
     _.U._     %(message)s
    [_____]"""
    title = None
    subtitle = None
    message = None

    def configure(self, options, conf):
        pass
    
    def finalize(self, data, result):
        pass

    def announcement(self, info=None):
        template = self.template
        try:
            template = template.decode('utf-8')
        except AttributeError:
            pass
        return template % {'announcement': "Achievement unlocked!",
                           'title': self.title or "",
                           'subtitle': self.subtitle or "",
                           'message': self.message or ""}


########NEW FILE########
__FILENAME__ = builtin
# -*- coding: utf-8 -*-
import sys
import re
import math
from datetime import datetime, time, timedelta
from noseachievements.achievements.base import Achievement
# Python 3 compatibility:
from noseachievements.compat import StringIO


__all__ = ['NightShift', 'Punctuality', 'InstantFeedback', 'CoffeeBreak',
           'TakeAWalk', 'FullOfDots', 'MockingMe', 'GreatExpectations',
           'CompleteFailure', 'EpicFail', 'MinorLetdown', 'MajorLetdown',
           'HappyEnding', 'ToUnderstandRecursion', 'TakeANap',
           'TakeAVacation', 'SausageFingers', 'CodeCoverage']


class NightShift(Achievement):
    key = 'builtin:night-shift'
    title = "Night Shift"
    message = "Don't you think it's getting a bit late?"
    template = """
     .·:´   |   *
 * ·::·   – ¤ –      %(announcement)s
  :::::     |
  :::::.        .:   %(title)s
   :::::`:·..·:´:'   %(subtitle)s
    `·::::::::·´  *  %(message)s
        ˘˘˘˘"""

    shift_start = time(0, 0)
    shift_end = time(5, 0)

    def finalize(self, data, result):
        if (data['result.tests'] and data['result.success'] and
            data['history'] and
            not data['history'][-1].get('result.success', True) and
            self.shift_start <= data['time.start'].time() < self.shift_end and
            self.shift_start <= data['time.finish'].time() < self.shift_end):
            data.unlock(self)

class Punctuality(Achievement):
    key = 'builtin:punctuality'
    title = "Punctuality"

    punctual_start = time(8, 59)
    punctual_end = time(9, 1)

    def finalize(self, data, result):
        if (data['result.tests'] and data['result.success'] and
            data['history'] and
            not data['history'][-1].get('result.success', True) and
            (self.punctual_start <= data['time.start'].time() <
             self.punctual_end or self.punctual_start <=
             data['time.finish'].time() < self.punctual_end)):
            data.unlock(self)

class InstantFeedback(Achievement):
    key = 'builtin:instant-feedback'
    title = "Instant Feedback"

    def finalize(self, data, result):
        duration = data['time.finish'] - data['time.start']
        if len(data['result.tests']) >= 50 and duration < timedelta(seconds=1):
            data.unlock(self)

class CoffeeBreak(Achievement):
    key = 'builtin:coffee-break'
    title = "Coffee Break"
    template = """
          (
        (  )
      .·:)::·.
   _.|`·::::·´|  %(announcement)s
 /,¯`,        |
 :'_.|        |  %(title)s
  `¯˘:        |  %(subtitle)s
      `·.__.·´"""

    def finalize(self, data, result):
        duration = data['time.finish'] - data['time.start']
        if timedelta(minutes=5) <= duration < timedelta(minutes=15):
            data.unlock(self)

class TakeAWalk(Achievement):
    key = 'builtin:take-a-walk'
    title = "Take a Walk"

    def finalize(self, data, result):
        duration = data['time.finish'] - data['time.start']
        if timedelta(minutes=15) <= duration < timedelta(minutes=60):
            data.unlock(self)

class TakeANap(Achievement):
    key = 'builtin:take-a-nap'
    title = "Take a Nap"

    def finalize(self, data, result):
        duration = data['time.finish'] - data['time.start']
        if timedelta(hours=1) <= duration < timedelta(hours=5):
            data.unlock(self)

class TakeAVacation(Achievement):
    key = 'builtin:take-a-vacation'
    title = "Take a Vacation"

    def finalize(self, data, result):
        duration = data['time.finish'] - data['time.start']
        if duration >= timedelta(days=3):
            data.unlock(self)

class CompleteFailure(Achievement):
    key = 'builtin:complete-failure'
    title = "Complete Failure"

    def finalize(self, data, result):
        if (50 <= len(data['result.tests']) <= 999 and
            len(data['result.tests']) == len(data['result.failures'])):
            data.unlock(self)

class EpicFail(Achievement):
    key = 'builtin:epic-fail'
    title = "Epic Fail"

    def finalize(self, data, result):
        if (len(data['result.tests']) >= 1000 and
            len(data['result.tests']) == len(data['result.failures'])):
            data.unlock(self)

class MinorLetdown(Achievement):
    key = 'builtin:minor-letdown'
    title = "Minor Letdown"
    
    def finalize(self, data, result):
        if re.match(r'[.]{9,98}[FE]$', data['result.string']):
            data.unlock(self)

class MajorLetdown(Achievement):
    key = 'builtin:major-letdown'
    title = "Major Letdown"

    def finalize(self, data, result):
        if re.match(r'[.]{99,}[FE]$', data['result.string']):
            data.unlock(self)

class HappyEnding(Achievement):
    key = 'builtin:happy-ending'
    title = "Happy Ending"

    def finalize(self, data, result):
        if re.match(r'[EF]{9,}[.]$', data['result.string']):
            data.unlock(self)

class FullOfDots(Achievement):
    key = 'builtin:my-god-its-full-of-dots'
    title = "My God, It's Full of Dots"

    def finalize(self, data, result):
        if data['result.string'].count('.') >= 2001:
            data.unlock(self)

class MockingMe(Achievement):
    key = 'builtin:mocking-me'
    title = "Are You Mocking Me?"
    mocking_modules = ['mock', 'mocker', 'pmock', 'dingus', 'mox', 'ludibrio',
                       'minimock', 'mocktest', 'mocky', 'plone.mocktestcase',
                       'pymock', 'fudge']

    def __init__(self, imported_modules=sys.modules):
        self.imported_modules = imported_modules

    def __getstate__(self):
        return {'imported_modules': dict.fromkeys(self.imported_modules)}

    def finalize(self, data, result):
        for module in self.mocking_modules:
            if module in self.imported_modules:
                data.unlock(self)
                break

class GreatExpectations(Achievement):
    key = 'builtin:great-expectations'
    title = "Great Expectations"

    def __init__(self, imported_modules=sys.modules):
        self.imported_modules = imported_modules

    def __getstate__(self):
        return {'imported_modules': dict.fromkeys(self.imported_modules)}

    def finalize(self, data, result):
        if 'expecter' in self.imported_modules:
            data.unlock(self)

class ToUnderstandRecursion(Achievement):
    key = 'builtin:to-understand-recursion'
    title = "To Understand Recursion..."

    def finalize(self, data, result):
        for test, (type_, value, exc_string) in data['result.errors']:
            if exc_string.endswith("RuntimeError: maximum recursion depth "
                                   "exceeded\n"):
                data.unlock(self)
                break

class SausageFingers(Achievement):
    key = 'builtin:sausage-fingers'
    title = "Sausage Fingers"

    def finalize(self, data, result):
        syntax_errors = set()
        for test, (type_, value, exc_string) in data['result.errors']:
            if type_ is SyntaxError:
                syntax_errors.add((value.filename, value.lineno))
        if len(syntax_errors) > 1:
            data.unlock(self)

class CodeCoverage(Achievement):
    key = 'builtin:100-code-coverage'
    title = "100% Code Coverage"
    template = """
            .
         .cd'b;
     _  (xk',kx)
   ckko  lk kd/      %(announcement)s
  (kk.`l_)k k(_,dl,
   `·q. lk',kp'´dk)  %(title)s
    _)k.'q k',.d·´   %(subtitle)s
   ldxkkp, ,xq(_     %(message)s
    `-^·´u|u^-·´
          |"""

    def configure(self, options, conf):
        self.enabled = getattr(options, 'enable_plugin_coverage', False)
        if self.enabled:
            try:
                from coverage import coverage
            except ImportError:
                self.enabled = False
            else:
                self.coverage = coverage

    def finalize(self, data, result):
        if self.enabled and data['result.success']:
            coverage = self.coverage()
            coverage.load()
            report = StringIO()
            coverage.report(file=report)
            report_string = report.getvalue()
            last_line = report_string.splitlines()[-1]
            match = re.match(r'TOTAL\s+(?P<stmts>\d+)\s+(?P<exec>\d+)\s+'
                             r'(?P<cover>\d+)%', last_line)
            if match:
                statements = int(match.group('stmts'))
                executed = int(match.group('exec'))
                percent_covered = int(match.group('cover'))
                if percent_covered == 100:
                    level = int(math.log(statements, 2) - 7)
                    data.unlock(self)


########NEW FILE########
__FILENAME__ = compat
try:
    basestring = basestring
except NameError:
    basestring = str

try:
    unicode = unicode
except NameError:
    unicode = str

try:
    callable = callable
except NameError:
    def callable(obj):
        return hasattr(obj, '__call__')

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import cPickle as pickle
except ImportError:
    import pickle


########NEW FILE########
__FILENAME__ = data
import logging
from noseachievements.compat import pickle


log = logging.getLogger(__name__)

class AchievementData(dict):
    PICKLE_PROTOCOL = 2

    def save(self, stream):
        pickle.dump(self, stream, self.PICKLE_PROTOCOL)

    @classmethod
    def load(cls, stream):
        try:
            return pickle.load(stream)
        except EOFError:
            log.warning("Empty data file, returning empty data")
            return cls()

    def unlock(self, achievement):
        if achievement.key not in self['achievements.unlocked']:
            self['achievements.unlocked'][achievement.key] = achievement
            self['achievements.new'].append(achievement)


########NEW FILE########
__FILENAME__ = djangotest
from django.test.simple import DjangoTestRunner, DjangoTestSuiteRunner

from noseachievements.plugin import AchievementsPlugin
from noseachievements.result import AchievementsTestResult
from noseachievements.runner import AchievementsTestRunner


class AchievementsDjangoTestResult(AchievementsTestResult):
    def stopTest(self, test):
        super(AchievementsDjangoTestResult, self).stopTest(test)
        if ((self._runner.failfast and not self.wasSuccessful()) or 
            self._runner._keyboard_interrupt_intercepted):
            self.stop()

class AchievementsDjangoTestRunner(DjangoTestRunner, AchievementsTestRunner):
    _result_class = AchievementsDjangoTestResult

    def _makeResult(self):
        result = super(AchievementsDjangoTestRunner, self)._makeResult()
        result._runner = self
        return result

class AchievementsDjangoTestSuiteRunner(DjangoTestSuiteRunner):
    _runner_class = AchievementsDjangoTestRunner

    def run_suite(self, suite, **kwargs):
        return self._runner_class(verbosity=self.verbosity,
                                  failfast=self.failfast).run(suite)


########NEW FILE########
__FILENAME__ = manager
import noseachievements.achievements.builtin
from noseachievements.achievements.base import Achievement
# Python 3 compatibility:
from noseachievements.compat import callable, basestring

class AchievementManager(object):
    def __init__(self, achievements=()):
        self.achievements = {}
        self.add_achievements(achievements)

    def __iter__(self):
        return iter(self.achievements.values())

    def __contains__(self, achievement):
        if not isinstance(achievement, basestring):
            achievement = achievement.key
        return achievement in self.achievements
    
    def __len__(self):
        return len(self.achievements)
    
    def add_achievement(self, achievement):
        if callable(achievement):
            achievement = achievement()
        self.achievements[achievement.key] = achievement

    def add_achievements(self, achievements):
        for achievement in achievements:
            self.add_achievement(achievement)

    def load(self):
        pass

class BuiltinAchievementManager(AchievementManager):
    def load(self):
        AchievementManager.load(self)
        for name in noseachievements.achievements.builtin.__all__:
            achievement = getattr(noseachievements.achievements.builtin, name)
            self.add_achievement(achievement)

class EntryPointAchievementManager(AchievementManager):
    entry_point = 'nose.achievements'

    def __init__(self, entry_point=None):
        AchievementManager.__init__(self)
        if entry_point is not None:
            self.entry_point = entry_point

    def load(self):
        AchievementManager.load(self)
        from pkg_resources import iter_entry_points
        for entry_point in iter_entry_points(self.entry_point):
            achievement = entry_point.load()
            if callable(achievement):
                achievement = achievement()
            self.add_achievement(achievement)

try:
    from pkg_resources import iter_entry_points
except ImportError:
    default_manager = BuiltinAchievementManager
else:
    default_manager = EntryPointAchievementManager

class FilterAchievementManager(AchievementManager):
    def __init__(self, keys, manager=default_manager, default='all'):
        AchievementManager.__init__(self)
        self.include_keys = set()
        self.exclude_keys = set()
        self.add_filter(keys)
        if not self.include_keys and default is not None:
            self.add_filter(default)
        if callable(manager):
            manager = manager()
        self.manager = manager

    def add_filter(self, keys):
        if isinstance(keys, basestring):
            keys = keys.split(',')
        for key in keys:
            if key.startswith('-'):
                self.exclude_keys.add(key[1:])
            else:
                self.include_keys.add(key)

    def load(self):
        self.manager.load()
        for achievement in self.manager:
            key = achievement.key
            group, name = key.split(':', 1)
            if ('all' in self.include_keys or key in self.include_keys or
                group in self.include_keys):
                if (key not in self.exclude_keys and
                    group not in self.exclude_keys):
                    self.add_achievement(achievement)


########NEW FILE########
__FILENAME__ = plugin
import logging
import codecs
from traceback import format_exception
from datetime import datetime

from noseachievements.data import AchievementData
from noseachievements.manager import (AchievementManager,
    FilterAchievementManager, default_manager)

try:
    from nose.plugins import Plugin
except ImportError:
    Plugin = object
try:
    from nose.util import test_address
except ImportError:
    def test_address(test):
        return test.id()

# Python 3 compatibility:
from noseachievements.compat import callable, unicode


log = logging.getLogger(__name__)

class AchievementsPlugin(Plugin):
    name = 'achievements'
    score = -1000
    default_filename = '.achievements'
    default_achievements = 'all'

    def __init__(self, achievements=default_manager, data=None):
        super(AchievementsPlugin, self).__init__()
        if callable(achievements):
            achievements = achievements()
        if not isinstance(achievements, AchievementManager):
            achievements = AchievementManager(achievements)
        self.achievements = achievements
        self.data = AchievementData(data or {})
        self.output_stream = None

    def options(self, parser, env):
        if Plugin is not object:
            super(AchievementsPlugin, self).options(parser, env)

        parser.add_option('--achievements-file', action='store',
            default=env.get('ACHIEVEMENTS_FILE', self.default_filename),
            metavar='FILE', dest='data_filename',
            help="Load and save achievement data in FILE. "
                 "An empty string will disable loading and saving. "
                 "[ACHIEVEMENTS_FILE]")
        parser.add_option('--achievements', action='store',
            default=env.get('ACHIEVEMENTS', self.default_achievements),
            metavar='FILTER', dest='achievements',
            help="Select or exclude specific achievements or achievement "
                 "groups. [ACHIEVEMENTS]")
    
    def configure(self, options, conf):
        # Save a reference to the `Config` to access its `stream` in case
        # setOutputStream isn't called.
        self.config = conf
        if Plugin is not object:
            super(AchievementsPlugin, self).configure(options, conf)

        self.data_filename = options.data_filename or None

        if options.achievements is not None:
            self.achievements = FilterAchievementManager(options.achievements,
                                                         self.achievements)

        self.achievements.load()
        for achievement in self.achievements:
            achievement.configure(options, conf)

    def begin(self):
        history = []
        unlocked = {}
        if self.data_filename:
            try:
                data_file = open(self.data_filename, 'rb')
            except IOError:
                log.debug("Failed to read achievement data from %s",
                          self.data_filename)
            else:
                data = AchievementData.load(data_file)
                data_file.close()
                log.info("Loaded achievement data from %s",
                         self.data_filename)
                history = data.pop('history', history)
                history.append(data)
                del history[:-10]
                unlocked = data.get('achievements.unlocked', unlocked)

        self.data.setdefault('history', history)
        self.data.setdefault('achievements.unlocked', unlocked)
        self.data.setdefault('achievements.new', [])
        self.data.setdefault('result.tests', [])
        self.data.setdefault('result.string', '')
        self.data.setdefault('result.errors', [])
        self.data.setdefault('result.failures', [])
        self.data.setdefault('time.start', datetime.now())

    def addError(self, test, err):
        type_, value, traceback = err
        exc_string = "".join(format_exception(type_, value, traceback))
        self.data['result.string'] += 'E'
        self.data['result.errors'].append((test_address(test),
                                           (type_, value, exc_string)))

    def addFailure(self, test, err):
        type_, value, traceback = err
        exc_string = "".join(format_exception(type_, value, traceback))
        self.data['result.string'] += 'F'
        self.data['result.failures'].append((test_address(test),
                                             (type_, value, exc_string)))

    def addSuccess(self, test):
        self.data['result.string'] += '.'

    def afterTest(self, test):
        self.data['result.tests'].append(test_address(test))

    def setOutputStream(self, stream):
        self.output_stream = stream

    def finalize(self, result):
        self.data.setdefault('time.finish', datetime.now())
        self.data.setdefault('result.success', result.wasSuccessful())
        
        for achievement in self.achievements:
            if achievement.key not in self.data['achievements.unlocked']:
                achievement.finalize(self.data, result)

        if self.data_filename:
            try:
                data_file = open(self.data_filename, 'wb')
            except IOError:
                log.error("Failed to write achievement data to %s (I/O error)",
                          self.data_filename)
            else:
                log.info("Saving achievement data to %s", self.data_filename)
                self.data.save(data_file)
                data_file.close()

        output_stream = self.output_stream or self.config.stream
        if str is not unicode:
            output_stream = codecs.getwriter('utf-8')(output_stream)
        for achievement in self.data['achievements.new']:
            announcement = achievement.announcement()
            output_stream.write(announcement)
            output_stream.write('\n')


########NEW FILE########
__FILENAME__ = result
import unittest


class AchievementsTestResult(unittest._TextTestResult):
    def __init__(self, *args, **kwargs):
        self.plugin = kwargs.pop('plugin', None)
        super(AchievementsTestResult, self).__init__(*args, **kwargs)

    def stopTest(self, test):
        self.plugin.afterTest(test)
        return super(AchievementsTestResult, self).stopTest(test)

    def addSuccess(self, test):
        self.plugin.addSuccess(test)
        return super(AchievementsTestResult, self).addSuccess(test)

    def addError(self, test, err):
        self.plugin.addError(test, err)
        return super(AchievementsTestResult, self).addError(test, err)

    def addFailure(self, test, err):
        self.plugin.addFailure(test, err)
        return super(AchievementsTestResult, self).addFailure(test, err)


########NEW FILE########
__FILENAME__ = runner
import os
import sys
from unittest import TextTestRunner
from optparse import OptionParser

from noseachievements.result import AchievementsTestResult
from noseachievements.plugin import AchievementsPlugin

try:
    from nose.config import Config
except ImportError:
    config = None
else:
    config = Config()


class AchievementsTestRunner(TextTestRunner):
    _result_class = AchievementsTestResult

    def __init__(self, *args, **kwargs):
        plugin = kwargs.pop('plugin', None)
        super(AchievementsTestRunner, self).__init__(*args, **kwargs)
        if plugin is None:
            plugin = AchievementsPlugin()
        parser = OptionParser()
        plugin.options(parser, os.environ)
        options, args = parser.parse_args([])
        plugin.configure(options, config)
        plugin.enabled = True
        self.plugin = plugin

    def _makeResult(self):
        return self._result_class(self.stream, self.descriptions,
                                  self.verbosity, plugin=self.plugin)

    def run(self, test):
        self.plugin.begin()
        result = super(AchievementsTestRunner, self).run(test)
        self.plugin.setOutputStream(self.stream)
        self.plugin.finalize(result)
        return result


########NEW FILE########
__FILENAME__ = helpers
import unittest
from cStringIO import StringIO

from nose.plugins.plugintest import PluginTester
from nose.plugins.skip import SkipTest

from noseachievements.achievements.base import Achievement
from noseachievements.plugin import AchievementsPlugin


def pass_func():
    assert True

def fail_func():
    assert False

def error_func():
    raise Exception

def error_test(exception):
    def error_func():
        raise exception
    return unittest.FunctionTestCase(error_func)
error_test.__test__ = False

PASS = unittest.FunctionTestCase(pass_func)
FAIL = unittest.FunctionTestCase(fail_func)
ERROR = unittest.FunctionTestCase(error_func)

class TestPlugin(PluginTester, unittest.TestCase):
    activate = '--with-achievements'
    args = ['--achievements-file=']
    tests = [PASS]
    data = None
    achievements = []

    def setUp(self):
        self.plugin = AchievementsPlugin(self.achievements, self.data)
        self.plugins = [self.plugin]
        PluginTester.setUp(self)

    def makeSuite(self):
        return self.tests

    def test_data_is_serializable(self):
        if self.plugin.enabled:
            stream = StringIO()
            self.plugin.data.save(stream)
            self.assertTrue(stream.getvalue())

class NeverUnlockedAchievement(Achievement):
    key = 'test:never-unlocked'
    title = "Test Achievement"
    subtitle = "Test Subtitle"
    message = "Test Message"

class AlwaysUnlockedAchievement(Achievement):
    key = 'test:always-unlocked'
    title = "Test Achievement"
    subtitle = "Test Subtitle"
    message = "Test Message"

    def finalize(self, data, result):
        data.unlock(self)


########NEW FILE########
__FILENAME__ = run_all
#!/usr/bin/env python
import nose

if __name__ == '__main__':
    nose.run()


########NEW FILE########
__FILENAME__ = test_achievement
# -*- coding: utf-8 -*-
import unittest

from noseachievements.achievements.base import Achievement
from noseachievements.compat import unicode

from helpers import (PASS, TestPlugin, NeverUnlockedAchievement,
    AlwaysUnlockedAchievement)


class TestAchievement(TestPlugin):
    achievement = NeverUnlockedAchievement()
    achievements = [achievement]

    def test_achievement_is_loaded(self):
        self.assert_(self.achievement in self.plugin.achievements)

    def test_no_achievements_are_printed(self):
        self.assert_("Ran 1 test" in self.output)
        self.assert_("Achievement unlocked" not in self.output)

    def test_announcement_returns_unlocked_string(self):
        self.assertEqual(self.achievement.announcement(), unicode("""
  /.–==*==–.\\
 ( |      #| ) Achievement unlocked!
  ):      ':(
    `·…_…·´    Test Achievement
      `H´      Test Subtitle
     _.U._     Test Message
    [_____]""", 'utf-8'))


class TestUnlockedAchievement(TestPlugin):
    def setUp(self):
        self.achievement = AlwaysUnlockedAchievement()
        self.achievements = [self.achievement]
        TestPlugin.setUp(self)

    def test_achievement_is_printed(self):
        self.assert_("""
  /.–==*==–.\\
 ( |      #| ) Achievement unlocked!
  ):      ':(
    `·…_…·´    Test Achievement
      `H´      Test Subtitle
     _.U._     Test Message
    [_____]""" in self.output)
            


########NEW FILE########
__FILENAME__ = test_builtin_achievements
# -*- coding: utf-8 -*-
import unittest
from datetime import datetime

from noseachievements.plugin import AchievementsPlugin
from noseachievements.achievements.builtin import (CompleteFailure, EpicFail,
    MinorLetdown, MajorLetdown, HappyEnding, NightShift, Punctuality,
    SausageFingers, ToUnderstandRecursion, InstantFeedback, CoffeeBreak,
    TakeAWalk, TakeANap, TakeAVacation, MockingMe, FullOfDots,
    GreatExpectations)

from helpers import PASS, FAIL, ERROR, TestPlugin, error_test

class TestNightShiftAchievement(TestPlugin):
    achievements = [NightShift]
    data = {'time.start': datetime(2010, 1, 1, 23, 59, 59),
            'time.finish': datetime(2010, 1, 1, 23, 59, 59)}

    def test_achievement_is_not_unlocked(self):
        self.assert_("Achievement unlocked" not in self.output and
                     "Night Shift" not in self.output)

class TestNightShiftAchievementFailures(TestNightShiftAchievement):
    tests = [PASS, FAIL]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 0, 0)}

class TestNightShiftAchievementErrors(TestNightShiftAchievement):
    tests = [PASS, ERROR]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 0, 0)}

class TestNightShiftAchievementLastPassed(TestNightShiftAchievement):
    tests = [PASS]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 0, 0),
            'history': [{'result.success': True}]}

class TestNightShiftAchievementUnlocked(TestPlugin):
    achievements = [NightShift]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 0, 0),
            'history': [{'result.success': False}]}

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked" in self.output and
                     "Night Shift" in self.output)

class TestPunctualityAchievement(TestPlugin):
    achievements = [Punctuality]
    data = {'time.start': datetime(2010, 1, 1, 8, 58, 59),
            'time.finish': datetime(2010, 1, 1, 8, 58, 59)}

    def test_achievement_is_not_unlocked(self):
        self.assert_("Achievement unlocked" not in self.output and
                     "Punctuality" not in self.output)

class TestPunctualityAchievementFailures(TestPunctualityAchievement):
    tests = [PASS, FAIL]
    data = {'time.start': datetime(2010, 1, 1, 9, 0, 0),
            'time.finish': datetime(2010, 1, 1, 9, 0, 0)}

class TestPunctualityAchievementErrors(TestPunctualityAchievement):
    tests = [PASS, ERROR]
    data = {'time.start': datetime(2010, 1, 1, 9, 0, 0),
            'time.finish': datetime(2010, 1, 1, 9, 0, 0)}

class TestPunctualityAchievementUnlocked(TestPlugin):
    achievements = [Punctuality]
    data = {'time.start': datetime(2010, 1, 1, 9, 0, 0),
            'time.finish': datetime(2010, 1, 1, 9, 0, 0),
            'history': [{'result.success': False}]}

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked" in self.output and
                     "Punctuality" in self.output)

class TestCompleteFailureAchievement(TestPlugin):
    achievements = [CompleteFailure]
    tests = [FAIL] * 49

    def test_achievement_is_not_unlocked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestCompleteFailureAchievementUnlocked(TestPlugin):
    achievements = [CompleteFailure]
    tests = [FAIL] * 999

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Complete Failure" in self.output)

class TestEpicFailAchievement(TestPlugin):
    achievements = [EpicFail]
    tests = [FAIL] * 999

    def test_achievement_is_not_unlocked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestEpicFailAchievementUnlocked(TestPlugin):
    achievements = [EpicFail]
    tests = [FAIL] * 1000

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Epic Fail" in self.output)

class TestMinorLetdownAchievement(TestPlugin):
    achievements = [MinorLetdown]
    tests = [FAIL] + [PASS] * 9

    def test_achievement_is_not_unlocked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestRecursionAchievement(TestPlugin):
    achievements = [ToUnderstandRecursion]
    tests = [error_test(RuntimeError("foo"))]

    def test_achievement_is_not_unlocked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestRecursionAchievementUnlocked(TestPlugin):
    achievements = [ToUnderstandRecursion]
    tests = [error_test(RuntimeError("maximum recursion depth exceeded"))]

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "To Understand Recursion..." in self.output)

class TestSausageFingersAchievement(TestPlugin):
    achievements = [SausageFingers]
    tests = [ERROR]

    def test_achievement_is_not_unlocked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestSausageFingersAchievementUnlocked(TestPlugin):
    achievements = [SausageFingers]
    tests = [unittest.FunctionTestCase(
        lambda: compile("def /", 'a.py', 'exec')),
             unittest.FunctionTestCase(
        lambda: compile("def /", 'b.py', 'exec'))]

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Sausage Fingers" in self.output)

class TestInstantFeedbackAchievementNotEnoughTests(TestPlugin):
    achievements = [InstantFeedback]
    tests = [PASS] * 49
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 0, 0, 1)}

    def test_achievement_is_locked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestInstantFeedbackAchievementTooSlow(TestPlugin):
    achievements = [InstantFeedback]
    tests = [PASS] * 49
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 0, 1, 0)}

    def test_achievement_is_locked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestInstantFeedbackAchievementUnlocked(TestPlugin):
    achievements = [InstantFeedback]
    tests = [ERROR] * 20 + [FAIL] * 20 + [PASS] * 10
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 0, 0, 1)}

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Instant Feedback" in self.output)

class TestCoffeeBreakAchievement(TestPlugin):
    achievements = [CoffeeBreak]
    tests = [PASS]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 4, 59)}

    def test_achievement_is_locked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestCoffeeBreakAchievementUnlocked(TestPlugin):
    achievements = [CoffeeBreak]
    tests = [ERROR]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 5, 0)}

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Coffee Break" in self.output)

class TestTakeAWalkAchievementUnlocked(TestPlugin):
    achievements = [TakeAWalk]
    tests = [ERROR]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 0, 15, 0)}

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Take a Walk" in self.output)

class TestTakeANapAchievementUnlocked(TestPlugin):
    achievements = [TakeANap]
    tests = [ERROR]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 1, 1, 0, 0)}

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Take a Nap" in self.output)

class TestTakeAVacationAchievementUnlocked(TestPlugin):
    achievements = [TakeAVacation]
    tests = [ERROR]
    data = {'time.start': datetime(2010, 1, 1, 0, 0, 0),
            'time.finish': datetime(2010, 1, 4, 0, 0, 0)}

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Take a Vacation" in self.output)

class TestMinorLetdownAchievementUnlocked(TestPlugin):
    achievements = [MinorLetdown]
    tests = [PASS] * 9 + [FAIL]

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Minor Letdown" in self.output)

class TestMajorLetdownAchievementUnlocked(TestPlugin):
    achievements = [MajorLetdown]
    tests = [PASS] * 99 + [FAIL]

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Major Letdown" in self.output)

class TestHappyEndingAchievementUnlocked(TestPlugin):
    achievements = [HappyEnding]
    tests = [FAIL] * 9 + [PASS]

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Happy Ending" in self.output)

class TestMockingMeAchievement(TestPlugin):
    achievements = [MockingMe({'foo': None, 'bar': None})]

    def test_achievement_is_locked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestMockingMeAchievementUnlocked(TestPlugin):
    achievements = [MockingMe({'dingus': None})]

    def test_achievement_is_locked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Are You Mocking Me?" in self.output)

class TestMockingMeAchievementPickler(TestPlugin):
    data = {'achievements.new': [MockingMe()]}

class TestFullOfDotsAchievement(TestPlugin):
    achievements = [FullOfDots]
    tests = [PASS] * 2000

    def test_achievement_is_locked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestFullOfDotsAchievementUnlocked(TestPlugin):
    achievements = [FullOfDots]
    tests = [FAIL] + [PASS] * 2001

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "My God, It's Full of Dots" in self.output)

class TestGreatExpectationsAchievement(TestPlugin):
    achievements = [GreatExpectations({'expect': None})]

    def test_achievement_is_locked(self):
        self.assert_("Achievement unlocked!" not in self.output)

class TestGreatExpectationsAchievementUnlocked(TestPlugin):
    achievements = [GreatExpectations({'expecter': None})]

    def test_achievement_is_unlocked(self):
        self.assert_("Achievement unlocked!" in self.output and
                     "Great Expectations" in self.output)

class TestMockingMeAchievementPickler(TestPlugin):
    data = {'achievements.new': [GreatExpectations()]}


########NEW FILE########
__FILENAME__ = test_data
import unittest
from datetime import datetime
from cStringIO import StringIO
from cPickle import dump, load

from noseachievements.data import AchievementData


class TestAchievementData(unittest.TestCase):
    def setUp(self):
        self.data = AchievementData({'time.start': datetime.now(),
                                     'time.finish': datetime.now()})
        self.stream = StringIO()
        self.data.save(self.stream)
        self.stream.seek(0)

    def test_is_dict(self):
        self.assert_(isinstance(self.data, dict))

    def test_save_writes_data_to_stream(self):
        stream = StringIO()
        dump(self.data, stream, AchievementData.PICKLE_PROTOCOL)
        self.assertEqual(self.stream.getvalue(), stream.getvalue())

    def test_load_reads_data_from_stream(self):
        data = AchievementData.load(self.stream)
        self.assertEqual(self.data, data)

class TestAchievementDataFromEmptyFile(unittest.TestCase):
    def setUp(self):
        self.stream = StringIO()

    def test_load_returns_empty_data_instead_of_eof_error(self):
        data = AchievementData.load(self.stream)
        self.assertEqual(data, AchievementData())


########NEW FILE########
__FILENAME__ = test_manager
import unittest

from nose.plugins.skip import SkipTest

import noseachievements.achievements.builtin
from noseachievements.manager import (AchievementManager,
                                      BuiltinAchievementManager,
                                      EntryPointAchievementManager,
                                      FilterAchievementManager)
from helpers import AlwaysUnlockedAchievement


class TestManager(unittest.TestCase):
    def setUp(self):
        self.achievements = [AlwaysUnlockedAchievement()]
        self.manager = AchievementManager(self.achievements * 2)
        self.manager.load()

    def test_does_not_add_duplicate_achievements(self):
        self.assertEqual(len(self.manager), 1)

    def test_achievement_key_is_in_manager(self):
        self.assertTrue(AlwaysUnlockedAchievement.key in self.manager)

    def test_other_instance_of_same_achievement_is_in_manager(self):
        self.assertTrue(AlwaysUnlockedAchievement() in self.manager)

    def test_iterating_manager_returns_achievements(self):
        self.assertEqual(list(self.manager), self.achievements)

class TestBuiltinAchievementManager(unittest.TestCase):
    def setUp(self):
        self.manager = BuiltinAchievementManager()
        self.manager.load()

    def test_includes_all_builtin_achievements(self):
        for name in noseachievements.achievements.builtin.__all__:
            achievement = getattr(noseachievements.achievements.builtin, name)()
            self.assertTrue(achievement in self.manager)

class TestFilterAchievementManager(unittest.TestCase):
    def setUp(self):
        self.manager = FilterAchievementManager('builtin', BuiltinAchievementManager)
        self.manager.load()
        self.builtin_manager = BuiltinAchievementManager()
        self.builtin_manager.load()

    def test_builtin_filter_includes_all_builtin_achievements(self):
        self.assertEqual(set(self.manager.achievements),
                         set(self.builtin_manager.achievements))

class TestFilterAchievementManagerAll(unittest.TestCase):
    def setUp(self):
        self.manager = FilterAchievementManager('all', BuiltinAchievementManager)
        self.manager.load()
        self.builtin_manager = BuiltinAchievementManager()
        self.builtin_manager.load()

    def test_builtin_filter_includes_all_builtin_achievements(self):
        self.assertEqual(set(self.manager.achievements),
                         set(self.builtin_manager.achievements))

class TestFilterAchievementManagerEmpty(unittest.TestCase):
    def setUp(self):
        self.manager = FilterAchievementManager('', BuiltinAchievementManager)
        self.manager.load()

    def test_empty_filter_includes_no_achievements(self):
        self.assertEqual(len(self.manager), 0)

class TestFilterAchievementManagerExclude(unittest.TestCase):
    def setUp(self):
        self.manager = FilterAchievementManager('-builtin:night-shift,'
                                                  '-builtin:punctuality',
                                                  BuiltinAchievementManager)
        self.manager.load()
        self.builtin_manager = BuiltinAchievementManager()
        self.builtin_manager.load()

    def test_achievements_are_excluded(self):
        achievements = set(self.builtin_manager.achievements)
        achievements.discard('builtin:night-shift')
        achievements.discard('builtin:punctuality')
        self.assertEqual(set(self.manager.achievements), achievements)

class TestFilterAchievementManagerExcludeAll(unittest.TestCase):
    def setUp(self):
        self.manager = FilterAchievementManager('-builtin',
                                                  BuiltinAchievementManager)
        self.manager.load()

    def test_all_achievements_are_excluded(self):
        self.assertEqual(len(self.manager), 0)


########NEW FILE########
__FILENAME__ = test_plugin
import unittest

from nose.plugins import Plugin

from noseachievements.achievements.base import Achievement
from noseachievements.manager import default_manager, FilterAchievementManager
from noseachievements.plugin import AchievementsPlugin
from helpers import PASS, TestPlugin


class TestDisabledPlugin(TestPlugin):
    activate = ''

    def test_is_plugin(self):
        self.assert_(isinstance(self.plugin, Plugin))

    def test_name_is_achievements(self):
        self.assertEqual(self.plugin.name, 'achievements')

    def test_is_not_enabled_by_default(self):
        self.assert_(not self.plugin.enabled)

    def test_has_data_dict(self):
        self.assert_(isinstance(self.plugin.data, dict))

    def test_data_is_not_shared(self):
        plugin = AchievementsPlugin()
        self.assert_(plugin.data is not self.plugin.data)

class TestEnabledPlugin(TestPlugin):
    data = {}

    def test_is_enabled(self):
        self.assert_(self.plugin.enabled)

    def test_no_achievements_are_loaded(self):
        self.assertEqual(len(self.plugin.achievements), 0)

    def test_no_achievements_are_printed(self):
        self.assert_("Ran 1 test" in self.output and
                     "OK" in self.output)

class TestPluginWithAchievementFilterInclude(TestPlugin):
    achievements = default_manager
    args = TestPlugin.args + ['--achievements=builtin:night-shift']

    def test_manager_is_filter_achievement_manager(self):
        self.assertTrue(isinstance(self.plugin.achievements,
                                   FilterAchievementManager))

    def test_manager_includes_achievement(self):
        self.assertEqual(self.plugin.achievements.include_keys,
                         set(['builtin:night-shift']))

    def test_manager_excludes_none(self):
        self.assertEqual(self.plugin.achievements.exclude_keys, set())

class TestPluginWithAchievementFilterAll(TestPlugin):
    args = TestPlugin.args + ['--achievements=all']

    def test_manager_includes_all(self):
        self.assertEqual(self.plugin.achievements.include_keys, set(['all']))

    def test_manager_excludes_none(self):
        self.assertEqual(self.plugin.achievements.exclude_keys, set())

class TestPluginWithAchievementFilterExclude(TestPlugin):
    args = TestPlugin.args + ['--achievements='
                              '-builtin:night-shift,-builtin:coffee-break']
    
    def test_manager_excludes_achievements(self):
        self.assertEqual(self.plugin.achievements.exclude_keys,
                         set(['builtin:night-shift', 'builtin:coffee-break']))

    def test_manager_includes_all(self):
        self.assertEqual(self.plugin.achievements.include_keys, set(['all']))

class TestPluginWithAchievementFilterEmpty(TestPlugin):
    args = TestPlugin.args + ['--achievements=']

    def test_manager_includes_empty_string(self):
        self.assertEqual(self.plugin.achievements.include_keys, set(['']))
    
    def test_manager_exculdes_none(self):
        self.assertEqual(self.plugin.achievements.exclude_keys, set())

########NEW FILE########
