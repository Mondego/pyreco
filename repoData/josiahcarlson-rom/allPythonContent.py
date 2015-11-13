__FILENAME__ = columns

from datetime import datetime, date, time as dtime
from decimal import Decimal as _Decimal
import json

import six

from .exceptions import (ORMError, InvalidOperation, ColumnError,
    MissingColumn, InvalidColumnValue)
from .util import (_numeric_keygen, _string_keygen, _many_to_one_keygen,
    _boolean_keygen, dt2ts, ts2dt, t2ts, ts2t, session, _connect)

NULL = object()
MODELS = {}
_NUMERIC = (0, 0.0, _Decimal('0'), datetime(1970, 1, 1), date(1970, 1, 1), dtime(0, 0, 0))
USE_LUA = True

class Column(object):
    '''
    Column objects handle data conversion to/from strings, store metadata
    about indices, etc. Note that these are "heavy" columns, in that whenever
    data is read/written, it must go through descriptor processing. This is
    primarily so that (for example) if you try to write a Decimal to a Float
    column, you get an error the moment you try to do it, not some time later
    when you try to save the object (though saving can still cause an error
    during the conversion process).

    Standard Arguments:

        * *required* - determines whether this column is required on
          creation
        * *default* - a default value (either a callable or a simple value)
          when this column is not provided
        * *unique* - can only be enabled on ``String`` columns, allows for
          required distinct column values (like an email address on a User
          model)
        * *index* - can be enabled on numeric, string, and unicode columns.
          Will create a ZSET-based numeric index for numeric columns and a
          "full word"-based search for string/unicode columns. If enabled
          for other (or custom) columns, remember to provide the
          ``keygen`` argument
        * *keygen* - pass a function that takes your column's value and
          returns the data that you want to index (see the keygen docs for
          what kinds of data to return)
        * *prefix* - can be enabled on any column that generates a list of
          strings as a result of the default or passed *keygen* function, and
          will allow the searching of prefix matches (autocomplete) over your
          data
        * *suffix* - can be enabled in the same contexts as *prefix* and
          enables suffix matching over your data. Any individual string in the
          returned data will be reversed (you need to make sure this makes
          conceptual sense with your data) before being stored or used.

    .. warning: Enabling prefix or suffix matching on a column only makes
       sense for columns defining a non-numeric *keygen* function.

    Notes:

        * Columns with *unique* set to True can only be string columns
        * If you have disabled Lua support, you can only have at most one
          unique column on each model
        * *Unique* and *index* are not mutually exclusive
        * The *keygen* argument determines how index values are generated
          from column data (with reasonably sensible defaults for numeric
          and string columns)
        * If you set *required* to True, then you must have the column set
          during object construction: ``MyModel(col=val)``
        * If *index* and *prefix*, or *index* and *suffix* are set, the same
          keygen for both the regular *index* as well as the *prefix* and/or
          *suffix* searches
        * If *prefix* is set, you can perform pattern matches over your data.
          See documention for ``Query.like()`` for details.
        * Pattern matching over data is only guaranteed to be valid or correct
          for ANSI strings that do not include nulls, though we make an effort
          to support
        * Prefix, suffix, and pattern matching are performed within a Lua
          script, so may have substantial execution time if there are a large
          number of matching prefix or suffix entries
        * Whenever possible, pattern matching will attempt to use any
          non-wildcard prefixes on the pattern to limit the items to be
          scanned. A pattern starting with ``?``, ``*``, ``+``, or ``!`` will
          not be able to use any prefix, so will scan the entire index for
          matches (aka: expensive)
    '''
    _allowed = ()
    _default_ = None

    __slots__ = '_required _default _init _unique _index _model _attr _keygen _prefix _suffix'.split()

    def __init__(self, required=False, default=NULL, unique=False, index=False, keygen=None, prefix=False, suffix=False):
        self._required = required
        self._default = default
        self._unique = unique
        self._index = index
        self._prefix = prefix
        self._suffix = suffix
        self._init = False
        self._model = None
        self._attr = None
        self._keygen = None

        if not self._allowed and not hasattr(self, '_fmodel') and not hasattr(self, '_ftable'):
            raise ColumnError("Missing valid _allowed attribute")

        allowed = (self._allowed,) if isinstance(self._allowed, type) else self._allowed
        is_string = all(issubclass(x, six.string_types) for x in allowed)
        if unique:
            if not is_string:
                raise ColumnError("Unique columns can only be strings")

        numeric = True
        if index and not isinstance(self, ManyToOne):
            if not any(isinstance(i, allowed) for i in _NUMERIC):
                numeric = False
                if issubclass(bool, allowed):
                    keygen = keygen or _boolean_keygen
                if not is_string and not keygen:
                    raise ColumnError("Non-numeric/string indexed columns must provide keygen argument on creation")

        if index:
            self._keygen = keygen if keygen else (
                _numeric_keygen if numeric else _string_keygen)
        elif prefix or suffix:
            self._keygen = keygen if keygen else _string_keygen

    def _from_redis(self, value):
        convert = self._allowed[0] if isinstance(self._allowed, (tuple, list)) else self._allowed
        return convert(value)

    def _to_redis(self, value):
        return repr(value)

    def _validate(self, value):
        if value is not None:
            if isinstance(value, self._allowed):
                return
        elif not self._required:
            return
        raise InvalidColumnValue("%s.%s has type %r but must be of type %r"%(
            self._model, self._attr, type(value), self._allowed))

    def _init_(self, obj, model, attr, value, loading):
        # You shouldn't be calling this directly, but this is what sets up all
        # of the necessary pieces when creating an entity from scratch, or
        # loading the entity from Redis
        self._model = model
        self._attr = attr

        if value is None:
            if self._default is NULL:
                if self._required:
                    raise MissingColumn("%s.%s cannot be missing"%(self._model, self._attr))
            elif callable(self._default):
                value = self._default()
            else:
                value = self._default
        elif not isinstance(value, self._allowed):
            try:
                value = self._from_redis(value)
            except (ValueError, TypeError) as e:
                raise InvalidColumnValue(*e.args)

        if not loading:
            self._validate(value)
        obj._data[attr] = value

    def __set__(self, obj, value):
        if not obj._init:
            self._init_(obj, *value)
            return
        try:
            if not isinstance(value, self._allowed):
                value = self._from_redis(value)
        except (ValueError, TypeError):
            raise InvalidColumnValue("Cannot convert %r into type %s"%(value, self._allowed))
        self._validate(value)
        obj._data[self._attr] = value
        obj._modified = True
        session.add(obj)

    def __get__(self, obj, objtype):
        try:
            return obj._data[self._attr]
        except KeyError:
            AttributeError("%s.%s does not exist"%(self._model, self._attr))

    def __delete__(self, obj):
        if self._required:
            raise InvalidOperation("%s.%s cannot be null"%(self._model, self._attr))
        try:
            obj._data.pop(self._attr)
        except KeyError:
            raise AttributeError("%s.%s does not exist"%(self._model, self._attr))
        obj._modified = True
        session.add(obj)

class Integer(Column):
    '''
    Used for integer numeric columns.

    All standard arguments supported.

    Used via::

        class MyModel(Model):
            col = Integer()
    '''
    _allowed = six.integer_types
    def _to_redis(self, value):
        return str(value)

class Boolean(Column):
    '''
    Used for boolean columns.

    All standard arguments supported.

    All values passed in on creation are casted via bool(), with the exception
    of None (which behaves as though the value was missing), and any existing
    data in Redis is considered ``False`` if empty, and ``True`` otherwise.

    Used via::

        class MyModel(Model):
            col = Boolean()

    Queries via ``MyModel.get_by(...)`` and ``MyModel.query.filter(...)`` work
    as expected when passed ``True`` or ``False``.

    .. note: these columns are not sortable by default.
    '''
    _allowed = bool
    def _to_redis(self, obj):
        return '1' if obj else ''
    def _from_redis(self, obj):
        return bool(obj)

class Float(Column):
    '''
    Numeric column that supports integers and floats (values are turned into
    floats on load from Redis).

    All standard arguments supported.

    Used via::

        class MyModel(Model):
            col = Float()
    '''
    _allowed = (float,) + six.integer_types

class Decimal(Column):
    '''
    A Decimal-only numeric column (converts ints/longs into Decimals
    automatically). Attempts to assign Python float will fail.

    All standard arguments supported.

    Used via::

        class MyModel(Model):
            col = Decimal()
    '''
    _allowed = _Decimal
    def _from_redis(self, value):
        return _Decimal(value)
    def _to_redis(self, value):
        return str(value)

class DateTime(Column):
    '''
    A datetime column.

    All standard arguments supported.

    Used via::

        class MyModel(Model):
            col = DateTime()

    .. note:: tzinfo objects are not stored
    '''
    _allowed = datetime
    def _from_redis(self, value):
        return ts2dt(float(value))
    def _to_redis(self, value):
        return repr(dt2ts(value))

class Date(Column):
    '''
    A date column.

    All standard arguments supported.

    Used via::

        class MyModel(Model):
            col = Date()
    '''
    _allowed = date
    def _from_redis(self, value):
        return ts2dt(float(value)).date()
    def _to_redis(self, value):
        return repr(dt2ts(value))

class Time(Column):
    '''
    A time column. Timezones are ignored.

    All standard arguments supported.

    Used via::

        class MyModel(Model):
            col = Time()

    .. note:: tzinfo objects are not stored
    '''
    _allowed = dtime
    def _from_redis(self, value):
        return ts2t(float(value))
    def _to_redis(self, value):
        return repr(t2ts(value))

if six.PY2:
    class String(Column):
        '''
        .. note:: this column type is only available in Python 2.x

        A plain string column. Trying to save unicode strings will probably result
        in an error, if not bad data.

        All standard arguments supported.

        This column can be indexed, which will allow for searching for words
        contained in the column, extracted via::

            filter(None, [s.lower().strip(string.punctuation) for s in val.split()])

        .. note:: if Lua writing is disabled, only one String column per model can
         be used.

        Used via::

            class MyModel(Model):
                col = String()
        '''
        _allowed = str
        def _to_redis(self, value):
            return value

class Text(Column):
    '''
    A unicode string column. All standard arguments supported. Behavior is
    more or less identical to the String column type, except that unicode is
    supported (unicode in 2.x, str in 3.x). UTF-8 is used by default as the
    encoding to bytes on the wire.

    Used via::

        class MyModel(Model):
            col = Text()
    '''
    _allowed = six.text_type
    def _to_redis(self, value):
        return value.encode('utf-8') if six.PY2 or not USE_LUA else value
    def _from_redis(self, value):
        if isinstance(value, six.binary_type):
            return value.decode('utf-8')
        return value

class Json(Column):
    '''
    Allows for more complicated nested structures as attributes.

    All standard arguments supported. The ``keygen`` argument must be provided
    if ``index`` is ``True``.

    Used via::

        class MyModel(Model):
            col = Json()
    '''
    _allowed = (dict, list, tuple)
    def _to_redis(self, value):
        return json.dumps(value)
    def _from_redis(self, value):
        if isinstance(value, self._allowed):
            return value
        return json.loads(value)

class PrimaryKey(Column):
    '''
    This is a primary key column, used when you want the primary key to be
    named something other than 'id'. If you omit a PrimaryKey column on your
    Model classes, one will be automatically cretaed for you.

    Only the ``index`` argument will be used. You may want to enable indexing
    on this column if you want to be able to perform queries and sort the
    results by primary key.

    Used via:

        class MyModel(Model):
            id = PrimaryKey()
    '''
    _allowed = six.integer_types

    def __init__(self, index=False):
        Column.__init__(self, required=False, default=None, unique=False, index=index)

    def _init_(self, obj, model, attr, value, loading):
        self._model = model
        self._attr = attr
        if value is None:
            value = _connect(obj).incr('%s:%s:'%(model, attr))
            obj._modified = True
        else:
            value = int(value)
        obj._data[attr] = value
        session.add(obj)

    def __set__(self, obj, value):
        if not obj._init:
            self._init_(obj, *value)
            return
        raise InvalidOperation("Cannot update primary key value")

class ManyToOne(Column):
    '''
    This ManyToOne column allows for one model to reference another model.
    While a ManyToOne column does not require a reverse OneToMany column
    (which will return a list of models that reference it via a ManyToOne), it
    is generally seen as being useful to have both sides of the relationship
    defined.

    Aside from the name of the other model, only the ``required`` and
    ``default`` arguments are accepted.

    Used via::

        class MyModel(Model):
            col = ManyToOne('OtherModelName')

    .. note: Technically, all ``ManyToOne`` columns are indexed numerically,
      which means that you can find entities with specific id ranges or even
      sort by the ids referenced.

    '''
    __slots__ = Column.__slots__ + ['_ftable']
    def __init__(self, ftable, required=False, default=NULL):
        self._ftable = ftable
        Column.__init__(self, required, default, index=True, keygen=_many_to_one_keygen)

    def _from_redis(self, value):
        try:
            model = MODELS[self._ftable]
        except KeyError:
            raise ORMError("Missing foreign table %r referenced by %s.%s"%(self._ftable, self._model, self._attr))
        if isinstance(value, model):
            return value
        return model.get(value)

    def _validate(self, value):
        try:
            model = MODELS[self._ftable]
        except KeyError:
            raise ORMError("Missing foreign table %r referenced by %s.%s"%(self._ftable, self._model, self._attr))
        if not self._required and value is None:
            return
        if not isinstance(value, model):
            raise InvalidColumnValue("%s.%s has type %r but must be of type %r"%(
                self._model, self._attr, type(value), model))

    def _to_redis(self, value):
        if not value:
            return None
        if isinstance(value, six.integer_types):
            return str(value)
        if value._new:
            # should spew a warning here
            value.save()
        v = str(getattr(value, value._pkey))
        return v

class ForeignModel(Column):
    '''
    This column allows for ``rom`` models to reference an instance of another
    model from an unrelated ORM or otherwise.

    .. note: In order for this mechanism to work, the foreign model *must*
      have an ``id`` attribute or property represents its primary key, and
      *must* have a classmethod or staticmethod named ``get()`` that returns
      the proper database entity.

    Used via::

        class MyModel(Model):
            col = ForeignModel(DjangoModel)

        dm = DjangoModel(col1='foo')
        django.db.transaction.commit()

        x = MyModel(col=dm)
        x.save()
    '''
    __slots__ = Column.__slots__ + ['_fmodel']
    def __init__(self, fmodel, required=False, default=NULL):
        self._fmodel = fmodel
        Column.__init__(self, required, default, index=True, keygen=_many_to_one_keygen)

    def _from_redis(self, value):
        if isinstance(value, self._fmodel):
            return value
        if isinstance(value, six.string_types) and value.isdigit():
            value = int(value, 10)
        return self._fmodel.get(value)

    def _validate(self, value):
        if not self._required and value is None:
            return
        if not isinstance(value, self._fmodel):
            raise InvalidColumnValue("%s.%s has type %r but must be of type %r"%(
                self._model, self._attr, type(value), self._fmodel))

    def _to_redis(self, value):
        if not value:
            return None
        if isinstance(value, six.integer_types):
            return str(value)
        return str(value.id)

class OneToMany(Column):
    '''
    OneToMany columns do not actually store any information. They rely on a
    properly defined reverse ManyToOne column on the referenced model in order
    to be able to fetch a list of referring entities.

    Only the name of the other model can be passed.

    Used via::

        class MyModel(Model):
            col = OneToMany('OtherModelName')
    '''
    __slots__ = '_model _attr _ftable _required _unique _index _prefix _suffix _keygen'.split()
    def __init__(self, ftable):
        self._ftable = ftable
        self._required = self._unique = self._index = self._prefix = self._suffix = False
        self._model = self._attr = self._keygen = None

    def _to_redis(self, value):
        return ''

    def __set__(self, obj, value):
        if not obj._init:
            self._model, self._attr = value[:2]
            try:
                MODELS[self._ftable]
            except KeyError:
                raise ORMError("Missing foreign table %r referenced by %s.%s"%(self._ftable, self._model, self._attr))
            return
        raise InvalidOperation("Cannot assign to OneToMany relationships")

    def __get__(self, obj, objtype):
        try:
            model = MODELS[self._ftable]
        except KeyError:
            raise ORMError("Missing foreign table %r referenced by %s.%s"%(self._ftable, self._model, self._attr))

        for attr, col in model._columns.items():
            if isinstance(col, ManyToOne) and col._ftable == self._model:
                return model.get_by(**{attr: getattr(obj, obj._pkey)})

        raise ORMError("Reverse ManyToOne relationship not found for %s.%s -> %s"%(self._model, self._attr, self._ftable))

    def __delete__(self, obj):
        raise InvalidOperation("Cannot delete OneToMany relationships")

########NEW FILE########
__FILENAME__ = exceptions

__all__ = '''
    ORMError UniqueKeyViolation InvalidOperation
    QueryError ColumnError MissingColumn
    InvalidColumnValue'''.split()

class ORMError(Exception):
    'Base class for all ORM-related errors'

class UniqueKeyViolation(ORMError):
    'Raised when trying to save an entity without a distinct column value'

class InvalidOperation(ORMError):
    'Raised when trying to delete or modify a column that cannot be deleted or modified'

class QueryError(InvalidOperation):
    'Raised when arguments to ``Model.get_by()`` or ``Query.filter`` are not valid'

class ColumnError(ORMError):
    'Raised when your column definitions are not kosher'

class MissingColumn(ColumnError):
    'Raised when a model has a required column, but it is not provided on construction'

class InvalidColumnValue(ColumnError):
    'Raised when you attempt to pass a primary key on entity creation or when data assigned to a column is the wrong type'

########NEW FILE########
__FILENAME__ = index

from collections import namedtuple
import json
import re
import uuid

import six

from .exceptions import QueryError
from .util import _prefix_score, _script_load, _to_score

Prefix = namedtuple('Prefix', 'attr prefix')
Suffix = namedtuple('Suffix', 'attr suffix')
Pattern = namedtuple('Pattern', 'attr pattern')

SPECIAL = re.compile('([-().%[^$])')
def _pattern_to_lua_pattern(pat):
    if isinstance(pat, six.string_types) and not isinstance(pat, str):
        # XXX: Decode only py2k unicode. Why can't we run the unicode
        # pattern through the re? -JM
        pat = pat.encode('utf-8')
    # We use '-' instead of '*' to get the shortest matches possible, which is
    # usually the desired case for pattern matching.
    return SPECIAL.sub('%\1', pat) \
        .replace('?', '.?') \
        .replace('*', '.-') \
        .replace('+', '.+') \
        .replace('!', '.')

def _find_prefix(pat):
    pat = SPECIAL.sub('%\1', pat)
    if isinstance(pat, six.string_types) and not isinstance(pat, str):
        # XXX: Decode only py2k unicode. Why can't we run the unicode
        # pattern through the re? -JM
        pat = pat.encode('utf-8')
    x = []
    for i in pat:
        if i in '?*+!':
            break
        x.append(i)
    return ''.join(x[:7])

MAX_PREFIX_SCORE = _prefix_score(7*'\xff', True)
def _start_end(prefix):
    return _prefix_score(prefix), (_prefix_score(prefix, True) if prefix else MAX_PREFIX_SCORE)

class GeneralIndex(object):
    '''
    This class implements general indexing and search for the ``rom`` package.

    .. warning: You probably don't want to be calling this directly. Instead,
      you should rely on the ``Query`` object returned from ``Model.query`` to
      handle all of your query pre-processing.

    Generally speaking, numeric indices use ZSETs, and text indices use SETs
    built using an 'inverted index'.

    Say that we have words ``hello world`` in a column ``c`` on a model with
    primary key ``MyModel:1``. The member ``1`` will be added to SETs with
    keys::

        MyModel:c:hello
        MyModel:c:world

    Text searching performs a sequence of intersections of SETs for the words
    to be searched for.

    Numeric range searching performs a sequence of intersections of ZSETs,
    removing items outside the requested range after each intersection.

    Searches will pre-sort intersections from smallest to largest SET/ZSET
    prior to performing the search to improve performance.

    Prefix, suffix, and pattern matching change this operation. Given a key
    generated of ``hello`` on a column ``c`` on a model with primary key
    ``MyModel:1``, the member ``hello\\01`` with score 0 will be added to a
    ZSET with the key name ``MyModel:c:pre`` for the prefix/pattern index.
    On a suffix index, the member ``olleh\\01`` with score 0 will be added to
    a ZSET with the key name ``MyModel:c:suf``.

    Prefix and suffix matches are excuted in Lua with a variant of the
    autocomplete method described in Redis in Action. These methods ensure a
    runtime proportional to the number of matched entries.

    Pattern matching also uses a Lua script to scan over data in the prefix
    index, exploiting prefixes in patterns if they exist.

    '''
    def __init__(self, namespace):
        self.namespace = namespace

    def _unindex(self, conn, pipe, id):
        known = conn.hget(self.namespace + '::', id)
        if not known:
            return 0
        old = json.loads(known.decode())
        keys, scored = old[:2]
        pre, suf = ([],[]) if len(old) == 2 else old[2:]

        for key in keys:
            pipe.srem('%s:%s:idx'%(self.namespace, key), id)
        for key in scored:
            pipe.zrem('%s:%s:idx'%(self.namespace, key), id)
        for attr, key in pre:
            pipe.zrem('%s:%s:pre'%(self.namespace, attr), '%s\0%s'%(key, id))
        for attr, key in suf:
            pipe.zrem('%s:%s:suf'%(self.namespace, attr), '%s\0%s'%(key, id))

        pipe.hdel(self.namespace + '::', id)
        return len(keys) + len(scored)

    def unindex(self, conn, id):
        '''
        Will unindex an entity atomically.

        Arguments:

            * *id* - the id of the entity to remove from the index
        '''
        pipe = conn.pipeline(True)
        ret = self._unindex(conn, pipe, id)
        pipe.execute()
        return ret

    def index(self, conn, id, keys, scores, prefix, suffix, pipe=None):
        '''
        Will index the provided data atomically.

        Arguments:

            * *id* - the id of the entity that is being indexed
            * *keys* - an iterable sequence of keys of the form:
              ``column_name:key`` to index
            * *scores* - a dictionary mapping ``column_name`` to numeric
              scores and/or mapping ``column_name:key`` to numeric scores
            * *prefix* - an iterable sequence of strings that will be used for
              prefix matching
            * *suffix* - an iterable sequence of strings that will be used for
              suffix matching (each string is likely to be a reversed version
              of *pre*, but this is not required)

        This will automatically unindex the provided id before
        indexing/re-indexing.

        Unindexing is possible because we keep a record of all keys, score
        keys, pre, and suf lists that were provided.
        '''
        had_pipe = bool(pipe)
        pipe = pipe or conn.pipeline(True)
        self._unindex(conn, pipe, id)

        for key in keys:
            pipe.sadd('%s:%s:idx'%(self.namespace, key), id)
        for key, score in scores.items():
            pipe.zadd('%s:%s:idx'%(self.namespace, key), id, _to_score(score))
        for attr, key in prefix:
            pipe.zadd('%s:%s:pre'%(self.namespace, attr), '%s\0%s'%(key, id), _prefix_score(key))
        for attr, key in suffix:
            pipe.zadd('%s:%s:suf'%(self.namespace, attr), '%s\0%s'%(key, id), _prefix_score(key))
        pipe.hset(self.namespace + '::', id, json.dumps([list(keys), list(scores), list(prefix), list(suffix)]))
        if not had_pipe:
            pipe.execute()
        return len(keys) + len(scores) + len(prefix) + len(suffix)

    def _prepare(self, conn, filters):
        temp_id = "%s:%s"%(self.namespace, uuid.uuid4())
        pipe = conn.pipeline(True)
        sfilters = filters
        if len(filters) > 1:
            # reorder filters based on the size of the underlying set/zset
            for fltr in filters:
                if isinstance(fltr, six.string_types):
                    pipe.scard('%s:%s:idx'%(self.namespace, fltr))
                elif isinstance(fltr, Prefix):
                    estimate_work_lua(pipe, '%s:%s:pre'%(self.namespace, fltr.attr), fltr.prefix)
                elif isinstance(fltr, Suffix):
                    estimate_work_lua(pipe, '%s:%s:suf'%(self.namespace, fltr.attr), fltr.suffix)
                elif isinstance(fltr, Pattern):
                    estimate_work_lua(pipe, '%s:%s:pre'%(self.namespace, fltr.attr), _find_prefix(fltr.pattern))
                elif isinstance(fltr, (tuple, list)):
                    pipe.zcard('%s:%s:idx'%(self.namespace, fltr[0]))
                else:
                    raise QueryError("Don't know how to handle a filter of: %r"%(fltr,))
            sizes = list(enumerate(pipe.execute()))
            sizes.sort(key=lambda x:x[1])
            sfilters = [filters[x[0]] for x in sizes]

        # the first "intersection" is actually a union to get us started
        intersect = pipe.zunionstore
        first = True
        for fltr in sfilters:
            if isinstance(fltr, list):
                # or string string/tag search
                if len(fltr) == 1:
                    # only 1? Use the simple version.
                    fltr = fltr[0]
                elif not fltr:
                    continue
                else:
                    temp_id2 = str(uuid.uuid4())
                    pipe.zunionstore(temp_id2, dict(
                        ('%s:%s:idx'%(self.namespace, fi), 0) for fi in fltr))
                    intersect(temp_id, {temp_id:0, temp_id2:0})
                    pipe.delete(temp_id2)
            if isinstance(fltr, six.string_types):
                # simple string/tag search
                intersect(temp_id, {temp_id:0, '%s:%s:idx'%(self.namespace, fltr):0})
            elif isinstance(fltr, Prefix):
                redis_prefix_lua(conn, temp_id, '%s:%s:pre'%(self.namespace, fltr.attr), fltr.prefix, first)
            elif isinstance(fltr, Suffix):
                redis_prefix_lua(conn, temp_id, '%s:%s:suf'%(self.namespace, fltr.attr), fltr.suffix, first)
            elif isinstance(fltr, Pattern):
                redis_prefix_lua(conn, temp_id,
                    '%s:%s:pre'%(self.namespace, fltr.attr),
                    _find_prefix(fltr.pattern),
                    first, '^' + _pattern_to_lua_pattern(fltr.pattern),
                )
            elif isinstance(fltr, tuple):
                # zset range search
                if len(fltr) != 3:
                    raise QueryError("Cannot filter range of data without 2 endpoints (%s given)"%(len(fltr)-1,))
                fltr, mi, ma = fltr
                intersect(temp_id, {temp_id:0, '%s:%s:idx'%(self.namespace, fltr):1})
                if mi is not None:
                    pipe.zremrangebyscore(temp_id, '-inf', _to_score(mi, True))
                if ma is not None:
                    pipe.zremrangebyscore(temp_id, _to_score(ma, True), 'inf')
            first = False
            intersect = pipe.zinterstore
        return pipe, intersect, temp_id

    def search(self, conn, filters, order_by, offset=None, count=None, timeout=None):
        '''
        Search for model ids that match the provided filters.

        Arguments:

            * *filters* - A list of filters that apply to the search of one of
              the following two forms:

                1. ``'column:string'`` - a plain string will match a word in a
                   text search on the column

                .. note: Read the documentation about the ``Query`` object
                  for what is actually passed during text search

                2. ``('column', min, max)`` - a numeric column range search,
                   between min and max (inclusive by default)

                .. note: Read the documentation about the ``Query`` object
                  for information about open-ended ranges

                3. ``['column:string1', 'column:string2']`` - will match any
                   of the provided words in a text search on the column

                4. ``Prefix('column', 'prefix')`` - will match prefixes of
                   words in a text search on the column

                5. ``Suffix('column', 'suffix')`` - will match suffixes of
                   words in a text search on the column

                6. ``Pattern('column', 'pattern')`` - will match patterns over
                   words in a text search on the column

            * *order_by* - A string that names the numeric column by which to
              sort the results by. Prefixing with '-' will return results in
              descending order

            .. note: While you can technically pass a non-numeric index as an
              *order_by* clause, the results will basically be to order the
              results by string comparison of the ids (10 will come before 2).

            .. note: If you omit the ``order_by`` argument, results will be
              ordered by the last filter. If the last filter was a text
              filter, see the previous note. If the last filter was numeric,
              then results will be ordered by that result.

            * *offset* - A numeric starting offset for results
            * *count* - The maximum number of results to return from the query
        '''
        # prepare the filters
        pipe, intersect, temp_id = self._prepare(conn, filters)

        # handle ordering
        if order_by:
            reverse = order_by and order_by.startswith('-')
            order_clause = '%s:%s:idx'%(self.namespace, order_by.lstrip('-'))
            intersect(temp_id, {temp_id:0, order_clause: -1 if reverse else 1})

        # handle returning the temporary result key
        if timeout is not None:
            pipe.expire(temp_id, timeout)
            pipe.execute()
            return temp_id

        offset = offset if offset is not None else 0
        end = (offset + count - 1) if count and count > 0 else -1
        pipe.zrange(temp_id, offset, end)
        pipe.delete(temp_id)
        return pipe.execute()[-2]

    def count(self, conn, filters):
        '''
        Returns the count of the items that match the provided filters.

        For the meaning of what the ``filters`` argument means, see the
        ``.search()`` method docs.
        '''
        pipe, intersect, temp_id = self._prepare(conn, filters)
        pipe.zcard(temp_id)
        pipe.delete(temp_id)
        return pipe.execute()[-2]

_redis_prefix_lua = _script_load('''
-- first unpack most of our passed variables
local dest = KEYS[1]
local tkey = KEYS[2]
local idx = KEYS[3]

local start_score = ARGV[1]
local end_score = ARGV[2]
local prefix = ARGV[3]
local psize = #prefix
local is_first = tonumber(ARGV[5])

-- find the start offset of our matching
local start_index = 0
if psize > 0 then
    -- All entries end with a null and the id, so we can go before all of them
    -- by just adding a null.
    local pfix = prefix .. '\\0'
    redis.call('ZADD', idx, start_score, pfix)
    start_index = tonumber(redis.call('ZRANK', idx, pfix))
    redis.call('ZREM', idx, pfix)
else
    local start_member = redis.call('ZRANGEBYSCORE', idx, start_score, 'inf', 'limit', 0, 1)
    if #start_member == 1 then
        start_index = tonumber(redis.call('ZRANK', idx, start_member[1]))
    end
end

-- Find the end offset of our matching. We don't bother with the prefix-based
-- ZADD/ZREM pair here because we do an endpoint check every 100 items or so,
--
local end_member = redis.call('ZREVRANGEBYSCORE', idx, '('..end_score, '-inf', 'limit', 0, 1)
local end_index = 0
if #end_member == 1 then
    end_index = tonumber(redis.call('ZRANK', idx, end_member[1]))
end

-- use functions to check instead of embedding an if inside the core loop
local check_match
if tonumber(ARGV[4]) > 0 then
    check_match = function(v, pattern) return string.match(v, pattern) end
else
    check_match = function(v, prefix) return string.sub(v, 1, psize) == prefix end
end

local matched = 0
local found_match = function(v)
    local endv = #v
    while string.sub(v, endv, endv) ~= '\\0' do
        endv = endv - 1
    end
    return redis.call('ZADD', tkey, 0, string.sub(v, endv+1, #v))
end

-- core matching loop
local has_prefix = psize > 0 and tonumber(ARGV[4]) == 0
for i=start_index,end_index,100 do
    local data = redis.call('ZRANGE', idx, i, i+99)
    local last
    for j, v in ipairs(data) do
        if check_match(v, prefix) then
            matched = matched + tonumber(found_match(v))
        end
        last = v
    end
    -- bail early if we've passed all of the shared prefixes
    if has_prefix and string.sub(last, 1, psize) > prefix then
        break
    end
end

if is_first > 0 then
    if matched > 0 then
        redis.call('RENAME', tkey, dest)
    end
else
    matched = redis.call('ZINTERSTORE', dest, 2, tkey, dest, 'WEIGHTS', 1, 0)
    redis.call('DEL', tkey)
end

return matched
''')

def redis_prefix_lua(conn, dest, index, prefix, is_first, pattern=None):
    '''
    Performs the actual prefix, suffix, and pattern match operations. 
    '''
    tkey = '%s:%s'%(index.partition(':')[0], uuid.uuid4())
    start, end = _start_end(prefix)
    return _redis_prefix_lua(conn,
        [dest, tkey, index],
        [start, end, pattern or prefix, int(pattern is not None), int(bool(is_first))],
        force_eval=True
    )

_estimate_work_lua = _script_load('''
-- We could use the ZADD/ZREM stuff from our prefix searching if we have a
-- prefix, but this is only an estimate, and it doesn't make sense to modify
-- an index just to get a better estimate.
local idx = KEYS[1]

local start_score = ARGV[1]
local end_score = ARGV[2]

local start_member = redis.call('ZRANGEBYSCORE', idx, start_score, 'inf', 'limit', 0, 1)
local start_index = 0
if #start_member == 1 then
    start_index = tonumber(redis.call('ZRANK', idx, start_member[1]))
end

local end_member = redis.call('ZREVRANGEBYSCORE', idx, '('..end_score, '-inf', 'limit', 0, 1)
local end_index = -1
if #end_member == 1 then
    end_index = tonumber(redis.call('ZRANK', idx, end_member[1]))
end

return math.max(0, end_index - start_index + 1)
''')

def estimate_work_lua(conn, index, prefix):
    '''
    Estimates the total work necessary to calculate the prefix match over the
    given index with the provided prefix.
    '''
    start, end = _start_end(prefix)
    return _estimate_work_lua(conn, [index], [start, end], force_eval=True)

########NEW FILE########
__FILENAME__ = util

'''
Changing connection settings
============================

There are 4 ways to change the way that ``rom`` connects to Redis.

1. Set the global default connection settings by calling
   ``rom.util.set_connection_settings()``` with the same arguments you would
   pass to the redis.Redis() constructor::

    import rom.util

    rom.util.set_connection_settings(host='myhost', db=7)

2. Give each model its own Redis connection on creation, called _conn, which
   will be used whenever any Redis-related calls are made on instances of that
   model::

    import rom

    class MyModel(rom.Model):
        _conn = redis.Redis(host='myhost', db=7)

        attribute = rom.String()
        other_attribute = rom.String()

3. Replace the ``CONNECTION`` object in ``rom.util``::

    import rom.util

    rom.util.CONNECTION = redis.Redis(host='myhost', db=7)

4. Monkey-patch ``rom.util.get_connection`` with a function that takes no
   arguments and returns a Redis connection::

    import rom.util

    def my_connection():
        # Note that this function doesn't use connection pooling,
        # you would want to instantiate and cache a real connection
        # as necessary.
        return redis.Redis(host='myhost', db=7)

    rom.util.get_connection = my_connection
'''

from datetime import datetime, date, time as dtime
import string
import threading
import weakref

import redis
import six

from .exceptions import ORMError

__all__ = '''
    get_connection Session refresh_indices set_connection_settings'''.split()

CONNECTION = redis.Redis()

def set_connection_settings(*args, **kwargs):
    '''
    Update the global connection settings for models that don't have
    model-specific connections.
    '''
    global CONNECTION
    CONNECTION = redis.Redis(*args, **kwargs)

def get_connection():
    '''
    Override me for one of the ways to change the way I connect to Redis.
    '''
    return CONNECTION

def _connect(obj):
    '''
    Tries to get the _conn attribute from a model. Barring that, gets the
    global default connection using other methods.
    '''
    from .columns import MODELS
    if isinstance(obj, MODELS['Model']):
        obj = obj.__class__
    if hasattr(obj, '_conn'):
        return obj._conn
    return get_connection()

class ClassProperty(object):
    '''
    Borrowed from: https://gist.github.com/josiahcarlson/1561563
    '''
    def __init__(self, get, set=None, delete=None):
        self.get = get
        self.set = set
        self.delete = delete

    def __get__(self, obj, cls=None):
        if cls is None:
            cls = type(obj)
        return self.get(cls)

    def __set__(self, obj, value):
        cls = type(obj)
        self.set(cls, value)

    def __delete__(self, obj):
        cls = type(obj)
        self.delete(cls)

    def getter(self, get):
        return ClassProperty(get, self.set, self.delete)

    def setter(self, set):
        return ClassProperty(self.get, set, self.delete)

    def deleter(self, delete):
        return ClassProperty(self.get, self.set, delete)

# These are just the default index key generators for numeric and string
# types. Numeric keys are used as values in a ZSET, for range searching and
# sorting. Strings are tokenized trivially, and are used as keys to map into
# standard SETs for fairly simple intersection/union searches (like for tags).
# With a bit of work on the string side of things, you could build a simple
# autocomplete, or on the numeric side of things, you could take things like
# 15.23 and turn it into a "$$" key (representing that the value is between 10
# and 20).
# If you return a dictionary with {'':...}, then you can search by just that
# attribute. But if you return a dictionary with {'x':...}, when searching,
# you must use <attr>:x as the attribute for the column.
# For an example of fetching a range based on a numeric index...
# results = Model.query.filter(col=(start, end)).execute()
# vs.
# results = Model.query.filter(**{'col:ex':(start, end)}).execute()

def _numeric_keygen(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        val = dt2ts(val)
    elif isinstance(val, dtime):
        val = t2ts(val)
    return {'': repr(val) if isinstance(val, float) else str(val)}

def _boolean_keygen(val):
    return [str(bool(val))]

def _string_keygen(val):
    if isinstance(val, float):
        val = repr(val)
    elif val in (None, ''):
        return None
    elif not isinstance(val, six.string_types):
        val = str(val)
    r = sorted(set([x for x in [s.lower().strip(string.punctuation) for s in val.split()] if x]))
    if isinstance(val, six.string_types) and not isinstance(val, str):  # unicode on py2k
        return [s.encode('utf-8') for s in r]
    return r

def _many_to_one_keygen(val):
    if val is None:
        return []
    if hasattr(val, '_data') and hasattr(val, '_pkey'):
        return {'': val._data[val._pkey]}
    return {'': val.id}

def _to_score(v, s=False):
    v = repr(v) if isinstance(v, float) else str(v)
    if s:
        if v[:1] != '(':
            return '(' + v
    return v.lstrip('(')

# borrowed and modified from:
# https://gist.github.com/josiahcarlson/8459874
def _bigint_to_float(v):
    assert isinstance(v, six.integer_types)
    sign = -1 if v < 0 else 1
    v *= sign
    assert v < 0x7fe0000000000000
    exponent, mantissa = divmod(v, 2**52)
    return sign * (2**52 + mantissa) * 2.0**(exponent-52-1022)

def _prefix_score(v, next=False):
    if isinstance(v, six.text_type):
        v = v.encode('utf-8')
    # We only get 7 characters of score-based prefix.
    score = 0
    for ch in six.iterbytes(v[:7]):
        score *= 258
        score += ch + 1
    if next:
        score += 1
    score *= 258 ** max(0, 7-len(v))
    return repr(_bigint_to_float(score))

_epoch = datetime(1970, 1, 1)
_epochd = _epoch.date()
def dt2ts(value):
    if isinstance(value, datetime):
        delta = value - _epoch
    else:
        delta = value - _epochd
    return delta.days * 86400 + delta.seconds + delta.microseconds / 1000000.

def ts2dt(value):
    return datetime.utcfromtimestamp(value)

def t2ts(value):
    return value.hour*3600 + value.minute * 60 + value.second + value.microsecond / 1000000.

def ts2t(value):
    hour, value = divmod(value, 3600)
    minute, value = divmod(value, 60)
    second, value = divmod(value, 1)
    return dtime(*map(int, [hour, minute, second, value*1000000]))

class Session(threading.local):
    '''
    This is a very dumb session. All it tries to do is to keep a cache of
    loaded entities, offering the ability to call ``.save()`` on modified (or
    all) entities with ``.flush()`` or ``.commit()``.

    This is exposed via the ``session`` global variable, which is available
    when you ``import rom`` as ``rom.session``.

    .. note: calling ``.flush()`` or ``.commit()`` doesn't cause all objects
        to be written simultanously. They are written one-by-one, with any
        error causing the call to fail.
    '''
    def _init(self):
        try:
            self.known
        except AttributeError:
            self.known = {}
            self.wknown = weakref.WeakValueDictionary()

    def add(self, obj):
        '''
        Adds an entity to the session.
        '''
        self._init()
        self.known[obj._pk] = obj
        self.wknown[obj._pk] = obj

    def forget(self, obj):
        '''
        Forgets about an entity (automatically called when an entity is
        deleted). Call this to ensure that an entity that you've modified is
        not automatically saved on ``session.commit()`` .
        '''
        self._init()
        self.known.pop(obj._pk, None)
        self.wknown.pop(obj._pk, None)

    def get(self, pk):
        '''
        Fetches an entity from the session based on primary key.
        '''
        self._init()
        return self.known.get(pk) or self.wknown.get(pk)

    def rollback(self):
        '''
        Forget about all entities in the session (``.commit()`` will do
        nothing).
        '''
        self.known = {}
        self.wknown = weakref.WeakValueDictionary()

    def flush(self, full=False, all=False):
        '''
        Call ``.save()`` on all modified entities in the session. Use when you
        want to flush changes to Redis, but don't want to lose your local
        session cache.

        See the ``.commit()`` method for arguments and their meanings.
        '''
        self._init()
        changes = 0
        for value in self.known.values():
            if not value._deleted and (all or value._modified):
                changes += value.save(full)
        return changes

    def commit(self, full=False, all=False):
        '''
        Call ``.save()`` on all modified entities in the session. Also forgets
        all known entities in the session, so this should only be called at
        the end of a request.

        Arguments:

            * *full* - pass ``True`` to force save full entities, not only
              changes
            * *all* - pass ``True`` to save all entities known, not only those
              entities that have been modified.
        '''
        changes = self.flush(full, all)
        self.known = {}
        return changes

    def save(self, *objects, **kwargs):
        '''
        This method an alternate API for saving many entities (possibly not
        tracked by the session). You can call::

            session.save(obj)
            session.save(obj1, obj2, ...)
            session.save([obj1, obj2, ...])

        And the entities will be flushed to Redis.

        You can pass the keyword arguments ``full`` and ``all`` with the same
        meaning and semantics as the ``.commit()`` method.
        '''
        from rom import Model
        full = kwargs.get('full')
        all = kwargs.get('all')
        changes = 0
        for o in objects:
            if isinstance(o, (list, tuple)):
                changes += self.save(*o, full=full, all=all)
            elif isinstance(o, Model):
                if not o._deleted and (all or o._modified):
                    changes += o.save(full)
            else:
                raise ORMError(
                    "Cannot save an object that is not an instance of a Model (you provided %r)"%(
                        o,))
        return changes

    def refresh(self, *objects, **kwargs):
        '''
        This method is an alternate API for refreshing many entities (possibly
        not tracked by the session). You can call::

            session.refresh(obj)
            session.refresh(obj1, obj2, ...)
            session.refresh([obj1, obj2, ...])

        And all provided entities will be reloaded from Redis.

        To force reloading for modified entities, you can pass ``force=True``.
        '''
        from rom import Model
        force = kwargs.get('force')
        for o in objects:
            if isinstance(o, (list, tuple)):
                self.refresh(*o, force=force)
            elif isinstance(o, Model):
                if not o._new:
                    o.refresh(force=force)
                else:
                    # all objects are re-added to the session after refresh,
                    # except for deleted entities...
                    self.add(o)
            else:
                raise ORMError(
                    "Cannot refresh an object that is not an instance of a Model (you provided %r)"%(
                        o,))

    def refresh_all(self, *objects, **kwargs):
        '''
        This method is an alternate API for refreshing all entities tracked
        by the session. You can call::

            session.refresh_all()
            session.refresh_all(force=True)

        And all entities known by the session will be reloaded from Redis.

        To force reloading for modified entities, you can pass ``force=True``.
        '''
        self.refresh(*self.known.values(), force=kwargs.get('force'))

session = Session()

def refresh_indices(model, block_size=100):
    '''
    This utility function will iterate over all entities of a provided model,
    refreshing their indices. This is primarily useful after adding an index
    on a column.

    Arguments:

        * *model* - the model whose entities you want to reindex
        * *block_size* - the maximum number of entities you want to fetch from
          Redis at a time, defaulting to 100

    This function will yield its progression through re-indexing all of your
    entities.

    Example use::

        for progress, total in refresh_indices(MyModel, block_size=200):
            print "%s of %s"%(progress, total)

    .. note: This uses the session object to handle index refresh via calls to
      ``.commit()``. If you have any outstanding entities known in the
      session, they will be committed.

    '''
    conn = _connect(model)
    max_id = int(conn.get('%s:%s:'%(model.__name__, model._pkey)) or '0')
    block_size = max(block_size, 10)
    for i in range(1, max_id+1, block_size):
        # fetches entities, keeping a record in the session
        models = model.get(list(range(i, i+block_size)))
        models # for pyflakes
        # re-save un-modified data, resulting in index-only updates
        session.commit(all=True)
        yield min(i+block_size, max_id), max_id

def _script_load(script):
    '''
    Borrowed from my book, Redis in Action:
    https://github.com/josiahcarlson/redis-in-action/blob/master/python/ch11_listing_source.py

    Used for Lua scripting support when writing against Redis 2.6+ to allow
    for multiple unique columns per model.
    '''
    sha = [None]
    def call(conn, keys=[], args=[], force_eval=False):
        if not force_eval:
            if not sha[0]:
                sha[0] = conn.execute_command(
                    "SCRIPT", "LOAD", script, parse="LOAD")

            try:
                return conn.execute_command(
                    "EVALSHA", sha[0], len(keys), *(keys+args))

            except redis.exceptions.ResponseError as msg:
                if not msg.args[0].startswith("NOSCRIPT"):
                    raise

        return conn.execute_command(
            "EVAL", script, len(keys), *(keys+args))

    return call


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# rom documentation build configuration file, created by
# sphinx-quickstart on Sun Apr 21 15:05:03 2013.
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
sys.path.insert(0, os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'rom'
copyright = u'2013, Josiah Carlson'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
import rom

version = rom.VERSION
# The full version, including alpha/beta/rc tags.
release = rom.VERSION

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
exclude_patterns = []

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'romdoc'


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
  ('index', 'rom.tex', u'rom Documentation',
   u'Josiah Carlson', 'manual'),
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
    ('index', 'rom', u'rom Documentation',
     [u'Josiah Carlson'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'rom', u'rom Documentation',
   u'Josiah Carlson', 'rom', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = test_rom
from __future__ import print_function
from datetime import datetime, timedelta
from decimal import Decimal as _Decimal
import time
import unittest

import redis
import six

from rom import util

util.CONNECTION = redis.Redis(db=15)
connect = util._connect

from rom import *
from rom import _disable_lua_writes, _enable_lua_writes
from rom.exceptions import *

def global_setup():
    c = connect(None)
    keys = c.keys('RomTest*')
    if keys:
        c.delete(*keys)
    from rom.columns import MODELS
    Model = MODELS['Model']
    for k, v in MODELS.copy().items():
        if v is not Model:
            del MODELS[k]

def get_state():
    c = connect(None)
    data = []
    for k in c.keys('*'):
        k = k.decode() if six.PY3 else k
        t = c.type(k)
        t = t.decode() if six.PY3 else t
        if t == 'string':
            data.append((k, c.get(k)))
        elif t == 'list':
            data.append((k, c.lrange(k, 0, -1)))
        elif t == 'set':
            data.append((k, c.smembers(k)))
        elif t == 'hash':
            data.append((k, c.hgetall(k)))
        else:
            data.append((k, c.zrange(k, 0, -1, withscores=True)))
    data.sort()
    return data

_now = datetime.utcnow()
_now_time = time.time()

def _default_time():
    return _now_time

class TestORM(unittest.TestCase):
    def setUp(self):
        session.rollback()

    # for Python 2.6
    def assertIsNone(self, arg):
        assert arg is None
    def assertIs(self, arg1, arg2):
        assert arg1 is arg2

    def test_basic_model(self):
        class RomTestBasicModel(Model):
            val = Integer()
            oval = Integer(default=7)
            created_at = Float(default=_default_time)
            req = Text(required=True)

        self.assertRaises(ColumnError, RomTestBasicModel)
        self.assertRaises(InvalidColumnValue, lambda: RomTestBasicModel(oval='t', req='X'))
        self.assertRaises(MissingColumn, lambda: RomTestBasicModel(created_at=7))

        # try object saving/loading
        x = RomTestBasicModel(val=1, req="hello")
        x.save()
        id = x.id
        x = x.to_dict()

        y = RomTestBasicModel.get(id)
        yd = y.to_dict()
        ## cax = x.pop('created_at'); cay = yd.pop('created_at')
        self.assertEqual(x, yd)
        ## self.assertTrue(abs(cax - cay) < .005, cax-cay)

        # try object copying
        zd = y.copy().to_dict()
        ## caz = zd.pop('created_at')
        self.assertNotEqual(yd, zd)
        zd.pop('id')
        yd.pop('id')
        self.assertEqual(yd, zd)
        ## self.assertTrue(abs(cay-caz) < .005, cay-caz)

    def test_unique_index(self):
        def foo2():
            class RomTestBadIndexModel2(Model):
                bad = Integer(unique=True)
        self.assertRaises(ColumnError, foo2)

        class RomTestIndexModel(Model):
            key = Text(required=True, unique=True)

        self.assertRaises(MissingColumn, RomTestIndexModel)
        item = RomTestIndexModel(key="hello")
        item.save()

        m = RomTestIndexModel.get_by(key="hello")
        self.assertTrue(m)
        self.assertEqual(m.id, item.id)
        self.assertTrue(m is item)

    def test_foreign_key(self):
        def foo():
            class RomTestBFkey1(Model):
                bad = ManyToOne("RomTestBad")
            RomTestBFkey1()
        self.assertRaises(ORMError, foo)

        def foo2():
            class RomTestBFkey2(Model):
                bad = OneToMany("RomTestBad")
            RomTestBFkey2()
        self.assertRaises(ORMError, foo2)

        class RomTestFkey1(Model):
            fkey2 = ManyToOne("RomTestFkey2")
        class RomTestFkey2(Model):
            fkey1 = OneToMany("RomTestFkey1")

        x = RomTestFkey2()
        y = RomTestFkey1(fkey2=x) # implicitly saves x
        y.save()

        xid = x.id
        yid = y.id
        x = y = None
        y = RomTestFkey1.get(yid)
        self.assertEqual(y.fkey2.id, xid)
        fk1 = y.fkey2.fkey1

        self.assertEqual(len(fk1), 1)
        self.assertEqual(fk1[0].id, y.id)

    def test_unique(self):
        class RomTestUnique(Model):
            attr = Text(unique=True)

        a = RomTestUnique(attr='hello')
        b = RomTestUnique(attr='hello2')
        a.save()
        b.save()
        b.attr = 'hello'
        self.assertRaises(UniqueKeyViolation, b.save)

        c = RomTestUnique(attr='hello')
        self.assertRaises(UniqueKeyViolation, c.save)

        a.delete()
        b.save()

    def test_saving(self):
        class RomTestNormal(Model):
            attr = Text()

        self.assertTrue(RomTestNormal().save())
        self.assertTrue(RomTestNormal(attr='hello').save())
        x = RomTestNormal()
        self.assertTrue(x.save())
        self.assertFalse(x.save())
        session.commit()

        self.assertTrue(x is RomTestNormal.get(x.id))

    def test_index(self):
        class RomTestIndexedModel(Model):
            attr = Text(index=True)
            attr2 = Text(index=True)
            attr3 = Integer(index=True)
            attr4 = Float(index=True)
            attr5 = Decimal(index=True)

        x = RomTestIndexedModel(
            attr='hello world',
            attr2='how are you doing?',
            attr3=7,
            attr4=4.5,
            attr5=_Decimal('2.643'),
        )
        x.save()
        RomTestIndexedModel(
            attr='world',
            attr3=100,
            attr4=-1000,
            attr5=_Decimal('2.643'),
        ).save()

        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello').count(), 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr2='how').filter(attr2='are').count(), 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello').filter(attr2='how').filter(attr2='are').count(), 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello', noattr='bad').filter(attr2='how').filter(attr2='are').count(), 0)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello', attr3=(None, None)).count(), 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello', attr3=(None, 10)).count(), 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello', attr3=(None, 10)).execute()[0].id, 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello', attr3=(5, None)).count(), 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello', attr3=(5, 10), attr4=(4,5), attr5=(2.5, 2.7)).count(), 1)
        first = RomTestIndexedModel.query.filter(attr='hello', attr3=(5, 10), attr4=(4,5), attr5=(2.5, 2.7)).first()
        self.assertTrue(first)
        self.assertTrue(first is x)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='hello', attr3=(10, 20), attr4=(4,5), attr5=(2.5, 2.7)).count(), 0)
        self.assertEqual(RomTestIndexedModel.query.filter(attr3=100).count(), 1)
        self.assertEqual(RomTestIndexedModel.query.filter(attr='world', attr5=_Decimal('2.643')).count(), 2)

        results = RomTestIndexedModel.query.filter(attr='world').order_by('attr4').execute()
        self.assertEqual([x.id for x in results], [2,1])

        for i in range(50):
            RomTestIndexedModel(attr3=i)
        session.commit()
        session.rollback()

        self.assertEqual(len(RomTestIndexedModel.get_by(attr3=(10, 25))), 16)
        self.assertEqual(len(RomTestIndexedModel.get_by(attr3=(10, 25), _limit=(0,5))), 5)

        key = RomTestIndexedModel.query.filter(attr='hello').filter(attr2='how').filter(attr2='are').cached_result(30)
        conn = connect(None)
        self.assertTrue(conn.ttl(key) <= 30)
        self.assertEqual(conn.zcard(key), 1)
        conn.delete(key)

    def test_alternate_models(self):
        ctr = [0]
        class RomTestAlternate(object):
            def __init__(self, id=None):
                if id is None:
                    id = ctr[0]
                    ctr[0] += 1
                self.id = id

            @classmethod
            def get(self, id):
                return RomTestAlternate(id)

        class RomTestFModel(Model):
            attr = ForeignModel(RomTestAlternate)

        a = RomTestAlternate()
        ai = a.id
        i = RomTestFModel(attr=a).id
        session.commit()   # two lines of magic to destroy session history
        session.rollback() #
        del a

        f = RomTestFModel.get(i)
        self.assertEqual(f.attr.id, ai)

    def test_model_connection(self):
        class RomTestFoo(Model):
            pass

        class RomTestBar(Model):
            _conn = redis.Redis(db=14)

        RomTestBar._conn.delete('RomTestBar:id:')

        RomTestFoo().save()
        RomTestBar().save()

        self.assertEqual(RomTestBar._conn.get('RomTestBar:id:').decode(), '1')
        self.assertEqual(util.CONNECTION.get('RomTestBar:id:'), None)
        RomTestBar.get(1).delete()
        RomTestBar._conn.delete('RomTestBar:id:')
        k = RomTestBar._conn.keys('RomTest*')
        if k:
            RomTestBar._conn.delete(*k)

    def test_entity_caching(self):
        class RomTestGoo(Model):
            pass

        f = RomTestGoo()
        i = f.id
        session.commit()

        for j in range(10):
            RomTestGoo()

        g = RomTestGoo.get(i)
        self.assertIs(f, g)

    def test_index_preservation(self):
        """ Edits to unrelated columns should not remove the index of other
        columns. Issue: https://github.com/josiahcarlson/rom/issues/2. """

        class RomTestM(Model):
            u = Text(unique=True)
            i = Integer(index=True)
            unrelated = Text()

        RomTestM(u='foo', i=11).save()

        m = RomTestM.get_by(u='foo')
        m.unrelated = 'foobar'
        self.assertEqual(len(RomTestM.get_by(i=11)), 1)
        m.save()
        self.assertEqual(len(RomTestM.get_by(i=11)), 1)
        self.assertEqual(len(RomTestM.get_by(i=(10, 12))), 1)

    def test_json_multisave(self):
        class RomTestJsonTest(Model):
            col = Json()

        d = {'hello': 'world'}
        x = RomTestJsonTest(col=d)
        x.save()
        del x
        for i in range(5):
            x = RomTestJsonTest.get(1)
            self.assertEqual(x.col, d)
            x.save(full=True)
            session.rollback()

    def test_boolean(self):
        class RomTestBooleanTest(Model):
            col = Boolean(index=True)

        RomTestBooleanTest(col=True).save()
        RomTestBooleanTest(col=1).save()
        RomTestBooleanTest(col=False).save()
        RomTestBooleanTest(col='').save()
        RomTestBooleanTest(col=None).save() # None is considered "not data", so is ignored
        y = RomTestBooleanTest()
        yid = y.id
        y.save()
        del y
        self.assertEqual(len(RomTestBooleanTest.get_by(col=True)), 2)
        self.assertEqual(len(RomTestBooleanTest.get_by(col=False)), 2)
        session.rollback()
        x = RomTestBooleanTest.get(1)
        x.col = False
        x.save()
        self.assertEqual(len(RomTestBooleanTest.get_by(col=True)), 1)
        self.assertEqual(len(RomTestBooleanTest.get_by(col=False)), 3)
        self.assertEqual(len(RomTestBooleanTest.get_by(col=True)), 1)
        self.assertEqual(len(RomTestBooleanTest.get_by(col=False)), 3)
        y = RomTestBooleanTest.get(yid)
        self.assertEqual(y.col, None)

    def test_datetimes(self):
        class RomTestDateTimesTest(Model):
            col1 = DateTime(index=True)
            col2 = Date(index=True)
            col3 = Time(index=True)

        dtt = RomTestDateTimesTest(col1=_now, col2=_now.date(), col3=_now.time())
        dtt.save()
        session.commit()
        del dtt
        self.assertEqual(len(RomTestDateTimesTest.get_by(col1=_now)), 1)
        self.assertEqual(len(RomTestDateTimesTest.get_by(col2=_now.date())), 1)
        self.assertEqual(len(RomTestDateTimesTest.get_by(col3=_now.time())), 1)

    def test_deletion(self):
        class RomTestDeletionTest(Model):
            col1 = Text(index=True)

        x = RomTestDeletionTest(col1="this is a test string that should be indexed")
        session.commit()
        self.assertEqual(len(RomTestDeletionTest.get_by(col1='this')), 1)

        x.delete()
        self.assertEqual(len(RomTestDeletionTest.get_by(col1='this')), 0)

        session.commit()
        self.assertEqual(len(RomTestDeletionTest.get_by(col1='this')), 0)

    def test_empty_query(self):
        class RomTestEmptyQueryTest(Model):
            col1 = Text()

        RomTestEmptyQueryTest().save()
        self.assertRaises(QueryError, RomTestEmptyQueryTest.query.all)
        self.assertRaises(QueryError, RomTestEmptyQueryTest.query.count)
        self.assertRaises(QueryError, RomTestEmptyQueryTest.query.limit(0, 10).count)

    def test_refresh(self):
        class RomTestRefresh(Model):
            col = Text()

        d = RomTestRefresh(col='hello')
        d.save()
        d.col = 'world'
        self.assertRaises(InvalidOperation, d.refresh)
        d.refresh(True)
        self.assertEqual(d.col, 'hello')
        d.col = 'world'
        session.refresh(d, force=True)
        self.assertEqual(d.col, 'hello')
        d.col = 'world'
        session.refresh_all(force=True)
        self.assertEqual(d.col, 'hello')
        self.assertRaises(InvalidOperation, RomTestRefresh(col='boo').refresh)

    def test_datetime(self):
        class RomTestDT(Model):
            created_at = DateTime(default=datetime.utcnow)
            event_datetime = DateTime(index=True)

        x = RomTestDT()
        x.event_datetime = datetime.utcnow()
        x.save()
        RomTestDT(event_datetime=datetime.utcnow()).save()
        session.rollback() # clearing the local cache

        self.assertEqual(RomTestDT.get_by(event_datetime=(datetime(2000, 1, 1), datetime(2000, 1, 1))), [])
        self.assertEqual(len(RomTestDT.get_by(event_datetime=(datetime(2000, 1, 1), datetime.utcnow()))), 2)

    def test_prefix_suffix_pattern(self):
        import rom
        if not rom.USE_LUA:
            return

        class RomTestPSP(Model):
            col = Text(prefix=True, suffix=True)

        x = RomTestPSP(col="hello world how are you doing, join us today")
        x.save()

        self.assertEqual(RomTestPSP.query.startswith(col='he').count(), 1)
        self.assertEqual(RomTestPSP.query.startswith(col='notthere').count(), 0)
        self.assertEqual(RomTestPSP.query.endswith(col='rld').count(), 1)
        self.assertEqual(RomTestPSP.query.endswith(col='bad').count(), 0)
        self.assertEqual(RomTestPSP.query.like(col='?oin?').count(), 1)
        self.assertEqual(RomTestPSP.query.like(col='*oin+').count(), 1)
        self.assertEqual(RomTestPSP.query.like(col='oin').count(), 0)
        self.assertEqual(RomTestPSP.query.like(col='+oin').like(col='wor!d').count(), 1)

    def test_unicode_text(self):
        import rom
        ch = unichr(0xfeff) if six.PY2 else chr(0xfeff)
        pre = ch + 'hello'
        suf = 'hello' + ch

        class RomTestUnicode1(Model):
            col = Text(index=True, unique=True)

        RomTestUnicode1(col=pre).save()
        RomTestUnicode1(col=suf).save()

        self.assertEqual(RomTestUnicode1.query.filter(col=pre).count(), 1)
        self.assertEqual(RomTestUnicode1.query.filter(col=suf).count(), 1)
        self.assertTrue(RomTestUnicode1.get_by(col=pre))
        self.assertTrue(RomTestUnicode1.get_by(col=suf))

        import rom
        if rom.USE_LUA:
            class RomTestUnicode2(Model):
                col = Text(prefix=True, suffix=True)

            RomTestUnicode2(col=pre).save()
            RomTestUnicode2(col=suf).save()

            self.assertEqual(RomTestUnicode2.query.startswith(col="h").count(), 1)
            self.assertEqual(RomTestUnicode2.query.startswith(col=ch).count(), 1)
            self.assertEqual(RomTestUnicode2.query.endswith(col="o").count(), 1)
            self.assertEqual(RomTestUnicode2.query.endswith(col=ch).count(), 1)

    def test_infinite_ranges(self):
        """ Infinite range lookups via None in tuple.
        The get_by method accepts None as an argument to range based
        lookups.  A range lookup is done by passing a tuple as the value
        to the kwarg representing the column in question such as,
        Model.get_by(some_column=(small, large)).  The left and right side
        are inclusive. """

        class RomTestInfRange(Model):
            dt = DateTime(index=True)
            num = Integer(index=True)

        start_dt = datetime(2000, 1, 1)
        for x in range(3):
            RomTestInfRange(dt=start_dt+timedelta(days=x), num=x)
        session.commit()
        ranges = (
            (dict(dt=(start_dt-timedelta(days=1), None)), 3),
            (dict(dt=(start_dt, None)), 3),
            (dict(dt=(start_dt+timedelta(days=0.5), None)), 2),
            (dict(dt=(start_dt+timedelta(days=1), None)), 2),
            (dict(dt=(start_dt+timedelta(days=1.5), None)), 1),
            (dict(dt=(start_dt+timedelta(days=2), None)), 1),
            (dict(dt=(start_dt+timedelta(days=2.5), None)), 0),

            (dict(dt=(None, start_dt+timedelta(days=2.5))), 3),
            (dict(dt=(None, start_dt+timedelta(days=2))), 3),
            (dict(dt=(None, start_dt+timedelta(days=1.5))), 2),
            (dict(dt=(None, start_dt+timedelta(days=1))), 2),
            (dict(dt=(None, start_dt+timedelta(days=0.5))), 1),
            (dict(dt=(None, start_dt)), 1),
            (dict(dt=(None, start_dt-timedelta(days=1))), 0),

            (dict(num=(-1, None)), 3),
            (dict(num=(0, None)), 3),
            (dict(num=(0.5, None)), 2),
            (dict(num=(1, None)), 2),
            (dict(num=(1.5, None)), 1),
            (dict(num=(2, None)), 1),
            (dict(num=(2.5, None)), 0),

            (dict(num=(None, 2.5)), 3),
            (dict(num=(None, 2)), 3),
            (dict(num=(None, 1.5)), 2),
            (dict(num=(None, 1)), 2),
            (dict(num=(None, 0.5)), 1),
            (dict(num=(None, 0)), 1),
            (dict(num=(None, -1)), 0),
        )
        for i, (kwargs, count) in enumerate(ranges):
            try:
                st = 1
                self.assertEqual(len(RomTestInfRange.get_by(**kwargs)), count)
                st = 2
                self.assertEqual(RomTestInfRange.query.filter(**kwargs).count(), count)
                st = 3
                self.assertEqual(len(RomTestInfRange.query.filter(**kwargs).execute()), count)
            except Exception:
                msg = 'test %d step %d: range %s, expect: %d' % (i, st, kwargs, count)
                print(msg)
                raise

    def test_big_int(self):
        """ Ensure integers that overflow py2k int work. """

        class RomTestBigInt(Model):
            num = Integer()

        numbers = [
            1,
            200,
            1<<15,
            1<<63,
            1<<128,
            1<<256,
        ]

        for i, num in enumerate(numbers):
            RomTestBigInt(num=num).save()
            session.commit()
            session.rollback()
            echo = RomTestBigInt.get(i+1).num
            self.assertEqual(num, echo)

    def test_cleanup(self):
        """ Ensure no side effects are left in the db after a delete. """
        redis = connect(None)

        class RomTestCleanupA(Model):
            foo = Text()
            blist = OneToMany('RomTestCleanupB')

        class RomTestCleanupB(Model):
            bar = Text()
            a = ManyToOne('RomTestCleanupA')

        a = RomTestCleanupA(foo='foo')
        a.save()
        b = RomTestCleanupB(bar='foo', a=a)
        b.save()
        b.delete()
        self.assertFalse(redis.hkeys('RomTestCleanupB:%d' % b.id))
        a.delete()
        self.assertFalse(redis.hkeys('RomTestCleanupA:%d' % a.id))

        # Test delete() where a column value does not change. This affects
        # the writer logic which checks for deltas as a means to determine
        # what keys should be removed from the redis hash bucket.
        a = RomTestCleanupA(foo='foo')
        a.save()
        b = RomTestCleanupB(bar='foo', a=a)
        b.save()
        a.delete()  # Nullify FK on b.
        self.assertFalse(redis.hkeys('RomTestCleanupA:%d' % a.id))
        session.rollback() # XXX purge session cache
        b = RomTestCleanupB.get(b.id)
        b.delete()  # Nullify FK on b.
        self.assertFalse(redis.hkeys('RomTestCleanupB:%d' % b.id))

    def test_delete_writethrough(self):
        """ Verify that a Model.delete() writes through backing and session. """

        class RomTestDelete(Model):
            pass

        # write-through backing
        a = RomTestDelete()
        a.save()
        a.delete()
        session.commit()
        session.rollback()
        self.assertIsNone(RomTestDelete.get(a.id))

        # write-through cache auto-commit (session)
        a = RomTestDelete()
        a.save()
        a.delete()
        self.assertIsNone(RomTestDelete.get(a.id))

        # write-through cache force-commit (session)
        a = RomTestDelete()
        a.save()
        a.delete()
        session.commit()
        self.assertIsNone(RomTestDelete.get(a.id))

    def test_(self):
        from rom import columns
        if not columns.USE_LUA:
            return
        class RomTestPerson(Model):
            name = Text(prefix=True, suffix=True, index=True)

        names = ['Acasaoi', 'Maria Williamson IV', 'Rodrigo Howe',
            'Mr. Willow Goldner', 'Melody Prohaska', 'Hulda Botsford',
            'Lester Swaniawski MD', 'Vilma Mohr Sr.', 'Pierre Moen',
            'Beau Streich', 'Mrs. Laron Morar III', 'bmliodasas',
            'Jewell Stroman', 'Garfield Stark', 'Dr. Ignatius Kuvalis PhD',
            'Nikita Okuneva', 'Daija Turcotte', 'Royce Halvorson',
            'Tess Schimmel', 'Ms. Monte Heathcote', 'Johann Glover',
            'Kade Lueilwitz', 'bsaasao', 'Casper Pouros',
            'Miss Griffin Corkery II', 'Cierra Volkman V', 'Sean McLaughlin',
            'Cmlio', 'Cdsdmlio', 'Dasao', 'Dioasu', 'Eioasu', 'Fasao',
            'Emilie Towne II', 'G h o', 'Jhorecgssd',
            'H Mrs. Newton Murazik Sr.  Zidfdfoaxaol dfgdfggf ',
            'Zidfdfoasaol dfgdfggf Mrs. Newton Murazik Sr.  ',
            'Perry Ankunding', 'Dusty Kessler', 'Jacinthe Bechtelar',
            'Dr. Jordan Hintz PhD', 'Miss Monty Kuvalis']
        for name in names:
            RomTestPerson(name=name)
        session.commit()

        self.assertEqual(RomTestPerson.query.like(name='*asao*').count(), 5)

def main():
    _disable_lua_writes()
    global_setup()
    print("Testing standard writing")
    try:
        unittest.main()
    except SystemExit:
        pass
    data = get_state()
    global_setup()
    _enable_lua_writes()
    print("Testing Lua writing")
    try:
        unittest.main()
    except SystemExit:
        pass
    lua_data = get_state()
    global_setup()

    ## if data != lua_data:
        ## print("WARNING: Regular/Lua data writing does not match!")
        ## import pprint
        ## pprint.pprint(data)
        ## pprint.pprint(lua_data)

if __name__ == '__main__':
    main()

########NEW FILE########
