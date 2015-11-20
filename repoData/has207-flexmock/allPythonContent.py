__FILENAME__ = flexmock
"""Copyright 2011 Herman Sheremetyev. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


# from flexmock import * is evil, keep it from doing any damage
__all__ = ['flexmock']


import inspect
import re
import sys
import types


AT_LEAST = 'at least'
AT_MOST = 'at most'
EXACTLY = 'exactly'
UPDATED_ATTRS = ['should_receive', 'should_call', 'new_instances']
DEFAULT_CLASS_ATTRIBUTES = [attr for attr in dir(type)
                            if attr not in dir(type('', (object,), {}))]
RE_TYPE = re.compile('')
SPECIAL_METHODS = (classmethod, staticmethod)


try:
  any([])
except NameError:
  # Python 2.4 sucks
  def any(iterable):
    for x in iterable:
      if x: return True
    return False


class FlexmockError(Exception):
  pass


class MockBuiltinError(Exception):
  pass


class MethodSignatureError(FlexmockError):
  pass


class ExceptionClassError(FlexmockError):
  pass


class ExceptionMessageError(FlexmockError):
  pass


class StateError(FlexmockError):
  pass


class MethodCallError(FlexmockError):
  pass


class CallOrderError(FlexmockError):
  pass


class ReturnValue(object):
  def __init__(self, value=None, raises=None):
    self.value = value
    self.raises = raises

  def __str__(self):
    if self.raises:
      return '%s(%s)' % (self.raises, _arg_to_str(self.value))
    else:
      if not isinstance(self.value, tuple):
        return '%s' % _arg_to_str(self.value)
      elif len(self.value) == 1:
        return '%s' % _arg_to_str(self.value[0])
      else:
        return '(%s)' % ', '.join([_arg_to_str(x) for x in self.value])


class ArgSpec(object):
  """Silly hack for inpsect.getargspec return a tuple on python <2.6"""
  def __init__(self, spec):
    self.args, self.varargs, self.keywords, self.defaults = spec


class FlexmockContainer(object):
  """Holds global hash of object/expectation mappings."""
  flexmock_objects = {}
  properties = {}
  ordered = []
  last = None

  @classmethod
  def reset(cls):
    cls.ordered = []
    cls.last = None
    cls.flexmock_objects = {}
    cls.properties = {}

  @classmethod
  def get_flexmock_expectation(cls, obj, name=None, args=None):
    """Retrieves an existing matching expectation."""
    if args == None:
      args = {'kargs': (), 'kwargs': {}}
    if not isinstance(args, dict):
      args = {'kargs': args, 'kwargs': {}}
    if not isinstance(args['kargs'], tuple):
      args['kargs'] = (args['kargs'],)
    if name and obj in cls.flexmock_objects:
      for e in reversed(cls.flexmock_objects[obj]):
        if e.name == name and e.match_args(args):
          if e._ordered:
            cls._verify_call_order(e, args)
          return e

  @classmethod
  def _verify_call_order(cls, expectation, args):
    if not cls.ordered:
      next_method = cls.last
    else:
      next_method = cls.ordered.pop(0)
      cls.last = next_method
    if expectation is not next_method:
      raise CallOrderError(
          '%s called before %s' %
          (_format_args(expectation.name, args),
           _format_args(next_method.name, next_method.args)))

  @classmethod
  def add_expectation(cls, obj, expectation):
    if obj in cls.flexmock_objects:
      cls.flexmock_objects[obj].append(expectation)
    else:
      cls.flexmock_objects[obj] = [expectation]

  @classmethod
  def add_teardown_property(cls, obj, name):
    if obj in cls.properties:
      cls.properties[obj].append(name)
    else:
      cls.properties[obj] = [name]

  @classmethod
  def teardown_properties(cls):
    for obj, names in cls.properties.items():
      for name in names:
        delattr(obj, name)


class Expectation(object):
  """Holds expectations about methods.

  The information contained in the Expectation object includes method name,
  its argument list, return values, and any exceptions that the method might
  raise.
  """

  def __init__(self, mock, name=None, return_value=None, original=None):
    self.name = name
    self.modifier = EXACTLY
    if original is not None:
      self.original = original
    self.args = None
    self.method_type = types.MethodType
    self.argspec = None
    value = ReturnValue(return_value)
    self.return_values = return_values = []
    self._replace_with = None
    if return_value is not None:
      return_values.append(value)
    self.times_called = 0
    self.expected_calls = {
        EXACTLY: None,
        AT_LEAST: None,
        AT_MOST: None}
    self.runnable = lambda: True
    self._mock = mock
    self._pass_thru = False
    self._ordered = False
    self._one_by_one = False
    self._verified = False
    self._callable = True
    self._local_override = False

  def __str__(self):
    return '%s -> (%s)' % (_format_args(self.name, self.args),
                           ', '.join(['%s' % x for x in self.return_values]))

  def __call__(self):
    return self

  def __getattribute__(self, name):
    if name == 'once':
      return _getattr(self, 'times')(1)
    elif name == 'twice':
      return _getattr(self, 'times')(2)
    elif name == 'never':
      return _getattr(self, 'times')(0)
    elif name in ('at_least', 'at_most', 'ordered', 'one_by_one'):
      return _getattr(self, name)()
    elif name == 'mock':
      return _getattr(self, 'mock')()
    else:
      return _getattr(self, name)

  def __getattr__(self, name):
    self.__raise(
        AttributeError,
        "'%s' object has not attribute '%s'" % (self.__class__.__name__, name))

  def _get_runnable(self):
    """Ugly hack to get the name of when() condition from the source code."""
    name = 'condition'
    try:
      source = inspect.getsource(self.runnable)
      if 'when(' in source:
        name = source.split('when(')[1].split(')')[0]
      elif 'def ' in source:
        name = source.split('def ')[1].split('(')[0]
    except:  # couldn't get the source, oh well
      pass
    return name

  def _verify_signature_match(self, *kargs, **kwargs):
    if isinstance(self._mock, Mock):
      return  # no sense in enforcing this for fake objects
    allowed = self.argspec
    # TODO(herman): fix it properly so that module mocks aren't set as methods
    is_method = (inspect.ismethod(getattr(self._mock, self.name)) and
                 self.method_type is not staticmethod and
                 type(self._mock) != types.ModuleType)
    args_len = len(allowed.args)
    if is_method:
      args_len -= 1
    minimum = args_len - (allowed.defaults and len(allowed.defaults) or 0)
    maximum = None
    if allowed.varargs is None and allowed.keywords is None:
      maximum = args_len
    total_positional = len(
        kargs + tuple(a for a in kwargs if a in allowed.args))
    named_optionals = [a for a in kwargs
        if allowed.defaults
        if a in allowed.args[len(allowed.args) - len(allowed.defaults):]]
    if allowed.defaults and total_positional == minimum and named_optionals:
      minimum += len(named_optionals)
    if total_positional < minimum:
      raise MethodSignatureError(
          '%s requires at least %s arguments, expectation provided %s' %
          (self.name, minimum, total_positional))
    if maximum is not None and total_positional > maximum:
      raise MethodSignatureError(
          '%s requires at most %s arguments, expectation provided %s' %
          (self.name, maximum, total_positional))
    if args_len == len(kargs) and any(a for a in kwargs if a in allowed.args):
      raise MethodSignatureError(
          '%s already given as positional arguments to %s' %
          ([a for a in kwargs if a in allowed.args], self.name))
    if not allowed.keywords and any(a for a in kwargs if a not in allowed.args):
      raise MethodSignatureError(
          '%s is not a valid keyword argument to %s' %
          ([a for a in kwargs if a not in allowed.args][0], self.name))

  def _update_original(self, name, obj):
    if hasattr(obj, '__dict__') and name in obj.__dict__:
      self.original = obj.__dict__[name]
    else:
      self.original = getattr(obj, name)
    self._update_argspec()

  def _update_argspec(self):
    original = self.__dict__.get('original')
    if original:
      try:
        self.argspec = ArgSpec(inspect.getargspec(original))
      except TypeError:
        # built-in function: fall back to stupid processing and hope the
        # builtins don't change signature
        pass

  def _normalize_named_args(self, *kargs, **kwargs):
    argspec = self.argspec
    default = {'kargs': kargs, 'kwargs': kwargs}
    if not argspec:
      return default
    ret = {'kargs': (), 'kwargs': kwargs}
    if inspect.ismethod(getattr(self._mock, self.name)):
      args = argspec.args[1:]
    else:
      args = argspec.args
    for i, arg in enumerate(kargs):
      if len(args) <= i: return default
      ret['kwargs'][args[i]] = arg
    return ret

  def __raise(self, exception, message):
    """Safe internal raise implementation.

    In case we're patching builtins, it's important to reset the
    expectation before raising any exceptions or else things like
    open() might be stubbed out and the resulting runner errors are very
    difficult to diagnose.
    """
    self.reset()
    raise exception(message)

  def match_args(self, given_args):
    """Check if the set of given arguments matches this expectation."""
    expected_args = self.args
    given_args = self._normalize_named_args(
        *given_args['kargs'], **given_args['kwargs'])
    if (expected_args == given_args or expected_args is None):
      return True
    if (len(given_args['kargs']) != len(expected_args['kargs']) or
        len(given_args['kwargs']) != len(expected_args['kwargs']) or
        (sorted(given_args['kwargs'].keys()) !=
         sorted(expected_args['kwargs'].keys()))):
      return False
    for i, arg in enumerate(given_args['kargs']):
      if not _arguments_match(arg, expected_args['kargs'][i]):
        return False
    for k, v in given_args['kwargs'].items():
      if not _arguments_match(v, expected_args['kwargs'][k]):
        return False
    return True

  def mock(self):
    """Return the mock associated with this expectation."""
    return self._mock

  def with_args(self, *kargs, **kwargs):
    """Override the arguments used to match this expectation's method.

    Args:
      - kargs: optional keyword arguments
      - kwargs: optional named arguments

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use with_args() with attribute stubs")
    self._update_argspec()
    if self.argspec:
      # do this outside try block as TypeError is way too general and catches
      # unrelated errors in the verify signature code
      self._verify_signature_match(*kargs, **kwargs)
      self.args = self._normalize_named_args(*kargs, **kwargs)
    else:
      self.args = {'kargs': kargs, 'kwargs': kwargs}
    return self

  def and_return(self, *values):
    """Override the return value of this expectation's method.

    When and_return is given multiple times, each value provided is returned
    on successive invocations of the method. It is also possible to mix
    and_return with and_raise in the same manner to alternate between returning
    a value and raising and exception on different method invocations.

    When combined with the one_by_one property, value is treated as a list of
    values to be returned in the order specified by successive calls to this
    method rather than a single list to be returned each time.

    Args:
      - values: optional list of return values, defaults to None if not given

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not values:
      value = None
    elif len(values) == 1:
      value = values[0]
    else:
      value = values

    if not self._callable:
      _setattr(self._mock, self.name, value)
      return self

    return_values = _getattr(self, 'return_values')
    if not _getattr(self, '_one_by_one'):
      value = ReturnValue(value)
      return_values.append(value)
    else:
      try:
        return_values.extend([ReturnValue(v) for v in value])
      except TypeError:
        return_values.append(ReturnValue(value))
    return self

  def times(self, number):
    """Number of times this expectation's method is expected to be called.

    There are also 3 aliases for the times() method:

      - once() -> times(1)
      - twice() -> times(2)
      - never() -> times(0)

    Args:
      - number: int

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use times() with attribute stubs")
    expected_calls = _getattr(self, 'expected_calls')
    modifier = _getattr(self, 'modifier')
    expected_calls[modifier] = number
    return self

  def one_by_one(self):
    """Modifies the return value to be treated as a list of return values.

    Each value in the list is returned on successive invocations of the method.

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use one_by_one() with attribute stubs")
    if not self._one_by_one:
      self._one_by_one = True
      return_values = _getattr(self, 'return_values')
      saved_values = return_values[:]
      self.return_values = return_values = []
      for value in saved_values:
        try:
          for val in value.value:
            return_values.append(ReturnValue(val))
        except TypeError:
          return_values.append(value)
    return self

  def at_least(self):
    """Modifies the associated times() expectation.

    When given, an exception will only be raised if the method is called less
    than times() specified. Does nothing if times() is not given.

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use at_least() with attribute stubs")
    expected_calls = _getattr(self, 'expected_calls')
    modifier = _getattr(self, 'modifier')
    if expected_calls[AT_LEAST] is not None or modifier == AT_LEAST:
      self.__raise(FlexmockError, 'cannot use at_least modifier twice')
    if modifier == AT_MOST and expected_calls[AT_MOST] is None:
      self.__raise(FlexmockError, 'cannot use at_least with at_most unset')
    self.modifier = AT_LEAST
    return self

  def at_most(self):
    """Modifies the associated "times" expectation.

    When given, an exception will only be raised if the method is called more
    than times() specified. Does nothing if times() is not given.

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use at_most() with attribute stubs")
    expected_calls = _getattr(self, 'expected_calls')
    modifier = _getattr(self, 'modifier')
    if expected_calls[AT_MOST] is not None or modifier == AT_MOST:
      self.__raise(FlexmockError, 'cannot use at_most modifier twice')
    if modifier == AT_LEAST and expected_calls[AT_LEAST] is None:
      self.__raise(FlexmockError, 'cannot use at_most with at_least unset')
    self.modifier = AT_MOST
    return self

  def ordered(self):
    """Makes the expectation respect the order of should_receive statements.

    An exception will be raised if methods are called out of order, determined
    by order of should_receive calls in the test.

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use ordered() with attribute stubs")
    self._ordered = True
    FlexmockContainer.ordered.append(self)
    return self

  def when(self, func):
    """Sets an outside resource to be checked before executing the method.

    Args:
      - func: function to call to check if the method should be executed

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use when() with attribute stubs")
    if not hasattr(func, '__call__'):
      self.__raise(FlexmockError, 'when() parameter must be callable')
    self.runnable = func
    return self

  def and_raise(self, exception, *kargs, **kwargs):
    """Specifies the exception to be raised when this expectation is met.

    Args:
      - exception: class or instance of the exception
      - kargs: optional keyword arguments to pass to the exception
      - kwargs: optional named arguments to pass to the exception

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError, "can't use and_raise() with attribute stubs")
    args = {'kargs': kargs, 'kwargs': kwargs}
    return_values = _getattr(self, 'return_values')
    return_values.append(ReturnValue(raises=exception, value=args))
    return self

  def replace_with(self, function):
    """Gives a function to run instead of the mocked out one.

    Args:
      - function: callable

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(FlexmockError,
          "can't use replace_with() with attribute/property stubs")
    replace_with = _getattr(self, '_replace_with')
    original = self.__dict__.get('original')
    if replace_with:
      self.__raise(FlexmockError, 'replace_with cannot be specified twice')
    if function == original:
      self._pass_thru = True
    self._replace_with = function
    return self

  def and_yield(self, *kargs):
    """Specifies the list of items to be yielded on successive method calls.

    In effect, the mocked object becomes a generator.

    Returns:
      - self, i.e. can be chained with other Expectation methods
    """
    if not self._callable:
      self.__raise(
          FlexmockError, "can't use and_yield() with attribute stubs")
    return self.and_return(iter(kargs))

  def verify(self, final=True):
    """Verify that this expectation has been met.

    Args:
      final: boolean, True if no further calls to this method expected
             (skip checking at_least expectations when False)

    Raises:
      MethodCallError Exception
    """
    failed, message = self._verify_number_of_calls(final)
    if failed and not self._verified:
      self._verified = True
      self.__raise(
          MethodCallError,
          '%s expected to be called %s times, called %s times' %
          (_format_args(self.name, self.args), message, self.times_called))

  def _verify_number_of_calls(self, final):
    failed = False
    message = ''
    expected_calls = _getattr(self, 'expected_calls')
    times_called = _getattr(self, 'times_called')
    if expected_calls[EXACTLY] is not None:
      message = 'exactly %s' % expected_calls[EXACTLY]
      if final:
        if times_called != expected_calls[EXACTLY]:
          failed = True
      else:
        if times_called > expected_calls[EXACTLY]:
          failed = True
    else:
      if final and expected_calls[AT_LEAST] is not None:
        message = 'at least %s' % expected_calls[AT_LEAST]
        if times_called < expected_calls[AT_LEAST]:
          failed = True
      if expected_calls[AT_MOST] is not None:
        if message:
          message += ' and '
        message += 'at most %s' % expected_calls[AT_MOST]
        if times_called > expected_calls[AT_MOST]:
          failed = True
    return failed, message

  def reset(self):
    """Returns the methods overriden by this expectation to their originals."""
    _mock = _getattr(self, '_mock')
    if not isinstance(_mock, Mock):
      original = self.__dict__.get('original')
      if original:
        name = _getattr(self, 'name')
        if (hasattr(_mock, '__dict__') and
            name in _mock.__dict__ and
            self._local_override):
          del _mock.__dict__[name]
        elif (hasattr(_mock, '__dict__') and
            name in _mock.__dict__ and
            type(_mock.__dict__) is dict):
          _mock.__dict__[name] = original
        else:
          setattr(_mock, name, original)
    del self


class Mock(object):
  """Fake object class returned by the flexmock() function."""

  def __init__(self, **kwargs):
    """Mock constructor.

    Args:
      - kwargs: dict of attribute/value pairs used to initialize the mock object
    """
    self._object = self
    for attr, value in kwargs.items():
      if type(value) is property:
        setattr(self.__class__, attr, value)
      else:
        setattr(self, attr, value)

  def __enter__(self):
    return self._object

  def __exit__(self, type, value, traceback):
    return self

  def __call__(self, *kargs, **kwargs):
    """Hack to make Expectation.mock() work with parens."""
    return self

  def __iter__(self):
    """Makes the mock object iterable.

    Call the instance's version of __iter__ if available, otherwise yield self.
    """
    if (hasattr(self, '__dict__') and type(self.__dict__) is dict and
        '__iter__' in self.__dict__):
      for item in self.__dict__['__iter__'](self):
        yield item
    else:
      yield self

  def should_receive(self, name):
    """Replaces the specified attribute with a fake.

    Args:
      - name: string name of the attribute to replace

    Returns:
      - Expectation object which can be used to modify the expectations
        on the fake attribute
    """
    if name in UPDATED_ATTRS:
      raise FlexmockError('unable to replace flexmock methods')
    chained_methods = None
    obj = _getattr(self, '_object')
    if '.' in name:
      name, chained_methods = name.split('.', 1)
    name = _update_name_if_private(obj, name)
    _ensure_object_has_named_attribute(obj, name)
    if chained_methods:
      if (not isinstance(obj, Mock) and
          not hasattr(getattr(obj, name), '__call__')):
        return_value = _create_partial_mock(getattr(obj, name))
      else:
        return_value = Mock()
      self._create_expectation(obj, name, return_value)
      return return_value.should_receive(chained_methods)
    else:
      return self._create_expectation(obj, name)

  def should_call(self, name):
    """Creates a spy.

    This means that the original method will be called rather than the fake
    version. However, we can still keep track of how many times it's called and
    with what arguments, and apply expectations accordingly.

    should_call is meaningless/not allowed for non-callable attributes.

    Args:
      - name: string name of the method

    Returns:
      - Expectation object
    """
    expectation = self.should_receive(name)
    return expectation.replace_with(expectation.__dict__.get('original'))

  def new_instances(self, *kargs):
    """Overrides __new__ method on the class to return custom objects.

    Alias for should_receive('__new__').and_return(kargs).one_by_one

    Args:
      - kargs: objects to return on each successive call to __new__

    Returns:
      - Expectation object
    """
    if _isclass(self._object):
      return self.should_receive('__new__').and_return(kargs).one_by_one
    else:
      raise FlexmockError('new_instances can only be called on a class mock')

  def _create_expectation(self, obj, name, return_value=None):
    if self not in FlexmockContainer.flexmock_objects:
      FlexmockContainer.flexmock_objects[self] = []
    expectation = self._save_expectation(name, return_value)
    FlexmockContainer.add_expectation(self, expectation)
    if _isproperty(obj, name):
      self._update_property(expectation, name, return_value)
    elif (isinstance(obj, Mock) or
          hasattr(getattr(obj, name), '__call__') or
          _isclass(getattr(obj, name))):
      self._update_method(expectation, name)
    else:
      self._update_attribute(expectation, name, return_value)
    return expectation

  def _save_expectation(self, name, return_value=None):
    if name in [x.name for x in
                FlexmockContainer.flexmock_objects[self]]:
      expectation = [x for x in FlexmockContainer.flexmock_objects[self]
                     if x.name == name][0]
      expectation = Expectation(
          self._object, name=name, return_value=return_value,
          original=expectation.__dict__.get('original'))
    else:
      expectation = Expectation(
          self._object, name=name, return_value=return_value)
    return expectation

  def _update_class_for_magic_builtins( self, obj, name):
    """Fixes MRO for builtin methods on new-style objects.

    On 2.7+ and 3.2+, replacing magic builtins on instances of new-style
    classes has no effect as the one attached to the class takes precedence.
    To work around it, we update the class' method to check if the instance
    in question has one in its own __dict__ and call that instead.
    """
    if not (name.startswith('__') and name.endswith('__') and len(name) > 4):
      return
    original = getattr(obj.__class__, name)
    def updated(self, *kargs, **kwargs):
      if (hasattr(self, '__dict__') and type(self.__dict__) is dict and
          name in self.__dict__):
        return self.__dict__[name](*kargs, **kwargs)
      else:
        return original(self, *kargs, **kwargs)
    setattr(obj.__class__, name, updated)
    if _get_code(updated) != _get_code(original):
      self._create_placeholder_mock_for_proper_teardown(
          obj.__class__, name, original)

  def _create_placeholder_mock_for_proper_teardown(self, obj, name, original):
    """Ensures that the given function is replaced on teardown."""
    mock = Mock()
    mock._object = obj
    expectation = Expectation(obj, name=name, original=original)
    FlexmockContainer.add_expectation(mock, expectation)

  def _update_method(self, expectation, name):
    method_instance = self._create_mock_method(name)
    obj = self._object
    if _hasattr(obj, name) and not hasattr(expectation, 'original'):
      expectation._update_original(name, obj)
      method_type = type(_getattr(expectation, 'original'))
      try:
        # TODO(herman): this is awful, fix this properly.
        # When a class/static method is mocked out on an *instance*
        # we need to fetch the type from the class
        method_type = type(_getattr(obj.__class__, name))
      except: pass
      if method_type in SPECIAL_METHODS:
        expectation.original_function = getattr(obj, name)
      expectation.method_type = method_type
    override = _setattr(obj, name, types.MethodType(method_instance, obj))
    expectation._local_override = override
    if (override and not _isclass(obj) and not isinstance(obj, Mock) and
        hasattr(obj.__class__, name)):
      self._update_class_for_magic_builtins(obj, name)

  def _update_attribute(self, expectation, name, return_value=None):
    obj = self._object
    expectation._callable = False
    if _hasattr(obj, name) and not hasattr(expectation, 'original'):
      expectation._update_original(name, obj)
    override = _setattr(obj, name, return_value)
    expectation._local_override = override

  def _update_property(self, expectation, name, return_value=None):
    new_name = '_flexmock__%s' % name
    obj = self._object
    if not _isclass(obj):
      obj = obj.__class__
    expectation._callable = False
    original = getattr(obj, name)
    @property
    def updated(self):
      if (hasattr(self, '__dict__') and type(self.__dict__) is dict and
          name in self.__dict__):
        return self.__dict__[name]
      else:
        return getattr(self, new_name)
    setattr(obj, name, updated)
    if not hasattr(obj, new_name):
      # don't try to double update
      FlexmockContainer.add_teardown_property(obj, new_name)
      setattr(obj, new_name, original)
      self._create_placeholder_mock_for_proper_teardown(obj, name, original)

  def _create_mock_method(self, name):
    def _handle_exception_matching(expectation):
      return_values = _getattr(expectation, 'return_values')
      if return_values:
        raised, instance = sys.exc_info()[:2]
        message = '%s' % instance
        expected = return_values[0].raises
        if not expected:
          raise
        args = return_values[0].value
        expected_instance = expected(*args['kargs'], **args['kwargs'])
        expected_message = '%s' % expected_instance
        if _isclass(expected):
          if expected is not raised and expected not in raised.__bases__:
            raise (ExceptionClassError('expected %s, raised %s' %
                   (expected, raised)))
          if args['kargs'] and type(RE_TYPE) is type(args['kargs'][0]):
            if not args['kargs'][0].search(message):
              raise (ExceptionMessageError('expected /%s/, raised "%s"' %
                     (args['kargs'][0].pattern, message)))
          elif expected_message and expected_message != message:
            raise (ExceptionMessageError('expected "%s", raised "%s"' %
                   (expected_message, message)))
        elif expected is not raised:
          raise (ExceptionClassError('expected "%s", raised "%s"' %
                 (expected, raised)))
      else:
        raise

    def match_return_values(expected, received):
      if not isinstance(expected, tuple):
        expected = (expected,)
      if not isinstance(received, tuple):
        received = (received,)
      if len(received) != len(expected):
        return False
      for i, val in enumerate(received):
        if not _arguments_match(val, expected[i]):
          return False
      return True

    def pass_thru(expectation, runtime_self, *kargs, **kwargs):
      return_values = None
      try:
        original = _getattr(expectation, 'original')
        _mock = _getattr(expectation, '_mock')
        if _isclass(_mock):
          if type(original) in SPECIAL_METHODS:
            original = _getattr(expectation, 'original_function')
            return_values = original(*kargs, **kwargs)
          else:
            return_values = original(runtime_self, *kargs, **kwargs)
        else:
          return_values = original(*kargs, **kwargs)
      except:
        return _handle_exception_matching(expectation)
      expected_values = _getattr(expectation, 'return_values')
      if (expected_values and
          not match_return_values(expected_values[0].value, return_values)):
        raise (MethodSignatureError('expected to return %s, returned %s' %
               (expected_values[0].value, return_values)))
      return return_values

    def mock_method(runtime_self, *kargs, **kwargs):
      arguments = {'kargs': kargs, 'kwargs': kwargs}
      expectation = FlexmockContainer.get_flexmock_expectation(
          self, name, arguments)
      if expectation:
        if not expectation.runnable():
          raise StateError('%s expected to be called when %s is True' %
                             (name, expectation._get_runnable()))
        expectation.times_called += 1
        expectation.verify(final=False)
        _pass_thru = _getattr(expectation, '_pass_thru')
        _replace_with = _getattr(expectation, '_replace_with')
        if _pass_thru:
          return pass_thru(expectation, runtime_self, *kargs, **kwargs)
        elif _replace_with:
          return _replace_with(*kargs, **kwargs)
        return_values = _getattr(expectation, 'return_values')
        if return_values:
          return_value = return_values[0]
          del return_values[0]
          return_values.append(return_value)
        else:
          return_value = ReturnValue()
        if return_value.raises:
          if _isclass(return_value.raises):
            raise return_value.raises(
                *return_value.value['kargs'], **return_value.value['kwargs'])
          else:
            raise return_value.raises
        else:
          return return_value.value
      else:
        # make sure to clean up expectations to ensure none of them
        # interfere with the runner's error reporing mechanism
        # e.g. open()
        for _, expectations in FlexmockContainer.flexmock_objects.items():
          for expectation in expectations:
            _getattr(expectation, 'reset')()
        raise MethodSignatureError(_format_args(name, arguments))

    return mock_method


def _arg_to_str(arg):
  if type(RE_TYPE) is type(arg):
    return '/%s/' % arg.pattern
  if sys.version_info < (3, 0):
    # prior to 3.0 unicode strings are type unicode that inherits
    # from basestring along with str, in 3.0 both unicode and basestring
    # go away and str handles everything properly
    if isinstance(arg, basestring):
      return '"%s"' % (arg,)
    else:
      return '%s' % (arg,)
  else:
    if isinstance(arg, str):
      return '"%s"' % (arg,)
    else:
      return '%s' % (arg,)


def _format_args(name, arguments):
  if arguments is None:
    arguments = {'kargs': (), 'kwargs': {}}
  kargs = ', '.join(_arg_to_str(arg) for arg in arguments['kargs'])
  kwargs = ', '.join('%s=%s' % (k, _arg_to_str(v)) for k, v in
                                arguments['kwargs'].items())
  if kargs and kwargs:
    args = '%s, %s' % (kargs, kwargs)
  else:
    args = '%s%s' % (kargs, kwargs)
  return '%s(%s)' % (name, args)


def _create_partial_mock(obj_or_class, **kwargs):
  matches = [x for x in FlexmockContainer.flexmock_objects
             if x._object is obj_or_class]
  if matches:
    mock = matches[0]
  else:
    mock = Mock()
    mock._object = obj_or_class
  for name, return_value in kwargs.items():
    if hasattr(return_value, '__call__'):
      mock.should_receive(name).replace_with(return_value)
    else:
      mock.should_receive(name).and_return(return_value)
  if not matches:
    FlexmockContainer.add_expectation(mock, Expectation(obj_or_class))
  if (_attach_flexmock_methods(mock, Mock, obj_or_class) and
    not _isclass(mock._object)):
    mock = mock._object
  return mock


def _attach_flexmock_methods(mock, flexmock_class, obj):
  try:
    for attr in UPDATED_ATTRS:
      if hasattr(obj, attr):
        if (_get_code(getattr(obj, attr)) is not
            _get_code(getattr(flexmock_class, attr))):
          return False
    for attr in UPDATED_ATTRS:
      _setattr(obj, attr, getattr(mock, attr))
  except TypeError:
    raise MockBuiltinError(
        'Python does not allow you to mock builtin objects or modules. '
        'Consider wrapping it in a class you can mock instead')
  except AttributeError:
    raise MockBuiltinError(
        'Python does not allow you to mock instances of builtin objects. '
        'Consider wrapping it in a class you can mock instead')
  return True


def _get_code(func):
  if hasattr(func, 'func_code'):
    code = 'func_code'
  elif hasattr(func, 'im_func'):
    func = func.im_func
    code = 'func_code'
  else:
    code = '__code__'
  return getattr(func, code)


def _arguments_match(arg, expected_arg):
  if expected_arg == arg:
    return True
  elif _isclass(expected_arg) and isinstance(arg, expected_arg):
    return True
  elif (type(RE_TYPE) is type(expected_arg) and
        expected_arg.search(arg)):
    return True
  else:
    return False


def _getattr(obj, name):
  """Convenience wrapper to work around custom __getattribute__."""
  return object.__getattribute__(obj, name)


def _setattr(obj, name, value):
  """Ensure we use local __dict__ where possible."""
  local_override = False
  if hasattr(obj, '__dict__') and type(obj.__dict__) is dict:
    if name not in obj.__dict__:
      local_override = True
    obj.__dict__[name] = value
  else:
    setattr(obj, name, value)
  return local_override


def _hasattr(obj, name):
  """Ensure hasattr checks don't create side-effects for properties."""
  if (not _isclass(obj) and hasattr(obj, '__dict__') and
      name not in obj.__dict__):
    if name in DEFAULT_CLASS_ATTRIBUTES:
      return False  # avoid false positives for things like __call__
    else:
      return hasattr(obj.__class__, name)
  else:
    return hasattr(obj, name)


def _isclass(obj):
  """Fixes stupid bug in inspect.isclass from < 2.7."""
  if sys.version_info < (2, 7):
    return isinstance(obj, (type, types.ClassType))
  else:
    return inspect.isclass(obj)


def _isproperty(obj, name):
  if isinstance(obj, Mock):
    return False
  if not _isclass(obj) and hasattr(obj, '__dict__') and name not in obj.__dict__:
    attr = getattr(obj.__class__, name)
    if type(attr) is property:
      return True
  elif _isclass(obj):
    attr = getattr(obj, name)
    if type(attr) is property:
      return True
  return False


def _update_name_if_private(obj, name):
  if (name.startswith('__') and not name.endswith('__') and
      not inspect.ismodule(obj)):
    if _isclass(obj):
      class_name = obj.__name__
    else:
      class_name = obj.__class__.__name__
    name = '_%s__%s' % (class_name.lstrip('_'), name.lstrip('_'))
  return name


def _ensure_object_has_named_attribute(obj, name):
  if not isinstance(obj, Mock) and not _hasattr(obj, name):
    exc_msg = '%s does not have attribute %s' % (obj, name)
    if name == '__new__':
       exc_msg = 'old-style classes do not have a __new__() method'
    raise FlexmockError(exc_msg)


def flexmock_teardown():
  """Performs lexmock-specific teardown tasks."""
  saved = {}
  instances = []
  classes = []
  for mock_object, expectations in FlexmockContainer.flexmock_objects.items():
    saved[mock_object] = expectations[:]
    for expectation in expectations:
      _getattr(expectation, 'reset')()
  for mock in saved.keys():
    obj = mock._object
    if not isinstance(obj, Mock) and not _isclass(obj):
      instances.append(obj)
    if _isclass(obj):
      classes.append(obj)
  for obj in instances + classes:
    for attr in UPDATED_ATTRS:
      try:
        obj_dict = obj.__dict__
        if _get_code(obj_dict[attr]) is _get_code(Mock.__dict__[attr]):
          del obj_dict[attr]
      except:
        try:
          if _get_code(getattr(obj, attr)) is _get_code(Mock.__dict__[attr]):
            delattr(obj, attr)
        except AttributeError:
          pass
  FlexmockContainer.teardown_properties()
  FlexmockContainer.reset()

  # make sure this is done last to keep exceptions here from breaking
  # any of the previous steps that cleanup all the changes
  for mock_object, expectations in saved.items():
    for expectation in expectations:
      _getattr(expectation, 'verify')()


def flexmock(spec=None, **kwargs):
  """Main entry point into the flexmock API.

  This function is used to either generate a new fake object or take
  an existing object (or class or module) and use it as a basis for
  a partial mock. In case of a partial mock, the passed in object
  is modified to support basic Mock class functionality making
  it unnecessary to make successive flexmock() calls on the same
  objects to generate new expectations.

  Examples:
    >>> flexmock(SomeClass)
    >>> SomeClass.should_receive('some_method')

  NOTE: it's safe to call flexmock() on the same object, it will detect
  when an object has already been partially mocked and return it each time.

  Args:
    - spec: object (or class or module) to mock
    - kwargs: method/return_value pairs to attach to the object

  Returns:
    Mock object if no spec is provided. Otherwise return the spec object.
  """
  if spec is not None:
    return _create_partial_mock(spec, **kwargs)
  else:
    # use this intermediate class to attach properties
    klass = type('MockClass', (Mock,), {})
    return klass(**kwargs)


# RUNNER INTEGRATION


def _hook_into_pytest():
  try:
    from _pytest import runner
    saved = runner.call_runtest_hook
    def call_runtest_hook(item, when, **kwargs):
      ret = saved(item, when, **kwargs)
      if when != 'call' or ret.excinfo is None:
        return ret
      teardown = runner.CallInfo(flexmock_teardown, when=when)
      teardown.result = None
      return teardown
    runner.call_runtest_hook = call_runtest_hook

  except ImportError:
    pass
_hook_into_pytest()


def _hook_into_doctest():
  try:
    from doctest import DocTestRunner
    saved = DocTestRunner.run
    def run(self, test, compileflags=None, out=None, clear_globs=True):
      try:
        return saved(self, test, compileflags, out, clear_globs)
      finally:
        flexmock_teardown()
    DocTestRunner.run = run
  except ImportError:
    pass
_hook_into_doctest()


def _patch_test_result(klass):
  """Patches flexmock into any class that inherits unittest.TestResult.

  This seems to work well for majority of test runners. In the case of nose
  it's not even necessary as it doesn't override unittest.TestResults's
  addSuccess and addFailure methods so simply patching unittest works
  out of the box for nose.

  For those that do inherit from unittest.TestResult and override its
  stopTest and addSuccess methods, patching is pretty straightforward
  (numerous examples below).

  The reason we don't simply patch unittest's parent TestResult class
  is stopTest and addSuccess in the child classes tend to add messages
  into the output that we want to override in case flexmock generates
  its own failures.
  """

  saved_addSuccess = klass.addSuccess
  saved_stopTest = klass.stopTest

  def addSuccess(self, test):
    self._pre_flexmock_success = True

  def stopTest(self, test):
    if _get_code(saved_stopTest) is not _get_code(stopTest):
      # if parent class was for some reason patched, avoid calling
      # flexmock_teardown() twice and delegate up the class hierarchy
      # this doesn't help if there is a gap and only the parent's
      # parent class was patched, but should cover most screw-ups
      try:
        flexmock_teardown()
        saved_addSuccess(self, test)
      except:
        if hasattr(self, '_pre_flexmock_success'):
          self.addFailure(test, sys.exc_info())
      if hasattr(self, '_pre_flexmock_success'):
        del self._pre_flexmock_success
    return saved_stopTest(self, test)

  if klass.stopTest is not stopTest:
    klass.stopTest = stopTest

  if klass.addSuccess is not addSuccess:
    klass.addSuccess = addSuccess


def _hook_into_unittest():
  import unittest
  try:
    try:
      # only valid TestResult class for unittest is TextTestResult
      _patch_test_result(unittest.TextTestResult)
    except AttributeError:
      # ugh, python2.4
      _patch_test_result(unittest._TextTestResult)
  except: # let's not take any chances
    pass
_hook_into_unittest()


def _hook_into_unittest2():
  try:
    try:
      from unittest2 import TextTestResult
    except ImportError:
      # Django has its own copy of unittest2 it uses as fallback
      from django.utils.unittest import TextTestResult
    _patch_test_result(TextTestResult)
  except:
    pass
_hook_into_unittest2()


def _hook_into_twisted():
  try:
    from twisted.trial import reporter
    _patch_test_result(reporter.MinimalReporter)
    _patch_test_result(reporter.TextReporter)
    _patch_test_result(reporter.VerboseTextReporter)
    _patch_test_result(reporter.TreeReporter)
  except:
    pass
_hook_into_twisted()


def _hook_into_subunit():
  try:
    import subunit
    _patch_test_result(subunit.TestProtocolClient)
  except:
    pass
_hook_into_subunit()


def _hook_into_zope():
  try:
    from zope import testrunner
    _patch_test_result(testrunner.runner.TestResult)
  except:
    pass
_hook_into_zope()


def _hook_into_testtools():
  try:
    from testtools import testresult
    _patch_test_result(testresult.TestResult)
  except:
    pass
_hook_into_testtools()


def _hook_into_teamcity_unittest():
  try:
    from tcunittest import TeamcityTestResult
    _patch_test_result(TeamcityTestResult)
  except:
    pass
_hook_into_teamcity_unittest()

# Dark magic to make the flexmock module itself callable.
# So that you can say:
#   import flexmock
# instead of:
#   from flexmock import flexmock
class _CallableModule(types.ModuleType):
  def __init__(self):
    super(_CallableModule, self).__init__('flexmock')
    self._realmod = sys.modules['flexmock']
    sys.modules['flexmock'] = self
    self.__doc__ = flexmock.__doc__
  def __dir__(self):
    return dir(self._realmod)
  def __call__(self, *args, **kw):
    return self._realmod.flexmock(*args, **kw)
  def __getattr__(self, attr):
    return getattr(self._realmod, attr)

_CallableModule()

########NEW FILE########
__FILENAME__ = flexmock_modern_test
import flexmock
import sys
import unittest

class ModernClass(object):
  """Contains features only available in 2.6 and above."""
  def test_context_manager_on_instance(self):
    class CM(object):
      def __enter__(self): pass
      def __exit__(self, *_): pass
    cm = CM()
    flexmock(cm).should_call('__enter__').once
    flexmock(cm).should_call('__exit__').once
    with cm: pass
    self._tear_down()

  def test_context_manager_on_class(self):
    class CM(object):
      def __enter__(self): pass
      def __exit__(self, *_): pass
    cm = CM()
    flexmock(CM).should_receive('__enter__').once
    flexmock(CM).should_receive('__exit__').once
    with cm: pass
    self._tear_down()

  def test_flexmock_should_support_with(self):
    foo = flexmock()
    with foo as mock:
      mock.should_receive('bar').and_return('baz')
    assert foo.bar() == 'baz'

  def test_builtin_open(self):
    if sys.version_info < (3, 0):
      mock = flexmock(sys.modules['__builtin__'])
    else:
      mock = flexmock(sys.modules['builtins'])
    fake_fd = flexmock(read=lambda: 'some data')
    mock.should_receive('open').once.with_args('file_name').and_return(fake_fd)
    with open('file_name') as f:
      data = f.read()
    self.assertEqual('some data', data)



class TestFlexmockUnittestModern(ModernClass, unittest.TestCase):
  def _tear_down(self):
    return unittest.TestCase.tearDown(self)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = flexmock_nose_test
from flexmock import MethodCallError
from flexmock import flexmock_teardown
from flexmock_test import assertRaises
from nose import with_setup
import flexmock
import flexmock_test
import unittest


def test_module_level():
  m = flexmock(mod=2)
  m.should_receive('mod').once
  assertRaises(MethodCallError, flexmock_teardown)


def test_module_level_generator():
  mock = flexmock(foo=lambda x, y: None, bar=lambda: None)
  mock.should_receive('bar').never  # change never to once to observe the failure
  for i in range(0, 3):
    yield mock.foo, i, i*3


class TestRegularClass(flexmock_test.RegularClass):

  def test_regular(self):
    a = flexmock(a=2)
    a.should_receive('a').once
    assertRaises(MethodCallError, flexmock_teardown)

  def test_class_level_generator_tests(self):
    mock = flexmock(foo=lambda a, b: a)
    mock.should_receive('bar').never  # change never to once to observe the failure
    for i in range(0, 3):
      yield mock.foo, i, i*3


class TestUnittestClass(flexmock_test.TestFlexmockUnittest):

  def test_unittest(self):
    a = flexmock(a=2)
    a.should_receive('a').once
    assertRaises(MethodCallError, flexmock_teardown)

########NEW FILE########
__FILENAME__ = flexmock_pytest_test
from flexmock import MethodCallError
from flexmock import flexmock_teardown
from flexmock_test import assertRaises
import flexmock
import flexmock_test
import unittest
import pytest


def test_module_level_test_for_pytest():
  flexmock(foo='bar').should_receive('foo').once
  assertRaises(MethodCallError, flexmock_teardown)


@pytest.fixture()
def runtest_hook_fixture():
  return flexmock(foo='bar').should_receive('foo').once.mock()

def test_runtest_hook_with_fixture_for_pytest(runtest_hook_fixture):
  runtest_hook_fixture.foo()


class TestForPytest(flexmock_test.RegularClass):

  def test_class_level_test_for_pytest(self):
    flexmock(foo='bar').should_receive('foo').once
    assertRaises(MethodCallError, flexmock_teardown)


class TestUnittestClass(flexmock_test.TestFlexmockUnittest):

  def test_unittest(self):
    a = flexmock(a=2)
    a.should_receive('a').once
    assertRaises(MethodCallError, flexmock_teardown)

########NEW FILE########
__FILENAME__ = flexmock_test
# -*- coding: utf8 -*-
from flexmock import EXACTLY
from flexmock import AT_LEAST
from flexmock import AT_MOST
from flexmock import UPDATED_ATTRS
from flexmock import Mock
from flexmock import MockBuiltinError
from flexmock import FlexmockContainer
from flexmock import FlexmockError
from flexmock import MethodSignatureError
from flexmock import ExceptionClassError
from flexmock import ExceptionMessageError
from flexmock import StateError
from flexmock import MethodCallError
from flexmock import CallOrderError
from flexmock import ReturnValue
from flexmock import flexmock_teardown
from flexmock import _format_args
from flexmock import _isproperty
import flexmock
import re
import sys
import unittest


def module_level_function(some, args):
  return "%s, %s" % (some, args)


module_level_attribute = 'test'


class OldStyleClass:
  pass


class NewStyleClass(object):
  pass


def assertRaises(exception, method, *kargs, **kwargs):
  try:
    method(*kargs, **kwargs)
  except exception:
    return
  except:
    instance = sys.exc_info()[1]
    print('%s' % instance)
  raise Exception('%s not raised' % exception.__name__)


def assertEqual(expected, received, msg=''):
  if not msg:
    msg = 'expected %s, received %s' % (expected, received)
  if expected != received:
    raise AssertionError('%s != %s : %s' % (expected, received, msg))


class RegularClass(object):

  def _tear_down(self):
    return flexmock_teardown()

  def test_flexmock_should_create_mock_object(self):
    mock = flexmock()
    assert isinstance(mock, Mock)

  def test_flexmock_should_create_mock_object_from_dict(self):
    mock = flexmock(foo='foo', bar='bar')
    assertEqual('foo',  mock.foo)
    assertEqual('bar', mock.bar)

  def test_flexmock_should_add_expectations(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo')
    assert ('method_foo' in
            [x.name for x in FlexmockContainer.flexmock_objects[mock]])

  def test_flexmock_should_return_value(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar')
    mock.should_receive('method_bar').and_return('value_baz')
    assertEqual('value_bar', mock.method_foo())
    assertEqual('value_baz', mock.method_bar())

  def test_flexmock_should_accept_shortcuts_for_creating_mock_object(self):
    mock = flexmock(attr1='value 1', attr2=lambda: 'returning 2')
    assertEqual('value 1', mock.attr1)
    assertEqual('returning 2',  mock.attr2())

  def test_flexmock_should_accept_shortcuts_for_creating_expectations(self):
    class Foo:
      def method1(self): pass
      def method2(self): pass
    foo = Foo()
    flexmock(foo, method1='returning 1', method2='returning 2')
    assertEqual('returning 1', foo.method1())
    assertEqual('returning 2', foo.method2())
    assertEqual('returning 2', foo.method2())

  def test_flexmock_expectations_returns_all(self):
    mock = flexmock(name='temp')
    assert mock not in FlexmockContainer.flexmock_objects
    mock.should_receive('method_foo')
    mock.should_receive('method_bar')
    assertEqual(2, len(FlexmockContainer.flexmock_objects[mock]))

  def test_flexmock_expectations_returns_named_expectation(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo')
    assertEqual('method_foo',
                FlexmockContainer.get_flexmock_expectation(
                     mock, 'method_foo').name)

  def test_flexmock_expectations_returns_none_if_not_found(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo')
    assert (FlexmockContainer.get_flexmock_expectation(
       mock, 'method_bar') is None)

  def test_flexmock_should_check_parameters(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').with_args('bar').and_return(1)
    mock.should_receive('method_foo').with_args('baz').and_return(2)
    assertEqual(1, mock.method_foo('bar'))
    assertEqual(2, mock.method_foo('baz'))

  def test_flexmock_should_keep_track_of_calls(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').with_args('foo').and_return(0)
    mock.should_receive('method_foo').with_args('bar').and_return(1)
    mock.should_receive('method_foo').with_args('baz').and_return(2)
    mock.method_foo('bar')
    mock.method_foo('bar')
    mock.method_foo('baz')
    expectation = FlexmockContainer.get_flexmock_expectation(
        mock, 'method_foo', ('foo',))
    assertEqual(0, expectation.times_called)
    expectation = FlexmockContainer.get_flexmock_expectation(
        mock, 'method_foo', ('bar',))
    assertEqual(2, expectation.times_called)
    expectation = FlexmockContainer.get_flexmock_expectation(
        mock, 'method_foo', ('baz',))
    assertEqual(1, expectation.times_called)

  def test_flexmock_should_set_expectation_call_numbers(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').times(1)
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertRaises(MethodCallError, expectation.verify)
    mock.method_foo()
    expectation.verify()

  def test_flexmock_should_check_raised_exceptions(self):
    mock = flexmock(name='temp')
    class FakeException(Exception):
      pass
    mock.should_receive('method_foo').and_raise(FakeException)
    assertRaises(FakeException, mock.method_foo)
    assertEqual(1,
                FlexmockContainer.get_flexmock_expectation(
                    mock, 'method_foo').times_called)

  def test_flexmock_should_check_raised_exceptions_instance_with_args(self):
    mock = flexmock(name='temp')
    class FakeException(Exception):
      def __init__(self, arg, arg2):
        pass
    mock.should_receive('method_foo').and_raise(FakeException(1, arg2=2))
    assertRaises(FakeException, mock.method_foo)
    assertEqual(1,
                FlexmockContainer.get_flexmock_expectation(
                    mock, 'method_foo').times_called)

  def test_flexmock_should_check_raised_exceptions_class_with_args(self):
    mock = flexmock(name='temp')
    class FakeException(Exception):
      def __init__(self, arg, arg2):
        pass
    mock.should_receive('method_foo').and_raise(FakeException, 1, arg2=2)
    assertRaises(FakeException, mock.method_foo)
    assertEqual(1,
                FlexmockContainer.get_flexmock_expectation(
                    mock, 'method_foo').times_called)

  def test_flexmock_should_match_any_args_by_default(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('bar')
    mock.should_receive('method_foo').with_args('baz').and_return('baz')
    assertEqual('bar', mock.method_foo())
    assertEqual('bar', mock.method_foo(1))
    assertEqual('bar', mock.method_foo('foo', 'bar'))
    assertEqual('baz', mock.method_foo('baz'))

  def test_flexmock_should_fail_to_match_exactly_no_args_when_calling_with_args(self):
    mock = flexmock()
    mock.should_receive('method_foo').with_args()
    assertRaises(MethodSignatureError, mock.method_foo, 'baz')

  def test_flexmock_should_match_exactly_no_args(self):
    class Foo:
      def bar(self): pass
    foo = Foo()
    flexmock(foo).should_receive('bar').with_args().and_return('baz')
    assertEqual('baz', foo.bar())

  def test_expectation_dot_mock_should_return_mock(self):
    mock = flexmock(name='temp')
    assertEqual(mock, mock.should_receive('method_foo').mock)

  def test_flexmock_should_create_partial_new_style_object_mock(self):
    class User(object):
      def __init__(self, name=None):
        self.name = name
      def get_name(self):
        return self.name
      def set_name(self, name):
        self.name = name
    user = User()
    flexmock(user)
    user.should_receive('get_name').and_return('john')
    user.set_name('mike')
    assertEqual('john', user.get_name())

  def test_flexmock_should_create_partial_old_style_object_mock(self):
    class User:
      def __init__(self, name=None):
        self.name = name
      def get_name(self):
        return self.name
      def set_name(self, name):
        self.name = name
    user = User()
    flexmock(user)
    user.should_receive('get_name').and_return('john')
    user.set_name('mike')
    assertEqual('john', user.get_name())

  def test_flexmock_should_create_partial_new_style_class_mock(self):
    class User(object):
      def __init__(self): pass
      def get_name(self): pass
    flexmock(User)
    User.should_receive('get_name').and_return('mike')
    user = User()
    assertEqual('mike', user.get_name())

  def test_flexmock_should_create_partial_old_style_class_mock(self):
    class User:
      def __init__(self): pass
      def get_name(self): pass
    flexmock(User)
    User.should_receive('get_name').and_return('mike')
    user = User()
    assertEqual('mike', user.get_name())

  def test_flexmock_should_match_expectations_against_builtin_classes(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').with_args(str).and_return('got a string')
    mock.should_receive('method_foo').with_args(int).and_return('got an int')
    assertEqual('got a string', mock.method_foo('string!'))
    assertEqual('got an int', mock.method_foo(23))
    assertRaises(MethodSignatureError, mock.method_foo, 2.0)

  def test_flexmock_should_match_expectations_against_user_defined_classes(self):
    mock = flexmock(name='temp')
    class Foo:
      pass
    mock.should_receive('method_foo').with_args(Foo).and_return('got a Foo')
    assertEqual('got a Foo', mock.method_foo(Foo()))
    assertRaises(MethodSignatureError, mock.method_foo, 1)

  def test_flexmock_configures_global_mocks_dict(self):
    mock = flexmock(name='temp')
    assert mock not in FlexmockContainer.flexmock_objects
    mock.should_receive('method_foo')
    assert mock in FlexmockContainer.flexmock_objects
    assertEqual(len(FlexmockContainer.flexmock_objects[mock]), 1)

  def test_flexmock_teardown_verifies_mocks(self):
    mock = flexmock(name='temp')
    mock.should_receive('verify_expectations').times(1)
    assertRaises(MethodCallError, self._tear_down)

  def test_flexmock_teardown_does_not_verify_stubs(self):
    mock = flexmock(name='temp')
    mock.should_receive('verify_expectations')
    self._tear_down()

  def test_flexmock_preserves_stubbed_object_methods_between_tests(self):
    class User:
      def get_name(self):
        return 'mike'
    user = User()
    flexmock(user).should_receive('get_name').and_return('john')
    assertEqual('john', user.get_name())
    self._tear_down()
    assertEqual('mike', user.get_name())

  def test_flexmock_preserves_stubbed_class_methods_between_tests(self):
    class User:
      def get_name(self):
        return 'mike'
    user = User()
    flexmock(User).should_receive('get_name').and_return('john')
    assertEqual('john', user.get_name())
    self._tear_down()
    assertEqual('mike', user.get_name())

  def test_flexmock_removes_new_stubs_from_objects_after_tests(self):
    class User:
      def get_name(self): pass
    user = User()
    saved = user.get_name
    flexmock(user).should_receive('get_name').and_return('john')
    assert saved != user.get_name
    assertEqual('john', user.get_name())
    self._tear_down()
    assertEqual(saved, user.get_name)

  def test_flexmock_removes_new_stubs_from_classes_after_tests(self):
    class User:
      def get_name(self): pass
    user = User()
    saved = user.get_name
    flexmock(User).should_receive('get_name').and_return('john')
    assert saved != user.get_name
    assertEqual('john', user.get_name())
    self._tear_down()
    assertEqual(saved, user.get_name)

  def test_flexmock_removes_stubs_from_multiple_objects_on_teardown(self):
    class User:
      def get_name(self): pass
    class Group:
      def get_name(self): pass
    user = User()
    group = User()
    saved1 = user.get_name
    saved2 = group.get_name
    flexmock(user).should_receive('get_name').and_return('john').once()
    flexmock(group).should_receive('get_name').and_return('john').once()
    assert saved1 != user.get_name
    assert saved2 != group.get_name
    assertEqual('john', user.get_name())
    assertEqual('john', group.get_name())
    self._tear_down()
    assertEqual(saved1, user.get_name)
    assertEqual(saved2, group.get_name)

  def test_flexmock_removes_stubs_from_multiple_classes_on_teardown(self):
    class User:
      def get_name(self): pass
    class Group:
      def get_name(self): pass
    user = User()
    group = User()
    saved1 = user.get_name
    saved2 = group.get_name
    flexmock(User).should_receive('get_name').and_return('john')
    flexmock(Group).should_receive('get_name').and_return('john')
    assert saved1 != user.get_name
    assert saved2 != group.get_name
    assertEqual('john', user.get_name())
    assertEqual('john', group.get_name())
    self._tear_down()
    assertEqual(saved1, user.get_name)
    assertEqual(saved2, group.get_name)

  def test_flexmock_respects_at_least_when_called_less_than_requested(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('bar').at_least().twice()
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(AT_LEAST, expectation.modifier)
    mock.method_foo()
    assertRaises(MethodCallError, self._tear_down)

  def test_flexmock_respects_at_least_when_called_requested_number(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar').at_least().once()
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(AT_LEAST, expectation.modifier)
    mock.method_foo()
    self._tear_down()

  def test_flexmock_respects_at_least_when_called_more_than_requested(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar').at_least().once()
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(AT_LEAST, expectation.modifier)
    mock.method_foo()
    mock.method_foo()
    self._tear_down()

  def test_flexmock_respects_at_most_when_called_less_than_requested(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('bar').at_most().twice()
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(AT_MOST, expectation.modifier)
    mock.method_foo()
    self._tear_down()

  def test_flexmock_respects_at_most_when_called_requested_number(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar').at_most().once()
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(AT_MOST, expectation.modifier)
    mock.method_foo()
    self._tear_down()

  def test_flexmock_respects_at_most_when_called_more_than_requested(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar').at_most().once()
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(AT_MOST, expectation.modifier)
    mock.method_foo()
    assertRaises(MethodCallError, mock.method_foo)

  def test_flexmock_treats_once_as_times_one(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar').once()
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(1, expectation.expected_calls[EXACTLY])
    assertRaises(MethodCallError, self._tear_down)

  def test_flexmock_treats_twice_as_times_two(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').twice().and_return('value_bar')
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(2, expectation.expected_calls[EXACTLY])
    assertRaises(MethodCallError, self._tear_down)

  def test_flexmock_works_with_never_when_true(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar').never
    expectation = FlexmockContainer.get_flexmock_expectation(mock, 'method_foo')
    assertEqual(0, expectation.expected_calls[EXACTLY])
    self._tear_down()

  def test_flexmock_works_with_never_when_false(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').and_return('value_bar').never
    assertRaises(MethodCallError, mock.method_foo)
  
  def test_flexmock_get_flexmock_expectation_should_work_with_args(self):
    mock = flexmock(name='temp')
    mock.should_receive('method_foo').with_args('value_bar')
    assert FlexmockContainer.get_flexmock_expectation(
        mock, 'method_foo', 'value_bar')

  def test_flexmock_function_should_return_previously_mocked_object(self):
    class User(object): pass
    user = User()
    foo = flexmock(user)
    assert foo == user
    assert foo == flexmock(user)

  def test_flexmock_should_not_return_class_object_if_mocking_instance(self):
    class User:
      def method(self): pass
    user = User()
    user2 = User()
    class_mock = flexmock(User).should_receive(
        'method').and_return('class').mock
    user_mock = flexmock(user).should_receive(
        'method').and_return('instance').mock
    assert class_mock is not user_mock
    assertEqual('instance', user.method())
    assertEqual('class', user2.method())

  def test_should_call_on_class_mock(self):
    class User:
      def foo(self): return 'class'
    user1 = User()
    user2 = User()
    flexmock(User).should_call('foo').once()
    assertRaises(MethodCallError, self._tear_down)
    flexmock(User).should_call('foo').twice()
    assertEqual('class', user1.foo())
    assertEqual('class', user2.foo())

  def test_flexmock_should_not_blow_up_on_should_call_for_class_methods(self):
    class User:
      @classmethod
      def foo(self):
        return 'class'
    flexmock(User).should_call('foo')
    assertEqual('class', User.foo())

  def test_flexmock_should_not_blow_up_on_should_call_for_static_methods(self):
    class User:
      @staticmethod
      def foo():
        return 'static'
    flexmock(User).should_call('foo')
    assertEqual('static', User.foo())

  def test_flexmock_should_mock_new_instances_with_multiple_params(self):
    class User(object): pass
    class Group(object):
      def __init__(self, arg, arg2):
        pass
    user = User()
    flexmock(Group).new_instances(user)
    assert user is Group(1, 2)

  def test_flexmock_should_revert_new_instances_on_teardown(self):
    class User(object): pass
    class Group(object): pass
    user = User()
    group = Group()
    flexmock(Group).new_instances(user)
    assert user is Group()
    self._tear_down()
    assertEqual(group.__class__, Group().__class__)

  def test_flexmock_should_cleanup_added_methods_and_attributes(self):
    class Group(object): pass
    group = Group()
    flexmock(Group)
    assert 'should_receive' in Group.__dict__
    assert 'should_receive' not in group.__dict__
    flexmock(group)
    assert 'should_receive' in group.__dict__
    self._tear_down()
    for method in UPDATED_ATTRS:
      assert method not in Group.__dict__
      assert method not in group.__dict__

  def test_flexmock_should_cleanup_after_exception(self):
    class User:
      def method2(self): pass
    class Group:
      def method1(self): pass
    flexmock(Group)
    flexmock(User)
    Group.should_receive('method1').once()
    User.should_receive('method2').once()
    assertRaises(MethodCallError, self._tear_down)
    for method in UPDATED_ATTRS:
      assert method not in dir(Group)
    for method in UPDATED_ATTRS:
      assert method not in dir(User)

  def test_flexmock_should_call_respects_matched_expectations(self):
    class Group(object):
      def method1(self, arg1, arg2='b'):
        return '%s:%s' % (arg1, arg2)
      def method2(self, arg):
        return arg
    group = Group()
    flexmock(group).should_call('method1').twice()
    assertEqual('a:c', group.method1('a', arg2='c'))
    assertEqual('a:b', group.method1('a'))
    group.should_call('method2').once().with_args('c')
    assertEqual('c', group.method2('c'))
    self._tear_down()

  def test_flexmock_should_call_respects_unmatched_expectations(self):
    class Group(object):
      def method1(self, arg1, arg2='b'):
        return '%s:%s' % (arg1, arg2)
      def method2(self, a): pass
    group = Group()
    flexmock(group).should_call('method1').at_least().once()
    assertRaises(MethodCallError, self._tear_down)
    flexmock(group)
    group.should_call('method2').with_args('a').once()
    group.should_receive('method2').with_args('not a')
    group.method2('not a')
    assertRaises(MethodCallError, self._tear_down)

  def test_flexmock_doesnt_error_on_properly_ordered_expectations(self):
    class Foo(object):
      def foo(self): pass
      def method1(self, a): pass
      def bar(self): pass
      def baz(self): pass
    foo = Foo()
    flexmock(foo).should_receive('foo')
    flexmock(foo).should_receive('method1').with_args('a').ordered()
    flexmock(foo).should_receive('bar')
    flexmock(foo).should_receive('method1').with_args('b').ordered()
    flexmock(foo).should_receive('baz')
    foo.bar()
    foo.method1('a')
    foo.method1('b')
    foo.baz()
    foo.foo()

  def test_flexmock_errors_on_improperly_ordered_expectations(self):
    class Foo(object):
      def method1(self, a): pass
    foo = Foo()
    flexmock(foo)
    foo.should_receive('method1').with_args('a').ordered()
    foo.should_receive('method1').with_args('b').ordered()
    assertRaises(CallOrderError, foo.method1, 'b')

  def test_flexmock_should_accept_multiple_return_values(self):
    class Foo:
      def method1(self): pass
    foo = Foo()
    flexmock(foo).should_receive('method1').and_return(1, 5).and_return(2)
    assertEqual((1, 5), foo.method1())
    assertEqual(2, foo.method1())
    assertEqual((1, 5), foo.method1())
    assertEqual(2, foo.method1())

  def test_flexmock_should_accept_multiple_return_values_with_shortcut(self):
    class Foo:
      def method1(self): pass
    foo = Foo()
    flexmock(foo).should_receive('method1').and_return(1, 2).one_by_one()
    assertEqual(1, foo.method1())
    assertEqual(2, foo.method1())
    assertEqual(1, foo.method1())
    assertEqual(2, foo.method1())

  def test_flexmock_should_mix_multiple_return_values_with_exceptions(self):
    class Foo:
      def method1(self): pass
    foo = Foo()
    flexmock(foo).should_receive('method1').and_return(1).and_raise(Exception)
    assertEqual(1, foo.method1())
    assertRaises(Exception, foo.method1)
    assertEqual(1, foo.method1())
    assertRaises(Exception, foo.method1)

  def test_flexmock_should_match_types_on_multiple_arguments(self):
    class Foo:
      def method1(self, a, b): pass
    foo = Foo()
    flexmock(foo).should_receive('method1').with_args(str, int).and_return('ok')
    assertEqual('ok', foo.method1('some string', 12))
    assertRaises(MethodSignatureError, foo.method1, 12, 32)
    flexmock(foo).should_receive('method1').with_args(str, int).and_return('ok')
    assertRaises(MethodSignatureError, foo.method1, 12, 'some string')
    flexmock(foo).should_receive('method1').with_args(str, int).and_return('ok')
    assertRaises(MethodSignatureError, foo.method1, 'string', 12, 14)

  def test_flexmock_should_match_types_on_multiple_arguments_generic(self):
    class Foo:
      def method1(self, a, b, c): pass
    foo = Foo()
    flexmock(foo).should_receive('method1').with_args(
        object, object, object).and_return('ok')
    assertEqual('ok', foo.method1('some string', None, 12))
    assertEqual('ok', foo.method1((1,), None, 12))
    assertEqual('ok', foo.method1(12, 14, []))
    assertEqual('ok', foo.method1('some string', 'another one', False))
    assertRaises(MethodSignatureError, foo.method1, 'string', 12)
    flexmock(foo).should_receive('method1').with_args(
        object, object, object).and_return('ok')
    assertRaises(MethodSignatureError, foo.method1, 'string', 12, 13, 14)

  def test_flexmock_should_match_types_on_multiple_arguments_classes(self):
    class Foo:
      def method1(self, a, b): pass
    class Bar: pass
    foo = Foo()
    bar = Bar()
    flexmock(foo).should_receive('method1').with_args(
        object, Bar).and_return('ok')
    assertEqual('ok', foo.method1('some string', bar))
    assertRaises(MethodSignatureError, foo.method1, bar, 'some string')
    flexmock(foo).should_receive('method1').with_args(
        object, Bar).and_return('ok')
    assertRaises(MethodSignatureError, foo.method1, 12, 'some string')

  def test_flexmock_should_match_keyword_arguments(self):
    class Foo:
      def method1(self, a, **kwargs): pass
    foo = Foo()
    flexmock(foo).should_receive('method1').with_args(1, arg3=3, arg2=2).twice()
    foo.method1(1, arg2=2, arg3=3)
    foo.method1(1, arg3=3, arg2=2)
    self._tear_down()
    flexmock(foo).should_receive('method1').with_args(1, arg3=3, arg2=2)
    assertRaises(MethodSignatureError, foo.method1, arg2=2, arg3=3)
    flexmock(foo).should_receive('method1').with_args(1, arg3=3, arg2=2)
    assertRaises(MethodSignatureError, foo.method1, 1, arg2=2, arg3=4)
    flexmock(foo).should_receive('method1').with_args(1, arg3=3, arg2=2)
    assertRaises(MethodSignatureError, foo.method1, 1)

  def test_flexmock_should_call_should_match_keyword_arguments(self):
    class Foo:
      def method1(self, arg1, arg2=None, arg3=None):
        return '%s%s%s' % (arg1, arg2, arg3)
    foo = Foo()
    flexmock(foo).should_call('method1').with_args(1, arg3=3, arg2=2).once()
    assertEqual('123', foo.method1(1, arg2=2, arg3=3))

  def test_flexmock_should_mock_private_methods(self):
    class Foo:
      def __private_method(self):
        return 'foo'
      def public_method(self):
        return self.__private_method()
    foo = Foo()
    flexmock(foo).should_receive('__private_method').and_return('bar')
    assertEqual('bar', foo.public_method())

  def test_flexmock_should_mock_special_methods(self):
    class Foo:
      def __special_method__(self):
        return 'foo'
      def public_method(self):
        return self.__special_method__()
    foo = Foo()
    flexmock(foo).should_receive('__special_method__').and_return('bar')
    assertEqual('bar', foo.public_method())

  def test_flexmock_should_mock_double_underscore_method(self):
    class Foo:
      def __(self):
        return 'foo'
      def public_method(self):
        return self.__()
    foo = Foo()
    flexmock(foo).should_receive('__').and_return('bar')
    assertEqual('bar', foo.public_method())

  def test_flexmock_should_mock_private_class_methods(self):
    class Foo:
      def __iter__(self): pass
    flexmock(Foo).should_receive('__iter__').and_yield(1, 2, 3)
    assertEqual([1, 2, 3], [x for x in Foo()])

  def test_flexmock_should_mock_iter_on_new_style_instances(self):
    class Foo(object):
      def __iter__(self):
        yield None
    old = Foo.__iter__
    foo = Foo()
    foo2 = Foo()
    foo3 = Foo()
    flexmock(foo, __iter__=iter([1, 2, 3]))
    flexmock(foo2, __iter__=iter([3, 4, 5]))
    assertEqual([1, 2, 3], [x for x in foo])
    assertEqual([3, 4, 5], [x for x in foo2])
    assertEqual([None], [x for x in foo3])
    assertEqual(False, foo.__iter__ == old)
    assertEqual(False, foo2.__iter__ == old)
    assertEqual(False, foo3.__iter__ == old)
    self._tear_down()
    assertEqual([None], [x for x in foo])
    assertEqual([None], [x for x in foo2])
    assertEqual([None], [x for x in foo3])
    assertEqual(True, Foo.__iter__ == old, '%s != %s' % (Foo.__iter__, old))

  def test_flexmock_should_mock_private_methods_with_leading_underscores(self):
    class _Foo:
      def __stuff(self): pass
      def public_method(self):
        return self.__stuff()
    foo = _Foo()
    flexmock(foo).should_receive('__stuff').and_return('bar')
    assertEqual('bar', foo.public_method())

  def test_flexmock_should_mock_generators(self):
    class Gen:
      def foo(self): pass
    gen = Gen()
    flexmock(gen).should_receive('foo').and_yield(*range(1, 10))
    output = [val for val in gen.foo()]
    assertEqual([val for val in range(1, 10)], output)

  def test_flexmock_should_verify_correct_spy_return_values(self):
    class User:
      def get_stuff(self): return 'real', 'stuff'
    user = User()
    flexmock(user).should_call('get_stuff').and_return('real', 'stuff')
    assertEqual(('real', 'stuff'), user.get_stuff())

  def test_flexmock_should_verify_correct_spy_regexp_return_values(self):
    class User:
      def get_stuff(self): return 'real', 'stuff'
    user = User()
    flexmock(user).should_call('get_stuff').and_return(
        re.compile('ea.*'), re.compile('^stuff$'))
    assertEqual(('real', 'stuff'), user.get_stuff())

  def test_flexmock_should_verify_spy_raises_correct_exception_class(self):
    class FakeException(Exception):
      def __init__(self, param, param2):
        self.message = '%s, %s' % (param, param2)
        Exception.__init__(self)
    class User:
      def get_stuff(self): raise FakeException(1, 2)
    user = User()
    flexmock(user).should_call('get_stuff').and_raise(FakeException, 1, 2)
    user.get_stuff()

  def test_flexmock_should_verify_spy_matches_exception_message(self):
    class FakeException(Exception):
      def __init__(self, param, param2):
        self.p1 = param
        self.p2 = param2
        Exception.__init__(self, param)
      def __str__(self):
        return '%s, %s' % (self.p1, self.p2)
    class User:
      def get_stuff(self): raise FakeException('1', '2')
    user = User()
    flexmock(user).should_call('get_stuff').and_raise(FakeException, '2', '1')
    assertRaises(ExceptionMessageError, user.get_stuff)

  def test_flexmock_should_verify_spy_matches_exception_regexp(self):
    class User:
      def get_stuff(self): raise Exception('123asdf345')
    user = User()
    flexmock(user).should_call(
        'get_stuff').and_raise(Exception, re.compile('asdf'))
    user.get_stuff()
    self._tear_down()

  def test_flexmock_should_verify_spy_matches_exception_regexp_mismatch(self):
    class User:
      def get_stuff(self): raise Exception('123asdf345')
    user = User()
    flexmock(user).should_call(
        'get_stuff').and_raise(Exception, re.compile('^asdf'))
    assertRaises(ExceptionMessageError, user.get_stuff)

  def test_flexmock_should_blow_up_on_wrong_spy_exception_type(self):
    class User:
      def get_stuff(self): raise CallOrderError('foo')
    user = User()
    flexmock(user).should_call('get_stuff').and_raise(MethodCallError)
    assertRaises(ExceptionClassError, user.get_stuff)

  def test_flexmock_should_match_spy_exception_parent_type(self):
    class User:
      def get_stuff(self): raise CallOrderError('foo')
    user = User()
    flexmock(user).should_call('get_stuff').and_raise(FlexmockError)
    user.get_stuff()

  def test_flexmock_should_blow_up_on_wrong_spy_return_values(self):
    class User:
      def get_stuff(self): return 'real', 'stuff'
      def get_more_stuff(self): return 'other', 'stuff'
    user = User()
    flexmock(user).should_call('get_stuff').and_return('other', 'stuff')
    assertRaises(MethodSignatureError, user.get_stuff)
    flexmock(user).should_call('get_more_stuff').and_return()
    assertRaises(MethodSignatureError, user.get_more_stuff)

  def test_flexmock_should_mock_same_class_twice(self):
    class Foo: pass
    flexmock(Foo)
    flexmock(Foo)

  def test_flexmock_spy_should_not_clobber_original_method(self):
    class User:
      def get_stuff(self): return 'real', 'stuff'
    user = User()
    flexmock(user).should_call('get_stuff')
    flexmock(user).should_call('get_stuff')
    assertEqual(('real', 'stuff'), user.get_stuff())

  def test_flexmock_should_properly_restore_static_methods(self):
    class User:
      @staticmethod
      def get_stuff(): return 'ok!'
    assertEqual('ok!', User.get_stuff())
    flexmock(User).should_receive('get_stuff')
    assert User.get_stuff() is None
    self._tear_down()
    assertEqual('ok!', User.get_stuff())

  def test_flexmock_should_properly_restore_undecorated_static_methods(self):
    class User:
      def get_stuff(): return 'ok!'
      get_stuff = staticmethod(get_stuff)
    assertEqual('ok!', User.get_stuff())
    flexmock(User).should_receive('get_stuff')
    assert User.get_stuff() is None
    self._tear_down()
    assertEqual('ok!', User.get_stuff())

  def test_flexmock_should_properly_restore_module_level_functions(self):
    if 'flexmock_test' in sys.modules:
      mod = sys.modules['flexmock_test']
    else:
      mod = sys.modules['__main__']
    flexmock(mod).should_receive('module_level_function').with_args(1, 2)
    assertEqual(None,  module_level_function(1, 2))
    self._tear_down()
    assertEqual('1, 2', module_level_function(1, 2))

  def test_flexmock_should_support_mocking_old_style_classes_as_functions(self):
    if 'flexmock_test' in sys.modules:
      mod = sys.modules['flexmock_test']
    else:
      mod = sys.modules['__main__']
    flexmock(mod).should_receive('OldStyleClass').and_return('yay')
    assertEqual('yay', OldStyleClass())

  def test_flexmock_should_support_mocking_new_style_classes_as_functions(self):
    if 'flexmock_test' in sys.modules:
      mod = sys.modules['flexmock_test']
    else:
      mod = sys.modules['__main__']
    flexmock(mod).should_receive('NewStyleClass').and_return('yay')
    assertEqual('yay', NewStyleClass())

  def test_flexmock_should_properly_restore_class_methods(self):
    class User:
      @classmethod
      def get_stuff(cls):
        return cls.__name__
    assertEqual('User', User.get_stuff())
    flexmock(User).should_receive('get_stuff').and_return('foo')
    assertEqual('foo', User.get_stuff())
    self._tear_down()
    assertEqual('User', User.get_stuff())

  def test_spy_should_match_return_value_class(self):
    class User: pass
    user = User()
    foo = flexmock(foo=lambda: ('bar', 'baz'),
                   bar=lambda: user,
                   baz=lambda: None,
                   bax=lambda: None)
    foo.should_call('foo').and_return(str, str)
    foo.should_call('bar').and_return(User)
    foo.should_call('baz').and_return(object)
    foo.should_call('bax').and_return(None)
    assertEqual(('bar', 'baz'), foo.foo())
    assertEqual(user, foo.bar())
    assertEqual(None, foo.baz())
    assertEqual(None, foo.bax())

  def test_spy_should_not_match_falsy_stuff(self):
    class Foo:
      def foo(self): return None
      def bar(self): return False
      def baz(self): return []
      def quux(self): return ''
    foo = Foo()
    flexmock(foo).should_call('foo').and_return('bar').once
    flexmock(foo).should_call('bar').and_return('bar').once
    flexmock(foo).should_call('baz').and_return('bar').once
    flexmock(foo).should_call('quux').and_return('bar').once
    assertRaises(FlexmockError, foo.foo)
    assertRaises(FlexmockError, foo.bar)
    assertRaises(FlexmockError, foo.baz)
    assertRaises(FlexmockError, foo.quux)

  def test_new_instances_should_blow_up_on_should_receive(self):
    class User(object): pass
    mock = flexmock(User).new_instances(None).mock
    assertRaises(FlexmockError, mock.should_receive, 'foo')

  def test_should_call_alias_should_create_a_spy(self):
    class Foo:
      def get_stuff(self):
        return 'yay'
    foo = Foo()
    flexmock(foo).should_call('get_stuff').and_return('yay').once()
    assertRaises(MethodCallError, self._tear_down)

  def test_flexmock_should_fail_mocking_nonexistent_methods(self):
    class User: pass
    user = User()
    assertRaises(FlexmockError,
                 flexmock(user).should_receive, 'nonexistent')

  def test_flexmock_should_not_explode_on_unicode_formatting(self):
    if sys.version_info >= (3, 0):
      formatted = _format_args(
          'method', {'kargs' : (chr(0x86C7),), 'kwargs' : {}})
      assertEqual('method("蛇")', formatted)
    else:
      formatted = _format_args(
          'method', {'kargs' : (unichr(0x86C7),), 'kwargs' : {}})
      assertEqual('method("%s")' % unichr(0x86C7), formatted)

  def test_return_value_should_not_explode_on_unicode_values(self):
    class Foo:
      def method(self): pass
    if sys.version_info >= (3, 0):
      return_value = ReturnValue(chr(0x86C7))
      assertEqual('"蛇"', '%s' % return_value)
      return_value = ReturnValue((chr(0x86C7), chr(0x86C7)))
      assertEqual('("蛇", "蛇")', '%s' % return_value)
    else:
      return_value = ReturnValue(unichr(0x86C7))
      assertEqual('"%s"' % unichr(0x86C7), unicode(return_value))

  def test_pass_thru_should_call_original_method_only_once(self):
    class Nyan(object):
      def __init__(self):
          self.n = 0
      def method(self):
          self.n += 1
    obj = Nyan()
    flexmock(obj)
    obj.should_call('method')
    obj.method()
    assertEqual(obj.n, 1)
  
  def test_should_call_works_for_same_method_with_different_args(self):
    class Foo:
      def method(self, arg):
        pass
    foo = Foo()
    flexmock(foo).should_call('method').with_args('foo').once()
    flexmock(foo).should_call('method').with_args('bar').once()
    foo.method('foo')
    foo.method('bar')
    self._tear_down()

  def test_should_call_fails_properly_for_same_method_with_different_args(self):
    class Foo:
      def method(self, arg):
        pass
    foo = Foo()
    flexmock(foo).should_call('method').with_args('foo').once()
    flexmock(foo).should_call('method').with_args('bar').once()
    foo.method('foo')
    assertRaises(MethodCallError, self._tear_down)

  def test_should_give_reasonable_error_for_builtins(self):
    assertRaises(MockBuiltinError, flexmock, object)

  def test_should_give_reasonable_error_for_instances_of_builtins(self):
    assertRaises(MockBuiltinError, flexmock, object())

  def test_mock_chained_method_calls_works_with_one_level(self):
    class Foo:
      def method2(self):
        return 'foo'
    class Bar:
      def method1(self):
        return Foo()
    foo = Bar()
    assertEqual('foo', foo.method1().method2())
    flexmock(foo).should_receive('method1.method2').and_return('bar')
    assertEqual('bar', foo.method1().method2())

  def test_mock_chained_method_supports_args_and_mocks(self):
    class Foo:
      def method2(self, arg):
        return arg
    class Bar:
      def method1(self):
        return Foo()
    foo = Bar()
    assertEqual('foo', foo.method1().method2('foo'))
    flexmock(foo).should_receive('method1.method2').with_args(
        'foo').and_return('bar').once()
    assertEqual('bar', foo.method1().method2('foo'))
    self._tear_down()
    flexmock(foo).should_receive('method1.method2').with_args(
        'foo').and_return('bar').once()
    assertRaises(MethodCallError, self._tear_down)

  def test_mock_chained_method_calls_works_with_more_than_one_level(self):
    class Baz:
      def method3(self):
        return 'foo'
    class Foo:
      def method2(self):
        return Baz()
    class Bar:
      def method1(self):
        return Foo()
    foo = Bar()
    assertEqual('foo', foo.method1().method2().method3())
    flexmock(foo).should_receive('method1.method2.method3').and_return('bar')
    assertEqual('bar', foo.method1().method2().method3())

  def test_flexmock_should_replace_method(self):
    class Foo:
      def method(self, arg):
        return arg
    foo = Foo()
    flexmock(foo).should_receive('method').replace_with(lambda x: x == 5)
    assertEqual(foo.method(5), True)
    assertEqual(foo.method(4), False)

  def test_flexmock_should_replace_cannot_be_specified_twice(self):
    class Foo:
      def method(self, arg):
        return arg
    foo = Foo()
    expectation = flexmock(foo).should_receive(
        'method').replace_with(lambda x: x == 5)
    assertRaises(FlexmockError,
                 expectation.replace_with, lambda x: x == 3)

  def test_flexmock_should_mock_the_same_method_multiple_times(self):
    class Foo:
      def method(self): pass
    foo = Foo()
    flexmock(foo).should_receive('method').and_return(1)
    assertEqual(foo.method(), 1)
    flexmock(foo).should_receive('method').and_return(2)
    assertEqual(foo.method(), 2)
    flexmock(foo).should_receive('method').and_return(3)
    assertEqual(foo.method(), 3)
    flexmock(foo).should_receive('method').and_return(4)
    assertEqual(foo.method(), 4)

  def test_new_instances_should_be_a_method(self):
    class Foo(object): pass
    flexmock(Foo).new_instances('bar')
    assertEqual('bar', Foo())
    self._tear_down()
    assert 'bar' != Foo()

  def test_new_instances_raises_error_when_not_a_class(self):
    class Foo(object): pass
    foo = Foo()
    flexmock(foo)
    assertRaises(FlexmockError, foo.new_instances, 'bar')

  def test_new_instances_works_with_multiple_return_values(self):
    class Foo(object): pass
    flexmock(Foo).new_instances('foo', 'bar')
    assertEqual('foo', Foo())
    assertEqual('bar', Foo())

  def test_should_receive_should_not_replace_flexmock_methods(self):
    class Foo:
      def bar(self): pass
    foo = Foo()
    flexmock(foo)
    assertRaises(FlexmockError, foo.should_receive, 'should_receive')

  def test_flexmock_should_not_add_methods_if_they_already_exist(self):
    class Foo:
      def should_receive(self):
        return 'real'
      def bar(self): pass
    foo = Foo()
    mock = flexmock(foo)
    assertEqual(foo.should_receive(), 'real')
    assert 'should_call' not in dir(foo)
    assert 'new_instances' not in dir(foo)
    mock.should_receive('bar').and_return('baz')
    assertEqual(foo.bar(), 'baz')
    self._tear_down()
    assertEqual(foo.should_receive(), 'real')

  def test_flexmock_should_not_add_class_methods_if_they_already_exist(self):
    class Foo:
      def should_receive(self):
        return 'real'
      def bar(self): pass
    foo = Foo()
    mock = flexmock(Foo)
    assertEqual(foo.should_receive(), 'real')
    assert 'should_call' not in dir(Foo)
    assert 'new_instances' not in dir(Foo)
    mock.should_receive('bar').and_return('baz')
    assertEqual(foo.bar(), 'baz')
    self._tear_down()
    assertEqual(foo.should_receive(), 'real')

  def test_expectation_properties_work_with_parens(self):
    foo = flexmock().should_receive(
        'bar').at_least().once().and_return('baz').mock()
    assertEqual('baz', foo.bar())

  def test_mocking_down_the_inheritance_chain_class_to_class(self):
    class Parent(object):
      def foo(self): pass
    class Child(Parent):
      def bar(self): pass

    flexmock(Parent).should_receive('foo').and_return('outer')
    flexmock(Child).should_receive('bar').and_return('inner')
    assert 'outer', Parent().foo()
    assert 'inner', Child().bar()

  def test_arg_matching_works_with_regexp(self):
    class Foo:
      def foo(self, arg1, arg2): pass
    foo = Foo()
    flexmock(foo).should_receive('foo').with_args(
        re.compile('^arg1.*asdf$'), arg2=re.compile('f')).and_return('mocked')
    assertEqual('mocked', foo.foo('arg1somejunkasdf', arg2='aadsfdas'))

  def test_arg_matching_with_regexp_fails_when_regexp_doesnt_match_karg(self):
    class Foo:
      def foo(self, arg1, arg2): pass
    foo = Foo()
    flexmock(foo).should_receive('foo').with_args(
        re.compile('^arg1.*asdf$'), arg2=re.compile('a')).and_return('mocked')
    assertRaises(MethodSignatureError, foo.foo, 'arg1somejunkasdfa', arg2='a')

  def test_arg_matching_with_regexp_fails_when_regexp_doesnt_match_kwarg(self):
    class Foo:
      def foo(self, arg1, arg2): pass
    foo = Foo()
    flexmock(foo).should_receive('foo').with_args(
        re.compile('^arg1.*asdf$'), arg2=re.compile('a')).and_return('mocked')
    assertRaises(MethodSignatureError, foo.foo, 'arg1somejunkasdf', arg2='b')

  def test_flexmock_class_returns_same_object_on_repeated_calls(self):
    class Foo: pass
    a = flexmock(Foo)
    b = flexmock(Foo)
    assertEqual(a, b)

  def test_flexmock_object_returns_same_object_on_repeated_calls(self):
    class Foo: pass
    foo = Foo()
    a = flexmock(foo)
    b = flexmock(foo)
    assertEqual(a, b)

  def test_flexmock_ordered_worked_after_default_stub(self):
    foo = flexmock()
    foo.should_receive('bar')
    foo.should_receive('bar').with_args('a').ordered()
    foo.should_receive('bar').with_args('b').ordered()
    assertRaises(CallOrderError, foo.bar, 'b')

  def test_state_machine(self):
    class Radio:
      def __init__(self): self.is_on = False
      def switch_on(self): self.is_on = True
      def switch_off(self): self.is_on = False
      def select_channel(self): return None
      def adjust_volume(self, num): self.volume = num

    radio = Radio()
    flexmock(radio)
    radio.should_receive('select_channel').once().when(
        lambda: radio.is_on)
    radio.should_call('adjust_volume').once().with_args(5).when(
        lambda: radio.is_on)

    assertRaises(StateError, radio.select_channel)
    assertRaises(StateError, radio.adjust_volume, 5)
    radio.is_on = True
    radio.select_channel()
    radio.adjust_volume(5)

  def test_support_at_least_and_at_most_together(self):
    class Foo:
      def bar(self): pass

    foo = Foo()
    flexmock(foo).should_call('bar').at_least().once().at_most().twice()
    assertRaises(MethodCallError, self._tear_down)

    flexmock(foo).should_call('bar').at_least().once().at_most().twice()
    foo.bar()
    foo.bar()
    assertRaises(MethodCallError, foo.bar)

    flexmock(foo).should_call('bar').at_least().once().at_most().twice()
    foo.bar()
    self._tear_down()

    flexmock(foo).should_call('bar').at_least().once().at_most().twice()
    foo.bar()
    foo.bar()
    self._tear_down()

  def test_at_least_cannot_be_used_twice(self):
    class Foo:
      def bar(self): pass

    expectation = flexmock(Foo).should_receive('bar')
    try:
      expectation.at_least().at_least()
      raise Exception('should not be able to specify at_least twice')
    except FlexmockError:
      pass
    except Exception:
      raise

  def test_at_most_cannot_be_used_twice(self):
    class Foo:
      def bar(self): pass

    expectation = flexmock(Foo).should_receive('bar')
    try:
      expectation.at_most().at_most()
      raise Exception('should not be able to specify at_most twice')
    except FlexmockError:
      pass
    except Exception:
      raise

  def test_at_least_cannot_be_specified_until_at_most_is_set(self):
    class Foo:
      def bar(self): pass

    expectation = flexmock(Foo).should_receive('bar')
    try:
      expectation.at_least().at_most()
      raise Exception('should not be able to specify at_most if at_least unset')
    except FlexmockError:
      pass
    except Exception:
      raise

  def test_at_most_cannot_be_specified_until_at_least_is_set(self):
    class Foo:
      def bar(self): pass

    expectation = flexmock(Foo).should_receive('bar')
    try:
      expectation.at_most().at_least()
      raise Exception('should not be able to specify at_least if at_most unset')
    except FlexmockError:
      pass
    except Exception:
      raise

  def test_proper_reset_of_subclass_methods(self):
    class A:
      def x(self):
        return 'a'
    class B(A):
      def x(self):
        return 'b'
    flexmock(B).should_receive('x').and_return('1')
    self._tear_down()
    assertEqual('b', B().x())

  def test_format_args_supports_tuples(self):
    formatted = _format_args('method', {'kargs' : ((1, 2),), 'kwargs' : {}})
    assertEqual('method((1, 2))', formatted)

  def test_mocking_subclass_of_str(self):
    class String(str): pass
    s = String()
    flexmock(s, endswith='fake')
    assertEqual('fake', s.endswith('stuff'))
    self._tear_down()
    assertEqual(False, s.endswith('stuff'))

  def test_ordered_on_different_methods(self):
    class String(str): pass
    s = String('abc')
    flexmock(s)
    s.should_call('startswith').with_args('asdf').ordered()
    s.should_call('endswith').ordered()
    assertRaises(CallOrderError, s.endswith, 'c')

  def test_fake_object_takes_properties(self):
    foo = flexmock(bar=property(lambda self: 'baz'))
    bar = flexmock(foo=property(lambda self: 'baz'))
    assertEqual('baz', foo.bar)
    assertEqual('baz', bar.foo)

  def test_replace_non_callable_class_attributes(self):
    class Foo:
      bar = 1
    foo = Foo()
    bar = Foo()
    flexmock(foo, bar=2)
    assertEqual(2, foo.bar)
    assertEqual(1, bar.bar)
    self._tear_down()
    assertEqual(1, foo.bar)

  def test_should_chain_attributes(self):
    class Baz:
      x = 1
    class Bar:
      baz = Baz()
    class Foo:
      bar = Bar()

    foo = Foo()
    foo = flexmock(foo)
    foo.should_receive('bar.baz.x').and_return(2)
    assertEqual(2, foo.bar.baz.x)
    self._tear_down()
    assertEqual(1, foo.bar.baz.x)

  def test_replace_non_callable_instance_attributes(self):
    class Foo:
      def __init__(self):
        self.bar = 1
    foo = Foo()
    bar = Foo()
    flexmock(foo, bar=2)
    flexmock(bar, bar=1)
    assertEqual(2, foo.bar)
    self._tear_down()
    assertEqual(1, foo.bar)

  def test_replace_non_callable_module_attributes(self):
    if 'flexmock_test' in sys.modules:
      mod = sys.modules['flexmock_test']
    else:
      mod = sys.modules['__main__']
    flexmock(mod, module_level_attribute='yay')
    assertEqual('yay',  module_level_attribute)
    self._tear_down()
    assertEqual('test', module_level_attribute)

  def test_non_callable_attributes_fail_to_set_expectations(self):
    class Foo:
      bar = 1
    foo = Foo()
    e = flexmock(foo).should_receive('bar').and_return(2)
    assertRaises(FlexmockError, e.times, 1)
    assertRaises(FlexmockError, e.with_args, ())
    assertRaises(FlexmockError, e.replace_with, lambda x: x)
    assertRaises(FlexmockError, e.and_raise, Exception)
    assertRaises(FlexmockError, e.when, lambda x: x)
    assertRaises(FlexmockError, e.and_yield, 1)
    assertRaises(FlexmockError, object.__getattribute__(e, 'ordered'))
    assertRaises(FlexmockError, object.__getattribute__(e, 'at_least'))
    assertRaises(FlexmockError, object.__getattribute__(e, 'at_most'))
    assertRaises(FlexmockError, object.__getattribute__(e, 'one_by_one'))

  def test_and_return_defaults_to_none_with_no_arguments(self):
    foo = flexmock()
    foo.should_receive('bar').and_return()
    assertEqual(None, foo.bar())

  def test_should_replace_attributes_that_are_instances_of_classes(self):
    class Foo(object):
      pass
    class Bar(object):
      foo = Foo()
    bar = Bar()
    flexmock(bar, foo='test')
    assertEqual('test', bar.foo)

  def test_isproperty(self):
    class Foo:
      @property
      def bar(self): pass
      def baz(self): pass
    class Bar(Foo): pass
    foo = Foo()
    bar = Bar()
    assertEqual(True, _isproperty(foo, 'bar'))
    assertEqual(False, _isproperty(foo, 'baz'))
    assertEqual(True, _isproperty(Foo, 'bar'))
    assertEqual(False, _isproperty(Foo, 'baz'))
    assertEqual(True, _isproperty(bar, 'bar'))
    assertEqual(False, _isproperty(bar, 'baz'))
    assertEqual(True, _isproperty(Bar, 'bar'))
    assertEqual(False, _isproperty(Bar, 'baz'))
    assertEqual(False, _isproperty(Mock(), 'baz'))

  def test_fake_object_supporting_iteration(self):
    foo = flexmock()
    foo.should_receive('__iter__').and_yield(1, 2, 3)
    assertEqual([1, 2, 3], [i for i in foo])

  def test_with_args_for_single_named_arg_with_optional_args(self):
    class Foo(object):
      def bar(self, one, two='optional'): pass
    e = flexmock(Foo).should_receive('bar')
    e.with_args(one=1)

  def test_with_args_doesnt_set_max_when_using_varargs(self):
    class Foo(object):
      def bar(self, *kargs): pass
    flexmock(Foo).should_receive('bar').with_args(1, 2, 3)

  def test_with_args_doesnt_set_max_when_using_kwargs(self):
    class Foo(object):
      def bar(self, **kwargs): pass
    flexmock(Foo).should_receive('bar').with_args(1, 2, 3)

  def test_with_args_blows_up_on_too_few_args(self):
    class Foo(object):
      def bar(self, a, b, c=1): pass
    e = flexmock(Foo).should_receive('bar')
    assertRaises(MethodSignatureError, e.with_args, 1)

  def test_with_args_blows_up_on_too_few_args_with_kwargs(self):
    class Foo(object):
      def bar(self, a, b, c=1): pass
    e = flexmock(Foo).should_receive('bar')
    assertRaises(MethodSignatureError, e.with_args, 1, c=2)

  def test_with_args_blows_up_on_too_many_args(self):
    class Foo(object):
      def bar(self, a, b, c=1): pass
    e = flexmock(Foo).should_receive('bar')
    assertRaises(MethodSignatureError, e.with_args, 1, 2, 3, 4)

  def test_with_args_blows_up_on_kwarg_overlapping_positional(self):
    class Foo(object):
      def bar(self, a, b, c=1, **kwargs): pass
    e = flexmock(Foo).should_receive('bar')
    assertRaises(MethodSignatureError, e.with_args, 1, 2, 3, c=2)

  def test_with_args_blows_up_on_invalid_kwarg(self):
    class Foo(object):
      def bar(self, a, b, c=1): pass
    e = flexmock(Foo).should_receive('bar')
    assertRaises(MethodSignatureError, e.with_args, 1, 2, d=2)

  def test_with_args_ignores_invalid_args_on_flexmock_instances(self):
    foo = flexmock(bar=lambda x: x)
    foo.should_receive('bar').with_args('stuff')
    foo.bar('stuff')

  def test_with_args_does_not_compensate_for_self_on_static_instance_methods(self):
    class Foo(object):
      @staticmethod
      def bar(x): pass
    foo = Foo()
    flexmock(foo).should_receive('bar').with_args('stuff')
    foo.bar('stuff')

  def test_with_args_does_not_compensate_for_self_on_static_class_methods(self):
    class Foo(object):
      @staticmethod
      def bar(x): pass
    flexmock(Foo).should_receive('bar').with_args('stuff')
    Foo.bar('stuff')

  def test_with_args_does_compensate_for_cls_on_class_methods(self):
    class Foo(object):
      @classmethod
      def bar(cls, x): pass
    foo = Foo()
    flexmock(foo).should_receive('bar').with_args('stuff')
    foo.bar('stuff')

  def test_calling_with_keyword_args_matches_mock_with_positional_args(self):
    class Foo(object):
      def bar(self, a, b, c): pass
    foo = Foo()
    flexmock(foo).should_receive('bar').with_args(1,2,3).once()
    foo.bar(a=1, b=2, c=3)

  def test_calling_with_positional_args_matches_mock_with_kwargs(self):
    class Foo(object):
      def bar(self, a, b, c): pass
    foo = Foo()
    flexmock(foo).should_receive('bar').with_args(a=1,b=2,c=3).once()
    foo.bar(1, 2, c=3)

  def test_use_replace_with_for_callable_shortcut_kwargs(self):
    class Foo(object):
      def bar(self): return 'bar'
    foo = Foo()
    flexmock(foo, bar=lambda: 'baz')
    assertEqual('baz', foo.bar())

  def test_mock_property_with_attribute_on_instance(self):
    class Foo(object):
      @property
      def bar(self): return 'bar'
    foo = Foo()
    foo2 = Foo()
    foo3 = Foo()
    flexmock(foo, bar='baz')
    flexmock(foo2, bar='baz2')
    assertEqual('baz', foo.bar)
    assertEqual('baz2', foo2.bar)
    assertEqual('bar', foo3.bar)
    self._tear_down()
    assertEqual(False, hasattr(Foo, '_flexmock__bar'),
                'Property bar not cleaned up')
    assertEqual('bar', foo.bar)
    assertEqual('bar', foo2.bar)
    assertEqual('bar', foo3.bar)

  def test_mock_property_with_attribute_on_class(self):
    class Foo(object):
      @property
      def bar(self): return 'bar'
    foo = Foo()
    foo2 = Foo()
    flexmock(Foo, bar='baz')
    assertEqual('baz', foo.bar)
    assertEqual('baz', foo2.bar)
    self._tear_down()
    assertEqual(False, hasattr(Foo, '_flexmock__bar'),
                'Property bar not cleaned up')
    assertEqual('bar', foo.bar)
    assertEqual('bar', foo2.bar)


class TestFlexmockUnittest(RegularClass, unittest.TestCase):
  def tearDown(self):
    pass

  def _tear_down(self):
    return flexmock_teardown()


if sys.version_info >= (2, 6):
  import flexmock_modern_test

  class TestUnittestModern(flexmock_modern_test.TestFlexmockUnittestModern):
    pass



if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = flexmock_unittest_test
import sys
import unittest

from flexmock_test import TestFlexmockUnittest

if sys.version_info >= (2, 6):
  from flexmock_modern_test import TestFlexmockUnittestModern


if __name__ == '__main__':
  unittest.main()

########NEW FILE########