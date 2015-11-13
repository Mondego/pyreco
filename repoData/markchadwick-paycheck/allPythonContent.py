__FILENAME__ = checker
import paycheck
from paycheck.generator import PayCheckGenerator

from functools import partial
from itertools import izip, izip_longest, islice, repeat
import sys
from types import FunctionType

def with_checker(*args, **keywords):
    if len(args) == 1 and isinstance(args[0],FunctionType):
        return Checker()(args[0])
    else:
        return Checker(*args, **keywords)

class Checker(object):
    
    def __init__(self, *args, **keywords):
        self._number_of_calls = keywords.pop('number_of_calls', 100)
        self._verbose = keywords.pop('verbose', False) 
        self._argument_generators = [PayCheckGenerator.get(t) for t in args]
        self._keyword_generators = [izip(repeat(name),PayCheckGenerator.get(t)) for (name,t) in keywords.iteritems()]
    
    def __call__(self, test_func):
        if test_func.func_defaults:
            self._argument_generators += [PayCheckGenerator.get(t) for t in test_func.func_defaults]
        if len(self._argument_generators) + len(self._keyword_generators) > 0:
            argument_generators = izip(*self._argument_generators)
            keyword_generators = izip(*self._keyword_generators)
            generator = islice(izip_longest(argument_generators,keyword_generators,fillvalue=()),self._number_of_calls)
        else:
            generator = repeat(((),()),self._number_of_calls)
        def wrapper(*pre_args):
            i = 0
            for (args,keywords) in generator:
                try:
                    if self._verbose:
                        sys.stderr.write("%d: %r\n" % (i, args))
                    test_func(*(pre_args+args), **dict(keywords))
                except Exception, e:
                    if sys.version_info[0] < 3:
                        raise e.__class__("Failed for input %s with message '%s'" % (args+keywords,e)), None, sys.exc_traceback
                    else:
                        raise e.__class__("Failed for input {}".format(args)).with_traceback(e.__traceback__)
                i += 1
        
        wrapper.__doc__ = test_func.__doc__
        wrapper.__name__ = test_func.__name__

        return wrapper

__all__ = [
    'with_checker',
    'Checker',
]

########NEW FILE########
__FILENAME__ = generator
import sys
import string
import random
from itertools import izip, islice
from math import log, exp, pi
import cmath

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

MIN_INT = -sys.maxint - 1
MAX_INT = sys.maxint

MAX_UNI = sys.maxunicode

LIST_LEN = 30

# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------

class PayCheckException(Exception):
    pass

class UnknownTypeException(PayCheckException):
    def __init__(self, t_def):
        self.t_def = t_def
    
    def __str__(self):
        return "PayCheck doesn't know about type: " + str(self.t_def)

class IncompleteTypeException(PayCheckException):
    def __init__(self, t_def):
        self.t_def = t_def
    
    def __str__(self):
        return "The type specification '" + str(self.t_def) + " is incomplete."

# ------------------------------------------------------------------------------
# Base Generator
# ------------------------------------------------------------------------------

class PayCheckGenerator(object):
    def __iter__(self):
        return self

    def next(self):
        return self.__next__()
    
    @classmethod
    def get(cls, t_def):
        try:
            if isinstance(t_def, PayCheckGenerator):
                return t_def
            elif isinstance(t_def, type):
                if issubclass(t_def, PayCheckGenerator):
                    return t_def()
                else:
                    return scalar_generators[t_def]()
            else:
                return container_generators[type(t_def)](t_def)
        except KeyError:
            raise UnknownTypeException(t_def)

# ------------------------------------------------------------------------------
# Basic Type Generators
# ------------------------------------------------------------------------------

class StringGenerator(PayCheckGenerator):
    def __next__(self):
        length = random.randint(0, LIST_LEN)
        return ''.join([chr(random.randint(ord('!'), ord('~'))) for x in xrange(length)])

if sys.version_info[0] < 3:
    class UnicodeGenerator(PayCheckGenerator):
        def __next__(self):
            length = random.randint(0, LIST_LEN)
            return ''.join([unicode(random.randint(0, MAX_UNI)) for x in xrange(length)])

class IntGenerator(PayCheckGenerator):
    def __init__(self, min=MIN_INT, max=MAX_INT, step=1):
        PayCheckGenerator.__init__(self)
        self._min = min
        self._boundary = (max-min)//step
        self._step = step

    def __next__(self):
        return int(random.randint(0,self._boundary)*self._step+self._min)

def irange(min,max,step=1):
    return IntGenerator(min,max,step)

class BooleanGenerator(PayCheckGenerator):
    def __next__(self):
        return random.randint(0, 1) == 1

class UniformFloatGenerator(PayCheckGenerator):
    def __init__(self,min=-1e7,max=1e7):
        self._min = min
        self._length = max-min
        
    def __next__(self):
        return random.random()*self._length+self._min

frange = UniformFloatGenerator

unit_interval_float = frange(0,1)

class NonNegativeFloatGenerator(PayCheckGenerator):
    def __init__(self,minimum_magnitude=1e-7,maximum_magnitude=1e+7):
        minimum_magnitude = log(minimum_magnitude)
        maximum_magnitude = log(maximum_magnitude)
        self._scale_range = maximum_magnitude-minimum_magnitude
        self._minimum_magnitude = minimum_magnitude
    def __next__(self):
        return exp(random.random() * self._scale_range + self._minimum_magnitude)
non_negative_float = NonNegativeFloatGenerator

class PositiveFloatGenerator(NonNegativeFloatGenerator):
    def __next__(self):
        value = 0
        while value == 0:
            value = NonNegativeFloatGenerator.__next__(self)
        return value
positive_float = PositiveFloatGenerator

class FloatGenerator(NonNegativeFloatGenerator):
    def __next__(self):
        return NonNegativeFloatGenerator.__next__(self)*random.choice([+1,-1])

class ComplexGenerator(NonNegativeFloatGenerator):
    def __next__(self):
        return NonNegativeFloatGenerator.__next__(self) * cmath.exp(random.random()*2*pi*1j)

# ------------------------------------------------------------------------------
# Collection Generators
# ------------------------------------------------------------------------------

class CollectionGenerator(PayCheckGenerator):
    def __init__(self, t_def):
        PayCheckGenerator.__init__(self)
        self.inner = PayCheckGenerator.get(t_def)
    
    def __next__(self):
        return self.to_container(islice(self.inner,random.randint(0,LIST_LEN)))

class ListGenerator(CollectionGenerator):
    def __init__(self, example):
        try:
            CollectionGenerator.__init__(self,iter(example).next())
        except StopIteration:
            raise IncompleteTypeException(example)

    def to_container(self,generator):
        return list(generator)

class SetGenerator(ListGenerator):
    def to_container(self,generator):
        return set(generator)

class DictGenerator(CollectionGenerator):
    def __init__(self, example):
        try:
            CollectionGenerator.__init__(self,example.iteritems().next())
        except StopIteration:
            raise IncompleteTypeException(example)

    def to_container(self,generator):
        return dict(generator)

class TupleGenerator(PayCheckGenerator):
    def __init__(self, example):
        PayCheckGenerator.__init__(self)
        self.generators = map(PayCheckGenerator.get,example)

    def __iter__(self):
        return izip(*self.generators)        
        
# ------------------------------------------------------------------------------
# Dictionary of Generators
# ------------------------------------------------------------------------------

scalar_generators = {
    str:     StringGenerator,
    int:     IntGenerator,
    bool:    BooleanGenerator,
    float:   FloatGenerator,
    complex: ComplexGenerator,
  }

if sys.version_info[0] < 3:
    scalar_generators[unicode] = UnicodeGenerator

container_generators = {
    list:    ListGenerator,
    dict:    DictGenerator,
    set:     SetGenerator,
    tuple:   TupleGenerator,
  }

# ------------------------------------------------------------------------------
# List of exports
# ------------------------------------------------------------------------------

__all__ = [
    'MIN_INT',
    'MAX_INT',
    'LIST_LEN',
    'PayCheckException',
    'UnknownTypeException',
    'IncompleteTypeException',
    'PayCheckGenerator',
    'StringGenerator',
    'IntGenerator',
    'irange',
    'BooleanGenerator',
    'UniformFloatGenerator',
    'frange',
    'unit_interval_float',
    'NonNegativeFloatGenerator',
    'non_negative_float',
    'PositiveFloatGenerator',
    'positive_float',
    'FloatGenerator',
    'ComplexGenerator',
    'CollectionGenerator',
    'ListGenerator',
    'SetGenerator',
    'DictGenerator',
    'TupleGenerator',
    'scalar_generators',
    'container_generators',
]

if sys.version_info[0] < 3:
    __all__.append('UnicodeGenerator')

########NEW FILE########
__FILENAME__ = test_basics
import unittest
from paycheck import with_checker
import sys

class Dummy:
    pass

class TestBasics(unittest.TestCase):
    def test_calls_method(self):
        o = Dummy()
        @with_checker(number_of_calls=10)
        def call_me():
            o.times_called += 1
        o.times_called = 0
        call_me()
        self.assertEqual(10,o.times_called)

    def test_calls_method_without_parentheses(self):
        o = Dummy()
        @with_checker
        def call_me():
            o.times_called += 1
        o.times_called = 0
        call_me()
        self.assert_(o.times_called > 0)

    def test_throws_correct_exception_upon_failure(self):
        class MyException(Exception):
            pass
        e = MyException("FAIL")
        @with_checker(number_of_calls=1)
        def call_me():
            raise e
        try:
            call_me()
            self.fail("Exception was not thrown!")
        except MyException:
            pass

tests = [TestBasics]

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_generator
import unittest
from paycheck.generator import *
import sys

class TestGenerator(unittest.TestCase):
    def test_get_int(self):
        self.assert_(isinstance(
                    PayCheckGenerator.get(int),
                    IntGenerator
                    ))
        
    def test_get_string(self):
        self.assert_(isinstance(
                    PayCheckGenerator.get(str),
                    StringGenerator
                    ))

    if sys.version_info[0] < 3:
        def test_get_unicode(self):
            self.assert_(isinstance(
                        PayCheckGenerator.get(unicode),
                        UnicodeGenerator
                        ))
    
    def test_get_boolean(self):
        self.assert_(isinstance(
                    PayCheckGenerator.get(bool),
                    BooleanGenerator
                    ))
    
    def test_get_float(self):
        self.assert_(isinstance(
                    PayCheckGenerator.get(float),
                    FloatGenerator
                    ))
    
    def test_get_unknown_type_throws_exception(self):
        getter = lambda: PayCheckGenerator.get(TestGenerator)
        self.assertRaises(UnknownTypeException, getter)
        
    def test_bad_object_throws_exception(self):
        getter = lambda: PayCheckGenerator.get("what?")
        self.assertRaises(UnknownTypeException, getter)
        
    def test_get_list_of_type(self):
        generator = PayCheckGenerator.get([int])
        self.assertTrue(isinstance(generator, ListGenerator))
        self.assertTrue(isinstance(generator.inner, IntGenerator))
        
    def test_get_nested_list_of_type(self):
        generator = PayCheckGenerator.get([[int]])
        self.assertTrue(isinstance(generator, ListGenerator))
        self.assertTrue(isinstance(generator.inner, ListGenerator))
        self.assertTrue(isinstance(generator.inner.inner, IntGenerator))
    
    def test_empty_list(self):
        getter = lambda: PayCheckGenerator.get([])
        self.assertRaises(IncompleteTypeException, getter)    

    def test_empty_dict(self):
        getter = lambda: PayCheckGenerator.get({})
        self.assertRaises(IncompleteTypeException, getter)
    
    def test_dict_of_str_int(self):
        generator = PayCheckGenerator.get({str:int})
        self.assertTrue(isinstance(generator, DictGenerator))
        self.assertTrue(isinstance(generator.inner, TupleGenerator))
        print(generator.inner.generators[0].__class__)
        self.assertTrue(isinstance(generator.inner.generators[0], StringGenerator))
        self.assertTrue(isinstance(generator.inner.generators[1], IntGenerator))

tests = [TestGenerator]

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sample
import unittest
from paycheck import with_checker
from paycheck.generator import irange

class TestSample(unittest.TestCase):
    
    @with_checker(str, str)
    def test_string_concatination(self, a, b):
        self.assertTrue((a+b).endswith(b))

tests = [TestSample]

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_strings
import unittest
from paycheck import with_checker

class TestStrings(unittest.TestCase):
    """
    More-or-less a direct port of the string testing example from the ScalaCheck
    doc at: http://code.google.com/p/scalacheck/
    """
    
    @with_checker(str, str)
    def test_starts_with(self, a, b):
        self.assertTrue((a+b).startswith(a))

    @with_checker(str, str)
    def test_ends_with(self, a, b):
        self.assertTrue((a+b).endswith(b))

    @with_checker(str, str)
    def test_concat(self, a, b):
        self.assertTrue(len(a+b) >= len(a))
        self.assertTrue(len(a+b) >= len(b))

    @with_checker(str, str)
    def test_substring2(self, a, b):
        self.assertEquals( (a+b)[len(a):], b )
    
    @with_checker(str, str, str)
    def test_substring3(self, a, b, c):
        self.assertEquals((a+b+c)[len(a):len(a)+len(b)], b)

tests = [TestStrings]

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_types
import unittest
from paycheck import with_checker, irange, frange
import sys

class TestTypes(unittest.TestCase):

    @with_checker(str)
    def test_string(self, s):
        self.assertTrue(isinstance(s, str))

    @with_checker(int)
    def test_int(self, i):
        self.assertTrue(isinstance(i, int))

    @with_checker(irange(1,10))
    def test_irange(self, i):
        self.assertTrue(isinstance(i, int))

    @with_checker(float)
    def test_float(self, f):
        self.assertTrue(isinstance(f, float))

    @with_checker(frange(1,10))
    def test_frange(self, f):
        self.assertTrue(isinstance(f, float))

    @with_checker(complex)
    def test_complex(self, c):
        self.assertTrue(isinstance(c, complex))

    if sys.version_info[0] < 3:
        @with_checker(unicode)
        def test_unicode(self, u):
            self.assertTrue(isinstance(u, unicode) or
                        isinstance(u, str))

    @with_checker(bool)
    def test_boolean(self, b):
        self.assertEquals(b, b == True)

    @with_checker([int])
    def test_get_list(self, list_of_ints):
        self.assertTrue(isinstance(list_of_ints, list))
        for i in list_of_ints:
            self.assertTrue(isinstance(i, int))

    @with_checker(set([str]))
    def test_get_list(self, set_of_strs):
        self.assertTrue(isinstance(set_of_strs, set))
        for s in set_of_strs:
            self.assertTrue(isinstance(s, str))

    @with_checker({str: int})
    def test_get_dict(self, dict_of_str_int):
        self.assertTrue(isinstance(dict_of_str_int, dict))
        for key, value in dict_of_str_int.items():
            self.assertTrue(isinstance(key, str))
            self.assertTrue(isinstance(value, int))

    @with_checker(str, [[bool]])
    def test_nested_types(self, s, list_of_lists_of_bools):
        self.assertTrue(isinstance(s, str))
        self.assertTrue(isinstance(list_of_lists_of_bools, list))
        
        for list_of_bools in list_of_lists_of_bools:
            self.assertTrue(isinstance(list_of_bools, list))
            for b in list_of_bools:
                self.assertTrue(isinstance(b, bool))

    @with_checker(int, {str: int})
    def test_dict_of_str_key_int_values(self, i, dict_of_str_int):
        self.assertTrue(isinstance(i, int))
        self.assertTrue(isinstance(dict_of_str_int, dict))
        
        for key, value in dict_of_str_int.items():
            self.assertTrue(isinstance(key, str))
            self.assertTrue(isinstance(value, int))

    @with_checker([{str: int}])
    def test_list_of_dict_of_int_string(self, list_of_dict_of_int_string):
        self.assertTrue(isinstance(list_of_dict_of_int_string, list))
        
        for dict_of_int_string in list_of_dict_of_int_string:
            self.assertTrue(isinstance(dict_of_int_string, dict))

            for key, value in dict_of_int_string.items():
                self.assertTrue(isinstance(key, str))
                self.assertTrue(isinstance(value, int))

tests = [TestTypes]

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_usage
import unittest
from paycheck import with_checker

class TestUsage(unittest.TestCase):

    @with_checker()
    def test_defaults(self, i=int, f=float):
        self.assertTrue(isinstance(i, int))
        self.assertTrue(isinstance(f, float))

    @with_checker(int)
    def test_mixed(self, i, f=float):
        self.assertTrue(isinstance(i, int))
        self.assertTrue(isinstance(f, float))

    @with_checker
    def test_without_parentheses(self, i=int, f=float):
        self.assertTrue(isinstance(i, int))
        self.assertTrue(isinstance(f, float))

tests = [TestUsage]

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_values
import unittest
from paycheck import *
from paycheck import generator

class TestValues(unittest.TestCase):

    @with_checker(irange(0,10))
    def test_irange_range(self,i):
        self.assertTrue(i >= 0)
        self.assertTrue(i <= 10)

    @with_checker(irange(0,10,3))
    def test_irange_step(self,i):
        self.assertEqual(0,i%3)

    @with_checker(irange(-17,86,9))
    def test_irange_exotic(self,i):
        self.assertTrue(i >= -17)
        self.assertTrue(i <= 86)
        self.assertEqual(0,(i+17)%9)

    @with_checker(irange(0,0))
    def test_irange_tiny(self,i):
        self.assertEqual(0,i)

    @with_checker(frange(0,10))
    def test_frange(self,f):
        self.assertTrue(f >=  0)
        self.assertTrue(f <  10)

    @with_checker(unit_interval_float)
    def test_unit_interval_float(self,f):
        self.assertTrue(f >=  0)
        self.assertTrue(f <=  1)

    @with_checker(non_negative_float)
    def test_non_negative_floats(self,f):
        self.assertTrue(f >= 0)

    @with_checker(non_negative_float(1e3,1e5))
    def test_frange(self,f):
        self.assertTrue(f >=  1e3)
        self.assertTrue(f <   1e5)

    @with_checker(positive_float)
    def test_positive_floats(self,f):
        self.assertTrue(f >= 0)

tests = [TestValues]

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = __main__
import tests
tests.run_tests()

########NEW FILE########
