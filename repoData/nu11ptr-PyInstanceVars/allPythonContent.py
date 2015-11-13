__FILENAME__ = instancevars
from functools import wraps
import inspect

def make_setter(args, def_args, names, omit):
    # Construct a function definition that will assign values
    # to instance variables
    function_defn = "def _setter(%s): %s" % (
        ", ".join(args + def_args),
        "; ".join(["self.%s = %s" % (name, name) for name in names
                  if name != "self" and name not in omit])
    )

    # Evaluate the string and extract the constructed function object
    tmp_locals = {}
    exec(function_defn, tmp_locals)
    return tmp_locals['_setter']


def instancevars(func=None, omit=[]):
    """
    A function decorator that automatically creates instance variables from
    function arguments. 

    Arguments can be omitted by adding them to the 'omit' list argument of the decorator.
    Names are retained on a one-to-one basis (i.e '_arg' -> 'self._arg'). Passing
    arguments as raw literals, using a keyword, or as defaults all work. If *args and/or
    **kwargs are used by the decorated function, they are not processed and must be handled
    explicitly.  
    """
    if func:
        names, varargs, keywargs, defaults = inspect.getargspec(func)

        if defaults:
            args, def_args = names[:-len(defaults)], names[-len(defaults):]
            def_args = ["%s=%s" % (arg, repr(default)) for arg, default
                        in zip(def_args, defaults)]
        else:
            def_args = []
            args = names

        _setter = make_setter(args, def_args, names, omit)

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            _setter(self, *args, **kwargs)
            func(self, *args, **kwargs)

        return wrapper
    else:
        return lambda func: instancevars(func, omit)

########NEW FILE########
__FILENAME__ = instancevars_bench
from __future__ import print_function
import timeit
from instancevars import *

class AutoVars(object):
	@instancevars(omit=['arg3', 'arg4'])
	def __init__(self, arg1, arg2, arg3, arg4, arg5, arg6, arg7=7, arg8=8):
		pass

class ExplicitVars(object):
	def __init__(self, arg1, arg2, arg3, arg4, arg5, arg6, arg7=7, arg8=8):
		self.arg1 = arg1
		self.arg2 = arg2
		self.arg5 = arg5
		self.arg6 = arg6
		self.arg7 = arg7
		self.arg8 = arg8

def bench_microseconds(stmt):
	iterations = 100000
	bench_import = 'import instancevars_bench as bench\n'
	total = timeit.timeit(bench_import + stmt, number=iterations)
	return total * 1000000 / iterations

if __name__ == '__main__':
	auto_time = bench_microseconds('bench.AutoVars(1, 2, 3, 4, arg5=5, arg6=6)')
	explicit_time = bench_microseconds('bench.ExplicitVars(1, 2, 3, 4, arg5=5, arg6=6)')

	print("The microseconds per iteration for '@instancevars' was: %.04f" % auto_time)
	print("The microseconds per iteration for explicit init. was: %.04f" %  explicit_time)
	print("Explicit vars are %.04f times faster than using '@instancevars'" % (auto_time / explicit_time))
########NEW FILE########
__FILENAME__ = instancevars_tests
import unittest
from instancevars import *

class BasicTestClass(object):
	@instancevars(omit=['arg2_', 'arg3_'])
	def __init__(self, arg1, arg2_, arg3_='456', _arg4='789'):
		self.arg3 = arg3_

class InheritTestClass(BasicTestClass):
	@instancevars(omit=['arg1_', 'arg3_', 'arg4_'])
	def __init__(self, arg1_, arg2, _newarg, arg3_, arg4_='123'):
		super(InheritTestClass, self).__init__(arg1_, arg2, arg3_, arg4_)

class NoDefaultsTestClass(object):
	@instancevars(omit=['arg1_'])
	def __init__(self, arg1_, arg2, _arg3, arg4):
		pass

class TestInstanceVars(unittest.TestCase):
	def assertNotExist(self, func):
		try:
			func()
		except AttributeError:
			pass
		else:
			self.fail('AttributeError should have been thrown')

	def test_basic(self):
		obj = BasicTestClass(1, 2, 3)
		assert obj.arg1 == 1
		self.assertNotExist(lambda: obj.arg2_ == 2)
		self.assertNotExist(lambda: obj.arg3_ == 3)
		assert obj.arg3 == 3
		assert obj._arg4 == '789'

	def test_inheritance(self):
		obj = InheritTestClass(1, 2, 3, 4)
		assert obj.arg1 == 1
		self.assertNotExist(lambda: obj.arg1_ == 1)

		self.assertNotExist(lambda: obj.arg2_ == 2)
		assert obj.arg2 == 2

		assert obj._newarg == 3
		self.assertNotExist(lambda: obj.arg3_ == 3)

		self.assertNotExist(lambda: obj.arg4_ == '123')
		assert obj._arg4 == '123'

	def test_nodefaults(self):
		obj = NoDefaultsTestClass(1, 2, 3, 4)
		self.assertNotExist(lambda: obj.arg1_ == 1)
		assert obj.arg2 == 2
		assert obj._arg3 == 3
		assert obj.arg4 == 4

if __name__ == '__main__':
	unittest.main()
########NEW FILE########
