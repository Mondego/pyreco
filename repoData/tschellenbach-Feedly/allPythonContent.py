__FILENAME__ = base_bench
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DJANGO_SETTINGS_MODULE"] = "conf"
from feedly.utils.timing import timer
import logging
from feedly.activity import Activity
from feedly.feeds.cassandra import CassandraFeed
from feedly.feeds.aggregated_feed.cassandra import CassandraAggregatedFeed
from feedly.feed_managers.base import Feedly
from feedly.feed_managers.base import FanoutPriority
from feedly.verbs.base import Love
from optparse import OptionParser


logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(handler)


def parse_options():
    parser = OptionParser()
    parser.add_option('-l', '--log-level', default='warning',
                      help='logging level: debug, info, warning, or error')
    parser.add_option('-p', '--profile', action='store_true', dest='profile',
                      help='Profile the run')
    options, args = parser.parse_args()
    logger.setLevel(options.log_level.upper())
    return options, args


class FashiolistaFeed(CassandraFeed):
    timeline_cf_name = 'timeline_flat'
    key_format = 'feed:flat:%(user_id)s'
    max_length = 3600

    def trim(self, *args, **kwargs):
        pass


class UserFeed(CassandraFeed):
    timeline_cf_name = 'timeline_personal'
    key_format = 'feed:personal:%(user_id)s'
    max_length = 10 ** 6


class AggregatedFeed(CassandraAggregatedFeed):
    timeline_cf_name = 'timeline_aggregated'
    key_format = 'feed:aggregated:%(user_id)s'
    lock_format = 'feed:aggregated:lock:%(user_id)s'
    max_length = 2400
    merge_max_length = 1


class BenchFeedly(Feedly):
    feed_classes = {
        'aggregated': AggregatedFeed,
        'flat': FashiolistaFeed
    }
    user_feed_class = UserFeed
    follow_activity_limit = 360
    fanout_chunk_size = 100

    def add_entry(self, user_id, activity_id):
        verb = Love()
        activity = Activity(user_id, verb, activity_id)
        self.add_user_activity(user_id, activity)

    def get_user_follower_ids(self, user_id):
        active_follower_ids = range(100)
        return {FanoutPriority.HIGH: active_follower_ids}


manager = BenchFeedly()


def cassandra_setup():
    from cqlengine.management import create_table, create_keyspace
    aggregated_timeline = AggregatedFeed.get_timeline_storage()
    timeline = FashiolistaFeed.get_timeline_storage()
    user_timeline = UserFeed.get_timeline_storage()
    create_keyspace('test')
    create_table(aggregated_timeline.model)
    create_table(timeline.model)
    create_table(user_timeline.model)


def benchmark():
    benchmark_flat_feed()
    benchmark_aggregated_feed()


def benchmark_flat_feed():
    t = timer()
    manager.feed_classes = {'flat': FashiolistaFeed}
    manager.add_entry(1, 1)
    print "Benchmarking flat feed took: %0.2fs" % t.next()


def benchmark_aggregated_feed():
    t = timer()
    manager.feed_classes = {'aggregated': AggregatedFeed}
    manager.add_entry(1, 1)
    print "Benchmarking aggregated feed took: %0.2fs" % t.next()


if __name__ == '__main__':
    options, args = parse_options()
    cassandra_setup()
    benchmark()

########NEW FILE########
__FILENAME__ = cassandra_feedly

########NEW FILE########
__FILENAME__ = conf
SECRET_KEY = '123456789'

FEEDLY_DEFAULT_KEYSPACE = 'test'

FEEDLY_CASSANDRA_HOSTS = [
    '127.0.0.1', '127.0.0.2', '127.0.0.3'
]

CELERY_ALWAYS_EAGER = True

import djcelery
djcelery.setup_loader()

########NEW FILE########
__FILENAME__ = columns
from cassandra import cqltypes
from copy import copy
from datetime import datetime
from datetime import date
import re
from uuid import uuid1, uuid4

from cqlengine.exceptions import ValidationError


def __escape_quotes(term):
    assert isinstance(term, basestring)
    return term.replace("'", "''")


def cql_quote(term, cql_major_version=3):
    if isinstance(term, unicode):
        return "'%s'" % __escape_quotes(term.encode('utf8'))
    elif isinstance(term, str):
        return "'%s'" % __escape_quotes(str(term))
    elif isinstance(term, bool) and cql_major_version == 2:
        return "'%s'" % str(term)
    else:
        return str(term)


internal_clq_type_mapping = {
    'text': cqltypes.UTF8Type,
    'blob': cqltypes.BytesType,
    'ascii': cqltypes.AsciiType,
    'text': cqltypes.UTF8Type,
    'int': cqltypes.Int32Type,
    'varint': cqltypes.IntegerType,
    'timestamp': cqltypes.DateType,
    'uuid': cqltypes.UUIDType,
    'timeuuid': cqltypes.TimeUUIDType,
    'boolean': cqltypes.BooleanType,
    'double': cqltypes.DoubleType,
}


class BaseValueManager(object):

    def __init__(self, instance, column, value):
        self.instance = instance
        self.column = column
        self.previous_value = copy(value)
        self.value = value

    @property
    def deleted(self):
        return self.value is None and self.previous_value is not None

    @property
    def changed(self):
        """
        Indicates whether or not this value has changed.

        :rtype: boolean

        """
        return self.value != self.previous_value

    def reset_previous_value(self):
        self.previous_value = copy(self.value)

    def getval(self):
        return self.value

    def setval(self, val):
        self.value = val

    def delval(self):
        self.value = None

    def get_property(self):
        _get = lambda slf: self.getval()
        _set = lambda slf, val: self.setval(val)
        _del = lambda slf: self.delval()

        if self.column.can_delete:
            return property(_get, _set, _del)
        else:
            return property(_get, _set)


class ValueQuoter(object):

    """
    contains a single value, which will quote itself for CQL insertion statements
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        raise NotImplementedError

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        return False


class Column(object):

    # the cassandra type this column maps to
    db_type = None

    value_manager = BaseValueManager

    instance_counter = 0

    def __init__(self,
                 primary_key=False,
                 partition_key=False,
                 index=False,
                 db_field=None,
                 default=None,
                 required=False,
                 clustering_order=None):
        """
        :param primary_key: bool flag, indicates this column is a primary key. The first primary key defined
            on a model is the partition key (unless partition keys are set), all others are cluster keys
        :param partition_key: indicates that this column should be the partition key, defining
            more than one partition key column creates a compound partition key
        :param index: bool flag, indicates an index should be created for this column
        :param db_field: the fieldname this field will map to in the database
        :param default: the default value, can be a value or a callable (no args)
        :param required: boolean, is the field required? Model validation will raise and
            exception if required is set to True and there is a None value assigned
        :param clustering_order: only applicable on clustering keys (primary keys that are not partition keys)
            determines the order that the clustering keys are sorted on disk
        """
        self.partition_key = partition_key
        self.primary_key = partition_key or primary_key
        self.index = index
        self.db_field = db_field
        self.default = default
        self.required = required
        self.clustering_order = clustering_order
        # the column name in the model definition
        self.column_name = None

        self.value = None

        # keep track of instantiation order
        self.position = Column.instance_counter
        Column.instance_counter += 1

    def validate(self, value):
        '''
        add extra validation (before cassandra-driver)
        '''
        if value is None:
            if self.has_default:
                value = self.get_default()
            elif self.required:
                value = self.ctype.validate(value)
        return value

    def to_python(self, value):
        '''
        does some extra python-python conversion
        eg. convert a datetime to date for a date column
        '''
        return value

    @property
    def ctype(self):
        '''
        the cassandra type identifier as defined in 
        python cassandra driver
        '''
        return internal_clq_type_mapping[self.db_type]

    @property
    def has_default(self):
        return self.default is not None

    @property
    def is_primary_key(self):
        return self.primary_key

    @property
    def can_delete(self):
        return not self.primary_key

    def get_default(self):
        if self.has_default:
            if callable(self.default):
                return self.default()
            else:
                return self.default

    def get_column_def(self):
        """
        Returns a column definition for CQL table definition
        """
        return '{} {}'.format(self.cql, self.db_type)

    def set_column_name(self, name):
        """
        Sets the column name during document class construction
        This value will be ignored if db_field is set in __init__
        """
        self.column_name = name

    @property
    def db_field_name(self):
        """ Returns the name of the cql name of this column """
        return self.db_field or self.column_name

    @property
    def db_index_name(self):
        """ Returns the name of the cql index """
        return 'index_{}'.format(self.db_field_name)

    @property
    def cql(self):
        return self.get_cql()

    def get_cql(self):
        return '"{}"'.format(self.db_field_name)


class Bytes(Column):
    db_type = 'blob'


class Ascii(Column):
    db_type = 'ascii'


class Text(Column):
    db_type = 'text'

    def __init__(self, *args, **kwargs):
        self.min_length = kwargs.pop(
            'min_length', 1 if kwargs.get('required', False) else None)
        self.max_length = kwargs.pop('max_length', None)
        super(Text, self).__init__(*args, **kwargs)

    def validate(self, value):
        value = super(Text, self).validate(value)
        if value is None:
            return
        if not isinstance(value, (basestring, bytearray)) and value is not None:
            raise ValidationError('{} is not a string'.format(type(value)))
        if self.max_length:
            if len(value) > self.max_length:
                raise ValidationError(
                    '{} is longer than {} characters'.format(self.column_name, self.max_length))
        if self.min_length:
            if len(value) < self.min_length:
                raise ValidationError(
                    '{} is shorter than {} characters'.format(self.column_name, self.min_length))
        return value


class Integer(Column):
    db_type = 'int'


class VarInt(Column):
    db_type = 'varint'


class CounterValueManager(BaseValueManager):

    def __init__(self, instance, column, value):
        super(CounterValueManager, self).__init__(instance, column, value)
        self.value = self.value or 0
        self.previous_value = self.previous_value or 0


class Counter(Integer):
    db_type = 'counter'

    value_manager = CounterValueManager

    def __init__(self,
                 index=False,
                 db_field=None,
                 required=False):
        super(Counter, self).__init__(
            primary_key=False,
            partition_key=False,
            index=index,
            db_field=db_field,
            default=0,
            required=required,
        )

    def get_update_statement(self, val, prev, ctx):
        prev = prev or 0
        field_id = uuid4().hex

        delta = val - prev
        sign = '-' if delta < 0 else '+'
        delta = abs(delta)
        ctx[field_id] = delta
        return ['"{0}" = "{0}" {1} {2}'.format(self.db_field_name, sign, delta)]


class DateTime(Column):
    db_type = 'timestamp'


class Date(Column):
    db_type = 'timestamp'

    def to_python(self, value):
        value = super(Date, self).to_python(value)
        if isinstance(value, datetime):
            return value.date()
        return value


class UUID(Column):

    """
    Type 1 or 4 UUID
    """
    db_type = 'uuid'

    re_uuid = re.compile(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    def validate(self, value):
        val = super(UUID, self).validate(value)
        if val is None:
            return
        from uuid import UUID as _UUID
        if isinstance(val, _UUID):
            return val
        if isinstance(val, basestring) and self.re_uuid.match(val):
            return _UUID(val)
        raise ValidationError("{} is not a valid uuid".format(value))


from uuid import UUID as pyUUID, getnode


class TimeUUID(UUID):

    """
    UUID containing timestamp
    """

    db_type = 'timeuuid'

    @classmethod
    def from_datetime(self, dt):
        """
        generates a UUID for a given datetime

        :param dt: datetime
        :type dt: datetime
        :return:
        """
        global _last_timestamp

        epoch = datetime(1970, 1, 1, tzinfo=dt.tzinfo)

        offset = 0
        if epoch.tzinfo:
            offset_delta = epoch.tzinfo.utcoffset(epoch)
            offset = offset_delta.days * 24 * 3600 + offset_delta.seconds

        timestamp = (dt - epoch).total_seconds() - offset

        node = None
        clock_seq = None

        nanoseconds = int(timestamp * 1e9)
        timestamp = int(nanoseconds // 100) + 0x01b21dd213814000L

        if clock_seq is None:
            import random
            clock_seq = random.randrange(1 << 14L)  # instead of stable storage
        time_low = timestamp & 0xffffffffL
        time_mid = (timestamp >> 32L) & 0xffffL
        time_hi_version = (timestamp >> 48L) & 0x0fffL
        clock_seq_low = clock_seq & 0xffL
        clock_seq_hi_variant = (clock_seq >> 8L) & 0x3fL
        if node is None:
            node = getnode()
        return pyUUID(fields=(time_low, time_mid, time_hi_version,
                              clock_seq_hi_variant, clock_seq_low, node), version=1)


class Boolean(Column):
    db_type = 'boolean'


class Float(Column):
    db_type = 'double'

    def validate(self, value):
        value = super(Float, self).validate(value)
        if value is None:
            return
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError("{} is not a valid float".format(value))


class Decimal(Column):
    db_type = 'decimal'


class BaseContainerColumn(Column):

    """
    Base Container type
    """

    def __init__(self, value_type, **kwargs):
        """
        :param value_type: a column class indicating the types of the value
        """
        inheritance_comparator = issubclass if isinstance(
            value_type, type) else isinstance
        if not inheritance_comparator(value_type, Column):
            raise ValidationError('value_type must be a column class')
        if inheritance_comparator(value_type, BaseContainerColumn):
            raise ValidationError('container types cannot be nested')
        if value_type.db_type is None:
            raise ValidationError(
                'value_type cannot be an abstract column type')

        if isinstance(value_type, type):
            self.value_type = value_type
            self.value_col = self.value_type()
        else:
            self.value_col = value_type
            self.value_type = self.value_col.__class__

        super(BaseContainerColumn, self).__init__(**kwargs)

    def get_column_def(self):
        """
        Returns a column definition for CQL table definition
        """
        db_type = self.db_type.format(self.value_type.db_type)
        return '{} {}'.format(self.db_field_name, db_type)

    def get_update_statement(self, val, prev, ctx):
        """
        Used to add partial update statements
        """
        raise NotImplementedError


class Set(BaseContainerColumn):

    """
    Stores a set of unordered, unique values

    http://www.datastax.com/docs/1.2/cql_cli/using/collections
    """
    db_type = 'set<{}>'

    class Quoter(ValueQuoter):

        def __str__(self):
            cq = cql_quote
            return '{' + ', '.join([cq(v) for v in self.value]) + '}'

    def __init__(self, value_type, strict=True, default=set, **kwargs):
        """
        :param value_type: a column class indicating the types of the value
        :param strict: sets whether non set values will be coerced to set
            type on validation, or raise a validation error, defaults to True
        """
        self.strict = strict

        super(Set, self).__init__(value_type, default=default, **kwargs)

    def validate(self, value):
        val = super(Set, self).validate(value)
        if val is None:
            return
        types = (set,) if self.strict else (set, list, tuple)
        if not isinstance(val, types):
            if self.strict:
                raise ValidationError('{} is not a set object'.format(val))
            else:
                raise ValidationError(
                    '{} cannot be coerced to a set object'.format(val))

        return {self.value_col.validate(v) for v in val}

    def to_python(self, value):
        if value is None:
            return set()
        return {self.value_col.to_python(v) for v in value}

    def get_update_statement(self, val, prev, ctx):
        """
        Returns statements that will be added to an object's update statement
        also updates the query context

        :param val: the current column value
        :param prev: the previous column value
        :param ctx: the values that will be passed to the query
        :rtype: list
        """

        # remove from Quoter containers, if applicable
        if isinstance(val, self.Quoter):
            val = val.value
        if isinstance(prev, self.Quoter):
            prev = prev.value

        if val is None or val == prev:
            # don't return anything if the new value is the same as
            # the old one, or if the new value is none
            return []
        elif prev is None or not any({v in prev for v in val}):
            field = uuid1().hex
            ctx[field] = self.Quoter(val)
            return ['"{}" = {{}}'.format(self.db_field_name, field)]
        else:
            # partial update time
            to_create = val - prev
            to_delete = prev - val
            statements = []

            if to_create:
                field_id = uuid1().hex
                ctx[field_id] = self.Quoter(to_create)
                statements += [
                    '"{0}" = "{0}" + %({1})s'.format(self.db_field_name, field_id)]

            if to_delete:
                field_id = uuid1().hex
                ctx[field_id] = self.Quoter(to_delete)
                statements += [
                    '"{0}" = "{0}" - %({1})s'.format(self.db_field_name, field_id)]

            return statements


class List(BaseContainerColumn):

    """
    Stores a list of ordered values

    http://www.datastax.com/docs/1.2/cql_cli/using/collections_list
    """
    db_type = 'list<{}>'

    class Quoter(ValueQuoter):

        def __str__(self):
            cq = cql_quote
            return '[' + ', '.join([cq(v) for v in self.value]) + ']'

    def __init__(self, value_type, default=set, **kwargs):
        return super(List, self).__init__(value_type=value_type, default=default, **kwargs)

    def validate(self, value):
        val = super(List, self).validate(value)
        if val is None:
            return
        if not isinstance(val, (set, list, tuple)):
            raise ValidationError('{} is not a list object'.format(val))
        return [self.value_col.validate(v) for v in val]

    def to_python(self, value):
        if value is None:
            return []
        return [self.value_col.to_python(v) for v in value]

    def get_update_statement(self, val, prev, values):
        """
        Returns statements that will be added to an object's update statement
        also updates the query context
        """
        # remove from Quoter containers, if applicable
        if isinstance(val, self.Quoter):
            val = val.value
        if isinstance(prev, self.Quoter):
            prev = prev.value

        def _insert():
            field_id = uuid1().hex
            values[field_id] = self.Quoter(val)
            return ['"{}" = {}'.format(self.db_field_name, field_id)]

        if val is None or val == prev:
            return []

        elif prev is None:
            return _insert()

        elif len(val) < len(prev):
            # if elements have been removed,
            # rewrite the whole list
            return _insert()

        elif len(prev) == 0:
            # if we're updating from an empty
            # list, do a complete insert
            return _insert()

        else:
            # the prepend and append lists,
            # if both of these are still None after looking
            # at both lists, an insert statement will be returned
            prepend = None
            append = None

            # the max start idx we want to compare
            search_space = len(val) - max(0, len(prev) - 1)

            # the size of the sub lists we want to look at
            search_size = len(prev)

            for i in range(search_space):
                # slice boundary
                j = i + search_size
                sub = val[i:j]
                idx_cmp = lambda idx: prev[idx] == sub[idx]
                if idx_cmp(0) and idx_cmp(-1) and prev == sub:
                    prepend = val[:i]
                    append = val[j:]
                    break

            # create update statements
            if prepend is append is None:
                return _insert()

            statements = []
            if prepend:
                field_id = uuid1().hex
                # CQL seems to prepend element at a time, starting
                # with the element at idx 0, we can either reverse
                # it here, or have it inserted in reverse
                prepend.reverse()
                values[field_id] = self.Quoter(prepend)
                statements += [
                    '"{0}" = %({1})s + "{0}"'.format(self.db_field_name, field_id)]

            if append:
                field_id = uuid1().hex
                values[field_id] = self.Quoter(append)
                statements += [
                    '"{0}" = "{0}" + %({1})s'.format(self.db_field_name, field_id)]

            return statements


class Map(BaseContainerColumn):

    """
    Stores a key -> value map (dictionary)

    http://www.datastax.com/docs/1.2/cql_cli/using/collections_map
    """

    db_type = 'map<{}, {}>'

    class Quoter(ValueQuoter):

        def __str__(self):
            cq = cql_quote
            return '{' + ', '.join([cq(k) + ':' + cq(v) for k, v in self.value.items()]) + '}'

    def __init__(self, key_type, value_type, default=dict, **kwargs):
        """
        :param key_type: a column class indicating the types of the key
        :param value_type: a column class indicating the types of the value
        """
        inheritance_comparator = issubclass if isinstance(
            key_type, type) else isinstance
        if not inheritance_comparator(key_type, Column):
            raise ValidationError('key_type must be a column class')
        if inheritance_comparator(key_type, BaseContainerColumn):
            raise ValidationError('container types cannot be nested')
        if key_type.db_type is None:
            raise ValidationError('key_type cannot be an abstract column type')

        if isinstance(key_type, type):
            self.key_type = key_type
            self.key_col = self.key_type()
        else:
            self.key_col = key_type
            self.key_type = self.key_col.__class__
        super(Map, self).__init__(value_type, default=default, **kwargs)

    def get_column_def(self):
        """
        Returns a column definition for CQL table definition
        """
        db_type = self.db_type.format(
            self.key_type.db_type,
            self.value_type.db_type
        )
        return '{} {}'.format(self.db_field_name, db_type)

    def validate(self, value):
        val = super(Map, self).validate(value)
        if val is None:
            return
        if not isinstance(val, dict):
            raise ValidationError('{} is not a dict object'.format(val))
        return {self.key_col.validate(k): self.value_col.validate(v) for k, v in val.items()}

    def to_python(self, value):
        if value is None:
            return {}
        if value is not None:
            return {self.key_col.to_python(k): self.value_col.to_python(v) for k, v in value.items()}

    def get_update_statement(self, val, prev, ctx):
        """
        http://www.datastax.com/docs/1.2/cql_cli/using/collections_map#deletion
        """
        # remove from Quoter containers, if applicable
        if isinstance(val, self.Quoter):
            val = val.value
        if isinstance(prev, self.Quoter):
            prev = prev.value
        val = val or {}
        prev = prev or {}

        # get the updated map
        update = {k: v for k, v in val.items() if v != prev.get(k)}

        statements = []
        for k, v in update.items():
            key_id = uuid1().hex
            val_id = uuid1().hex
            ctx[key_id] = k
            ctx[val_id] = v
            statements += ['"{}"[%({})s] = %({})s'.format(self.db_field_name,
                                                          key_id, val_id)]

        return statements

    def get_delete_statement(self, val, prev, ctx):
        """
        Returns statements that will be added to an object's delete statement
        also updates the query context, used for removing keys from a map
        """
        if val is prev is None:
            return []
        if isinstance(val, self.Quoter):
            val = val.value
        if isinstance(prev, self.Quoter):
            prev = prev.value

        old_keys = set(prev.keys()) if prev else set()
        new_keys = set(val.keys()) if val else set()
        del_keys = old_keys - new_keys

        del_statements = []
        for key in del_keys:
            field_id = uuid1().hex
            ctx[field_id] = key
            del_statements += ['"{}"[%({})s]'.format(self.db_field_name,
                                                     field_id)]

        return del_statements


class _PartitionKeysToken(Column):

    """
    virtual column representing token of partition columns.
    Used by filter(pk__token=Token(...)) filters
    """

    def __init__(self, model):
        self.partition_columns = model._partition_keys.values()
        super(_PartitionKeysToken, self).__init__(partition_key=True)

    def get_cql(self):
        return "token({})".format(", ".join(c.cql for c in self.partition_columns))

########NEW FILE########
__FILENAME__ = connection
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.policies import RetryPolicy
from cassandra.policies import WriteType
from contextlib import contextmanager
from cqlengine.exceptions import CQLEngineException
from cassandra.query import SimpleStatement
from feedly import settings
import logging


LOG = logging.getLogger('cqlengine.cql')


class CQLConnectionError(CQLEngineException):
    pass


class FeedlyRetryPolicy(RetryPolicy):

    def __init__(self, max_read_retries, max_write_retries):
        self.max_read_retries = max_read_retries
        self.max_write_retries = max_write_retries

    def on_read_timeout(self, query, consistency, required_responses, received_responses, data_retrieved, retry_num):
        if retry_num >= self.max_read_retries:
            return (self.RETHROW, None)
        elif received_responses >= required_responses and not data_retrieved:
            return (self.RETRY, consistency)
        else:
            return (self.RETHROW, None)

    def on_write_timeout(self, query, consistency, write_type, required_responses, received_responses, retry_num):
        if retry_num >= self.max_write_retries:
            return (self.RETHROW, None)
        elif write_type == WriteType.BATCH_LOG:
            return (self.RETRY, consistency)
        else:
            return (self.RETHROW, None)


class Connection:
    configured = False
    connection_pool = None
    default_consistency = None
    cluster_args = None
    cluster_kwargs = None
    default_timeout = 10.0


def setup(hosts, username=None, password=None, default_keyspace=None, consistency=None, metrics_enabled=False, default_timeout=10.0):
    """
    Records the hosts and connects to one of them

    :param hosts: list of hosts, strings in the <hostname>:<port>, or just <hostname>
    """

    if Connection.configured:
        LOG.info('cqlengine connection is already configured')
        return

    if default_keyspace:
        from cqlengine import models
        models.DEFAULT_KEYSPACE = default_keyspace

    _hosts = []
    port = 9042
    for host in hosts:
        host = host.strip()
        host = host.split(':')
        if len(host) == 1:
            _hosts.append(host[0])
        elif len(host) == 2:
            _hosts.append(host[0])
            port = host[1]
        else:
            raise CQLConnectionError("Can't parse {}".format(''.join(host)))

    if not _hosts:
        raise CQLConnectionError("At least one host required")

    Connection.cluster_args = (_hosts, )
    Connection.cluster_kwargs = {
        'port': int(port),
        'control_connection_timeout': 6.0,
        'metrics_enabled': metrics_enabled
    }
    Connection.default_timeout = default_timeout

    if consistency is None:
        Connection.default_consistency = ConsistencyLevel.ONE
    else:
        Connection.default_consistency = consistency


def get_cluster():
    cluster = Cluster(*Connection.cluster_args, **Connection.cluster_kwargs)
    cluster.default_retry_policy = FeedlyRetryPolicy(
        max_read_retries=settings.FEEDLY_CASSANDRA_READ_RETRY_ATTEMPTS,
        max_write_retries=settings.FEEDLY_CASSANDRA_WRITE_RETRY_ATTEMPTS
    )
    try:
        from cassandra.io.libevreactor import LibevConnection
        cluster.connection_class = LibevConnection
    except ImportError:
        pass
    return cluster


def get_connection_pool():
    if Connection.connection_pool is None or Connection.connection_pool.cluster._is_shutdown:
        cluster = get_cluster()
        Connection.connection_pool = cluster.connect()
        Connection.connection_pool.default_timeout = Connection.default_timeout
    return Connection.connection_pool


def get_consistency_level(consistency_level):
    if consistency_level is None:
        return Connection.default_consistency
    else:
        return consistency_level


def execute(query, params=None, consistency_level=None):
    params = params or {}
    consistency_level = get_consistency_level(consistency_level)
    session = get_connection_pool()
    query = SimpleStatement(query, consistency_level=consistency_level)
    return session.execute(query, parameters=params)


def execute_async(query, params=None, consistency_level=None):
    params = params or {}
    consistency_level = get_consistency_level(consistency_level)
    session = get_connection_pool()
    query = SimpleStatement(query, consistency_level=consistency_level)
    return session.execute_async(query, parameters=params)


@contextmanager
def connection_manager():
    yield get_connection_pool()

########NEW FILE########
__FILENAME__ = exceptions
# cqlengine exceptions
class CQLEngineException(Exception):
    pass


class ModelException(CQLEngineException):
    pass


class ValidationError(CQLEngineException):
    pass

########NEW FILE########
__FILENAME__ = functions
from datetime import datetime
from uuid import uuid1

from cqlengine.exceptions import ValidationError


class QueryValue(object):

    """
    Base class for query filter values. Subclasses of these classes can
    be passed into .filter() keyword args
    """

    _cql_string = '%({})s'

    def __init__(self, value, identifier=None):
        self.value = value
        self.identifier = uuid1().hex if identifier is None else identifier

    def get_cql(self):
        return self._cql_string.format(self.identifier)

    def get_value(self):
        return self.value

    def get_dict(self, column):
        return {self.identifier: self.get_value()}

    @property
    def cql(self):
        return self.get_cql()


class BaseQueryFunction(QueryValue):

    """
    Base class for filtering functions. Subclasses of these classes can
    be passed into .filter() and will be translated into CQL functions in
    the resulting query
    """


class MinTimeUUID(BaseQueryFunction):

    """
    return a fake timeuuid corresponding to the smallest possible timeuuid for the given timestamp

    http://cassandra.apache.org/doc/cql3/CQL.html#timeuuidFun
    """

    _cql_string = 'MinTimeUUID(:{})'

    def __init__(self, value):
        """
        :param value: the time to create a maximum time uuid from
        :type value: datetime
        """
        if not isinstance(value, datetime):
            raise ValidationError('datetime instance is required')
        super(MinTimeUUID, self).__init__(value)

    def get_value(self):
        epoch = datetime(1970, 1, 1)
        return long((self.value - epoch).total_seconds() * 1000)

    def get_dict(self, column):
        return {self.identifier: self.get_value()}


class MaxTimeUUID(BaseQueryFunction):

    """
    return a fake timeuuid corresponding to the largest possible timeuuid for the given timestamp

    http://cassandra.apache.org/doc/cql3/CQL.html#timeuuidFun
    """

    _cql_string = 'MaxTimeUUID(%({})s)'

    def __init__(self, value):
        """
        :param value: the time to create a minimum time uuid from
        :type value: datetime
        """
        if not isinstance(value, datetime):
            raise ValidationError('datetime instance is required')
        super(MaxTimeUUID, self).__init__(value)

    def get_value(self):
        epoch = datetime(1970, 1, 1)
        return long((self.value - epoch).total_seconds() * 1000)

    def get_dict(self, column):
        return {self.identifier: self.get_value()}


class Token(BaseQueryFunction):

    """
    compute the token for a given partition key

    http://cassandra.apache.org/doc/cql3/CQL.html#tokenFun
    """

    def __init__(self, *values):
        if len(values) == 1 and isinstance(values[0], (list, tuple)):
            values = values[0]
        super(Token, self).__init__(values, [uuid1().hex for i in values])

    def get_dict(self, column):
        items = zip(self.identifier, self.value, column.partition_columns)
        return dict(
            (id, val) for id, val, col in items
        )

    def get_cql(self):
        token_args = ', '.join(':{}'.format(id) for id in self.identifier)
        return "token({})".format(token_args)

########NEW FILE########
__FILENAME__ = management
import json
import warnings
from cqlengine import SizeTieredCompactionStrategy, LeveledCompactionStrategy
from cqlengine.named import NamedTable

from cqlengine.connection import connection_manager, execute
from cqlengine.exceptions import CQLEngineException

import logging
from collections import namedtuple
Field = namedtuple('Field', ['name', 'type'])

logger = logging.getLogger(__name__)


# system keyspaces
schema_columnfamilies = NamedTable('system', 'schema_columnfamilies')


def create_keyspace(name, strategy_class='SimpleStrategy', replication_factor=3, durable_writes=True, **replication_values):
    """
    creates a keyspace

    :param name: name of keyspace to create
    :param strategy_class: keyspace replication strategy class
    :param replication_factor: keyspace replication factor
    :param durable_writes: 1.2 only, write log is bypassed if set to False
    :param **replication_values: 1.2 only, additional values to ad to the replication data map
    """
    with connection_manager() as con:
        keyspaces = con.execute(
            """SELECT keyspace_name FROM system.schema_keyspaces""", {})
        if name not in [r[0] for r in keyspaces]:
            # try the 1.2 method
            replication_map = {
                'class': strategy_class,
                'replication_factor': replication_factor
            }
            replication_map.update(replication_values)

            query = """
            CREATE KEYSPACE {}
            WITH REPLICATION = {}
            """.format(name, json.dumps(replication_map).replace('"', "'"))

            if strategy_class != 'SimpleStrategy':
                query += " AND DURABLE_WRITES = {}".format(
                    'true' if durable_writes else 'false')

            execute(query)


def delete_keyspace(name):
    with connection_manager() as con:
        _, keyspaces = con.execute(
            """SELECT keyspace_name FROM system.schema_keyspaces""", {})
        if name in [r[0] for r in keyspaces]:
            execute("DROP KEYSPACE {}".format(name))


def create_table(model, create_missing_keyspace=True):
    warnings.warn(
        "create_table has been deprecated in favor of sync_table and will be removed in a future release", DeprecationWarning)
    sync_table(model, create_missing_keyspace)


def sync_table(model, create_missing_keyspace=True):

    if model.__abstract__:
        raise CQLEngineException("cannot create table from abstract model")

    # construct query string
    cf_name = model.column_family_name()
    raw_cf_name = model.column_family_name(include_keyspace=False)

    ks_name = model._get_keyspace()
    # create missing keyspace
    if create_missing_keyspace:
        create_keyspace(ks_name)

    with connection_manager() as con:
        tables = con.execute(
            "SELECT columnfamily_name from system.schema_columnfamilies WHERE keyspace_name = %(ks_name)s",
            {'ks_name': ks_name}
        )
    tables = [x.columnfamily_name for x in tables]

    # check for an existing column family
    if raw_cf_name not in tables:
        qs = get_create_table(model)

        try:
            execute(qs)
        except CQLEngineException as ex:
            # 1.2 doesn't return cf names, so we have to examine the exception
            # and ignore if it says the column family already exists
            if "Cannot add already existing column family" not in unicode(ex):
                raise
    else:
        # see if we're missing any columns
        fields = get_fields(model)
        field_names = [x.name for x in fields]
        for name, col in model._columns.items():
            if col.primary_key or col.partition_key:
                continue  # we can't mess with the PK
            if col.db_field_name in field_names:
                continue  # skip columns already defined

            # add missing column using the column def
            query = "ALTER TABLE {} add {}".format(
                cf_name, col.get_column_def())
            logger.debug(query)
            execute(query)

        update_compaction(model)

    # get existing index names, skip ones that already exist
    with connection_manager() as con:
        idx_names = con.execute(
            "SELECT index_name from system.\"IndexInfo\" WHERE table_name=%(table_name)s",
            {'table_name': raw_cf_name}
        )

    idx_names = [i.index_name for i in idx_names]
    idx_names = filter(None, idx_names)

    indexes = [c for n, c in model._columns.items() if c.index]
    if indexes:
        for column in indexes:
            if column.db_index_name in idx_names:
                continue
            qs = ['CREATE INDEX index_{}_{}'.format(
                raw_cf_name, column.db_field_name)]
            qs += ['ON {}'.format(cf_name)]
            qs += ['("{}")'.format(column.db_field_name)]
            qs = ' '.join(qs)

            try:
                execute(qs)
            except CQLEngineException:
                # index already exists
                pass


def get_create_table(model):
    cf_name = model.column_family_name()
    qs = ['CREATE TABLE {}'.format(cf_name)]

    # add column types
    pkeys = []  # primary keys
    ckeys = []  # clustering keys
    qtypes = []  # field types

    def add_column(col):
        s = col.get_column_def()
        if col.primary_key:
            keys = (pkeys if col.partition_key else ckeys)
            keys.append('"{}"'.format(col.db_field_name))
        qtypes.append(s)
    for name, col in model._columns.items():
        add_column(col)

    qtypes.append('PRIMARY KEY (({}){})'.format(
        ', '.join(pkeys), ckeys and ', ' + ', '.join(ckeys) or ''))

    qs += ['({})'.format(', '.join(qtypes))]

    with_qs = ['read_repair_chance = {}'.format(model.__read_repair_chance__)]

    _order = ['"{}" {}'.format(c.db_field_name, c.clustering_order or 'ASC')
              for c in model._clustering_keys.values()]

    if _order:
        with_qs.append('clustering order by ({})'.format(', '.join(_order)))

    compaction_options = get_compaction_options(model)

    if compaction_options:
        compaction_options = json.dumps(compaction_options).replace('"', "'")
        with_qs.append("compaction = {}".format(compaction_options))

    # add read_repair_chance
    qs += ['WITH {}'.format(' AND '.join(with_qs))]

    qs = ' '.join(qs)
    return qs


def get_compaction_options(model):
    """
    Generates dictionary (later converted to a string) for creating and altering
    tables with compaction strategy

    :param model:
    :return:
    """
    if not model.__compaction__:
        return {}

    result = {'class': model.__compaction__}

    def setter(key, limited_to_strategy=None):
        """
        sets key in result, checking if the key is limited to either SizeTiered or Leveled
        :param key: one of the compaction options, like "bucket_high"
        :param limited_to_strategy: SizeTieredCompactionStrategy, LeveledCompactionStrategy
        :return:
        """
        mkey = "__compaction_{}__".format(key)
        tmp = getattr(model, mkey)
        if tmp and limited_to_strategy and limited_to_strategy != model.__compaction__:
            raise CQLEngineException(
                "{} is limited to {}".format(key, limited_to_strategy))

        if tmp:
            result[key] = tmp

    setter('tombstone_compaction_interval')

    setter('bucket_high', SizeTieredCompactionStrategy)
    setter('bucket_low', SizeTieredCompactionStrategy)
    setter('max_threshold', SizeTieredCompactionStrategy)
    setter('min_threshold', SizeTieredCompactionStrategy)
    setter('min_sstable_size', SizeTieredCompactionStrategy)

    setter("sstable_size_in_mb", LeveledCompactionStrategy)

    return result


def get_fields(model):
    # returns all fields that aren't part of the PK
    ks_name = model._get_keyspace()
    col_family = model.column_family_name(include_keyspace=False)

    with connection_manager() as con:
        query = "SELECT column_name, validator FROM system.schema_columns \
                 WHERE keyspace_name = %(ks_name)s AND columnfamily_name = %(col_family)s"

        logger.debug("get_fields %s %s", ks_name, col_family)

        results = con.execute(
            query, {'ks_name': ks_name, 'col_family': col_family})
    return [Field(x.column_name, x.validator) for x in results]
    # convert to Field named tuples


def get_table_settings(model):
    return schema_columnfamilies.get(keyspace_name=model._get_keyspace(),
                                     columnfamily_name=model.column_family_name(include_keyspace=False))


def update_compaction(model):
    logger.debug("Checking %s for compaction differences", model)
    row = get_table_settings(model)
    # check compaction_strategy_class
    if not model.__compaction__:
        return

    do_update = not row['compaction_strategy_class'].endswith(
        model.__compaction__)

    existing_options = row['compaction_strategy_options']
    existing_options = json.loads(existing_options)

    desired_options = get_compaction_options(model)
    desired_options.pop('class', None)

    for k, v in desired_options.items():
        val = existing_options.pop(k, None)
        if val != v:
            do_update = True

    # check compaction_strategy_options
    if do_update:
        options = get_compaction_options(model)
        # jsonify
        options = json.dumps(options).replace('"', "'")
        cf_name = model.column_family_name()
        query = "ALTER TABLE {} with compaction = {}".format(cf_name, options)
        logger.debug(query)
        execute(query)


def delete_table(model):
    warnings.warn(
        "delete_table has been deprecated in favor of drop_table()", DeprecationWarning)
    return drop_table(model)


def drop_table(model):

    # don't try to delete non existant tables
    ks_name = model._get_keyspace()
    with connection_manager() as con:
        tables = con.execute(
            "SELECT columnfamily_name from system.schema_columnfamilies WHERE keyspace_name = %(ks_name)s",
            {'ks_name': ks_name}
        )
    raw_cf_name = model.column_family_name(include_keyspace=False)
    if raw_cf_name not in [t[0] for t in tables]:
        return

    cf_name = model.column_family_name()
    execute('drop table {};'.format(cf_name))

########NEW FILE########
__FILENAME__ = models
from collections import OrderedDict
import re

from cqlengine import columns
from cqlengine.exceptions import ModelException, CQLEngineException, ValidationError
from cqlengine.query import ModelQuerySet, DMLQuery, AbstractQueryableColumn
from cqlengine.query import DoesNotExist as _DoesNotExist
from cqlengine.query import MultipleObjectsReturned as _MultipleObjectsReturned


class ModelDefinitionException(ModelException):
    pass

DEFAULT_KEYSPACE = 'cqlengine'


class hybrid_classmethod(object):

    """
    Allows a method to behave as both a class method and
    normal instance method depending on how it's called
    """

    def __init__(self, clsmethod, instmethod):
        self.clsmethod = clsmethod
        self.instmethod = instmethod

    def __get__(self, instance, owner):
        if instance is None:
            return self.clsmethod.__get__(owner, owner)
        else:
            return self.instmethod.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        """
        Just a hint to IDEs that it's ok to call this
        """
        raise NotImplementedError


class QuerySetDescriptor(object):

    """
    returns a fresh queryset for the given model
    it's declared on everytime it's accessed
    """

    def __get__(self, obj, model):
        """ :rtype: ModelQuerySet """
        if model.__abstract__:
            raise CQLEngineException(
                'cannot execute queries against abstract models')
        return model.__queryset__(model)

    def __call__(self, *args, **kwargs):
        """
        Just a hint to IDEs that it's ok to call this

        :rtype: ModelQuerySet
        """
        raise NotImplementedError


class ColumnQueryEvaluator(AbstractQueryableColumn):

    """
    Wraps a column and allows it to be used in comparator
    expressions, returning query operators

    ie:
    Model.column == 5
    """

    def __init__(self, column):
        self.column = column

    def _get_column(self):
        return self.column


class ColumnDescriptor(object):

    """
    Handles the reading and writing of column values to and from
    a model instance's value manager, as well as creating
    comparator queries
    """

    def __init__(self, column):
        """
        :param column:
        :type column: columns.Column
        :return:
        """
        self.column = column
        self.query_evaluator = ColumnQueryEvaluator(self.column)

    def __get__(self, instance, owner):
        """
        Returns either the value or column, depending
        on if an instance is provided or not

        :param instance: the model instance
        :type instance: Model
        """

        if instance:
            return instance._values[self.column.column_name].getval()
        else:
            return self.query_evaluator

    def __set__(self, instance, value):
        """
        Sets the value on an instance, raises an exception with classes
        TODO: use None instance to create update statements
        """
        if instance:
            return instance._values[self.column.column_name].setval(value)
        else:
            raise AttributeError('cannot reassign column values')

    def __delete__(self, instance):
        """
        Sets the column value to None, if possible
        """
        if instance:
            if self.column.can_delete:
                instance._values[self.column.column_name].delval()
            else:
                raise AttributeError(
                    'cannot delete {} columns'.format(self.column.column_name))


class BaseModel(object):

    """
    The base model class, don't inherit from this, inherit from Model, defined below
    """

    class DoesNotExist(_DoesNotExist):
        pass

    class MultipleObjectsReturned(_MultipleObjectsReturned):
        pass

    objects = QuerySetDescriptor()

    # table names will be generated automatically from it's model and package name
    # however, you can also define them manually here
    __table_name__ = None

    # the keyspace for this model
    __keyspace__ = None

    # compaction options
    __compaction__ = None
    __compaction_tombstone_compaction_interval__ = None
    __compaction_tombstone_threshold = None

    # compaction - size tiered options
    __compaction_bucket_high__ = None
    __compaction_bucket_low__ = None
    __compaction_max_threshold__ = None
    __compaction_min_threshold__ = None
    __compaction_min_sstable_size__ = None

    # compaction - leveled options
    __compaction_sstable_size_in_mb__ = None

    # end compaction
    # the queryset class used for this class
    __queryset__ = ModelQuerySet
    __dmlquery__ = DMLQuery

    __read_repair_chance__ = 0.1

    def __init__(self, **values):
        self._values = {}

        extra_columns = set(values.keys()) - set(self._columns.keys())
        if extra_columns:
            raise ValidationError(
                "Incorrect columns passed: {}".format(extra_columns))

        for name, column in self._columns.items():
            value = values.get(name, None)
            if value is not None or isinstance(column, columns.BaseContainerColumn):
                value = column.to_python(value)
            value_mngr = column.value_manager(self, column, value)
            self._values[name] = value_mngr

        # a flag set by the deserializer to indicate
        # that update should be used when persisting changes
        self._is_persisted = False
        self._batch = None

    def _can_update(self):
        """
        Called by the save function to check if this should be
        persisted with update or insert

        :return:
        """
        if not self._is_persisted:
            return False
        pks = self._primary_keys.keys()
        return all([not self._values[k].changed for k in self._primary_keys])

    @classmethod
    def _get_keyspace(cls):
        """ Returns the manual keyspace, if set, otherwise the default keyspace """
        return cls.__keyspace__ or DEFAULT_KEYSPACE

    @classmethod
    def _get_column(cls, name):
        """
        Returns the column matching the given name, raising a key error if
        it doesn't exist

        :param name: the name of the column to return
        :rtype: Column
        """
        return cls._columns[name]

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        # check attribute keys
        keys = set(self._columns.keys())
        other_keys = set(self._columns.keys())
        if keys != other_keys:
            return False

        # check that all of the attributes match
        for key in other_keys:
            if getattr(self, key, None) != getattr(other, key, None):
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def column_family_name(cls, include_keyspace=True):
        """
        Returns the column family name if it's been defined
        otherwise, it creates it from the module and class name
        """
        cf_name = ''
        if cls.__table_name__:
            cf_name = cls.__table_name__.lower()
        else:
            camelcase = re.compile(r'([a-z])([A-Z])')
            ccase = lambda s: camelcase.sub(
                lambda v: '{}_{}'.format(v.group(1), v.group(2).lower()), s)

            cf_name += ccase(cls.__name__)
            # trim to less than 48 characters or cassandra will complain
            cf_name = cf_name[-48:]
            cf_name = cf_name.lower()
            cf_name = re.sub(r'^_+', '', cf_name)
        if not include_keyspace:
            return cf_name
        return '{}.{}'.format(cls._get_keyspace(), cf_name)

    def validate(self):
        """ Cleans and validates the field values """
        for name, col in self._columns.items():
            val = col.validate(getattr(self, name))
            setattr(self, name, val)

    def _as_dict(self):
        """ Returns a map of column names to cleaned values """
        values = self._dynamic_columns or {}
        for name, col in self._columns.items():
            values[name] = getattr(self, name, None)
        print values
        return values

    @classmethod
    def create(cls, **kwargs):
        return cls.objects.create(**kwargs)

    @classmethod
    def all(cls):
        return cls.objects.all()

    @classmethod
    def filter(cls, *args, **kwargs):
        return cls.objects.filter(*args, **kwargs)

    @classmethod
    def get(cls, *args, **kwargs):
        return cls.objects.get(*args, **kwargs)

    def save(self):
        is_new = self.pk is None
        self.validate()
        self.__dmlquery__(self.__class__, self, batch=self._batch).save()

        # reset the value managers
        for v in self._values.values():
            v.reset_previous_value()
        self._is_persisted = True

        return self

    def delete(self):
        """ Deletes this instance """
        self.__dmlquery__(self.__class__, self, batch=self._batch).delete()

    @classmethod
    def _class_batch(cls, batch):
        return cls.objects.batch(batch)

    def _inst_batch(self, batch):
        self._batch = batch
        return self

    batch = hybrid_classmethod(_class_batch, _inst_batch)


class ModelMetaClass(type):

    def __new__(cls, name, bases, attrs):
        """
        """
        # move column definitions into columns dict
        # and set default column names
        column_dict = OrderedDict()
        primary_keys = OrderedDict()
        pk_name = None

        # get inherited properties
        inherited_columns = OrderedDict()
        for base in bases:
            for k, v in getattr(base, '_defined_columns', {}).items():
                inherited_columns.setdefault(k, v)

        # short circuit __abstract__ inheritance
        is_abstract = attrs['__abstract__'] = attrs.get('__abstract__', False)

        def _transform_column(col_name, col_obj):
            column_dict[col_name] = col_obj
            if col_obj.primary_key:
                primary_keys[col_name] = col_obj
            col_obj.set_column_name(col_name)
            # set properties
            attrs[col_name] = ColumnDescriptor(col_obj)

        column_definitions = [
            (k, v) for k, v in attrs.items() if isinstance(v, columns.Column)]
        column_definitions = sorted(
            column_definitions, lambda x, y: cmp(x[1].position, y[1].position))

        column_definitions = inherited_columns.items() + column_definitions

        defined_columns = OrderedDict(column_definitions)

        # prepend primary key if one hasn't been defined
        if not is_abstract and not any([v.primary_key for k, v in column_definitions]):
            raise ModelDefinitionException(
                "At least 1 primary key is required.")

        counter_columns = [
            c for c in defined_columns.values() if isinstance(c, columns.Counter)]
        data_columns = [c for c in defined_columns.values(
        ) if not c.primary_key and not isinstance(c, columns.Counter)]
        if counter_columns and data_columns:
            raise ModelDefinitionException(
                'counter models may not have data columns')

        has_partition_keys = any(
            v.partition_key for (k, v) in column_definitions)

        # TODO: check that the defined columns don't conflict with any of the Model API's existing attributes/methods
        # transform column definitions
        for k, v in column_definitions:
            # counter column primary keys are not allowed
            if (v.primary_key or v.partition_key) and isinstance(v, (columns.Counter, columns.BaseContainerColumn)):
                raise ModelDefinitionException(
                    'counter columns and container columns cannot be used as primary keys')

            # this will mark the first primary key column as a partition
            # key, if one hasn't been set already
            if not has_partition_keys and v.primary_key:
                v.partition_key = True
                has_partition_keys = True
            _transform_column(k, v)

        partition_keys = OrderedDict(
            k for k in primary_keys.items() if k[1].partition_key)
        clustering_keys = OrderedDict(
            k for k in primary_keys.items() if not k[1].partition_key)

        # setup partition key shortcut
        if len(partition_keys) == 0:
            if not is_abstract:
                raise ModelException(
                    "at least one partition key must be defined")
        if len(partition_keys) == 1:
            pk_name = partition_keys.keys()[0]
            attrs['pk'] = attrs[pk_name]
        else:
            # composite partition key case, get/set a tuple of values
            _get = lambda self: tuple(
                self._values[c].getval() for c in partition_keys.keys())
            _set = lambda self, val: tuple(
                self._values[c].setval(v) for (c, v) in zip(partition_keys.keys(), val))
            attrs['pk'] = property(_get, _set)

        # some validation
        col_names = set()
        for v in column_dict.values():
            # check for duplicate column names
            if v.db_field_name in col_names:
                raise ModelException(
                    "{} defines the column {} more than once".format(name, v.db_field_name))
            if v.clustering_order and not (v.primary_key and not v.partition_key):
                raise ModelException(
                    "clustering_order may be specified only for clustering primary keys")
            if v.clustering_order and v.clustering_order.lower() not in ('asc', 'desc'):
                raise ModelException("invalid clustering order {} for column {}".format(
                    repr(v.clustering_order), v.db_field_name))
            col_names.add(v.db_field_name)

        # create db_name -> model name map for loading
        db_map = {}
        for field_name, col in column_dict.items():
            db_map[col.db_field_name] = field_name

        # add management members to the class
        attrs['_columns'] = column_dict
        attrs['_primary_keys'] = primary_keys
        attrs['_defined_columns'] = defined_columns
        attrs['_db_map'] = db_map
        attrs['_pk_name'] = pk_name
        attrs['_dynamic_columns'] = {}

        attrs['_partition_keys'] = partition_keys
        attrs['_clustering_keys'] = clustering_keys
        attrs['_has_counter'] = len(counter_columns) > 0

        # setup class exceptions
        DoesNotExistBase = None
        for base in bases:
            DoesNotExistBase = getattr(base, 'DoesNotExist', None)
            if DoesNotExistBase is not None:
                break
        DoesNotExistBase = DoesNotExistBase or attrs.pop(
            'DoesNotExist', BaseModel.DoesNotExist)
        attrs['DoesNotExist'] = type('DoesNotExist', (DoesNotExistBase,), {})

        MultipleObjectsReturnedBase = None
        for base in bases:
            MultipleObjectsReturnedBase = getattr(
                base, 'MultipleObjectsReturned', None)
            if MultipleObjectsReturnedBase is not None:
                break
        MultipleObjectsReturnedBase = DoesNotExistBase or attrs.pop(
            'MultipleObjectsReturned', BaseModel.MultipleObjectsReturned)
        attrs['MultipleObjectsReturned'] = type(
            'MultipleObjectsReturned', (MultipleObjectsReturnedBase,), {})

        # create the class and add a QuerySet to it
        klass = super(ModelMetaClass, cls).__new__(cls, name, bases, attrs)
        return klass


class Model(BaseModel):

    """
    the db name for the column family can be set as the attribute db_name, or
    it will be genertaed from the class name
    """
    __abstract__ = True
    __metaclass__ = ModelMetaClass

########NEW FILE########
__FILENAME__ = named
from cqlengine.exceptions import CQLEngineException
from cqlengine.query import AbstractQueryableColumn, SimpleQuerySet

from cqlengine.query import DoesNotExist as _DoesNotExist
from cqlengine.query import MultipleObjectsReturned as _MultipleObjectsReturned


class QuerySetDescriptor(object):

    """
    returns a fresh queryset for the given model
    it's declared on everytime it's accessed
    """

    def __get__(self, obj, model):
        """ :rtype: ModelQuerySet """
        if model.__abstract__:
            raise CQLEngineException(
                'cannot execute queries against abstract models')
        return SimpleQuerySet(obj)

    def __call__(self, *args, **kwargs):
        """
        Just a hint to IDEs that it's ok to call this

        :rtype: ModelQuerySet
        """
        raise NotImplementedError


class NamedColumn(AbstractQueryableColumn):

    """
    A column that is not coupled to a model class, or type
    """

    def __init__(self, name):
        self.name = name

    def _get_column(self):
        return self

    @property
    def cql(self):
        return self.get_cql()

    def get_cql(self):
        return '"{}"'.format(self.name)


class NamedTable(object):

    """
    A Table that is not coupled to a model class
    """

    __abstract__ = False

    objects = QuerySetDescriptor()

    class DoesNotExist(_DoesNotExist):
        pass

    class MultipleObjectsReturned(_MultipleObjectsReturned):
        pass

    def __init__(self, keyspace, name):
        self.keyspace = keyspace
        self.name = name

    def column(self, name):
        return NamedColumn(name)

    def column_family_name(self, include_keyspace=True):
        """
        Returns the column family name if it's been defined
        otherwise, it creates it from the module and class name
        """
        if include_keyspace:
            return '{}.{}'.format(self.keyspace, self.name)
        else:
            return self.name

    def _get_column(self, name):
        """
        Returns the column matching the given name

        :rtype: Column
        """
        return self.column(name)

    # def create(self, **kwargs):
    #     return self.objects.create(**kwargs)

    def all(self):
        return self.objects.all()

    def filter(self, *args, **kwargs):
        return self.objects.filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.objects.get(*args, **kwargs)


class NamedKeyspace(object):

    """
    A keyspace
    """

    def __init__(self, name):
        self.name = name

    def table(self, name):
        """
        returns a table descriptor with the given
        name that belongs to this keyspace
        """
        return NamedTable(self.name, name)

########NEW FILE########
__FILENAME__ = query
import copy
from datetime import datetime
from uuid import uuid4
from cqlengine import BaseContainerColumn, Map, columns
from cqlengine.columns import Counter
from cqlengine.connection import get_connection_pool
from cqlengine.connection import execute

from cqlengine.exceptions import CQLEngineException
from cqlengine.functions import QueryValue, Token
from cqlengine.utils import chunks


# CQL 3 reference:
# http://www.datastax.com/docs/1.1/references/cql/index

class QueryException(CQLEngineException):
    pass


class DoesNotExist(QueryException):
    pass


class MultipleObjectsReturned(QueryException):
    pass


class QueryOperatorException(QueryException):
    pass


class QueryOperator(object):
    # The symbol that identifies this operator in filter kwargs
    # ie: colname__<symbol>
    symbol = None

    # The comparator symbol this operator uses in cql
    cql_symbol = None

    QUERY_VALUE_WRAPPER = QueryValue

    def __init__(self, column, value):
        self.column = column
        self.value = value

        if isinstance(value, QueryValue):
            self.query_value = value
        else:
            self.query_value = self.QUERY_VALUE_WRAPPER(value)

        # perform validation on this operator
        self.validate_operator()
        self.validate_value()

    @property
    def cql(self):
        """
        Returns this operator's portion of the WHERE clause
        """
        return '{} {} {}'.format(self.column.cql, self.cql_symbol, self.query_value.cql)

    def validate_operator(self):
        """
        Checks that this operator can be used on the column provided
        """
        if self.symbol is None:
            raise QueryOperatorException(
                "{} is not a valid operator, use one with 'symbol' defined".format(
                    self.__class__.__name__
                )
            )
        if self.cql_symbol is None:
            raise QueryOperatorException(
                "{} is not a valid operator, use one with 'cql_symbol' defined".format(
                    self.__class__.__name__
                )
            )

    def validate_value(self):
        """
        Checks that the compare value works with this operator

        Doesn't do anything by default
        """
        pass

    def get_dict(self):
        """
        Returns this operators contribution to the cql.query arg dictionanry

        ie: if this column's name is colname, and the identifier is colval,
        this should return the dict: {'colval':<self.value>}
        SELECT * FROM column_family WHERE colname=:colval
        """
        return self.query_value.get_dict(self.column)

    @classmethod
    def get_operator(cls, symbol):
        if not hasattr(cls, 'opmap'):
            QueryOperator.opmap = {}

            def _recurse(klass):
                if klass.symbol:
                    QueryOperator.opmap[klass.symbol.upper()] = klass
                for subklass in klass.__subclasses__():
                    _recurse(subklass)
                pass
            _recurse(QueryOperator)
        try:
            return QueryOperator.opmap[symbol.upper()]
        except KeyError:
            raise QueryOperatorException(
                "{} doesn't map to a QueryOperator".format(symbol))

    # equality operator, used by tests

    def __eq__(self, op):
        return self.__class__ is op.__class__ and \
            self.column.db_field_name == op.column.db_field_name and \
            self.value == op.value

    def __ne__(self, op):
        return not (self == op)

    def __hash__(self):
        return hash(self.column.db_field_name) ^ hash(self.value)


class EqualsOperator(QueryOperator):
    symbol = 'EQ'
    cql_symbol = '='


class IterableQueryValue(QueryValue):

    def __init__(self, value):
        try:
            super(IterableQueryValue, self).__init__(
                value, [uuid4().hex for i in value])
        except TypeError:
            raise QueryException(
                "in operator arguments must be iterable, {} found".format(value))

    def get_dict(self, column):
        return dict((i, v) for (i, v) in zip(self.identifier, self.value))

    def get_cql(self):
        return '({})'.format(', '.join('%({})s'.format(i) for i in self.identifier))


class InOperator(EqualsOperator):
    symbol = 'IN'
    cql_symbol = 'IN'

    QUERY_VALUE_WRAPPER = IterableQueryValue


class GreaterThanOperator(QueryOperator):
    symbol = "GT"
    cql_symbol = '>'


class GreaterThanOrEqualOperator(QueryOperator):
    symbol = "GTE"
    cql_symbol = '>='


class LessThanOperator(QueryOperator):
    symbol = "LT"
    cql_symbol = '<'


class LessThanOrEqualOperator(QueryOperator):
    symbol = "LTE"
    cql_symbol = '<='


class AbstractQueryableColumn(object):

    """
    exposes cql query operators through pythons
    builtin comparator symbols
    """

    def _get_column(self):
        raise NotImplementedError

    def in_(self, item):
        """
        Returns an in operator

        used in where you'd typically want to use python's `in` operator
        """
        return InOperator(self._get_column(), item)

    def __eq__(self, other):
        return EqualsOperator(self._get_column(), other)

    def __gt__(self, other):
        return GreaterThanOperator(self._get_column(), other)

    def __ge__(self, other):
        return GreaterThanOrEqualOperator(self._get_column(), other)

    def __lt__(self, other):
        return LessThanOperator(self._get_column(), other)

    def __le__(self, other):
        return LessThanOrEqualOperator(self._get_column(), other)


class BatchType(object):
    Unlogged = 'UNLOGGED'
    Counter = 'COUNTER'


class BatchQuery(object):

    """
    Handles the batching of queries

    http://www.datastax.com/docs/1.2/cql_cli/cql/BATCH
    """

    def __init__(self, batch_type=None, timestamp=None):
        self.queries = []
        self.batch_type = batch_type
        if timestamp is not None and not isinstance(timestamp, datetime):
            raise CQLEngineException(
                'timestamp object must be an instance of datetime')
        self.timestamp = timestamp

    def add_query(self, query, params):
        self.queries.append((query, params))

    def execute(self):
        if len(self.queries) == 0:
            # Empty batch is a no-op
            return

        opener = 'BEGIN ' + \
            (self.batch_type + ' ' if self.batch_type else '') + ' BATCH'
        if self.timestamp:
            epoch = datetime(1970, 1, 1)
            ts = long((self.timestamp - epoch).total_seconds() * 1000)
            opener += ' USING TIMESTAMP {}'.format(ts)

        query_list = [opener]
        parameters = {}
        for query, params in self.queries:
            query_list.append('  ' + query)
            parameters.update(params)

        query_list.append('APPLY BATCH;')

        execute('\n'.join(query_list), parameters)

        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # don't execute if there was an exception
        if exc_type is not None:
            return
        self.execute()


class AbstractQuerySet(object):

    def __init__(self, model):
        super(AbstractQuerySet, self).__init__()
        self.model = model

        # Where clause filters
        self._where = []

        # ordering arguments
        self._order = []

        self._allow_filtering = False

        # CQL has a default limit of 10000, it's defined here
        # because explicit is better than implicit
        self._limit = 10000

        # see the defer and only methods
        self._defer_fields = []
        self._only_fields = []

        self._values_list = False
        self._flat_values_list = False

        # results cache
        self._con = None
        self._cur = None
        self._result_cache = None
        self._result_idx = None

        self._batch = None

    @property
    def column_family_name(self):
        return self.model.column_family_name()

    def __unicode__(self):
        return self._select_query()

    def __str__(self):
        return str(self.__unicode__())

    def __call__(self, *args, **kwargs):
        return self.filter(*args, **kwargs)

    def __deepcopy__(self, memo):
        clone = self.__class__(self.model)
        for k, v in self.__dict__.items():
            if k in ['_con', '_cur', '_result_cache', '_result_idx']:
                clone.__dict__[k] = None
            elif k == '_batch':
                # we need to keep the same batch instance across
                # all queryset clones, otherwise the batched queries
                # fly off into other batch instances which are never
                # executed, thx @dokai
                clone.__dict__[k] = self._batch
            else:
                clone.__dict__[k] = copy.deepcopy(v, memo)

        return clone

    def __len__(self):
        self._execute_query()
        return len(self._result_cache)

    #----query generation / execution----

    def _where_clause(self):
        """ Returns a where clause based on the given filter args """
        return ' AND '.join([f.cql for f in self._where])

    def _where_values(self):
        """ Returns the value dict to be passed to the cql query """
        values = {}
        for where in self._where:
            values.update(where.get_dict())
        return values

    def _get_select_statement(self):
        """ returns the select portion of this queryset's cql statement """
        raise NotImplementedError

    def _select_query(self):
        """
        Returns a select clause based on the given filter args
        """
        qs = [self._get_select_statement()]
        qs += ['FROM {}'.format(self.column_family_name)]

        if self._where:
            qs += ['WHERE {}'.format(self._where_clause())]

        if self._order:
            qs += ['ORDER BY {}'.format(', '.join(self._order))]

        if self._limit:
            qs += ['LIMIT {}'.format(self._limit)]

        if self._allow_filtering:
            qs += ['ALLOW FILTERING']

        return ' '.join(qs)

    #----Reads------

    def _execute_query(self):
        if self._batch:
            raise CQLEngineException(
                "Only inserts, updates, and deletes are available in batch mode")
        if self._result_cache is None:
            self._result_cache = execute(
                self._select_query(), self._where_values())
            field_names = set(
                sum([res._fields for res in self._result_cache], tuple()))
            self._construct_result = self._get_result_constructor(field_names)

    def _fill_result_cache_to_idx(self, idx):
        self._execute_query()
        if self._result_idx is None:
            self._result_idx = -1

        qty = idx - self._result_idx
        if qty < 1:
            return
        else:
            for idx in range(qty):
                self._result_idx += 1
                self._result_cache[self._result_idx] = self._construct_result(
                    self._result_cache[self._result_idx])

            # return the connection to the connection pool if we have all
            # objects
            if self._result_cache and self._result_idx == (len(self._result_cache) - 1):
                self._con = None
                self._cur = None

    def __iter__(self):
        self._execute_query()
        for idx in range(len(self._result_cache)):
            instance = self._result_cache[idx]
            # TODO: find a better way to check for this (cassandra.decoder.Row
            # is factorized :/)
            if instance.__class__.__name__ == 'Row':
                self._fill_result_cache_to_idx(idx)
            yield self._result_cache[idx]

    def __getitem__(self, s):
        self._execute_query()

        num_results = len(self._result_cache)

        if isinstance(s, slice):
            # calculate the amount of results that need to be loaded
            end = num_results if s.step is None else s.step
            if end < 0:
                end += num_results
            else:
                end -= 1
            self._fill_result_cache_to_idx(end)
            return self._result_cache[s.start:s.stop:s.step]
        else:
            # return the object at this index
            s = long(s)

            # handle negative indexing
            if s < 0:
                s += num_results

            if s >= num_results:
                raise IndexError
            else:
                self._fill_result_cache_to_idx(s)
                return self._result_cache[s]

    def _get_result_constructor(self, names):
        """
        Returns a function that will be used to instantiate query results
        """
        raise NotImplementedError

    def batch(self, batch_obj):
        """
        Adds a batch query to the mix
        :param batch_obj:
        :return:
        """
        if batch_obj is not None and not isinstance(batch_obj, BatchQuery):
            raise CQLEngineException(
                'batch_obj must be a BatchQuery instance or None')
        clone = copy.deepcopy(self)
        clone._batch = batch_obj
        return clone

    def first(self):
        try:
            return iter(self).next()
        except StopIteration:
            return None

    def all(self):
        return copy.deepcopy(self)

    def _parse_filter_arg(self, arg):
        """
        Parses a filter arg in the format:
        <colname>__<op>
        :returns: colname, op tuple
        """
        statement = arg.rsplit('__', 1)
        if len(statement) == 1:
            return arg, None
        elif len(statement) == 2:
            return statement[0], statement[1]
        else:
            raise QueryException("Can't parse '{}'".format(arg))

    def filter(self, *args, **kwargs):
        """
        Adds WHERE arguments to the queryset, returning a new queryset

        #TODO: show examples

        :rtype: AbstractQuerySet
        """
        # add arguments to the where clause filters
        clone = copy.deepcopy(self)
        for operator in args:
            if not isinstance(operator, QueryOperator):
                raise QueryException(
                    '{} is not a valid query operator'.format(operator))
            clone._where.append(operator)

        for arg, val in kwargs.items():
            col_name, col_op = self._parse_filter_arg(arg)
            # resolve column and operator
            try:
                column = self.model._get_column(col_name)
            except KeyError:
                if col_name == 'pk__token':
                    column = columns._PartitionKeysToken(self.model)
                else:
                    raise QueryException(
                        "Can't resolve column name: '{}'".format(col_name))

            # get query operator, or use equals if not supplied
            operator_class = QueryOperator.get_operator(col_op or 'EQ')
            operator = operator_class(column, val)

            clone._where.append(operator)

        return clone

    def get(self, *args, **kwargs):
        """
        Returns a single instance matching this query, optionally with additional filter kwargs.

        A DoesNotExistError will be raised if there are no rows matching the query
        A MultipleObjectsFoundError will be raised if there is more than one row matching the queyr
        """
        if args or kwargs:
            return self.filter(*args, **kwargs).get()

        self._execute_query()
        if len(self._result_cache) == 0:
            raise self.model.DoesNotExist
        elif len(self._result_cache) > 1:
            raise self.model.MultipleObjectsReturned(
                '{} objects found'.format(len(self._result_cache)))
        else:
            return self[0]

    def _get_ordering_condition(self, colname):
        order_type = 'DESC' if colname.startswith('-') else 'ASC'
        colname = colname.replace('-', '')

        return colname, order_type

    def order_by(self, *colnames):
        """
        orders the result set.
        ordering can only use clustering columns.

        Default order is ascending, prepend a '-' to the column name for descending
        """
        if len(colnames) == 0:
            clone = copy.deepcopy(self)
            clone._order = []
            return clone

        conditions = []
        for colname in colnames:
            conditions.append(
                '"{}" {}'.format(*self._get_ordering_condition(colname)))

        clone = copy.deepcopy(self)
        clone._order.extend(conditions)
        return clone

    def count(self):
        """ Returns the number of rows matched by this query """
        if self._batch:
            raise CQLEngineException(
                "Only inserts, updates, and deletes are available in batch mode")
        # TODO: check for previous query execution and return row count if it
        # exists
        if self._result_cache is None:
            qs = ['SELECT COUNT(*)']
            qs += ['FROM {}'.format(self.column_family_name)]
            if self._where:
                qs += ['WHERE {}'.format(self._where_clause())]
            if self._allow_filtering:
                qs += ['ALLOW FILTERING']

            qs = ' '.join(qs)

            result = execute(qs, self._where_values())
            return result[0][0]
        else:
            return len(self._result_cache)

    def limit(self, v):
        """
        Sets the limit on the number of results returned
        CQL has a default limit of 10,000
        """
        if not (v is None or isinstance(v, (int, long))):
            raise TypeError
        if v == self._limit:
            return self

        if v < 0:
            raise QueryException("Negative limit is not allowed")

        clone = copy.deepcopy(self)
        clone._limit = v
        return clone

    def allow_filtering(self):
        """
        Enables the unwise practive of querying on a clustering
        key without also defining a partition key
        """
        clone = copy.deepcopy(self)
        clone._allow_filtering = True
        return clone

    def _only_or_defer(self, action, fields):
        clone = copy.deepcopy(self)
        if clone._defer_fields or clone._only_fields:
            raise QueryException(
                "QuerySet alread has only or defer fields defined")

        # check for strange fields
        missing_fields = [
            f for f in fields if f not in self.model._columns.keys()]
        if missing_fields:
            raise QueryException(
                "Can't resolve fields {} in {}".format(
                    ', '.join(missing_fields), self.model.__name__))

        if action == 'defer':
            clone._defer_fields = fields
        elif action == 'only':
            clone._only_fields = fields
        else:
            raise ValueError

        return clone

    def only(self, fields):
        """ Load only these fields for the returned query """
        return self._only_or_defer('only', fields)

    def defer(self, fields):
        """ Don't load these fields for the returned query """
        return self._only_or_defer('defer', fields)

    def create(self, **kwargs):
        return self.model(**kwargs).batch(self._batch).save()

    #----delete---
    def delete(self, columns=[]):
        """
        Deletes the contents of a query
        """
        # validate where clause
        partition_key = self.model._primary_keys.values()[0]
        if not any([c.column.db_field_name == partition_key.db_field_name for c in self._where]):
            raise QueryException(
                "The partition key must be defined on delete queries")
        qs = ['DELETE FROM {}'.format(self.column_family_name)]
        qs += ['WHERE {}'.format(self._where_clause())]
        qs = ' '.join(qs)

        if self._batch:
            self._batch.add_query(qs, self._where_values())
        else:
            execute(qs, self._where_values())

    def __eq__(self, q):
        return set(self._where) == set(q._where)

    def __ne__(self, q):
        return not (self != q)


class ResultObject(dict):

    """
    adds attribute access to a dictionary
    """

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError


class SimpleQuerySet(AbstractQuerySet):

    """

    """

    def _get_select_statement(self):
        """ Returns the fields to be returned by the select query """
        return 'SELECT *'

    def _get_result_constructor(self, names):
        """
        Returns a function that will be used to instantiate query results
        """
        def _construct_instance(values):
            return ResultObject([(name, getattr(values, name)) for name in names])
        return _construct_instance


class ModelQuerySet(AbstractQuerySet):

    """

    """

    def _validate_where_syntax(self):
        """ Checks that a filterset will not create invalid cql """

        # check that there's either a = or IN relationship with a primary key
        # or indexed field
        equal_ops = [w for w in self._where if isinstance(w, EqualsOperator)]
        token_ops = [w for w in self._where if isinstance(w.value, Token)]
        if not any([w.column.primary_key or w.column.index for w in equal_ops]) and not token_ops:
            raise QueryException(
                'Where clauses require either a "=" or "IN" comparison with either a primary key or indexed field')

        if not self._allow_filtering:
            # if the query is not on an indexed field
            if not any([w.column.index for w in equal_ops]):
                if not any([w.column.partition_key for w in equal_ops]) and not token_ops:
                    raise QueryException(
                        'Filtering on a clustering key without a partition key is not allowed unless allow_filtering() is called on the querset')
            if any(not w.column.partition_key for w in token_ops):
                raise QueryException(
                    'The token() function is only supported on the partition key')

                # TODO: abuse this to see if we can get cql to raise an
                # exception
    def _where_clause(self):
        """ Returns a where clause based on the given filter args """
        self._validate_where_syntax()
        return super(ModelQuerySet, self)._where_clause()

    def _get_select_statement(self):
        """ Returns the fields to be returned by the select query """
        fields = self.model._columns.keys()
        if self._defer_fields:
            fields = [f for f in fields if f not in self._defer_fields]
        elif self._only_fields:
            fields = self._only_fields
        db_fields = [self.model._columns[f].db_field_name for f in fields]
        return 'SELECT {}'.format(', '.join(['"{}"'.format(f) for f in db_fields]))

    def _get_instance_constructor(self, names):
        """ returns a function used to construct model instances """
        model = self.model
        db_map = model._db_map

        def _construct_instance(values):
            field_dict = dict(
                (db_map.get(field, field), getattr(values, field)) for field in names)
            instance = model(**field_dict)
            instance._is_persisted = True
            return instance
        return _construct_instance

    def _get_result_constructor(self, names):
        """ Returns a function that will be used to instantiate query results """
        if not self._values_list:
            return self._get_instance_constructor(names)
        else:
            columns = [self.model._columns[n] for n in names]
            if self._flat_values_list:
                return lambda values: columns[0].to_python(values[0])
            else:
                return lambda values: map(lambda (c, v): c.to_python(v), zip(columns, values))

    def _get_ordering_condition(self, colname):
        colname, order_type = super(
            ModelQuerySet, self)._get_ordering_condition(colname)

        column = self.model._columns.get(colname)
        if column is None:
            raise QueryException(
                "Can't resolve the column name: '{}'".format(colname))

        # validate the column selection
        if not column.primary_key:
            raise QueryException(
                "Can't order on '{}', can only order on (clustered) primary keys".format(colname))

        pks = [v for k, v in self.model._columns.items() if v.primary_key]
        if column == pks[0]:
            raise QueryException(
                "Can't order by the first primary key (partition key), clustering (secondary) keys only")

        return column.db_field_name, order_type

    def values_list(self, *fields, **kwargs):
        """ Instructs the query set to return tuples, not model instance """
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                            % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError(
                "'flat' is not valid when values_list is called with more than one field.")
        clone = self.only(fields)
        clone._values_list = True
        clone._flat_values_list = flat
        return clone

    def get_model_columns(self):
        return self.model._columns

    def get_parametrized_insert_cql_query(self):
        column_names = [
            col.db_field_name for col in self.get_model_columns().values()]
        query_def = dict(
            column_family=self.model.column_family_name(),
            column_def=', '.join(column_names),
            param_def=', '.join('?' * len(column_names))
        )
        return "INSERT INTO %(column_family)s (%(column_def)s) VALUES (%(param_def)s)" % query_def

    def get_insert_parameters(self, model_instance):
        dbvalues = []
        for name in self.get_model_columns().keys():
            dbvalues.append(getattr(model_instance, name))
        return dbvalues

    def batch_insert(self, instances, batch_size, atomic=True):
        if self._batch:
            raise CQLEngineException(
                'you cant mix BatchQuery and batch inserts together')

        connection_pool = get_connection_pool()
        insert_queries_count = len(instances)
        query_per_batch = min(batch_size, insert_queries_count)

        insert_query = self.get_parametrized_insert_cql_query()

        if atomic:
            batch_query = """
                BEGIN BATCH
                {}
                APPLY BATCH;
            """
        else:
            batch_query = """
                BEGIN UNLOGGED BATCH
                {}
                APPLY BATCH;
            """

        prepared_query = connection_pool.prepare(
            batch_query.format(insert_query * query_per_batch)
        )

        results = []
        insert_chunks = chunks(instances, query_per_batch)
        for insert_chunk in insert_chunks:
            params = sum([self.get_insert_parameters(m)
                         for m in insert_chunk], [])
            if len(insert_chunk) == query_per_batch:
                results.append(
                    connection_pool.execute_async(prepared_query.bind(params)))
            elif len(insert_chunk) > 0:
                cleanup_prepared_query = connection_pool.prepare(
                    batch_query.format(insert_query * len(insert_chunk))
                )
                results.append(
                    connection_pool.execute_async(cleanup_prepared_query.bind(params)))

        # block until results are returned
        for r in results:
            r.result()


class DMLQuery(object):

    """
    A query object used for queries performing inserts, updates, or deletes

    this is usually instantiated by the model instance to be modified

    unlike the read query object, this is mutable
    """

    def __init__(self, model, instance=None, batch=None):
        self.model = model
        self.column_family_name = self.model.column_family_name()
        self.instance = instance
        self._batch = batch
        pass

    def batch(self, batch_obj):
        if batch_obj is not None and not isinstance(batch_obj, BatchQuery):
            raise CQLEngineException(
                'batch_obj must be a BatchQuery instance or None')
        self._batch = batch_obj
        return self

    def save(self):
        """
        Creates / updates a row.
        This is a blind insert call.
        All validation and cleaning needs to happen
        prior to calling this.
        """
        if self.instance is None:
            raise CQLEngineException("DML Query intance attribute is None")
        assert type(self.instance) == self.model

        # organize data
        value_pairs = []
        values = self.instance._as_dict()

        # get defined fields and their column names
        for name, col in self.model._columns.items():
            val = values.get(name)
            if val is None:
                continue
            value_pairs += [(col.db_field_name, val)]

        # construct query string
        field_names = zip(*value_pairs)[0]
        field_ids = {n: uuid4().hex for n in field_names}
        field_values = dict(value_pairs)
        query_values = {field_ids[n]: field_values[n] for n in field_names}

        qs = []
        if self.instance._has_counter or self.instance._can_update():
            qs += ["UPDATE {}".format(self.column_family_name)]
            qs += ["SET"]

            set_statements = []
            # get defined fields and their column names
            for name, col in self.model._columns.items():
                if not col.is_primary_key:
                    val = values.get(name)
                    if val is None:
                        continue
                    if isinstance(col, (BaseContainerColumn, Counter)):
                        # remove value from query values, the column will
                        # handle it
                        query_values.pop(field_ids.get(name), None)

                        val_mgr = self.instance._values[name]
                        set_statements += col.get_update_statement(
                            val, val_mgr.previous_value, query_values)

                    else:
                        set_statements += [
                            '"{}" = %({})s'.format(col.db_field_name, field_ids[col.db_field_name])]
            qs += [', '.join(set_statements)]

            qs += ['WHERE']

            where_statements = []
            for name, col in self.model._primary_keys.items():
                where_statements += ['"{}" = %({})s'.format(col.db_field_name,
                                                            field_ids[col.db_field_name])]

            qs += [' AND '.join(where_statements)]

            # clear the qs if there are no set statements and this is not a
            # counter model
            if not set_statements and not self.instance._has_counter:
                qs = []

        else:
            qs += ["INSERT INTO {}".format(self.column_family_name)]
            qs += ["({})".format(', '.join(['"{}"'.format(f)
                                            for f in field_names]))]
            qs += ['VALUES']
            qs += ["({})".format(', '.join(['%(' + field_ids[f] + ')s' for f in field_names]))]

        qs = ' '.join(qs)

        # skip query execution if it's empty
        # caused by pointless update queries
        if qs:
            if self._batch:
                self._batch.add_query(qs, query_values)
            else:
                execute(qs, query_values)

        # delete nulled columns and removed map keys
        qs = ['DELETE']
        query_values = {}

        del_statements = []
        for k, v in self.instance._values.items():
            col = v.column
            if v.deleted:
                del_statements += ['"{}"'.format(col.db_field_name)]
            elif isinstance(col, Map):
                del_statements += col.get_delete_statement(
                    v.value, v.previous_value, query_values)

        if del_statements:
            qs += [', '.join(del_statements)]

            qs += ['FROM {}'.format(self.column_family_name)]

            qs += ['WHERE']
            where_statements = []
            for name, col in self.model._primary_keys.items():
                field_id = uuid4().hex
                query_values[field_id] = field_values[name]
                where_statements += [
                    '"{}" = %({})s'.format(col.db_field_name, field_id)]
            qs += [' AND '.join(where_statements)]

            qs = ' '.join(qs)

            if self._batch:
                self._batch.add_query(qs, query_values)
            else:
                execute(qs, query_values)

    def delete(self):
        """ Deletes one instance """
        if self.instance is None:
            raise CQLEngineException("DML Query intance attribute is None")
        field_values = {}
        qs = ['DELETE FROM {}'.format(self.column_family_name)]
        qs += ['WHERE']
        where_statements = []
        for name, col in self.model._primary_keys.items():
            field_id = uuid4().hex
            field_values[field_id] = getattr(self.instance, name)
            where_statements += ['"{}" = %({})s'.format(col.db_field_name,
                                                        field_id)]

        qs += [' AND '.join(where_statements)]
        qs = ' '.join(qs)

        if self._batch:
            self._batch.add_query(qs, field_values)
        else:
            execute(qs, field_values)

########NEW FILE########
__FILENAME__ = base
from unittest import TestCase
from cqlengine import connection
import os


if os.environ.get('CASSANDRA_TEST_HOST'):
    CASSANDRA_TEST_HOST = os.environ['CASSANDRA_TEST_HOST']
else:
    CASSANDRA_TEST_HOST = 'localhost:9160'


class BaseCassEngTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseCassEngTestCase, cls).setUpClass()
        connection.setup(
            [CASSANDRA_TEST_HOST], default_keyspace='cqlengine_test')

    def assertHasAttr(self, obj, attr):
        self.assertTrue(hasattr(obj, attr),
                        "{} doesn't have attribute: {}".format(obj, attr))

    def assertNotHasAttr(self, obj, attr):
        self.assertFalse(hasattr(obj, attr),
                         "{} shouldn't have the attribute: {}".format(obj, attr))

########NEW FILE########
__FILENAME__ = test_container_columns
from datetime import datetime, timedelta
import json
from uuid import uuid4

from cqlengine import Model, ValidationError
from cqlengine import columns
from cqlengine.management import create_table, delete_table
from cqlengine.tests.base import BaseCassEngTestCase


class TestSetModel(Model):
    partition = columns.UUID(primary_key=True, default=uuid4)
    int_set = columns.Set(columns.Integer, required=False)
    text_set = columns.Set(columns.Text, required=False)


class JsonTestColumn(columns.Column):
    db_type = 'text'

    def to_python(self, value):
        if value is None:
            return
        if isinstance(value, basestring):
            return json.loads(value)
        else:
            return value

    def to_database(self, value):
        if value is None:
            return
        return json.dumps(value)


class TestSetColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestSetColumn, cls).setUpClass()
        delete_table(TestSetModel)
        create_table(TestSetModel)

    @classmethod
    def tearDownClass(cls):
        super(TestSetColumn, cls).tearDownClass()
        delete_table(TestSetModel)

    def test_empty_set_initial(self):
        """
        tests that sets are set() by default, should never be none
        :return:
        """
        m = TestSetModel.create()
        m.int_set.add(5)
        m.save()

    def test_empty_set_retrieval(self):
        m = TestSetModel.create()
        m2 = TestSetModel.get(partition=m.partition)
        m2.int_set.add(3)

    def test_io_success(self):
        """ Tests that a basic usage works as expected """
        m1 = TestSetModel.create(int_set={1, 2}, text_set={'kai', 'andreas'})
        m2 = TestSetModel.get(partition=m1.partition)

        assert isinstance(m2.int_set, set)
        assert isinstance(m2.text_set, set)

        assert 1 in m2.int_set
        assert 2 in m2.int_set

        assert 'kai' in m2.text_set
        assert 'andreas' in m2.text_set

    def test_type_validation(self):
        """
        Tests that attempting to use the wrong types will raise an exception
        """
        with self.assertRaises(ValidationError):
            TestSetModel.create(int_set={'string', True}, text_set={1, 3.0})

    def test_partial_updates(self):
        """ Tests that partial udpates work as expected """
        m1 = TestSetModel.create(int_set={1, 2, 3, 4})

        m1.int_set.add(5)
        m1.int_set.remove(1)
        assert m1.int_set == {2, 3, 4, 5}

        m1.save()

        m2 = TestSetModel.get(partition=m1.partition)
        assert m2.int_set == {2, 3, 4, 5}

    def test_partial_update_creation(self):
        """
        Tests that proper update statements are created for a partial set update
        :return:
        """
        ctx = {}
        col = columns.Set(columns.Integer, db_field="TEST")
        statements = col.get_update_statement({1, 2, 3, 4}, {2, 3, 4, 5}, ctx)

        assert len([v for v in ctx.values() if {1} == v.value]) == 1
        assert len([v for v in ctx.values() if {5} == v.value]) == 1
        assert len([s for s in statements if '"TEST" = "TEST" -' in s]) == 1
        assert len([s for s in statements if '"TEST" = "TEST" +' in s]) == 1

    def test_update_from_none(self):
        """ Tests that updating an 'None' list creates a straight insert statement """
        ctx = {}
        col = columns.Set(columns.Integer, db_field="TEST")
        statements = col.get_update_statement({1, 2, 3, 4}, None, ctx)

        # only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == {1, 2, 3, 4}
        assert statements[0] == '"TEST" = {{}}'.format(ctx.keys()[0])

    def test_update_from_empty(self):
        """ Tests that updating an empty list creates a straight insert statement """
        ctx = {}
        col = columns.Set(columns.Integer, db_field="TEST")
        statements = col.get_update_statement({1, 2, 3, 4}, set(), ctx)

        # only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == {1, 2, 3, 4}
        assert statements[0] == '"TEST" = {{}}'.format(ctx.keys()[0])

    def test_instantiation_with_column_class(self):
        """
        Tests that columns instantiated with a column class work properly
        and that the class is instantiated in the constructor
        """
        column = columns.Set(columns.Text)
        assert isinstance(column.value_col, columns.Text)

    def test_instantiation_with_column_instance(self):
        """
        Tests that columns instantiated with a column instance work properly
        """
        column = columns.Set(columns.Text(min_length=100))
        assert isinstance(column.value_col, columns.Text)

    def test_to_python(self):
        """ Tests that to_python of value column is called """
        column = columns.Set(JsonTestColumn)
        val = {1, 2, 3}
        db_val = column.to_database(val)
        assert db_val.value == {json.dumps(v) for v in val}
        py_val = column.to_python(db_val.value)
        assert py_val == val


class TestListModel(Model):
    partition = columns.UUID(primary_key=True, default=uuid4)
    int_list = columns.List(columns.Integer, required=False)
    text_list = columns.List(columns.Text, required=False)


class TestListColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestListColumn, cls).setUpClass()
        delete_table(TestListModel)
        create_table(TestListModel)

    @classmethod
    def tearDownClass(cls):
        super(TestListColumn, cls).tearDownClass()
        delete_table(TestListModel)

    def test_initial(self):
        tmp = TestListModel.create()
        tmp.int_list.append(1)

    def test_initial(self):
        tmp = TestListModel.create()
        tmp2 = TestListModel.get(partition=tmp.partition)
        tmp2.int_list.append(1)

    def test_io_success(self):
        """ Tests that a basic usage works as expected """
        m1 = TestListModel.create(
            int_list=[1, 2], text_list=['kai', 'andreas'])
        m2 = TestListModel.get(partition=m1.partition)

        assert isinstance(m2.int_list, list)
        assert isinstance(m2.text_list, list)

        assert len(m2.int_list) == 2
        assert len(m2.text_list) == 2

        assert m2.int_list[0] == 1
        assert m2.int_list[1] == 2

        assert m2.text_list[0] == 'kai'
        assert m2.text_list[1] == 'andreas'

    def test_type_validation(self):
        """
        Tests that attempting to use the wrong types will raise an exception
        """
        with self.assertRaises(ValidationError):
            TestListModel.create(int_list=['string', True], text_list=[1, 3.0])

    def test_partial_updates(self):
        """ Tests that partial udpates work as expected """
        final = range(10)
        initial = final[3:7]
        m1 = TestListModel.create(int_list=initial)

        m1.int_list = final
        m1.save()

        m2 = TestListModel.get(partition=m1.partition)
        assert list(m2.int_list) == final

    def test_partial_update_creation(self):
        """ Tests that proper update statements are created for a partial list update """
        final = range(10)
        initial = final[3:7]

        ctx = {}
        col = columns.List(columns.Integer, db_field="TEST")
        statements = col.get_update_statement(final, initial, ctx)

        assert len([v for v in ctx.values() if [2, 1, 0] == v.value]) == 1
        assert len([v for v in ctx.values() if [7, 8, 9] == v.value]) == 1
        assert len([s for s in statements if '"TEST" = "TEST" +' in s]) == 1
        assert len([s for s in statements if '+ "TEST"' in s]) == 1

    def test_update_from_none(self):
        """ Tests that updating an 'None' list creates a straight insert statement """
        ctx = {}
        col = columns.List(columns.Integer, db_field="TEST")
        statements = col.get_update_statement([1, 2, 3], None, ctx)

        # only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == [1, 2, 3]
        assert statements[0] == '"TEST" = {}'.format(ctx.keys()[0])

    def test_update_from_empty(self):
        """ Tests that updating an empty list creates a straight insert statement """
        ctx = {}
        col = columns.List(columns.Integer, db_field="TEST")
        statements = col.get_update_statement([1, 2, 3], [], ctx)

        # only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == [1, 2, 3]
        assert statements[0] == '"TEST" = {}'.format(ctx.keys()[0])

    def test_instantiation_with_column_class(self):
        """
        Tests that columns instantiated with a column class work properly
        and that the class is instantiated in the constructor
        """
        column = columns.List(columns.Text)
        assert isinstance(column.value_col, columns.Text)

    def test_instantiation_with_column_instance(self):
        """
        Tests that columns instantiated with a column instance work properly
        """
        column = columns.List(columns.Text(min_length=100))
        assert isinstance(column.value_col, columns.Text)

    def test_to_python(self):
        """ Tests that to_python of value column is called """
        column = columns.List(JsonTestColumn)
        val = [1, 2, 3]
        db_val = column.to_database(val)
        assert db_val.value == [json.dumps(v) for v in val]
        py_val = column.to_python(db_val.value)
        assert py_val == val


class TestMapModel(Model):
    partition = columns.UUID(primary_key=True, default=uuid4)
    int_map = columns.Map(columns.Integer, columns.UUID, required=False)
    text_map = columns.Map(columns.Text, columns.DateTime, required=False)


class TestMapColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMapColumn, cls).setUpClass()
        delete_table(TestMapModel)
        create_table(TestMapModel)

    @classmethod
    def tearDownClass(cls):
        super(TestMapColumn, cls).tearDownClass()
        delete_table(TestMapModel)

    def test_empty_default(self):
        tmp = TestMapModel.create()
        tmp.int_map['blah'] = 1

    def test_empty_retrieve(self):
        tmp = TestMapModel.create()
        tmp2 = TestMapModel.get(partition=tmp.partition)
        tmp2.int_map['blah'] = 1

    def test_io_success(self):
        """ Tests that a basic usage works as expected """
        k1 = uuid4()
        k2 = uuid4()
        now = datetime.now()
        then = now + timedelta(days=1)
        m1 = TestMapModel.create(
            int_map={1: k1, 2: k2}, text_map={'now': now, 'then': then})
        m2 = TestMapModel.get(partition=m1.partition)

        assert isinstance(m2.int_map, dict)
        assert isinstance(m2.text_map, dict)

        assert 1 in m2.int_map
        assert 2 in m2.int_map
        assert m2.int_map[1] == k1
        assert m2.int_map[2] == k2

        assert 'now' in m2.text_map
        assert 'then' in m2.text_map
        assert (now - m2.text_map['now']).total_seconds() < 0.001
        assert (then - m2.text_map['then']).total_seconds() < 0.001

    def test_type_validation(self):
        """
        Tests that attempting to use the wrong types will raise an exception
        """
        with self.assertRaises(ValidationError):
            TestMapModel.create(
                int_map={'key': 2, uuid4(): 'val'}, text_map={2: 5})

    def test_partial_updates(self):
        """ Tests that partial udpates work as expected """
        now = datetime.now()
        # derez it a bit
        now = datetime(*now.timetuple()[:-3])
        early = now - timedelta(minutes=30)
        earlier = early - timedelta(minutes=30)
        later = now + timedelta(minutes=30)

        initial = {'now': now, 'early': earlier}
        final = {'later': later, 'early': early}

        m1 = TestMapModel.create(text_map=initial)

        m1.text_map = final
        m1.save()

        m2 = TestMapModel.get(partition=m1.partition)
        assert m2.text_map == final

    def test_updates_from_none(self):
        """ Tests that updates from None work as expected """
        m = TestMapModel.create(int_map=None)
        expected = {1: uuid4()}
        m.int_map = expected
        m.save()

        m2 = TestMapModel.get(partition=m.partition)
        assert m2.int_map == expected

    def test_updates_to_none(self):
        """ Tests that setting the field to None works as expected """
        m = TestMapModel.create(int_map={1: uuid4()})
        m.int_map = None
        m.save()

        m2 = TestMapModel.get(partition=m.partition)
        assert m2.int_map == {}

    def test_instantiation_with_column_class(self):
        """
        Tests that columns instantiated with a column class work properly
        and that the class is instantiated in the constructor
        """
        column = columns.Map(columns.Text, columns.Integer)
        assert isinstance(column.key_col, columns.Text)
        assert isinstance(column.value_col, columns.Integer)

    def test_instantiation_with_column_instance(self):
        """
        Tests that columns instantiated with a column instance work properly
        """
        column = columns.Map(columns.Text(min_length=100), columns.Integer())
        assert isinstance(column.key_col, columns.Text)
        assert isinstance(column.value_col, columns.Integer)

    def test_to_python(self):
        """ Tests that to_python of value column is called """
        column = columns.Map(JsonTestColumn, JsonTestColumn)
        val = {1: 2, 3: 4, 5: 6}
        db_val = column.to_database(val)
        assert db_val.value == {
            json.dumps(k): json.dumps(v) for k, v in val.items()}
        py_val = column.to_python(db_val.value)
        assert py_val == val

#    def test_partial_update_creation(self):
#        """
#        Tests that proper update statements are created for a partial list update
#        :return:
#        """
#        final = range(10)
#        initial = final[3:7]
#
#        ctx = {}
#        col = columns.List(columns.Integer, db_field="TEST")
#        statements = col.get_update_statement(final, initial, ctx)
#
#        assert len([v for v in ctx.values() if [0,1,2] == v.value]) == 1
#        assert len([v for v in ctx.values() if [7,8,9] == v.value]) == 1
#        assert len([s for s in statements if '"TEST" = "TEST" +' in s]) == 1
#        assert len([s for s in statements if '+ "TEST"' in s]) == 1

########NEW FILE########
__FILENAME__ = test_counter_column
from uuid import uuid4

from cqlengine import Model
from cqlengine import columns
from cqlengine.management import create_table, delete_table
from cqlengine.models import ModelDefinitionException
from cqlengine.tests.base import BaseCassEngTestCase


class TestCounterModel(Model):
    partition = columns.UUID(primary_key=True, default=uuid4)
    cluster = columns.UUID(primary_key=True, default=uuid4)
    counter = columns.Counter()


class TestClassConstruction(BaseCassEngTestCase):

    def test_defining_a_non_counter_column_fails(self):
        """ Tests that defining a non counter column field in a model with a counter column fails """
        with self.assertRaises(ModelDefinitionException):
            class model(Model):
                partition = columns.UUID(primary_key=True, default=uuid4)
                counter = columns.Counter()
                text = columns.Text()

    def test_defining_a_primary_key_counter_column_fails(self):
        """ Tests that defining primary keys on counter columns fails """
        with self.assertRaises(TypeError):
            class model(Model):
                partition = columns.UUID(primary_key=True, default=uuid4)
                cluster = columns.Counter(primary_ley=True)
                counter = columns.Counter()

        # force it
        with self.assertRaises(ModelDefinitionException):
            class model(Model):
                partition = columns.UUID(primary_key=True, default=uuid4)
                cluster = columns.Counter()
                cluster.primary_key = True
                counter = columns.Counter()


class TestCounterColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestCounterColumn, cls).setUpClass()
        delete_table(TestCounterModel)
        create_table(TestCounterModel)

    @classmethod
    def tearDownClass(cls):
        super(TestCounterColumn, cls).tearDownClass()
        delete_table(TestCounterModel)

    def test_updates(self):
        """ Tests that counter updates work as intended """
        instance = TestCounterModel.create()
        instance.counter += 5
        instance.save()

        actual = TestCounterModel.get(partition=instance.partition)
        assert actual.counter == 5

    def test_concurrent_updates(self):
        """ Tests updates from multiple queries reaches the correct value """
        instance = TestCounterModel.create()
        new1 = TestCounterModel.get(partition=instance.partition)
        new2 = TestCounterModel.get(partition=instance.partition)

        new1.counter += 5
        new1.save()
        new2.counter += 5
        new2.save()

        actual = TestCounterModel.get(partition=instance.partition)
        assert actual.counter == 10

    def test_update_from_none(self):
        """ Tests that updating from None uses a create statement """
        instance = TestCounterModel()
        instance.counter += 1
        instance.save()

        new = TestCounterModel.get(partition=instance.partition)
        assert new.counter == 1

    def test_new_instance_defaults_to_zero(self):
        """ Tests that instantiating a new model instance will set the counter column to zero """
        instance = TestCounterModel()
        assert instance.counter == 0

########NEW FILE########
__FILENAME__ = test_validation
# tests the behavior of the column classes
from datetime import datetime, timedelta
from datetime import date
from datetime import tzinfo
from decimal import Decimal as D
from unittest import TestCase
from uuid import uuid4, uuid1
from cqlengine import ValidationError

from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.columns import Column, TimeUUID
from cqlengine.columns import Bytes
from cqlengine.columns import Ascii
from cqlengine.columns import Text
from cqlengine.columns import Integer
from cqlengine.columns import VarInt
from cqlengine.columns import DateTime
from cqlengine.columns import Date
from cqlengine.columns import UUID
from cqlengine.columns import Boolean
from cqlengine.columns import Float
from cqlengine.columns import Decimal

from cqlengine.management import create_table, delete_table
from cqlengine.models import Model

import sys


class TestDatetime(BaseCassEngTestCase):

    class DatetimeTest(Model):
        test_id = Integer(primary_key=True)
        created_at = DateTime()

    @classmethod
    def setUpClass(cls):
        super(TestDatetime, cls).setUpClass()
        create_table(cls.DatetimeTest)

    @classmethod
    def tearDownClass(cls):
        super(TestDatetime, cls).tearDownClass()
        delete_table(cls.DatetimeTest)

    def test_datetime_io(self):
        now = datetime.now()
        dt = self.DatetimeTest.objects.create(test_id=0, created_at=now)
        dt2 = self.DatetimeTest.objects(test_id=0).first()
        assert dt2.created_at.timetuple()[:6] == now.timetuple()[:6]

    def test_datetime_tzinfo_io(self):
        class TZ(tzinfo):

            def utcoffset(self, date_time):
                return timedelta(hours=-1)

            def dst(self, date_time):
                return None

        now = datetime(1982, 1, 1, tzinfo=TZ())
        dt = self.DatetimeTest.objects.create(test_id=0, created_at=now)
        dt2 = self.DatetimeTest.objects(test_id=0).first()
        assert dt2.created_at.timetuple()[:6] == (
            now + timedelta(hours=1)).timetuple()[:6]

    def test_datetime_date_support(self):
        today = date.today()
        self.DatetimeTest.objects.create(test_id=0, created_at=today)
        dt2 = self.DatetimeTest.objects(test_id=0).first()
        assert dt2.created_at.isoformat() == datetime(
            today.year, today.month, today.day).isoformat()


class TestVarInt(BaseCassEngTestCase):

    class VarIntTest(Model):
        test_id = Integer(primary_key=True)
        bignum = VarInt(primary_key=True)

    @classmethod
    def setUpClass(cls):
        super(TestVarInt, cls).setUpClass()
        create_table(cls.VarIntTest)

    @classmethod
    def tearDownClass(cls):
        super(TestVarInt, cls).tearDownClass()
        delete_table(cls.VarIntTest)

    def test_varint_io(self):
        long_int = sys.maxint + 1
        int1 = self.VarIntTest.objects.create(test_id=0, bignum=long_int)
        int2 = self.VarIntTest.objects(test_id=0).first()
        assert int1.bignum == int2.bignum


class TestDate(BaseCassEngTestCase):

    class DateTest(Model):
        test_id = Integer(primary_key=True)
        created_at = Date()

    @classmethod
    def setUpClass(cls):
        super(TestDate, cls).setUpClass()
        create_table(cls.DateTest)

    @classmethod
    def tearDownClass(cls):
        super(TestDate, cls).tearDownClass()
        delete_table(cls.DateTest)

    def test_date_io(self):
        today = date.today()
        self.DateTest.objects.create(test_id=0, created_at=today)
        dt2 = self.DateTest.objects(test_id=0).first()
        assert dt2.created_at.isoformat() == today.isoformat()

    def test_date_io_using_datetime(self):
        now = datetime.utcnow()
        self.DateTest.objects.create(test_id=0, created_at=now)
        dt2 = self.DateTest.objects(test_id=0).first()
        assert not isinstance(dt2.created_at, datetime)
        assert isinstance(dt2.created_at, date)
        assert dt2.created_at.isoformat() == now.date().isoformat()


class TestDecimal(BaseCassEngTestCase):

    class DecimalTest(Model):
        test_id = Integer(primary_key=True)
        dec_val = Decimal()

    @classmethod
    def setUpClass(cls):
        super(TestDecimal, cls).setUpClass()
        create_table(cls.DecimalTest)

    @classmethod
    def tearDownClass(cls):
        super(TestDecimal, cls).tearDownClass()
        delete_table(cls.DecimalTest)

    def test_decimal_io(self):
        dt = self.DecimalTest.objects.create(test_id=0, dec_val=D('0.00'))
        dt2 = self.DecimalTest.objects(test_id=0).first()
        assert dt2.dec_val == dt.dec_val

        dt = self.DecimalTest.objects.create(test_id=0, dec_val=5)
        dt2 = self.DecimalTest.objects(test_id=0).first()
        assert dt2.dec_val == D('5')


class TestTimeUUID(BaseCassEngTestCase):

    class TimeUUIDTest(Model):
        test_id = Integer(primary_key=True)
        timeuuid = TimeUUID(default=uuid1())

    @classmethod
    def setUpClass(cls):
        super(TestTimeUUID, cls).setUpClass()
        create_table(cls.TimeUUIDTest)

    @classmethod
    def tearDownClass(cls):
        super(TestTimeUUID, cls).tearDownClass()
        delete_table(cls.TimeUUIDTest)

    def test_timeuuid_io(self):
        """
        ensures that
        :return:
        """
        t0 = self.TimeUUIDTest.create(test_id=0)
        t1 = self.TimeUUIDTest.get(test_id=0)

        assert t1.timeuuid.time == t1.timeuuid.time


class TestInteger(BaseCassEngTestCase):

    class IntegerTest(Model):
        test_id = UUID(primary_key=True, default=lambda: uuid4())
        value = Integer(default=0, required=True)

    def test_default_zero_fields_validate(self):
        """ Tests that integer columns with a default value of 0 validate """
        it = self.IntegerTest()
        it.validate()


class TestText(BaseCassEngTestCase):

    def test_min_length(self):
        # min len defaults to 1
        col = Text()
        col.validate('')

        col.validate('b')

        # test not required defaults to 0
        Text(required=False).validate('')

        # test arbitrary lengths
        Text(min_length=0).validate('')
        Text(min_length=5).validate('blake')
        Text(min_length=5).validate('blaketastic')
        with self.assertRaises(ValidationError):
            Text(min_length=6).validate('blake')

    def test_max_length(self):

        Text(max_length=5).validate('blake')
        with self.assertRaises(ValidationError):
            Text(max_length=5).validate('blaketastic')

    def test_type_checking(self):
        Text().validate('string')
        Text().validate(u'unicode')
        Text().validate(bytearray('bytearray'))

        with self.assertRaises(ValidationError):
            Text(required=True).validate(None)

        with self.assertRaises(ValidationError):
            Text().validate(5)

        with self.assertRaises(ValidationError):
            Text().validate(True)

    def test_non_required_validation(self):
        """ Tests that validation is ok on none and blank values if required is False """
        Text().validate('')
        Text().validate(None)


class TestExtraFieldsRaiseException(BaseCassEngTestCase):

    class TestModel(Model):
        id = UUID(primary_key=True, default=uuid4)

    def test_extra_field(self):
        with self.assertRaises(ValidationError):
            self.TestModel.create(bacon=5000)


class TestTimeUUIDFromDatetime(TestCase):

    def test_conversion_specific_date(self):
        dt = datetime(1981, 7, 11, microsecond=555000)

        uuid = TimeUUID.from_datetime(dt)

        from uuid import UUID
        assert isinstance(uuid, UUID)

        ts = (uuid.time - 0x01b21dd213814000) / 1e7  # back to a timestamp
        new_dt = datetime.utcfromtimestamp(ts)

        # checks that we created a UUID1 with the proper timestamp
        assert new_dt == dt

########NEW FILE########
__FILENAME__ = test_value_io
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid1, uuid4, UUID

from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.management import create_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine.columns import ValueQuoter
from cqlengine import columns
import unittest


class BaseColumnIOTest(BaseCassEngTestCase):

    """
    Tests that values are come out of cassandra in the format we expect

    To test a column type, subclass this test, define the column, and the primary key
    and data values you want to test
    """

    # The generated test model is assigned here
    _generated_model = None

    # the column we want to test
    column = None

    # the values we want to test against, you can
    # use a single value, or multiple comma separated values
    pkey_val = None
    data_val = None

    @classmethod
    def setUpClass(cls):
        super(BaseColumnIOTest, cls).setUpClass()

        # if the test column hasn't been defined, bail out
        if not cls.column:
            return

        # create a table with the given column
        class IOTestModel(Model):
            table_name = cls.column.db_type + \
                "_io_test_model_{}".format(uuid4().hex[:8])
            pkey = cls.column(primary_key=True)
            data = cls.column()
        cls._generated_model = IOTestModel
        create_table(cls._generated_model)

        # tupleify the tested values
        if not isinstance(cls.pkey_val, tuple):
            cls.pkey_val = cls.pkey_val,
        if not isinstance(cls.data_val, tuple):
            cls.data_val = cls.data_val,

    @classmethod
    def tearDownClass(cls):
        super(BaseColumnIOTest, cls).tearDownClass()
        if not cls.column:
            return
        delete_table(cls._generated_model)

    def comparator_converter(self, val):
        """ If you want to convert the original value used to compare the model vales """
        return val

    def test_column_io(self):
        """ Tests the given models class creates and retrieves values as expected """
        if not self.column:
            return
        for pkey, data in zip(self.pkey_val, self.data_val):
            # create
            m1 = self._generated_model.create(pkey=pkey, data=data)

            # get
            m2 = self._generated_model.get(pkey=pkey)
            assert m1.pkey == m2.pkey == self.comparator_converter(
                pkey), self.column
            assert m1.data == m2.data == self.comparator_converter(
                data), self.column

            # delete
            self._generated_model.filter(pkey=pkey).delete()


class TestBlobIO(BaseColumnIOTest):

    column = columns.Bytes
    pkey_val = 'blake', uuid4().bytes
    data_val = 'eggleston', uuid4().bytes


class TestTextIO(BaseColumnIOTest):

    column = columns.Text
    pkey_val = 'bacon'
    data_val = 'monkey'


class TestInteger(BaseColumnIOTest):

    column = columns.Integer
    pkey_val = 5
    data_val = 6


class TestDateTime(BaseColumnIOTest):

    column = columns.DateTime

    now = datetime(*datetime.now().timetuple()[:6])
    pkey_val = now
    data_val = now + timedelta(days=1)


class TestDate(BaseColumnIOTest):

    column = columns.Date

    now = datetime.now().date()
    pkey_val = now
    data_val = now + timedelta(days=1)


class TestUUID(BaseColumnIOTest):

    column = columns.UUID

    pkey_val = str(uuid4()), uuid4()
    data_val = str(uuid4()), uuid4()

    def comparator_converter(self, val):
        return val if isinstance(val, UUID) else UUID(val)


class TestTimeUUID(BaseColumnIOTest):

    column = columns.TimeUUID

    pkey_val = str(uuid1()), uuid1()
    data_val = str(uuid1()), uuid1()

    def comparator_converter(self, val):
        return val if isinstance(val, UUID) else UUID(val)


class TestBooleanIO(BaseColumnIOTest):

    column = columns.Boolean

    pkey_val = True
    data_val = False


class TestFloatIO(BaseColumnIOTest):

    column = columns.Float

    pkey_val = 3.14
    data_val = -1982.11


class TestDecimalIO(BaseColumnIOTest):

    column = columns.Decimal

    pkey_val = Decimal('1.35'), 5, '2.4'
    data_val = Decimal('0.005'), 3.5, '8'

    def comparator_converter(self, val):
        return Decimal(val)


class TestQuoter(unittest.TestCase):

    def test_equals(self):
        assert ValueQuoter(False) == ValueQuoter(False)
        assert ValueQuoter(1) == ValueQuoter(1)
        assert ValueQuoter("foo") == ValueQuoter("foo")
        assert ValueQuoter(1.55) == ValueQuoter(1.55)

########NEW FILE########
__FILENAME__ = test_connection_pool

########NEW FILE########
__FILENAME__ = test_compaction_settings
import copy
import json
from time import sleep
from mock import patch, MagicMock
from cqlengine import Model, columns, SizeTieredCompactionStrategy, LeveledCompactionStrategy
from cqlengine.exceptions import CQLEngineException
from cqlengine.management import get_compaction_options, drop_table, sync_table, get_table_settings
from cqlengine.tests.base import BaseCassEngTestCase


class CompactionModel(Model):
    __compaction__ = None
    cid = columns.UUID(primary_key=True)
    name = columns.Text()


class BaseCompactionTest(BaseCassEngTestCase):

    def assert_option_fails(self, key):
        # key is a normal_key, converted to
        # __compaction_key__

        key = "__compaction_{}__".format(key)

        with patch.object(self.model, key, 10), \
                self.assertRaises(CQLEngineException):
            get_compaction_options(self.model)


class SizeTieredCompactionTest(BaseCompactionTest):

    def setUp(self):
        self.model = copy.deepcopy(CompactionModel)
        self.model.__compaction__ = SizeTieredCompactionStrategy

    def test_size_tiered(self):
        result = get_compaction_options(self.model)
        assert result['class'] == SizeTieredCompactionStrategy

    def test_min_threshold(self):
        self.model.__compaction_min_threshold__ = 2
        result = get_compaction_options(self.model)
        assert result['min_threshold'] == 2


class LeveledCompactionTest(BaseCompactionTest):

    def setUp(self):
        self.model = copy.deepcopy(CompactionLeveledStrategyModel)

    def test_simple_leveled(self):
        result = get_compaction_options(self.model)
        assert result['class'] == LeveledCompactionStrategy

    def test_bucket_high_fails(self):
        self.assert_option_fails('bucket_high')

    def test_bucket_low_fails(self):
        self.assert_option_fails('bucket_low')

    def test_max_threshold_fails(self):
        self.assert_option_fails('max_threshold')

    def test_min_threshold_fails(self):
        self.assert_option_fails('min_threshold')

    def test_min_sstable_size_fails(self):
        self.assert_option_fails('min_sstable_size')

    def test_sstable_size_in_mb(self):
        with patch.object(self.model, '__compaction_sstable_size_in_mb__', 32):
            result = get_compaction_options(self.model)

        assert result['sstable_size_in_mb'] == 32


class LeveledcompactionTestTable(Model):
    __compaction__ = LeveledCompactionStrategy
    __compaction_sstable_size_in_mb__ = 64

    user_id = columns.UUID(primary_key=True)
    name = columns.Text()

from cqlengine.management import schema_columnfamilies


class AlterTableTest(BaseCassEngTestCase):

    def test_alter_is_called_table(self):
        drop_table(LeveledcompactionTestTable)
        sync_table(LeveledcompactionTestTable)
        with patch('cqlengine.management.update_compaction') as mock:
            sync_table(LeveledcompactionTestTable)
        assert mock.called == 1

    def test_alter_actually_alters(self):
        tmp = copy.deepcopy(LeveledcompactionTestTable)
        drop_table(tmp)
        sync_table(tmp)
        tmp.__compaction__ = SizeTieredCompactionStrategy
        tmp.__compaction_sstable_size_in_mb__ = None
        sync_table(tmp)

        table_settings = get_table_settings(tmp)

        self.assertRegexpMatches(
            table_settings['compaction_strategy_class'], '.*SizeTieredCompactionStrategy$')

    def test_alter_options(self):

        class AlterTable(Model):
            __compaction__ = LeveledCompactionStrategy
            __compaction_sstable_size_in_mb__ = 64

            user_id = columns.UUID(primary_key=True)
            name = columns.Text()

        drop_table(AlterTable)
        sync_table(AlterTable)
        AlterTable.__compaction_sstable_size_in_mb__ = 128
        sync_table(AlterTable)


class EmptyCompactionTest(BaseCassEngTestCase):

    def test_empty_compaction(self):
        class EmptyCompactionModel(Model):
            __compaction__ = None
            cid = columns.UUID(primary_key=True)
            name = columns.Text()

        result = get_compaction_options(EmptyCompactionModel)
        self.assertEqual({}, result)


class CompactionLeveledStrategyModel(Model):
    __compaction__ = LeveledCompactionStrategy
    cid = columns.UUID(primary_key=True)
    name = columns.Text()


class CompactionSizeTieredModel(Model):
    __compaction__ = SizeTieredCompactionStrategy
    cid = columns.UUID(primary_key=True)
    name = columns.Text()


class OptionsTest(BaseCassEngTestCase):

    def test_all_size_tiered_options(self):
        class AllSizeTieredOptionsModel(Model):
            __compaction__ = SizeTieredCompactionStrategy
            __compaction_bucket_low__ = .3
            __compaction_bucket_high__ = 2
            __compaction_min_threshold__ = 2
            __compaction_max_threshold__ = 64
            __compaction_tombstone_compaction_interval__ = 86400

            cid = columns.UUID(primary_key=True)
            name = columns.Text()

        drop_table(AllSizeTieredOptionsModel)
        sync_table(AllSizeTieredOptionsModel)

        settings = get_table_settings(AllSizeTieredOptionsModel)
        options = json.loads(settings['compaction_strategy_options'])
        expected = {u'min_threshold': u'2',
                    u'bucket_low': u'0.3',
                    u'tombstone_compaction_interval': u'86400',
                    u'bucket_high': u'2',
                    u'max_threshold': u'64'}
        self.assertDictEqual(options, expected)

    def test_all_leveled_options(self):

        class AllLeveledOptionsModel(Model):
            __compaction__ = LeveledCompactionStrategy
            __compaction_sstable_size_in_mb__ = 64

            cid = columns.UUID(primary_key=True)
            name = columns.Text()

        drop_table(AllLeveledOptionsModel)
        sync_table(AllLeveledOptionsModel)

        settings = get_table_settings(AllLeveledOptionsModel)
        options = json.loads(settings['compaction_strategy_options'])
        self.assertDictEqual(options, {u'sstable_size_in_mb': u'64'})

########NEW FILE########
__FILENAME__ = test_management
from cqlengine.management import create_table, delete_table, get_fields
from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine import management
from cqlengine.tests.query.test_queryset import TestModel
from cqlengine.models import Model
from cqlengine import columns


class CreateKeyspaceTest(BaseCassEngTestCase):

    def test_create_succeeeds(self):
        management.create_keyspace('test_keyspace')
        management.delete_keyspace('test_keyspace')


class DeleteTableTest(BaseCassEngTestCase):

    def test_multiple_deletes_dont_fail(self):
        """

        """
        create_table(TestModel)

        delete_table(TestModel)
        delete_table(TestModel)


class LowercaseKeyModel(Model):
    first_key = columns.Integer(primary_key=True)
    second_key = columns.Integer(primary_key=True)
    some_data = columns.Text()


class CapitalizedKeyModel(Model):
    firstKey = columns.Integer(primary_key=True)
    secondKey = columns.Integer(primary_key=True)
    someData = columns.Text()


class CapitalizedKeyTest(BaseCassEngTestCase):

    def test_table_definition(self):
        """ Tests that creating a table with capitalized column names succeedso """
        create_table(LowercaseKeyModel)
        create_table(CapitalizedKeyModel)

        delete_table(LowercaseKeyModel)
        delete_table(CapitalizedKeyModel)


class FirstModel(Model):
    __table_name__ = 'first_model'
    first_key = columns.UUID(primary_key=True)
    second_key = columns.UUID()
    third_key = columns.Text()


class SecondModel(Model):
    __table_name__ = 'first_model'
    first_key = columns.UUID(primary_key=True)
    second_key = columns.UUID()
    third_key = columns.Text()
    fourth_key = columns.Text()


class ThirdModel(Model):
    __table_name__ = 'first_model'
    first_key = columns.UUID(primary_key=True)
    second_key = columns.UUID()
    third_key = columns.Text()
    # removed fourth key, but it should stay in the DB
    blah = columns.Map(columns.Text, columns.Text)


class FourthModel(Model):
    __table_name__ = 'first_model'
    first_key = columns.UUID(primary_key=True)
    second_key = columns.UUID()
    third_key = columns.Text()
    # removed fourth key, but it should stay in the DB
    renamed = columns.Map(columns.Text, columns.Text, db_field='blah')


class AddColumnTest(BaseCassEngTestCase):

    def setUp(self):
        delete_table(FirstModel)

    def test_add_column(self):
        create_table(FirstModel)
        fields = get_fields(FirstModel)

        # this should contain the second key
        self.assertEqual(len(fields), 2)
        # get schema
        create_table(SecondModel)

        fields = get_fields(FirstModel)
        self.assertEqual(len(fields), 3)

        create_table(ThirdModel)
        fields = get_fields(FirstModel)
        self.assertEqual(len(fields), 4)

        create_table(FourthModel)
        fields = get_fields(FirstModel)
        self.assertEqual(len(fields), 4)

########NEW FILE########
__FILENAME__ = test_class_construction
from uuid import uuid4
from cqlengine.query import QueryException, ModelQuerySet, DMLQuery
from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.exceptions import ModelException, CQLEngineException
from cqlengine.models import Model, ModelDefinitionException, ColumnQueryEvaluator
from cqlengine import columns
import cqlengine


class TestModelClassFunction(BaseCassEngTestCase):

    """
    Tests verifying the behavior of the Model metaclass
    """

    def test_column_attributes_handled_correctly(self):
        """
        Tests that column attributes are moved to a _columns dict
        and replaced with simple value attributes
        """

        class TestModel(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            text = columns.Text()

        # check class attibutes
        self.assertHasAttr(TestModel, '_columns')
        self.assertHasAttr(TestModel, 'id')
        self.assertHasAttr(TestModel, 'text')

        # check instance attributes
        inst = TestModel()
        self.assertHasAttr(inst, 'id')
        self.assertHasAttr(inst, 'text')
        self.assertIsNone(inst.id)
        self.assertIsNone(inst.text)

    def test_db_map(self):
        """
        Tests that the db_map is properly defined
        -the db_map allows columns
        """
        class WildDBNames(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            content = columns.Text(db_field='words_and_whatnot')
            numbers = columns.Integer(db_field='integers_etc')

        db_map = WildDBNames._db_map
        self.assertEquals(db_map['words_and_whatnot'], 'content')
        self.assertEquals(db_map['integers_etc'], 'numbers')

    def test_attempting_to_make_duplicate_column_names_fails(self):
        """
        Tests that trying to create conflicting db column names will fail
        """

        with self.assertRaises(ModelException):
            class BadNames(Model):
                words = columns.Text()
                content = columns.Text(db_field='words')

    def test_column_ordering_is_preserved(self):
        """
        Tests that the _columns dics retains the ordering of the class definition
        """

        class Stuff(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            words = columns.Text()
            content = columns.Text()
            numbers = columns.Integer()

        self.assertEquals(
            Stuff._columns.keys(), ['id', 'words', 'content', 'numbers'])

    def test_exception_raised_when_creating_class_without_pk(self):
        with self.assertRaises(ModelDefinitionException):
            class TestModel(Model):
                count = columns.Integer()
                text = columns.Text(required=False)

    def test_value_managers_are_keeping_model_instances_isolated(self):
        """
        Tests that instance value managers are isolated from other instances
        """
        class Stuff(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            num = columns.Integer()

        inst1 = Stuff(num=5)
        inst2 = Stuff(num=7)

        self.assertNotEquals(inst1.num, inst2.num)
        self.assertEquals(inst1.num, 5)
        self.assertEquals(inst2.num, 7)

    def test_superclass_fields_are_inherited(self):
        """
        Tests that fields defined on the super class are inherited properly
        """
        class TestModel(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            text = columns.Text()

        class InheritedModel(TestModel):
            numbers = columns.Integer()

        assert 'text' in InheritedModel._columns
        assert 'numbers' in InheritedModel._columns

    def test_column_family_name_generation(self):
        """ Tests that auto column family name generation works as expected """
        class TestModel(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            text = columns.Text()

        assert TestModel.column_family_name(
            include_keyspace=False) == 'test_model'

    def test_normal_fields_can_be_defined_between_primary_keys(self):
        """
        Tests tha non primary key fields can be defined between primary key fields
        """

    def test_at_least_one_non_primary_key_column_is_required(self):
        """
        Tests that an error is raised if a model doesn't contain at least one primary key field
        """

    def test_model_keyspace_attribute_must_be_a_string(self):
        """
        Tests that users can't set the keyspace to None, or something else
        """

    def test_indexes_arent_allowed_on_models_with_multiple_primary_keys(self):
        """
        Tests that attempting to define an index on a model with multiple primary keys fails
        """

    def test_meta_data_is_not_inherited(self):
        """
        Test that metadata defined in one class, is not inherited by subclasses
        """

    def test_partition_keys(self):
        """
        Test compound partition key definition
        """
        class ModelWithPartitionKeys(cqlengine.Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            c1 = cqlengine.Text(primary_key=True)
            p1 = cqlengine.Text(partition_key=True)
            p2 = cqlengine.Text(partition_key=True)

        cols = ModelWithPartitionKeys._columns

        self.assertTrue(cols['c1'].primary_key)
        self.assertFalse(cols['c1'].partition_key)

        self.assertTrue(cols['p1'].primary_key)
        self.assertTrue(cols['p1'].partition_key)
        self.assertTrue(cols['p2'].primary_key)
        self.assertTrue(cols['p2'].partition_key)

        obj = ModelWithPartitionKeys(p1='a', p2='b')
        self.assertEquals(obj.pk, ('a', 'b'))

    def test_del_attribute_is_assigned_properly(self):
        """ Tests that columns that can be deleted have the del attribute """
        class DelModel(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())
            key = columns.Integer(primary_key=True)
            data = columns.Integer(required=False)

        model = DelModel(key=4, data=5)
        del model.data
        with self.assertRaises(AttributeError):
            del model.key

    def test_does_not_exist_exceptions_are_not_shared_between_model(self):
        """ Tests that DoesNotExist exceptions are not the same exception between models """

        class Model1(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())

        class Model2(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())

        try:
            raise Model1.DoesNotExist
        except Model2.DoesNotExist:
            assert False, "Model1 exception should not be caught by Model2"
        except Model1.DoesNotExist:
            # expected
            pass

    def test_does_not_exist_inherits_from_superclass(self):
        """ Tests that a DoesNotExist exception can be caught by it's parent class DoesNotExist """
        class Model1(Model):
            id = columns.UUID(primary_key=True, default=lambda: uuid4())

        class Model2(Model1):
            pass

        try:
            raise Model2.DoesNotExist
        except Model1.DoesNotExist:
            # expected
            pass
        except Exception:
            assert False, "Model2 exception should not be caught by Model1"


class TestManualTableNaming(BaseCassEngTestCase):

    class RenamedTest(cqlengine.Model):
        __keyspace__ = 'whatever'
        __table_name__ = 'manual_name'

        id = cqlengine.UUID(primary_key=True)
        data = cqlengine.Text()

    def test_proper_table_naming(self):
        assert self.RenamedTest.column_family_name(
            include_keyspace=False) == 'manual_name'
        assert self.RenamedTest.column_family_name(
            include_keyspace=True) == 'whatever.manual_name'


class AbstractModel(Model):
    __abstract__ = True


class ConcreteModel(AbstractModel):
    pkey = columns.Integer(primary_key=True)
    data = columns.Integer()


class AbstractModelWithCol(Model):
    __abstract__ = True
    pkey = columns.Integer(primary_key=True)


class ConcreteModelWithCol(AbstractModelWithCol):
    data = columns.Integer()


class AbstractModelWithFullCols(Model):
    __abstract__ = True
    pkey = columns.Integer(primary_key=True)
    data = columns.Integer()


class TestAbstractModelClasses(BaseCassEngTestCase):

    def test_id_field_is_not_created(self):
        """ Tests that an id field is not automatically generated on abstract classes """
        assert not hasattr(AbstractModel, 'id')
        assert not hasattr(AbstractModelWithCol, 'id')

    def test_id_field_is_not_created_on_subclass(self):
        assert not hasattr(ConcreteModel, 'id')

    def test_abstract_attribute_is_not_inherited(self):
        """ Tests that __abstract__ attribute is not inherited """
        assert not ConcreteModel.__abstract__
        assert not ConcreteModelWithCol.__abstract__

    def test_attempting_to_save_abstract_model_fails(self):
        """ Attempting to save a model from an abstract model should fail """
        with self.assertRaises(CQLEngineException):
            AbstractModelWithFullCols.create(pkey=1, data=2)

    def test_attempting_to_create_abstract_table_fails(self):
        """ Attempting to create a table from an abstract model should fail """
        from cqlengine.management import create_table
        with self.assertRaises(CQLEngineException):
            create_table(AbstractModelWithFullCols)

    def test_attempting_query_on_abstract_model_fails(self):
        """ Tests attempting to execute query with an abstract model fails """
        with self.assertRaises(CQLEngineException):
            iter(AbstractModelWithFullCols.objects(pkey=5)).next()

    def test_abstract_columns_are_inherited(self):
        """ Tests that columns defined in the abstract class are inherited into the concrete class """
        assert hasattr(ConcreteModelWithCol, 'pkey')
        assert isinstance(ConcreteModelWithCol.pkey, ColumnQueryEvaluator)
        assert isinstance(
            ConcreteModelWithCol._columns['pkey'], columns.Column)

    def test_concrete_class_table_creation_cycle(self):
        """ Tests that models with inherited abstract classes can be created, and have io performed """
        from cqlengine.management import create_table, delete_table
        create_table(ConcreteModelWithCol)

        w1 = ConcreteModelWithCol.create(pkey=5, data=6)
        w2 = ConcreteModelWithCol.create(pkey=6, data=7)

        r1 = ConcreteModelWithCol.get(pkey=5)
        r2 = ConcreteModelWithCol.get(pkey=6)

        assert w1.pkey == r1.pkey
        assert w1.data == r1.data
        assert w2.pkey == r2.pkey
        assert w2.data == r2.data

        delete_table(ConcreteModelWithCol)


class TestCustomQuerySet(BaseCassEngTestCase):

    """ Tests overriding the default queryset class """

    class TestException(Exception):
        pass

    def test_overriding_queryset(self):

        class QSet(ModelQuerySet):

            def create(iself, **kwargs):
                raise self.TestException

        class CQModel(Model):
            __queryset__ = QSet
            part = columns.UUID(primary_key=True)
            data = columns.Text()

        with self.assertRaises(self.TestException):
            CQModel.create(part=uuid4(), data='s')

    def test_overriding_dmlqueryset(self):

        class DMLQ(DMLQuery):

            def save(iself):
                raise self.TestException

        class CDQModel(Model):
            __dmlquery__ = DMLQ
            part = columns.UUID(primary_key=True)
            data = columns.Text()

        with self.assertRaises(self.TestException):
            CDQModel().save()

########NEW FILE########
__FILENAME__ = test_clustering_order
import random
from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.management import create_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine import columns


class TestModel(Model):
    id = columns.Integer(primary_key=True)
    clustering_key = columns.Integer(primary_key=True, clustering_order='desc')


class TestClusteringOrder(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestClusteringOrder, cls).setUpClass()
        create_table(TestModel)

    @classmethod
    def tearDownClass(cls):
        super(TestClusteringOrder, cls).tearDownClass()
        delete_table(TestModel)

    def test_clustering_order(self):
        """
        Tests that models can be saved and retrieved
        """
        items = list(range(20))
        random.shuffle(items)
        for i in items:
            TestModel.create(id=1, clustering_key=i)

        values = list(
            TestModel.objects.values_list('clustering_key', flat=True))
        self.assertEquals(values, sorted(items, reverse=True))

########NEW FILE########
__FILENAME__ = test_equality_operations
from unittest import skip
from uuid import uuid4
from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.management import create_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine import columns


class TestModel(Model):
    id = columns.UUID(primary_key=True, default=lambda: uuid4())
    count = columns.Integer()
    text = columns.Text(required=False)


class TestEqualityOperators(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestEqualityOperators, cls).setUpClass()
        create_table(TestModel)

    def setUp(self):
        super(TestEqualityOperators, self).setUp()
        self.t0 = TestModel.create(count=5, text='words')
        self.t1 = TestModel.create(count=5, text='words')

    @classmethod
    def tearDownClass(cls):
        super(TestEqualityOperators, cls).tearDownClass()
        delete_table(TestModel)

    def test_an_instance_evaluates_as_equal_to_itself(self):
        """
        """
        assert self.t0 == self.t0

    def test_two_instances_referencing_the_same_rows_and_different_values_evaluate_not_equal(self):
        """
        """
        t0 = TestModel.get(id=self.t0.id)
        t0.text = 'bleh'
        assert t0 != self.t0

    def test_two_instances_referencing_the_same_rows_and_values_evaluate_equal(self):
        """
        """
        t0 = TestModel.get(id=self.t0.id)
        assert t0 == self.t0

    def test_two_instances_referencing_different_rows_evaluate_to_not_equal(self):
        """
        """
        assert self.t0 != self.t1

########NEW FILE########
__FILENAME__ = test_model_io
from uuid import uuid4
import random
from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.management import create_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine import columns


class TestModel(Model):
    id = columns.UUID(primary_key=True, default=lambda: uuid4())
    count = columns.Integer()
    text = columns.Text(required=False)
    a_bool = columns.Boolean(default=False)


class TestModel(Model):
    id = columns.UUID(primary_key=True, default=lambda: uuid4())
    count = columns.Integer()
    text = columns.Text(required=False)
    a_bool = columns.Boolean(default=False)


class TestModelIO(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestModelIO, cls).setUpClass()
        create_table(TestModel)

    @classmethod
    def tearDownClass(cls):
        super(TestModelIO, cls).tearDownClass()
        delete_table(TestModel)

    def test_model_save_and_load(self):
        """
        Tests that models can be saved and retrieved
        """
        tm = TestModel.create(count=8, text='123456789')
        tm2 = TestModel.objects(id=tm.pk).first()

        for cname in tm._columns.keys():
            self.assertEquals(getattr(tm, cname), getattr(tm2, cname))

    def test_model_updating_works_properly(self):
        """
        Tests that subsequent saves after initial model creation work
        """
        tm = TestModel.objects.create(count=8, text='123456789')

        tm.count = 100
        tm.a_bool = True
        tm.save()

        tm2 = TestModel.objects(id=tm.pk).first()
        self.assertEquals(tm.count, tm2.count)
        self.assertEquals(tm.a_bool, tm2.a_bool)

    def test_model_deleting_works_properly(self):
        """
        Tests that an instance's delete method deletes the instance
        """
        tm = TestModel.create(count=8, text='123456789')
        tm.delete()
        tm2 = TestModel.objects(id=tm.pk).first()
        self.assertIsNone(tm2)

    def test_column_deleting_works_properly(self):
        """
        """
        tm = TestModel.create(count=8, text='123456789')
        tm.text = None
        tm.save()

        tm2 = TestModel.objects(id=tm.pk).first()
        assert tm2.text is None
        assert tm2._values['text'].previous_value is None

    def test_a_sensical_error_is_raised_if_you_try_to_create_a_table_twice(self):
        """
        """
        create_table(TestModel)
        create_table(TestModel)


class TestMultiKeyModel(Model):
    partition = columns.Integer(primary_key=True)
    cluster = columns.Integer(primary_key=True)
    count = columns.Integer(required=False)
    text = columns.Text(required=False)


class TestDeleting(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestDeleting, cls).setUpClass()
        delete_table(TestMultiKeyModel)
        create_table(TestMultiKeyModel)

    @classmethod
    def tearDownClass(cls):
        super(TestDeleting, cls).tearDownClass()
        delete_table(TestMultiKeyModel)

    def test_deleting_only_deletes_one_object(self):
        partition = random.randint(0, 1000)
        for i in range(5):
            TestMultiKeyModel.create(
                partition=partition, cluster=i, count=i, text=str(i))

        assert TestMultiKeyModel.filter(partition=partition).count() == 5

        TestMultiKeyModel.get(partition=partition, cluster=0).delete()

        assert TestMultiKeyModel.filter(partition=partition).count() == 4

        TestMultiKeyModel.filter(partition=partition).delete()


class TestUpdating(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestUpdating, cls).setUpClass()
        delete_table(TestMultiKeyModel)
        create_table(TestMultiKeyModel)

    @classmethod
    def tearDownClass(cls):
        super(TestUpdating, cls).tearDownClass()
        delete_table(TestMultiKeyModel)

    def setUp(self):
        super(TestUpdating, self).setUp()
        self.instance = TestMultiKeyModel.create(
            partition=random.randint(0, 1000),
            cluster=random.randint(0, 1000),
            count=0,
            text='happy'
        )

    def test_vanilla_update(self):
        self.instance.count = 5
        self.instance.save()

        check = TestMultiKeyModel.get(
            partition=self.instance.partition, cluster=self.instance.cluster)
        assert check.count == 5
        assert check.text == 'happy'

    def test_deleting_only(self):
        self.instance.count = None
        self.instance.text = None
        self.instance.save()

        check = TestMultiKeyModel.get(
            partition=self.instance.partition, cluster=self.instance.cluster)
        assert check.count is None
        assert check.text is None


class TestCanUpdate(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestCanUpdate, cls).setUpClass()
        delete_table(TestModel)
        create_table(TestModel)

    @classmethod
    def tearDownClass(cls):
        super(TestCanUpdate, cls).tearDownClass()
        delete_table(TestModel)

    def test_success_case(self):
        tm = TestModel(count=8, text='123456789')

        # object hasn't been saved,
        # shouldn't be able to update
        assert not tm._is_persisted
        assert not tm._can_update()

        tm.save()

        # object has been saved,
        # should be able to update
        assert tm._is_persisted
        assert tm._can_update()

        tm.count = 200

        # primary keys haven't changed,
        # should still be able to update
        assert tm._can_update()
        tm.save()

        tm.id = uuid4()

        # primary keys have changed,
        # should not be able to update
        assert not tm._can_update()


class IndexDefinitionModel(Model):
    key = columns.UUID(primary_key=True)
    val = columns.Text(index=True)


class TestIndexedColumnDefinition(BaseCassEngTestCase):

    def test_exception_isnt_raised_if_an_index_is_defined_more_than_once(self):
        create_table(IndexDefinitionModel)
        create_table(IndexDefinitionModel)


class ReservedWordModel(Model):
    token = columns.Text(primary_key=True)
    insert = columns.Integer(index=True)


class TestQueryQuoting(BaseCassEngTestCase):

    def test_reserved_cql_words_can_be_used_as_column_names(self):
        """
        """
        create_table(ReservedWordModel)

        model1 = ReservedWordModel.create(token='1', insert=5)

        model2 = ReservedWordModel.filter(token='1')

        assert len(model2) == 1
        assert model1.token == model2[0].token
        assert model1.insert == model2[0].insert

########NEW FILE########
__FILENAME__ = test_validation

########NEW FILE########
__FILENAME__ = test_batch_query
from datetime import datetime
from unittest import skip
from uuid import uuid4
import random
from cqlengine import Model, columns
from cqlengine.management import delete_table, create_table
from cqlengine.query import BatchQuery, DMLQuery
from cqlengine.tests.base import BaseCassEngTestCase


class TestMultiKeyModel(Model):
    partition = columns.Integer(primary_key=True)
    cluster = columns.Integer(primary_key=True)
    count = columns.Integer(required=False)
    text = columns.Text(required=False)


class BatchQueryTests(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BatchQueryTests, cls).setUpClass()
        delete_table(TestMultiKeyModel)
        create_table(TestMultiKeyModel)

    @classmethod
    def tearDownClass(cls):
        super(BatchQueryTests, cls).tearDownClass()
        delete_table(TestMultiKeyModel)

    def setUp(self):
        super(BatchQueryTests, self).setUp()
        self.pkey = 1
        for obj in TestMultiKeyModel.filter(partition=self.pkey):
            obj.delete()

    def test_insert_success_case(self):

        b = BatchQuery()
        inst = TestMultiKeyModel.batch(b).create(
            partition=self.pkey, cluster=2, count=3, text='4')

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_update_success_case(self):

        inst = TestMultiKeyModel.create(
            partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.count = 4
        inst.batch(b).save()

        inst2 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst2.count == 3

        b.execute()

        inst3 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst3.count == 4

    def test_delete_success_case(self):

        inst = TestMultiKeyModel.create(
            partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.batch(b).delete()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_context_manager(self):

        with BatchQuery() as b:
            for i in range(5):
                TestMultiKeyModel.batch(b).create(
                    partition=self.pkey, cluster=i, count=3, text='4')

            for i in range(5):
                with self.assertRaises(TestMultiKeyModel.DoesNotExist):
                    TestMultiKeyModel.get(partition=self.pkey, cluster=i)

        for i in range(5):
            TestMultiKeyModel.get(partition=self.pkey, cluster=i)

    def test_bulk_delete_success_case(self):

        for i in range(1):
            for j in range(5):
                TestMultiKeyModel.create(
                    partition=i, cluster=j, count=i * j, text='{}:{}'.format(i, j))

        with BatchQuery() as b:
            TestMultiKeyModel.objects.batch(b).filter(partition=0).delete()
            assert TestMultiKeyModel.filter(partition=0).count() == 5

        assert TestMultiKeyModel.filter(partition=0).count() == 0
        # cleanup
        for m in TestMultiKeyModel.all():
            m.delete()

    def test_none_success_case(self):
        """ Tests that passing None into the batch call clears any batch object """
        b = BatchQuery()

        q = TestMultiKeyModel.objects.batch(b)
        assert q._batch == b

        q = q.batch(None)
        assert q._batch is None

    def test_dml_none_success_case(self):
        """ Tests that passing None into the batch call clears any batch object """
        b = BatchQuery()

        q = DMLQuery(TestMultiKeyModel, batch=b)
        assert q._batch == b

        q.batch(None)
        assert q._batch is None

########NEW FILE########
__FILENAME__ = test_datetime_queries
from datetime import datetime, timedelta
from uuid import uuid4

from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.exceptions import ModelException
from cqlengine.management import create_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine import columns
from cqlengine import query


class DateTimeQueryTestModel(Model):
    user = columns.Integer(primary_key=True)
    day = columns.DateTime(primary_key=True)
    data = columns.Text()


class TestDateTimeQueries(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestDateTimeQueries, cls).setUpClass()
        create_table(DateTimeQueryTestModel)

        cls.base_date = datetime.now() - timedelta(days=10)
        for x in range(7):
            for y in range(10):
                DateTimeQueryTestModel.create(
                    user=x,
                    day=(cls.base_date + timedelta(days=y)),
                    data=str(uuid4())
                )

    @classmethod
    def tearDownClass(cls):
        super(TestDateTimeQueries, cls).tearDownClass()
        delete_table(DateTimeQueryTestModel)

    def test_range_query(self):
        """ Tests that loading from a range of dates works properly """
        start = datetime(*self.base_date.timetuple()[:3])
        end = start + timedelta(days=3)

        results = DateTimeQueryTestModel.filter(
            user=0, day__gte=start, day__lt=end)
        assert len(results) == 3

    def test_datetime_precision(self):
        """ Tests that millisecond resolution is preserved when saving datetime objects """
        now = datetime.now()
        pk = 1000
        obj = DateTimeQueryTestModel.create(
            user=pk, day=now, data='energy cheese')
        load = DateTimeQueryTestModel.get(user=pk)

        assert abs(now - load.day).total_seconds() < 0.001
        obj.delete()

########NEW FILE########
__FILENAME__ = test_named
from cqlengine import query
from cqlengine.named import NamedKeyspace
from cqlengine.query import ResultObject
from cqlengine.tests.query.test_queryset import BaseQuerySetUsage
from cqlengine.tests.base import BaseCassEngTestCase


class TestQuerySetOperation(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestQuerySetOperation, cls).setUpClass()
        cls.keyspace = NamedKeyspace('cqlengine_test')
        cls.table = cls.keyspace.table('test_model')

    def test_query_filter_parsing(self):
        """
        Tests the queryset filter method parses it's kwargs properly
        """
        query1 = self.table.objects(test_id=5)
        assert len(query1._where) == 1

        op = query1._where[0]
        assert isinstance(op, query.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(expected_result__gte=1)
        assert len(query2._where) == 2

        op = query2._where[1]
        assert isinstance(op, query.GreaterThanOrEqualOperator)
        assert op.value == 1

    def test_query_expression_parsing(self):
        """ Tests that query experessions are evaluated properly """
        query1 = self.table.filter(self.table.column('test_id') == 5)
        assert len(query1._where) == 1

        op = query1._where[0]
        assert isinstance(op, query.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(self.table.column('expected_result') >= 1)
        assert len(query2._where) == 2

        op = query2._where[1]
        assert isinstance(op, query.GreaterThanOrEqualOperator)
        assert op.value == 1

    def test_filter_method_where_clause_generation(self):
        """
        Tests the where clause creation
        """
        query1 = self.table.objects(test_id=5)
        ids = [o.query_value.identifier for o in query1._where]
        where = query1._where_clause()
        assert where == '"test_id" = %({})s'.format(*ids)

        query2 = query1.filter(expected_result__gte=1)
        ids = [o.query_value.identifier for o in query2._where]
        where = query2._where_clause()
        assert where == '"test_id" = %({})s AND "expected_result" >= %({})s'.format(
            *ids)

    def test_query_expression_where_clause_generation(self):
        """
        Tests the where clause creation
        """
        query1 = self.table.objects(self.table.column('test_id') == 5)
        ids = [o.query_value.identifier for o in query1._where]
        where = query1._where_clause()
        assert where == '"test_id" = %({})s'.format(*ids)

        query2 = query1.filter(self.table.column('expected_result') >= 1)
        ids = [o.query_value.identifier for o in query2._where]
        where = query2._where_clause()
        assert where == '"test_id" = %({})s AND "expected_result" >= %({})s'.format(
            *ids)


class TestQuerySetCountSelectionAndIteration(BaseQuerySetUsage):

    @classmethod
    def setUpClass(cls):
        super(TestQuerySetCountSelectionAndIteration, cls).setUpClass()

        from cqlengine.tests.query.test_queryset import TestModel

        ks, tn = TestModel.column_family_name().split('.')
        cls.keyspace = NamedKeyspace(ks)
        cls.table = cls.keyspace.table(tn)

    def test_count(self):
        """ Tests that adding filtering statements affects the count query as expected """
        assert self.table.objects.count() == 12

        q = self.table.objects(test_id=0)
        assert q.count() == 4

    def test_query_expression_count(self):
        """ Tests that adding query statements affects the count query as expected """
        assert self.table.objects.count() == 12

        q = self.table.objects(self.table.column('test_id') == 0)
        assert q.count() == 4

    def test_iteration(self):
        """ Tests that iterating over a query set pulls back all of the expected results """
        q = self.table.objects(test_id=0)
        # tuple of expected attempt_id, expected_result values
        compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
        for t in q:
            val = t.attempt_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with regular filtering
        q = self.table.objects(attempt_id=3).allow_filtering()
        assert len(q) == 3
        # tuple of expected test_id, expected_result values
        compare_set = set([(0, 20), (1, 20), (2, 75)])
        for t in q:
            val = t.test_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with query method
        q = self.table.objects(
            self.table.column('attempt_id') == 3).allow_filtering()
        assert len(q) == 3
        # tuple of expected test_id, expected_result values
        compare_set = set([(0, 20), (1, 20), (2, 75)])
        for t in q:
            val = t.test_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

    def test_multiple_iterations_work_properly(self):
        """ Tests that iterating over a query set more than once works """
        # test with both the filtering method and the query method
        for q in (self.table.objects(test_id=0), self.table.objects(self.table.column('test_id') == 0)):
            # tuple of expected attempt_id, expected_result values
            compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
            for t in q:
                val = t.attempt_id, t.expected_result
                assert val in compare_set
                compare_set.remove(val)
            assert len(compare_set) == 0

            # try it again
            compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
            for t in q:
                val = t.attempt_id, t.expected_result
                assert val in compare_set
                compare_set.remove(val)
            assert len(compare_set) == 0

    def test_multiple_iterators_are_isolated(self):
        """
        tests that the use of one iterator does not affect the behavior of another
        """
        for q in (self.table.objects(test_id=0), self.table.objects(self.table.column('test_id') == 0)):
            q = q.order_by('attempt_id')
            expected_order = [0, 1, 2, 3]
            iter1 = iter(q)
            iter2 = iter(q)
            for attempt_id in expected_order:
                assert iter1.next().attempt_id == attempt_id
                assert iter2.next().attempt_id == attempt_id

    def test_get_success_case(self):
        """
        Tests that the .get() method works on new and existing querysets
        """
        m = self.table.objects.get(test_id=0, attempt_id=0)
        assert isinstance(m, ResultObject)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = self.table.objects(test_id=0, attempt_id=0)
        m = q.get()
        assert isinstance(m, ResultObject)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = self.table.objects(test_id=0)
        m = q.get(attempt_id=0)
        assert isinstance(m, ResultObject)
        assert m.test_id == 0
        assert m.attempt_id == 0

    def test_query_expression_get_success_case(self):
        """
        Tests that the .get() method works on new and existing querysets
        """
        m = self.table.get(
            self.table.column('test_id') == 0, self.table.column('attempt_id') == 0)
        assert isinstance(m, ResultObject)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = self.table.objects(
            self.table.column('test_id') == 0, self.table.column('attempt_id') == 0)
        m = q.get()
        assert isinstance(m, ResultObject)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = self.table.objects(self.table.column('test_id') == 0)
        m = q.get(self.table.column('attempt_id') == 0)
        assert isinstance(m, ResultObject)
        assert m.test_id == 0
        assert m.attempt_id == 0

    def test_get_doesnotexist_exception(self):
        """
        Tests that get calls that don't return a result raises a DoesNotExist error
        """
        with self.assertRaises(self.table.DoesNotExist):
            self.table.objects.get(test_id=100)

    def test_get_multipleobjects_exception(self):
        """
        Tests that get calls that return multiple results raise a MultipleObjectsReturned error
        """
        with self.assertRaises(self.table.MultipleObjectsReturned):
            self.table.objects.get(test_id=1)

########NEW FILE########
__FILENAME__ = test_queryoperators
from datetime import datetime
import time

from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine import columns, Model
from cqlengine import functions
from cqlengine import query


class TestQuerySetOperation(BaseCassEngTestCase):

    def test_maxtimeuuid_function(self):
        """
        Tests that queries with helper functions are generated properly
        """
        now = datetime.now()
        col = columns.DateTime()
        col.set_column_name('time')
        qry = query.EqualsOperator(col, functions.MaxTimeUUID(now))

        assert qry.cql == '"time" = MaxTimeUUID(:{})'.format(
            qry.value.identifier)

    def test_mintimeuuid_function(self):
        """
        Tests that queries with helper functions are generated properly
        """
        now = datetime.now()
        col = columns.DateTime()
        col.set_column_name('time')
        qry = query.EqualsOperator(col, functions.MinTimeUUID(now))

        assert qry.cql == '"time" = MinTimeUUID(:{})'.format(
            qry.value.identifier)

    def test_token_function(self):

        class TestModel(Model):
            p1 = columns.Text(partition_key=True)
            p2 = columns.Text(partition_key=True)

        func = functions.Token('a', 'b')

        q = TestModel.objects.filter(pk__token__gt=func)
        self.assertEquals(
            q._where[0].cql, 'token("p1", "p2") > token(:{}, :{})'.format(*func.identifier))

        # Token(tuple()) is also possible for convinience
        # it (allows for Token(obj.pk) syntax)
        func = functions.Token(('a', 'b'))

        q = TestModel.objects.filter(pk__token__gt=func)
        self.assertEquals(
            q._where[0].cql, 'token("p1", "p2") > token(:{}, :{})'.format(*func.identifier))

########NEW FILE########
__FILENAME__ = test_queryset
from datetime import datetime
import time
from uuid import uuid1, uuid4

from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.exceptions import ModelException
from cqlengine import functions
from cqlengine.management import create_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine import columns
from cqlengine import query


class TestModel(Model):
    test_id = columns.Integer(primary_key=True)
    attempt_id = columns.Integer(primary_key=True)
    description = columns.Text()
    expected_result = columns.Integer()
    test_result = columns.Integer()


class IndexedTestModel(Model):
    test_id = columns.Integer(primary_key=True)
    attempt_id = columns.Integer(index=True)
    description = columns.Text()
    expected_result = columns.Integer()
    test_result = columns.Integer(index=True)


class TestMultiClusteringModel(Model):
    one = columns.Integer(primary_key=True)
    two = columns.Integer(primary_key=True)
    three = columns.Integer(primary_key=True)


class TestQuerySetOperation(BaseCassEngTestCase):

    def test_query_filter_parsing(self):
        """
        Tests the queryset filter method parses it's kwargs properly
        """
        query1 = TestModel.objects(test_id=5)
        assert len(query1._where) == 1

        op = query1._where[0]
        assert isinstance(op, query.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(expected_result__gte=1)
        assert len(query2._where) == 2

        op = query2._where[1]
        assert isinstance(op, query.GreaterThanOrEqualOperator)
        assert op.value == 1

    def test_query_expression_parsing(self):
        """ Tests that query experessions are evaluated properly """
        query1 = TestModel.filter(TestModel.test_id == 5)
        assert len(query1._where) == 1

        op = query1._where[0]
        assert isinstance(op, query.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(TestModel.expected_result >= 1)
        assert len(query2._where) == 2

        op = query2._where[1]
        assert isinstance(op, query.GreaterThanOrEqualOperator)
        assert op.value == 1

    def test_using_invalid_column_names_in_filter_kwargs_raises_error(self):
        """
        Tests that using invalid or nonexistant column names for filter args raises an error
        """
        with self.assertRaises(query.QueryException):
            TestModel.objects(nonsense=5)

    def test_using_nonexistant_column_names_in_query_args_raises_error(self):
        """
        Tests that using invalid or nonexistant columns for query args raises an error
        """
        with self.assertRaises(AttributeError):
            TestModel.objects(TestModel.nonsense == 5)

    def test_using_non_query_operators_in_query_args_raises_error(self):
        """
        Tests that providing query args that are not query operator instances raises an error
        """
        with self.assertRaises(query.QueryException):
            TestModel.objects(5)

    def test_filter_method_where_clause_generation(self):
        """
        Tests the where clause creation
        """
        query1 = TestModel.objects(test_id=5)
        ids = [o.query_value.identifier for o in query1._where]
        where = query1._where_clause()
        assert where == '"test_id" = %({})s'.format(*ids)

        query2 = query1.filter(expected_result__gte=1)
        ids = [o.query_value.identifier for o in query2._where]
        where = query2._where_clause()
        assert where == '"test_id" = %({})s AND "expected_result" >= %({})s'.format(
            *ids)

    def test_query_expression_where_clause_generation(self):
        """
        Tests the where clause creation
        """
        query1 = TestModel.objects(TestModel.test_id == 5)
        ids = [o.query_value.identifier for o in query1._where]
        where = query1._where_clause()
        assert where == '"test_id" = %({})s'.format(*ids)

        query2 = query1.filter(TestModel.expected_result >= 1)
        ids = [o.query_value.identifier for o in query2._where]
        where = query2._where_clause()
        assert where == '"test_id" = %({})s AND "expected_result" >= %({})s'.format(
            *ids)

    def test_querystring_generation(self):
        """
        Tests the select querystring creation
        """

    def test_queryset_is_immutable(self):
        """
        Tests that calling a queryset function that changes it's state returns a new queryset
        """
        query1 = TestModel.objects(test_id=5)
        assert len(query1._where) == 1

        query2 = query1.filter(expected_result__gte=1)
        assert len(query2._where) == 2
        assert len(query1._where) == 1

    def test_the_all_method_duplicates_queryset(self):
        """
        Tests that calling all on a queryset with previously defined filters duplicates queryset
        """
        query1 = TestModel.objects(test_id=5)
        assert len(query1._where) == 1

        query2 = query1.filter(expected_result__gte=1)
        assert len(query2._where) == 2

        query3 = query2.all()
        assert query3 == query2

    def test_defining_only_and_defer_fails(self):
        """
        Tests that trying to add fields to either only or defer, or doing so more than once fails
        """

    def test_defining_only_or_defer_on_nonexistant_fields_fails(self):
        """
        Tests that setting only or defer fields that don't exist raises an exception
        """


class BaseQuerySetUsage(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseQuerySetUsage, cls).setUpClass()
        delete_table(TestModel)
        delete_table(IndexedTestModel)
        create_table(TestModel)
        create_table(IndexedTestModel)
        create_table(TestMultiClusteringModel)

        TestModel.objects.create(
            test_id=0, attempt_id=0, description='try1', expected_result=5, test_result=30)
        TestModel.objects.create(
            test_id=0, attempt_id=1, description='try2', expected_result=10, test_result=30)
        TestModel.objects.create(
            test_id=0, attempt_id=2, description='try3', expected_result=15, test_result=30)
        TestModel.objects.create(
            test_id=0, attempt_id=3, description='try4', expected_result=20, test_result=25)

        TestModel.objects.create(
            test_id=1, attempt_id=0, description='try5', expected_result=5, test_result=25)
        TestModel.objects.create(
            test_id=1, attempt_id=1, description='try6', expected_result=10, test_result=25)
        TestModel.objects.create(
            test_id=1, attempt_id=2, description='try7', expected_result=15, test_result=25)
        TestModel.objects.create(
            test_id=1, attempt_id=3, description='try8', expected_result=20, test_result=20)

        TestModel.objects.create(
            test_id=2, attempt_id=0, description='try9', expected_result=50, test_result=40)
        TestModel.objects.create(
            test_id=2, attempt_id=1, description='try10', expected_result=60, test_result=40)
        TestModel.objects.create(
            test_id=2, attempt_id=2, description='try11', expected_result=70, test_result=45)
        TestModel.objects.create(
            test_id=2, attempt_id=3, description='try12', expected_result=75, test_result=45)

        IndexedTestModel.objects.create(
            test_id=0, attempt_id=0, description='try1', expected_result=5, test_result=30)
        IndexedTestModel.objects.create(
            test_id=1, attempt_id=1, description='try2', expected_result=10, test_result=30)
        IndexedTestModel.objects.create(
            test_id=2, attempt_id=2, description='try3', expected_result=15, test_result=30)
        IndexedTestModel.objects.create(
            test_id=3, attempt_id=3, description='try4', expected_result=20, test_result=25)

        IndexedTestModel.objects.create(
            test_id=4, attempt_id=0, description='try5', expected_result=5, test_result=25)
        IndexedTestModel.objects.create(
            test_id=5, attempt_id=1, description='try6', expected_result=10, test_result=25)
        IndexedTestModel.objects.create(
            test_id=6, attempt_id=2, description='try7', expected_result=15, test_result=25)
        IndexedTestModel.objects.create(
            test_id=7, attempt_id=3, description='try8', expected_result=20, test_result=20)

        IndexedTestModel.objects.create(
            test_id=8, attempt_id=0, description='try9', expected_result=50, test_result=40)
        IndexedTestModel.objects.create(
            test_id=9, attempt_id=1, description='try10', expected_result=60, test_result=40)
        IndexedTestModel.objects.create(
            test_id=10, attempt_id=2, description='try11', expected_result=70, test_result=45)
        IndexedTestModel.objects.create(
            test_id=11, attempt_id=3, description='try12', expected_result=75, test_result=45)

    @classmethod
    def tearDownClass(cls):
        super(BaseQuerySetUsage, cls).tearDownClass()
        delete_table(TestModel)
        delete_table(IndexedTestModel)
        delete_table(TestMultiClusteringModel)


class TestQuerySetCountSelectionAndIteration(BaseQuerySetUsage):

    def test_count(self):
        """ Tests that adding filtering statements affects the count query as expected """
        assert TestModel.objects.count() == 12

        q = TestModel.objects(test_id=0)
        assert q.count() == 4

    def test_query_expression_count(self):
        """ Tests that adding query statements affects the count query as expected """
        assert TestModel.objects.count() == 12

        q = TestModel.objects(TestModel.test_id == 0)
        assert q.count() == 4

    def test_iteration(self):
        """ Tests that iterating over a query set pulls back all of the expected results """
        q = TestModel.objects(test_id=0)
        # tuple of expected attempt_id, expected_result values
        compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
        for t in q:
            val = t.attempt_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with regular filtering
        q = TestModel.objects(attempt_id=3).allow_filtering()
        assert len(q) == 3
        # tuple of expected test_id, expected_result values
        compare_set = set([(0, 20), (1, 20), (2, 75)])
        for t in q:
            val = t.test_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with query method
        q = TestModel.objects(TestModel.attempt_id == 3).allow_filtering()
        assert len(q) == 3
        # tuple of expected test_id, expected_result values
        compare_set = set([(0, 20), (1, 20), (2, 75)])
        for t in q:
            val = t.test_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

    def test_multiple_iterations_work_properly(self):
        """ Tests that iterating over a query set more than once works """
        # test with both the filtering method and the query method
        for q in (TestModel.objects(test_id=0), TestModel.objects(TestModel.test_id == 0)):
            # tuple of expected attempt_id, expected_result values
            compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
            for t in q:
                val = t.attempt_id, t.expected_result
                assert val in compare_set
                compare_set.remove(val)
            assert len(compare_set) == 0

            # try it again
            compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
            for t in q:
                val = t.attempt_id, t.expected_result
                assert val in compare_set
                compare_set.remove(val)
            assert len(compare_set) == 0

    def test_multiple_iterators_are_isolated(self):
        """
        tests that the use of one iterator does not affect the behavior of another
        """
        for q in (TestModel.objects(test_id=0), TestModel.objects(TestModel.test_id == 0)):
            q = q.order_by('attempt_id')
            expected_order = [0, 1, 2, 3]
            iter1 = iter(q)
            iter2 = iter(q)
            for attempt_id in expected_order:
                assert iter1.next().attempt_id == attempt_id
                assert iter2.next().attempt_id == attempt_id

    def test_get_success_case(self):
        """
        Tests that the .get() method works on new and existing querysets
        """
        m = TestModel.objects.get(test_id=0, attempt_id=0)
        assert isinstance(m, TestModel)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = TestModel.objects(test_id=0, attempt_id=0)
        m = q.get()
        assert isinstance(m, TestModel)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = TestModel.objects(test_id=0)
        m = q.get(attempt_id=0)
        assert isinstance(m, TestModel)
        assert m.test_id == 0
        assert m.attempt_id == 0

    def test_query_expression_get_success_case(self):
        """
        Tests that the .get() method works on new and existing querysets
        """
        m = TestModel.get(TestModel.test_id == 0, TestModel.attempt_id == 0)
        assert isinstance(m, TestModel)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = TestModel.objects(
            TestModel.test_id == 0, TestModel.attempt_id == 0)
        m = q.get()
        assert isinstance(m, TestModel)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = TestModel.objects(TestModel.test_id == 0)
        m = q.get(TestModel.attempt_id == 0)
        assert isinstance(m, TestModel)
        assert m.test_id == 0
        assert m.attempt_id == 0

    def test_get_doesnotexist_exception(self):
        """
        Tests that get calls that don't return a result raises a DoesNotExist error
        """
        with self.assertRaises(TestModel.DoesNotExist):
            TestModel.objects.get(test_id=100)

    def test_get_multipleobjects_exception(self):
        """
        Tests that get calls that return multiple results raise a MultipleObjectsReturned error
        """
        with self.assertRaises(TestModel.MultipleObjectsReturned):
            TestModel.objects.get(test_id=1)

    def test_allow_filtering_flag(self):
        """
        """


class TestQuerySetOrdering(BaseQuerySetUsage):

    def test_order_by_success_case(self):

        q = TestModel.objects(test_id=0).order_by('attempt_id')
        expected_order = [0, 1, 2, 3]
        for model, expect in zip(q, expected_order):
            assert model.attempt_id == expect

        q = q.order_by('-attempt_id')
        expected_order.reverse()
        for model, expect in zip(q, expected_order):
            assert model.attempt_id == expect

    def test_ordering_by_non_second_primary_keys_fail(self):
        # kwarg filtering
        with self.assertRaises(query.QueryException):
            q = TestModel.objects(test_id=0).order_by('test_id')

        # kwarg filtering
        with self.assertRaises(query.QueryException):
            q = TestModel.objects(TestModel.test_id == 0).order_by('test_id')

    def test_ordering_by_non_primary_keys_fails(self):
        with self.assertRaises(query.QueryException):
            q = TestModel.objects(test_id=0).order_by('description')

    def test_ordering_on_indexed_columns_fails(self):
        with self.assertRaises(query.QueryException):
            q = IndexedTestModel.objects(test_id=0).order_by('attempt_id')

    def test_ordering_on_multiple_clustering_columns(self):
        TestMultiClusteringModel.create(one=1, two=1, three=4)
        TestMultiClusteringModel.create(one=1, two=1, three=2)
        TestMultiClusteringModel.create(one=1, two=1, three=5)
        TestMultiClusteringModel.create(one=1, two=1, three=1)
        TestMultiClusteringModel.create(one=1, two=1, three=3)

        results = TestMultiClusteringModel.objects.filter(
            one=1, two=1).order_by('-two', '-three')
        assert [r.three for r in results] == [5, 4, 3, 2, 1]

        results = TestMultiClusteringModel.objects.filter(
            one=1, two=1).order_by('two', 'three')
        assert [r.three for r in results] == [1, 2, 3, 4, 5]

        results = TestMultiClusteringModel.objects.filter(
            one=1, two=1).order_by('two').order_by('three')
        assert [r.three for r in results] == [1, 2, 3, 4, 5]


class TestQuerySetSlicing(BaseQuerySetUsage):

    def test_out_of_range_index_raises_error(self):
        q = TestModel.objects(test_id=0).order_by('attempt_id')
        with self.assertRaises(IndexError):
            q[10]

    def test_array_indexing_works_properly(self):
        q = TestModel.objects(test_id=0).order_by('attempt_id')
        expected_order = [0, 1, 2, 3]
        for i in range(len(q)):
            assert q[i].attempt_id == expected_order[i]

    def test_negative_indexing_works_properly(self):
        q = TestModel.objects(test_id=0).order_by('attempt_id')
        expected_order = [0, 1, 2, 3]
        assert q[-1].attempt_id == expected_order[-1]
        assert q[-2].attempt_id == expected_order[-2]

    def test_slicing_works_properly(self):
        q = TestModel.objects(test_id=0).order_by('attempt_id')
        expected_order = [0, 1, 2, 3]
        for model, expect in zip(q[1:3], expected_order[1:3]):
            assert model.attempt_id == expect

    def test_negative_slicing(self):
        q = TestModel.objects(test_id=0).order_by('attempt_id')
        expected_order = [0, 1, 2, 3]
        for model, expect in zip(q[-3:], expected_order[-3:]):
            assert model.attempt_id == expect
        for model, expect in zip(q[:-1], expected_order[:-1]):
            assert model.attempt_id == expect


class TestQuerySetValidation(BaseQuerySetUsage):

    def test_primary_key_or_index_must_be_specified(self):
        """
        Tests that queries that don't have an equals relation to a primary key or indexed field fail
        """
        with self.assertRaises(query.QueryException):
            q = TestModel.objects(test_result=25)
            list([i for i in q])

    def test_primary_key_or_index_must_have_equal_relation_filter(self):
        """
        Tests that queries that don't have non equal (>,<, etc) relation to a primary key or indexed field fail
        """
        with self.assertRaises(query.QueryException):
            q = TestModel.objects(test_id__gt=0)
            list([i for i in q])

    def test_indexed_field_can_be_queried(self):
        """
        Tests that queries on an indexed field will work without any primary key relations specified
        """
        q = IndexedTestModel.objects(test_result=25)
        assert q.count() == 4


class TestQuerySetDelete(BaseQuerySetUsage):

    def test_delete(self):
        TestModel.objects.create(
            test_id=3, attempt_id=0, description='try9', expected_result=50, test_result=40)
        TestModel.objects.create(
            test_id=3, attempt_id=1, description='try10', expected_result=60, test_result=40)
        TestModel.objects.create(
            test_id=3, attempt_id=2, description='try11', expected_result=70, test_result=45)
        TestModel.objects.create(
            test_id=3, attempt_id=3, description='try12', expected_result=75, test_result=45)

        assert TestModel.objects.count() == 16
        assert TestModel.objects(test_id=3).count() == 4

        TestModel.objects(test_id=3).delete()

        assert TestModel.objects.count() == 12
        assert TestModel.objects(test_id=3).count() == 0

    def test_delete_without_partition_key(self):
        """ Tests that attempting to delete a model without defining a partition key fails """
        with self.assertRaises(query.QueryException):
            TestModel.objects(attempt_id=0).delete()

    def test_delete_without_any_where_args(self):
        """ Tests that attempting to delete a whole table without any arguments will fail """
        with self.assertRaises(query.QueryException):
            TestModel.objects(attempt_id=0).delete()


class TestQuerySetConnectionHandling(BaseQuerySetUsage):

    def test_conn_is_returned_after_filling_cache(self):
        """
        Tests that the queryset returns it's connection after it's fetched all of it's results
        """
        q = TestModel.objects(test_id=0)
        # tuple of expected attempt_id, expected_result values
        compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
        for t in q:
            val = t.attempt_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)

        assert q._con is None
        assert q._cur is None


class TimeUUIDQueryModel(Model):
    partition = columns.UUID(primary_key=True)
    time = columns.TimeUUID(primary_key=True)
    data = columns.Text(required=False)


class TestMinMaxTimeUUIDFunctions(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMinMaxTimeUUIDFunctions, cls).setUpClass()
        create_table(TimeUUIDQueryModel)

    @classmethod
    def tearDownClass(cls):
        super(TestMinMaxTimeUUIDFunctions, cls).tearDownClass()
        delete_table(TimeUUIDQueryModel)

    def test_success_case(self):
        """ Test that the min and max time uuid functions work as expected """
        pk = uuid4()
        TimeUUIDQueryModel.create(partition=pk, time=uuid1(), data='1')
        time.sleep(0.2)
        TimeUUIDQueryModel.create(partition=pk, time=uuid1(), data='2')
        time.sleep(0.2)
        midpoint = datetime.utcnow()
        time.sleep(0.2)
        TimeUUIDQueryModel.create(partition=pk, time=uuid1(), data='3')
        time.sleep(0.2)
        TimeUUIDQueryModel.create(partition=pk, time=uuid1(), data='4')
        time.sleep(0.2)

        # test kwarg filtering
        q = TimeUUIDQueryModel.filter(
            partition=pk, time__lte=functions.MaxTimeUUID(midpoint))
        q = [d for d in q]
        assert len(q) == 2
        datas = [d.data for d in q]
        assert '1' in datas
        assert '2' in datas

        q = TimeUUIDQueryModel.filter(
            partition=pk, time__gte=functions.MinTimeUUID(midpoint))
        assert len(q) == 2
        datas = [d.data for d in q]
        assert '3' in datas
        assert '4' in datas

        # test query expression filtering
        q = TimeUUIDQueryModel.filter(
            TimeUUIDQueryModel.partition == pk,
            TimeUUIDQueryModel.time <= functions.MaxTimeUUID(midpoint)
        )
        q = [d for d in q]
        assert len(q) == 2
        datas = [d.data for d in q]
        assert '1' in datas
        assert '2' in datas

        q = TimeUUIDQueryModel.filter(
            TimeUUIDQueryModel.partition == pk,
            TimeUUIDQueryModel.time >= functions.MinTimeUUID(midpoint)
        )
        assert len(q) == 2
        datas = [d.data for d in q]
        assert '3' in datas
        assert '4' in datas


class TestInOperator(BaseQuerySetUsage):

    def test_kwarg_success_case(self):
        """ Tests the in operator works with the kwarg query method """
        q = TestModel.filter(test_id__in=[0, 1])
        assert q.count() == 8

    def test_query_expression_success_case(self):
        """ Tests the in operator works with the query expression query method """
        q = TestModel.filter(TestModel.test_id.in_([0, 1]))
        assert q.count() == 8


class TestValuesList(BaseQuerySetUsage):

    def test_values_list(self):
        q = TestModel.objects.filter(test_id=0, attempt_id=1)
        item = q.values_list(
            'test_id', 'attempt_id', 'description', 'expected_result', 'test_result').first()
        assert item == [0, 1, 'try2', 10, 30]

        item = q.values_list('expected_result', flat=True).first()
        assert item == 10


class TestObjectsProperty(BaseQuerySetUsage):

    def test_objects_property_returns_fresh_queryset(self):
        assert TestModel.objects._result_cache is None
        len(TestModel.objects)  # evaluate queryset
        assert TestModel.objects._result_cache is None

########NEW FILE########
__FILENAME__ = test_batch_query
from cqlengine import Model, columns
from cqlengine.management import delete_table, create_table
from cqlengine.query import BatchQuery
from cqlengine.tests.base import BaseCassEngTestCase


class TestMultiKeyModel(Model):
    partition = columns.Integer(primary_key=True)
    cluster = columns.Integer(primary_key=True)
    count = columns.Integer(required=False)
    text = columns.Text(required=False)


class BatchQueryTests(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BatchQueryTests, cls).setUpClass()
        delete_table(TestMultiKeyModel)
        create_table(TestMultiKeyModel)

    @classmethod
    def tearDownClass(cls):
        super(BatchQueryTests, cls).tearDownClass()
        delete_table(TestMultiKeyModel)

    def setUp(self):
        super(BatchQueryTests, self).setUp()
        self.pkey = 1
        for obj in TestMultiKeyModel.filter(partition=self.pkey):
            obj.delete()

    def test_insert_success_case(self):

        b = BatchQuery()
        TestMultiKeyModel.batch(b).create(
            partition=self.pkey, cluster=2, count=3, text='4')

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_update_success_case(self):

        inst = TestMultiKeyModel.create(
            partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.count = 4
        inst.batch(b).save()

        inst2 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst2.count == 3

        b.execute()

        inst3 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst3.count == 4

    def test_delete_success_case(self):

        inst = TestMultiKeyModel.create(
            partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.batch(b).delete()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_context_manager(self):

        with BatchQuery() as b:
            for i in range(5):
                TestMultiKeyModel.batch(b).create(
                    partition=self.pkey, cluster=i, count=3, text='4')

            for i in range(5):
                with self.assertRaises(TestMultiKeyModel.DoesNotExist):
                    TestMultiKeyModel.get(partition=self.pkey, cluster=i)

        for i in range(5):
            TestMultiKeyModel.get(partition=self.pkey, cluster=i)

    def test_bulk_delete_success_case(self):

        for i in range(1):
            for j in range(5):
                TestMultiKeyModel.create(
                    partition=i, cluster=j, count=i * j, text='{}:{}'.format(i, j))

        with BatchQuery() as b:
            TestMultiKeyModel.objects.batch(b).filter(partition=0).delete()
            assert TestMultiKeyModel.filter(partition=0).count() == 5

        assert TestMultiKeyModel.filter(partition=0).count() == 0
        # cleanup
        for m in TestMultiKeyModel.all():
            m.delete()

    def test_empty_batch(self):
        b = BatchQuery()
        b.execute()

        with BatchQuery() as b:
            pass

########NEW FILE########
__FILENAME__ = utils
import itertools


def chunks(iterable, n=10000):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Feedly documentation build configuration file, created by
# sphinx-quickstart on Tue Jul 16 18:07:58 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# on_rtd is whether we are on readthedocs.org
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# otherwise, readthedocs.org uses their theme by default, so no need to
# specify it

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Feedly'
copyright = u'2013, Thierry Schellenbach'

project_root = os.path.abspath('..')
example_path = os.path.abspath(os.path.join('..', 'pinterest_example'))
sys.path.append(example_path)
sys.path.append(project_root)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = ''

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'autumn'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
# html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Feedlydoc'


# -- Options for LaTeX output --------------------------------------------

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
    ('index', 'Feedly.tex', u'Feedly Documentation',
     u'Thierry Schellenbach', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output --------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'feedly', u'Feedly Documentation',
     [u'Thierry Schellenbach'], 1)
]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output ------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'Feedly', u'Feedly Documentation',
     u'Thierry Schellenbach', 'Feedly', 'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
# texinfo_appendices = []

# If false, no module index is generated.
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
# texinfo_no_detailmenu = False


# -- Options for Epub output ---------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Feedly'
epub_author = u'Thierry Schellenbach'
epub_publisher = u'Thierry Schellenbach'
epub_copyright = u'2013, Thierry Schellenbach'

# The language of the text. It defaults to the language option
# or en if the language is not set.
# epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
# epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
# epub_identifier = ''

# A unique identification for the text.
# epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
# epub_cover = ()

# A sequence of (type, uri, title) tuples for the guide element of content.opf.
# epub_guide = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
# epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
# epub_post_files = []

# A list of files that should not be packed into the epub file.
# epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
# epub_tocdepth = 3

# Allow duplicate toc entries.
# epub_tocdup = True

# Fix unsupported image types using the PIL.
# epub_fix_images = False

# Scale large images.
# epub_max_image_width = 0

# If 'no', URL addresses will not be shown.
# epub_show_urls = 'inline'

# If false, no index is generated.
# epub_use_index = True

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import local, cd
import os
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))


def publish(test='yes'):
    '''
    Easy publishing of my nice open source project
    '''
    if test == 'yes':
        validate()

    from feedly import __version__
    tag_name = 'v%s' % __version__
    local('python setup.py sdist upload')

    local('git tag %s' % tag_name)
    local('git push origin --tags')


def validate():
    with cd(PROJECT_ROOT):
        local('pep8 --exclude=migrations --ignore=E501,E225,W293 feedly')
        # local('pyflakes -x W feedly')
        local(
            'py.test -sl --tb=short --cov coveralls --cov-report html --cov feedly feedly/tests')


def clean():
    # all dirs which contain python code
    python_dirs = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        python_dir = any(f.endswith('.py') for f in files)
        if python_dir:
            python_dirs.append(root)
    for d in python_dirs:
        local('bash -c "autopep8 -i %s/*.py"' % d)


def docs():
    local('pandoc -s -w rst README.md -o docs/readme.rst')
    local('sphinx-build -Eav docs html')

########NEW FILE########
__FILENAME__ = activity
from feedly import exceptions as feedly_exceptions
from feedly.utils import make_list_unique, datetime_to_epoch
import datetime


MAX_AGGREGATED_ACTIVITIES_LENGTH = 15


class BaseActivity(object):

    '''
    Common parent class for Activity and Aggregated Activity
    Check for this if you want to see if something is an activity
    '''
    pass


class DehydratedActivity(BaseActivity):

    '''
    The dehydrated verions of an :class:`Activity`.
    the only data stored is serialization_id of the original

    Serializers can store this instead of the full activity
    Feed classes

    '''

    def __init__(self, serialization_id):
        self.serialization_id = serialization_id
        self._activity_ids = [serialization_id]
        self.dehydrated = True

    def get_hydrated(self, activities):
        '''
        returns the full hydrated Activity from activities

        :param activities a dict {'activity_id': Activity}

        '''
        activity = activities[int(self.serialization_id)]
        activity.dehydrated = False
        return activity


class Activity(BaseActivity):

    '''
    Wrapper class for storing activities
    Note

    actor_id
    target_id
    and object_id are always present

    actor, target and object are lazy by default
    '''

    def __init__(self, actor, verb, object, target=None, time=None, extra_context=None):
        self.verb = verb
        self.time = time or datetime.datetime.utcnow()
        # either set .actor or .actor_id depending on the data
        self._set_object_or_id('actor', actor)
        self._set_object_or_id('object', object)
        self._set_object_or_id('target', target)
        # store the extra context which gets serialized
        self.extra_context = extra_context or {}
        self.dehydrated = False

    def get_dehydrated(self):
        '''
        returns the dehydrated version of the current activity

        '''
        return DehydratedActivity(serialization_id=self.serialization_id)

    def __cmp__(self, other):
        if not isinstance(other, Activity):
            raise ValueError(
                'Can only compare to Activity not %r of type %s' % (other, type(other)))
        return cmp(self.serialization_id, other.serialization_id)

    def __hash__(self):
        return hash(self.serialization_id)

    @property
    def serialization_id(self):
        '''
        serialization_id is used to keep items locally sorted and unique
        (eg. used redis sorted sets' score or cassandra column names)

        serialization_id is also used to select random activities from the feed
        (eg. remove activities from feeds must be fast operation)
        for this reason the serialization_id should be unique and not change over time

        eg:
        activity.serialization_id = 1373266755000000000042008
        1373266755000 activity creation time as epoch with millisecond resolution
        0000000000042 activity left padded object_id (10 digits)
        008 left padded activity verb id (3 digits)

        :returns: int --the serialization id
        '''
        if self.object_id >= 10 ** 10 or self.verb.id >= 10 ** 3:
            raise TypeError('Fatal: object_id / verb have too many digits !')
        if not self.time:
            raise TypeError('Cant serialize activities without a time')
        milliseconds = str(int(datetime_to_epoch(self.time) * 1000))
        serialization_id_str = '%s%0.10d%0.3d' % (
            milliseconds, self.object_id, self.verb.id)
        serialization_id = int(serialization_id_str)
        return serialization_id

    def _set_object_or_id(self, field, object_):
        '''
        Either write the integer to
        field_id
        Or if its a real object
        field_id = int
        field = object
        '''
        id_field = '%s_id' % field
        if isinstance(object_, (int, long)):
            setattr(self, id_field, object_)
        elif object_ is None:
            setattr(self, field, None)
            setattr(self, id_field, None)
        else:
            setattr(self, field, object_)
            setattr(self, id_field, object_.id)

    def __getattr__(self, name):
        '''
        Fail early if using the activity class in the wrong way
        '''
        if name in ['object', 'target', 'actor']:
            if name not in self.__dict__:
                error_message = 'Field self.%s is not defined, use self.%s_id instead' % (
                    name, name)
                raise AttributeError(error_message)
        return object.__getattribute__(self, name)

    def __repr__(self):
        class_name = self.__class__.__name__
        message = '%s(%s) %s %s' % (class_name,
                                    self.verb.past_tense, self.actor_id, self.object_id)
        return message


class AggregatedActivity(BaseActivity):

    '''
    Object to store aggregated activities
    '''
    max_aggregated_activities_length = MAX_AGGREGATED_ACTIVITIES_LENGTH

    def __init__(self, group, activities=None, created_at=None, updated_at=None):
        self.group = group
        self.activities = activities or []
        self.created_at = created_at
        self.updated_at = updated_at
        # if the user opened the notification window and browsed over the
        # content
        self.seen_at = None
        # if the user engaged with the content
        self.read_at = None
        # activity
        self.minimized_activities = 0
        self.dehydrated = False
        self._activity_ids = []

    @property
    def serialization_id(self):
        '''
        serialization_id is used to keep items locally sorted and unique
        (eg. used redis sorted sets' score or cassandra column names)

        serialization_id is also used to select random activities from the feed
        (eg. remove activities from feeds must be fast operation)
        for this reason the serialization_id should be unique and not change over time

        eg:
        activity.serialization_id = 1373266755000000000042008
        1373266755000 activity creation time as epoch with millisecond resolution
        0000000000042 activity left padded object_id (10 digits)
        008 left padded activity verb id (3 digits)

        :returns: int --the serialization id
        '''
        milliseconds = str(int(datetime_to_epoch(self.updated_at)))
        return milliseconds

    def get_dehydrated(self):
        '''
        returns the dehydrated version of the current activity

        '''
        if self.dehydrated is True:
            raise ValueError('already dehydrated')
        self._activity_ids = []
        for activity in self.activities:
            self._activity_ids.append(activity.serialization_id)
        self.activities = []
        self.dehydrated = True
        return self

    def get_hydrated(self, activities):
        '''
        expects activities to be a dict like this {'activity_id': Activity}

        '''
        assert self.dehydrated, 'not dehydrated yet'
        for activity_id in self._activity_ids:
            self.activities.append(activities[activity_id])
        self._activity_ids = []
        self.dehydrated = False
        return self

    def __len__(self):
        '''
        Works on both hydrated and not hydrated activities
        '''
        if self._activity_ids:
            length = len(self.activity_ids)
        else:
            length = len(self.activities)
        return length

    @property
    def activity_ids(self):
        '''
        Returns a list of activity ids
        '''
        if self._activity_ids:
            activity_ids = self._activity_ids
        else:
            activity_ids = [a.serialization_id for a in self.activities]
        return activity_ids

    def __cmp__(self, other):
        if not isinstance(other, AggregatedActivity):
            raise ValueError(
                'I can only compare aggregated activities to other aggregated activities')
        equal = True
        date_fields = ['created_at', 'updated_at', 'seen_at', 'read_at']
        for field in date_fields:
            current = getattr(self, field)
            other_value = getattr(other, field)
            if isinstance(current, datetime.datetime) and isinstance(other_value, datetime.datetime):
                delta = abs(current - other_value)
                if delta > datetime.timedelta(seconds=10):
                    equal = False
                    break
            else:
                if current != other_value:
                    equal = False
                    break

        if self.activities != other.activities:
            equal = False

        return_value = 0 if equal else -1

        return return_value

    def contains(self, activity):
        '''
        Checks if activity is present in this aggregated
        '''
        if not isinstance(activity, (Activity, long)):
            raise ValueError('contains needs an activity or long not %s', activity)
        activity_id = getattr(activity, 'serialization_id', activity)
        return activity_id in set([a.serialization_id for a in self.activities])

    def append(self, activity):
        if self.contains(activity):
            raise feedly_exceptions.DuplicateActivityException()

        # append the activity
        self.activities.append(activity)

        # set the first seen
        if self.created_at is None:
            self.created_at = activity.time

        # set the last seen
        if self.updated_at is None or activity.time > self.updated_at:
            self.updated_at = activity.time

        # ensure that our memory usage, and pickling overhead don't go up
        # endlessly
        if len(self.activities) > self.max_aggregated_activities_length:
            self.activities.pop(0)
            self.minimized_activities += 1

    def remove(self, activity):
        if not self.contains(activity):
            raise feedly_exceptions.ActivityNotFound()

        if len(self.activities) == 1:
            raise ValueError(
                'removing this activity would leave an empty aggregation')

        # remove the activity
        activity_id = getattr(activity, 'serialization_id', activity)
        self.activities = [a for a in self.activities if a.serialization_id != activity_id]

        # now time to update the times
        self.updated_at = self.last_activity.time

        # adjust the count
        if self.minimized_activities:
            self.minimized_activities -= 1

    def remove_many(self, activities):
        removed_activities = []
        for activity in activities:
            try:
                self.remove(activity)
            except feedly_exceptions.ActivityNotFound:
                pass
            else:
                removed_activities.append(activity)
        return removed_activities

    @property
    def actor_count(self):
        '''
        Returns a count of the number of actors
        When dealing with large lists only approximate the number of actors
        '''
        base = self.minimized_activities
        actor_id_count = len(self.actor_ids)
        base += actor_id_count
        return base

    @property
    def other_actor_count(self):
        actor_count = self.actor_count
        return actor_count - 2

    @property
    def activity_count(self):
        '''
        Returns the number of activities
        '''
        base = self.minimized_activities
        base += len(self.activities)
        return base

    @property
    def last_activity(self):
        activity = self.activities[-1]
        return activity

    @property
    def last_activities(self):
        activities = self.activities[::-1]
        return activities

    @property
    def verb(self):
        return self.activities[0].verb

    @property
    def verbs(self):
        return make_list_unique([a.verb for a in self.activities])

    @property
    def actor_ids(self):
        return make_list_unique([a.actor_id for a in self.activities])

    @property
    def object_ids(self):
        return make_list_unique([a.object_id for a in self.activities])

    def is_seen(self):
        '''
        Returns if the activity should be considered as seen at this moment
        '''
        seen = self.seen_at is not None and self.seen_at >= self.updated_at
        return seen

    def is_read(self):
        '''
        Returns if the activity should be considered as seen at this moment
        '''
        read = self.read_at is not None and self.read_at >= self.updated_at
        return read

    def __repr__(self):
        if self.dehydrated:
            message = 'Dehydrated AggregatedActivity (%s)' % self._activity_ids
            return message
        verbs = [v.past_tense for v in self.verbs]
        actor_ids = self.actor_ids
        object_ids = self.object_ids
        actors = ','.join(map(str, actor_ids))
        message = 'AggregatedActivity(%s-%s) Actors %s: Objects %s' % (
            self.group, ','.join(verbs), actors, object_ids)
        return message

########NEW FILE########
__FILENAME__ = base
from feedly.activity import AggregatedActivity, Activity
from copy import deepcopy
from feedly.exceptions import DuplicateActivityException


class BaseAggregator(object):

    '''
    Aggregators implement the combining of multiple activities into aggregated activities.

    The two most important methods are
    aggregate and merge

    Aggregate takes a list of activities and turns it into a list of aggregated activities

    Merge takes two lists of aggregated activities and returns a list of new and changed aggregated activities
    '''

    aggregated_activity_class = AggregatedActivity
    activity_class = Activity

    def __init__(self, aggregated_activity_class=None, activity_class=None):
        '''
        :param aggregated_activity_class: the class which we should use
        for returning the aggregated activities
        '''
        if aggregated_activity_class is not None:
            self.aggregated_activity_class = aggregated_activity_class
        if activity_class is not None:
            self.activity_class = activity_class

    def aggregate(self, activities):
        '''

        :param activties: A list of activities
        :returns list: A list of aggregated activities

        Runs the group activities (using get group)
        Ranks them using the giving ranking function
        And returns the sorted activities

        **Example** ::

            aggregator = ModulusAggregator()
            activities = [Activity(1), Activity(2)]
            aggregated_activities = aggregator.aggregate(activities)

        '''
        aggregate_dict = self.group_activities(activities)
        aggregated_activities = aggregate_dict.values()
        ranked_aggregates = self.rank(aggregated_activities)
        return ranked_aggregates

    def merge(self, aggregated, activities):
        '''
        :param aggregated: A list of aggregated activities
        :param activities: A list of the new activities
        :returns tuple: Returns new, changed

        Merges two lists of aggregated activities and returns the new aggregated
        activities and a from, to mapping of the changed aggregated activities

        **Example** ::

            aggregator = ModulusAggregator()
            activities = [Activity(1), Activity(2)]
            aggregated_activities = aggregator.aggregate(activities)
            activities = [Activity(3), Activity(4)]
            new, changed = aggregator.merge(aggregated_activities, activities)
            for activity in new:
                print activity

            for from, to in changed:
                print 'changed from %s to %s' % (from, to)

        '''
        current_activities_dict = dict([(a.group, a) for a in aggregated])
        new = []
        changed = []
        new_aggregated = self.aggregate(activities)
        for aggregated in new_aggregated:
            if aggregated.group not in current_activities_dict:
                new.append(aggregated)
            else:
                current_aggregated = current_activities_dict.get(
                    aggregated.group)
                new_aggregated = deepcopy(current_aggregated)
                for activity in aggregated.activities:
                    try:
                        new_aggregated.append(activity)
                    except DuplicateActivityException, e:
                        pass
                if current_aggregated.activities != new_aggregated.activities:
                    changed.append((current_aggregated, new_aggregated))
        return new, changed, []

    def group_activities(self, activities):
        '''
        Groups the activities based on their group
        Found by running get_group(actvity on them)
        '''
        aggregate_dict = dict()
        for activity in activities:
            group = self.get_group(activity)
            if group not in aggregate_dict:
                aggregate_dict[group] = self.aggregated_activity_class(group)
            aggregate_dict[group].append(activity)

        return aggregate_dict

    def get_group(self, activity):
        '''
        Returns a group to stick this activity in
        '''
        raise ValueError('not implemented')

    def rank(self, aggregated_activities):
        '''
        The ranking logic, for sorting aggregated activities
        '''
        raise ValueError('not implemented')


class RecentVerbAggregator(BaseAggregator):

    '''
    Aggregates based on the same verb and same time period
    '''

    def rank(self, aggregated_activities):
        '''
        The ranking logic, for sorting aggregated activities
        '''
        aggregated_activities.sort(key=lambda a: a.updated_at, reverse=True)
        return aggregated_activities

    def get_group(self, activity):
        '''
        Returns a group based on the day and verb
        '''
        verb = activity.verb.id
        date = activity.time.date()
        group = '%s-%s' % (verb, date)
        return group

########NEW FILE########
__FILENAME__ = conftest
import pytest
import redis


@pytest.fixture(autouse=True)
def celery_eager():
    from celery import current_app
    current_app.conf.CELERY_ALWAYS_EAGER = True
    current_app.conf.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


@pytest.fixture
def redis_reset():
    redis.Redis().flushall()


@pytest.fixture
def cassandra_reset():
    from feedly.feeds.cassandra import CassandraFeed
    from feedly.feeds.aggregated_feed.cassandra import CassandraAggregatedFeed
    from cqlengine.management import create_table
    aggregated_timeline = CassandraAggregatedFeed.get_timeline_storage()
    timeline = CassandraFeed.get_timeline_storage()
    create_table(aggregated_timeline.model)
    create_table(timeline.model)

########NEW FILE########
__FILENAME__ = default_settings

# : we recommend that you connect to Redis via Twemproxy
FEEDLY_REDIS_CONFIG = {
    'default': {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 0,
        'password': None
    },
}

FEEDLY_CASSANDRA_HOSTS = ['localhost']

FEEDLY_CASSANDRA_DEFAULT_TIMEOUT = 10.0

FEEDLY_DEFAULT_KEYSPACE = 'feedly'

FEEDLY_CASSANDRA_CONSISTENCY_LEVEL = None

FEEDLY_CASSANDRA_READ_RETRY_ATTEMPTS = 1

FEEDLY_CASSANDRA_WRITE_RETRY_ATTEMPTS = 1

FEEDLY_TRACK_CASSANDRA_DRIVER_METRICS = False

FEEDLY_METRIC_CLASS = 'feedly.metrics.base.Metrics'

FEEDLY_METRICS_OPTIONS = {}

FEEDLY_VERB_STORAGE = 'in-memory'

try:
    from cassandra import ConsistencyLevel
    FEEDLY_CASSANDRA_CONSISTENCY_LEVEL = ConsistencyLevel.ONE
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = exceptions


class SerializationException(Exception):

    '''
    Raised when encountering invalid data for serialization
    '''
    pass


class DuplicateActivityException(Exception):

    '''
    Raised when someone sticks a duplicate activity in the aggregated activity
    '''
    pass


class ActivityNotFound(Exception):

    '''
    Raised when the activity is not present in the aggregated Activity
    '''
    pass

########NEW FILE########
__FILENAME__ = base
from feedly.activity import Activity, AggregatedActivity
from feedly.aggregators.base import RecentVerbAggregator
from feedly.feeds.base import BaseFeed
from feedly.serializers.aggregated_activity_serializer import \
    AggregatedActivitySerializer
import copy
import logging
import random
import itertools
from feedly.utils.timing import timer
from collections import defaultdict
from feedly.utils.validate import validate_list_of_strict
from feedly.tests.utils import FakeActivity, FakeAggregatedActivity


logger = logging.getLogger(__name__)


class AggregatedFeed(BaseFeed):

    '''
    Aggregated feeds are an extension of the basic feed.
    The turn activities into aggregated activities by using an aggregator class.

    See :class:`.BaseAggregator`

    You can use aggregated feeds to built smart feeds, such as Facebook's newsfeed.
    Alternatively you can also use smart feeds for building complex notification systems.

    Have a look at fashiolista.com for the possibilities.

    .. note::

       Aggregated feeds do more work in the fanout phase. Remember that for every user
       activity the number of fanouts is equal to their number of followers.
       So with a 1000 user activities, with an average of 500 followers per user, you
       already end up running 500.000 fanout operations

       Since the fanout operation happens so often, you should make sure not to
       do any queries in the fanout phase or any other resource intensive operations.

    Aggregated feeds differ from feeds in a few ways:

    - Aggregator classes aggregate activities into aggregated activities
    - We need to update aggregated activities instead of only appending
    - Serialization is different
    '''
    # : The class to use for aggregating activities into aggregated activities
    # : also see :class:`.BaseAggregator`
    aggregator_class = RecentVerbAggregator

    # : The class to use for storing the aggregated activity
    aggregated_activity_class = AggregatedActivity
    # : the number of aggregated items to search to see if we match
    # : or create a new aggregated activity
    merge_max_length = 20

    # : we use a different timeline serializer for aggregated activities
    timeline_serializer = AggregatedActivitySerializer

    @classmethod
    def get_timeline_storage_options(cls):
        '''
        Returns the options for the timeline storage
        '''
        options = super(AggregatedFeed, cls).get_timeline_storage_options()
        options['aggregated_activity_class'] = cls.aggregated_activity_class
        return options

    def add_many(self, activities, trim=True, current_activities=None, *args, **kwargs):
        '''
        Adds many activities to the feed

        Unfortunately we can't support the batch interface.
        The writes depend on the reads.

        Also subsequent writes will depend on these writes.
        So no batching is possible at all.

        :param activities: the list of activities
        '''
        validate_list_of_strict(
            activities, (self.activity_class, FakeActivity))
        # start by getting the aggregator
        aggregator = self.get_aggregator()

        t = timer()
        # get the current aggregated activities
        if current_activities is None:
            current_activities = self[:self.merge_max_length]
        msg_format = 'reading %s items took %s'
        logger.debug(msg_format, self.merge_max_length, t.next())

        # merge the current activities with the new ones
        new, changed, deleted = aggregator.merge(
            current_activities, activities)
        logger.debug('merge took %s', t.next())

        # new ones we insert, changed we do a delete and insert
        new_aggregated = self._update_from_diff(new, changed, deleted)
        new_aggregated = aggregator.rank(new_aggregated)

        # trim every now and then
        if trim and random.random() <= self.trim_chance:
            self.timeline_storage.trim(self.key, self.max_length)

        return new_aggregated

    def remove_many(self, activities, batch_interface=None, trim=True, *args, **kwargs):
        '''
        Removes many activities from the feed

        :param activities: the list of activities to remove
        '''
        validate_list_of_strict(
            activities, (self.activity_class, FakeActivity, long))

        # trim to make sure nothing we don't need is stored after the max
        # length
        self.trim()
        # now we only have to look at max length
        current_activities = self.get_activity_slice(
            stop=self.max_length, rehydrate=False)

        # setup our variables
        new, deleted, changed = [], [], []
        getid = lambda a: getattr(a, 'serialization_id', a)
        activities_to_remove = set(getid(a) for a in activities)
        activity_dict = dict((getid(a), a) for a in activities)

        # first built the activity lookup dict
        activity_remove_dict = defaultdict(list)
        for aggregated in current_activities:
            for activity_id in aggregated.activity_ids:
                if activity_id in activities_to_remove:
                    activity_remove_dict[aggregated].append(activity_id)
                    activities_to_remove.discard(activity_id)
            # stop searching when we have all of the activities to remove
            if not activities_to_remove:
                break

        # stick the activities to remove in changed or remove
        hydrated_aggregated = activity_remove_dict.keys()
        if self.needs_hydration(hydrated_aggregated):
            hydrated_aggregated = self.hydrate_activities(hydrated_aggregated)
        hydrate_dict = dict((a.group, a) for a in hydrated_aggregated)

        for aggregated, activity_ids_to_remove in activity_remove_dict.items():
            aggregated = hydrate_dict.get(aggregated.group)
            if len(aggregated) == len(activity_ids_to_remove):
                deleted.append(aggregated)
            else:
                original = copy.deepcopy(aggregated)
                activities_to_remove = map(
                    activity_dict.get, activity_ids_to_remove)
                aggregated.remove_many(activities_to_remove)
                changed.append((original, aggregated))

        # new ones we insert, changed we do a delete and insert
        new_aggregated = self._update_from_diff(new, changed, deleted)
        return new_aggregated

    def add_many_aggregated(self, aggregated, *args, **kwargs):
        '''
        Adds the list of aggregated activities

        :param aggregated: the list of aggregated activities to add
        '''
        validate_list_of_strict(
            aggregated, (self.aggregated_activity_class, FakeAggregatedActivity))
        self.timeline_storage.add_many(self.key, aggregated, *args, **kwargs)

    def remove_many_aggregated(self, aggregated, *args, **kwargs):
        '''
        Removes the list of aggregated activities

        :param aggregated: the list of aggregated activities to remove
        '''
        validate_list_of_strict(
            aggregated, (self.aggregated_activity_class, FakeAggregatedActivity))
        self.timeline_storage.remove_many(
            self.key, aggregated, *args, **kwargs)

    def contains(self, activity):
        '''
        Checks if the activity is present in any of the aggregated activities

        :param activity: the activity to search for
        '''
        # get all the current aggregated activities
        aggregated = self[:self.max_length]
        activities = sum([list(a.activities) for a in aggregated], [])
        # make sure we don't modify things in place
        activities = copy.deepcopy(activities)
        activity = copy.deepcopy(activity)

        activity_dict = dict()
        for a in activities:
            key = (a.verb.id, a.actor_id, a.object_id, a.target_id)
            activity_dict[key] = a

        a = activity
        activity_key = (a.verb.id, a.actor_id, a.object_id, a.target_id)
        present = activity_key in activity_dict
        return present

    def get_aggregator(self):
        '''
        Returns the class used for aggregation
        '''
        aggregator = self.aggregator_class(
            self.aggregated_activity_class, self.activity_class)
        return aggregator

    def _update_from_diff(self, new, changed, deleted):
        '''
        Sends the add and remove commands to the storage layer based on a diff
        of

        :param new: list of new items
        :param changed: list of tuples (from, to)
        :param deleted: list of things to delete
        '''
        msg_format = 'now updating from diff new: %s changed: %s deleted: %s'
        logger.debug(msg_format, *map(len, [new, changed, deleted]))
        to_remove, to_add = self._translate_diff(new, changed, deleted)

        # do the remove and add in batch
        with self.get_timeline_batch_interface() as batch_interface:
            # remove those which changed
            if to_remove:
                self.remove_many_aggregated(
                    to_remove, batch_interface=batch_interface)
            # now add the new ones
            if to_add:
                self.add_many_aggregated(
                    to_add, batch_interface=batch_interface)
            logger.debug(
                'removed %s, added %s items from feed %s', len(to_remove), len(to_add), self)

        # return the merge of these two
        new_aggregated = new[:]
        if changed:
            new_aggregated += zip(*changed)[1]

        self.on_update_feed(to_add, to_remove)
        return new_aggregated

    def _translate_diff(self, new, changed, deleted):
        '''
        Translates a list of new changed and deleted into
        Add and remove instructions

        :param new: list of new items
        :param changed: list of tuples (from, to)
        :param deleted: list of things to delete
        :returns: a tuple with a list of items to remove and to add

        **Example**::

            new = [AggregatedActivity]
            deleted = [AggregatedActivity]
            changed = [(AggregatedActivity, AggregatedActivity]
            to_remove, to_delete = feed._translate_diff(new, changed, deleted)
        '''
        # validate this data makes sense
        error_format = 'please only send aggregated activities not %s'
        flat_changed = sum(map(list, changed), [])
        for aggregated_activity in itertools.chain(new, flat_changed, deleted):
            if not isinstance(aggregated_activity, AggregatedActivity):
                raise ValueError(error_format % aggregated_activity)

        # now translate the instructions
        to_remove = deleted[:]
        to_add = new[:]
        if changed:
            # sorry about the very python specific hack :)
            to_remove += zip(*changed)[0]
            to_add += zip(*changed)[1]
        return to_remove, to_add

########NEW FILE########
__FILENAME__ = cassandra
from feedly.feeds.aggregated_feed.base import AggregatedFeed
from feedly.feeds.cassandra import CassandraFeed
from feedly.serializers.cassandra.aggregated_activity_serializer import \
    CassandraAggregatedActivitySerializer
from feedly.storage.cassandra.activity_storage import CassandraActivityStorage
from feedly.storage.cassandra.timeline_storage import CassandraTimelineStorage
from feedly.storage.cassandra import models


class AggregatedActivityTimelineStorage(CassandraTimelineStorage):
    base_model = models.AggregatedActivity


class CassandraAggregatedFeed(AggregatedFeed, CassandraFeed):
    activity_storage_class = CassandraActivityStorage
    timeline_storage_class = AggregatedActivityTimelineStorage

    timeline_serializer = CassandraAggregatedActivitySerializer

    timeline_cf_name = 'aggregated'

########NEW FILE########
__FILENAME__ = notification_feed
from feedly.feeds.aggregated_feed.base import AggregatedFeed
from feedly.serializers.aggregated_activity_serializer import \
    NotificationSerializer
from feedly.storage.redis.timeline_storage import RedisTimelineStorage
import copy
import datetime
import json
import logging

logger = logging.getLogger(__name__)


class NotificationFeed(AggregatedFeed):

    '''
    Similar to an aggregated feed, but:
    - doesnt use the activity storage (serializes everything into the timeline storage)
    - features denormalized counts
    - pubsub signals which you can subscribe to
    For now this is entirely tied to Redis
    '''
    #: notification feeds only need a small max length
    max_length = 99
    key_format = 'notification_feed:1:user:%(user_id)s'
    #: the format we use to denormalize the count
    count_format = 'notification_feed:1:user:%(user_id)s:count'
    #: the key used for locking
    lock_format = 'notification_feed:1:user:%s:lock'
    #: the main channel to publish
    pubsub_main_channel = 'juggernaut'

    timeline_serializer = NotificationSerializer
    activity_storage_class = None
    activity_serializer = None

    def __init__(self, user_id, **kwargs):
        '''
        User id (the user for which we want to read/write notifications)
        '''
        AggregatedFeed.__init__(self, user_id, **kwargs)

        # location to which we denormalize the count
        self.format_dict = dict(user_id=user_id)
        self.count_key = self.count_format % self.format_dict
        # set the pubsub key if we're using it
        self.pubsub_key = user_id
        self.lock_key = self.lock_format % self.format_dict
        from feedly.storage.redis.connection import get_redis_connection
        self.redis = get_redis_connection()

    def add_many(self, activities, **kwargs):
        '''
        Similar to the AggregatedActivity.add_many
        The only difference is that it denormalizes a count of unseen activities
        '''
        with self.redis.lock(self.lock_key, timeout=2):
            current_activities = AggregatedFeed.add_many(
                self, activities, **kwargs)
            # denormalize the count
            self.denormalize_count()
            # return the current state of the notification feed
            return current_activities

    def get_denormalized_count(self):
        '''
        Returns the denormalized count stored in self.count_key
        '''
        result = self.redis.get(self.count_key) or 0
        result = int(result)
        return result

    def set_denormalized_count(self, count):
        '''
        Updates the denormalized count to count

        :param count: the count to update to
        '''
        self.redis.set(self.count_key, count)
        self.publish_count(count)

    def publish_count(self, count):
        '''
        Published the count via pubsub

        :param count: the count to publish
        '''
        count_dict = dict(unread_count=count, unseen_count=count)
        count_data = json.dumps(count_dict)
        data = {'channel': self.pubsub_key, 'data': count_data}
        encoded_data = json.dumps(data)
        self.redis.publish(self.pubsub_main_channel, encoded_data)

    def denormalize_count(self):
        '''
        Denormalize the number of unseen aggregated activities to the key
        defined in self.count_key
        '''
        # now count the number of unseen
        count = self.count_unseen()
        # and update the count if it changed
        stored_count = self.get_denormalized_count()
        if stored_count != count:
            self.set_denormalized_count(count)
        return count

    def count_unseen(self, aggregated_activities=None):
        '''
        Counts the number of aggregated activities which are unseen

        :param aggregated_activities: allows you to specify the aggregated
            activities for improved performance
        '''
        count = 0
        if aggregated_activities is None:
            aggregated_activities = self[:self.max_length]
        for aggregated in aggregated_activities:
            if not aggregated.is_seen():
                count += 1
        return count

    def mark_all(self, seen=True, read=None):
        '''
        Mark all the entries as seen or read

        :param seen: set seen_at
        :param read: set read_at
        '''
        with self.redis.lock(self.lock_key, timeout=10):
            # get the current aggregated activities
            aggregated_activities = self[:self.max_length]
            # create the update dict
            update_dict = {}

            for aggregated_activity in aggregated_activities:
                changed = False
                old_activity = copy.deepcopy(aggregated_activity)
                if seen is True and not aggregated_activity.is_seen():
                    aggregated_activity.seen_at = datetime.datetime.today()
                    changed = True
                if read is True and not aggregated_activity.is_read():
                    aggregated_activity.read_at = datetime.datetime.today()
                    changed = True

                if changed:
                    update_dict[old_activity] = aggregated_activity

            # send the diff to the storage layer
            new, deleted = [], []
            changed = update_dict.items()
            self._update_from_diff(new, changed, deleted)

        # denormalize the count
        self.denormalize_count()

        # return the new activities
        return aggregated_activities


class RedisNotificationFeed(NotificationFeed):
    timeline_storage_class = RedisTimelineStorage

########NEW FILE########
__FILENAME__ = redis
from feedly.feeds.aggregated_feed.base import AggregatedFeed
from feedly.storage.redis.activity_storage import RedisActivityStorage
from feedly.storage.redis.timeline_storage import RedisTimelineStorage
from feedly.serializers.aggregated_activity_serializer import AggregatedActivitySerializer
from feedly.serializers.activity_serializer import ActivitySerializer


class RedisAggregatedFeed(AggregatedFeed):
    timeline_serializer = AggregatedActivitySerializer
    activity_serializer = ActivitySerializer
    timeline_storage_class = RedisTimelineStorage
    activity_storage_class = RedisActivityStorage

########NEW FILE########
__FILENAME__ = base
import copy
from feedly.serializers.base import BaseSerializer
from feedly.serializers.simple_timeline_serializer import \
    SimpleTimelineSerializer
from feedly.storage.base import BaseActivityStorage, BaseTimelineStorage
import random
from feedly.activity import Activity
from feedly.utils.validate import validate_list_of_strict
from feedly.tests.utils import FakeActivity


class BaseFeed(object):

    '''
    The feed class allows you to add and remove activities from a feed.
    Please find below a quick usage example.

    **Usage Example**::

        feed = BaseFeed(user_id)
        # start by adding some existing activities to a feed
        feed.add_many([activities])
        # querying results
        results = feed[:10]
        # removing activities
        feed.remove_many([activities])
        # counting the number of items in the feed
        count = feed.count()
        feed.delete()


    The feed is easy to subclass.
    Commonly you'll want to change the max_length and the key_format.

    **Subclassing**::

        class MyFeed(BaseFeed):
            key_format = 'user_feed:%(user_id)s'
            max_length = 1000


    **Filtering and Pagination**::

        feed.filter(activity_id__gte=1)[:10]
        feed.filter(activity_id__lte=1)[:10]
        feed.filter(activity_id__gt=1)[:10]
        feed.filter(activity_id__lt=1)[:10]


    **Activity storage and Timeline storage**

    To keep reduce timelines memory utilization the BaseFeed supports
    normalization of activity data.

    The full activity data is stored only in the activity_storage while the timeline
    only keeps a activity references (refered as activity_id in the code)

    For this reason when an activity is created it must be stored in the activity_storage
    before other timelines can refer to it

    eg. ::

        feed = BaseFeed(user_id)
        feed.insert_activity(activity)
        follower_feed = BaseFeed(follower_user_id)
        feed.add(activity)

    It is also possible to store the full data in the timeline storage

    The strategy used by the BaseFeed depends on the serializer utilized by the timeline_storage

    When activities are stored as dehydrated (just references) the BaseFeed will query the
    activity_storage to return full activities

    eg. ::

        feed = BaseFeed(user_id)
        feed[:10]

    gets the first 10 activities from the timeline_storage, if the results are not complete activities then
    the BaseFeed will hydrate them via the activity_storage

    '''
    # : the format of the key used when storing the data
    key_format = 'feed_%(user_id)s'

    # : the max length after which we start trimming
    max_length = 100

    # : the activity class to use
    activity_class = Activity

    # : the activity storage class to use (Redis, Cassandra etc)
    activity_storage_class = BaseActivityStorage
    # : the timeline storage class to use (Redis, Cassandra etc)
    timeline_storage_class = BaseTimelineStorage

    # : the class the activity storage should use for serialization
    activity_serializer = BaseSerializer
    # : the class the timline storage should use for serialization
    timeline_serializer = SimpleTimelineSerializer

    # : the chance that we trim the feed, the goal is not to keep the feed
    # : at exactly max length, but make sure we don't grow to infinite size :)
    trim_chance = 0.01

    # : if we can use .filter calls to filter on things like activity id
    filtering_supported = False
    ordering_supported = False

    def __init__(self, user_id):
        '''
        :param user_id: the id of the user who's feed we're working on
        '''
        self.user_id = user_id
        self.key_format = self.key_format
        self.key = self.key_format % {'user_id': self.user_id}

        self.timeline_storage = self.get_timeline_storage()
        self.activity_storage = self.get_activity_storage()

        # ability to filter and change ordering (not supported for all
        # backends)
        self._filter_kwargs = dict()
        self._ordering_args = tuple()

    @classmethod
    def get_timeline_storage_options(cls):
        '''
        Returns the options for the timeline storage
        '''
        options = {}
        options['serializer_class'] = cls.timeline_serializer
        options['activity_class'] = cls.activity_class
        return options

    @classmethod
    def get_timeline_storage(cls):
        '''
        Returns an instance of the timeline storage
        '''
        options = cls.get_timeline_storage_options()
        timeline_storage = cls.timeline_storage_class(**options)
        return timeline_storage

    @classmethod
    def get_activity_storage(cls):
        '''
        Returns an instance of the activity storage
        '''
        options = {}
        options['serializer_class'] = cls.activity_serializer
        options['activity_class'] = cls.activity_class
        if cls.activity_storage_class is not None:
            activity_storage = cls.activity_storage_class(**options)
            return activity_storage

    @classmethod
    def insert_activities(cls, activities, **kwargs):
        '''
        Inserts an activity to the activity storage

        :param activity: the activity class
        '''
        activity_storage = cls.get_activity_storage()
        if activity_storage:
            activity_storage.add_many(activities)

    @classmethod
    def insert_activity(cls, activity, **kwargs):
        '''
        Inserts an activity to the activity storage

        :param activity: the activity class
        '''
        cls.insert_activities([activity])

    @classmethod
    def remove_activity(cls, activity, **kwargs):
        '''
        Removes an activity from the activity storage

        :param activity: the activity class or an activity id
        '''
        activity_storage = cls.get_activity_storage()
        activity_storage.remove(activity)

    @classmethod
    def get_timeline_batch_interface(cls):
        timeline_storage = cls.get_timeline_storage()
        return timeline_storage.get_batch_interface()

    def add(self, activity, *args, **kwargs):
        return self.add_many([activity], *args, **kwargs)

    def add_many(self, activities, batch_interface=None, trim=True, *args, **kwargs):
        '''
        Add many activities

        :param activities: a list of activities
        :param batch_interface: the batch interface
        '''
        validate_list_of_strict(
            activities, (self.activity_class, FakeActivity))

        add_count = self.timeline_storage.add_many(
            self.key, activities, batch_interface=batch_interface, *args, **kwargs)

        # trim the feed sometimes
        if trim and random.random() <= self.trim_chance:
            self.trim()
        self.on_update_feed(new=activities, deleted=[])
        return add_count

    def remove(self, activity_id, *args, **kwargs):
        return self.remove_many([activity_id], *args, **kwargs)

    def remove_many(self, activity_ids, batch_interface=None, trim=True, *args, **kwargs):
        '''
        Remove many activities

        :param activity_ids: a list of activities or activity ids
        '''
        del_count = self.timeline_storage.remove_many(
            self.key, activity_ids, batch_interface=None, *args, **kwargs)
        # trim the feed sometimes
        if trim and random.random() <= self.trim_chance:
            self.trim()
        self.on_update_feed(new=[], deleted=activity_ids)
        return del_count

    def on_update_feed(self, new, deleted):
        '''
        A hook called when activities area created or removed from the feed
        '''
        pass

    def trim(self, length=None):
        '''
        Trims the feed to the length specified

        :param length: the length to which to trim the feed, defaults to self.max_length
        '''
        length = length or self.max_length
        self.timeline_storage.trim(self.key, length)

    def count(self):
        '''
        Count the number of items in the feed
        '''
        return self.timeline_storage.count(self.key)

    __len__ = count

    def delete(self):
        '''
        Delete the entire feed
        '''
        return self.timeline_storage.delete(self.key)

    @classmethod
    def flush(cls):
        activity_storage = cls.get_activity_storage()
        timeline_storage = cls.get_timeline_storage()
        activity_storage.flush()
        timeline_storage.flush()

    def __iter__(self):
        raise TypeError('Iteration over non sliced feeds is not supported')

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.

        """
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        if isinstance(k, slice):
            start = k.start

            if k.stop is not None:
                bound = int(k.stop)
            else:
                bound = None
        else:
            start = k
            bound = k + 1

        start = start or 0

        if None not in (start, bound) and start == bound:
            return []

        # We need check to see if we need to populate more of the cache.
        try:
            results = self.get_activity_slice(
                start, bound)
        except StopIteration:
            # There's nothing left, even though the bound is higher.
            results = None

        return results

    def index_of(self, activity_id):
        '''
        Returns the index of the activity id

        :param activity_id: the activity id
        '''
        return self.timeline_storage.index_of(self.key, activity_id)

    def hydrate_activities(self, activities):
        '''
        hydrates the activities using the activity_storage
        '''
        activity_ids = []
        for activity in activities:
            activity_ids += activity._activity_ids
        activity_list = self.activity_storage.get_many(activity_ids)
        activity_data = {a.serialization_id: a for a in activity_list}
        return [activity.get_hydrated(activity_data) for activity in activities]

    def needs_hydration(self, activities):
        '''
        checks if the activities are dehydrated
        '''
        for activity in activities:
            if hasattr(activity, 'dehydrated') and activity.dehydrated:
                return True
        return False

    def get_activity_slice(self, start=None, stop=None, rehydrate=True):
        '''
        Gets activity_ids from timeline_storage and then loads the
        actual data querying the activity_storage
        '''
        activities = self.timeline_storage.get_slice(
            self.key, start, stop, filter_kwargs=self._filter_kwargs,
            ordering_args=self._ordering_args)
        if self.needs_hydration(activities) and rehydrate:
            activities = self.hydrate_activities(activities)
        return activities

    def _clone(self):
        '''
        Copy the feed instance
        '''
        feed_copy = copy.copy(self)
        filter_kwargs = copy.copy(self._filter_kwargs)
        feed_copy._filter_kwargs = filter_kwargs
        return feed_copy

    def filter(self, **kwargs):
        '''
        Filter based on the kwargs given, uses django orm like syntax

        **Example** ::
            # filter between 100 and 200
            feed = feed.filter(activity_id__gte=100)
            feed = feed.filter(activity_id__lte=200)
            # the same statement but in one step
            feed = feed.filter(activity_id__gte=100, activity_id__lte=200)

        '''
        new = self._clone()
        new._filter_kwargs.update(kwargs)
        return new

    def order_by(self, *ordering_args):
        '''
        Change default ordering

        '''
        new = self._clone()
        new._ordering_args = ordering_args
        return new


class UserBaseFeed(BaseFeed):

    '''
    Implementation of the base feed with a different
    Key format and a really large max_length
    '''
    key_format = 'user_feed:%(user_id)s'
    max_length = 10 ** 6

########NEW FILE########
__FILENAME__ = cassandra
from feedly import settings
from feedly.feeds.base import BaseFeed
from feedly.storage.cassandra.activity_storage import CassandraActivityStorage
from feedly.storage.cassandra.timeline_storage import CassandraTimelineStorage
from feedly.serializers.cassandra.activity_serializer import CassandraActivitySerializer


class CassandraFeed(BaseFeed):

    """
    Apache Cassandra feed implementation

    This implementation does not store activities in a
    denormalized fashion

    Activities are stored completely in the timeline storage

    """

    activity_storage_class = CassandraActivityStorage
    timeline_storage_class = CassandraTimelineStorage
    timeline_serializer = CassandraActivitySerializer

    # ; the name of the column family
    timeline_cf_name = 'example'

    @classmethod
    def get_timeline_storage_options(cls):
        '''
        Returns the options for the timeline storage
        '''
        options = super(CassandraFeed, cls).get_timeline_storage_options()
        options['hosts'] = settings.FEEDLY_CASSANDRA_HOSTS
        options['column_family_name'] = cls.timeline_cf_name
        return options

    # : clarify that this feed supports filtering and ordering
    filtering_supported = True
    ordering_supported = True

########NEW FILE########
__FILENAME__ = memory
from feedly.feeds.base import BaseFeed
from feedly.storage.memory import InMemoryActivityStorage
from feedly.storage.memory import InMemoryTimelineStorage


class Feed(BaseFeed):
    timeline_storage_class = InMemoryTimelineStorage
    activity_storage_class = InMemoryActivityStorage

########NEW FILE########
__FILENAME__ = redis
from feedly.feeds.base import BaseFeed
from feedly.storage.redis.activity_storage import RedisActivityStorage
from feedly.storage.redis.timeline_storage import RedisTimelineStorage
from feedly.serializers.activity_serializer import ActivitySerializer


class RedisFeed(BaseFeed):
    timeline_storage_class = RedisTimelineStorage
    activity_storage_class = RedisActivityStorage

    activity_serializer = ActivitySerializer

    # : allow you point to a different redis server as specified in
    # : settings.FEEDLY_REDIS_CONFIG
    redis_server = 'default'

    @classmethod
    def get_timeline_storage_options(cls):
        '''
        Returns the options for the timeline storage
        '''
        options = super(RedisFeed, cls).get_timeline_storage_options()
        options['redis_server'] = cls.redis_server
        return options

    # : clarify that this feed supports filtering
    filtering_supported = True

########NEW FILE########
__FILENAME__ = base
from feedly.feeds.base import UserBaseFeed
from feedly.tasks import follow_many, unfollow_many
from feedly.tasks import fanout_operation
from feedly.tasks import fanout_operation_hi_priority
from feedly.tasks import fanout_operation_low_priority
from feedly.utils import chunks
from feedly.utils import get_metrics_instance
from feedly.utils.timing import timer
import logging
from feedly.feeds.redis import RedisFeed


logger = logging.getLogger(__name__)


def add_operation(feed, activities, trim=True, batch_interface=None):
    '''
    Add the activities to the feed
    functions used in tasks need to be at the main level of the module
    '''
    t = timer()
    msg_format = 'running %s.add_many operation for %s activities batch interface %s and trim %s'
    logger.debug(msg_format, feed, len(activities), batch_interface, trim)
    feed.add_many(activities, batch_interface=batch_interface, trim=trim)
    logger.debug('add many operation took %s seconds', t.next())


def remove_operation(feed, activities, trim=True, batch_interface=None):
    '''
    Remove the activities from the feed
    functions used in tasks need to be at the main level of the module
    '''
    t = timer()
    msg_format = 'running %s.remove_many operation for %s activities batch interface %s'
    logger.debug(msg_format, feed, len(activities), batch_interface)
    feed.remove_many(activities, trim=trim, batch_interface=batch_interface)
    logger.debug('remove many operation took %s seconds', t.next())


class FanoutPriority(object):
    HIGH = 'HIGH'
    LOW = 'LOW'


class Feedly(object):

    '''
    The Feedly class handles the fanout from a user's activity
    to all their follower's feeds

    .. note::
        Fanout is the process which pushes a little bit of data to all of your
        followers in many small and asynchronous tasks.

    To write your own Feedly class you will need to implement

    - get_user_follower_ids
    - feed_classes
    - user_feed_class

    **Example** ::

        from feedly.feed_managers.base import Feedly

        class PinFeedly(Feedly):
            # customize the feed classes we write to
            feed_classes = dict(
                normal=PinFeed,
                aggregated=AggregatedPinFeed
            )
            # customize the user feed class
            user_feed_class = UserPinFeed

            # define how feedly can get the follower ids
            def get_user_follower_ids(self, user_id):
                ids = Follow.objects.filter(target=user_id).values_list('user_id', flat=True)
                return {FanoutPriority.HIGH:ids}

            # utility functions to easy integration for your project
            def add_pin(self, pin):
                activity = pin.create_activity()
                # add user activity adds it to the user feed, and starts the fanout
                self.add_user_activity(pin.user_id, activity)

            def remove_pin(self, pin):
                activity = pin.create_activity()
                # removes the pin from the user's followers feeds
                self.remove_user_activity(pin.user_id, activity)

    '''
    # : a dictionary with the feeds to fanout to
    # : for example feed_classes = dict(normal=PinFeed, aggregated=AggregatedPinFeed)
    feed_classes = dict(
        normal=RedisFeed
    )
    # : the user feed class (it stores the latest activity by one user)
    user_feed_class = UserBaseFeed

    # : the number of activities which enter your feed when you follow someone
    follow_activity_limit = 5000
    # : the number of users which are handled in one asynchronous task
    # : when doing the fanout
    fanout_chunk_size = 100

    # maps between priority and fanout tasks
    priority_fanout_task = {
        FanoutPriority.HIGH: fanout_operation_hi_priority,
        FanoutPriority.LOW: fanout_operation_low_priority
    }

    metrics = get_metrics_instance()

    def get_user_follower_ids(self, user_id):
        '''
        Returns a dict of users ids which follow the given user grouped by
        priority/importance

        eg.
        {'HIGH': [...], 'LOW': [...]}

        :param user_id: the user id for which to get the follower ids
        '''
        raise NotImplementedError()

    def add_user_activity(self, user_id, activity):
        '''
        Store the new activity and then fanout to user followers

        This function will
        - store the activity in the activity storage
        - store it in the user feed (list of activities for one user)
        - fanout for all feed_classes

        :param user_id: the id of the user
        :param activity: the activity which to add
        '''
        # add into the global activity cache (if we are using it)
        self.user_feed_class.insert_activity(activity)
        # now add to the user's personal feed
        user_feed = self.get_user_feed(user_id)
        user_feed.add(activity)
        operation_kwargs = dict(activities=[activity], trim=True)

        for priority_group, follower_ids in self.get_user_follower_ids(user_id=user_id).items():
            # create the fanout tasks
            for feed_class in self.feed_classes.values():
                self.create_fanout_tasks(
                    follower_ids,
                    feed_class,
                    add_operation,
                    operation_kwargs=operation_kwargs,
                    fanout_priority=priority_group
                )
        self.metrics.on_activity_published()

    def remove_user_activity(self, user_id, activity):
        '''
        Remove the activity and then fanout to user followers

        :param user_id: the id of the user
        :param activity: the activity which to add
        '''
        # we don't remove from the global feed due to race conditions
        # but we do remove from the personal feed
        user_feed = self.get_user_feed(user_id)
        user_feed.remove(activity)

        # no need to trim when removing items
        operation_kwargs = dict(activities=[activity], trim=False)

        for priority_group, follower_ids in self.get_user_follower_ids(user_id=user_id).items():
            for feed_class in self.feed_classes.values():
                self.create_fanout_tasks(
                    follower_ids,
                    feed_class,
                    remove_operation,
                    operation_kwargs=operation_kwargs,
                    fanout_priority=priority_group
                )
        self.metrics.on_activity_removed()

    def get_feeds(self, user_id):
        '''
        get the feed that contains the sum of all activity
        from feeds :user_id is subscribed to

        :returns dict: a dictionary with the feeds we're pushing to
        '''
        return dict([(k, feed(user_id)) for k, feed in self.feed_classes.items()])

    def get_user_feed(self, user_id):
        '''
        feed where activity from :user_id is saved

        :param user_id: the id of the user
        '''
        return self.user_feed_class(user_id)

    def update_user_activities(self, activities):
        '''
        Update the user activities
        :param activities: the activities to update
        '''
        for activity in activities:
            self.add_user_activity(activity.actor_id, activity)

    def update_user_activity(self, activity):
        self.update_user_activities([activity])

    def follow_feed(self, feed, activities):
        '''
        copies source_feed entries into feed
        it will only copy follow_activity_limit activities

        :param feed: the feed to copy to
        :param activities: the activities to copy into the feed
        '''
        if activities:
            return feed.add_many(activities)

    def unfollow_feed(self, feed, source_feed):
        '''
        removes entries originating from the source feed form the feed class
        this will remove all activities, so this could take a wh
        :param feed: the feed to copy to
        :param source_feed: the feed with a list of activities to remove
        '''
        activities = source_feed[:]  # need to slice
        if activities:
            return feed.remove_many(activities)

    def follow_user(self, user_id, target_user_id, async=True):
        '''
        user_id starts following target_user_id

        :param user_id: the user which is doing the following/unfollowing
        :target_user_id: the user which is being unfollowed
        '''
        source_feed = self.get_user_feed(target_user_id)
        # fetch the activities only once
        activities = source_feed[:self.follow_activity_limit]
        for user_feed in self.get_feeds(user_id).values():
            self.follow_feed(user_feed, activities)

    def unfollow_user(self, user_id, target_user_id, async=True):
        '''
        unfollows the user

        :param user_id: the user which is doing the following/unfollowing
        :target_user_id: the user which is being unfollowed
        '''
        if async:
            unfollow_many_fn = unfollow_many.delay
        else:
            unfollow_many_fn = unfollow_many

        unfollow_many_fn(self, user_id, [target_user_id])

    def follow_many_users(self, user_id, target_ids, async=True):
        '''
        copies feeds for target_ids in user_id

        :param user_id: the user which is doing the following/unfollowing
        :param target_ids: the user to follow
        :param async: controls if the operation should be done via celery
        '''
        if async:
            follow_many_fn = follow_many.delay
        else:
            follow_many_fn = follow_many

        follow_many_fn(
            self,
            user_id,
            target_ids,
            self.follow_activity_limit
        )

    def get_fanout_task(self, priority=None, feed_class=None):
        '''
        Returns the fanout task taking priority in account.

        :param priority: the priority of the task
        :param feed_class: the feed_class the task will write to
        '''
        return self.priority_fanout_task.get(priority, fanout_operation)

    def create_fanout_tasks(self, follower_ids, feed_class, operation, operation_kwargs=None, fanout_priority=None):
        '''
        Creates the fanout task for the given activities and feed classes
        followers

        It takes the following ids and distributes them per fanout_chunk_size
        into smaller tasks

        :param follower_ids: specify the list of followers
        :param feed_class: the feed classes to run the operation on
        :param operation: the operation function applied to all follower feeds
        :param operation_kwargs: kwargs passed to the operation
        :param fanout_priority: the priority set to this fanout
        '''
        fanout_task = self.get_fanout_task(
            fanout_priority, feed_class=feed_class)
        if not fanout_task:
            return []
        chunk_size = self.fanout_chunk_size
        user_ids_chunks = list(chunks(follower_ids, chunk_size))
        msg_format = 'spawning %s subtasks for %s user ids in chunks of %s users'
        logger.info(
            msg_format, len(user_ids_chunks), len(follower_ids), chunk_size)
        tasks = []
        # now actually create the tasks
        for ids_chunk in user_ids_chunks:
            task = fanout_task.delay(
                feed_manager=self,
                feed_class=feed_class,
                user_ids=ids_chunk,
                operation=operation,
                operation_kwargs=operation_kwargs
            )
            tasks.append(task)
        return tasks

    def fanout(self, user_ids, feed_class, operation, operation_kwargs):
        '''
        This functionality is called from within feedly.tasks.fanout_operation

        :param user_ids: the list of user ids which feeds we should apply the
            operation against
        :param feed_class: the feed to run the operation on
        :param operation: the operation to run on the feed
        :param operation_kwargs: kwargs to pass to the operation

        '''
        with self.metrics.fanout_timer(feed_class):
            separator = '===' * 10
            logger.info('%s starting fanout %s', separator, separator)
            batch_context_manager = feed_class.get_timeline_batch_interface()
            msg_format = 'starting batch interface for feed %s, fanning out to %s users'
            with batch_context_manager as batch_interface:
                logger.info(msg_format, feed_class, len(user_ids))
                operation_kwargs['batch_interface'] = batch_interface
                for user_id in user_ids:
                    logger.debug('now handling fanout to user %s', user_id)
                    feed = feed_class(user_id)
                    operation(feed, **operation_kwargs)
            logger.info('finished fanout for feed %s', feed_class)
        fanout_count = len(operation_kwargs['activities']) * len(user_ids)
        self.metrics.on_fanout(feed_class, operation, fanout_count)

    def batch_import(self, user_id, activities, fanout=True, chunk_size=500):
        '''
        Batch import all of the users activities and distributes
        them to the users followers

        **Example**::

            activities = [long list of activities]
            feedly.batch_import(13, activities, 500)

        :param user_id: the user who created the activities
        :param activities: a list of activities from this user
        :param fanout: if we should run the fanout or not
        :param chunk_size: per how many activities to run the batch operations

        '''
        activities = list(activities)
        # skip empty lists
        if not activities:
            return
        logger.info('running batch import for user %s', user_id)

        user_feed = self.get_user_feed(user_id)
        if activities[0].actor_id != user_id:
            raise ValueError('Send activities for only one user please')

        activity_chunks = list(chunks(activities, chunk_size))
        logger.info('processing %s items in %s chunks of %s',
                    len(activities), len(activity_chunks), chunk_size)

        for index, activity_chunk in enumerate(activity_chunks):
            # first insert into the global activity storage
            self.user_feed_class.insert_activities(activity_chunk)
            logger.info(
                'inserted chunk %s (length %s) into the global activity store', index, len(activity_chunk))
            # next add the activities to the users personal timeline
            user_feed.add_many(activity_chunk, trim=False)
            logger.info(
                'inserted chunk %s (length %s) into the user feed', index, len(activity_chunk))
            # now start a big fanout task
            if fanout:
                logger.info('starting task fanout for chunk %s', index)
                follower_ids_by_prio = self.get_user_follower_ids(
                    user_id=user_id)
                # create the fanout tasks
                operation_kwargs = dict(activities=activity_chunk, trim=False)
                for feed_class in self.feed_classes.values():
                    for priority_group, fids in follower_ids_by_prio.items():
                        self.create_fanout_tasks(
                            fids,
                            feed_class,
                            add_operation,
                            fanout_priority=priority_group,
                            operation_kwargs=operation_kwargs
                        )

########NEW FILE########
__FILENAME__ = base
class NoopTimer(object):

    def __enter__(self):
        pass

    def __exit__(self, *args, **kwds):
        pass


class Metrics(object):

    def __init__(self, *args, **kwargs):
        pass

    def fanout_timer(self, feed_class):
        return NoopTimer()

    def feed_reads_timer(self, feed_class):
        return NoopTimer()

    def on_feed_read(self, feed_class, activities_count):
        pass

    def on_feed_remove(self, feed_class, activities_count):
        pass

    def on_feed_write(self, feed_class, activities_count):
        pass

    def on_fanout(self, feed_class, operation, activities_count=1):
        pass

    def on_activity_published(self):
        pass

    def on_activity_removed(self):
        pass

########NEW FILE########
__FILENAME__ = python_statsd
from __future__ import absolute_import
from feedly.metrics.base import Metrics
import statsd


class Timer(object):

    def __init__(self, metric_name):
        self.metric_name = metric_name

    def __enter__(self):
        self.timer = statsd.Timer(self.metric_name)
        self.timer.start()

    def __exit__(self, *args, **kwds):
        self.timer.stop()


class StatsdMetrics(Metrics):

    def __init__(self, host='localhost', port=8125, prefix='feedly'):
        statsd.Connection.set_defaults(host=host, port=port)
        self.prefix = prefix

    def fanout_timer(self, feed_class):
        return Timer('%s.%s.fanout_latency' % (self.prefix, feed_class.__name__))

    def feed_reads_timer(self, feed_class):
        return Timer('%s.%s.read_latency' % (self.prefix, feed_class.__name__))

    def on_feed_read(self, feed_class, activities_count):
        counter = statsd.Counter(
            '%s.%s.reads' % (self.prefix, feed_class.__name__))
        counter += activities_count

    def on_feed_write(self, feed_class, activities_count):
        counter = statsd.Counter(
            '%s.%s.writes' % (self.prefix, feed_class.__name__))
        counter += activities_count

    def on_feed_remove(self, feed_class, activities_count):
        counter = statsd.Counter(
            '%s.%s.deletes' % (self.prefix, feed_class.__name__))
        counter += activities_count

    def on_fanout(self, feed_class, operation, activities_count=1):
        metric = (self.prefix, feed_class.__name__, operation.__name__)
        counter = statsd.Counter('%s.%s.fanout.%s' % metric)
        counter += activities_count

    def on_activity_published(self):
        counter = statsd.Counter('%s.activities.published' % self.prefix)
        counter += 1

    def on_activity_removed(self):
        counter = statsd.Counter('%s.activities.removed' % self.prefix)
        counter += 1

########NEW FILE########
__FILENAME__ = statsd
from __future__ import absolute_import
from feedly.metrics.base import Metrics
from statsd import StatsClient


class StatsdMetrics(Metrics):

    def __init__(self, host='localhost', port=8125, prefix=None):
        self.statsd = StatsClient(host, port, prefix)

    def fanout_timer(self, feed_class):
        return self.statsd.timer('%s.fanout_latency' % feed_class.__name__)

    def feed_reads_timer(self, feed_class):
        return self.statsd.timer('%s.read_latency' % feed_class.__name__)

    def on_feed_read(self, feed_class, activities_count):
        self.statsd.incr('%s.reads' % feed_class.__name__, activities_count)

    def on_feed_write(self, feed_class, activities_count):
        self.statsd.incr('%s.writes' % feed_class.__name__, activities_count)

    def on_feed_remove(self, feed_class, activities_count):
        self.statsd.incr('%s.deletes' % feed_class.__name__, activities_count)

    def on_fanout(self, feed_class, operation, activities_count=1):
        metric = (feed_class.__name__, operation.__name__)
        self.statsd.incr('%s.fanout.%s' % metric, activities_count)

    def on_activity_published(self):
        self.statsd.incr('activities.published')

    def on_activity_removed(self):
        self.statsd.incr('activities.removed')

########NEW FILE########
__FILENAME__ = activity_serializer
from feedly.activity import Activity
from feedly.serializers.base import BaseSerializer
from feedly.utils import epoch_to_datetime, datetime_to_epoch
from feedly.verbs import get_verb_by_id
import pickle


class ActivitySerializer(BaseSerializer):

    '''
    Serializer optimized for taking as little memory as possible to store an
    Activity

    Serialization consists of 5 parts
    - actor_id
    - verb_id
    - object_id
    - target_id
    - extra_context (pickle)

    None values are stored as 0
    '''

    def dumps(self, activity):
        self.check_type(activity)
        activity_time = datetime_to_epoch(activity.time)
        parts = [activity.actor_id, activity.verb.id,
                 activity.object_id, activity.target_id or 0]
        extra_context = activity.extra_context.copy()
        pickle_string = ''
        if extra_context:
            pickle_string = pickle.dumps(activity.extra_context)
        parts += [activity_time, pickle_string]
        serialized_activity = ','.join(map(str, parts))
        return serialized_activity

    def loads(self, serialized_activity):
        parts = serialized_activity.split(',')
        # convert these to ids
        actor_id, verb_id, object_id, target_id = map(
            int, parts[:4])
        activity_datetime = epoch_to_datetime(float(parts[4]))
        pickle_string = str(parts[5])
        if not target_id:
            target_id = None
        verb = get_verb_by_id(verb_id)
        extra_context = {}
        if pickle_string:
            extra_context = pickle.loads(pickle_string)
        activity = self.activity_class(actor_id, verb, object_id, target_id,
                                       time=activity_datetime, extra_context=extra_context)

        return activity

########NEW FILE########
__FILENAME__ = aggregated_activity_serializer
from feedly.activity import AggregatedActivity, Activity
from feedly.exceptions import SerializationException
from feedly.serializers.activity_serializer import ActivitySerializer
from feedly.serializers.utils import check_reserved
from feedly.utils import epoch_to_datetime, datetime_to_epoch
from feedly.serializers.base import BaseAggregatedSerializer


class AggregatedActivitySerializer(BaseAggregatedSerializer):

    '''
    Optimized version of the Activity serializer for AggregatedActivities

    v3group;;created_at;;updated_at;;seen_at;;read_at;;aggregated_activities

    Main advantage is that it prevents you from increasing the storage of
    a notification without realizing you are adding the extra data

    Depending on dehydrate it will either dump dehydrated aggregated activities
    or store the full aggregated activity
    '''
    #: indicates if dumps returns dehydrated aggregated activities
    dehydrate = True
    identifier = 'v3'
    reserved_characters = [';', ',', ';;']
    date_fields = ['created_at', 'updated_at', 'seen_at', 'read_at']

    activity_serializer_class = ActivitySerializer

    def dumps(self, aggregated):
        self.check_type(aggregated)

        activity_serializer = self.activity_serializer_class(Activity)
        # start by storing the group
        parts = [aggregated.group]
        check_reserved(aggregated.group, [';;'])

        # store the dates
        for date_field in self.date_fields:
            value = getattr(aggregated, date_field)
            epoch = datetime_to_epoch(value) if value is not None else -1
            parts += [epoch]

        # add the activities serialization
        serialized_activities = []
        if self.dehydrate:
            if not aggregated.dehydrated:
                aggregated = aggregated.get_dehydrated()
            serialized_activities = map(str, aggregated._activity_ids)
        else:
            for activity in aggregated.activities:
                serialized = activity_serializer.dumps(activity)
                check_reserved(serialized, [';', ';;'])
                serialized_activities.append(serialized)

        serialized_activities_part = ';'.join(serialized_activities)
        parts.append(serialized_activities_part)

        # add the minified activities
        parts.append(aggregated.minimized_activities)

        # stick everything together
        serialized_aggregated = ';;'.join(map(str, parts))
        serialized = '%s%s' % (self.identifier, serialized_aggregated)
        return serialized

    def loads(self, serialized_aggregated):
        activity_serializer = self.activity_serializer_class(Activity)
        try:
            serialized_aggregated = serialized_aggregated[2:]
            parts = serialized_aggregated.split(';;')
            # start with the group
            group = parts[0]
            aggregated = self.aggregated_activity_class(group)

            # get the date and activities
            date_dict = dict(zip(self.date_fields, parts[1:5]))
            for k, v in date_dict.items():
                date_value = None
                if v != '-1':
                    date_value = epoch_to_datetime(float(v))
                setattr(aggregated, k, date_value)

            # write the activities
            serializations = parts[5].split(';')
            if self.dehydrate:
                activity_ids = map(int, serializations)
                aggregated._activity_ids = activity_ids
                aggregated.dehydrated = True
            else:
                activities = [activity_serializer.loads(s)
                              for s in serializations]
                aggregated.activities = activities
                aggregated.dehydrated = False

            # write the minimized activities
            minimized = int(parts[6])
            aggregated.minimized_activities = minimized

            return aggregated
        except Exception, e:
            msg = unicode(e)
            raise SerializationException(msg)


class NotificationSerializer(AggregatedActivitySerializer):
    #: indicates if dumps returns dehydrated aggregated activities
    dehydrate = False

########NEW FILE########
__FILENAME__ = base
from feedly.activity import Activity, AggregatedActivity


class BaseSerializer(object):

    '''
    The base serializer class, only defines the signature for
    loads and dumps

    It serializes Activity objects
    '''

    def __init__(self, activity_class, *args, **kwargs):
        self.activity_class = activity_class

    def check_type(self, data):
        if not isinstance(data, Activity):
            raise ValueError('we only know how to dump activities, not %s' % type(data))

    def loads(self, serialized_activity):
        activity = serialized_activity
        return activity

    def dumps(self, activity):
        self.check_type(activity)
        return activity


class BaseAggregatedSerializer(BaseSerializer):

    '''
    Serialized aggregated activities
    '''
    #: indicates if dumps returns dehydrated aggregated activities
    dehydrate = False

    def __init__(self, aggregated_activity_class, *args, **kwargs):
        BaseSerializer.__init__(self, *args, **kwargs)
        self.aggregated_activity_class = aggregated_activity_class

    def check_type(self, data):
        if not isinstance(data, AggregatedActivity):
            raise ValueError(
                'we only know how to dump AggregatedActivity not %r' % data)

########NEW FILE########
__FILENAME__ = activity_serializer
from feedly.activity import Activity
from feedly.verbs import get_verb_by_id
import pickle
from feedly.serializers.base import BaseSerializer


class CassandraActivitySerializer(BaseSerializer):

    def __init__(self, model, *args, **kwargs):
        BaseSerializer.__init__(self, *args, **kwargs)
        self.model = model

    def dumps(self, activity):
        self.check_type(activity)
        return self.model(
            activity_id=long(activity.serialization_id),
            actor=activity.actor_id,
            time=activity.time,
            verb=activity.verb.id,
            object=activity.object_id,
            target=activity.target_id,
            extra_context=pickle.dumps(activity.extra_context)
        )

    def loads(self, serialized_activity):
        # TODO: convert cqlengine model to feedly Activity using public API
        activity_kwargs = {k: getattr(serialized_activity, k)
                           for k in serialized_activity.__dict__['_values'].keys()}
        activity_kwargs.pop('activity_id')
        activity_kwargs.pop('feed_id')
        activity_kwargs['verb'] = get_verb_by_id(int(serialized_activity.verb))
        activity_kwargs['extra_context'] = pickle.loads(
            activity_kwargs['extra_context']
        )
        return self.activity_class(**activity_kwargs)

########NEW FILE########
__FILENAME__ = aggregated_activity_serializer
from feedly.activity import AggregatedActivity
from feedly.serializers.aggregated_activity_serializer import AggregatedActivitySerializer
import pickle


class CassandraAggregatedActivitySerializer(AggregatedActivitySerializer):

    def __init__(self, model, *args, **kwargs):
        AggregatedActivitySerializer.__init__(self, *args, **kwargs)
        self.model = model

    def dumps(self, aggregated):
        activities = pickle.dumps(aggregated.activities)
        model_instance = self.model(
            activity_id=long(aggregated.serialization_id),
            activities=activities,
            group=aggregated.group,
            created_at=aggregated.created_at,
            updated_at=aggregated.updated_at
        )
        return model_instance

    def loads(self, serialized_aggregated):
        activities = pickle.loads(serialized_aggregated.activities)
        aggregated = self.aggregated_activity_class(
            group=serialized_aggregated.group,
            activities=activities,
            created_at=serialized_aggregated.created_at,
            updated_at=serialized_aggregated.updated_at,
        )
        return aggregated

########NEW FILE########
__FILENAME__ = dummy
from feedly.serializers.base import BaseSerializer, BaseAggregatedSerializer


class DummySerializer(BaseSerializer):

    '''
    The dummy serializer doesnt care about the type of your data
    '''

    def check_type(self, data):
        pass


class DummyAggregatedSerializer(BaseAggregatedSerializer):

    '''
    The dummy serializer doesnt care about the type of your data
    '''

    def check_type(self, data):
        pass

########NEW FILE########
__FILENAME__ = pickle_serializer
import pickle
from feedly.serializers.base import BaseSerializer, BaseAggregatedSerializer


class PickleSerializer(BaseSerializer):

    def loads(self, serialized_activity):
        activity = pickle.loads(serialized_activity)
        return activity

    def dumps(self, activity):
        self.check_type(activity)
        return pickle.dumps(activity)


class AggregatedActivityPickleSerializer(BaseAggregatedSerializer):
    #: indicates if dumps returns dehydrated aggregated activities
    dehydrate = True

    def loads(self, serialized_data):
        return pickle.loads(serialized_data)

    def dumps(self, aggregated):
        self.check_type(aggregated)
        if not aggregated.dehydrated:
            aggregated = aggregated.get_dehydrated()
        return pickle.dumps(aggregated)

########NEW FILE########
__FILENAME__ = simple_timeline_serializer
from feedly.activity import DehydratedActivity
from feedly.serializers.base import BaseSerializer


class SimpleTimelineSerializer(BaseSerializer):

    def loads(self, serialized_activity, *args, **kwargs):
        return DehydratedActivity(serialization_id=serialized_activity)

    def dumps(self, activity, *args, **kwargs):
        '''
        Returns the serialized version of activity and the
        '''
        return activity.serialization_id

########NEW FILE########
__FILENAME__ = utils
from feedly.exceptions import SerializationException


def check_reserved(value, reserved_characters):
    if any([reserved in value for reserved in reserved_characters]):
        raise SerializationException(
            'encountered reserved character %s in %s' % (reserved, value))

########NEW FILE########
__FILENAME__ = settings
from default_settings import *

'''
Please fork and add hooks to import your custom settings system.
Right now we only support Django, but the intention is to support
any settings system
'''


def import_global_module(module, current_locals, current_globals, exceptions=None):
    '''Import the requested module into the global scope
    Warning! This will import your module into the global scope

    **Example**:
        from django.conf import settings
        import_global_module(settings, locals(), globals())

    :param module: the module which to import into global scope
    :param current_locals: the local globals
    :param current_globals: the current globals
    :param exceptions: the exceptions which to ignore while importing

    '''
    try:
        try:
            objects = getattr(module, '__all__', dir(module))

            for k in objects:
                if k and k[0] != '_':
                    current_globals[k] = getattr(module, k)
        except exceptions, e:
            return e
    finally:
        del current_globals, current_locals


try:
    import django
    settings_system = 'django'
except ImportError, e:
    settings_system = None

if settings_system == 'django':
    from django.conf import settings
    import_global_module(settings, locals(), globals())

########NEW FILE########
__FILENAME__ = base
from feedly.serializers.dummy import DummySerializer
from feedly.serializers.simple_timeline_serializer import \
    SimpleTimelineSerializer
from feedly.utils import get_metrics_instance
from feedly.activity import AggregatedActivity, Activity


class BaseStorage(object):

    '''
    The feed uses two storage classes, the
    - Activity Storage and the
    - Timeline Storage

    The process works as follows::

        feed = BaseFeed()
        # the activity storage is used to store the activity and mapped to an id
        feed.insert_activity(activity)
        # now the id is inserted into the timeline storage
        feed.add(activity)

    Currently there are two activity storage classes ready for production:

    - Cassandra
    - Redis

    The storage classes always receive a full activity object.
    The serializer class subsequently determines how to transform the activity
    into something the database can store.
    '''
    #: The default serializer class to use
    default_serializer_class = DummySerializer
    metrics = get_metrics_instance()

    activity_class = Activity
    aggregated_activity_class = AggregatedActivity

    def __init__(self, serializer_class=None, activity_class=None, **options):
        '''
        :param serializer_class: allows you to overwrite the serializer class
        '''
        self.serializer_class = serializer_class or self.default_serializer_class
        self.options = options
        if activity_class is not None:
            self.activity_class = activity_class
        aggregated_activity_class = options.pop(
            'aggregated_activity_class', None)
        if aggregated_activity_class is not None:
            self.aggregated_activity_class = aggregated_activity_class

    def flush(self):
        '''
        Flushes the entire storage
        '''
        pass

    def activities_to_ids(self, activities_or_ids):
        '''
        Utility function for lower levels to chose either serialize
        '''
        ids = []
        for activity_or_id in activities_or_ids:
            ids.append(self.activity_to_id(activity_or_id))
        return ids

    def activity_to_id(self, activity):
        return getattr(activity, 'serialization_id', activity)

    @property
    def serializer(self):
        '''
        Returns an instance of the serializer class

        The serializer needs to know about the activity and
        aggregated activity classes we're using
        '''
        serializer_class = self.serializer_class
        kwargs = {}
        if getattr(self, 'aggregated_activity_class', None) is not None:
            kwargs[
                'aggregated_activity_class'] = self.aggregated_activity_class
        serializer_instance = serializer_class(
            activity_class=self.activity_class, **kwargs)
        return serializer_instance

    def serialize_activity(self, activity):
        '''
        Serialize the activity and returns the serialized activity

        :returns str: the serialized activity
        '''
        serialized_activity = self.serializer.dumps(activity)
        return serialized_activity

    def serialize_activities(self, activities):
        '''
        Serializes the list of activities

        :param activities: the list of activities
        '''
        serialized_activities = {}
        for activity in activities:
            serialized_activity = self.serialize_activity(activity)
            serialized_activities[
                self.activity_to_id(activity)] = serialized_activity
        return serialized_activities

    def deserialize_activities(self, serialized_activities):
        '''
        Serializes the list of activities

        :param serialized_activities: the list of activities
        :param serialized_activities: a dictionary with activity ids and activities
        '''
        activities = []
        # handle the case where this is a dict
        if isinstance(serialized_activities, dict):
            serialized_activities = serialized_activities.values()

        if serialized_activities is not None:
            for serialized_activity in serialized_activities:
                activity = self.serializer.loads(serialized_activity)
                activities.append(activity)
        return activities


class BaseActivityStorage(BaseStorage):

    '''
    The Activity storage globally stores a key value mapping.
    This is used to store the mapping between an activity_id and the actual
    activity object.

    **Example**::

        storage = BaseActivityStorage()
        storage.add_many(activities)
        storage.get_many(activity_ids)

    The storage specific functions are located in

    - add_to_storage
    - get_from_storage
    - remove_from_storage
    '''

    def add_to_storage(self, serialized_activities, *args, **kwargs):
        '''
        Adds the serialized activities to the storage layer

        :param serialized_activities: a dictionary with {id: serialized_activity}
        '''
        raise NotImplementedError()

    def get_from_storage(self, activity_ids, *args, **kwargs):
        '''
        Retrieves the given activities from the storage layer

        :param activity_ids: the list of activity ids
        :returns dict: a dictionary mapping activity ids to activities
        '''
        raise NotImplementedError()

    def remove_from_storage(self, activity_ids, *args, **kwargs):
        '''
        Removes the specified activities

        :param activity_ids: the list of activity ids
        '''
        raise NotImplementedError()

    def get_many(self, activity_ids, *args, **kwargs):
        '''
        Gets many activities and deserializes them

        :param activity_ids: the list of activity ids
        '''
        self.metrics.on_feed_read(self.__class__, len(activity_ids))
        activities_data = self.get_from_storage(activity_ids, *args, **kwargs)
        return self.deserialize_activities(activities_data)

    def get(self, activity_id, *args, **kwargs):
        results = self.get_many([activity_id], *args, **kwargs)
        if not results:
            return None
        else:
            return results[0]

    def add(self, activity, *args, **kwargs):
        return self.add_many([activity], *args, **kwargs)

    def add_many(self, activities, *args, **kwargs):
        '''
        Adds many activities and serializes them before forwarding
        this to add_to_storage

        :param activities: the list of activities
        '''
        self.metrics.on_feed_write(self.__class__, len(activities))
        serialized_activities = self.serialize_activities(activities)
        return self.add_to_storage(serialized_activities, *args, **kwargs)

    def remove(self, activity, *args, **kwargs):
        return self.remove_many([activity], *args, **kwargs)

    def remove_many(self, activities, *args, **kwargs):
        '''
        Figures out the ids of the given activities and forwards
        The removal to the remove_from_storage function

        :param activities: the list of activities
        '''
        self.metrics.on_feed_remove(self.__class__, len(activities))

        if activities and isinstance(activities[0], (basestring, int, long)):
            activity_ids = activities
        else:
            activity_ids = self.serialize_activities(activities).keys()
        return self.remove_from_storage(activity_ids, *args, **kwargs)


class BaseTimelineStorage(BaseStorage):

    '''
    The Timeline storage class handles the feed/timeline sorted part of storing
    a feed.

    **Example**::

        storage = BaseTimelineStorage()
        storage.add_many(key, activities)
        # get a sorted slice of the feed
        storage.get_slice(key, start, stop)
        storage.remove_many(key, activities)

    The storage specific functions are located in
    '''

    default_serializer_class = SimpleTimelineSerializer

    def add(self, key, activity, *args, **kwargs):
        return self.add_many(key, [activity], *args, **kwargs)

    def add_many(self, key, activities, *args, **kwargs):
        '''
        Adds the activities to the feed on the given key
        (The serialization is done by the serializer class)

        :param key: the key at which the feed is stored
        :param activities: the activities which to store
        '''
        self.metrics.on_feed_write(self.__class__, len(activities))
        serialized_activities = self.serialize_activities(activities)
        return self.add_to_storage(key, serialized_activities, *args, **kwargs)

    def remove(self, key, activity, *args, **kwargs):
        return self.remove_many(key, [activity], *args, **kwargs)

    def remove_many(self, key, activities, *args, **kwargs):
        '''
        Removes the activities from the feed on the given key
        (The serialization is done by the serializer class)

        :param key: the key at which the feed is stored
        :param activities: the activities which to remove
        '''
        self.metrics.on_feed_remove(self.__class__, len(activities))
        
        if activities and isinstance(activities[0], (basestring, int, long)):
            serialized_activities = {a: a for a in activities}
        else:
            serialized_activities = self.serialize_activities(activities)
        
        return self.remove_from_storage(key, serialized_activities, *args, **kwargs)

    def get_index_of(self, key, activity_id):
        raise NotImplementedError()

    def remove_from_storage(self, key, serialized_activities):
        raise NotImplementedError()

    def index_of(self, key, activity_or_id):
        '''
        Returns activity's index within a feed or raises ValueError if not present

        :param key: the key at which the feed is stored
        :param activity_id: the activity's id to search
        '''
        activity_id = self.activities_to_ids([activity_or_id])[0]
        return self.get_index_of(key, activity_id)

    def get_slice_from_storage(self, key, start, stop, filter_kwargs=None, ordering_args=None):
        '''
        :param key: the key at which the feed is stored
        :param start: start
        :param stop: stop
        :returns list: Returns a list with tuples of key,value pairs
        '''
        raise NotImplementedError()

    def get_slice(self, key, start, stop, filter_kwargs=None, ordering_args=None):
        '''
        Returns a sorted slice from the storage

        :param key: the key at which the feed is stored
        '''
        activities_data = self.get_slice_from_storage(
            key, start, stop, filter_kwargs=filter_kwargs, ordering_args=ordering_args)
        activities = []
        if activities_data:
            serialized_activities = zip(*activities_data)[1]
            activities = self.deserialize_activities(serialized_activities)
        self.metrics.on_feed_read(self.__class__, len(activities))
        return activities

    def get_batch_interface(self):
        '''
        Returns a context manager which ensure all subsequent operations
        Happen via a batch interface

        An example is redis.map
        '''
        raise NotImplementedError()

    def trim(self, key, length):
        '''
        Trims the feed to the given length

        :param key: the key location
        :param length: the length to which to trim
        '''
        pass

    def count(self, key, *args, **kwargs):
        raise NotImplementedError()

    def delete(self, key, *args, **kwargs):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = activity_storage
from feedly.storage.base import BaseActivityStorage


class CassandraActivityStorage(BaseActivityStorage):

    def get_from_storage(self, activity_ids, *args, **kwargs):
        pass

    def add_to_storage(self, serialized_activities, *args, **kwargs):
        pass

    def remove_from_storage(self, activity_ids, *args, **kwargs):
        pass

########NEW FILE########
__FILENAME__ = connection
from cqlengine import connection
from feedly import settings


def setup_connection():
    connection.setup(
        settings.FEEDLY_CASSANDRA_HOSTS,
        consistency=settings.FEEDLY_CASSANDRA_CONSISTENCY_LEVEL,
        default_keyspace=settings.FEEDLY_DEFAULT_KEYSPACE,
        metrics_enabled=settings.FEEDLY_TRACK_CASSANDRA_DRIVER_METRICS,
        default_timeout=settings.FEEDLY_CASSANDRA_DEFAULT_TIMEOUT
    )

########NEW FILE########
__FILENAME__ = models
from cqlengine import columns
from cqlengine.models import Model
from cqlengine.exceptions import ValidationError


class VarInt(columns.Column):
    db_type = 'varint'

    def validate(self, value):
        val = super(VarInt, self).validate(value)
        if val is None:
            return
        try:
            return long(val)
        except (TypeError, ValueError):
            raise ValidationError(
                "{} can't be converted to integer value".format(value))

    def to_python(self, value):
        return self.validate(value)

    def to_database(self, value):
        return self.validate(value)


class BaseActivity(Model):
    feed_id = columns.Ascii(primary_key=True, partition_key=True)
    activity_id = VarInt(primary_key=True, clustering_order='desc')


class Activity(BaseActivity):
    actor = columns.Integer(required=False)
    extra_context = columns.Bytes(required=False)
    object = columns.Integer(required=False)
    target = columns.Integer(required=False)
    time = columns.DateTime(required=False)
    verb = columns.Integer(required=False)


class AggregatedActivity(BaseActivity):
    activities = columns.Bytes(required=False)
    created_at = columns.DateTime(required=False)
    group = columns.Ascii(required=False)
    updated_at = columns.DateTime(required=False)

########NEW FILE########
__FILENAME__ = timeline_storage
from collections import defaultdict
from cqlengine import BatchQuery
from cqlengine.connection import execute
from feedly.storage.base import BaseTimelineStorage
from feedly.storage.cassandra import models
from feedly.serializers.cassandra.activity_serializer import CassandraActivitySerializer
from feedly.utils import memoized
import logging


logger = logging.getLogger(__name__)


class Batch(BatchQuery):

    """
    Batch class which inherits from cqlengine.BatchQuery and adds speed ups
    for inserts

    """

    def __init__(self, batch_type=None, timestamp=None,
                 batch_size=100, atomic_inserts=False):
        self.batch_inserts = defaultdict(list)
        self.batch_size = batch_size
        self.atomic_inserts = False
        super(Batch, self).__init__(batch_type, timestamp)

    def batch_insert(self, model_instance):
        modeltable = model_instance.__class__.__table_name__
        self.batch_inserts[modeltable].append(model_instance)

    def execute(self):
        super(Batch, self).execute()
        for instances in self.batch_inserts.values():
            modelclass = instances[0].__class__
            modelclass.objects.batch_insert(
                instances, self.batch_size, self.atomic_inserts)
        self.batch_inserts.clear()


@memoized
def factor_model(base_model, column_family_name):
    camel_case = ''.join([s.capitalize()
                         for s in column_family_name.split('_')])
    class_name = '%sFeedModel' % camel_case
    return type(class_name, (base_model,), {'__table_name__': column_family_name})


class CassandraTimelineStorage(BaseTimelineStorage):

    """
    A feed timeline implementation that uses Apache Cassandra 2.0 for storage.

    CQL3 is used to access the data stored on Cassandra via the ORM
    library CqlEngine.

    """

    from feedly.storage.cassandra.connection import setup_connection
    setup_connection()

    default_serializer_class = CassandraActivitySerializer
    base_model = models.Activity
    insert_batch_size = 100

    def __init__(self, serializer_class=None, **options):
        self.column_family_name = options.pop('column_family_name')
        super(CassandraTimelineStorage, self).__init__(
            serializer_class, **options)
        self.model = self.get_model(self.base_model, self.column_family_name)

    def add_to_storage(self, key, activities, batch_interface=None):
        batch = batch_interface or self.get_batch_interface()
        for model_instance in activities.values():
            model_instance.feed_id = str(key)
            batch.batch_insert(model_instance)
        if batch_interface is None:
            batch.execute()

    def remove_from_storage(self, key, activities, batch_interface=None):
        batch = batch_interface or self.get_batch_interface()
        for activity_id in activities.keys():
            self.model(feed_id=key, activity_id=activity_id).batch(
                batch).delete()
        if batch_interface is None:
            batch.execute()

    def trim(self, key, length, batch_interface=None):
        '''
        trim using Cassandra's tombstones black magic
        retrieve the WRITETIME of the last item we want to keep
        then delete everything written after that

        this is still pretty inefficient since it needs to retrieve
        length amount of items

        WARNING: since activities created using Batch share the same timestamp
        trim can trash up to (batch_size - 1) more activities than requested

        '''
        query = "SELECT WRITETIME(%s) as wt FROM %s.%s WHERE feed_id='%s' ORDER BY activity_id DESC LIMIT %s;"
        trim_col = [c for c in self.model._columns.keys(
        ) if c not in self.model._primary_keys.keys()][0]
        parameters = (
            trim_col, self.model._get_keyspace(), self.column_family_name, key, length + 1)
        results = execute(query % parameters)
        if len(results) < length:
            return
        trim_ts = (results[-1].wt + results[-2].wt) / 2
        delete_query = "DELETE FROM %s.%s USING TIMESTAMP %s WHERE feed_id='%s';"
        delete_params = (
            self.model._get_keyspace(), self.column_family_name, trim_ts, key)
        execute(delete_query % delete_params)

    def count(self, key):
        return self.model.objects.filter(feed_id=key).count()

    def delete(self, key):
        self.model.objects.filter(feed_id=key).delete()

    @classmethod
    def get_model(cls, base_model, column_family_name):
        '''
        Creates an instance of the base model with the table_name (column family name)
        set to column family name
        :param base_model: the model to extend from
        :param column_family_name: the name of the column family
        '''
        return factor_model(base_model, column_family_name)

    @property
    def serializer(self):
        '''
        Returns an instance of the serializer class
        '''
        serializer_class = self.serializer_class
        kwargs = {}
        if getattr(self, 'aggregated_activity_class', None) is not None:
            kwargs[
                'aggregated_activity_class'] = self.aggregated_activity_class
        serializer_instance = serializer_class(
            self.model, activity_class=self.activity_class, **kwargs)
        return serializer_instance

    def get_batch_interface(self):
        return Batch(batch_size=self.insert_batch_size, atomic_inserts=False)

    def contains(self, key, activity_id):
        return self.model.objects.filter(feed_id=key, activity_id=activity_id).count() > 0

    def index_of(self, key, activity_id):
        if not self.contains(key, activity_id):
            raise ValueError
        return len(self.model.objects.filter(feed_id=key, activity_id__gt=activity_id).values_list('feed_id'))

    def get_ordering_or_default(self, ordering_args):
        if ordering_args is None:
            ordering = ('-activity_id', )
        else:
            ordering = ordering_args
        return ordering

    def get_nth_item(self, key, index, ordering_args=None):
        ordering = self.get_ordering_or_default(ordering_args)
        return self.model.objects.filter(feed_id=key).order_by(*ordering).limit(index + 1)[index]

    def get_slice_from_storage(self, key, start, stop, filter_kwargs=None, ordering_args=None):
        '''
        :returns list: Returns a list with tuples of key,value pairs
        '''
        results = []
        limit = 10 ** 6

        ordering = self.get_ordering_or_default(ordering_args)

        query = self.model.objects.filter(feed_id=key)
        if filter_kwargs:
            query = query.filter(**filter_kwargs)

        try:
            if start not in (0, None):
                offset_activity_id = self.get_nth_item(key, start, ordering)
                query = query.filter(
                    activity_id__lte=offset_activity_id.activity_id)
        except IndexError:
            return []

        if stop is not None:
            limit = (stop - (start or 0))

        for activity in query.order_by(*ordering).limit(limit):
            results.append([activity.activity_id, activity])
        return results

########NEW FILE########
__FILENAME__ = memory
from collections import defaultdict
from feedly.storage.base import (BaseTimelineStorage, BaseActivityStorage)
from contextlib import contextmanager


timeline_store = defaultdict(list)
activity_store = defaultdict(dict)


def reverse_bisect_left(a, x, lo=0, hi=None):
    '''
    same as python bisect.bisect_left but for
    lists with reversed order
    '''
    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if x > a[mid]:
            hi = mid
        else:
            lo = mid + 1
    return lo


class InMemoryActivityStorage(BaseActivityStorage):

    def get_from_storage(self, activity_ids, *args, **kwargs):
        return {_id: activity_store.get(_id) for _id in activity_ids}

    def add_to_storage(self, activities, *args, **kwargs):
        insert_count = 0
        for activity_id, activity_data in activities.iteritems():
            if activity_id not in activity_store:
                insert_count += 1
            activity_store[activity_id] = activity_data
        return insert_count

    def remove_from_storage(self, activity_ids, *args, **kwargs):
        removed = 0
        for activity_id in activity_ids:
            exists = activity_store.pop(activity_id, None)
            if exists:
                removed += 1
        return removed

    def flush(self):
        activity_store.clear()


class InMemoryTimelineStorage(BaseTimelineStorage):

    def contains(self, key, activity_id):
        return activity_id in timeline_store[key]

    def get_index_of(self, key, activity_id):
        return timeline_store[key].index(activity_id)

    def get_slice_from_storage(self, key, start, stop, filter_kwargs=None, ordering_args=None):
        results = list(timeline_store[key][start:stop])
        score_value_pairs = zip(results, results)
        return score_value_pairs

    def add_to_storage(self, key, activities, *args, **kwargs):
        timeline = timeline_store[key]
        initial_count = len(timeline)
        for activity_id, activity_data in activities.iteritems():
            if self.contains(key, activity_id):
                continue
            timeline.insert(reverse_bisect_left(
                timeline, activity_id), activity_data)
        return len(timeline) - initial_count

    def remove_from_storage(self, key, activities, *args, **kwargs):
        timeline = timeline_store[key]
        initial_count = len(timeline)
        for activity_id, activity_data in activities.iteritems():
            if self.contains(key, activity_id):
                timeline.remove(activity_id)
        return initial_count - len(timeline)

    @classmethod
    def get_batch_interface(cls):
        @contextmanager
        def meandmyself():
            yield cls
        return meandmyself

    def count(self, key, *args, **kwargs):
        return len(timeline_store[key])

    def delete(self, key, *args, **kwargs):
        timeline_store.pop(key, None)

    def trim(self, key, length):
        timeline_store[key] = timeline_store[key][:length]

########NEW FILE########
__FILENAME__ = activity_storage
from feedly.storage.base import BaseActivityStorage
from feedly.storage.redis.structures.hash import ShardedHashCache
from feedly.serializers.activity_serializer import ActivitySerializer


class ActivityCache(ShardedHashCache):
    key_format = 'activity:cache:%s'


class RedisActivityStorage(BaseActivityStorage):
    default_serializer_class = ActivitySerializer

    def get_key(self):
        return self.options.get('key', 'global')

    def get_cache(self):
        key = self.get_key()
        return ActivityCache(key)

    def get_from_storage(self, activity_ids, *args, **kwargs):
        cache = self.get_cache()
        activities = cache.get_many(activity_ids)
        activities = dict((k, unicode(v)) for k, v in activities.items() if v)
        return activities

    def add_to_storage(self, serialized_activities, *args, **kwargs):
        cache = self.get_cache()
        key_value_pairs = serialized_activities.items()
        result = cache.set_many(key_value_pairs)
        insert_count = 0
        if result:
            insert_count = len(key_value_pairs)

        return insert_count

    def remove_from_storage(self, activity_ids, *args, **kwargs):
        # we never explicitly remove things from storage
        cache = self.get_cache()
        result = cache.delete_many(activity_ids)
        return result

    def flush(self):
        cache = self.get_cache()
        cache.delete()

########NEW FILE########
__FILENAME__ = connection
import redis
from feedly import settings

connection_pool = None


def get_redis_connection(server_name='default'):
    '''
    Gets the specified redis connection
    '''
    global connection_pool

    if connection_pool is None:
        connection_pool = setup_redis()

    pool = connection_pool[server_name]

    return redis.StrictRedis(connection_pool=pool)


def setup_redis():
    '''
    Starts the connection pool for all configured redis servers
    '''
    pools = {}
    for name, config in settings.FEEDLY_REDIS_CONFIG.items():
        pool = redis.ConnectionPool(
            host=config['host'],
            port=config['port'],
            password=config.get('password'),
            db=config['db']
        )
        pools[name] = pool
    return pools

########NEW FILE########
__FILENAME__ = base
from feedly.storage.redis.connection import get_redis_connection
from redis.client import BasePipeline


class RedisCache(object):

    '''
    The base for all redis data structures
    '''
    key_format = 'redis:cache:%s'

    def __init__(self, key, redis=None):
        # write the key
        self.key = key
        # handy when using fallback to other data sources
        self.source = 'redis'
        # the redis connection, self.redis is lazy loading the connection
        self._redis = redis

    def get_redis(self):
        '''
        Only load the redis connection if we use it
        '''
        if self._redis is None:
            self._redis = get_redis_connection()
        return self._redis

    def set_redis(self, value):
        '''
        Sets the redis connection
        '''
        self._redis = value

    redis = property(get_redis, set_redis)

    def get_key(self):
        return self.key

    def delete(self):
        key = self.get_key()
        self.redis.delete(key)

    def _pipeline_if_needed(self, operation, *args, **kwargs):
        '''
        If the redis connection is already in distributed state use it
        Otherwise spawn a new distributed connection using .map
        '''
        pipe_needed = not isinstance(self.redis, BasePipeline)
        if pipe_needed:
            pipe = self.redis.pipeline(transaction=False)
            operation(pipe, *args, **kwargs)
            results = pipe.execute()
        else:
            results = operation(self.redis, *args, **kwargs)
        return results

########NEW FILE########
__FILENAME__ = hash
from feedly.storage.redis.structures.base import RedisCache
import logging
logger = logging.getLogger(__name__)


class BaseRedisHashCache(RedisCache):
    key_format = 'redis:base_hash_cache:%s'
    pass


class RedisHashCache(BaseRedisHashCache):
    key_format = 'redis:hash_cache:%s'

    def get_key(self, *args, **kwargs):
        return self.key

    def count(self):
        '''
        Returns the number of elements in the sorted set
        '''
        key = self.get_key()
        redis_result = self.redis.hlen(key)
        redis_count = int(redis_result)
        return redis_count

    def contains(self, field):
        '''
        Uses hexists to see if the given field is present
        '''
        key = self.get_key()
        result = self.redis.hexists(key, field)
        activity_found = bool(result)
        return activity_found

    def get(self, field):
        fields = [field]
        results = self.get_many(fields)
        result = results[field]
        return result

    def keys(self):
        key = self.get_key()
        keys = self.redis.hkeys(key)
        return keys

    def delete_many(self, fields):
        results = {}

        def _delete_many(redis, fields):
            for field in fields:
                key = self.get_key(field)
                logger.debug('removing field %s from %s', field, key)
                result = redis.hdel(key, field)
                results[field] = result
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_delete_many, fields)

        return results

    def get_many(self, fields):
        key = self.get_key()
        results = {}
        values = list(self.redis.hmget(key, fields))
        for field, result in zip(fields, values):
            logger.debug('getting field %s from %s', field, key)
            results[field] = result

        return results

    def set(self, key, value):
        key_value_pairs = [(key, value)]
        results = self.set_many(key_value_pairs)
        result = results[0]
        return result

    def set_many(self, key_value_pairs):
        results = []

        def _set_many(redis, key_value_pairs):
            for field, value in key_value_pairs:
                key = self.get_key(field)
                logger.debug(
                    'writing hash(%s) field %s to %s', key, field, value)
                result = redis.hmset(key, {field: value})
                results.append(result)
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_set_many, key_value_pairs)

        return results


class FallbackHashCache(RedisHashCache):

    '''
    Redis structure with fallback to the database
    '''
    key_format = 'redis:db_hash_cache:%s'

    def get_many(self, fields, database_fallback=True):
        results = {}

        def _get_many(redis, fields):
            for field in fields:
                # allow for easy sharding
                key = self.get_key(field)
                logger.debug('getting field %s from %s', field, key)
                result = redis.hget(key, field)
                results[field] = result
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_get_many, fields)
        results = dict(zip(fields, results))

        # query missing results from the database and store them
        if database_fallback:
            missing_keys = [f for f in fields if not results[f]]
            database_results = self.get_many_from_fallback(missing_keys)
            # update our results with the data from the db and send them to
            # redis
            results.update(database_results)
            self.set_many(database_results.items())

        return results

    def get_many_from_fallback(self, missing_keys):
        '''
        Return a dictionary with the serialized values for the missing keys
        '''
        raise NotImplementedError('Please implement this')


class ShardedHashCache(RedisHashCache):

    '''
    Use multiple keys instead of one so its easier to shard across redis machines
    '''
    number_of_keys = 10

    def get_keys(self):
        '''
        Returns all possible keys
        '''
        keys = []
        for x in range(self.number_of_keys):
            key = self.key + ':%s' % x
            keys.append(key)
        return keys

    def get_key(self, field):
        '''
        Takes something like
        field="3,79159750" and returns 7 as the index
        '''
        import hashlib
        # redis treats everything like strings
        field = str(field)
        number = int(hashlib.md5(field).hexdigest(), 16)
        position = number % self.number_of_keys
        return self.key + ':%s' % position

    def get_many(self, fields):
        results = {}

        def _get_many(redis, fields):
            for field in fields:
                # allow for easy sharding
                key = self.get_key(field)
                logger.debug('getting field %s from %s', field, key)
                result = redis.hget(key, field)
                results[field] = result
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_get_many, fields)
        results = dict(zip(fields, results))

        return results

    def delete_many(self, fields):
        results = {}

        def _get_many(redis, fields):
            for field in fields:
                # allow for easy sharding
                key = self.get_key(field)
                logger.debug('getting field %s from %s', field, key)
                result = redis.hdel(key, field)
                results[field] = result
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_get_many, fields)
        results = dict(zip(fields, results))
        # results = dict((k, v) for k, v in results.items() if v)

        return results

    def count(self):
        '''
        Returns the number of elements in the sorted set
        '''
        logger.warn('counting all keys is slow and should be used sparsely')
        keys = self.get_keys()
        total = 0
        for key in keys:
            redis_result = self.redis.hlen(key)
            redis_count = int(redis_result)
            total += redis_count
        return total

    def contains(self, field):
        raise NotImplementedError(
            'contains isnt implemented for ShardedHashCache')

    def delete(self):
        '''
        Delete all the base variations of the key
        '''
        logger.warn('deleting all keys is slow and should be used sparsely')
        keys = self.get_keys()

        for key in keys:
            # TODO, batch this, but since we barely do this
            # not too important
            self.redis.delete(key)

    def keys(self):
        '''
        list all the keys, very slow, don't use too often
        '''
        logger.warn('listing all keys is slow and should be used sparsely')
        keys = self.get_keys()
        fields = []
        for key in keys:
            more_fields = self.redis.hkeys(key)
            fields += more_fields
        return fields


class ShardedDatabaseFallbackHashCache(ShardedHashCache, FallbackHashCache):
    pass

########NEW FILE########
__FILENAME__ = list
from feedly.storage.redis.structures.base import RedisCache
import logging
logger = logging.getLogger(__name__)


class BaseRedisListCache(RedisCache):

    '''
    Generic list functionality used for both the sorted set and list implementations

    Retrieve the sorted list/sorted set by using python slicing
    '''
    key_format = 'redis:base_list_cache:%s'
    max_length = 100

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        This is the complicated stuff which allows us to slice
        """
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        # Remember if it's a slice or not. We're going to treat everything as
        # a slice to simply the logic and will `.pop()` at the end as needed.
        if isinstance(k, slice):
            start = k.start

            if k.stop is not None:
                bound = int(k.stop)
            else:
                bound = None
        else:
            start = k
            bound = k + 1

        start = start or 0

        # We need check to see if we need to populate more of the cache.
        try:
            results = self.get_results(start, bound)
        except StopIteration:
            # There's nothing left, even though the bound is higher.
            results = None

        return results

    def get_results(self, start, stop):
        raise NotImplementedError('please define this function in subclasses')


class RedisListCache(BaseRedisListCache):
    key_format = 'redis:list_cache:%s'
    #: the maximum number of items the list stores
    max_items = 1000

    def get_results(self, start, stop):
        if start is None:
            start = 0
        if stop is None:
            stop = -1
        key = self.get_key()
        results = self.redis.lrange(key, start, stop)
        return results

    def append(self, value):
        values = [value]
        results = self.append_many(values)
        result = results[0]
        return result

    def append_many(self, values):
        key = self.get_key()
        results = []

        def _append_many(redis, values):
            for value in values:
                logger.debug('adding to %s with value %s', key, value)
                result = redis.rpush(key, value)
                results.append(result)
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_append_many, values)

        return results

    def remove(self, value):
        values = [value]
        results = self.remove_many(values)
        result = results[0]
        return result

    def remove_many(self, values):
        key = self.get_key()
        results = []

        def _remove_many(redis, values):
            for value in values:
                logger.debug('removing from %s with value %s', key, value)
                result = redis.lrem(key, 10, value)
                results.append(result)
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_remove_many, values)

        return results

    def count(self):
        key = self.get_key()
        count = self.redis.llen(key)
        return count

    def trim(self):
        '''
        Removes the old items in the list
        '''
        # clean up everything with a rank lower than max items up to the end of
        # the list
        key = self.get_key()
        removed = self.redis.ltrim(key, 0, self.max_items - 1)
        msg_format = 'cleaning up the list %s to a max of %s items'
        logger.info(msg_format, self.get_key(), self.max_items)
        return removed


class FallbackRedisListCache(RedisListCache):

    '''
    Redis list cache which after retrieving all items from redis falls back
    to a main data source (like the database)
    '''
    key_format = 'redis:db_list_cache:%s'

    def get_fallback_results(self, start, stop):
        raise NotImplementedError('please define this function in subclasses')

    def get_results(self, start, stop):
        '''
        Retrieves results from redis and the fallback datasource
        '''
        if stop is not None:
            redis_results = self.get_redis_results(start, stop - 1)
            required_items = stop - start
            enough_results = len(redis_results) == required_items
            assert len(redis_results) <= required_items, 'we should never have more than we ask for, start %s, stop %s' % (
                start, stop)
        else:
            # [start:] slicing does not know what's enough so
            # does not hit the db unless the cache is empty
            redis_results = self.get_redis_results(start, stop)
            enough_results = True
        if not redis_results or not enough_results:
            self.source = 'fallback'
            filtered = getattr(self, "_filtered", False)
            db_results = self.get_fallback_results(start, stop)

            if start == 0 and not redis_results and not filtered:
                logger.info('setting cache for type %s with len %s',
                            self.get_key(), len(db_results))
                # only cache when we have no results, to prevent duplicates
                self.cache(db_results)
            elif start == 0 and redis_results and not filtered:
                logger.info('overwriting cache for type %s with len %s',
                            self.get_key(), len(db_results))
                # clear the cache and add these values
                self.overwrite(db_results)
            results = db_results
            logger.info(
                'retrieved %s to %s from db and not from cache with key %s' %
                (start, stop, self.get_key()))
        else:
            results = redis_results
            logger.info('retrieved %s to %s from cache on key %s' %
                        (start, stop, self.get_key()))
        return results

    def get_redis_results(self, start, stop):
        '''
        Returns the results from redis

        :param start: the beginning
        :param stop: the end
        '''
        results = RedisListCache.get_results(self, start, stop)
        return results

    def cache(self, fallback_results):
        '''
        Hook to write the results from the fallback to redis
        '''
        self.append_many(fallback_results)

    def overwrite(self, fallback_results):
        '''
        Clear the cache and write the results from the fallback
        '''
        self.delete()
        self.cache(fallback_results)

########NEW FILE########
__FILENAME__ = sorted_set
from feedly.utils.functional import lazy
from feedly.storage.redis.structures.hash import BaseRedisHashCache
from feedly.storage.redis.structures.list import BaseRedisListCache
import logging
from feedly.utils import epoch_to_datetime, chunks
logger = logging.getLogger(__name__)


class RedisSortedSetCache(BaseRedisListCache, BaseRedisHashCache):
    sort_asc = False

    def count(self):
        '''
        Returns the number of elements in the sorted set
        '''
        key = self.get_key()
        redis_result = self.redis.zcount(key, '-inf', '+inf')
        # lazily convert this to an int, this keeps it compatible with
        # distributed connections
        redis_count = lambda: int(redis_result)
        lazy_factory = lazy(redis_count, int, long)
        lazy_object = lazy_factory()
        return lazy_object

    def index_of(self, value):
        '''
        Returns the index of the given value
        '''
        if self.sort_asc:
            redis_rank_fn = self.redis.zrank
        else:
            redis_rank_fn = self.redis.zrevrank
        key = self.get_key()
        result = redis_rank_fn(key, value)
        if result:
            result = int(result)
        elif result is None:
            raise ValueError(
                'Couldnt find item with value %s in key %s' % (value, key))
        return result

    def add(self, score, key):
        score_value_pairs = [(score, key)]
        results = self.add_many(score_value_pairs)
        result = results[0]
        return result

    def add_many(self, score_value_pairs):
        '''
        StrictRedis so it expects score1, name1
        '''
        key = self.get_key()
        scores = zip(*score_value_pairs)[0]
        msg_format = 'Please send floats as the first part of the pairs got %s'
        numeric_types = (float, int, long)
        if not all([isinstance(score, numeric_types) for score in scores]):
            raise ValueError(msg_format % score_value_pairs)
        results = []

        def _add_many(redis, score_value_pairs):
            score_value_list = sum(map(list, score_value_pairs), [])
            score_value_chunks = chunks(score_value_list, 200)

            for score_value_chunk in score_value_chunks:
                result = redis.zadd(key, *score_value_chunk)
                logger.debug('adding to %s with score_value_chunk %s',
                             key, score_value_chunk)
                results.append(result)
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_add_many, score_value_pairs)

        return results

    def remove_many(self, values):
        '''
        values
        '''
        key = self.get_key()
        results = []

        def _remove_many(redis, values):
            for value in values:
                logger.debug('removing value %s from %s', value, key)
                result = redis.zrem(key, value)
                results.append(result)
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_remove_many, values)

        return results

    def remove_by_scores(self, scores):
        key = self.get_key()
        results = []

        def _remove_many(redis, scores):
            for score in scores:
                logger.debug('removing score %s from %s', score, key)
                result = redis.zremrangebyscore(key, score, score)
                results.append(result)
            return results

        # start a new map redis or go with the given one
        results = self._pipeline_if_needed(_remove_many, scores)

        return results

    def contains(self, value):
        '''
        Uses zscore to see if the given activity is present in our sorted set
        '''
        key = self.get_key()
        result = self.redis.zscore(key, value)
        activity_found = result is not None
        return activity_found

    def trim(self, max_length=None):
        '''
        Trim the sorted set to max length
        zremrangebyscore
        '''
        key = self.get_key()
        if max_length is None:
            max_length = self.max_length

        # map things to the funny redis syntax
        end = (max_length * -1) - 1

        removed = self.redis.zremrangebyrank(key, 0, end)
        logger.info('cleaning up the sorted set %s to a max of %s items' %
                    (key, max_length))
        return removed

    def get_results(self, start=None, stop=None, min_score=None, max_score=None):
        '''
        Retrieve results from redis using zrevrange
        O(log(N)+M) with N being the number of elements in the sorted set and M the number of elements returned.
        '''
        if self.sort_asc:
            redis_range_fn = self.redis.zrangebyscore
        else:
            redis_range_fn = self.redis.zrevrangebyscore

        # -1 means infinity
        if stop is None:
            stop = -1

        if start is None:
            start = 0

        if stop != -1:
            limit = stop - start
        else:
            limit = -1

        key = self.get_key()

        # some type validations
        if min_score and not isinstance(min_score, (float, int, long)):
            raise ValueError(
                'min_score is not of type float, int or long got %s' % min_score)
        if max_score and not isinstance(max_score, (float, int, long)):
            raise ValueError(
                'max_score is not of type float, int or long got %s' % max_score)

        if min_score is None:
            min_score = '-inf'
        if max_score is None:
            max_score = '+inf'

        # handle the starting score support
        results = redis_range_fn(
            key, start=start, num=limit, withscores=True, min=min_score, max=max_score)
        return results

########NEW FILE########
__FILENAME__ = timeline_storage
from feedly.storage.base import BaseTimelineStorage
from feedly.storage.redis.structures.sorted_set import RedisSortedSetCache
from feedly.storage.redis.connection import get_redis_connection


class TimelineCache(RedisSortedSetCache):
    sort_asc = False


class RedisTimelineStorage(BaseTimelineStorage):

    def get_cache(self, key):
        cache = TimelineCache(key)
        return cache

    def contains(self, key, activity_id):
        cache = self.get_cache(key)
        contains = cache.contains(activity_id)
        return contains

    def get_slice_from_storage(self, key, start, stop, filter_kwargs=None, ordering_args=None):
        '''
        Returns a slice from the storage
        :param key: the redis key at which the sorted set is located
        :param start: the start
        :param stop: the stop
        :param filter_kwargs: a dict of filter kwargs
        :param ordering_args: a list of fields used for sorting

        **Example**::
           get_slice_from_storage('feed:13', 0, 10, {activity_id__lte=10})
        '''
        cache = self.get_cache(key)

        # parse the filter kwargs and translate them to min max
        # as used by the get results function
        valid_kwargs = [
            'activity_id__gte', 'activity_id__lte',
            'activity_id__gt', 'activity_id__lt',
        ]
        filter_kwargs = filter_kwargs or {}
        result_kwargs = {}
        for k in valid_kwargs:
            v = filter_kwargs.pop(k, None)
            if v is not None:
                if not isinstance(v, (float, int, long)):
                    raise ValueError(
                        'Filter kwarg values should be floats, int or long, got %s=%s' % (k, v))
                _, direction = k.split('__')
                equal = 'te' in direction
                offset = 0.01
                if 'gt' in direction:
                    if not equal:
                        v += offset
                    result_kwargs['min_score'] = v
                else:
                    if not equal:
                        v -= offset
                    result_kwargs['max_score'] = v
        # complain if we didn't recognize the filter kwargs
        if filter_kwargs:
            raise ValueError('Unrecognized filter kwargs %s' % filter_kwargs)

        # get the actual results
        key_score_pairs = cache.get_results(start, stop, **result_kwargs)
        score_key_pairs = [(score, data) for data, score in key_score_pairs]

        return score_key_pairs

    def get_batch_interface(self):
        return get_redis_connection().pipeline(transaction=False)

    def get_index_of(self, key, activity_id):
        cache = self.get_cache(key)
        index = cache.index_of(activity_id)
        return index

    def add_to_storage(self, key, activities, batch_interface=None):
        cache = self.get_cache(key)
        # turn it into key value pairs
        scores = map(long, activities.keys())
        score_value_pairs = zip(scores, activities.values())
        result = cache.add_many(score_value_pairs)
        for r in result:
            # errors in strings?
            # anyhow raise them here :)
            if hasattr(r, 'isdigit') and not r.isdigit():
                raise ValueError('got error %s in results %s' % (r, result))
        return result

    def remove_from_storage(self, key, activities, batch_interface=None):
        cache = self.get_cache(key)
        results = cache.remove_many(activities.values())
        return results

    def count(self, key):
        cache = self.get_cache(key)
        return int(cache.count())

    def delete(self, key):
        cache = self.get_cache(key)
        cache.delete()

    def trim(self, key, length, batch_interface=None):
        cache = self.get_cache(key)
        cache.trim(length)

########NEW FILE########
__FILENAME__ = tasks
from celery import task
from feedly.activity import Activity, AggregatedActivity


@task.task()
def fanout_operation(feed_manager, feed_class, user_ids, operation, operation_kwargs):
    '''
    Simple task wrapper for _fanout task
    Just making sure code is where you expect it :)
    '''
    feed_manager.fanout(user_ids, feed_class, operation, operation_kwargs)
    return "%d user_ids, %r, %r (%r)" % (len(user_ids), feed_class, operation, operation_kwargs)


@task.task()
def fanout_operation_hi_priority(feed_manager, feed_class, user_ids, operation, operation_kwargs):
    return fanout_operation(feed_manager, feed_class, user_ids, operation, operation_kwargs)


@task.task()
def fanout_operation_low_priority(feed_manager, feed_class, user_ids, operation, operation_kwargs):
    return fanout_operation(feed_manager, feed_class, user_ids, operation, operation_kwargs)


@task.task()
def follow_many(feed_manager, user_id, target_ids, follow_limit):
    feeds = feed_manager.get_feeds(user_id).values()
    target_feeds = map(feed_manager.get_user_feed, target_ids)

    activities = []
    for target_feed in target_feeds:
        activities += target_feed[:follow_limit]
    for feed in feeds:
        with feed.get_timeline_batch_interface() as batch_interface:
            feed.add_many(activities, batch_interface=batch_interface)


@task.task()
def unfollow_many(feed_manager, user_id, source_ids):
    for feed in feed_manager.get_feeds(user_id).values():
        activities = []
        feed.trim()
        for item in feed[:feed.max_length]:
            if isinstance(item, Activity):
                if item.actor_id in source_ids:
                    activities.append(item)
            elif isinstance(item, AggregatedActivity):
                activities.extend(
                    [activity for activity in item.activities if activity.actor_id in source_ids])

        if activities:
            feed.remove_many(activities)

########NEW FILE########
__FILENAME__ = activity
from feedly.activity import Activity
from feedly.activity import AggregatedActivity
from feedly.activity import DehydratedActivity
from feedly.tests.utils import Pin
from feedly.verbs.base import Love as LoveVerb
import unittest
from feedly.aggregators.base import RecentVerbAggregator
from feedly.exceptions import ActivityNotFound
from feedly.exceptions import DuplicateActivityException


class TestActivity(unittest.TestCase):

    def test_serialization_length(self):
        activity_object = Pin(id=1)
        activity = Activity(1, LoveVerb, activity_object)
        assert len(str(activity.serialization_id)) == 26

    def test_serialization_type(self):
        activity_object = Pin(id=1)
        activity = Activity(1, LoveVerb, activity_object)
        assert isinstance(activity.serialization_id, (int, long, float))

    def test_serialization_overflow_check_object_id(self):
        activity_object = Pin(id=10 ** 10)
        activity = Activity(1, LoveVerb, activity_object)
        with self.assertRaises(TypeError):
            activity.serialization_id

    def test_serialization_overflow_check_role_id(self):
        activity_object = Pin(id=1)
        Verb = type('Overflow', (LoveVerb,), {'id': 9999})
        activity = Activity(1, Verb, activity_object)
        with self.assertRaises(TypeError):
            activity.serialization_id

    def test_dehydrated_activity(self):
        activity_object = Pin(id=1)
        activity = Activity(1, LoveVerb, activity_object)
        dehydrated = activity.get_dehydrated()
        self.assertTrue(isinstance(dehydrated, DehydratedActivity))
        self.assertEquals(
            dehydrated.serialization_id, activity.serialization_id)

    def test_compare_apple_and_oranges(self):
        activity_object = Pin(id=1)
        activity = Activity(1, LoveVerb, activity_object)
        with self.assertRaises(ValueError):
            activity == activity_object


class TestAggregatedActivity(unittest.TestCase):

    def test_contains(self):
        activity = Activity(1, LoveVerb, Pin(id=1))
        aggregated = AggregatedActivity(1, [activity])
        self.assertTrue(aggregated.contains(activity))

    def test_duplicated_activities(self):
        activity = Activity(1, LoveVerb, Pin(id=1))
        aggregated = AggregatedActivity(1, [activity])
        with self.assertRaises(DuplicateActivityException):
            aggregated.append(activity)

    def test_compare_apple_and_oranges(self):
        activity = AggregatedActivity(1, [Activity(1, LoveVerb, Pin(id=1))])
        with self.assertRaises(ValueError):
            activity == Pin(id=1)

    def test_contains_extraneous_object(self):
        activity = AggregatedActivity(1, [Activity(1, LoveVerb, Pin(id=1))])
        with self.assertRaises(ValueError):
            activity.contains(Pin(id=1))

    def test_aggregated_properties(self):
        activities = []
        for x in range(1, 101):
            activity_object = Pin(id=x)
            activity = Activity(x, LoveVerb, activity_object)
            activities.append(activity)
        aggregator = RecentVerbAggregator()
        aggregated_activities = aggregator.aggregate(activities)
        aggregated = aggregated_activities[0]

        self.assertEqual(aggregated.verbs, [LoveVerb])
        self.assertEqual(aggregated.verb, LoveVerb)
        self.assertEqual(aggregated.actor_count, 100)
        self.assertEqual(aggregated.minimized_activities, 85)
        self.assertEqual(aggregated.other_actor_count, 98)
        self.assertEqual(aggregated.activity_count, 100)
        self.assertEqual(aggregated.object_ids, range(86, 101))
        # the other ones should be dropped
        self.assertEqual(aggregated.actor_ids, range(86, 101))
        self.assertEqual(aggregated.is_seen(), False)
        self.assertEqual(aggregated.is_read(), False)

    def generate_aggregated_activities(self, diff=0):
        aggregator = RecentVerbAggregator()
        activities = []
        for x in range(1, 20 + diff):
            activity = Activity(x, LoveVerb, Pin(id=x))
            activities.append(activity)
        aggregated_activities = aggregator.aggregate(activities)
        return aggregated_activities

    def test_aggregated_compare(self):
        aggregated_activities = self.generate_aggregated_activities()
        aggregated_activities_two = self.generate_aggregated_activities()
        aggregated_activities_three = self.generate_aggregated_activities(3)

        # this should be equal
        self.assertEqual(aggregated_activities, aggregated_activities_two)
        # this should not be equal
        self.assertNotEqual(aggregated_activities, aggregated_activities_three)

    def test_aggregated_remove(self):
        activities = []
        for x in range(1, 101):
            activity_object = Pin(id=x)
            activity = Activity(x, LoveVerb, activity_object)
            activities.append(activity)
        aggregator = RecentVerbAggregator()
        aggregated_activities = aggregator.aggregate(activities)
        aggregated = aggregated_activities[0]
        for activity in activities:
            try:
                aggregated.remove(activity)
            except (ActivityNotFound, ValueError):
                pass
        self.assertEqual(len(aggregated.activities), 1)
        self.assertEqual(aggregated.activity_count, 72)

########NEW FILE########
__FILENAME__ = base
from feedly.activity import Activity, AggregatedActivity
from feedly.feeds.aggregated_feed.base import AggregatedFeed
from feedly.tests.utils import FakeActivity
from feedly.utils.timing import timer
from feedly.verbs.base import Add as AddVerb, Love as LoveVerb
import copy
import datetime
import random
import unittest


def implementation(meth):
    def wrapped_test(self, *args, **kwargs):
        if self.feed_cls == AggregatedFeed:
            raise unittest.SkipTest('only test this on actual implementations')
        return meth(self, *args, **kwargs)
    return wrapped_test


class TestAggregatedFeed(unittest.TestCase):
    feed_cls = AggregatedFeed
    activity_class = Activity
    aggregated_activity_class = AggregatedActivity

    def setUp(self):
        self.user_id = 42
        self.test_feed = self.feed_cls(self.user_id)
        self.activity = self.activity_class(
            1, LoveVerb, 1, 1, datetime.datetime.now(), {})
        activities = []
        base_time = datetime.datetime.now() - datetime.timedelta(days=10)
        for x in range(1, 10):
            activity_time = base_time + datetime.timedelta(
                hours=x)
            activity = self.activity_class(
                x, LoveVerb, 1, x, activity_time, dict(x=x))
            activities.append(activity)
        for x in range(20, 30):
            activity_time = base_time + datetime.timedelta(
                hours=x)
            activity = self.activity_class(
                x, AddVerb, 1, x, activity_time, dict(x=x))
            activities.append(activity)
        self.activities = activities
        aggregator = self.test_feed.get_aggregator()
        self.aggregated_activities = aggregator.aggregate(activities)
        self.aggregated = self.aggregated_activities[0]
        if self.__class__ != TestAggregatedFeed:
            self.test_feed.delete()

    # def tearDown(self):
    #     if self.feed_cls != AggregatedFeed:
    #         self.test_feed.delete()

    @implementation
    def test_add_aggregated_activity(self):
        # start by adding one
        self.test_feed.insert_activities(self.aggregated.activities)
        self.test_feed.add_many_aggregated([self.aggregated])
        assert len(self.test_feed[:10]) == 1

    @implementation
    def test_slicing(self):
        # start by adding one
        self.test_feed.insert_activities(self.aggregated.activities)
        self.test_feed.add_many_aggregated([self.aggregated])
        assert len(self.test_feed[:10]) == 1

        assert len(self.test_feed[:]) == 1

    @implementation
    def test_translate_diff(self):
        new = [self.aggregated_activities[0]]
        deleted = [self.aggregated_activities[1]]
        from_aggregated = copy.deepcopy(self.aggregated_activities[1])
        from_aggregated.seen_at = datetime.datetime.now()
        to_aggregated = copy.deepcopy(from_aggregated)
        to_aggregated.seen_at = None
        changed = [(from_aggregated, to_aggregated)]
        to_remove, to_add = self.test_feed._translate_diff(
            new, changed, deleted)

        correct_to_remove = [self.aggregated_activities[1], from_aggregated]
        correct_to_add = [self.aggregated_activities[0], to_aggregated]
        self.assertEqual(to_remove, correct_to_remove)
        self.assertEqual(to_add, correct_to_add)

    @implementation
    def test_remove_aggregated_activity(self):
        # start by adding one
        self.test_feed.insert_activities(self.aggregated.activities)
        self.test_feed.add_many_aggregated([self.aggregated])
        assert len(self.test_feed[:10]) == 1
        # now remove it
        self.test_feed.remove_many_aggregated([self.aggregated])
        assert len(self.test_feed[:10]) == 0

    @implementation
    def test_add_activity(self):
        '''
        Test the aggregated feed by comparing the aggregator class
        to the output of the feed
        '''
        # test by sticking the items in the feed
        for activity in self.activities:
            self.test_feed.insert_activity(activity)
            self.test_feed.add(activity)
        results = self.test_feed[:3]
        # compare it to a direct call on the aggregator
        aggregator = self.test_feed.get_aggregator()
        aggregated_activities = aggregator.aggregate(self.activities)
        # check the feed
        assert results[0].actor_ids == aggregated_activities[0].actor_ids

    @implementation
    def test_contains(self):
        # test by sticking the items in the feed
        few_activities = self.activities[:10]
        self.test_feed.insert_activities(few_activities)
        self.test_feed.add_many(few_activities)

        for activity in few_activities:
            contains = self.test_feed.contains(activity)
            self.assertTrue(contains)

    @implementation
    def test_remove_activity(self):
        assert len(self.test_feed[:10]) == 0
        # test by sticking the items in the feed
        activity = self.activities[0]
        self.test_feed.insert_activity(activity)
        self.test_feed.add(activity)
        assert len(self.test_feed[:10]) == 1
        assert len(self.test_feed[:10][0].activities) == 1
        # now remove the activity
        self.test_feed.remove(activity)
        assert len(self.test_feed[:10]) == 0

    @implementation
    def test_partially_remove_activity(self):
        assert len(self.test_feed[:10]) == 0
        # test by sticking the items in the feed
        activities = self.activities[:2]
        for activity in activities:
            self.test_feed.insert_activity(activity)
            self.test_feed.add(activity)
        assert len(self.test_feed[:10]) == 1
        assert len(self.test_feed[:10][0].activities) == 2
        # now remove the activity
        self.test_feed.remove(activity)
        assert len(self.test_feed[:10]) == 1
        assert len(self.test_feed[:10][0].activities) == 1

    @implementation
    def test_large_remove_activity(self):
        # first built a large feed
        self.test_feed.max_length = 3600
        activities = []
        choices = [LoveVerb, AddVerb]
        for i in range(1, 3600):
            verb = choices[i % 2]
            activity = self.activity_class(
                i, verb, i, i, datetime.datetime.now() - datetime.timedelta(days=i))
            activities.append(activity)
        self.test_feed.insert_activities(activities)
        self.test_feed.add_many(activities)

        to_remove = activities[200:700]
        self.test_feed.remove_many(to_remove)

    @implementation
    def test_add_many_and_trim(self):
        activities = []
        choices = [LoveVerb, AddVerb]
        for i in range(1, 50):
            verb = choices[i % 2]
            activity = self.activity_class(
                i, verb, i, i, datetime.datetime.now() - datetime.timedelta(seconds=i))
            activities.append(activity)

        self.test_feed.insert_activities(activities)
        for activity in activities:
            self.test_feed.add_many([activity])

        self.test_feed[1:3]
        # now test the trim
        self.assertEqual(self.test_feed.count(), 2)
        self.test_feed.trim(1)
        self.assertEqual(self.test_feed.count(), 1)

########NEW FILE########
__FILENAME__ = cassandra
from feedly.activity import AggregatedActivity
from feedly.feeds.aggregated_feed.cassandra import CassandraAggregatedFeed
from feedly.tests.feeds.aggregated_feed.base import TestAggregatedFeed,\
    implementation
from feedly.tests.feeds.cassandra import CustomActivity
import pytest


class CustomAggregated(AggregatedActivity):
    pass


class CassandraCustomAggregatedFeed(CassandraAggregatedFeed):
    activity_class = CustomActivity
    aggregated_activity_class = CustomAggregated


@pytest.mark.usefixtures("cassandra_reset")
class TestCassandraAggregatedFeed(TestAggregatedFeed):
    feed_cls = CassandraAggregatedFeed


@pytest.mark.usefixtures("cassandra_reset")
class TestCassandraCustomAggregatedFeed(TestAggregatedFeed):
    feed_cls = CassandraCustomAggregatedFeed
    activity_class = CustomActivity
    aggregated_activity_class = CustomAggregated

    @implementation
    def test_custom_activity(self):
        assert self.test_feed.count() == 0
        self.feed_cls.insert_activity(
            self.activity
        )
        self.test_feed.add(self.activity)
        assert self.test_feed.count() == 1
        aggregated = self.test_feed[:10][0]
        assert type(aggregated) == self.aggregated_activity_class
        assert type(aggregated.activities[0]) == self.activity_class

########NEW FILE########
__FILENAME__ = notification_feed
from feedly.tests.feeds.aggregated_feed.base import TestAggregatedFeed
from feedly.feeds.aggregated_feed.notification_feed import RedisNotificationFeed
import time


class TestNotificationFeed(TestAggregatedFeed):
    feed_cls = RedisNotificationFeed

    def test_mark_all(self):
        # start by adding one
        self.test_feed.insert_activities(self.aggregated.activities)
        self.test_feed.add_many_aggregated([self.aggregated])
        assert len(self.test_feed[:10]) == 1
        assert int(self.test_feed.count_unseen()) == 1
        # TODO: don't know why this is broken
        # assert int(self.test_feed.get_denormalized_count()) == 1
        self.test_feed.mark_all()
        assert int(self.test_feed.count_unseen()) == 0
        assert int(self.test_feed.get_denormalized_count()) == 0

########NEW FILE########
__FILENAME__ = redis
from feedly.feeds.aggregated_feed.redis import RedisAggregatedFeed
from feedly.tests.feeds.aggregated_feed.base import TestAggregatedFeed,\
    implementation
from feedly.activity import AggregatedActivity
from feedly.tests.feeds.redis import CustomActivity


class CustomAggregated(AggregatedActivity):
    pass


class RedisCustomAggregatedFeed(RedisAggregatedFeed):
    activity_class = CustomActivity
    aggregated_activity_class = CustomAggregated


class TestRedisAggregatedFeed(TestAggregatedFeed):
    feed_cls = RedisAggregatedFeed


class TestRedisCustomAggregatedFeed(TestAggregatedFeed):
    feed_cls = RedisCustomAggregatedFeed
    activity_class = CustomActivity
    aggregated_activity_class = CustomAggregated

    @implementation
    def test_custom_activity(self):
        assert self.test_feed.count() == 0
        self.feed_cls.insert_activity(
            self.activity
        )
        self.test_feed.add(self.activity)
        assert self.test_feed.count() == 1
        aggregated = self.test_feed[:10][0]
        assert type(aggregated) == self.aggregated_activity_class
        assert type(aggregated.activities[0]) == self.activity_class

########NEW FILE########
__FILENAME__ = base
from contextlib import nested
import datetime
from feedly.feeds.base import BaseFeed
from feedly.tests.utils import FakeActivity
from feedly.tests.utils import Pin
from feedly.verbs.base import Love as LoveVerb
from mock import patch
import unittest
import time
from feedly.activity import Activity


def implementation(meth):
    def wrapped_test(self, *args, **kwargs):
        if self.feed_cls == BaseFeed:
            raise unittest.SkipTest('only test this on actual implementations')
        return meth(self, *args, **kwargs)
    return wrapped_test


class TestBaseFeed(unittest.TestCase):
    feed_cls = BaseFeed
    activity_class = FakeActivity

    def setUp(self):
        self.user_id = 42
        self.test_feed = self.feed_cls(self.user_id)
        self.pin = Pin(
            id=1, created_at=datetime.datetime.now() - datetime.timedelta(hours=1))
        self.activity = self.activity_class(
            1, LoveVerb, self.pin, 1, datetime.datetime.now(), {})
        activities = []
        for x in range(10):
            activity_time = datetime.datetime.now() + datetime.timedelta(
                hours=1)
            activity = self.activity_class(
                x, LoveVerb, self.pin, x, activity_time, dict(x=x))
            activities.append(activity)
        self.activities = activities

    def tearDown(self):
        if self.feed_cls != BaseFeed:
            self.test_feed.activity_storage.flush()
            self.test_feed.delete()

    def test_format_key(self):
        assert self.test_feed.key == 'feed_42'

    def test_delegate_add_many_to_storage(self):
        with nested(
                patch.object(self.test_feed.timeline_storage, 'add_many'),
                patch.object(self.test_feed.timeline_storage, 'trim')
        ) as (add_many, trim):
            self.test_feed.add(self.activity)
            add_many.assertCalled()
            trim.assertCalled()

    def test_delegate_count_to_storage(self):
        with patch.object(self.test_feed.timeline_storage, 'count') as count:
            self.test_feed.count()
            count.assertCalled()
            count.assert_called_with(self.test_feed.key)

    def test_delegate_delete_to_storage(self):
        with patch.object(self.test_feed.timeline_storage, 'delete') as delete:
            self.test_feed.delete()
            delete.assertCalled()
            delete.assert_called_with(self.test_feed.key)

    def test_delegate_remove_many_to_storage(self):
        with patch.object(self.test_feed.timeline_storage, 'remove_many') as remove_many:
            self.test_feed.remove(self.activity.serialization_id)
            remove_many.assertCalled()

    def test_delegate_add_to_add_many(self):
        with patch.object(self.test_feed, 'add_many') as add_many:
            self.test_feed.add(self.activity.serialization_id)
            add_many.assertCalled()

    def test_delegate_remove_to_remove_many(self):
        with patch.object(self.test_feed, 'remove_many') as remove_many:
            self.test_feed.remove(self.activity.serialization_id)
            remove_many.assertCalled()

    def test_slicing_left(self):
        with patch.object(self.test_feed, 'get_activity_slice') as get_activity_slice:
            self.test_feed[5:]
            get_activity_slice.assert_called_with(5, None)

    def test_slicing_between(self):
        with patch.object(self.test_feed, 'get_activity_slice') as get_activity_slice:
            self.test_feed[5:10]
            get_activity_slice.assert_called_with(5, 10)

    def test_slicing_right(self):
        with patch.object(self.test_feed, 'get_activity_slice') as get_activity_slice:
            self.test_feed[:5]
            get_activity_slice.assert_called_with(0, 5)

    def test_get_index(self):
        with patch.object(self.test_feed, 'get_activity_slice') as get_activity_slice:
            self.test_feed[5]
            get_activity_slice.assert_called_with(5, 6)

    @implementation
    def test_add_insert_activity(self):
        self.feed_cls.insert_activity(self.activity)
        activity = self.test_feed.activity_storage.get(
            self.activity.serialization_id
        )
        assert self.activity == activity

    @implementation
    def test_remove_missing_activity(self):
        self.feed_cls.remove_activity(self.activity)

    @implementation
    def test_add_remove_activity(self):
        self.feed_cls.insert_activity(
            self.activity
        )
        self.feed_cls.remove_activity(
            self.activity
        )
        activity = self.test_feed.activity_storage.get(
            self.activity.serialization_id,
        )
        assert activity is None

    @implementation
    def test_add_remove_activity_by_id(self):
        self.feed_cls.insert_activity(
            self.activity
        )
        self.feed_cls.remove_activity(
            self.activity.serialization_id
        )
        activity = self.test_feed.activity_storage.get(
            self.activity.serialization_id,
        )
        assert activity is None

    @implementation
    def test_check_violation_unsliced_iter_feed(self):
        with self.assertRaises(TypeError):
            [i for i in self.test_feed]

    @implementation
    def test_delete(self):
        # flush is not implemented by all backends
        assert self.test_feed.count() == 0
        self.feed_cls.insert_activity(
            self.activity
        )
        self.test_feed.add(self.activity)
        assert self.test_feed.count() == 1
        assert [self.activity] == self.test_feed[0]
        self.test_feed.delete()
        assert self.test_feed.count() == 0

    @implementation
    def test_add_to_timeline(self):
        assert self.test_feed.count() == 0
        self.feed_cls.insert_activity(
            self.activity
        )
        self.test_feed.add(self.activity)
        assert [self.activity] == self.test_feed[0]
        assert self.test_feed.count() == 1

    @implementation
    def test_add_many_to_timeline(self):
        assert self.test_feed.count() == 0
        self.feed_cls.insert_activity(
            self.activity
        )
        self.test_feed.add_many([self.activity])
        assert self.test_feed.count() == 1
        assert [self.activity] == self.test_feed[0]

    @implementation
    def test_add_many_and_trim(self):
        activities = []
        for i in range(50):
            activity = self.activity_class(
                i, LoveVerb, i, i, datetime.datetime.now(), {})
            activities.append(activity)
            self.test_feed.add_many([activity])

        self.test_feed.insert_activities(activities)
        self.assertEqual(self.test_feed.count(), 50)
        self.test_feed.trim(10)
        self.assertEqual(self.test_feed.count(), 10)

    def _check_order(self, activities):
        serialization_id = [a.serialization_id for a in activities]
        assert serialization_id == sorted(serialization_id, reverse=True)
        assert activities == sorted(
            activities, key=lambda a: a.time, reverse=True)

    @implementation
    def test_feed_timestamp_order(self):
        activities = []
        deltas = [1, 2, 9, 8, 11, 10, 5, 16, 14, 50]
        for i in range(10):
            activity = self.activity_class(
                i, LoveVerb, i, i, time=datetime.datetime.now() - datetime.timedelta(seconds=deltas.pop()))
            activities.append(activity)
            self.feed_cls.insert_activity(
                activity
            )
        self.test_feed.add_many(activities)
        self._check_order(self.test_feed[:10])
        self._check_order(self.test_feed[1:9])
        self._check_order(self.test_feed[5:])

    @implementation
    def test_feed_indexof_large(self):
        assert self.test_feed.count() == 0
        activity_dict = {}
        for i in range(150):
            moment = datetime.datetime.now() - datetime.timedelta(seconds=i)
            activity = self.activity_class(i, LoveVerb, i, i, time=moment)
            activity_dict[i] = activity
        self.test_feed.insert_activities(activity_dict.values())
        self.test_feed.add_many(activity_dict.values())

        # give cassandra a moment
        time.sleep(0.1)

        activity = activity_dict[110]
        index_of = self.test_feed.index_of(activity.serialization_id)
        self.assertEqual(index_of, 110)

    @implementation
    def test_feed_slice(self):
        activity_dict = {}
        for i in range(10):
            activity = self.activity_class(
                i, LoveVerb, i, i, time=datetime.datetime.now() - datetime.timedelta(seconds=i))
            activity_dict[i] = activity
        self.test_feed.insert_activities(activity_dict.values())
        self.test_feed.add_many(activity_dict.values())

        results = self.test_feed[:]
        self.assertEqual(len(results), self.test_feed.count())

    def setup_filter(self):
        if not self.test_feed.filtering_supported:
            self.skipTest('%s does not support filtering' %
                          self.test_feed.__class__.__name__)
        activities = []
        for i in range(10):
            activities.append(self.activity_class(
                i, LoveVerb, i, i, time=datetime.datetime.now() - datetime.timedelta(seconds=i))
            )
        self.test_feed.insert_activities(activities)
        self.test_feed.add_many(activities)
        assert len(self.test_feed[:]) == 10

    @implementation
    def test_feed_filter_copy(self):
        '''
        The feed should get deepcopied, so this method of filtering shouldnt
        work
        '''
        self.setup_filter()
        original_count = len(self.test_feed[:])
        offset = self.test_feed[3:][0].serialization_id
        self.test_feed.filter(activity_id__lte=offset)
        self.assertEquals(len(self.test_feed[:]), original_count)

    @implementation
    def test_feed_filter_lte_count(self):
        self.setup_filter()
        original_count = len(self.test_feed[:])
        offset = self.test_feed[3:][0].serialization_id
        feed = self.test_feed.filter(activity_id__lte=offset)
        new_count = len(feed[:])
        self.assertEquals((original_count - 3), new_count)

    @implementation
    def test_feed_filter_lte(self):
        self.setup_filter()
        offset = self.test_feed[3:][0].serialization_id
        feed = self.test_feed.filter(activity_id__lte=offset)
        filtered_results = feed[:]
        self.assertEquals(filtered_results, self.test_feed[3:])

    @implementation
    def test_feed_filter_gte_count(self):
        self.setup_filter()
        offset = self.test_feed[3:][0].serialization_id
        feed = self.test_feed.filter(activity_id__gte=offset)
        new_count = len(feed[:])
        self.assertEquals(4, new_count)

    @implementation
    def test_feed_filter_gte(self):
        self.setup_filter()
        offset = self.test_feed[3:][0].serialization_id
        feed = self.test_feed.filter(activity_id__gte=offset)
        filtered_results = feed[:]
        self.assertEquals(filtered_results, self.test_feed[:4])

    def setup_ordering(self):
        if not self.test_feed.ordering_supported:
            self.skipTest('%s does not support ordering' %
                          self.test_feed.__class__.__name__)
        activities = []
        for i in range(10):
            activities.append(self.activity_class(
                i, LoveVerb, i, i, time=datetime.datetime.now() - datetime.timedelta(seconds=i))
            )
        self.test_feed.insert_activities(activities)
        self.test_feed.add_many(activities)
        assert len(self.test_feed[:]) == 10

    @implementation
    def test_feed_ordering(self):
        self.setup_ordering()
        feed_asc = self.test_feed.order_by('activity_id')
        feed_desc = self.test_feed.order_by('-activity_id')
        asc_ids = [a.serialization_id for a in feed_asc[:100]]
        desc_ids = [a.serialization_id for a in feed_desc[:100]]
        self.assertNotEquals(asc_ids, desc_ids)
        self.assertNotEquals(asc_ids, reversed(desc_ids))

    @implementation
    def test_feed_pagination(self):
        '''
        assuming that we know element N and we want to get element N-M
        we should be able to get to element N-M without reading N-M elements
        but by changing sorting and reading M elements
        '''
        self.setup_ordering()
        page2 = self.test_feed[4:6]
        page3 = self.test_feed[7:9]
        page2_first_element = self.test_feed.filter(
            activity_id__gt=page3[0].serialization_id).order_by('activity_id')[:3][-1]
        self.assertEquals(page2[0], page2_first_element)

########NEW FILE########
__FILENAME__ = cassandra
from feedly.tests.feeds.base import TestBaseFeed, implementation
import pytest
from feedly.feeds.cassandra import CassandraFeed
from feedly.utils import datetime_to_epoch
from feedly.activity import Activity


class CustomActivity(Activity):

    @property
    def serialization_id(self):
        '''
        Shorter serialization id than used by default
        '''
        if self.object_id >= 10 ** 10 or self.verb.id >= 10 ** 3:
            raise TypeError('Fatal: object_id / verb have too many digits !')
        if not self.time:
            raise TypeError('Cant serialize activities without a time')
        milliseconds = str(int(datetime_to_epoch(self.time) * 1000))

        # shorter than the default version
        serialization_id_str = '%s%0.2d%0.2d' % (
            milliseconds, self.object_id % 100, self.verb.id)
        serialization_id = int(serialization_id_str)

        return serialization_id


class CassandraCustomFeed(CassandraFeed):
    activity_class = CustomActivity


@pytest.mark.usefixtures("cassandra_reset")
class TestCassandraBaseFeed(TestBaseFeed):
    feed_cls = CassandraFeed

    def test_add_insert_activity(self):
        pass

    def test_add_remove_activity(self):
        pass


@pytest.mark.usefixtures("cassandra_reset")
class TestCassandraCustomFeed(TestBaseFeed):
    feed_cls = CassandraCustomFeed
    activity_class = CustomActivity

    def test_add_insert_activity(self):
        pass

    def test_add_remove_activity(self):
        pass

    @implementation
    def test_custom_activity(self):
        assert self.test_feed.count() == 0
        self.feed_cls.insert_activity(
            self.activity
        )
        self.test_feed.add(self.activity)
        assert self.test_feed.count() == 1
        assert self.activity == self.test_feed[:10][0]
        assert type(self.activity) == type(self.test_feed[0][0])
        # make sure nothing is wrong with the activity storage

########NEW FILE########
__FILENAME__ = memory
from feedly.tests.feeds.base import TestBaseFeed
from feedly.feeds.memory import Feed


class InMemoryBaseFeed(TestBaseFeed):
    feed_cls = Feed

########NEW FILE########
__FILENAME__ = redis
from feedly.tests.feeds.base import TestBaseFeed, implementation
from feedly.feeds.redis import RedisFeed
from feedly.activity import Activity
from feedly.utils import datetime_to_epoch


class CustomActivity(Activity):

    @property
    def serialization_id(self):
        '''
        Shorter serialization id than used by default
        '''
        if self.object_id >= 10 ** 10 or self.verb.id >= 10 ** 3:
            raise TypeError('Fatal: object_id / verb have too many digits !')
        if not self.time:
            raise TypeError('Cant serialize activities without a time')
        milliseconds = str(int(datetime_to_epoch(self.time) * 1000))

        # shorter than the default version
        serialization_id_str = '%s%0.2d%0.2d' % (
            milliseconds, self.object_id % 100, self.verb.id)
        serialization_id = int(serialization_id_str)

        return serialization_id


class RedisCustom(RedisFeed):
    activity_class = CustomActivity


class TestRedisFeed(TestBaseFeed):
    feed_cls = RedisFeed


class TestCustomRedisFeed(TestBaseFeed):

    '''
    Test if the option to customize the activity class works without troubles
    '''
    feed_cls = RedisCustom
    activity_class = CustomActivity

    @implementation
    def test_custom_activity(self):
        assert self.test_feed.count() == 0
        self.feed_cls.insert_activity(
            self.activity
        )
        self.test_feed.add(self.activity)
        assert self.test_feed.count() == 1
        assert self.activity == self.test_feed[:10][0]
        assert type(self.activity) == type(self.test_feed[0][0])
        # make sure nothing is wrong with the activity storage

########NEW FILE########
__FILENAME__ = base
import datetime
from feedly.feed_managers.base import Feedly
from feedly.tests.utils import Pin
from feedly.tests.utils import FakeActivity
from feedly.verbs.base import Love as LoveVerb
from mock import patch
import unittest
import copy
from functools import partial


def implementation(meth):
    def wrapped_test(self, *args, **kwargs):
        if self.__class__ == BaseFeedlyTest:
            raise unittest.SkipTest('only test this on actual implementations')
        return meth(self, *args, **kwargs)
    return wrapped_test


class BaseFeedlyTest(unittest.TestCase):
    manager_class = Feedly

    def setUp(self):
        self.feedly = self.manager_class()
        self.actor_id = 42
        self.pin = Pin(
            id=1, created_at=datetime.datetime.now() - datetime.timedelta(hours=1))
        self.activity = FakeActivity(
            self.actor_id, LoveVerb, self.pin, 1, datetime.datetime.now(), {})

        if self.__class__ != BaseFeedlyTest:
            for user_id in range(1, 4) + [17, 42, 44]:
                self.feedly.get_user_feed(user_id).delete()
                for feed in self.feedly.get_feeds(user_id).values():
                    feed.delete()

    @implementation
    def test_add_user_activity(self):
        assert self.feedly.get_user_feed(
            self.actor_id).count() == 0, 'the test feed is not empty'

        with patch.object(self.feedly, 'get_user_follower_ids', return_value={None: [1]}) as get_user_follower_ids:
            self.feedly.add_user_activity(self.actor_id, self.activity)
            get_user_follower_ids.assert_called_with(user_id=self.actor_id)

        assert self.feedly.get_user_feed(self.actor_id).count() == 1
        for feed in self.feedly.get_feeds(1).values():
            assert feed.count() == 1

    @implementation
    def test_batch_import(self):
        assert self.feedly.get_user_feed(
            self.actor_id).count() == 0, 'the test feed is not empty'

        with patch.object(self.feedly, 'get_user_follower_ids', return_value={None: [1]}) as get_user_follower_ids:
            activities = [self.activity]
            self.feedly.batch_import(self.actor_id, activities, 10)
            get_user_follower_ids.assert_called_with(user_id=self.actor_id)

        assert self.feedly.get_user_feed(self.actor_id).count() == 1
        for feed in self.feedly.get_feeds(1).values():
            assert feed.count() == 1

    @implementation
    def test_batch_import_errors(self):
        activities = []
        # this should return without trouble
        self.feedly.batch_import(self.actor_id, activities, 10)

        # batch import with activities from different users should give an
        # error
        activity = copy.deepcopy(self.activity)
        activity.actor_id = 10
        with patch.object(self.feedly, 'get_user_follower_ids', return_value={None: [1]}):
            batch = partial(
                self.feedly.batch_import, self.actor_id, [activity], 10)
            self.assertRaises(ValueError, batch)

    @implementation
    def test_add_remove_user_activity(self):
        user_id = 42
        assert self.feedly.get_user_feed(
            user_id).count() == 0, 'the test feed is not empty'

        with patch.object(self.feedly, 'get_user_follower_ids', return_value={None: [1]}) as get_user_follower_ids:
            self.feedly.add_user_activity(user_id, self.activity)
            get_user_follower_ids.assert_called_with(user_id=user_id)
        assert self.feedly.get_user_feed(user_id).count() == 1

        with patch.object(self.feedly, 'get_user_follower_ids', return_value={None: [1]}) as get_user_follower_ids:
            self.feedly.remove_user_activity(user_id, self.activity)
            get_user_follower_ids.assert_called_with(user_id=user_id)
        assert self.feedly.get_user_feed(user_id).count() == 0

    @implementation
    def test_add_user_activity_fanout(self):
        user_id = 42
        followers = {None: [1, 2, 3]}
        assert self.feedly.get_user_feed(
            user_id).count() == 0, 'the test feed is not empty'

        for follower in followers.values():
            assert self.feedly.get_user_feed(follower).count() == 0

        with patch.object(self.feedly, 'get_user_follower_ids', return_value=followers) as get_user_follower_ids:
            self.feedly.add_user_activity(user_id, self.activity)
            get_user_follower_ids.assert_called_with(user_id=user_id)

        assert self.feedly.get_user_feed(user_id).count() == 1

        for follower in followers.values()[0]:
            assert self.feedly.get_user_feed(follower).count() == 0
            for f in self.feedly.get_feeds(follower).values():
                assert f.count() == 1

    @implementation
    def test_follow_unfollow_user(self):
        target_user_id = 17
        target2_user_id = 44
        follower_user_id = 42

        control_pin = Pin(
            id=2, created_at=datetime.datetime.now() - datetime.timedelta(hours=1))
        control_activity = FakeActivity(
            target_user_id, LoveVerb, control_pin, 2, datetime.datetime.now(), {})

        with patch.object(self.feedly, 'get_user_follower_ids', return_value={}) as get_user_follower_ids:
            self.feedly.add_user_activity(target2_user_id, control_activity)
            self.feedly.add_user_activity(target_user_id, self.activity)
            get_user_follower_ids.assert_called_with(user_id=target_user_id)

        # checks user feed is empty
        for f in self.feedly.get_feeds(follower_user_id).values():
            self.assertEqual(f.count(), 0)

        self.feedly.follow_user(follower_user_id, target2_user_id)

        # make sure one activity was pushed
        for f in self.feedly.get_feeds(follower_user_id).values():
            self.assertEqual(f.count(), 1)

        self.feedly.follow_user(follower_user_id, target_user_id)

        # make sure another one activity was pushed
        for f in self.feedly.get_feeds(follower_user_id).values():
            self.assertEqual(f.count(), 2)

        self.feedly.unfollow_user(
            follower_user_id, target_user_id, async=False)

        # make sure only one activity was removed
        for f in self.feedly.get_feeds(follower_user_id).values():
            self.assertEqual(f.count(), 1)
            activity = f[:][0]
            assert activity.object_id == self.pin.id

########NEW FILE########
__FILENAME__ = cassandra
from feedly.feed_managers.base import Feedly
from feedly.feeds.base import UserBaseFeed
from feedly.feeds.cassandra import CassandraFeed
from feedly.tests.managers.base import BaseFeedlyTest
import pytest


class CassandraUserBaseFeed(UserBaseFeed, CassandraFeed):
    pass


class CassandraFeedly(Feedly):
    feed_classes = {
        'feed': CassandraFeed
    }
    user_feed_class = CassandraUserBaseFeed


@pytest.mark.usefixtures("cassandra_reset")
class RedisFeedlyTest(BaseFeedlyTest):
    manager_class = CassandraFeedly

########NEW FILE########
__FILENAME__ = redis
from feedly.feed_managers.base import Feedly
from feedly.feeds.base import UserBaseFeed
from feedly.feeds.redis import RedisFeed
from feedly.tests.managers.base import BaseFeedlyTest
import pytest


class RedisUserBaseFeed(UserBaseFeed, RedisFeed):
    pass


class RedisFeedly(Feedly):
    feed_classes = {
        'feed': RedisFeed
    }
    user_feed_class = RedisUserBaseFeed


@pytest.mark.usefixtures("redis_reset")
class RedisFeedlyTest(BaseFeedlyTest):
    manager_class = RedisFeedly

########NEW FILE########
__FILENAME__ = serializers
from feedly.aggregators.base import RecentVerbAggregator
from feedly.serializers.activity_serializer import ActivitySerializer
from feedly.serializers.aggregated_activity_serializer import \
    AggregatedActivitySerializer, NotificationSerializer
from feedly.serializers.base import BaseSerializer
from feedly.serializers.cassandra.activity_serializer import CassandraActivitySerializer
from feedly.serializers.pickle_serializer import PickleSerializer, \
    AggregatedActivityPickleSerializer
from feedly.storage.cassandra import models
from feedly.tests.utils import FakeActivity
from functools import partial
import datetime
import unittest
from feedly.activity import Activity, AggregatedActivity


class ActivitySerializationTest(unittest.TestCase):
    serialization_class = BaseSerializer
    serialization_class_kwargs = {
        'activity_class': Activity, 'aggregated_activity_class': AggregatedActivity}
    activity_extra_context = {'xxx': 'yyy'}

    def setUp(self):
        from feedly.verbs.base import Love as LoveVerb
        self.serializer = self.serialization_class(
            **self.serialization_class_kwargs)
        self.activity = FakeActivity(
            1, LoveVerb, 1, 1, datetime.datetime.now(), {})
        self.activity.extra_context = self.activity_extra_context
        aggregator = RecentVerbAggregator()
        self.aggregated_activity = aggregator.aggregate([self.activity])[0]
        self.args = ()
        self.kwargs = {}

    def test_serialization(self):
        serialized_activity = self.serializer.dumps(self.activity)
        deserialized_activity = self.serializer.loads(serialized_activity)
        self.assertEqual(deserialized_activity, self.activity)
        self.assertEqual(
            deserialized_activity.extra_context, self.activity_extra_context)

    def test_type_exception(self):
        give_error = partial(self.serializer.dumps, 1)
        self.assertRaises(ValueError, give_error)
        give_error = partial(self.serializer.dumps, self.aggregated_activity)
        self.assertRaises(ValueError, give_error)


class PickleSerializationTestCase(ActivitySerializationTest):
    serialization_class = PickleSerializer


class ActivitySerializerTest(ActivitySerializationTest):
    serialization_class = ActivitySerializer


class AggregatedActivitySerializationTest(ActivitySerializationTest):
    serialization_class = AggregatedActivitySerializer

    def test_serialization(self):
        serialized = self.serializer.dumps(self.aggregated_activity)
        deserialized = self.serializer.loads(serialized)
        self.assertEqual(deserialized, self.aggregated_activity)

    def test_type_exception(self):
        give_error = partial(self.serializer.dumps, 1)
        self.assertRaises(ValueError, give_error)
        give_error = partial(self.serializer.dumps, self.activity)
        self.assertRaises(ValueError, give_error)

    def test_hydration(self):
        serialized_activity = self.serializer.dumps(self.aggregated_activity)
        deserialized_activity = self.serializer.loads(serialized_activity)
        assert self.serialization_class.dehydrate == deserialized_activity.dehydrated
        if deserialized_activity.dehydrated:
            assert not deserialized_activity.activities
            assert deserialized_activity._activity_ids


class PickleAggregatedActivityTest(AggregatedActivitySerializationTest):
    serialization_class = AggregatedActivityPickleSerializer


class NotificationSerializerTest(AggregatedActivitySerializationTest):
    serialization_class = NotificationSerializer


class CassandraActivitySerializerTest(ActivitySerializationTest):
    serialization_class = CassandraActivitySerializer
    serialization_class_kwargs = {
        'model': models.Activity, 'activity_class': Activity, 'aggregated_activity_class': AggregatedActivity}

########NEW FILE########
__FILENAME__ = settings
import os

FEEDLY_DEFAULT_KEYSPACE = 'test_feedly'

if os.environ.get('TEST_CASSANDRA_HOST'):
    FEEDLY_CASSANDRA_HOSTS = [os.environ['TEST_CASSANDRA_HOST']]

SECRET_KEY = 'ib_^kc#v536)v$x!h3*#xs6&l8&7#4cqi^rjhczu85l9txbz+w'
FEEDLY_DISCOVER_CASSANDRA_NODES = False
FEEDLY_CASSANDRA_CONSITENCY_LEVEL = 'ONE'


FEEDLY_REDIS_CONFIG = {
    'default': {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 0,
        'password': None
    },
}

########NEW FILE########
__FILENAME__ = base
from feedly.storage.base import BaseActivityStorage, BaseTimelineStorage
from feedly.tests.utils import FakeActivity
from feedly.tests.utils import Pin
from feedly.verbs.base import Love as PinVerb
from mock import patch
import datetime
import unittest
from feedly.activity import Activity


def implementation(meth):
    def wrapped_test(self, *args, **kwargs):
        if self.storage.__class__ in (BaseActivityStorage, BaseTimelineStorage):
            raise unittest.SkipTest('only test this on actual implementations')
        return meth(self, *args, **kwargs)
    return wrapped_test


def compare_lists(a, b, msg):
    a_stringified = map(str, a)
    b_stringified = map(str, b)
    assert a_stringified == b_stringified, msg


class TestBaseActivityStorageStorage(unittest.TestCase):

    '''

    Makes sure base wirings are not broken, you should
    implement this test class for every BaseActivityStorage subclass
    to make sure APIs is respected

    '''

    storage_cls = BaseActivityStorage
    storage_options = {'activity_class': Activity}

    def setUp(self):
        self.pin = Pin(
            id=1, created_at=datetime.datetime.now() - datetime.timedelta(hours=1))
        self.storage = self.storage_cls(**self.storage_options)
        self.activity = FakeActivity(
            1, PinVerb, self.pin, 1, datetime.datetime.now(), {})
        self.args = ()
        self.kwargs = {}

    def tearDown(self):
        self.storage.flush()

    def test_add_to_storage(self):
        with patch.object(self.storage, 'add_to_storage') as add_to_storage:
            self.storage.add(self.activity, *self.args, **self.kwargs)
            add_to_storage.assert_called()

    def test_remove_from_storage(self):
        with patch.object(self.storage, 'remove_from_storage') as remove_from_storage:
            self.storage.remove(self.activity)
            remove_from_storage.assert_called()
            remove_from_storage.assert_called_with(
                [self.activity.serialization_id], *self.args, **self.kwargs)

    def test_get_from_storage(self):
        with patch.object(self.storage, 'get_from_storage') as get_from_storage:
            self.storage.get(self.activity)
            get_from_storage.assert_called()
            get_from_storage.assert_called_with(
                [self.activity], *self.args, **self.kwargs)

    @implementation
    def test_add(self):
        add_count = self.storage.add(
            self.activity, *self.args, **self.kwargs)
        self.assertEqual(add_count, 1)

    @implementation
    def test_add_get(self):
        self.storage.add(self.activity, *self.args, **self.kwargs)
        result = self.storage.get(
            self.activity.serialization_id, *self.args, **self.kwargs)
        assert result == self.activity

    @implementation
    def test_add_twice(self):
        self.storage.add(
            self.activity, *self.args, **self.kwargs)
        # this shouldnt raise errors
        self.storage.add(
            self.activity, *self.args, **self.kwargs)

    @implementation
    def test_get_missing(self):
        result = self.storage.get(
            self.activity.serialization_id, *self.args, **self.kwargs)
        assert result is None

    @implementation
    def test_remove(self):
        self.storage.remove(self.activity, *self.args, **self.kwargs)

    @implementation
    def test_add_remove(self):
        self.storage.add(self.activity, *self.args, **self.kwargs)
        result = self.storage.get(
            self.activity.serialization_id, *self.args, **self.kwargs)
        assert result == self.activity
        self.storage.remove(
            self.activity, *self.args, **self.kwargs)
        result = self.storage.get(
            self.activity.serialization_id, *self.args, **self.kwargs)
        assert result is None


class TestBaseTimelineStorageClass(unittest.TestCase):

    storage_cls = BaseTimelineStorage
    storage_options = {'activity_class': Activity}

    def setUp(self):
        self.storage = self.storage_cls(**self.storage_options)
        self.test_key = 'key'
        if self.__class__ != TestBaseTimelineStorageClass:
            self.storage.delete(self.test_key)
        self.storage.flush()

    def tearDown(self):
        if self.__class__ != TestBaseTimelineStorageClass:
            self.storage.delete(self.test_key)
        self.storage.flush()

    def _build_activity_list(self, ids_list):
        now = datetime.datetime.now()
        pins = [Pin(id=i, created_at=now + datetime.timedelta(hours=i))
                for i in ids_list]
        pins_ids = zip(pins, ids_list)
        return [FakeActivity(i, PinVerb, pin, i, now + datetime.timedelta(hours=i), {'i': i}) for id, pin in pins_ids]

    def assert_results(self, results, activities, msg=''):
        activity_ids = []
        extra_context = []
        for result in results:
            if hasattr(result, 'serialization_id'):
                activity_ids.append(result.serialization_id)
            else:
                activity_ids.append(result)
            if hasattr(result, 'extra_context'):
                extra_context.append(result.extra_context)
        compare_lists(
            activity_ids, [a.serialization_id for a in activities], msg)

        if extra_context:
            self.assertEquals(
                [a.extra_context for a in activities], extra_context)

    @implementation
    def test_count_empty(self):
        assert self.storage.count(self.test_key) == 0

    @implementation
    def test_count_insert(self):
        assert self.storage.count(self.test_key) == 0
        activity = self._build_activity_list([1])[0]
        self.storage.add(self.test_key, activity)
        assert self.storage.count(self.test_key) == 1

    @implementation
    def test_add_many(self):
        results = self.storage.get_slice(self.test_key, 0, None)
        # make sure no data polution
        assert results == []
        activities = self._build_activity_list(range(3, 0, -1))
        self.storage.add_many(self.test_key, activities)
        results = self.storage.get_slice(self.test_key, 0, None)
        self.assert_results(results, activities)

    @implementation
    def test_add_many_unique(self):
        activities = self._build_activity_list(
            range(3, 0, -1) + range(3, 0, -1))
        self.storage.add_many(self.test_key, activities)
        results = self.storage.get_slice(self.test_key, 0, None)
        self.assert_results(results, activities[:3])

    @implementation
    def test_contains(self):
        activities = self._build_activity_list(range(4, 0, -1))
        self.storage.add_many(self.test_key, activities[:3])
        results = self.storage.get_slice(self.test_key, 0, None)
        if self.storage.contains:
            self.assert_results(results, activities[:3])
            for a in activities[:3]:
                assert self.storage.contains(self.test_key, a.serialization_id)
            assert not self.storage.contains(
                self.test_key, activities[3].serialization_id)

    @implementation
    def test_index_of(self):
        activities = self._build_activity_list(range(1, 43))
        activity_ids = [a.serialization_id for a in activities]
        self.storage.add_many(self.test_key, activities)
        assert self.storage.index_of(self.test_key, activity_ids[41]) == 0
        assert self.storage.index_of(self.test_key, activity_ids[7]) == 34
        with self.assertRaises(ValueError):
            self.storage.index_of(self.test_key, 0)

    @implementation
    def test_trim(self):
        activities = self._build_activity_list(range(10, 0, -1))
        self.storage.add_many(self.test_key, activities[5:])
        self.storage.add_many(self.test_key, activities[:5])
        assert self.storage.count(self.test_key) == 10
        self.storage.trim(self.test_key, 5)
        assert self.storage.count(self.test_key) == 5
        results = self.storage.get_slice(self.test_key, 0, None)
        self.assert_results(
            results, activities[:5], 'check trim direction')

    @implementation
    def test_noop_trim(self):
        activities = self._build_activity_list(range(10, 0, -1))
        self.storage.add_many(self.test_key, activities)
        assert self.storage.count(self.test_key) == 10
        self.storage.trim(self.test_key, 12)
        assert self.storage.count(self.test_key) == 10

    @implementation
    def test_trim_empty_feed(self):
        self.storage.trim(self.test_key, 12)

    @implementation
    def test_remove_missing(self):
        activities = self._build_activity_list(range(10))
        self.storage.remove(self.test_key, activities[1])
        self.storage.remove_many(self.test_key, activities[1:2])

    @implementation
    def test_add_remove(self):
        assert self.storage.count(self.test_key) == 0
        activities = self._build_activity_list(range(10, 0, -1))
        self.storage.add_many(self.test_key, activities)
        self.storage.remove_many(self.test_key, activities[5:])
        results = self.storage.get_slice(self.test_key, 0, 20)
        assert self.storage.count(self.test_key) == 5
        self.assert_results(results, activities[:5])

    @implementation
    def test_get_many_empty(self):
        assert self.storage.get_slice(self.test_key, 0, 10) == []

    @implementation
    def test_timeline_order(self):
        activities = self._build_activity_list(range(10, 0, -1))
        self.storage.add_many(self.test_key, activities)
        self.storage.trim(self.test_key, 5)
        self.storage.add_many(self.test_key, activities)
        results = self.storage.get_slice(self.test_key, 0, 5)
        self.assert_results(results, activities[:5])

    @implementation
    def test_implements_batcher_as_ctx_manager(self):
        batcher = self.storage.get_batch_interface()
        hasattr(batcher, '__enter__')
        hasattr(batcher, '__exit__')

    @implementation
    def test_union_set_slice(self):
        activities = self._build_activity_list(range(42, 0, -1))
        self.storage.add_many(self.test_key, activities)
        assert self.storage.count(self.test_key) == 42
        s1 = self.storage.get_slice(self.test_key, 0, 21)
        self.assert_results(s1, activities[0:21])
        s2 = self.storage.get_slice(self.test_key, 22, 42)
        self.assert_results(s2, activities[22:42])
        s3 = self.storage.get_slice(self.test_key, 22, 23)
        self.assert_results(s3, activities[22:23])
        s4 = self.storage.get_slice(self.test_key, None, 23)
        self.assert_results(s4, activities[:23])
        s5 = self.storage.get_slice(self.test_key, None, None)
        self.assert_results(s5, activities[:])
        s6 = self.storage.get_slice(self.test_key, 1, None)
        self.assert_results(s6, activities[1:])
        # check intersections
        assert len(set(s1 + s2)) == len(s1) + len(s2)

########NEW FILE########
__FILENAME__ = cassandra
from feedly import settings
from feedly.storage.cassandra.timeline_storage import CassandraTimelineStorage
from feedly.tests.storage.base import TestBaseTimelineStorageClass
import pytest
from feedly.activity import Activity


@pytest.mark.usefixtures("cassandra_reset")
class TestCassandraTimelineStorage(TestBaseTimelineStorageClass):
    storage_cls = CassandraTimelineStorage
    storage_options = {
        'hosts': settings.FEEDLY_CASSANDRA_HOSTS,
        'column_family_name': 'example',
        'activity_class': Activity
    }

########NEW FILE########
__FILENAME__ = memory
from feedly.storage.memory import InMemoryTimelineStorage
from feedly.storage.memory import InMemoryActivityStorage
from feedly.tests.storage.base import TestBaseActivityStorageStorage
from feedly.tests.storage.base import TestBaseTimelineStorageClass


class InMemoryActivityStorage(TestBaseActivityStorageStorage):
    storage_cls = InMemoryActivityStorage


class TestInMemoryTimelineStorageClass(TestBaseTimelineStorageClass):
    storage_cls = InMemoryTimelineStorage

########NEW FILE########
__FILENAME__ = activity_storage
from feedly.tests.storage.base import TestBaseActivityStorageStorage
from feedly.storage.redis.activity_storage import RedisActivityStorage


class RedisActivityStorageTest(TestBaseActivityStorageStorage):
    storage_cls = RedisActivityStorage

########NEW FILE########
__FILENAME__ = structures
import unittest
from feedly.storage.redis.structures.hash import RedisHashCache,\
    ShardedHashCache, FallbackHashCache
from feedly.storage.redis.structures.list import RedisListCache,\
    FallbackRedisListCache
from feedly.storage.redis.connection import get_redis_connection
from functools import partial
from feedly.storage.redis.structures.sorted_set import RedisSortedSetCache


class BaseRedisStructureTestCase(unittest.TestCase):

    def get_structure(self):
        return


class RedisSortedSetTest(BaseRedisStructureTestCase):

    test_data = [(1.0, 'a'), (2.0, 'b'), (3.0, 'c')]

    def get_structure(self):
        structure_class = RedisSortedSetCache
        structure = structure_class('test')
        structure.delete()
        return structure

    def test_add_many(self):
        cache = self.get_structure()
        test_data = self.test_data
        for key, value in test_data:
            cache.add(key, value)
        # this shouldnt insert data, its a sorted set after all
        cache.add_many(test_data)
        count = cache.count()
        self.assertEqual(int(count), 3)

    def test_ordering(self):
        cache = self.get_structure()
        data = self.test_data

        test_data = data
        cache.add_many(test_data)
        results = cache[:]
        expected_results = [p[::-1] for p in test_data]
        self.assertEqual(results, expected_results[::-1])
        cache.sort_asc = True
        results = cache[:10]
        self.assertEqual(results, expected_results)

    def test_filtering(self):
        # setup the data
        cache = self.get_structure()
        cache.add_many(self.test_data)
        # try a max
        results = cache.get_results(0, 2, max_score=2.0)
        self.assertEqual(results, [('b', 2.0), ('a', 1.0)])
        # try a min
        results = cache.get_results(0, 2, min_score=2.0)
        self.assertEqual(results, [('c', 3.0), ('b', 2.0)])
        # try a max with a start
        results = cache.get_results(1, 2, max_score=2.0)
        self.assertEqual(results, [('a', 1.0)])

    def test_long_filtering(self):
        '''
        Check if nothing breaks when using long numbers as scores
        '''
        self.skipTest('This is a known issue with Redis')
        # setup the data
        test_data = [(13930920300000000000007001, 'a'), (
            13930920300000000000007002, 'b'), (13930920300000000000007003, 'c')]
        cache = self.get_structure()
        cache.add_many(test_data)
        # try a max
        results = cache.get_results(0, 2, max_score=13930920300000000000007002)
        self.assertEqual(results, [('b', float(13930920300000000000007002)), (
            'a', float(13930920300000000000007001))])
        # try a min
        results = cache.get_results(0, 2, min_score=13930920300000000000007002)
        self.assertEqual(results, [('c', float(13930920300000000000007003)), (
            'b', float(13930920300000000000007002))])
        # try a max with a start
        results = cache.get_results(1, 2, max_score=13930920300000000000007002)
        self.assertEqual(results, [('a', float(13930920300000000000007001))])

    def test_trim(self):
        cache = self.get_structure()
        test_data = self.test_data
        for score, value in test_data:
            cache.add(score, value)
        cache.trim(1)
        count = cache.count()
        self.assertEqual(count, 1)

    def test_simple_trim(self):
        cache = self.get_structure()
        test_data = self.test_data
        for key, value in test_data:
            cache.add(key, value)
        cache.max_length = 1
        cache.trim()
        count = int(cache.count())
        self.assertEqual(count, 1)

    def test_remove(self):
        cache = self.get_structure()
        test_data = self.test_data
        cache.add_many(test_data)
        cache.remove_many(['a'])
        count = cache.count()
        self.assertEqual(count, 2)

    def test_remove_by_score(self):
        cache = self.get_structure()
        test_data = self.test_data
        cache.add_many(test_data)
        cache.remove_by_scores([1.0, 2.0])
        count = cache.count()
        self.assertEqual(count, 1)

    def test_zremrangebyrank(self):
        redis = get_redis_connection()
        key = 'test'
        # start out fresh
        redis.delete(key)
        redis.zadd(key, 1, 'a')
        redis.zadd(key, 2, 'b')
        redis.zadd(key, 3, 'c')
        redis.zadd(key, 4, 'd')
        redis.zadd(key, 5, 'e')
        expected_results = [('a', 1.0), ('b', 2.0), ('c', 3.0), (
            'd', 4.0), ('e', 5.0)]
        results = redis.zrange(key, 0, -1, withscores=True)
        self.assertEqual(results, expected_results)
        results = redis.zrange(key, 0, -4, withscores=True)

        # now the idea is to only keep 3,4,5
        max_length = 3
        end = (max_length * -1) - 1
        redis.zremrangebyrank(key, 0, end)
        expected_results = [('c', 3.0), ('d', 4.0), ('e', 5.0)]
        results = redis.zrange(key, 0, -1, withscores=True)
        self.assertEqual(results, expected_results)


class ListCacheTestCase(BaseRedisStructureTestCase):

    def get_structure(self):
        structure_class = type(
            'MyCache', (RedisListCache, ), dict(max_items=10))
        structure = structure_class('test')
        structure.delete()
        return structure

    def test_append(self):
        cache = self.get_structure()
        cache.append_many(['a', 'b'])
        self.assertEqual(cache[:5], ['a', 'b'])
        self.assertEqual(cache.count(), 2)

    def test_simple_append(self):
        cache = self.get_structure()
        for value in ['a', 'b']:
            cache.append(value)
        self.assertEqual(cache[:5], ['a', 'b'])
        self.assertEqual(cache.count(), 2)

    def test_trim(self):
        cache = self.get_structure()
        cache.append_many(range(100))
        self.assertEqual(cache.count(), 100)
        cache.trim()
        self.assertEqual(cache.count(), 10)

    def test_remove(self):
        cache = self.get_structure()
        data = ['a', 'b']
        cache.append_many(data)
        self.assertEqual(cache[:5], data)
        self.assertEqual(cache.count(), 2)
        for value in data:
            cache.remove(value)
        self.assertEqual(cache[:5], [])
        self.assertEqual(cache.count(), 0)


class FakeFallBack(FallbackRedisListCache):
    max_items = 10

    def __init__(self, *args, **kwargs):
        self.fallback_data = kwargs.pop('fallback')
        FallbackRedisListCache.__init__(self, *args, **kwargs)

    def get_fallback_results(self, start, stop):
        return self.fallback_data[start:stop]


class FallbackRedisListCacheTest(ListCacheTestCase):

    def get_structure(self):
        structure = FakeFallBack('test', fallback=['a', 'b'])
        structure.delete()
        return structure

    def test_remove(self):
        cache = self.get_structure()
        data = ['a', 'b']
        cache.append_many(data)
        self.assertEqual(cache[:5], data)
        self.assertEqual(cache.count(), 2)
        for value in data:
            cache.remove(value)
        self.assertEqual(cache.count(), 0)
        # fallback should still work
        self.assertEqual(cache[:5], data)


class SecondFallbackRedisListCacheTest(BaseRedisStructureTestCase):

    def get_structure(self):
        structure = FakeFallBack('test', fallback=['a', 'b', 'c'])
        structure.delete()
        return structure

    def test_append(self):
        cache = self.get_structure()
        # test while we have no redis data
        self.assertEqual(cache[:5], ['a', 'b', 'c'])
        # now test with redis data
        cache.append_many(['d', 'e', 'f', 'g'])
        self.assertEqual(cache.count(), 7)
        self.assertEqual(cache[:3], ['a', 'b', 'c'])

    def test_slice(self):
        cache = self.get_structure()
        # test while we have no redis data
        self.assertEqual(cache[:], ['a', 'b', 'c'])


class HashCacheTestCase(BaseRedisStructureTestCase):

    def get_structure(self):
        structure = RedisHashCache('test')
        # always start fresh
        structure.delete()
        return structure

    def test_set_many(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        keys = cache.keys()
        self.assertEqual(keys, ['key', 'key2'])

    def test_set(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        for key, value in key_value_pairs:
            cache.set(key, value)
        keys = cache.keys()
        self.assertEqual(keys, ['key', 'key2'])

    def test_delete_many(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        keys = cache.keys()
        cache.delete_many(keys)
        keys = cache.keys()
        self.assertEqual(keys, [])

    def test_get_and_set(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        results = cache.get_many(['key', 'key2'])
        self.assertEqual(results, {'key2': 'value2', 'key': 'value'})

        result = cache.get('key')
        self.assertEqual(result, 'value')

        result = cache.get('key_missing')
        self.assertEqual(result, None)

    def test_contains(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        result = cache.contains('key')
        self.assertEqual(result, True)
        result = cache.contains('key2')
        self.assertEqual(result, True)
        result = cache.contains('key_missing')
        self.assertEqual(result, False)

    def test_count(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        count = cache.count()
        self.assertEqual(count, 2)


class MyFallbackHashCache(FallbackHashCache):

    def get_many_from_fallback(self, fields):
        return dict(zip(fields, range(100)))


class FallbackHashCacheTestCase(HashCacheTestCase):

    def get_structure(self):
        structure = MyFallbackHashCache('test')
        # always start fresh
        structure.delete()
        return structure

    def test_get_and_set(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        results = cache.get_many(['key', 'key2'])
        self.assertEqual(results, {'key2': 'value2', 'key': 'value'})

        result = cache.get('key')
        self.assertEqual(result, 'value')

        result = cache.get('key_missing')
        self.assertEqual(result, 0)


class ShardedHashCacheTestCase(HashCacheTestCase):

    def get_structure(self):
        structure = ShardedHashCache('test')
        # always start fresh
        structure.delete()
        return structure

    def test_set_many(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)

    def test_get_and_set(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        results = cache.get_many(['key', 'key2'])
        self.assertEqual(results, {'key2': 'value2', 'key': 'value'})

        result = cache.get('key')
        self.assertEqual(result, 'value')

        result = cache.get('key_missing')
        self.assertEqual(result, None)

    def test_count(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        count = cache.count()
        self.assertEqual(count, 2)

    def test_contains(self):
        cache = self.get_structure()
        key_value_pairs = [('key', 'value'), ('key2', 'value2')]
        cache.set_many(key_value_pairs)
        contains = partial(cache.contains, 'key')
        self.assertRaises(NotImplementedError, contains)

########NEW FILE########
__FILENAME__ = timeline_storage
from feedly.tests.storage.base import TestBaseTimelineStorageClass
from feedly.storage.redis.timeline_storage import RedisTimelineStorage


class TestRedisTimelineStorageClass(TestBaseTimelineStorageClass):
    storage_cls = RedisTimelineStorage

########NEW FILE########
__FILENAME__ = utils_test
import unittest
from feedly.utils import chunks, warn_on_duplicate, make_list_unique,\
    warn_on_error
from feedly.exceptions import DuplicateActivityException
from functools import partial
import mock


class ChunksTest(unittest.TestCase):

    def test_chunks(self):
        chunked = chunks(range(6), 2)
        chunked = list(chunked)
        self.assertEqual(chunked, [(0, 1), (2, 3), (4, 5)])

    def test_one_chunk(self):
        chunked = chunks(range(2), 5)
        chunked = list(chunked)
        self.assertEqual(chunked, [(0, 1)])


def safe_function():
    return 10


def evil_duplicate():
    raise DuplicateActivityException('test')


def evil_value():
    raise ValueError('test')


class WarnTest(unittest.TestCase):

    def test_warn(self):
        # this should raise an error
        self.assertRaises(ValueError, evil_value)
        with mock.patch('feedly.utils.logger.warn') as warn:
            # this shouldnt raise an error
            wrapped = warn_on_error(evil_value, (ValueError,))
            wrapped()
        # but stick something in the log
        assert warn.called

    def test_warn_on_duplicate(self):
        # this should raise an error
        self.assertRaises(DuplicateActivityException, evil_duplicate)
        # this shouldnt raise an error
        with mock.patch('feedly.utils.logger.warn') as warn:
            wrapped = warn_on_duplicate(evil_duplicate)
            wrapped()
        # but stick something in the log
        assert warn.called


class UniqueListTest(unittest.TestCase):

    def test_make_list_unique(self):
        with_doubles = range(10) + range(5, 15)
        result = make_list_unique(with_doubles)
        assert result == range(15)

    def test_make_list_unique_marker(self):
        with_doubles = range(10) + range(5, 15)
        marker = lambda x: x / 5
        result = make_list_unique(with_doubles, marker)
        assert result == [0, 5, 10]

########NEW FILE########
__FILENAME__ = functional
import copy
import operator
from functools import wraps
import sys
from feedly.utils import six


class Promise(object):

    """
    This is just a base class for the proxy class created in
    the closure of the lazy function. It can be used to recognize
    promises in code.
    """
    pass


def lazy(func, *resultclasses):
    """
    Turns any callable into a lazy evaluated callable. You need to give result
    classes or types -- at least one is needed so that the automatic forcing of
    the lazy evaluation code is triggered. Results are not memoized; the
    function is evaluated on every access.
    """

    @total_ordering
    class __proxy__(Promise):

        """
        Encapsulate a function call and act as a proxy for methods that are
        called on the result of that function. The function is not evaluated
        until one of the methods on the result is called.
        """
        __dispatch = None

        def __init__(self, args, kw):
            self.__args = args
            self.__kw = kw
            if self.__dispatch is None:
                self.__prepare_class__()

        def __reduce__(self):
            return (
                _lazy_proxy_unpickle,
                (func, self.__args, self.__kw) + resultclasses
            )

        @classmethod
        def __prepare_class__(cls):
            cls.__dispatch = {}
            for resultclass in resultclasses:
                cls.__dispatch[resultclass] = {}
                for type_ in reversed(resultclass.mro()):
                    for (k, v) in type_.__dict__.items():
                        # All __promise__ return the same wrapper method, but
                        # they also do setup, inserting the method into the
                        # dispatch dict.
                        meth = cls.__promise__(resultclass, k, v)
                        if hasattr(cls, k):
                            continue
                        setattr(cls, k, meth)
            cls._delegate_bytes = bytes in resultclasses
            cls._delegate_text = six.text_type in resultclasses
            assert not (
                cls._delegate_bytes and cls._delegate_text), "Cannot call lazy() with both bytes and text return types."
            if cls._delegate_text:
                if six.PY3:
                    cls.__str__ = cls.__text_cast
                else:
                    cls.__unicode__ = cls.__text_cast
            elif cls._delegate_bytes:
                if six.PY3:
                    cls.__bytes__ = cls.__bytes_cast
                else:
                    cls.__str__ = cls.__bytes_cast

        @classmethod
        def __promise__(cls, klass, funcname, method):
            # Builds a wrapper around some magic method and registers that
            # magic method for the given type and method name.
            def __wrapper__(self, *args, **kw):
                # Automatically triggers the evaluation of a lazy value and
                # applies the given magic method of the result type.
                res = func(*self.__args, **self.__kw)
                for t in type(res).mro():
                    if t in self.__dispatch:
                        return self.__dispatch[t][funcname](res, *args, **kw)
                raise TypeError("Lazy object returned unexpected type.")

            if klass not in cls.__dispatch:
                cls.__dispatch[klass] = {}
            cls.__dispatch[klass][funcname] = method
            return __wrapper__

        def __text_cast(self):
            return func(*self.__args, **self.__kw)

        def __bytes_cast(self):
            return bytes(func(*self.__args, **self.__kw))

        def __cast(self):
            if self._delegate_bytes:
                return self.__bytes_cast()
            elif self._delegate_text:
                return self.__text_cast()
            else:
                return func(*self.__args, **self.__kw)

        def __ne__(self, other):
            if isinstance(other, Promise):
                other = other.__cast()
            return self.__cast() != other

        def __eq__(self, other):
            if isinstance(other, Promise):
                other = other.__cast()
            return self.__cast() == other

        def __lt__(self, other):
            if isinstance(other, Promise):
                other = other.__cast()
            return self.__cast() < other

        def __hash__(self):
            return hash(self.__cast())

        def __mod__(self, rhs):
            if self._delegate_bytes and six.PY2:
                return bytes(self) % rhs
            elif self._delegate_text:
                return six.text_type(self) % rhs
            return self.__cast() % rhs

        def __deepcopy__(self, memo):
            # Instances of this class are effectively immutable. It's just a
            # collection of functions. So we don't need to do anything
            # complicated for copying.
            memo[id(self)] = self
            return self

    @wraps(func)
    def __wrapper__(*args, **kw):
        # Creates the proxy object, instead of the actual value.
        return __proxy__(args, kw)

    return __wrapper__


def _lazy_proxy_unpickle(func, args, kwargs, *resultclasses):
    return lazy(func, *resultclasses)(*args, **kwargs)


def allow_lazy(func, *resultclasses):
    """
    A decorator that allows a function to be called with one or more lazy
    arguments. If none of the args are lazy, the function is evaluated
    immediately, otherwise a __proxy__ is returned that will evaluate the
    function when needed.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        for arg in list(args) + list(six.itervalues(kwargs)):
            if isinstance(arg, Promise):
                break
        else:
            return func(*args, **kwargs)
        return lazy(func, *resultclasses)(*args, **kwargs)
    return wrapper

empty = object()


def new_method_proxy(func):
    def inner(self, *args):
        if self._wrapped is empty:
            self._setup()
        return func(self._wrapped, *args)
    return inner


class LazyObject(object):

    """
    A wrapper for another class that can be used to delay instantiation of the
    wrapped class.

    By subclassing, you have the opportunity to intercept and alter the
    instantiation. If you don't need to do that, use SimpleLazyObject.
    """

    # Avoid infinite recursion when tracing __init__ (#19456).
    _wrapped = None

    def __init__(self):
        self._wrapped = empty

    __getattr__ = new_method_proxy(getattr)

    def __setattr__(self, name, value):
        if name == "_wrapped":
            # Assign to __dict__ to avoid infinite __setattr__ loops.
            self.__dict__["_wrapped"] = value
        else:
            if self._wrapped is empty:
                self._setup()
            setattr(self._wrapped, name, value)

    def __delattr__(self, name):
        if name == "_wrapped":
            raise TypeError("can't delete _wrapped.")
        if self._wrapped is empty:
            self._setup()
        delattr(self._wrapped, name)

    def _setup(self):
        """
        Must be implemented by subclasses to initialize the wrapped object.
        """
        raise NotImplementedError(
            'subclasses of LazyObject must provide a _setup() method')

    # Because we have messed with __class__ below, we confuse pickle as to what
    # class we are pickling. It also appears to stop __reduce__ from being
    # called. So, we define __getstate__ in a way that cooperates with the way
    # that pickle interprets this class.  This fails when the wrapped class is
    # a builtin, but it is better than nothing.
    def __getstate__(self):
        if self._wrapped is empty:
            self._setup()
        return self._wrapped.__dict__

    # Python 3.3 will call __reduce__ when pickling; this method is needed
    # to serialize and deserialize correctly.
    @classmethod
    def __newobj__(cls, *args):
        return cls.__new__(cls, *args)

    def __reduce_ex__(self, proto):
        if proto >= 2:
            # On Py3, since the default protocol is 3, pickle uses the
            # ``__newobj__`` method (& more efficient opcodes) for writing.
            return (self.__newobj__, (self.__class__,), self.__getstate__())
        else:
            # On Py2, the default protocol is 0 (for back-compat) & the above
            # code fails miserably (see regression test). Instead, we return
            # exactly what's returned if there's no ``__reduce__`` method at
            # all.
            return (copyreg._reconstructor, (self.__class__, object, None), self.__getstate__())

    def __deepcopy__(self, memo):
        if self._wrapped is empty:
            # We have to use type(self), not self.__class__, because the
            # latter is proxied.
            result = type(self)()
            memo[id(self)] = result
            return result
        return copy.deepcopy(self._wrapped, memo)

    if six.PY3:
        __bytes__ = new_method_proxy(bytes)
        __str__ = new_method_proxy(str)
        __bool__ = new_method_proxy(bool)
    else:
        __str__ = new_method_proxy(str)
        __unicode__ = new_method_proxy(unicode)
        __nonzero__ = new_method_proxy(bool)

    # Introspection support
    __dir__ = new_method_proxy(dir)

    # Need to pretend to be the wrapped class, for the sake of objects that
    # care about this (especially in equality tests)
    __class__ = property(new_method_proxy(operator.attrgetter("__class__")))
    __eq__ = new_method_proxy(operator.eq)
    __ne__ = new_method_proxy(operator.ne)
    __hash__ = new_method_proxy(hash)

    # Dictionary methods support
    __getitem__ = new_method_proxy(operator.getitem)
    __setitem__ = new_method_proxy(operator.setitem)
    __delitem__ = new_method_proxy(operator.delitem)

    __len__ = new_method_proxy(len)
    __contains__ = new_method_proxy(operator.contains)


# Workaround for http://bugs.python.org/issue12370
_super = super


class SimpleLazyObject(LazyObject):

    """
    A lazy object initialized from any function.

    Designed for compound objects of unknown type. For builtins or objects of
    known type, use django.utils.functional.lazy.
    """

    def __init__(self, func):
        """
        Pass in a callable that returns the object to be wrapped.

        If copies are made of the resulting SimpleLazyObject, which can happen
        in various circumstances within Django, then you must ensure that the
        callable can be safely run more than once and will return the same
        value.
        """
        self.__dict__['_setupfunc'] = func
        _super(SimpleLazyObject, self).__init__()

    def _setup(self):
        self._wrapped = self._setupfunc()

    # Return a meaningful representation of the lazy object for debugging
    # without evaluating the wrapped object.
    def __repr__(self):
        if self._wrapped is empty:
            repr_attr = self._setupfunc
        else:
            repr_attr = self._wrapped
        return '<%s: %r>' % (type(self).__name__, repr_attr)

    def __deepcopy__(self, memo):
        if self._wrapped is empty:
            # We have to use SimpleLazyObject, not self.__class__, because the
            # latter is proxied.
            result = SimpleLazyObject(self._setupfunc)
            memo[id(self)] = result
            return result
        return copy.deepcopy(self._wrapped, memo)


class lazy_property(property):

    """
    A property that works with subclasses by wrapping the decorated
    functions of the base class.
    """
    def __new__(cls, fget=None, fset=None, fdel=None, doc=None):
        if fget is not None:
            @wraps(fget)
            def fget(instance, instance_type=None, name=fget.__name__):
                return getattr(instance, name)()
        if fset is not None:
            @wraps(fset)
            def fset(instance, value, name=fset.__name__):
                return getattr(instance, name)(value)
        if fdel is not None:
            @wraps(fdel)
            def fdel(instance, name=fdel.__name__):
                return getattr(instance, name)()
        return property(fget, fset, fdel, doc)


if sys.version_info >= (2, 7, 2):
    from functools import total_ordering
else:
    # For Python < 2.7.2. total_ordering in versions prior to 2.7.2 is buggy.
    # See http://bugs.python.org/issue10042 for details. For these versions use
    # code borrowed from Python 2.7.3.
    def total_ordering(cls):
        """Class decorator that fills in missing ordering methods"""
        convert = {
            '__lt__': [('__gt__', lambda self, other: not (self < other or self == other)),
                       ('__le__', lambda self, other:
                        self < other or self == other),
                       ('__ge__', lambda self, other: not self < other)],
            '__le__': [('__ge__', lambda self, other: not self <= other or self == other),
                       ('__lt__', lambda self, other:
                        self <= other and not self == other),
                       ('__gt__', lambda self, other: not self <= other)],
            '__gt__': [('__lt__', lambda self, other: not (self > other or self == other)),
                       ('__ge__', lambda self, other:
                        self > other or self == other),
                       ('__le__', lambda self, other: not self > other)],
            '__ge__': [('__le__', lambda self, other: (not self >= other) or self == other),
                       ('__gt__', lambda self, other:
                        self >= other and not self == other),
                       ('__lt__', lambda self, other: not self >= other)]
        }
        roots = set(dir(cls)) & set(convert)
        if not roots:
            raise ValueError(
                'must define at least one ordering operation: < > <= >=')
        root = max(roots)       # prefer __lt__ to __le__ to __gt__ to __ge__
        for opname, opfunc in convert[root]:
            if opname not in roots:
                opfunc.__name__ = opname
                opfunc.__doc__ = getattr(int, opname).__doc__
                setattr(cls, opname, opfunc)
        return cls

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.6.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):

            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        try:
            result = self._resolve()
        except ImportError:
            # See the nice big comment in MovedModule.__getattr__.
            raise AttributeError("%s could not be imported " % self.name)
        setattr(obj, self.name, result)  # Invokes __set__.
        # This is a bit ugly, but it avoids running this again.
        delattr(obj.__class__, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)

    def __getattr__(self, attr):
        # It turns out many Python frameworks like to traverse sys.modules and
        # try to load various attributes. This causes problems if this is a
        # platform-specific module on the wrong platform, like _winreg on
        # Unixes. Therefore, we silently pretend unimportable modules do not
        # have any attributes. See issues #51, #53, #56, and #63 for the full
        # tales of woe.
        #
        # First, if possible, avoid loading the module just to look at __file__,
        # __name__, or __path__.
        if (attr in ("__file__", "__name__", "__path__") and
                self.mod not in sys.modules):
            raise AttributeError(attr)
        try:
            _module = self._resolve()
        except ImportError:
            raise AttributeError(attr)
        value = getattr(_module, attr)
        setattr(self, attr, value)
        return value


class _LazyModule(types.ModuleType):

    def __init__(self, name):
        super(_LazyModule, self).__init__(name)
        self.__doc__ = self.__class__.__doc__

    def __dir__(self):
        attrs = ["__doc__", "__name__"]
        attrs += [attr.name for attr in self._moved_attributes]
        return attrs

    # Subclasses should override this
    _moved_attributes = []


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)


class _MovedItems(_LazyModule):

    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools",
                   "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools",
                   "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart",
                "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("_thread", "thread", "_thread"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText",
                "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_ttk", "ttk", "tkinter.ttk"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ +
                ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ +
                ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib",
                __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("xmlrpc_client", "xmlrpclib", "xmlrpc.client"),
    MovedModule("xmlrpc_server", "xmlrpclib", "xmlrpc.server"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if isinstance(attr, MovedModule):
        sys.modules[__name__ + ".moves." + attr.name] = attr
del attr

_MovedItems._moved_attributes = _moved_attributes

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")


class Module_six_moves_urllib_parse(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("SplitResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
    MovedAttribute("splitquery", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes

sys.modules[__name__ + ".moves.urllib_parse"] = sys.modules[__name__ +
                                                            ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")


class Module_six_moves_urllib_error(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes

sys.modules[__name__ + ".moves.urllib_error"] = sys.modules[__name__ +
                                                            ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm",
                   "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

sys.modules[__name__ + ".moves.urllib_request"] = sys.modules[__name__ +
                                                              ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes

sys.modules[__name__ + ".moves.urllib_response"] = sys.modules[__name__ +
                                                               ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes

sys.modules[__name__ + ".moves.urllib_robotparser"] = sys.modules[__name__ +
                                                                  ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):

    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]

    def __dir__(self):
        return ['parse', 'error', 'request', 'response', 'robotparser']


sys.modules[__name__ +
            ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))


def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))


def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))


def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")

    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    # Workaround for standalone backslash

    def u(s):
        return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
    unichr = unichr
    int2byte = chr

    def byte2int(bs):
        return ord(bs[0])

    def indexbytes(buf, i):
        return ord(buf[i])

    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    exec_ = getattr(moves.builtins, "exec")

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


print_ = getattr(moves.builtins, "print", None)
if print_ is None:
    def print_(*args, **kwargs):
        """The new-style print function for Python 2.4 and 2.5."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return

        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            # If the file has an encoding, encode unicode with it.
            if (isinstance(fp, file) and
                    isinstance(data, unicode) and
                    fp.encoding is not None):
                errors = getattr(fp, "errors", None)
                if errors is None:
                    errors = "strict"
                data = data.encode(fp.encoding, errors)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


### Additional customizations for Django ###

if PY3:
    _assertRaisesRegex = "assertRaisesRegex"
    _assertRegex = "assertRegex"
    memoryview = memoryview
else:
    _assertRaisesRegex = "assertRaisesRegexp"
    _assertRegex = "assertRegexpMatches"
    # memoryview and buffer are not strictly equivalent, but should be fine for
    # django core usage (mainly BinaryField). However, Jython doesn't support
    # buffer (see http://bugs.jython.org/issue1521), so we have to be careful.
    if sys.platform.startswith('java'):
        memoryview = memoryview
    else:
        memoryview = buffer


def assertRaisesRegex(self, *args, **kwargs):
    return getattr(self, _assertRaisesRegex)(*args, **kwargs)


def assertRegex(self, *args, **kwargs):
    return getattr(self, _assertRegex)(*args, **kwargs)


add_move(MovedModule("_dummy_thread", "dummy_thread"))
add_move(MovedModule("_thread", "thread"))

########NEW FILE########
__FILENAME__ = timing
import time


class timer(object):

    def __init__(self):
        self.times = [time.time()]
        self.total = 0.
        self.next()

    def next(self):
        times = self.times
        times.append(time.time())
        delta = times[-1] - times[-2]
        self.total += delta
        return delta

########NEW FILE########
__FILENAME__ = validate


def validate_type_strict(object_, object_types):
    '''
    Validates that object_ is of type object__type
    :param object_: the object to check
    :param object_types: the desired type of the object (or tuple of types)
    '''
    if not isinstance(object_types, tuple):
        object_types = (object_types,)
    exact_type_match = any([type(object_) == t for t in object_types])
    if not exact_type_match:
        error_format = 'Please pass object_ of type %s as the argument, encountered type %s'
        message = error_format % (object_types, type(object_))
        raise ValueError(message)


def validate_list_of_strict(object_list, object_types):
    '''
    Verifies that the items in object_list are of
    type object__type

    :param object_list: the list of objects to check
    :param object_types: the type of the object (or tuple with types)

    In general this goes against Python's duck typing ideology
    See this discussion for instance
    http://stackoverflow.com/questions/1549801/differences-between-isinstance-and-type-in-python

    We use it in cases where you can configure the type of class to use
    And where we should validate that you are infact supplying that class
    '''
    for object_ in object_list:
        validate_type_strict(object_, object_types)

########NEW FILE########
__FILENAME__ = base
from feedly.verbs import register


class Verb(object):

    '''
    Every activity has a verb and an object.
    Nomenclatura is loosly based on
    http://activitystrea.ms/specs/atom/1.0/#activity.summary
    '''
    id = 0

    def __str__(self):
        return self.infinitive

    def serialize(self):
        serialized = self.id
        return serialized


class Follow(Verb):
    id = 1
    infinitive = 'follow'
    past_tense = 'followed'

register(Follow)


class Comment(Verb):
    id = 2
    infinitive = 'comment'
    past_tense = 'commented'

register(Comment)


class Love(Verb):
    id = 3
    infinitive = 'love'
    past_tense = 'loved'

register(Love)


class Add(Verb):
    id = 4
    infinitive = 'add'
    past_tense = 'added'

register(Add)

########NEW FILE########
