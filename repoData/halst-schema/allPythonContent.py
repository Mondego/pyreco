__FILENAME__ = schema
__version__ = '0.3.1'


class SchemaError(Exception):

    """Error during Schema validation."""

    def __init__(self, autos, errors):
        self.autos = autos if type(autos) is list else [autos]
        self.errors = errors if type(errors) is list else [errors]
        Exception.__init__(self, self.code)

    @property
    def code(self):
        def uniq(seq):
            seen = set()
            seen_add = seen.add
            return [x for x in seq if x not in seen and not seen_add(x)]
        a = uniq(i for i in self.autos if i is not None)
        e = uniq(i for i in self.errors if i is not None)
        if e:
            return '\n'.join(e)
        return '\n'.join(a)


class And(object):

    def __init__(self, *args, **kw):
        self._args = args
        assert list(kw) in (['error'], [])
        self._error = kw.get('error')

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(repr(a) for a in self._args))

    def validate(self, data):
        for s in [Schema(s, error=self._error) for s in self._args]:
            data = s.validate(data)
        return data


class Or(And):

    def validate(self, data):
        x = SchemaError([], [])
        for s in [Schema(s, error=self._error) for s in self._args]:
            try:
                return s.validate(data)
            except SchemaError as _x:
                x = _x
        raise SchemaError(['%r did not validate %r' % (self, data)] + x.autos,
                          [self._error] + x.errors)


class Use(object):

    def __init__(self, callable_, error=None):
        assert callable(callable_)
        self._callable = callable_
        self._error = error

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._callable)

    def validate(self, data):
        try:
            return self._callable(data)
        except SchemaError as x:
            raise SchemaError([None] + x.autos, [self._error] + x.errors)
        except BaseException as x:
            f = self._callable.__name__
            raise SchemaError('%s(%r) raised %r' % (f, data, x), self._error)


def priority(s):
    """Return priority for a give object."""
    if type(s) in (list, tuple, set, frozenset):
        return 6
    if type(s) is dict:
        return 5
    if hasattr(s, 'validate'):
        return 4
    if issubclass(type(s), type):
        return 3
    if callable(s):
        return 2
    else:
        return 1


class Schema(object):

    def __init__(self, schema, error=None):
        self._schema = schema
        self._error = error

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._schema)

    def validate(self, data):
        s = self._schema
        e = self._error
        if type(s) in (list, tuple, set, frozenset):
            data = Schema(type(s), error=e).validate(data)
            return type(s)(Or(*s, error=e).validate(d) for d in data)
        if type(s) is dict:
            data = Schema(dict, error=e).validate(data)
            new = type(data)()  # new - is a dict of the validated values
            x = None
            coverage = set()  # non-optional schema keys that were matched
            # for each key and value find a schema entry matching them, if any
            sorted_skeys = list(sorted(s, key=priority))
            for key, value in data.items():
                valid = False
                skey = None
                for skey in sorted_skeys:
                    svalue = s[skey]
                    try:
                        nkey = Schema(skey, error=e).validate(key)
                    except SchemaError:
                        pass
                    else:
                        try:
                            nvalue = Schema(svalue, error=e).validate(value)
                        except SchemaError as _x:
                            x = _x
                            raise
                        else:
                            coverage.add(skey)
                            valid = True
                            break
                if valid:
                    new[nkey] = nvalue
                elif skey is not None:
                    if x is not None:
                        raise SchemaError(['invalid value for key %r' % key] +
                                          x.autos, [e] + x.errors)
            coverage = set(k for k in coverage if type(k) is not Optional)
            required = set(k for k in s if type(k) is not Optional)
            if coverage != required:
                raise SchemaError('missed keys %r' % (required - coverage), e)
            if len(new) != len(data):
                wrong_keys = set(data.keys()) - set(new.keys())
                s_wrong_keys = ', '.join('%r' % k for k in sorted(wrong_keys))
                raise SchemaError('wrong keys %s in %r' % (s_wrong_keys, data),
                                  e)
            return new
        if hasattr(s, 'validate'):
            try:
                return s.validate(data)
            except SchemaError as x:
                raise SchemaError([None] + x.autos, [e] + x.errors)
            except BaseException as x:
                raise SchemaError('%r.validate(%r) raised %r' % (s, data, x),
                                  self._error)
        if issubclass(type(s), type):
            if isinstance(data, s):
                return data
            else:
                raise SchemaError('%r should be instance of %r' % (data, s), e)
        if callable(s):
            f = s.__name__
            try:
                if s(data):
                    return data
            except SchemaError as x:
                raise SchemaError([None] + x.autos, [e] + x.errors)
            except BaseException as x:
                raise SchemaError('%s(%r) raised %r' % (f, data, x),
                                  self._error)
            raise SchemaError('%s(%r) should evaluate to True' % (f, data), e)
        if s == data:
            return data
        else:
            raise SchemaError('%r does not match %r' % (s, data), e)


class Optional(Schema):

    """Marker for an optional part of Schema."""

########NEW FILE########
__FILENAME__ = test_schema
from __future__ import with_statement
import os

from pytest import raises

from schema import Schema, Use, And, Or, Optional, SchemaError


try:
    basestring
except NameError:
    basestring = str  # Python 3 does not have basestring


SE = raises(SchemaError)


def ve(_):
    raise ValueError()


def se(_):
    raise SchemaError('first auto', 'first error')


def test_schema():

    assert Schema(1).validate(1) == 1
    with SE: Schema(1).validate(9)

    assert Schema(int).validate(1) == 1
    with SE: Schema(int).validate('1')
    assert Schema(Use(int)).validate('1') == 1
    with SE: Schema(int).validate(int)

    assert Schema(str).validate('hai') == 'hai'
    with SE: Schema(str).validate(1)
    assert Schema(Use(str)).validate(1) == '1'

    assert Schema(list).validate(['a', 1]) == ['a', 1]
    assert Schema(dict).validate({'a': 1}) == {'a': 1}
    with SE: Schema(dict).validate(['a', 1])

    assert Schema(lambda n: 0 < n < 5).validate(3) == 3
    with SE: Schema(lambda n: 0 < n < 5).validate(-1)


def test_validate_file():
    assert Schema(
            Use(open)).validate('LICENSE-MIT').read().startswith('Copyright')
    with SE: Schema(Use(open)).validate('NON-EXISTENT')
    assert Schema(os.path.exists).validate('.') == '.'
    with SE: Schema(os.path.exists).validate('./non-existent/')
    assert Schema(os.path.isfile).validate('LICENSE-MIT') == 'LICENSE-MIT'
    with SE: Schema(os.path.isfile).validate('NON-EXISTENT')


def test_and():
    assert And(int, lambda n: 0 < n < 5).validate(3) == 3
    with SE: And(int, lambda n: 0 < n < 5).validate(3.33)
    assert And(Use(int), lambda n: 0 < n < 5).validate(3.33) == 3
    with SE: And(Use(int), lambda n: 0 < n < 5).validate('3.33')


def test_or():
    assert Or(int, dict).validate(5) == 5
    assert Or(int, dict).validate({}) == {}
    with SE: Or(int, dict).validate('hai')
    assert Or(int).validate(4)
    with SE: Or().validate(2)


def test_validate_list():
    assert Schema([1, 0]).validate([1, 0, 1, 1]) == [1, 0, 1, 1]
    assert Schema([1, 0]).validate([]) == []
    with SE: Schema([1, 0]).validate(0)
    with SE: Schema([1, 0]).validate([2])
    assert And([1, 0], lambda l: len(l) > 2).validate([0, 1, 0]) == [0, 1, 0]
    with SE: And([1, 0], lambda l: len(l) > 2).validate([0, 1])


def test_list_tuple_set_frozenset():
    assert Schema([int]).validate([1, 2])
    with SE: Schema([int]).validate(['1', 2])
    assert Schema(set([int])).validate(set([1, 2])) == set([1, 2])
    with SE: Schema(set([int])).validate([1, 2])  # not a set
    with SE: Schema(set([int])).validate(['1', 2])
    assert Schema(tuple([int])).validate(tuple([1, 2])) == tuple([1, 2])
    with SE: Schema(tuple([int])).validate([1, 2])  # not a set


def test_strictly():
    assert Schema(int).validate(1) == 1
    with SE: Schema(int).validate('1')


def test_dict():
    assert Schema({'key': 5}).validate({'key': 5}) == {'key': 5}
    with SE: Schema({'key': 5}).validate({'key': 'x'})
    assert Schema({'key': int}).validate({'key': 5}) == {'key': 5}
    assert Schema({'n': int, 'f': float}).validate(
            {'n': 5, 'f': 3.14}) == {'n': 5, 'f': 3.14}
    with SE: Schema({'n': int, 'f': float}).validate(
            {'n': 3.14, 'f': 5})
    with SE:
        try:
            Schema({'key': 5}).validate({})
        except SchemaError as e:
            assert e.args[0] in ["missed keys set(['key'])",
                                 "missed keys {'key'}"]  # Python 3 style
            raise
    with SE:
        try:
            Schema({'key': 5}).validate({'n': 5})
        except SchemaError as e:
            assert e.args[0] in ["missed keys set(['key'])",
                                 "missed keys {'key'}"]  # Python 3 style
            raise
    with SE:
        try:
            Schema({}).validate({'n': 5})
        except SchemaError as e:
            assert e.args[0] == "wrong keys 'n' in {'n': 5}"
            raise
    with SE:
        try:
            Schema({'key': 5}).validate({'key': 5, 'bad': 5})
        except SchemaError as e:
            assert e.args[0] in ["wrong keys 'bad' in {'key': 5, 'bad': 5}",
                                 "wrong keys 'bad' in {'bad': 5, 'key': 5}"]
            raise
    with SE:
        try:
            Schema({}).validate({'a': 5, 'b': 5})
        except SchemaError as e:
            assert e.args[0] in ["wrong keys 'a', 'b' in {'a': 5, 'b': 5}",
                                 "wrong keys 'a', 'b' in {'b': 5, 'a': 5}"]
            raise


def test_dict_keys():
    assert Schema({str: int}).validate(
            {'a': 1, 'b': 2}) == {'a': 1, 'b': 2}
    with SE: Schema({str: int}).validate({1: 1, 'b': 2})
    assert Schema({Use(str): Use(int)}).validate(
            {1: 3.14, 3.14: 1}) == {'1': 3, '3.14': 1}


def test_dict_optional_keys():
    with SE: Schema({'a': 1, 'b': 2}).validate({'a': 1})
    assert Schema({'a': 1, Optional('b'): 2}).validate({'a': 1}) == {'a': 1}
    assert Schema({'a': 1, Optional('b'): 2}).validate(
            {'a': 1, 'b': 2}) == {'a': 1, 'b': 2}


def test_complex():
    s = Schema({'<file>': And([Use(open)], lambda l: len(l)),
                '<path>': os.path.exists,
                Optional('--count'): And(int, lambda n: 0 <= n <= 5)})
    data = s.validate({'<file>': ['./LICENSE-MIT'], '<path>': './'})
    assert len(data) == 2
    assert len(data['<file>']) == 1
    assert data['<file>'][0].read().startswith('Copyright')
    assert data['<path>'] == './'


def test_nice_errors():
    try:
        Schema(int, error='should be integer').validate('x')
    except SchemaError as e:
        assert e.errors == ['should be integer']
    try:
        Schema(Use(float), error='should be a number').validate('x')
    except SchemaError as e:
        assert e.code == 'should be a number'
    try:
        Schema({Optional('i'): Use(int, error='should be a number')}).validate({'i': 'x'})
    except SchemaError as e:
        assert e.code == 'should be a number'


def test_use_error_handling():
    try:
        Use(ve).validate('x')
    except SchemaError as e:
        assert e.autos == ["ve('x') raised ValueError()"]
        assert e.errors == [None]
    try:
        Use(ve, error='should not raise').validate('x')
    except SchemaError as e:
        assert e.autos == ["ve('x') raised ValueError()"]
        assert e.errors == ['should not raise']
    try:
        Use(se).validate('x')
    except SchemaError as e:
        assert e.autos == [None, 'first auto']
        assert e.errors == [None, 'first error']
    try:
        Use(se, error='second error').validate('x')
    except SchemaError as e:
        assert e.autos == [None, 'first auto']
        assert e.errors == ['second error', 'first error']


def test_or_error_handling():
    try:
        Or(ve).validate('x')
    except SchemaError as e:
        assert e.autos[0].startswith('Or(')
        assert e.autos[0].endswith(") did not validate 'x'")
        assert e.autos[1] == "ve('x') raised ValueError()"
        assert len(e.autos) == 2
        assert e.errors == [None, None]
    try:
        Or(ve, error='should not raise').validate('x')
    except SchemaError as e:
        assert e.autos[0].startswith('Or(')
        assert e.autos[0].endswith(") did not validate 'x'")
        assert e.autos[1] == "ve('x') raised ValueError()"
        assert len(e.autos) == 2
        assert e.errors == ['should not raise', 'should not raise']
    try:
        Or('o').validate('x')
    except SchemaError as e:
        assert e.autos == ["Or('o') did not validate 'x'",
                           "'o' does not match 'x'"]
        assert e.errors == [None, None]
    try:
        Or('o', error='second error').validate('x')
    except SchemaError as e:
        assert e.autos == ["Or('o') did not validate 'x'",
                           "'o' does not match 'x'"]
        assert e.errors == ['second error', 'second error']


def test_and_error_handling():
    try:
        And(ve).validate('x')
    except SchemaError as e:
        assert e.autos == ["ve('x') raised ValueError()"]
        assert e.errors == [None]
    try:
        And(ve, error='should not raise').validate('x')
    except SchemaError as e:
        assert e.autos == ["ve('x') raised ValueError()"]
        assert e.errors == ['should not raise']
    try:
        And(str, se).validate('x')
    except SchemaError as e:
        assert e.autos == [None, 'first auto']
        assert e.errors == [None, 'first error']
    try:
        And(str, se, error='second error').validate('x')
    except SchemaError as e:
        assert e.autos == [None, 'first auto']
        assert e.errors == ['second error', 'first error']


def test_schema_error_handling():
    try:
        Schema(Use(ve)).validate('x')
    except SchemaError as e:
        assert e.autos == [None, "ve('x') raised ValueError()"]
        assert e.errors == [None, None]
    try:
        Schema(Use(ve), error='should not raise').validate('x')
    except SchemaError as e:
        assert e.autos == [None, "ve('x') raised ValueError()"]
        assert e.errors == ['should not raise', None]
    try:
        Schema(Use(se)).validate('x')
    except SchemaError as e:
        assert e.autos == [None, None, 'first auto']
        assert e.errors == [None, None, 'first error']
    try:
        Schema(Use(se), error='second error').validate('x')
    except SchemaError as e:
        assert e.autos == [None, None, 'first auto']
        assert e.errors == ['second error', None, 'first error']


def test_use_json():
    import json
    gist_schema = Schema(And(Use(json.loads),  # first convert from JSON
                             {Optional('description'): basestring,
                              'public': bool,
                              'files': {basestring: {'content': basestring}}}))
    gist = '''{"description": "the description for this gist",
               "public": true,
               "files": {
                   "file1.txt": {"content": "String file contents"},
                   "other.txt": {"content": "Another file contents"}}}'''
    assert gist_schema.validate(gist)


def test_error_reporting():
    s = Schema({'<files>': [Use(open, error='<files> should be readable')],
                '<path>': And(os.path.exists, error='<path> should exist'),
                '--count': Or(None, And(Use(int), lambda n: 0 < n < 5),
                              error='--count should be integer 0 < n < 5')},
               error='Error:')
    s.validate({'<files>': [], '<path>': './', '--count': 3})

    try:
        s.validate({'<files>': [], '<path>': './', '--count': '10'})
    except SchemaError as e:
        assert e.code == 'Error:\n--count should be integer 0 < n < 5'
    try:
        s.validate({'<files>': [], '<path>': './hai', '--count': '2'})
    except SchemaError as e:
        assert e.code == 'Error:\n<path> should exist'
    try:
        s.validate({'<files>': ['hai'], '<path>': './', '--count': '2'})
    except SchemaError as e:
        assert e.code == 'Error:\n<files> should be readable'


def test_schema_repr():  # what about repr with `error`s?
    schema = Schema([Or(None, And(str, Use(float)))])
    repr_ = "Schema([Or(None, And(<type 'str'>, Use(<type 'float'>)))])"
    # in Python 3 repr contains <class 'str'>, not <type 'str'>
    assert repr(schema).replace('class', 'type') == repr_


def test_validate_object():
    schema = Schema({object: str})
    assert schema.validate({42: 'str'}) == {42: 'str'}
    with SE: schema.validate({42: 777})


def test_issue_9_prioritized_key_comparison():
    validate = Schema({'key': 42, object: 42}).validate
    assert validate({'key': 42, 777: 42}) == {'key': 42, 777: 42}


def test_issue_9_prioritized_key_comparison_in_dicts():
    # http://stackoverflow.com/questions/14588098/docopt-schema-validation
    s = Schema({'ID': Use(int, error='ID should be an int'),
                'FILE': Or(None, Use(open, error='FILE should be readable')),
                Optional(str): object})
    data = {'ID': 10, 'FILE': None, 'other': 'other', 'other2': 'other2'}
    assert s.validate(data) == data
    data = {'ID': 10, 'FILE': None}
    assert s.validate(data) == data

########NEW FILE########
