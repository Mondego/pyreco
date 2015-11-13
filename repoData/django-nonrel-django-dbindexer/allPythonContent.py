__FILENAME__ = api
from .lookups import LookupDoesNotExist, ExtraFieldLookup
from . import lookups as lookups_module
from .resolver import resolver
import inspect

# TODO: add possibility to add lookup modules
def create_lookup(lookup_def):
    for _, cls in inspect.getmembers(lookups_module):
        if inspect.isclass(cls) and issubclass(cls, ExtraFieldLookup) and \
                cls.matches_lookup_def(lookup_def):
            return cls()
    raise LookupDoesNotExist('No Lookup found for %s .' % lookup_def)

def register_index(model, mapping):
    for field_name, lookups in mapping.items():
        if not isinstance(lookups, (list, tuple)):
            lookups = (lookups, )

        # create indexes and add model and field_name to lookups
        # create ExtraFieldLookup instances on the fly if needed
        for lookup in lookups:
            lookup_def = None
            if not isinstance(lookup, ExtraFieldLookup):
                lookup_def = lookup
                lookup = create_lookup(lookup_def)
            lookup.contribute(model, field_name, lookup_def)
            resolver.create_index(lookup)

########NEW FILE########
__FILENAME__ = backends
import django
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.utils.tree import Node

try:
    from django.db.models.sql.where import SubqueryConstraint
except ImportError:
    SubqueryConstraint = None

from djangotoolbox.fields import ListField

from dbindexer.lookups import StandardLookup

if django.VERSION >= (1, 6):
    TABLE_NAME = 0
    RHS_ALIAS = 1
    JOIN_TYPE = 2
    LHS_ALIAS = 3

    def join_cols(join_info):
        return join_info.join_cols[0]
elif django.VERSION >= (1, 5):
    TABLE_NAME = 0
    RHS_ALIAS = 1
    JOIN_TYPE = 2
    LHS_ALIAS = 3

    def join_cols(join_info):
        return (join_info.lhs_join_col, join_info.rhs_join_col)
else:
    from django.db.models.sql.constants import (JOIN_TYPE, LHS_ALIAS,
        LHS_JOIN_COL, TABLE_NAME, RHS_JOIN_COL)

    def join_cols(join_info):
        return (join_info[LHS_JOIN_COL], join_info[RHS_JOIN_COL])

OR = 'OR'

# TODO: optimize code
class BaseResolver(object):
    def __init__(self):
        # mapping from lookups to indexes
        self.index_map = {}
        # mapping from column names to field names
        self.column_to_name = {}

    ''' API called by resolver'''

    def create_index(self, lookup):
        field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)

        # backend doesn't now how to handle this index definition
        if not field_to_index:
            return

        index_field = lookup.get_field_to_add(field_to_index)
        config_field = index_field.item_field if \
            isinstance(index_field, ListField) else index_field
        if field_to_index.max_length is not None and \
                isinstance(config_field, models.CharField):
            config_field.max_length = field_to_index.max_length

        if isinstance(field_to_index,
            (models.DateField, models.DateTimeField, models.TimeField)):
            if field_to_index.auto_now or field_to_index.auto_now_add:
                raise ImproperlyConfigured('\'auto_now\' and \'auto_now_add\' '
                    'on %s.%s is not supported by dbindexer.' %
                    (lookup.model._meta.object_name, lookup.field_name))

        # don't install a field if it already exists
        try:
            lookup.model._meta.get_field(self.index_name(lookup))
        except:
            lookup.model.add_to_class(self.index_name(lookup), index_field)
            self.index_map[lookup] = index_field
            self.add_column_to_name(lookup.model, lookup.field_name)
        else:
            # makes dbindexer unit test compatible
            if lookup not in self.index_map:
                self.index_map[lookup] = lookup.model._meta.get_field(
                    self.index_name(lookup))
                self.add_column_to_name(lookup.model, lookup.field_name)

    def convert_insert_query(self, query):
        '''Converts a database saving query.'''

        for lookup in self.index_map.keys():
            self._convert_insert_query(query, lookup)

    def _convert_insert_query(self, query, lookup):
        if not lookup.model == query.model:
            return

        position = self.get_query_position(query, lookup)
        if position is None:
            return

        value = self.get_value(lookup.model, lookup.field_name, query)

        if isinstance(value, list):
            for i in range(0, len(value)):
                setattr(query.objs[i], lookup.index_name, lookup.convert_value(value[i]))
        else:
            try:
                setattr(query.objs[0], lookup.index_name, lookup.convert_value(value))
            except ValueError, e:
                '''
                If lookup.index_name is a foreign key field, we need to set the actual
                referenced object, not just the id.  When we try to set the id, we get an
                exception.
                '''
                field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)

                # backend doesn't now how to handle this index definition
                if not field_to_index:
                    raise Exception('Unable to convert insert query because of unknown field'
                        ' %s.%s' % (lookup.model._meta.object_name, lookup.field_name))

                index_field = lookup.get_field_to_add(field_to_index)
                if isinstance(index_field, models.ForeignKey):
                    setattr(query.objs[0], '%s_id' % lookup.index_name, lookup.convert_value(value))
                else:
                    raise

    def convert_filters(self, query):
        self._convert_filters(query, query.where)

    ''' helper methods '''

    def _convert_filters(self, query, filters):
        for index, child in enumerate(filters.children[:]):
            if isinstance(child, Node):
                self._convert_filters(query, child)
                continue

            if SubqueryConstraint is not None and isinstance(child, SubqueryConstraint):
                continue

            self.convert_filter(query, filters, child, index)

    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child

        if constraint.field is None:
            return

        field_name = self.column_to_name.get(constraint.field.column)
        if field_name and constraint.alias == \
                query.table_map[query.model._meta.db_table][0]:
            for lookup in self.index_map.keys():
                if lookup.matches_filter(query.model, field_name, lookup_type,
                                         value):
                    new_lookup_type, new_value = lookup.convert_lookup(value,
                                                                       lookup_type)
                    index_name = self.index_name(lookup)
                    self._convert_filter(query, filters, child, index,
                                         new_lookup_type, new_value, index_name)

    def _convert_filter(self, query, filters, child, index, new_lookup_type,
                        new_value, index_name):
        constraint, lookup_type, annotation, value = child
        lookup_type, value = new_lookup_type, new_value
        constraint.field = query.get_meta().get_field(index_name)
        constraint.col = constraint.field.column
        child = constraint, lookup_type, annotation, value
        filters.children[index] = child

    def index_name(self, lookup):
        return lookup.index_name

    def get_field_to_index(self, model, field_name):
        try:
            return model._meta.get_field(field_name)
        except:
            return None

    def get_value(self, model, field_name, query):
        field_to_index = self.get_field_to_index(model, field_name)

        if field_to_index in query.fields:
            values = []
            for obj in query.objs:
                value = field_to_index.value_from_object(obj)
                values.append(value)
            if len(values):
                return values
        raise FieldDoesNotExist('Cannot find field in query.')

    def add_column_to_name(self, model, field_name):
        column_name = model._meta.get_field(field_name).column
        self.column_to_name[column_name] = field_name

    def get_index(self, lookup):
        return self.index_map[lookup]

    def get_query_position(self, query, lookup):
        for index, field in enumerate(query.fields):
            if field is self.get_index(lookup):
                return index
        return None

def unref_alias(query, alias):
    table_name = query.alias_map[alias][TABLE_NAME]
    query.alias_refcount[alias] -= 1
    if query.alias_refcount[alias] < 1:
        # Remove all information about the join
        del query.alias_refcount[alias]
        if hasattr(query, 'rev_join_map'):
            # Django 1.4 compatibility
            del query.join_map[query.rev_join_map[alias]]
            del query.rev_join_map[alias]
        else:
            try:
                table, _, _, lhs, join_cols, _, _ = query.alias_map[alias]
                del query.join_map[(lhs, table, join_cols)]
            except KeyError:
                # Django 1.5 compatibility
                table, _, _, lhs, lhs_col, col, _ = query.alias_map[alias]
                del query.join_map[(lhs, table, lhs_col, col)]

        del query.alias_map[alias]
        query.tables.remove(alias)
        query.table_map[table_name].remove(alias)
        if len(query.table_map[table_name]) == 0:
            del query.table_map[table_name]
        query.used_aliases.discard(alias)

class FKNullFix(BaseResolver):
    '''
        Django doesn't generate correct code for ForeignKey__isnull.
        It becomes a JOIN with pk__isnull which won't work on nonrel DBs,
        so we rewrite the JOIN here.
    '''

    def create_index(self, lookup):
        pass

    def convert_insert_query(self, query):
        pass

    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        if constraint.field is not None and lookup_type == 'isnull' and \
                        isinstance(constraint.field, models.ForeignKey):
            self.fix_fk_null_filter(query, constraint)

    def unref_alias(self, query, alias):
        unref_alias(query, alias)

    def fix_fk_null_filter(self, query, constraint):
        alias = constraint.alias
        table_name = query.alias_map[alias][TABLE_NAME]
        lhs_join_col, rhs_join_col = join_cols(query.alias_map[alias])
        if table_name != constraint.field.rel.to._meta.db_table or \
                rhs_join_col != constraint.field.rel.to._meta.pk.column or \
                lhs_join_col != constraint.field.column:
            return
        next_alias = query.alias_map[alias][LHS_ALIAS]
        if not next_alias:
            return
        self.unref_alias(query, alias)
        alias = next_alias
        constraint.col = constraint.field.column
        constraint.alias = alias

class ConstantFieldJOINResolver(BaseResolver):
    def create_index(self, lookup):
        if '__' in lookup.field_name:
            super(ConstantFieldJOINResolver, self).create_index(lookup)

    def convert_insert_query(self, query):
        '''Converts a database saving query.'''

        for lookup in self.index_map.keys():
            if '__' in lookup.field_name:
                self._convert_insert_query(query, lookup)

    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        field_chain = self.get_field_chain(query, constraint)

        if field_chain is None:
            return

        for lookup in self.index_map.keys():
            if lookup.matches_filter(query.model, field_chain, lookup_type,
                                     value):
                self.resolve_join(query, child)
                new_lookup_type, new_value = lookup.convert_lookup(value,
                                                                   lookup_type)
                index_name = self.index_name(lookup)
                self._convert_filter(query, filters, child, index,
                                     new_lookup_type, new_value, index_name)

    def get_field_to_index(self, model, field_name):
        model = self.get_model_chain(model, field_name)[-1]
        field_name = field_name.split('__')[-1]
        return super(ConstantFieldJOINResolver, self).get_field_to_index(model,
            field_name)

    def get_value(self, model, field_name, query):
        value = super(ConstantFieldJOINResolver, self).get_value(model,
                                    field_name.split('__')[0],
                                    query)

        if isinstance(value, list):
            value = value[0]
        if value is not None:
            value = self.get_target_value(model, field_name, value)
        return value

    def get_field_chain(self, query, constraint):
        if constraint.field is None:
            return

        column_index = self.get_column_index(query, constraint)
        return self.column_to_name.get(column_index)

    def get_model_chain(self, model, field_chain):
        model_chain = [model, ]
        for value in field_chain.split('__')[:-1]:
            model = model._meta.get_field(value).rel.to
            model_chain.append(model)
        return model_chain

    def get_target_value(self, start_model, field_chain, pk):
        fields = field_chain.split('__')
        foreign_key = start_model._meta.get_field(fields[0])

        if not foreign_key.rel:
            # field isn't a related one, so return the value itself
            return pk

        target_model = foreign_key.rel.to
        foreignkey = target_model.objects.all().get(pk=pk)
        for value in fields[1:-1]:
            foreignkey = getattr(foreignkey, value)

        if isinstance(foreignkey._meta.get_field(fields[-1]), models.ForeignKey):
            return getattr(foreignkey, '%s_id' % fields[-1])
        else:
            return getattr(foreignkey, fields[-1])

    def add_column_to_name(self, model, field_name):
        model_chain = self.get_model_chain(model, field_name)
        column_chain = ''
        field_names = field_name.split('__')
        for model, name in zip(model_chain, field_names):
            column_chain += model._meta.get_field(name).column + '__'
        self.column_to_name[column_chain[:-2]] = field_name

    def unref_alias(self, query, alias):
        unref_alias(query, alias)

    def get_column_index(self, query, constraint):
        column_chain = []
        if constraint.field:
            column_chain.append(constraint.col)
            alias = constraint.alias
            while alias:
                join = query.alias_map.get(alias)
                if join and join[JOIN_TYPE] == 'INNER JOIN':
                    column_chain.insert(0, join_cols(join)[0])
                    alias = query.alias_map[alias][LHS_ALIAS]
                else:
                    alias = None
        return '__'.join(column_chain)

    def resolve_join(self, query, child):
        constraint, lookup_type, annotation, value = child
        if not constraint.field:
            return

        alias = constraint.alias
        while True:
            next_alias = query.alias_map[alias][LHS_ALIAS]
            if not next_alias:
                break
            self.unref_alias(query, alias)
            alias = next_alias

        constraint.alias = alias

# TODO: distinguish in memory joins from standard joins somehow
class InMemoryJOINResolver(ConstantFieldJOINResolver):
    def __init__(self):
        self.field_chains = []
        super(InMemoryJOINResolver, self).__init__()

    def create_index(self, lookup):
        if '__' in lookup.field_name:
            field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)

            if not field_to_index:
                return

            # save old column_to_name so we can make in memory queries later on
            self.add_column_to_name(lookup.model, lookup.field_name)

            # don't add an extra field for standard lookups!
            if isinstance(lookup, StandardLookup):
                return

            # install lookup on target model
            model = self.get_model_chain(lookup.model, lookup.field_name)[-1]
            lookup.model = model
            lookup.field_name = lookup.field_name.split('__')[-1]
            super(ConstantFieldJOINResolver, self).create_index(lookup)

    def convert_insert_query(self, query):
        super(ConstantFieldJOINResolver, self).convert_insert_query(query)

    def _convert_filters(self, query, filters):
        # or queries are not supported for in-memory-JOINs
        if self.contains_OR(query.where, OR):
            return

        # start with the deepest JOIN level filter!
        all_filters = self.get_all_filters(filters)
        all_filters.sort(key=lambda item: self.get_field_chain(query, item[1][0]) and \
                         -len(self.get_field_chain(query, item[1][0])) or 0)

        for filters, child, index in all_filters:
            # check if convert_filter removed a given child from the where-tree
            if not self.contains_child(query.where, child):
                continue
            self.convert_filter(query, filters, child, index)

    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        field_chain = self.get_field_chain(query, constraint)

        if field_chain is None:
            return

        if '__' not in field_chain:
            return super(ConstantFieldJOINResolver, self).convert_filter(query,
                filters, child, index)

        pks = self.get_pks(query, field_chain, lookup_type, value)
        self.resolve_join(query, child)
        self._convert_filter(query, filters, child, index, 'in',
                             (pk for pk in pks), field_chain.split('__')[0])

    def tree_contains(self, filters, to_find, func):
        result = False
        for child in filters.children[:]:
            if func(child, to_find):
                result = True
                break
            if isinstance(child, Node):
                result = self.tree_contains(child, to_find, func)
                if result:
                    break
        return result

    def contains_OR(self, filters, or_):
        return self.tree_contains(filters, or_,
            lambda c, f: isinstance(c, Node) and c.connector == f)

    def contains_child(self, filters, to_find):
        return self.tree_contains(filters, to_find, lambda c, f: c is f)

    def get_all_filters(self, filters):
        all_filters = []
        for index, child in enumerate(filters.children[:]):
            if isinstance(child, Node):
                all_filters.extend(self.get_all_filters(child))
                continue

            all_filters.append((filters, child, index))
        return all_filters

    def index_name(self, lookup):
        # use another index_name to avoid conflicts with lookups defined on the
        # target model which are handled by the BaseBackend
        return lookup.index_name + '_in_memory_join'

    def get_pks(self, query, field_chain, lookup_type, value):
        model_chain = self.get_model_chain(query.model, field_chain)

        first_lookup = {'%s__%s' %(field_chain.rsplit('__', 1)[-1],
                                   lookup_type): value}
        self.combine_with_same_level_filter(first_lookup, query, field_chain)
        pks = model_chain[-1].objects.all().filter(**first_lookup).values_list(
            'id', flat=True)

        chains = [field_chain.rsplit('__', i+1)[0]
                  for i in range(field_chain.count('__'))]
        lookup = {}
        for model, chain in reversed(zip(model_chain[1:-1], chains[:-1])):
            lookup.update({'%s__%s' %(chain.rsplit('__', 1)[-1], 'in'):
                           (pk for pk in pks)})
            self.combine_with_same_level_filter(lookup, query, chain)
            pks = model.objects.all().filter(**lookup).values_list('id', flat=True)
        return pks

    def combine_with_same_level_filter(self, lookup, query, field_chain):
        lookup_updates = {}
        field_chains = self.get_all_field_chains(query, query.where)

        for chain, child in field_chains.items():
            if chain == field_chain:
                continue
            if field_chain.rsplit('__', 1)[0] == chain.rsplit('__', 1)[0]:
                lookup_updates ['%s__%s' %(chain.rsplit('__', 1)[1], child[1])] \
                    = child[3]

                self.remove_child(query.where, child)
                self.resolve_join(query, child)
                # TODO: update query.alias_refcount correctly!
        lookup.update(lookup_updates)

    def remove_child(self, filters, to_remove):
        ''' Removes a child object from filters. If filters doesn't contain
            children afterwoods, filters will be removed from its parent. '''

        for child in filters.children[:]:
            if child is to_remove:
                self._remove_child(filters, to_remove)
                return
            elif isinstance(child, Node):
                self.remove_child(child, to_remove)

            if hasattr(child, 'children') and not child.children:
                self.remove_child(filters, child)

    def _remove_child(self, filters, to_remove):
        result = []
        for child in filters.children[:]:
            if child is to_remove:
                continue
            result.append(child)
        filters.children = result

    def get_all_field_chains(self, query, filters):
        ''' Returns a dict mapping from field_chains to the corresponding child.'''

        field_chains = {}
        all_filters = self.get_all_filters(filters)
        for filters, child, index in all_filters:
            field_chain = self.get_field_chain(query, child[0])
            # field_chain can be None if the user didn't specified an index for it
            if field_chain:
                field_chains[field_chain] = child
        return field_chains

########NEW FILE########
__FILENAME__ = base
from django.conf import settings
from django.utils.importlib import import_module


def merge_dicts(d1, d2):
    '''Update dictionary recursively. If values for a given key exist in both dictionaries and are dict-like they are merged.'''

    for k, v in d2.iteritems():

        # Try to merge the values as if they were dicts.
        try:
            merge_dicts(d1[k], v)

        # Otherwise just overwrite the original value (if any).
        except (AttributeError, KeyError):
            d1[k] = v


class DatabaseOperations(object):
    dbindexer_compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def __init__(self):
        self._dbindexer_cache = {}

    def compiler(self, compiler_name):
        if compiler_name not in self._dbindexer_cache:
            target = super(DatabaseOperations, self).compiler(compiler_name)
            base = getattr(
                import_module(self.dbindexer_compiler_module), compiler_name)
            class Compiler(base, target):
                pass
            self._dbindexer_cache[compiler_name] = Compiler
        return self._dbindexer_cache[compiler_name]

class BaseDatabaseWrapper(object):
    def __init__(self, *args, **kwargs):
        super(BaseDatabaseWrapper, self).__init__(*args, **kwargs)
        class Operations(DatabaseOperations, self.ops.__class__):
            pass
        self.ops.__class__ = Operations
        self.ops.__init__()

def DatabaseWrapper(settings_dict, *args, **kwargs):
    target_settings = settings_dict['TARGET']
    if isinstance(target_settings, (str, unicode)):
        target_settings = settings.DATABASES[target_settings]
    engine = target_settings['ENGINE'] + '.base'
    target = import_module(engine).DatabaseWrapper
    class Wrapper(BaseDatabaseWrapper, target):
        pass

    # Update settings with target database settings (which can contain nested dicts).
    merged_settings = settings_dict.copy()
    merge_dicts(merged_settings, target_settings)

    return Wrapper(merged_settings, *args, **kwargs)

########NEW FILE########
__FILENAME__ = compiler
from .resolver import resolver
from django.utils.importlib import import_module

def __repr__(self):
    return '<%s, %s, %s, %s>' % (self.alias, self.col, self.field.name,
        self.field.model.__name__)

from django.db.models.sql.where import Constraint
Constraint.__repr__ = __repr__

# TODO: manipulate a copy of the query instead of the query itself. This has to
# be done because the query can be reused afterwards by the user so that a
# manipulated query can result in strange behavior for these cases!
# TODO: Add watching layer which gives suggestions for indexes via query inspection
# at runtime

class BaseCompiler(object):
    def convert_filters(self):
        resolver.convert_filters(self.query)

class SQLCompiler(BaseCompiler):
    def execute_sql(self, *args, **kwargs):
        self.convert_filters()
        return super(SQLCompiler, self).execute_sql(*args, **kwargs)

    def results_iter(self):
        self.convert_filters()
        return super(SQLCompiler, self).results_iter()

    def has_results(self):
        self.convert_filters()
        return super(SQLCompiler, self).has_results()

class SQLInsertCompiler(BaseCompiler):
    def execute_sql(self, return_id=False):
        resolver.convert_insert_query(self.query)
        return super(SQLInsertCompiler, self).execute_sql(return_id=return_id)

class SQLUpdateCompiler(BaseCompiler):
    pass

class SQLDeleteCompiler(BaseCompiler):
    pass

class SQLDateCompiler(BaseCompiler):
    pass

class SQLDateTimeCompiler(BaseCompiler):
    pass

class SQLAggregateCompiler(BaseCompiler):
    pass

########NEW FILE########
__FILENAME__ = lookups
from django.db import models
from djangotoolbox.fields import ListField
from copy import deepcopy

import re
regex = type(re.compile(''))

class LookupDoesNotExist(Exception):
    pass

class LookupBase(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if not isinstance(new_cls.lookup_types, (list, tuple)):
            new_cls.lookup_types = (new_cls.lookup_types, )
        return new_cls

class ExtraFieldLookup(object):
    '''Default is to behave like an exact filter on an ExtraField.'''
    __metaclass__ = LookupBase
    lookup_types = 'exact'

    def __init__(self, model=None, field_name=None, lookup_def=None,
                 new_lookup='exact', field_to_add=models.CharField(
                 max_length=500, editable=False, null=True)):
        self.field_to_add = field_to_add
        self.new_lookup = new_lookup
        self.contribute(model, field_name, lookup_def)

    def contribute(self, model, field_name, lookup_def):
        self.model = model
        self.field_name = field_name
        self.lookup_def = lookup_def

    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.field_name, self.lookup_types[0])

    def convert_lookup(self, value, lookup_type):
        # TODO: can value be a list or tuple? (in case of in yes)
        if isinstance(value, (tuple, list)):
            value = [self._convert_lookup(val, lookup_type)[1] for val in value]
        else:
            _, value = self._convert_lookup(value, lookup_type)
        return self.new_lookup, value

    def _convert_lookup(self, value, lookup_type):
        return lookup_type, value

    def convert_value(self, value):
        if value is not None:
            if isinstance(value, (tuple, list)):
                value = [self._convert_value(val) for val in value if val is not None]
            else:
                value = self._convert_value(value)
        return value

    def _convert_value(self, value):
        return value

    def matches_filter(self, model, field_name, lookup_type, value):
        return self.model == model and lookup_type in self.lookup_types \
            and field_name == self.field_name

    @classmethod
    def matches_lookup_def(cls, lookup_def):
        if lookup_def in cls.lookup_types:
            return True
        return False

    def get_field_to_add(self, field_to_index):
        field_to_add = deepcopy(self.field_to_add)
        if isinstance(field_to_index, ListField):
            field_to_add = ListField(field_to_add, editable=False, null=True)
        return field_to_add

class DateLookup(ExtraFieldLookup):
    # DateLookup is abstract so set lookup_types to None so it doesn't match
    lookup_types = None

    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'exact',
                    'field_to_add': models.IntegerField(editable=False, null=True)}
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value

class Day(DateLookup):
    lookup_types = 'day'

    def _convert_value(self, value):
        return value.day

class Month(DateLookup):
    lookup_types = 'month'

    def _convert_value(self, value):
        return value.month

class Year(DateLookup):
    lookup_types = 'year'

    def _convert_value(self, value):
        return value.year

class Weekday(DateLookup):
    lookup_types = 'week_day'

    def _convert_value(self, value):
        return value.isoweekday()

class Contains(ExtraFieldLookup):
    lookup_types = 'contains'

    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'startswith',
                    'field_to_add': ListField(models.CharField(500),
                                              editable=False, null=True)
        }
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def get_field_to_add(self, field_to_index):
        # always return a ListField of CharFields even in the case of
        # field_to_index being a ListField itself!
        return deepcopy(self.field_to_add)

    def convert_value(self, value):
        new_value = []
        if isinstance(value, (tuple, list)):
            for val in value:
                new_value.extend(self.contains_indexer(val))
        else:
            new_value = self.contains_indexer(value)
        return new_value

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value

    def contains_indexer(self, value):
        # In indexing mode we add all postfixes ('o', 'lo', ..., 'hello')
        result = []
        if value:
            result.extend([value[count:] for count in range(len(value))])
        return result

class Icontains(Contains):
    lookup_types = 'icontains'

    def convert_value(self, value):
        return [val.lower() for val in Contains.convert_value(self, value)]

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value.lower()

class Iexact(ExtraFieldLookup):
    lookup_types = 'iexact'

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value.lower()

    def _convert_value(self, value):
        return value.lower()

class Istartswith(ExtraFieldLookup):
    lookup_types = 'istartswith'

    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'startswith'}
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value.lower()

    def _convert_value(self, value):
        return value.lower()

class Endswith(ExtraFieldLookup):
    lookup_types = 'endswith'

    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'startswith'}
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value[::-1]

    def _convert_value(self, value):
        return value[::-1]

class Iendswith(Endswith):
    lookup_types = 'iendswith'

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value[::-1].lower()

    def _convert_value(self, value):
        return value[::-1].lower()

class RegexLookup(ExtraFieldLookup):
    lookup_types = ('regex', 'iregex')

    def __init__(self, *args, **kwargs):
        defaults = {'field_to_add': models.NullBooleanField(editable=False,
                                                            null=True)
        }
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def contribute(self, model, field_name, lookup_def):
        ExtraFieldLookup.contribute(self, model, field_name, lookup_def)
        if isinstance(lookup_def, regex):
            self.lookup_def = re.compile(lookup_def.pattern, re.S | re.U |
                                         (lookup_def.flags & re.I))

    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.field_name,
                                 self.lookup_def.pattern.encode('hex'))

    def is_icase(self):
        return self.lookup_def.flags & re.I

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, True

    def _convert_value(self, value):
        if self.lookup_def.match(value):
            return True
        return False

    def matches_filter(self, model, field_name, lookup_type, value):
        return self.model == model and lookup_type == \
                '%sregex' % ('i' if self.is_icase() else '') and \
                value == self.lookup_def.pattern and field_name == self.field_name

    @classmethod
    def matches_lookup_def(cls, lookup_def):
        if isinstance(lookup_def, regex):
            return True
        return False

class StandardLookup(ExtraFieldLookup):
    ''' Creates a copy of the field_to_index in order to allow querying for
        standard lookup_types on a JOINed property. '''
    # TODO: database backend can specify standardLookups
    lookup_types = ('exact', 'gt', 'gte', 'lt', 'lte', 'in', 'range', 'isnull')

    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.field_name, 'standard')

    def convert_lookup(self, value, lookup_type):
        return lookup_type, value

    def get_field_to_add(self, field_to_index):
        field_to_add = deepcopy(field_to_index)
        if isinstance(field_to_add, (models.DateTimeField,
                                    models.DateField, models.TimeField)):
            field_to_add.auto_now_add = field_to_add.auto_now = False
        field_to_add.name = self.index_name
        return field_to_add

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = resolver
from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

class Resolver(object):
    def __init__(self):
        self.backends = []
        self.load_backends(getattr(settings, 'DBINDEXER_BACKENDS',
                               ('dbindexer.backends.BaseResolver',
                                'dbindexer.backends.FKNullFix')))

    def load_backends(self, backend_paths):
        for backend in backend_paths:
                self.backends.append(self.load_backend(backend))

    def load_backend(self, path):
        module_name, attr_name = path.rsplit('.', 1)
        try:
            mod = import_module(module_name)
        except (ImportError, ValueError), e:
            raise ImproperlyConfigured('Error importing backend module %s: "%s"'
                % (module_name, e))
        try:
            return getattr(mod, attr_name)()
        except AttributeError:
            raise ImproperlyConfigured('Module "%s" does not define a "%s" backend'
                % (module_name, attr_name))

    def convert_filters(self, query):
        for backend in self.backends:
            backend.convert_filters(query)

    def create_index(self, lookup):
        for backend in self.backends:
            backend.create_index(lookup)

    def convert_insert_query(self, query):
        for backend in self.backends:
            backend.convert_insert_query(query)

resolver = Resolver()

########NEW FILE########
__FILENAME__ = tests
from django.db import models
from django.test import TestCase
from .api import register_index
from .lookups import StandardLookup
from .resolver import resolver
from djangotoolbox.fields import ListField
from datetime import datetime
import re

class ForeignIndexed2(models.Model):
    name_fi2 = models.CharField(max_length=500)
    age = models.IntegerField()

class ForeignIndexed(models.Model):
    title = models.CharField(max_length=500)
    name_fi = models.CharField(max_length=500)
    fk = models.ForeignKey(ForeignIndexed2, null=True)

class Indexed(models.Model):
    name = models.CharField(max_length=500)
    published = models.DateTimeField(auto_now_add=True)
    foreignkey = models.ForeignKey(ForeignIndexed, null=True)
    foreignkey2 = models.ForeignKey(ForeignIndexed2, related_name='idx_set', null=True)
    tags = ListField(models.CharField(max_length=500, null=True))

class NullableCharField(models.Model):
    name = models.CharField(max_length=500, null=True)

# TODO: add test for foreign key with multiple filters via different and equal paths
# to do so we have to create some entities matching equal paths but not matching
# different paths
class IndexedTest(TestCase):
    def setUp(self):
        self.backends = list(resolver.backends)
        resolver.backends = []
        resolver.load_backends(('dbindexer.backends.BaseResolver',
                      'dbindexer.backends.FKNullFix',
#                      'dbindexer.backends.InMemoryJOINResolver',
                      'dbindexer.backends.ConstantFieldJOINResolver',
        ))
        self.register_indexes()

        juubi = ForeignIndexed2(name_fi2='Juubi', age=2)
        juubi.save()
        rikudo = ForeignIndexed2(name_fi2='Rikudo', age=200)
        rikudo.save()

        kyuubi = ForeignIndexed(name_fi='Kyuubi', title='Bijuu', fk=juubi)
        hachibi= ForeignIndexed(name_fi='Hachibi', title='Bijuu', fk=rikudo)
        kyuubi.save()
        hachibi.save()

        Indexed(name='ItAchi', tags=('Sasuke', 'Madara'), foreignkey=kyuubi,
                foreignkey2=juubi).save()
        Indexed(name='YondAimE', tags=('Naruto', 'Jiraya'), foreignkey=kyuubi,
                foreignkey2=juubi).save()
        Indexed(name='Neji', tags=('Hinata'), foreignkey=hachibi,
                foreignkey2=juubi).save()
        Indexed(name='I1038593i', tags=('Sharingan'), foreignkey=hachibi,
                foreignkey2=rikudo).save()

    def tearDown(self):
        resolver.backends = self.backends

    def register_indexes(self):
        register_index(Indexed, {
            'name': ('iexact', 'endswith', 'istartswith', 'iendswith', 'contains',
                     'icontains', re.compile('^i+', re.I), re.compile('^I+'),
                     re.compile('^i\d*i$', re.I)),
            'tags': ('iexact', 'icontains', StandardLookup() ),
            'foreignkey__fk': (StandardLookup()),
            'foreignkey__title': 'iexact',
            'foreignkey__name_fi': 'iexact',
            'foreignkey__fk__name_fi2': ('iexact', 'endswith'),
            'foreignkey2__name_fi2': (StandardLookup(), 'iexact'),
            'foreignkey2__age': (StandardLookup())
        })

        register_index(ForeignIndexed, {
            'title': 'iexact',
            'name_fi': ('iexact', 'icontains'),
            'fk__name_fi2': ('iexact', 'endswith'),
            'fk__age': (StandardLookup()),
        })

        register_index(NullableCharField, {
             'name': ('iexact', 'istartswith', 'endswith', 'iendswith',)
        })

    # TODO: add tests for created indexes for all backends!
#    def test_model_fields(self):
#        field_list = [(item[0], item[0].column)
#                       for item in Indexed._meta.get_fields_with_model()]
#        print field_list
#        x()
        # in-memory JOIN backend shouldn't create multiple indexes on the foreignkey side
        # for different paths or not even for index definition on different models. Test this!
        # standard JOIN backend should always add extra fields to registered model. Test this!

    def test_joins(self):
        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi',
            foreignkey__title__iexact='biJuu')))

        self.assertEqual(0, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi',
            foreignkey2__name_fi2__iexact='Rikudo')))

        self.assertEqual(1, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__endswith='udo',
            foreignkey2__name_fi2__iexact='Rikudo')))

        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu',
            foreignkey__name_fi__iexact='kyuuBi')))

        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu',
            foreignkey__name_fi__iexact='Hachibi')))

        self.assertEqual(1, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu', name__iendswith='iMe')))

        # JOINs on one field only
        self.assertEqual(4, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
           foreignkey2__name_fi2='Juubi')))

        # text endswith instead iexact all the time :)
        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__endswith='bi')))

        # test JOINs via different paths targeting the same field
        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
           foreignkey2__name_fi2__iexact='Juubi')))

        # test standard lookups for foreign_keys
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey2__age=2)))
        self.assertEqual(4, len(Indexed.objects.all().filter(
            foreignkey2__age__lt=201)))

        # test JOINs on different model
        # standard lookups JOINs
        self.assertEqual(1, len(ForeignIndexed.objects.all().filter(
            fk__age=2)))
        self.assertEqual(2, len(ForeignIndexed.objects.all().filter(
            fk__age__lt=210)))

        # other JOINs
        self.assertEqual(1, len(ForeignIndexed.objects.all().filter(
            fk__name_fi2__iexact='juUBI')))
        self.assertEqual(1, len(ForeignIndexed.objects.all().filter(
            fk__name_fi2__endswith='bi')))

    def test_fix_fk_isnull(self):
        self.assertEqual(0, len(Indexed.objects.filter(foreignkey=None)))
        self.assertEqual(4, len(Indexed.objects.exclude(foreignkey=None)))

    def test_iexact(self):
        self.assertEqual(1, len(Indexed.objects.filter(name__iexact='itaChi')))
        self.assertEqual(1, Indexed.objects.filter(name__iexact='itaChi').count())

        self.assertEqual(2, ForeignIndexed.objects.filter(title__iexact='BIJUU').count())
        self.assertEqual(1, ForeignIndexed.objects.filter(name_fi__iexact='KYuubi').count())

        # test on list field
        self.assertEqual(1, Indexed.objects.filter(tags__iexact='SasuKE').count())

    def test_standard_lookups(self):
        self.assertEqual(1, Indexed.objects.filter(tags__exact='Naruto').count())

        # test standard lookup on foreign_key
        juubi = ForeignIndexed2.objects.all().get(name_fi2='Juubi', age=2)
        self.assertEqual(2, Indexed.objects.filter(foreignkey__fk=juubi).count())

    def test_delete(self):
        Indexed.objects.get(name__iexact='itaChi').delete()
        self.assertEqual(0, Indexed.objects.all().filter(name__iexact='itaChi').count())

    def test_delete_query(self):
        Indexed.objects.all().delete()
        self.assertEqual(0, Indexed.objects.all().filter(name__iexact='itaChi').count())

    def test_exists_query(self):
        self.assertTrue(Indexed.objects.filter(name__iexact='itaChi').exists())

    def test_istartswith(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__istartswith='iTa')))

    def test_endswith(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__endswith='imE')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iendswith='iMe')))

    def test_regex(self):
        self.assertEqual(2, len(Indexed.objects.all().filter(name__iregex='^i+')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__regex='^I+')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iregex='^i\d*i$')))

    def test_null_strings(self):
        """Test indexing with nullable CharFields, see: https://github.com/django-nonrel/django-dbindexer/issues/3."""
        NullableCharField.objects.create()

    def test_contains(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__contains='Aim')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__icontains='aim')))

        self.assertEqual(1, ForeignIndexed.objects.filter(name_fi__icontains='Yu').count())

        # test icontains on a list
        self.assertEqual(2, len(Indexed.objects.all().filter(tags__icontains='RA')))


class AutoNowIndexed(models.Model):
    published = models.DateTimeField(auto_now=True)

class AutoNowAddIndexed(models.Model):
    published = models.DateTimeField(auto_now_add=True)

class DateIndexed(models.Model):
    published = models.DateTimeField()

class DateAutoNowTest(TestCase):
    def setUp(self):
        self.backends = list(resolver.backends)
        resolver.backends = []
        resolver.load_backends(('dbindexer.backends.BaseResolver',
                      'dbindexer.backends.FKNullFix',
#                      'dbindexer.backends.InMemoryJOINResolver',
                      'dbindexer.backends.ConstantFieldJOINResolver',
        ))
        self.register_indexes()

        DateIndexed(published=datetime.now()).save()
        DateIndexed(published=datetime.now()).save()
        DateIndexed(published=datetime.now()).save()
        DateIndexed(published=datetime.now()).save()

    def tearDown(self):
        resolver.backends = self.backends

    def register_indexes(self):
        register_index(DateIndexed, {
            'published': ('month', 'day', 'year', 'week_day'),
        })

    def test_auto_now(self):
        from django.core.exceptions import ImproperlyConfigured

        self.assertRaises(ImproperlyConfigured, register_index, AutoNowIndexed, {
            'published': ('month', 'day', 'year', 'week_day'),
        })
        self.assertRaises(ImproperlyConfigured, register_index, AutoNowAddIndexed, {
            'published': ('month', 'day', 'year', 'week_day'),
        })

    def test_date_filters(self):
        now = datetime.now()
        self.assertEqual(4, len(DateIndexed.objects.all().filter(published__month=now.month)))
        self.assertEqual(4, len(DateIndexed.objects.all().filter(published__day=now.day)))
        self.assertEqual(4, len(DateIndexed.objects.all().filter(published__year=now.year)))
        self.assertEqual(4, len(DateIndexed.objects.all().filter(
            published__week_day=now.isoweekday())))

########NEW FILE########
