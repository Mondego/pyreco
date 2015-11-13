__FILENAME__ = compat_py3
import six

if six.PY3:
    def compat_repr(object_repr):
        return object_repr
else:
    def compat_repr(object_repr):
        # compat_repr is designed to return all reprs with leading 'u's
        # inserted to make all strings look like unicode strings.
        # This makes testing between py2 and py3 much easier.
        result = ''
        in_quote = False
        curr_quote = None
        for char in object_repr:
            if char in ['"', "'"] and (
                not curr_quote or char == curr_quote):
                if in_quote:
                    # Closing quote
                    curr_quote = None
                    in_quote = False
                else:
                    # Opening quote
                    curr_quote = char
                    result += 'u'
                    in_quote = True
            result += char
        return result

text_type_name = six.text_type().__class__.__name__

########NEW FILE########
__FILENAME__ = core
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2010-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

try:
    from collections import OrderedDict
except ImportError:
    from sure.ordereddict import OrderedDict

import os
import mock
import inspect
from six import (
    text_type, integer_types, string_types, binary_type,
    PY3, get_function_code
)
from sure.terminal import red, green, yellow


class FakeOrderedDict(OrderedDict):
    """ OrderedDict that has the repr of a normal dict

    We must return a string whether in py2 or py3.
    """
    def __unicode__(self):
        if not self:
            return '{}'
        key_values = []
        for key, value in self.items():
            key, value = repr(key), repr(value)
            if isinstance(value, binary_type) and not PY3:
                value = value.decode("utf-8")
            key_values.append("{0}: {1}".format(key, value))
        res = "{{{0}}}".format(", ".join(key_values))
        return res

    if PY3:
        def __repr__(self):
            return self.__unicode__()
    else:
        def __repr__(self):
            return self.__unicode__().encode('utf-8')


def _obj_with_safe_repr(obj):
    if isinstance(obj, dict):
        ret = FakeOrderedDict()
        for key in sorted(obj.keys()):
            ret[_obj_with_safe_repr(key)] = _obj_with_safe_repr(obj[key])
    elif isinstance(obj, list):
        ret = []
        for x in obj:
            if isinstance(x, dict):
                ret.append(_obj_with_safe_repr(x))
            else:
                ret.append(x)
    else:
        ret = obj
    return ret


def safe_repr(val):
    try:
        if isinstance(val, dict):
            # We special case dicts to have a sorted repr. This makes testing
            # significantly easier
            val = _obj_with_safe_repr(val)
        ret = repr(val)
        if not PY3:
            ret = ret.decode('utf-8')
    except UnicodeEncodeError:
        ret = red('a %r that cannot be represented' % type(val))
    else:
        ret = green(ret)

    return ret


class DeepExplanation(text_type):
    def get_header(self, X, Y, suffix):
        params = (safe_repr(X), safe_repr(Y), str(suffix))
        header = "given\nX = %s\n    and\nY = %s\n%s" % params

        return yellow(header).strip()

    def get_assertion(self, X, Y):
        return AssertionError(self.get_header(X, Y, self))

    def as_assertion(self, X, Y):
        raise self.get_assertion(X, Y)


class DeepComparison(object):
    def __init__(self, X, Y, parent=None):
        self.operands = X, Y
        self.parent = parent
        self._context = None

    def is_simple(self, obj):
        return isinstance(obj, (
            float, string_types, integer_types
        ))

    def compare_complex_stuff(self, X, Y):
        kind = type(X)
        mapping = {
            dict: self.compare_dicts,
            list: self.compare_iterables,
            tuple: self.compare_iterables,
        }
        return mapping.get(kind, self.compare_generic)(X, Y)

    def compare_generic(self, X, Y):
        c = self.get_context()
        if X == Y:
            return True
        else:
            m = 'X%s != Y%s' % (red(c.current_X_keys), green(c.current_Y_keys))
            return DeepExplanation(m)

    def compare_dicts(self, X, Y):
        c = self.get_context()

        x_keys = list(sorted(X.keys()))
        y_keys = list(sorted(Y.keys()))

        diff_x = list(set(x_keys).difference(set(y_keys)))
        diff_y = list(set(y_keys).difference(set(x_keys)))
        if diff_x:
            msg = "X%s has the key %%r whereas Y%s does not" % (
                red(c.current_X_keys),
                green(c.current_Y_keys),
            ) % diff_x[0]
            return DeepExplanation(msg)

        elif diff_y:
            msg = "X%s does not have the key %%r whereas Y%s has it" % (
                red(c.current_X_keys),
                green(c.current_Y_keys),
            ) % diff_y[0]
            return DeepExplanation(msg)

        elif X == Y:
            return True

        else:
            for key_X, key_Y in zip(x_keys, y_keys):
                self.key_X = key_X
                self.key_Y = key_Y
                value_X = X[key_X]
                value_Y = Y[key_Y]
                child = DeepComparison(
                    value_X,
                    value_Y,
                    parent=self,
                ).compare()
                if isinstance(child, DeepExplanation):
                    return child

    def get_context(self):
        if self._context:
            return self._context

        X_keys = []
        Y_keys = []

        comp = self
        while comp.parent:
            X_keys.insert(0, comp.parent.key_X)
            Y_keys.insert(0, comp.parent.key_Y)
            comp = comp.parent

        def get_keys(i):
            if not i:
                return ''

            return '[%s]' % ']['.join(map(safe_repr, i))

        class ComparisonContext:
            current_X_keys = get_keys(X_keys)
            current_Y_keys = get_keys(Y_keys)
            parent = comp

        self._context = ComparisonContext()
        return self._context

    def compare_iterables(self, X, Y):
        len_X, len_Y = map(len, (X, Y))
        if len_X > len_Y:
            msg = "X has %d items whereas Y has only %d" % (len_X, len_Y)
            return DeepExplanation(msg)
        elif len_X < len_Y:
            msg = "Y has %d items whereas X has only %d" % (len_Y, len_X)
            return DeepExplanation(msg)
        elif X == Y:
            return True
        else:
            for i, (value_X, value_Y) in enumerate(zip(X, Y)):
                self.key_X = self.key_Y = i
                child = DeepComparison(
                    value_X,
                    value_Y,
                    parent=self,
                ).compare()
                if isinstance(child, DeepExplanation):
                    return child

    def compare(self):
        X, Y = self.operands

        if isinstance(X, mock._CallList):
            X = list(X)

        if isinstance(Y, mock._CallList):
            X = list(Y)

        c = self.get_context()
        if self.is_simple(X) and self.is_simple(Y):  # both simple
            if X == Y:
                return True
            c = self.get_context()
            m = "X%s is %%r whereas Y%s is %%r"
            msg = m % (red(c.current_X_keys), green(c.current_Y_keys)) % (X, Y)
            return DeepExplanation(msg)

        elif type(X) is not type(Y):  # different types
            xname, yname = map(lambda _: type(_).__name__, (X, Y))
            msg = 'X%s is a %%s and Y%s is a %%s instead' % (
                red(c.current_X_keys),
                green(c.current_Y_keys),
            ) % (xname, yname)
            exp = DeepExplanation(msg)

        else:
            exp = self.compare_complex_stuff(X, Y)

        if isinstance(exp, DeepExplanation):

            original_X, original_Y = c.parent.operands
            raise exp.as_assertion(original_X, original_Y)

        return exp

    def explanation(self):
        return self._explanation


def _get_file_name(func):
    try:
        name = inspect.getfile(func)
    except AttributeError:
        name = get_function_code(func).co_filename

    return os.path.abspath(name)


def _get_line_number(func):
    try:
        return inspect.getlineno(func)
    except AttributeError:
        return get_function_code(func).co_firstlineno


def itemize_length(items):
    length = len(items)
    return '%d item%s' % (length, length > 1 and "s" or "")

########NEW FILE########
__FILENAME__ = deprecated
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2010-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

from sure.old import AssertionHelper

that = AssertionHelper

__all__ = ['that']

########NEW FILE########
__FILENAME__ = magic
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2012>  Gabriel Falcão <gabriel@nacaolivre.org>
# Copyright (C) <2012>  Lincoln Clarete <lincoln@comum.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

import platform

is_cpython = (
    hasattr(platform, 'python_implementation')
    and platform.python_implementation().lower() == 'cpython')

if is_cpython:

    import ctypes
    DictProxyType = type(object.__dict__)

    Py_ssize_t = \
        hasattr(ctypes.pythonapi, 'Py_InitModule4_64') \
            and ctypes.c_int64 or ctypes.c_int

    class PyObject(ctypes.Structure):
        pass

    PyObject._fields_ = [
        ('ob_refcnt', Py_ssize_t),
        ('ob_type', ctypes.POINTER(PyObject)),
    ]

    class SlotsProxy(PyObject):
        _fields_ = [('dict', ctypes.POINTER(PyObject))]

    def patchable_builtin(klass):
        name = klass.__name__
        target = getattr(klass, '__dict__', name)

        if not isinstance(target, DictProxyType):
            return target

        proxy_dict = SlotsProxy.from_address(id(target))
        namespace = {}

        ctypes.pythonapi.PyDict_SetItem(
            ctypes.py_object(namespace),
            ctypes.py_object(name),
            proxy_dict.dict,
        )

        return namespace[name]
else:
    patchable_builtin = lambda *args, **kw: None

########NEW FILE########
__FILENAME__ = old
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2010-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

import re
import traceback
import inspect
from copy import deepcopy
from pprint import pformat
from functools import wraps
try:
    from collections import Iterable
except ImportError:
    Iterable = (list, dict, tuple, set)

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

from six import string_types, text_type

from sure.core import DeepComparison
from sure.core import _get_file_name
from sure.core import _get_line_number
from sure.core import itemize_length


def is_iterable(obj):
    return hasattr(obj, '__iter__') and not isinstance(obj, string_types)


def all_integers(obj):
    if not is_iterable(obj):
        return

    for element in obj:
        if not isinstance(element, int):
            return

    return True


def explanation(msg):
    def dec(func):
        @wraps(func)
        def wrap(self, what):
            ret = func(self, what)
            assert ret, msg % (self._src, what)
            return True

        return wrap

    return dec


class AssertionHelper(object):
    def __init__(self, src,
                 within_range=None,
                 with_args=None,
                 with_kwargs=None,
                 and_kwargs=None):

        self._src = src
        self._attribute = None
        self._eval = None
        self._range = None
        if all_integers(within_range):
            if len(within_range) != 2:
                raise TypeError(
                    'within_range parameter must be a tuple with 2 objects',
                )

            self._range = within_range

        self._callable_args = []
        if isinstance(with_args, (list, tuple)):
            self._callable_args = list(with_args)

        self._callable_kw = {}
        if isinstance(with_kwargs, dict):
            self._callable_kw.update(with_kwargs)

        if isinstance(and_kwargs, dict):
            self._callable_kw.update(and_kwargs)

    @classmethod
    def is_a_matcher(cls, func):
        def match(self, *args, **kw):
            return func(self._src, *args, **kw)

        new_matcher = deepcopy(match)
        new_matcher.__name__ = func.__name__
        setattr(cls, func.__name__, new_matcher)

        return new_matcher

    def raises(self, exc, msg=None):
        if not callable(self._src):
            raise TypeError('%r is not callable' % self._src)

        try:
            self._src(*self._callable_args, **self._callable_kw)
        except BaseException as e:
            if isinstance(exc, string_types):
                msg = exc
                exc = type(e)

            err = text_type(e)

            if isinstance(exc, type) and issubclass(exc, BaseException):
                if not isinstance(e, exc):
                    raise AssertionError(
                        '%r should raise %r, but raised %r:\nORIGINAL EXCEPTION:\n\n%s' % (
                            self._src, exc, e.__class__, traceback.format_exc(e)))

                if isinstance(msg, string_types) and msg not in err:
                    raise AssertionError('''
                    %r raised %s, but the exception message does not
                    match.\n\nEXPECTED:\n%s\n\nGOT:\n%s'''.strip() % (
                            self._src,
                            type(e).__name__,
                            msg, err))

            elif isinstance(msg, string_types) and msg not in err:
                raise AssertionError(
                    'When calling %r the exception message does not match. ' \
                    'Expected: %r\n got:\n %r' % (self._src, msg, err))

            else:
                raise e
        else:
            if inspect.isbuiltin(self._src):
                _src_filename = '<built-in function>'
            else:
                _src_filename = _get_file_name(self._src)

            if inspect.isfunction(self._src):
                _src_lineno = _get_line_number(self._src)
                raise AssertionError(
                    'calling function %s(%s at line: "%d") with args %r and kwargs %r did not raise %r' % (
                        self._src.__name__,
                        _src_filename, _src_lineno,
                        self._callable_args,
                        self._callable_kw, exc))
            else:
                raise AssertionError(
                    'at %s:\ncalling %s() with args %r and kwargs %r did not raise %r' % (
                        _src_filename,
                        self._src.__name__,
                        self._callable_args,
                        self._callable_kw, exc))

        return True

    def deep_equals(self, dst):
        deep = DeepComparison(self._src, dst)
        comparison = deep.compare()
        if isinstance(comparison, bool):
            return comparison

        raise comparison.as_assertion(self._src, dst)

    def equals(self, dst):
        if self._attribute and is_iterable(self._src):
            msg = '%r[%d].%s should be %r, but is %r'

            for index, item in enumerate(self._src):
                if self._range:
                    if index < self._range[0] or index > self._range[1]:
                        continue

                attribute = getattr(item, self._attribute)
                error = msg % (
                    self._src, index, self._attribute, dst, attribute)
                if attribute != dst:
                    raise AssertionError(error)
        else:
            return self.deep_equals(dst)

        return True

    def looks_like(self, dst):
        old_src = pformat(self._src)
        old_dst = pformat(dst)
        self._src = re.sub(r'\s', '', self._src).lower()
        dst = re.sub(r'\s', '', dst).lower()
        error = '%s does not look like %s' % (old_src, old_dst)
        assert self._src == dst, error
        return self._src == dst

    def every_one_is(self, dst):
        msg = 'all members of %r should be %r, but the %dth is %r'
        for index, item in enumerate(self._src):
            if self._range:
                if index < self._range[0] or index > self._range[1]:
                    continue

            error = msg % (self._src, dst, index, item)
            if item != dst:
                raise AssertionError(error)

        return True

    @explanation('%r should differ to %r, but is the same thing')
    def differs(self, dst):
        return self._src != dst

    @explanation('%r should be a instance of %r, but is not')
    def is_a(self, dst):
        return isinstance(self._src, dst)

    def at(self, key):
        assert self.has(key)
        if isinstance(self._src, dict):
            return AssertionHelper(self._src[key])

        else:
            return AssertionHelper(getattr(self._src, key))

    @explanation('%r should have %r, but have not')
    def has(self, that):
        return that in self

    def _get_that(self, that):
        try:
            that = int(that)
        except TypeError:
            that = len(that)
        return that

    def len_greater_than(self, that):
        that = self._get_that(that)
        length = len(self._src)

        if length <= that:
            error = 'the length of the %s should be greater then %d, but is %d' % (
                type(self._src).__name__,
                that,
                length,
            )
            raise AssertionError(error)

        return True

    def len_greater_than_or_equals(self, that):
        that = self._get_that(that)

        length = len(self._src)

        if length < that:
            error = 'the length of %r should be greater then or equals %d, but is %d' % (
                self._src,
                that,
                length,
            )
            raise AssertionError(error)

        return True

    def len_lower_than(self, that):
        original_that = that
        if isinstance(that, Iterable):
            that = len(that)
        else:
            that = self._get_that(that)
        length = len(self._src)

        if length >= that:
            error = 'the length of %r should be lower then %r, but is %d' % (
                self._src,
                original_that,
                length,
            )
            raise AssertionError(error)

        return True

    def len_lower_than_or_equals(self, that):
        that = self._get_that(that)

        length = len(self._src)
        error = 'the length of %r should be lower then or equals %d, but is %d'

        if length > that:
            msg = error % (
                self._src,
                that,
                length,
            )
            raise AssertionError(msg)

        return True

    def len_is(self, that):
        that = self._get_that(that)
        length = len(self._src)

        if length != that:
            error = 'the length of %r should be %d, but is %d' % (
                self._src,
                that,
                length,
            )
            raise AssertionError(error)

        return True

    def len_is_not(self, that):
        that = self._get_that(that)
        length = len(self._src)

        if length == that:
            error = 'the length of %r should not be %d' % (
                self._src,
                that,
            )
            raise AssertionError(error)

        return True

    def like(self, that):
        return self.has(that)

    def the_attribute(self, attr):
        self._attribute = attr
        return self

    def in_each(self, attr):
        self._eval = attr
        return self

    def matches(self, items):
        msg = '%r[%d].%s should be %r, but is %r'
        get_eval = lambda item: eval(
            "%s.%s" % ('current', self._eval), {}, {'current': item},
        )

        if self._eval and is_iterable(self._src):
            if isinstance(items, string_types):
                items = [items for x in range(len(items))]
            else:
                if len(items) != len(self._src):
                    source = list(map(get_eval, self._src))
                    source_len = len(source)
                    items_len = len(items)

                    raise AssertionError(
                        '%r has %d items, but the matching list has %d: %r'
                        % (source, source_len, items_len, items),
                    )

            for index, (item, other) in enumerate(zip(self._src, items)):
                if self._range:
                    if index < self._range[0] or index > self._range[1]:
                        continue

                value = get_eval(item)

                error = msg % (self._src, index, self._eval, other, value)
                if other != value:
                    raise AssertionError(error)
        else:
            return self.equals(items)

        return True

    @builtins.property
    def is_empty(self):
        try:
            lst = list(self._src)
            length = len(lst)
            assert length == 0, \
                   '%r is not empty, it has %s' % (self._src,
                                                   itemize_length(self._src))
            return True

        except TypeError:
            raise AssertionError("%r is not iterable" % self._src)

    @builtins.property
    def are_empty(self):
        return self.is_empty

    def __contains__(self, what):
        if isinstance(self._src, dict):
            items = self._src.keys()

        if isinstance(self._src, Iterable):
            items = self._src
        else:
            items = dir(self._src)

        return what in items

    def contains(self, what):
        assert what in self._src, '%r should be in %r' % (what, self._src)
        return True

    def does_not_contain(self, what):
        assert what not in self._src, \
            '%r should NOT be in %r' % (what, self._src)

        return True

    doesnt_contain = does_not_contain


that = AssertionHelper

########NEW FILE########
__FILENAME__ = ordereddict
# Copyright (c) 2009 Raymond Hettinger
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be
#     included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#     OTHER DEALINGS IN THE SOFTWARE.

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other
########NEW FILE########
__FILENAME__ = registry
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2012>  Gabriel Falcão <gabriel@nacaolivre.org>
# Copyright (C) <2012>  Lincoln Clarete <lincoln@comum.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

context = {
    'is_running': False,
}

########NEW FILE########
__FILENAME__ = terminal
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2010-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

import os
import sys
import platform

SUPPORTS_ANSI = False
for handle in [sys.stdout, sys.stderr]:
    if (hasattr(handle, "isatty") and handle.isatty()) or \
        ('TERM' in os.environ and os.environ['TERM'] == 'ANSI'):
        if platform.system() == 'Windows' and not (
            'TERM' in os.environ and os.environ['TERM'] == 'ANSI'):
            SUPPORTS_ANSI = False
        else:
            SUPPORTS_ANSI = True

if os.getenv('SURE_NO_COLORS'):
    SUPPORTS_ANSI = False

SUPPORTS_ANSI = False


def red(string):
    if not SUPPORTS_ANSI:
        return string
    return r"\033[1;31m{0}\033[0m".format(string)


def green(string):
    if not SUPPORTS_ANSI:
        return string
    return r"\033[1;32m{0}\033[0m".format(string)


def yellow(string):
    if not SUPPORTS_ANSI:
        return string
    return r"\033[1;33m{0}\033[0m".format(string)


def white(string):
    if not SUPPORTS_ANSI:
        return string
    return r"\033[1;37m{0}\033[0m".format(string)

########NEW FILE########
__FILENAME__ = test_assertion_builder
## #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2010-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals
import mock
from datetime import datetime
from sure import this, these, those, it, expect, AssertionBuilder
from six import PY3
from sure.compat_py3 import compat_repr


def test_assertion_builder_synonyms():
    ("this, it, these and those are all synonyms")

    assert isinstance(it, AssertionBuilder)
    assert isinstance(this, AssertionBuilder)
    assert isinstance(these, AssertionBuilder)
    assert isinstance(those, AssertionBuilder)


def test_4_equal_2p2():
    ("this(4).should.equal(2 + 2)")

    time = datetime.now()

    assert this(4).should.equal(2 + 2)
    assert this(time).should_not.equal(datetime.now())

    def opposite():
        assert this(4).should.equal(8)

    def opposite_not():
        assert this(4).should_not.equal(4)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw("X is 4 whereas Y is 8")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "4 should differ to 4, but is the same thing")


def test_2_within_0a2():
    ("this(1).should.be.within(0, 2)")

    assert this(1).should.be.within(0, 2)
    assert this(4).should_not.be.within(0, 2)

    def opposite():
        assert this(1).should.be.within(2, 4)

    def opposite_not():
        assert this(1).should_not.be.within(0, 2)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw("1 should be in [2, 3]")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw("1 should NOT be in [0, 1]")


def test_true_be_ok():
    ("this(True).should.be.ok")

    assert this(True).should.be.ok
    assert this(False).should_not.be.ok

    def opposite():
        assert this(False).should.be.ok

    def opposite_not():
        assert this(True).should_not.be.ok

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw("expected `False` to be truthy")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw("expected `True` to be falsy")


def test_false_be_falsy():
    ("this(False).should.be.false")

    assert this(False).should.be.falsy
    assert this(True).should_not.be.falsy

    def opposite():
        assert this(True).should.be.falsy

    def opposite_not():
        assert this(False).should_not.be.falsy

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw("expected `True` to be falsy")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw("expected `False` to be truthy")


def test_none():
    ("this(None).should.be.none")

    assert this(None).should.be.none
    assert this(not None).should_not.be.none

    def opposite():
        assert this("cool").should.be.none

    def opposite_not():
        assert this(None).should_not.be.none

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw("expected `cool` to be None")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw("expected `None` to not be None")


def test_should_be_a():
    ("this(None).should.be.none")

    assert this(1).should.be.an(int)
    assert this([]).should.be.a('collections.Iterable')
    assert this({}).should_not.be.a(list)

    def opposite():
        assert this(1).should_not.be.an(int)

    def opposite_not():
        assert this([]).should_not.be.a('list')

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw("expected `1` to not be an int")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw("expected `[]` to not be a list")


def test_should_be_callable():
    ("this(function).should.be.callable")

    assert this(lambda: None).should.be.callable
    assert this("aa").should_not.be.callable

    def opposite():
        assert this("foo").should.be.callable

    def opposite_not():
        assert this(opposite).should_not.be.callable

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr(
        "expected 'foo' to be callable"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "expected `{0}` to not be callable but it is".format(repr(opposite)))


def test_iterable_should_be_empty():
    ("this(iterable).should.be.empty")

    assert this([]).should.be.empty
    assert this([1, 2, 3]).should_not.be.empty

    def opposite():
        assert this([3, 2, 1]).should.be.empty

    def opposite_not():
        assert this({}).should_not.be.empty

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(
        "expected `[3, 2, 1]` to be empty but it has 3 items")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw("expected `{}` to not be empty")


def test_iterable_should_have_length_of():
    ("this(iterable).should.have.length_of(N)")

    assert this({'foo': 'bar', 'a': 'b'}).should.have.length_of(2)
    assert this([1, 2, 3]).should_not.have.length_of(4)

    def opposite():
        assert this(('foo', 'bar', 'a', 'b')).should.have.length_of(1)

    def opposite_not():
        assert this([1, 2, 3]).should_not.have.length_of(3)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr(
        "the length of ('foo', 'bar', 'a', 'b') should be 1, but is 4"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "the length of [1, 2, 3] should not be 3")


def test_greater_than():
    ("this(X).should.be.greater_than(Y)")

    assert this(5).should.be.greater_than(4)
    assert this(1).should_not.be.greater_than(2)

    def opposite():
        assert this(4).should.be.greater_than(5)

    def opposite_not():
        assert this(2).should_not.be.greater_than(1)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(
        "expected `4` to be greater than `5`")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "expected `2` to not be greater than `1`")


def test_greater_than_or_equal_to():
    ("this(X).should.be.greater_than_or_equal_to(Y)")

    assert this(4).should.be.greater_than_or_equal_to(4)
    assert this(1).should_not.be.greater_than_or_equal_to(2)

    def opposite():
        assert this(4).should.be.greater_than_or_equal_to(5)

    def opposite_not():
        assert this(2).should_not.be.greater_than_or_equal_to(1)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(
        "expected `4` to be greater than or equal to `5`")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "expected `2` to not be greater than or equal to `1`")


def test_lower_than():
    ("this(X).should.be.lower_than(Y)")

    assert this(4).should.be.lower_than(5)
    assert this(2).should_not.be.lower_than(1)

    def opposite():
        assert this(5).should.be.lower_than(4)

    def opposite_not():
        assert this(1).should_not.be.lower_than(2)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(
        "expected `5` to be lower than `4`")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "expected `1` to not be lower than `2`")


def test_lower_than_or_equal_to():
    ("this(X).should.be.lower_than_or_equal_to(Y)")

    assert this(5).should.be.lower_than_or_equal_to(5)
    assert this(2).should_not.be.lower_than_or_equal_to(1)

    def opposite():
        assert this(5).should.be.lower_than_or_equal_to(4)

    def opposite_not():
        assert this(1).should_not.be.lower_than_or_equal_to(2)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(
        "expected `5` to be lower than or equal to `4`")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "expected `1` to not be lower than or equal to `2`")


def test_be():
    ("this(X).should.be(X) when X is a reference to the same object")

    d1 = {}
    d2 = d1
    d3 = {}

    assert isinstance(this(d2).should.be(d1), bool)
    assert this(d2).should.be(d1)
    assert this(d3).should_not.be(d1)

    def wrong_should():
        return this(d3).should.be(d1)

    def wrong_should_not():
        return this(d2).should_not.be(d1)

    wrong_should_not.when.called.should.throw(
        AssertionError,
        '{} should not be the same object as {}, but it is',
    )
    wrong_should.when.called.should.throw(
        AssertionError,
        '{} should be the same object as {}, but it is not',
    )


def test_have_property():
    ("this(instance).should.have.property(property_name)")

    class Person(object):
        name = "John Doe"

        def __repr__(self):
            return r"Person()"

    jay = Person()

    assert this(jay).should.have.property("name")
    assert this(jay).should_not.have.property("age")

    def opposite():
        assert this(jay).should_not.have.property("name")

    def opposite_not():
        assert this(jay).should.have.property("age")

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr(
        "Person() should not have the property `name`, but it is 'John Doe'"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "Person() should have the property `age` but does not")


def test_have_property_with_value():
    ("this(instance).should.have.property(property_name).being or "
     ".with_value should allow chain up")

    class Person(object):
        name = "John Doe"

        def __repr__(self):
            return r"Person()"

    jay = Person()

    assert this(jay).should.have.property("name").being.equal("John Doe")
    assert this(jay).should.have.property("name").not_being.equal("Foo")

    def opposite():
        assert this(jay).should.have.property("name").not_being.equal(
            "John Doe")

    def opposite_not():
        assert this(jay).should.have.property("name").being.equal(
            "Foo")

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr(
        "'John Doe' should differ to 'John Doe', but is the same thing"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(compat_repr(
        "X is 'John Doe' whereas Y is 'Foo'"))


def test_have_key():
    ("this(dictionary).should.have.key(key_name)")

    jay = {'name': "John Doe"}

    assert this(jay).should.have.key("name")
    assert this(jay).should_not.have.key("age")

    def opposite():
        assert this(jay).should_not.have.key("name")

    def opposite_not():
        assert this(jay).should.have.key("age")

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr(
        "{'name': 'John Doe'} should not have the key `name`, "
        "but it is 'John Doe'"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(compat_repr(
        "{'name': 'John Doe'} should have the key `age` but does not"))


def test_have_key_with_value():
    ("this(dictionary).should.have.key(key_name).being or "
     ".with_value should allow chain up")

    jay = dict(name="John Doe")

    assert this(jay).should.have.key("name").being.equal("John Doe")
    assert this(jay).should.have.key("name").not_being.equal("Foo")

    def opposite():
        assert this(jay).should.have.key("name").not_being.equal(
            "John Doe")

    def opposite_not():
        assert this(jay).should.have.key("name").being.equal(
            "Foo")

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr(
        "'John Doe' should differ to 'John Doe', but is the same thing"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(compat_repr(
        "X is 'John Doe' whereas Y is 'Foo'"))


def test_look_like():
    ("this('   aa  \n  ').should.look_like('aa')")

    assert this('   \n  aa \n  ').should.look_like('AA')
    assert this('   \n  bb \n  ').should_not.look_like('aa')

    def opposite():
        assert this('\n aa \n').should.look_like('bb')

    def opposite_not():
        assert this('\n aa \n').should_not.look_like('aa')

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr(r"'\n aa \n' does not look like 'bb'"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(compat_repr(r"'\n aa \n' should not look like 'aa' but does"))


def test_equal_with_repr_of_complex_types_and_unicode():
    ("test usage of repr() inside expect(complex1).to.equal(complex2)")

    class Y(object):
        def __init__(self, x):
            self.x = x

        def __repr__(self):
            if PY3:
                # PY3K should return the regular (unicode) string
                return self.x
            else:
                return self.x.encode('utf-8')

        def __eq__(self, other):
            return self.x == other.x

    y1 = dict(
        a=2,
        b=Y('Gabriel Falcão'),
        c='Foo',
    )

    expect(y1).to.equal(dict(
        a=2,
        b=Y('Gabriel Falcão'),
        c='Foo',
    ))


def test_equal_with_repr_of_complex_types_and_repr():
    ("test usage of repr() inside expect(complex1).to.equal(complex2)")

    class Y(object):
        def __init__(self, x):
            self.x = x

        def __repr__(self):
            if PY3:
                # PY3K should return the regular (unicode) string
                return self.x
            else:
                return self.x.encode('utf-8')

        def __eq__(self, other):
            return self.x == other.x

    y1 = {
        'a': 2,
        'b': Y('Gabriel Falcão'),
        'c': 'Foo',
    }

    expect(y1).to.equal({
        'a': 2,
        'b': Y('Gabriel Falcão'),
        'c': 'Foo',
    })

    expect(y1).to_not.equal({
        'a': 2,
        'b': Y('Gabriel Falçao'),
        'c': 'Foo',
    })

    def opposite():
        expect(y1).to.equal({
            'a': 2,
            'b': Y('Gabriel Falçao'),
            'c': 'Foo',
        })

    def opposite_not():
        expect(y1).to_not.equal({
            'a': 2,
            'b': Y('Gabriel Falcão'),
            'c': 'Foo',
        })

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw(compat_repr("X['b'] != Y['b']"))

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(compat_repr(
        "{'a': 2, 'b': Gabriel Falcão, 'c': 'Foo'} should differ to {'a': 2, 'b': Gabriel Falcão, 'c': 'Foo'}, but is the same thing"))


def test_match_regex():
    ("expect('some string').to.match(r'\w{4} \w{6}') matches regex")

    assert this("some string").should.match(r"\w{4} \w{6}")
    assert this("some string").should_not.match(r"^\d*$")

    def opposite():
        assert this("some string").should.match(r"\d{2} \d{4}")

    def opposite_not():
        assert this("some string").should_not.match(r"some string")

    expect(opposite).when.called.to.throw(
        AssertionError,
        "'some string' doesn't match the regular expression /\d{2} \d{4}/")

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw(
        "'some string' should not match the regular expression /some string/")


def test_match_contain():
    ("expect('some string').to.contain('tri')")

    assert this("some string").should.contain("tri")
    assert this("some string").should_not.contain('foo')

    def opposite():
        assert this("some string").should.contain("bar")

    def opposite_not():
        assert this("some string").should_not.contain(r"string")

    expect(opposite).when.called.to.throw(AssertionError)
    if PY3:
        expect(opposite).when.called.to.throw(
            "'bar' should be in 'some string'")
    else:
        expect(opposite).when.called.to.throw(
            "u'bar' should be in u'some string'")

    expect(opposite_not).when.called.to.throw(AssertionError)
    if PY3:
        expect(opposite_not).when.called.to.throw(
            "'string' should NOT be in 'some string'")
    else:
        expect(opposite_not).when.called.to.throw(
            "u'string' should NOT be in u'some string'")


def test_catching_exceptions():

    # Given that I have a function that raises an exceptiont that does *not*
    # inherit from the `Exception` class
    def blah():
        raise SystemExit(2)

    # When I call it testing which exception it's raising, Then it should be
    # successful
    expect(blah).when.called_with().should.throw(SystemExit)


def test_catching_exceptions_with_params():

    # Given that I have a function that raises an exceptiont that does *not*
    # inherit from the `Exception` class
    def blah(foo):
        raise SystemExit(2)

    # When I call it testing which exception it's raising, Then it should be
    # successful
    expect(blah).when.called_with(0).should.throw(SystemExit)


def test_success_with_params():
    def blah(foo):
        pass

    expect(blah).when.called_with(0).should_not.throw(TypeError)


def test_success_with_params_exception():
    def blah():
        pass

    expect(blah).when.called_with(0).should.throw(TypeError)


def test_should_not_be_different():
    ("'something'.should_not.be.different('SOMETHING'.lower())")

    part1 = '''<root>
  <a-tag with-attribute="one">AND A VALUE</a-tag>
</root>'''

    part2 = '''<root>
  <a-tag with-attribute="two">AND A VALUE</a-tag>
</root>'''

    assert this(part1).should.be.different_of(part2)
    assert this(part2).should_not.be.different_of(part2)

    def opposite():
        assert this(part2).should.be.different_of(part2)

    def opposite_not():
        assert this(part1).should_not.be.different_of(part2)

    expect(opposite).when.called.to.throw(AssertionError)
    expect(opposite).when.called.to.throw('''<root>
  <a-tag with-attribute="two">AND A VALUE</a-tag>
</root> should be different of <root>
  <a-tag with-attribute="two">AND A VALUE</a-tag>
</root>''')

    expect(opposite_not).when.called.to.throw(AssertionError)
    expect(opposite_not).when.called.to.throw('''Difference:

  <root>
-   <a-tag with-attribute="one">AND A VALUE</a-tag>
?                           --
+   <a-tag with-attribute="two">AND A VALUE</a-tag>
?                          ++
  </root>''')


def test_equals_handles_mock_call_list():
    ".equal() Should convert mock._CallList instances to lists"

    # Given the following mocked callback
    callback = mock.Mock()

    # When I call the callback with a few parameters twice
    callback(a=1, b=2)
    callback(a=3, b=4)

    # Then I see I can compare the call list without manually
    # converting anything

    callback.call_args_list.should.equal([
        mock.call(a=1, b=2),
        mock.call(a=3, b=4),
    ])

########NEW FILE########
__FILENAME__ = test_cpython_patches
## #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2010-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

import sure
from sure import expect


if sure.allows_new_syntax:
    def test_it_works_with_objects():
        ("anything that inherits from object should be patched")

        (4).should.equal(2 + 2)
        "foo".should.equal("f" + ("o" * 2))
        {}.should.be.empty


def test_dir_conceals_sure_specific_attributes():
    ("dir(obj) should conceal names of methods that were grafted by sure")

    x = 123

    expect(set(dir(x)).intersection(set(sure.POSITIVES))).to.be.empty
    expect(set(dir(x)).intersection(set(sure.NEGATIVES))).to.be.empty


# TODO
# def test_it_works_with_non_objects():
#     ("anything that inherits from non-object should also be patched")

#     class Foo:
#         pass

#     f = Foo()

#     f.should.be.a(Foo)

# def test_can_override_properties():
#     x =1
#     x.should = 2
#     assert x.should == 2

########NEW FILE########
__FILENAME__ = test_old_api
## #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <sure - utility belt for automated testing in python>
# Copyright (C) <2010-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

from six import text_type, PY3
from six.moves import xrange

import sure
from sure.deprecated import that
from sure import VariablesBag, expect
from nose.tools import assert_equals, assert_raises
from sure.compat_py3 import compat_repr, text_type_name


def test_setup_with_context():
    "sure.with_context() runs setup before the function itself"

    def setup(context):
        context.name = "John Resig"

    @sure.that_with_context(setup)
    def john_is_within_context(context):
        assert isinstance(context, VariablesBag)
        assert hasattr(context, "name")

    john_is_within_context()
    assert_equals(
        john_is_within_context.__name__,
        'john_is_within_context',
    )


def test_context_is_not_optional():
    "sure.that_with_context() when no context is given it fails"

    def setup(context):
        context.name = "John Resig"

    @sure.that_with_context(setup)
    def it_crashes():
        assert True

    assert that(it_crashes).raises(
        TypeError, (
        "the function it_crashes defined at test_old_api.py line 55, is being "
        "decorated by either @that_with_context or @scenario, so it should "
        "take at least 1 parameter, which is the test context"),
    )


def test_setup_with_context_context_failing():
    "sure.that_with_context() in a failing test"

    def setup(context):
        context.name = "John Resig"

    @sure.that_with_context(setup)
    def it_fails(context):
        assert False, 'should fail with this exception'

    assert that(it_fails).raises('should fail with this exception')


def test_teardown_with_context():
    "sure.with_context() runs teardown before the function itself"

    class something:
        pass

    def setup(context):
        something.modified = True

    def teardown(context):
        del something.modified

    @sure.that_with_context(setup, teardown)
    def something_was_modified(context):
        assert hasattr(something, "modified")
        assert something.modified

    something_was_modified()
    assert not hasattr(something, "modified")


def test_that_is_a():
    "that() is_a(object)"

    something = "something"

    assert that(something).is_a(text_type)
    assert isinstance(something, text_type)


def test_that_equals():
    "that() equals(string)"

    something = "something"

    assert that('something').equals(something)
    assert something == 'something'


def test_that_differs():
    "that() differs(object)"

    something = "something"

    assert that(something).differs("23123%FYTUGIHOfdf")
    assert something != "23123%FYTUGIHOfdf"


def test_that_has():
    "that() has(object)"
    class Class:
        name = "some class"
    Object = Class()
    dictionary = {
        'name': 'John',
    }
    name = "john"

    assert hasattr(Class, 'name')
    assert that(Class).has("name")
    assert that(Class).like("name")
    assert "name" in that(Class)

    assert hasattr(Object, 'name')
    assert that(Object).has("name")
    assert that(Object).like("name")
    assert "name" in that(Object)

    assert 'name' in dictionary
    assert that(dictionary).has("name")
    assert that(dictionary).like("name")
    assert "name" in that(dictionary)

    assert that(name).has("john")
    assert that(name).like("john")
    assert "john" in that(name)
    assert that(name).has("hn")
    assert that(name).like("hn")
    assert "hn" in that(name)
    assert that(name).has("jo")
    assert that(name).like("jo")
    assert "jo" in that(name)


def test_that_at_key_equals():
    "that().at(object).equals(object)"

    class Class:
        name = "some class"
    Object = Class()
    dictionary = {
        'name': 'John',
    }

    assert that(Class).at("name").equals('some class')
    assert that(Object).at("name").equals('some class')
    assert that(dictionary).at("name").equals('John')


def test_that_len_is():
    "that() len_is(number)"

    lst = range(1000)

    assert that(lst).len_is(1000)
    assert len(lst) == 1000
    assert that(lst).len_is(lst)


def test_that_len_greater_than():
    "that() len_greater_than(number)"

    lst = range(1000)
    lst2 = range(100)

    assert that(lst).len_greater_than(100)
    assert len(lst) == 1000
    assert that(lst).len_greater_than(lst2)


def test_that_len_greater_than_should_raise_assertion_error():
    "that() len_greater_than(number) raise AssertionError"

    lst = list(range(1000))
    try:
        that(lst).len_greater_than(1000)
    except AssertionError as e:
        assert_equals(
            str(e),
            'the length of the list should be greater then %d, but is %d'  \
            % (1000, 1000))


def test_that_len_greater_than_or_equals():
    "that() len_greater_than_or_equals(number)"

    lst = list(range(1000))
    lst2 = list(range(100))

    assert that(lst).len_greater_than_or_equals(100)
    assert that(lst).len_greater_than_or_equals(1000)
    assert len(lst) == 1000
    assert that(lst).len_greater_than_or_equals(lst2)
    assert that(lst).len_greater_than_or_equals(lst)


def test_that_len_greater_than_or_equals_should_raise_assertion_error():
    "that() len_greater_than_or_equals(number) raise AssertionError"

    lst = list(range(1000))
    try:
        that(lst).len_greater_than_or_equals(1001)
    except AssertionError as e:
        assert_equals(
            str(e),
            'the length of %r should be greater then or equals %d, but is %d' \
            % (lst, 1001, 1000))


def test_that_len_lower_than():
    "that() len_lower_than(number)"

    lst = list(range(100))
    lst2 = list(range(1000))

    assert that(lst).len_lower_than(101)
    assert len(lst) == 100
    assert that(lst).len_lower_than(lst2)


def test_that_len_lower_than_should_raise_assertion_error():
    "that() len_lower_than(number) raise AssertionError"

    lst = list(range(1000))
    try:
        that(lst).len_lower_than(1000)
    except AssertionError as e:
        assert_equals(
            str(e),
            'the length of %r should be lower then %d, but is %d' % \
            (lst, 1000, 1000))


def test_that_len_lower_than_or_equals():
    "that() len_lower_than_or_equals(number)"

    lst = list(range(1000))
    lst2 = list(range(1001))

    assert that(lst).len_lower_than_or_equals(1001)
    assert that(lst).len_lower_than_or_equals(1000)
    assert len(lst) == 1000
    assert that(lst).len_lower_than_or_equals(lst2)
    assert that(lst).len_lower_than_or_equals(lst)


def test_that_len_lower_than_or_equals_should_raise_assertion_error():
    "that() len_lower_than_or_equals(number) raise AssertionError"

    lst = list(range(1000))
    try:
        that(lst).len_lower_than_or_equals(100)
    except AssertionError as e:
        assert_equals(
            str(e),
            'the length of %r should be lower then or equals %d, but is %d' % \
            (lst, 100, 1000))


def test_that_checking_all_atributes():
    "that(iterable).the_attribute('name').equals('value')"
    class shape(object):
        def __init__(self, name):
            self.kind = 'geometrical form'
            self.name = name

    shapes = [
        shape('circle'),
        shape('square'),
        shape('rectangle'),
        shape('triangle'),
    ]

    assert that(shapes).the_attribute("kind").equals('geometrical form')


def test_that_checking_all_atributes_of_range():
    "that(iterable, within_range=(1, 2)).the_attribute('name').equals('value')"
    class shape(object):
        def __init__(self, name):
            self.kind = 'geometrical form'
            self.name = name

        def __repr__(self):
            return '<%s:%s>' % (self.kind, self.name)

    shapes = [
        shape('circle'),
        shape('square'),
        shape('square'),
        shape('triangle'),
    ]

    assert shapes[0].name != 'square'
    assert shapes[3].name != 'square'

    assert shapes[1].name == 'square'
    assert shapes[2].name == 'square'

    assert that(shapes, within_range=(1, 2)). \
                           the_attribute("name"). \
                           equals('square')


def test_that_checking_all_elements():
    "that(iterable).every_one_is('value')"
    shapes = [
        'cube',
        'ball',
        'ball',
        'piramid',
    ]

    assert shapes[0] != 'ball'
    assert shapes[3] != 'ball'

    assert shapes[1] == 'ball'
    assert shapes[2] == 'ball'

    assert that(shapes, within_range=(1, 2)).every_one_is('ball')


def test_that_checking_each_matches():
    "that(iterable).in_each('').equals('value')"
    class animal(object):
        def __init__(self, kind):
            self.attributes = {
                'class': 'mammal',
                'kind': kind,
            }

    animals = [
        animal('dog'),
        animal('cat'),
        animal('cow'),
        animal('cow'),
        animal('cow'),
    ]

    assert animals[0].attributes['kind'] != 'cow'
    assert animals[1].attributes['kind'] != 'cow'

    assert animals[2].attributes['kind'] == 'cow'
    assert animals[3].attributes['kind'] == 'cow'
    assert animals[4].attributes['kind'] == 'cow'

    assert animals[0].attributes['class'] == 'mammal'
    assert animals[1].attributes['class'] == 'mammal'
    assert animals[2].attributes['class'] == 'mammal'
    assert animals[3].attributes['class'] == 'mammal'
    assert animals[4].attributes['class'] == 'mammal'

    assert that(animals).in_each("attributes['class']").matches('mammal')
    assert that(animals).in_each("attributes['class']"). \
           matches(['mammal','mammal','mammal','mammal','mammal'])

    assert that(animals).in_each("attributes['kind']"). \
           matches(['dog','cat','cow','cow','cow'])

    try:
        assert that(animals).in_each("attributes['kind']").matches(['dog'])
        assert False, 'should not reach here'
    except AssertionError as e:
        assert that(text_type(e)).equals(
            '%r has 5 items, but the matching list has 1: %r' % (
                ['dog','cat','cow','cow','cow'], ['dog'],
            )
        )


def test_that_raises():
    "that(callable, with_args=[arg1], and_kwargs={'arg2': 'value'}).raises(SomeException)"
    global called

    called = False

    def function(arg1=None, arg2=None):
        global called
        called = True
        if arg1 == 1 and arg2 == 2:
            raise RuntimeError('yeah, it failed')

        return "OK"

    try:
        function(1, 2)
        assert False, 'should not reach here'

    except RuntimeError as e:
        assert text_type(e) == 'yeah, it failed'

    except Exception:
        assert False, 'should not reach here'

    finally:
        assert called
        called = False

    assert_raises(RuntimeError, function, 1, 2)

    called = False
    assert_equals(function(3, 5), 'OK')
    assert called

    called = False
    assert that(function, with_args=[1], and_kwargs={'arg2': 2}). \
           raises(RuntimeError)
    assert called

    called = False
    assert that(function, with_args=[1], and_kwargs={'arg2': 2}). \
           raises(RuntimeError, 'yeah, it failed')
    assert called

    called = False
    assert that(function, with_args=[1], and_kwargs={'arg2': 2}). \
           raises('yeah, it failed')
    assert called

    called = False
    assert that(function, with_kwargs={'arg1': 1, 'arg2': 2}). \
           raises(RuntimeError)
    assert called

    called = False
    assert that(function, with_kwargs={'arg1': 1, 'arg2': 2}). \
           raises(RuntimeError, 'yeah, it failed')
    assert called

    called = False
    assert that(function, with_kwargs={'arg1': 1, 'arg2': 2}). \
           raises('yeah, it failed')
    assert called

    called = False
    assert that(function, with_kwargs={'arg1': 1, 'arg2': 2}). \
           raises(r'it fail')
    assert called

    called = False
    assert that(function, with_kwargs={'arg1': 1, 'arg2': 2}). \
           raises(RuntimeError, r'it fail')
    assert called


def test_that_looks_like():
    "that('String\\n with BREAKLINE').looks_like('string with breakline')"
    assert that('String\n with BREAKLINE').looks_like('string with breakline')


def test_that_raises_with_args():
    "that(callable, with_args=['foo']).raises(FooError)"

    class FooError(Exception):
        pass

    def my_function(string):
        if string == 'foo':
            raise FooError('OOps')

    assert that(my_function, with_args=['foo']).raises(FooError, 'OOps')


def test_that_does_not_raise_with_args():
    "that(callable).doesnt_raise(FooError) and does_not_raise"

    class FooError(Exception):
        pass

    def my_function(string):
        if string == 'foo':
            raise FooError('OOps')

    assert that(my_function, with_args=['foo']).raises(FooError, 'OOps')


def test_that_contains_string():
    "that('foobar').contains('foo')"

    assert 'foo' in 'foobar'
    assert that('foobar').contains('foo')


def test_that_doesnt_contain_string():
    "that('foobar').does_not_contain('123'), .doesnt_contain"

    assert '123' not in 'foobar'
    assert that('foobar').doesnt_contain('123')
    assert that('foobar').does_not_contain('123')


def test_that_contains_none():
    "that('foobar').contains(None)"

    def assertions():
        # We can't use unicode in Py2, otherwise it will try to coerce
        assert that('foobar' if PY3 else b'foobar').contains(None)

    assert that(assertions).raises(
        TypeError,
        "'in <string>' requires string as left operand, not NoneType",
    )


def test_that_none_contains_string():
    "that(None).contains('bungalow')"

    try:
        assert that(None).contains('bungalow')
        assert False, 'should not reach here'
    except Exception as e:
        assert_equals(
            text_type(e),
            "argument of type 'NoneType' is not iterable",
        )


def test_that_some_iterable_is_empty():
    "that(some_iterable).is_empty and that(something).are_empty"

    assert that([]).is_empty
    assert that([]).are_empty

    assert that(tuple()).is_empty
    assert that({}).are_empty

    def fail_single():
        assert that((1,)).is_empty

    assert that(fail_single).raises('(1,) is not empty, it has 1 item')

    def fail_plural():
        assert that((1, 2)).is_empty

    assert that(fail_plural).raises('(1, 2) is not empty, it has 2 items')


def test_that_something_is_empty_raises():
    "that(something_not_iterable).is_empty and that(something_not_iterable).are_empty raises"

    obj = object()

    def fail():
        assert that(obj).is_empty
        assert False, 'should not reach here'

    assert that(fail).raises('%r is not iterable' % obj)


def test_that_something_iterable_matches_another():
    "that(something_iterable).matches(another_iterable)"

    # types must be unicode in py3, bute bytestrings in py2
    KlassOne = type('KlassOne' if PY3 else b'KlassOne', (object,), {})
    KlassTwo = type('KlassTwo' if PY3 else b'KlassTwo', (object,), {})
    one = [
        ("/1", KlassOne),
        ("/2", KlassTwo),
    ]

    two = [
        ("/1", KlassOne),
        ("/2", KlassTwo),
    ]

    assert that(one).matches(two)
    assert that(one).equals(two)

    def fail_1():
        assert that([1]).matches(xrange(2))

    class Fail2(object):
        def __init__(self):
            assert that(xrange(1)).matches([2])

    class Fail3(object):
        def __call__(self):
            assert that(xrange(1)).matches([2])

    xrange_name = xrange.__name__
    assert that(fail_1).raises('X is a list and Y is a {0} instead'.format(xrange_name))
    assert that(Fail2).raises('X is a {0} and Y is a list instead'.format(xrange_name))
    assert that(Fail3()).raises('X is a {0} and Y is a list instead'.format(xrange_name))


def test_within_pass():
    "within(five=miliseconds) will pass"
    from sure import within, miliseconds

    within(five=miliseconds)(lambda *a: None)()


def test_within_fail():
    "within(five=miliseconds) will fail"
    import time
    from sure import within, miliseconds

    def sleepy(*a):
        time.sleep(0.7)

    failed = False
    try:
        within(five=miliseconds)(sleepy)()
    except AssertionError as e:
        failed = True
        assert_equals('sleepy did not run within five miliseconds', str(e))

    assert failed, 'within(five=miliseconds)(sleepy) did not fail'


def test_word_to_number():
    assert_equals(sure.word_to_number('one'),      1)
    assert_equals(sure.word_to_number('two'),      2)
    assert_equals(sure.word_to_number('three'),    3)
    assert_equals(sure.word_to_number('four'),     4)
    assert_equals(sure.word_to_number('five'),     5)
    assert_equals(sure.word_to_number('six'),      6)
    assert_equals(sure.word_to_number('seven'),    7)
    assert_equals(sure.word_to_number('eight'),    8)
    assert_equals(sure.word_to_number('nine'),     9)
    assert_equals(sure.word_to_number('ten'),     10)
    assert_equals(sure.word_to_number('eleven'),  11)
    assert_equals(sure.word_to_number('twelve'),  12)


def test_word_to_number_fail():
    failed = False
    try:
        sure.word_to_number('twenty')
    except AssertionError as e:
        failed = True
        assert_equals(
            text_type(e),
            'sure supports only literal numbers from one ' \
            'to twelve, you tried the word "twenty"')

    assert failed, 'should raise assertion error'


def test_microsecond_unit():
    "testing microseconds convertion"
    cfrom, cto = sure.UNITS[sure.microsecond]

    assert_equals(cfrom(1), 100000)
    assert_equals(cto(1), 1)

    cfrom, cto = sure.UNITS[sure.microseconds]

    assert_equals(cfrom(1), 100000)
    assert_equals(cto(1), 1)


def test_milisecond_unit():
    "testing miliseconds convertion"
    cfrom, cto = sure.UNITS[sure.milisecond]

    assert_equals(cfrom(1), 1000)
    assert_equals(cto(100), 1)

    cfrom, cto = sure.UNITS[sure.miliseconds]

    assert_equals(cfrom(1), 1000)
    assert_equals(cto(100), 1)


def test_second_unit():
    "testing seconds convertion"
    cfrom, cto = sure.UNITS[sure.second]

    assert_equals(cfrom(1), 1)
    assert_equals(cto(100000), 1)

    cfrom, cto = sure.UNITS[sure.seconds]

    assert_equals(cfrom(1), 1)
    assert_equals(cto(100000), 1)


def test_minute_unit():
    "testing minutes convertion"
    cfrom, cto = sure.UNITS[sure.minute]

    assert_equals(cfrom(60), 1)
    assert_equals(cto(1), 6000000)

    cfrom, cto = sure.UNITS[sure.minutes]

    assert_equals(cfrom(60), 1)
    assert_equals(cto(1), 6000000)


def test_within_pass_utc():
    "within(five=miliseconds) gives utc parameter"
    from sure import within, miliseconds
    from datetime import datetime

    def assert_utc(utc):
        assert isinstance(utc, datetime)

    within(five=miliseconds)(assert_utc)()


def test_that_is_a_matcher_should_absorb_callables_to_be_used_as_matcher():
    "that.is_a_matcher should absorb callables to be used as matcher"
    @that.is_a_matcher
    def is_truthful(what):
        assert bool(what), '%s is so untrue' % (what)
        return 'foobar'

    assert that('friend').is_truthful()
    assert_equals(that('friend').is_truthful(), 'foobar')


def test_accepts_setup_list():
    "sure.with_context() accepts a list of callbacks for setup"

    def setup1(context):
        context.first_name = "John"

    def setup2(context):
        context.last_name = "Resig"

    @sure.that_with_context([setup1, setup2])
    def john_is_within_context(context):
        assert context.first_name == 'John'
        assert context.last_name == 'Resig'

    john_is_within_context()
    assert_equals(
        john_is_within_context.__name__,
        'john_is_within_context',
    )


def test_accepts_teardown_list():
    "sure.with_context() runs teardown before the function itself"

    class something:
        modified = True
        finished = 'nope'

    def setup(context):
        something.modified = False

    def teardown1(context):
        something.modified = True

    def teardown2(context):
        something.finished = 'yep'

    @sure.that_with_context(setup, [teardown1, teardown2])
    def something_was_modified(context):
        assert not something.modified
        assert something.finished == 'nope'

    something_was_modified()
    assert something.modified
    assert something.finished == 'yep'


def test_scenario_is_alias_for_context_on_setup_and_teardown():
    "@scenario aliases @that_with_context for setup and teardown"
    from sure import scenario

    def setup(context):
        context.name = "Robert C Martin"

    def teardown(context):
        assert_equals(context.name, "Robert C Martin")

    @scenario([setup], [teardown])
    def robert_is_within_context(context):
        "Robert is within context"
        assert isinstance(context, VariablesBag)
        assert hasattr(context, "name")
        assert_equals(context.name, "Robert C Martin")

    robert_is_within_context()
    assert_equals(
        robert_is_within_context.__name__,
        'robert_is_within_context',
    )


def test_actions_returns_context():
    "the actions always returns the context"
    from sure import action_for, scenario

    def with_setup(context):
        @action_for(context)
        def action1():
            pass

        @action_for(context)
        def action2():
            pass

    @scenario(with_setup)
    def i_can_use_actions(context):
        assert that(context.action1()).equals(context)
        assert that(context.action2()).equals(context)
        return True

    assert i_can_use_actions()


def test_actions_providing_variables_in_the_context():
    "the actions should be able to declare the variables they provide"
    from sure import action_for, scenario

    def with_setup(context):
        @action_for(context, provides=['var1', 'foobar'])
        def the_context_has_variables():
            context.var1 = 123
            context.foobar = "qwerty"

    @scenario(with_setup)
    def the_providers_are_working(Then):
        Then.the_context_has_variables()
        assert hasattr(Then, 'var1')
        assert hasattr(Then, 'foobar')
        assert hasattr(Then, '__sure_providers_of__')

        providers = Then.__sure_providers_of__
        action = Then.the_context_has_variables.__name__

        providers_of_var1 = [p.__name__ for p in providers['var1']]
        assert that(providers_of_var1).contains(action)

        providers_of_foobar = [p.__name__ for p in providers['foobar']]
        assert that(providers_of_foobar).contains(action)

        return True

    assert the_providers_are_working()


def test_fails_when_action_doesnt_fulfill_the_agreement_of_provides():
    "it fails when an action doesn't fulfill its agreements"
    from sure import action_for, scenario

    error = 'the action "bad_action" was supposed to provide the ' \
        'attribute "two" into the context, but it did not. Please ' \
        'double check its implementation'

    def with_setup(context):
        @action_for(context, provides=['one', 'two'])
        def bad_action():
            context.one = 123

    @scenario(with_setup)
    def the_providers_are_working(the):
        assert that(the.bad_action).raises(AssertionError, error)
        return True

    assert the_providers_are_working()


def test_depends_on_failing_due_nothing_found():
    "it fails when an action depends on some attribute that is not " \
        "provided by any other previous action"
    import os
    from sure import action_for, scenario

    fullpath = os.path.abspath(__file__).replace('.pyc', '.py')
    error = 'the action "lonely_action" defined at %s:900 ' \
        'depends on the attribute "something" to be available in the' \
        ' context. It turns out that there are no actions providing ' \
        'that. Please double-check the implementation' % fullpath

    def with_setup(context):
        @action_for(context, depends_on=['something'])
        def lonely_action():
            pass

    @scenario(with_setup)
    def depends_on_fails(the):
        assert that(the.lonely_action).raises(AssertionError, error)
        return True

    assert depends_on_fails()


def test_depends_on_failing_due_not_calling_a_previous_action():
    "it fails when an action depends on some attribute that is being " \
        "provided by other actions"

    import os
    from sure import action_for, scenario

    fullpath = os.path.abspath(__file__).replace('.pyc', '.py')
    error = 'the action "my_action" defined at {0}:930 ' \
        'depends on the attribute "some_attr" to be available in the context.'\
        ' You need to call one of the following actions beforehand:\n' \
        ' -> dependency_action at {0}:926'.replace('{0}', fullpath)

    def with_setup(context):
        @action_for(context, provides=['some_attr'])
        def dependency_action():
            context.some_attr = True

        @action_for(context, depends_on=['some_attr'])
        def my_action():
            pass

    @scenario(with_setup)
    def depends_on_fails(the):
        assert that(the.my_action).raises(AssertionError, error)
        return True

    assert depends_on_fails()


def test_that_contains_dictionary_keys():
    "that(dict(name='foobar')).contains('name')"

    data = dict(name='foobar')
    assert 'name' in data
    assert 'name' in data.keys()
    assert that(data).contains('name')


def test_that_contains_list():
    "that(['foobar', '123']).contains('foobar')"

    data = ['foobar', '123']
    assert 'foobar' in data
    assert that(data).contains('foobar')


def test_that_contains_set():
    "that(set(['foobar', '123']).contains('foobar')"

    data = set(['foobar', '123'])
    assert 'foobar' in data
    assert that(data).contains('foobar')


def test_that_contains_tuple():
    "that(('foobar', '123')).contains('foobar')"

    data = ('foobar', '123')
    assert 'foobar' in data
    assert that(data).contains('foobar')


def test_variables_bag_provides_meaningful_error_on_nonexisting_attribute():
    "VariablesBag() provides a meaningful error when attr does not exist"

    context = VariablesBag()

    context.name = "John"
    context.foo = "bar"

    assert that(context.name).equals("John")
    assert that(context.foo).equals("bar")

    def access_nonexisting_attr():
        assert context.bleh == 'crash :('

    assert that(access_nonexisting_attr).raises(
        AssertionError,
        'you have tried to access the attribute \'bleh\' from the context ' \
        '(aka VariablesBag), but there is no such attribute assigned to it. ' \
        'Maybe you misspelled it ? Well, here are the options: ' \
        '[\'name\', \'foo\']',
    )


def test_actions_providing_dinamically_named_variables():
    "the actions should be able to declare the variables they provide"
    from sure import action_for, scenario

    def with_setup(context):
        @action_for(context, provides=['var1', '{0}'])
        def the_context_has_variables(first_arg):
            context.var1 = 123
            context[first_arg] = "qwerty"

    @scenario(with_setup)
    def the_providers_are_working(Then):
        Then.the_context_has_variables('JohnDoe')
        assert hasattr(Then, 'var1')
        assert 'JohnDoe' in Then
        assert hasattr(Then, '__sure_providers_of__')

        providers = Then.__sure_providers_of__
        action = Then.the_context_has_variables.__name__

        providers_of_var1 = [p.__name__ for p in providers['var1']]
        assert that(providers_of_var1).contains(action)

        providers_of_JohnDoe = [p.__name__ for p in providers['JohnDoe']]
        assert that(providers_of_JohnDoe).contains(action)

        return True

    assert the_providers_are_working()


def test_deep_equals_dict_level1_success():
    "that() deep_equals(dict) succeeding on level 1"

    something = {
        'one': 'yeah',
    }

    assert that(something).deep_equals({
        'one': 'yeah',
    })


def test_deep_equals_dict_level1_fail():
    "that() deep_equals(dict) failing on level 1"

    something = {
        'one': 'yeah',
    }

    def assertions():
        assert that(something).deep_equals({
            'one': 'oops',
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'one': 'yeah'}\n" \
        "    and\n" \
        "Y = {'one': 'oops'}\n" \
        "X['one'] is 'yeah' whereas Y['one'] is 'oops'",
    ))


def test_deep_equals_list_level1_success():
    "that(list) deep_equals(list) succeeding on level 1"

    something = ['one', 'yeah']
    assert that(something).deep_equals(['one', 'yeah'])


def test_deep_equals_list_level1_fail_by_value():
    "that(list) deep_equals(list) failing on level 1"

    something = ['one', 'yeahs']

    def assertions():
        assert that(something).deep_equals(['one', 'yeah'])

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = ['one', 'yeahs']\n" \
        "    and\n" \
        "Y = ['one', 'yeah']\n" \
        "X[1] is 'yeahs' whereas Y[1] is 'yeah'",
    ))


def test_deep_equals_list_level1_fail_by_length_x_gt_y():
    "that(list) deep_equals(list) failing by length (len(X) > len(Y))"

    something = ['one', 'yeah', 'awesome!']

    def assertions():
        assert that(something).deep_equals(['one', 'yeah'])

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = ['one', 'yeah', 'awesome!']\n" \
        "    and\n" \
        "Y = ['one', 'yeah']\n" \
        "X has 3 items whereas Y has only 2",
    ))


def test_deep_equals_list_level1_fail_by_length_y_gt_x():
    "that(list) deep_equals(list) failing by length (len(Y) > len(X))"

    something = ['one', 'yeah']

    def assertions():
        assert that(something).deep_equals(['one', 'yeah', 'damn'])

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = ['one', 'yeah']\n" \
        "    and\n" \
        "Y = ['one', 'yeah', 'damn']\n" \
        "Y has 3 items whereas X has only 2",
    ))


def test_deep_equals_dict_level1_fails_missing_key_on_y():
    "that(X) deep_equals(Y) fails when Y is missing a key that X has"

    something = {
        'one': 'yeah',
    }

    def assertions():
        assert that(something).deep_equals({
            'two': 'yeah',
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'one': 'yeah'}\n" \
        "    and\n" \
        "Y = {'two': 'yeah'}\n" \
        "X has the key 'one' whereas Y does not",
    ))


def test_deep_equals_failing_basic_vs_complex():
    "that(X) deep_equals(Y) fails with basic vc complex type"

    def assertions():
        assert that('two yeah').deep_equals({
            'two': 'yeah',
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = 'two yeah'\n"
        "    and\n" \
        "Y = {'two': 'yeah'}\n" \
        "X is a %s and Y is a dict instead" % text_type_name,
    ))


def test_deep_equals_failing_complex_vs_basic():
    "that(X) deep_equals(Y) fails with complex vc basic type"

    def assertions():
        assert that({'two': 'yeah'}).deep_equals('two yeah')

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'two': 'yeah'}\n" \
        "    and\n" \
        "Y = 'two yeah'\n"
        "X is a dict and Y is a %s instead" % text_type_name,
    ))


def test_deep_equals_tuple_level1_success():
    "that(tuple) deep_equals(tuple) succeeding on level 1"

    something = ('one', 'yeah')
    assert that(something).deep_equals(('one', 'yeah'))


def test_deep_equals_tuple_level1_fail_by_value():
    "that(tuple) deep_equals(tuple) failing on level 1"

    something = ('one', 'yeahs')

    def assertions():
        assert that(something).deep_equals(('one', 'yeah'))

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = ('one', 'yeahs')\n" \
        "    and\n" \
        "Y = ('one', 'yeah')\n" \
        "X[1] is 'yeahs' whereas Y[1] is 'yeah'",
    ))


def test_deep_equals_tuple_level1_fail_by_length_x_gt_y():
    "that(tuple) deep_equals(tuple) failing by length (len(X) > len(Y))"

    something = ('one', 'yeah', 'awesome!')

    def assertions():
        assert that(something).deep_equals(('one', 'yeah'))

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = ('one', 'yeah', 'awesome!')\n" \
        "    and\n" \
        "Y = ('one', 'yeah')\n" \
        "X has 3 items whereas Y has only 2",
    ))


def test_deep_equals_tuple_level1_fail_by_length_y_gt_x():
    "that(tuple) deep_equals(tuple) failing by length (len(Y) > len(X))"

    something = ('one', 'yeah')

    def assertions():
        assert that(something).deep_equals(('one', 'yeah', 'damn'))

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = ('one', 'yeah')\n" \
        "    and\n" \
        "Y = ('one', 'yeah', 'damn')\n" \
        "Y has 3 items whereas X has only 2",
    ))


def test_deep_equals_fallsback_to_generic_comparator():
    "that() deep_equals(dict) falling back to generic comparator"
    from datetime import datetime
    now = datetime.now()
    something = {
        'one': 'yeah',
        'date': now,
    }

    assert that(something).deep_equals({
        'one': 'yeah',
        'date': now,
    })


def test_deep_equals_fallsback_to_generic_comparator_failing():
    "that() deep_equals(dict) with generic comparator failing"
    from datetime import datetime
    now = datetime(2012, 3, 5)
    tomorrow = datetime(2012, 3, 6)
    something = {
        'date': now,
    }

    def assertions():
        assert that(something).deep_equals({
            'date': tomorrow,
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'date': datetime.datetime(2012, 3, 5, 0, 0)}\n" \
        "    and\n" \
        "Y = {'date': datetime.datetime(2012, 3, 6, 0, 0)}\n" \
        "X['date'] != Y['date']",
    ))


def test_deep_equals_fallsback_to_generic_comparator_failing_type():
    "that() deep_equals(dict) with generic comparator failing"
    from datetime import datetime
    now = datetime(2012, 3, 5)
    something = {
        'date': now,
    }

    def assertions():
        assert that(something).deep_equals({
            'date': None,
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'date': datetime.datetime(2012, 3, 5, 0, 0)}\n" \
        "    and\n" \
        "Y = {'date': None}\n" \
        "X['date'] is a datetime and Y['date'] is a NoneType instead",
    ))


def test_deep_equals_dict_level2_success():
    "that() deep_equals(dict) succeeding on level 2"

    something = {
        'one': 'yeah',
        'another': {
            'two': 'cool',
        },
    }

    assert that(something).deep_equals({
        'one': 'yeah',
        'another': {
            'two': 'cool',
        },
    })


def test_deep_equals_dict_level2_list_success():
    "that() deep_equals(dict) succeeding on level 2"

    something = {
        'one': 'yeah',
        'another': ['one', 'two', 3],
    }

    assert that(something).deep_equals({
        'one': 'yeah',
        'another': ['one', 'two', 3],
    })


def test_deep_equals_dict_level2_fail():
    "that() deep_equals(dict) failing on level 2"

    something = {
        'one': 'yeah',
        'another': {
            'two': '##',
        },
    }

    def assertions():
        assert that(something).deep_equals({
            'one': 'yeah',
            'another': {
                'two': '$$',
            },
        })
    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'another': {'two': '##'}, 'one': 'yeah'}\n" \
        "    and\n" \
        "Y = {'another': {'two': '$$'}, 'one': 'yeah'}\n" \
        "X['another']['two'] is '##' whereas Y['another']['two'] is '$$'",
    ))


def test_deep_equals_dict_level3_fail_values():
    "that() deep_equals(dict) failing on level 3"

    something = {
        'my::all_users': [
            {'name': 'John', 'age': 33},
        ],
    }

    def assertions():
        assert that(something).deep_equals({
            'my::all_users': [
                {'name': 'John', 'age': 30},
            ],
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'my::all_users': [{'age': 33, 'name': 'John'}]}\n" \
        "    and\n" \
        "Y = {'my::all_users': [{'age': 30, 'name': 'John'}]}\n" \
        "X['my::all_users'][0]['age'] is 33 whereas Y['my::all_users'][0]['age'] is 30",
    ))


def test_deep_equals_dict_level3_fails_missing_key():
    "that() deep_equals(dict) failing on level 3 when missing a key"

    something = {
        'my::all_users': [
            {'name': 'John', 'age': 33},
        ],
    }

    def assertions():
        assert that(something).deep_equals({
            'my::all_users': [
                {'name': 'John', 'age': 30, 'foo': 'bar'},
            ],
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'my::all_users': [{'age': 33, 'name': 'John'}]}\n" \
        "    and\n" \
        "Y = {'my::all_users': [{'age': 30, 'foo': 'bar', 'name': 'John'}]}\n" \
        "X['my::all_users'][0] does not have the key 'foo' whereas Y['my::all_users'][0] has it",
    ))


def test_deep_equals_dict_level3_fails_extra_key():
    "that() deep_equals(dict) failing on level 3 when has an extra key"

    something = {
        'my::all_users': [
            {'name': 'John', 'age': 33, 'foo': 'bar'},
        ],
    }

    def assertions():
        assert that(something).deep_equals({
            'my::all_users': [
                {'name': 'John', 'age': 30},
            ],
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'my::all_users': [{'age': 33, 'foo': 'bar', 'name': 'John'}]}\n" \
        "    and\n" \
        "Y = {'my::all_users': [{'age': 30, 'name': 'John'}]}\n" \
        "X['my::all_users'][0] has the key 'foo' whereas Y['my::all_users'][0] does not",
    ))


def test_deep_equals_dict_level3_fails_different_key():
    "that() deep_equals(dict) failing on level 3 when has an extra key"

    something = {
        'my::all_users': [
            {'name': 'John', 'age': 33, 'foo': 'bar'},
        ],
    }

    def assertions():
        assert that(something).deep_equals({
            'my::all_users': [
            {'name': 'John', 'age': 33, 'bar': 'foo'},
            ],
        })

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'my::all_users': [{'age': 33, 'foo': 'bar', 'name': 'John'}]}\n" \
        "    and\n" \
        "Y = {'my::all_users': [{'age': 33, 'bar': 'foo', 'name': 'John'}]}\n" \
        "X['my::all_users'][0] has the key 'foo' whereas Y['my::all_users'][0] does not",
    ))


def test_deep_equals_list_level2_fail_by_length_x_gt_y():
    "that(list) deep_equals(list) failing by length (len(X) > len(Y))"

    something = {'iterable': ['one', 'yeah', 'awesome!']}

    def assertions():
        assert that(something).deep_equals({'iterable': ['one', 'yeah']})

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = {'iterable': ['one', 'yeah', 'awesome!']}\n" \
        "    and\n" \
        "Y = {'iterable': ['one', 'yeah']}\n" \
        "X has 3 items whereas Y has only 2",
    ))


def test_deep_equals_list_level2_fail_by_length_y_gt_x():
    "that(list) deep_equals(list) failing by length (len(Y) > len(X))"

    something = ['one', 'yeah']

    def assertions():
        assert that(something).deep_equals(['one', 'yeah', 'damn'])

    assert that(assertions).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = ['one', 'yeah']\n" \
        "    and\n" \
        "Y = ['one', 'yeah', 'damn']\n" \
        "Y has 3 items whereas X has only 2",
    ))


def test_function_decorated_with_wip_should_set_a_flag():
    "@sure.work_in_progress should set an internal flag into `sure`"

    @sure.work_in_progress
    def this_was_called():
        assert sure.it('is_running')
        return True

    assert not sure._registry['is_running']
    assert this_was_called()
    assert not sure._registry['is_running']


def test_that_equals_fails():
    "that() equals(string) when it's supposed to fail"

    something = "else"

    def fail():
        assert that('something').equals(something)

    assert that(fail).raises(
        AssertionError, compat_repr(
        "given\n" \
        "X = 'something'\n" \
        "    and\n" \
        "Y = 'else'\n" \
        "X is 'something' whereas Y is 'else'",
    ))


def test_raises_with_string():
    "that(callable).raises('message') should compare the message"

    def it_fails():
        assert False, 'should fail with this exception'

    try:
        that(it_fails).raises('wrong msg')
        raise RuntimeError('should not reach here')
    except AssertionError as e:
        assert that(text_type(e)).contains('''EXPECTED:
wrong msg

GOT:
should fail with this exception''')


def test_deep_equals_weird():
    part1 = [
        ('Bootstraping Redis role', []),
        ('Restart scalarizr', []),
        ('Rebundle server', ['rebundle']),
        ('Use new role', ['rebundle']),
        ('Restart scalarizr after bundling', ['rebundle']),
        ('Bundling data', []),
        ('Modifying data', []),
        ('Reboot server', []),
        ('Backuping data on Master', []),
        ('Setup replication', []),
        ('Restart scalarizr in slave', []),
        ('Slave force termination', []),
        ('Slave delete EBS', ['ec2']),
        ('Setup replication for EBS test', ['ec2']),
        ('Writing on Master, reading on Slave', []),
        ('Slave -> Master promotion', []),
        ('Restart farm', ['restart_farm']),
    ]

    part2 = [
        ('Bootstraping Redis role', ['rebundle', 'rebundle', 'rebundle']),
        ('Restart scalarizr', []),
        ('Rebundle server', ['rebundle']),
        ('Use new role', ['rebundle']),
        ('Restart scalarizr after bundling', ['rebundle']),
        ('Bundling data', []),
        ('Modifying data', []),
        ('Reboot server', []),
        ('Backuping data on Master', []),
        ('Setup replication', []),
        ('Restart scalarizr in slave', []),
        ('Slave force termination', []),
        ('Slave delete EBS', ['ec2']),
        ('Setup replication for EBS test', ['ec2']),
        ('Writing on Master, reading on Slave', []),
        ('Slave -> Master promotion', []),
        ('Restart farm', ['restart_farm']),
    ]

    expect(that(part1).equals).when.called_with(part2).should.throw("")

########NEW FILE########
__FILENAME__ = test_safe_repr
## #!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from six import  PY3

from sure import expect
from sure.core import safe_repr
from sure.compat_py3 import compat_repr


def test_basic_list():
    "safe_repr should display a simple list"
    X = ['one', 'yeah']
    expect(safe_repr(X)).should.equal(compat_repr(
        "['one', 'yeah']"
    ))


def test_basic_dict():
    "safe_repr should return a sorted repr"
    X = {'b': 'd', 'a': 'c'}
    expect(safe_repr(X)).should.equal(compat_repr(
        "{'a': 'c', 'b': 'd'}"
    ))


def test_nested_dict():
    "dicts nested inside values should also get sorted"
    X = {'my::all_users': [{'age': 33, 'name': 'John', 'foo': 'bar'}]}
    expect(safe_repr(X)).should.equal(compat_repr(
        '''{'my::all_users': [{'age': 33, 'foo': 'bar', 'name': 'John'}]}'''
    ))


def test_unicode():
    "dicts with unicode should work properly"
    class Y(object):
        def __init__(self, x):
            self.x = x

        def __repr__(self):
            if PY3:
                # PY3K should return the regular (unicode) string
                return self.x
            else:
                return self.x.encode('utf-8')

        def __eq__(self, other):
            return self.x == other.x

    y1 = {
        'a': 2,
        'b': Y('Gabriel Falcão'),
        'c': 'Foo',
    }
    name = 'Gabriel Falcão' if PY3 else 'Gabriel Falc\xe3o'

    expect(safe_repr(y1)).should.equal(compat_repr(
        "{'a': 2, 'b': %s, 'c': 'Foo'}" % name
    ))

########NEW FILE########
