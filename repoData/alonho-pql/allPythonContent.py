__FILENAME__ = aggregation_tests
from unittest import TestCase
from bson import SON
import pymongo
import pql

class PqlAggregationTest(TestCase):

    def compare(self, expression, expected):
        self.assertEqual(pql.AggregationParser().parse(expression), expected)

class PqlAggregationPipesTest(PqlAggregationTest):

    def test_match(self):
        self.assertEqual(pql.match('a == 1'), [{'$match': {'a': 1}}])
    
    def test_group(self):
        for group_func in pql.AggregationGroupParser.GROUP_FUNCTIONS:
            self.assertEqual(pql.group(_id='foo', total=group_func + '(bar)'),
                             [{'$group': {'_id': '$foo', 'total': {'$' + group_func: '$bar'}}}])

    def test_invalid_group(self):
        with self.assertRaises(pql.ParseError):
            pql.group(_id='foo', total='bar(1)')
        with self.assertRaises(pql.ParseError):
            pql.group(_id='foo', total='min(1, 2)')

    def test_project(self):
        self.assertEqual(pql.project(foo='bar', a='b + c'),
                         [{'$project': {'foo': '$bar', 'a': {'$add': ['$b', '$c']}}}])

    def test_skip(self):
        self.assertEqual(pql.skip(3), [{'$skip': 3}])

    def test_limit(self):
        self.assertEqual(pql.limit(2), [{'$limit': 2}])

    def test_unwind(self):
        self.assertEqual(pql.unwind('foo'), [{'$unwind': '$foo'}])

    def test_sort(self):
        self.assertEqual(pql.sort('a'), [{'$sort': SON([('a', pymongo.ASCENDING)])}])
        self.assertEqual(pql.sort(['a', '-b', '+c']),
                         [{'$sort': SON([('a', pymongo.ASCENDING),
                                         ('b', pymongo.DESCENDING),
                                         ('c', pymongo.ASCENDING)])}])

class PqlAggregationDataTypesTest(PqlAggregationTest):

    def test_bool(self):
        self.compare('True', True)
        self.compare('true', True)
        self.compare('False', False)
        self.compare('false', False)
        self.compare('None', None)
        self.compare('null', None)

class PqlAggregationSimpleProjectionTest(PqlAggregationTest):

    def test(self):
        self.compare('a', '$a')

    def test_nested(self):
        self.compare('a.b.c', '$a.b.c')

class PqlAggregationLogicTest(PqlAggregationTest):

    def test_and(self):
        self.compare('a and b', {'$and': ['$a', '$b']})

    def test_or(self):
        self.compare('a or b', {'$or': ['$a', '$b']})

    def test_not(self):
        self.compare('not a', {'$not': '$a'})

class PqlAggregationBoolTest(PqlAggregationTest):

    def test_cmp(self):
        self.compare('cmp(a, "bar")', {'$cmp': ['$a', 'bar']})

    def test_eq(self):
        self.compare('a == 0', {'$eq': ['$a', 0]})

    def test_gt(self):
        self.compare('a > 0', {'$gt': ['$a', 0]})

    def test_gte(self):
        self.compare('a >= 0', {'$gte': ['$a', 0]})

    def test_lt(self):
        self.compare('a < 0', {'$lt': ['$a', 0]})

    def test_lte(self):
        self.compare('a <= 0', {'$lte': ['$a', 0]})

    def test_ne(self):
        self.compare('a != 0', {'$ne': ['$a', 0]})

class PqlAggregationArithmicTest(PqlAggregationTest):
    
    def test_add(self):
        self.compare('a + 1', {'$add': ['$a', 1]})
        
    def test_divide(self):
        self.compare('a / 1', {'$divide': ['$a', 1]})

    def test_mod(self):
        self.compare('a % 1', {'$mod': ['$a', 1]})

    def test_multiply(self):
        self.compare('a * 1', {'$multiply': ['$a', 1]})

    def test_subtract(self):
        self.compare('a - 1', {'$subtract': ['$a', 1]})

class PqlAggregationStringTest(PqlAggregationTest):

    def test_concat(self):
        self.compare('concat("foo", "bar", b)', {'$concat': ['foo', 'bar', '$b']})

    def test_strcasecmp(self):
        self.compare('strcasecmp("foo", b)', {'$strcasecmp': ['foo', '$b']})

    def test_substr(self):
        self.compare('substr("foo", 1, 2)', {'$substr': ['foo', 1, 2]})

    def test_toLower(self):
        self.compare('toLower(a)', {'$toLower': ['$a']})

    def test_toUpper(self):
        self.compare('toUpper(a)', {'$toUpper': ['$a']})

class PqlAggregationDateTest(PqlAggregationTest):
    def test(self):
        for func in ['dayOfYear', 'dayOfMonth', 'dayOfWeek',
                     'year', 'month', 'week',
                     'hour', 'minute', 'second', 'millisecond']:
            self.compare('{0}(a)'.format(func), {'${0}'.format(func): ['$a']})

class PqlConditionTest(PqlAggregationTest):
    def test_if(self):
        self.compare('a if b > 3 else c', {'$cond': [{'$gt': ['$b', 3]}, '$a', '$c']})

    def test_if_null(self):
        self.compare('ifnull(a + b, 100)', {'$ifnull': [{'$add': ['$a', '$b']}, 100]})
    
class PqlAggregationSanityTest(PqlAggregationTest):
    def test(self):
        self.compare('a + b / c - 3 * 4 == 1',
                     {'$eq': [
                         {'$subtract': [{'$add': ['$a', {'$divide': ['$b', '$c']}]},
                                        {'$multiply': [3, 4]}]},
                         1]})

class PqlAggregationErrorsTest(PqlAggregationTest):
    def test_invalid_num_args(self):
        with self.assertRaises(pql.ParseError):
            self.compare('ifnull(1)', None)
        with self.assertRaises(pql.ParseError):
            self.compare('ifnull()', None)

    def test_invalid_func(self):
        with self.assertRaises(pql.ParseError):
            self.compare('foo(10)', None)

    def test_invalid_comparators(self):
        with self.assertRaises(pql.ParseError):
            self.compare('1 < a < 3', None)

########NEW FILE########
__FILENAME__ = find_tests
from datetime import datetime
from dateutil.parser import parse as parse_date
from unittest import TestCase
import bson
import pql

class BasePqlTestCase(TestCase):

    def compare(self, string, expected):
        print string, '|', expected
        self.assertEqual(pql.find(string), expected)

class PqlSchemaLessTestCase(BasePqlTestCase):

    def test_hyphenated(self):
        self.compare('"foo-bar" == "spam"', {'foo-bar': 'spam'})

    def test_equal_int(self):
        self.compare('a == 1', {'a': 1})

    def test_not_equal_string(self):
        self.compare('a != "foo"', {'a': {'$ne': 'foo'}})

    def test_nested(self):
        self.compare('a.b == 1', {'a.b': 1})

    def test_and(self):
        self.compare('a == 1 and b == 2', {'$and': [{'a': 1}, {'b': 2}]})

    def test_or(self):
        self.compare('a == 1 or b == 2', {'$or': [{'a': 1}, {'b': 2}]})

    def test_not(self):
        self.compare('not a > 1', {'a': {'$not': {'$gt': 1}}})

    def test_algebra(self):
        for string, expected in [('a > 1', {'a': {'$gt': 1}}),
                                 ('a >= 1', {'a': {'$gte': 1}}),
                                 ('a < 1', {'a': {'$lt': 1}}),
                                 ('a <= 1', {'a': {'$lte': 1}})]:
            self.compare(string, expected)

    def test_bool(self):
        self.compare('a == True', {'a': True})
        self.compare('a == False', {'a': False})

    def test_none(self):
        self.compare('a == None', {'a': None})
        self.compare('a == null', {'a': None})

    def test_list(self):
        self.compare('a == [1, 2, 3]', {'a': [1, 2, 3]})

    def test_dict(self):
        self.compare('a == {"foo": 1}', {'a': {'foo': 1}})

    def test_in(self):
        self.compare('a in [1, 2, 3]', {'a': {'$in': [1, 2, 3]}})

        with self.assertRaises(pql.ParseError) as context:
            pql.find('a in (1)')

        self.assertIn('Invalid value type', str(context.exception))

    def test_not_in(self):
        self.compare('a not in [1, 2, 3]', {'a': {'$nin': [1, 2, 3]}})

        with self.assertRaises(pql.ParseError) as context:
            pql.find('a not in (1)')

        self.assertIn('Invalid value type', str(context.exception))

    def test_missing_func(self):
        with self.assertRaises(pql.ParseError) as context:
            pql.find('a == foo()')
        self.assertIn('Unsupported function', str(context.exception))

    def test_invalid_name(self):
        with self.assertRaises(pql.ParseError) as context:
            pql.find('a == foo')
        self.assertIn('Invalid name', str(context.exception))

    def test_exists(self):
        self.compare('a == exists(True)', {'a': {'$exists': True}})

    def test_type(self):
        self.compare('a == type(3)', {'a': {'$type': 3}})

    def test_regex(self):
        self.compare('a == regex("foo")', {'a': {'$regex': 'foo'}})
        self.compare('a == regex("foo", "i")', {'a': {'$regex': 'foo', '$options': 'i'}})

    def test_mod(self):
        self.compare('a == mod(10, 3)', {'a': {'$mod': [10, 3]}})

    def test_size(self):
        self.compare('a == size(4)', {'a': {'$size': 4}})

    def test_all(self):
        self.compare('a == all([1, 2, 3])', {'a': {'$all': [1, 2, 3]}})

    def test_match(self):
        self.compare('a == match({"foo": "bar"})', {'a': {'$elemMatch': {'foo': 'bar'}}})

    def test_date(self):
        self.compare('a == date(10)', {'a': datetime.fromtimestamp(10)})
        self.compare('a == date("2012-3-4")', {'a': datetime(2012, 3, 4)})
        self.compare('a == date("2012-3-4 12:34:56.123")',
                     {'a': datetime(2012, 3, 4, 12, 34, 56, 123000)})

    def test_epoch(self):
        self.compare('a == epoch(10)', {'a': 10})
        self.compare('a == epoch("2012")', {'a': float(parse_date("2012").strftime('%s.%f'))})

    def test_epoch_utc(self):
        self.compare('a == epoch_utc(10)', {'a': 10})
        self.compare('a == epoch_utc("2012")', {'a': 1326844800})

    def test_id(self):
        self.compare('_id == id("abcdeabcdeabcdeabcdeabcd")',
                     {'_id': bson.ObjectId("abcdeabcdeabcdeabcdeabcd")})

    def test_near_legacy_coordinates(self):
        self.compare('location == near([1, 2], 10)',
                     {'location':
                      {'$near': [1,2],
                       '$maxDistance': 10}})

    def test_near_sphere_point(self):
        self.compare('location == nearSphere(Point(1, 2))',
                     {'location':
                      {'$nearSphere':
                       {'$geometry':
                        {'type': 'Point',
                         'coordinates': [1, 2]}}}})

    def test_near_point_with_max(self):
        self.compare('location == near(Point(1, 2), 10)',
                     {'location':
                      {'$near':
                       {'$geometry':
                        {'type': 'Point',
                         'coordinates': [1, 2]},
                        '$maxDistance': 10}}})

    def test_geo_within_polygon(self):
        self.compare('location == geoWithin(Polygon([[1, 2], [3, 4]]))',
                     {'location':
                      {'$geoWithin':
                       {'$geometry':
                        {'type': 'Polygon',
                         'coordinates': [[1, 2], [3, 4]]}}}})

    def test_geo_intersects_line_string(self):
        self.compare('location == geoIntersects(LineString([[1, 2], [3, 4]]))',
                     {'location':
                      {'$geoIntersects':
                       {'$geometry':
                        {'type': 'LineString',
                         'coordinates': [[1, 2], [3, 4]]}}}})

    def test_center_within(self):
        for center_type in ['center', 'centerSphere']:
            self.compare('location == geoWithin({}([1, 2], 3))'.format(center_type),
                         {'location':
                          {'$geoWithin':
                           {'$' + center_type: [[1, 2], 3]}}})

    def test_polygon_and_box(self):
        for shape in ['box', 'polygon']:
            self.compare('location == geoWithin({}([[1, 2], [3, 4], [5, 6]]))'.format(shape),
                         {'location':
                          {'$geoWithin':
                           {'$' + shape: [[1, 2], [3, 4], [5, 6]]}}})

class PqlSchemaAwareTestCase(BasePqlTestCase):

    def compare(self, string, expected):
        print string, '|', expected
        self.assertEqual(pql.find(string, schema={'a': pql.IntField(),
                                                  'd': pql.DateTimeField(),
                                                  'foo.bar': pql.ListField(pql.StringField())}), expected)

    def test_sanity(self):
        self.compare('a == 3', {'a': 3})

    def test_invalid_field(self):
        with self.assertRaises(pql.ParseError) as context:
            self.compare('b == 3', None)
        self.assertEqual(sorted(context.exception.options),
                         sorted(['a', 'd', 'foo.bar']))

    def test_type_error(self):
        with self.assertRaises(pql.ParseError):
            self.compare('a == "foo"', None)

    def test_invalid_function(self):
        with self.assertRaises(pql.ParseError) as context:
            self.compare('a == size(3)', None)
        self.assertIn('Unsupported function', str(context.exception))

    def test_invalid_date(self):
        with self.assertRaises(pql.ParseError) as context:
            self.compare('d == "foo"', None)
        self.assertIn('Error parsing date', str(context.exception))

    def test_date(self):
        self.compare('d > "2012-03-02"',
                     {'d': {'$gt': datetime(2012, 3, 2)}})

    def test_nested(self):
        self.compare('foo.bar == ["spam"]', {'foo.bar': ['spam']})
        #self.compare('foo.bar == "spam"', {'foo.bar': 'spam'}) # currently broken

########NEW FILE########
__FILENAME__ = aggregation
'''
TODO:

optimize adds, multiplies, 'or' and 'and' as they can accept more than two values
validate type info on specific functions
'''
from .matching import AstHandler, ParseError, DateTimeFunc

class AggregationParser(AstHandler):

    FUNC_TO_ARGS = {'concat': '+', # more than 1
                    'strcasecmp': 2,
                    'substr': 3,
                    'toLower': 1,
                    'toUpper': 1,

                    'dayOfYear': 1,
                    'dayOfMonth': 1,
                    'dayOfWeek': 1,
                    'year': 1,
                    'month': 1,
                    'week': 1,
                    'hour': 1,
                    'minute': 1,
                    'second': 1,
                    'millisecond': 1,
                    
                    'date': 1,

                    'cmp': 2,

                    'ifnull': 2}

    SPECIAL_VALUES = {'False': False,
                      'false': False,
                      'True': True,
                      'true': True,
                      'None': None,
                      'null': None}
    
    def handle_Str(self, node):
        return node.s

    def handle_Num(self, node):
        return node.n

    def handle_Name(self, node):
        return self.SPECIAL_VALUES.get(node.id, '$' + node.id)

    def handle_Attribute(self, node):
        return '${0}.{1}'.format(self.handle(node.value), node.attr).replace('$$', '$')

    def handle_UnaryOp(self, op):
        return {self.handle(op.op): self.handle(op.operand)}

    def handle_IfExp(self, op):
        return {'$cond': [self.handle(op.test),
                          self.handle(op.body),
                          self.handle(op.orelse)]}

    def handle_Call(self, node):
        name = node.func.id
        if name == 'date':
            return DateTimeFunc().handle_date(node)
        if name not in self.FUNC_TO_ARGS:
            raise ParseError('Unsupported function ({0}).'.format(name),
                             col_offset=node.col_offset)
        if len(node.args) != self.FUNC_TO_ARGS[name] and \
           self.FUNC_TO_ARGS[name] != '+' or len(node.args) == 0:
            raise ParseError('Invalid number of arguments to function {0}'.format(name),
                             col_offset=node.col_offset)

        # because of SERVER-9289 the following fails: {'$year': {'$add' :['$time_stamp', 1]}}
        # wrapping both single arg functions in a list solves it: {'$year': [{'$add' :['$time_stamp', 1]}]}
        return {'$' + node.func.id: list(map(self.handle, node.args))}

    def handle_BinOp(self, node):
        return {self.handle(node.op): [self.handle(node.left),
                                       self.handle(node.right)]}

    def handle_Not(self, not_node):
        return '$not'

    def handle_And(self, op):
        return '$and'

    def handle_Or(self, op):
        return '$or'

    def handle_BoolOp(self, op):
        return {self.handle(op.op): list(map(self.handle, op.values))}

    def handle_Compare(self, node):
        if len(node.ops) != 1:
            raise ParseError('Invalid number of comparators: {0}'.format(len(node.ops)),
                             col_offset=node.comparators[1].col_offset)
        return {self.handle(node.ops[0]): [self.handle(node.left),
                                           self.handle(node.comparators[0])]}

    def handle_Gt(self, node):
        return '$gt'
        
    def handle_Lt(self,node):
        return '$lt'
        
    def handle_GtE(self, node):
        return '$gte'
        
    def handle_LtE(self, node):
        return '$lte'

    def handle_Eq(self, node):
        return '$eq'
        
    def handle_NotEq(self, node):
        return '$ne'

    def handle_Add(self, node):
        return '$add'

    def handle_Sub(self, node):
        return '$subtract'

    def handle_Mod(self, node):
        return '$mod'

    def handle_Mult(self, node):
        return '$multiply'

    def handle_Div(self, node):
        return '$divide'

class AggregationGroupParser(AstHandler):
    GROUP_FUNCTIONS = ['addToSet', 'push', 'first', 'last',
                       'max', 'min', 'avg', 'sum']
    def handle_Call(self, node):
        if len(node.args) != 1:
            raise ParseError('The {0} group aggregation function accepts one argument'.format(node.func.id),
                             col_offset=node.col_offset)
        if node.func.id not in self.GROUP_FUNCTIONS:
            raise ParseError('Unsupported group function: {0}'.format(node.func.id),
                             col_offset=node.col_offset,
                             options=self.GROUP_FUNCTIONS)
        return {'$' + node.func.id: AggregationParser().handle(node.args[0])}


########NEW FILE########
__FILENAME__ = matching
"""
The parser:
1. gets and expression
2. parses it
3. handles all boolean logic
4. delegates operator and rvalue parsing to the OperatorMap

SchemaFreeOperatorMap

  supports all mongo operators for all fields.

SchemaAwareOperatorMap

  1. verifies fields exist.
  2. verifies operators are applied to fields of correct type.

currently unsupported:
1. $where - kind of intentionally against injections
2. geospatial
"""
import ast
import bson
import datetime
import dateutil.parser
from calendar import timegm


def parse_date(node):
    if hasattr(node, 'n'): # it's a number!
        return datetime.datetime.fromtimestamp(node.n)
    try:
        return dateutil.parser.parse(node.s)
    except Exception as e:
        raise ParseError('Error parsing date: ' + str(e), col_offset=node.col_offset)

class AstHandler(object):

    def get_options(self):
        return [f.replace('handle_', '') for f in dir(self) if f.startswith('handle_')]

    def resolve(self, thing):
        thing_name = thing.__class__.__name__
        try:
            handler = getattr(self, 'handle_' + thing_name)
        except AttributeError:
            raise ParseError('Unsupported syntax ({0}).'.format(thing_name,
                                                              self.get_options()),
                             col_offset=thing.col_offset if hasattr(thing, 'col_offset') else None,
                             options=self.get_options())
        return handler

    def handle(self, thing):
        return self.resolve(thing)(thing)

    def parse(self, string):
        ex = ast.parse(string, mode='eval')
        return self.handle(ex.body)

class ParseError(Exception):
    def __init__(self, message, col_offset, options=[]):
        super(ParseError, self).__init__(message)
        self.message = message
        self.col_offset = col_offset
        self.options = options
    def __str__(self):
        if self.options:
            return '{0} options: {1}'.format(self.message, self.options)
        return self.message

class Parser(AstHandler):
    def __init__(self, operator_map):
        self._operator_map = operator_map

    def get_options(self):
        return self._operator_map.get_options()

    def handle_BoolOp(self, op):
        return {self.handle(op.op): list(map(self.handle, op.values))}

    def handle_And(self, op):
        '''and'''
        return '$and'

    def handle_Or(self, op):
        '''or'''
        return '$or'

    def handle_UnaryOp(self, op):
        operator = self.handle(op.operand)
        field, value = list(operator.items())[0]
        return {field: {self.handle(op.op): value}}

    def handle_Not(self, not_node):
        '''not'''
        return '$not'

    def handle_Compare(self, compare):
        if len(compare.comparators) != 1:
            raise ParseError('Invalid number of comparators: {0}'.format(len(compare.comparators)),
                             col_offset=compare.comparators[1].col_offset)
        return self._operator_map.handle(left=compare.left,
                                         operator=compare.ops[0],
                                         right=compare.comparators[0])

class SchemaFreeParser(Parser):
    def __init__(self):
        super(SchemaFreeParser, self).__init__(SchemaFreeOperatorMap())

class SchemaAwareParser(Parser):
    def __init__(self, *a, **k):
        super(SchemaAwareParser, self).__init__(SchemaAwareOperatorMap(*a, **k))

class FieldName(AstHandler):
    def handle_Str(self, node):
        return node.s
    def handle_Name(self, name):
        return name.id
    def handle_Attribute(self, attr):
        return '{0}.{1}'.format(self.handle(attr.value), attr.attr)

class OperatorMap(object):
    def resolve_field(self, node):
        return FieldName().handle(node)
    def handle(self, operator, left, right):
        field = self.resolve_field(left)
        return {field: self.resolve_type(field).handle_operator_and_right(operator, right)}

class SchemaFreeOperatorMap(OperatorMap):
    def get_options(self):
        return None
    def resolve_type(self, field):
        return GenericField()

class SchemaAwareOperatorMap(OperatorMap):
    def __init__(self, field_to_type):
        self._field_to_type = field_to_type
    def resolve_field(self, node):
        field = super(SchemaAwareOperatorMap, self).resolve_field(node)
        try:
            self._field_to_type[field]
        except KeyError:
            raise ParseError('Field not found: {0}.'.format(field),
                             col_offset=node.col_offset,
                             options=self._field_to_type.keys())
        return field

    def resolve_type(self, field):
        return self._field_to_type[field]

#---Function-Handlers---#

class Func(AstHandler):

    @staticmethod
    def get_arg(node, index):
        if index > len(node.args) - 1:
            raise ParseError('Missing argument in {0}.'.format(node.func.id),
                             col_offset=node.col_offset)
        return node.args[index]

    @staticmethod
    def parse_arg(node, index, field):
        return field.handle(Func.get_arg(node, index))

    def handle(self, node):
        try:
            handler = getattr(self, 'handle_' + node.func.id)
        except AttributeError:
            raise ParseError('Unsupported function ({0}).'.format(node.func.id),
                             col_offset=node.col_offset,
                             options=self.get_options())
        return handler(node)

    def handle_exists(self, node):
        return {'$exists': self.parse_arg(node, 0, BoolField())}

    def handle_type(self, node):
        return {'$type': self.parse_arg(node, 0, IntField())}

class StringFunc(Func):
    def handle_regex(self, node):
        result = {'$regex': self.parse_arg(node, 0, StringField())}
        try:
            result['$options'] = self.parse_arg(node, 1, StringField())
        except ParseError:
            pass
        return result

class IntFunc(Func):
    def handle_mod(self, node):
        return {'$mod': [self.parse_arg(node, 0, IntField()),
                         self.parse_arg(node, 1, IntField())]}

class ListFunc(Func):
    def handle_size(self, node):
        return {'$size': self.parse_arg(node, 0, IntField())}

    def handle_all(self, node):
        return {'$all': self.parse_arg(node, 0, ListField())}

    def handle_match(self, node):
        return {'$elemMatch': self.parse_arg(node, 0, DictField())}

class DateTimeFunc(Func):
    def handle_date(self, node):
        return parse_date(self.get_arg(node, 0))

class IdFunc(Func):
    def handle_id(self, node):
        return self.parse_arg(node, 0, IdField())

class EpochFunc(Func):
    def handle_epoch(self, node):
        return self.parse_arg(node, 0, EpochField())

class EpochUTCFunc(Func):
    def handle_epoch_utc(self, node):
        return self.parse_arg(node, 0, EpochUTCField())

class GeoShapeFuncParser(Func):

    def handle_Point(self, node):
        return {'$geometry':
                {'type': 'Point',
                 'coordinates': [self.parse_arg(node, 0, IntField()),
                                                  self.parse_arg(node, 1, IntField())]}}

    def handle_LineString(self, node):
        return {'$geometry':
                {'type': 'LineString',
                 'coordinates': self.parse_arg(node, 0, ListField(ListField(IntField())))}}

    def handle_Polygon(self, node):
        return {'$geometry':
                {'type': 'Polygon',
                'coordinates': self.parse_arg(node, 0, ListField(ListField(IntField())))}}

    def handle_box(self, node):
        return {'$box': self.parse_arg(node, 0, ListField(ListField(IntField())))}

    def handle_polygon(self, node):
        return {'$polygon': self.parse_arg(node, 0, ListField(ListField(IntField())))}

    def _any_center(self, node, center_name):
        return {center_name: [self.parse_arg(node, 0, ListField(IntField())),
                              self.parse_arg(node, 1, IntField())]}

    def handle_center(self, node):
        return self._any_center(node, '$center')

    def handle_centerSphere(self, node):
        return self._any_center(node, '$centerSphere')

class GeoShapeParser(AstHandler):
    def handle_Call(self, node):
        return GeoShapeFuncParser().handle(node)
    def handle_List(self, node):
        '''
        This is a legacy coordinate pair. consider supporting box, polygon, center, centerSphere
        '''
        return ListField(IntField()).handle(node)

class GeoFunc(Func):
    def _any_near(self, node, near_name):
        shape = GeoShapeParser().handle(self.get_arg(node, 0))
        result = bson.SON({near_name: shape}) # use SON because mongo expects the command before the arguments
        if len(node.args) > 1:
            distance = self.parse_arg(node, 1, IntField()) # meters
            if isinstance(shape, list): # legacy coordinate pair
                result['$maxDistance'] = distance
            else:
                shape['$maxDistance'] = distance
        return result

    def handle_near(self, node):
        return self._any_near(node, '$near')

    def handle_nearSphere(self, node):
        return self._any_near(node, '$nearSphere')

    def handle_geoIntersects(self, node):
        return {'$geoIntersects': GeoShapeParser().handle(self.get_arg(node, 0))}

    def handle_geoWithin(self, node):
        return {'$geoWithin': GeoShapeParser().handle(self.get_arg(node, 0))}

class GenericFunc(StringFunc, IntFunc, ListFunc, DateTimeFunc,
                  IdFunc, EpochFunc, EpochUTCFunc, GeoFunc):
    pass

#---Operators---#

class Operator(AstHandler):
    def __init__(self, field):
        self.field = field
    def handle_Eq(self, node):
        '''=='''
        return self.field.handle(node)
    def handle_NotEq(self, node):
        '''!='''
        return {'$ne': self.field.handle(node)}
    def handle_In(self, node):
        '''in'''
        try:
            elts = node.elts
        except AttributeError:
            raise ParseError('Invalid value type for `in` operator: {0}'.format(node.__class__.__name__),
                             col_offset=node.col_offset)
        return {'$in': list(map(self.field.handle, elts))}
    def handle_NotIn(self, node):
        '''not in'''
        try:
            elts = node.elts
        except AttributeError:
            raise ParseError('Invalid value type for `not in` operator: {0}'.format(node.__class__.__name__),
                             col_offset=node.col_offset)
        return {'$nin': list(map(self.field.handle, elts))}

class AlgebricOperator(Operator):
    def handle_Gt(self, node):
        '''>'''
        return {'$gt': self.field.handle(node)}
    def handle_Lt(self,node):
        '''<'''
        return {'$lt': self.field.handle(node)}
    def handle_GtE(self, node):
        '''>='''
        return {'$gte': self.field.handle(node)}
    def handle_LtE(self, node):
        '''<='''
        return {'$lte': self.field.handle(node)}

#---Field-Types---#

class Field(AstHandler):
    OP_CLASS = Operator

    SPECIAL_VALUES = {'None': None,
                      'null': None}
    def handle_Name(self, node):
        try:
            return self.SPECIAL_VALUES[node.id]
        except KeyError:
            raise ParseError('Invalid name: {0}'.format(node.id), node.col_offset, options=list(self.SPECIAL_VALUES))

    def handle_operator_and_right(self, operator, right):
        return self.OP_CLASS(self).resolve(operator)(right)

class GeoField(Field):
    def handle_Call(self, node):
        return GeoFunc().handle(node)

class AlgebricField(Field):
    OP_CLASS = AlgebricOperator

class StringField(AlgebricField):
    def handle_Call(self, node):
        return StringFunc().handle(node)
    def handle_Str(self, node):
        return node.s

class IntField(AlgebricField):
    def handle_Num(self, node):
        return node.n
    def handle_Call(self, node):
        return IntFunc().handle(node)

class BoolField(Field):
    SPECIAL_VALUES = dict(Field.SPECIAL_VALUES,
                          **{'False': False,
                             'True': True,
                             'false': False,
                             'true': True})

class ListField(Field):
    def __init__(self, field=None):
        self._field = field
    def handle_List(self, node):
        return list(map((self._field or GenericField()).handle, node.elts))
    def handle_Call(self, node):
        return ListFunc().handle(node)

class DictField(Field):
    def __init__(self, field=None):
        self._field = field
    def handle_Dict(self, node):
        return dict((StringField().handle(key), (self._field or GenericField()).handle(value))
                    for key, value in zip(node.keys, node.values))

class DateTimeField(AlgebricField):
    def handle_Str(self, node):
        return parse_date(node)
    def handle_Num(self, node):
        return parse_date(node)
    def handle_Call(self, node):
        return DateTimeFunc().handle(node)

class EpochField(AlgebricField):
    def handle_Str(self, node):
        return float(parse_date(node).strftime('%s.%f'))
    def handle_Num(self, node):
        return node.n
    def handle_Call(self, node):
        return EpochFunc().handle(node)

class EpochUTCField(AlgebricField):
    def handle_Str(self, node):
        return timegm(parse_date(node).timetuple())
    def handle_Num(self, node):
        return node.n
    def handle_Call(self, node):
        return EpochUTCFunc().handle(node)

class IdField(AlgebricField):
    def handle_Str(self, node):
        return bson.ObjectId(node.s)
    def handle_Call(self, node):
        return IdFunc().handle(node)

class GenericField(IntField, BoolField, StringField, ListField, DictField, GeoField):
    def handle_Call(self, node):
        return GenericFunc().handle(node)

########NEW FILE########
