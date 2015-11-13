__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2012 Michael Foord & the mock team
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 1.0
# http://www.voidspace.org.uk/python/mock/

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.


__all__ = (
    'Mock',
    'MagicMock',
    'patch',
    'sentinel',
    'DEFAULT',
    'ANY',
    'call',
    'create_autospec',
    'FILTER_DIR',
    'NonCallableMock',
    'NonCallableMagicMock',
    'mock_open',
    'PropertyMock',
)


__version__ = '1.0.1'


import pprint
import sys

try:
    import inspect
except ImportError:
    # for alternative platforms that
    # may not have inspect
    inspect = None

try:
    from functools import wraps as original_wraps
except ImportError:
    # Python 2.4 compatibility
    def wraps(original):
        def inner(f):
            f.__name__ = original.__name__
            f.__doc__ = original.__doc__
            f.__module__ = original.__module__
            f.__wrapped__ = original
            return f
        return inner
else:
    if sys.version_info[:2] >= (3, 3):
        wraps = original_wraps
    else:
        def wraps(func):
            def inner(f):
                f = original_wraps(func)(f)
                f.__wrapped__ = func
                return f
            return inner

try:
    unicode
except NameError:
    # Python 3
    basestring = unicode = str

try:
    long
except NameError:
    # Python 3
    long = int

try:
    BaseException
except NameError:
    # Python 2.4 compatibility
    BaseException = Exception

try:
    next
except NameError:
    def next(obj):
        return obj.next()


BaseExceptions = (BaseException,)
if 'java' in sys.platform:
    # jython
    import java
    BaseExceptions = (BaseException, java.lang.Throwable)

try:
    _isidentifier = str.isidentifier
except AttributeError:
    # Python 2.X
    import keyword
    import re
    regex = re.compile(r'^[a-z_][a-z0-9_]*$', re.I)
    def _isidentifier(string):
        if string in keyword.kwlist:
            return False
        return regex.match(string)


inPy3k = sys.version_info[0] == 3

# Needed to work around Python 3 bug where use of "super" interferes with
# defining __class__ as a descriptor
_super = super

self = 'im_self'
builtin = '__builtin__'
if inPy3k:
    self = '__self__'
    builtin = 'builtins'

FILTER_DIR = True


def _is_instance_mock(obj):
    # can't use isinstance on Mock objects because they override __class__
    # The base class for all mocks is NonCallableMock
    return issubclass(type(obj), NonCallableMock)


def _is_exception(obj):
    return (
        isinstance(obj, BaseExceptions) or
        isinstance(obj, ClassTypes) and issubclass(obj, BaseExceptions)
    )


class _slotted(object):
    __slots__ = ['a']


DescriptorTypes = (
    type(_slotted.a),
    property,
)


def _getsignature(func, skipfirst, instance=False):
    if inspect is None:
        raise ImportError('inspect module not available')

    if isinstance(func, ClassTypes) and not instance:
        try:
            func = func.__init__
        except AttributeError:
            return
        skipfirst = True
    elif not isinstance(func, FunctionTypes):
        # for classes where instance is True we end up here too
        try:
            func = func.__call__
        except AttributeError:
            return

    if inPy3k:
        try:
            argspec = inspect.getfullargspec(func)
        except TypeError:
            # C function / method, possibly inherited object().__init__
            return
        regargs, varargs, varkw, defaults, kwonly, kwonlydef, ann = argspec
    else:
        try:
            regargs, varargs, varkwargs, defaults = inspect.getargspec(func)
        except TypeError:
            # C function / method, possibly inherited object().__init__
            return

    # instance methods and classmethods need to lose the self argument
    if getattr(func, self, None) is not None:
        regargs = regargs[1:]
    if skipfirst:
        # this condition and the above one are never both True - why?
        regargs = regargs[1:]

    if inPy3k:
        signature = inspect.formatargspec(
            regargs, varargs, varkw, defaults,
            kwonly, kwonlydef, ann, formatvalue=lambda value: "")
    else:
        signature = inspect.formatargspec(
            regargs, varargs, varkwargs, defaults,
            formatvalue=lambda value: "")
    return signature[1:-1], func


def _check_signature(func, mock, skipfirst, instance=False):
    if not _callable(func):
        return

    result = _getsignature(func, skipfirst, instance)
    if result is None:
        return
    signature, func = result

    # can't use self because "self" is common as an argument name
    # unfortunately even not in the first place
    src = "lambda _mock_self, %s: None" % signature
    checksig = eval(src, {})
    _copy_func_details(func, checksig)
    type(mock)._mock_check_sig = checksig


def _copy_func_details(func, funcopy):
    funcopy.__name__ = func.__name__
    funcopy.__doc__ = func.__doc__
    #funcopy.__dict__.update(func.__dict__)
    funcopy.__module__ = func.__module__
    if not inPy3k:
        funcopy.func_defaults = func.func_defaults
        return
    funcopy.__defaults__ = func.__defaults__
    funcopy.__kwdefaults__ = func.__kwdefaults__


def _callable(obj):
    if isinstance(obj, ClassTypes):
        return True
    if getattr(obj, '__call__', None) is not None:
        return True
    return False


def _is_list(obj):
    # checks for list or tuples
    # XXXX badly named!
    return type(obj) in (list, tuple)


def _instance_callable(obj):
    """Given an object, return True if the object is callable.
    For classes, return True if instances would be callable."""
    if not isinstance(obj, ClassTypes):
        # already an instance
        return getattr(obj, '__call__', None) is not None

    klass = obj
    # uses __bases__ instead of __mro__ so that we work with old style classes
    if klass.__dict__.get('__call__') is not None:
        return True

    for base in klass.__bases__:
        if _instance_callable(base):
            return True
    return False


def _set_signature(mock, original, instance=False):
    # creates a function with signature (*args, **kwargs) that delegates to a
    # mock. It still does signature checking by calling a lambda with the same
    # signature as the original.
    if not _callable(original):
        return

    skipfirst = isinstance(original, ClassTypes)
    result = _getsignature(original, skipfirst, instance)
    if result is None:
        # was a C function (e.g. object().__init__ ) that can't be mocked
        return

    signature, func = result

    src = "lambda %s: None" % signature
    checksig = eval(src, {})
    _copy_func_details(func, checksig)

    name = original.__name__
    if not _isidentifier(name):
        name = 'funcopy'
    context = {'_checksig_': checksig, 'mock': mock}
    src = """def %s(*args, **kwargs):
    _checksig_(*args, **kwargs)
    return mock(*args, **kwargs)""" % name
    exec (src, context)
    funcopy = context[name]
    _setup_func(funcopy, mock)
    return funcopy


def _setup_func(funcopy, mock):
    funcopy.mock = mock

    # can't use isinstance with mocks
    if not _is_instance_mock(mock):
        return

    def assert_called_with(*args, **kwargs):
        return mock.assert_called_with(*args, **kwargs)
    def assert_called_once_with(*args, **kwargs):
        return mock.assert_called_once_with(*args, **kwargs)
    def assert_has_calls(*args, **kwargs):
        return mock.assert_has_calls(*args, **kwargs)
    def assert_any_call(*args, **kwargs):
        return mock.assert_any_call(*args, **kwargs)
    def reset_mock():
        funcopy.method_calls = _CallList()
        funcopy.mock_calls = _CallList()
        mock.reset_mock()
        ret = funcopy.return_value
        if _is_instance_mock(ret) and not ret is mock:
            ret.reset_mock()

    funcopy.called = False
    funcopy.call_count = 0
    funcopy.call_args = None
    funcopy.call_args_list = _CallList()
    funcopy.method_calls = _CallList()
    funcopy.mock_calls = _CallList()

    funcopy.return_value = mock.return_value
    funcopy.side_effect = mock.side_effect
    funcopy._mock_children = mock._mock_children

    funcopy.assert_called_with = assert_called_with
    funcopy.assert_called_once_with = assert_called_once_with
    funcopy.assert_has_calls = assert_has_calls
    funcopy.assert_any_call = assert_any_call
    funcopy.reset_mock = reset_mock

    mock._mock_delegate = funcopy


def _is_magic(name):
    return '__%s__' % name[2:-2] == name


class _SentinelObject(object):
    "A unique, named, sentinel object."
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'sentinel.%s' % self.name


class _Sentinel(object):
    """Access attributes to return a named object, usable as a sentinel."""
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        if name == '__bases__':
            # Without this help(mock) raises an exception
            raise AttributeError
        return self._sentinels.setdefault(name, _SentinelObject(name))


sentinel = _Sentinel()

DEFAULT = sentinel.DEFAULT
_missing = sentinel.MISSING
_deleted = sentinel.DELETED


class OldStyleClass:
    pass
ClassType = type(OldStyleClass)


def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value


ClassTypes = (type,)
if not inPy3k:
    ClassTypes = (type, ClassType)

_allowed_names = set(
    [
        'return_value', '_mock_return_value', 'side_effect',
        '_mock_side_effect', '_mock_parent', '_mock_new_parent',
        '_mock_name', '_mock_new_name'
    ]
)


def _delegating_property(name):
    _allowed_names.add(name)
    _the_name = '_mock_' + name
    def _get(self, name=name, _the_name=_the_name):
        sig = self._mock_delegate
        if sig is None:
            return getattr(self, _the_name)
        return getattr(sig, name)
    def _set(self, value, name=name, _the_name=_the_name):
        sig = self._mock_delegate
        if sig is None:
            self.__dict__[_the_name] = value
        else:
            setattr(sig, name, value)

    return property(_get, _set)



class _CallList(list):

    def __contains__(self, value):
        if not isinstance(value, list):
            return list.__contains__(self, value)
        len_value = len(value)
        len_self = len(self)
        if len_value > len_self:
            return False

        for i in range(0, len_self - len_value + 1):
            sub_list = self[i:i+len_value]
            if sub_list == value:
                return True
        return False

    def __repr__(self):
        return pprint.pformat(list(self))


def _check_and_set_parent(parent, value, name, new_name):
    if not _is_instance_mock(value):
        return False
    if ((value._mock_name or value._mock_new_name) or
        (value._mock_parent is not None) or
        (value._mock_new_parent is not None)):
        return False

    _parent = parent
    while _parent is not None:
        # setting a mock (value) as a child or return value of itself
        # should not modify the mock
        if _parent is value:
            return False
        _parent = _parent._mock_new_parent

    if new_name:
        value._mock_new_parent = parent
        value._mock_new_name = new_name
    if name:
        value._mock_parent = parent
        value._mock_name = name
    return True



class Base(object):
    _mock_return_value = DEFAULT
    _mock_side_effect = None
    def __init__(self, *args, **kwargs):
        pass



class NonCallableMock(Base):
    """A non-callable version of `Mock`"""

    def __new__(cls, *args, **kw):
        # every instance has its own class
        # so we can create magic methods on the
        # class without stomping on other mocks
        new = type(cls.__name__, (cls,), {'__doc__': cls.__doc__})
        instance = object.__new__(new)
        return instance


    def __init__(
            self, spec=None, wraps=None, name=None, spec_set=None,
            parent=None, _spec_state=None, _new_name='', _new_parent=None,
            **kwargs
        ):
        if _new_parent is None:
            _new_parent = parent

        __dict__ = self.__dict__
        __dict__['_mock_parent'] = parent
        __dict__['_mock_name'] = name
        __dict__['_mock_new_name'] = _new_name
        __dict__['_mock_new_parent'] = _new_parent

        if spec_set is not None:
            spec = spec_set
            spec_set = True

        self._mock_add_spec(spec, spec_set)

        __dict__['_mock_children'] = {}
        __dict__['_mock_wraps'] = wraps
        __dict__['_mock_delegate'] = None

        __dict__['_mock_called'] = False
        __dict__['_mock_call_args'] = None
        __dict__['_mock_call_count'] = 0
        __dict__['_mock_call_args_list'] = _CallList()
        __dict__['_mock_mock_calls'] = _CallList()

        __dict__['method_calls'] = _CallList()

        if kwargs:
            self.configure_mock(**kwargs)

        _super(NonCallableMock, self).__init__(
            spec, wraps, name, spec_set, parent,
            _spec_state
        )


    def attach_mock(self, mock, attribute):
        """
        Attach a mock as an attribute of this one, replacing its name and
        parent. Calls to the attached mock will be recorded in the
        `method_calls` and `mock_calls` attributes of this one."""
        mock._mock_parent = None
        mock._mock_new_parent = None
        mock._mock_name = ''
        mock._mock_new_name = None

        setattr(self, attribute, mock)


    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)


    def _mock_add_spec(self, spec, spec_set):
        _spec_class = None

        if spec is not None and not _is_list(spec):
            if isinstance(spec, ClassTypes):
                _spec_class = spec
            else:
                _spec_class = _get_class(spec)

            spec = dir(spec)

        __dict__ = self.__dict__
        __dict__['_spec_class'] = _spec_class
        __dict__['_spec_set'] = spec_set
        __dict__['_mock_methods'] = spec


    def __get_return_value(self):
        ret = self._mock_return_value
        if self._mock_delegate is not None:
            ret = self._mock_delegate.return_value

        if ret is DEFAULT:
            ret = self._get_child_mock(
                _new_parent=self, _new_name='()'
            )
            self.return_value = ret
        return ret


    def __set_return_value(self, value):
        if self._mock_delegate is not None:
            self._mock_delegate.return_value = value
        else:
            self._mock_return_value = value
            _check_and_set_parent(self, value, None, '()')

    __return_value_doc = "The value to be returned when the mock is called."
    return_value = property(__get_return_value, __set_return_value,
                            __return_value_doc)


    @property
    def __class__(self):
        if self._spec_class is None:
            return type(self)
        return self._spec_class

    called = _delegating_property('called')
    call_count = _delegating_property('call_count')
    call_args = _delegating_property('call_args')
    call_args_list = _delegating_property('call_args_list')
    mock_calls = _delegating_property('mock_calls')


    def __get_side_effect(self):
        sig = self._mock_delegate
        if sig is None:
            return self._mock_side_effect
        return sig.side_effect

    def __set_side_effect(self, value):
        value = _try_iter(value)
        sig = self._mock_delegate
        if sig is None:
            self._mock_side_effect = value
        else:
            sig.side_effect = value

    side_effect = property(__get_side_effect, __set_side_effect)


    def reset_mock(self):
        "Restore the mock object to its initial state."
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.mock_calls = _CallList()
        self.call_args_list = _CallList()
        self.method_calls = _CallList()

        for child in self._mock_children.values():
            if isinstance(child, _SpecState):
                continue
            child.reset_mock()

        ret = self._mock_return_value
        if _is_instance_mock(ret) and ret is not self:
            ret.reset_mock()


    def configure_mock(self, **kwargs):
        """Set attributes on the mock through keyword arguments.

        Attributes plus return values and side effects can be set on child
        mocks using standard dot notation and unpacking a dictionary in the
        method call:

        >>> attrs = {'method.return_value': 3, 'other.side_effect': KeyError}
        >>> mock.configure_mock(**attrs)"""
        for arg, val in sorted(kwargs.items(),
                               # we sort on the number of dots so that
                               # attributes are set before we set attributes on
                               # attributes
                               key=lambda entry: entry[0].count('.')):
            args = arg.split('.')
            final = args.pop()
            obj = self
            for entry in args:
                obj = getattr(obj, entry)
            setattr(obj, final, val)


    def __getattr__(self, name):
        if name == '_mock_methods':
            raise AttributeError(name)
        elif self._mock_methods is not None:
            if name not in self._mock_methods or name in _all_magics:
                raise AttributeError("Mock object has no attribute %r" % name)
        elif _is_magic(name):
            raise AttributeError(name)

        result = self._mock_children.get(name)
        if result is _deleted:
            raise AttributeError(name)
        elif result is None:
            wraps = None
            if self._mock_wraps is not None:
                # XXXX should we get the attribute without triggering code
                # execution?
                wraps = getattr(self._mock_wraps, name)

            result = self._get_child_mock(
                parent=self, name=name, wraps=wraps, _new_name=name,
                _new_parent=self
            )
            self._mock_children[name]  = result

        elif isinstance(result, _SpecState):
            result = create_autospec(
                result.spec, result.spec_set, result.instance,
                result.parent, result.name
            )
            self._mock_children[name]  = result

        return result


    def __repr__(self):
        _name_list = [self._mock_new_name]
        _parent = self._mock_new_parent
        last = self

        dot = '.'
        if _name_list == ['()']:
            dot = ''
        seen = set()
        while _parent is not None:
            last = _parent

            _name_list.append(_parent._mock_new_name + dot)
            dot = '.'
            if _parent._mock_new_name == '()':
                dot = ''

            _parent = _parent._mock_new_parent

            # use ids here so as not to call __hash__ on the mocks
            if id(_parent) in seen:
                break
            seen.add(id(_parent))

        _name_list = list(reversed(_name_list))
        _first = last._mock_name or 'mock'
        if len(_name_list) > 1:
            if _name_list[1] not in ('()', '().'):
                _first += '.'
        _name_list[0] = _first
        name = ''.join(_name_list)

        name_string = ''
        if name not in ('mock', 'mock.'):
            name_string = ' name=%r' % name

        spec_string = ''
        if self._spec_class is not None:
            spec_string = ' spec=%r'
            if self._spec_set:
                spec_string = ' spec_set=%r'
            spec_string = spec_string % self._spec_class.__name__
        return "<%s%s%s id='%s'>" % (
            type(self).__name__,
            name_string,
            spec_string,
            id(self)
        )


    def __dir__(self):
        """Filter the output of `dir(mock)` to only useful members.
        XXXX
        """
        extras = self._mock_methods or []
        from_type = dir(type(self))
        from_dict = list(self.__dict__)

        if FILTER_DIR:
            from_type = [e for e in from_type if not e.startswith('_')]
            from_dict = [e for e in from_dict if not e.startswith('_') or
                         _is_magic(e)]
        return sorted(set(extras + from_type + from_dict +
                          list(self._mock_children)))


    def __setattr__(self, name, value):
        if name in _allowed_names:
            # property setters go through here
            return object.__setattr__(self, name, value)
        elif (self._spec_set and self._mock_methods is not None and
            name not in self._mock_methods and
            name not in self.__dict__):
            raise AttributeError("Mock object has no attribute '%s'" % name)
        elif name in _unsupported_magics:
            msg = 'Attempting to set unsupported magic method %r.' % name
            raise AttributeError(msg)
        elif name in _all_magics:
            if self._mock_methods is not None and name not in self._mock_methods:
                raise AttributeError("Mock object has no attribute '%s'" % name)

            if not _is_instance_mock(value):
                setattr(type(self), name, _get_method(name, value))
                original = value
                value = lambda *args, **kw: original(self, *args, **kw)
            else:
                # only set _new_name and not name so that mock_calls is tracked
                # but not method calls
                _check_and_set_parent(self, value, None, name)
                setattr(type(self), name, value)
                self._mock_children[name] = value
        elif name == '__class__':
            self._spec_class = value
            return
        else:
            if _check_and_set_parent(self, value, name, name):
                self._mock_children[name] = value
        return object.__setattr__(self, name, value)


    def __delattr__(self, name):
        if name in _all_magics and name in type(self).__dict__:
            delattr(type(self), name)
            if name not in self.__dict__:
                # for magic methods that are still MagicProxy objects and
                # not set on the instance itself
                return

        if name in self.__dict__:
            object.__delattr__(self, name)

        obj = self._mock_children.get(name, _missing)
        if obj is _deleted:
            raise AttributeError(name)
        if obj is not _missing:
            del self._mock_children[name]
        self._mock_children[name] = _deleted



    def _format_mock_call_signature(self, args, kwargs):
        name = self._mock_name or 'mock'
        return _format_call_signature(name, args, kwargs)


    def _format_mock_failure_message(self, args, kwargs):
        message = 'Expected call: %s\nActual call: %s'
        expected_string = self._format_mock_call_signature(args, kwargs)
        call_args = self.call_args
        if len(call_args) == 3:
            call_args = call_args[1:]
        actual_string = self._format_mock_call_signature(*call_args)
        return message % (expected_string, actual_string)


    def assert_called_with(_mock_self, *args, **kwargs):
        """assert that the mock was called with the specified arguments.

        Raises an AssertionError if the args and keyword args passed in are
        different to the last call to the mock."""
        self = _mock_self
        if self.call_args is None:
            expected = self._format_mock_call_signature(args, kwargs)
            raise AssertionError('Expected call: %s\nNot called' % (expected,))

        if self.call_args != (args, kwargs):
            msg = self._format_mock_failure_message(args, kwargs)
            raise AssertionError(msg)


    def assert_called_once_with(_mock_self, *args, **kwargs):
        """assert that the mock was called exactly once and with the specified
        arguments."""
        self = _mock_self
        if not self.call_count == 1:
            msg = ("Expected to be called once. Called %s times." %
                   self.call_count)
            raise AssertionError(msg)
        return self.assert_called_with(*args, **kwargs)


    def assert_has_calls(self, calls, any_order=False):
        """assert the mock has been called with the specified calls.
        The `mock_calls` list is checked for the calls.

        If `any_order` is False (the default) then the calls must be
        sequential. There can be extra calls before or after the
        specified calls.

        If `any_order` is True then the calls can be in any order, but
        they must all appear in `mock_calls`."""
        if not any_order:
            if calls not in self.mock_calls:
                raise AssertionError(
                    'Calls not found.\nExpected: %r\n'
                    'Actual: %r' % (calls, self.mock_calls)
                )
            return

        all_calls = list(self.mock_calls)

        not_found = []
        for kall in calls:
            try:
                all_calls.remove(kall)
            except ValueError:
                not_found.append(kall)
        if not_found:
            raise AssertionError(
                '%r not all found in call list' % (tuple(not_found),)
            )


    def assert_any_call(self, *args, **kwargs):
        """assert the mock has been called with the specified arguments.

        The assert passes if the mock has *ever* been called, unlike
        `assert_called_with` and `assert_called_once_with` that only pass if
        the call is the most recent one."""
        kall = call(*args, **kwargs)
        if kall not in self.call_args_list:
            expected_string = self._format_mock_call_signature(args, kwargs)
            raise AssertionError(
                '%s call not found' % expected_string
            )


    def _get_child_mock(self, **kw):
        """Create the child mocks for attributes and return value.
        By default child mocks will be the same type as the parent.
        Subclasses of Mock may want to override this to customize the way
        child mocks are made.

        For non-callable mocks the callable variant will be used (rather than
        any custom subclass)."""
        _type = type(self)
        if not issubclass(_type, CallableMixin):
            if issubclass(_type, NonCallableMagicMock):
                klass = MagicMock
            elif issubclass(_type, NonCallableMock) :
                klass = Mock
        else:
            klass = _type.__mro__[1]
        return klass(**kw)



def _try_iter(obj):
    if obj is None:
        return obj
    if _is_exception(obj):
        return obj
    if _callable(obj):
        return obj
    try:
        return iter(obj)
    except TypeError:
        # XXXX backwards compatibility
        # but this will blow up on first call - so maybe we should fail early?
        return obj



class CallableMixin(Base):

    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                 wraps=None, name=None, spec_set=None, parent=None,
                 _spec_state=None, _new_name='', _new_parent=None, **kwargs):
        self.__dict__['_mock_return_value'] = return_value

        _super(CallableMixin, self).__init__(
            spec, wraps, name, spec_set, parent,
            _spec_state, _new_name, _new_parent, **kwargs
        )

        self.side_effect = side_effect


    def _mock_check_sig(self, *args, **kwargs):
        # stub method that can be replaced with one with a specific signature
        pass


    def __call__(_mock_self, *args, **kwargs):
        # can't use self in-case a function / method we are mocking uses self
        # in the signature
        _mock_self._mock_check_sig(*args, **kwargs)
        return _mock_self._mock_call(*args, **kwargs)


    def _mock_call(_mock_self, *args, **kwargs):
        self = _mock_self
        self.called = True
        self.call_count += 1
        self.call_args = _Call((args, kwargs), two=True)
        self.call_args_list.append(_Call((args, kwargs), two=True))

        _new_name = self._mock_new_name
        _new_parent = self._mock_new_parent
        self.mock_calls.append(_Call(('', args, kwargs)))

        seen = set()
        skip_next_dot = _new_name == '()'
        do_method_calls = self._mock_parent is not None
        name = self._mock_name
        while _new_parent is not None:
            this_mock_call = _Call((_new_name, args, kwargs))
            if _new_parent._mock_new_name:
                dot = '.'
                if skip_next_dot:
                    dot = ''

                skip_next_dot = False
                if _new_parent._mock_new_name == '()':
                    skip_next_dot = True

                _new_name = _new_parent._mock_new_name + dot + _new_name

            if do_method_calls:
                if _new_name == name:
                    this_method_call = this_mock_call
                else:
                    this_method_call = _Call((name, args, kwargs))
                _new_parent.method_calls.append(this_method_call)

                do_method_calls = _new_parent._mock_parent is not None
                if do_method_calls:
                    name = _new_parent._mock_name + '.' + name

            _new_parent.mock_calls.append(this_mock_call)
            _new_parent = _new_parent._mock_new_parent

            # use ids here so as not to call __hash__ on the mocks
            _new_parent_id = id(_new_parent)
            if _new_parent_id in seen:
                break
            seen.add(_new_parent_id)

        ret_val = DEFAULT
        effect = self.side_effect
        if effect is not None:
            if _is_exception(effect):
                raise effect

            if not _callable(effect):
                result = next(effect)
                if _is_exception(result):
                    raise result
                return result

            ret_val = effect(*args, **kwargs)
            if ret_val is DEFAULT:
                ret_val = self.return_value

        if (self._mock_wraps is not None and
             self._mock_return_value is DEFAULT):
            return self._mock_wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val



class Mock(CallableMixin, NonCallableMock):
    """
    Create a new `Mock` object. `Mock` takes several optional arguments
    that specify the behaviour of the Mock object:

    * `spec`: This can be either a list of strings or an existing object (a
      class or instance) that acts as the specification for the mock object. If
      you pass in an object then a list of strings is formed by calling dir on
      the object (excluding unsupported magic attributes and methods). Accessing
      any attribute not in this list will raise an `AttributeError`.

      If `spec` is an object (rather than a list of strings) then
      `mock.__class__` returns the class of the spec object. This allows mocks
      to pass `isinstance` tests.

    * `spec_set`: A stricter variant of `spec`. If used, attempting to *set*
      or get an attribute on the mock that isn't on the object passed as
      `spec_set` will raise an `AttributeError`.

    * `side_effect`: A function to be called whenever the Mock is called. See
      the `side_effect` attribute. Useful for raising exceptions or
      dynamically changing return values. The function is called with the same
      arguments as the mock, and unless it returns `DEFAULT`, the return
      value of this function is used as the return value.

      Alternatively `side_effect` can be an exception class or instance. In
      this case the exception will be raised when the mock is called.

      If `side_effect` is an iterable then each call to the mock will return
      the next value from the iterable. If any of the members of the iterable
      are exceptions they will be raised instead of returned.

    * `return_value`: The value returned when the mock is called. By default
      this is a new Mock (created on first access). See the
      `return_value` attribute.

    * `wraps`: Item for the mock object to wrap. If `wraps` is not None then
      calling the Mock will pass the call through to the wrapped object
      (returning the real result). Attribute access on the mock will return a
      Mock object that wraps the corresponding attribute of the wrapped object
      (so attempting to access an attribute that doesn't exist will raise an
      `AttributeError`).

      If the mock has an explicit `return_value` set then calls are not passed
      to the wrapped object and the `return_value` is returned instead.

    * `name`: If the mock has a name then it will be used in the repr of the
      mock. This can be useful for debugging. The name is propagated to child
      mocks.

    Mocks can also be called with arbitrary keyword arguments. These will be
    used to set attributes on the mock after it is created.
    """



def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


def _is_started(patcher):
    # XXXX horrible
    return hasattr(patcher, 'is_local')


class _patch(object):

    attribute_name = None
    _active_patches = set()

    def __init__(
            self, getter, attribute, new, spec, create,
            spec_set, autospec, new_callable, kwargs
        ):
        if new_callable is not None:
            if new is not DEFAULT:
                raise ValueError(
                    "Cannot use 'new' and 'new_callable' together"
                )
            if autospec is not None:
                raise ValueError(
                    "Cannot use 'autospec' and 'new_callable' together"
                )

        self.getter = getter
        self.attribute = attribute
        self.new = new
        self.new_callable = new_callable
        self.spec = spec
        self.create = create
        self.has_local = False
        self.spec_set = spec_set
        self.autospec = autospec
        self.kwargs = kwargs
        self.additional_patchers = []


    def copy(self):
        patcher = _patch(
            self.getter, self.attribute, self.new, self.spec,
            self.create, self.spec_set,
            self.autospec, self.new_callable, self.kwargs
        )
        patcher.attribute_name = self.attribute_name
        patcher.additional_patchers = [
            p.copy() for p in self.additional_patchers
        ]
        return patcher


    def __call__(self, func):
        if isinstance(func, ClassTypes):
            return self.decorate_class(func)
        return self.decorate_callable(func)


    def decorate_class(self, klass):
        for attr in dir(klass):
            if not attr.startswith(patch.TEST_PREFIX):
                continue

            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue

            patcher = self.copy()
            setattr(klass, attr, patcher(attr_value))
        return klass


    def decorate_callable(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        @wraps(func)
        def patched(*args, **keywargs):
            # don't use a with here (backwards compatability with Python 2.4)
            extra_args = []
            entered_patchers = []

            # can't use try...except...finally because of Python 2.4
            # compatibility
            exc_info = tuple()
            try:
                try:
                    for patching in patched.patchings:
                        arg = patching.__enter__()
                        entered_patchers.append(patching)
                        if patching.attribute_name is not None:
                            keywargs.update(arg)
                        elif patching.new is DEFAULT:
                            extra_args.append(arg)

                    args += tuple(extra_args)
                    return func(*args, **keywargs)
                except:
                    if (patching not in entered_patchers and
                        _is_started(patching)):
                        # the patcher may have been started, but an exception
                        # raised whilst entering one of its additional_patchers
                        entered_patchers.append(patching)
                    # Pass the exception to __exit__
                    exc_info = sys.exc_info()
                    # re-raise the exception
                    raise
            finally:
                for patching in reversed(entered_patchers):
                    patching.__exit__(*exc_info)

        patched.patchings = [self]
        if hasattr(func, 'func_code'):
            # not in Python 3
            patched.compat_co_firstlineno = getattr(
                func, "compat_co_firstlineno",
                func.func_code.co_firstlineno
            )
        return patched


    def get_original(self):
        target = self.getter()
        name = self.attribute

        original = DEFAULT
        local = False

        try:
            original = target.__dict__[name]
        except (AttributeError, KeyError):
            original = getattr(target, name, DEFAULT)
        else:
            local = True

        if not self.create and original is DEFAULT:
            raise AttributeError(
                "%s does not have the attribute %r" % (target, name)
            )
        return original, local


    def __enter__(self):
        """Perform the patch."""
        new, spec, spec_set = self.new, self.spec, self.spec_set
        autospec, kwargs = self.autospec, self.kwargs
        new_callable = self.new_callable
        self.target = self.getter()

        # normalise False to None
        if spec is False:
            spec = None
        if spec_set is False:
            spec_set = None
        if autospec is False:
            autospec = None

        if spec is not None and autospec is not None:
            raise TypeError("Can't specify spec and autospec")
        if ((spec is not None or autospec is not None) and
            spec_set not in (True, None)):
            raise TypeError("Can't provide explicit spec_set *and* spec or autospec")

        original, local = self.get_original()

        if new is DEFAULT and autospec is None:
            inherit = False
            if spec is True:
                # set spec to the object we are replacing
                spec = original
                if spec_set is True:
                    spec_set = original
                    spec = None
            elif spec is not None:
                if spec_set is True:
                    spec_set = spec
                    spec = None
            elif spec_set is True:
                spec_set = original

            if spec is not None or spec_set is not None:
                if original is DEFAULT:
                    raise TypeError("Can't use 'spec' with create=True")
                if isinstance(original, ClassTypes):
                    # If we're patching out a class and there is a spec
                    inherit = True

            Klass = MagicMock
            _kwargs = {}
            if new_callable is not None:
                Klass = new_callable
            elif spec is not None or spec_set is not None:
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if _is_list(this_spec):
                    not_callable = '__call__' not in this_spec
                else:
                    not_callable = not _callable(this_spec)
                if not_callable:
                    Klass = NonCallableMagicMock

            if spec is not None:
                _kwargs['spec'] = spec
            if spec_set is not None:
                _kwargs['spec_set'] = spec_set

            # add a name to mocks
            if (isinstance(Klass, type) and
                issubclass(Klass, NonCallableMock) and self.attribute):
                _kwargs['name'] = self.attribute

            _kwargs.update(kwargs)
            new = Klass(**_kwargs)

            if inherit and _is_instance_mock(new):
                # we can only tell if the instance should be callable if the
                # spec is not a list
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if (not _is_list(this_spec) and not
                    _instance_callable(this_spec)):
                    Klass = NonCallableMagicMock

                _kwargs.pop('name')
                new.return_value = Klass(_new_parent=new, _new_name='()',
                                         **_kwargs)
        elif autospec is not None:
            # spec is ignored, new *must* be default, spec_set is treated
            # as a boolean. Should we check spec is not None and that spec_set
            # is a bool?
            if new is not DEFAULT:
                raise TypeError(
                    "autospec creates the mock for you. Can't specify "
                    "autospec and new."
                )
            if original is DEFAULT:
                raise TypeError("Can't use 'autospec' with create=True")
            spec_set = bool(spec_set)
            if autospec is True:
                autospec = original

            new = create_autospec(autospec, spec_set=spec_set,
                                  _name=self.attribute, **kwargs)
        elif kwargs:
            # can't set keyword args when we aren't creating the mock
            # XXXX If new is a Mock we could call new.configure_mock(**kwargs)
            raise TypeError("Can't pass kwargs to a mock we aren't creating")

        new_attr = new

        self.temp_original = original
        self.is_local = local
        setattr(self.target, self.attribute, new_attr)
        if self.attribute_name is not None:
            extra_args = {}
            if self.new is DEFAULT:
                extra_args[self.attribute_name] =  new
            for patching in self.additional_patchers:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.update(arg)
            return extra_args

        return new


    def __exit__(self, *exc_info):
        """Undo the patch."""
        if not _is_started(self):
            raise RuntimeError('stop called on unstarted patcher')

        if self.is_local and self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
            if not self.create and not hasattr(self.target, self.attribute):
                # needed for proxy objects like django settings
                setattr(self.target, self.attribute, self.temp_original)

        del self.temp_original
        del self.is_local
        del self.target
        for patcher in reversed(self.additional_patchers):
            if _is_started(patcher):
                patcher.__exit__(*exc_info)


    def start(self):
        """Activate a patch, returning any created mock."""
        result = self.__enter__()
        self._active_patches.add(self)
        return result


    def stop(self):
        """Stop an active patch."""
        self._active_patches.discard(self)
        return self.__exit__()



def _get_target(target):
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %r" %
                        (target,))
    getter = lambda: _importer(target)
    return getter, attribute


def _patch_object(
        target, attribute, new=DEFAULT, spec=None,
        create=False, spec_set=None, autospec=None,
        new_callable=None, **kwargs
    ):
    """
    patch.object(target, attribute, new=DEFAULT, spec=None, create=False,
                 spec_set=None, autospec=None, new_callable=None, **kwargs)

    patch the named member (`attribute`) on an object (`target`) with a mock
    object.

    `patch.object` can be used as a decorator, class decorator or a context
    manager. Arguments `new`, `spec`, `create`, `spec_set`,
    `autospec` and `new_callable` have the same meaning as for `patch`. Like
    `patch`, `patch.object` takes arbitrary keyword arguments for configuring
    the mock object it creates.

    When used as a class decorator `patch.object` honours `patch.TEST_PREFIX`
    for choosing which methods to wrap.
    """
    getter = lambda: target
    return _patch(
        getter, attribute, new, spec, create,
        spec_set, autospec, new_callable, kwargs
    )


def _patch_multiple(target, spec=None, create=False, spec_set=None,
                    autospec=None, new_callable=None, **kwargs):
    """Perform multiple patches in a single call. It takes the object to be
    patched (either as an object or a string to fetch the object by importing)
    and keyword arguments for the patches::

        with patch.multiple(settings, FIRST_PATCH='one', SECOND_PATCH='two'):
            ...

    Use `DEFAULT` as the value if you want `patch.multiple` to create
    mocks for you. In this case the created mocks are passed into a decorated
    function by keyword, and a dictionary is returned when `patch.multiple` is
    used as a context manager.

    `patch.multiple` can be used as a decorator, class decorator or a context
    manager. The arguments `spec`, `spec_set`, `create`,
    `autospec` and `new_callable` have the same meaning as for `patch`. These
    arguments will be applied to *all* patches done by `patch.multiple`.

    When used as a class decorator `patch.multiple` honours `patch.TEST_PREFIX`
    for choosing which methods to wrap.
    """
    if type(target) in (unicode, str):
        getter = lambda: _importer(target)
    else:
        getter = lambda: target

    if not kwargs:
        raise ValueError(
            'Must supply at least one keyword argument with patch.multiple'
        )
    # need to wrap in a list for python 3, where items is a view
    items = list(kwargs.items())
    attribute, new = items[0]
    patcher = _patch(
        getter, attribute, new, spec, create, spec_set,
        autospec, new_callable, {}
    )
    patcher.attribute_name = attribute
    for attribute, new in items[1:]:
        this_patcher = _patch(
            getter, attribute, new, spec, create, spec_set,
            autospec, new_callable, {}
        )
        this_patcher.attribute_name = attribute
        patcher.additional_patchers.append(this_patcher)
    return patcher


def patch(
        target, new=DEFAULT, spec=None, create=False,
        spec_set=None, autospec=None, new_callable=None, **kwargs
    ):
    """
    `patch` acts as a function decorator, class decorator or a context
    manager. Inside the body of the function or with statement, the `target`
    is patched with a `new` object. When the function/with statement exits
    the patch is undone.

    If `new` is omitted, then the target is replaced with a
    `MagicMock`. If `patch` is used as a decorator and `new` is
    omitted, the created mock is passed in as an extra argument to the
    decorated function. If `patch` is used as a context manager the created
    mock is returned by the context manager.

    `target` should be a string in the form `'package.module.ClassName'`. The
    `target` is imported and the specified object replaced with the `new`
    object, so the `target` must be importable from the environment you are
    calling `patch` from. The target is imported when the decorated function
    is executed, not at decoration time.

    The `spec` and `spec_set` keyword arguments are passed to the `MagicMock`
    if patch is creating one for you.

    In addition you can pass `spec=True` or `spec_set=True`, which causes
    patch to pass in the object being mocked as the spec/spec_set object.

    `new_callable` allows you to specify a different class, or callable object,
    that will be called to create the `new` object. By default `MagicMock` is
    used.

    A more powerful form of `spec` is `autospec`. If you set `autospec=True`
    then the mock with be created with a spec from the object being replaced.
    All attributes of the mock will also have the spec of the corresponding
    attribute of the object being replaced. Methods and functions being
    mocked will have their arguments checked and will raise a `TypeError` if
    they are called with the wrong signature. For mocks replacing a class,
    their return value (the 'instance') will have the same spec as the class.

    Instead of `autospec=True` you can pass `autospec=some_object` to use an
    arbitrary object as the spec instead of the one being replaced.

    By default `patch` will fail to replace attributes that don't exist. If
    you pass in `create=True`, and the attribute doesn't exist, patch will
    create the attribute for you when the patched function is called, and
    delete it again afterwards. This is useful for writing tests against
    attributes that your production code creates at runtime. It is off by by
    default because it can be dangerous. With it switched on you can write
    passing tests against APIs that don't actually exist!

    Patch can be used as a `TestCase` class decorator. It works by
    decorating each test method in the class. This reduces the boilerplate
    code when your test methods share a common patchings set. `patch` finds
    tests by looking for method names that start with `patch.TEST_PREFIX`.
    By default this is `test`, which matches the way `unittest` finds tests.
    You can specify an alternative prefix by setting `patch.TEST_PREFIX`.

    Patch can be used as a context manager, with the with statement. Here the
    patching applies to the indented block after the with statement. If you
    use "as" then the patched object will be bound to the name after the
    "as"; very useful if `patch` is creating a mock object for you.

    `patch` takes arbitrary keyword arguments. These will be passed to
    the `Mock` (or `new_callable`) on construction.

    `patch.dict(...)`, `patch.multiple(...)` and `patch.object(...)` are
    available for alternate use-cases.
    """
    getter, attribute = _get_target(target)
    return _patch(
        getter, attribute, new, spec, create,
        spec_set, autospec, new_callable, kwargs
    )


class _patch_dict(object):
    """
    Patch a dictionary, or dictionary like object, and restore the dictionary
    to its original state after the test.

    `in_dict` can be a dictionary or a mapping like container. If it is a
    mapping then it must at least support getting, setting and deleting items
    plus iterating over keys.

    `in_dict` can also be a string specifying the name of the dictionary, which
    will then be fetched by importing it.

    `values` can be a dictionary of values to set in the dictionary. `values`
    can also be an iterable of `(key, value)` pairs.

    If `clear` is True then the dictionary will be cleared before the new
    values are set.

    `patch.dict` can also be called with arbitrary keyword arguments to set
    values in the dictionary::

        with patch.dict('sys.modules', mymodule=Mock(), other_module=Mock()):
            ...

    `patch.dict` can be used as a context manager, decorator or class
    decorator. When used as a class decorator `patch.dict` honours
    `patch.TEST_PREFIX` for choosing which methods to wrap.
    """

    def __init__(self, in_dict, values=(), clear=False, **kwargs):
        if isinstance(in_dict, basestring):
            in_dict = _importer(in_dict)
        self.in_dict = in_dict
        # support any argument supported by dict(...) constructor
        self.values = dict(values)
        self.values.update(kwargs)
        self.clear = clear
        self._original = None


    def __call__(self, f):
        if isinstance(f, ClassTypes):
            return self.decorate_class(f)
        @wraps(f)
        def _inner(*args, **kw):
            self._patch_dict()
            try:
                return f(*args, **kw)
            finally:
                self._unpatch_dict()

        return _inner


    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if (attr.startswith(patch.TEST_PREFIX) and
                 hasattr(attr_value, "__call__")):
                decorator = _patch_dict(self.in_dict, self.values, self.clear)
                decorated = decorator(attr_value)
                setattr(klass, attr, decorated)
        return klass


    def __enter__(self):
        """Patch the dict."""
        self._patch_dict()


    def _patch_dict(self):
        values = self.values
        in_dict = self.in_dict
        clear = self.clear

        try:
            original = in_dict.copy()
        except AttributeError:
            # dict like object with no copy method
            # must support iteration over keys
            original = {}
            for key in in_dict:
                original[key] = in_dict[key]
        self._original = original

        if clear:
            _clear_dict(in_dict)

        try:
            in_dict.update(values)
        except AttributeError:
            # dict like object with no update method
            for key in values:
                in_dict[key] = values[key]


    def _unpatch_dict(self):
        in_dict = self.in_dict
        original = self._original

        _clear_dict(in_dict)

        try:
            in_dict.update(original)
        except AttributeError:
            for key in original:
                in_dict[key] = original[key]


    def __exit__(self, *args):
        """Unpatch the dict."""
        self._unpatch_dict()
        return False

    start = __enter__
    stop = __exit__


def _clear_dict(in_dict):
    try:
        in_dict.clear()
    except AttributeError:
        keys = list(in_dict)
        for key in keys:
            del in_dict[key]


def _patch_stopall():
    """Stop all active patches."""
    for patch in list(_patch._active_patches):
        patch.stop()


patch.object = _patch_object
patch.dict = _patch_dict
patch.multiple = _patch_multiple
patch.stopall = _patch_stopall
patch.TEST_PREFIX = 'test'

magic_methods = (
    "lt le gt ge eq ne "
    "getitem setitem delitem "
    "len contains iter "
    "hash str sizeof "
    "enter exit "
    "divmod neg pos abs invert "
    "complex int float index "
    "trunc floor ceil "
)

numerics = "add sub mul div floordiv mod lshift rshift and xor or pow "
inplace = ' '.join('i%s' % n for n in numerics.split())
right = ' '.join('r%s' % n for n in numerics.split())
extra = ''
if inPy3k:
    extra = 'bool next '
else:
    extra = 'unicode long nonzero oct hex truediv rtruediv '

# not including __prepare__, __instancecheck__, __subclasscheck__
# (as they are metaclass methods)
# __del__ is not supported at all as it causes problems if it exists

_non_defaults = set('__%s__' % method for method in [
    'cmp', 'getslice', 'setslice', 'coerce', 'subclasses',
    'format', 'get', 'set', 'delete', 'reversed',
    'missing', 'reduce', 'reduce_ex', 'getinitargs',
    'getnewargs', 'getstate', 'setstate', 'getformat',
    'setformat', 'repr', 'dir'
])


def _get_method(name, func):
    "Turns a callable object (like a mock) into a real function"
    def method(self, *args, **kw):
        return func(self, *args, **kw)
    method.__name__ = name
    return method


_magics = set(
    '__%s__' % method for method in
    ' '.join([magic_methods, numerics, inplace, right, extra]).split()
)

_all_magics = _magics | _non_defaults

_unsupported_magics = set([
    '__getattr__', '__setattr__',
    '__init__', '__new__', '__prepare__'
    '__instancecheck__', '__subclasscheck__',
    '__del__'
])

_calculate_return_value = {
    '__hash__': lambda self: object.__hash__(self),
    '__str__': lambda self: object.__str__(self),
    '__sizeof__': lambda self: object.__sizeof__(self),
    '__unicode__': lambda self: unicode(object.__str__(self)),
}

_return_values = {
    '__lt__': NotImplemented,
    '__gt__': NotImplemented,
    '__le__': NotImplemented,
    '__ge__': NotImplemented,
    '__int__': 1,
    '__contains__': False,
    '__len__': 0,
    '__exit__': False,
    '__complex__': 1j,
    '__float__': 1.0,
    '__bool__': True,
    '__nonzero__': True,
    '__oct__': '1',
    '__hex__': '0x1',
    '__long__': long(1),
    '__index__': 1,
}


def _get_eq(self):
    def __eq__(other):
        ret_val = self.__eq__._mock_return_value
        if ret_val is not DEFAULT:
            return ret_val
        return self is other
    return __eq__

def _get_ne(self):
    def __ne__(other):
        if self.__ne__._mock_return_value is not DEFAULT:
            return DEFAULT
        return self is not other
    return __ne__

def _get_iter(self):
    def __iter__():
        ret_val = self.__iter__._mock_return_value
        if ret_val is DEFAULT:
            return iter([])
        # if ret_val was already an iterator, then calling iter on it should
        # return the iterator unchanged
        return iter(ret_val)
    return __iter__

_side_effect_methods = {
    '__eq__': _get_eq,
    '__ne__': _get_ne,
    '__iter__': _get_iter,
}



def _set_return_value(mock, method, name):
    fixed = _return_values.get(name, DEFAULT)
    if fixed is not DEFAULT:
        method.return_value = fixed
        return

    return_calulator = _calculate_return_value.get(name)
    if return_calulator is not None:
        try:
            return_value = return_calulator(mock)
        except AttributeError:
            # XXXX why do we return AttributeError here?
            #      set it as a side_effect instead?
            return_value = AttributeError(name)
        method.return_value = return_value
        return

    side_effector = _side_effect_methods.get(name)
    if side_effector is not None:
        method.side_effect = side_effector(mock)



class MagicMixin(object):
    def __init__(self, *args, **kw):
        _super(MagicMixin, self).__init__(*args, **kw)
        self._mock_set_magics()


    def _mock_set_magics(self):
        these_magics = _magics

        if self._mock_methods is not None:
            these_magics = _magics.intersection(self._mock_methods)

            remove_magics = set()
            remove_magics = _magics - these_magics

            for entry in remove_magics:
                if entry in type(self).__dict__:
                    # remove unneeded magic methods
                    delattr(self, entry)

        # don't overwrite existing attributes if called a second time
        these_magics = these_magics - set(type(self).__dict__)

        _type = type(self)
        for entry in these_magics:
            setattr(_type, entry, MagicProxy(entry, self))



class NonCallableMagicMock(MagicMixin, NonCallableMock):
    """A version of `MagicMock` that isn't callable."""
    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()



class MagicMock(MagicMixin, Mock):
    """
    MagicMock is a subclass of Mock with default implementations
    of most of the magic methods. You can use MagicMock without having to
    configure the magic methods yourself.

    If you use the `spec` or `spec_set` arguments then *only* magic
    methods that exist in the spec will be created.

    Attributes and the return value of a `MagicMock` will also be `MagicMocks`.
    """
    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()



class MagicProxy(object):
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def __call__(self, *args, **kwargs):
        m = self.create_mock()
        return m(*args, **kwargs)

    def create_mock(self):
        entry = self.name
        parent = self.parent
        m = parent._get_child_mock(name=entry, _new_name=entry,
                                   _new_parent=parent)
        setattr(parent, entry, m)
        _set_return_value(parent, m, entry)
        return m

    def __get__(self, obj, _type=None):
        return self.create_mock()



class _ANY(object):
    "A helper object that compares equal to everything."

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return '<ANY>'

ANY = _ANY()



def _format_call_signature(name, args, kwargs):
    message = '%s(%%s)' % name
    formatted_args = ''
    args_string = ', '.join([repr(arg) for arg in args])
    kwargs_string = ', '.join([
        '%s=%r' % (key, value) for key, value in kwargs.items()
    ])
    if args_string:
        formatted_args = args_string
    if kwargs_string:
        if formatted_args:
            formatted_args += ', '
        formatted_args += kwargs_string

    return message % formatted_args



class _Call(tuple):
    """
    A tuple for holding the results of a call to a mock, either in the form
    `(args, kwargs)` or `(name, args, kwargs)`.

    If args or kwargs are empty then a call tuple will compare equal to
    a tuple without those values. This makes comparisons less verbose::

        _Call(('name', (), {})) == ('name',)
        _Call(('name', (1,), {})) == ('name', (1,))
        _Call(((), {'a': 'b'})) == ({'a': 'b'},)

    The `_Call` object provides a useful shortcut for comparing with call::

        _Call(((1, 2), {'a': 3})) == call(1, 2, a=3)
        _Call(('foo', (1, 2), {'a': 3})) == call.foo(1, 2, a=3)

    If the _Call has no name then it will match any name.
    """
    def __new__(cls, value=(), name=None, parent=None, two=False,
                from_kall=True):
        name = ''
        args = ()
        kwargs = {}
        _len = len(value)
        if _len == 3:
            name, args, kwargs = value
        elif _len == 2:
            first, second = value
            if isinstance(first, basestring):
                name = first
                if isinstance(second, tuple):
                    args = second
                else:
                    kwargs = second
            else:
                args, kwargs = first, second
        elif _len == 1:
            value, = value
            if isinstance(value, basestring):
                name = value
            elif isinstance(value, tuple):
                args = value
            else:
                kwargs = value

        if two:
            return tuple.__new__(cls, (args, kwargs))

        return tuple.__new__(cls, (name, args, kwargs))


    def __init__(self, value=(), name=None, parent=None, two=False,
                 from_kall=True):
        self.name = name
        self.parent = parent
        self.from_kall = from_kall


    def __eq__(self, other):
        if other is ANY:
            return True
        try:
            len_other = len(other)
        except TypeError:
            return False

        self_name = ''
        if len(self) == 2:
            self_args, self_kwargs = self
        else:
            self_name, self_args, self_kwargs = self

        other_name = ''
        if len_other == 0:
            other_args, other_kwargs = (), {}
        elif len_other == 3:
            other_name, other_args, other_kwargs = other
        elif len_other == 1:
            value, = other
            if isinstance(value, tuple):
                other_args = value
                other_kwargs = {}
            elif isinstance(value, basestring):
                other_name = value
                other_args, other_kwargs = (), {}
            else:
                other_args = ()
                other_kwargs = value
        else:
            # len 2
            # could be (name, args) or (name, kwargs) or (args, kwargs)
            first, second = other
            if isinstance(first, basestring):
                other_name = first
                if isinstance(second, tuple):
                    other_args, other_kwargs = second, {}
                else:
                    other_args, other_kwargs = (), second
            else:
                other_args, other_kwargs = first, second

        if self_name and other_name != self_name:
            return False

        # this order is important for ANY to work!
        return (other_args, other_kwargs) == (self_args, self_kwargs)


    def __ne__(self, other):
        return not self.__eq__(other)


    def __call__(self, *args, **kwargs):
        if self.name is None:
            return _Call(('', args, kwargs), name='()')

        name = self.name + '()'
        return _Call((self.name, args, kwargs), name=name, parent=self)


    def __getattr__(self, attr):
        if self.name is None:
            return _Call(name=attr, from_kall=False)
        name = '%s.%s' % (self.name, attr)
        return _Call(name=name, parent=self, from_kall=False)


    def __repr__(self):
        if not self.from_kall:
            name = self.name or 'call'
            if name.startswith('()'):
                name = 'call%s' % name
            return name

        if len(self) == 2:
            name = 'call'
            args, kwargs = self
        else:
            name, args, kwargs = self
            if not name:
                name = 'call'
            elif not name.startswith('()'):
                name = 'call.%s' % name
            else:
                name = 'call%s' % name
        return _format_call_signature(name, args, kwargs)


    def call_list(self):
        """For a call object that represents multiple calls, `call_list`
        returns a list of all the intermediate calls as well as the
        final call."""
        vals = []
        thing = self
        while thing is not None:
            if thing.from_kall:
                vals.append(thing)
            thing = thing.parent
        return _CallList(reversed(vals))


call = _Call(from_kall=False)



def create_autospec(spec, spec_set=False, instance=False, _parent=None,
                    _name=None, **kwargs):
    """Create a mock object using another object as a spec. Attributes on the
    mock will use the corresponding attribute on the `spec` object as their
    spec.

    Functions or methods being mocked will have their arguments checked
    to check that they are called with the correct signature.

    If `spec_set` is True then attempting to set attributes that don't exist
    on the spec object will raise an `AttributeError`.

    If a class is used as a spec then the return value of the mock (the
    instance of the class) will have the same spec. You can use a class as the
    spec for an instance object by passing `instance=True`. The returned mock
    will only be callable if instances of the mock are callable.

    `create_autospec` also takes arbitrary keyword arguments that are passed to
    the constructor of the created mock."""
    if _is_list(spec):
        # can't pass a list instance to the mock constructor as it will be
        # interpreted as a list of strings
        spec = type(spec)

    is_type = isinstance(spec, ClassTypes)

    _kwargs = {'spec': spec}
    if spec_set:
        _kwargs = {'spec_set': spec}
    elif spec is None:
        # None we mock with a normal mock without a spec
        _kwargs = {}

    _kwargs.update(kwargs)

    Klass = MagicMock
    if type(spec) in DescriptorTypes:
        # descriptors don't have a spec
        # because we don't know what type they return
        _kwargs = {}
    elif not _callable(spec):
        Klass = NonCallableMagicMock
    elif is_type and instance and not _instance_callable(spec):
        Klass = NonCallableMagicMock

    _new_name = _name
    if _parent is None:
        # for a top level object no _new_name should be set
        _new_name = ''

    mock = Klass(parent=_parent, _new_parent=_parent, _new_name=_new_name,
                 name=_name, **_kwargs)

    if isinstance(spec, FunctionTypes):
        # should only happen at the top level because we don't
        # recurse for functions
        mock = _set_signature(mock, spec)
    else:
        _check_signature(spec, mock, is_type, instance)

    if _parent is not None and not instance:
        _parent._mock_children[_name] = mock

    if is_type and not instance and 'return_value' not in kwargs:
        mock.return_value = create_autospec(spec, spec_set, instance=True,
                                            _name='()', _parent=mock)

    for entry in dir(spec):
        if _is_magic(entry):
            # MagicMock already does the useful magic methods for us
            continue

        if isinstance(spec, FunctionTypes) and entry in FunctionAttributes:
            # allow a mock to actually be a function
            continue

        # XXXX do we need a better way of getting attributes without
        # triggering code execution (?) Probably not - we need the actual
        # object to mock it so we would rather trigger a property than mock
        # the property descriptor. Likewise we want to mock out dynamically
        # provided attributes.
        # XXXX what about attributes that raise exceptions other than
        # AttributeError on being fetched?
        # we could be resilient against it, or catch and propagate the
        # exception when the attribute is fetched from the mock
        try:
            original = getattr(spec, entry)
        except AttributeError:
            continue

        kwargs = {'spec': original}
        if spec_set:
            kwargs = {'spec_set': original}

        if not isinstance(original, FunctionTypes):
            new = _SpecState(original, spec_set, mock, entry, instance)
            mock._mock_children[entry] = new
        else:
            parent = mock
            if isinstance(spec, FunctionTypes):
                parent = mock.mock

            new = MagicMock(parent=parent, name=entry, _new_name=entry,
                            _new_parent=parent, **kwargs)
            mock._mock_children[entry] = new
            skipfirst = _must_skip(spec, entry, is_type)
            _check_signature(original, new, skipfirst=skipfirst)

        # so functions created with _set_signature become instance attributes,
        # *plus* their underlying mock exists in _mock_children of the parent
        # mock. Adding to _mock_children may be unnecessary where we are also
        # setting as an instance attribute?
        if isinstance(new, FunctionTypes):
            setattr(mock, entry, new)

    return mock


def _must_skip(spec, entry, is_type):
    if not isinstance(spec, ClassTypes):
        if entry in getattr(spec, '__dict__', {}):
            # instance attribute - shouldn't skip
            return False
        spec = spec.__class__
    if not hasattr(spec, '__mro__'):
        # old style class: can't have descriptors anyway
        return is_type

    for klass in spec.__mro__:
        result = klass.__dict__.get(entry, DEFAULT)
        if result is DEFAULT:
            continue
        if isinstance(result, (staticmethod, classmethod)):
            return False
        return is_type

    # shouldn't get here unless function is a dynamically provided attribute
    # XXXX untested behaviour
    return is_type


def _get_class(obj):
    try:
        return obj.__class__
    except AttributeError:
        # in Python 2, _sre.SRE_Pattern objects have no __class__
        return type(obj)


class _SpecState(object):

    def __init__(self, spec, spec_set=False, parent=None,
                 name=None, ids=None, instance=False):
        self.spec = spec
        self.ids = ids
        self.spec_set = spec_set
        self.parent = parent
        self.instance = instance
        self.name = name


FunctionTypes = (
    # python function
    type(create_autospec),
    # instance method
    type(ANY.__eq__),
    # unbound method
    type(_ANY.__eq__),
)

FunctionAttributes = set([
    'func_closure',
    'func_code',
    'func_defaults',
    'func_dict',
    'func_doc',
    'func_globals',
    'func_name',
])


file_spec = None


def mock_open(mock=None, read_data=''):
    """
    A helper function to create a mock to replace the use of `open`. It works
    for `open` called directly or used as a context manager.

    The `mock` argument is the mock object to configure. If `None` (the
    default) then a `MagicMock` will be created for you, with the API limited
    to methods or attributes available on standard file handles.

    `read_data` is a string for the `read` method of the file handle to return.
    This is an empty string by default.
    """
    global file_spec
    if file_spec is None:
        # set on first use
        if inPy3k:
            import _io
            file_spec = list(set(dir(_io.TextIOWrapper)).union(set(dir(_io.BytesIO))))
        else:
            file_spec = file

    if mock is None:
        mock = MagicMock(name='open', spec=open)

    handle = MagicMock(spec=file_spec)
    handle.write.return_value = None
    handle.__enter__.return_value = handle
    handle.read.return_value = read_data

    mock.return_value = handle
    return mock


class PropertyMock(Mock):
    """
    A mock intended to be used as a property, or other descriptor, on a class.
    `PropertyMock` provides `__get__` and `__set__` methods so you can specify
    a return value when it is fetched.

    Fetching a `PropertyMock` instance from an object calls the mock, with
    no args. Setting it calls the mock with the value being set.
    """
    def _get_child_mock(self, **kwargs):
        return MagicMock(**kwargs)

    def __get__(self, obj, obj_type):
        return self()
    def __set__(self, obj, val):
        self(val)

########NEW FILE########
__FILENAME__ = command
import sublime_plugin

from php_coverage.data import CoverageDataFactory
from php_coverage.finder import CoverageFinder
from php_coverage.matcher import Matcher


class CoverageCommand(sublime_plugin.TextCommand):

    """
    Base class for a text command which has a coverage file.
    """

    def __init__(self, view, coverage_finder=None, matcher=None):
        super(CoverageCommand, self).__init__(view)
        self.coverage_finder = coverage_finder
        self.matcher = matcher

    def get_coverage_finder(self):
        """
        Gets the coverage finder for the command. If none is set, it
        instantiates an instance of the default CoverageFinder class.
        """
        if not self.coverage_finder:
            self.coverage_finder = CoverageFinder()

        return self.coverage_finder

    def coverage(self):
        """
        Loads coverage data for the file open in the view which is
        running this command.
        """
        filename = self.view.file_name()
        coverage_file = self.get_coverage_finder().find(filename)
        if (coverage_file):
            return CoverageDataFactory().factory(coverage_file)

        return None

    def get_matcher(self):
        """
        Gets the matcher for the command. If none is set, it
        instantiates an instance of the default Matcher class.
        """
        if not self.matcher:
            self.matcher = Matcher()

        return self.matcher

    def should_include(self, filename):
        """
        Determines whether a file should be included or not.
        """
        return self.get_matcher().should_include(filename)

########NEW FILE########
__FILENAME__ = config
from php_coverage.debug import debug_message


class Config():

    """
    Handles retrieval of plugin settings.
    """

    keys = [
        "debug",
        "report_path",
        "watch_report",
        "include",
        "exclude",
    ]

    def __init__(self):
        self.loaded = False

    def load(self):
        """
        Loads the settings from disk into structured data.
        """
        debug_message('[config] Loading config')
        import sublime

        self.filename = "SublimePHPCoverage.sublime-settings"
        self.settings = sublime.load_settings(self.filename)
        self.project = {}

        if sublime.active_window() is not None:
            debug_message('[config] Window is active, loading project')
            project = sublime.active_window().active_view().settings()

            if project.has('phpcoverage'):
                debug_message("[config] Found project settings")
                project.clear_on_change('phpcoverage')
                self.project = project.get('phpcoverage')
                project.add_on_change('phpcoverage', config.load)
            else:
                debug_message("[config] No 'phpcoverage' key, ignoring")

        for key in self.keys:
            self.settings.clear_on_change(key)
            setattr(self, key, self.get_setting(key))
            self.settings.add_on_change(key, config.load)

        self.loaded = True

    def is_loaded(self):
        """
        Determines whether or not the settings have been loaded.
        """
        return self.loaded

    def get_setting(self, key):
        """
        Gets a configuration value by key.
        """
        if key in self.project:
            value = self.project.get(key)
            debug_message("[config] [project] %s: '%s'" % (key, value))
            return value
        else:
            value = self.settings.get(key, None)
            debug_message("[config]: %s: '%s'" % (key, value))
            return value

    def __getattr__(self, key):
        """
        Raise exception when retrieving configuration settings before
        load() is called.
        """
        if key in self.keys:
            if not self.is_loaded():
                raise ConfigurationNotLoaded()
            else:
                raise AttributeError("Unknown configuration key '%s'" % key)


class ConfigurationNotLoaded(Exception):

    """
    An exception representing an attempt to retrieve a configuration
    key before the configuration has been loaded.
    """

    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        if not self.message:
            self.message = "Configuration not ready yet"

        return self.message

config = Config()

########NEW FILE########
__FILENAME__ = data
import os
import xml.etree.ElementTree


class CoverageData():

    """
    Represents a coverage data file.
    """

    def __init__(self, coverage_file):
        self.coverage_file = coverage_file
        self.elements = None
        self.files = {}

    def is_loaded(self):
        """
        Checks if the XML data is loaded from the coverage file.
        """
        return not self.elements is None

    def load(self):
        """
        Loads the XML data from the coverage file.
        """
        self.files = {}
        if os.path.exists(self.coverage_file):
            root = xml.etree.ElementTree.parse(self.coverage_file)
            self.elements = root.findall('./project//file')
        else:
            self.elements = []

    def normalise(self, filename):
        """
        Normalises a filename to aid comparisons.
        """
        return os.path.normcase(os.path.realpath(filename))

    def get_file(self, filename):
        """
        Gets a FileCoverage object for a particular source file, which
        will represent the coverage data for that source file.
        """
        if not self.is_loaded():
            self.load()

        filename = self.normalise(filename)

        # check in self.files cache
        if filename not in self.files:
            self.files[filename] = None

            # find coverage data in the parsed XML coverage file
            for data in self.elements:
                if self.normalise(data.get('name')) == filename:
                    # create FileCoverage with the data
                    self.files[filename] = FileCoverage(filename, data)

        return self.files[filename]


class CoverageDataFactory():

    """
    Creates instances of CoverageData objects.
    """

    def __init__(self, class_name=CoverageData):
        self.class_name = class_name

    def factory(self, coverage_file):
        return self.class_name(coverage_file)


class FileCoverage():

    """
    Represents coverage data for a single file.
    """

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data
        self.parsed = False

    def is_parsed(self):
        """
        Determines whether the coverage data has been parsed into
        structured data.
        """
        return self.parsed

    def parse(self):
        """
        Parses the coverage data into structured data.
        """
        metrics = self.data.find('./metrics')

        self.num_lines = int(metrics.get('loc'))
        self.covered = int(metrics.get('coveredstatements'))
        self.statements = int(metrics.get('statements'))

        self.good_lines = []
        self.bad_lines = []

        for line in self.data.findall('line'):
            # skip non-statement lines
            if line.get('type') != 'stmt':
                continue

            line_number = int(line.get('num'))
            test_count = int(line.get('count'))

            # quirks in the coverage data: skip line #0 and any
            # lines greater than the number of lines in the file
            if line_number == 0 or line_number > self.num_lines:
                continue

            # add this line number to good_lines or bad_lines depending
            # on whether it's covered by at least one test or not
            dest = self.good_lines if test_count > 0 else self.bad_lines
            dest.append(line_number)

        self.parsed = True

    def __getattr__(self, name):
        """
        Automatically parse when attempting to retrieve output values.
        """
        methods = [
            'num_lines',
            'covered',
            'statements',
            'good_lines',
            'bad_lines',
        ]

        if name in methods:
            if not self.is_parsed():
                self.parse()

            return getattr(self, name)

        raise AttributeError()

########NEW FILE########
__FILENAME__ = debug
import threading


def debug_message(message):
    """
    Prints a debug message to the Sublime console
    """
    from php_coverage.config import config
    if config.loaded and config.debug:
        thread = threading.current_thread().name
        print("[PHPCoverage] [%s] %s" % (str(thread), str(message)))

########NEW FILE########
__FILENAME__ = finder
import os

from php_coverage.config import config
from php_coverage.debug import debug_message


class CoverageFinder():

    """
    Finds the filename containing coverage data for a particular file.
    Currently it ascends through parent directories, until it finds
    "build/logs/clover.xml".
    """

    def find(self, filename):
        """
        Finds the coverage file for a given filename.
        """
        # start from the file's directory
        parent, current = os.path.split(os.path.abspath(filename))
        path = os.path.normcase(os.path.normpath(config.report_path))

        # iterate through parent directories until coverage file found
        while current:
            coverage = os.path.join(parent, path)
            if os.path.exists(coverage):
                debug_message("Coverage for %s in %s" % (filename, coverage))
                return coverage

            parent, current = os.path.split(parent)

        debug_message("Coverage file not found for " + str(filename))
        return None

########NEW FILE########
__FILENAME__ = helper
import sublime
from php_coverage.debug import debug_message


sublime3 = int(sublime.version()) >= 3000

if sublime3:
    set_timeout_async = sublime.set_timeout_async
else:
    debug_message("Adding Sublime 3 polyfills")
    set_timeout_async = sublime.set_timeout

########NEW FILE########
__FILENAME__ = matcher
import re

from php_coverage.config import config


class Matcher():

    """
    Matches filenames against patterns to determine whether to include
    them or not.
    """

    def should_include(self, filename):
        """
        Determines whether to include a file or not based on its
        filename and the settings in the plugin configuration.
        """
        return self.included(filename) and not self.excluded(filename)

    def included(self, filename):
        """
        Determines whether a filename is on the "include" list.
        """
        return self.match(config.include, filename)

    def excluded(self, filename):
        """
        Determines whether a filename is on the "exclude" list.
        """
        return self.match(config.exclude, filename)

    def match(self, patterns, string):
        """
        Determines whether a string matches any of a list of patterns.
        """
        for pattern in patterns:
            if re.search(pattern, string):
                return True

        # no patterns matched
        return False

########NEW FILE########
__FILENAME__ = mediator
import os

from php_coverage.config import config
from php_coverage.debug import debug_message
from php_coverage.finder import CoverageFinder
from php_coverage.helper import set_timeout_async
from php_coverage.matcher import Matcher
from php_coverage.watcher import CoverageWatcher


class ViewWatcherMediator():

    """
    Mediates between views and CoverageWatchers.

    The "callbacks" parameter is a dictionary mapping CoverageWatcher
    events to a callback which should be run when that event occurs to
    the coverage file for a view which has been added. The callback
    will be passed the view whose coverage data file has experienced
    the event, as well as a CoverageData object representing the new
    content of the file.

    When calling add(view), a CoverageWatcher will be set up to watch
    the file containing that view's coverage data. When the watcher
    detects an event, this mediator will pass the relevant view to the
    callback so that it can be informed about changes to its code
    coverage data.

    This class re-uses CoverageWatchers, so if there's multiple views
    that need to be notified about the same coverage file, there will
    be only one CoverageWatcher created.

    Calling remove(view) will de-register any watchers that were set
    up for a view by add(view). If this results in a CoverageWatchers
    having no more registered callbacks, that CoverageWatchers will be
    stopped. A new CoverageWatchers will be created and started next
    time a view is added using add(view).
    """

    def __init__(self, callbacks={}, coverage_finder=None, matcher=None):
        self.coverage_finder = coverage_finder or CoverageFinder()
        self.matcher = matcher or Matcher()
        self.callbacks = callbacks
        self.watchers = {}

    def add(self, view):
        """
        Sets up a watcher for a newly opened view.
        """
        if not config.watch_report:
            return

        # find coverage file for the view's file
        filename = view.file_name()

        if filename is None:
            return

        if not self.matcher.should_include(filename):
            debug_message("Ignoring excluded file '%s'" % filename)
            return

        coverage = self.coverage_finder.find(filename)

        # nothing can be done if the coverage file can't be found
        if not coverage:
            return

        # ensure a CoverageWatcher exists for the coverage file
        if not coverage in self.watchers:
            debug_message("Creating CoverageWatcher for " + coverage)
            self.watchers[coverage] = CoverageWatcher(coverage)
        else:
            debug_message("Found existing CoverageWatcher for " + coverage)

        watcher = self.watchers[coverage]

        # add callbacks as defined at construction time, also adding in
        # the relevant view as a parameter to the callback
        for event, callback in self.callbacks.items():
            wrapped = self.prepare_callback(callback, view)
            watcher.add_callback(event, view.id(), wrapped)

        # start the watcher if it's not already running
        if not watcher.is_alive():
            debug_message("Starting CoverageWatcher for " + coverage)
            watcher.start()

    def prepare_callback(self, callback, view):
        """
        Wraps a callback function in a lambda to add a view as an
        additional parameter, and to be run in the main thread.
        """
        return lambda data: set_timeout_async(lambda: callback(view, data), 1)

    def remove(self, view):
        """
        Unregisters any set-up listeners for a recently closed view.
        """
        # loop over the watchers
        for id, watcher in list(self.watchers.items()):
            # delete any callback related to this view
            watcher.remove_callback(view.id())

            # if no more callbacks on this watcher, stop and remove it
            if not watcher.has_callbacks():
                filename = watcher.filename
                debug_message("Stopping CoverageWatcher for '%s'" % filename)
                watcher.stop(1)
                del self.watchers[id]

########NEW FILE########
__FILENAME__ = thread
import threading


class PollingThread(threading.Thread):

    """
    A Thread that polls a resource repeatedly, and which can be stopped
    by calling the stop() method.

    Override the poll() method in a subclass to define the behaviour of
    each "poll" event, which happens every self.tick() seconds.
    """

    def __init__(self):
        super(PollingThread, self).__init__()
        self.stop_event = threading.Event()

    def stop(self, timeout=None):
        """
        Stops the thread, blocking until it terminates. This can be
        called multiple times and will return immediately on subsequent
        invocations.
        """
        self.stop_event.set()
        self.join(timeout)
        if self.is_alive():
            raise Timeout("Timeout waiting for PollingThread to stop")

    def tick(self):
        """
        The timeout between polls, in seconds.
        """
        return 0.1  # seconds

    def run(self):
        """
        This method is called in the separate thread, and handles the
        scheduling of the polling. It waits for the stop event for
        up to self.tick() seconds, then stops if the stop event is set.
        If not, it calls self.poll() and resumes waiting again.
        """
        while True:
            # Effectively the same as time.sleep(self.tick()), but if
            # the stop event gets set, the thread wakes up immediately
            self.stop_event.wait(timeout=self.tick())

            # Terminate the method (and thread) if stop flag is set
            if (self.stop_event.is_set()):
                return

            # Delegate polling behaviour to subclass' poll() method
            self.poll()

    def poll(self):
        """
        Override in subclass to define polling behaviour
        """
        raise NotImplementedError("poll() should be overridden")


class NullPollingThread(PollingThread):

    """
    An example PollingThread which does nothing during its poll action.
    """

    def poll(self):
        """
        Do nothing.
        """
        pass


class Timeout(Exception):

    """
    An exception representing a timeout while trying to stop a thread.
    """

    def __str__():
        if len(args) > 0:
            return args[0]
        else:
            super(Timeout, self).__str__()

########NEW FILE########
__FILENAME__ = updater
import os
import sublime
import xml.etree.ElementTree

from php_coverage.debug import debug_message


class ViewUpdater():

    """
    Handles updating the coverage data shown in a particular view.
    """

    def update(self, view, coverage=None):
        """
        Updates a view with the coverage data in a particular file
        """
        self.remove(view)

        if not coverage:
            return

        self.annotate_lines(
            view=view,
            name='SublimePHPCoverageGood',
            lines=coverage.good_lines,
            scope='markup.inserted',
            icon='dot',
        )

        self.annotate_lines(
            view=view,
            name='SublimePHPCoverageBad',
            lines=coverage.bad_lines,
            scope='markup.deleted',
            icon='bookmark',
        )

        try:
            percentage = 100 * coverage.covered / float(coverage.statements)
        except ZeroDivisionError:
            percentage = 0

        status = '%d/%d lines (%.2f%%)' % (
            coverage.covered, coverage.statements, percentage)
        debug_message('Code coverage: %s' % status)
        view.set_status(
            'SublimePHPCoveragePercentage', 'Code coverage: %s' % status)

    def remove(self, view):
        view.erase_regions('SublimePHPCoverageBad')
        view.erase_regions('SublimePHPCoverageGood')
        view.erase_status('SublimePHPCoveragePercentage')

    def annotate_lines(self, view=None, name=None, lines=[], scope=None, icon=None, **kwargs):
        regions = []
        for line in lines:
            regions.append(view.full_line(view.text_point(line - 1, 0)))

        if len(regions) > 0:
            view.add_regions(name, regions, scope, icon, sublime.HIDDEN)

########NEW FILE########
__FILENAME__ = watcher
import hashlib
import os

from php_coverage.data import CoverageDataFactory
from php_coverage.debug import debug_message
from php_coverage.thread import PollingThread

# Chunk size used to read file in
CHUNK_SIZE = 1024 * 1024


class FileWatcher(PollingThread):

    """
    Watches a file for changes, calling a callback every time the file
    is modified.
    """

    CREATED = 'created'      # didn't exist before, does now
    DELETED = 'deleted'      # existed before, doesn't now
    MODIFIED = 'modified'    # mtime changed, different content
    UNCHANGED = 'unchanged'  # mtime changed, same content

    def __init__(self, filename):
        super(FileWatcher, self).__init__()
        self.filename = filename
        self.callbacks = {
            self.CREATED: {},
            self.DELETED: {},
            self.MODIFIED: {},
            self.UNCHANGED: {},
        }

    def add_callback(self, events, id, callback):
        """
        Adds a new callback function for particular events. When one of
        the events in "events" occurs, callback will be called without
        any arguments.
        """
        # make events a list if only one passed in
        if type(events) is not list:
            events = [events]

        # add callback to each event in events
        for event in events:
            if not id in self.callbacks[event]:
                self.callbacks[event][id] = callback

    def has_callbacks(self):
        """
        Determines whether or not this FileWatcher has any callbacks.
        Returns True if at least one callback exists for at least one
        event, otherwise False.
        """
        for callbacks in self.callbacks.values():
            for callback in callbacks.values():
                return True

        return False

    def remove_callback(self, id):
        """
        Removes an existing callback for particular events. The "id"
        parameter identifies the callback by the same "id" parameter
        passed to add_callback() initally.
        """
        # remove callback from each event, if it exists
        for event in self.callbacks:
            if id in self.callbacks[event]:
                del self.callbacks[event][id]

    def dispatch(self, event):
        """
        Dispatches an event, calling all relevant callbacks.
        """
        callbacks = self.callbacks[event]

        debug_message("[FileWatcher] %s '%s'" % (event, self.filename))
        debug_message("[FileWatcher] %d callbacks" % len(callbacks))

        for callback in callbacks.values():
            debug_message("[FileWatcher] Calling %s" % repr(callback))
            callback()

    def hash(self):
        """
        Gets the hash of the file referred to by self.filename. Returns
        None if the file doesn't exist.
        """
        if not os.path.exists(self.filename):
            return None

        sha1 = hashlib.sha1()
        with open(self.filename, 'rb') as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                sha1.update(data)

        return sha1.digest()

    def mtime(self):
        """
        Gets the last modified time of the file referred to by
        self.filename. Returns None if the file doesn't exist.
        """
        if not os.path.exists(self.filename):
            return None

        return os.path.getmtime(self.filename)

    def start(self):
        self.last_mtime = self.mtime()
        self.last_hash = self.hash()
        if self.last_mtime:
            debug_message("[FileWatcher] exists: %s" % self.filename)
        else:
            debug_message("[FileWatcher] doesn't exist: %s" % self.filename)
        super(FileWatcher, self).start()

    def poll(self):
        """
        Checks the modified time of the file and dispatches events
        representing any changes to it.
        """
        new_mtime = self.mtime()

        # if unchanged, do nothing
        if self.last_mtime == new_mtime:
            return

        new_hash = self.hash()

        # otherwise dispatch the corresponding event
        if not self.last_mtime:
            self.dispatch(self.CREATED)
        elif not new_mtime:
            self.dispatch(self.DELETED)
        elif self.last_hash != new_hash:
            self.dispatch(self.MODIFIED)
        else:
            self.dispatch(self.UNCHANGED)

        # save new mtime for next poll
        self.last_mtime = new_mtime
        self.last_hash = new_hash


class CoverageWatcher(FileWatcher):

    """
    A FileWatcher which looks for changes to a coverage file, and
    passes extra coverage-related data to the event callbacks.
    """

    def __init__(self, filename, coverage_factory=None):
        super(CoverageWatcher, self).__init__(filename)
        self.coverage_factory = coverage_factory

    def get_coverage_factory(self):
        """
        Gets the coverage factory for this CoverageWatcher. If none is
        set, it instantiates an instance of the CoverageDataFactory
        class as a default.
        """
        if not self.coverage_factory:
            self.coverage_factory = CoverageDataFactory()

        return self.coverage_factory

    def dispatch(self, event):
        """
        Dispatches an event, calling all relevant callbacks.

        Overridden to pass coverage data to the callback, taken from
        the coverage file being watched by this CoverageWatcher.
        """
        callbacks = self.callbacks[event]

        debug_message("[CoverageWatcher] %s '%s'" % (event, self.filename))
        debug_message("[CoverageWatcher] %d callbacks" % len(callbacks))

        data = self.get_coverage_factory().factory(self.filename)

        for callback in callbacks.values():
            debug_message("[CoverageWatcher] Calling %s" % repr(callback))
            callback(data)

########NEW FILE########
__FILENAME__ = SublimePHPCoverage
import os
import sys
import sublime
import sublime_plugin

# Add current directory to Python's import path, to import php_coverage
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from php_coverage.command import CoverageCommand
from php_coverage.config import config
from php_coverage.debug import debug_message
from php_coverage.helper import set_timeout_async, sublime3
from php_coverage.mediator import ViewWatcherMediator
from php_coverage.updater import ViewUpdater
from php_coverage.watcher import FileWatcher


mediator = ViewWatcherMediator({
    FileWatcher.CREATED: lambda view, data: update_view(view, data),
    FileWatcher.MODIFIED: lambda view, data: update_view(view, data),
    FileWatcher.DELETED: lambda view, data: update_view(view, data),
})


def update_view(view, coverage=None):
    """
    Updates the coverage data displayed in a view.

    Arguments are the view to update, and the coverage data. The
    coverage data should be a CoverageData object, which contains
    the relevant coverage data for the file shown in the view. If the
    coverage data doesn't exist for the file shown in the view, or the
    coverage data is None, then the displayed coverage data will be
    removed from the view.
    """

    filename = view.file_name()
    debug_message('Updating coverage for ' + filename)

    file_coverage = coverage.get_file(filename) if coverage else None
    ViewUpdater().update(view, file_coverage)


def plugin_loaded():
    """
    Called automatically by Sublime when the API is ready to be used.
    Updates coverage for any open views, and adds them to the mediator.
    """

    config.load()

    # add open views to the mediator
    for window in sublime.windows():
        debug_message("[plugin_loaded] Found window %d" % window.id())
        for view in window.views():
            debug_message("[plugin_loaded] Found view %d" % view.id())
            mediator.add(view)
            set_timeout_async(
                lambda: view.run_command('phpcoverage_update'),
                1
            )

    debug_message("[plugin_loaded] Finished.")


class NewFileEventListener(sublime_plugin.EventListener):

    """
    An event listener that receives notifications about new files being
    opened in Sublime. Whenever a new file is opened or created, it
    creates a new FileWatcher for the relevant coverage file which
    contains the coverage data for the file being edited by the user.
    """

    def on_load_async(self, view):
        """
        Sets up a listener for the file that was just opened, and also
        update the code coverage to show it in the newly opened view.
        """
        mediator.add(view)
        view.run_command('phpcoverage_update')

    def on_load(self, view):
        """
        Synchronous fallback for on_load_async() for Sublime 2
        """
        if not sublime3:
            self.on_load_async(view)

    def on_close(self, view):
        """
        Unregister any listeners for the view that was just closed.
        """
        set_timeout_async(lambda: mediator.remove(view), 1)


class PhpcoverageUpdateCommand(CoverageCommand, sublime_plugin.TextCommand):

    """
    Updates the code coverage data for a file in a view.
    """

    def run(self, edit, coverage=None, **kwargs):
        filename = self.view.file_name()

        if filename is None:
            return

        if not self.should_include(filename):
            debug_message("Ignoring excluded file '%s'" % filename)
            return

        if not coverage:
            coverage = self.coverage()

        update_view(self.view, coverage)


class PhpcoverageUpdateAllCommand(CoverageCommand, sublime_plugin.TextCommand):

    """
    Updates the code coverage data for files in all open views.
    """

    def run(self, edit):
        windows = sublime.windows() or []

        for window in windows:
            views = window.views() or []

            for view in views:
                view.run_command("phpcoverage_update")


if not sublime3:
    plugin_loaded()

########NEW FILE########
__FILENAME__ = testdata
import os
import unittest
import xml.etree.ElementTree

from php_coverage.data import CoverageData
from php_coverage.data import FileCoverage


class CoverageDataTest(unittest.TestCase):

    def setUp(self):
        file = os.path.join(os.path.dirname(__file__), 'data', 'test.xml')
        self.data = CoverageData(file)

    def test_is_loaded(self):
        self.assertFalse(self.data.is_loaded())
        self.data.elements = []
        self.assertTrue(self.data.is_loaded())

    def test_load(self):
        self.data.load()
        self.assertTrue(self.data.is_loaded())
        self.assertEquals(self.data.files, {})

    def test_load_nonexistent_file(self):
        self.data = CoverageData('/path/to/nonexistent/coverage.xml')
        self.data.load()
        self.assertTrue(self.data.is_loaded())
        self.assertEquals(self.data.elements, [])
        self.assertEquals(self.data.files, {})

    def test_normalise(self):
        out = self.data.normalise('/path/to/../the/../../file')
        self.assertEquals(out, '/file')

    def test_get_file(self):
        self.data.load()
        coverage = self.data.get_file('/path/to/file.php')
        self.assertIsInstance(coverage, FileCoverage)

    def test_get_file_implicit_load(self):
        coverage = self.data.get_file('/path/to/file.php')
        self.assertIsInstance(coverage, FileCoverage)

    def test_get_file_invalid(self):
        self.data.load()
        coverage = self.data.get_file('/path/to/nonexistent/file.php')
        self.assertIs(coverage, None)


class FileCoverageTest(unittest.TestCase):

    def setUp(self):
        file = os.path.join(os.path.dirname(__file__), 'data', 'test.xml')
        tree = xml.etree.ElementTree.parse(file)
        element = tree.findall('./project//file')[0]
        self.coverage = FileCoverage('/path/to/file.php', element)

    def test_is_parsed(self):
        self.assertFalse(self.coverage.is_parsed())
        self.coverage.parse()
        self.assertTrue(self.coverage.is_parsed())

    def test_parse(self):
        self.coverage.parse()
        self.assertEquals(self.coverage.num_lines, 16)
        self.assertEquals(self.coverage.covered, 0)
        self.assertEquals(self.coverage.statements, 4)
        self.assertEquals(self.coverage.good_lines, [])
        self.assertEquals(self.coverage.bad_lines, [12, 13, 14, 15])

    def test_get_implicit_parse(self):
        self.assertEquals(self.coverage.num_lines, 16)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testfinder
import os
import unittest

from php_coverage.config import config
from php_coverage.finder import CoverageFinder


class CoverageFinderTest(unittest.TestCase):

    def setUp(self):
        config.loaded = True
        config.debug = True
        config.report_path = 'foo/bar/baz.xml'
        self.finder = CoverageFinder()
        dir = os.path.join(os.path.dirname(__file__), 'finder')
        self.invalid_src = dir
        self.src = os.path.join(dir, 'src', 'path', 'test.php')
        self.coverage = os.path.join(dir, 'foo', 'bar', 'baz.xml')

    def tearDown(self):
        config.loaded = False
        del config.debug
        del config.report_path

    def test_find(self):
        self.assertEquals(self.finder.find(self.src), self.coverage)

    def test_find_invalid(self):
        self.assertIs(self.finder.find(self.invalid_src), None)

########NEW FILE########
__FILENAME__ = testmatcher
import unittest

from php_coverage.config import config
from php_coverage.matcher import Matcher


class MatcherTest(unittest.TestCase):

    def setUp(self):
        config.loaded = True
        # config.debug = True
        config.include = [r"foo.*\.php$", r"win[\\/]do[\\/]ws\.php"]
        config.exclude = [r"foo.*bar\.php$", "foofoo\.php$"]
        self.matcher = Matcher()

    def tearDown(self):
        config.loaded = False
        # del config.debug
        del config.include
        del config.exclude

    def test_should_include(self):
        self.assertTrue(self.matcher.should_include('foo.php'))
        self.assertFalse(self.matcher.should_include('foobar.php'))
        self.assertFalse(self.matcher.should_include('thefoofoo.php'))
        self.assertFalse(self.matcher.should_include('feet.php'))
        self.assertTrue(self.matcher.should_include('win\\do/ws.php'))

    def test_included(self):
        self.assertTrue(self.matcher.included('foo.php'))
        self.assertTrue(self.matcher.included('foobar.php'))
        self.assertTrue(self.matcher.included('thefoofoo.php'))
        self.assertFalse(self.matcher.included('feet.php'))
        self.assertTrue(self.matcher.included('win\\do/ws.php'))

    def test_excluded(self):
        self.assertFalse(self.matcher.excluded('foo.php'))
        self.assertTrue(self.matcher.excluded('foobar.php'))
        self.assertTrue(self.matcher.excluded('thefoofoo.php'))
        self.assertFalse(self.matcher.excluded('feet.php'))
        self.assertFalse(self.matcher.excluded('win\\do/ws.php'))

    def test_match(self):
        patterns = [r"test.+test", r"newtest"]
        self.assertTrue(self.matcher.match(patterns, 'testthistest'))
        self.assertTrue(self.matcher.match(patterns, 'mynewtester'))
        self.assertFalse(self.matcher.match(patterns, 'testtest'))
        self.assertFalse(self.matcher.match(patterns, 'newesttest'))

########NEW FILE########
__FILENAME__ = testthread
import unittest

from php_coverage.thread import NullPollingThread
from php_coverage.thread import PollingThread
from php_coverage.thread import Timeout


class NullPollingThreadTest(unittest.TestCase):

    def setUp(self):
        self.thread = NullPollingThread()

    def test_stop(self):
        self.thread.start()
        self.assertTrue(self.thread.is_alive())
        self.thread.stop(0.5)
        self.assertFalse(self.thread.is_alive())

    def test_stop_unsuccessful(self):
        self.thread.start()
        self.assertTrue(self.thread.is_alive())
        with self.assertRaises(Timeout):
            self.thread.stop(0)

    def test_poll_is_abstract(self):
        with self.assertRaises(NotImplementedError):
            PollingThread().poll()

########NEW FILE########
__FILENAME__ = testwatcher
import os
import sys
import threading
import unittest

from php_coverage.watcher import CoverageWatcher, FileWatcher

if sys.version_info >= (3, 3):
    from unittest.mock import Mock, MagicMock
else:
    path = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(os.path.join(path, '..', 'dist'))
    from mock import Mock, MagicMock

CREATED = FileWatcher.CREATED
DELETED = FileWatcher.DELETED
MODIFIED = FileWatcher.MODIFIED
UNCHANGED = FileWatcher.UNCHANGED


class TestFileWatcher(unittest.TestCase):

    def setUp(self):
        dir = os.path.join(os.path.dirname(__file__), 'watcher')
        if not os.path.exists(dir):
            os.mkdir(dir)
        self.file = os.path.join(dir, 'test.txt')
        self.watcher = FileWatcher(self.file)
        self.detected = threading.Event()
        self.delete()

    def tearDown(self):
        if self.watcher.is_alive():
            self.watcher.stop(1)

        assert(not self.watcher.is_alive())

    def test_created(self):
        self.watcher.add_callback(CREATED, 1, lambda: self.detected.set())
        self.watcher.start()
        self.create('created')
        self.assertTrue(self.detected.wait(1))

    def test_deleted(self):
        self.watcher.add_callback(DELETED, 1, lambda: self.detected.set())
        self.create('deleted')
        self.watcher.start()
        self.delete()
        self.assertTrue(self.detected.wait(1))

    def test_modified(self):
        self.watcher.add_callback(MODIFIED, 1, lambda: self.detected.set())
        self.create('modified1')
        self.watcher.start()
        self.modify('modified2')
        self.assertTrue(self.detected.wait(1))

    def test_unchanged(self):
        self.watcher.add_callback(UNCHANGED, 1, lambda: self.detected.set())
        self.create('unchanged')
        self.watcher.start()
        self.modify('unchanged')
        self.assertTrue(self.detected.wait(1))

    def create(self, content):
        if not os.path.exists(os.path.dirname(self.file)):
            os.mkdir(os.path.dirname(self.file))

        with open(self.file, 'w') as file:
            file.write(content)

    def modify(self, content):
        self.create(content)

        # bump mtime 10s into the future
        new_atime = os.path.getatime(self.file) + 10
        new_mtime = os.path.getmtime(self.file) + 10
        os.utime(self.file, (new_atime, new_mtime))

    def delete(self):
        if os.path.exists(self.file):
            os.remove(self.file)


class TestCoverageWatcher(TestFileWatcher):

    def setUp(self):
        dir = os.path.dirname(__file__)
        self.file = os.path.join(dir, 'watcher', 'test.txt')

        factory = Mock()
        factory.factory = MagicMock(return_value='return')

        self.watcher = CoverageWatcher(self.file, factory)
        self.detected = threading.Event()
        self.delete()

    def tearDown(self):
        super(TestCoverageWatcher, self).tearDown()
        factory = self.watcher.get_coverage_factory()
        factory.factory.assert_called_once_with(self.file)

    def test_created(self):
        self.watcher.add_callback(CREATED, 1, lambda x: self.detect(x))
        self.watcher.start()
        self.create('created')
        self.assertTrue(self.detected.wait(1))

    def test_deleted(self):
        self.watcher.add_callback(DELETED, 1, lambda x: self.detect(x))
        self.create('deleted')
        self.watcher.start()
        self.delete()
        self.assertTrue(self.detected.wait(1))

    def test_modified(self):
        self.watcher.add_callback(MODIFIED, 1, lambda x: self.detect(x))
        self.create('modified1')
        self.watcher.start()
        self.modify('modified2')
        self.assertTrue(self.detected.wait(1))

    def test_unchanged(self):
        self.watcher.add_callback(UNCHANGED, 1, lambda x: self.detect(x))
        self.create('unchanged')
        self.watcher.start()
        self.modify('unchanged')
        self.assertTrue(self.detected.wait(1))

    def detect(self, data):
        "Perform callback parameter assertions and set detected event"
        self.assertEquals(data, 'return')
        self.detected.set()

########NEW FILE########
