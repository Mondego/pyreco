__FILENAME__ = dependencyinjection
from helpers import frame_out_of_context
from inspect import getframeinfo, getmodule
from sys import _getframe
from types import ModuleType
import gc

_oldimport = __import__

class DependencyInjection(object):

    def __init__(self, double):
        self.double = double
        self.replace_import_to_conf()

    def __enter__(self):
        self.replace_import_to_conf()
        return self

    def replace_import_to_conf(self):
        __builtins__['__import__'] = self.import_double

    def __exit__(self, type, value, traceback):
        self.restore_import()

    def restore_import(self):
        __builtins__['__import__'] = _oldimport

    def import_double(self, name, globals={}, locals={}, fromlist=[], level=-1):
        """import_double(name, globals={}, locals={}, fromlist=[], level=-1) -> module
        """
        if not fromlist:raise ImportError('Use: from ... import ...')
        module = _oldimport(name, globals, locals, fromlist, level)
        self.original = module.__dict__[fromlist[0]]
        self.frame = frame_out_of_context()
        self.inject()
        return module

    def inject(self):
        if hasattr(self,'original'):
            self._original_to_double()

    def restore_object(self):
        self._double_to_original()

    def _original_to_double(self):
            self._replace_all(self.original, self.double)

    def _double_to_original(self):
        if hasattr(self,'original'):
            self._replace_all(self.double, self.original)

    def _replace_all(self, old, new):
        self._old, self._new = old, new
        self._replace_in_context(self.frame.f_locals)
        for module in self._all_modules():
            self._replace_in_context(module.__dict__)

    def _replace_in_context(self, context_dict):
         for k, v in context_dict.items():
                if v is self._old:
                    context_dict[k] = self._new

    def _all_modules(self):
        for obj in gc.get_objects():
            if isinstance(obj, ModuleType):
                yield obj


########NEW FILE########
__FILENAME__ = dummy
#-*- coding:utf-8 -*-

from sys import _getframe as getframe
from _testdouble import _TestDouble

class Dummy(_TestDouble):
    """Dummy:
        Objects that are not used directly by the unit under test. Usually,
        dummies are parameters that are merely passed on.
    """
    def __methodCalled__(self, *args, **kargs):
        return self

    def __iter__(self):
        yield self

    def __str__(self):
        return self.__kargs__.get('str', 'Dummy Object')

    def __int__(self):
        return self.__kargs__.get('int', 1)

    def __float__(self):
        return self.__kargs__.get('float', 1.0)

    def __nonzero__(self):
        return True

    def __getattr__(self, x):
        if x in dir(Dummy):
            return object.__getattribute__(self, x)
        else:
            return self
            
    def __getattribute__(self, x):
        if x == '__class__':
            return self.__kargs__.get('type', type(self))
        elif x in dir(Dummy):
            return object.__getattribute__(self, x)
        else:
            return self


########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from sys import _getframe
import os


def frame_out_of_context():
    this_frame = frame = _getframe(1)
    while folder() in frame.f_code.co_filename:
        frame = frame.f_back
    return frame

def folder():
    return os.path.dirname(__file__)

def format_called(attr, args, kargs):
    if attr == "__getattribute__": return args[0]
    parameters = ', '.join(
                     [repr(arg) for arg in args]
                    +['%s=%r'%(k, v) for k, v in kargs.items()])
    return "%s(%s)"%( attr, parameters)


########NEW FILE########
__FILENAME__ = matcher
from ludibrio.specialarguments import matcher
import re


class ParameterException(Exception):
    """'Exception' for mandatory parameters"""


@matcher
def any(x, y):
    return True

@matcher
def equal_to(x, y):
    if  x == y: return True
    raise ParameterException("%r is not equal to %r"%(x, y))

@matcher
def into(item, container):
    if item in container: return True
    raise ParameterException("%r is not in %r"%(item, container))

@matcher
def contains(container, item):
    if item in container: return True
    raise ParameterException("%r is not contains %r"%(container, item))

@matcher
def greater_than(x, y):
    if x > y: return True
    raise ParameterException("%r is not greater than %r"%(x, y))

@matcher
def greater_than_or_equal_to(x, y):
    if x >= y: return True
    raise ParameterException("%r is not greater than or equal to %r"%(x, y))

@matcher
def less_than(x, y):
    if x < y: return True
    raise ParameterException("%r is not less than %r"%(x, y))

@matcher
def less_than_or_equal_to(x, y):
    if x <= y: return True
    raise ParameterException("%r is not less than or equal to %r"%(x, y))

@matcher
def in_any_order(container, elements):
    for element in elements:
        if element not in container:
            raise ParameterException("%r does not have in any order %r"%(container, elements))
    return True

@matcher
def any_of(container, elements):
    for element in elements:
        if element in container:
            return True
    raise ParameterException("%r does not have any of %r"%(container, elements))

@matcher
def kind_of(obj, kind):
    if isinstance(obj, kind): return True
    raise ParameterException("%r is not a kind of %r"%(obj, kind))

@matcher
def instance_of(obj, kind):
    if isinstance(obj, kind): return True
    raise ParameterException("%r is not a instance of %r"%(obj, kind))

@matcher
def ended_with(x, y):
    if x.endswith(y): return True
    raise ParameterException("%r is not ended with %r"%(x, y))

@matcher
def started_with(x, y):
    if x.startswith(y): return True
    raise ParameterException("%r is not started with %r"%(x, y))


@matcher
def like(string, regex):
    if re.match(regex, string) is not None:
        return True
    raise ParameterException("%r is not like %r"%(string, regex))


@matcher
def equal_to_ignoring_case(x, y):
    if unicode(x).lower() == unicode(y).lower():
        return True
    raise ParameterException("%r is not equal to %r ignoring case"%(x, y))


########NEW FILE########
__FILENAME__ = mock
#-*- coding:utf-8 -*-

from inspect import getframeinfo 
from sys import _getframe as getframe 
from _testdouble import _TestDouble 
from dependencyinjection import DependencyInjection
from ludibrio.helpers import format_called

STOPRECORD = False
RECORDING = True


class Mock(_TestDouble):
    """Mocks are what we are talking about here:
    objects pre-programmed with expectations which form a
    specification of the calls they are expected to receive.
    """
    __expectation__ =[]#[MockedCall(attribute, args, kargs),]
    __recording__ = RECORDING
    __last_property_called__ = None
    __dependency_injection__ = None

    def __enter__(self):
        self.__expectation__ = []
        self.__recording__ = RECORDING
        self.__dependency_injection__ = DependencyInjection(double = self)
        return self

    def __methodCalled__(self, *args, **kargs):
        property = getframeinfo(getframe(1))[2]
        return self._property_called(property, args, kargs)

    def _property_called(self, property, args=[], kargs={}):
        if self.__recording__:
            self._new_expectation(MockedCall(property, args = args, kargs = kargs, response = self))
            return self 
        else:
            return self._expectancy_recorded(property, args, kargs)

    def __exit__(self, type, value, traceback):
        self.__dependency_injection__.restore_import()
        self.__recording__ = STOPRECORD

    def __setattr__(self, attr, value):
        if attr in dir(Mock):
            object.__setattr__(self, attr, value)
        else:
            self._property_called('__setattr__', args=[attr, value])

    def _new_expectation(self, attr):
        self.__expectation__.append(attr)

    def __rshift__(self, response):
            self.__expectation__[-1].set_response(response)
    __lshift__ = __rshift__ 

    def _expectancy_recorded(self, attr, args=[], kargs={}):
        try:
            if self._is_ordered():
                return self._call_mocked_ordered(attr, args, kargs)
            else:
                return self._call_mocked_unordered(attr, args, kargs)
        except (CallExpectation, IndexError):
            raise MockExpectationError(self._unexpected_call_msg(attr, args, kargs))

    def _unexpected_call_msg(self, attr, args, kargs):
        if attr == "__call__":
            attribute = self.__last_property_called__
        else:
            attribute = attr
        return "Mock Object received unexpected call:%s" % format_called(attribute, args, kargs)

    def _is_ordered(self):
        return self.__kargs__.get('ordered', True)

    def _call_mocked_unordered(self, attr, args, kargs):
        for number, call in enumerate(self.__expectation__):
            if call.has_callable(attr, args, kargs):
                call_mocked = self.__expectation__.pop(number)
                return call_mocked.call(attr, args, kargs)
        raise CallExpectation("Mock object has no called %s" %attr)

    def _call_mocked_ordered(self, attr, args, kargs):
        call_mocked = self.__expectation__.pop(0)
        return call_mocked.call(attr, args, kargs)

    def __getattr__(self, x):
        self.__last_property_called__ = x
        return self._property_called('__getattribute__',[x])

    def validate(self):
        self.__dependency_injection__.restore_object()
        if self.__expectation__:
            raise MockExpectationError(self._call_waiting_msg())

    def __del__(self):
        self.__dependency_injection__.restore_object()
        if self.__expectation__:
            print  self._call_waiting_msg()
    
    def _call_waiting_msg(self):
        call_wait = self.__expectation__.pop(0)
        if call_wait.attribute == "__call__":
            attribute = self.__last_property_called__
        else:
            attribute = call_wait.attribute
        return "Call waiting: %s" % format_called(attribute, call_wait.args, call_wait.kargs)


class MockedCall(object):
    def __init__(self, attribute, args=[], kargs={}, response = None):
        self.attribute = attribute 
        self.args = args 
        self.kargs = kargs 
        self.response = response 

    def __repr__(self):
        return str((self.attribute, self.args, self.kargs))

    def set_response(self, response):
        self.response = response

    def has_callable(self, attr, args, kargs):
        return (self.attribute, self.args, self.kargs) == (attr, args, kargs)

    def call(self, attribute, args=[], kargs={}):
        if(self.attribute == attribute 
        and self.args == args 
        and self.kargs == kargs):
            if isinstance(self.response, Exception):
                raise self.response 
            else:
                return self.response 
        else:
            raise CallExpectation('Mock Object received unexpected call.')


class MockExpectationError(AssertionError):
    """Extends AssertionError for unittest compatibility"""

class CallExpectation(AssertionError):
    """Extends AssertionError for unittest compatibility"""

########NEW FILE########
__FILENAME__ = specialarguments
#!/usr/bin/env python
#-*- coding:utf-8 -*-


class matcher(object):
    """Base for special arguments for matching parameters."""

    def __init__(self, matcher, expected=None):
        self.expected = expected
        self.matcher = matcher

    def __call__(self, expected=None):
        return type(self)(self.matcher, expected)

    def __eq__(self, other):
        return self.matcher(other, self.expected)

from matcher import *




########NEW FILE########
__FILENAME__ = compat
"""
This module provides doctest compatibility for Python < 3.
"""
import sys


if sys.version_info < (3,):
    # Python 2 doesn't include the exception's module name in tracebacks, but
    # Python 3 does. Simulate this for doctests by setting __name__ to the
    # exception's fully-qualified name.
    from ludibrio.matcher import ParameterException
    from ludibrio.mock import MockExpectationError
    from ludibrio.spy import SpyExpectationError
    ParameterException.__name__ = 'ludibrio.matcher.ParameterException'
    MockExpectationError.__name__ = 'ludibrio.mock.MockExpectationError'
    SpyExpectationError.__name__ = 'ludibrio.spy.SpyExpectationError'

########NEW FILE########
__FILENAME__ = spy
from ludibrio import Stub
from ludibrio.helpers import format_called


class Spy(Stub):

    __calls__ = []

    def _expectation_value(self, attr, args=[], kargs={}):
        self.__calls__.append([attr, args, kargs])
        for position, (attr_expectation, args_expectation, kargs_expectation, response) in enumerate(self.__expectation__):
            if (attr_expectation, args_expectation, kargs_expectation) == (attr, args, kargs):
                self._to_the_end(position)
                return response
        if self._has_proxy():
            return self._proxy(attr, args, kargs)
        return self
        
    def __repr__(self):
        return 'Spy Object'
    
        
    def called_count(self, expectation):
        count = 0
        for call in self.__calls__:
            if call == expectation:
                count+=1
        return count


class verify(object):

    def __init__(self, spy):
        self.spy = spy

    def __getattr__(self, attr):
        self._attr_called = attr
        return self

    def __call__(self, *args, **kargs):
        self.args = args
        self.kargs = kargs
        return self  

    def called(self, times):
        called_count = self.spy.called_count([self._attr_called,
                                              self.args,
                                              self.kargs])
        if not times.verify(called_count):
            raise SpyExpectationError("Spy expected %s %s%d times but received %d" % (
                                        format_called(self._attr_called,
                                                      self.args,
                                                      self.kargs), 
                                        times.operator_message,
                                        times.expectation_value, 
                                        called_count))
    
    @property
    def before(self):        
        return Before(self)

    @property
    def after(self):
        return After(self)


class Times(object):
    
    def _handle(self, operation, expectation_value):
        self.operation = operation
        self.expectation_value = expectation_value
        return self

    def __eq__(self, expectation_value):
        self.operator_message = ''
        return self._handle(lambda x, y: x == y,
                             expectation_value)        

    def __gt__(self, expectation_value):
        self.operator_message = 'more than '
        return self._handle(lambda x, y: x > y,
                             expectation_value)       
        
    def __ge__(self, expectation_value):
        self.operator_message = 'more than or equal to '
        return self._handle(lambda x, y: x >= y,
                             expectation_value)
    
    def __lt__(self, expectation_value):
        self.operator_message = 'less than '
        return self._handle(lambda x, y: x < y,
                             expectation_value)
        
    def __le__(self, expectation_value):
        self.operator_message = 'less than or equal to '
        return self._handle(lambda x, y: x <= y,
                             expectation_value)

    def verify(self, value):
        return self.operation(value, self.expectation_value)


times = Times()


class TimeCalled(object):
    
    def __init__(self, verify_object):
        attr = verify_object._attr_called
        args = verify_object.args
        kargs = verify_object.kargs
        self.calls = verify_object.spy.__calls__
        self.before = [attr, args, kargs]
    
    def __getattr__(self, attr):
        self.attr_called = [attr]
        return self

    def __call__(self, *args, **kargs):
        self.attr_called += [args, kargs]
        self.after = self.attr_called
        return self.compare()


class Before(TimeCalled):
    def compare(self):
        if not self.calls.index(self.before) < self.calls.index(self.after):
            raise SpyExpectationError("Spy expected %s called before %s" %
                                           (format_called(*self.before), format_called(*self.after)))

class After(TimeCalled):
    def compare(self):
        if not self.calls.index(self.before) > self.calls.index(self.after):
            raise SpyExpectationError("Spy expected %s called after %s" %
                                           (format_called(*self.before), format_called(*self.after)))


class SpyExpectationError(AssertionError):
    """Extends AssertionError for unittest compatibility"""

########NEW FILE########
__FILENAME__ = stub
#-*- coding:utf-8 -*-

from inspect import getframeinfo
from sys import _getframe as getframe
from _testdouble import _TestDouble
from dependencyinjection import DependencyInjection
from ludibrio.helpers import format_called

STOPRECORD = False
RECORDING = True


class Stub(_TestDouble):
    """Stubs provides canned answers to calls made during the test.
    """
    __expectation__= [] # [(attribute, args, kargs),]
    __recording__ = RECORDING
    __last_property_called__ = None
    __dependency_injection__ = None

    def __enter__(self):
        self.__expectation__= []
        self.__recording__ = RECORDING
        self.__dependency_injection__ = DependencyInjection(double = self)
        return self

    def __methodCalled__(self, *args, **kargs):
        property_name = self._property_called_name()
        return self._property_called(property_name, args, kargs)

    def _property_called_name(self):
        property_called_name =  self.__last_property_called__ or getframeinfo(getframe(2))[2]
        self.__last_property_called__ = None
        return property_called_name

    def _property_called(self, property, args=[], kargs={}, response=None):
        if self.__recording__:
            response = response if response is not None else self
            self._new_expectation([property, args, kargs, response])
            return self
        else:
            return self._expectation_value(property, args, kargs)

    def __exit__(self, type, value, traceback):
        self.__dependency_injection__.restore_import()
        self.__recording__ = STOPRECORD

    def __setattr__(self, attr, value):
        if attr in dir(Stub):
            object.__setattr__(self, attr, value)
        else:
            self._property_called('__setattr__', args=[attr, value])

    def _new_expectation(self, expectation):
        self.__expectation__.append(expectation)

    def __rshift__(self, response):
            self.__expectation__[-1][3] = response
    __lshift__ = __rshift__

    def _expectation_value(self, attr, args=[], kargs={}):
        for position, (attr_expectation, args_expectation, kargs_expectation, response) in enumerate(self.__expectation__):
            if (attr_expectation, args_expectation, kargs_expectation) == (attr, args, kargs):
                self._to_the_end(position)
                return response
        if self._has_proxy():
            return self._proxy(attr, args, kargs)
        self._attribute_expectation(attr, args, kargs)

    def _attribute_expectation(self, attr, args, kargs):
        raise AttributeError(
            "Stub Object received unexpected call. %s"%(
                    self._format_called(attr, args, kargs)))

    def _proxy(self, attr, args, kargs):
        proxy = self.__kargs__.get('proxy')
        if attr in ['__getattribute__', '__getattr__'] :
            return getattr(proxy, args[0])
        return getattr(proxy, attr)(*args, **kargs)

    def _has_proxy(self):
        return self.__kargs__.has_key('proxy')

    def _format_called(self, attr, args, kargs):
        if attr == '__call__' and self.__last_property_called__:
            attr = self.__last_property_called__
        return format_called(attr, args, kargs)

    def _to_the_end(self, position):
        self.__expectation__.append(self.__expectation__.pop(position))

    def __getattr__(self, x):
        self.__last_property_called__ = x
        return self._property_called('__getattribute__', (x,), response=self)
    
    def __del__(self):
        self.__dependency_injection__.restore_object()
    
    def restore_import(self):
        self.__dependency_injection__.restore_object()

########NEW FILE########
__FILENAME__ = _importexample
from os import times

def tempo():
    return times()[-1]

########NEW FILE########
__FILENAME__ = _testdouble

class _TestDouble(object):

    __kargs__ = {}
    __args__ = []

    def __init__(self,  *args, **kargs):
        self.__args__ = args or []
        self.__kargs__ = kargs or {}

    def __repr__(self):
        return self.__kargs__.get('repr', self.__class__.__name__ + ' Object')

    def __methodCalled__(self, *args, **kargs):
        raise SyntaxError("invalid syntax, Method Not Implemented")

    def __call__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __getattribute__(self, x):
        if x == '__class__':
            return self.__kargs__.get('type', type(self))
        return object.__getattribute__(self, x)


    def __enter__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __exit__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __item__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __contains__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __eq__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __ge__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __getitem__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __gt__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __le__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __len__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __lt__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __ne__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __delattr__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __delitem__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __add__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __and__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __delattr__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __div__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __divmod__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __floordiv__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __invert__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __long__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __lshift__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __mod__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __mul__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __neg__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __or__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __pos__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __pow__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __radd__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rand__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rdiv__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rfloordiv__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rlshift__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rmod__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rmul__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __ror__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rrshift__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rshift__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rsub__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rtruediv__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __rxor__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __setitem__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __sizeof__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __sub__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __truediv__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __xor__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)

    def __call__(self, *args, **kargs):
        return self.__methodCalled__(*args, **kargs)


########NEW FILE########
