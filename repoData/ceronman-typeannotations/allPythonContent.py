__FILENAME__ = overload
# Copyright 2013 Moritz Sichert
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.  See the License for the specific language
# governing permissions and limitations under the License.

import collections
import inspect


_empty_func = lambda *args: None
_empty_annotation = inspect.Parameter.empty


def _ann_cmp(ann1, ann2):
    """
    Compares two annotations and returns True if ann1 is more specific
    than ann2.
    """
    return ann1 != ann2 and (ann2 == _empty_annotation or issubclass(ann1, ann2))


def _get_annotations(func):
    return (param.annotation for param in inspect.signature(func).parameters.values())


def _func_eq(func1, func2):
    """
    Returns True if the two functions's signatures evaluate to the same types.

    Arguments:
    func1, func2: Functions that are supported by inspect.signature.
                  Both must have same number of arguments.
    """
    # That's how the algorithm works:
    # First check if the functions aren't equal (obvious).
    # Then check if the annotations aren't all equal, too.
    # 
    # Now basically we create a table with following structure:
    # 
    #                             | annotation1 | annotation2 | annot3 | ...
    # ------------------------------------------------------------------------
    # #1 | _ann_cmp(func1, func2) |    True     |    False    |  False | ...
    # #2 | _ann_cmp(func2, func1) |    False    |    False    |  True  | ...
    # #3 | func1 == func2         |    False    |    True     |  False | ...
    # 
    # funcN means: "Take funcN's Mth annotation" where M is the number shown in
    # the column caption.
    # 
    # First we get rid of all columns with True in row #3. We also don't need
    # row #3 anymore.
    # 
    #    | annotation1 | annotation3 | ...
    # --------------------------------------
    # #1 |    True     |    False    | ...
    # #2 |    False    |    True     | ...
    # 
    # Then we generate a new row called #1+2 by combining #1 and #2 with
    # logical or
    # 
    #      | annotation1 | annotation3 | ...
    # ----------------------------------------
    # #1   |    True     |    False    | ...
    # #2   |    False    |    True     | ...
    # #1+2 |    True     |    True     | ...
    # 
    # The last step is to check if #1+2 is equal with #1 or #2. If it is,
    # return False, otherwise return True.
    # 
    # Why does it work?
    # #TODO
    if func1 == func2:
        return True
    if func1 == _empty_func or func2 == _empty_func:
        return False
    # grab all annotations
    # annotations = [[func1ann1, func2ann1], [func1ann2, func2ann2], ...]
    annotations = tuple(zip(*[_get_annotations(func) for func in (func1, func2)]))
    if all(ann1 == ann2 for ann1, ann2 in annotations):
        return True
    # generate #1 and #2 and leave out the ones with True in #3
    annotations = [(_ann_cmp(ann1, ann2), _ann_cmp(ann2, ann1)) for ann1, ann2 in annotations if ann1!=ann2]
    # calculate #1+2
    annotations_combined = tuple(ann1 or ann2 for ann1, ann2 in annotations)
    return annotations_combined not in zip(*annotations)


def _func_cmp(func1, func2):
    """
    Compares two functions by their signatures.

    Arguments:
    func1, func2: Functions that are supported by inspect.signature.
                  Both must have same number of arguments.

    Returns:
    True if func1's argument annotation types have stronger or as strong types
    than func2's ones.
    False else.
    """
    if func1 == func2:
        return False
    if func1 == _empty_func:
        return False
    elif func2 == _empty_func:
        return True
    for ann1, ann2 in zip(*[_get_annotations(func) for func in (func1, func2)]):
        if ann1 == ann2:
            continue
        if ann2 == _empty_annotation:
            continue
        if not issubclass(ann1, ann2):
            return False
    return True


def _check_func_types(func, types):
    return all((typ == ann) or issubclass(typ, ann) for typ, ann in zip(types, _get_annotations(func)) if ann != _empty_annotation)


class AmbiguousFunction(ValueError):
    """
    Gets raised if trying to add a function to a FunctionHeap if an equivalent
    one is already in it.
    """
    def __init__(self, func):
        ValueError.__init__(self,
            'function {0} is ambiguous with an existing one'.format(func))


class FunctionNotFound(Exception):
    """
    Gets raised if a function with given types couldn't be found.
    """
    pass


class FunctionHeap(object):
    def __init__(self, func):
        self._root = func
        self._childs = set()

    def push(self, func):
        if _func_eq(func, self._root):
            raise AmbiguousFunction(func)
        if self._root == _empty_func:
            if all(_func_cmp(child._root, func) for child in self._childs):
                self._root = func
        elif _func_cmp(func, self._root):
            if any(_func_eq(func, child._root) for child in self._childs):
                raise AmbiguousFunction(func)
            for child in self._childs:
                if _func_cmp(func, child._root):
                    child.push(func)
                    return
            self._childs.add(self.__class__(func))
        else:
            old_heap = self.__class__(self._root)
            old_heap._childs = self._childs
            if _func_cmp(self._root, func):
                self._root = func
                self._childs = set([old_heap])
            else:
                new_heap = self.__class__(func)
                self._root = _empty_func
                self._childs = set([old_heap, new_heap])

    def find(self, types):
        """
        Finds the most specialized function for args.
        For example if args where (1,2,'foo', 'bar') and the Heap had the childs
        foo(a:int,b,c,d) and bar(a:int,b,c:str,d) it would choose bar.

        Arguments:
        *args: all types that the function should accept
        """
        if self._root != _empty_func and not _check_func_types(self._root, types):
            raise FunctionNotFound()
        current_heap = self
        new_root = True
        while new_root:
            new_root = False
            for child in current_heap._childs:
                if _check_func_types(child._root, types):
                    current_heap = child
                    new_root = True
        if current_heap._root == _empty_func:
            raise FunctionNotFound()
        return current_heap._root


class OverloadedFunction(collections.Callable):
    def __init__(self, module, name):
        self._module = module
        self._name = name
        self._functions = {} # {arg_len: FunctionHeap, ...}
        self._function_cache = {} # {(type1, type2, ...): func, ...}
    
    def add_function(self, func):
        parameters = inspect.signature(func).parameters
        for param in parameters.values():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                raise TypeError('functions with *args and **kwargs are not supported')
        if len(parameters) not in self._functions:
            self._functions[len(parameters)] = FunctionHeap(func)
        else:
            self._functions[len(parameters)].push(func)
        self._function_cache = {}
    
    def __call__(self, *args):
        types = tuple(type(arg) for arg in args)
        if types in self._function_cache:
            return self._function_cache[types](*args)
        if len(args) not in self._functions:
            raise FunctionNotFound('No function found for signature: {0}'.format(types))
        else:
            func = self._functions[len(args)].find(types)
            self._function_cache[types] = func
            return func(*args)


_overloaded_functions = {} # {'module': {'function_name': OverloadedFunction, ...}, ...}


def overloaded(func):
    """
    Decorator that lets you declare the same function various times with
    different type annotations.
    """
    module = func.__module__
    qualname = func.__qualname__
    if module not in _overloaded_functions:
        _overloaded_functions[module] = {}
    if qualname not in _overloaded_functions[module]:
        _overloaded_functions[module][qualname] = OverloadedFunction(module, qualname)
    _overloaded_functions[module][qualname].add_function(func)
    return _overloaded_functions[module][qualname]

########NEW FILE########
__FILENAME__ = typed
# Written by Manuel Cerón

# Copyright Manuel Cerón.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.  See the License for the specific language
# governing permissions and limitations under the License.

"""Tools for adding type annotations in Python.

This module provides a set of tools for type checking and annotations:

- typechecked() provides a decorator for checking the types in annotations.
- Interface provides a subclass to define structural interfaces.
- union() provides a group of types.
- predicate() provides type that checks a precondition.
"""

__author__ = ('Manuel Cerón <ceronman@gmail.com>')
__all__ = ['AnyType', 'Interface', 'only', 'optional', 'options', 'predicate',
           'typechecked', 'typedef', 'union']

import functools
import inspect

EMPTY_ANNOTATION = inspect.Signature.empty


class UnionMeta(type):
    """Metaclass for union types.

    An object is an instance of a union type if it is instance of any of the
    members of the union.

    >>> NumberOrString = union(int, str)
    >>> isinstance(1, NumberOrString)
    True
    >>> isinstance('string', NumberOrString)
    True
    >>> issubclass(int, NumberOrString)
    True
    >>> issubclass(str, NumberOrString)
    True
    """
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)
        types = getattr(cls, '__types__', None)
        if not isinstance(types, set):
            raise TypeError('Union requires a __types__ set')

        if any(not isinstance(t, type) for t in types):
            raise TypeError('Union __types__ elements must be type')
        return cls

    def __instancecheck__(cls, instance):
        """Override for isinstance(instance, cls)."""
        return any(isinstance(instance, t) for t in cls.__types__)

    def __subclasscheck__(cls, subclass):
        """Override for isinstance(instance, cls)."""
        if isinstance(subclass, UnionMeta):
            return all(issubclass(t, cls) for t in subclass.__types__)
        return any(issubclass(subclass, t) for t in cls.__types__)

    def __repr__(cls):
        return '<union {0}>'.format(repr(cls.__types__))


def union(*args):
    """A convenience function for creating unions. See UnionMeta."""
    return UnionMeta('union', (), {'__types__': set(args)})


class AnyTypeMeta(type):
    """Metaclass for AnyType.

    Any object is instance of AnyType and any type is sublcass of anytype.

    >>> isinstance(1, AnyType)
    True
    >>> isinstance(None, AnyType)
    True
    >>> isinstance('string', AnyType)
    True
    >>> issubclass(int, AnyType)
    True
    >>> issubclass(str, AnyType)
    True
    >>> issubclass(None, AnyType)
    True
    """
    def __new__(mcls, name, bases, namespace):
        return super().__new__(mcls, name, bases, namespace)

    def __instancecheck__(cls, instance):
        """Override for isinstance(instance, cls)."""
        return True

    def __subclasscheck__(cls, subclass):
        """Override for isinstance(instance, cls)."""
        return True


class AnyType(metaclass=AnyTypeMeta):
    """See AnyTypeMeta."""
    pass


def _implements_signature(function, signature):
    """True if the given function implements the given inspect.Signature."""
    try:
        instance_signature = inspect.signature(function)
    except TypeError:
        return False
    except ValueError: # we got a builtin.
        return True

    cls_params = signature.parameters.values()
    instance_params = instance_signature.parameters.values()
    if len(cls_params) != len(instance_params):
        return False

    for cls_param, instance_param in zip(cls_params, instance_params):
        if cls_param.name != instance_param.name:
            return False

        cls_annotation = cls_param.annotation
        instance_annotation = instance_param.annotation

        if cls_annotation is EMPTY_ANNOTATION:
            cls_annotation = AnyType

        if instance_annotation is EMPTY_ANNOTATION:
            instance_annotation = AnyType

        if not issubclass(cls_annotation, instance_annotation):
            return False


    cls_annotation = signature.return_annotation
    instance_annotation = instance_signature.return_annotation

    if cls_annotation is EMPTY_ANNOTATION:
        cls_annotation = AnyType

    if instance_annotation is EMPTY_ANNOTATION:
        instance_annotation = AnyType

    if not issubclass(instance_annotation, cls_annotation):
        return False
    return True


class InterfaceMeta(type):
    """Metaclass for an Interface.

    An interface defines a set methods and attributes that an object must
    implement. Any object implementing those will be considered an instance of
    the interface.

    >>> class IterableWithLen(Interface):
    ...     def __iter__():
    ...             pass
    ...     def __len__():
    ...             pass
    ...
    >>> isinstance([], IterableWithLen)
    True
    >>> isinstance({}, IterableWithLen)
    True
    >>> isinstance(1, IterableWithLen)
    False
    >>> isinstance(iter([]), IterableWithLen)
    False
    >>> issubclass(list, IterableWithLen)
    True
    >>> issubclass(int, IterableWithLen)
    False
    >>> class Person(Interface):
    ...     name = str
    ...     age = int
    ...     def say_hello(name: str) -> str:
    ...             pass
    ...
    >>> class Developer:
    ...     def __init__(self, name, age):
    ...             self.name = name
    ...             self.age = age
    ...     def say_hello(self, name: str) -> str:
    ...             return 'hello ' + name
    ...
    >>> isinstance(Developer('dave', 20), Person)
    True
    """

    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)
        # TODO: check base classes, prevent multiple inheritance.
        cls.__signatures__ = {}
        cls.__attributes__ = {}
        for name, value in namespace.items():
            if name in ('__qualname__', '__module__', '__doc__'):
                continue
            if inspect.isfunction(value):
                mcls.add_method(cls, value)
                continue

            mcls.add_attribute(cls, name, value)
        return cls

    def __instancecheck__(cls, instance):
        """Override for isinstance(instance, cls)."""
        for name, type_ in cls.__attributes__.items():
            try:
                attribute = getattr(instance, name)
            except AttributeError:
                return False

            if not isinstance(attribute, type_):
                return False

        for name, signature in cls.__signatures__.items():
            function = getattr(instance, name, None)
            if not _implements_signature(function, signature):
                return False
        return True

    def __subclasscheck__(cls, subclass):
        """Override for isinstance(instance, cls)."""
        if cls is subclass:
            return True

        # TODO: support attributes
        for name, signature in cls.__signatures__.items():
            try:
                function = inspect.getattr_static(subclass, name)
            except AttributeError:
                return False
            if isinstance(function, (staticmethod, classmethod)):
                return False
            try:
                subclass_signature = inspect.signature(function)
            except TypeError:
                return False
            except ValueError: # we probably got a builtin
                return True

            cls_params = list(signature.parameters.values())
            subclass_params = list(subclass_signature.parameters.values())

            subclass_params.pop(0) # remove 'self'

            if len(cls_params) != len(subclass_params):
                return False

            for cls_param, instance_param in zip(cls_params, subclass_params):
                if cls_param.name != instance_param.name:
                    return False

                cls_annotation = cls_param.annotation
                instance_annotation = instance_param.annotation

                if cls_annotation is EMPTY_ANNOTATION:
                    cls_annotation = AnyType

                if instance_annotation is EMPTY_ANNOTATION:
                    instance_annotation = AnyType

                if not issubclass(cls_annotation, instance_annotation):
                    return False


            cls_annotation = signature.return_annotation
            instance_annotation = subclass_signature.return_annotation

            if cls_annotation is EMPTY_ANNOTATION:
                cls_annotation = AnyType

            if instance_annotation is EMPTY_ANNOTATION:
                instance_annotation = AnyType

            if not issubclass(instance_annotation, cls_annotation):
                return False
        return True

    def add_method(cls, method):
        """Adds a new method to an Interface."""
        # TODO check that signatures contain only types as annotations.
        try:
            cls.__signatures__[method.__name__] = inspect.signature(method)
        except (TypeError, AttributeError):
            raise TypeError('Interface methods should have a signature')
        return method

    def add_attribute(cls, name, type_=AnyType):
        """Adds a new attribute to an Interface."""
        if not isinstance(type_, type):
            # TODO the error message below is incomplete.
            raise TypeError('Interface attributes should be type')
        cls.__attributes__[name] = type_


class Interface(metaclass=InterfaceMeta):
    """See InterfaceMeta."""
    pass


class PredicateMeta(type):
    """Metaclass for a predicate.

    An object is an instance of a predicate if applying the predicate to the
    object returns True.

    >>> Positive = predicate(lambda x: x > 0)
    >>> isinstance(1, Positive)
    True
    >>> isinstance(0, Positive)
    False
    """
    def __new__(mcls, name, bases, namespace):
        return super().__new__(mcls, name, bases, namespace)

    def __instancecheck__(cls, instance):
        try:
            return cls.__predicate__(instance)
        except AttributeError:
            return False

    def __subclasscheck__(cls, subclass):
        return False


def predicate(function, name=None):
    """Convenience function to create predicates. See PredicateMeta.

    >>> Even = predicate(lambda x: x % 2 == 0)
    >>> isinstance(2, Even)
    True
    >>> isinstance(1, Even)
    False
    """
    name = name or function.__name__
    return PredicateMeta(name, (), {'__predicate__': function})


def optional(type_):
    """Optional type predicate. An object can be None or the specified type.

    >>> isinstance(1, optional(int))
    True
    >>> isinstance(None, optional(int))
    True
    """
    return predicate(lambda x: (x is None or isinstance(x, type_)), 'optional')


def typedef(function):
    """A type representing a given function signature.

    It should be used as decorator:

    >>> @typedef
    ... def callback(a: int) -> int:
    ...     pass
    ...
    >>> def handler(a: int) -> int:
    ...     return a
    ...
    >>> isinstance(handler, callback)
    True
    >>> isinstance(lambda x: x, callback)
    False
    """
    signature = inspect.signature(function)
    return predicate(lambda x: _implements_signature(x, signature), 'typedef')


def options(*args):
    """A predicate type for a set of predefined values.

    >>> Days = options('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
    >>> isinstance('mon', Days)
    True
    >>> isinstance('other', Days)
    False
    """
    return predicate(lambda x: x in args, 'options')


def only(type_):
    """A predicate requiring an exact type, not super classes.

    >>> isinstance(True, only(bool))
    True
    >>> isinstance(1, only(bool))
    False
    """
    return predicate(lambda x: type(x) is type_, 'only')


def _check_argument_types(signature, *args, **kwargs):
    """Check that the arguments of a function match the given signature."""
    bound_arguments = signature.bind(*args, **kwargs)
    parameters = signature.parameters
    for name, value in bound_arguments.arguments.items():
        annotation = parameters[name].annotation
        if annotation is EMPTY_ANNOTATION:
            annotation = AnyType
        if not isinstance(value, annotation):
            raise TypeError('Incorrect type for "{0}"'.format(name))


def _check_return_type(signature, return_value):
    """Check that the return value of a function matches the signature."""
    annotation = signature.return_annotation
    if annotation is EMPTY_ANNOTATION:
        annotation = AnyType
    if not isinstance(return_value, annotation):
        raise TypeError('Incorrect return type')
    return return_value


def typechecked(target):
    """A decorator to make a function check its types at runtime.

    >>> @typechecked
    ... def test(a: int):
    ...     return a
    ...
    >>> test(1)
    1
    >>> test('string')
    Traceback (most recent call last):
        ...
    TypeError: Incorrect type for "a"
    """
    signature = inspect.signature(target)

    @functools.wraps(target)
    def wrapper(*args, **kwargs):
        _check_argument_types(signature, *args, **kwargs)
        return _check_return_type(signature, target(*args, **kwargs))
    return wrapper

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = test_annontations
import unittest

from annotation.typed import (typechecked, Interface, union, AnyType, predicate,
    optional, typedef, options, only)



class TypecheckedTest(unittest.TestCase):

    def test_single_argument_with_builtin_type(self):

        @typechecked
        def test(a: int):
            return a

        self.assertEqual(1, test(1))
        self.assertRaises(TypeError, test, 'string')
        self.assertRaises(TypeError, test, 1.2)

    def test_single_argument_with_class(self):

        class MyClass:
            pass

        @typechecked
        def test(a: MyClass):
            return a

        value = MyClass()
        self.assertEqual(value, test(value))
        self.assertRaises(TypeError, test, 'string')

    def test_single_argument_with_subclass(self):

        class MyClass: pass
        class MySubClass(MyClass): pass

        @typechecked
        def test(a: MyClass):
            return a

        value = MySubClass()
        self.assertEqual(value, test(value))
        self.assertRaises(TypeError, test, 'string')

    def test_single_argument_with_union_annotation(self):
        from decimal import Decimal

        @typechecked
        def test(a: union(int, float, Decimal)):
            return a

        self.assertEqual(1, test(1))
        self.assertEqual(1.5, test(1.5))
        self.assertEqual(Decimal('2.5'), test(Decimal('2.5')))
        self.assertRaises(TypeError, test, 'string')

    def test_single_argument_with_predicate_annotation(self):

        @typechecked
        def test(a: predicate(lambda x: x > 0)):
            return a

        self.assertEqual(1, test(1))
        self.assertRaises(TypeError, test, 0)

    def test_single_argument_with_optional_annotation(self):

        @typechecked
        def test(a: optional(int)):
            return a

        self.assertEqual(1, test(1))
        self.assertEqual(None, test(None))

    def test_single_argument_with_typedef_annotation(self):

        @typedef
        def callback(a: int, b: str) -> dict:
            pass

        @typechecked
        def test(a: callback):
            return a(1, 'string')

        def f1(a: int, b: str) -> dict:
            return {}

        def f2(a: str, b: str):
            pass

        self.assertEqual({}, test(f1))
        self.assertRaises(TypeError, test, f2)

    def test_single_argument_with_options_annotation(self):

        @typechecked
        def test(a: options('open', 'write')):
            return a

        self.assertEqual('open', test('open'))
        self.assertEqual('write', test('write'))
        self.assertRaises(TypeError, test, 'other')

    def test_single_argument_with_only_annotation(self):

        @typechecked
        def test(a: only(int)):
            return a

        self.assertEqual(1, test(1))
        self.assertRaises(TypeError, test, True)

    def test_single_argument_with_interface(self):

        class Test(Interface):
            def test():
                pass

        class TestImplementation:
            def test(self):
                return 1

        class Other: pass

        @typechecked
        def test(a: Test):
            return 1

        self.assertEqual(1, test(TestImplementation()))
        self.assertRaises(TypeError, test, Other())

    def test_single_argument_with_no_annotation(self):

        @typechecked
        def test(a):
            return a

        self.assertEqual(1, test(1))
        self.assertEqual(1.5, test(1.5))
        self.assertEqual('string', test('string'))

    def test_multiple_arguments_with_annotations(self):

        @typechecked
        def test(a: int, b: str):
            return a, b

        self.assertEqual((1, 'string'), test(1, 'string'))
        self.assertRaises(TypeError, test, 1, 1)
        self.assertRaises(TypeError, test, 'string', 'string')
        self.assertRaises(TypeError, test, 'string', 1)

    def test_single_argument_with_none_value(self):

        @typechecked
        def test(a: int):
            return a

        self.assertRaises(TypeError, test, None)

    def test_multiple_arguments_some_with_annotations(self):

        @typechecked
        def test(a, b: str):
            return a, b

        self.assertEqual((1, 'string'), test(1, 'string'))
        self.assertEqual(('string', 'string'), test('string', 'string'))
        self.assertRaises(TypeError, test, 1, 1)
        self.assertRaises(TypeError, test, 'string', 1)

    def test_return_with_builtin_type(self):

        @typechecked
        def test(a) -> int:
            return a

        self.assertEqual(1, test(1))
        self.assertRaises(TypeError, test, 'string')
        self.assertRaises(TypeError, test, 1.2)

    def test_return_with_class(self):

        class MyClass:
            pass

        @typechecked
        def test1() -> MyClass:
            return MyClass()

        @typechecked
        def test2() -> MyClass:
            return 1

        self.assertIsInstance(test1(), MyClass)
        self.assertRaises(TypeError, test2)

    def test_return_with_sublass(self):

        class MyClass: pass
        class MySubClass(MyClass): pass

        @typechecked
        def test1() -> MyClass:
            return MySubClass()

        @typechecked
        def test2() -> MyClass:
            return 1

        self.assertIsInstance(test1(), MyClass)
        self.assertRaises(TypeError, test2)

    def test_return_with_union(self):

        @typechecked
        def test(a) -> union(int, float):
            return a

        self.assertEqual(1, test(1))
        self.assertEqual(1.1, test(1.1))
        self.assertRaises(TypeError, test, 'string')

    def test_return_with_interface(self):

        class Test(Interface):
            def test():
                pass

        class TestImplementation:
            def test(self):
                return 1

        class Other: pass

        @typechecked
        def test1() -> Test:
            return TestImplementation()

        @typechecked
        def test2() -> Test:
            return 1

        self.assertIsInstance(test1(), TestImplementation)
        self.assertRaises(TypeError, test2)

    def test_return_with_none_value(self):

        @typechecked
        def test(a) -> int:
            return a

        self.assertRaises(TypeError, test, None)


class UnionTest(unittest.TestCase):

    def test_union_is_type(self):
        self.assertIsInstance(union(int, float), type)

    def test_union_with_no_type(self):
        self.assertRaises(TypeError, union, 1, int, 'three')

    def test_isinstance_bultin_types(self):
        self.assertIsInstance(1, union(int, float))
        self.assertIsInstance(1.2, union(int, float))

        self.assertNotIsInstance('string', union(int, float))
        self.assertNotIsInstance([], union(int, float))
        self.assertNotIsInstance(tuple(), union(int, float))
        self.assertNotIsInstance({}, union(int, float))

    def test_isinstance_classes(self):

        class Test1: pass
        class Test2: pass
        class Other: pass

        self.assertIsInstance(Test1(), union(Test1, Test2))
        self.assertIsInstance(Test2(), union(Test1, Test2))

        self.assertNotIsInstance(Other(), union(Test1, Test2))

    def test_isinstance_subclasses(self):

        class Test1: pass
        class Test1Sub(Test1): pass
        class Test2: pass
        class Test2Sub(Test2): pass
        class Other: pass

        self.assertIsInstance(Test1Sub(), union(Test1, Test2))
        self.assertIsInstance(Test2Sub(), union(Test1, Test2))

        self.assertNotIsInstance(Other(), union(Test1, Test2))
        self.assertNotIsInstance(Test1(), union(Test1Sub, Test2Sub))
        self.assertNotIsInstance(Test2(), union(Test1Sub, Test2Sub))

    def test_isinstance_interfaces(self):

        class Test1(Interface):
            def test1() -> int:
                pass
        class Test1Implementation:
            def test1(self) -> int:
                return 1
        class Test2(Interface):
            def test2() -> str:
                pass
        class Test2Implementation:
            def test2(self) -> str:
                return 1
        class Other: pass

        self.assertIsInstance(Test1Implementation(), union(Test1, Test2))
        self.assertIsInstance(Test2Implementation(), union(Test1, Test2))

        self.assertNotIsInstance(Other(), union(Test1, Test2))

    def test_isinstance_mixed(self):

        class Test1:
            pass

        class Test2(Interface):
            def test2() -> str:
                pass

        class Test2Implementation:
            def test2() -> str:
                return 1

        class Other:
            pass

        self.assertIsInstance(1, union(int, Test1, Test2))
        self.assertIsInstance(Test1(), union(int, Test1, Test2))
        self.assertIsInstance(Test2Implementation(), union(int, Test1, Test2))

        self.assertNotIsInstance('string', union(int, Test1, Test2))
        self.assertNotIsInstance(Other(), union(int, Test1, Test2))


    def test_issubclass_single_builtin_type(self):
        self.assertTrue(issubclass(int, union(int, float)))
        self.assertTrue(issubclass(float, union(int, float)))

        self.assertFalse(issubclass(str, union(int, float)))
        self.assertFalse(issubclass(list, union(int, float)))

    def test_issubclass_single_class(self):
        class Test1: pass
        class Test2: pass
        class Other: pass

        self.assertTrue(issubclass(Test1, union(Test1, Test2)))
        self.assertTrue(issubclass(Test2, union(Test1, Test2)))

        self.assertFalse(issubclass(Other, union(Test1, Test2)))

    def test_issubclass_single_subclass(self):
        class Test1: pass
        class Test1Sub(Test1): pass
        class Test2: pass
        class Test2Sub(Test2): pass
        class Other: pass

        self.assertTrue(issubclass(Test1Sub, union(Test1, Test2)))
        self.assertTrue(issubclass(Test2Sub, union(Test1, Test2)))

        self.assertFalse(issubclass(Other, union(Test1, Test2)))
        self.assertFalse(issubclass(Test1, union(Test1Sub, Test2Sub)))
        self.assertFalse(issubclass(Test2, union(Test1Sub, Test2Sub)))

    def test_issubclass_single_interface(self):

        class Test1(Interface):
            def test1(self) -> int:
                pass

        class Test2(Interface):
            def test2(self) -> str:
                pass

        class Other(Interface): pass
        class Other2: pass

        self.assertTrue(issubclass(Test1, union(Test1, Test2)))
        self.assertTrue(issubclass(Test2, union(Test1, Test2)))

        self.assertFalse(issubclass(Other, union(Test1, Test2)))
        self.assertFalse(issubclass(Other2, union(Test1, Test2)))

    def test_issubclass_single_mixed(self):

        class Test1(Interface):
            def test1(self) -> int:
                pass

        class Test2:
            pass

        self.assertTrue(issubclass(int, union(int, Test1, Test2)))
        self.assertTrue(issubclass(Test1, union(int, Test1, Test2)))
        self.assertTrue(issubclass(Test2, union(int, Test1, Test2)))

        self.assertTrue(issubclass(int, union(int, Test1, Test2)))
        self.assertTrue(issubclass(Test1, union(int, Test1, Test2)))
        self.assertTrue(issubclass(Test2, union(int, Test1, Test2)))

    def test_issubclass_union(self):
        self.assertTrue(issubclass(union(int, float), union(int, float)))
        self.assertTrue(issubclass(union(int, float), union(float, int)))
        self.assertTrue(issubclass(union(int, float), union(int, float, bool)))

        self.assertFalse(issubclass(union(int, float), union(int, str)))
        self.assertFalse(issubclass(union(int, str, float), union(int, float)))


class AnyTypeTest(unittest.TestCase):

    def test_isinstance(self):

        class Test:
            pass

        self.assertIsInstance(1, AnyType)
        self.assertIsInstance('string', AnyType)
        self.assertIsInstance(Test(), AnyType)
        self.assertIsInstance(None, AnyType)

    def test_issubclass(self):

        class Test:
            pass

        self.assertTrue(issubclass(int, AnyType))
        self.assertTrue(issubclass(str, AnyType))
        self.assertTrue(issubclass(type, AnyType))
        self.assertTrue(issubclass(Interface, AnyType))


class InterfaceTest(unittest.TestCase):

    def test_matching_arguments_annotations(self):

        class TestInterface(Interface):
            def test(a: int, b: str):
                pass


        class TestImplementation:
            def test(self, a: int, b: str ):
                return 1


        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_arguments_without_annotation(self):

        class TestInterface(Interface):
            def test(a, b):
                pass


        class TestImplementation:
            def test(self, a, b):
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_arguments_annotated_in_interface_only(self):

        class TestInterface(Interface):
            def test(a: int, b: str):
                pass


        class TestImplementation:
            def test(self, a, b):
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_arguments_with_union_annotations(self):

        class TestInterface(Interface):
            def test(a: union(int, float)) -> int:
                pass


        class TestImplementation:
            def test(self, a: union(int, float)) -> int:
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_arguments_with_interface(self):

        class TestInterface1(Interface):
            def test1(x, y):
                pass

        class TestInterface2(Interface):
            def test2(a: TestInterface1):
                pass

        class TestImplementation:
            def test2(self, a: TestInterface1):
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface2)
        self.assertTrue(issubclass(TestImplementation, TestInterface2))

    def test_arguments_with_annotations_not_matching(self):

        class TestInterface(Interface):
            def test(a: int, b: str) -> int:
                pass


        class TestImplementation:
            def test(self, a: int, b: int) -> int:
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_arguments_in_different_order(self):

        class TestInterface(Interface):
            def test(b: str, a: int) -> int:
                pass


        class TestImplementation:
            def test(self, a: int, b: str) -> int:
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_arguments_with_different_name(self):
        class TestInterface(Interface):
            def test(a: int, b: int) -> int:
                pass


        class TestImplementation:
            def test(self, c: int, d: int) -> int:
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_arguments_with_different_length(self):

        class TestInterface(Interface):
            def test(a: int) -> int:
                pass


        class TestImplementation:
            def test(self, a: int, b: str) -> int:
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_arguments_annotated_in_implementation_only(self):

        class TestInterface(Interface):
            def test(a, b) -> int:
                pass

        class TestImplementation:
            def test(self, a: int, b: str) -> int:
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_matching_return(self):
        class TestInterface(Interface):
            def test() -> int:
                pass


        class TestImplementation:
            def test(self) -> int:
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_return_without_annotation(self):
        class TestInterface(Interface):
            def test():
                pass


        class TestImplementation:
            def test(self):
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_return_annotated_in_implementation_only(self):
        class TestInterface(Interface):
            def test():
                pass


        class TestImplementation:
            def test(self) -> int:
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_return_with_tuple_annotations(self):
        class TestInterface(Interface):
            def test() -> union(int, float):
                pass


        class TestImplementation:
            def test(self) -> union(int, float):
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_return_with_tuple_annotations_different_order(self):
        class TestInterface(Interface):
            def test() -> union(int, float):
                pass


        class TestImplementation:
            def test(self) -> union(float, int):
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_return_with_subset(self):
        class TestInterface(Interface):
            def test() -> union(int, float, bool):
                pass


        class TestImplementation:
            def test(self) -> union(float, int):
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_matching_return_with_single_subset(self):
        class TestInterface(Interface):
            def test() -> union(int, float):
                pass


        class TestImplementation:
            def test(self) -> int:
                return 1

        self.assertIsInstance(TestImplementation(), TestInterface)
        self.assertTrue(issubclass(TestImplementation, TestInterface))

    def test_return_with_annotation_not_matching(self):

        class TestInterface(Interface):
            def test() -> int:
                pass


        class TestImplementation:
            def test(self) -> str:
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_return_annotated_in_interface_only(self):

        class TestInterface(Interface):
            def test() -> int:
                pass


        class TestImplementation:
            def test(self):
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_return_superset(self):

        class TestInterface(Interface):
            def test() -> union(int, float):
                pass


        class TestImplementation:
            def test(self) -> union(int, float, str):
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_return_single_superset(self):

        class TestInterface(Interface):
            def test() -> int:
                pass


        class TestImplementation:
            def test(self) -> union(int, float):
                return 1

        self.assertNotIsInstance(TestImplementation(), TestInterface)
        self.assertFalse(issubclass(TestImplementation, TestInterface))

    def test_matching_attribute(self):
        class TestInterface(Interface):
            x = int

        class TestImplementation1:
            def __init__(self):
                self.x = 1

        class TestImplementation2:
            @property
            def x(self):
                return 1

        self.assertIsInstance(TestImplementation1(), TestInterface)
        self.assertIsInstance(TestImplementation2(), TestInterface)

    def test_matching_attribute_with_anytype(self):

        class TestInterface(Interface):
            x = AnyType

        class TestImplementation1:
            def __init__(self):
                self.x = 1

        class TestImplementation2:
            def __init__(self):
                self.x = 'string'

        self.assertIsInstance(TestImplementation1(), TestInterface)
        self.assertIsInstance(TestImplementation2(), TestInterface)

    def test_matching_attribute_with_union(self):

        class TestInterface(Interface):
            x = union(int, str)

        class TestImplementation1:
            def __init__(self):
                self.x = 1

        class TestImplementation2:
            def __init__(self):
                self.x = 'string'

        self.assertIsInstance(TestImplementation1(), TestInterface)
        self.assertIsInstance(TestImplementation2(), TestInterface)

    def test_attribute_with_different_type(self):

        class TestInterface(Interface):
            x = int

        class Other:
            def __init__(self):
                self.x = 'string'


        self.assertNotIsInstance(Other(), TestInterface)

    def test_attribute_not_in_implementation(self):

        class TestInterface(Interface):
            x = AnyType
            y = int

        class Other:
            y = int

        self.assertNotIsInstance(Other(), TestInterface)

    def test_attribute_with_type_not_in_union(self):

        class TestInterface(Interface):
            x = union(int, str)

        class Other:
            x = 1.5

        self.assertNotIsInstance(Other(), TestInterface)

    def test_multiple_attributes(self):

        class TestInterface(Interface):
            x = AnyType
            y = int

        class TestImplementation1:
            def __init__(self):
                self.x = 'hello'
                self.y = 1

        class TestImplementation2:
            x = 'string'

            @property
            def y(self):
                return 1

        self.assertIsInstance(TestImplementation1(), TestInterface)
        self.assertIsInstance(TestImplementation2(), TestInterface)

    def test_multiple_matching_function(self):

        class TestInterface(Interface):
            def test1(a: int) -> int:
                pass

            def test2(b: str) -> str:
                pass

            def test3(c: bool) -> bool:
                pass


        class TestImplementation:
            def test1(self, a: int) -> int:
                return 1

            def test2(self, b: str) -> str:
                return 'string'

            def test3(self, c: bool) -> bool:
                return False

        self.assertIsInstance(TestImplementation(), TestInterface)

    def test_matching_implementation_with_extra_functions(self):

        class TestInterface(Interface):
            def test1(a: int) -> int:
                pass

        class TestImplementation:
            def test1(self, a: int) -> int:
                return 1

            def test2(self, b: str) -> str:
                return 'string'

            def test3(self, c: bool) -> bool:
                return False

        self.assertIsInstance(TestImplementation(), TestInterface)

    def test_builtin_implementation(self):

        class TestInterface(Interface):
            def __len__():
                pass

        self.assertIsInstance([], TestInterface)
        self.assertIsInstance('', TestInterface)
        self.assertIsInstance(set, TestInterface)

        self.assertNotIsInstance(iter([]), TestInterface)
        self.assertNotIsInstance(1, TestInterface)

    def test_self_referencing_interface(self):
        class TreeNode(Interface):
            pass

        TreeNode.add_attribute('left', optional(TreeNode))
        TreeNode.add_attribute('right', optional(TreeNode))

        class TreeNodeImplementation:
            def __init__(self):
                self.left = None
                self.right = None

        tree = TreeNodeImplementation()
        tree.left = TreeNodeImplementation()
        tree.right = TreeNodeImplementation()

        self.assertIsInstance(tree, TreeNode)

        tree.left = 1
        self.assertNotIsInstance(tree, TreeNode)

    def test_interface_add_method(self):

        class Test(Interface):
            pass

        @Test.add_method
        def test(x: int) -> int:
            pass

        class TestImplementation:
            def test(self, x: int) -> int:
                return 1

        class Other: pass

        self.assertIsInstance(TestImplementation(), Test)
        self.assertNotIsInstance(Other(), Test)

    def test_interface_add_method_with_no_method(self):

        class Test(Interface):
            pass

        self.assertRaises(TypeError, Test.add_method, 1)

    def test_interface_add_attribute(self):

        class Test(Interface):
            pass

        Test.add_attribute('x', int)

        class TestImplementation:
            x = 1

        class Other: pass

        self.assertIsInstance(TestImplementation(), Test)
        self.assertNotIsInstance(Other(), Test)

    def test_interface_add_attribute_with_no_type(self):

        class Test(Interface):
            pass

        self.assertRaises(TypeError, Test.add_attribute, 'name', 1)

    def test_interface_with_no_type_attribute(self):

        def test():
            class Test(Interface):
                x = 1

        self.assertRaises(TypeError, test)


class PredicateTest(unittest.TestCase):

    def test_predicate(self):
        self.assertIsInstance(1, predicate(lambda x: x > 0))
        self.assertNotIsInstance(0, predicate(lambda x: x > 0))
        self.assertNotIsInstance(-1, predicate(lambda x: x > 0))

    def test_predicate_called(self):
        called = False

        @predicate
        def positive(x):
            nonlocal called
            called = True
            return x > 0

        self.assertIsInstance(1, positive)
        self.assertTrue(called)

    def test_optional(self):
        self.assertIsInstance(1, optional(int))
        self.assertIsInstance(None, optional(int))
        self.assertNotIsInstance('string', optional(int))

    def test_typedef(self):
        @typedef
        def callback(a: int) -> int:
            pass

        def f1(a: int) -> int:
            return a

        def f2():
            pass

        self.assertIsInstance(f1, callback)
        self.assertNotIsInstance(f2, callback)

    def test_options(self):
        self.assertIsInstance('open', options('open', 'write'))
        self.assertIsInstance('write', options('open', 'write'))
        self.assertNotIsInstance('other', options('open', 'write'))

    def test_only(self):
        self.assertIsInstance(1, only(int))
        self.assertNotIsInstance(True, only(int))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_overload
import unittest

from annotation.overload import AmbiguousFunction, FunctionNotFound, overloaded


class TestOverloaded(unittest.TestCase):
    def test_creation(self):
        @overloaded
        def foo():
            return 'no args'
        
        @overloaded
        def foo(a, b):
            return 'two empty args'
        
        @overloaded
        def foo(a:int, b):
            return 'one int'
        
        @overloaded
        def foo(a:int, b:str):
            return 'int and str'
        
        def other_foo(a:str, b:int):
            return 'str and int'
        foo.add_function(other_foo)
        
        self.assertEqual(foo(), 'no args')
        self.assertEqual(foo(object(), object()), 'two empty args')
        self.assertEqual(foo(1, object()), 'one int')
        self.assertEqual(foo(1, ''), 'int and str')
        self.assertEqual(foo('', 1), 'str and int')
        self.assertRaises(FunctionNotFound, foo, object(), object(), object())

        def bar(*args):
            pass
        
        def baz(**kwargs):
            pass
        
        self.assertRaises(TypeError, overloaded, bar)
        self.assertRaises(TypeError, overloaded, baz)
    
    def test_ambiguous(self):
        @overloaded
        def foo():
            pass
        
        def other_foo():
            pass
        
        self.assertRaises(AmbiguousFunction, foo.add_function, other_foo)

        @overloaded
        def foo(a:int, b):
            pass
        
        def other_foo(a, b:int):
            pass
        
        self.assertRaises(AmbiguousFunction, foo.add_function, other_foo)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
