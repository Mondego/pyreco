__FILENAME__ = context
from __future__ import absolute_import
__all__ = [
	'step',
	'steps',
	'world',
	'TestCase',
	'Given',
	'When',
	'Then',
	'And',
	]

from .formatter import PeaFormatter
import unittest
class StepCollection(object):
	def __setattr__(self, attr, val):
		if hasattr(self, attr):
			raise RuntimeError("step %s is already declared!" % (attr,))
		return super(StepCollection, self).__setattr__(attr, val)

class Object(object): pass
class World(unittest.TestCase):
	def __init__(self):
		self._reset()
		super(World, self).__init__('_world')
	
	def _world(self): pass

	def __getattr__(self, a):
		return getattr(self._current, a)

	def _reset(self):
		self._current = Object()

steps = StepCollection()
world = World()

class StepCollectionWrapper(object):
	def __init__(self, prefix):
		self._prefix = prefix

	def __getattr__(self, a):
		attr = getattr(steps, a)
		return attr(self._prefix)

Given = StepCollectionWrapper('Given')
When = StepCollectionWrapper('When')
Then = StepCollectionWrapper('Then')
And = StepCollectionWrapper('And')

class TestCase(unittest.TestCase):
	def setUp(self):
		global world
		world._reset()

def step(func):
	#print "adding func: %s" % (func.__name__)
	setattr(steps, func.__name__, lambda prefix: PeaFormatter.with_formatting(prefix, func))
	return func


########NEW FILE########
__FILENAME__ = formatter
from __future__ import print_function
import os
import sys
import nose
import functools
import termstyle

failure = 'FAILED'
error = 'ERROR'
success = 'passed'
skip = 'skipped'
line_length = 77

class PeaFormatter(nose.plugins.Plugin):
	name = 'pea'
	score = 500
	instance = None
	_newtest = False
	stream = None
	
	def __init__(self, *args):
		self.enabled = False
		type(self).instance = self

	def setOutputStream(self, stream):
		type(self).stream = stream

	def configure(self, options, conf):
		self.enabled = options.verbosity >= 2
		if not self.enabled: return
		color = getattr(options, 'rednose', True)
		force_color = getattr(options, 'rednose_color', 'auto') == 'force'
		if color:
			try:
				(termstyle.enable if force_color else termstyle.auto)()
			except TypeError: # happens when stdout is closed
				pass
		else:
			termstyle.disable()

	def beforeTest(self, test):
		type(self)._newtest = True
	
	def afterTest(self, test):
		if self.enabled and self._newtest is False:
			print >> self.stream, ""

	@classmethod
	def with_formatting(cls, prefix, func):
		def prn(s):
			if cls.instance and cls.instance.enabled:
				if cls._newtest:
					print >> cls.stream, ""
					cls._newtest = False
				print >> cls.stream, s

		@functools.wraps(func)
		def nice_repr(obj):
			return obj if isinstance(obj, str) else repr(obj)

		def _run(*a, **kw):
			name = func.__name__.replace('_', ' ')
			def desc(color):
				desc = color("    %s %s" % (prefix, name))
				if a:
					desc += ' ' + color(termstyle.bold(' '.join(map(nice_repr,a))))
				if kw:
					desc += ' ' + ' '.join([color("%s=%s") % (k, termstyle.bold(repr(v))) for k,v in kw.items()])
				return desc
			try:
				ret = func(*a, **kw)
				prn(desc(termstyle.green))
				return ret
			except:
				prn(desc(termstyle.red))
				raise
		return _run


########NEW FILE########
__FILENAME__ = test_pea
from __future__ import print_function
from pea import *

FEATURE_FILE="""
from pea import *
import steps
class TestFoo(TestCase):
	def test_output(self):
		Given.my_setup("argument")
		When.I_do_foo(keyword_arg=123, second_arg=456)
		And.I_do_bar()
		Then.foo_and_bar_happen()
"""

PASSING_STEPS = """
from pea import *
@step
def my_setup(a): pass

@step
def I_do_foo(**k): pass

@step
def I_do_bar(): pass

@step
def foo_and_bar_happen(): pass
"""

import tempfile
import shutil
from os.path import join
import os
import subprocess
import itertools
import re

@step
def I_have_a_feature_file_with(contents):
	with open(join(world.dir, 'test_feature.py'), 'w') as f:
		f.write(contents)

@step
def I_have_defined_steps(contents):
	with open(join(world.dir, 'steps.py'), 'w') as f:
		f.write(contents)

@step
def I_run_nosetests(*args):
	p = subprocess.Popen(['nosetests'] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	stdout, _ = p.communicate()
	world.nose_output = stdout.decode('utf-8')
	world.nose_success = p.returncode == 0

@step
def the_output_should_be(expected, ignoring_summary=True):
	actual = world.nose_output
	if ignoring_summary:
		actual = '\n'.join(itertools.takewhile(lambda line: '--------' not in line, actual.splitlines()))
	actual = actual.replace(str(termstyle.green), '{green}')
	actual = actual.replace(str(termstyle.reset), '{reset}')
	actual = actual.replace(str(termstyle.bold), '{bold}')
	actual = re.sub(r'(tests? run in )[^ ]+( seconds)', r'\1{time}\2', actual)
	try:
		world.assertEquals(actual, expected)
	except AssertionError:
		print(actual)
		raise

@step
def the_output_should_contain(expected):
	assert expected in world.nose_output


import termstyle
class TestPea(TestCase):
	def setUp(self):
		super(TestPea, self).setUp()
		world.dir = tempfile.mkdtemp()
		os.chdir(world.dir)
	
	def tearDown(self):
		shutil.rmtree(world.dir)
		super(TestPea, self).tearDown()

	def test_basic_output(self):
		Given.I_have_a_feature_file_with(FEATURE_FILE)
		And.I_have_defined_steps(PASSING_STEPS)
		When.I_run_nosetests('-v', '--force-color')
		Then.the_output_should_be("""test_output (test_feature.TestFoo) ... 
{green}    Given my setup{reset} {green}{bold}argument{reset}{reset}
{green}    When I do foo{reset} {green}keyword_arg={bold}123{reset}{reset} {green}second_arg={bold}456{reset}{reset}
{green}    And I do bar{reset}
{green}    Then foo and bar happen{reset}
{green}passed{reset}

""")
	
	def test_non_coloured_output(self):
		Given.I_have_a_feature_file_with(FEATURE_FILE)
		And.I_have_defined_steps(PASSING_STEPS)
		When.I_run_nosetests('-v', '--no-color')
		Then.the_output_should_be("""test_output (test_feature.TestFoo) ... 
    Given my setup argument
    When I do foo keyword_arg=123 second_arg=456
    And I do bar
    Then foo and bar happen
ok

""")
	
	def test_non_verbose_output(self):
		Given.I_have_a_feature_file_with(FEATURE_FILE)
		And.I_have_defined_steps(PASSING_STEPS)
		When.I_run_nosetests()
		Then.the_output_should_be('.')
	
	def test_missing_step(self):
		Given.I_have_a_feature_file_with(FEATURE_FILE)
		And.I_have_defined_steps("")
		When.I_run_nosetests('-v')
		Then.the_output_should_contain("AttributeError: 'StepCollection' object has no attribute 'my_setup'")
	
	def test_using_world(self):
		Given.I_have_a_feature_file_with("""
from pea import *
@step
def I_save(val):
	world.val = val

@step
def I_dont_save_anything(): pass

@step
def I_get(val):
	assert world.val == val


class TestFoo(TestCase):
	def test_success(self):
		Given.I_save(1)
		Then.I_get(1)
	def test_failure(self):
		Given.I_dont_save_anything()
		Then.I_get(1)
""")
		When.I_run_nosetests('-v')
		Then.the_output_should_be("""test_failure (test_feature.TestFoo) ... 
    Given I dont save anything
    Then I get 1
ERROR

test_success (test_feature.TestFoo) ... 
    Given I save 1
    Then I get 1
passed

""")



########NEW FILE########
