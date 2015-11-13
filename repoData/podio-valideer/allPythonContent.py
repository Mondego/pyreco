__FILENAME__ = base
import inspect
from contextlib import contextmanager
from functools import partial
from threading import RLock
from decorator import decorator

__all__ = [
    "ValidationError", "SchemaError", "Validator", "accepts", "adapts",
    "parse", "register", "register_factory",
    "set_name_for_types", "reset_type_names",
]

_NAMED_VALIDATORS = {}
_VALIDATOR_FACTORIES = []
_VALIDATOR_FACTORIES_LOCK = RLock()

class SchemaError(Exception):
    """An object cannot be parsed as a validator."""


class ValidationError(ValueError):
    """A value is invalid for a given validator."""

    _UNDEFINED = object()

    def __init__(self, msg, value=_UNDEFINED):
        self.msg = msg
        self.value = value
        self.context = []
        super(ValidationError, self).__init__(str(self))

    def __str__(self):
        return self.to_string()

    def to_string(self, repr_value=repr):
        msg = self.msg
        if self.value is not self._UNDEFINED:
            msg = "Invalid value %s (%s): %s" % (repr_value(self.value),
                                                 get_type_name(self.value.__class__),
                                                 msg)
        if self.context:
            msg += " (at %s)" % "".join("[%r]" % context if i > 0 else str(context)
                                        for i, context in enumerate(reversed(self.context)))
        return msg

    def add_context(self, context):
        self.context.append(context)
        return self


def parse(obj, required_properties=None, additional_properties=None):
    """Try to parse the given ``obj`` as a validator instance.

    :param obj: If it is a ...
        - ``Validator`` instance, return it.
        - ``Validator`` subclass, instantiate it without arguments and return it.
        - name of a known ``Validator`` subclass, instantiate the subclass
          without arguments and return it.
        - otherwise find the first registered ``Validator`` factory that can
          create it. The search order is the reverse of the factory registration
          order. The caller is responsible for ensuring there are no ambiguous
          values that can be parsed by more than one factory.
    :param required_properties: Specifies for this parse call whether parsed
        ``Object`` properties are required or optional by default. If True, they
        are required; if False, they are optional; if None, it is determined by
        the (global) ``Object.REQUIRED_PROPERTIES`` attribute.
    :param additional_properties: Specifies for this parse call the schema of
        all ``Object`` properties that are not explicitly defined as ``optional``
        or ``required``.  It can also be:
            - ``False`` to disallow any additional properties
            - ``True`` to allow any value for additional properties
            - ``None`` to use the value of the (global)
              ``Object.ADDITIONAL_PROPERTIES`` attribute.
    :raises SchemaError: If no appropriate validator could be found.
    """
    if required_properties is not None and not isinstance(required_properties, bool):
        raise TypeError("required_properties must be bool or None")

    validator = None

    if isinstance(obj, Validator):
        validator = obj
    elif inspect.isclass(obj) and issubclass(obj, Validator):
        validator = obj()
    else:
        try:
            validator = _NAMED_VALIDATORS[obj]
        except (KeyError, TypeError):
            if required_properties is additional_properties is None:
                validator = _parse_from_factories(obj)
            else:
                from .validators import _ObjectFactory
                with _register_temp_factories(partial(_ObjectFactory,
                                      required_properties=required_properties,
                                      additional_properties=additional_properties)):
                    validator = _parse_from_factories(obj)
        else:
            if inspect.isclass(validator) and issubclass(validator, Validator):
                _NAMED_VALIDATORS[obj] = validator = validator()

    if not isinstance(validator, Validator):
        raise SchemaError("%r cannot be parsed as a Validator" % obj)

    return validator


def _parse_from_factories(obj):
    for factory in _VALIDATOR_FACTORIES:
        validator = factory(obj)
        if validator is not None:
            return validator


def register(name, validator):
    """Register a validator instance under the given ``name``."""
    if not isinstance(validator, Validator):
        raise TypeError("Validator instance expected, %s given" % validator.__class__)
    _NAMED_VALIDATORS[name] = validator


def register_factory(func):
    """Decorator for registering a validator factory.

    The decorated factory must be a callable that takes a single parameter
    that can be any arbitrary object and returns a Validator instance if it
    can parse the input object successfully, or None otherwise.
    """
    _VALIDATOR_FACTORIES.insert(0, func)
    return func


@contextmanager
def _register_temp_factories(*funcs):
    with _VALIDATOR_FACTORIES_LOCK:
        for func in funcs:
            _VALIDATOR_FACTORIES.insert(0, func)
        yield
        for func in reversed(funcs):
            _VALIDATOR_FACTORIES.remove(func)


class Validator(object):
    """Abstract base class of all validators.

    Concrete subclasses must implement ``validate()``. A subclass may optionally
    define a ``name`` attribute (typically a string) that can be used to specify
    a validator in ``parse()`` instead of instantiating it explicitly.
    """

    class __metaclass__(type):
        def __new__(mcs, name, bases, attrs): #@NoSelf
            validator_type = type.__new__(mcs, name, bases, attrs)
            validator_name = attrs.get("name")
            if validator_name is not None:
                _NAMED_VALIDATORS[validator_name] = validator_type
            return validator_type

    name = None

    def validate(self, value, adapt=True):
        """Check if ``value`` is valid and if so adapt it.

        :param adapt: If False, it indicates that the caller is interested only
            on whether ``value`` is valid, not on adapting it. This is essentially
            an optimization hint for cases that validation can be done more
            efficiently than adaptation.

        :raises ValidationError: If ``value`` is invalid.
        :returns: The adapted value if ``adapt`` is True, otherwise anything.
        """
        raise NotImplementedError

    def is_valid(self, value):
        """Check if the value is valid.

        :returns: True if the value is valid, False if invalid.
        """
        try:
            self.validate(value, adapt=False)
            return True
        except ValidationError:
            return False

    def error(self, value):
        """Helper method that can be called when ``value`` is deemed invalid.

        Can be overriden to provide customized ``ValidationError``s.
        """
        raise ValidationError("must be %s" % self.humanized_name, value)

    @property
    def humanized_name(self):
        """Return a human-friendly string name for this validator."""
        return self.name or self.__class__.__name__

    # for backwards compatibility

    parse = staticmethod(parse)
    register = staticmethod(register)
    register_factory = staticmethod(register_factory)


def accepts(**schemas):
    """Create a decorator for validating function parameters.

    Example::

        @accepts(a="number", body={"+field_ids": [int], "is_ok": bool})
        def f(a, body):
            print (a, body["field_ids"], body.get("is_ok"))

    :param schemas: The schema for validating a given parameter.
    """
    validate = parse(schemas).validate
    @decorator
    def validating(func, *args, **kwargs):
        validate(inspect.getcallargs(func, *args, **kwargs), adapt=False)
        return func(*args, **kwargs)
    return validating


def adapts(**schemas):
    """Create a decorator for validating and adapting function parameters.

    Example::

        @adapts(a="number", body={"+field_ids": [int], "is_ok": bool})
        def f(a, body):
            print (a, body.field_ids, body.is_ok)

    :param schemas: The schema for adapting a given parameter.
    """
    validate = parse(schemas).validate

    @decorator
    def adapting(func, *args, **kwargs):
        adapted = validate(inspect.getcallargs(func, *args, **kwargs), adapt=True)
        argspec = inspect.getargspec(func)

        if argspec.varargs is argspec.keywords is None:
            # optimization for the common no varargs, no keywords case
            return func(**adapted)

        adapted_varargs = adapted.pop(argspec.varargs, ())
        adapted_keywords = adapted.pop(argspec.keywords, {})
        if not adapted_varargs: # keywords only
            if adapted_keywords:
                adapted.update(adapted_keywords)
            return func(**adapted)

        adapted_posargs = [adapted[arg] for arg in argspec.args]
        adapted_posargs.extend(adapted_varargs)
        return func(*adapted_posargs, **adapted_keywords)

    return adapting


_TYPE_NAMES = {}

def set_name_for_types(name, *types):
    """Associate one or more types with an alternative human-friendly name."""
    for t in types:
        _TYPE_NAMES[t] = name

def reset_type_names():
    _TYPE_NAMES.clear()

def get_type_name(type):
    return _TYPE_NAMES.get(type) or type.__name__

########NEW FILE########
__FILENAME__ = test_validators
from datetime import date, datetime
from decimal import Decimal
from functools import partial
import collections
import json
import re
import unittest
import valideer as V


class Fraction(V.Type):
    name = "fraction"
    accept_types = (float, complex, Decimal)

class Gender(V.Enum):
    name = "gender"
    values = ("male", "female", "it's complicated")


class TestValidator(unittest.TestCase):

    parse = staticmethod(V.parse)

    def setUp(self):
        V.Object.REQUIRED_PROPERTIES = True
        V.base.reset_type_names()
        self.complex_validator = self.parse({
            "n": "number",
            "?i": V.Nullable("integer", 0),
            "?b": bool,
            "?e": V.Enum(["r", "g", "b"]),
            "?d": V.AnyOf("date", "datetime"),
            "?s": V.String(min_length=1, max_length=8),
            "?p": V.Nullable(re.compile(r"\d{1,4}$")),
            "?l": [{"+s2": "string"}],
            "?t": (unicode, "number"),
            "?h": V.Mapping(int, ["string"]),
            "?o": V.NonNullable({"+i2": "integer"}),
        })

    def test_none(self):
        for obj in ["boolean", "integer", "number", "string",
                    V.HomogeneousSequence, V.HeterogeneousSequence,
                    V.Mapping, V.Object, int, float, str, unicode,
                    Fraction, Fraction(), Gender, Gender()]:
            self.assertFalse(self.parse(obj).is_valid(None))

    def test_boolean(self):
        for obj in "boolean", V.Boolean, V.Boolean():
            self._testValidation(obj,
                                 valid=[True, False],
                                 invalid=[1, 1.1, "foo", u"bar", {}, []])

    def test_integer(self):
        for obj in "integer", V.Integer, V.Integer():
            self._testValidation(obj,
                                 valid=[1],
                                 invalid=[1.1, "foo", u"bar", {}, [], False, True])

    def test_int(self):
        # bools are ints
        self._testValidation(int,
                             valid=[1, True, False],
                             invalid=[1.1, "foo", u"bar", {}, []])

    def test_number(self):
        for obj in "number", V.Number, V.Number():
            self._testValidation(obj,
                                 valid=[1, 1.1],
                                 invalid=["foo", u"bar", {}, [], False, True])

    def test_float(self):
        self._testValidation(float,
                             valid=[1.1],
                             invalid=[1, "foo", u"bar", {}, [], False, True])

    def test_string(self):
        for obj in "string", V.String, V.String():
            self._testValidation(obj,
                                 valid=["foo", u"bar"],
                                 invalid=[1, 1.1, {}, [], False, True])

    def test_string_min_length(self):
        self._testValidation(V.String(min_length=2),
                             valid=["foo", u"fo"],
                             invalid=[u"f", "", False])

    def test_string_max_length(self):
        self._testValidation(V.String(max_length=2),
                             valid=["", "f", u"fo"],
                             invalid=[u"foo", [1, 2, 3]])

    def test_pattern(self):
        self._testValidation(re.compile(r"a*$"),
                             valid=["aaa"],
                             invalid=[u"aba", "baa"])

    def test_range(self):
        self._testValidation(V.Range("integer", 1),
                             valid=[1, 2, 3],
                             invalid=[0, -1])
        self._testValidation(V.Range("integer", max_value=2),
                             valid=[-1, 0, 1, 2],
                             invalid=[3])
        self._testValidation(V.Range("integer", 1, 2),
                             valid=[1, 2],
                             invalid=[-1, 0, 3])

    def test_homogeneous_sequence(self):
        for obj in V.HomogeneousSequence, V.HomogeneousSequence():
            self._testValidation(obj,
                                 valid=[[], [1], (1, 2), [1, (2, 3), 4]],
                                 invalid=[1, 1.1, "foo", u"bar", {}, False, True])
        self._testValidation(["number"],
                             valid=[[], [1, 2.1, 3L], (1, 4L, 6)],
                             invalid=[[1, 2.1, 3L, u"x"]])

    def test_heterogeneous_sequence(self):
        for obj in V.HeterogeneousSequence, V.HeterogeneousSequence():
            self._testValidation(obj,
                                 valid=[(), []],
                                 invalid=[1, 1.1, "foo", u"bar", {}, False, True])
        self._testValidation(("string", "number"),
                             valid=[("a", 2), [u"b", 4.1]],
                             invalid=[[], (), (2, "a"), ("a", "b"), (1, 2)])

    def test_sequence_min_length(self):
        self._testValidation(V.HomogeneousSequence(int, min_length=2),
                             valid=[[1, 2, 4], (1, 2)],
                             invalid=[[1], [], (), "123", "", False])

    def test_sequence_max_length(self):
        self._testValidation(V.HomogeneousSequence(int, max_length=2),
                             valid=[[], (), (1,), (1, 2), [1, 2]],
                             invalid=[[1, 2, 3], "123", "f"])

    def test_mapping(self):
        for obj in V.Mapping, V.Mapping():
            self._testValidation(obj,
                                 valid=[{}, {"foo": 3}],
                                 invalid=[1, 1.1, "foo", u"bar", [], False, True])
        self._testValidation(V.Mapping("string", "number"),
                             valid=[{"foo": 3},
                                    {"foo": 3, u"bar":-2.1, "baz":Decimal("12.3")}],
                             invalid=[{"foo": 3, ("bar",):-2.1},
                                      {"foo": 3, "bar":"2.1"}])

    def test_object(self):
        for obj in V.Object, V.Object():
            self._testValidation(obj,
                                 valid=[{}, {"foo": 3}],
                                 invalid=[1, 1.1, "foo", u"bar", [], False, True])
        self._testValidation({"foo": "number", "bar": "string"},
                             valid=[{"foo": 1, "bar": "baz"},
                                    {"foo": 1, "bar": "baz", "quux": 42}],
                             invalid=[{"foo": 1, "bar": []},
                                      {"foo": "baz", "bar": 2.3}])

    def test_required_properties_global(self):
        self._testValidation({"foo": "number", "?bar": "boolean", "baz":"string"},
                             valid=[{"foo":-23., "baz":"yo"}],
                             invalid=[{},
                                      {"bar":True},
                                      {"baz":"yo"},
                                      {"foo":3},
                                      {"bar":False, "baz":"yo"},
                                      {"bar":True, "foo":3.1}])

    def test_required_properties_parse_parameter(self):
        schema = {
            "foo": "number",
            "?bar": "boolean",
            "?nested": [{
                "baz": "string"
            }]
        }
        values = [{}, {"bar":True}, {"foo":3, "nested":[{}]}]
        for _ in xrange(3):
            self._testValidation(V.parse(schema, required_properties=True),
                                 invalid=values)
            self._testValidation(V.parse(schema, required_properties=False),
                                 valid=values)
            self.assertRaises(TypeError, V.parse, schema, required_properties=1)

    def test_adapt_missing_property(self):
        self._testValidation({"foo": "number", "?bar": V.Nullable("boolean", False)},
                             adapted=[({"foo":-12}, {"foo":-12, "bar":False})])

    def test_no_additional_properties(self):
        self._testValidation(V.Object(required={"foo": "number"},
                                      optional={"bar": "string"},
                                      additional=False),
                             valid=[{"foo":23},
                                    {"foo":-23., "bar":"yo"}],
                             invalid=[{"foo":23, "xyz":1},
                                      {"foo":-23., "bar":"yo", "xyz":1}]
                             )

    def test_additional_properties_schema(self):
        self._testValidation(V.Object(required={"foo": "number"},
                                      optional={"bar": "string"},
                                      additional="boolean"),
                             valid=[{"foo":23, "bar":"yo", "x1":True, "x2":False}],
                             invalid=[{"foo":23, "x1":1},
                                      {"foo":-23., "bar":"yo", "x1":True, "x2":0}]
                             )

    def test_additional_properties_parse_parameter(self):
        schema = {
            "?bar": "boolean",
            "?nested": [{
                "?baz": "integer"
            }]
        }
        values = [{"x1": "yes"},
                  {"bar":True, "nested": [{"x1": "yes"}]}]
        for _ in xrange(3):
            self._testValidation(V.parse(schema, additional_properties=True),
                                 valid=values)
            self._testValidation(V.parse(schema, additional_properties=False),
                                 invalid=values)
            self._testValidation(V.parse(schema, additional_properties="string"),
                                 valid=values,
                                 invalid=[{"x1": 42},
                                          {"bar":True, "nested": [{"x1": 42}]}])

    def test_enum(self):
        self._testValidation(V.Enum([1, 2, 3]),
                             valid=[1, 2, 3], invalid=[0, 4, "1", [1]])
        self._testValidation(V.Enum([u"foo", u"bar"]),
                             valid=["foo", "bar"], invalid=["", "fooabar", ["foo"]])
        self._testValidation(V.Enum([True]),
                             valid=[True], invalid=[False, [True]])
        self._testValidation(V.Enum([{"foo" : u"bar"}]),
                             valid=[{u"foo" : "bar"}])
        self._testValidation(V.Enum([{"foo" : u"quux"}]),
                             invalid=[{u"foo" : u"bar"}])

    def test_enum_class(self):
        for obj in "gender", Gender, Gender():
            self._testValidation(obj,
                                 valid=["male", "female", "it's complicated"],
                                 invalid=["other", ""])

    def test_nullable(self):
        for obj in "?integer", V.Nullable(V.Integer()), V.Nullable("+integer"):
            self._testValidation(obj,
                                 valid=[None, 0],
                                 invalid=[1.1, True, False])
        self._testValidation(V.Nullable(["?string"]),
                             valid=[None, [], ["foo"], [None], ["foo", None]],
                             invalid=["", [None, "foo", 1]])

    def test_nullable_with_default(self):
        self._testValidation(V.Nullable("integer", -1),
                             adapted=[(None, -1), (0, 0)],
                             invalid=[1.1, True, False])
        self._testValidation(V.Nullable("integer", lambda:-1),
                             adapted=[(None, -1), (0, 0)],
                             invalid=[1.1, True, False])

    def test_nonnullable(self):
        for obj in V.NonNullable, V.NonNullable():
            self._testValidation(obj,
                                 invalid=[None],
                                 valid=[0, False, "", (), []])
        for obj in "+integer", V.NonNullable(V.Integer()), V.NonNullable("?integer"):
            self._testValidation(obj,
                                 invalid=[None, False],
                                 valid=[0, 2L])

    def test_anyof(self):
        self._testValidation(V.AnyOf("integer", {"foo" : "integer"}),
                             valid=[1, {"foo" : 1}],
                             invalid=[{"foo" : 1.1}])

    def test_allof(self):
        self._testValidation(V.AllOf({"id": "integer"}, V.Mapping("string", "number")),
                             valid=[{"id": 3}, {"id": 3, "bar": 4.5}],
                             invalid=[{"id" : 1.1, "bar":4.5},
                                      {"id" : 3, "bar": True},
                                      {"id" : 3, 12: 4.5}])

        self._testValidation(V.AllOf("number",
                                     lambda x: x > 0,
                                     V.AdaptBy(datetime.fromtimestamp)),
                            adapted=[(1373475820, datetime(2013, 7, 10, 20, 3, 40))],
                            invalid=["1373475820", -1373475820])

    def test_chainof(self):
        self._testValidation(V.ChainOf(V.AdaptTo(int),
                                       V.Condition(lambda x: x > 0),
                                       V.AdaptBy(datetime.fromtimestamp)),
                            adapted=[(1373475820, datetime(2013, 7, 10, 20, 3, 40)),
                                     ("1373475820", datetime(2013, 7, 10, 20, 3, 40))],
                            invalid=["nan", -1373475820])

    def test_condition(self):
        def is_odd(n): return n % 2 == 1
        is_even = lambda n: n % 2 == 0

        class C(object):
            def is_odd_method(self, n): return is_odd(n)
            def is_even_method(self, n): return is_even(n)
            is_odd_static = staticmethod(is_odd)
            is_even_static = staticmethod(is_even)

        for obj in is_odd, C().is_odd_method, C.is_odd_static:
            self._testValidation(obj,
                                 valid=[1, 3L, -11, 9.0, True],
                                 invalid=[6, 2.1, False, "1", []])

        for obj in is_even, C().is_even_method, C.is_even_static:
            self._testValidation(obj,
                                 valid=[6, 2L, -42, 4.0, 0, 0.0, False],
                                 invalid=[1, 2.1, True, "2", []])

        self._testValidation(str.isalnum,
                             valid=["abc", "123", "ab32c"],
                             invalid=["a+b", "a 1", "", True, 2])

        self.assertRaises(TypeError, V.Condition, C)
        self.assertRaises(TypeError, V.Condition(is_even, traps=()).validate, [2, 4])


    def test_adapt_by(self):
        self._testValidation(V.AdaptBy(hex, traps=TypeError),
                             invalid=[1.2, "1"],
                             adapted=[(255, "0xff"), (0, "0x0")])
        self._testValidation(V.AdaptBy(int, traps=(ValueError, TypeError)),
                             invalid=["12b", "1.2", {}, (), []],
                             adapted=[(12, 12), ("12", 12), (1.2, 1)])
        self.assertRaises(TypeError, V.AdaptBy(hex, traps=()).validate, 1.2)

    def test_adapt_to(self):
        self.assertRaises(TypeError, V.AdaptTo, hex)
        for exact in False, True:
            self._testValidation(V.AdaptTo(int, traps=(ValueError, TypeError), exact=exact),
                                 invalid=["12b", "1.2", {}, (), []],
                                 adapted=[(12, 12), ("12", 12), (1.2, 1)])

        class smallint(int):
            pass
        i = smallint(2)
        self.assertIs(V.AdaptTo(int).validate(i), i)
        self.assertIsNot(V.AdaptTo(int, exact=True).validate(i), i)

    def test_fraction(self):
        for obj in "fraction", Fraction, Fraction():
            self._testValidation(obj,
                                 valid=[1.1, 0j, 5 + 3j, Decimal(1) / Decimal(8)],
                                 invalid=[1, "foo", u"bar", {}, [], False, True])

    def test_reject_types(self):
        ExceptionValidator = V.Type(accept_types=Exception, reject_types=Warning)
        ExceptionValidator.validate(KeyError())
        self.assertRaises(V.ValidationError, ExceptionValidator.validate, UserWarning())

    def test_accepts(self):
        @V.accepts(a="fraction", b=int, body={"+field_ids": ["integer"],
                                               "?is_ok": bool,
                                               "?sex": "gender"})
        def f(a, b=1, **body):
            pass

        valid = [
            partial(f, 2.0, field_ids=[]),
            partial(f, Decimal(1), b=5, field_ids=[1], is_ok=True),
            partial(f, a=3j, b= -1, field_ids=[1L, 2, 5L], sex="male"),
            partial(f, 5 + 3j, 0, field_ids=[-12L, 0, 0L], is_ok=False, sex="female"),
            partial(f, 2.0, field_ids=[], additional="extra param allowed"),
        ]

        invalid = [
            partial(f, 1), # 'a' is not a fraction
            partial(f, 1.0), # missing 'field_ids' from body
            partial(f, 1.0, b=4.1, field_ids=[]), # 'b' is not int
            partial(f, 1.0, b=2, field_ids=3), # 'field_ids' is not a list
            partial(f, 1.0, b=1, field_ids=[3.0]), # 'field_ids[0]' is not a integer
            partial(f, 1.0, b=1, field_ids=[], is_ok=1), # 'is_ok' is not bool
            partial(f, 1.0, b=1, field_ids=[], sex="m"), # 'sex' is not a gender
        ]

        for fcall in valid:
            fcall()
        for fcall in invalid:
            self.assertRaises(V.ValidationError, fcall)

    def test_adapts(self):
        @V.adapts(body={"+field_ids": ["integer"],
                         "?scores": V.Mapping("string", float),
                         "?users": [{
                            "+name": ("+string", "+string"),
                            "?sex": "gender",
                            "?active": V.Nullable("boolean", True),
                         }]})
        def f(body):
            return body

        adapted = f({
                    "field_ids": [1, 5],
                    "scores": {"foo": 23.1, "bar": 2.0},
                    "users": [
                        {"name": ("Nick", "C"), "sex": "male"},
                        {"name": ("Kim", "B"), "active": False},
                        {"name": ("Joe", "M"), "active": None},
                    ]})

        self.assertEqual(adapted["field_ids"], [1, 5])
        self.assertEqual(adapted["scores"]["foo"], 23.1)
        self.assertEqual(adapted["scores"]["bar"], 2.0)

        self.assertEqual(adapted["users"][0]["name"], ("Nick", "C"))
        self.assertEqual(adapted["users"][0]["sex"], "male")
        self.assertEqual(adapted["users"][0]["active"], True)

        self.assertEqual(adapted["users"][1]["name"], ("Kim", "B"))
        self.assertEqual(adapted["users"][1].get("sex"), None)
        self.assertEqual(adapted["users"][1]["active"], False)

        self.assertEqual(adapted["users"][2]["name"], ("Joe", "M"))
        self.assertEqual(adapted["users"][2].get("sex"), None)
        self.assertEqual(adapted["users"][2].get("active"), True)

        invalid = [
            # missing 'field_ids' from body
            partial(f, {}),
            # score value is not float
            partial(f, {"field_ids": [], "scores":{"a": "2.3"}}),
            # 'name' is not a length-2 tuple
            partial(f, {"field_ids": [], "users":[{"name": ("Bob", "R", "Junior")}]}),
            # name[1] is not a string
            partial(f, {"field_ids": [], "users":[{"name": ("Bob", 12)}]}),
            # name[1] is required
            partial(f, {"field_ids": [], "users":[{"name": ("Bob", None)}]}),
        ]
        for fcall in invalid:
            self.assertRaises(V.ValidationError, fcall)

    def test_adapts_varargs(self):
        @V.adapts(a="integer",
                   b="number",
                   nums=["number"])
        def f(a, b=1, *nums, **params):
            return a * b + sum(nums)

        self.assertEqual(f(2), 2)
        self.assertEqual(f(2, b=2), 4)
        self.assertEqual(f(2, 2.5, 3), 8)
        self.assertEqual(f(2, 2.5, 3, -2.5), 5.5)

    def test_adapts_kwargs(self):
        @V.adapts(a="integer",
                   b="number",
                   params={"?foo": int, "?bar": float})
        def f(a, b=1, **params):
            return a * b + params.get("foo", 1) * params.get("bar", 0.0)

        self.assertEqual(f(1), 1)
        self.assertEqual(f(1, 2), 2)
        self.assertEqual(f(1, b=2.5, foo=3), 2.5)
        self.assertEqual(f(1, b=2.5, bar=3.5), 6.0)
        self.assertEqual(f(1, foo=2, bar=3.5), 8.0)
        self.assertEqual(f(1, b=2.5, foo=2, bar=3.5), 9.5)

    def test_adapts_varargs_kwargs(self):
        @V.adapts(a="integer",
                   b="number",
                   nums=["number"],
                   params={"?foo": int, "?bar": float})
        def f(a, b=1, *nums, **params):
            return a * b + sum(nums) + params.get("foo", 1) * params.get("bar", 0.0)

        self.assertEqual(f(2), 2)
        self.assertEqual(f(2, b=2), 4)
        self.assertEqual(f(2, 2.5, 3), 8)
        self.assertEqual(f(2, 2.5, 3, -2.5), 5.5)
        self.assertEqual(f(1, b=2.5, foo=3), 2.5)
        self.assertEqual(f(1, b=2.5, bar=3.5), 6.0)
        self.assertEqual(f(1, foo=2, bar=3.5), 8.0)
        self.assertEqual(f(1, b=2.5, foo=2, bar=3.5), 9.5)
        self.assertEqual(f(2, 2.5, 3, foo=2), 8.0)
        self.assertEqual(f(2, 2.5, 3, bar=3.5), 11.5)
        self.assertEqual(f(2, 2.5, 3, foo=2, bar=3.5), 15.0)

    def test_schema_errors(self):
        for obj in [
            True,
            1,
            3.2,
            "foo",
            object(),
            ["foo"],
            {"field": "foo"},
        ]:
            self.assertRaises(V.SchemaError, self.parse, obj)

    def test_not_implemented_validation(self):
        class MyValidator(V.Validator):
            pass

        validator = MyValidator()
        self.assertRaises(NotImplementedError, validator.validate, 1)

    def test_register(self):
        for register in V.register, V.Validator.register:
            register("to_int", V.AdaptTo(int, traps=(ValueError, TypeError)))
            self._testValidation("to_int",
                                 invalid=["12b", "1.2"],
                                 adapted=[(12, 12), ("12", 12), (1.2, 1)])

            self.assertRaises(TypeError, register, "to_int", int)

    def test_complex_validation(self):

        for valid in [
            {'n': 2},
            {'n': 2.1, 'i':3},
            {'n':-1, 'b':False},
            {'n': Decimal(3), 'e': "r"},
            {'n': 2L, 'd': datetime.now()},
            {'n': 0, 'd': date.today()},
            {'n': 0, 's': "abc"},
            {'n': 0, 'p': None},
            {'n': 0, 'p': "123"},
            {'n': 0, 'l': []},
            {'n': 0, 'l': [{"s2": "foo"}, {"s2": ""}]},
            {'n': 0, 't': (u"joe", 3.1)},
            {'n': 0, 'h': {5: ["foo", u"bar"], 0: []}},
            {'n': 0, 'o': {"i2": 3}},
        ]:
            self.complex_validator.validate(valid, adapt=False)

        for invalid in [
            None,
            {},
            {'n': None},
            {'n': True},
            {'n': 1, 'e': None},
            {'n': 1, 'e': "a"},
            {'n': 1, 'd': None},
            {'n': 1, 's': None},
            {'n': 1, 's': ''},
            {'n': 1, 's': '123456789'},
            {'n': 1, 'p': '123a'},
            {'n': 1, 'l': None},
            {'n': 1, 'l': [None]},
            {'n': 1, 'l': [{}]},
            {'n': 1, 'l': [{'s2': None}]},
            {'n': 1, 'l': [{'s2': 1}]},
            {'n': 1, 't': ()},
            {'n': 0, 't': (3.1, u"joe")},
            {'n': 0, 't': (u"joe", None)},
            {'n': 1, 'h': {5: ["foo", u"bar"], "0": []}},
            {'n': 1, 'h': {5: ["foo", 2.1], 0: []}},
            {'n': 1, 'o': {}},
            {'n': 1, 'o': {"i2": "2"}},
        ]:
            self.assertRaises(V.ValidationError,
                              self.complex_validator.validate, invalid, adapt=False)

    def test_complex_adaptation(self):
        for value in [
            {'n': 2},
            {'n': 2.1, 'i':3},
            {'n':-1, 'b':False},
            {'n': Decimal(3), 'e': "r"},
            {'n': 2L, 'd': datetime.now()},
            {'n': 0, 'd': date.today()},
            {'n': 0, 's': "abc"},
            {'n': 0, 'p': None},
            {'n': 0, 'p': "123"},
            {'n': 0, 'l': []},
            {'n': 0, 'l': [{"s2": "foo"}, {"s2": ""}]},
            {'n': 0, 't': (u"joe", 3.1)},
            {'n': 0, 'h': {5: ["foo", u"bar"], 0: []}},
            {'n': 0, 'o': {"i2": 3}},
        ]:
            adapted = self.complex_validator.validate(value)
            self.assertTrue(isinstance(adapted["n"], (int, long, float, Decimal)))
            self.assertTrue(isinstance(adapted["i"], (int, long)))
            self.assertTrue(adapted.get("b") is None or isinstance(adapted["b"], bool))
            self.assertTrue(adapted.get("d") is None or isinstance(adapted["d"], (date, datetime)))
            self.assertTrue(adapted.get("e") is None or adapted["e"] in "rgb")
            self.assertTrue(adapted.get("s") is None or isinstance(adapted["s"], basestring))
            self.assertTrue(adapted.get("l") is None or isinstance(adapted["l"], list))
            self.assertTrue(adapted.get("t") is None or isinstance(adapted["t"], tuple))
            self.assertTrue(adapted.get("h") is None or isinstance(adapted["h"], dict))
            if adapted.get("l") is not None:
                self.assertTrue(all(isinstance(item["s2"], basestring)
                                    for item in adapted["l"]))
            if adapted.get("t") is not None:
                self.assertEqual(len(adapted["t"]), 2)
                self.assertTrue(isinstance(adapted["t"][0], unicode))
                self.assertTrue(isinstance(adapted["t"][1], float))
            if adapted.get("h") is not None:
                self.assertTrue(all(isinstance(key, int)
                                    for key in adapted["h"].keys()))
                self.assertTrue(all(isinstance(value_item, basestring)
                                    for value in adapted["h"].values()
                                    for value_item in value))
            if adapted.get("o") is not None:
                self.assertTrue(isinstance(adapted["o"]["i2"], (int, long)))

    def test_humanized_names(self):
        class DummyValidator(V.Validator):
            name = "dummy"
            def validate(self, value, adapt=True):
                return value

        self.assertEqual(DummyValidator().humanized_name, "dummy")
        self.assertEqual(V.Nullable(DummyValidator()).humanized_name, "dummy or null")
        self.assertEqual(V.AnyOf("boolean", DummyValidator()).humanized_name,
                         "boolean or dummy")

    def test_error_message(self):
        self._testValidation({"+foo": "number", "?bar":["integer"]}, errors=[
            (42,
             "Invalid value 42 (int): must be Mapping"),
            ({},
             "Invalid value {} (dict): missing required properties: ['foo']"),
            ({"foo": "3"},
             "Invalid value '3' (str): must be number (at foo)"),
            ({"foo": 3, "bar":None},
             "Invalid value None (NoneType): must be Sequence (at bar)"),
            ({"foo": 3, "bar":[1, "2", 3]},
             "Invalid value '2' (str): must be integer (at bar[1])"),
        ])

    def test_error_message_custom_repr_value(self):
        self._testValidation({"+foo": "number", "?bar":["integer"]},
                             error_value_repr=json.dumps,
                             errors=[
            (42,
             "Invalid value 42 (int): must be Mapping"),
            ({},
             "Invalid value {} (dict): missing required properties: ['foo']"),
            ({"foo": "3"},
             'Invalid value "3" (str): must be number (at foo)'),
            ({"foo": [3]},
             'Invalid value [3] (list): must be number (at foo)'),
            ({"foo": 3, "bar":None},
             "Invalid value null (NoneType): must be Sequence (at bar)"),
            ({"foo": 3, "bar": False},
             "Invalid value false (bool): must be Sequence (at bar)"),
            ({"foo": 3, "bar":[1, {u'a': 3}, 3]},
             'Invalid value {"a": 3} (dict): must be integer (at bar[1])'),
        ])

    def test_error_message_json_type_names(self):
        V.set_name_for_types("null", type(None))
        V.set_name_for_types("integer", int, long)
        V.set_name_for_types("number", float)
        V.set_name_for_types("string", str, unicode)
        V.set_name_for_types("array", list, collections.Sequence)
        V.set_name_for_types("object", dict, collections.Mapping)

        self._testValidation({"+foo": "number",
                              "?bar":["integer"],
                              "?baz": V.AnyOf("number", ["number"]),
                              "?opt": "?string",
                              }, errors=[
            (42,
             "Invalid value 42 (integer): must be object"),
            ({},
             "Invalid value {} (object): missing required properties: ['foo']"),
            ({"foo": "3"},
             "Invalid value '3' (string): must be number (at foo)"),
            ({"foo": None},
             "Invalid value None (null): must be number (at foo)"),
            ({"foo": 3, "bar":None},
             "Invalid value None (null): must be array (at bar)"),
            ({"foo": 3, "bar":[1, "2", 3]},
             "Invalid value '2' (string): must be integer (at bar[1])"),
            ({"foo": 3, "baz":"23"},
             "Invalid value '23' (string): must be number or must be array (at baz)"),
            ({"foo": 3, "opt":12},
             "Invalid value 12 (integer): must be string (at opt)"),
            ])

    def _testValidation(self, obj, invalid=(), valid=(), adapted=(), errors=(),
                        error_value_repr=repr):
        validator = self.parse(obj)
        for value in invalid:
            self.assertFalse(validator.is_valid(value))
            self.assertRaises(V.ValidationError, validator.validate, value, adapt=False)
        for value in valid:
            validator.validate(value)
            self.assertTrue(validator.is_valid(value))
            self.assertEqual(validator.validate(value), value)
        for from_value, to_value in adapted:
            validator.validate(from_value, adapt=False)
            self.assertTrue(validator.is_valid(from_value))
            self.assertEqual(validator.validate(from_value), to_value)
        for value, error in errors:
            try:
                validator.validate(value)
            except V.ValidationError as ex:
                error_repr = ex.to_string(error_value_repr)
                self.assertEqual(error_repr, error, "Actual error: %r" % error_repr)


class TestValidatorModuleParse(TestValidator):

    parse = staticmethod(V.Validator.parse)


class OptionalPropertiesTestValidator(TestValidator):

    def setUp(self):
        super(OptionalPropertiesTestValidator, self).setUp()
        V.Object.REQUIRED_PROPERTIES = False
        self.complex_validator = self.parse({
            "+n": "+number",
            "i": V.Nullable("integer", 0),
            "b": bool,
            "e": V.Enum(["r", "g", "b"]),
            "d": V.AnyOf("date", "datetime"),
            "s": V.String(min_length=1, max_length=8),
            "p": V.Nullable(re.compile(r"\d{1,4}$")),
            "l": [{"+s2": "string"}],
            "t": (unicode, "number"),
            "h": V.Mapping(int, ["string"]),
            "o": V.NonNullable({"+i2": "integer"}),
        })

    def test_required_properties_global(self):
        self._testValidation({"+foo": "number", "bar": "boolean", "+baz":"string"},
                             valid=[{"foo":-23., "baz":"yo"}],
                             invalid=[{},
                                      {"bar":True},
                                      {"baz":"yo"},
                                      {"foo":3},
                                      {"bar":False, "baz":"yo"},
                                      {"bar":True, "foo":3.1}])

########NEW FILE########
__FILENAME__ = validators
from .base import Validator, ValidationError, parse, get_type_name
from itertools import izip
import collections
import datetime
import inspect
import numbers
import re

__all__ = [
    "AnyOf", "AllOf", "ChainOf", "Nullable", "NonNullable",
    "Enum", "Condition", "AdaptBy", "AdaptTo",
    "Type", "Boolean", "Integer", "Number", "Range",
    "String", "Pattern", "Date", "Datetime", "Time",
    "HomogeneousSequence", "HeterogeneousSequence", "Mapping", "Object",
]


class AnyOf(Validator):
    """A composite validator that accepts values accepted by any of its component
    validators.

    In case of adaptation, the first validator to successfully adapt the value
    is used.
    """

    def __init__(self, *schemas):
        self._validators = map(parse, schemas)

    def validate(self, value, adapt=True):
        msgs = []
        for validator in self._validators:
            try:
                return validator.validate(value, adapt)
            except ValidationError as ex:
                msgs.append(ex.msg)
        raise ValidationError(" or ".join(msgs), value)

    @property
    def humanized_name(self):
        return " or ".join(v.humanized_name for v in self._validators)


class AllOf(Validator):
    """A composite validator that accepts values accepted by all of its component
    validators.

    In case of adaptation, the adapted value from the last validator is returned.
    """

    def __init__(self, *schemas):
        self._validators = map(parse, schemas)

    def validate(self, value, adapt=True):
        result = value
        for validator in self._validators:
            result = validator.validate(value, adapt)
        return result

    @property
    def humanized_name(self):
        return " and ".join(v.humanized_name for v in self._validators)


class ChainOf(Validator):
    """A composite validator that passes a value through a sequence of validators.

    value -> validator1 -> value2 -> validator2 -> ... -> validatorN -> final_value
    """

    def __init__(self, *schemas):
        self._validators = map(parse, schemas)

    def validate(self, value, adapt=True):
        for validator in self._validators:
            value = validator.validate(value, adapt)
        return value

    @property
    def humanized_name(self):
        return " chained to ".join(v.humanized_name for v in self._validators)


class Nullable(Validator):
    """A validator that also accepts None.

    None is adapted to ``default``. ``default`` can also be a zero-argument
    callable, in which None is adapted to ``default()``.
    """

    def __init__(self, schema, default=None):
        if isinstance(schema, Validator):
            self._validator = schema
        else:
            validator = parse(schema)
            if isinstance(validator, (Nullable, NonNullable)):
                validator = validator._validator
            self._validator = validator
        self._default = default

    def validate(self, value, adapt=True):
        if value is None:
            return self.default
        return self._validator.validate(value, adapt)

    @property
    def default(self):
        if callable(self._default):
            return self._default()
        else:
            return self._default

    @property
    def humanized_name(self):
        return "%s or null" % self._validator.humanized_name


@Nullable.register_factory
def _NullableFactory(obj):
    """Parse a string starting with "?" as a Nullable validator."""
    if isinstance(obj, basestring) and obj.startswith("?"):
        return Nullable(obj[1:])


class NonNullable(Validator):
    """A validator that does not accept None."""

    def __init__(self, schema=None):
        if schema is not None and not isinstance(schema, Validator):
            validator = parse(schema)
            if isinstance(validator, (Nullable, NonNullable)):
                validator = validator._validator
            self._validator = validator
        else:
            self._validator = schema

    def validate(self, value, adapt=True):
        if value is None:
            self.error(value)
        if self._validator is not None:
            return self._validator.validate(value, adapt)
        return value

    @property
    def humanized_name(self):
        return self._validator.humanized_name if self._validator else "non null"


@NonNullable.register_factory
def _NonNullableFactory(obj):
    """Parse a string starting with "+" as an NonNullable validator."""
    if isinstance(obj, basestring) and obj.startswith("+"):
        return NonNullable(obj[1:])


class Enum(Validator):
    """A validator that accepts only a finite set of values.

    Attributes:
        - values: The collection of valid values.
    """

    values = ()

    def __init__(self, values=None):
        super(Enum, self).__init__()
        if values is None:
            values = self.values
        try:
            self.values = set(values)
        except TypeError: # unhashable
            self.values = list(values)

    def validate(self, value, adapt=True):
        try:
            if value in self.values:
                return value
        except TypeError: # unhashable
            pass
        self.error(value)

    @property
    def humanized_name(self):
        return "one of {%s}" % ", ".join(map(repr, self.values))


class Condition(Validator):
    """A validator that accepts a value using a callable ``predicate``.

    A value is accepted if ``predicate(value)`` is true.
    """

    def __init__(self, predicate, traps=Exception):
        if not inspect.isroutine(predicate):
            raise TypeError("Routine expected, %s given" % predicate.__class__)
        self._predicate = predicate
        self._traps = traps

    def validate(self, value, adapt=True):
        if self._traps:
            try:
                is_valid = self._predicate(value)
            except self._traps:
                is_valid = False
        else:
            is_valid = self._predicate(value)

        if not is_valid:
            self.error(value)

        return value

    def error(self, value):
        raise ValidationError("must satisfy predicate %s" % self.humanized_name, value)

    @property
    def humanized_name(self):
        return str(getattr(self._predicate, "__name__", self._predicate))


@Condition.register_factory
def _ConditionFactory(obj):
    """Parse a function or method as a Condition validator."""
    if inspect.isroutine(obj):
        return Condition(obj)


class AdaptBy(Validator):
    """A validator that adapts a value using an ``adaptor`` callable."""

    def __init__(self, adaptor, traps=Exception):
        """Instantiate this validator.

        :param adaptor: The callable ``f(value)`` to adapt values.
        :param traps: An exception or a tuple of exceptions to catch and wrap
            into a ``ValidationError``. Any other raised exception is left to
            propagate.
        """
        self._adaptor = adaptor
        self._traps = traps

    def validate(self, value, adapt=True):
        if not self._traps:
            return self._adaptor(value)
        try:
            return self._adaptor(value)
        except self._traps, ex:
            raise ValidationError(str(ex), value)


class AdaptTo(AdaptBy):
    """A validator that adapts a value to a target class."""

    def __init__(self, target_cls, traps=Exception, exact=False):
        """Instantiate this validator.

        :param target_cls: The target class.
        :param traps: An exception or a tuple of exceptions to catch and wrap
            into a ``ValidationError``. Any other raised exception is left to
            propagate.
        :param exact: If False, instances of ``target_cls`` or a subclass are
            returned as is. If True, only instances of ``target_cls`` are
            returned as is.
        """
        if not inspect.isclass(target_cls):
            raise TypeError("Type expected, %s given" % target_cls.__class__)
        self._exact = exact
        super(AdaptTo, self).__init__(target_cls, traps)

    def validate(self, value, adapt=True):
        if isinstance(value, self._adaptor) and (not self._exact or
                                                 value.__class__ == self._adaptor):
            return value
        return super(AdaptTo, self).validate(value, adapt)


class Type(Validator):
    """A validator accepting values that are instances of one or more given types.

    Attributes:
        - accept_types: A type or tuple of types that are valid.
        - reject_types: A type or tuple of types that are invalid.
    """

    accept_types = ()
    reject_types = ()

    def __init__(self, accept_types=None, reject_types=None):
        if accept_types is not None:
            self.accept_types = accept_types
        if reject_types is not None:
            self.reject_types = reject_types

    def validate(self, value, adapt=True):
        if not isinstance(value, self.accept_types) or isinstance(value, self.reject_types):
            self.error(value)
        return value

    @property
    def humanized_name(self):
        return self.name or _format_types(self.accept_types)


@Type.register_factory
def _TypeFactory(obj):
    """Parse a python type (or "old-style" class) as a ``Type`` instance."""
    if inspect.isclass(obj):
        return Type(obj)


class Boolean(Type):
    """A validator that accepts bool values."""

    name = "boolean"
    accept_types = bool


class Integer(Type):
    """A validator that accepts integers (numbers.Integral instances) but not bool."""

    name = "integer"
    accept_types = numbers.Integral
    reject_types = bool


class Range(Validator):
    """A validator that accepts only numbers in a certain range"""

    def __init__(self, schema, min_value=None, max_value=None):
        """Instantiate an Integer validator.

        :param min_value: If not None, values less than ``min_value`` are
            invalid.
        :param max_value: If not None, values larger than ``max_value`` are
            invalid.
        """
        super(Range, self).__init__()
        self._validator = parse(schema)
        self._min_value = min_value
        self._max_value = max_value

    def validate(self, value, adapt=True):
        value = self._validator.validate(value, adapt=adapt)

        if self._min_value is not None and value < self._min_value:
            raise ValidationError("must not be less than %d" %
                                  self._min_value, value)
        if self._max_value is not None and value > self._max_value:
            raise ValidationError("must not be larger than %d" %
                                  self._max_value, value)

        return value


class Number(Type):
    """A validator that accepts any numbers (but not bool)."""

    name = "number"
    accept_types = numbers.Number
    reject_types = bool


class Date(Type):
    """A validator that accepts datetime.date values."""

    name = "date"
    accept_types = datetime.date


class Datetime(Type):
    """A validator that accepts datetime.datetime values."""

    name = "datetime"
    accept_types = datetime.datetime


class Time(Type):
    """A validator that accepts datetime.time values."""

    name = "time"
    accept_types = datetime.time


class String(Type):
    """A validator that accepts string values."""

    name = "string"
    accept_types = basestring

    def __init__(self, min_length=None, max_length=None):
        """Instantiate a String validator.

        :param min_length: If not None, strings shorter than ``min_length`` are
            invalid.
        :param max_length: If not None, strings longer than ``max_length`` are
            invalid.
        """
        super(String, self).__init__()
        self._min_length = min_length
        self._max_length = max_length

    def validate(self, value, adapt=True):
        super(String, self).validate(value)
        if self._min_length is not None and len(value) < self._min_length:
            raise ValidationError("must be at least %d characters long" %
                                  self._min_length, value)
        if self._max_length is not None and len(value) > self._max_length:
            raise ValidationError("must be at most %d characters long" %
                                  self._max_length, value)
        return value


_SRE_Pattern = type(re.compile(""))

class Pattern(String):
    """A validator that accepts strings that match a given regular expression.

    Attributes:
        - regexp: The regular expression (string or compiled) to be matched.
    """

    regexp = None

    def __init__(self, regexp=None):
        super(Pattern, self).__init__()
        self.regexp = re.compile(regexp or self.regexp)

    def validate(self, value, adapt=True):
        super(Pattern, self).validate(value)
        if not self.regexp.match(value):
            self.error(value)
        return value

    def error(self, value):
        raise ValidationError("must match %s" % self.humanized_name, value)

    @property
    def humanized_name(self):
        return "pattern %s" % self.regexp.pattern


@Pattern.register_factory
def _PatternFactory(obj):
    """Parse a compiled regexp as a ``Pattern`` instance."""
    if isinstance(obj, _SRE_Pattern):
        return Pattern(obj)


class HomogeneousSequence(Type):
    """A validator that accepts homogeneous, non-fixed size sequences."""

    accept_types = collections.Sequence
    reject_types = basestring

    def __init__(self, item_schema=None, min_length=None, max_length=None):
        """Instantiate a ``HomogeneousSequence`` validator.

        :param item_schema: If not None, the schema of the items of the list.
        """
        super(HomogeneousSequence, self).__init__()
        if item_schema is not None:
            self._item_validator = parse(item_schema)
        else:
            self._item_validator = None
        self._min_length = min_length
        self._max_length = max_length

    def validate(self, value, adapt=True):
        super(HomogeneousSequence, self).validate(value)
        if self._min_length is not None and len(value) < self._min_length:
            raise ValidationError("must contain at least %d elements" %
                                  self._min_length, value)
        if self._max_length is not None and len(value) > self._max_length:
            raise ValidationError("must contain at most %d elements" %
                                  self._max_length, value)
        if self._item_validator is None:
            return value
        if adapt:
            return value.__class__(self._iter_validated_items(value, adapt))
        for _ in self._iter_validated_items(value, adapt):
            pass

    def _iter_validated_items(self, value, adapt):
        validate_item = self._item_validator.validate
        for i, item in enumerate(value):
            try:
                yield validate_item(item, adapt)
            except ValidationError as ex:
                raise ex.add_context(i)

@HomogeneousSequence.register_factory
def _HomogeneousSequenceFactory(obj):
    """Parse an empty or 1-element ``[schema]`` list as a ``HomogeneousSequence`` 
    validator.
    """
    if isinstance(obj, list) and len(obj) <= 1:
        return HomogeneousSequence(*obj)


class HeterogeneousSequence(Type):
    """A validator that accepts heterogeneous, fixed size sequences."""

    accept_types = collections.Sequence
    reject_types = basestring

    def __init__(self, *item_schemas):
        """Instantiate a ``HeterogeneousSequence`` validator.

        :param item_schemas: The schema of each element of the the tuple.
        """
        super(HeterogeneousSequence, self).__init__()
        self._item_validators = map(parse, item_schemas)

    def validate(self, value, adapt=True):
        super(HeterogeneousSequence, self).validate(value)
        if len(value) != len(self._item_validators):
            raise ValidationError("%d items expected, %d found" %
                                  (len(self._item_validators), len(value)), value)
        if adapt:
            return value.__class__(self._iter_validated_items(value, adapt))
        for _ in self._iter_validated_items(value, adapt):
            pass

    def _iter_validated_items(self, value, adapt):
        for i, (validator, item) in enumerate(izip(self._item_validators, value)):
            try:
                yield validator.validate(item, adapt)
            except ValidationError as ex:
                raise ex.add_context(i)

@HeterogeneousSequence.register_factory
def _HeterogeneousSequenceFactory(obj):
    """Parse a  ``(schema1, ..., schemaN)`` tuple as a ``HeterogeneousSequence`` 
    validator.
    """
    if isinstance(obj, tuple):
        return HeterogeneousSequence(*obj)


class Mapping(Type):
    """A validator that accepts dicts."""

    accept_types = collections.Mapping

    def __init__(self, key_schema=None, value_schema=None):
        """Instantiate a dict validator.

        :param key_schema: If not None, the schema of the dict keys.
        :param value_schema: If not None, the schema of the dict values.
        """
        super(Mapping, self).__init__()
        if key_schema is not None:
            self._key_validator = parse(key_schema)
        else:
            self._key_validator = None
        if value_schema is not None:
            self._value_validator = parse(value_schema)
        else:
            self._value_validator = None

    def validate(self, value, adapt=True):
        super(Mapping, self).validate(value)
        if adapt:
            return dict(self._iter_validated_items(value, adapt))
        for _ in self._iter_validated_items(value, adapt):
            pass

    def _iter_validated_items(self, value, adapt):
        validate_key = validate_value = None
        if self._key_validator is not None:
            validate_key = self._key_validator.validate
        if self._value_validator is not None:
            validate_value = self._value_validator.validate
        for k, v in value.iteritems():
            if validate_value is not None:
                try:
                    v = validate_value(v, adapt)
                except ValidationError as ex:
                    raise ex.add_context(k)
            if validate_key is not None:
                k = validate_key(k, adapt)
            yield (k, v)


class Object(Type):
    """A validator that accepts json-like objects.

    A ``json-like object`` here is meant as a dict with specific properties 
    (i.e. string keys).
    """

    accept_types = collections.Mapping

    REQUIRED_PROPERTIES = False
    ADDITIONAL_PROPERTIES = True

    def __init__(self, optional={}, required={}, additional=None):
        """Instantiate an Object validator.

        :param optional: The schema of optional properties, specified as a
            ``{name: schema}`` dict.
        :param required: The schema of required properties, specified as a
            ``{name: schema}`` dict.
        :param additional: The schema of all properties that are not explicitly
            defined as ``optional`` or ``required``. It can also be:
            - ``True`` to allow any value for additional properties.
            - ``False`` to disallow any additional properties.
            - ``None`` to use the value of the ``ADDITIONAL_PROPERTIES`` class
              attribute.
        """
        super(Object, self).__init__()
        if additional is None:
            additional = self.ADDITIONAL_PROPERTIES
        if not isinstance(additional, bool):
            additional = parse(additional)
        self._named_validators = [
            (name, parse(schema))
            for name, schema in dict(optional, **required).iteritems()
        ]
        self._required_keys = set(required)
        self._all_keys = set(name for name, _ in self._named_validators)
        self._additional = additional

    def validate(self, value, adapt=True):
        super(Object, self).validate(value)
        missing_required = self._required_keys.difference(value)
        if missing_required:
            raise ValidationError("missing required properties: %s" %
                                  list(missing_required), value)
        if adapt:
            adapted = dict(value)
            adapted.update(self._iter_validated_items(value, adapt))
            return adapted
        for _ in self._iter_validated_items(value, adapt):
            pass

    def _iter_validated_items(self, value, adapt):
        for name, validator in self._named_validators:
            if name in value:
                try:
                    yield (name, validator.validate(value[name], adapt))
                except ValidationError as ex:
                    raise ex.add_context(name)
            elif isinstance(validator, Nullable) and validator._default is not None:
                yield (name, validator.default)

        if self._additional != True:
            all_keys = self._all_keys
            additional_properties = [k for k in value if k not in all_keys]
            if additional_properties:
                if self._additional == False:
                    raise ValidationError("additional properties: %s" %
                                          additional_properties, value)
                additional_validate = self._additional.validate
                for name in additional_properties:
                    try:
                        yield (name, additional_validate(value[name], adapt))
                    except ValidationError as ex:
                        raise ex.add_context(name)


@Object.register_factory
def _ObjectFactory(obj, required_properties=None, additional_properties=None):
    """Parse a python ``{name: schema}`` dict as an ``Object`` instance.

    - A property name prepended by "+" is required
    - A property name prepended by "?" is optional
    - Any other property is:
      - required if ``required_properties`` is True or ``required_properties``
        is None and ``Object.REQUIRED_PROPERTIES``
      - optional if ``required_properties`` is False or ``required_properties``
        is None and ``not Object.REQUIRED_PROPERTIES``

    :param additional_properties: The ``additional`` parameter to ``Object()``.
    """
    if isinstance(obj, dict):
        if required_properties is None:
            required_properties = Object.REQUIRED_PROPERTIES
        optional, required = {}, {}
        for key, value in obj.iteritems():
            if key.startswith("+"):
                required[key[1:]] = value
            elif key.startswith("?"):
                optional[key[1:]] = value
            elif required_properties:
                required[key] = value
            else:
                optional[key] = value
        return Object(optional, required, additional_properties)


def _format_types(types):
    if inspect.isclass(types):
        types = (types,)
    names = map(get_type_name, types)
    s = names[-1]
    if len(names) > 1:
        s = ", ".join(names[:-1]) + " or " + s
    return s

########NEW FILE########
