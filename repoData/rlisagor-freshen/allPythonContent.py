__FILENAME__ = steps
from freshen import *
from friends import find_user

@Transform(r'^user (\w+)$')
def transform_user(username):
    return find_user(username)

@When(r'^(user \w+) befriends (user \w+)$')
def befriend(user, friend):
    user.befriend(friend)

@Then(r'^(user \w+) should be friends with (user \w+)$')
def check_friends(user, friend):
    assert user.is_friends_with(friend)


########NEW FILE########
__FILENAME__ = friends
class User(object):
    
    def __init__(self, name):
        self.name = name
        self.friends = []
    
    def befriend(self, other):
        if other.name not in self.friends:
            self.friends.append(other.name)
        if not other.is_friends_with(self):
            other.befriend(self)
    
    def is_friends_with(self, other):
        return other.name in self.friends


users = {
    'paxton': User('paxton'),
    'adelaide': User('adelaide'),
    'hazel': User('hazel'),
    'duane': User('duane')
}

def find_user(name):
    return users.get(name)


########NEW FILE########
__FILENAME__ = steps
from freshen import *
from friends import find_user

def combinations(iterable, r):
    # combinations('ABCD', 2) --> AB AC AD BC BD CD
    # combinations(range(4), 3) --> 012 013 023 123
    pool = tuple(iterable)
    n = len(pool)
    if r > n:
        return
    indices = range(r)
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i+1, r):
            indices[j] = indices[j-1] + 1
        yield tuple(pool[i] for i in indices)


@Transform(r'^user (\w+)$')
def transform_user(username):
    return find_user(username)

@NamedTransform( '{user list}', r'([\w, ]+)' )
def transform_user_list( user_list ):
    return [ find_user( name.strip() ) for name in user_list.split( ',' ) ]

@When(r'^(user \w+) befriends (user \w+)$')
def befriend(user, friend):
    user.befriend(friend)

@Then(r'^(user \w+) should be friends with (user \w+)$')
def check_friends(user, friend):
    assert user.is_friends_with(friend)

@Then(r'these users should be friends: {user list}' )
def check_all_friends( user_list ):
    for user1, user2 in combinations( user_list, 2 ):
        assert user1.is_friends_with( user2 )
    


########NEW FILE########
__FILENAME__ = friends
class User(object):
    
    def __init__(self, name):
        self.name = name
        self.friends = []
    
    def befriend(self, other):
        if other.name not in self.friends:
            self.friends.append(other.name)
        if not other.is_friends_with(self):
            other.befriend(self)
    
    def is_friends_with(self, other):
        return other.name in self.friends


users = {
    'paxton': User('paxton'),
    'adelaide': User('adelaide'),
    'hazel': User('hazel'),
    'duane': User('duane')
}

def find_user(name):
    return users.get(name)


########NEW FILE########
__FILENAME__ = calculator
class Calculator(object):
    
    def __init__(self):
        self.args = []
    
    def push(self, value):
        self.args.append(value)
    
    def add(self):
        return sum(self.args)
    
    def divide(self):
        return float(self.args[0]) / float(self.args[1])


########NEW FILE########
__FILENAME__ = steps
from freshen import *
from freshen.checks import *

import calculator

@Before
def before(sc):
    scc.calc = calculator.Calculator()
    scc.result = None

@Given("I have entered (\d+) into the calculator")
def enter(num):
    scc.calc.push(int(num))

@When("I press (\w+)")
def press(button):
    op = getattr(scc.calc, button)
    scc.result = op()

@Then("the result should be (.*) on the screen")
def check_result(value):
    assert_equal(str(scc.result), value)


########NEW FILE########
__FILENAME__ = calculator
class Calculator(object):
    
    def __init__(self):
        self.args = []
    
    def push(self, value):
        self.args.append(value)
    
    def add(self):
        return sum(self.args)
    
    def divide(self):
        return float(self.args[0]) / float(self.args[1])


########NEW FILE########
__FILENAME__ = steps
#-*- coding: utf8 -*-
from freshen import *
from freshen.checks import *

import calculator

@Before
def before(sc):
    scc.calc = calculator.Calculator()
    scc.result = None

@Given("le nombre (\d+) entré dans la calculatrice")
def enter(num):
    scc.calc.push(int(num))

@When("j'appuie sur (\w+)")
def press(button):
    op = getattr(scc.calc, button)
    scc.result = op()

@Then("le résultat doit être (.*) à l'écran")
def check_result(value):
    assert_equal(str(scc.result), value)


########NEW FILE########
__FILENAME__ = counter
"""
Counter that is shared between two different python modules.
Used to test independence.
Not intended to be used as a real example.
"""

counter = 0

def increment_counter():
    global counter
    counter = counter + 1

def reset_counter():
    global counter
    counter = 0
    
def get_counter():
    global counter
    return counter

########NEW FILE########
__FILENAME__ = independent_one_steps
"""
Independant steps for one.
"""

from freshen import *
from freshen.checks import *

from examples.counter_independence import counter

@Before
def before(sc):
    counter.increment_counter()

@After
def after(sc):
    counter.reset_counter()

@Then("the counter prints (\d+).")
def check_counter(number):
    assert_equal(counter.get_counter(), int(number))

########NEW FILE########
__FILENAME__ = independent_two_steps
"""
Same as independent_one_steps.py.
"""

from freshen import *
from freshen.checks import *

from examples.counter_independence import counter

@Before
def before(sc):
    counter.increment_counter()

@After
def after(sc):
    counter.reset_counter()

@Then("the counter prints (\d+).")
def check_counter(number):
    assert_equal(counter.get_counter(), int(number))

########NEW FILE########
__FILENAME__ = document

class Document(object):
    def __init__(self, num_pages):
        self._num_pages = num_pages
        self._page = 0
        
    def set_page(self, page):
        if page <= self._num_pages:
            self._page = page
            
    def get_page(self):
        return self._page
    
    def get_num_pages(self):
        return self._num_pages
        
    def next_page(self):
        if self._page < self._num_pages:
            self._page = self._page + 1
 
    def rip_off_page(self):
        if self._page == self._num_pages:
            self._page = self._page - 1
        self._num_pages = self._num_pages - 1
########NEW FILE########
__FILENAME__ = page_steps
from freshen import *
from freshen.checks import assert_equals
from examples.docu.document import Document

@Given('a document of (\d+) pages?')
def create_doc(num_pages):
    scc.doc = Document(int(num_pages))
    
@Given('the page is (\d+)')
def set_page_doc(page):
    scc.doc.set_page(int(page))
    
@When('I click for the next page')
def click_next_page():
    scc.doc.next_page()

@When('I rip off the current page')
def rip_off_page():
    scc.doc.rip_off_page()
    
@Then('the page is (\d+)')
def check_page(expected_page):
    assert_equals(int(expected_page), scc.doc.get_page())

@Then('the document has (\d+) pages?')
def check_num_pages(expected_num_pages):
    assert_equals(int(expected_num_pages), scc.doc.get_num_pages())
########NEW FILE########
__FILENAME__ = defs
from freshen import *

@Given("a step also in the nested directory")
def step():
    pass

@Given("^passing without a table$")
def pass_without_table():
    pass

########NEW FILE########
__FILENAME__ = steps
from examples.self_test.features.nested.steps import *


########NEW FILE########
__FILENAME__ = defs
from freshen import *

@Given("a step also in the nested directory")
def step():
    pass


########NEW FILE########
__FILENAME__ = steps
from freshen import *
from nose.tools import *

def flunker():
    raise Exception("FAIL")


@Given("^passing$")
def passing(table):
    pass

@Given("^failing$")
def failing(string):
    flunker()

@Given("^passing without a table$")
def pass_without_table():
    pass

@Given("^failing without a table$")
def fail_without_table():
    flunker()

@Given("^a step definition that calls an undefined step$")
def call_undef():
    run_steps("Given this does not exist")

@Given("^call step \"(.*)\"$")
def call_step(step):
    run_steps("Given step")

@Given("^'(.+)' cukes$")
def do_cukes(c):
    if glc.cukes:
        raise Exception("We already have %s cukes!" % glc.cukes)
    glc.cukes = c

@Then("^I should have '(.+)' cukes$")
def should_have_cukes(c):
    assert_equals(c, glc.cukes)

@Given("^'(.+)' global cukes$")
def global_cukes(c):
    if scc.scenario_runs >= 1:
        flunker()
    
    glc.cukes = c
    scc.scenario_runs += 1

@Then("^I should have '(.+)' global cukes$")
def check_global_cukes(c):
    assert_equals(c, glc.cukes)

@Given("^table$")
def with_table(table):
    scc.t = table

@Given("^multiline string$")
def with_m_string(string):
    scc.multiline = string

@Then("^the table should be$")
def check_table(table):
    assert_equals(scc.t, table)

@Then("^the multiline string should be$")
def check_m_string(string):
    assert_equals(scc.multiline)

@Given("^failing expectation$")
def failing_expectations():
    assert_equals('this', 'that')

@Given("^unused$")
def unused():
    pass

@Given("^another unused$")
def another_unused():
    pass


########NEW FILE########
__FILENAME__ = steps
"""
Steps to simulate asynchronous events and function calls.
"""

from freshen import When, Then, scc
from twisted.internet import reactor
from twisted.internet.defer import Deferred

@When("^I implement a step that returns a twisted Deferred object$")
def simulate_async_event():
    """Simulate an asynchronous event."""
    scc.state = 'executing'
    def async_event(result):
        """All other asynchronous events or function calls
        returned from later steps will wait until this
        callback fires."""
        scc.state = result
        return 'some event result'
    deferred = Deferred()
    reactor.callLater(1, deferred.callback, 'done') # pylint: disable=E1101
    deferred.addCallback(async_event)
    return deferred

@Then("^freshen will wait for the result before executing the next step$")
def check_async_execution():
    """Simulate an asynchronous function call."""
    def async_function(result_from_prior_event):
        """This function will only be called after
        all events returned from previous steps have
        been executed."""
        assert scc.state == 'done', \
               'Freshen did not wait for async ' \
               'test to be finished before executing ' \
               'the next step.'
        assert result_from_prior_event == 'some event result', \
               'The result from a prior event was not correctly' \
               'passed into the asynchronous function call.'
    return async_function


########NEW FILE########
__FILENAME__ = checks
#-*- coding: utf8 -*-

from nose.tools import *
import re as _re
import difflib as _difflib

__unittest = 1

def assert_looks_like(first, second, msg=None):
    """ Compare two strings if all contiguous whitespace is coalesced. """
    first = _re.sub("\s+", " ", first.strip())
    second = _re.sub("\s+", " ", second.strip())
    if first != second:
        raise AssertionError(msg or "%r does not look like %r" % (first, second))

_assert_equal = assert_equal
def assert_equal(first, second, msg=None):
    doit = all(isinstance(s, basestring) for s in [first, second]) and \
           any("\n" in s for s in [first, second])
    
    if not doit:
        return _assert_equal(first, second, msg)
        
    if first != second:
        diff = _difflib.unified_diff(first.split("\n"), second.split("\n"),
                                     "expected", "actual", lineterm="")
        diff = "    " + "\n    ".join(diff)
        raise AssertionError(msg or "Strings not equal\n" + diff)

assert_equals = assert_equal


########NEW FILE########
__FILENAME__ = commands
import sys
import os

from freshen.compat import relpath
from freshen.core import TagMatcher, load_language, load_feature
from freshen.stepregistry import StepImplLoader, StepImplRegistry, UndefinedStepImpl

LANGUAGE = 'en'

class Colors(object):
    HEADER = '\033[95m'
    FILE = '\033[93m'
    ENDC = '\033[0m'

    @classmethod
    def disable(cls):
        cls.HEADER = ''
        cls.FILE = ''
        cls.ENDC = ''

    @classmethod
    def write(cls, text, color):
        return "%s%s%s" % (color, text, cls.ENDC)



def load_file(filepath):
    feature = load_feature(filepath, load_language(LANGUAGE))
    registry = StepImplRegistry(TagMatcher)
    loader = StepImplLoader()
    loader.load_steps_impl(registry, os.path.dirname(feature.src_file), feature.use_step_defs)
    return registry

def load_dir(dirpath):
    registry = StepImplRegistry(TagMatcher)
    loader = StepImplLoader()
    def walktree(top, filter_func=lambda x: True):
        names = os.listdir(top)
        for name in names:
            path = os.path.join(top, name)
            if filter_func(path):
                yield path
            if os.path.isdir(path):
                for i in walktree(path, filter_func):
                    yield i
    for feature_file in walktree(dirpath, lambda x: x.endswith('.feature')):
        feature = load_feature(feature_file, load_language(LANGUAGE))
        loader.load_steps_impl(registry, os.path.dirname(feature.src_file), feature.use_step_defs)
    return registry

def print_registry(registry):
    steps = {}
    for keyword in ['given', 'when', 'then']:
        steps[keyword] = {}
        for step in registry.steps[keyword]:
            path = os.path.relpath(step.get_location())
            filename = path.rsplit(':', 1)[0]
            if filename not in steps[keyword]:
                steps[keyword][filename] = []
            if step not in steps[keyword][filename]:
                steps[keyword][filename].append(step)
    for keyword in ['given', 'when', 'then']:
        print Colors.write(keyword.upper(), Colors.HEADER)
        for filename in steps[keyword]:
            print "  %s" % Colors.write(filename, Colors.FILE)
            for step in steps[keyword][filename]:
                print "    %s" % step.spec


def list_steps():
    if len(sys.argv) < 2 or sys.argv[1] in ["--help", "-h"]:
        print >> sys.stderr, "Prints list of step definitions that are available to the feature files."
        print >> sys.stderr, "Usage: %s [file or directory]" % sys.argv[0]
        exit(1)

    file_or_dir = sys.argv[1]
    
    if not os.path.exists(file_or_dir):
        print >> sys.stderr, "No such file or directory: %s" % file_or_dir
        exit(1)
    
    if os.path.isdir(file_or_dir):
        registry = load_dir(file_or_dir)
    else:
        registry = load_file(file_or_dir)
    print_registry(registry)


########NEW FILE########
__FILENAME__ = compat
#-*- coding: utf8 -*-

from os.path import abspath, commonprefix, sep, pardir, join
import os
curdir = os.getcwd()

def relpath(path, start=curdir):
    """Return a relative version of a path"""

    if not path:
        raise ValueError("no path specified")

    start_list = abspath(start).split(sep)
    path_list = abspath(path).split(sep)

    # Work out how much of the filepath is shared by start and path.
    i = len(commonprefix([start_list, path_list]))

    rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return curdir
    return join(*rel_list)

    
if __name__ == "__main__":
    print relpath("/tmp/dir1/file", "/tmp")
    print relpath("/tmp/dir1/file", "/usr")

########NEW FILE########
__FILENAME__ = context
#-*- coding: utf8 -*-

__all__ = ['glc', 'ftc', 'scc']

# Contexts
class Context(object):
    """
    A javascript/lua like dictionary whose items can be accessed as attributes
    """
    
    def __init__(self):
        self.__dict__['d'] = {}
    
    def __getattr__(self, name):
        if name in self.d:
            return self.d[name]
        else:
            return None
    __getitem__ = __getattr__
    
    def __setattr__(self, name, value):
        self.d[name] = value
    __setitem__ = __setattr__
    
    def __delattr__(self, name):
        if name in self.d:
            del self.d[name]
    __delitem__ = __delattr__

    def clear(self):
        self.__dict__['d'] = {}


glc = Context() # Global context - never cleared
ftc = Context() # Feature context - cleared for every feature
scc = Context() # Scenario context - cleared for every scenario


########NEW FILE########
__FILENAME__ = core
#-*- coding: utf8 -*-

# This line ensures that frames from this file will not be shown in tracebacks
__unittest = 1

import inspect
import os
import yaml

from freshen.context import *
from freshen.parser import parse_steps, parse_file


class StepsRunner(object):
    
    def __init__(self, step_registry):
        self.step_registry = step_registry
    
    def run_steps_from_string(self, spec, language_name='en'):
        """ Called from within step definitions to run other steps. """
        
        caller = inspect.currentframe().f_back
        line = caller.f_lineno - 1
        fname = caller.f_code.co_filename
        
        steps = parse_steps(spec, fname, line, load_language(language_name))
        for s in steps:
            self.run_step(s)
    
    def run_step(self, step):
        step_impl, args = self.step_registry.find_step_impl(step)
        if step.arg is not None:
            return step_impl.run(step.arg, *args)
        else:
            return step_impl.run(*args)


class TagMatcher(object):
    
    def __init__(self, tags):
        self.include_tags = set(t.lstrip("@") for t in tags if not t.startswith("~"))
        self.exclude_tags = set(t.lstrip("~@") for t in tags if t.startswith("~"))

    def check_match(self, tagset):
        tagset = set(t.lstrip("@") for t in tagset)
        if tagset & self.exclude_tags:
            return False
        
        return not self.include_tags or (tagset & self.include_tags)


class Language(object):
    def __init__(self, mappings, default_mappings=None):
        self.mappings = mappings
        self.default_mappings = default_mappings
    
    def words(self, key):
        """
        Give all the synonymns of a word in the requested language 
        (or the default language if no word is available).
        """
        if self.default_mappings is not None and key not in self.mappings:
            return self.default_mappings[key].encode('utf').split("|")
        else:
            return self.mappings[key].encode('utf').split("|")


def load_feature(fname, language):
    """ Load and parse a feature file. """

    fname = os.path.abspath(fname)
    feat = parse_file(fname, language)
    return feat

def load_language(language_name, default_language_name="en"):
    directory, _f = os.path.split(os.path.abspath(__file__))
    language_path = os.path.join(directory, 'languages.yml')
    languages = yaml.load(open(language_path))
    if language_name not in languages:
        return None
    return Language(languages[language_name], languages[default_language_name])

def run_steps(spec, language="en"):
    """ Can be called by the user from within a step definition to execute other steps. """

    # The way this works is a little exotic, but I couldn't think of a better way to work around
    # the fact that this has to be a global function and therefore cannot know about which step
    # runner to use (other than making step runner global)
    
    # Find the step runner that is currently running and use it to run the given steps
    fr = inspect.currentframe()
    while fr:
        if "self" in fr.f_locals:
            f_self = fr.f_locals['self']
            if isinstance(f_self, StepsRunner):
                return f_self.run_steps_from_string(spec, language)
        fr = fr.f_back




########NEW FILE########
__FILENAME__ = cuke
#-*- coding: utf8 -*-

# Experimental - a non-nose runner for tests, may end up being compatible
# with Cucumber commandline

import os
from freshen.context import *
from freshen.core import TagMatcher, StepsRunner, load_feature, load_language
from freshen.stepregistry import StepImplLoader, StepImplRegistry, UndefinedStepImpl, AmbiguousStepImpl

class FreshenHandler(object):
    
    def before_feature(self, feature):
        pass
    
    def after_feature(self, feature):
        pass
    
    def before_scenario(self, scenario):
        pass
    
    def after_scenario(self, scenario):
        pass

    def before_step(self, step):
        pass
    
    def step_failed(self, step, e):
        pass
    
    def step_ambiguous(self, step, e):
        pass
        
    def step_undefined(self, step, e):
        pass
    
    def step_exception(self, step, e):
        pass
    
    def after_step(self, step):
        pass


class FreshenHandlerProxy(object):
    """ Acts as a handler and proxies callback events to a list of actual handlers. """
        
    def __init__(self, handlers):
        self._handlers = handlers
    
    def __getattr__(self, attr):
        def proxy(*args, **kwargs):
            for h in self._handlers:
                method = getattr(h, attr)
                method(*args, **kwargs)
        return proxy


def run_scenario(step_registry, scenario, handler):
    handler.before_scenario(scenario)
    
    runner = StepsRunner(step_registry)
    scc.clear()
    
    # Run @Before hooks
    for hook_impl in step_registry.get_hooks('before', scenario.get_tags()):
        hook_impl.run(scenario)
    
    # Run all the steps
    for step in scenario.iter_steps():
        handler.before_step(step)
        
        called = False
        try:
            runner.run_step(step)
        except AssertionError, e:
            handler.step_failed(step, e)
            called = True
        except UndefinedStepImpl, e:
            handler.step_undefined(step, e)
            called = True
        except AmbiguousStepImpl, e:
            handler.step_ambiguous(step, e)
            called = True
        except Exception, e:
            handler.step_exception(step, e)
            called = True
        
        if not called:
            handler.after_step(step)
    
    # Run @After hooks
    for hook_impl in step_registry.get_hooks('after', scenario.get_tags()):
        hook_impl.run(scenario)    
    handler.after_scenario(scenario)

def run_feature(step_registry, feature, handler):
    handler.before_feature(feature)
    ftc.clear()
    for scenario in feature.iter_scenarios():
        run_scenario(step_registry, scenario, handler)
    handler.after_feature(feature)

def run_features(step_registry, features, handler):
    for feature in features:
        run_feature(step_registry, feature, handler)

def load_step_definitions(paths):
    loader = StepImplLoader()
    sr = StepImplRegistry(TagMatcher)
    for path in paths:
        loader.load_steps_impl(sr, path)
    return sr

def load_features(paths, language):
    result = []
    for path in paths:
        for (dirpath, dirnames, filenames) in os.walk(path):
            for feature_file in filenames:
                if feature_file.endswith(".feature"):
                    feature_file = os.path.join(dirpath, feature_file)
                    result.append(load_feature(feature_file, language))
    return result

if __name__ == "__main__":
    import sys
    import logging
    from freshen.handlers import ConsoleHandler
    
    logging.basicConfig(level=logging.DEBUG)
    
    paths = sys.argv[1:] or ["features"]
    
    language = load_language('en')
    registry = load_step_definitions(paths)
    features = load_features(paths, language)
    handler = FreshenHandlerProxy([ConsoleHandler()])
    run_features(registry, features, handler)


########NEW FILE########
__FILENAME__ = handlers
#-*- coding: utf8 -*-

from freshen.cuke import FreshenHandler
from freshen.prettyprint import FreshenPrettyPrint

class ConsoleHandler(FreshenHandler):
    
    def before_feature(self, feature):
        print FreshenPrettyPrint.feature(feature)
        print
    
    def before_scenario(self, scenario):
        print FreshenPrettyPrint.scenario(scenario)
    
    def after_scenario(self, scenario):
        print
    
    def step_failed(self, step, e):
        print FreshenPrettyPrint.step_failed(step)
    
    def step_ambiguous(self, step, e):
        print FreshenPrettyPrint.step_ambiguous(step)
        
    def step_undefined(self, step, e):
        print FreshenPrettyPrint.step_undefined(step)
    
    def step_exception(self, step, e):
        print FreshenPrettyPrint.step_exception(step)
    
    def after_step(self, step):
        print FreshenPrettyPrint.step_passed(step)



########NEW FILE########
__FILENAME__ = noseplugin
#-*- coding: utf8 -*-

import sys
import os
import logging
import re
from new import instancemethod

from pyparsing import ParseException

from nose.plugins import Plugin
from nose.plugins.errorclass import ErrorClass, ErrorClassPlugin
from nose.selector import TestAddress
from nose.failure import Failure
from nose.util import isclass

from freshen.core import TagMatcher, load_language, load_feature, StepsRunner
from freshen.prettyprint import FreshenPrettyPrint
from freshen.stepregistry import StepImplLoader, StepImplRegistry
from freshen.stepregistry import UndefinedStepImpl, StepImplLoadException
from freshen.test.base import FeatureSuite, FreshenTestCase, ExceptionWrapper

try:
    # use colorama for cross-platform colored text, if available
    import colorama # pylint: disable=F0401
    colorama.init()
except ImportError:
    colorama = None

log = logging.getLogger('nose.plugins.freshen')

# This line ensures that frames from this file will not be shown in tracebacks
__unittest = 1


class FreshenErrorPlugin(ErrorClassPlugin):

    enabled = True
    undefined = ErrorClass(UndefinedStepImpl,
                           label="UNDEFINED",
                           isfailure=False)

    def options(self, parser, env):
        # Forced to be on!
        pass


class StepsLoadFailure(Failure):

    def __str__(self):
        return "Could not load steps for %s" % self.address()

class ParseFailure(Failure):

    def __init__(self, parse_exception, tb, filename):
        self.parse_exception = parse_exception
        self.filename = filename
        address = TestAddress(filename).totuple()
        super(ParseFailure, self).__init__(parse_exception.__class__, parse_exception, tb, address)

    def __str__(self):
        return "Could not parse %s" % (self.filename)

class FreshenNosePlugin(Plugin):

    name = "freshen"

    # This makes it so that freshen's formatFailure gets called before capture
    # and logcapture - those plugins replace and obscure the true exception value
    score = 1000

    def options(self, parser, env):
        super(FreshenNosePlugin, self).options(parser, env)

        parser.add_option('--tags', action='store',
                          dest='tags',
                          default=env.get('NOSE_FRESHEN_TAGS'),
                          help="Run only those scenarios and features which "
                               "match the given tags. Should be a comma-separated "
                               "list. Each tag can be prefixed with a ~ to negate "
                               "[NOSE_FRESHEN_TAGS]")
        parser.add_option('--language',
                          action="store",
                          dest='language',
                          default='en',
                          help='Change the language used when reading the feature files')
        parser.add_option('--list-undefined',
                          action="store_true",
                          default=env.get('NOSE_FRESHEN_LIST_UNDEFINED') == '1',
                          dest="list_undefined",
                          help="Make a report of all undefined steps that "
                               "freshen encounters when running scenarios. "
                               "[NOSE_FRESHEN_LIST_UNDEFINED]")

    def configure(self, options, config):
        super(FreshenNosePlugin, self).configure(options, config)
        all_tags = options.tags.split(",") if options.tags else []
        self.tagmatcher = TagMatcher(all_tags)
        self.language = load_language(options.language)
        self.impl_loader = StepImplLoader()
        if not self.language:
            print >> sys.stderr, "Error: language '%s' not available" % options.language
            exit(1)
        if options.list_undefined:
            self.undefined_steps = []
        else:
            self.undefined_steps = None
        self._test_class = None

    def wantDirectory(self, dirname):
        if not os.path.exists(os.path.join(dirname, ".freshenignore")):
            return True
        return None

    def wantFile(self, filename):
        return filename.endswith(".feature") or None

    def _makeTestClass(self, feature, scenario):
        """Chooses the test base class appropriate
        for the given feature.
        
        This method supports late import of the
        test base class so that userspace code (e.g.
        in the support environment) can configure
        the test framework first (e.g. in the case
        of twisted tests to install a custom
        reactor implementation).
        
        The current simplistic implementation chooses
        a twisted-enabled test class if twisted is
        present and returns a PyUnit-based test otherwise.
        
        In the future this can be extended to support
        more flexible (e.g. user-defined) test classes
        on a per-feature basis."""
        if self._test_class is None:
            try:
                from freshen.test.async import TwistedTestCase
                self._test_class = TwistedTestCase
            except ImportError:
                from freshen.test.pyunit import PyunitTestCase
                self._test_class = PyunitTestCase
        return type(feature.name, (self._test_class, ), {scenario.name: lambda self: self.runScenario()})

    def loadTestsFromFile(self, filename, indexes=[]):
        log.debug("Loading from file %s" % filename)

        step_registry = StepImplRegistry(TagMatcher)
        try:
            feat = load_feature(filename, self.language)
            path = os.path.dirname(filename)
        except ParseException, e:
            _, _, tb = sys.exc_info()
            yield ParseFailure(e, tb, filename)
            return

        try:
            self.impl_loader.load_steps_impl(step_registry, path, feat.use_step_defs)
        except StepImplLoadException, e:
            yield StepsLoadFailure(address=TestAddress(filename), *e.exc)
            return

        cnt = 0
        ctx = FeatureSuite()
        for i, sc in enumerate(feat.iter_scenarios()):
            if (not indexes or (i + 1) in indexes):
                if self.tagmatcher.check_match(sc.tags + feat.tags):
                    test_class = self._makeTestClass(feat, sc)
                    yield test_class(StepsRunner(step_registry), step_registry, feat, sc, ctx)
                    cnt += 1

        if not cnt:
            yield False

    def loadTestsFromName(self, name, _=None):
        log.debug("Loading from name %s" % name)

        if not self._is_file_with_indexes(name):
            return # let nose take care of it

        name_without_indexes, indexes = self._split_file_in_indexes(name)
        if not os.path.exists(name_without_indexes):
            return

        if os.path.isfile(name_without_indexes) \
           and name_without_indexes.endswith(".feature"):
            for tc in self.loadTestsFromFile(name_without_indexes, indexes):
                yield tc

    def _is_file_with_indexes(self, name):
        drive, tail = os.path.splitdrive(name)
        if ":" not in tail:
            return False
        else:
            return True

    def _split_file_in_indexes(self, name_with_indexes):
        drive, tail = os.path.splitdrive(name_with_indexes)
        parts = tail.split(":")
        name_without_indexes = drive + parts.pop(0)
        indexes = []
        indexes = set(int(p) for p in parts)
        return (name_without_indexes, indexes)

    def describeTest(self, test):
        if isinstance(test.test, FreshenTestCase):
            return test.test.description

    def formatFailure(self, test, err):
        if hasattr(test, 'test') and isinstance(test.test, FreshenTestCase):
            ec, ev, tb = err
            if ec is ExceptionWrapper and isinstance(ev, Exception):
                orig_ec, orig_ev, orig_tb = ev.e
                message = "%s\n\n%s" % (str(orig_ev), self._formatSteps(test, ev.step))
                return (orig_ec, message, orig_tb)
            elif not ec is UndefinedStepImpl and hasattr(test.test, 'last_step'):
                message = "%s\n\n%s" % (str(ev), self._formatSteps(test, test.test.last_step))
                return (ec, message, tb)

    formatError = formatFailure

    def prepareTestResult(self, result):
        # Patch the result handler with an addError method that saves
        # UndefinedStepImpl exceptions for reporting later.
        if self.undefined_steps is not None:
            plugin = self
            def _addError(self, test, err):
                ec, ev, tb = err
                if isclass(ec) and issubclass(ec, UndefinedStepImpl):
                    plugin.undefined_steps.append((test, ec, ev, tb))
                self._old_addError(test, err)
            result._old_addError = result.addError
            result.addError = instancemethod(_addError, result, result.__class__)

    def report(self, stream):
        if self.undefined_steps:
            stream.write("======================================================================\n")
            stream.write("Tests with undefined steps\n")
            stream.write("----------------------------------------------------------------------\n")
            for test, ec, ev, tb in self.undefined_steps:
                stream.write(self._formatSteps(test, ev.step, False) + "\n\n")
            stream.write("You can implement step definitions for the missing steps with these snippets:\n\n")
            uniq_steps = set(s[2].step for s in self.undefined_steps)
            for step in uniq_steps:
                stream.write('@%s(r"^%s$")\n' % (self.language.words(step.step_type)[0],
                                                 step.match))
                stream.write('def %s_%s():\n' % (step.step_type,
                                                 re.sub('[^\w]', '_', step.match).lower()))
                stream.write('    # code here\n\n')

    def _formatSteps(self, test, failed_step, failure=True):
        ret = []
        ret.append(FreshenPrettyPrint.feature(test.test.feature))
        ret.append(FreshenPrettyPrint.scenario(test.test.scenario))
        found = False
        for step in test.test.scenario.iter_steps():
            if step == failed_step:
                found = True
                if failure:
                    ret.append(FreshenPrettyPrint.step_failed(step))
                else:
                    ret.append(FreshenPrettyPrint.step_undefined(step))
            elif found:
                ret.append(FreshenPrettyPrint.step_notrun(step))
            else:
                ret.append(FreshenPrettyPrint.step_passed(step))
        return "\n".join(ret)


########NEW FILE########
__FILENAME__ = parser
#-*- coding: utf8 -*-

# This line ensures that frames from this file will not be shown in tracebacks
__unittest = 1

from pyparsing import *
import copy
import logging
import os
import re
import textwrap

try:
    from os.path import relpath
except Exception, e:
    from freshen.compat import relpath

log = logging.getLogger('freshen')

class Feature(object):

    def __init__(self, use_step_defs, tags, name, description, background, scenarios):
        self.use_step_defs = use_step_defs
        self.tags = tags
        self.name = name
        self.description = description
        self.scenarios = scenarios
        self.background = None

        if background != []:
            self.background = background[0]

        for sc in scenarios:
            sc.feature = self
            sc.background = self.background

    def __repr__(self):
        return '<Feature "%s": %d scenario(s)>' % (self.name, len(self.scenarios))

    def has_background(self):
        return self.background is not None

    def iter_scenarios(self):
        for sco in self.scenarios:
            for sc in sco.iterate():
                yield sc


class Background(object):

    def __init__(self, name, steps):
        self.name = name
        self.steps = steps

    def __repr__(self):
        return '<Background "%s">' % self.name

    def iter_steps(self):
        for step in self.steps:
            yield step

class Scenario(object):

    def __init__(self, tags, name, steps):
        self.tags = tags
        self.name = name
        self.steps = steps
        self.background = None

    def __repr__(self):
        return '<Scenario "%s">' % self.name

    def get_tags(self):
        return self.tags + self.feature.tags

    def iterate(self):
        yield self

    def iter_steps(self):
        if self.background is not None:
            for step in self.background.iter_steps():
                yield step

        for step in self.steps:
            yield step


class ScenarioOutline(Scenario):

    def __init__(self, tags, name, steps, examples):
        self.examples = examples
        super(ScenarioOutline, self).__init__(tags, name, steps)

    def __repr__(self):
        return '<ScenarioOutline "%s">' % self.name

    def iterate(self):
        for ex in self.examples:
            for values in ex.table.iterrows():
                new_steps = []
                for step in self.steps:
                    new_steps.append(step.set_values(values))
                sc = Scenario(self.tags, self.name, new_steps)
                sc.feature = self.feature
                sc.background = self.background
                yield sc


class Step(object):

    def __init__(self, step_type, match, arg=None):
        self.step_type_native, self.step_type = step_type
        self.match = match
        self.arg = arg

    def __repr__(self):
        return '<%s "%s">' % (self.step_type, self.match)

    def source_location(self, absolute=True):
        p = relpath(self.src_file, os.getcwd()) if absolute else self.src_file
        return '%s:%d' % (p, self.src_line)

    def set_values(self, value_dict):
        result = copy.deepcopy(self)
        for name, value in value_dict.iteritems():
            result.match = result.match.replace("<%s>" % name, value)
        return result


class Examples(object):

    def __init__(self, name, table):
        self.name = name
        self.table = table


class Table(object):

    def __init__(self, headings, rows):
        assert [len(r) == len(headings) for r in rows], "Malformed table"

        self.headings = headings
        self.rows = rows

    def __repr__(self):
        return "<Table: %dx%d>" % (len(self.headings), len(self.rows))

    def iterrows(self):
        for row in self.rows:
            yield dict(zip(self.headings, row))


def grammar(fname, l, convert=True, base_line=0):
    # l = language

    def create_object(klass):
        def untokenize(s, loc, toks):
            result = []
            for t in toks:
                if isinstance(t, ParseResults):
                    t = t.asList()
                result.append(t)
            obj = klass(*result)
            obj.src_file = fname
            obj.src_line = base_line + lineno(loc, s)
            return obj
        return untokenize

    def process_descr(s):
        return [p.strip() for p in s[0].strip().split("\n")]

    # This has to be an array for compatibility with Python versions which do not have "nonlocal"
    last_step_type = [None]

    def process_given_step(s):
        last_step_type[0] = 'given'
        return (s[0], 'given')

    def process_when_step(s):
        last_step_type[0] = 'when'
        return (s[0], 'when')

    def process_then_step(s):
        last_step_type[0] = 'then'
        return (s[0], 'then')

    def process_and_but_step(orig, loc, s):
        if last_step_type[0] == None:
            raise ParseFatalException(orig, loc,
                        "'And' or 'But' steps can only come after 'Given', 'When', or 'Then'")
        return (s[0], last_step_type[0])

    def process_string(s):
        return s[0].strip()

    def process_m_string(s):
        return textwrap.dedent(s[0])

    def process_tag(s):
        return s[0].strip("@")

    def or_words(words, kind, suffix='', parse_acts=None):
        elements = []
        for index, native_word in enumerate(words):
            for word in l.words(native_word):
                element = kind(word + suffix)
                if parse_acts is not None:
                    element.setParseAction(parse_acts[index])
                elements.append(element)
        return Or(elements)

    empty_not_n    = empty.copy().setWhitespaceChars(" \t")
    tags           = OneOrMore(Word("@", alphanums + "_").setParseAction(process_tag))

    step_file      = quotedString.setParseAction( removeQuotes )
    list_of_step_files = step_file + ZeroOrMore(Suppress(',') + step_file)
    use_step_defs  = or_words(['use_step_defs'], Suppress, ':') + list_of_step_files

    following_text = empty_not_n + restOfLine + Suppress(lineEnd)
    section_header = lambda name: Suppress(name + ":") + following_text

    section_name   = or_words(['scenario', 'scenario_outline', 'background'], Literal)
    descr_block    = Group(SkipTo(section_name | tags).setParseAction(process_descr))

    table_row      = Group(Suppress("|") +
                           delimitedList(
                                         CharsNotIn("|\n").setParseAction(process_string) +
                                         Suppress(empty_not_n), delim="|") +
                           Suppress("|"))
    table          = table_row + Group(OneOrMore(table_row))

    m_string       = (Suppress(Literal('"""') + lineEnd).setWhitespaceChars(" \t") +
                      SkipTo((lineEnd +
                              Literal('"""')).setWhitespaceChars(" \t")).setWhitespaceChars("") +
                      Suppress('"""'))
    m_string.setParseAction(process_m_string)

    step_name      = or_words(['given', 'when', 'then', 'and', 'but'], Keyword,
                              parse_acts=[process_given_step, process_when_step, process_then_step,
                                          process_and_but_step, process_and_but_step])
    step           = step_name + following_text + Optional(table | m_string)
    steps          = Group(ZeroOrMore(step))

    example        = or_words(['examples'], section_header) + table

    background     = or_words(['background'], section_header) + steps

    scenario       = Group(Optional(tags)) + or_words(['scenario'], section_header) + steps
    scenario_outline = Group(Optional(tags)) + or_words(['scenario_outline'], section_header) + steps + Group(OneOrMore(example))

    feature        = (Group(Optional(use_step_defs)) +
                      Group(Optional(tags)) +
                      or_words(['feature'], section_header) +
                      descr_block +
                      Group(Optional(background)) +
                      Group(OneOrMore(scenario | scenario_outline)))

    # Ignore tags for now as they are not supported
    feature.ignore(pythonStyleComment)
    steps.ignore(pythonStyleComment)

    if convert:
        table.setParseAction(create_object(Table))
        step.setParseAction(create_object(Step))
        background.setParseAction(create_object(Background))
        scenario.setParseAction(create_object(Scenario))
        scenario_outline.setParseAction(create_object(ScenarioOutline))
        example.setParseAction(create_object(Examples))
        feature.setParseAction(create_object(Feature))

    return feature, steps

def parse_file(fname, language, convert=True):
    feature, _ = grammar(fname, language, convert)
    try:
        file_obj = open(fname)
        if convert:
            feat = feature.parseFile(file_obj)[0]
        else:
            feat = feature.parseFile(file_obj)
    finally:
        file_obj.close()
    return feat

def parse_steps(spec, fname, base_line, language, convert=True):
    _, steps = grammar(fname, language, convert, base_line)
    if convert:
        return steps.parseString(spec)[0]
    else:
        return steps.parseString(spec)


########NEW FILE########
__FILENAME__ = prettyprint
#-*- coding: utf8 -*-

try:
    import curses
    curses.setupterm()
    COLOR_SUPPORT = (curses.tigetnum('colors') > 0)
except Exception:
    COLOR_SUPPORT = False


COLORS = {
    'bold': '1',
    'grey': '2',
    'underline': '4',
    'normal': '0',
    'red': '31',
    'green': '32',
    'yellow': '33',
    'blue': '34',
    'magenta': '35',
    'cyan': '36',
    'white': '37'
}

UNDEFINED = 'yellow'
AMBIGUOUS = 'cyan'
FAILED = 'red'
ERROR = 'red,bold'
PASSED = 'green'
TAG = 'cyan'
COMMENT = 'grey'
NOTRUN = 'normal'

def colored(text, colorspec):
    if not COLOR_SUPPORT:
        return text
    colors = [c.strip() for c in colorspec.split(',')]
    result = ""
    for c in colors:
        result += "\033[%sm" % COLORS[c]
    result += text + "\033[0m"
    return result

class FreshenPrettyPrint(object):
    @classmethod
    def feature(cls, feature):
        ret = []
        if feature.tags:
            ret.append(colored(" ".join(("@" + t) for t in feature.tags), TAG))
        ret.append("Feature: " + feature.name)
        if feature.description != ['']:
            ret.extend('    ' + l for l in feature.description)
        return "\n".join(ret)
    
    @classmethod
    def scenario(cls, scenario):
        ret = []
        if scenario.tags:
            ret.append("    " + colored(" ".join(('@' + t) for t in scenario.tags), TAG))
        ret.append("    Scenario: "+scenario.name)
        return "\n".join(ret)
    
    @classmethod
    def _step(cls, step, color):
        return "        " + colored('%-40s' % (step.step_type + " " + step.match), color) \
                            + " " +\
                            colored("# " + step.source_location(), COMMENT)
    
    @classmethod
    def step_failed(cls, step):
        return cls._step(step, FAILED)
    
    @classmethod
    def step_ambiguous(cls, step):
        return cls._step(step, AMBIGUOUS)
    
    @classmethod
    def step_undefined(cls, step):
        return cls._step(step, UNDEFINED)
    
    @classmethod
    def step_exception(cls, step):
        return cls._step(step, ERROR)
    
    @classmethod
    def step_passed(cls, step):
        return cls._step(step, PASSED)
    
    @classmethod
    def step_notrun(cls, step):
        return cls._step(step, NOTRUN)

########NEW FILE########
__FILENAME__ = stepregistry
#-*- coding: utf-8 -*-
import imp
import logging
import re
import os
import sys
import traceback
from itertools import chain

__all__ = ['Given', 'When', 'Then', 'Before', 'After', 'AfterStep', 'Transform', 'NamedTransform']
__unittest = 1

log = logging.getLogger('freshen')

class AmbiguousStepImpl(Exception):

    def __init__(self, step, impl1, impl2):
        self.step = step
        self.impl1 = impl1
        self.impl2 = impl2
        super(AmbiguousStepImpl, self).__init__('Ambiguous: "%s"\n %s\n %s' % (step.match,
                                                                              impl1.get_location(),
                                                                              impl2.get_location()))

class UndefinedStepImpl(Exception):

    def __init__(self, step):
        self.step = step
        super(UndefinedStepImpl, self).__init__('"%s" # %s' % (step.match, step.source_location()))

class StepImpl(object):

    def __init__(self, step_type, spec, func):
        self.step_type = step_type
        self.spec = spec
        self.func = func
        self.named_transforms = []

    def apply_named_transform(self, name, pattern, transform):
        if name in self.spec:
            self.spec = self.spec.replace(name, pattern)
            self.named_transforms.append(transform)
            if hasattr(self, 're_spec'):
                del self.re_spec

    def run(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def match(self, match):
        if not hasattr(self, 're_spec'):
            self.re_spec = re.compile(self.spec)
        return self.re_spec.match(match)

    def get_location(self):
        code = self.func.func_code
        return "%s:%d" % (code.co_filename, code.co_firstlineno)

class HookImpl(object):

    def __init__(self, cb_type, func, tags=[]):
        self.cb_type = cb_type
        self.tags = tags
        self.func = func
        self.tags = tags
        self.order = 0

    def __repr__(self):
        return "<Hook: @%s %s(...)>" % (self.cb_type, self.func.func_name)

    def run(self, scenario):
        return self.func(scenario)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

class TransformImpl(object):

    def __init__(self, spec_fragment, func):
        self.spec_fragment = spec_fragment
        self.re_spec = re.compile(spec_fragment)
        self.func = func

    def is_match(self, arg):
        if arg is None:
            return False
        return self.re_spec.match(arg) != None

    def transform_arg(self, arg):
        match = self.re_spec.match(arg)
        if match:
            return self.func(*match.groups())

    def __call__(self, *args, **kwargs):
        self.func(*args, **kwargs)

class NamedTransformImpl(TransformImpl):

    def __init__(self, name, in_pattern, out_pattern, func):
        super(NamedTransformImpl, self).__init__(out_pattern, func)
        self.name = name
        self.in_pattern = in_pattern
        self.out_pattern = out_pattern

    def apply_to_step(self, step):
        step.apply_named_transform(self.name, self.in_pattern, self)


class StepImplLoadException(Exception):
    def __init__(self, exc):
        self.exc = exc


class StepImplLoader(object):

    def __init__(self):
        self.modules = {}
        self.module_counter = 0

    def load_steps_impl(self, registry, path, module_names=None):
        """
        Load the step implementations at the given path, with the given module names. If
        module_names is None then the module 'steps' is searched by default.
        """

        if not module_names:
            module_names = ['steps']

        path = os.path.abspath(path)

        for module_name in module_names:
            mod = self.modules.get((path, module_name))

            if mod is None:
                #log.debug("Looking for step def module '%s' in %s" % (module_name, path))
                cwd = os.getcwd()
                if cwd not in sys.path:
                    sys.path.append(cwd)

                try:
                    actual_module_name = os.path.basename(module_name)
                    complete_path = os.path.join(path, os.path.dirname(module_name))
                    info = imp.find_module(actual_module_name, [complete_path])
                except ImportError:
                    #log.debug("Did not find step defs module '%s' in %s" % (module_name, path))
                    return
                
                try:
                    # Modules have to be loaded with unique names or else problems arise
                    mod = imp.load_module("stepdefs_" + str(self.module_counter), *info)
                except:
                    exc = sys.exc_info()
                    raise StepImplLoadException(exc)

                self.module_counter += 1
                self.modules[(path, module_name)] = mod

            for item_name in dir(mod):
                item = getattr(mod, item_name)
                if isinstance(item, StepImpl):
                    registry.add_step(item.step_type, item)
                elif isinstance(item, HookImpl):
                    registry.add_hook(item.cb_type, item)
                elif isinstance(item, NamedTransformImpl):
                    registry.add_named_transform(item)
                elif isinstance(item, TransformImpl):
                    registry.add_transform(item)

class StepImplRegistry(object):

    def __init__(self, tag_matcher_class):
        self.steps = {
            'given': [],
            'when': [],
            'then': []
        }

        self.hooks = {
            'before': [],
            'after': [],
            'after_step': []
        }

        self.transforms = []
        self.named_transforms = []
        self.tag_matcher_class = tag_matcher_class

    def add_step(self, step_type, step):
        self.steps[step_type].append(step)
        for named_transform in self.named_transforms:
            named_transform.apply_to_step(step)

    def add_hook(self, hook_type, hook):
        self.hooks[hook_type].append(hook)

    def add_transform(self, transform):
        self.transforms.append(transform)

    def add_named_transform(self, named_transform):
        self.named_transforms.append(named_transform)
        for step in chain(*self.steps.values()):
            named_transform.apply_to_step(step)

    def _apply_transforms(self, arg, step):
        for transform in chain(step.named_transforms, self.transforms):
            if transform.is_match(arg):
                return transform.transform_arg(arg)
        return arg

    def find_step_impl(self, step):
        """
        Find the implementation of the step for the given match string. Returns the StepImpl object
        corresponding to the implementation, and the arguments to the step implementation. If no
        implementation is found, raises UndefinedStepImpl. If more than one implementation is
        found, raises AmbiguousStepImpl.
        
        Each of the arguments returned will have been transformed by the first matching transform
        implementation.
        """
        result = None
        for si in self.steps[step.step_type]:
            matches = si.match(step.match)
            if matches:
                if result:
                    raise AmbiguousStepImpl(step, result[0], si)

                args = [self._apply_transforms(arg, si) for arg in matches.groups()]
                result = si, args

        if not result:
            raise UndefinedStepImpl(step)
        return result

    def get_hooks(self, cb_type, tags=[]):
        hooks = [h for h in self.hooks[cb_type] if self.tag_matcher_class(h.tags).check_match(tags)]
        hooks.sort(cmp=lambda x, y: cmp(x.order, y.order))
        return hooks


def step_decorator(step_type):
    def decorator_wrapper(spec):
        """ Decorator to wrap step definitions in. Registers definition. """
        def wrapper(func):
            return StepImpl(step_type, spec, func)
        return wrapper
    return decorator_wrapper

def hook_decorator(cb_type):
    """ Decorator to wrap hook definitions in. Registers hook. """
    def decorator_wrapper(*tags_or_func):
        if len(tags_or_func) == 1 and callable(tags_or_func[0]):
            # No tags were passed to this decorator
            func = tags_or_func[0]
            return HookImpl(cb_type, func)
        else:
            # We got some tags, so we need to produce the real decorator
            tags = tags_or_func
            def d(func):
                return HookImpl(cb_type, func, tags)
            return d
    return decorator_wrapper

def transform_decorator(spec_fragment):
    def wrapper(func):
        return TransformImpl(spec_fragment, func)
    return wrapper

def named_transform_decorator(name, in_pattern, out_pattern=None):
    if out_pattern is None: out_pattern = in_pattern
    def wrapper(func):
        return NamedTransformImpl(name, in_pattern, out_pattern, func)
    return wrapper

Given = step_decorator('given')
When = step_decorator('when')
Then = step_decorator('then')
Before = hook_decorator('before')
After = hook_decorator('after')
AfterStep = hook_decorator('after_step')
Transform = transform_decorator
NamedTransform = named_transform_decorator

########NEW FILE########
__FILENAME__ = async
#-*- coding: utf8 -*-

from freshen.test.base import FreshenTestCase

from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks, Deferred

class TwistedTestCase(FreshenTestCase, TestCase):
    """Support asynchronous feature tests."""

    timeout = 240

    # pylint: disable=R0913
    def __init__(self, step_runner, step_registry,
                 feature, scenario, feature_suite):
        FreshenTestCase.__init__(self, step_runner, step_registry,
                                 feature, scenario, feature_suite)
        TestCase.__init__(self, scenario.name)

    def setUp(self):
        """Initialize the test."""
        super(TwistedTestCase, self).setUp()
        hooks = []
        for hook_impl in \
        self.step_registry.get_hooks('before', self.scenario.get_tags()):
            hooks.append(lambda hook=hook_impl: hook.run(self.scenario))
        return self._run_deferred(hooks)

    @inlineCallbacks
    def runScenario(self):
        """Run the test."""
        steps = []
        for step in self.scenario.iter_steps():
            steps.append(lambda s=step: self.runStep(s, 3))
        yield self._run_deferred(steps)
        self.last_step = None

    def tearDown(self):
        """Clean up after the test."""
        hooks = []
        for hook_impl in reversed(\
        self.step_registry.get_hooks('after', self.scenario.get_tags())):
            hooks.append(lambda hook=hook_impl: hook_impl.run(self.scenario))
        return self._run_deferred(hooks)

    @inlineCallbacks
    def _run_deferred(self, callbacks):
        """Create a chain of deferred function calls
        and events.
        
        Returns: Deferred"""
        start_chain = Deferred()
        deferreds = [start_chain]

        for callback in callbacks:
            result = callback()
            if isinstance(result, Deferred):
                # Collect deferred events
                deferreds.append(result)
            elif callable(result):
                # Collect deferred function calls
                deferreds[-1].addCallback(result)

        # Trigger the deferred execution chain.
        start_chain.callback(None)

        # Wait for async events.
        for deferred in deferreds:
            yield deferred


########NEW FILE########
__FILENAME__ = base
#-*- coding: utf8 -*-

import traceback
import sys

from freshen.context import ftc, scc
from freshen.stepregistry import UndefinedStepImpl


class ExceptionWrapper(Exception):

    def __init__(self, e, step, discard_frames=0):
        e = list(e)
        while discard_frames:
            e[2] = e[2].tb_next
            discard_frames -= 1
        self.e = e
        self.step = step

    def __str__(self):
        return "".join(traceback.format_exception(*self.e))


class FeatureSuite(object):

    def setUp(self):
        #log.debug("Clearing feature context")
        ftc.clear()


class FreshenTestCase(object):

    start_live_server = True
    database_single_transaction = True
    database_flush = True
    selenium_start = False
    no_database_interaction = False
    make_translations = True
    required_sane_plugins = ["django", "http"]
    django_plugin_started = False
    http_plugin_started = False
    last_step = None

    test_type = "http"

    def __init__(self, step_runner, step_registry, feature, scenario, feature_suite):
        self.feature = feature
        self.scenario = scenario
        self.context = feature_suite
        self.step_registry = step_registry
        self.step_runner = step_runner

        self.description = feature.name + ": " + scenario.name

    def setUp(self):
        #log.debug("Clearing scenario context")
        scc.clear()

    def runAfterStepHooks(self):
        for hook_impl in reversed(self.step_registry.get_hooks('after_step', self.scenario.get_tags())):
            hook_impl.run(self.scenario)

    def runStep(self, step, discard_frames=0):
        try:
            self.last_step = step
            return self.step_runner.run_step(step)
        except (AssertionError, UndefinedStepImpl, ExceptionWrapper):
            raise
        except:
            raise ExceptionWrapper(sys.exc_info(), step, discard_frames)
        self.runAfterStepHooks()

    def runScenario(self):
        raise NotImplementedError('Must be implemented by subclasses')

########NEW FILE########
__FILENAME__ = pyunit
#-*- coding: utf8 -*-

from freshen.test.base import FreshenTestCase

from unittest import TestCase


class PyunitTestCase(FreshenTestCase, TestCase):
    """Support PyUnit tests."""

    def __init__(self, step_runner, step_registry, feature, scenario, feature_suite):
        FreshenTestCase.__init__(self, step_runner, step_registry,
                                 feature, scenario, feature_suite)
        TestCase.__init__(self, scenario.name)

    def setUp(self):
        super(PyunitTestCase, self).setUp()
        for hook_impl in self.step_registry.get_hooks('before', self.scenario.get_tags()):
            hook_impl.run(self.scenario)

    def runScenario(self):
        for step in self.scenario.iter_steps():
            self.runStep(step, 3)
        self.last_step = None

    def tearDown(self):
        for hook_impl in reversed(self.step_registry.get_hooks('after', self.scenario.get_tags())):
            hook_impl.run(self.scenario)

########NEW FILE########
__FILENAME__ = steps
from freshen import *
from freshen.checks import *

import os
import shlex
import subprocess
import re

@Before
def before(scenario):
    scc.cwd = os.getcwd()
    scc.is_traceback = False
    
@Before('traceback_not_important')
def set_eliminate_traceback(scenario):
    scc.is_traceback = True

@When("^I run nose (.+)$")
def run_nose(args):
    args_list = shlex.split(args)
    command = ['nosetests', '--with-freshen'] + args_list 
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    scc.output, _ = process.communicate()
    scc.status = process.returncode
    scc.output = _normalize_newlines(scc.output) 
    scc.output = scc.output.rstrip()
    _extract_time_and_traceback()
    
_newlines_re = re.compile(r'(\r\n|\r|\r)')
def _normalize_newlines(string):
    return _newlines_re.sub('\n', string)

def _extract_time_and_traceback():
    scc.time = _get_time_in_output_result(scc.output)
    if scc.is_traceback:
        scc.traceback = _get_traceback_in_output_result(scc.output)

_time_re = re.compile(r'\d+\.\d+s')
def _get_time_in_output_result(string):
    times = re.findall(_time_re, string)
    return times[0]

_traceback_re = re.compile(r'Traceback(.+)' 
                           + r'\n' + ('-' * 70),
                           re.DOTALL)
def _get_traceback_in_output_result(string):
    tracebacks = re.findall(_traceback_re, string)
    return tracebacks[0]



@Then("^it should (pass|fail)$")
def check_outcome(exp_status):
    if exp_status == "fail":
        assert_not_equals(scc.status, 0)
    elif scc.status != 0:
        raise Exception("Failed with exit status %d\nOUTPUT:\n%s" % (scc.status, scc.output))

def _check_outcome_with(exp_output, exp_status):
    run_steps("Then it should %s" % exp_status)
    
    exp_output = exp_output.replace("{cwd}", scc.cwd)
    exp_output = exp_output.replace("{time}", scc.time)
    exp_output = exp_output.replace("{sep}", os.sep)
    if scc.is_traceback:
        exp_output = exp_output.replace("{traceback_trace}", scc.traceback)
    assert_equals(exp_output, scc.output)

@Then("^it should (pass|fail) with$")
def check_outcome_with(exp_output, exp_status):
    # Strip color codes out first, we don't care
    scc.output = re.sub("\033\\[[0-9]*m", '', scc.output)
    return _check_outcome_with(exp_output, exp_status)

@Then("^it should (pass|fail) with colorized output$")
def check_outcome_with_colorized(exp_output, exp_status):
    return _check_outcome_with(exp_output, exp_status)

@Then("^it should (pass|fail) with xunit file (\S+)$")
def check_outcome_with_xunit(exp_status, xunit_file):
    run_steps("Then it should %s" % exp_status)
    assert_true(os.path.exists(xunit_file))

    from xml.dom.minidom import parse
    scc.xunit_report = parse(xunit_file)

status_tests = {
    'passed': lambda t: not t.hasChildNodes(),
    'failed': lambda t: t.hasChildNodes() and
                        t.firstChild.hasAttributes() and
                        not t.firstChild.getAttribute('type').startswith('freshen'),
    'undefined': lambda t:  t.hasChildNodes() and
                            t.firstChild.hasAttributes() and
                            t.firstChild.getAttribute('type') == 'freshen.stepregistry.UndefinedStepImpl'
}

@Then("^it should report (\w+) from (\w+) as (passed|failed|undefined)$")
def check_xunit_report(scenario, feature, exp_status):
    testcase = filter(  lambda t: t.getAttribute('classname') == 'freshen.noseplugin.' + feature and
                                  t.getAttribute('name') == scenario,
                        scc.xunit_report.getElementsByTagName('testcase'))[0]

    assert_true(status_tests[exp_status](testcase))

########NEW FILE########
__FILENAME__ = tests_freshen_nose_plugin
import unittest

import os
import sys

from freshen.noseplugin import FreshenNosePlugin
from optparse import OptionParser

class TestFreshenTestCaseName(unittest.TestCase):

    def __init__(self, method_name='runTest'):
        unittest.TestCase.__init__(self, method_name)
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))

    def _make_plugin(self):
        plugin = FreshenNosePlugin()
        parser = OptionParser()

        plugin.options(parser, {})

        sys.argv = ['nosetests', '--with-freshen']
        (options, args) = parser.parse_args()

        plugin.configure(options, None)
        return plugin

    def test_should_use_feature_name_as_class_name_when_subclassing_FreshenTestCase(self):
        plugin = self._make_plugin()
        test_generator = plugin.loadTestsFromFile(self.cur_dir + '/resources/valid_no_tags_no_use_only.feature')
        test_instance = test_generator.next()

        self.assertEquals(test_instance.__class__.__name__, 'Independence of the counter.')

    def test_should_use_scenario_name_as_method_name_when_subclassing_FreshenTestCase(self):
        plugin = self._make_plugin()
        test_generator = plugin.loadTestsFromFile(self.cur_dir + '/resources/valid_no_tags_no_use_only.feature')
        test_instance = test_generator.next()

        self.assertNotEqual(getattr(test_instance, 'Print counter', None), None)

########NEW FILE########
__FILENAME__ = tests_parser
# -*- coding: utf-8 -*-
"""
Partial tests for the parser.
"""
import unittest

from freshen.core import load_language
from freshen.parser import parse_file

import os

class TestParseValidFeature(unittest.TestCase):
    """
    Tests for the parsing of a valid feature.
    """

    def setUp(self):
        self.language = load_language('en')
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))


    def test_should_parse_feature_file_without_tags_and_without_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_no_tags_no_use_only.feature', self.language)
        self.assertEquals(feature.name, 'Independence of the counter.')


    def test_should_parse_feature_file_with_tags_and_without_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_no_use_only.feature', self.language)
        self.assertEquals(feature.tags[0], 'one')


    def test_should_parse_feature_file_without_tags_and_with_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_no_tags_with_use_only.feature', self.language)
        self.assertEquals(feature.use_step_defs[0], 'independent_one')


    def test_should_parse_feature_file_without_tags_and_with_multiple_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_no_tags_with_multiple_use_only.feature', self.language)
        self.assertEquals(feature.use_step_defs[0], 'independent_one')
        self.assertEquals(feature.use_step_defs[1], 'te st')


    def test_should_parse_feature_file_with_tags_and_with_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_with_use_only.feature', self.language)
        self.assertEquals(feature.tags[0], 'one')
        self.assertEquals(feature.use_step_defs[0], 'independent_one')


    def test_should_parse_feature_file_with_tags_and_with_multiple_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_with_multiple_use_only.feature', self.language)
        self.assertEquals(feature.tags[0], 'one')
        self.assertEquals(feature.use_step_defs[0], 'independent_one')
        self.assertEquals(feature.use_step_defs[1], 'te st')


    def test_should_parse_feature_file_with_unicode_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_with_unicode_use_only.feature', self.language)
        self.assertEquals(feature.tags[0], 'one')
        self.assertEquals(feature.use_step_defs[0], 'unicodeèédç')


    def test_should_parse_feature_file_with_full_unix_path_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_with_full_unix_path_use_only.feature', self.language)
        self.assertEquals(feature.tags[0], 'one')
        self.assertEquals(feature.use_step_defs[0], '/home/user/independent_one.py')


    def test_should_parse_feature_file_with_full_windows_path_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_with_full_windows_path_use_only.feature', self.language)
        self.assertEquals(feature.tags[0], 'one')
        self.assertEquals(feature.use_step_defs[0], 'C:\\Documents and Settings\\user\\Desktop\\independent_one.py')


    def test_should_parse_feature_file_with_use_only_short_form(self):
        feature = parse_file(self.cur_dir + '/resources/valid_no_tags_with_use_only_short_form.feature', self.language)
        self.assertEquals(feature.use_step_defs[0], 'independent_one')


    def test_should_parse_feature_file_with_background_and_no_tags(self):
        feature = parse_file(self.cur_dir + '/resources/Befriend_without_tags.feature', self.language)
        self.assertTrue(feature.has_background())
        self.assertEquals(len(feature.background.steps), 2)
        self.assertEquals(len(feature.scenarios), 2)


    def test_should_parse_feature_file_with_background_and_tags(self):
        feature = parse_file(self.cur_dir + '/resources/Befriend_with_tags.feature', self.language)
        self.assertTrue(feature.has_background())
        self.assertEquals(len(feature.background.steps), 2)
        self.assertEquals(len(feature.scenarios), 2)
        self.assertEquals(len(feature.scenarios[0].tags), 1)


    def test_should_parse_feature_file_with_background_and_title_and_tags(self):
        feature = parse_file(self.cur_dir + '/resources/Befriend_with_tags_and_background_title.feature', self.language)
        self.assertTrue(feature.has_background())
        self.assertEquals(len(feature.background.steps), 2)
        self.assertEquals(len(feature.scenarios), 2)
        self.assertEquals(len(feature.scenarios[0].tags), 1)


class TestParseValidFeatureInFrench(unittest.TestCase):
    """
    Tests for the parsing of a valid feature in French.
    """

    def setUp(self):
        self.language = load_language('fr')
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))


    def test_should_parse_feature_file_without_tags_and_without_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_no_tags_no_use_only_fr.feature', self.language)
        self.assertEquals(feature.name, "L'indépendance des compteurs.")


    def test_should_parse_feature_file_with_tags_and_without_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_no_use_only_fr.feature', self.language)
        self.assertEquals(feature.tags[0], 'un')


    def test_should_parse_feature_file_without_tags_and_with_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_no_tags_with_use_only_fr.feature', self.language)
        self.assertEquals(feature.use_step_defs[0], 'independent_one')


    def test_should_parse_feature_file_with_use_only_short_form_fr(self):
        feature = parse_file(self.cur_dir + '/resources/valid_no_tags_with_use_only_short_form_fr.feature', self.language)
        self.assertEquals(feature.use_step_defs[0], 'independent_one')


    def test_should_parse_feature_file_with_background_and_no_tags_fr(self):
        feature = parse_file(self.cur_dir + '/resources/Befriend_without_tags_fr.feature', self.language)
        self.assertTrue(feature.has_background())
        self.assertEquals(len(feature.background.steps), 2)
        self.assertEquals(len(feature.scenarios), 2)


class TestParseValidFeatureInBulgarian(unittest.TestCase):
    """
    Tests for the parsing of a valid feature in Bulgarian.

    @note: This test is used to ensure that if a keyword is not translated
           in a given language, then the missing keyword can be spelled in English.
    """

    def setUp(self):
        self.language = load_language('bg')
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))


    def test_should_parse_feature_file_with_tags_and_with_multiple_use_only(self):
        feature = parse_file(self.cur_dir + '/resources/valid_with_tags_with_multiple_use_only_bg.feature', self.language)
        self.assertEquals(feature.tags[0], 'one')
        self.assertEquals(feature.use_step_defs[0], 'independent_one')
        self.assertEquals(feature.use_step_defs[1], 'te st')


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
