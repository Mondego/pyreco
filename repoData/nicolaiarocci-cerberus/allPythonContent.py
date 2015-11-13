__FILENAME__ = cerberus
"""
    Extensible validation for Python dictionaries.
    This module implements Cerberus Validator class

    :copyright: 2012-2014 by Nicola Iarocci.
    :license: ISC, see LICENSE for more details.

    Full documentation is available at http://cerberus.readthedocs.org/
"""

import sys
import re
from datetime import datetime
from . import errors

if sys.version_info[0] == 3:
    _str_type = str
    _int_types = (int,)
else:
    _str_type = basestring
    _int_types = (int, long)


class ValidationError(ValueError):
    """ Raised when the target dictionary is missing or has the wrong format
    """
    pass


class SchemaError(ValueError):
    """ Raised when the validation schema is missing, has the wrong format or
    contains errors.
    """
    pass


class Validator(object):
    """ Validator class. Validates any Python dict against a validation schema,
    which is provided as an argument at class instantiation, or upon calling
    the :func:`validate` method.

    :param schema: optional validation schema.
    :param transparent_schema_rules: if ``True`` unknown schema rules will be
                                 ignored (no SchemaError will be raised).
                                 Defaults to ``False``. Useful you need to
                                 extend the schema grammar beyond Cerberus'
                                 domain.
    :param ignore_none_values: If ``True`` it will ignore None values for type
                               checking. (no UnknowType error will be added).
                               Defaults to ``False``. Useful if your document
                               is composed from function kwargs with defaults.
    :param allow_unknown: if ``True`` unknown key/value pairs (not present in
                          the schema) will be ignored, and validation will
                          pass. Defaults to ``False``, returning an 'unknown
                          field error' un validation.

    .. versionadded:: 0.7
       'keyschema' validation rule.
       'regex' validation rule.
       'dependencies' validation rule.
       'mix', 'max' now apply on floats and numbers too. Closes #30.
       'set' data type.

    .. versionadded:: 0.6
       'number' (integer or float) validator.

    .. versionchanged:: 0.5.0
       ``validator.errors`` returns a dict where keys are document fields and
       values are validation errors.

    .. versionchanged:: 0.4.0
       :func:`validate_update` is deprecated. Use :func:`validate` with
       ``update=True`` instead.
       Type validation is always performed first (only exception being
       ``nullable``). On failure, it blocks other rules on the same field.
       Closes #18.

    .. versionadded:: 0.2.0
       `self.errors` returns an empty list when validate() has not been called.
       Option so allow nullable field values.
       Option to allow unknown key/value pairs.

    .. versionadded:: 0.1.0
       Option to ignore None values for type checking.

    .. versionadded:: 0.0.3
       Support for transparent schema rules.
       Added new 'empty' rule for string fields.

    .. versionadded:: 0.0.2
        Support for addition and validation of custom data types.
    """

    def __init__(self, schema=None, transparent_schema_rules=False,
                 ignore_none_values=False, allow_unknown=False):
        self.schema = schema
        self.transparent_schema_rules = transparent_schema_rules
        self.ignore_none_values = ignore_none_values
        self.allow_unknown = allow_unknown
        self._errors = {}

    def __call__(self, *args, **kwargs):
        return self.validate(*args, **kwargs)

    @property
    def errors(self):
        """
        :rtype: a list of validation errors. Will be empty if no errors
                were found during. Resets after each call to :func:`validate`.
        """
        return self._errors

    def validate_update(self, document, schema=None):
        """ Validates a Python dicitionary against a validation schema. The
        difference with :func:`validate` is that the ``required`` rule will be
        ignored here.

        :param schema: optional validation schema. Defaults to ``None``. If not
                       provided here, the schema must have been provided at
                       class instantation.
        :return: True if validation succeeds, False otherwise. Check the
                 :func:`errors` property for a list of validation errors.

        .. deprecated:: 0.4.0
           Use :func:`validate` with ``update=True`` instead.
        """
        return self._validate(document, schema, update=True)

    def validate(self, document, schema=None, update=False):
        """ Validates a Python dictionary against a validation schema.

        :param document: the dict to validate.
        :param schema: the validation schema. Defaults to ``None``. If not
                       provided here, the schema must have been provided at
                       class instantation.
        :param update: If ``True`` validation of required fields won't be
                       performed.

        :return: True if validation succeeds, False otherwise. Check the
                 :func:`errors` property for a list of validation errors.

        .. versionchanged:: 0.4.0
           Support for update mode.
        """
        return self._validate(document, schema, update=update)

    def _validate(self, document, schema=None, update=False):

        self._errors = {}
        self.update = update

        if schema is not None:
            self.schema = schema
        elif self.schema is None:
            raise SchemaError(errors.ERROR_SCHEMA_MISSING)
        if not isinstance(self.schema, dict):
            raise SchemaError(errors.ERROR_SCHEMA_FORMAT % str(self.schema))

        if document is None:
            raise ValidationError(errors.ERROR_DOCUMENT_MISSING)
        if not isinstance(document, dict):
            raise ValidationError(errors.ERROR_DOCUMENT_FORMAT % str(document))
        self.document = document

        special_rules = ["required", "nullable", "type", "dependencies"]
        for field, value in self.document.items():

            if self.ignore_none_values and value is None:
                continue

            definition = self.schema.get(field)
            if definition:
                if isinstance(definition, dict):

                    if value is None:
                        if definition.get("nullable", False) is True:
                            continue
                        else:
                            self._error(field, errors.ERROR_NOT_NULLABLE)

                    if 'type' in definition:
                        self._validate_type(definition['type'], field, value)
                        if self.errors.get(field):
                            continue

                    if "dependencies" in definition:
                        self._validate_dependencies(
                            document=self.document,
                            dependencies=definition["dependencies"],
                            field=field
                        )
                        if self.errors.get(field):
                            continue

                    definition_rules = [rule for rule in definition.keys()
                                        if rule not in special_rules]
                    for rule in definition_rules:
                        validatorname = "_validate_" + rule.replace(" ", "_")
                        validator = getattr(self, validatorname, None)
                        if validator:
                            validator(definition[rule], field, value)
                        elif not self.transparent_schema_rules:
                            raise SchemaError(errors.ERROR_UNKNOWN_RULE %
                                              (rule, field))
                else:
                    raise SchemaError(errors.ERROR_DEFINITION_FORMAT % field)

            else:
                if not self.allow_unknown:
                    self._error(field, errors.ERROR_UNKNOWN_FIELD)

        if not self.update:
            self._validate_required_fields()

        return len(self._errors) == 0

    def _error(self, field, _error):
        field_errors = self._errors.get(field, [])

        if not isinstance(field_errors, list):
            field_errors = [field_errors]

        if isinstance(_error, (_str_type, dict)):
            field_errors.append(_error)
        else:
            field_errors.extend(_error)

        if len(field_errors) == 1:
            field_errors = field_errors.pop()

        self._errors[field] = field_errors

    def _validate_required_fields(self):
        required = list(field for field, definition in self.schema.items()
                        if definition.get('required') is True)
        missing = set(required) - set(key for key in self.document.keys()
                                      if self.document.get(key) is not None
                                      or not self.ignore_none_values)
        for field in missing:
            self._error(field, errors.ERROR_REQUIRED_FIELD)

    def _validate_readonly(self, read_only, field, value):
        if read_only:
            self._error(field, errors.ERROR_READONLY_FIELD)

    def _validate_regex(self, match, field, value):
        """
        .. versionadded:: 0.7
        """
        pattern = re.compile(match)
        if not pattern.match(value):
            self._error(field, errors.ERROR_REGEX % match)

    def _validate_type(self, data_type, field, value):
        validator = getattr(self, "_validate_type_" + data_type, None)
        if validator:
            validator(field, value)
        else:
            raise SchemaError(errors.ERROR_UNKNOWN_TYPE % data_type)

    def _validate_type_string(self, field, value):
        if not isinstance(value, _str_type):
            self._error(field, errors.ERROR_BAD_TYPE % "string")

    def _validate_type_integer(self, field, value):
        if not isinstance(value, _int_types):
            self._error(field, errors.ERROR_BAD_TYPE % "integer")

    def _validate_type_float(self, field, value):
        if not isinstance(value, float):
            self._error(field, errors.ERROR_BAD_TYPE % "float")

    def _validate_type_number(self, field, value):
        """
        .. versionadded:: 0.6
        """
        if not isinstance(value, float) and not isinstance(value, _int_types):
            self._error(field, errors.ERROR_BAD_TYPE % "number")

    def _validate_type_boolean(self, field, value):
        if not isinstance(value, bool):
            self._error(field, errors.ERROR_BAD_TYPE % "boolean")

    def _validate_type_datetime(self, field, value):
        if not isinstance(value, datetime):
            self._error(field, errors.ERROR_BAD_TYPE % "datetime")

    def _validate_type_dict(self, field, value):
        if not isinstance(value, dict):
            self._error(field, errors.ERROR_BAD_TYPE % "dict")

    def _validate_type_list(self, field, value):
        if not isinstance(value, list):
            self._error(field, errors.ERROR_BAD_TYPE % "list")

    def _validate_type_set(self, field, value):
        if not isinstance(value, set):
            self._error(field, errors.ERROR_BAD_TYPE % "set")

    def _validate_maxlength(self, max_length, field, value):
        if isinstance(value, (_str_type, list)):
            if len(value) > max_length:
                self._error(field, errors.ERROR_MAX_LENGTH % max_length)

    def _validate_minlength(self, min_length, field, value):
        if isinstance(value, (_str_type, list)):
            if len(value) < min_length:
                self._error(field, errors.ERROR_MIN_LENGTH % min_length)

    def _validate_max(self, max_value, field, value):
        if isinstance(value, (_int_types, float)):
            if value > max_value:
                self._error(field, errors.ERROR_MAX_VALUE % max_value)

    def _validate_min(self, min_value, field, value):
        if isinstance(value, (_int_types, float)):
            if value < min_value:
                self._error(field, errors.ERROR_MIN_VALUE % min_value)

    def _validate_allowed(self, allowed_values, field, value):
        if isinstance(value, _str_type):
            if value not in allowed_values:
                self._error(field, errors.ERROR_UNALLOWED_VALUE % value)
        elif isinstance(value, list):
            disallowed = set(value) - set(allowed_values)
            if disallowed:
                self._error(field,
                            errors.ERROR_UNALLOWED_VALUES % list(disallowed))
        elif isinstance(value, int):
            if value not in allowed_values:
                self._error(field, errors.ERROR_UNALLOWED_VALUE % value)

    def _validate_empty(self, empty, field, value):
        if isinstance(value, _str_type) and len(value) == 0 and not empty:
            self._error(field, errors.ERROR_EMPTY_NOT_ALLOWED)

    def _validate_schema(self, schema, field, value):
        if isinstance(value, list):
            list_errors = {}
            for i in range(len(value)):
                validator = self.__class__({i: schema})
                validator.validate({i: value[i]})
                list_errors.update(validator.errors)
            if len(list_errors):
                self._error(field, list_errors)
        elif isinstance(value, dict):
            validator = self.__class__(schema)
            validator.validate(value)
            if len(validator.errors):
                self._error(field, validator.errors)
        else:
            self._error(field, errors.ERROR_BAD_TYPE % "dict or list")

    def _validate_keyschema(self, schema, field, value):
        for key, document in value.items():
            validator = self.__class__(schema)
            validator.validate({key: document}, {key: schema})
            if len(validator.errors):
                self._error(field, validator.errors)

    def _validate_items(self, items, field, value):
        if isinstance(items, dict):
            self._validate_items_schema(items, field, value)
        elif isinstance(items, list):
            self._validate_items_list(items, field, value)

    def _validate_items_list(self, schema, field, values):
        if len(schema) != len(values):
            self._error(field, errors.ERROR_ITEMS_LIST % len(schema))
        else:
            for i in range(len(schema)):
                validator = self.__class__({i: schema[i]})
                validator.validate({i: values[i]})
                self.errors.update(validator.errors)

    def _validate_items_schema(self, schema, field, value):
        validator = self.__class__(schema)
        for item in value:
            validator.validate(item)
            for field, error in validator.errors.items():
                self._error(field, error)

    def _validate_dependencies(self, document, dependencies, field):

        # handle cases where dependencies is a string or list of strings
        if isinstance(dependencies, _str_type):
            dependencies = [dependencies]

        if isinstance(dependencies, (list, tuple)):
            for dependency in dependencies:
                if dependency not in document:
                    self._error(field, errors.ERROR_DEPENDENCIES_FIELD %
                                dependency)

########NEW FILE########
__FILENAME__ = errors
"""
This module contains the error messages issued by the Cerberus Validator.
The test suite uses this module as well.
"""
ERROR_SCHEMA_MISSING = "validation schema missing"
ERROR_SCHEMA_FORMAT = "'%s' is not a schema, must be a dict"
ERROR_DOCUMENT_MISSING = "document is missing"
ERROR_DOCUMENT_FORMAT = "'%s' is not a document, must be a dict"
ERROR_UNKNOWN_RULE = "unknown rule '%s' for field '%s'"
ERROR_DEFINITION_FORMAT = "schema definition for field '%s' must be a dict"
ERROR_UNKNOWN_FIELD = "unknown field"
ERROR_REQUIRED_FIELD = "required field"
ERROR_UNKNOWN_TYPE = "unrecognized data-type '%s'"
ERROR_BAD_TYPE = "must be of %s type"
ERROR_MIN_LENGTH = "min length is %d"
ERROR_MAX_LENGTH = "max length is %d"
ERROR_UNALLOWED_VALUES = "unallowed values %s"
ERROR_UNALLOWED_VALUE = "unallowed value %s"
ERROR_ITEMS_LIST = "length of list should be %d"
ERROR_READONLY_FIELD = "field is read-only"
ERROR_MAX_VALUE = "max value is %d"
ERROR_MIN_VALUE = "min value is %d"
ERROR_EMPTY_NOT_ALLOWED = "empty values not allowed"
ERROR_NOT_NULLABLE = "null value not allowed"
ERROR_REGEX = "value does not match regex '%s'"
ERROR_DEPENDENCIES_FIELD = "field '%s' is required"

########NEW FILE########
__FILENAME__ = tests
import re
from datetime import datetime
from random import choice
from string import ascii_lowercase
from . import TestBase
from ..cerberus import Validator, errors


class TestValidator(TestBase):

    def test_empty_schema(self):
        v = Validator()
        self.assertSchemaError(self.document, None, v,
                               errors.ERROR_SCHEMA_MISSING)

    def test_bad_schema_type(self):
        schema = "this string should really be  dict"
        v = Validator(schema)
        self.assertSchemaError(self.document, None, v,
                               errors.ERROR_SCHEMA_FORMAT % schema)

        v = Validator()
        self.assertSchemaError(self.document, schema, v,
                               errors.ERROR_SCHEMA_FORMAT % schema)

    def test_empty_document(self):
        self.assertValidationError(None, None, None,
                                   errors.ERROR_DOCUMENT_MISSING)

    def test_bad_document_type(self):
        document = "not a dict"
        self.assertValidationError(document, None, None,
                                   errors.ERROR_DOCUMENT_FORMAT % document)

    def test_bad_schema_definition(self):
        field = 'name'
        schema = {field: 'this should really be a dict'}
        self.assertSchemaError(self.document, schema, None,
                               errors.ERROR_DEFINITION_FORMAT % field)

    def test_unknown_field(self):
        field = 'surname'
        self.assertFail({field: 'doe'})
        self.assertError(field, errors.ERROR_UNKNOWN_FIELD)

    def test_unknown_rule(self):
        field = 'name'
        schema = {field: {'unknown_rule': True, 'type': 'string'}}
        self.assertSchemaError(
            self.document, schema, None,
            errors.ERROR_UNKNOWN_RULE % ('unknown_rule', field)
        )

    def test_required_field(self):
        self.assertFail({'an_integer': 1})
        self.assertError('a_required_string', errors.ERROR_REQUIRED_FIELD)

    def test_nullable_field(self):
        self.assertSuccess({'a_nullable_integer': None})
        self.assertSuccess({'a_nullable_integer': 3})
        self.assertSuccess({'a_nullable_field_without_type': None})
        self.assertFail({'a_nullable_integer': "foo"})
        self.assertFail({'an_integer': None})
        self.assertFail({'a_not_nullable_field_without_type': None})

    def test_readonly_field(self):
        field = 'a_readonly_string'
        self.assertFail({field: 'update me if you can'})
        self.assertError(field, errors.ERROR_READONLY_FIELD)

    def test_unknown_data_type(self):
        field = 'name'
        value = 'catch_me'
        schema = {field: {'type': value}}
        self.assertSchemaError(self.document, schema, None,
                               errors.ERROR_UNKNOWN_TYPE % value)

    def test_not_a_string(self):
        self.assertBadType('a_required_string', 'string', 1)

    def test_not_a_integer(self):
        self.assertBadType('an_integer', 'integer', "i'm not an integer")

    def test_not_a_boolean(self):
        self.assertBadType('a_boolean', 'boolean', "i'm not an boolean")

    def test_not_a_datetime(self):
        self.assertBadType('a_datetime', 'datetime', "i'm not a datetime")

    def test_not_a_float(self):
        self.assertBadType('a_float', 'float', "i'm not a float")

    def test_not_a_number(self):
        self.assertBadType('a_number', 'number', "i'm not a number")

    def test_not_a_list(self):
        self.assertBadType('a_list_of_values', 'list', "i'm not a list")

    def test_not_a_dict(self):
        self.assertBadType('a_dict', 'dict', "i'm not a dict")

    def test_bad_max_length(self):
        field = 'a_required_string'
        max_length = self.schema[field]['maxlength']
        value = "".join(choice(ascii_lowercase) for i in range(max_length + 1))
        self.assertFail({field: value})
        self.assertError(field, errors.ERROR_MAX_LENGTH % max_length)

    def test_bad_min_length(self):
        field = 'a_required_string'
        min_length = self.schema[field]['minlength']
        value = "".join(choice(ascii_lowercase) for i in range(min_length - 1))
        self.assertFail({field: value})
        self.assertError(field, errors.ERROR_MIN_LENGTH % min_length)

    def test_bad_max_value(self):
        def assert_bad_max_value(field, inc):
            max_value = self.schema[field]['max']
            value = max_value + inc
            self.assertFail({field: value})
            self.assertError(field, errors.ERROR_MAX_VALUE % max_value)

        field = 'an_integer'
        assert_bad_max_value(field, 1)
        field = 'a_float'
        assert_bad_max_value(field, 1.0)
        field = 'a_number'
        assert_bad_max_value(field, 1)

    def test_bad_min_value(self):
        def assert_bad_min_value(field, inc):
            min_value = self.schema[field]['min']
            value = min_value - inc
            self.assertFail({field: value})
            self.assertError(field, errors.ERROR_MIN_VALUE % min_value)

        field = 'an_integer'
        assert_bad_min_value(field, 1)
        field = 'a_float'
        assert_bad_min_value(field, 1.0)
        field = 'a_number'
        assert_bad_min_value(field, 1)

    def test_bad_schema(self):
        field = 'a_dict'
        schema_field = 'address'
        value = {schema_field: 34}
        self.assertFail({field: value})
        v = self.validator
        self.assertTrue(field in v.errors)
        self.assertTrue(schema_field in v.errors[field])
        self.assertTrue(errors.ERROR_BAD_TYPE % 'string' in
                        v.errors[field][schema_field])
        self.assertTrue('city' in v.errors[field])
        self.assertTrue(errors.ERROR_REQUIRED_FIELD in
                        v.errors[field]['city'])

    def test_bad_keyschema(self):
        field = 'a_dict_with_keyschema'
        schema_field = 'a_string'
        value = {schema_field: 'not an integer'}
        self.assertFail({field: value})
        v = self.validator
        self.assertTrue(field in v.errors)
        self.assertTrue(schema_field in v.errors[field])
        self.assertTrue(errors.ERROR_BAD_TYPE % 'integer' in
                        v.errors[field][schema_field])

    def test_bad_list_of_values(self):
        field = 'a_list_of_values'
        value = ['a string', 'not an integer']
        self.assertFail({field: value})
        v = self.validator
        self.assertTrue(1 in v.errors)
        self.assertTrue(errors.ERROR_BAD_TYPE % 'integer' in
                        v.errors[1])

        value = ['a string', 10, 'an extra item']
        self.assertFail({field: value})
        self.assertError(field, errors.ERROR_ITEMS_LIST % 2)

    def test_bad_list_of_integers(self):
        field = 'a_list_of_integers'
        value = [34, 'not an integer']
        self.assertFail({field: value})

    def test_bad_list_of_dicts_deprecated(self):
        field = 'a_list_of_dicts_deprecated'
        value = [{'sku': 'KT123', 'price': '100'}]
        self.assertFail({field: value})
        self.assertError('price', errors.ERROR_BAD_TYPE % 'integer')

        value = ["not a dict"]
        self.assertValidationError({field: value}, None, None,
                                   errors.ERROR_DOCUMENT_FORMAT % value[0])

    def test_bad_list_of_dicts(self):
        field = 'a_list_of_dicts'
        value = [{'sku': 'KT123', 'price': '100'}]
        self.assertFail({field: value})
        v = self.validator
        self.assertTrue(field in v.errors)
        self.assertTrue(0 in v.errors[field])
        self.assertTrue('price' in v.errors[field][0])
        self.assertTrue(errors.ERROR_BAD_TYPE % 'integer' in
                        v.errors[field][0]['price'])

        value = ["not a dict"]
        self.assertValidationError({field: value}, None, None,
                                   errors.ERROR_DOCUMENT_FORMAT % value[0])

    def test_array_unallowed(self):
        field = 'an_array'
        value = ['agent', 'client', 'profit']
        self.assertFail({field: value})
        self.assertError(field, errors.ERROR_UNALLOWED_VALUES % ['profit'])

    def test_string_unallowed(self):
        field = 'a_restricted_string'
        value = 'profit'
        self.assertFail({field: value})
        self.assertError(field, errors.ERROR_UNALLOWED_VALUE % value)

    def test_integer_unallowed(self):
        field = 'a_restricted_integer'
        value = 2
        self.assertFail({field: value})
        self.assertError(field, errors.ERROR_UNALLOWED_VALUE % value)

    def test_integer_allowed(self):
        self.assertSuccess({'a_restricted_integer': -1})

    def test_validate_update(self):
        self.assertTrue(self.validator.validate({'an_integer': 100},
                                                update=True))

    def test_string(self):
        self.assertSuccess({'a_required_string': 'john doe'})

    def test_string_allowed(self):
        self.assertSuccess({'a_restricted_string': 'client'})

    def test_integer(self):
        self.assertSuccess({'an_integer': 50})

    def test_boolean(self):
        self.assertSuccess({'a_boolean': True})

    def test_datetime(self):
        self.assertSuccess({'a_datetime': datetime.now()})

    def test_float(self):
        self.assertSuccess({'a_float': 3.5})

    def test_number(self):
        self.assertSuccess({'a_number': 3.5})
        self.assertSuccess({'a_number': 3})

    def test_array(self):
        self.assertSuccess({'an_array': ['agent', 'client']})

    def test_set(self):
        self.assertSuccess({'a_set': set(['hello', 1])})

    def test_regex(self):
        field = 'a_regex_email'
        self.assertSuccess({field: 'valid.email@gmail.com'})
        self.assertFalse(self.validator.validate({field: 'invalid'},
                                                 self.schema, update=True))
        self.assertError(field, 'does not match regex')

    def tst_a_list_of_dicts_deprecated(self):
        self.assertSuccess(
            {
                'a_list_of_dicts_deprecated': [
                    {'sku': 'AK345', 'price': 100},
                    {'sku': 'YZ069', 'price': 25}
                ]
            }
        )

    def tst_a_list_of_dicts(self):
        self.assertSuccess(
            {
                'a_list_of_dicts': [
                    {'sku': 'AK345', 'price': 100},
                    {'sku': 'YZ069', 'price': 25}
                ]
            }
        )

    def test_a_list_of_values(self):
        self.assertSuccess({'a_list_of_values': ['hello', 100]})

    def test_a_list_of_integers(self):
        self.assertSuccess({'a_list_of_integers': [99, 100]})

    def test_a_dict(self):
        self.assertSuccess(
            {
                'a_dict': {
                    'address': 'i live here',
                    'city': 'in my own town'
                }
            }
        )

    def test_a_dict_with_keyschema(self):
        self.assertSuccess(
            {
                'a_dict_with_keyschema': {
                    'an integer': 99,
                    'another integer': 100
                }
            }
        )

    def test_a_list_length(self):
        field = 'a_list_length'
        min_length = self.schema[field]['minlength']
        max_length = self.schema[field]['maxlength']

        self.assertFail({field: [1] * (min_length - 1)})
        self.assertError(field, errors.ERROR_MIN_LENGTH % min_length)

        for i in range(min_length, max_length):
            value = [1] * i
            self.assertSuccess({field: value})

        self.assertFail({field: [1] * (max_length + 1)})
        self.assertError(field, errors.ERROR_MAX_LENGTH % max_length)

    def test_custom_datatype(self):
        class MyValidator(Validator):
            def _validate_type_objectid(self, field, value):
                if not re.match('[a-f0-9]{24}', value):
                    self._error(field, 'Not an ObjectId')

        schema = {'test_field': {'type': 'objectid'}}
        v = MyValidator(schema)
        self.assertTrue(v.validate({'test_field': '50ad188438345b1049c88a28'}))
        self.assertFalse(v.validate({'test_field': 'hello'}))
        self.assertError('test_field', 'Not an ObjectId', validator=v)

    def test_custom_datatype_rule(self):
        class MyValidator(Validator):
            def _validate_min_number(self, min_number, field, value):
                if value < min_number:
                    self._error(field, 'Below the min')

            def _validate_type_number(self, field, value):
                if not isinstance(value, int):
                    self._error(field, 'Not a number')

        schema = {'test_field': {'min_number': 1, 'type': 'number'}}
        v = MyValidator(schema)
        self.assertFalse(v.validate({'test_field': '0'}))
        self.assertError('test_field', 'Not a number', validator=v)
        self.assertFalse(v.validate({'test_field': 0}))
        self.assertError('test_field', 'Below the min', validator=v)

    def test_custom_validator(self):
        class MyValidator(Validator):
            def _validate_isodd(self, isodd, field, value):
                if isodd and not bool(value & 1):
                    self._error(field, 'Not an odd number')

        schema = {'test_field': {'isodd': True}}
        v = MyValidator(schema)
        self.assertTrue(v.validate({'test_field': 7}))
        self.assertFalse(v.validate({'test_field': 6}))
        self.assertError('test_field', 'Not an odd number', validator=v)

    def test_transparent_schema_rules(self):
        field = 'test'
        schema = {field: {'type': 'string', 'unknown_rule': 'a value'}}
        document = {field: 'hey!'}
        v = Validator(transparent_schema_rules=True)
        self.assertSuccess(schema=schema, document=document, validator=v)
        v.transparent_schema_rules = False
        self.assertSchemaError(
            document, schema, v,
            errors.ERROR_UNKNOWN_RULE % ('unknown_rule', field)
        )
        self.assertSchemaError(
            document, schema, None,
            errors.ERROR_UNKNOWN_RULE % ('unknown_rule', field)
        )

    def test_allow_empty_strings(self):
        field = 'test'
        schema = {field: {'type': 'string'}}
        document = {field: ''}
        self.assertSuccess(document, schema)
        schema[field]['empty'] = False
        self.assertFail(document, schema)
        self.assertError(field, errors.ERROR_EMPTY_NOT_ALLOWED)
        schema[field]['empty'] = True
        self.assertSuccess(document, schema)

    def test_ignore_none_values(self):
        field = 'test'
        schema = {field: {'type': 'string', 'empty': False, 'required': False}}
        document = {field: None}

        # Test normal behaviour
        v = Validator(schema, ignore_none_values=False)
        self.assertFail(schema=schema, document=document, validator=v)
        schema[field]['required'] = True
        self.assertFail(schema=schema, document=document, validator=v)
        self.assertNoError(field, errors.ERROR_REQUIRED_FIELD, validator=v)

        # Test ignore None behaviour
        v = Validator(schema, ignore_none_values=True)
        schema[field]['required'] = False
        self.assertSuccess(schema=schema, document=document, validator=v)
        schema[field]['required'] = True
        self.assertFail(schema=schema, document=document, validator=v)
        self.assertError(field, errors.ERROR_REQUIRED_FIELD, validator=v)
        self.assertNoError(
            field,
            errors.ERROR_BAD_TYPE % 'string', validator=v
        )

    def test_unknown_keys(self):
        document = {"unknown1": True, "unknown2": "yes"}
        schema = {'a_field': {'type': 'string'}}
        v = Validator(allow_unknown=True)
        self.assertSuccess(schema=schema, document=document, validator=v)

    def test_novalidate_noerrors(self):
        '''In v0.1.0 and below `self.errors` raised an exception if no
        validation had been performed yet.
        '''
        self.assertEqual(self.validator.errors, {})

    def test_callable_validator(self):
        ''' Validator instance is callable, functions as a shorthand
        passthrough to validate()
        '''
        schema = {'test_field': {'type': 'string'}}
        v = Validator(schema)
        self.assertTrue(v.validate({'test_field': 'foo'}))
        self.assertTrue(v({'test_field': 'foo'}))
        self.assertFalse(v.validate({'test_field': 1}))
        self.assertFalse(v({'test_field': 1}))

    def test_dependencies_field(self):
        schema = {'test_field': {'dependencies': 'foo'}, 'foo': {'type':
                                                                 'string'}}
        v = Validator(schema)

        self.assertTrue(v.validate({'test_field': 'foobar', 'foo': 'bar'}))
        self.assertFalse(v.validate({'test_field': 'foobar'}))

    def test_dependencies_list(self):
        schema = {
            'test_field': {'dependencies': ['foo', 'bar']},
            'foo': {'type': 'string'},
            'bar': {'type': 'string'}
        }
        v = Validator(schema)

        self.assertTrue(v.validate({'test_field': 'foobar', 'foo': 'bar',
                                    'bar': 'foo'}))
        self.assertFalse(v.validate({'test_field': 'foobar', 'foo': 'bar'}))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Cerberus documentation build configuration file, created by
# sphinx-quickstart on Thu Oct 11 15:52:25 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Cerberus'
copyright = u'2012-2014, Nicola Iarocci'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = __import__('cerberus').__version__
# The short X.Y version.
version = release.split('-dev')[0]

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Cerberusdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Cerberus.tex', u'Cerberus Documentation',
   u'Nicola Iarocci', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cerberus', u'Cerberus Documentation',
     [u'Nicola Iarocci'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Cerberus', u'Cerberus Documentation',
   u'Nicola Iarocci', 'Cerberus', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
