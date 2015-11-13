__FILENAME__ = console
from finder import (find_steps_modules,
                    find_text_specs,
                    find_before_all,
                    find_before_each,
                    find_after_all,
                    find_after_each,)
from runner import StoryRunner
from optparse import OptionParser
import sys
import os

def pycukes_console(stories_dir, steps_dir, output, colored=False):
    modules = find_steps_modules(steps_dir)
    for spec in find_text_specs(stories_dir):
        StoryRunner(spec, output, colored=colored, modules=modules).run()


def main():
    steps_modules = []
    files = []
    before_all_methods = []
    before_each_methods = []
    after_all_methods = []
    after_each_methods = []
    stories_dirname = 'stories'
    for arg in sys.argv[1:]:
        if arg.startswith('-'):
            break
        files.append(arg)
        stories_dirname = os.path.dirname(arg) or '.'

    parser = OptionParser()
    parser.add_option('-s', '--stories-dir', default=None, dest='stories_dir')
    parser.add_option('-t', '--steps-dir', default=None, dest='steps_dir')
    parser.add_option('-n', '--no-colors', default=None, action='store_true', dest='no_colors')
    parser.add_option('-c', '--colored', default=None, action='store_true', dest='colored')
    parser.add_option('-l', '--language', default='en-us', dest='language')
    values, args = parser.parse_args()

    try:
        if values.stories_dir:
            files.extend([values.stories_dir+'/'+filename for filename in os.listdir(values.stories_dir)
                            if filename.endswith('.story')])
            stories_dirname = values.stories_dir
        elif files == []:
            files.extend([stories_dirname+'/'+filename for filename in os.listdir(stories_dirname)
                                              if filename.endswith('.story')])

        steps_modules = find_steps_modules(values.steps_dir or stories_dirname+'/step_definitions')
    except OSError:
        pass

    if os.path.exists(stories_dirname+'/support'):
        before_all_methods = find_before_all(stories_dirname+'/support')
        after_all_methods = find_after_all(stories_dirname+'/support')
        before_each_methods = find_before_each(stories_dirname+'/support')
        after_each_methods = find_after_each(stories_dirname+'/support')

    colored = True
    if values.no_colors and not values.colored:
        colored = False

    exit_code = True
    for index, story in enumerate(files):
        story_status = StoryRunner(open(story).read(),
                                         sys.stdout,
                                         colored=colored,
                                         modules=steps_modules,
                                         language=values.language,
                                         before_all=before_all_methods,
                                         before_each=before_each_methods,
                                         after_all=after_all_methods,
                                         after_each=after_each_methods).run()
        exit_code = exit_code and story_status
        if index < len(files)-1:
            sys.stdout.write('\n\n')

    exit(int(not exit_code))

########NEW FILE########
__FILENAME__ = finder
import os
import sys


def find_steps_modules(dirname):
    sys.path.insert(0, dirname)
    modules = [__import__(filename[:-3]) for filename in os.listdir(dirname)
                                           if filename.endswith('steps.py')]
    del sys.path[0]
    return modules

def find_text_specs(dirname):
    return [open('%s/%s' % (dirname,filename)).read() for filename in os.listdir(dirname)
                                                        if filename.endswith('.story')]


def _find_hook_steps(name, dirname):
    sys.path.insert(0, dirname)
    modules = [__import__(filename[:-3]) for filename in os.listdir(dirname)
                                           if filename.endswith('.py')]
    del sys.path[0]
    before_all_meths = []
    for module in modules:
        steps = getattr(module, name, [])
        before_all_meths.extend([step[1] for step in steps])
    return before_all_meths


def find_before_all(dirname):
    return _find_hook_steps('_before_alls', dirname)


def find_after_all(dirname):
    return _find_hook_steps('_after_alls', dirname)


def find_before_each(dirname):
    return _find_hook_steps('_before_eachs', dirname)

def find_after_each(dirname):
    return _find_hook_steps('_after_eachs', dirname)

########NEW FILE########
__FILENAME__ = hooks
from pyhistorian import Step

class BeforeAll(Step):
    name = 'before_all'

class AfterAll(Step):
    name = 'after_all'

class BeforeEach(Step):
    name = 'before_each'

class AfterEach(Step):
    name = 'after_each'

########NEW FILE########
__FILENAME__ = runner
from pyhistorian import Story, Scenario
from pyhistorian.language import TEMPLATE_PATTERN
from story_parser import parse_text
import re


class StoryRunner(object):
    def __init__(self, story_text, output, colored,
                 modules=(), language='en-us',
                 before_all=(), before_each=(),
                 after_all=(), after_each=()):
        self._story_text = story_text
        self._output = output
        self._modules = modules
        self._colored = colored
        self._language = language
        self._parsed_story = parse_text(story_text, self._language)
        self._pycukes_story = self._get_pycukes_story()
        self._all_givens = {}
        self._all_whens = {}
        self._all_thens = {}
        self._collect_steps()
        self._before_all = before_all
        self._before_each = before_each
        self._after_all = after_all
        self._after_each = after_each

    def _collect_steps(self):
        for module in self._modules:
            for step_name in ['given', 'when', 'then']:
                steps = getattr(module, '_%ss' % step_name, [])
                for method, message, args in steps:
                    all_this_step = getattr(self, '_all_%ss' % step_name)
                    all_this_step[message] = (method, args)

    def _get_header(self):
        story = self._parsed_story.get_stories()[0]
        return story.header

    def _call_before_each_methods(self, namespace):
        for before_meth in self._before_each:
            before_meth(namespace)

    def _call_before_all_methods(self, namespace):
        for before_meth in self._before_all:
            before_meth(namespace)

    def _call_after_all_methods(self, namespace):
        for after_meth in self._after_all:
            after_meth(namespace)

    def _call_after_each_methods(self, namespace):
        for after_meth in self._after_each:
            after_meth(namespace)

    def _get_pycukes_story(self):
        return type('PyCukesStory',
                    (Story,),
                    {'__doc__' :'\n'.join(self._get_header().split('\n')[1:]),
                     'output': self._output,
                     'title': self._parsed_story.get_stories()[0].title,
                     'colored': self._colored,
                     'scenarios': [],
                     'template_color':'yellow',
                     'language': self._language,
                     'before_each': self._call_before_each_methods,
                     'before_all': self._call_before_all_methods,
                     'after_all': self._call_after_all_methods,
                     'after_each': self._call_after_each_methods,})

    def run(self):
        scenarios = self._parsed_story.get_stories()[0].scenarios
        for scenario_title, steps in scenarios:
            new_scenario = type('PyCukesScenario',
                                (Scenario,),
                                {'__doc__': scenario_title,
                                '_givens': [],
                                '_whens': [],
                                '_thens': [],
                                })

            for step_name in ['given', 'when', 'then']:
                for step_message in steps[step_name]:
                    scenario_steps = getattr(new_scenario, '_%ss' % step_name)
                    all_runner_steps = getattr(self, '_all_%ss' % step_name)
                    actual_scenario = (None, step_message, ())
                    for step_regex, (step_method, step_args) in all_runner_steps.items():
                        msg_pattern = re.sub(TEMPLATE_PATTERN, r'(.*)', step_regex)
                        msg_pattern = re.escape(msg_pattern)
                        msg_pattern = msg_pattern.replace(re.escape(r'(.*)'), r'(.*)')

                        if re.match(msg_pattern, step_message):
                            actual_scenario = (step_method,
                                               step_message,
                                               re.match(msg_pattern,
                                                        step_message).groups())
                    scenario_steps.append(actual_scenario)
 
            self._pycukes_story.scenarios.append(new_scenario)
        return self._pycukes_story.run()

########NEW FILE########
__FILENAME__ = bowling_game_ptbr_steps
# coding: utf-8
from pycukes import *

class BowlingGame(object):
    score = 1
    def hit(self, pins):
        pass

@DadoQue('eu estou jogando boliche')
def start_game(contexto):
    contexto._bowling_game = BowlingGame()

@Quando('eu não acerto nenhum pino')
def hit_no_pins(contexto):
    contexto._bowling_game.hit(0)

@Entao('eu tenho 0 pontos')
def i_have_zero_points(contexto):
    assert contexto._bowling_game.score == 0 

########NEW FILE########
__FILENAME__ = run_examples
from cStringIO import StringIO
from should_dsl import should_be
import subprocess
import os
import sys


bowling_game_output = open('bowling_game_output').read()
bowling_game_pending_output = open('bowling_game_pending_output').read()
bowling_game_without_colors_output = open('bowling_game_without_colors_output').read()
bowling_game_using_feature_injection_output = open('bowling_game_using_feature_injection_output').read()
calculator_output = open('calculator_output').read()
bowling_game_ptbr_output = open('bowling_game_ptbr_output').read()
bowling_and_calculator_output = '\n'.join([bowling_game_output,
                                             calculator_output])
all_outputs = '\n'.join([bowling_game_output,
                           bowling_game_using_feature_injection_output,
                           calculator_output,])
hooks_output = open('hooks_output').read()

INPUTS_AND_OUTPUTS = [('pycukes stories/bowling_game.story',
                            bowling_game_output, 1),
                      ('pycukes stories/bowling_game.story stories/calculator.story',
                            bowling_and_calculator_output, 1),
                      ('pycukes',
                            all_outputs, 1),
                      ('pycukes --stories-dir=features',
                            '\n', 0),
                      ('pycukes --stories-dir=stories_dir1',
                            bowling_game_output.replace('stories', 'stories_dir1'), 1),
                      ('pycukes --stories-dir=stories_dir1 --steps-dir=stories',
                            bowling_game_pending_output, 0),
                      ('pycukes stories/bowling_game.story --no-colors',
                            bowling_game_without_colors_output, 1),
                      ('pycukes stories/bowling_game.story --colored',
                            bowling_game_output, 1),
                      ('pycukes stories/bowling_game.story --colored --no-colors',
                            bowling_game_output, 1),
                      ('pycukes stories/bowling_game_using_feature_injection.story',
                            bowling_game_using_feature_injection_output, 1),
                      ('pycukes ptbr_stories/bowling_game_ptbr.story --language pt-br',
                            bowling_game_ptbr_output, 1),
                      ('cd stories && pycukes bowling_game.story',
                            bowling_game_output.replace('stories', '.'), 1),
                      ('pycukes stories_with_hooks/messages.story -n',
                            hooks_output, 0)
                      ]

def remove_all_pycs(dirname):
    for filename in os.listdir(dirname):
        filename = os.path.join(dirname, filename)
        if filename.endswith('.pyc'):
            os.remove(filename)
        elif os.path.isdir(filename):
            remove_all_pycs(filename)

def run_examples():
    exceptions = []
    failures = 0
    for input_command, expected_output, exit_code in INPUTS_AND_OUTPUTS:
        print '\t', input_command,
        remove_all_pycs(os.path.abspath(os.path.dirname(__file__)))
        try:
            process = subprocess.Popen(input_command,
                                   stdout=subprocess.PIPE,
                                   shell=True)
            out = process.communicate()[0]+'\n'
            out |should_be.equal_to| expected_output
            process.wait() |should_be.equal_to| exit_code
            print '- OK'
        except AssertionError, e:
            print '- FAIL'
            print e
            failures += 1
    return failures


if __name__ == '__main__':
    print '-'*80
    print 'Running console examples'
    sys.exit(run_examples())

########NEW FILE########
__FILENAME__ = bowling_game_steps
from pycukes import *

class BowlingGame(object):
    score = 1
    def hit(self, pins):
        pass


@Given('I am playing a bowling game')
def start_game(context):
    context._bowling_game = BowlingGame()

@When('I hit no pins')
def hit_no_pins(context):
    context._bowling_game.hit(0)

@Then('I have 0 points')
def i_have_zero_points(context):
    assert context._bowling_game.score == 0 

########NEW FILE########
__FILENAME__ = bowling_game_steps
from pycukes import *

class BowlingGame(object):
    score = 1
    def hit(self, pins):
        pass


@Given('I am playing a bowling game')
def start_game(context):
    context._bowling_game = BowlingGame()

@When('I hit no pins')
def hit_no_pins(context):
    context._bowling_game.hit(0)

@Then('I have 0 points')
def i_have_zero_points(context):
    assert context._bowling_game.score == 0 

########NEW FILE########
__FILENAME__ = message_steps
from pycukes import *
from should_dsl import *


@Then('I should have $message attr')
def check_attr(context, message):
    getattr(context, message) |should_be.equal_to| 'msg'

########NEW FILE########
__FILENAME__ = env
from pycukes import BeforeAll, AfterAll, BeforeEach, AfterEach


@BeforeAll
def add_message1_attr(context):
    context.counter = 1


@BeforeEach
def add_message_attr(context):
    context.counter += 1
    setattr(context, 'message%d' % context.counter, 'msg')

@AfterEach
def increment_one(context):
    context.counter += 1

@AfterAll
def show_hello_world(context):
    print 'hello world'

########NEW FILE########
__FILENAME__ = finding_hooks
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             modules=find_steps_modules(DIR),
    ...             before_all=find_before_all(DIR2),
    ...             after_all=find_after_all(DIR2),
    ...             before_each=find_before_each(DIR2),
    ...             after_each=find_after_each(DIR2),
    ...             colored=False).run()
    HELLO WORLD
    True
'''

      
from pycukes import (StoryRunner,
                     find_steps_modules,
                     find_before_all,
                     find_after_all,
                     find_before_each,
                     find_after_each)
from cStringIO import StringIO
import os
import doctest

checker = doctest.OutputChecker()

story_text = """Story: Bowling Game
                As a bowling player
                I want to have a bowling software
                So that I and my friends can play online

                Scenario 1: Gutter Game
                  Then I have 2 points
                  And I have not printed HELLO WORLD
                
                Scenario 2: Gutter Game (again)
                  Then I have 4 points
                  And I have not printed HELLO WORLD
                """
output = StringIO()

DIR = os.path.dirname(__file__)+'/steps'
DIR2 = os.path.dirname(__file__)+'/hooks'

########NEW FILE########
__FILENAME__ = finding_steps_in_directory
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             modules=find_steps_modules(DIR),
    ...             colored=False).run()
    False
    >>> print output.getvalue()
    Story: Bowling Game
      As a bowling player
      I want to have a bowling software
      So that I and my friends can play online
    <BLANKLINE>
      Scenario 1: Gutter Game
        Given I am playing a bowling game   ... OK
        When I hit no pins   ... OK
        Then I have 0 points   ... FAIL
    <BLANKLINE>
      Failures:
        File ".../bowling_game_steps.py", line ..., in ...
          assert context._bowling_game.score == 0
        AssertionError
    <BLANKLINE>
    <BLANKLINE>
      Ran 1 scenario with 1 failure, 0 errors and 0 pending steps
    <BLANKLINE>
'''

      
from pycukes import StoryRunner, find_steps_modules
from cStringIO import StringIO
import os

story_text = """Story: Bowling Game
                As a bowling player
                I want to have a bowling software
                So that I and my friends can play online

                Scenario 1: Gutter Game
                  Given I am playing a bowling game
                  When I hit no pins
                  Then I have 0 points"""
output = StringIO()

DIR = os.path.dirname(__file__)+'/steps'

########NEW FILE########
__FILENAME__ = finding_text_specs_and_steps_modules
'''
    >>> pycukes_console(stories_dir=SPECS_DIR,
    ...                 steps_dir=STEPS_DIR,
    ...                 output=output)

    >>> print output.getvalue()
    Story: Bowling Game
      As a bowling player
      I want to play bowling online
      So that I can play with everyone in the world
    <BLANKLINE>
      Scenario 1: Gutter Game
        Given I am playing a bowling game   ... OK
        When I hit no pins   ... OK
        Then I have 0 points   ... FAIL
    <BLANKLINE>
      Failures:
        File ".../bowling_game_steps.py", line ..., in ...
          assert context._bowling_game.score == 0
        AssertionError
    <BLANKLINE>
    <BLANKLINE>
      Ran 1 scenario with 1 failure, 0 errors and 0 pending steps
    <BLANKLINE>
'''

from cStringIO import StringIO
from pycukes import pycukes_console
import os

SPECS_DIR = os.path.dirname(__file__)+'/text_specs'
STEPS_DIR = os.path.dirname(__file__)+'/steps'
output = StringIO()

########NEW FILE########
__FILENAME__ = finding_text_specs_in_a_dir
'''
    >>> find_text_specs(SPECS_DIR) == ["""Story: Bowling Game
    ... As a bowling player
    ... I want to play bowling online
    ... So that I can play with everyone in the world
    ...
    ...   Scenario 1: Gutter Game
    ...     Given I am playing a bowling game
    ...     When I hit no pins
    ...     Then I have 0 points
    ... """]
    True
'''

from pycukes import find_text_specs
import os

SPECS_DIR = os.path.dirname(__file__)+'/text_specs'

########NEW FILE########
__FILENAME__ = hook1
from pycukes import *
from should_dsl import *


class BowlingGame(object):
    score = 1
    def hit(self, pins):
        pass


@BeforeAll
def start_game(context):
    context._bowling_game = BowlingGame()
    context._bowling_game.score = 0
    context._printed_hello_world = False


@BeforeEach
def score_2(context):
    context._bowling_game.score += 2


@AfterAll
def print_hello_world(context):
    print 'HELLO WORLD'
    context._printed_hello_world = True

########NEW FILE########
__FILENAME__ = module_with_no_step_definition
'''
    >>> import sys
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             modules=[sys],
    ...             colored=False).run()
    True
    >>> print output.getvalue()
    Story: Bowling Game
      As a bowling player
      I want to have a bowling software
      So that I and my friends can play online
    <BLANKLINE>
      Scenario 1: Gutter Game
        Given I am playing a bowling game   ... PENDING
        When I hit no pins   ... PENDING
        Then I have 0 points   ... PENDING
    <BLANKLINE>
      Ran 1 scenario with 0 failures, 0 errors and 3 pending steps
    <BLANKLINE>
'''

      
from pycukes import StoryRunner, find_steps_modules
from cStringIO import StringIO
import os

story_text = """Story: Bowling Game
                As a bowling player
                I want to have a bowling software
                So that I and my friends can play online

                Scenario 1: Gutter Game
                  Given I am playing a bowling game
                  When I hit no pins
                  Then I have 0 points"""
output = StringIO()

########NEW FILE########
__FILENAME__ = no_scenario_story
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             colored=False,).run()
    True
    >>> print output.getvalue()
    Story: Calculator
      As a math student
      I want to use a calculator
      So that my calculations can be easy to do
    <BLANKLINE>
      Ran 0 scenarios with 0 failures, 0 errors and 0 pending steps
    <BLANKLINE>
'''

from pycukes import StoryRunner
from cStringIO import StringIO

story_text = """Story: Calculator
                As a math student
                I want to use a calculator
                So that my calculations can be easy to do"""

output = StringIO()

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = running_after_snippets
'''
    >>> sys.stderr = StringIO()
    >>> StoryRunner(text,
    ...             output,
    ...             colored=False,
    ...             before_all=[show_foo],
    ...             after_all=[show_bar]).run()
    True
    >>> sys.stderr.getvalue()
    'FOO\\nBAR\\n'


    >>> sys.stderr = StringIO()
    >>> StoryRunner(text,
    ...             output,
    ...             colored=False,
    ...             before_each=[show_foo],
    ...             after_each=[show_bar],
    ...             after_all=[show_foobar]).run()
    True
    >>> sys.stderr.getvalue()
    'FOO\\nBAR\\nFOO\\nBAR\\nFOOBAR\\n'
'''
from StringIO import StringIO
from pycukes.runner import StoryRunner
import sys


text = """
Story: Using after_all
  As a dev
  I want to execute some function after all scenarios
  So that I can manage my stories better

  Scenario 1: Nothing
    Then I should see "FOO" then I should see "BAR"
 
  Scenario 2: Repetition
    Then I should not see "BAR" after "FOO"
"""

output = StringIO()


def show_foo(context):
    print >>sys.stderr, "FOO"

def show_bar(context):
    print >>sys.stderr, "BAR"

def show_foobar(context):
    print >>sys.stderr, "FOOBAR"

########NEW FILE########
__FILENAME__ = running_before_snippets
'''
    >>> sys.stderr = StringIO()
    >>> StoryRunner(text,
    ...             output,
    ...             colored=False,
    ...             before_all=[show_foo, show_foobar]).run()
    True
    >>> sys.stderr.getvalue()
    'FOO\\nFOOBAR\\n'
    >>> sys.stderr = StringIO()
    >>> StoryRunner(text,
    ...             output,
    ...             colored=False,
    ...             before_each=[show_foo, show_foobar]).run()
    True
    >>> sys.stderr.getvalue()
    'FOO\\nFOOBAR\\nFOO\\nFOOBAR\\n'
'''
from StringIO import StringIO
from pycukes.runner import StoryRunner
import sys


text = """
Story: Using before_all
  As a dev
  I want to execute some function before all scenarios
  So that I can manage my stories better

  Scenario 1: Nothing
    Then I should see "FOO" and "BAR" on my stderr
 
  Scenario 2: Repetition
    Then I should not see "FOO" and "BAR" again
"""

output = StringIO()


def show_foo(context):
    context.last_call = "FOO"
    print >>sys.stderr, "FOO"

def show_foobar(context):
    print >>sys.stderr, context.last_call + "BAR"

########NEW FILE########
__FILENAME__ = run_specs
import doctest
import unittest
import os
import sys


if __name__ == '__main__':
    THIS_DIR = os.path.dirname(__file__) or '.'
    suite = unittest.TestSuite()
    for file in os.listdir(THIS_DIR):
        if file.endswith('.py') and file not in ['__init__.py', 'run_specs.py']:
            suite.addTest(doctest.DocTestSuite(__import__(file[:-3]),
                                               optionflags=doctest.ELLIPSIS))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    sys.exit(int(bool(result.errors or result.failures)))

########NEW FILE########
__FILENAME__ = single_ok_scenario
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             colored=False,
    ...             modules=[sum_of_one_and_two_with_three_oks]).run()
    True
    >>> print output.getvalue()
    Story: Calculator
      As a math student
      I want to use a calculator
      So that my calculations can be easy to do
    <BLANKLINE>
      Scenario 1: Sum of 1 and 2
        Given I have a calculator   ... OK
        When I enter with 1 + 2 and press =   ... OK
        Then I see 3 in my LCD   ... OK
    <BLANKLINE>
      Ran 1 scenario with 0 failures, 0 errors and 0 pending steps
    <BLANKLINE>
'''

from pycukes import StoryRunner
from pycukes.specs.steps import sum_of_one_and_two_with_three_oks
from cStringIO import StringIO


output = StringIO()
story_text = """Story: Calculator
                As a math student
                I want to use a calculator
                So that my calculations can be easy to do
                
                Scenario: Sum of 1 and 2
                  Given I have a calculator
                  When I enter with 1 + 2 and press =
                  Then I see 3 in my LCD"""

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = single_pending_scenario
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             colored=False,
    ...             modules=[]).run()
    True
    >>> print output.getvalue()
    Story: Calculator
      As a math student
      I want to use a calculator
      So that my calculations can be easy to do
    <BLANKLINE>
      Scenario 1: Sum of 1 and 2
        Given I have a calculator   ... PENDING
        When I enter with 1 + 2 and press =   ... PENDING
        Then I see 3 in my LCD   ... PENDING
    <BLANKLINE>
      Ran 1 scenario with 0 failures, 0 errors and 3 pending steps
    <BLANKLINE>
'''

from pycukes import StoryRunner
from cStringIO import StringIO


output = StringIO()
story_text = """Story: Calculator
                As a math student
                I want to use a calculator
                So that my calculations can be easy to do
                
                Scenario 1: Sum of 1 and 2
                  Given I have a calculator
                  When I enter with 1 + 2 and press =
                  Then I see 3 in my LCD"""

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = single_scenario_with_one_ok_one_failure_and_one_error
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             colored=False,
    ...             modules=[sum_of_one_and_two_with_one_ok_one_fail_and_one_error]).run()
    False
    >>> print output.getvalue()
    Story: Calculator
      As a math student
      I want to use a calculator
      So that my calculations can be easy to do
    <BLANKLINE>
      Scenario 1: Sum of 1 and 2
        Given I have a calculator   ... OK
        When I enter with 1 + 2 and press =   ... FAIL
        Then I see 3 in my LCD   ... ERROR
    <BLANKLINE>
      Failures:
        File ".../sum_of_one_and_two_with_one_ok_one_fail_and_one_error.py", line ..., in i_enter_with_one_and_two
          assert False
        AssertionError
    <BLANKLINE>
    <BLANKLINE>
      Errors:
        File ".../sum_of_one_and_two_with_one_ok_one_fail_and_one_error.py", line ..., in i_see_three_in_my_lcd
          raise Exception()
        Exception
    <BLANKLINE>
    <BLANKLINE>
      Ran 1 scenario with 1 failure, 1 error and 0 pending steps
    <BLANKLINE>
'''

from pycukes import StoryRunner
from pycukes.specs.steps import sum_of_one_and_two_with_one_ok_one_fail_and_one_error
from cStringIO import StringIO


output = StringIO()
story_text = """Story: Calculator
                As a math student
                I want to use a calculator
                So that my calculations can be easy to do
                
                Scenario 1: Sum of 1 and 2
                  Given I have a calculator
                  When I enter with 1 + 2 and press =
                  Then I see 3 in my LCD"""

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = single_scenario_with_two_oks_and_one_failure
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             colored=False,
    ...             modules=[sum_of_one_and_two_with_one_fail_and_two_oks]).run()
    False
    >>> print output.getvalue()
    Story: Calculator
      As a math student
      I want to use a calculator
      So that my calculations can be easy to do
    <BLANKLINE>
      Scenario 1: Sum of 1 and 2
        Given I have a calculator   ... OK
        When I enter with 1 + 2 and press =   ... OK
        Then I see 3 in my LCD   ... FAIL
    <BLANKLINE>
      Failures:
        File ".../sum_of_one_and_two_with_one_fail_and_two_oks.py", line ..., in ...
          assert False
        AssertionError
    <BLANKLINE>
    <BLANKLINE>
      Ran 1 scenario with 1 failure, 0 errors and 0 pending steps
    <BLANKLINE>
'''

from pycukes import StoryRunner
from pycukes.specs.steps import sum_of_one_and_two_with_one_fail_and_two_oks
from cStringIO import StringIO


output = StringIO()
story_text = """Story: Calculator
                As a math student
                I want to use a calculator
                So that my calculations can be easy to do
                
                Scenario 1: Sum of 1 and 2
                  Given I have a calculator
                  When I enter with 1 + 2 and press =
                  Then I see 3 in my LCD"""

if __name__ == '__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = bowling_game_steps
from pycukes import *

class BowlingGame(object):
    score = 1
    def hit(self, pins):
        pass


@Given('I am playing a bowling game')
def start_game(context):
    context._bowling_game = BowlingGame()

@When('I hit no pins')
def hit_no_pins(context):
    context._bowling_game.hit(0)

@Then('I have 0 points')
def i_have_zero_points(context):
    assert context._bowling_game.score == 0

@Then('I have not printed HELLO WORLD')
def not_printed_hello_world(context):
    assert context._printed_hello_world == False

@Then('I have $value points')
def i_have_zero_points(context, value):
    assert context._bowling_game.score == int(value), context._bowling_game.score



########NEW FILE########
__FILENAME__ = calculator_with_regexes
from pycukes import *

@When('I sum $left and $right')
def sum_two_numbers(context, left, right):
    context._sum = int(left) + int(right)
#Then I have 2 as result


########NEW FILE########
__FILENAME__ = sum_of_one_and_two_negative_with_two_oks_and_one_fail
from pycukes import *

@Given('I have a calculator')
def i_have_a_calc(context):
    pass

@When('I enter with 1 + -2 and press =')
def one_plus_minus_two(context):
    pass

@Then('I see -1 in my LCD')
def fail(context):
    assert None

########NEW FILE########
__FILENAME__ = sum_of_one_and_two_with_one_fail_and_two_oks
from pycukes import *

@Given('I have a calculator')
def i_have_a_calculator(context):
    pass

@When('I enter with 1 + 2 and press =')
def i_enter_with_one_and_two(context):
    pass

@Then('I see 3 in my LCD')
def i_see_three_in_my_lcd(context):
    assert False

########NEW FILE########
__FILENAME__ = sum_of_one_and_two_with_one_ok_one_fail_and_one_error
from pycukes import *

@Given('I have a calculator')
def i_have_a_calculator(context):
    pass

@When('I enter with 1 + 2 and press =')
def i_enter_with_one_and_two(context):
    assert False

@Then('I see 3 in my LCD')
def i_see_three_in_my_lcd(context):
    raise Exception()

########NEW FILE########
__FILENAME__ = sum_of_one_and_two_with_three_oks
from pycukes import *

@Given('I have a calculator')
def i_have_a_calculator(context):
    pass

@When('I enter with 1 + 2 and press =')
def i_enter_with_one_and_two(context):
    pass

@Then('I see 3 in my LCD')
def i_see_three_in_my_lcd(context):
    pass

########NEW FILE########
__FILENAME__ = two_scenarios_each_one_with_two_oks_and_a_fail
'''
    >>> StoryRunner(story_text,
    ...             output=output,
    ...             colored=False,
    ...             modules=[sum_of_one_and_two_with_one_fail_and_two_oks,
    ...                      sum_of_one_and_two_negative_with_two_oks_and_one_fail]).run()
    False
    >>> print output.getvalue()
    Story: Calculator
      As a math student
      I want to use a calculator
      So that my calculations can be easy to do
    <BLANKLINE>
      Scenario 1: Sum of 1 and 2
        Given I have a calculator   ... OK
        When I enter with 1 + 2 and press =   ... OK
        Then I see 3 in my LCD   ... FAIL
    <BLANKLINE>
      Failures:
        File ".../sum_of_one_and_two_with_one_fail_and_two_oks.py", line ..., in ...
          assert False
        AssertionError
    <BLANKLINE>
    <BLANKLINE>
      Scenario 2: Sum of 1 and -2
        Given I have a calculator   ... OK
        When I enter with 1 + -2 and press =   ... OK
        Then I see -1 in my LCD   ... FAIL
    <BLANKLINE>
      Failures:
        File ".../sum_of_one_and_two_negative_with_two_oks_and_one_fail.py", line ..., in ...
          assert None
        AssertionError
    <BLANKLINE>
    <BLANKLINE>
      Ran 2 scenarios with 2 failures, 0 errors and 0 pending steps
    <BLANKLINE>
 '''
from pycukes import StoryRunner
from pycukes.specs.steps import sum_of_one_and_two_with_one_fail_and_two_oks,\
                                    sum_of_one_and_two_negative_with_two_oks_and_one_fail
from cStringIO import StringIO
story_text = """Story: Calculator
                As a math student
                I want to use a calculator
                So that my calculations can be easy to do
                
                Scenario 1: Sum of 1 and 2
                  Given I have a calculator
                  When I enter with 1 + 2 and press =
                  Then I see 3 in my LCD

                Scenario 2: Sum of 1 and -2
                   Given I have a calculator
                   When I enter with 1 + -2 and press =
                   Then I see -1 in my LCD"""
output = StringIO()

########NEW FILE########
__FILENAME__ = unit_spec_for_find_steps_method
'''
    >>> steps_modules = find_steps_modules(STEPS_DIR)
    >>> len(steps_modules)
    1
    >>> steps_modules == [bowling_game_steps]
    True
'''
from pycukes import find_steps_modules
from pycukes.specs.steps import bowling_game_steps
import os
import sys


STEPS_DIR = os.path.dirname(__file__)+'/steps'

########NEW FILE########
__FILENAME__ = using_regexes_in_steps_definitions
'''
    >>> StoryRunner(story_text,
    ...             colored=False,
    ...             output=output,
    ...             modules=[calculator_with_regexes]).run()
    True
    >>> print output.getvalue()
    Story: Using Regexes in Step Definitions
      In order to use regexes in step definitions
      As a smart regex jedi
      I want to write step definitions using regexes
    <BLANKLINE>
      Scenario 1: Sum of 1 and 1
        When I sum 1 and 1   ... OK
        Then I have 2 as result   ... PENDING
    <BLANKLINE>
      Scenario 2: Sum of 22 and 33
        When I sum 22 and 33   ... OK
        Then I have 55 as result   ... PENDING
    <BLANKLINE>
      Ran 2 scenarios with 0 failures, 0 errors and 2 pending steps
    <BLANKLINE>
    '''

from pycukes import *
from pycukes.specs.steps import calculator_with_regexes
from cStringIO import StringIO

output = StringIO()

story_text = """Story: Using Regexes in Step Definitions
In order to use regexes in step definitions
As a smart regex jedi
I want to write step definitions using regexes

Scenario 1: Sum of 1 and 1
When I sum 1 and 1
Then I have 2 as result

Scenario 2: Sum of 22 and 33
When I sum 22 and 33
Then I have 55 as result"""

########NEW FILE########
