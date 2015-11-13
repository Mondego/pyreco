__FILENAME__ = columns
#column field types
from copy import deepcopy, copy
from datetime import datetime
from datetime import date
import re
from uuid import uuid1, uuid4
from cql.query import cql_quote
from cql.cqltypes import DateType

from cqlengine.exceptions import ValidationError


class BaseValueManager(object):

    def __init__(self, instance, column, value):
        self.instance = instance
        self.column = column
        self.previous_value = deepcopy(value)
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

    #the cassandra type this column maps to
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
                 clustering_order=None,
                 polymorphic_key=False):
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
        :param polymorphic_key: boolean, if set to True, this column will be used for saving and loading instances
            of polymorphic tables
        """
        self.partition_key = partition_key
        self.primary_key = partition_key or primary_key
        self.index = index
        self.db_field = db_field
        self.default = default
        self.required = required
        self.clustering_order = clustering_order
        self.polymorphic_key = polymorphic_key
        #the column name in the model definition
        self.column_name = None

        self.value = None

        #keep track of instantiation order
        self.position = Column.instance_counter
        Column.instance_counter += 1

    def validate(self, value):
        """
        Returns a cleaned and validated value. Raises a ValidationError
        if there's a problem
        """
        if value is None:
            if self.has_default:
                return self.get_default()
            elif self.required:
                raise ValidationError('{} - None values are not allowed'.format(self.column_name or self.db_field))
        return value

    def to_python(self, value):
        """
        Converts data from the database into python values
        raises a ValidationError if the value can't be converted
        """
        return value

    def to_database(self, value):
        """
        Converts python value into database value
        """
        if value is None and self.has_default:
            return self.get_default()
        return value

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

    def _val_is_null(self, val):
        """ determines if the given value equates to a null value for the given column type """
        return val is None


class Bytes(Column):
    db_type = 'blob'

    class Quoter(ValueQuoter):
        def __str__(self):
            return '0x' + self.value.encode('hex')

    def to_database(self, value):
        val = super(Bytes, self).to_database(value)
        if val is None: return

        return self.Quoter(val)

    def to_python(self, value):
        #return value[2:].decode('hex')
        return value


class Ascii(Column):
    db_type = 'ascii'


class Text(Column):
    db_type = 'text'

    def __init__(self, *args, **kwargs):
        self.min_length = kwargs.pop('min_length', 1 if kwargs.get('required', False) else None)
        self.max_length = kwargs.pop('max_length', None)
        super(Text, self).__init__(*args, **kwargs)

    def validate(self, value):
        value = super(Text, self).validate(value)
        if value is None: return
        if not isinstance(value, (basestring, bytearray)) and value is not None:
            raise ValidationError('{} is not a string'.format(type(value)))
        if self.max_length:
            if len(value) > self.max_length:
                raise ValidationError('{} is longer than {} characters'.format(self.column_name, self.max_length))
        if self.min_length:
            if len(value) < self.min_length:
                raise ValidationError('{} is shorter than {} characters'.format(self.column_name, self.min_length))
        return value


class Integer(Column):
    db_type = 'int'

    def validate(self, value):
        val = super(Integer, self).validate(value)
        if val is None: return
        try:
            return long(val)
        except (TypeError, ValueError):
            raise ValidationError("{} can't be converted to integral value".format(value))

    def to_python(self, value):
        return self.validate(value)

    def to_database(self, value):
        return self.validate(value)


class BigInt(Integer):
    db_type = 'bigint'


class VarInt(Column):
    db_type = 'varint'

    def validate(self, value):
        val = super(VarInt, self).validate(value)
        if val is None:
            return
        try:
            return long(val)
        except (TypeError, ValueError):
            raise ValidationError(
                "{} can't be converted to integral value".format(value))

    def to_python(self, value):
        return self.validate(value)

    def to_database(self, value):
        return self.validate(value)


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
        val = self.to_database(val)
        prev = self.to_database(prev or 0)
        field_id = uuid4().hex

        delta = val - prev
        sign = '-' if delta < 0 else '+'
        delta = abs(delta)
        ctx[field_id] = delta
        return ['"{0}" = "{0}" {1} {2}'.format(self.db_field_name, sign, delta)]


class DateTime(Column):
    db_type = 'timestamp'

    def to_python(self, value):
        if value is None: return
        if isinstance(value, datetime):
            return value
        elif isinstance(value, date):
            return datetime(*(value.timetuple()[:6]))
        try:
            return datetime.utcfromtimestamp(value)
        except TypeError:
            return datetime.utcfromtimestamp(DateType.deserialize(value))

    def to_database(self, value):
        value = super(DateTime, self).to_database(value)
        if value is None: return
        if not isinstance(value, datetime):
            if isinstance(value, date):
                value = datetime(value.year, value.month, value.day)
            else:
                raise ValidationError("'{}' is not a datetime object".format(value))
        epoch = datetime(1970, 1, 1, tzinfo=value.tzinfo)
        offset = epoch.tzinfo.utcoffset(epoch).total_seconds() if epoch.tzinfo else 0

        return long(((value - epoch).total_seconds() - offset) * 1000)


class Date(Column):
    db_type = 'timestamp'

    def to_python(self, value):
        if value is None: return
        if isinstance(value, datetime):
            return value.date()
        elif isinstance(value, date):
            return value
        try:
            return datetime.utcfromtimestamp(value).date()
        except TypeError:
            return datetime.utcfromtimestamp(DateType.deserialize(value)).date()

    def to_database(self, value):
        value = super(Date, self).to_database(value)
        if value is None: return
        if isinstance(value, datetime):
            value = value.date()
        if not isinstance(value, date):
            raise ValidationError("'{}' is not a date object".format(repr(value)))

        return long((value - date(1970, 1, 1)).total_seconds() * 1000)


class UUID(Column):
    """
    Type 1 or 4 UUID
    """
    db_type = 'uuid'

    re_uuid = re.compile(r'[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}')

    def validate(self, value):
        val = super(UUID, self).validate(value)
        if val is None: return
        from uuid import UUID as _UUID
        if isinstance(val, _UUID): return val
        if isinstance(val, basestring) and self.re_uuid.match(val):
            return _UUID(val)
        raise ValidationError("{} is not a valid uuid".format(value))

    def to_python(self, value):
        return self.validate(value)

    def to_database(self, value):
        return self.validate(value)

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
        offset = epoch.tzinfo.utcoffset(epoch).total_seconds() if epoch.tzinfo else 0
        timestamp = (dt  - epoch).total_seconds() - offset

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

    class Quoter(ValueQuoter):
        """ Cassandra 1.2.5 is stricter about boolean values """
        def __str__(self):
            return 'true' if self.value else 'false'

    def validate(self, value):
        """ Always returns a Python boolean. """
        if isinstance(value, self.Quoter):
            value = value.value
        return bool(value)

    def to_python(self, value):
        return self.validate(value)

    def to_database(self, value):
        return self.Quoter(self.validate(value))


class Float(Column):
    db_type = 'double'

    def __init__(self, double_precision=True, **kwargs):
        self.db_type = 'double' if double_precision else 'float'
        super(Float, self).__init__(**kwargs)

    def validate(self, value):
        value = super(Float, self).validate(value)
        if value is None: return
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError("{} is not a valid float".format(value))

    def to_python(self, value):
        return self.validate(value)

    def to_database(self, value):
        return self.validate(value)


class Decimal(Column):
    db_type = 'decimal'

    def validate(self, value):
        from decimal import Decimal as _Decimal
        from decimal import InvalidOperation
        val = super(Decimal, self).validate(value)
        if val is None: return
        try:
            return _Decimal(val)
        except InvalidOperation:
            raise ValidationError("'{}' can't be coerced to decimal".format(val))

    def to_python(self, value):
        return self.validate(value)

    def to_database(self, value):
        return self.validate(value)


class BaseContainerColumn(Column):
    """
    Base Container type for collection-like columns.

    https://cassandra.apache.org/doc/cql3/CQL.html#collections
    """

    def __init__(self, value_type, **kwargs):
        """
        :param value_type: a column class indicating the types of the value
        """
        inheritance_comparator = issubclass if isinstance(value_type, type) else isinstance
        if not inheritance_comparator(value_type, Column):
            raise ValidationError('value_type must be a column class')
        if inheritance_comparator(value_type, BaseContainerColumn):
            raise ValidationError('container types cannot be nested')
        if value_type.db_type is None:
            raise ValidationError('value_type cannot be an abstract column type')

        if isinstance(value_type, type):
            self.value_type = value_type
            self.value_col = self.value_type()
        else:
            self.value_col = value_type
            self.value_type = self.value_col.__class__

        super(BaseContainerColumn, self).__init__(**kwargs)

    def validate(self, value):
        value = super(BaseContainerColumn, self).validate(value)
        # It is dangerous to let collections have more than 65535.
        # See: https://issues.apache.org/jira/browse/CASSANDRA-5428
        if value is not None and len(value) > 65535:
            raise ValidationError("Collection can't have more than 65535 elements.")
        return value

    def get_column_def(self):
        """
        Returns a column definition for CQL table definition
        """
        db_type = self.db_type.format(self.value_type.db_type)
        return '{} {}'.format(self.cql, db_type)

    def get_update_statement(self, val, prev, ctx):
        """
        Used to add partial update statements
        """
        raise NotImplementedError

    def _val_is_null(self, val):
        return not val


class BaseContainerQuoter(ValueQuoter):

    def __nonzero__(self):
        return bool(self.value)


class Set(BaseContainerColumn):
    """
    Stores a set of unordered, unique values

    http://www.datastax.com/docs/1.2/cql_cli/using/collections
    """
    db_type = 'set<{}>'

    class Quoter(BaseContainerQuoter):

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
        if val is None: return
        types = (set,) if self.strict else (set, list, tuple)
        if not isinstance(val, types):
            if self.strict:
                raise ValidationError('{} is not a set object'.format(val))
            else:
                raise ValidationError('{} cannot be coerced to a set object'.format(val))

        if None in val:
            raise ValidationError("None not allowed in a set")

        return {self.value_col.validate(v) for v in val}

    def to_python(self, value):
        if value is None: return set()
        return {self.value_col.to_python(v) for v in value}

    def to_database(self, value):
        if value is None: return None

        if isinstance(value, self.Quoter): return value
        return self.Quoter({self.value_col.to_database(v) for v in value})

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
        val = self.to_database(val)
        prev = self.to_database(prev)
        if isinstance(val, self.Quoter): val = val.value
        if isinstance(prev, self.Quoter): prev = prev.value

        if val is None or val == prev:
            # don't return anything if the new value is the same as
            # the old one, or if the new value is none
            return []
        elif prev is None or not any({v in prev for v in val}):
            field = uuid1().hex
            ctx[field] = self.Quoter(val)
            return ['"{}" = :{}'.format(self.db_field_name, field)]
        else:
            # partial update time
            to_create = val - prev
            to_delete = prev - val
            statements = []

            if to_create:
                field_id = uuid1().hex
                ctx[field_id] = self.Quoter(to_create)
                statements += ['"{0}" = "{0}" + :{1}'.format(self.db_field_name, field_id)]

            if to_delete:
                field_id = uuid1().hex
                ctx[field_id] = self.Quoter(to_delete)
                statements += ['"{0}" = "{0}" - :{1}'.format(self.db_field_name, field_id)]

            return statements


class List(BaseContainerColumn):
    """
    Stores a list of ordered values

    http://www.datastax.com/docs/1.2/cql_cli/using/collections_list
    """
    db_type = 'list<{}>'

    class Quoter(BaseContainerQuoter):

        def __str__(self):
            cq = cql_quote
            return '[' + ', '.join([cq(v) for v in self.value]) + ']'

        def __nonzero__(self):
            return bool(self.value)

    def __init__(self, value_type, default=list, **kwargs):
        return super(List, self).__init__(value_type=value_type, default=default, **kwargs)

    def validate(self, value):
        val = super(List, self).validate(value)
        if val is None: return
        if not isinstance(val, (set, list, tuple)):
            raise ValidationError('{} is not a list object'.format(val))
        if None in val:
            raise ValidationError("None is not allowed in a list")
        return [self.value_col.validate(v) for v in val]

    def to_python(self, value):
        if value is None: return []
        return [self.value_col.to_python(v) for v in value]

    def to_database(self, value):
        if value is None: return None
        if isinstance(value, self.Quoter): return value
        return self.Quoter([self.value_col.to_database(v) for v in value])

    def get_update_statement(self, val, prev, values):
        """
        Returns statements that will be added to an object's update statement
        also updates the query context
        """
        # remove from Quoter containers, if applicable
        val = self.to_database(val)
        prev = self.to_database(prev)
        if isinstance(val, self.Quoter): val = val.value
        if isinstance(prev, self.Quoter): prev = prev.value

        def _insert():
            field_id = uuid1().hex
            values[field_id] = self.Quoter(val)
            return ['"{}" = :{}'.format(self.db_field_name, field_id)]

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
            search_space = len(val) - max(0, len(prev)-1)

            # the size of the sub lists we want to look at
            search_size = len(prev)

            for i in range(search_space):
                #slice boundary
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
                statements += ['"{0}" = :{1} + "{0}"'.format(self.db_field_name, field_id)]

            if append:
                field_id = uuid1().hex
                values[field_id] = self.Quoter(append)
                statements += ['"{0}" = "{0}" + :{1}'.format(self.db_field_name, field_id)]

            return statements


class Map(BaseContainerColumn):
    """
    Stores a key -> value map (dictionary)

    http://www.datastax.com/docs/1.2/cql_cli/using/collections_map
    """

    db_type = 'map<{}, {}>'

    class Quoter(BaseContainerQuoter):

        def __str__(self):
            cq = cql_quote
            return '{' + ', '.join([cq(k) + ':' + cq(v) for k,v in self.value.items()]) + '}'

        def get(self, key):
            return self.value.get(key)

        def keys(self):
            return self.value.keys()

    def __init__(self, key_type, value_type, default=dict, **kwargs):
        """
        :param key_type: a column class indicating the types of the key
        :param value_type: a column class indicating the types of the value
        """
        inheritance_comparator = issubclass if isinstance(key_type, type) else isinstance
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
        return '{} {}'.format(self.cql, db_type)

    def validate(self, value):
        val = super(Map, self).validate(value)
        if val is None: return
        if not isinstance(val, dict):
            raise ValidationError('{} is not a dict object'.format(val))
        return {self.key_col.validate(k):self.value_col.validate(v) for k,v in val.items()}

    def to_python(self, value):
        if value is None:
            return {}
        if value is not None:
            return {self.key_col.to_python(k): self.value_col.to_python(v) for k,v in value.items()}

    def to_database(self, value):
        if value is None: return None
        if isinstance(value, self.Quoter): return value
        return self.Quoter({self.key_col.to_database(k):self.value_col.to_database(v) for k,v in value.items()})

    def get_update_statement(self, val, prev, ctx):
        """
        http://www.datastax.com/docs/1.2/cql_cli/using/collections_map#deletion
        """
        # remove from Quoter containers, if applicable
        val = self.to_database(val)
        prev = self.to_database(prev)
        if isinstance(val, self.Quoter): val = val.value
        if isinstance(prev, self.Quoter): prev = prev.value
        val = val or {}
        prev = prev or {}

        #get the updated map
        update = {k:v for k,v in val.items() if v != prev.get(k)}

        statements = []
        for k,v in update.items():
            key_id = uuid1().hex
            val_id = uuid1().hex
            ctx[key_id] = k
            ctx[val_id] = v
            statements += ['"{}"[:{}] = :{}'.format(self.db_field_name, key_id, val_id)]

        return statements

    def get_delete_statement(self, val, prev, ctx):
        """
        Returns statements that will be added to an object's delete statement
        also updates the query context, used for removing keys from a map
        """
        if val is prev is None:
            return []

        val = self.to_database(val)
        prev = self.to_database(prev)
        if isinstance(val, self.Quoter): val = val.value
        if isinstance(prev, self.Quoter): prev = prev.value

        old_keys = set(prev.keys()) if prev else set()
        new_keys = set(val.keys()) if val else set()
        del_keys = old_keys - new_keys

        del_statements = []
        for key in del_keys:
            field_id = uuid1().hex
            ctx[field_id] = key
            del_statements += ['"{}"[:{}]'.format(self.db_field_name, field_id)]

        return del_statements


class _PartitionKeysToken(Column):
    """
    virtual column representing token of partition columns.
    Used by filter(pk__token=Token(...)) filters
    """

    def __init__(self, model):
        self.partition_columns = model._partition_keys.values()
        super(_PartitionKeysToken, self).__init__(partition_key=True)

    @property
    def db_field_name(self):
        return 'token({})'.format(', '.join(['"{}"'.format(c.db_field_name) for c in self.partition_columns]))

    def to_database(self, value):
        from cqlengine.functions import Token
        assert isinstance(value, Token)
        value.set_columns(self.partition_columns)
        return value

    def get_cql(self):
        return "token({})".format(", ".join(c.cql for c in self.partition_columns))


########NEW FILE########
__FILENAME__ = connection
#http://pypi.python.org/pypi/cql/1.0.4
#http://code.google.com/a/apache-extras.org/p/cassandra-dbapi2 /
#http://cassandra.apache.org/doc/cql/CQL.html

from collections import namedtuple
try:
    import Queue as queue
except ImportError:
    # python 3
    import queue
import random

import cql
import logging

from copy import copy
from cqlengine.exceptions import CQLEngineException

from cql import OperationalError

from contextlib import contextmanager

from thrift.transport.TTransport import TTransportException
from cqlengine.statements import BaseCQLStatement

LOG = logging.getLogger('cqlengine.cql')

class CQLConnectionError(CQLEngineException): pass

Host = namedtuple('Host', ['name', 'port'])

_max_connections = 10

# global connection pool
connection_pool = None



class CQLConnectionError(CQLEngineException): pass


class RowResult(tuple):
    pass

QueryResult = namedtuple('RowResult', ('columns', 'results'))


def _column_tuple_factory(colnames, values):
    return tuple(colnames), [RowResult(v) for v in values]


def setup(
        hosts,
        username=None,
        password=None,
        max_connections=10,
        default_keyspace=None,
        consistency='ONE',
        timeout=None):
    """
    Records the hosts and connects to one of them

    :param hosts: list of hosts, strings in the <hostname>:<port>, or just <hostname>
    :type hosts: list
    :param username: The cassandra username
    :type username: str
    :param password: The cassandra password
    :type password: str
    :param max_connections: The maximum number of connections to service
    :type max_connections: int or long
    :param default_keyspace: The default keyspace to use
    :type default_keyspace: str
    :param consistency: The global consistency level
    :type consistency: str
    :param timeout: The connection timeout in milliseconds
    :type timeout: int or long

    """
    global _max_connections
    global connection_pool
    _max_connections = max_connections

    if default_keyspace:
        from cqlengine import models
        models.DEFAULT_KEYSPACE = default_keyspace

    _hosts = []
    for host in hosts:
        host = host.strip()
        host = host.split(':')
        if len(host) == 1:
            port = 9160
        elif len(host) == 2:
            try:
                port = int(host[1])
            except ValueError:
                raise CQLConnectionError("Can't parse port as int {}".format(':'.join(host)))
        else:
            raise CQLConnectionError("Can't parse host string {}".format(':'.join(host)))

        _hosts.append(Host(host[0], port))

    if not _hosts:
        raise CQLConnectionError("At least one host required")

    connection_pool = ConnectionPool(_hosts, username, password, consistency, timeout)


class ConnectionPool(object):
    """Handles pooling of database connections."""

    def __init__(
            self,
            hosts,
            username=None,
            password=None,
            consistency=None,
            timeout=None):
        self._hosts = hosts
        self._username = username
        self._password = password
        self._consistency = consistency
        self._timeout = timeout

        self._queue = queue.Queue(maxsize=_max_connections)

    def clear(self):
        """
        Force the connection pool to be cleared. Will close all internal
        connections.
        """
        try:
            while not self._queue.empty():
                self._queue.get().close()
        except:
            pass

    def get(self):
        """
        Returns a usable database connection. Uses the internal queue to
        determine whether to return an existing connection or to create
        a new one.
        """
        try:
            # get with block=False returns an item if one
            # is immediately available, else raises the Empty exception
            return self._queue.get(block=False)
        except queue.Empty:
            return self._create_connection()

    def put(self, conn):
        """
        Returns a connection to the queue freeing it up for other queries to
        use.

        :param conn: The connection to be released
        :type conn: connection
        """

        try:
            self._queue.put(conn, block=False)
        except queue.Full:
            conn.close()

    def _create_transport(self, host):
        """
        Create a new Thrift transport for the given host.

        :param host: The host object
        :type host: Host

        :rtype: thrift.TTransport.*

        """
        from thrift.transport import TSocket, TTransport

        thrift_socket = TSocket.TSocket(host.name, host.port)

        if self._timeout is not None:
            thrift_socket.setTimeout(self._timeout)

        return TTransport.TFramedTransport(thrift_socket)

    def _create_connection(self):
        """
        Creates a new connection for the connection pool.

        should only return a valid connection that it's actually connected to
        """
        if not self._hosts:
            raise CQLConnectionError("At least one host required")

        hosts = copy(self._hosts)
        random.shuffle(hosts)

        for host in hosts:
            try:
                transport = self._create_transport(host)
                new_conn = cql.connect(
                    host.name,
                    host.port,
                    user=self._username,
                    password=self._password,
                    consistency_level=self._consistency,
                    transport=transport
                )
                new_conn.set_cql_version('3.0.0')
                return new_conn
            except Exception as exc:
                logging.debug("Could not establish connection to"
                              " {}:{} ({!r})".format(host.name, host.port, exc))

        raise CQLConnectionError("Could not connect to any server in cluster")

    def execute(self, query, params, consistency_level=None):
        if not consistency_level:
            consistency_level = self._consistency

        while True:
            try:
                con = self.get()
                if not con:
                    raise CQLEngineException("Error calling execute without calling setup.")
                LOG.debug('{} {}'.format(query, repr(params)))
                cur = con.cursor()
                cur.execute(query, params, consistency_level=consistency_level)
                columns = [i[0] for i in cur.description or []]
                results = [RowResult(r) for r in cur.fetchall()]
                self.put(con)
                return QueryResult(columns, results)
            except CQLConnectionError as ex:
                raise CQLEngineException("Could not execute query against the cluster")
            except cql.ProgrammingError as ex:
                raise CQLEngineException(unicode(ex))
            except TTransportException:
                pass
            except OperationalError as ex:
                LOG.exception("Operational Error %s on %s:%s", ex, con.host, con.port)
                raise ex


def execute(query, params=None, consistency_level=None):
    if isinstance(query, BaseCQLStatement):
        params = query.get_context()
        query = str(query)
    params = params or {}
    if consistency_level is None:
        consistency_level = connection_pool._consistency
    return connection_pool.execute(query, params, consistency_level)

@contextmanager
def connection_manager():
    """ :rtype: ConnectionPool """
    global connection_pool
    # tmp = connection_pool.get()
    yield connection_pool
    # connection_pool.put(tmp)

########NEW FILE########
__FILENAME__ = exceptions
#cqlengine exceptions
class CQLEngineException(Exception): pass
class ModelException(CQLEngineException): pass
class ValidationError(CQLEngineException): pass


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

    format_string = ':{}'

    def __init__(self, value):
        self.value = value
        self.context_id = None

    def __unicode__(self):
        return self.format_string.format(self.context_id)

    def set_context_id(self, ctx_id):
        self.context_id = ctx_id

    def get_context_size(self):
        return 1

    def update_context(self, ctx):
        ctx[str(self.context_id)] = self.value


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

    format_string = 'MinTimeUUID(:{})'

    def __init__(self, value):
        """
        :param value: the time to create a maximum time uuid from
        :type value: datetime
        """
        if not isinstance(value, datetime):
            raise ValidationError('datetime instance is required')
        super(MinTimeUUID, self).__init__(value)

    def to_database(self, val):
        epoch = datetime(1970, 1, 1, tzinfo=val.tzinfo)
        offset = epoch.tzinfo.utcoffset(epoch).total_seconds() if epoch.tzinfo else 0
        return long(((val - epoch).total_seconds() - offset) * 1000)

    def update_context(self, ctx):
        ctx[str(self.context_id)] = self.to_database(self.value)


class MaxTimeUUID(BaseQueryFunction):
    """
    return a fake timeuuid corresponding to the largest possible timeuuid for the given timestamp

    http://cassandra.apache.org/doc/cql3/CQL.html#timeuuidFun
    """

    format_string = 'MaxTimeUUID(:{})'

    def __init__(self, value):
        """
        :param value: the time to create a minimum time uuid from
        :type value: datetime
        """
        if not isinstance(value, datetime):
            raise ValidationError('datetime instance is required')
        super(MaxTimeUUID, self).__init__(value)

    def to_database(self, val):
        epoch = datetime(1970, 1, 1, tzinfo=val.tzinfo)
        offset = epoch.tzinfo.utcoffset(epoch).total_seconds() if epoch.tzinfo else 0
        return long(((val - epoch).total_seconds() - offset) * 1000)

    def update_context(self, ctx):
        ctx[str(self.context_id)] = self.to_database(self.value)


class Token(BaseQueryFunction):
    """
    compute the token for a given partition key

    http://cassandra.apache.org/doc/cql3/CQL.html#tokenFun
    """

    def __init__(self, *values):
        if len(values) == 1 and isinstance(values[0], (list, tuple)):
            values = values[0]
        super(Token, self).__init__(values)
        self._columns = None

    def set_columns(self, columns):
        self._columns = columns

    def get_context_size(self):
        return len(self.value)

    def __unicode__(self):
        token_args = ', '.join(':{}'.format(self.context_id + i) for i in range(self.get_context_size()))
        return "token({})".format(token_args)

    def update_context(self, ctx):
        for i, (col, val) in enumerate(zip(self._columns, self.value)):
            ctx[str(self.context_id + i)] = col.to_database(val)


########NEW FILE########
__FILENAME__ = management
import json
import warnings
from cqlengine import SizeTieredCompactionStrategy, LeveledCompactionStrategy
from cqlengine import ONE
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
        _, keyspaces = con.execute("""SELECT keyspace_name FROM system.schema_keyspaces""", {}, ONE)
        if name not in [r[0] for r in keyspaces]:
            #try the 1.2 method
            replication_map = {
                'class': strategy_class,
                'replication_factor':replication_factor
            }
            replication_map.update(replication_values)
            if strategy_class.lower() != 'simplestrategy':
                # Although the Cassandra documentation states for `replication_factor`
                # that it is "Required if class is SimpleStrategy; otherwise,
                # not used." we get an error if it is present.
                replication_map.pop('replication_factor', None)

            query = """
            CREATE KEYSPACE {}
            WITH REPLICATION = {}
            """.format(name, json.dumps(replication_map).replace('"', "'"))

            if strategy_class != 'SimpleStrategy':
                query += " AND DURABLE_WRITES = {}".format('true' if durable_writes else 'false')

            execute(query)


def delete_keyspace(name):
    with connection_manager() as con:
        _, keyspaces = con.execute("""SELECT keyspace_name FROM system.schema_keyspaces""", {}, ONE)
        if name in [r[0] for r in keyspaces]:
            execute("DROP KEYSPACE {}".format(name))

def create_table(model, create_missing_keyspace=True):
    warnings.warn("create_table has been deprecated in favor of sync_table and will be removed in a future release", DeprecationWarning)
    sync_table(model, create_missing_keyspace)

def sync_table(model, create_missing_keyspace=True):
    """
    Inspects the model and creates / updates the corresponding table and columns.

    Note that the attributes removed from the model are not deleted on the database.
    They become effectively ignored by (will not show up on) the model.

    :param create_missing_keyspace: (Defaults to True) Flags to us that we need to create missing keyspace
        mentioned in the model automatically.
    :type create_missing_keyspace: bool
    """

    if model.__abstract__:
        raise CQLEngineException("cannot create table from abstract model")

    #construct query string
    cf_name = model.column_family_name()
    raw_cf_name = model.column_family_name(include_keyspace=False)

    ks_name = model._get_keyspace()
    #create missing keyspace
    if create_missing_keyspace:
        create_keyspace(ks_name)

    with connection_manager() as con:
        tables = con.execute(
            "SELECT columnfamily_name from system.schema_columnfamilies WHERE keyspace_name = :ks_name",
            {'ks_name': ks_name},
            ONE
        )
    tables = [x[0] for x in tables.results]

    #check for an existing column family
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
            if col.primary_key or col.partition_key: continue # we can't mess with the PK
            if col.db_field_name in field_names: continue # skip columns already defined

            # add missing column using the column def
            query = "ALTER TABLE {} add {}".format(cf_name, col.get_column_def())
            logger.debug(query)
            execute(query)

        update_compaction(model)


    #get existing index names, skip ones that already exist
    with connection_manager() as con:
        _, idx_names = con.execute(
            "SELECT index_name from system.\"IndexInfo\" WHERE table_name=:table_name",
            {'table_name': raw_cf_name},
            ONE
        )

    idx_names = [i[0] for i in idx_names]
    idx_names = filter(None, idx_names)

    indexes = [c for n,c in model._columns.items() if c.index]
    if indexes:
        for column in indexes:
            if column.db_index_name in idx_names: continue
            qs = ['CREATE INDEX index_{}_{}'.format(raw_cf_name, column.db_field_name)]
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

    #add column types
    pkeys = [] # primary keys
    ckeys = [] # clustering keys
    qtypes = [] # field types
    def add_column(col):
        s = col.get_column_def()
        if col.primary_key:
            keys = (pkeys if col.partition_key else ckeys)
            keys.append('"{}"'.format(col.db_field_name))
        qtypes.append(s)
    for name, col in model._columns.items():
        add_column(col)

    qtypes.append('PRIMARY KEY (({}){})'.format(', '.join(pkeys), ckeys and ', ' + ', '.join(ckeys) or ''))

    qs += ['({})'.format(', '.join(qtypes))]

    with_qs = ['read_repair_chance = {}'.format(model.__read_repair_chance__)]

    _order = ['"{}" {}'.format(c.db_field_name, c.clustering_order or 'ASC') for c in model._clustering_keys.values()]

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

    result = {'class':model.__compaction__}

    def setter(key, limited_to_strategy = None):
        """
        sets key in result, checking if the key is limited to either SizeTiered or Leveled
        :param key: one of the compaction options, like "bucket_high"
        :param limited_to_strategy: SizeTieredCompactionStrategy, LeveledCompactionStrategy
        :return:
        """
        mkey = "__compaction_{}__".format(key)
        tmp = getattr(model, mkey)
        if tmp and limited_to_strategy and limited_to_strategy != model.__compaction__:
            raise CQLEngineException("{} is limited to {}".format(key, limited_to_strategy))

        if tmp:
            # Explicitly cast the values to strings to be able to compare the
            # values against introspected values from Cassandra.
            result[key] = str(tmp)

    setter('tombstone_compaction_interval')
    setter('tombstone_threshold')

    setter('bucket_high', SizeTieredCompactionStrategy)
    setter('bucket_low', SizeTieredCompactionStrategy)
    setter('max_threshold', SizeTieredCompactionStrategy)
    setter('min_threshold', SizeTieredCompactionStrategy)
    setter('min_sstable_size', SizeTieredCompactionStrategy)

    setter('sstable_size_in_mb', LeveledCompactionStrategy)

    return result


def get_fields(model):
    # returns all fields that aren't part of the PK
    ks_name = model._get_keyspace()
    col_family = model.column_family_name(include_keyspace=False)

    with connection_manager() as con:
        query = "SELECT * FROM system.schema_columns \
                 WHERE keyspace_name = :ks_name AND columnfamily_name = :col_family"

        logger.debug("get_fields %s %s", ks_name, col_family)

        tmp = con.execute(query, {'ks_name': ks_name, 'col_family': col_family}, ONE)

    # Tables containing only primary keys do not appear to create
    # any entries in system.schema_columns, as only non-primary-key attributes
    # appear to be inserted into the schema_columns table
    if not tmp.results:
        return []

    column_name_positon = tmp.columns.index('column_name')
    validator_positon = tmp.columns.index('validator')
    try:
        type_position = tmp.columns.index('type')
        return [Field(x[column_name_positon], x[validator_positon]) for x in tmp.results if x[type_position] == 'regular']
    except ValueError:
        return [Field(x[column_name_positon], x[validator_positon]) for x in tmp.results]
    # convert to Field named tuples


def get_table_settings(model):
    return schema_columnfamilies.objects.consistency(ONE).get(
        keyspace_name=model._get_keyspace(),
        columnfamily_name=model.column_family_name(include_keyspace=False))


def update_compaction(model):
    """Updates the compaction options for the given model if necessary.

    :param model: The model to update.

    :return: `True`, if the compaction options were modified in Cassandra,
        `False` otherwise.
    :rtype: bool
    """
    logger.debug("Checking %s for compaction differences", model)
    row = get_table_settings(model)
    # check compaction_strategy_class
    if not model.__compaction__:
        return

    do_update = not row['compaction_strategy_class'].endswith(model.__compaction__)

    existing_options = json.loads(row['compaction_strategy_options'])
    # The min/max thresholds are stored differently in the system data dictionary
    existing_options.update({
        'min_threshold': str(row['min_compaction_threshold']),
        'max_threshold': str(row['max_compaction_threshold']),
        })

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
        return True

    return False


def delete_table(model):
    warnings.warn("delete_table has been deprecated in favor of drop_table()", DeprecationWarning)
    return drop_table(model)


def drop_table(model):

    # don't try to delete non existant tables
    ks_name = model._get_keyspace()
    with connection_manager() as con:
        _, tables = con.execute(
            "SELECT columnfamily_name from system.schema_columnfamilies WHERE keyspace_name = :ks_name",
            {'ks_name': ks_name},
            ONE
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

class ModelDefinitionException(ModelException): pass


class PolyMorphicModelException(ModelException): pass

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
            raise CQLEngineException('cannot execute queries against abstract models')
        queryset = model.__queryset__(model)

        # if this is a concrete polymorphic model, and the polymorphic
        # key is an indexed column, add a filter clause to only return
        # logical rows of the proper type
        if model._is_polymorphic and not model._is_polymorphic_base:
            name, column = model._polymorphic_column_name, model._polymorphic_column
            if column.partition_key or column.index:
                # look for existing poly types
                return queryset.filter(**{name: model.__polymorphic_key__})

        return queryset

    def __call__(self, *args, **kwargs):
        """
        Just a hint to IDEs that it's ok to call this

        :rtype: ModelQuerySet
        """
        raise NotImplementedError


class TTLDescriptor(object):
    """
    returns a query set descriptor
    """
    def __get__(self, instance, model):
        if instance:
            #instance = copy.deepcopy(instance)
            # instance method
            def ttl_setter(ts):
                instance._ttl = ts
                return instance
            return ttl_setter

        qs = model.__queryset__(model)

        def ttl_setter(ts):
            qs._ttl = ts
            return qs

        return ttl_setter

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

class TimestampDescriptor(object):
    """
    returns a query set descriptor with a timestamp specified
    """
    def __get__(self, instance, model):
        if instance:
            # instance method
            def timestamp_setter(ts):
                instance._timestamp = ts
                return instance
            return timestamp_setter

        return model.objects.timestamp


    def __call__(self, *args, **kwargs):
        raise NotImplementedError

class ConsistencyDescriptor(object):
    """
    returns a query set descriptor if called on Class, instance if it was an instance call
    """
    def __get__(self, instance, model):
        if instance:
            #instance = copy.deepcopy(instance)
            def consistency_setter(consistency):
                instance.__consistency__ = consistency
                return instance
            return consistency_setter

        qs = model.__queryset__(model)

        def consistency_setter(consistency):
            qs._consistency = consistency
            return qs

        return consistency_setter

    def __call__(self, *args, **kwargs):
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

    def __unicode__(self):
        return self.column.db_field_name

    def _get_column(self):
        """ :rtype: ColumnQueryEvaluator """
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
        try:
            return instance._values[self.column.column_name].getval()
        except AttributeError as e:
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
                raise AttributeError('cannot delete {} columns'.format(self.column.column_name))


class BaseModel(object):
    """
    The base model class, don't inherit from this, inherit from Model, defined below
    """

    class DoesNotExist(_DoesNotExist): pass

    class MultipleObjectsReturned(_MultipleObjectsReturned): pass

    objects = QuerySetDescriptor()
    ttl = TTLDescriptor()
    consistency = ConsistencyDescriptor()

    # custom timestamps, see USING TIMESTAMP X
    timestamp = TimestampDescriptor()

    # _len is lazily created by __len__

    # table names will be generated automatically from it's model
    # however, you can also define them manually here
    __table_name__ = None

    # the keyspace for this model
    __keyspace__ = None

    # polymorphism options
    __polymorphic_key__ = None

    # compaction options
    __compaction__ = None
    __compaction_tombstone_compaction_interval__ = None
    __compaction_tombstone_threshold__ = None

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

    #__ttl__ = None # this doesn't seem to be used
    __consistency__ = None # can be set per query

    __read_repair_chance__ = 0.1


    _timestamp = None # optional timestamp to include with the operation (USING TIMESTAMP)

    def __init__(self, **values):
        self._values = {}
        self._ttl = None
        self._timestamp = None

        for name, column in self._columns.items():
            value =  values.get(name, None)
            if value is not None or isinstance(column, columns.BaseContainerColumn):
                value = column.to_python(value)
            value_mngr = column.value_manager(self, column, value)
            self._values[name] = value_mngr

        # a flag set by the deserializer to indicate
        # that update should be used when persisting changes
        self._is_persisted = False
        self._batch = None


    def __repr__(self):
        """
        Pretty printing of models by their primary key
        """
        return '{} <{}>'.format(self.__class__.__name__,
                                ', '.join(('{}={}'.format(k, getattr(self, k)) for k,v in self._primary_keys.iteritems()))
                                )



    @classmethod
    def _discover_polymorphic_submodels(cls):
        if not cls._is_polymorphic_base:
            raise ModelException('_discover_polymorphic_submodels can only be called on polymorphic base classes')
        def _discover(klass):
            if not klass._is_polymorphic_base and klass.__polymorphic_key__ is not None:
                cls._polymorphic_map[klass.__polymorphic_key__] = klass
            for subklass in klass.__subclasses__():
                _discover(subklass)
        _discover(cls)

    @classmethod
    def _get_model_by_polymorphic_key(cls, key):
        if not cls._is_polymorphic_base:
            raise ModelException('_get_model_by_polymorphic_key can only be called on polymorphic base classes')
        return cls._polymorphic_map.get(key)

    @classmethod
    def _construct_instance(cls, names, values):
        """
        method used to construct instances from query results
        this is where polymorphic deserialization occurs
        """
        field_dict = dict((cls._db_map.get(k, k), v) for k, v in zip(names, values))
        if cls._is_polymorphic:
            poly_key = field_dict.get(cls._polymorphic_column_name)

            if poly_key is None:
                raise PolyMorphicModelException('polymorphic key was not found in values')

            poly_base = cls if cls._is_polymorphic_base else cls._polymorphic_base

            klass = poly_base._get_model_by_polymorphic_key(poly_key)
            if klass is None:
                poly_base._discover_polymorphic_submodels()
                klass = poly_base._get_model_by_polymorphic_key(poly_key)
                if klass is None:
                    raise PolyMorphicModelException(
                        'unrecognized polymorphic key {} for class {}'.format(poly_key, poly_base.__name__)
                    )

            if not issubclass(klass, cls):
                raise PolyMorphicModelException(
                    '{} is not a subclass of {}'.format(klass.__name__, cls.__name__)
                )

            field_dict = {k: v for k, v in field_dict.items() if k in klass._columns.keys()}

        else:
            klass = cls

        instance = klass(**field_dict)
        instance._is_persisted = True
        return instance

    def _can_update(self):
        """
        Called by the save function to check if this should be
        persisted with update or insert

        :return:
        """
        if not self._is_persisted: return False
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
        other_keys = set(other._columns.keys())
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
            # get polymorphic base table names if model is polymorphic
            if cls._is_polymorphic and not cls._is_polymorphic_base:
                return cls._polymorphic_base.column_family_name(include_keyspace=include_keyspace)

            camelcase = re.compile(r'([a-z])([A-Z])')
            ccase = lambda s: camelcase.sub(lambda v: '{}_{}'.format(v.group(1), v.group(2).lower()), s)

            cf_name += ccase(cls.__name__)
            #trim to less than 48 characters or cassandra will complain
            cf_name = cf_name[-48:]
            cf_name = cf_name.lower()
            cf_name = re.sub(r'^_+', '', cf_name)
        if not include_keyspace: return cf_name
        return '{}.{}'.format(cls._get_keyspace(), cf_name)

    def validate(self):
        """ Cleans and validates the field values """
        for name, col in self._columns.items():
            val = col.validate(getattr(self, name))
            setattr(self, name, val)

    ### Let an instance be used like a dict of its columns keys/values

    def __iter__(self):
        """ Iterate over column ids. """
        for column_id in self._columns.keys():
            yield column_id

    def __getitem__(self, key):
        """ Returns column's value. """
        if not isinstance(key, basestring):
            raise TypeError
        if key not in self._columns.keys():
            raise KeyError
        return getattr(self, key)

    def __setitem__(self, key, val):
        """ Sets a column's value. """
        if not isinstance(key, basestring):
            raise TypeError
        if key not in self._columns.keys():
            raise KeyError
        return setattr(self, key, val)

    def __len__(self):
        """ Returns the number of columns defined on that model. """
        try:
            return self._len
        except:
            self._len = len(self._columns.keys())
            return self._len

    def keys(self):
        """ Returns list of column's IDs. """
        return [k for k in self]

    def values(self):
        """ Returns list of column's values. """
        return [self[k] for k in self]

    def items(self):
        """ Returns a list of columns's IDs/values. """
        return [(k, self[k]) for k in self]

    def _as_dict(self):
        """ Returns a map of column names to cleaned values """
        values = self._dynamic_columns or {}
        for name, col in self._columns.items():
            values[name] = col.to_database(getattr(self, name, None))
        return values

    @classmethod
    def create(cls, **kwargs):
        extra_columns = set(kwargs.keys()) - set(cls._columns.keys())
        if extra_columns:
            raise ValidationError("Incorrect columns passed: {}".format(extra_columns))
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
        # handle polymorphic models
        if self._is_polymorphic:
            if self._is_polymorphic_base:
                raise PolyMorphicModelException('cannot save polymorphic base model')
            else:
                setattr(self, self._polymorphic_column_name, self.__polymorphic_key__)

        is_new = self.pk is None
        self.validate()
        self.__dmlquery__(self.__class__, self,
                          batch=self._batch,
                          ttl=self._ttl,
                          timestamp=self._timestamp,
                          consistency=self.__consistency__).save()

        #reset the value managers
        for v in self._values.values():
            v.reset_previous_value()
        self._is_persisted = True

        self._ttl = None
        self._timestamp = None

        return self

    def update(self, **values):
        for k, v in values.items():
            col = self._columns.get(k)

            # check for nonexistant columns
            if col is None:
                raise ValidationError("{}.{} has no column named: {}".format(self.__module__, self.__class__.__name__, k))

            # check for primary key update attempts
            if col.is_primary_key:
                raise ValidationError("Cannot apply update to primary key '{}' for {}.{}".format(k, self.__module__, self.__class__.__name__))

            setattr(self, k, v)

        # handle polymorphic models
        if self._is_polymorphic:
            if self._is_polymorphic_base:
                raise PolyMorphicModelException('cannot update polymorphic base model')
            else:
                setattr(self, self._polymorphic_column_name, self.__polymorphic_key__)

        self.validate()
        self.__dmlquery__(self.__class__, self,
                          batch=self._batch,
                          ttl=self._ttl,
                          timestamp=self._timestamp,
                          consistency=self.__consistency__).update()

        #reset the value managers
        for v in self._values.values():
            v.reset_previous_value()
        self._is_persisted = True

        self._ttl = None
        self._timestamp = None

        return self

    def delete(self):
        """ Deletes this instance """
        self.__dmlquery__(self.__class__, self, batch=self._batch, timestamp=self._timestamp, consistency=self.__consistency__).delete()

    def get_changed_columns(self):
        """ returns a list of the columns that have been updated since instantiation or save """
        return [k for k,v in self._values.items() if v.changed]

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
        #move column definitions into columns dict
        #and set default column names
        column_dict = OrderedDict()
        primary_keys = OrderedDict()
        pk_name = None

        #get inherited properties
        inherited_columns = OrderedDict()
        for base in bases:
            for k,v in getattr(base, '_defined_columns', {}).items():
                inherited_columns.setdefault(k,v)

        #short circuit __abstract__ inheritance
        is_abstract = attrs['__abstract__'] = attrs.get('__abstract__', False)

        #short circuit __polymorphic_key__ inheritance
        attrs['__polymorphic_key__'] = attrs.get('__polymorphic_key__', None)

        def _transform_column(col_name, col_obj):
            column_dict[col_name] = col_obj
            if col_obj.primary_key:
                primary_keys[col_name] = col_obj
            col_obj.set_column_name(col_name)
            #set properties
            attrs[col_name] = ColumnDescriptor(col_obj)

        column_definitions = [(k,v) for k,v in attrs.items() if isinstance(v, columns.Column)]
        column_definitions = sorted(column_definitions, lambda x,y: cmp(x[1].position, y[1].position))

        is_polymorphic_base = any([c[1].polymorphic_key for c in column_definitions])

        column_definitions = inherited_columns.items() + column_definitions

        polymorphic_columns = [c for c in column_definitions if c[1].polymorphic_key]
        is_polymorphic = len(polymorphic_columns) > 0
        if len(polymorphic_columns) > 1:
            raise ModelDefinitionException('only one polymorphic_key can be defined in a model, {} found'.format(len(polymorphic_columns)))

        polymorphic_column_name, polymorphic_column = polymorphic_columns[0] if polymorphic_columns else (None, None)

        if isinstance(polymorphic_column, (columns.BaseContainerColumn, columns.Counter)):
            raise ModelDefinitionException('counter and container columns cannot be used for polymorphic keys')

        # find polymorphic base class
        polymorphic_base = None
        if is_polymorphic and not is_polymorphic_base:
            def _get_polymorphic_base(bases):
                for base in bases:
                    if getattr(base, '_is_polymorphic_base', False):
                        return base
                    klass = _get_polymorphic_base(base.__bases__)
                    if klass:
                        return klass
            polymorphic_base = _get_polymorphic_base(bases)

        defined_columns = OrderedDict(column_definitions)

        # check for primary key
        if not is_abstract and not any([v.primary_key for k,v in column_definitions]):
            raise ModelDefinitionException("At least 1 primary key is required.")

        counter_columns = [c for c in defined_columns.values() if isinstance(c, columns.Counter)]
        data_columns = [c for c in defined_columns.values() if not c.primary_key and not isinstance(c, columns.Counter)]
        if counter_columns and data_columns:
            raise ModelDefinitionException('counter models may not have data columns')

        has_partition_keys = any(v.partition_key for (k, v) in column_definitions)

        #TODO: check that the defined columns don't conflict with any of the Model API's existing attributes/methods
        #transform column definitions
        for k, v in column_definitions:
            # counter column primary keys are not allowed
            if (v.primary_key or v.partition_key) and isinstance(v, (columns.Counter, columns.BaseContainerColumn)):
                raise ModelDefinitionException('counter columns and container columns cannot be used as primary keys')

            # this will mark the first primary key column as a partition
            # key, if one hasn't been set already
            if not has_partition_keys and v.primary_key:
                v.partition_key = True
                has_partition_keys = True
            _transform_column(k,v)

        partition_keys = OrderedDict(k for k in primary_keys.items() if k[1].partition_key)
        clustering_keys = OrderedDict(k for k in primary_keys.items() if not k[1].partition_key)

        #setup partition key shortcut
        if len(partition_keys) == 0:
            if not is_abstract:
                raise ModelException("at least one partition key must be defined")
        if len(partition_keys) == 1:
            pk_name = partition_keys.keys()[0]
            attrs['pk'] = attrs[pk_name]
        else:
            # composite partition key case, get/set a tuple of values
            _get = lambda self: tuple(self._values[c].getval() for c in partition_keys.keys())
            _set = lambda self, val: tuple(self._values[c].setval(v) for (c, v) in zip(partition_keys.keys(), val))
            attrs['pk'] = property(_get, _set)

        # some validation
        col_names = set()
        for v in column_dict.values():
            # check for duplicate column names
            if v.db_field_name in col_names:
                raise ModelException("{} defines the column {} more than once".format(name, v.db_field_name))
            if v.clustering_order and not (v.primary_key and not v.partition_key):
                raise ModelException("clustering_order may be specified only for clustering primary keys")
            if v.clustering_order and v.clustering_order.lower() not in ('asc', 'desc'):
                raise ModelException("invalid clustering order {} for column {}".format(repr(v.clustering_order), v.db_field_name))
            col_names.add(v.db_field_name)

        #create db_name -> model name map for loading
        db_map = {}
        for field_name, col in column_dict.items():
            db_map[col.db_field_name] = field_name

        #add management members to the class
        attrs['_columns'] = column_dict
        attrs['_primary_keys'] = primary_keys
        attrs['_defined_columns'] = defined_columns
        attrs['_db_map'] = db_map
        attrs['_pk_name'] = pk_name
        attrs['_dynamic_columns'] = {}

        attrs['_partition_keys'] = partition_keys
        attrs['_clustering_keys'] = clustering_keys
        attrs['_has_counter'] = len(counter_columns) > 0

        # add polymorphic management attributes
        attrs['_is_polymorphic_base'] = is_polymorphic_base
        attrs['_is_polymorphic'] = is_polymorphic
        attrs['_polymorphic_base'] = polymorphic_base
        attrs['_polymorphic_column'] = polymorphic_column
        attrs['_polymorphic_column_name'] = polymorphic_column_name
        attrs['_polymorphic_map'] = {} if is_polymorphic_base else None

        #setup class exceptions
        DoesNotExistBase = None
        for base in bases:
            DoesNotExistBase = getattr(base, 'DoesNotExist', None)
            if DoesNotExistBase is not None: break
        DoesNotExistBase = DoesNotExistBase or attrs.pop('DoesNotExist', BaseModel.DoesNotExist)
        attrs['DoesNotExist'] = type('DoesNotExist', (DoesNotExistBase,), {})

        MultipleObjectsReturnedBase = None
        for base in bases:
            MultipleObjectsReturnedBase = getattr(base, 'MultipleObjectsReturned', None)
            if MultipleObjectsReturnedBase is not None: break
        MultipleObjectsReturnedBase = DoesNotExistBase or attrs.pop('MultipleObjectsReturned', BaseModel.MultipleObjectsReturned)
        attrs['MultipleObjectsReturned'] = type('MultipleObjectsReturned', (MultipleObjectsReturnedBase,), {})

        #create the class and add a QuerySet to it
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
            raise CQLEngineException('cannot execute queries against abstract models')
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

    def __unicode__(self):
        return self.name

    def _get_column(self):
        """ :rtype: NamedColumn """
        return self

    @property
    def db_field_name(self):
        return self.name

    @property
    def cql(self):
        return self.get_cql()

    def get_cql(self):
        return '"{}"'.format(self.name)

    def to_database(self, val):
        return val


class NamedTable(object):
    """
    A Table that is not coupled to a model class
    """

    __abstract__ = False

    objects = QuerySetDescriptor()

    class DoesNotExist(_DoesNotExist): pass
    class MultipleObjectsReturned(_MultipleObjectsReturned): pass

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
__FILENAME__ = operators
class QueryOperatorException(Exception): pass


class BaseQueryOperator(object):
    # The symbol that identifies this operator in kwargs
    # ie: colname__<symbol>
    symbol = None

    # The comparator symbol this operator uses in cql
    cql_symbol = None

    def __unicode__(self):
        if self.cql_symbol is None:
            raise QueryOperatorException("cql symbol is None")
        return self.cql_symbol

    def __str__(self):
        return unicode(self).encode('utf-8')

    @classmethod
    def get_operator(cls, symbol):
        if cls == BaseQueryOperator:
            raise QueryOperatorException("get_operator can only be called from a BaseQueryOperator subclass")
        if not hasattr(cls, 'opmap'):
            cls.opmap = {}
            def _recurse(klass):
                if klass.symbol:
                    cls.opmap[klass.symbol.upper()] = klass
                for subklass in klass.__subclasses__():
                    _recurse(subklass)
                pass
            _recurse(cls)
        try:
            return cls.opmap[symbol.upper()]
        except KeyError:
            raise QueryOperatorException("{} doesn't map to a QueryOperator".format(symbol))


class BaseWhereOperator(BaseQueryOperator):
    """ base operator used for where clauses """


class EqualsOperator(BaseWhereOperator):
    symbol = 'EQ'
    cql_symbol = '='


class InOperator(EqualsOperator):
    symbol = 'IN'
    cql_symbol = 'IN'


class GreaterThanOperator(BaseWhereOperator):
    symbol = "GT"
    cql_symbol = '>'


class GreaterThanOrEqualOperator(BaseWhereOperator):
    symbol = "GTE"
    cql_symbol = '>='


class LessThanOperator(BaseWhereOperator):
    symbol = "LT"
    cql_symbol = '<'


class LessThanOrEqualOperator(BaseWhereOperator):
    symbol = "LTE"
    cql_symbol = '<='


class BaseAssignmentOperator(BaseQueryOperator):
    """ base operator used for insert and delete statements """


class AssignmentOperator(BaseAssignmentOperator):
    cql_symbol = "="


class AddSymbol(BaseAssignmentOperator):
    cql_symbol = "+"
########NEW FILE########
__FILENAME__ = query
import copy
import time
from datetime import datetime, timedelta
from cqlengine import BaseContainerColumn, Map, columns
from cqlengine.columns import Counter, List, Set

from cqlengine.connection import execute, RowResult

from cqlengine.exceptions import CQLEngineException, ValidationError
from cqlengine.functions import Token, BaseQueryFunction, QueryValue

#CQL 3 reference:
#http://www.datastax.com/docs/1.1/references/cql/index
from cqlengine.operators import InOperator, EqualsOperator, GreaterThanOperator, GreaterThanOrEqualOperator
from cqlengine.operators import LessThanOperator, LessThanOrEqualOperator, BaseWhereOperator
from cqlengine.statements import WhereClause, SelectStatement, DeleteStatement, UpdateStatement, AssignmentClause, InsertStatement, BaseCQLStatement, MapUpdateClause, MapDeleteClause, ListUpdateClause, SetUpdateClause, CounterUpdateClause


class QueryException(CQLEngineException): pass
class DoesNotExist(QueryException): pass
class MultipleObjectsReturned(QueryException): pass


class AbstractQueryableColumn(object):
    """
    exposes cql query operators through pythons
    builtin comparator symbols
    """

    def _get_column(self):
        raise NotImplementedError

    def __unicode__(self):
        raise NotImplementedError

    def __str__(self):
        return str(unicode(self))

    def _to_database(self, val):
        if isinstance(val, QueryValue):
            return val
        else:
            return self._get_column().to_database(val)

    def in_(self, item):
        """
        Returns an in operator

        used where you'd typically want to use python's `in` operator
        """
        return WhereClause(unicode(self), InOperator(), item)

    def __eq__(self, other):
        return WhereClause(unicode(self), EqualsOperator(), self._to_database(other))

    def __gt__(self, other):
        return WhereClause(unicode(self), GreaterThanOperator(), self._to_database(other))

    def __ge__(self, other):
        return WhereClause(unicode(self), GreaterThanOrEqualOperator(), self._to_database(other))

    def __lt__(self, other):
        return WhereClause(unicode(self), LessThanOperator(), self._to_database(other))

    def __le__(self, other):
        return WhereClause(unicode(self), LessThanOrEqualOperator(), self._to_database(other))


class BatchType(object):
    Unlogged    = 'UNLOGGED'
    Counter     = 'COUNTER'


class BatchQuery(object):
    """
    Handles the batching of queries

    http://www.datastax.com/docs/1.2/cql_cli/cql/BATCH
    """
    _consistency = None

    def __init__(self, batch_type=None, timestamp=None, consistency=None, execute_on_exception=False):
        """
        :param batch_type: (optional) One of batch type values available through BatchType enum
        :type batch_type: str or None
        :param timestamp: (optional) A datetime or timedelta object with desired timestamp to be applied
            to the batch transaction.
        :type timestamp: datetime or timedelta or None
        :param consistency: (optional) One of consistency values ("ANY", "ONE", "QUORUM" etc)
        :type consistency: str or None
        :param execute_on_exception: (Defaults to False) Indicates that when the BatchQuery instance is used
            as a context manager the queries accumulated within the context must be executed despite
            encountering an error within the context. By default, any exception raised from within
            the context scope will cause the batched queries not to be executed.
        :type execute_on_exception: bool
        :param callbacks: A list of functions to be executed after the batch executes. Note, that if the batch
            does not execute, the callbacks are not executed. This, thus, effectively is a list of "on success"
            callback handlers. If defined, must be a collection of callables.
        :type callbacks: list or set or tuple
        """
        self.queries = []
        self.batch_type = batch_type
        if timestamp is not None and not isinstance(timestamp, (datetime, timedelta)):
            raise CQLEngineException('timestamp object must be an instance of datetime')
        self.timestamp = timestamp
        self._consistency = consistency
        self._execute_on_exception = execute_on_exception
        self._callbacks = []

    def add_query(self, query):
        if not isinstance(query, BaseCQLStatement):
            raise CQLEngineException('only BaseCQLStatements can be added to a batch query')
        self.queries.append(query)

    def consistency(self, consistency):
        self._consistency = consistency

    def _execute_callbacks(self):
        for callback, args, kwargs in self._callbacks:
            callback(*args, **kwargs)

        # trying to clear up the ref counts for objects mentioned in the set
        del self._callbacks

    def add_callback(self, fn, *args, **kwargs):
        """Add a function and arguments to be passed to it to be executed after the batch executes.

        A batch can support multiple callbacks.

        Note, that if the batch does not execute, the callbacks are not executed.
        A callback, thus, is an "on batch success" handler.

        :param fn: Callable object
        :type fn: callable
        :param *args: Positional arguments to be passed to the callback at the time of execution
        :param **kwargs: Named arguments to be passed to the callback at the time of execution
        """
        if not callable(fn):
            raise ValueError("Value for argument 'fn' is {} and is not a callable object.".format(type(fn)))
        self._callbacks.append((fn, args, kwargs))

    def execute(self):
        if len(self.queries) == 0:
            # Empty batch is a no-op
            # except for callbacks
            self._execute_callbacks()
            return

        opener = 'BEGIN ' + (self.batch_type + ' ' if self.batch_type else '') + ' BATCH'
        if self.timestamp:

            if isinstance(self.timestamp, (int, long)):
                ts = self.timestamp
            elif isinstance(self.timestamp, (datetime, timedelta)):
                ts = self.timestamp
                if isinstance(self.timestamp, timedelta):
                    ts += datetime.now()  # Apply timedelta
                ts = long(time.mktime(ts.timetuple()) * 1e+6 + ts.microsecond)
            else:
                raise ValueError("Batch expects a long, a timedelta, or a datetime")

            opener += ' USING TIMESTAMP {}'.format(ts)

        query_list = [opener]
        parameters = {}
        ctx_counter = 0
        for query in self.queries:
            query.update_context_id(ctx_counter)
            ctx = query.get_context()
            ctx_counter += len(ctx)
            query_list.append('  ' + str(query))
            parameters.update(ctx)

        query_list.append('APPLY BATCH;')

        execute('\n'.join(query_list), parameters, self._consistency)

        self.queries = []
        self._execute_callbacks()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        #don't execute if there was an exception by default
        if exc_type is not None and not self._execute_on_exception: return
        self.execute()


class AbstractQuerySet(object):

    def __init__(self, model):
        super(AbstractQuerySet, self).__init__()
        self.model = model

        #Where clause filters
        self._where = []

        #ordering arguments
        self._order = []

        self._allow_filtering = False

        #CQL has a default limit of 10000, it's defined here
        #because explicit is better than implicit
        self._limit = 10000

        #see the defer and only methods
        self._defer_fields = []
        self._only_fields = []

        self._values_list = False
        self._flat_values_list = False

        #results cache
        self._con = None
        self._cur = None
        self._result_cache = None
        self._result_idx = None

        self._batch = None
        self._ttl = None
        self._consistency = None
        self._timestamp = None

    @property
    def column_family_name(self):
        return self.model.column_family_name()

    def _execute(self, q):
        if self._batch:
            return self._batch.add_query(q)
        else:
            return execute(q, consistency_level=self._consistency)

    def __unicode__(self):
        return unicode(self._select_query())

    def __str__(self):
        return str(self.__unicode__())

    def __call__(self, *args, **kwargs):
        return self.filter(*args, **kwargs)

    def __deepcopy__(self, memo):
        clone = self.__class__(self.model)
        for k, v in self.__dict__.items():
            if k in ['_con', '_cur', '_result_cache', '_result_idx']: # don't clone these
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

    def _select_fields(self):
        """ returns the fields to select """
        return []

    def _validate_select_where(self):
        """ put select query validation here """

    def _select_query(self):
        """
        Returns a select clause based on the given filter args
        """
        if self._where:
            self._validate_select_where()
        return SelectStatement(
            self.column_family_name,
            fields=self._select_fields(),
            where=self._where,
            order_by=self._order,
            limit=self._limit,
            allow_filtering=self._allow_filtering
        )

    #----Reads------

    def _execute_query(self):
        if self._batch:
            raise CQLEngineException("Only inserts, updates, and deletes are available in batch mode")
        if self._result_cache is None:
            columns, self._result_cache = self._execute(self._select_query())
            self._construct_result = self._get_result_constructor(columns)

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
                self._result_cache[self._result_idx] = self._construct_result(self._result_cache[self._result_idx])

            #return the connection to the connection pool if we have all objects
            if self._result_cache and self._result_idx == (len(self._result_cache) - 1):
                self._con = None
                self._cur = None

    def __iter__(self):
        self._execute_query()

        for idx in range(len(self._result_cache)):
            instance = self._result_cache[idx]
            if isinstance(instance, RowResult):
                self._fill_result_cache_to_idx(idx)
            yield self._result_cache[idx]

    def __getitem__(self, s):
        self._execute_query()

        num_results = len(self._result_cache)

        if isinstance(s, slice):
            #calculate the amount of results that need to be loaded
            end = num_results if s.step is None else s.step
            if end < 0:
                end += num_results
            else:
                end -= 1
            self._fill_result_cache_to_idx(end)
            return self._result_cache[s.start:s.stop:s.step]
        else:
            #return the object at this index
            s = long(s)

            #handle negative indexing
            if s < 0: s += num_results

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
            raise CQLEngineException('batch_obj must be a BatchQuery instance or None')
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

    def consistency(self, consistency):
        clone = copy.deepcopy(self)
        clone._consistency = consistency
        return clone

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
        #add arguments to the where clause filters
        clone = copy.deepcopy(self)
        for operator in args:
            if not isinstance(operator, WhereClause):
                raise QueryException('{} is not a valid query operator'.format(operator))
            clone._where.append(operator)

        for arg, val in kwargs.items():
            col_name, col_op = self._parse_filter_arg(arg)
            quote_field = True
            #resolve column and operator
            try:
                column = self.model._get_column(col_name)
            except KeyError:
                if col_name == 'pk__token':
                    if not isinstance(val, Token):
                        raise QueryException("Virtual column 'pk__token' may only be compared to Token() values")
                    column = columns._PartitionKeysToken(self.model)
                    quote_field = False
                else:
                    raise QueryException("Can't resolve column name: '{}'".format(col_name))

            if isinstance(val, Token):
                if col_name != 'pk__token':
                    raise QueryException("Token() values may only be compared to the 'pk__token' virtual column")
                partition_columns = column.partition_columns
                if len(partition_columns) != len(val.value):
                    raise QueryException(
                        'Token() received {} arguments but model has {} partition keys'.format(
                            len(val.value), len(partition_columns)))
                val.set_columns(partition_columns)

            #get query operator, or use equals if not supplied
            operator_class = BaseWhereOperator.get_operator(col_op or 'EQ')
            operator = operator_class()

            if isinstance(operator, InOperator):
                if not isinstance(val, (list, tuple)):
                    raise QueryException('IN queries must use a list/tuple value')
                query_val = [column.to_database(v) for v in val]
            elif isinstance(val, BaseQueryFunction):
                query_val = val
            else:
                query_val = column.to_database(val)

            clone._where.append(WhereClause(column.db_field_name, operator, query_val, quote_field=quote_field))

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
            conditions.append('"{}" {}'.format(*self._get_ordering_condition(colname)))

        clone = copy.deepcopy(self)
        clone._order.extend(conditions)
        return clone

    def count(self):
        """ Returns the number of rows matched by this query """
        if self._batch:
            raise CQLEngineException("Only inserts, updates, and deletes are available in batch mode")

        if self._result_cache is None:
            query = self._select_query()
            query.count = True
            _, result = self._execute(query)
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
            raise QueryException("QuerySet alread has only or defer fields defined")

        #check for strange fields
        missing_fields = [f for f in fields if f not in self.model._columns.keys()]
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
        return self.model(**kwargs).batch(self._batch).ttl(self._ttl).\
            consistency(self._consistency).\
            timestamp(self._timestamp).save()

    def delete(self):
        """
        Deletes the contents of a query
        """
        #validate where clause
        partition_key = self.model._primary_keys.values()[0]
        if not any([c.field == partition_key.column_name for c in self._where]):
            raise QueryException("The partition key must be defined on delete queries")

        dq = DeleteStatement(
            self.column_family_name,
            where=self._where,
            timestamp=self._timestamp
        )
        self._execute(dq)

    def __eq__(self, q):
        if len(self._where) == len(q._where):
            return all([w in q._where for w in self._where])
        return False

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

    def _get_result_constructor(self, names):
        """
        Returns a function that will be used to instantiate query results
        """
        def _construct_instance(values):
            return ResultObject(zip(names, values))
        return _construct_instance


class ModelQuerySet(AbstractQuerySet):
    """

    """
    def _validate_select_where(self):
        """ Checks that a filterset will not create invalid select statement """
        #check that there's either a = or IN relationship with a primary key or indexed field
        equal_ops = [self.model._columns.get(w.field) for w in self._where if isinstance(w.operator, EqualsOperator)]
        token_comparison = any([w for w in self._where if isinstance(w.value, Token)])
        if not any([w.primary_key or w.index for w in equal_ops]) and not token_comparison:
            raise QueryException('Where clauses require either a "=" or "IN" comparison with either a primary key or indexed field')

        if not self._allow_filtering:
            #if the query is not on an indexed field
            if not any([w.index for w in equal_ops]):
                if not any([w.partition_key for w in equal_ops]) and not token_comparison:
                    raise QueryException('Filtering on a clustering key without a partition key is not allowed unless allow_filtering() is called on the querset')

    def _select_fields(self):
        if self._defer_fields or self._only_fields:
            fields = self.model._columns.keys()
            if self._defer_fields:
                fields = [f for f in fields if f not in self._defer_fields]
            elif self._only_fields:
                fields = self._only_fields
            return [self.model._columns[f].db_field_name for f in fields]
        return super(ModelQuerySet, self)._select_fields()

    def _get_result_constructor(self, names):
        """ Returns a function that will be used to instantiate query results """
        if not self._values_list:
            return lambda values: self.model._construct_instance(names, values)
        else:
            columns = [self.model._columns[n] for n in names]
            if self._flat_values_list:
                return lambda values: columns[0].to_python(values[0])
            else:
                return lambda values: map(lambda (c, v): c.to_python(v), zip(columns, values))

    def _get_ordering_condition(self, colname):
        colname, order_type = super(ModelQuerySet, self)._get_ordering_condition(colname)

        column = self.model._columns.get(colname)
        if column is None:
            raise QueryException("Can't resolve the column name: '{}'".format(colname))

        #validate the column selection
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
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        clone = self.only(fields)
        clone._values_list = True
        clone._flat_values_list = flat
        return clone

    def ttl(self, ttl):
        clone = copy.deepcopy(self)
        clone._ttl = ttl
        return clone

    def timestamp(self, timestamp):
        clone = copy.deepcopy(self)
        clone._timestamp = timestamp
        return clone

    def update(self, **values):
        """ Updates the rows in this queryset """
        if not values:
            return

        nulled_columns = set()
        us = UpdateStatement(self.column_family_name, where=self._where, ttl=self._ttl, timestamp=self._timestamp)
        for name, val in values.items():
            col_name, col_op = self._parse_filter_arg(name)
            col = self.model._columns.get(col_name)
            # check for nonexistant columns
            if col is None:
                raise ValidationError("{}.{} has no column named: {}".format(self.__module__, self.model.__name__, col_name))
            # check for primary key update attempts
            if col.is_primary_key:
                raise ValidationError("Cannot apply update to primary key '{}' for {}.{}".format(col_name, self.__module__, self.model.__name__))

            val = col.validate(val)
            if val is None:
                nulled_columns.add(col_name)
                continue

            # add the update statements
            if isinstance(col, Counter):
                # TODO: implement counter updates
                raise NotImplementedError
            elif isinstance(col, (List, Set, Map)):
                if isinstance(col, List):
                    klass = ListUpdateClause
                elif isinstance(col, Set):
                    klass = SetUpdateClause
                elif isinstance(col, Map):
                    klass = MapUpdateClause
                else:
                    raise RuntimeError
                us.add_assignment_clause(klass(col_name, col.to_database(val), operation=col_op))
            else:
                us.add_assignment_clause(AssignmentClause(
                    col_name, col.to_database(val)))

        if us.assignments:
            self._execute(us)

        if nulled_columns:
            ds = DeleteStatement(self.column_family_name, fields=nulled_columns, where=self._where)
            self._execute(ds)


class DMLQuery(object):
    """
    A query object used for queries performing inserts, updates, or deletes

    this is usually instantiated by the model instance to be modified

    unlike the read query object, this is mutable
    """
    _ttl = None
    _consistency = None
    _timestamp = None

    def __init__(self, model, instance=None, batch=None, ttl=None, consistency=None, timestamp=None):
        self.model = model
        self.column_family_name = self.model.column_family_name()
        self.instance = instance
        self._batch = batch
        self._ttl = ttl
        self._consistency = consistency
        self._timestamp = timestamp

    def _execute(self, q):
        if self._batch:
            return self._batch.add_query(q)
        else:
            return execute(q, consistency_level=self._consistency)

    def batch(self, batch_obj):
        if batch_obj is not None and not isinstance(batch_obj, BatchQuery):
            raise CQLEngineException('batch_obj must be a BatchQuery instance or None')
        self._batch = batch_obj
        return self

    def _delete_null_columns(self):
        """
        executes a delete query to remove columns that have changed to null
        """
        ds = DeleteStatement(self.column_family_name)
        deleted_fields = False
        for _, v in self.instance._values.items():
            col = v.column
            if v.deleted:
                ds.add_field(col.db_field_name)
                deleted_fields = True
            elif isinstance(col, Map):
                uc = MapDeleteClause(col.db_field_name, v.value, v.previous_value)
                if uc.get_context_size() > 0:
                    ds.add_field(uc)
                    deleted_fields = True

        if deleted_fields:
            for name, col in self.model._primary_keys.items():
                ds.add_where_clause(WhereClause(
                    col.db_field_name,
                    EqualsOperator(),
                    col.to_database(getattr(self.instance, name))
                ))
            self._execute(ds)

    def update(self):
        """
        updates a row.
        This is a blind update call.
        All validation and cleaning needs to happen
        prior to calling this.
        """
        if self.instance is None:
            raise CQLEngineException("DML Query intance attribute is None")
        assert type(self.instance) == self.model

        statement = UpdateStatement(self.column_family_name, ttl=self._ttl, timestamp=self._timestamp)
        #get defined fields and their column names
        for name, col in self.model._columns.items():
            if not col.is_primary_key:
                val = getattr(self.instance, name, None)
                val_mgr = self.instance._values[name]

                # don't update something that is null
                if val is None:
                    continue

                # don't update something if it hasn't changed
                if not val_mgr.changed and not isinstance(col, Counter):
                    continue

                if isinstance(col, (BaseContainerColumn, Counter)):
                    # get appropriate clause
                    if isinstance(col, List): klass = ListUpdateClause
                    elif isinstance(col, Map): klass = MapUpdateClause
                    elif isinstance(col, Set): klass = SetUpdateClause
                    elif isinstance(col, Counter): klass = CounterUpdateClause
                    else: raise RuntimeError

                    # do the stuff
                    clause = klass(col.db_field_name, val,
                            previous=val_mgr.previous_value, column=col)
                    if clause.get_context_size() > 0:
                        statement.add_assignment_clause(clause)
                else:
                    statement.add_assignment_clause(AssignmentClause(
                        col.db_field_name,
                        col.to_database(val)
                    ))

        if statement.get_context_size() > 0 or self.instance._has_counter:
            for name, col in self.model._primary_keys.items():
                statement.add_where_clause(WhereClause(
                    col.db_field_name,
                    EqualsOperator(),
                    col.to_database(getattr(self.instance, name))
                ))
            self._execute(statement)

        self._delete_null_columns()

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

        nulled_fields = set()
        if self.instance._has_counter or self.instance._can_update():
            return self.update()
        else:
            insert = InsertStatement(self.column_family_name, ttl=self._ttl, timestamp=self._timestamp)
            for name, col in self.instance._columns.items():
                val = getattr(self.instance, name, None)
                if col._val_is_null(val):
                    if self.instance._values[name].changed:
                        nulled_fields.add(col.db_field_name)
                    continue
                insert.add_assignment_clause(AssignmentClause(
                    col.db_field_name,
                    col.to_database(getattr(self.instance, name, None))
                ))

        # skip query execution if it's empty
        # caused by pointless update queries
        if not insert.is_empty:
            self._execute(insert)

        # delete any nulled columns
        self._delete_null_columns()

    def delete(self):
        """ Deletes one instance """
        if self.instance is None:
            raise CQLEngineException("DML Query instance attribute is None")

        ds = DeleteStatement(self.column_family_name, timestamp=self._timestamp)
        for name, col in self.model._primary_keys.items():
            ds.add_where_clause(WhereClause(
                col.db_field_name,
                EqualsOperator(),
                col.to_database(getattr(self.instance, name))
            ))
        self._execute(ds)



########NEW FILE########
__FILENAME__ = statements
import time
from datetime import datetime, timedelta
from cqlengine.functions import QueryValue
from cqlengine.operators import BaseWhereOperator, InOperator


class StatementException(Exception): pass


class ValueQuoter(object):

    def __init__(self, value):
        self.value = value

    def __unicode__(self):
        from cql.query import cql_quote
        if isinstance(self.value, bool):
            return 'true' if self.value else 'false'
        elif isinstance(self.value, (list, tuple)):
            return '[' + ', '.join([cql_quote(v) for v in self.value]) + ']'
        elif isinstance(self.value, dict):
            return '{' + ', '.join([cql_quote(k) + ':' + cql_quote(v) for k,v in self.value.items()]) + '}'
        elif isinstance(self.value, set):
            return '{' + ', '.join([cql_quote(v) for v in self.value]) + '}'
        return cql_quote(self.value)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        return False

    def __str__(self):
        return unicode(self).encode('utf-8')


class InQuoter(ValueQuoter):

    def __unicode__(self):
        from cql.query import cql_quote
        return '(' + ', '.join([cql_quote(v) for v in self.value]) + ')'


class BaseClause(object):

    def __init__(self, field, value):
        self.field = field
        self.value = value
        self.context_id = None

    def __unicode__(self):
        raise NotImplementedError

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __hash__(self):
        return hash(self.field) ^ hash(self.value)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.field == other.field and self.value == other.value
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_context_size(self):
        """ returns the number of entries this clause will add to the query context """
        return 1

    def set_context_id(self, i):
        """ sets the value placeholder that will be used in the query """
        self.context_id = i

    def update_context(self, ctx):
        """ updates the query context with this clauses values """
        assert isinstance(ctx, dict)
        ctx[str(self.context_id)] = self.value


class WhereClause(BaseClause):
    """ a single where statement used in queries """

    def __init__(self, field, operator, value, quote_field=True):
        """

        :param field:
        :param operator:
        :param value:
        :param quote_field: hack to get the token function rendering properly
        :return:
        """
        if not isinstance(operator, BaseWhereOperator):
            raise StatementException(
                "operator must be of type {}, got {}".format(BaseWhereOperator, type(operator))
            )
        super(WhereClause, self).__init__(field, value)
        self.operator = operator
        self.query_value = self.value if isinstance(self.value, QueryValue) else QueryValue(self.value)
        self.quote_field = quote_field

    def __unicode__(self):
        field = ('"{}"' if self.quote_field else '{}').format(self.field)
        return u'{} {} {}'.format(field, self.operator, unicode(self.query_value))

    def __hash__(self):
        return super(WhereClause, self).__hash__() ^ hash(self.operator)

    def __eq__(self, other):
        if super(WhereClause, self).__eq__(other):
            return self.operator.__class__ == other.operator.__class__
        return False

    def get_context_size(self):
        return self.query_value.get_context_size()

    def set_context_id(self, i):
        super(WhereClause, self).set_context_id(i)
        self.query_value.set_context_id(i)

    def update_context(self, ctx):
        if isinstance(self.operator, InOperator):
            ctx[str(self.context_id)] = InQuoter(self.value)
        else:
            self.query_value.update_context(ctx)


class AssignmentClause(BaseClause):
    """ a single variable st statement """

    def __unicode__(self):
        return u'"{}" = :{}'.format(self.field, self.context_id)

    def insert_tuple(self):
        return self.field, self.context_id


class ContainerUpdateClause(AssignmentClause):

    def __init__(self, field, value, operation=None, previous=None, column=None):
        super(ContainerUpdateClause, self).__init__(field, value)
        self.previous = previous
        self._assignments = None
        self._operation = operation
        self._analyzed = False
        self._column = column

    def _to_database(self, val):
        return self._column.to_database(val) if self._column else val

    def _analyze(self):
        raise NotImplementedError

    def get_context_size(self):
        raise NotImplementedError

    def update_context(self, ctx):
        raise NotImplementedError


class SetUpdateClause(ContainerUpdateClause):
    """ updates a set collection """

    def __init__(self, field, value, operation=None, previous=None, column=None):
        super(SetUpdateClause, self).__init__(field, value, operation, previous, column=column)
        self._additions = None
        self._removals = None

    def __unicode__(self):
        qs = []
        ctx_id = self.context_id
        if self._assignments:
            qs += ['"{}" = :{}'.format(self.field, ctx_id)]
            ctx_id += 1
        if self._additions:
            qs += ['"{0}" = "{0}" + :{1}'.format(self.field, ctx_id)]
            ctx_id += 1
        if self._removals:
            qs += ['"{0}" = "{0}" - :{1}'.format(self.field, ctx_id)]

        return ', '.join(qs)

    def _analyze(self):
        """ works out the updates to be performed """
        if self.value is None or self.value == self.previous:
            pass
        elif self._operation == "add":
            self._additions = self.value
        elif self._operation == "remove":
            self._removals = self.value
        elif self.previous is None:
            self._assignments = self.value
        else:
            # partial update time
            self._additions = (self.value - self.previous) or None
            self._removals = (self.previous - self.value) or None
        self._analyzed = True

    def get_context_size(self):
        if not self._analyzed: self._analyze()
        return int(bool(self._assignments)) + int(bool(self._additions)) + int(bool(self._removals))

    def update_context(self, ctx):
        if not self._analyzed: self._analyze()
        ctx_id = self.context_id
        if self._assignments:
            ctx[str(ctx_id)] = self._to_database(self._assignments)
            ctx_id += 1
        if self._additions:
            ctx[str(ctx_id)] = self._to_database(self._additions)
            ctx_id += 1
        if self._removals:
            ctx[str(ctx_id)] = self._to_database(self._removals)


class ListUpdateClause(ContainerUpdateClause):
    """ updates a list collection """

    def __init__(self, field, value, operation=None, previous=None, column=None):
        super(ListUpdateClause, self).__init__(field, value, operation, previous, column=column)
        self._append = None
        self._prepend = None

    def __unicode__(self):
        if not self._analyzed: self._analyze()
        qs = []
        ctx_id = self.context_id
        if self._assignments is not None:
            qs += ['"{}" = :{}'.format(self.field, ctx_id)]
            ctx_id += 1

        if self._prepend:
            qs += ['"{0}" = :{1} + "{0}"'.format(self.field, ctx_id)]
            ctx_id += 1

        if self._append:
            qs += ['"{0}" = "{0}" + :{1}'.format(self.field, ctx_id)]

        return ', '.join(qs)

    def get_context_size(self):
        if not self._analyzed: self._analyze()
        return int(self._assignments is not None) + int(bool(self._append)) + int(bool(self._prepend))

    def update_context(self, ctx):
        if not self._analyzed: self._analyze()
        ctx_id = self.context_id
        if self._assignments is not None:
            ctx[str(ctx_id)] = self._to_database(self._assignments)
            ctx_id += 1
        if self._prepend:
            # CQL seems to prepend element at a time, starting
            # with the element at idx 0, we can either reverse
            # it here, or have it inserted in reverse
            ctx[str(ctx_id)] = self._to_database(list(reversed(self._prepend)))
            ctx_id += 1
        if self._append:
            ctx[str(ctx_id)] = self._to_database(self._append)

    def _analyze(self):
        """ works out the updates to be performed """
        if self.value is None or self.value == self.previous:
            pass

        elif self._operation == "append":
            self._append = self.value

        elif self._operation == "prepend":
            # self.value is a Quoter but we reverse self._prepend later as if
            # it's a list, so we have to set it to the underlying list
            self._prepend = self.value.value

        elif self.previous is None:
            self._assignments = self.value

        elif len(self.value) < len(self.previous):
            # if elements have been removed,
            # rewrite the whole list
            self._assignments = self.value

        elif len(self.previous) == 0:
            # if we're updating from an empty
            # list, do a complete insert
            self._assignments = self.value
        else:

            # the max start idx we want to compare
            search_space = len(self.value) - max(0, len(self.previous)-1)

            # the size of the sub lists we want to look at
            search_size = len(self.previous)

            for i in range(search_space):
                #slice boundary
                j = i + search_size
                sub = self.value[i:j]
                idx_cmp = lambda idx: self.previous[idx] == sub[idx]
                if idx_cmp(0) and idx_cmp(-1) and self.previous == sub:
                    self._prepend = self.value[:i] or None
                    self._append = self.value[j:] or None
                    break

            # if both append and prepend are still None after looking
            # at both lists, an insert statement will be created
            if self._prepend is self._append is None:
                self._assignments = self.value

        self._analyzed = True


class MapUpdateClause(ContainerUpdateClause):
    """ updates a map collection """

    def __init__(self, field, value, operation=None, previous=None, column=None):
        super(MapUpdateClause, self).__init__(field, value, operation, previous, column=column)
        self._updates = None
        self.previous = self.previous or {}

    def _analyze(self):
        if self._operation == "update":
            self._updates = self.value.keys()
        else:
            self._updates = sorted([k for k, v in self.value.items() if v != self.previous.get(k)]) or None
        self._analyzed = True

    def get_context_size(self):
        if not self._analyzed: self._analyze()
        return len(self._updates or []) * 2

    def update_context(self, ctx):
        if not self._analyzed: self._analyze()
        ctx_id = self.context_id
        for key in self._updates or []:
            val = self.value.get(key)
            ctx[str(ctx_id)] = self._column.key_col.to_database(key) if self._column else key
            ctx[str(ctx_id + 1)] = self._column.value_col.to_database(val) if self._column else val
            ctx_id += 2

    def __unicode__(self):
        if not self._analyzed: self._analyze()
        qs = []

        ctx_id = self.context_id
        for _ in self._updates or []:
            qs += ['"{}"[:{}] = :{}'.format(self.field, ctx_id, ctx_id + 1)]
            ctx_id += 2

        return ', '.join(qs)


class CounterUpdateClause(ContainerUpdateClause):

    def __init__(self, field, value, previous=None, column=None):
        super(CounterUpdateClause, self).__init__(field, value, previous=previous, column=column)
        self.previous = self.previous or 0

    def get_context_size(self):
        return 1

    def update_context(self, ctx):
        ctx[str(self.context_id)] = self._to_database(abs(self.value - self.previous))

    def __unicode__(self):
        delta = self.value - self.previous
        sign = '-' if delta < 0 else '+'
        return '"{0}" = "{0}" {1} :{2}'.format(self.field, sign, self.context_id)


class BaseDeleteClause(BaseClause):
    pass


class FieldDeleteClause(BaseDeleteClause):
    """ deletes a field from a row """

    def __init__(self, field):
        super(FieldDeleteClause, self).__init__(field, None)

    def __unicode__(self):
        return '"{}"'.format(self.field)

    def update_context(self, ctx):
        pass

    def get_context_size(self):
        return 0


class MapDeleteClause(BaseDeleteClause):
    """ removes keys from a map """

    def __init__(self, field, value, previous=None):
        super(MapDeleteClause, self).__init__(field, value)
        self.value = self.value or {}
        self.previous = previous or {}
        self._analyzed = False
        self._removals = None

    def _analyze(self):
        self._removals = sorted([k for k in self.previous if k not in self.value])
        self._analyzed = True

    def update_context(self, ctx):
        if not self._analyzed: self._analyze()
        for idx, key in enumerate(self._removals):
            ctx[str(self.context_id + idx)] = key

    def get_context_size(self):
        if not self._analyzed: self._analyze()
        return len(self._removals)

    def __unicode__(self):
        if not self._analyzed: self._analyze()
        return ', '.join(['"{}"[:{}]'.format(self.field, self.context_id + i) for i in range(len(self._removals))])


class BaseCQLStatement(object):
    """ The base cql statement class """

    def __init__(self, table, consistency=None, timestamp=None, where=None):
        super(BaseCQLStatement, self).__init__()
        self.table = table
        self.consistency = consistency
        self.context_id = 0
        self.context_counter = self.context_id
        self.timestamp = timestamp

        self.where_clauses = []
        for clause in where or []:
            self.add_where_clause(clause)

    def add_where_clause(self, clause):
        """
        adds a where clause to this statement
        :param clause: the clause to add
        :type clause: WhereClause
        """
        if not isinstance(clause, WhereClause):
            raise StatementException("only instances of WhereClause can be added to statements")
        clause.set_context_id(self.context_counter)
        self.context_counter += clause.get_context_size()
        self.where_clauses.append(clause)

    def get_context(self):
        """
        returns the context dict for this statement
        :rtype: dict
        """
        ctx = {}
        for clause in self.where_clauses or []:
            clause.update_context(ctx)
        return ctx

    def get_context_size(self):
        return len(self.get_context())

    def update_context_id(self, i):
        self.context_id = i
        self.context_counter = self.context_id
        for clause in self.where_clauses:
            clause.set_context_id(self.context_counter)
            self.context_counter += clause.get_context_size()

    @property
    def timestamp_normalized(self):
        """
        we're expecting self.timestamp to be either a long, int, a datetime, or a timedelta
        :return:
        """
        if not self.timestamp:
            return None

        if isinstance(self.timestamp, (int, long)):
            return self.timestamp

        if isinstance(self.timestamp, timedelta):
            tmp = datetime.now() + self.timestamp
        else:
            tmp = self.timestamp

        return long(time.mktime(tmp.timetuple()) * 1e+6 + tmp.microsecond)

    def __unicode__(self):
        raise NotImplementedError

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return self.__unicode__()

    @property
    def _where(self):
        return 'WHERE {}'.format(' AND '.join([unicode(c) for c in self.where_clauses]))


class SelectStatement(BaseCQLStatement):
    """ a cql select statement """

    def __init__(self,
                 table,
                 fields=None,
                 count=False,
                 consistency=None,
                 where=None,
                 order_by=None,
                 limit=None,
                 allow_filtering=False):

        super(SelectStatement, self).__init__(
            table,
            consistency=consistency,
            where=where
        )

        self.fields = [fields] if isinstance(fields, basestring) else (fields or [])
        self.count = count
        self.order_by = [order_by] if isinstance(order_by, basestring) else order_by
        self.limit = limit
        self.allow_filtering = allow_filtering

    def __unicode__(self):
        qs = ['SELECT']
        if self.count:
            qs += ['COUNT(*)']
        else:
            qs += [', '.join(['"{}"'.format(f) for f in self.fields]) if self.fields else '*']
        qs += ['FROM', self.table]

        if self.where_clauses:
            qs += [self._where]

        if self.order_by and not self.count:
            qs += ['ORDER BY {}'.format(', '.join(unicode(o) for o in self.order_by))]

        if self.limit and not self.count:
            qs += ['LIMIT {}'.format(self.limit)]

        if self.allow_filtering:
            qs += ['ALLOW FILTERING']

        return ' '.join(qs)


class AssignmentStatement(BaseCQLStatement):
    """ value assignment statements """

    def __init__(self,
                 table,
                 assignments=None,
                 consistency=None,
                 where=None,
                 ttl=None,
                 timestamp=None):
        super(AssignmentStatement, self).__init__(
            table,
            consistency=consistency,
            where=where,
        )
        self.ttl = ttl
        self.timestamp = timestamp

        # add assignments
        self.assignments = []
        for assignment in assignments or []:
            self.add_assignment_clause(assignment)

    def update_context_id(self, i):
        super(AssignmentStatement, self).update_context_id(i)
        for assignment in self.assignments:
            assignment.set_context_id(self.context_counter)
            self.context_counter += assignment.get_context_size()

    def add_assignment_clause(self, clause):
        """
        adds an assignment clause to this statement
        :param clause: the clause to add
        :type clause: AssignmentClause
        """
        if not isinstance(clause, AssignmentClause):
            raise StatementException("only instances of AssignmentClause can be added to statements")
        clause.set_context_id(self.context_counter)
        self.context_counter += clause.get_context_size()
        self.assignments.append(clause)

    @property
    def is_empty(self):
        return len(self.assignments) == 0

    def get_context(self):
        ctx = super(AssignmentStatement, self).get_context()
        for clause in self.assignments:
            clause.update_context(ctx)
        return ctx


class InsertStatement(AssignmentStatement):
    """ an cql insert select statement """

    def add_where_clause(self, clause):
        raise StatementException("Cannot add where clauses to insert statements")

    def __unicode__(self):
        qs = ['INSERT INTO {}'.format(self.table)]

        # get column names and context placeholders
        fields = [a.insert_tuple() for a in self.assignments]
        columns, values = zip(*fields)

        qs += ["({})".format(', '.join(['"{}"'.format(c) for c in columns]))]
        qs += ['VALUES']
        qs += ["({})".format(', '.join([':{}'.format(v) for v in values]))]

        if self.ttl:
            qs += ["USING TTL {}".format(self.ttl)]

        if self.timestamp:
            qs += ["USING TIMESTAMP {}".format(self.timestamp_normalized)]

        return ' '.join(qs)


class UpdateStatement(AssignmentStatement):
    """ an cql update select statement """

    def __unicode__(self):
        qs = ['UPDATE', self.table]

        using_options = []

        if self.ttl:
            using_options += ["TTL {}".format(self.ttl)]

        if self.timestamp:
            using_options += ["TIMESTAMP {}".format(self.timestamp_normalized)]

        if using_options:
            qs += ["USING {}".format(" AND ".join(using_options))]

        qs += ['SET']
        qs += [', '.join([unicode(c) for c in self.assignments])]

        if self.where_clauses:
            qs += [self._where]

        return ' '.join(qs)


class DeleteStatement(BaseCQLStatement):
    """ a cql delete statement """

    def __init__(self, table, fields=None, consistency=None, where=None, timestamp=None):
        super(DeleteStatement, self).__init__(
            table,
            consistency=consistency,
            where=where,
            timestamp=timestamp
        )
        self.fields = []
        if isinstance(fields, basestring):
            fields = [fields]
        for field in fields or []:
            self.add_field(field)

    def update_context_id(self, i):
        super(DeleteStatement, self).update_context_id(i)
        for field in self.fields:
            field.set_context_id(self.context_counter)
            self.context_counter += field.get_context_size()

    def get_context(self):
        ctx = super(DeleteStatement, self).get_context()
        for field in self.fields:
            field.update_context(ctx)
        return ctx

    def add_field(self, field):
        if isinstance(field, basestring):
            field = FieldDeleteClause(field)
        if not isinstance(field, BaseClause):
            raise StatementException("only instances of AssignmentClause can be added to statements")
        field.set_context_id(self.context_counter)
        self.context_counter += field.get_context_size()
        self.fields.append(field)

    def __unicode__(self):
        qs = ['DELETE']
        if self.fields:
            qs += [', '.join(['{}'.format(f) for f in self.fields])]
        qs += ['FROM', self.table]

        delete_option = []

        if self.timestamp:
            delete_option += ["TIMESTAMP {}".format(self.timestamp_normalized)]

        if delete_option:
            qs += [" USING {} ".format(" AND ".join(delete_option))]

        if self.where_clauses:
            qs += [self._where]

        return ' '.join(qs)


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
        connection.setup([CASSANDRA_TEST_HOST], default_keyspace='cqlengine_test')

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
from cqlengine.management import sync_table, drop_table
from cqlengine.tests.base import BaseCassEngTestCase


class TestSetModel(Model):

    partition = columns.UUID(primary_key=True, default=uuid4)
    int_set = columns.Set(columns.Integer, required=False)
    text_set = columns.Set(columns.Text, required=False)


class JsonTestColumn(columns.Column):

    db_type = 'text'

    def to_python(self, value):
        if value is None: return
        if isinstance(value, basestring):
            return json.loads(value)
        else:
            return value

    def to_database(self, value):
        if value is None: return
        return json.dumps(value)


class TestSetColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestSetColumn, cls).setUpClass()
        drop_table(TestSetModel)
        sync_table(TestSetModel)

    @classmethod
    def tearDownClass(cls):
        super(TestSetColumn, cls).tearDownClass()
        drop_table(TestSetModel)

    def test_add_none_fails(self):
        with self.assertRaises(ValidationError):
            m = TestSetModel.create(int_set=set([None]))

    def test_empty_set_initial(self):
        """
        tests that sets are set() by default, should never be none
        :return:
        """
        m = TestSetModel.create()
        m.int_set.add(5)
        m.save()

    def test_deleting_last_item_should_succeed(self):
        m = TestSetModel.create()
        m.int_set.add(5)
        m.save()
        m.int_set.remove(5)
        m.save()

        m = TestSetModel.get(partition=m.partition)
        self.assertNotIn(5, m.int_set)

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

    def test_element_count_validation(self):
        """
        Tests that big collections are detected and raise an exception.
        """
        TestSetModel.create(text_set={str(uuid4()) for i in range(65535)})
        with self.assertRaises(ValidationError):
            TestSetModel.create(text_set={str(uuid4()) for i in range(65536)})

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
        """ Tests that updating a 'None' list creates a straight insert statement """
        ctx = {}
        col = columns.Set(columns.Integer, db_field="TEST")
        statements = col.get_update_statement({1, 2, 3, 4}, None, ctx)

        #only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == {1, 2, 3, 4}
        assert statements[0] == '"TEST" = :{}'.format(ctx.keys()[0])

    def test_update_from_empty(self):
        """ Tests that updating an empty list creates a straight insert statement """
        ctx = {}
        col = columns.Set(columns.Integer, db_field="TEST")
        statements = col.get_update_statement({1, 2, 3, 4}, set(), ctx)

        #only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == {1, 2, 3, 4}
        assert statements[0] == '"TEST" = :{}'.format(ctx.keys()[0])

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

    def test_default_empty_container_saving(self):
        """ tests that the default empty container is not saved if it hasn't been updated """
        pkey = uuid4()
        # create a row with set data
        TestSetModel.create(partition=pkey, int_set={3, 4})
        # create another with no set data
        TestSetModel.create(partition=pkey)

        m = TestSetModel.get(partition=pkey)
        self.assertEqual(m.int_set, {3, 4})


class TestListModel(Model):

    partition = columns.UUID(primary_key=True, default=uuid4)
    int_list = columns.List(columns.Integer, required=False)
    text_list = columns.List(columns.Text, required=False)


class TestListColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestListColumn, cls).setUpClass()
        drop_table(TestListModel)
        sync_table(TestListModel)

    @classmethod
    def tearDownClass(cls):
        super(TestListColumn, cls).tearDownClass()
        drop_table(TestListModel)

    def test_initial(self):
        tmp = TestListModel.create()
        tmp.int_list.append(1)

    def test_initial(self):
        tmp = TestListModel.create()
        tmp2 = TestListModel.get(partition=tmp.partition)
        tmp2.int_list.append(1)

    def test_io_success(self):
        """ Tests that a basic usage works as expected """
        m1 = TestListModel.create(int_list=[1, 2], text_list=['kai', 'andreas'])
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

    def test_element_count_validation(self):
        """
        Tests that big collections are detected and raise an exception.
        """
        TestListModel.create(text_list=[str(uuid4()) for i in range(65535)])
        with self.assertRaises(ValidationError):
            TestListModel.create(text_list=[str(uuid4()) for i in range(65536)])

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

        #only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == [1, 2, 3]
        assert statements[0] == '"TEST" = :{}'.format(ctx.keys()[0])

    def test_update_from_empty(self):
        """ Tests that updating an empty list creates a straight insert statement """
        ctx = {}
        col = columns.List(columns.Integer, db_field="TEST")
        statements = col.get_update_statement([1, 2, 3], [], ctx)

        #only one variable /statement should be generated
        assert len(ctx) == 1
        assert len(statements) == 1

        assert ctx.values()[0].value == [1, 2, 3]
        assert statements[0] == '"TEST" = :{}'.format(ctx.keys()[0])

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

    def test_default_empty_container_saving(self):
        """ tests that the default empty container is not saved if it hasn't been updated """
        pkey = uuid4()
        # create a row with list data
        TestListModel.create(partition=pkey, int_list=[1,2,3,4])
        # create another with no list data
        TestListModel.create(partition=pkey)

        m = TestListModel.get(partition=pkey)
        self.assertEqual(m.int_list, [1,2,3,4])

    def test_remove_entry_works(self):
        pkey = uuid4()
        tmp = TestListModel.create(partition=pkey, int_list=[1,2])
        tmp.int_list.pop()
        tmp.update()
        tmp = TestListModel.get(partition=pkey)
        self.assertEqual(tmp.int_list, [1])

    def test_update_from_non_empty_to_empty(self):
        pkey = uuid4()
        tmp = TestListModel.create(partition=pkey, int_list=[1,2])
        tmp.int_list = []
        tmp.update()

        tmp = TestListModel.get(partition=pkey)
        self.assertEqual(tmp.int_list, [])

    def test_insert_none(self):
        pkey = uuid4()
        with self.assertRaises(ValidationError):
            TestListModel.create(partition=pkey, int_list=[None])


class TestMapModel(Model):

    partition = columns.UUID(primary_key=True, default=uuid4)
    int_map = columns.Map(columns.Integer, columns.UUID, required=False)
    text_map = columns.Map(columns.Text, columns.DateTime, required=False)


class TestMapColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMapColumn, cls).setUpClass()
        drop_table(TestMapModel)
        sync_table(TestMapModel)

    @classmethod
    def tearDownClass(cls):
        super(TestMapColumn, cls).tearDownClass()
        drop_table(TestMapModel)

    def test_empty_default(self):
        tmp = TestMapModel.create()
        tmp.int_map['blah'] = 1

    def test_add_none_as_map_key(self):
        with self.assertRaises(ValidationError):
            TestMapModel.create(int_map={None:1})

    def test_add_none_as_map_value(self):
        with self.assertRaises(ValidationError):
            TestMapModel.create(int_map={None:1})

    def test_empty_retrieve(self):
        tmp = TestMapModel.create()
        tmp2 = TestMapModel.get(partition=tmp.partition)
        tmp2.int_map['blah'] = 1

    def test_remove_last_entry_works(self):
        tmp = TestMapModel.create()
        tmp.text_map["blah"] = datetime.now()
        tmp.save()
        del tmp.text_map["blah"]
        tmp.save()

        tmp = TestMapModel.get(partition=tmp.partition)
        self.assertNotIn("blah", tmp.int_map)

    def test_io_success(self):
        """ Tests that a basic usage works as expected """
        k1 = uuid4()
        k2 = uuid4()
        now = datetime.now()
        then = now + timedelta(days=1)
        m1 = TestMapModel.create(int_map={1: k1, 2: k2}, text_map={'now': now, 'then': then})
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
            TestMapModel.create(int_map={'key': 2, uuid4(): 'val'}, text_map={2: 5})

    def test_element_count_validation(self):
        """
        Tests that big collections are detected and raise an exception.
        """
        TestMapModel.create(text_map={str(uuid4()): i for i in range(65535)})
        with self.assertRaises(ValidationError):
            TestMapModel.create(text_map={str(uuid4()): i for i in range(65536)})

    def test_partial_updates(self):
        """ Tests that partial udpates work as expected """
        now = datetime.now()
        #derez it a bit
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

        m2.int_map = None
        m2.save()
        m3 = TestMapModel.get(partition=m.partition)
        assert m3.int_map != expected

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
        assert db_val.value == {json.dumps(k):json.dumps(v) for k,v in val.items()}
        py_val = column.to_python(db_val.value)
        assert py_val == val

    def test_default_empty_container_saving(self):
        """ tests that the default empty container is not saved if it hasn't been updated """
        pkey = uuid4()
        tmap = {1: uuid4(), 2: uuid4()}
        # create a row with set data
        TestMapModel.create(partition=pkey, int_map=tmap)
        # create another with no set data
        TestMapModel.create(partition=pkey)

        m = TestMapModel.get(partition=pkey)
        self.assertEqual(m.int_map, tmap)

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


class TestCamelMapModel(Model):

    partition = columns.UUID(primary_key=True, default=uuid4)
    camelMap = columns.Map(columns.Text, columns.Integer, required=False)


class TestCamelMapColumn(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestCamelMapColumn, cls).setUpClass()
        drop_table(TestCamelMapModel)
        sync_table(TestCamelMapModel)

    @classmethod
    def tearDownClass(cls):
        super(TestCamelMapColumn, cls).tearDownClass()
        drop_table(TestCamelMapModel)

    def test_camelcase_column(self):
        TestCamelMapModel.create(partition=None, camelMap={'blah': 1})

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
#tests the behavior of the column classes
from datetime import datetime, timedelta
from datetime import date
from datetime import tzinfo
from decimal import Decimal as D
from unittest import TestCase
from uuid import uuid4, uuid1
from cqlengine import ValidationError
from cqlengine.connection import execute

from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.columns import Column, TimeUUID
from cqlengine.columns import Bytes
from cqlengine.columns import Ascii
from cqlengine.columns import Text
from cqlengine.columns import Integer
from cqlengine.columns import BigInt
from cqlengine.columns import VarInt
from cqlengine.columns import DateTime
from cqlengine.columns import Date
from cqlengine.columns import UUID
from cqlengine.columns import Boolean
from cqlengine.columns import Float
from cqlengine.columns import Decimal

from cqlengine.management import create_table, delete_table, sync_table, drop_table
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
        assert dt2.created_at.timetuple()[:6] == (now + timedelta(hours=1)).timetuple()[:6]

    def test_datetime_date_support(self):
        today = date.today()
        self.DatetimeTest.objects.create(test_id=0, created_at=today)
        dt2 = self.DatetimeTest.objects(test_id=0).first()
        assert dt2.created_at.isoformat() == datetime(today.year, today.month, today.day).isoformat()

    def test_datetime_none(self):
        dt = self.DatetimeTest.objects.create(test_id=1, created_at=None)
        dt2 = self.DatetimeTest.objects(test_id=1).first()
        assert dt2.created_at is None

        dts = self.DatetimeTest.objects.filter(test_id=1).values_list('created_at')
        assert dts[0][0] is None


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

    def test_date_none(self):
        self.DateTest.objects.create(test_id=1, created_at=None)
        dt2 = self.DateTest.objects(test_id=1).first()
        assert dt2.created_at is None

        dts = self.DateTest.objects(test_id=1).values_list('created_at')
        assert dts[0][0] is None


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

class TestUUID(BaseCassEngTestCase):
    class UUIDTest(Model):
        test_id = Integer(primary_key=True)
        a_uuid = UUID(default=uuid4())

    @classmethod
    def setUpClass(cls):
        super(TestUUID, cls).setUpClass()
        create_table(cls.UUIDTest)

    @classmethod
    def tearDownClass(cls):
        super(TestUUID, cls).tearDownClass()
        delete_table(cls.UUIDTest)  

    def test_uuid_str_with_dashes(self):
        a_uuid = uuid4()
        t0 = self.UUIDTest.create(test_id=0, a_uuid=str(a_uuid))
        t1 = self.UUIDTest.get(test_id=0)
        assert a_uuid == t1.a_uuid

    def test_uuid_str_no_dashes(self):
        a_uuid = uuid4()
        t0 = self.UUIDTest.create(test_id=1, a_uuid=a_uuid.hex)
        t1 = self.UUIDTest.get(test_id=1)
        assert a_uuid == t1.a_uuid

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
        test_id = UUID(primary_key=True, default=lambda:uuid4())
        value   = Integer(default=0, required=True)

    def test_default_zero_fields_validate(self):
        """ Tests that integer columns with a default value of 0 validate """
        it = self.IntegerTest()
        it.validate()

class TestBigInt(BaseCassEngTestCase):
    class BigIntTest(Model):
        test_id = UUID(primary_key=True, default=lambda:uuid4())
        value   = BigInt(default=0, required=True)

    def test_default_zero_fields_validate(self):
        """ Tests that bigint columns with a default value of 0 validate """
        it = self.BigIntTest()
        it.validate()

class TestText(BaseCassEngTestCase):

    def test_min_length(self):
        #min len defaults to 1
        col = Text()
        col.validate('')

        col.validate('b')

        #test not required defaults to 0
        Text(required=False).validate('')

        #test arbitrary lengths
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

class TestPythonDoesntDieWhenExtraFieldIsInCassandra(BaseCassEngTestCase):
    class TestModel(Model):
        __table_name__ = 'alter_doesnt_break_running_app'
        id = UUID(primary_key=True, default=uuid4)

    def test_extra_field(self):
        drop_table(self.TestModel)
        sync_table(self.TestModel)
        self.TestModel.create()
        execute("ALTER TABLE {} add blah int".format(self.TestModel.column_family_name(include_keyspace=True)))
        self.TestModel.objects().all()

class TestTimeUUIDFromDatetime(TestCase):
    def test_conversion_specific_date(self):
        dt = datetime(1981, 7, 11, microsecond=555000)

        uuid = TimeUUID.from_datetime(dt)

        from uuid import UUID
        assert isinstance(uuid, UUID)

        ts = (uuid.time - 0x01b21dd213814000) / 1e7 # back to a timestamp
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

        #if the test column hasn't been defined, bail out
        if not cls.column: return

        # create a table with the given column
        class IOTestModel(Model):
            table_name = cls.column.db_type + "_io_test_model_{}".format(uuid4().hex[:8])
            pkey = cls.column(primary_key=True)
            data = cls.column()
        cls._generated_model = IOTestModel
        create_table(cls._generated_model)

        #tupleify the tested values
        if not isinstance(cls.pkey_val, tuple):
            cls.pkey_val = cls.pkey_val,
        if not isinstance(cls.data_val, tuple):
            cls.data_val = cls.data_val,

    @classmethod
    def tearDownClass(cls):
        super(BaseColumnIOTest, cls).tearDownClass()
        if not cls.column: return
        delete_table(cls._generated_model)

    def comparator_converter(self, val):
        """ If you want to convert the original value used to compare the model vales """
        return val

    def test_column_io(self):
        """ Tests the given models class creates and retrieves values as expected """
        if not self.column: return
        for pkey, data in zip(self.pkey_val, self.data_val):
            #create
            m1 = self._generated_model.create(pkey=pkey, data=data)

            #get
            m2 = self._generated_model.get(pkey=pkey)
            assert m1.pkey == m2.pkey == self.comparator_converter(pkey), self.column
            assert m1.data == m2.data == self.comparator_converter(data), self.column

            #delete
            self._generated_model.filter(pkey=pkey).delete()

class TestBlobIO(BaseColumnIOTest):

    column = columns.Bytes
    pkey_val = 'blake', uuid4().bytes
    data_val = 'eggleston', uuid4().bytes

class TestTextIO(BaseColumnIOTest):

    column = columns.Text
    pkey_val = 'bacon'
    data_val = 'monkey'


class TestNonBinaryTextIO(BaseColumnIOTest):

    column = columns.Text
    pkey_val = 'bacon'
    data_val = '0xmonkey'

class TestInteger(BaseColumnIOTest):

    column = columns.Integer
    pkey_val = 5
    data_val = 6

class TestBigInt(BaseColumnIOTest):

    column = columns.BigInt
    pkey_val = 6
    data_val = pow(2, 63) - 1

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

    def comparator_converter(self, val):
        return val.value if isinstance(val, columns.Boolean.Quoter) else val

class TestBooleanQuoter(BaseColumnIOTest):

    column = columns.Boolean

    pkey_val = True
    data_val = columns.Boolean.Quoter(False)

    def comparator_converter(self, val):
        return val.value if isinstance(val, columns.Boolean.Quoter) else val

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
from unittest import TestCase
from cql import OperationalError
from mock import MagicMock, patch, Mock

from cqlengine import ONE
from cqlengine.connection import ConnectionPool, Host


class OperationalErrorLoggingTest(TestCase):
    def test_logging(self):
        p = ConnectionPool([Host('127.0.0.1', '9160')])

        class MockConnection(object):
            host = 'localhost'
            port = 6379
            def cursor(self):
                raise OperationalError('test')


        with patch.object(p, 'get', return_value=MockConnection()):
            with self.assertRaises(OperationalError):
                p.execute("select * from system.peers", {}, ONE)

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
        assert result['min_threshold'] == '2'


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

        assert result['sstable_size_in_mb'] == '32'


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

    def test_compaction_not_altered_without_changes_leveled(self):
        from cqlengine.management import update_compaction

        class LeveledCompactionChangesDetectionTest(Model):
            __compaction__ = LeveledCompactionStrategy
            __compaction_sstable_size_in_mb__ = 160
            __compaction_tombstone_threshold__ = 0.125
            __compaction_tombstone_compaction_interval__ = 3600

            pk = columns.Integer(primary_key=True)

        drop_table(LeveledCompactionChangesDetectionTest)
        sync_table(LeveledCompactionChangesDetectionTest)

        assert not update_compaction(LeveledCompactionChangesDetectionTest)

    def test_compaction_not_altered_without_changes_sizetiered(self):
        from cqlengine.management import update_compaction

        class SizeTieredCompactionChangesDetectionTest(Model):
            __compaction__ = SizeTieredCompactionStrategy
            __compaction_bucket_high__ = 20
            __compaction_bucket_low__ = 10
            __compaction_max_threshold__ = 200
            __compaction_min_threshold__ = 100
            __compaction_min_sstable_size__ = 1000
            __compaction_tombstone_threshold__ = 0.125
            __compaction_tombstone_compaction_interval__ = 3600

            pk = columns.Integer(primary_key=True)

        drop_table(SizeTieredCompactionChangesDetectionTest)
        sync_table(SizeTieredCompactionChangesDetectionTest)

        assert not update_compaction(SizeTieredCompactionChangesDetectionTest)

    def test_alter_actually_alters(self):
        tmp = copy.deepcopy(LeveledcompactionTestTable)
        drop_table(tmp)
        sync_table(tmp)
        tmp.__compaction__ = SizeTieredCompactionStrategy
        tmp.__compaction_sstable_size_in_mb__ = None
        sync_table(tmp)

        table_settings = get_table_settings(tmp)

        self.assertRegexpMatches(table_settings['compaction_strategy_class'], '.*SizeTieredCompactionStrategy$')


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
from mock import MagicMock, patch

from cqlengine import ONE
from cqlengine.exceptions import CQLEngineException
from cqlengine.management import create_table, delete_table, get_fields, sync_table
from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine.connection import ConnectionPool, Host
from cqlengine import management
from cqlengine.tests.query.test_queryset import TestModel
from cqlengine.models import Model
from cqlengine import columns, SizeTieredCompactionStrategy, LeveledCompactionStrategy

class ConnectionPoolFailoverTestCase(BaseCassEngTestCase):
    """Test cassandra connection pooling."""

    def setUp(self):
        self.host = Host('127.0.0.1', '9160')
        self.pool = ConnectionPool([self.host])

    def test_totally_dead_pool(self):
        # kill the con
        with patch('cqlengine.connection.cql.connect') as mock:
            mock.side_effect=CQLEngineException
            with self.assertRaises(CQLEngineException):
                self.pool.execute("select * from system.peers", {}, ONE)

    def test_dead_node(self):
        """
        tests that a single dead node doesn't mess up the pool
        """
        self.pool._hosts.append(self.host)

        # cursor mock needed so set_cql_version doesn't crap out
        ok_cur = MagicMock()

        ok_conn = MagicMock()
        ok_conn.return_value = ok_cur


        returns = [CQLEngineException(), ok_conn]

        def side_effect(*args, **kwargs):
            result = returns.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with patch('cqlengine.connection.cql.connect') as mock:
            mock.side_effect = side_effect
            conn = self.pool._create_connection()


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

class PrimaryKeysOnlyModel(Model):
    __compaction__ = LeveledCompactionStrategy

    first_ey = columns.Integer(primary_key=True)
    second_key = columns.Integer(primary_key=True)


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


class SyncTableTests(BaseCassEngTestCase):

    def setUp(self):
        delete_table(PrimaryKeysOnlyModel)

    def test_sync_table_works_with_primary_keys_only_tables(self):

        # This is "create table":

        sync_table(PrimaryKeysOnlyModel)

        # let's make sure settings persisted correctly:

        assert PrimaryKeysOnlyModel.__compaction__ == LeveledCompactionStrategy
        # blows up with DoesNotExist if table does not exist
        table_settings = management.get_table_settings(PrimaryKeysOnlyModel)
        # let make sure the flag we care about
        assert LeveledCompactionStrategy in table_settings['compaction_strategy_class']


        # Now we are "updating" the table:

        # setting up something to change
        PrimaryKeysOnlyModel.__compaction__ = SizeTieredCompactionStrategy

        # primary-keys-only tables do not create entries in system.schema_columns
        # table. Only non-primary keys are added to that table.
        # Our code must deal with that eventuality properly (not crash)
        # on subsequent runs of sync_table (which runs get_fields internally)
        get_fields(PrimaryKeysOnlyModel)
        sync_table(PrimaryKeysOnlyModel)

        table_settings = management.get_table_settings(PrimaryKeysOnlyModel)
        assert SizeTieredCompactionStrategy in table_settings['compaction_strategy_class']

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
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())
            text = columns.Text()

        #check class attibutes
        self.assertHasAttr(TestModel, '_columns')
        self.assertHasAttr(TestModel, 'id')
        self.assertHasAttr(TestModel, 'text')

        #check instance attributes
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
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())
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
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())
            words = columns.Text()
            content = columns.Text()
            numbers = columns.Integer()

        self.assertEquals(Stuff._columns.keys(), ['id', 'words', 'content', 'numbers'])

    def test_exception_raised_when_creating_class_without_pk(self):
        with self.assertRaises(ModelDefinitionException):
            class TestModel(Model):
                count   = columns.Integer()
                text    = columns.Text(required=False)


    def test_value_managers_are_keeping_model_instances_isolated(self):
        """
        Tests that instance value managers are isolated from other instances
        """
        class Stuff(Model):
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())
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
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())
            text = columns.Text()

        class InheritedModel(TestModel):
            numbers = columns.Integer()

        assert 'text' in InheritedModel._columns
        assert 'numbers' in InheritedModel._columns

    def test_column_family_name_generation(self):
        """ Tests that auto column family name generation works as expected """
        class TestModel(Model):
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())
            text = columns.Text()

        assert TestModel.column_family_name(include_keyspace=False) == 'test_model'

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
            id = columns.UUID(primary_key=True, default=lambda:uuid4())
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
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())
            key = columns.Integer(primary_key=True)
            data = columns.Integer(required=False)

        model = DelModel(key=4, data=5)
        del model.data
        with self.assertRaises(AttributeError):
            del model.key

    def test_does_not_exist_exceptions_are_not_shared_between_model(self):
        """ Tests that DoesNotExist exceptions are not the same exception between models """

        class Model1(Model):
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())

        class Model2(Model):
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())

        try:
            raise Model1.DoesNotExist
        except Model2.DoesNotExist:
            assert False, "Model1 exception should not be caught by Model2"
        except Model1.DoesNotExist:
            #expected
            pass

    def test_does_not_exist_inherits_from_superclass(self):
        """ Tests that a DoesNotExist exception can be caught by it's parent class DoesNotExist """
        class Model1(Model):
            id  = columns.UUID(primary_key=True, default=lambda:uuid4())

        class Model2(Model1):
            pass

        try:
            raise Model2.DoesNotExist
        except Model1.DoesNotExist:
            #expected
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
        assert self.RenamedTest.column_family_name(include_keyspace=False) == 'manual_name'
        assert self.RenamedTest.column_family_name(include_keyspace=True) == 'whatever.manual_name'

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
        assert isinstance(ConcreteModelWithCol._columns['pkey'], columns.Column)

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

    class TestException(Exception): pass

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


class TestCachedLengthIsNotCarriedToSubclasses(BaseCassEngTestCase):
    def test_subclassing(self):

        length = len(ConcreteModelWithCol())

        class AlreadyLoadedTest(ConcreteModelWithCol):
            new_field = columns.Integer()

        self.assertGreater(len(AlreadyLoadedTest()), length)











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

        values = list(TestModel.objects.values_list('clustering_key', flat=True))
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
    id      = columns.UUID(primary_key=True, default=lambda:uuid4())
    count   = columns.Integer()
    text    = columns.Text(required=False)

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
__FILENAME__ = test_model
from unittest import TestCase

from cqlengine.models import Model
from cqlengine import columns


class TestModel(TestCase):
    """ Tests the non-io functionality of models """

    def test_instance_equality(self):
        """ tests the model equality functionality """
        class EqualityModel(Model):
            pk = columns.Integer(primary_key=True)

        m0 = EqualityModel(pk=0)
        m1 = EqualityModel(pk=1)

        self.assertEqual(m0, m0)
        self.assertNotEqual(m0, m1)

    def test_model_equality(self):
        """ tests the model equality functionality """
        class EqualityModel0(Model):
            pk = columns.Integer(primary_key=True)

        class EqualityModel1(Model):
            kk = columns.Integer(primary_key=True)

        m0 = EqualityModel0(pk=0)
        m1 = EqualityModel1(kk=1)

        self.assertEqual(m0, m0)
        self.assertNotEqual(m0, m1)

########NEW FILE########
__FILENAME__ = test_model_io
from uuid import uuid4
import random
from datetime import date
from operator import itemgetter
from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.management import create_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine import columns

class TestModel(Model):
    id      = columns.UUID(primary_key=True, default=lambda:uuid4())
    count   = columns.Integer()
    text    = columns.Text(required=False)
    a_bool  = columns.Boolean(default=False)

class TestModel(Model):
    id      = columns.UUID(primary_key=True, default=lambda:uuid4())
    count   = columns.Integer()
    text    = columns.Text(required=False)
    a_bool  = columns.Boolean(default=False)


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

    def test_model_read_as_dict(self):
        """
        Tests that columns of an instance can be read as a dict.
        """
        tm = TestModel.create(count=8, text='123456789', a_bool=True)
        column_dict = {
            'id': tm.id,
            'count': tm.count,
            'text': tm.text,
            'a_bool': tm.a_bool,
        }
        self.assertEquals(sorted(tm.keys()), sorted(column_dict.keys()))
        self.assertEquals(sorted(tm.values()), sorted(column_dict.values()))
        self.assertEquals(
            sorted(tm.items(), key=itemgetter(0)),
            sorted(column_dict.items(), key=itemgetter(0)))
        self.assertEquals(len(tm), len(column_dict))
        for column_id in column_dict.keys():
            self.assertEqual(tm[column_id], column_dict[column_id])

        tm['count'] = 6
        self.assertEqual(tm.count, 6)

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
    partition   = columns.Integer(primary_key=True)
    cluster     = columns.Integer(primary_key=True)
    count       = columns.Integer(required=False)
    text        = columns.Text(required=False)


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
        partition = random.randint(0,1000)
        for i in range(5):
            TestMultiKeyModel.create(partition=partition, cluster=i, count=i, text=str(i))

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

        check = TestMultiKeyModel.get(partition=self.instance.partition, cluster=self.instance.cluster)
        assert check.count == 5
        assert check.text == 'happy'

    def test_deleting_only(self):
        self.instance.count = None
        self.instance.text = None
        self.instance.save()

        check = TestMultiKeyModel.get(partition=self.instance.partition, cluster=self.instance.cluster)
        assert check.count is None
        assert check.text is None

    def test_get_changed_columns(self):
        assert self.instance.get_changed_columns() == []
        self.instance.count = 1
        changes = self.instance.get_changed_columns()
        assert len(changes) == 1
        assert changes == ['count']
        self.instance.save()
        assert self.instance.get_changed_columns() == []


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
    key     = columns.UUID(primary_key=True)
    val     = columns.Text(index=True)

class TestIndexedColumnDefinition(BaseCassEngTestCase):

    def test_exception_isnt_raised_if_an_index_is_defined_more_than_once(self):
        create_table(IndexDefinitionModel)
        create_table(IndexDefinitionModel)

class ReservedWordModel(Model):
    token   = columns.Text(primary_key=True)
    insert  = columns.Integer(index=True)

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


class TestQueryModel(Model):
    test_id = columns.UUID(primary_key=True, default=uuid4)
    date = columns.Date(primary_key=True)
    description = columns.Text()


class TestQuerying(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestQuerying, cls).setUpClass()
        delete_table(TestQueryModel)
        create_table(TestQueryModel)

    @classmethod
    def tearDownClass(cls):
        super(TestQuerying, cls).tearDownClass()
        delete_table(TestQueryModel)

    def test_query_with_date(self):
        uid = uuid4()
        day = date(2013, 11, 26)
        TestQueryModel.create(test_id=uid, date=day, description=u'foo')

        inst = TestQueryModel.filter(
            TestQueryModel.test_id == uid,
            TestQueryModel.date == day).limit(1).first()

        assert inst.test_id == uid
        assert inst.date == day

########NEW FILE########
__FILENAME__ = test_polymorphism
import uuid
import mock

from cqlengine import columns
from cqlengine import models
from cqlengine.connection import ConnectionPool
from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine import management


class TestPolymorphicClassConstruction(BaseCassEngTestCase):

    def test_multiple_polymorphic_key_failure(self):
        """ Tests that defining a model with more than one polymorphic key fails """
        with self.assertRaises(models.ModelDefinitionException):
            class M(models.Model):
                partition = columns.Integer(primary_key=True)
                type1 = columns.Integer(polymorphic_key=True)
                type2 = columns.Integer(polymorphic_key=True)

    def test_polymorphic_key_inheritance(self):
        """ Tests that polymorphic_key attribute is not inherited """
        class Base(models.Model):
            partition = columns.Integer(primary_key=True)
            type1 = columns.Integer(polymorphic_key=True)

        class M1(Base):
            __polymorphic_key__ = 1

        class M2(M1):
            pass

        assert M2.__polymorphic_key__ is None

    def test_polymorphic_metaclass(self):
        """ Tests that the model meta class configures polymorphic models properly """
        class Base(models.Model):
            partition = columns.Integer(primary_key=True)
            type1 = columns.Integer(polymorphic_key=True)

        class M1(Base):
            __polymorphic_key__ = 1

        assert Base._is_polymorphic
        assert M1._is_polymorphic

        assert Base._is_polymorphic_base
        assert not M1._is_polymorphic_base

        assert Base._polymorphic_column is Base._columns['type1']
        assert M1._polymorphic_column is M1._columns['type1']

        assert Base._polymorphic_column_name == 'type1'
        assert M1._polymorphic_column_name == 'type1'

    def test_table_names_are_inherited_from_poly_base(self):
        class Base(models.Model):
            partition = columns.Integer(primary_key=True)
            type1 = columns.Integer(polymorphic_key=True)

        class M1(Base):
            __polymorphic_key__ = 1

        assert Base.column_family_name() == M1.column_family_name()

    def test_collection_columns_cant_be_polymorphic_keys(self):
        with self.assertRaises(models.ModelDefinitionException):
            class Base(models.Model):
                partition = columns.Integer(primary_key=True)
                type1 = columns.Set(columns.Integer, polymorphic_key=True)


class PolyBase(models.Model):
    partition = columns.UUID(primary_key=True, default=uuid.uuid4)
    row_type = columns.Integer(polymorphic_key=True)


class Poly1(PolyBase):
    __polymorphic_key__ = 1
    data1 = columns.Text()


class Poly2(PolyBase):
    __polymorphic_key__ = 2
    data2 = columns.Text()


class TestPolymorphicModel(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestPolymorphicModel, cls).setUpClass()
        management.sync_table(Poly1)
        management.sync_table(Poly2)

    @classmethod
    def tearDownClass(cls):
        super(TestPolymorphicModel, cls).tearDownClass()
        management.drop_table(Poly1)
        management.drop_table(Poly2)

    def test_saving_base_model_fails(self):
        with self.assertRaises(models.PolyMorphicModelException):
            PolyBase.create()

    def test_saving_subclass_saves_poly_key(self):
        p1 = Poly1.create(data1='pickle')
        p2 = Poly2.create(data2='bacon')

        assert p1.row_type == Poly1.__polymorphic_key__
        assert p2.row_type == Poly2.__polymorphic_key__

    def test_query_deserialization(self):
        p1 = Poly1.create(data1='pickle')
        p2 = Poly2.create(data2='bacon')

        p1r = PolyBase.get(partition=p1.partition)
        p2r = PolyBase.get(partition=p2.partition)

        assert isinstance(p1r, Poly1)
        assert isinstance(p2r, Poly2)

    def test_delete_on_polymorphic_subclass_does_not_include_polymorphic_key(self):
        p1 = Poly1.create()

        with mock.patch.object(ConnectionPool, 'execute') as m:
            Poly1.objects(partition=p1.partition).delete()

        # make sure our polymorphic key isn't in the CQL
        # not sure how we would even get here if it was in there
        # since the CQL would fail.

        self.assertNotIn("row_type", m.call_args[0][0])





class UnindexedPolyBase(models.Model):
    partition = columns.UUID(primary_key=True, default=uuid.uuid4)
    cluster = columns.UUID(primary_key=True, default=uuid.uuid4)
    row_type = columns.Integer(polymorphic_key=True)


class UnindexedPoly1(UnindexedPolyBase):
    __polymorphic_key__ = 1
    data1 = columns.Text()


class UnindexedPoly2(UnindexedPolyBase):
    __polymorphic_key__ = 2
    data2 = columns.Text()


class UnindexedPoly3(UnindexedPoly2):
    __polymorphic_key__ = 3
    data3 = columns.Text()


class TestUnindexedPolymorphicQuery(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestUnindexedPolymorphicQuery, cls).setUpClass()
        management.sync_table(UnindexedPoly1)
        management.sync_table(UnindexedPoly2)
        management.sync_table(UnindexedPoly3)

        cls.p1 = UnindexedPoly1.create(data1='pickle')
        cls.p2 = UnindexedPoly2.create(partition=cls.p1.partition, data2='bacon')
        cls.p3 = UnindexedPoly3.create(partition=cls.p1.partition, data3='turkey')

    @classmethod
    def tearDownClass(cls):
        super(TestUnindexedPolymorphicQuery, cls).tearDownClass()
        management.drop_table(UnindexedPoly1)
        management.drop_table(UnindexedPoly2)
        management.drop_table(UnindexedPoly3)

    def test_non_conflicting_type_results_work(self):
        p1, p2, p3 = self.p1, self.p2, self.p3
        assert len(list(UnindexedPoly1.objects(partition=p1.partition, cluster=p1.cluster))) == 1
        assert len(list(UnindexedPoly2.objects(partition=p1.partition, cluster=p2.cluster))) == 1

    def test_subclassed_model_results_work_properly(self):
        p1, p2, p3 = self.p1, self.p2, self.p3
        assert len(list(UnindexedPoly2.objects(partition=p1.partition, cluster__in=[p2.cluster, p3.cluster]))) == 2

    def test_conflicting_type_results(self):
        with self.assertRaises(models.PolyMorphicModelException):
            list(UnindexedPoly1.objects(partition=self.p1.partition))
        with self.assertRaises(models.PolyMorphicModelException):
            list(UnindexedPoly2.objects(partition=self.p1.partition))


class IndexedPolyBase(models.Model):
    partition = columns.UUID(primary_key=True, default=uuid.uuid4)
    cluster = columns.UUID(primary_key=True, default=uuid.uuid4)
    row_type = columns.Integer(polymorphic_key=True, index=True)


class IndexedPoly1(IndexedPolyBase):
    __polymorphic_key__ = 1
    data1 = columns.Text()


class IndexedPoly2(IndexedPolyBase):
    __polymorphic_key__ = 2
    data2 = columns.Text()


class TestIndexedPolymorphicQuery(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestIndexedPolymorphicQuery, cls).setUpClass()
        management.sync_table(IndexedPoly1)
        management.sync_table(IndexedPoly2)

        cls.p1 = IndexedPoly1.create(data1='pickle')
        cls.p2 = IndexedPoly2.create(partition=cls.p1.partition, data2='bacon')

    @classmethod
    def tearDownClass(cls):
        super(TestIndexedPolymorphicQuery, cls).tearDownClass()
        management.drop_table(IndexedPoly1)
        management.drop_table(IndexedPoly2)

    def test_success_case(self):
        assert len(list(IndexedPoly1.objects(partition=self.p1.partition))) == 1
        assert len(list(IndexedPoly2.objects(partition=self.p1.partition))) == 1



########NEW FILE########
__FILENAME__ = test_updates
from uuid import uuid4

from mock import patch
from cqlengine.exceptions import ValidationError

from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine.models import Model
from cqlengine import columns
from cqlengine.management import sync_table, drop_table
from cqlengine.connection import ConnectionPool


class TestUpdateModel(Model):
    partition   = columns.UUID(primary_key=True, default=uuid4)
    cluster     = columns.UUID(primary_key=True, default=uuid4)
    count       = columns.Integer(required=False)
    text        = columns.Text(required=False, index=True)


class ModelUpdateTests(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(ModelUpdateTests, cls).setUpClass()
        sync_table(TestUpdateModel)

    @classmethod
    def tearDownClass(cls):
        super(ModelUpdateTests, cls).tearDownClass()
        drop_table(TestUpdateModel)

    def test_update_model(self):
        """ tests calling udpate on models with no values passed in """
        m0 = TestUpdateModel.create(count=5, text='monkey')

        # independently save over a new count value, unknown to original instance
        m1 = TestUpdateModel.get(partition=m0.partition, cluster=m0.cluster)
        m1.count = 6
        m1.save()

        # update the text, and call update
        m0.text = 'monkey land'
        m0.update()

        # database should reflect both updates
        m2 = TestUpdateModel.get(partition=m0.partition, cluster=m0.cluster)
        self.assertEqual(m2.count, m1.count)
        self.assertEqual(m2.text, m0.text)

    def test_update_values(self):
        """ tests calling update on models with values passed in """
        m0 = TestUpdateModel.create(count=5, text='monkey')

        # independently save over a new count value, unknown to original instance
        m1 = TestUpdateModel.get(partition=m0.partition, cluster=m0.cluster)
        m1.count = 6
        m1.save()

        # update the text, and call update
        m0.update(text='monkey land')
        self.assertEqual(m0.text, 'monkey land')

        # database should reflect both updates
        m2 = TestUpdateModel.get(partition=m0.partition, cluster=m0.cluster)
        self.assertEqual(m2.count, m1.count)
        self.assertEqual(m2.text, m0.text)

    def test_noop_model_update(self):
        """ tests that calling update on a model with no changes will do nothing. """
        m0 = TestUpdateModel.create(count=5, text='monkey')

        with patch.object(ConnectionPool, 'execute') as execute:
            m0.update()
        assert execute.call_count == 0

        with patch.object(ConnectionPool, 'execute') as execute:
            m0.update(count=5)
        assert execute.call_count == 0

    def test_invalid_update_kwarg(self):
        """ tests that passing in a kwarg to the update method that isn't a column will fail """
        m0 = TestUpdateModel.create(count=5, text='monkey')
        with self.assertRaises(ValidationError):
            m0.update(numbers=20)

    def test_primary_key_update_failure(self):
        """ tests that attempting to update the value of a primary key will fail """
        m0 = TestUpdateModel.create(count=5, text='monkey')
        with self.assertRaises(ValidationError):
            m0.update(partition=uuid4())


########NEW FILE########
__FILENAME__ = test_validation


########NEW FILE########
__FILENAME__ = test_assignment_operators

########NEW FILE########
__FILENAME__ = test_base_operator
from unittest import TestCase
from cqlengine.operators import BaseQueryOperator, QueryOperatorException


class BaseOperatorTest(TestCase):

    def test_get_operator_cannot_be_called_from_base_class(self):
        with self.assertRaises(QueryOperatorException):
            BaseQueryOperator.get_operator('*')
########NEW FILE########
__FILENAME__ = test_where_operators
from unittest import TestCase
from cqlengine.operators import *


class TestWhereOperators(TestCase):

    def test_symbol_lookup(self):
        """ tests where symbols are looked up properly """

        def check_lookup(symbol, expected):
            op = BaseWhereOperator.get_operator(symbol)
            self.assertEqual(op, expected)

        check_lookup('EQ', EqualsOperator)
        check_lookup('IN', InOperator)
        check_lookup('GT', GreaterThanOperator)
        check_lookup('GTE', GreaterThanOrEqualOperator)
        check_lookup('LT', LessThanOperator)
        check_lookup('LTE', LessThanOrEqualOperator)

    def test_operator_rendering(self):
        """ tests symbols are rendered properly """
        self.assertEqual("=", unicode(EqualsOperator()))
        self.assertEqual("IN", unicode(InOperator()))
        self.assertEqual(">", unicode(GreaterThanOperator()))
        self.assertEqual(">=", unicode(GreaterThanOrEqualOperator()))
        self.assertEqual("<", unicode(LessThanOperator()))
        self.assertEqual("<=", unicode(LessThanOrEqualOperator()))



########NEW FILE########
__FILENAME__ = test_batch_query
from datetime import datetime
from unittest import skip
from uuid import uuid4
import random
from cqlengine import Model, columns
from cqlengine.management import drop_table, sync_table
from cqlengine.query import BatchQuery, DMLQuery
from cqlengine.tests.base import BaseCassEngTestCase

class TestMultiKeyModel(Model):
    partition   = columns.Integer(primary_key=True)
    cluster     = columns.Integer(primary_key=True)
    count       = columns.Integer(required=False)
    text        = columns.Text(required=False)

class BatchQueryLogModel(Model):
    # simple k/v table
    k = columns.Integer(primary_key=True)
    v = columns.Integer()

class BatchQueryTests(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BatchQueryTests, cls).setUpClass()
        drop_table(TestMultiKeyModel)
        sync_table(TestMultiKeyModel)

    @classmethod
    def tearDownClass(cls):
        super(BatchQueryTests, cls).tearDownClass()
        drop_table(TestMultiKeyModel)

    def setUp(self):
        super(BatchQueryTests, self).setUp()
        self.pkey = 1
        for obj in TestMultiKeyModel.filter(partition=self.pkey):
            obj.delete()

    def test_insert_success_case(self):

        b = BatchQuery()
        inst = TestMultiKeyModel.batch(b).create(partition=self.pkey, cluster=2, count=3, text='4')

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_update_success_case(self):

        inst = TestMultiKeyModel.create(partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.count = 4
        inst.batch(b).save()

        inst2 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst2.count == 3

        b.execute()

        inst3 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst3.count == 4

    def test_delete_success_case(self):

        inst = TestMultiKeyModel.create(partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.batch(b).delete()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_context_manager(self):

        with BatchQuery() as b:
            for i in range(5):
                TestMultiKeyModel.batch(b).create(partition=self.pkey, cluster=i, count=3, text='4')

            for i in range(5):
                with self.assertRaises(TestMultiKeyModel.DoesNotExist):
                    TestMultiKeyModel.get(partition=self.pkey, cluster=i)

        for i in range(5):
            TestMultiKeyModel.get(partition=self.pkey, cluster=i)

    def test_bulk_delete_success_case(self):

        for i in range(1):
            for j in range(5):
                TestMultiKeyModel.create(partition=i, cluster=j, count=i*j, text='{}:{}'.format(i,j))

        with BatchQuery() as b:
            TestMultiKeyModel.objects.batch(b).filter(partition=0).delete()
            assert TestMultiKeyModel.filter(partition=0).count() == 5

        assert TestMultiKeyModel.filter(partition=0).count() == 0
        #cleanup
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

    def test_batch_execute_on_exception_succeeds(self):
    # makes sure if execute_on_exception == True we still apply the batch
        drop_table(BatchQueryLogModel)
        sync_table(BatchQueryLogModel)

        obj = BatchQueryLogModel.objects(k=1)
        self.assertEqual(0, len(obj))

        try:
            with BatchQuery(execute_on_exception=True) as b:
                BatchQueryLogModel.batch(b).create(k=1, v=1)
                raise Exception("Blah")
        except:
            pass

        obj = BatchQueryLogModel.objects(k=1)
        # should be 1 because the batch should execute
        self.assertEqual(1, len(obj))

    def test_batch_execute_on_exception_skips_if_not_specified(self):
    # makes sure if execute_on_exception == True we still apply the batch
        drop_table(BatchQueryLogModel)
        sync_table(BatchQueryLogModel)

        obj = BatchQueryLogModel.objects(k=2)
        self.assertEqual(0, len(obj))

        try:
            with BatchQuery() as b:
                BatchQueryLogModel.batch(b).create(k=2, v=2)
                raise Exception("Blah")
        except:
            pass

        obj = BatchQueryLogModel.objects(k=2)
        
        # should be 0 because the batch should not execute
        self.assertEqual(0, len(obj))

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
    user        = columns.Integer(primary_key=True)
    day         = columns.DateTime(primary_key=True)
    data        = columns.Text()

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
                    day=(cls.base_date+timedelta(days=y)),
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

        results = DateTimeQueryTestModel.filter(user=0, day__gte=start, day__lt=end)
        assert len(results) == 3

    def test_datetime_precision(self):
        """ Tests that millisecond resolution is preserved when saving datetime objects """
        now = datetime.now()
        pk = 1000
        obj = DateTimeQueryTestModel.create(user=pk, day=now, data='energy cheese')
        load = DateTimeQueryTestModel.get(user=pk)

        assert abs(now - load.day).total_seconds() < 0.001
        obj.delete()


########NEW FILE########
__FILENAME__ = test_named
from cqlengine import operators
from cqlengine.named import NamedKeyspace
from cqlengine.operators import EqualsOperator, GreaterThanOrEqualOperator
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
        assert isinstance(op.operator, operators.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(expected_result__gte=1)
        assert len(query2._where) == 2

        op = query2._where[1]
        assert isinstance(op.operator, operators.GreaterThanOrEqualOperator)
        assert op.value == 1

    def test_query_expression_parsing(self):
        """ Tests that query experessions are evaluated properly """
        query1 = self.table.filter(self.table.column('test_id') == 5)
        assert len(query1._where) == 1

        op = query1._where[0]
        assert isinstance(op.operator, operators.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(self.table.column('expected_result') >= 1)
        assert len(query2._where) == 2

        op = query2._where[1]
        assert isinstance(op.operator, operators.GreaterThanOrEqualOperator)
        assert op.value == 1

    def test_filter_method_where_clause_generation(self):
        """
        Tests the where clause creation
        """
        query1 = self.table.objects(test_id=5)
        self.assertEqual(len(query1._where), 1)
        where = query1._where[0]
        self.assertEqual(where.field, 'test_id')
        self.assertEqual(where.value, 5)

        query2 = query1.filter(expected_result__gte=1)
        self.assertEqual(len(query2._where), 2)

        where = query2._where[0]
        self.assertEqual(where.field, 'test_id')
        self.assertIsInstance(where.operator, EqualsOperator)
        self.assertEqual(where.value, 5)

        where = query2._where[1]
        self.assertEqual(where.field, 'expected_result')
        self.assertIsInstance(where.operator, GreaterThanOrEqualOperator)
        self.assertEqual(where.value, 1)

    def test_query_expression_where_clause_generation(self):
        """
        Tests the where clause creation
        """
        query1 = self.table.objects(self.table.column('test_id') == 5)
        self.assertEqual(len(query1._where), 1)
        where = query1._where[0]
        self.assertEqual(where.field, 'test_id')
        self.assertEqual(where.value, 5)

        query2 = query1.filter(self.table.column('expected_result') >= 1)
        self.assertEqual(len(query2._where), 2)

        where = query2._where[0]
        self.assertEqual(where.field, 'test_id')
        self.assertIsInstance(where.operator, EqualsOperator)
        self.assertEqual(where.value, 5)

        where = query2._where[1]
        self.assertEqual(where.field, 'expected_result')
        self.assertIsInstance(where.operator, GreaterThanOrEqualOperator)
        self.assertEqual(where.value, 1)


class TestQuerySetCountSelectionAndIteration(BaseQuerySetUsage):

    @classmethod
    def setUpClass(cls):
        super(TestQuerySetCountSelectionAndIteration, cls).setUpClass()

        from cqlengine.tests.query.test_queryset import TestModel

        ks,tn = TestModel.column_family_name().split('.')
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
        #tuple of expected attempt_id, expected_result values
        compare_set = set([(0,5), (1,10), (2,15), (3,20)])
        for t in q:
            val = t.attempt_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with regular filtering
        q = self.table.objects(attempt_id=3).allow_filtering()
        assert len(q) == 3
        #tuple of expected test_id, expected_result values
        compare_set = set([(0,20), (1,20), (2,75)])
        for t in q:
            val = t.test_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with query method
        q = self.table.objects(self.table.column('attempt_id') == 3).allow_filtering()
        assert len(q) == 3
        #tuple of expected test_id, expected_result values
        compare_set = set([(0,20), (1,20), (2,75)])
        for t in q:
            val = t.test_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

    def test_multiple_iterations_work_properly(self):
        """ Tests that iterating over a query set more than once works """
        # test with both the filtering method and the query method
        for q in (self.table.objects(test_id=0), self.table.objects(self.table.column('test_id') == 0)):
            #tuple of expected attempt_id, expected_result values
            compare_set = set([(0,5), (1,10), (2,15), (3,20)])
            for t in q:
                val = t.attempt_id, t.expected_result
                assert val in compare_set
                compare_set.remove(val)
            assert len(compare_set) == 0

            #try it again
            compare_set = set([(0,5), (1,10), (2,15), (3,20)])
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
            expected_order = [0,1,2,3]
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
        m = self.table.get(self.table.column('test_id') == 0, self.table.column('attempt_id') == 0)
        assert isinstance(m, ResultObject)
        assert m.test_id == 0
        assert m.attempt_id == 0

        q = self.table.objects(self.table.column('test_id') == 0, self.table.column('attempt_id') == 0)
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
from cqlengine.columns import DateTime

from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine import columns, Model
from cqlengine import functions
from cqlengine import query
from cqlengine.statements import WhereClause
from cqlengine.operators import EqualsOperator
from cqlengine.management import sync_table, drop_table

class TestQuerySetOperation(BaseCassEngTestCase):

    def test_maxtimeuuid_function(self):
        """
        Tests that queries with helper functions are generated properly
        """
        now = datetime.now()
        where = WhereClause('time', EqualsOperator(), functions.MaxTimeUUID(now))
        where.set_context_id(5)

        self.assertEqual(str(where), '"time" = MaxTimeUUID(:5)')
        ctx = {}
        where.update_context(ctx)
        self.assertEqual(ctx, {'5': DateTime().to_database(now)})

    def test_mintimeuuid_function(self):
        """
        Tests that queries with helper functions are generated properly
        """
        now = datetime.now()
        where = WhereClause('time', EqualsOperator(), functions.MinTimeUUID(now))
        where.set_context_id(5)

        self.assertEqual(str(where), '"time" = MinTimeUUID(:5)')
        ctx = {}
        where.update_context(ctx)
        self.assertEqual(ctx, {'5': DateTime().to_database(now)})


class TokenTestModel(Model):
    key = columns.Integer(primary_key=True)
    val = columns.Integer()


class TestTokenFunction(BaseCassEngTestCase):

    def setUp(self):
        super(TestTokenFunction, self).setUp()
        sync_table(TokenTestModel)

    def tearDown(self):
        super(TestTokenFunction, self).tearDown()
        drop_table(TokenTestModel)

    def test_token_function(self):
        """ Tests that token functions work properly """
        assert TokenTestModel.objects().count() == 0
        for i in range(10):
            TokenTestModel.create(key=i, val=i)
        assert TokenTestModel.objects().count() == 10
        seen_keys = set()
        last_token = None
        for instance in TokenTestModel.objects().limit(5):
            last_token = instance.key
            seen_keys.add(last_token)
        assert len(seen_keys) == 5
        for instance in TokenTestModel.objects(pk__token__gt=functions.Token(last_token)):
            seen_keys.add(instance.key)

        assert len(seen_keys) == 10
        assert all([i in seen_keys for i in range(10)])

    def test_compound_pk_token_function(self):

        class TestModel(Model):
            p1 = columns.Text(partition_key=True)
            p2 = columns.Text(partition_key=True)

        func = functions.Token('a', 'b')

        q = TestModel.objects.filter(pk__token__gt=func)
        where = q._where[0]
        where.set_context_id(1)
        self.assertEquals(str(where), 'token("p1", "p2") > token(:{}, :{})'.format(1, 2))

        # Verify that a SELECT query can be successfully generated
        str(q._select_query())

        # Token(tuple()) is also possible for convenience
        # it (allows for Token(obj.pk) syntax)
        func = functions.Token(('a', 'b'))

        q = TestModel.objects.filter(pk__token__gt=func)
        where = q._where[0]
        where.set_context_id(1)
        self.assertEquals(str(where), 'token("p1", "p2") > token(:{}, :{})'.format(1, 2))
        str(q._select_query())

        # The 'pk__token' virtual column may only be compared to a Token
        self.assertRaises(query.QueryException, TestModel.objects.filter, pk__token__gt=10)

        # A Token may only be compared to the `pk__token' virtual column
        func = functions.Token('a', 'b')
        self.assertRaises(query.QueryException, TestModel.objects.filter, p1__gt=func)

        # The # of arguments to Token must match the # of partition keys
        func = functions.Token('a')
        self.assertRaises(query.QueryException, TestModel.objects.filter, pk__token__gt=func)

########NEW FILE########
__FILENAME__ = test_queryset
from datetime import datetime
import time
from uuid import uuid1, uuid4

from cqlengine.tests.base import BaseCassEngTestCase

from cqlengine.exceptions import ModelException
from cqlengine import functions
from cqlengine.management import create_table, drop_table
from cqlengine.management import delete_table
from cqlengine.models import Model
from cqlengine import columns
from cqlengine import query
from datetime import timedelta
from datetime import tzinfo

from cqlengine import statements
from cqlengine import operators


class TzOffset(tzinfo):
    """Minimal implementation of a timezone offset to help testing with timezone
    aware datetimes.
    """

    def __init__(self, offset):
        self._offset = timedelta(hours=offset)

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return 'TzOffset: {}'.format(self._offset.hours)

    def dst(self, dt):
        return timedelta(0)


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

        assert isinstance(op, statements.WhereClause)
        assert isinstance(op.operator, operators.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(expected_result__gte=1)
        assert len(query2._where) == 2

        op = query2._where[1]
        self.assertIsInstance(op, statements.WhereClause)
        self.assertIsInstance(op.operator, operators.GreaterThanOrEqualOperator)
        assert op.value == 1

    def test_query_expression_parsing(self):
        """ Tests that query experessions are evaluated properly """
        query1 = TestModel.filter(TestModel.test_id == 5)
        assert len(query1._where) == 1

        op = query1._where[0]
        assert isinstance(op, statements.WhereClause)
        assert isinstance(op.operator, operators.EqualsOperator)
        assert op.value == 5

        query2 = query1.filter(TestModel.expected_result >= 1)
        assert len(query2._where) == 2

        op = query2._where[1]
        self.assertIsInstance(op, statements.WhereClause)
        self.assertIsInstance(op.operator, operators.GreaterThanOrEqualOperator)
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

    def test_queryset_is_immutable(self):
        """
        Tests that calling a queryset function that changes it's state returns a new queryset
        """
        query1 = TestModel.objects(test_id=5)
        assert len(query1._where) == 1

        query2 = query1.filter(expected_result__gte=1)
        assert len(query2._where) == 2
        assert len(query1._where) == 1

    def test_queryset_limit_immutability(self):
        """
        Tests that calling a queryset function that changes it's state returns a new queryset with same limit
        """
        query1 = TestModel.objects(test_id=5).limit(1)
        assert query1._limit == 1

        query2 = query1.filter(expected_result__gte=1)
        assert query2._limit == 1

        query3 = query1.filter(expected_result__gte=1).limit(2)
        assert query1._limit == 1
        assert query3._limit == 2

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

        TestModel.objects.create(test_id=0, attempt_id=0, description='try1', expected_result=5, test_result=30)
        TestModel.objects.create(test_id=0, attempt_id=1, description='try2', expected_result=10, test_result=30)
        TestModel.objects.create(test_id=0, attempt_id=2, description='try3', expected_result=15, test_result=30)
        TestModel.objects.create(test_id=0, attempt_id=3, description='try4', expected_result=20, test_result=25)

        TestModel.objects.create(test_id=1, attempt_id=0, description='try5', expected_result=5, test_result=25)
        TestModel.objects.create(test_id=1, attempt_id=1, description='try6', expected_result=10, test_result=25)
        TestModel.objects.create(test_id=1, attempt_id=2, description='try7', expected_result=15, test_result=25)
        TestModel.objects.create(test_id=1, attempt_id=3, description='try8', expected_result=20, test_result=20)

        TestModel.objects.create(test_id=2, attempt_id=0, description='try9', expected_result=50, test_result=40)
        TestModel.objects.create(test_id=2, attempt_id=1, description='try10', expected_result=60, test_result=40)
        TestModel.objects.create(test_id=2, attempt_id=2, description='try11', expected_result=70, test_result=45)
        TestModel.objects.create(test_id=2, attempt_id=3, description='try12', expected_result=75, test_result=45)

        IndexedTestModel.objects.create(test_id=0, attempt_id=0, description='try1', expected_result=5, test_result=30)
        IndexedTestModel.objects.create(test_id=1, attempt_id=1, description='try2', expected_result=10, test_result=30)
        IndexedTestModel.objects.create(test_id=2, attempt_id=2, description='try3', expected_result=15, test_result=30)
        IndexedTestModel.objects.create(test_id=3, attempt_id=3, description='try4', expected_result=20, test_result=25)

        IndexedTestModel.objects.create(test_id=4, attempt_id=0, description='try5', expected_result=5, test_result=25)
        IndexedTestModel.objects.create(test_id=5, attempt_id=1, description='try6', expected_result=10, test_result=25)
        IndexedTestModel.objects.create(test_id=6, attempt_id=2, description='try7', expected_result=15, test_result=25)
        IndexedTestModel.objects.create(test_id=7, attempt_id=3, description='try8', expected_result=20, test_result=20)

        IndexedTestModel.objects.create(test_id=8, attempt_id=0, description='try9', expected_result=50, test_result=40)
        IndexedTestModel.objects.create(test_id=9, attempt_id=1, description='try10', expected_result=60,
                                        test_result=40)
        IndexedTestModel.objects.create(test_id=10, attempt_id=2, description='try11', expected_result=70,
                                        test_result=45)
        IndexedTestModel.objects.create(test_id=11, attempt_id=3, description='try12', expected_result=75,
                                        test_result=45)

    @classmethod
    def tearDownClass(cls):
        super(BaseQuerySetUsage, cls).tearDownClass()
        drop_table(TestModel)
        drop_table(IndexedTestModel)
        drop_table(TestMultiClusteringModel)


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
        #tuple of expected attempt_id, expected_result values
        compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
        for t in q:
            val = t.attempt_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with regular filtering
        q = TestModel.objects(attempt_id=3).allow_filtering()
        assert len(q) == 3
        #tuple of expected test_id, expected_result values
        compare_set = set([(0, 20), (1, 20), (2, 75)])
        for t in q:
            val = t.test_id, t.expected_result
            assert val in compare_set
            compare_set.remove(val)
        assert len(compare_set) == 0

        # test with query method
        q = TestModel.objects(TestModel.attempt_id == 3).allow_filtering()
        assert len(q) == 3
        #tuple of expected test_id, expected_result values
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
            #tuple of expected attempt_id, expected_result values
            compare_set = set([(0, 5), (1, 10), (2, 15), (3, 20)])
            for t in q:
                val = t.attempt_id, t.expected_result
                assert val in compare_set
                compare_set.remove(val)
            assert len(compare_set) == 0

            #try it again
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

        q = TestModel.objects(TestModel.test_id == 0, TestModel.attempt_id == 0)
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

        results = TestMultiClusteringModel.objects.filter(one=1, two=1).order_by('-two', '-three')
        assert [r.three for r in results] == [5, 4, 3, 2, 1]

        results = TestMultiClusteringModel.objects.filter(one=1, two=1).order_by('two', 'three')
        assert [r.three for r in results] == [1, 2, 3, 4, 5]

        results = TestMultiClusteringModel.objects.filter(one=1, two=1).order_by('two').order_by('three')
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
        TestModel.objects.create(test_id=3, attempt_id=0, description='try9', expected_result=50, test_result=40)
        TestModel.objects.create(test_id=3, attempt_id=1, description='try10', expected_result=60, test_result=40)
        TestModel.objects.create(test_id=3, attempt_id=2, description='try11', expected_result=70, test_result=45)
        TestModel.objects.create(test_id=3, attempt_id=3, description='try12', expected_result=75, test_result=45)

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
        #tuple of expected attempt_id, expected_result values
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

    def test_tzaware_datetime_support(self):
        """Test that using timezone aware datetime instances works with the
        MinTimeUUID/MaxTimeUUID functions.
        """
        pk = uuid4()
        midpoint_utc = datetime.utcnow().replace(tzinfo=TzOffset(0))
        midpoint_helsinki = midpoint_utc.astimezone(TzOffset(3))

        # Assert pre-condition that we have the same logical point in time
        assert midpoint_utc.utctimetuple() == midpoint_helsinki.utctimetuple()
        assert midpoint_utc.timetuple() != midpoint_helsinki.timetuple()

        TimeUUIDQueryModel.create(
            partition=pk,
            time=columns.TimeUUID.from_datetime(midpoint_utc - timedelta(minutes=1)),
            data='1')

        TimeUUIDQueryModel.create(
            partition=pk,
            time=columns.TimeUUID.from_datetime(midpoint_utc),
            data='2')

        TimeUUIDQueryModel.create(
            partition=pk,
            time=columns.TimeUUID.from_datetime(midpoint_utc + timedelta(minutes=1)),
            data='3')

        assert ['1', '2'] == [o.data for o in TimeUUIDQueryModel.filter(
            TimeUUIDQueryModel.partition == pk,
            TimeUUIDQueryModel.time <= functions.MaxTimeUUID(midpoint_utc))]

        assert ['1', '2'] == [o.data for o in TimeUUIDQueryModel.filter(
            TimeUUIDQueryModel.partition == pk,
            TimeUUIDQueryModel.time <= functions.MaxTimeUUID(midpoint_helsinki))]

        assert ['2', '3'] == [o.data for o in TimeUUIDQueryModel.filter(
            TimeUUIDQueryModel.partition == pk,
            TimeUUIDQueryModel.time >= functions.MinTimeUUID(midpoint_utc))]

        assert ['2', '3'] == [o.data for o in TimeUUIDQueryModel.filter(
            TimeUUIDQueryModel.partition == pk,
            TimeUUIDQueryModel.time >= functions.MinTimeUUID(midpoint_helsinki))]

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
        q = TimeUUIDQueryModel.filter(partition=pk, time__lte=functions.MaxTimeUUID(midpoint))
        q = [d for d in q]
        assert len(q) == 2
        datas = [d.data for d in q]
        assert '1' in datas
        assert '2' in datas

        q = TimeUUIDQueryModel.filter(partition=pk, time__gte=functions.MinTimeUUID(midpoint))
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
        item = q.values_list('test_id', 'attempt_id', 'description', 'expected_result', 'test_result').first()
        assert item == [0, 1, 'try2', 10, 30]

        item = q.values_list('expected_result', flat=True).first()
        assert item == 10


class TestObjectsProperty(BaseQuerySetUsage):
    def test_objects_property_returns_fresh_queryset(self):
        assert TestModel.objects._result_cache is None
        len(TestModel.objects) # evaluate queryset
        assert TestModel.objects._result_cache is None



########NEW FILE########
__FILENAME__ = test_updates
from uuid import uuid4
from cqlengine.exceptions import ValidationError
from cqlengine.query import QueryException

from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine.models import Model
from cqlengine.management import sync_table, drop_table
from cqlengine import columns


class TestQueryUpdateModel(Model):
    partition   = columns.UUID(primary_key=True, default=uuid4)
    cluster     = columns.Integer(primary_key=True)
    count       = columns.Integer(required=False)
    text        = columns.Text(required=False, index=True)
    text_set    = columns.Set(columns.Text, required=False)
    text_list   = columns.List(columns.Text, required=False)
    text_map    = columns.Map(columns.Text, columns.Text, required=False)

class QueryUpdateTests(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(QueryUpdateTests, cls).setUpClass()
        sync_table(TestQueryUpdateModel)

    @classmethod
    def tearDownClass(cls):
        super(QueryUpdateTests, cls).tearDownClass()
        drop_table(TestQueryUpdateModel)

    def test_update_values(self):
        """ tests calling udpate on a queryset """
        partition = uuid4()
        for i in range(5):
            TestQueryUpdateModel.create(partition=partition, cluster=i, count=i, text=str(i))

        # sanity check
        for i, row in enumerate(TestQueryUpdateModel.objects(partition=partition)):
            assert row.cluster == i
            assert row.count == i
            assert row.text == str(i)

        # perform update
        TestQueryUpdateModel.objects(partition=partition, cluster=3).update(count=6)

        for i, row in enumerate(TestQueryUpdateModel.objects(partition=partition)):
            assert row.cluster == i
            assert row.count == (6 if i == 3 else i)
            assert row.text == str(i)

    def test_update_values_validation(self):
        """ tests calling udpate on models with values passed in """
        partition = uuid4()
        for i in range(5):
            TestQueryUpdateModel.create(partition=partition, cluster=i, count=i, text=str(i))

        # sanity check
        for i, row in enumerate(TestQueryUpdateModel.objects(partition=partition)):
            assert row.cluster == i
            assert row.count == i
            assert row.text == str(i)

        # perform update
        with self.assertRaises(ValidationError):
            TestQueryUpdateModel.objects(partition=partition, cluster=3).update(count='asdf')

    def test_invalid_update_kwarg(self):
        """ tests that passing in a kwarg to the update method that isn't a column will fail """
        with self.assertRaises(ValidationError):
            TestQueryUpdateModel.objects(partition=uuid4(), cluster=3).update(bacon=5000)

    def test_primary_key_update_failure(self):
        """ tests that attempting to update the value of a primary key will fail """
        with self.assertRaises(ValidationError):
            TestQueryUpdateModel.objects(partition=uuid4(), cluster=3).update(cluster=5000)

    def test_null_update_deletes_column(self):
        """ setting a field to null in the update should issue a delete statement """
        partition = uuid4()
        for i in range(5):
            TestQueryUpdateModel.create(partition=partition, cluster=i, count=i, text=str(i))

        # sanity check
        for i, row in enumerate(TestQueryUpdateModel.objects(partition=partition)):
            assert row.cluster == i
            assert row.count == i
            assert row.text == str(i)

        # perform update
        TestQueryUpdateModel.objects(partition=partition, cluster=3).update(text=None)

        for i, row in enumerate(TestQueryUpdateModel.objects(partition=partition)):
            assert row.cluster == i
            assert row.count == i
            assert row.text == (None if i == 3 else str(i))

    def test_mixed_value_and_null_update(self):
        """ tests that updating a columns value, and removing another works properly """
        partition = uuid4()
        for i in range(5):
            TestQueryUpdateModel.create(partition=partition, cluster=i, count=i, text=str(i))

        # sanity check
        for i, row in enumerate(TestQueryUpdateModel.objects(partition=partition)):
            assert row.cluster == i
            assert row.count == i
            assert row.text == str(i)

        # perform update
        TestQueryUpdateModel.objects(partition=partition, cluster=3).update(count=6, text=None)

        for i, row in enumerate(TestQueryUpdateModel.objects(partition=partition)):
            assert row.cluster == i
            assert row.count == (6 if i == 3 else i)
            assert row.text == (None if i == 3 else str(i))

    def test_counter_updates(self):
        pass

    def test_set_add_updates(self):
        partition = uuid4()
        cluster = 1
        TestQueryUpdateModel.objects.create(
                partition=partition, cluster=cluster, text_set={"foo"})
        TestQueryUpdateModel.objects(
                partition=partition, cluster=cluster).update(text_set__add={'bar'})
        obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        self.assertEqual(obj.text_set, {"foo", "bar"})

    def test_set_add_updates_new_record(self):
        """ If the key doesn't exist yet, an update creates the record
        """
        partition = uuid4()
        cluster = 1
        TestQueryUpdateModel.objects(
                partition=partition, cluster=cluster).update(text_set__add={'bar'})
        obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        self.assertEqual(obj.text_set, {"bar"})

    def test_set_remove_updates(self):
        partition = uuid4()
        cluster = 1
        TestQueryUpdateModel.objects.create(
                partition=partition, cluster=cluster, text_set={"foo", "baz"})
        TestQueryUpdateModel.objects(
                partition=partition, cluster=cluster).update(
                text_set__remove={'foo'})
        obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        self.assertEqual(obj.text_set, {"baz"})

    def test_set_remove_new_record(self):
        """ Removing something not in the set should silently do nothing
        """
        partition = uuid4()
        cluster = 1
        TestQueryUpdateModel.objects.create(
                partition=partition, cluster=cluster, text_set={"foo"})
        TestQueryUpdateModel.objects(
                partition=partition, cluster=cluster).update(
                text_set__remove={'afsd'})
        obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        self.assertEqual(obj.text_set, {"foo"})

    def test_list_append_updates(self):
        partition = uuid4()
        cluster = 1
        TestQueryUpdateModel.objects.create(
                partition=partition, cluster=cluster, text_list=["foo"])
        TestQueryUpdateModel.objects(
                partition=partition, cluster=cluster).update(
                text_list__append=['bar'])
        obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        self.assertEqual(obj.text_list, ["foo", "bar"])

    def test_list_prepend_updates(self):
        """ Prepend two things since order is reversed by default by CQL """
        partition = uuid4()
        cluster = 1
        TestQueryUpdateModel.objects.create(
                partition=partition, cluster=cluster, text_list=["foo"])
        TestQueryUpdateModel.objects(
                partition=partition, cluster=cluster).update(
                text_list__prepend=['bar', 'baz'])
        obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        self.assertEqual(obj.text_list, ["bar", "baz", "foo"])

    def test_map_update_updates(self):
        """ Merge a dictionary into existing value """
        partition = uuid4()
        cluster = 1
        TestQueryUpdateModel.objects.create(
                partition=partition, cluster=cluster,
                text_map={"foo": '1', "bar": '2'})
        TestQueryUpdateModel.objects(
                partition=partition, cluster=cluster).update(
                text_map__update={"bar": '3', "baz": '4'})
        obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        self.assertEqual(obj.text_map, {"foo": '1', "bar": '3', "baz": '4'})

    def test_map_update_none_deletes_key(self):
        """ The CQL behavior is if you set a key in a map to null it deletes
        that key from the map.  Test that this works with __update.

        This test fails because of a bug in the cql python library not
        converting None to null (and the cql library is no longer in active
        developement).
        """
        # partition = uuid4()
        # cluster = 1
        # TestQueryUpdateModel.objects.create(
        #         partition=partition, cluster=cluster,
        #         text_map={"foo": '1', "bar": '2'})
        # TestQueryUpdateModel.objects(
        #         partition=partition, cluster=cluster).update(
        #         text_map__update={"bar": None})
        # obj = TestQueryUpdateModel.objects.get(partition=partition, cluster=cluster)
        # self.assertEqual(obj.text_map, {"foo": '1'})

########NEW FILE########
__FILENAME__ = test_assignment_clauses
from unittest import TestCase
from cqlengine.statements import AssignmentClause, SetUpdateClause, ListUpdateClause, MapUpdateClause, MapDeleteClause, FieldDeleteClause, CounterUpdateClause


class AssignmentClauseTests(TestCase):

    def test_rendering(self):
        pass

    def test_insert_tuple(self):
        ac = AssignmentClause('a', 'b')
        ac.set_context_id(10)
        self.assertEqual(ac.insert_tuple(), ('a', 10))


class SetUpdateClauseTests(TestCase):

    def test_update_from_none(self):
        c = SetUpdateClause('s', {1, 2}, previous=None)
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._assignments, {1, 2})
        self.assertIsNone(c._additions)
        self.assertIsNone(c._removals)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': {1, 2}})

    def test_null_update(self):
        """ tests setting a set to None creates an empty update statement """
        c = SetUpdateClause('s', None, previous={1, 2})
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertIsNone(c._additions)
        self.assertIsNone(c._removals)

        self.assertEqual(c.get_context_size(), 0)
        self.assertEqual(str(c), '')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {})

    def test_no_update(self):
        """ tests an unchanged value creates an empty update statement """
        c = SetUpdateClause('s', {1, 2}, previous={1, 2})
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertIsNone(c._additions)
        self.assertIsNone(c._removals)

        self.assertEqual(c.get_context_size(), 0)
        self.assertEqual(str(c), '')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {})

    def test_additions(self):
        c = SetUpdateClause('s', {1, 2, 3}, previous={1, 2})
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertEqual(c._additions, {3})
        self.assertIsNone(c._removals)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = "s" + :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': {3}})

    def test_removals(self):
        c = SetUpdateClause('s', {1, 2}, previous={1, 2, 3})
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertIsNone(c._additions)
        self.assertEqual(c._removals, {3})

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = "s" - :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': {3}})

    def test_additions_and_removals(self):
        c = SetUpdateClause('s', {2, 3}, previous={1, 2})
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertEqual(c._additions, {3})
        self.assertEqual(c._removals, {1})

        self.assertEqual(c.get_context_size(), 2)
        self.assertEqual(str(c), '"s" = "s" + :0, "s" = "s" - :1')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': {3}, '1': {1}})


class ListUpdateClauseTests(TestCase):

    def test_update_from_none(self):
        c = ListUpdateClause('s', [1, 2, 3])
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._assignments, [1, 2, 3])
        self.assertIsNone(c._append)
        self.assertIsNone(c._prepend)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': [1, 2, 3]})

    def test_update_from_empty(self):
        c = ListUpdateClause('s', [1, 2, 3], previous=[])
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._assignments, [1, 2, 3])
        self.assertIsNone(c._append)
        self.assertIsNone(c._prepend)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': [1, 2, 3]})

    def test_update_from_different_list(self):
        c = ListUpdateClause('s', [1, 2, 3], previous=[3, 2, 1])
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._assignments, [1, 2, 3])
        self.assertIsNone(c._append)
        self.assertIsNone(c._prepend)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': [1, 2, 3]})

    def test_append(self):
        c = ListUpdateClause('s', [1, 2, 3, 4], previous=[1, 2])
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertEqual(c._append, [3, 4])
        self.assertIsNone(c._prepend)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = "s" + :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': [3, 4]})

    def test_prepend(self):
        c = ListUpdateClause('s', [1, 2, 3, 4], previous=[3, 4])
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertIsNone(c._append)
        self.assertEqual(c._prepend, [1, 2])

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = :0 + "s"')

        ctx = {}
        c.update_context(ctx)
        # test context list reversal
        self.assertEqual(ctx, {'0': [2, 1]})

    def test_append_and_prepend(self):
        c = ListUpdateClause('s', [1, 2, 3, 4, 5, 6], previous=[3, 4])
        c._analyze()
        c.set_context_id(0)

        self.assertIsNone(c._assignments)
        self.assertEqual(c._append, [5, 6])
        self.assertEqual(c._prepend, [1, 2])

        self.assertEqual(c.get_context_size(), 2)
        self.assertEqual(str(c), '"s" = :0 + "s", "s" = "s" + :1')

        ctx = {}
        c.update_context(ctx)
        # test context list reversal
        self.assertEqual(ctx, {'0': [2, 1], '1': [5, 6]})

    def test_shrinking_list_update(self):
        """ tests that updating to a smaller list results in an insert statement """
        c = ListUpdateClause('s', [1, 2, 3], previous=[1, 2, 3, 4])
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._assignments, [1, 2, 3])
        self.assertIsNone(c._append)
        self.assertIsNone(c._prepend)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"s" = :0')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': [1, 2, 3]})


class MapUpdateTests(TestCase):

    def test_update(self):
        c = MapUpdateClause('s', {3: 0, 5: 6}, {5: 0, 3: 4})
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._updates, [3, 5])
        self.assertEqual(c.get_context_size(), 4)
        self.assertEqual(str(c), '"s"[:0] = :1, "s"[:2] = :3')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': 3, "1": 0, '2': 5, '3': 6})

    def test_update_from_null(self):
        c = MapUpdateClause('s', {3: 0, 5: 6})
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._updates, [3, 5])
        self.assertEqual(c.get_context_size(), 4)
        self.assertEqual(str(c), '"s"[:0] = :1, "s"[:2] = :3')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': 3, "1": 0, '2': 5, '3': 6})

    def test_nulled_columns_arent_included(self):
        c = MapUpdateClause('s', {3: 0}, {1: 2, 3: 4})
        c._analyze()
        c.set_context_id(0)

        self.assertNotIn(1, c._updates)


class CounterUpdateTests(TestCase):

    def test_positive_update(self):
        c = CounterUpdateClause('a', 5, 3)
        c.set_context_id(5)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"a" = "a" + :5')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'5': 2})

    def test_negative_update(self):
        c = CounterUpdateClause('a', 4, 7)
        c.set_context_id(3)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"a" = "a" - :3')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'3': 3})

    def noop_update(self):
        c = CounterUpdateClause('a', 5, 5)
        c.set_context_id(5)

        self.assertEqual(c.get_context_size(), 1)
        self.assertEqual(str(c), '"a" = "a" + :5')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'5': 0})


class MapDeleteTests(TestCase):

    def test_update(self):
        c = MapDeleteClause('s', {3: 0}, {1: 2, 3: 4, 5: 6})
        c._analyze()
        c.set_context_id(0)

        self.assertEqual(c._removals, [1, 5])
        self.assertEqual(c.get_context_size(), 2)
        self.assertEqual(str(c), '"s"[:0], "s"[:1]')

        ctx = {}
        c.update_context(ctx)
        self.assertEqual(ctx, {'0': 1, '1': 5})


class FieldDeleteTests(TestCase):

    def test_str(self):
        f = FieldDeleteClause("blake")
        assert str(f) == '"blake"'

########NEW FILE########
__FILENAME__ = test_assignment_statement
from unittest import TestCase
from cqlengine.statements import AssignmentStatement, StatementException


class AssignmentStatementTest(TestCase):

    def test_add_assignment_type_checking(self):
        """ tests that only assignment clauses can be added to queries """
        stmt = AssignmentStatement('table', [])
        with self.assertRaises(StatementException):
            stmt.add_assignment_clause('x=5')
########NEW FILE########
__FILENAME__ = test_base_clause
from unittest import TestCase
from cqlengine.statements import BaseClause


class BaseClauseTests(TestCase):

    def test_context_updating(self):
        ss = BaseClause('a', 'b')
        assert ss.get_context_size() == 1

        ctx = {}
        ss.set_context_id(10)
        ss.update_context(ctx)
        assert ctx == {'10': 'b'}



########NEW FILE########
__FILENAME__ = test_base_statement
from unittest import TestCase
from cqlengine.statements import BaseCQLStatement, StatementException


class BaseStatementTest(TestCase):

    def test_where_clause_type_checking(self):
        """ tests that only assignment clauses can be added to queries """
        stmt = BaseCQLStatement('table', [])
        with self.assertRaises(StatementException):
            stmt.add_where_clause('x=5')

########NEW FILE########
__FILENAME__ = test_delete_statement
from unittest import TestCase
from cqlengine.statements import DeleteStatement, WhereClause, MapDeleteClause
from cqlengine.operators import *


class DeleteStatementTests(TestCase):

    def test_single_field_is_listified(self):
        """ tests that passing a string field into the constructor puts it into a list """
        ds = DeleteStatement('table', 'field')
        self.assertEqual(len(ds.fields), 1)
        self.assertEqual(ds.fields[0].field, 'field')

    def test_field_rendering(self):
        """ tests that fields are properly added to the select statement """
        ds = DeleteStatement('table', ['f1', 'f2'])
        self.assertTrue(unicode(ds).startswith('DELETE "f1", "f2"'), unicode(ds))
        self.assertTrue(str(ds).startswith('DELETE "f1", "f2"'), str(ds))

    def test_none_fields_rendering(self):
        """ tests that a '*' is added if no fields are passed in """
        ds = DeleteStatement('table', None)
        self.assertTrue(unicode(ds).startswith('DELETE FROM'), unicode(ds))
        self.assertTrue(str(ds).startswith('DELETE FROM'), str(ds))

    def test_table_rendering(self):
        ds = DeleteStatement('table', None)
        self.assertTrue(unicode(ds).startswith('DELETE FROM table'), unicode(ds))
        self.assertTrue(str(ds).startswith('DELETE FROM table'), str(ds))

    def test_where_clause_rendering(self):
        ds = DeleteStatement('table', None)
        ds.add_where_clause(WhereClause('a', EqualsOperator(), 'b'))
        self.assertEqual(unicode(ds), 'DELETE FROM table WHERE "a" = :0', unicode(ds))

    def test_context_update(self):
        ds = DeleteStatement('table', None)
        ds.add_field(MapDeleteClause('d', {1: 2}, {1:2, 3: 4}))
        ds.add_where_clause(WhereClause('a', EqualsOperator(), 'b'))

        ds.update_context_id(7)
        self.assertEqual(unicode(ds), 'DELETE "d"[:8] FROM table WHERE "a" = :7')
        self.assertEqual(ds.get_context(), {'7': 'b', '8': 3})

    def test_context(self):
        ds = DeleteStatement('table', None)
        ds.add_where_clause(WhereClause('a', EqualsOperator(), 'b'))
        self.assertEqual(ds.get_context(), {'0': 'b'})

########NEW FILE########
__FILENAME__ = test_insert_statement
from unittest import TestCase
from cqlengine.statements import InsertStatement, StatementException, AssignmentClause


class InsertStatementTests(TestCase):

    def test_where_clause_failure(self):
        """ tests that where clauses cannot be added to Insert statements """
        ist = InsertStatement('table', None)
        with self.assertRaises(StatementException):
            ist.add_where_clause('s')

    def test_statement(self):
        ist = InsertStatement('table', None)
        ist.add_assignment_clause(AssignmentClause('a', 'b'))
        ist.add_assignment_clause(AssignmentClause('c', 'd'))

        self.assertEqual(
            unicode(ist),
            'INSERT INTO table ("a", "c") VALUES (:0, :1)'
        )

    def test_context_update(self):
        ist = InsertStatement('table', None)
        ist.add_assignment_clause(AssignmentClause('a', 'b'))
        ist.add_assignment_clause(AssignmentClause('c', 'd'))

        ist.update_context_id(4)
        self.assertEqual(
            unicode(ist),
            'INSERT INTO table ("a", "c") VALUES (:4, :5)'
        )
        ctx = ist.get_context()
        self.assertEqual(ctx, {'4': 'b', '5': 'd'})

    def test_additional_rendering(self):
        ist = InsertStatement('table', ttl=60)
        ist.add_assignment_clause(AssignmentClause('a', 'b'))
        ist.add_assignment_clause(AssignmentClause('c', 'd'))
        self.assertIn('USING TTL 60', unicode(ist))

########NEW FILE########
__FILENAME__ = test_quoter

########NEW FILE########
__FILENAME__ = test_select_statement
from unittest import TestCase
from cqlengine.statements import SelectStatement, WhereClause
from cqlengine.operators import *


class SelectStatementTests(TestCase):

    def test_single_field_is_listified(self):
        """ tests that passing a string field into the constructor puts it into a list """
        ss = SelectStatement('table', 'field')
        self.assertEqual(ss.fields, ['field'])

    def test_field_rendering(self):
        """ tests that fields are properly added to the select statement """
        ss = SelectStatement('table', ['f1', 'f2'])
        self.assertTrue(unicode(ss).startswith('SELECT "f1", "f2"'), unicode(ss))
        self.assertTrue(str(ss).startswith('SELECT "f1", "f2"'), str(ss))

    def test_none_fields_rendering(self):
        """ tests that a '*' is added if no fields are passed in """
        ss = SelectStatement('table')
        self.assertTrue(unicode(ss).startswith('SELECT *'), unicode(ss))
        self.assertTrue(str(ss).startswith('SELECT *'), str(ss))

    def test_table_rendering(self):
        ss = SelectStatement('table')
        self.assertTrue(unicode(ss).startswith('SELECT * FROM table'), unicode(ss))
        self.assertTrue(str(ss).startswith('SELECT * FROM table'), str(ss))

    def test_where_clause_rendering(self):
        ss = SelectStatement('table')
        ss.add_where_clause(WhereClause('a', EqualsOperator(), 'b'))
        self.assertEqual(unicode(ss), 'SELECT * FROM table WHERE "a" = :0', unicode(ss))

    def test_count(self):
        ss = SelectStatement('table', count=True, limit=10, order_by='d')
        ss.add_where_clause(WhereClause('a', EqualsOperator(), 'b'))
        self.assertEqual(unicode(ss), 'SELECT COUNT(*) FROM table WHERE "a" = :0', unicode(ss))
        self.assertNotIn('LIMIT', unicode(ss))
        self.assertNotIn('ORDER', unicode(ss))

    def test_context(self):
        ss = SelectStatement('table')
        ss.add_where_clause(WhereClause('a', EqualsOperator(), 'b'))
        self.assertEqual(ss.get_context(), {'0': 'b'})

    def test_context_id_update(self):
        """ tests that the right things happen the the context id """
        ss = SelectStatement('table')
        ss.add_where_clause(WhereClause('a', EqualsOperator(), 'b'))
        self.assertEqual(ss.get_context(), {'0': 'b'})
        self.assertEqual(str(ss), 'SELECT * FROM table WHERE "a" = :0')

        ss.update_context_id(5)
        self.assertEqual(ss.get_context(), {'5': 'b'})
        self.assertEqual(str(ss), 'SELECT * FROM table WHERE "a" = :5')

    def test_additional_rendering(self):
        ss = SelectStatement(
            'table',
            None,
            order_by=['x', 'y'],
            limit=15,
            allow_filtering=True
        )
        qstr = unicode(ss)
        self.assertIn('LIMIT 15', qstr)
        self.assertIn('ORDER BY x, y', qstr)
        self.assertIn('ALLOW FILTERING', qstr)


########NEW FILE########
__FILENAME__ = test_update_statement
from unittest import TestCase
from cqlengine.statements import UpdateStatement, WhereClause, AssignmentClause
from cqlengine.operators import *


class UpdateStatementTests(TestCase):

    def test_table_rendering(self):
        """ tests that fields are properly added to the select statement """
        us = UpdateStatement('table')
        self.assertTrue(unicode(us).startswith('UPDATE table SET'), unicode(us))
        self.assertTrue(str(us).startswith('UPDATE table SET'), str(us))

    def test_rendering(self):
        us = UpdateStatement('table')
        us.add_assignment_clause(AssignmentClause('a', 'b'))
        us.add_assignment_clause(AssignmentClause('c', 'd'))
        us.add_where_clause(WhereClause('a', EqualsOperator(), 'x'))
        self.assertEqual(unicode(us), 'UPDATE table SET "a" = :0, "c" = :1 WHERE "a" = :2', unicode(us))

    def test_context(self):
        us = UpdateStatement('table')
        us.add_assignment_clause(AssignmentClause('a', 'b'))
        us.add_assignment_clause(AssignmentClause('c', 'd'))
        us.add_where_clause(WhereClause('a', EqualsOperator(), 'x'))
        self.assertEqual(us.get_context(), {'0': 'b', '1': 'd', '2': 'x'})

    def test_context_update(self):
        us = UpdateStatement('table')
        us.add_assignment_clause(AssignmentClause('a', 'b'))
        us.add_assignment_clause(AssignmentClause('c', 'd'))
        us.add_where_clause(WhereClause('a', EqualsOperator(), 'x'))
        us.update_context_id(3)
        self.assertEqual(unicode(us), 'UPDATE table SET "a" = :4, "c" = :5 WHERE "a" = :3')
        self.assertEqual(us.get_context(), {'4': 'b', '5': 'd', '3': 'x'})

    def test_additional_rendering(self):
        us = UpdateStatement('table', ttl=60)
        us.add_assignment_clause(AssignmentClause('a', 'b'))
        us.add_where_clause(WhereClause('a', EqualsOperator(), 'x'))
        self.assertIn('USING TTL 60', unicode(us))


########NEW FILE########
__FILENAME__ = test_where_clause
from unittest import TestCase
from cqlengine.operators import EqualsOperator
from cqlengine.statements import StatementException, WhereClause


class TestWhereClause(TestCase):

    def test_operator_check(self):
        """ tests that creating a where statement with a non BaseWhereOperator object fails """
        with self.assertRaises(StatementException):
            WhereClause('a', 'b', 'c')

    def test_where_clause_rendering(self):
        """ tests that where clauses are rendered properly """
        wc = WhereClause('a', EqualsOperator(), 'c')
        wc.set_context_id(5)
        self.assertEqual('"a" = :5', unicode(wc))
        self.assertEqual('"a" = :5', str(wc))

    def test_equality_method(self):
        """ tests that 2 identical where clauses evaluate as == """
        wc1 = WhereClause('a', EqualsOperator(), 'c')
        wc2 = WhereClause('a', EqualsOperator(), 'c')
        assert wc1 == wc2

########NEW FILE########
__FILENAME__ = test_batch_query
from unittest import skip
from uuid import uuid4
import random
from cqlengine.connection import ConnectionPool

import mock
import sure

from cqlengine import Model, columns
from cqlengine.management import drop_table, sync_table
from cqlengine.query import BatchQuery
from cqlengine.tests.base import BaseCassEngTestCase

class TestMultiKeyModel(Model):
    partition   = columns.Integer(primary_key=True)
    cluster     = columns.Integer(primary_key=True)
    count       = columns.Integer(required=False)
    text        = columns.Text(required=False)


class BatchQueryTests(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BatchQueryTests, cls).setUpClass()
        drop_table(TestMultiKeyModel)
        sync_table(TestMultiKeyModel)

    @classmethod
    def tearDownClass(cls):
        super(BatchQueryTests, cls).tearDownClass()
        drop_table(TestMultiKeyModel)

    def setUp(self):
        super(BatchQueryTests, self).setUp()
        self.pkey = 1
        for obj in TestMultiKeyModel.filter(partition=self.pkey):
            obj.delete()

    def test_insert_success_case(self):

        b = BatchQuery()
        inst = TestMultiKeyModel.batch(b).create(partition=self.pkey, cluster=2, count=3, text='4')

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_update_success_case(self):

        inst = TestMultiKeyModel.create(partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.count = 4
        inst.batch(b).save()

        inst2 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst2.count == 3

        b.execute()

        inst3 = TestMultiKeyModel.get(partition=self.pkey, cluster=2)
        assert inst3.count == 4

    def test_delete_success_case(self):

        inst = TestMultiKeyModel.create(partition=self.pkey, cluster=2, count=3, text='4')

        b = BatchQuery()

        inst.batch(b).delete()

        TestMultiKeyModel.get(partition=self.pkey, cluster=2)

        b.execute()

        with self.assertRaises(TestMultiKeyModel.DoesNotExist):
            TestMultiKeyModel.get(partition=self.pkey, cluster=2)

    def test_context_manager(self):

        with BatchQuery() as b:
            for i in range(5):
                TestMultiKeyModel.batch(b).create(partition=self.pkey, cluster=i, count=3, text='4')

            for i in range(5):
                with self.assertRaises(TestMultiKeyModel.DoesNotExist):
                    TestMultiKeyModel.get(partition=self.pkey, cluster=i)

        for i in range(5):
            TestMultiKeyModel.get(partition=self.pkey, cluster=i)

    def test_bulk_delete_success_case(self):

        for i in range(1):
            for j in range(5):
                TestMultiKeyModel.create(partition=i, cluster=j, count=i*j, text='{}:{}'.format(i,j))

        with BatchQuery() as b:
            TestMultiKeyModel.objects.batch(b).filter(partition=0).delete()
            assert TestMultiKeyModel.filter(partition=0).count() == 5

        assert TestMultiKeyModel.filter(partition=0).count() == 0
        #cleanup
        for m in TestMultiKeyModel.all():
            m.delete()

    def test_empty_batch(self):
        b = BatchQuery()
        b.execute()

        with BatchQuery() as b:
            pass

class BatchQueryCallbacksTests(BaseCassEngTestCase):

    def test_API_managing_callbacks(self):

        # Callbacks can be added at init and after

        def my_callback(*args, **kwargs):
            pass

        # adding on init:
        batch = BatchQuery()

        batch.add_callback(my_callback)
        batch.add_callback(my_callback, 2, named_arg='value')
        batch.add_callback(my_callback, 1, 3)

        assert batch._callbacks == [
            (my_callback, (), {}),
            (my_callback, (2,), {'named_arg':'value'}),
            (my_callback, (1, 3), {})
        ]

    def test_callbacks_properly_execute_callables_and_tuples(self):

        call_history = []
        def my_callback(*args, **kwargs):
            call_history.append(args)

        # adding on init:
        batch = BatchQuery()

        batch.add_callback(my_callback)
        batch.add_callback(my_callback, 'more', 'args')

        batch.execute()

        assert len(call_history) == 2
        assert [(), ('more', 'args')] == call_history

    def test_callbacks_tied_to_execute(self):
        """Batch callbacks should NOT fire if batch is not executed in context manager mode"""

        call_history = []
        def my_callback(*args, **kwargs):
            call_history.append(args)

        with BatchQuery() as batch:
            batch.add_callback(my_callback)
            pass

        assert len(call_history) == 1

        class SomeError(Exception):
            pass

        with self.assertRaises(SomeError):
            with BatchQuery() as batch:
                batch.add_callback(my_callback)
                # this error bubbling up through context manager
                # should prevent callback runs (along with b.execute())
                raise SomeError

        # still same call history. Nothing added
        assert len(call_history) == 1

        # but if execute ran, even with an error bubbling through
        # the callbacks also would have fired
        with self.assertRaises(SomeError):
            with BatchQuery(execute_on_exception=True) as batch:
                batch.add_callback(my_callback)
                # this error bubbling up through context manager
                # should prevent callback runs (along with b.execute())
                raise SomeError

        # still same call history
        assert len(call_history) == 2

########NEW FILE########
__FILENAME__ = test_consistency
from cqlengine.management import sync_table, drop_table
from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine.models import Model
from uuid import uuid4
from cqlengine import columns
import mock
from cqlengine.connection import ConnectionPool
from cqlengine import ALL, BatchQuery

class TestConsistencyModel(Model):
    id      = columns.UUID(primary_key=True, default=lambda:uuid4())
    count   = columns.Integer()
    text    = columns.Text(required=False)

class BaseConsistencyTest(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseConsistencyTest, cls).setUpClass()
        sync_table(TestConsistencyModel)

    @classmethod
    def tearDownClass(cls):
        super(BaseConsistencyTest, cls).tearDownClass()
        drop_table(TestConsistencyModel)


class TestConsistency(BaseConsistencyTest):
    def test_create_uses_consistency(self):

        qs = TestConsistencyModel.consistency(ALL)
        with mock.patch.object(ConnectionPool, 'execute') as m:
            qs.create(text="i am not fault tolerant this way")

        args = m.call_args
        self.assertEqual(ALL, args[0][2])

    def test_queryset_is_returned_on_create(self):
        qs = TestConsistencyModel.consistency(ALL)
        self.assertTrue(isinstance(qs, TestConsistencyModel.__queryset__), type(qs))

    def test_update_uses_consistency(self):
        t = TestConsistencyModel.create(text="bacon and eggs")
        t.text = "ham sandwich"

        with mock.patch.object(ConnectionPool, 'execute') as m:
            t.consistency(ALL).save()

        args = m.call_args
        self.assertEqual(ALL, args[0][2])


    def test_batch_consistency(self):

        with mock.patch.object(ConnectionPool, 'execute') as m:
            with BatchQuery(consistency=ALL) as b:
                TestConsistencyModel.batch(b).create(text="monkey")

        args = m.call_args
        self.assertEqual(ALL, args[0][2])

        with mock.patch.object(ConnectionPool, 'execute') as m:
            with BatchQuery() as b:
                TestConsistencyModel.batch(b).create(text="monkey")

        args = m.call_args
        self.assertNotEqual(ALL, args[0][2])

    def test_blind_update(self):
        t = TestConsistencyModel.create(text="bacon and eggs")
        t.text = "ham sandwich"
        uid = t.id

        with mock.patch.object(ConnectionPool, 'execute') as m:
            TestConsistencyModel.objects(id=uid).consistency(ALL).update(text="grilled cheese")

        args = m.call_args
        self.assertEqual(ALL, args[0][2])


    def test_delete(self):
        # ensures we always carry consistency through on delete statements
        t = TestConsistencyModel.create(text="bacon and eggs")
        t.text = "ham and cheese sandwich"
        uid = t.id

        with mock.patch.object(ConnectionPool, 'execute') as m:
            t.consistency(ALL).delete()

        with mock.patch.object(ConnectionPool, 'execute') as m:
            TestConsistencyModel.objects(id=uid).consistency(ALL).delete()

        args = m.call_args
        self.assertEqual(ALL, args[0][2])

########NEW FILE########
__FILENAME__ = test_timestamp
"""
Tests surrounding the blah.timestamp( timedelta(seconds=30) ) format.
"""
from datetime import timedelta, datetime

from uuid import uuid4
import mock
import sure
from cqlengine import Model, columns, BatchQuery
from cqlengine.connection import ConnectionPool
from cqlengine.management import sync_table
from cqlengine.tests.base import BaseCassEngTestCase


class TestTimestampModel(Model):
    id      = columns.UUID(primary_key=True, default=lambda:uuid4())
    count   = columns.Integer()


class BaseTimestampTest(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseTimestampTest, cls).setUpClass()
        sync_table(TestTimestampModel)


class BatchTest(BaseTimestampTest):

    def test_batch_is_included(self):
        with mock.patch.object(ConnectionPool, "execute") as m, BatchQuery(timestamp=timedelta(seconds=30)) as b:
            TestTimestampModel.batch(b).create(count=1)

        "USING TIMESTAMP".should.be.within(m.call_args[0][0])


class CreateWithTimestampTest(BaseTimestampTest):

    def test_batch(self):
        with mock.patch.object(ConnectionPool, "execute") as m, BatchQuery() as b:
            TestTimestampModel.timestamp(timedelta(seconds=10)).batch(b).create(count=1)

        query = m.call_args[0][0]

        query.should.match(r"INSERT.*USING TIMESTAMP")
        query.should_not.match(r"TIMESTAMP.*INSERT")

    def test_timestamp_not_included_on_normal_create(self):
        with mock.patch.object(ConnectionPool, "execute") as m:
            TestTimestampModel.create(count=2)

        "USING TIMESTAMP".shouldnt.be.within(m.call_args[0][0])

    def test_timestamp_is_set_on_model_queryset(self):
        delta = timedelta(seconds=30)
        tmp = TestTimestampModel.timestamp(delta)
        tmp._timestamp.should.equal(delta)

    def test_non_batch_syntax_integration(self):
        tmp = TestTimestampModel.timestamp(timedelta(seconds=30)).create(count=1)
        tmp.should.be.ok

    def test_non_batch_syntax_unit(self):

        with mock.patch.object(ConnectionPool, "execute") as m:
            TestTimestampModel.timestamp(timedelta(seconds=30)).create(count=1)

        query = m.call_args[0][0]

        "USING TIMESTAMP".should.be.within(query)


class UpdateWithTimestampTest(BaseTimestampTest):
    def setUp(self):
        self.instance = TestTimestampModel.create(count=1)

    def test_instance_update_includes_timestamp_in_query(self):
        # not a batch

        with mock.patch.object(ConnectionPool, "execute") as m:
            self.instance.timestamp(timedelta(seconds=30)).update(count=2)

        "USING TIMESTAMP".should.be.within(m.call_args[0][0])

    def test_instance_update_in_batch(self):
        with mock.patch.object(ConnectionPool, "execute") as m, BatchQuery() as b:
            self.instance.batch(b).timestamp(timedelta(seconds=30)).update(count=2)

        query = m.call_args[0][0]
        "USING TIMESTAMP".should.be.within(query)


class DeleteWithTimestampTest(BaseTimestampTest):

    def test_non_batch(self):
        """
        we don't expect the model to come back at the end because the deletion timestamp should be in the future
        """
        uid = uuid4()
        tmp = TestTimestampModel.create(id=uid, count=1)

        TestTimestampModel.get(id=uid).should.be.ok

        tmp.timestamp(timedelta(seconds=5)).delete()

        with self.assertRaises(TestTimestampModel.DoesNotExist):
            TestTimestampModel.get(id=uid)

        tmp = TestTimestampModel.create(id=uid, count=1)

        with self.assertRaises(TestTimestampModel.DoesNotExist):
            TestTimestampModel.get(id=uid)

        # calling .timestamp sets the TS on the model
        tmp.timestamp(timedelta(seconds=5))
        tmp._timestamp.should.be.ok

        # calling save clears the set timestamp
        tmp.save()
        tmp._timestamp.shouldnt.be.ok

        tmp.timestamp(timedelta(seconds=5))
        tmp.update()
        tmp._timestamp.shouldnt.be.ok

    def test_blind_delete(self):
        """
        we don't expect the model to come back at the end because the deletion timestamp should be in the future
        """
        uid = uuid4()
        tmp = TestTimestampModel.create(id=uid, count=1)

        TestTimestampModel.get(id=uid).should.be.ok

        TestTimestampModel.objects(id=uid).timestamp(timedelta(seconds=5)).delete()

        with self.assertRaises(TestTimestampModel.DoesNotExist):
            TestTimestampModel.get(id=uid)

        tmp = TestTimestampModel.create(id=uid, count=1)

        with self.assertRaises(TestTimestampModel.DoesNotExist):
            TestTimestampModel.get(id=uid)

    def test_blind_delete_with_datetime(self):
        """
        we don't expect the model to come back at the end because the deletion timestamp should be in the future
        """
        uid = uuid4()
        tmp = TestTimestampModel.create(id=uid, count=1)

        TestTimestampModel.get(id=uid).should.be.ok

        plus_five_seconds = datetime.now() + timedelta(seconds=5)

        TestTimestampModel.objects(id=uid).timestamp(plus_five_seconds).delete()

        with self.assertRaises(TestTimestampModel.DoesNotExist):
            TestTimestampModel.get(id=uid)

        tmp = TestTimestampModel.create(id=uid, count=1)

        with self.assertRaises(TestTimestampModel.DoesNotExist):
            TestTimestampModel.get(id=uid)

    def test_delete_in_the_past(self):
        uid = uuid4()
        tmp = TestTimestampModel.create(id=uid, count=1)

        TestTimestampModel.get(id=uid).should.be.ok

        # delete the in past, should not affect the object created above
        TestTimestampModel.objects(id=uid).timestamp(timedelta(seconds=-60)).delete()

        TestTimestampModel.get(id=uid)



########NEW FILE########
__FILENAME__ = test_ttl
from cqlengine.management import sync_table, drop_table
from cqlengine.tests.base import BaseCassEngTestCase
from cqlengine.models import Model
from uuid import uuid4
from cqlengine import columns
import mock
from cqlengine.connection import ConnectionPool

class TestTTLModel(Model):
    id      = columns.UUID(primary_key=True, default=lambda:uuid4())
    count   = columns.Integer()
    text    = columns.Text(required=False)


class BaseTTLTest(BaseCassEngTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseTTLTest, cls).setUpClass()
        sync_table(TestTTLModel)

    @classmethod
    def tearDownClass(cls):
        super(BaseTTLTest, cls).tearDownClass()
        drop_table(TestTTLModel)



class TTLQueryTests(BaseTTLTest):

    def test_update_queryset_ttl_success_case(self):
        """ tests that ttls on querysets work as expected """

    def test_select_ttl_failure(self):
        """ tests that ttls on select queries raise an exception """


class TTLModelTests(BaseTTLTest):

    def test_ttl_included_on_create(self):
        """ tests that ttls on models work as expected """
        with mock.patch.object(ConnectionPool, 'execute') as m:
            TestTTLModel.ttl(60).create(text="hello blake")

        query = m.call_args[0][0]
        self.assertIn("USING TTL", query)

    def test_queryset_is_returned_on_class(self):
        """
        ensures we get a queryset descriptor back
        """
        qs = TestTTLModel.ttl(60)
        self.assertTrue(isinstance(qs, TestTTLModel.__queryset__), type(qs))



class TTLInstanceUpdateTest(BaseTTLTest):
    def test_update_includes_ttl(self):
        model = TestTTLModel.create(text="goodbye blake")
        with mock.patch.object(ConnectionPool, 'execute') as m:
            model.ttl(60).update(text="goodbye forever")

        query = m.call_args[0][0]
        self.assertIn("USING TTL", query)

    def test_update_syntax_valid(self):
        # sanity test that ensures the TTL syntax is accepted by cassandra
        model = TestTTLModel.create(text="goodbye blake")
        model.ttl(60).update(text="goodbye forever")





class TTLInstanceTest(BaseTTLTest):
    def test_instance_is_returned(self):
        """
        ensures that we properly handle the instance.ttl(60).save() scenario
        :return:
        """
        o = TestTTLModel.create(text="whatever")
        o.text = "new stuff"
        o = o.ttl(60)
        self.assertEqual(60, o._ttl)

    def test_ttl_is_include_with_query_on_update(self):
        o = TestTTLModel.create(text="whatever")
        o.text = "new stuff"
        o = o.ttl(60)

        with mock.patch.object(ConnectionPool, 'execute') as m:
            o.save()
        query = m.call_args[0][0]
        self.assertIn("USING TTL", query)


class TTLBlindUpdateTest(BaseTTLTest):
    def test_ttl_included_with_blind_update(self):
        o = TestTTLModel.create(text="whatever")
        tid = o.id

        with mock.patch.object(ConnectionPool, 'execute') as m:
            TestTTLModel.objects(id=tid).ttl(60).update(text="bacon")

        query = m.call_args[0][0]
        self.assertIn("USING TTL", query)





########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# cqlengine documentation build configuration file, created by
# sphinx-quickstart on Sat Dec  1 09:50:49 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.pngmath', 'sphinx.ext.mathjax']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'cqlengine'
copyright = u'2012, Blake Eggleston'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
__cqlengine_version_path__ = os.path.realpath(__file__ + '/../../cqlengine/VERSION')
# The short X.Y version.
version = open(__cqlengine_version_path__, 'r').readline().strip()
# The full version, including alpha/beta/rc tags.
release = version


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
htmlhelp_basename = 'cqlenginedoc'


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
    ('index', 'cqlengine.tex', u'cqlengine Documentation', u'Blake Eggleston', 'manual'),
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
    ('index', 'cqlengine', u'cqlengine Documentation',
     [u'Blake Eggleston'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'cqlengine', u'cqlengine Documentation',
     u'Blake Eggleston', 'cqlengine', 'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
