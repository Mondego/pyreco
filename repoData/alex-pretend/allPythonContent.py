__FILENAME__ = pretend
import functools
import sys


PY3K = sys.version_info >= (3,)


methods = set([
    "__iter__",
    "__len__",
    "__contains__",
    "__getitem__",
    "__setitem__",
    "__delitem__",

    "__enter__",
    "__exit__",

    "__lt__",
    "__le__",
    "__eq__",
    "__ne__",
    "__gt__",
    "__ge__",

    "__add__",
    "__and__",
    "__divmod__",
    "__floordiv__",
    "__lshift__",
    "__mod__",
    "__mul__",
    "__or__",
    "__pow__",
    "__rshift__",
    "__sub__",
    "__truediv__",
    "__xor__",

    "__repr__",
])
if PY3K:
    methods.add("__next__")
    methods.add("__bool__")
else:
    methods.add("__div__")
    methods.add("__nonzero__")
MAGIC_METHODS = frozenset(methods)
del methods


def _build_magic_dispatcher(method):
    def inner(self, *args, **kwargs):
        return self.__dict__[method](*args, **kwargs)
    inner.__name__ = method
    return inner


class stub(object):
    _classes_cache = {}

    def __new__(cls, **kwargs):
        magic_methods_present = MAGIC_METHODS.intersection(kwargs)
        if magic_methods_present not in cls._classes_cache:
            attrs = dict(
                (method, _build_magic_dispatcher(method))
                for method in magic_methods_present
            )
            attrs["__module__"] = cls.__module__
            cls._classes_cache[magic_methods_present] = (
                type("stub", (cls,), attrs)
            )
        new_cls = cls._classes_cache[magic_methods_present]
        return super(stub, new_cls).__new__(new_cls)

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '<stub(%s)>' % ', '.join([
            '%s=%r' % (key, val)
            for key, val in self.__dict__.items()
        ])


def raiser(exc):
    if (
        not (
            isinstance(exc, BaseException) or
            isinstance(exc, type) and issubclass(exc, BaseException)
        )
    ):
        raise TypeError("exc must be either an exception instance or class.")

    def inner(*args, **kwargs):
        raise exc
    return inner


class call(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __eq__(self, other):
        if not isinstance(other, call):
            return NotImplemented
        return self.args == other.args and self.kwargs == other.kwargs

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((
            self.args,
            frozenset(self.kwargs.items())
        ))

    def __repr__(self):
        args = ", ".join(map(repr, self.args))
        kwargs = ", ".join("%s=%r" % (k, v) for k, v in self.kwargs.items())
        comma = ", " if args and kwargs else ""
        return "<call(%s%s%s)>" % (args, comma, kwargs)


def call_recorder(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        inner.calls.append(call(*args, **kwargs))
        return func(*args, **kwargs)
    inner.calls = []
    return inner

########NEW FILE########
__FILENAME__ = test_pretend
import operator

import pytest

from pretend import stub, raiser, call, call_recorder, PY3K


class TestStub(object):
    def test_attribute(self):
        x = stub(attr=3)
        assert hasattr(x, "attr")
        assert x.attr == 3

    def test_function(self):
        x = stub(meth=lambda x, y: x + y)
        assert x.meth(3, 4) == 7

    def test_iter(self):
        x = stub(__iter__=lambda: iter([1, 2, 3]))
        iterator = iter(x)
        assert next(iterator) == 1

    @pytest.mark.skipif("not PY3K")
    def test_next(self):
        x = stub(__next__=lambda: 12)
        assert next(x) == 12

    def test_contains(self):
        x = stub(__contains__=lambda other: True)
        assert "hello world" in x

    @pytest.mark.skipif("PY3K")
    def test_nonzero(self):
        x = stub(__nonzero__=lambda: False)
        assert not bool(x)

    @pytest.mark.skipif("not PY3K")
    def test_bool(self):
        x = stub(__bool__=lambda: False)
        assert not bool(x)

    def test_len(self):
        x = stub(__len__=lambda: 12)
        assert len(x) == 12

    @pytest.mark.parametrize(("func", "op"), [
        (operator.lt, "__lt__"),
        (operator.le, "__le__"),
        (operator.eq, "__eq__"),
        (operator.ne, "__ne__"),
        (operator.gt, "__gt__"),
        (operator.ge, "__ge__"),

        (operator.add, "__add__"),
        (operator.and_, "__and__"),
        (divmod, "__divmod__"),
        (operator.floordiv, "__floordiv__"),
        (operator.lshift, "__lshift__"),
        (operator.mod, "__mod__"),
        (operator.mul, "__mul__"),
        (operator.or_, "__or__"),
        (operator.pow, "__pow__"),
        (operator.rshift, "__rshift__"),
        (operator.sub, "__sub__"),
        (operator.truediv, "__truediv__"),
        (operator.xor, "__xor__"),
    ])
    def test_special_binops(self, func, op):
        x = stub(**{
            op: lambda y: func(2, y)
        })
        assert func(x, 4) == func(2, 4)
        assert func(x, 2) == func(2, 2)

    @pytest.mark.skipif("PY3K")
    def test_div(self):
        x = stub(
            __div__=lambda y: 4
        )
        assert x / 3 == 4

    def test_missing_op_error(self):
        x = stub()
        with pytest.raises(TypeError):
            x + 2

    def test_subscript(self):
        x = stub(
            __getitem__=lambda idx: idx
        )
        assert x[5] == 5
        assert x[1, 2] == (1, 2)

    def test_setitem(self):
        d = {}
        x = stub(
            __setitem__=d.__setitem__
        )
        x[5] = 'a'
        x['b'] = 6
        assert d == {5: 'a', 'b': 6}

    def test_delitem(self):
        d = {5: 'a', 'b': 6}
        x = stub(
            __delitem__=d.__delitem__
        )
        del x['b']
        assert d == {5: 'a'}

    def test_context_manager(self):
        should_reraise = True
        x = stub(
            __enter__=lambda: 3,
            __exit__=lambda exc_type, exc_value, tb: should_reraise
        )
        with x as value:
            assert value == 3
            raise ValueError
        should_reraise = False
        with pytest.raises(ValueError):
            with x as value:
                assert value == 3
                raise ValueError

    def test_default_repr(self):
        x = stub(a=10)

        assert repr(x) == "<stub(a=10)>"

    def test_custom_repr(self):
        x = stub(id=300, __repr__=lambda: '<Something>')

        assert x.id == 300
        assert repr(x) == '<Something>'


class TestRaiser(object):
    def test_call_raiser(self):
        f = raiser(ValueError)
        with pytest.raises(ValueError):
            f()

    def test_call_raiser_exc_value(self):
        exc = ValueError(14)
        f = raiser(exc)
        with pytest.raises(ValueError) as exc_info:
            f()
        assert exc_info.value is exc

    def test_non_exc_raiser(self):
        with pytest.raises(TypeError):
            raiser("test")


class TestCallRecorder(object):
    def test_call_eq(self):
        assert call(a=2) == call(a=2)
        assert not (call(a=2) != call(a=2))
        assert call(a=2) != call(a=3)
        assert not (call(a=2) == call(a=3))

        assert call() != []

    def test_call_repr(self):
        assert repr(call(1, 2, a=3)) == "<call(1, 2, a=3)>"
        assert repr(call(a=2)) == "<call(a=2)>"

    def test_call_hash(self):
        c1 = call(a=2)
        c2 = call(a=2)
        assert hash(c1) == hash(c2)

    def test_simple(self):
        f = call_recorder(lambda *args, **kwargs: 3)
        assert f() == 3
        assert f.calls == [
            call()
        ]

########NEW FILE########
