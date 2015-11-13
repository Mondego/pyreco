__FILENAME__ = api
"""Provide the 'autogenerate' feature which can produce migration operations
automatically."""

import logging
import re

from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.util import OrderedSet
from .compare import _compare_tables
from .render import _drop_table, _drop_column, _drop_index, _drop_constraint, \
        _add_table, _add_column, _add_index, _add_constraint, _modify_col
from .. import util

log = logging.getLogger(__name__)

###################################################
# public
def compare_metadata(context, metadata):
    """Compare a database schema to that given in a
    :class:`~sqlalchemy.schema.MetaData` instance.

    The database connection is presented in the context
    of a :class:`.MigrationContext` object, which
    provides database connectivity as well as optional
    comparison functions to use for datatypes and
    server defaults - see the "autogenerate" arguments
    at :meth:`.EnvironmentContext.configure`
    for details on these.

    The return format is a list of "diff" directives,
    each representing individual differences::

        from alembic.migration import MigrationContext
        from alembic.autogenerate import compare_metadata
        from sqlalchemy.schema import SchemaItem
        from sqlalchemy.types import TypeEngine
        from sqlalchemy import (create_engine, MetaData, Column,
                Integer, String, Table)
        import pprint

        engine = create_engine("sqlite://")

        engine.execute('''
            create table foo (
                id integer not null primary key,
                old_data varchar,
                x integer
            )''')

        engine.execute('''
            create table bar (
                data varchar
            )''')

        metadata = MetaData()
        Table('foo', metadata,
            Column('id', Integer, primary_key=True),
            Column('data', Integer),
            Column('x', Integer, nullable=False)
        )
        Table('bat', metadata,
            Column('info', String)
        )

        mc = MigrationContext.configure(engine.connect())

        diff = compare_metadata(mc, metadata)
        pprint.pprint(diff, indent=2, width=20)

    Output::

        [ ( 'add_table',
            Table('bat', MetaData(bind=None),
                Column('info', String(), table=<bat>), schema=None)),
          ( 'remove_table',
            Table(u'bar', MetaData(bind=None),
                Column(u'data', VARCHAR(), table=<bar>), schema=None)),
          ( 'add_column',
            None,
            'foo',
            Column('data', Integer(), table=<foo>)),
          ( 'remove_column',
            None,
            'foo',
            Column(u'old_data', VARCHAR(), table=None)),
          [ ( 'modify_nullable',
              None,
              'foo',
              u'x',
              { 'existing_server_default': None,
                'existing_type': INTEGER()},
              True,
              False)]]


    :param context: a :class:`.MigrationContext`
     instance.
    :param metadata: a :class:`~sqlalchemy.schema.MetaData`
     instance.

    """
    autogen_context, connection = _autogen_context(context, None)
    diffs = []

    object_filters = _get_object_filters(context.opts)
    include_schemas = context.opts.get('include_schemas', False)

    _produce_net_changes(connection, metadata, diffs, autogen_context,
                         object_filters, include_schemas)

    return diffs

###################################################
# top level

def _produce_migration_diffs(context, template_args,
                                imports, include_symbol=None,
                                include_object=None,
                                include_schemas=False):
    opts = context.opts
    metadata = opts['target_metadata']
    include_schemas = opts.get('include_schemas', include_schemas)

    object_filters = _get_object_filters(opts, include_symbol, include_object)

    if metadata is None:
        raise util.CommandError(
                "Can't proceed with --autogenerate option; environment "
                "script %s does not provide "
                "a MetaData object to the context." % (
                    context.script.env_py_location
                ))
    autogen_context, connection = _autogen_context(context, imports)

    diffs = []
    _produce_net_changes(connection, metadata, diffs,
                                autogen_context, object_filters, include_schemas)
    template_args[opts['upgrade_token']] = \
            _indent(_produce_upgrade_commands(diffs, autogen_context))
    template_args[opts['downgrade_token']] = \
            _indent(_produce_downgrade_commands(diffs, autogen_context))
    template_args['imports'] = "\n".join(sorted(imports))


def _get_object_filters(context_opts, include_symbol=None, include_object=None):
    include_symbol = context_opts.get('include_symbol', include_symbol)
    include_object = context_opts.get('include_object', include_object)

    object_filters = []
    if include_symbol:
        def include_symbol_filter(object, name, type_, reflected, compare_to):
            if type_ == "table":
                return include_symbol(name, object.schema)
            else:
                return True
        object_filters.append(include_symbol_filter)
    if include_object:
        object_filters.append(include_object)

    return object_filters


def _autogen_context(context, imports):
    opts = context.opts
    connection = context.bind
    return {
        'imports': imports,
        'connection': connection,
        'dialect': connection.dialect,
        'context': context,
        'opts': opts
    }, connection

def _indent(text):
    text = "### commands auto generated by Alembic - "\
                    "please adjust! ###\n" + text
    text += "\n### end Alembic commands ###"
    text = re.compile(r'^', re.M).sub("    ", text).strip()
    return text

###################################################
# walk structures


def _produce_net_changes(connection, metadata, diffs, autogen_context,
                            object_filters=(),
                            include_schemas=False):
    inspector = Inspector.from_engine(connection)
    # TODO: not hardcode alembic_version here ?
    conn_table_names = set()

    default_schema = connection.dialect.default_schema_name
    if include_schemas:
        schemas = set(inspector.get_schema_names())
        # replace default schema name with None
        schemas.discard("information_schema")
        # replace the "default" schema with None
        schemas.add(None)
        schemas.discard(default_schema)
    else:
        schemas = [None]

    for s in schemas:
        tables = set(inspector.get_table_names(schema=s)).\
                difference(['alembic_version'])
        conn_table_names.update(zip([s] * len(tables), tables))

    metadata_table_names = OrderedSet([(table.schema, table.name)
                                for table in metadata.sorted_tables])

    _compare_tables(conn_table_names, metadata_table_names,
                    object_filters,
                    inspector, metadata, diffs, autogen_context)


###################################################
# element comparison


###################################################
# render python


###################################################
# produce command structure

def _produce_upgrade_commands(diffs, autogen_context):
    buf = []
    for diff in diffs:
        buf.append(_invoke_command("upgrade", diff, autogen_context))
    if not buf:
        buf = ["pass"]
    return "\n".join(buf)

def _produce_downgrade_commands(diffs, autogen_context):
    buf = []
    for diff in reversed(diffs):
        buf.append(_invoke_command("downgrade", diff, autogen_context))
    if not buf:
        buf = ["pass"]
    return "\n".join(buf)

def _invoke_command(updown, args, autogen_context):
    if isinstance(args, tuple):
        return _invoke_adddrop_command(updown, args, autogen_context)
    else:
        return _invoke_modify_command(updown, args, autogen_context)

def _invoke_adddrop_command(updown, args, autogen_context):
    cmd_type = args[0]
    adddrop, cmd_type = cmd_type.split("_")

    cmd_args = args[1:] + (autogen_context,)

    _commands = {
        "table": (_drop_table, _add_table),
        "column": (_drop_column, _add_column),
        "index": (_drop_index, _add_index),
        "constraint": (_drop_constraint, _add_constraint),
    }

    cmd_callables = _commands[cmd_type]

    if (
        updown == "upgrade" and adddrop == "add"
    ) or (
        updown == "downgrade" and adddrop == "remove"
    ):
        return cmd_callables[1](*cmd_args)
    else:
        return cmd_callables[0](*cmd_args)

def _invoke_modify_command(updown, args, autogen_context):
    sname, tname, cname = args[0][1:4]
    kw = {}

    _arg_struct = {
        "modify_type": ("existing_type", "type_"),
        "modify_nullable": ("existing_nullable", "nullable"),
        "modify_default": ("existing_server_default", "server_default"),
    }
    for diff in args:
        diff_kw = diff[4]
        for arg in ("existing_type", \
                "existing_nullable", \
                "existing_server_default"):
            if arg in diff_kw:
                kw.setdefault(arg, diff_kw[arg])
        old_kw, new_kw = _arg_struct[diff[0]]
        if updown == "upgrade":
            kw[new_kw] = diff[-1]
            kw[old_kw] = diff[-2]
        else:
            kw[new_kw] = diff[-2]
            kw[old_kw] = diff[-1]

    if "nullable" in kw:
        kw.pop("existing_nullable", None)
    if "server_default" in kw:
        kw.pop("existing_server_default", None)
    return _modify_col(tname, cname, autogen_context, schema=sname, **kw)

########NEW FILE########
__FILENAME__ = compare
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import schema as sa_schema, types as sqltypes
import logging
from .. import compat
from .render import _render_server_default
from sqlalchemy.util import OrderedSet


log = logging.getLogger(__name__)

def _run_filters(object_, name, type_, reflected, compare_to, object_filters):
    for fn in object_filters:
        if not fn(object_, name, type_, reflected, compare_to):
            return False
    else:
        return True

def _compare_tables(conn_table_names, metadata_table_names,
                    object_filters,
                    inspector, metadata, diffs, autogen_context):

    default_schema = inspector.bind.dialect.default_schema_name

    # tables coming from the connection will not have "schema"
    # set if it matches default_schema_name; so we need a list
    # of table names from local metadata that also have "None" if schema
    # == default_schema_name.  Most setups will be like this anyway but
    # some are not (see #170)
    metadata_table_names_no_dflt_schema = OrderedSet([
        (schema if schema != default_schema else None, tname)
        for schema, tname in metadata_table_names
    ])

    # to adjust for the MetaData collection storing the tables either
    # as "schemaname.tablename" or just "tablename", create a new lookup
    # which will match the "non-default-schema" keys to the Table object.
    tname_to_table = dict(
                        (
                            no_dflt_schema,
                            metadata.tables[sa_schema._get_table_key(tname, schema)]
                        )
                        for no_dflt_schema, (schema, tname) in zip(
                                    metadata_table_names_no_dflt_schema,
                                    metadata_table_names)
                        )
    metadata_table_names = metadata_table_names_no_dflt_schema

    for s, tname in metadata_table_names.difference(conn_table_names):
        name = '%s.%s' % (s, tname) if s else tname
        metadata_table = tname_to_table[(s, tname)]
        if _run_filters(metadata_table, tname, "table", False, None, object_filters):
            diffs.append(("add_table", metadata_table))
            log.info("Detected added table %r", name)
            _compare_indexes_and_uniques(s, tname, object_filters,
                    None,
                    metadata_table,
                    diffs, autogen_context, inspector)

    removal_metadata = sa_schema.MetaData()
    for s, tname in conn_table_names.difference(metadata_table_names):
        name = sa_schema._get_table_key(tname, s)
        exists = name in removal_metadata.tables
        t = sa_schema.Table(tname, removal_metadata, schema=s)
        if not exists:
            inspector.reflecttable(t, None)
        if _run_filters(t, tname, "table", True, None, object_filters):
            diffs.append(("remove_table", t))
            log.info("Detected removed table %r", name)

    existing_tables = conn_table_names.intersection(metadata_table_names)

    existing_metadata = sa_schema.MetaData()
    conn_column_info = {}
    for s, tname in existing_tables:
        name = sa_schema._get_table_key(tname, s)
        exists = name in existing_metadata.tables
        t = sa_schema.Table(tname, existing_metadata, schema=s)
        if not exists:
            inspector.reflecttable(t, None)
        conn_column_info[(s, tname)] = t

    for s, tname in sorted(existing_tables):
        name = '%s.%s' % (s, tname) if s else tname
        metadata_table = tname_to_table[(s, tname)]
        conn_table = existing_metadata.tables[name]

        if _run_filters(metadata_table, tname, "table", False, conn_table, object_filters):
            _compare_columns(s, tname, object_filters,
                    conn_table,
                    metadata_table,
                    diffs, autogen_context, inspector)
            _compare_indexes_and_uniques(s, tname, object_filters,
                    conn_table,
                    metadata_table,
                    diffs, autogen_context, inspector)

    # TODO:
    # table constraints
    # sequences

def _make_index(params, conn_table):
    return sa_schema.Index(
            params['name'],
            *[conn_table.c[cname] for cname in params['column_names']],
            unique=params['unique']
    )

def _make_unique_constraint(params, conn_table):
    return sa_schema.UniqueConstraint(
            *[conn_table.c[cname] for cname in params['column_names']],
            name=params['name']
    )

def _compare_columns(schema, tname, object_filters, conn_table, metadata_table,
                                diffs, autogen_context, inspector):
    name = '%s.%s' % (schema, tname) if schema else tname
    metadata_cols_by_name = dict((c.name, c) for c in metadata_table.c)
    conn_col_names = dict((c.name, c) for c in conn_table.c)
    metadata_col_names = OrderedSet(sorted(metadata_cols_by_name))

    for cname in metadata_col_names.difference(conn_col_names):
        if _run_filters(metadata_cols_by_name[cname], cname,
                                "column", False, None, object_filters):
            diffs.append(
                ("add_column", schema, tname, metadata_cols_by_name[cname])
            )
            log.info("Detected added column '%s.%s'", name, cname)

    for cname in set(conn_col_names).difference(metadata_col_names):
        if _run_filters(conn_table.c[cname], cname,
                                "column", True, None, object_filters):
            diffs.append(
                ("remove_column", schema, tname, conn_table.c[cname])
            )
            log.info("Detected removed column '%s.%s'", name, cname)

    for colname in metadata_col_names.intersection(conn_col_names):
        metadata_col = metadata_cols_by_name[colname]
        conn_col = conn_table.c[colname]
        if not _run_filters(
                    metadata_col, colname, "column", False, conn_col, object_filters):
            continue
        col_diff = []
        _compare_type(schema, tname, colname,
            conn_col,
            metadata_col,
            col_diff, autogen_context
        )
        _compare_nullable(schema, tname, colname,
            conn_col,
            metadata_col.nullable,
            col_diff, autogen_context
        )
        _compare_server_default(schema, tname, colname,
            conn_col,
            metadata_col,
            col_diff, autogen_context
        )
        if col_diff:
            diffs.append(col_diff)

class _constraint_sig(object):
    def __eq__(self, other):
        return self.const == other.const

    def __ne__(self, other):
        return self.const != other.const

    def __hash__(self):
        return hash(self.const)

class _uq_constraint_sig(_constraint_sig):
    is_index = False
    is_unique = True

    def __init__(self, const):
        self.const = const
        self.name = const.name
        self.sig = tuple(sorted([col.name for col in const.columns]))

    @property
    def column_names(self):
        return [col.name for col in self.const.columns]

class _ix_constraint_sig(_constraint_sig):
    is_index = True

    def __init__(self, const):
        self.const = const
        self.name = const.name
        self.sig = tuple(sorted([col.name for col in const.columns]))
        self.is_unique = bool(const.unique)

    @property
    def column_names(self):
        return _get_index_column_names(self.const)

def _get_index_column_names(idx):
    if compat.sqla_08:
        return [getattr(exp, "name", None) for exp in idx.expressions]
    else:
        return [getattr(col, "name", None) for col in idx.columns]

def _compare_indexes_and_uniques(schema, tname, object_filters, conn_table,
            metadata_table, diffs, autogen_context, inspector):

    is_create_table = conn_table is None

    # 1a. get raw indexes and unique constraints from metadata ...
    metadata_unique_constraints = set(uq for uq in metadata_table.constraints
            if isinstance(uq, sa_schema.UniqueConstraint)
    )
    metadata_indexes = set(metadata_table.indexes)

    conn_uniques = conn_indexes = frozenset()

    supports_unique_constraints = False

    if conn_table is not None:
        # 1b. ... and from connection, if the table exists
        if hasattr(inspector, "get_unique_constraints"):
            try:
                conn_uniques = inspector.get_unique_constraints(
                                                tname, schema=schema)
                supports_unique_constraints = True
            except NotImplementedError:
                pass
        try:
            conn_indexes = inspector.get_indexes(tname, schema=schema)
        except NotImplementedError:
            pass

        # 2. convert conn-level objects from raw inspector records
        # into schema objects
        conn_uniques = set(_make_unique_constraint(uq_def, conn_table)
                                        for uq_def in conn_uniques)
        conn_indexes = set(_make_index(ix, conn_table) for ix in conn_indexes)

    # 3. give the dialect a chance to omit indexes and constraints that
    # we know are either added implicitly by the DB or that the DB
    # can't accurately report on
    autogen_context['context'].impl.\
                                correct_for_autogen_constraints(
                                        conn_uniques, conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes
                                )

    # 4. organize the constraints into "signature" collections, the
    # _constraint_sig() objects provide a consistent facade over both
    # Index and UniqueConstraint so we can easily work with them
    # interchangeably
    metadata_unique_constraints = set(_uq_constraint_sig(uq)
                                    for uq in metadata_unique_constraints
                                    )

    metadata_indexes = set(_ix_constraint_sig(ix) for ix in metadata_indexes)

    conn_unique_constraints = set(_uq_constraint_sig(uq) for uq in conn_uniques)

    conn_indexes = set(_ix_constraint_sig(ix) for ix in conn_indexes)

    # 5. index things by name, for those objects that have names
    metadata_names = dict(
                        (c.name, c) for c in
                        metadata_unique_constraints.union(metadata_indexes)
                        if c.name is not None)

    conn_uniques_by_name = dict((c.name, c) for c in conn_unique_constraints)
    conn_indexes_by_name = dict((c.name, c) for c in conn_indexes)

    conn_names = dict((c.name, c) for c in
                    conn_unique_constraints.union(conn_indexes)
                            if c.name is not None)

    doubled_constraints = dict(
        (name, (conn_uniques_by_name[name], conn_indexes_by_name[name]))
        for name in set(conn_uniques_by_name).intersection(conn_indexes_by_name)
    )

    # 6. index things by "column signature", to help with unnamed unique
    # constraints.
    conn_uniques_by_sig = dict((uq.sig, uq) for uq in conn_unique_constraints)
    metadata_uniques_by_sig = dict(
                            (uq.sig, uq) for uq in metadata_unique_constraints)
    metadata_indexes_by_sig = dict(
                            (ix.sig, ix) for ix in metadata_indexes)
    unnamed_metadata_uniques = dict((uq.sig, uq) for uq in
                            metadata_unique_constraints if uq.name is None)

    # assumptions:
    # 1. a unique constraint or an index from the connection *always*
    #    has a name.
    # 2. an index on the metadata side *always* has a name.
    # 3. a unique constraint on the metadata side *might* have a name.
    # 4. The backend may double up indexes as unique constraints and
    #    vice versa (e.g. MySQL, Postgresql)

    def obj_added(obj):
        if obj.is_index:
            diffs.append(("add_index", obj.const))
            log.info("Detected added index '%s' on %s",
                obj.name, ', '.join([
                    "'%s'" % obj.column_names
                    ])
            )
        else:
            if not supports_unique_constraints:
                # can't report unique indexes as added if we don't
                # detect them
                return
            if is_create_table:
                # unique constraints are created inline with table defs
                return
            diffs.append(("add_constraint", obj.const))
            log.info("Detected added unique constraint '%s' on %s",
                obj.name, ', '.join([
                    "'%s'" % obj.column_names
                    ])
            )

    def obj_removed(obj):
        if obj.is_index:
            if obj.is_unique and not supports_unique_constraints:
                # many databases double up unique constraints
                # as unique indexes.  without that list we can't
                # be sure what we're doing here
                return

            diffs.append(("remove_index", obj.const))
            log.info("Detected removed index '%s' on '%s'", obj.name, tname)
        else:
            diffs.append(("remove_constraint", obj.const))
            log.info("Detected removed unique constraint '%s' on '%s'",
                obj.name, tname
            )

    def obj_changed(old, new, msg):
        if old.is_index:
            log.info("Detected changed index '%s' on '%s':%s",
                    old.name, tname, ', '.join(msg)
                )
            diffs.append(("remove_index", old.const))
            diffs.append(("add_index", new.const))
        else:
            log.info("Detected changed unique constraint '%s' on '%s':%s",
                    old.name, tname, ', '.join(msg)
                )
            diffs.append(("remove_constraint", old.const))
            diffs.append(("add_constraint", new.const))

    for added_name in sorted(set(metadata_names).difference(conn_names)):
        obj = metadata_names[added_name]
        obj_added(obj)


    for existing_name in sorted(set(metadata_names).intersection(conn_names)):
        metadata_obj = metadata_names[existing_name]

        if existing_name in doubled_constraints:
            conn_uq, conn_idx = doubled_constraints[existing_name]
            if metadata_obj.is_index:
                conn_obj = conn_idx
            else:
                conn_obj = conn_uq
        else:
            conn_obj = conn_names[existing_name]

        if conn_obj.is_index != metadata_obj.is_index:
            obj_removed(conn_obj)
            obj_added(metadata_obj)
        else:
            msg = []
            if conn_obj.is_unique != metadata_obj.is_unique:
                msg.append(' unique=%r to unique=%r' % (
                    conn_obj.is_unique, metadata_obj.is_unique
                ))
            if conn_obj.sig != metadata_obj.sig:
                msg.append(' columns %r to %r' % (
                    conn_obj.sig, metadata_obj.sig
                ))

            if msg:
                obj_changed(conn_obj, metadata_obj, msg)


    for removed_name in sorted(set(conn_names).difference(metadata_names)):
        conn_obj = conn_names[removed_name]
        if not conn_obj.is_index and conn_obj.sig in unnamed_metadata_uniques:
            continue
        elif removed_name in doubled_constraints:
            if conn_obj.sig not in metadata_indexes_by_sig and \
                conn_obj.sig not in metadata_uniques_by_sig:
                conn_uq, conn_idx = doubled_constraints[removed_name]
                obj_removed(conn_uq)
                obj_removed(conn_idx)
        else:
            obj_removed(conn_obj)

    for uq_sig in unnamed_metadata_uniques:
        if uq_sig not in conn_uniques_by_sig:
            obj_added(unnamed_metadata_uniques[uq_sig])


def _compare_nullable(schema, tname, cname, conn_col,
                            metadata_col_nullable, diffs,
                            autogen_context):
    conn_col_nullable = conn_col.nullable
    if conn_col_nullable is not metadata_col_nullable:
        diffs.append(
            ("modify_nullable", schema, tname, cname,
                {
                    "existing_type": conn_col.type,
                    "existing_server_default": conn_col.server_default,
                },
                conn_col_nullable,
                metadata_col_nullable),
        )
        log.info("Detected %s on column '%s.%s'",
            "NULL" if metadata_col_nullable else "NOT NULL",
            tname,
            cname
        )

def _compare_type(schema, tname, cname, conn_col,
                            metadata_col, diffs,
                            autogen_context):

    conn_type = conn_col.type
    metadata_type = metadata_col.type
    if conn_type._type_affinity is sqltypes.NullType:
        log.info("Couldn't determine database type "
                    "for column '%s.%s'", tname, cname)
        return
    if metadata_type._type_affinity is sqltypes.NullType:
        log.info("Column '%s.%s' has no type within "
                        "the model; can't compare", tname, cname)
        return

    isdiff = autogen_context['context']._compare_type(conn_col, metadata_col)

    if isdiff:

        diffs.append(
            ("modify_type", schema, tname, cname,
                    {
                        "existing_nullable": conn_col.nullable,
                        "existing_server_default": conn_col.server_default,
                    },
                    conn_type,
                    metadata_type),
        )
        log.info("Detected type change from %r to %r on '%s.%s'",
            conn_type, metadata_type, tname, cname
        )

def _compare_server_default(schema, tname, cname, conn_col, metadata_col,
                                diffs, autogen_context):

    metadata_default = metadata_col.server_default
    conn_col_default = conn_col.server_default
    if conn_col_default is None and metadata_default is None:
        return False
    rendered_metadata_default = _render_server_default(
                            metadata_default, autogen_context)
    rendered_conn_default = conn_col.server_default.arg.text \
                            if conn_col.server_default else None
    isdiff = autogen_context['context']._compare_server_default(
                        conn_col, metadata_col,
                        rendered_metadata_default,
                        rendered_conn_default
                    )
    if isdiff:
        conn_col_default = rendered_conn_default
        diffs.append(
            ("modify_default", schema, tname, cname,
                {
                    "existing_nullable": conn_col.nullable,
                    "existing_type": conn_col.type,
                },
                conn_col_default,
                metadata_default),
        )
        log.info("Detected server default on column '%s.%s'",
            tname,
            cname
        )




########NEW FILE########
__FILENAME__ = render
from sqlalchemy import schema as sa_schema, types as sqltypes, sql
import logging
from .. import compat
import re
from ..compat import string_types

log = logging.getLogger(__name__)

try:
    from sqlalchemy.sql.naming import conv
    def _render_gen_name(autogen_context, name):
        if isinstance(name, conv):
            return _f_name(_alembic_autogenerate_prefix(autogen_context), name)
        else:
            return name
except ImportError:
    def _render_gen_name(autogen_context, name):
        return name

class _f_name(object):
    def __init__(self, prefix, name):
        self.prefix = prefix
        self.name = name

    def __repr__(self):
        return "%sf(%r)" % (self.prefix, self.name)

def _render_potential_expr(value, autogen_context):
    if isinstance(value, sql.ClauseElement):
        if compat.sqla_08:
            compile_kw = dict(compile_kwargs={'literal_binds': True})
        else:
            compile_kw = {}

        return "%(prefix)stext(%(sql)r)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "sql": str(
                    value.compile(dialect=autogen_context['dialect'],
                    **compile_kw)
                )
        }

    else:
        return repr(value)

def _add_table(table, autogen_context):
    text = "%(prefix)screate_table(%(tablename)r,\n%(args)s" % {
        'tablename': table.name,
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'args': ',\n'.join(
            [col for col in
                [_render_column(col, autogen_context) for col in table.c]
            if col] +
            sorted([rcons for rcons in
                [_render_constraint(cons, autogen_context) for cons in
                    table.constraints]
                if rcons is not None
            ])
        )
    }
    if table.schema:
        text += ",\nschema=%r" % table.schema
    for k in sorted(table.kwargs):
        text += ",\n%s=%r" % (k.replace(" ", "_"), table.kwargs[k])
    text += "\n)"
    return text

def _drop_table(table, autogen_context):
    text = "%(prefix)sdrop_table(%(tname)r" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": table.name
        }
    if table.schema:
        text += ", schema=%r" % table.schema
    text += ")"
    return text

def _add_index(index, autogen_context):
    """
    Generate Alembic operations for the CREATE INDEX of an
    :class:`~sqlalchemy.schema.Index` instance.
    """
    from .compare import _get_index_column_names

    text = "%(prefix)screate_index(%(name)r, '%(table)s', %(columns)s, "\
                    "unique=%(unique)r%(schema)s%(kwargs)s)" % {
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'name': _render_gen_name(autogen_context, index.name),
        'table': index.table.name,
        'columns': _get_index_column_names(index),
        'unique': index.unique or False,
        'schema': (", schema='%s'" % index.table.schema) if index.table.schema else '',
        'kwargs': (', '+', '.join(
            ["%s=%s" % (key, _render_potential_expr(val, autogen_context))
                for key, val in index.kwargs.items()]))\
            if len(index.kwargs) else ''
    }
    return text

def _drop_index(index, autogen_context):
    """
    Generate Alembic operations for the DROP INDEX of an
    :class:`~sqlalchemy.schema.Index` instance.
    """
    text = "%(prefix)sdrop_index(%(name)r, "\
                "table_name='%(table_name)s'%(schema)s)" % {
            'prefix': _alembic_autogenerate_prefix(autogen_context),
            'name': _render_gen_name(autogen_context, index.name),
            'table_name': index.table.name,
            'schema': ((", schema='%s'" % index.table.schema)
                       if index.table.schema else '')
        }
    return text


def _render_unique_constraint(constraint, autogen_context):
    rendered = _user_defined_render("unique", constraint, autogen_context)
    if rendered is not False:
        return rendered

    return _uq_constraint(constraint, autogen_context, False)


def _add_unique_constraint(constraint, autogen_context):
    """
    Generate Alembic operations for the ALTER TABLE .. ADD CONSTRAINT ...
    UNIQUE of a :class:`~sqlalchemy.schema.UniqueConstraint` instance.
    """
    return _uq_constraint(constraint, autogen_context, True)

def _uq_constraint(constraint, autogen_context, alter):
    opts = []
    if constraint.deferrable:
        opts.append(("deferrable", str(constraint.deferrable)))
    if constraint.initially:
        opts.append(("initially", str(constraint.initially)))
    if alter and constraint.table.schema:
        opts.append(("schema", str(constraint.table.schema)))
    if not alter and constraint.name:
        opts.append(("name", _render_gen_name(autogen_context, constraint.name)))

    if alter:
        args = [repr(_render_gen_name(autogen_context, constraint.name)),
                        repr(constraint.table.name)]
        args.append(repr([col.name for col in constraint.columns]))
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)screate_unique_constraint(%(args)s)" % {
                'prefix': _alembic_autogenerate_prefix(autogen_context),
                'args': ", ".join(args)
            }
    else:
        args = [repr(col.name) for col in constraint.columns]
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)sUniqueConstraint(%(args)s)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "args": ", ".join(args)
        }


def _add_fk_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_pk_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_check_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_constraint(constraint, autogen_context):
    """
    Dispatcher for the different types of constraints.
    """
    funcs = {
        "unique_constraint": _add_unique_constraint,
        "foreign_key_constraint": _add_fk_constraint,
        "primary_key_constraint": _add_pk_constraint,
        "check_constraint": _add_check_constraint,
        "column_check_constraint": _add_check_constraint,
    }
    return funcs[constraint.__visit_name__](constraint, autogen_context)

def _drop_constraint(constraint, autogen_context):
    """
    Generate Alembic operations for the ALTER TABLE ... DROP CONSTRAINT
    of a  :class:`~sqlalchemy.schema.UniqueConstraint` instance.
    """
    text = "%(prefix)sdrop_constraint(%(name)r, '%(table_name)s'%(schema)s)" % {
            'prefix': _alembic_autogenerate_prefix(autogen_context),
            'name': _render_gen_name(autogen_context, constraint.name),
            'table_name': constraint.table.name,
            'schema': (", schema='%s'" % constraint.table.schema)
                      if constraint.table.schema else '',
    }
    return text

def _add_column(schema, tname, column, autogen_context):
    text = "%(prefix)sadd_column(%(tname)r, %(column)s" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": tname,
            "column": _render_column(column, autogen_context)
            }
    if schema:
        text += ", schema=%r" % schema
    text += ")"
    return text

def _drop_column(schema, tname, column, autogen_context):
    text = "%(prefix)sdrop_column(%(tname)r, %(cname)r" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": tname,
            "cname": column.name
            }
    if schema:
        text += ", schema=%r" % schema
    text += ")"
    return text

def _modify_col(tname, cname,
                autogen_context,
                server_default=False,
                type_=None,
                nullable=None,
                existing_type=None,
                existing_nullable=None,
                existing_server_default=False,
                schema=None):
    indent = " " * 11
    text = "%(prefix)salter_column(%(tname)r, %(cname)r" % {
                            'prefix': _alembic_autogenerate_prefix(
                                                autogen_context),
                            'tname': tname,
                            'cname': cname}
    text += ",\n%sexisting_type=%s" % (indent,
                    _repr_type(existing_type, autogen_context))
    if server_default is not False:
        rendered = _render_server_default(
                                server_default, autogen_context)
        text += ",\n%sserver_default=%s" % (indent, rendered)

    if type_ is not None:
        text += ",\n%stype_=%s" % (indent,
                        _repr_type(type_, autogen_context))
    if nullable is not None:
        text += ",\n%snullable=%r" % (
                        indent, nullable,)
    if existing_nullable is not None:
        text += ",\n%sexisting_nullable=%r" % (
                        indent, existing_nullable)
    if existing_server_default:
        rendered = _render_server_default(
                            existing_server_default,
                            autogen_context)
        text += ",\n%sexisting_server_default=%s" % (
                        indent, rendered)
    if schema:
        text += ",\n%sschema=%r" % (indent, schema)
    text += ")"
    return text

def _user_autogenerate_prefix(autogen_context):
    prefix = autogen_context['opts']['user_module_prefix']
    if prefix is None:
        return _sqlalchemy_autogenerate_prefix(autogen_context)
    else:
        return prefix

def _sqlalchemy_autogenerate_prefix(autogen_context):
    return autogen_context['opts']['sqlalchemy_module_prefix'] or ''

def _alembic_autogenerate_prefix(autogen_context):
    return autogen_context['opts']['alembic_module_prefix'] or ''

def _user_defined_render(type_, object_, autogen_context):
    if 'opts' in autogen_context and \
            'render_item' in autogen_context['opts']:
        render = autogen_context['opts']['render_item']
        if render:
            rendered = render(type_, object_, autogen_context)
            if rendered is not False:
                return rendered
    return False

def _render_column(column, autogen_context):
    rendered = _user_defined_render("column", column, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if column.server_default:
        rendered = _render_server_default(
                            column.server_default, autogen_context
                    )
        if rendered:
            opts.append(("server_default", rendered))

    if not column.autoincrement:
        opts.append(("autoincrement", column.autoincrement))

    if column.nullable is not None:
        opts.append(("nullable", column.nullable))

    # TODO: for non-ascii colname, assign a "key"
    return "%(prefix)sColumn(%(name)r, %(type)s, %(kw)s)" % {
        'prefix': _sqlalchemy_autogenerate_prefix(autogen_context),
        'name': column.name,
        'type': _repr_type(column.type, autogen_context),
        'kw': ", ".join(["%s=%s" % (kwname, val) for kwname, val in opts])
    }

def _render_server_default(default, autogen_context):
    rendered = _user_defined_render("server_default", default, autogen_context)
    if rendered is not False:
        return rendered

    if isinstance(default, sa_schema.DefaultClause):
        if isinstance(default.arg, string_types):
            default = default.arg
        else:
            default = str(default.arg.compile(
                            dialect=autogen_context['dialect']))
    if isinstance(default, string_types):
        # TODO: this is just a hack to get
        # tests to pass until we figure out
        # WTF sqlite is doing
        default = re.sub(r"^'|'$", "", default)
        return repr(default)
    else:
        return None

def _repr_type(type_, autogen_context):
    rendered = _user_defined_render("type", type_, autogen_context)
    if rendered is not False:
        return rendered

    mod = type(type_).__module__
    imports = autogen_context.get('imports', None)
    if mod.startswith("sqlalchemy.dialects"):
        dname = re.match(r"sqlalchemy\.dialects\.(\w+)", mod).group(1)
        if imports is not None:
            imports.add("from sqlalchemy.dialects import %s" % dname)
        return "%s.%r" % (dname, type_)
    elif mod.startswith("sqlalchemy"):
        prefix = _sqlalchemy_autogenerate_prefix(autogen_context)
        return "%s%r" % (prefix, type_)
    else:
        prefix = _user_autogenerate_prefix(autogen_context)
        return "%s%r" % (prefix, type_)

def _render_constraint(constraint, autogen_context):
    renderer = _constraint_renderers.get(type(constraint), None)
    if renderer:
        return renderer(constraint, autogen_context)
    else:
        return None

def _render_primary_key(constraint, autogen_context):
    rendered = _user_defined_render("primary_key", constraint, autogen_context)
    if rendered is not False:
        return rendered

    if not constraint.columns:
        return None

    opts = []
    if constraint.name:
        opts.append(("name", repr(_render_gen_name(autogen_context, constraint.name))))
    return "%(prefix)sPrimaryKeyConstraint(%(args)s)" % {
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
        "args": ", ".join(
            [repr(c.key) for c in constraint.columns] +
            ["%s=%s" % (kwname, val) for kwname, val in opts]
        ),
    }

def _fk_colspec(fk, metadata_schema):
    """Implement a 'safe' version of ForeignKey._get_colspec() that
    never tries to resolve the remote table.

    """
    if metadata_schema is None:
        return fk._get_colspec()
    else:
        # need to render schema breaking up tokens by hand, since the
        # ForeignKeyConstraint here may not actually have a remote
        # Table present
        tokens = fk._colspec.split(".")
        # no schema in the colspec, render it
        if len(tokens) == 2:
            return "%s.%s" % (metadata_schema, fk._colspec)
        else:
            return fk._colspec

def _render_foreign_key(constraint, autogen_context):
    rendered = _user_defined_render("foreign_key", constraint, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if constraint.name:
        opts.append(("name", repr(_render_gen_name(autogen_context, constraint.name))))
    if constraint.onupdate:
        opts.append(("onupdate", repr(constraint.onupdate)))
    if constraint.ondelete:
        opts.append(("ondelete", repr(constraint.ondelete)))
    if constraint.initially:
        opts.append(("initially", repr(constraint.initially)))
    if constraint.deferrable:
        opts.append(("deferrable", repr(constraint.deferrable)))
    if constraint.use_alter:
        opts.append(("use_alter", repr(constraint.use_alter)))

    apply_metadata_schema = constraint.parent.metadata.schema
    return "%(prefix)sForeignKeyConstraint([%(cols)s], "\
            "[%(refcols)s], %(args)s)" % {
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
        "cols": ", ".join("'%s'" % f.parent.key for f in constraint.elements),
        "refcols": ", ".join(repr(_fk_colspec(f, apply_metadata_schema))
                            for f in constraint.elements),
        "args": ", ".join(
            ["%s=%s" % (kwname, val) for kwname, val in opts]
        ),
    }

def _render_check_constraint(constraint, autogen_context):
    rendered = _user_defined_render("check", constraint, autogen_context)
    if rendered is not False:
        return rendered

    # detect the constraint being part of
    # a parent type which is probably in the Table already.
    # ideally SQLAlchemy would give us more of a first class
    # way to detect this.
    if constraint._create_rule and \
        hasattr(constraint._create_rule, 'target') and \
        isinstance(constraint._create_rule.target,
                sqltypes.TypeEngine):
        return None
    opts = []
    if constraint.name:
        opts.append(("name", repr(_render_gen_name(autogen_context, constraint.name))))
    return "%(prefix)sCheckConstraint(%(sqltext)r%(opts)s)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "opts": ", " + (", ".join("%s=%s" % (k, v)
                            for k, v in opts)) if opts else "",
            "sqltext": str(
                constraint.sqltext.compile(
                    dialect=autogen_context['dialect']
                )
            )
        }

_constraint_renderers = {
    sa_schema.PrimaryKeyConstraint: _render_primary_key,
    sa_schema.ForeignKeyConstraint: _render_foreign_key,
    sa_schema.UniqueConstraint: _render_unique_constraint,
    sa_schema.CheckConstraint: _render_check_constraint
}

########NEW FILE########
__FILENAME__ = command
import os

from .script import ScriptDirectory
from .environment import EnvironmentContext
from . import util, autogenerate as autogen

def list_templates(config):
    """List available templates"""

    config.print_stdout("Available templates:\n")
    for tempname in os.listdir(config.get_template_directory()):
        with open(os.path.join(
                        config.get_template_directory(),
                        tempname,
                        'README')) as readme:
            synopsis = next(readme)
        config.print_stdout("%s - %s", tempname, synopsis)

    config.print_stdout("\nTemplates are used via the 'init' command, e.g.:")
    config.print_stdout("\n  alembic init --template pylons ./scripts")

def init(config, directory, template='generic'):
    """Initialize a new scripts directory."""

    if os.access(directory, os.F_OK):
        raise util.CommandError("Directory %s already exists" % directory)

    template_dir = os.path.join(config.get_template_directory(),
                                    template)
    if not os.access(template_dir, os.F_OK):
        raise util.CommandError("No such template %r" % template)

    util.status("Creating directory %s" % os.path.abspath(directory),
                os.makedirs, directory)

    versions = os.path.join(directory, 'versions')
    util.status("Creating directory %s" % os.path.abspath(versions),
                os.makedirs, versions)

    script = ScriptDirectory(directory)

    for file_ in os.listdir(template_dir):
        file_path = os.path.join(template_dir, file_)
        if file_ == 'alembic.ini.mako':
            config_file = os.path.abspath(config.config_file_name)
            if os.access(config_file, os.F_OK):
                util.msg("File %s already exists, skipping" % config_file)
            else:
                script._generate_template(
                    file_path,
                    config_file,
                    script_location=directory
                )
        elif os.path.isfile(file_path):
            output_file = os.path.join(directory, file_)
            script._copy_file(
                file_path,
                output_file
            )

    util.msg("Please edit configuration/connection/logging "\
            "settings in %r before proceeding." % config_file)

def revision(config, message=None, autogenerate=False, sql=False):
    """Create a new revision file."""

    script = ScriptDirectory.from_config(config)
    template_args = {
        'config': config  # Let templates use config for
                          # e.g. multiple databases
    }
    imports = set()

    environment = util.asbool(
        config.get_main_option("revision_environment")
    )

    if autogenerate:
        environment = True
        def retrieve_migrations(rev, context):
            if script.get_revision(rev) is not script.get_revision("head"):
                raise util.CommandError("Target database is not up to date.")
            autogen._produce_migration_diffs(context, template_args, imports)
            return []
    elif environment:
        def retrieve_migrations(rev, context):
            return []

    if environment:
        with EnvironmentContext(
            config,
            script,
            fn=retrieve_migrations,
            as_sql=sql,
            template_args=template_args,
        ):
            script.run_env()
    return script.generate_revision(util.rev_id(), message, refresh=True,
                                    **template_args)


def upgrade(config, revision, sql=False, tag=None):
    """Upgrade to a later version."""

    script = ScriptDirectory.from_config(config)

    starting_rev = None
    if ":" in revision:
        if not sql:
            raise util.CommandError("Range revision not allowed")
        starting_rev, revision = revision.split(':', 2)

    def upgrade(rev, context):
        return script._upgrade_revs(revision, rev)

    with EnvironmentContext(
        config,
        script,
        fn=upgrade,
        as_sql=sql,
        starting_rev=starting_rev,
        destination_rev=revision,
        tag=tag
    ):
        script.run_env()

def downgrade(config, revision, sql=False, tag=None):
    """Revert to a previous version."""

    script = ScriptDirectory.from_config(config)
    starting_rev = None
    if ":" in revision:
        if not sql:
            raise util.CommandError("Range revision not allowed")
        starting_rev, revision = revision.split(':', 2)
    elif sql:
        raise util.CommandError("downgrade with --sql requires <fromrev>:<torev>")

    def downgrade(rev, context):
        return script._downgrade_revs(revision, rev)

    with EnvironmentContext(
        config,
        script,
        fn=downgrade,
        as_sql=sql,
        starting_rev=starting_rev,
        destination_rev=revision,
        tag=tag
    ):
        script.run_env()

def history(config, rev_range=None):
    """List changeset scripts in chronological order."""

    script = ScriptDirectory.from_config(config)
    if rev_range is not None:
        if ":" not in rev_range:
            raise util.CommandError(
                    "History range requires [start]:[end], "
                    "[start]:, or :[end]")
        base, head = rev_range.strip().split(":")
    else:
        base = head = None

    def _display_history(config, script, base, head):
        for sc in script.walk_revisions(
                                base=base or "base",
                                head=head or "head"):
            if sc.is_head:
                config.print_stdout("")
            config.print_stdout(sc.log_entry)

    def _display_history_w_current(config, script, base=None, head=None):
        def _display_current_history(rev, context):
            if head is None:
                _display_history(config, script, base, rev)
            elif base is None:
                _display_history(config, script, rev, head)
            return []

        with EnvironmentContext(
            config,
            script,
            fn=_display_current_history
        ):
            script.run_env()

    if base == "current":
        _display_history_w_current(config, script, head=head)
    elif head == "current":
        _display_history_w_current(config, script, base=base)
    else:
        _display_history(config, script, base, head)


def branches(config):
    """Show current un-spliced branch points"""
    script = ScriptDirectory.from_config(config)
    for sc in script.walk_revisions():
        if sc.is_branch_point:
            config.print_stdout(sc)
            for rev in sc.nextrev:
                config.print_stdout("%s -> %s",
                    " " * len(str(sc.down_revision)),
                    script.get_revision(rev)
                )

def current(config, head_only=False):
    """Display the current revision for each database."""

    script = ScriptDirectory.from_config(config)
    def display_version(rev, context):
        rev = script.get_revision(rev)

        if head_only:
            config.print_stdout("%s%s" % (
                rev.revision if rev else None,
                " (head)" if rev and rev.is_head else ""))

        else:
            config.print_stdout("Current revision for %s: %s",
                                util.obfuscate_url_pw(
                                    context.connection.engine.url),
                                rev)
        return []

    with EnvironmentContext(
        config,
        script,
        fn=display_version
    ):
        script.run_env()

def stamp(config, revision, sql=False, tag=None):
    """'stamp' the revision table with the given revision; don't
    run any migrations."""

    script = ScriptDirectory.from_config(config)
    def do_stamp(rev, context):
        if sql:
            current = False
        else:
            current = context._current_rev()
        dest = script.get_revision(revision)
        if dest is not None:
            dest = dest.revision
        context._update_current_rev(current, dest)
        return []
    with EnvironmentContext(
        config,
        script,
        fn=do_stamp,
        as_sql=sql,
        destination_rev=revision,
        tag=tag
    ):
        script.run_env()

def splice(config, parent, child):
    """'splice' two branches, creating a new revision file.

    this command isn't implemented right now.

    """
    raise NotImplementedError()

########NEW FILE########
__FILENAME__ = compat
import io
import sys
from sqlalchemy import __version__ as sa_version

if sys.version_info < (2, 6):
    raise NotImplementedError("Python 2.6 or greater is required.")

sqla_08 = sa_version >= '0.8.0'
sqla_09 = sa_version >= '0.9.0'

py2k = sys.version_info < (3, 0)
py3k = sys.version_info >= (3, 0)
py33 = sys.version_info >= (3, 3)

if py3k:
    import builtins as compat_builtins
    string_types = str,
    binary_type = bytes
    text_type = str
    def callable(fn):
        return hasattr(fn, '__call__')

    def u(s):
        return s

else:
    import __builtin__ as compat_builtins
    string_types = basestring,
    binary_type = str
    text_type = unicode
    callable = callable

    def u(s):
        return unicode(s, "utf-8")

if py3k:
    from configparser import ConfigParser as SafeConfigParser
    import configparser
else:
    from ConfigParser import SafeConfigParser
    import ConfigParser as configparser

if py2k:
    from mako.util import parse_encoding

if py33:
    from importlib import machinery
    def load_module_py(module_id, path):
        return machinery.SourceFileLoader(module_id, path).load_module(module_id)

    def load_module_pyc(module_id, path):
        return machinery.SourcelessFileLoader(module_id, path).load_module(module_id)

else:
    import imp
    def load_module_py(module_id, path):
        with open(path, 'rb') as fp:
            mod = imp.load_source(module_id, path, fp)
            if py2k:
                source_encoding = parse_encoding(fp)
                if source_encoding:
                    mod._alembic_source_encoding = source_encoding
            return mod

    def load_module_pyc(module_id, path):
        with open(path, 'rb') as fp:
            mod = imp.load_compiled(module_id, path, fp)
            # no source encoding here
            return mod

try:
    exec_ = getattr(compat_builtins, 'exec')
except AttributeError:
    # Python 2
    def exec_(func_text, globals_, lcl):
        exec('exec func_text in globals_, lcl')

################################################
# cross-compatible metaclass implementation
# Copyright (c) 2010-2012 Benjamin Peterson
def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("%sBase" % meta.__name__, (base,), {})
################################################


# produce a wrapper that allows encoded text to stream
# into a given buffer, but doesn't close it.
# not sure of a more idiomatic approach to this.
class EncodedIO(io.TextIOWrapper):
    def close(self):
        pass

if py2k:
    # in Py2K, the io.* package is awkward because it does not
    # easily wrap the file type (e.g. sys.stdout) and I can't
    # figure out at all how to wrap StringIO.StringIO (used by nosetests)
    # and also might be user specified too.  So create a full
    # adapter.

    class ActLikePy3kIO(object):
        """Produce an object capable of wrapping either
        sys.stdout (e.g. file) *or* StringIO.StringIO().

        """
        def _false(self):
            return False

        def _true(self):
            return True

        readable = seekable = _false
        writable = _true
        closed = False

        def __init__(self, file_):
            self.file_ = file_

        def write(self, text):
            return self.file_.write(text)

        def flush(self):
            return self.file_.flush()

    class EncodedIO(EncodedIO):
        def __init__(self, file_, encoding):
            super(EncodedIO, self).__init__(
                    ActLikePy3kIO(file_), encoding=encoding)



########NEW FILE########
__FILENAME__ = config
from argparse import ArgumentParser
from .compat import SafeConfigParser
import inspect
import os
import sys

from . import command, util, package_dir, compat

class Config(object):
    """Represent an Alembic configuration.

    Within an ``env.py`` script, this is available
    via the :attr:`.EnvironmentContext.config` attribute,
    which in turn is available at ``alembic.context``::

        from alembic import context

        some_param = context.config.get_main_option("my option")

    When invoking Alembic programatically, a new
    :class:`.Config` can be created by passing
    the name of an .ini file to the constructor::

        from alembic.config import Config
        alembic_cfg = Config("/path/to/yourapp/alembic.ini")

    With a :class:`.Config` object, you can then
    run Alembic commands programmatically using the directives
    in :mod:`alembic.command`.

    The :class:`.Config` object can also be constructed without
    a filename.   Values can be set programmatically, and
    new sections will be created as needed::

        from alembic.config import Config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "myapp:migrations")
        alembic_cfg.set_main_option("url", "postgresql://foo/bar")
        alembic_cfg.set_section_option("mysection", "foo", "bar")

    :param file_: name of the .ini file to open.
    :param ini_section: name of the main Alembic section within the
     .ini file
    :param output_buffer: optional file-like input buffer which
     will be passed to the :class:`.MigrationContext` - used to redirect
     the output of "offline generation" when using Alembic programmatically.
    :param stdout: buffer where the "print" output of commands will be sent.
     Defaults to ``sys.stdout``.

     ..versionadded:: 0.4

    """
    def __init__(self, file_=None, ini_section='alembic', output_buffer=None,
                        stdout=sys.stdout, cmd_opts=None):
        """Construct a new :class:`.Config`

        """
        self.config_file_name = file_
        self.config_ini_section = ini_section
        self.output_buffer = output_buffer
        self.stdout = stdout
        self.cmd_opts = cmd_opts

    cmd_opts = None
    """The command-line options passed to the ``alembic`` script.

    Within an ``env.py`` script this can be accessed via the
    :attr:`.EnvironmentContext.config` attribute.

    .. versionadded:: 0.6.0

    .. seealso::

        :meth:`.EnvironmentContext.get_x_argument`

    """

    config_file_name = None
    """Filesystem path to the .ini file in use."""

    config_ini_section = None
    """Name of the config file section to read basic configuration
    from.  Defaults to ``alembic``, that is the ``[alembic]`` section
    of the .ini file.  This value is modified using the ``-n/--name``
    option to the Alembic runnier.

    """

    def print_stdout(self, text, *arg):
        """Render a message to standard out."""

        util.write_outstream(
                self.stdout,
                (compat.text_type(text) % arg),
                "\n"
        )

    @util.memoized_property
    def file_config(self):
        """Return the underlying :class:`ConfigParser` object.

        Direct access to the .ini file is available here,
        though the :meth:`.Config.get_section` and
        :meth:`.Config.get_main_option`
        methods provide a possibly simpler interface.

        """

        if self.config_file_name:
            here = os.path.abspath(os.path.dirname(self.config_file_name))
        else:
            here = ""
        file_config = SafeConfigParser({'here': here})
        if self.config_file_name:
            file_config.read([self.config_file_name])
        else:
            file_config.add_section(self.config_ini_section)
        return file_config

    def get_template_directory(self):
        """Return the directory where Alembic setup templates are found.

        This method is used by the alembic ``init`` and ``list_templates``
        commands.

        """
        return os.path.join(package_dir, 'templates')

    def get_section(self, name):
        """Return all the configuration options from a given .ini file section
        as a dictionary.

        """
        return dict(self.file_config.items(name))

    def set_main_option(self, name, value):
        """Set an option programmatically within the 'main' section.

        This overrides whatever was in the .ini file.

        """
        self.file_config.set(self.config_ini_section, name, value)

    def remove_main_option(self, name):
        self.file_config.remove_option(self.config_ini_section, name)

    def set_section_option(self, section, name, value):
        """Set an option programmatically within the given section.

        The section is created if it doesn't exist already.
        The value here will override whatever was in the .ini
        file.

        """
        if not self.file_config.has_section(section):
            self.file_config.add_section(section)
        self.file_config.set(section, name, value)

    def get_section_option(self, section, name, default=None):
        """Return an option from the given section of the .ini file.

        """
        if not self.file_config.has_section(section):
            raise util.CommandError("No config file %r found, or file has no "
                                "'[%s]' section" %
                                (self.config_file_name, section))
        if self.file_config.has_option(section, name):
            return self.file_config.get(section, name)
        else:
            return default

    def get_main_option(self, name, default=None):
        """Return an option from the 'main' section of the .ini file.

        This defaults to being a key from the ``[alembic]``
        section, unless the ``-n/--name`` flag were used to
        indicate a different section.

        """
        return self.get_section_option(self.config_ini_section, name, default)


class CommandLine(object):
    def __init__(self, prog=None):
        self._generate_args(prog)


    def _generate_args(self, prog):
        def add_options(parser, positional, kwargs):
            if 'template' in kwargs:
                parser.add_argument("-t", "--template",
                                default='generic',
                                type=str,
                                help="Setup template for use with 'init'")
            if 'message' in kwargs:
                parser.add_argument("-m", "--message",
                                type=str,
                                help="Message string to use with 'revision'")
            if 'sql' in kwargs:
                parser.add_argument("--sql",
                                action="store_true",
                                help="Don't emit SQL to database - dump to "
                                        "standard output/file instead")
            if 'tag' in kwargs:
                parser.add_argument("--tag",
                                type=str,
                                help="Arbitrary 'tag' name - can be used by "
                                "custom env.py scripts.")
            if 'autogenerate' in kwargs:
                parser.add_argument("--autogenerate",
                                action="store_true",
                                help="Populate revision script with candidate "
                                    "migration operations, based on comparison "
                                    "of database to model.")
            # "current" command
            if 'head_only' in kwargs:
                parser.add_argument("--head-only",
                                    action="store_true",
                                    help="Only show current version and "
                                    "whether or not this is the head revision.")

            if 'rev_range' in kwargs:
                parser.add_argument("-r", "--rev-range",
                                    action="store",
                                    help="Specify a revision range; "
                                    "format is [start]:[end]")


            positional_help = {
                'directory': "location of scripts directory",
                'revision': "revision identifier"
            }
            for arg in positional:
                subparser.add_argument(arg, help=positional_help.get(arg))

        parser = ArgumentParser(prog=prog)
        parser.add_argument("-c", "--config",
                            type=str,
                            default="alembic.ini",
                            help="Alternate config file")
        parser.add_argument("-n", "--name",
                            type=str,
                            default="alembic",
                            help="Name of section in .ini file to "
                                    "use for Alembic config")
        parser.add_argument("-x", action="append",
                            help="Additional arguments consumed by "
                            "custom env.py scripts, e.g. -x "
                            "setting1=somesetting -x setting2=somesetting")

        subparsers = parser.add_subparsers()

        for fn in [getattr(command, n) for n in dir(command)]:
            if inspect.isfunction(fn) and \
                fn.__name__[0] != '_' and \
                fn.__module__ == 'alembic.command':

                spec = inspect.getargspec(fn)
                if spec[3]:
                    positional = spec[0][1:-len(spec[3])]
                    kwarg = spec[0][-len(spec[3]):]
                else:
                    positional = spec[0][1:]
                    kwarg = []

                subparser = subparsers.add_parser(
                                    fn.__name__,
                                    help=fn.__doc__)
                add_options(subparser, positional, kwarg)
                subparser.set_defaults(cmd=(fn, positional, kwarg))
        self.parser = parser

    def run_cmd(self, config, options):
        fn, positional, kwarg = options.cmd

        try:
            fn(config,
                        *[getattr(options, k) for k in positional],
                        **dict((k, getattr(options, k)) for k in kwarg)
                    )
        except util.CommandError as e:
            util.err(str(e))

    def main(self, argv=None):
        options = self.parser.parse_args(argv)
        if not hasattr(options, "cmd"):
            # see http://bugs.python.org/issue9253, argparse
            # behavior changed incompatibly in py3.3
            self.parser.error("too few arguments")
        else:
            cfg = Config(file_=options.config,
                            ini_section=options.name, cmd_opts=options)
            self.run_cmd(cfg, options)

def main(argv=None, prog=None, **kwargs):
    """The console runner function for Alembic."""

    CommandLine(prog=prog).main(argv=argv)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = context
from .environment import EnvironmentContext
from . import util

# create proxy functions for
# each method on the EnvironmentContext class.
util.create_module_class_proxy(EnvironmentContext, globals(), locals())

########NEW FILE########
__FILENAME__ = base
import functools

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import DDLElement, Column
from sqlalchemy import Integer
from sqlalchemy import types as sqltypes

class AlterTable(DDLElement):
    """Represent an ALTER TABLE statement.

    Only the string name and optional schema name of the table
    is required, not a full Table object.

    """
    def __init__(self, table_name, schema=None):
        self.table_name = table_name
        self.schema = schema

class RenameTable(AlterTable):
    def __init__(self, old_table_name, new_table_name, schema=None):
        super(RenameTable, self).__init__(old_table_name, schema=schema)
        self.new_table_name = new_table_name

class AlterColumn(AlterTable):
    def __init__(self, name, column_name, schema=None,
                        existing_type=None,
                        existing_nullable=None,
                        existing_server_default=None):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.existing_type=sqltypes.to_instance(existing_type) \
                        if existing_type is not None else None
        self.existing_nullable=existing_nullable
        self.existing_server_default=existing_server_default

class ColumnNullable(AlterColumn):
    def __init__(self, name, column_name, nullable, **kw):
        super(ColumnNullable, self).__init__(name, column_name,
                        **kw)
        self.nullable = nullable

class ColumnType(AlterColumn):
    def __init__(self, name, column_name, type_, **kw):
        super(ColumnType, self).__init__(name, column_name,
                        **kw)
        self.type_ = sqltypes.to_instance(type_)

class ColumnName(AlterColumn):
    def __init__(self, name, column_name, newname, **kw):
        super(ColumnName, self).__init__(name, column_name, **kw)
        self.newname = newname

class ColumnDefault(AlterColumn):
    def __init__(self, name, column_name, default, **kw):
        super(ColumnDefault, self).__init__(name, column_name, **kw)
        self.default = default

class AddColumn(AlterTable):
    def __init__(self, name, column, schema=None):
        super(AddColumn, self).__init__(name, schema=schema)
        self.column = column

class DropColumn(AlterTable):
    def __init__(self, name, column, schema=None):
        super(DropColumn, self).__init__(name, schema=schema)
        self.column = column


@compiles(RenameTable)
def visit_rename_table(element, compiler, **kw):
    return "%s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_table_name(compiler, element.new_table_name, element.schema)
    )

@compiles(AddColumn)
def visit_add_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        add_column(compiler, element.column, **kw)
    )

@compiles(DropColumn)
def visit_drop_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        drop_column(compiler, element.column.name, **kw)
    )

@compiles(ColumnNullable)
def visit_column_nullable(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "DROP NOT NULL" if element.nullable else "SET NOT NULL"
    )

@compiles(ColumnType)
def visit_column_type(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "TYPE %s" % format_type(compiler, element.type_)
    )

@compiles(ColumnName)
def visit_column_name(element, compiler, **kw):
    return "%s RENAME %s TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname)
    )

@compiles(ColumnDefault)
def visit_column_default(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "SET DEFAULT %s" %
            format_server_default(compiler, element.default)
        if element.default is not None
        else "DROP DEFAULT"
    )

def quote_dotted(name, quote):
    """quote the elements of a dotted name"""

    result = '.'.join([quote(x) for x in name.split('.')])
    return result

def format_table_name(compiler, name, schema):
    quote = functools.partial(compiler.preparer.quote, force=None)
    if schema:
        return quote_dotted(schema, quote) + "." + quote(name)
    else:
        return quote(name)

def format_column_name(compiler, name):
    return compiler.preparer.quote(name, None)

def format_server_default(compiler, default):
    return compiler.get_column_default_string(
                Column("x", Integer, server_default=default)
            )

def format_type(compiler, type_):
    return compiler.dialect.type_compiler.process(type_)

def alter_table(compiler, name, schema):
    return "ALTER TABLE %s" % format_table_name(compiler, name, schema)

def drop_column(compiler, name):
    return 'DROP COLUMN %s' % format_column_name(compiler, name)

def alter_column(compiler, name):
    return 'ALTER COLUMN %s' % format_column_name(compiler, name)

def add_column(compiler, column, **kw):
    return "ADD COLUMN %s" % compiler.get_column_specification(column, **kw)



########NEW FILE########
__FILENAME__ = impl
from sqlalchemy.sql.expression import _BindParamClause
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import schema, text
from sqlalchemy import types as sqltypes

from ..compat import string_types, text_type, with_metaclass
from .. import util
from . import base

class ImplMeta(type):
    def __init__(cls, classname, bases, dict_):
        newtype = type.__init__(cls, classname, bases, dict_)
        if '__dialect__' in dict_:
            _impls[dict_['__dialect__']] = cls
        return newtype

_impls = {}

class DefaultImpl(with_metaclass(ImplMeta)):
    """Provide the entrypoint for major migration operations,
    including database-specific behavioral variances.

    While individual SQL/DDL constructs already provide
    for database-specific implementations, variances here
    allow for entirely different sequences of operations
    to take place for a particular migration, such as
    SQL Server's special 'IDENTITY INSERT' step for
    bulk inserts.

    """
    __dialect__ = 'default'

    transactional_ddl = False
    command_terminator = ";"

    def __init__(self, dialect, connection, as_sql,
                    transactional_ddl, output_buffer,
                    context_opts):
        self.dialect = dialect
        self.connection = connection
        self.as_sql = as_sql
        self.output_buffer = output_buffer
        self.memo = {}
        self.context_opts = context_opts
        if transactional_ddl is not None:
            self.transactional_ddl = transactional_ddl

    @classmethod
    def get_by_dialect(cls, dialect):
        return _impls[dialect.name]

    def static_output(self, text):
        self.output_buffer.write(text_type(text + "\n\n"))
        self.output_buffer.flush()

    @property
    def bind(self):
        return self.connection

    def _exec(self, construct, execution_options=None,
                            multiparams=(),
                            params=util.immutabledict()):
        if isinstance(construct, string_types):
            construct = text(construct)
        if self.as_sql:
            if multiparams or params:
                # TODO: coverage
                raise Exception("Execution arguments not allowed with as_sql")
            self.static_output(text_type(
                    construct.compile(dialect=self.dialect)
                    ).replace("\t", "    ").strip() + self.command_terminator)
        else:
            conn = self.connection
            if execution_options:
                conn = conn.execution_options(**execution_options)
            conn.execute(construct, *multiparams, **params)

    def execute(self, sql, execution_options=None):
        self._exec(sql, execution_options)

    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=None,
                        existing_nullable=None,
                        existing_autoincrement=None
                    ):
        if autoincrement is not None or existing_autoincrement is not None:
            util.warn("nautoincrement and existing_autoincrement only make sense for MySQL")
        if nullable is not None:
            self._exec(base.ColumnNullable(table_name, column_name,
                                nullable, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                                ))
        if server_default is not False:
            self._exec(base.ColumnDefault(
                                table_name, column_name, server_default,
                                schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))
        if type_ is not None:
            self._exec(base.ColumnType(
                                table_name, column_name, type_, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))
        # do the new name last ;)
        if name is not None:
            self._exec(base.ColumnName(
                                table_name, column_name, name, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))

    def add_column(self, table_name, column, schema=None):
        self._exec(base.AddColumn(table_name, column, schema=schema))

    def drop_column(self, table_name, column, schema=None, **kw):
        self._exec(base.DropColumn(table_name, column, schema=schema))

    def add_constraint(self, const):
        if const._create_rule is None or \
            const._create_rule(self):
            self._exec(schema.AddConstraint(const))

    def drop_constraint(self, const):
        self._exec(schema.DropConstraint(const))

    def rename_table(self, old_table_name, new_table_name, schema=None):
        self._exec(base.RenameTable(old_table_name,
                    new_table_name, schema=schema))

    def create_table(self, table):
        if util.sqla_07:
            table.dispatch.before_create(table, self.connection,
                                        checkfirst=False,
                                            _ddl_runner=self)
        self._exec(schema.CreateTable(table))
        if util.sqla_07:
            table.dispatch.after_create(table, self.connection,
                                        checkfirst=False,
                                            _ddl_runner=self)
        for index in table.indexes:
            self._exec(schema.CreateIndex(index))

    def drop_table(self, table):
        self._exec(schema.DropTable(table))

    def create_index(self, index):
        self._exec(schema.CreateIndex(index))

    def drop_index(self, index):
        self._exec(schema.DropIndex(index))

    def bulk_insert(self, table, rows, multiinsert=True):
        if not isinstance(rows, list):
            raise TypeError("List expected")
        elif rows and not isinstance(rows[0], dict):
            raise TypeError("List of dictionaries expected")
        if self.as_sql:
            for row in rows:
                self._exec(table.insert(inline=True).values(**dict(
                    (k,
                        _literal_bindparam(k, v, type_=table.c[k].type)
                        if not isinstance(v, _literal_bindparam) else v)
                    for k, v in row.items()
                )))
        else:
            # work around http://www.sqlalchemy.org/trac/ticket/2461
            if not hasattr(table, '_autoincrement_column'):
                table._autoincrement_column = None
            if rows:
                if multiinsert:
                    self._exec(table.insert(inline=True), multiparams=rows)
                else:
                    for row in rows:
                        self._exec(table.insert(inline=True).values(**row))

    def compare_type(self, inspector_column, metadata_column):

        conn_type = inspector_column.type
        metadata_type = metadata_column.type

        metadata_impl = metadata_type.dialect_impl(self.dialect)

        # work around SQLAlchemy bug "stale value for type affinity"
        # fixed in 0.7.4
        metadata_impl.__dict__.pop('_type_affinity', None)

        if conn_type._compare_type_affinity(
                            metadata_impl
                        ):
            comparator = _type_comparators.get(conn_type._type_affinity, None)

            return comparator and comparator(metadata_type, conn_type)
        else:
            return True

    def compare_server_default(self, inspector_column,
                            metadata_column,
                            rendered_metadata_default,
                            rendered_inspector_default):
        return rendered_inspector_default != rendered_metadata_default

    def correct_for_autogen_constraints(self, conn_uniques, conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes):
        pass

    def start_migrations(self):
        """A hook called when :meth:`.EnvironmentContext.run_migrations`
        is called.

        Implementations can set up per-migration-run state here.

        """

    def emit_begin(self):
        """Emit the string ``BEGIN``, or the backend-specific
        equivalent, on the current connection context.

        This is used in offline mode and typically
        via :meth:`.EnvironmentContext.begin_transaction`.

        """
        self.static_output("BEGIN" + self.command_terminator)

    def emit_commit(self):
        """Emit the string ``COMMIT``, or the backend-specific
        equivalent, on the current connection context.

        This is used in offline mode and typically
        via :meth:`.EnvironmentContext.begin_transaction`.

        """
        self.static_output("COMMIT" + self.command_terminator)

class _literal_bindparam(_BindParamClause):
    pass

@compiles(_literal_bindparam)
def _render_literal_bindparam(element, compiler, **kw):
    return compiler.render_literal_bindparam(element, **kw)


def _string_compare(t1, t2):
    return \
        t1.length is not None and \
        t1.length != t2.length

def _numeric_compare(t1, t2):
    return \
        (
            t1.precision is not None and \
            t1.precision != t2.precision
        ) or \
        (
            t1.scale is not None and \
            t1.scale != t2.scale
        )
_type_comparators = {
    sqltypes.String:_string_compare,
    sqltypes.Numeric:_numeric_compare
}





########NEW FILE########
__FILENAME__ = mssql
from sqlalchemy.ext.compiler import compiles

from .. import util
from .impl import DefaultImpl
from .base import alter_table, AddColumn, ColumnName, \
    format_table_name, format_column_name, ColumnNullable, alter_column,\
    format_server_default,ColumnDefault, format_type, ColumnType
from sqlalchemy.sql.expression import ClauseElement, Executable

class MSSQLImpl(DefaultImpl):
    __dialect__ = 'mssql'
    transactional_ddl = True
    batch_separator = "GO"

    def __init__(self, *arg, **kw):
        super(MSSQLImpl, self).__init__(*arg, **kw)
        self.batch_separator = self.context_opts.get(
                                "mssql_batch_separator",
                                self.batch_separator)

    def _exec(self, construct, *args, **kw):
        super(MSSQLImpl, self)._exec(construct, *args, **kw)
        if self.as_sql and self.batch_separator:
            self.static_output(self.batch_separator)

    def emit_begin(self):
        self.static_output("BEGIN TRANSACTION" + self.command_terminator)

    def emit_commit(self):
        super(MSSQLImpl, self).emit_commit()
        if self.as_sql and self.batch_separator:
            self.static_output(self.batch_separator)

    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=None,
                        existing_nullable=None,
                        existing_autoincrement=None
                    ):

        if nullable is not None and existing_type is None:
            if type_ is not None:
                existing_type = type_
                # the NULL/NOT NULL alter will handle
                # the type alteration
                type_ = None
            else:
                raise util.CommandError(
                        "MS-SQL ALTER COLUMN operations "
                        "with NULL or NOT NULL require the "
                        "existing_type or a new type_ be passed.")

        super(MSSQLImpl, self).alter_column(
                        table_name, column_name,
                        nullable=nullable,
                        type_=type_,
                        schema=schema,
                        autoincrement=autoincrement,
                        existing_type=existing_type,
                        existing_nullable=existing_nullable,
                        existing_autoincrement=existing_autoincrement
        )

        if server_default is not False:
            if existing_server_default is not False or \
                server_default is None:
                self._exec(
                    _ExecDropConstraint(
                            table_name, column_name,
                            'sys.default_constraints')
                )
            if server_default is not None:
                super(MSSQLImpl, self).alter_column(
                                table_name, column_name,
                                schema=schema,
                                server_default=server_default)

        if name is not None:
            super(MSSQLImpl, self).alter_column(
                                table_name, column_name,
                                schema=schema,
                                name=name)

    def bulk_insert(self, table, rows, **kw):
        if self.as_sql:
            self._exec(
                "SET IDENTITY_INSERT %s ON" %
                    self.dialect.identifier_preparer.format_table(table)
            )
            super(MSSQLImpl, self).bulk_insert(table, rows, **kw)
            self._exec(
                "SET IDENTITY_INSERT %s OFF" %
                    self.dialect.identifier_preparer.format_table(table)
            )
        else:
            super(MSSQLImpl, self).bulk_insert(table, rows, **kw)


    def drop_column(self, table_name, column, **kw):
        drop_default = kw.pop('mssql_drop_default', False)
        if drop_default:
            self._exec(
                _ExecDropConstraint(
                        table_name, column,
                        'sys.default_constraints')
            )
        drop_check = kw.pop('mssql_drop_check', False)
        if drop_check:
            self._exec(
                _ExecDropConstraint(
                        table_name, column,
                        'sys.check_constraints')
            )
        drop_fks = kw.pop('mssql_drop_foreign_key', False)
        if drop_fks:
            self._exec(
                _ExecDropFKConstraint(table_name, column)
            )
        super(MSSQLImpl, self).drop_column(table_name, column)

class _ExecDropConstraint(Executable, ClauseElement):
    def __init__(self, tname, colname, type_):
        self.tname = tname
        self.colname = colname
        self.type_ = type_

class _ExecDropFKConstraint(Executable, ClauseElement):
    def __init__(self, tname, colname):
        self.tname = tname
        self.colname = colname


@compiles(_ExecDropConstraint, 'mssql')
def _exec_drop_col_constraint(element, compiler, **kw):
    tname, colname, type_ = element.tname, element.colname, element.type_
    # from http://www.mssqltips.com/sqlservertip/1425/working-with-default-constraints-in-sql-server/
    # TODO: needs table formatting, etc.
    return """declare @const_name varchar(256)
select @const_name = [name] from %(type)s
where parent_object_id = object_id('%(tname)s')
and col_name(parent_object_id, parent_column_id) = '%(colname)s'
exec('alter table %(tname_quoted)s drop constraint ' + @const_name)""" % {
        'type': type_,
        'tname': tname,
        'colname': colname,
        'tname_quoted': format_table_name(compiler, tname, None),
    }

@compiles(_ExecDropFKConstraint, 'mssql')
def _exec_drop_col_fk_constraint(element, compiler, **kw):
    tname, colname = element.tname, element.colname

    return """declare @const_name varchar(256)
select @const_name = [name] from
    sys.foreign_keys fk join sys.foreign_key_columns fkc
    on fk.object_id=fkc.constraint_object_id
where fkc.parent_object_id = object_id('%(tname)s')
and col_name(fkc.parent_object_id, fkc.parent_column_id) = '%(colname)s'
exec('alter table %(tname_quoted)s drop constraint ' + @const_name)""" % {
        'tname': tname,
        'colname': colname,
        'tname_quoted': format_table_name(compiler, tname, None),
    }



@compiles(AddColumn, 'mssql')
def visit_add_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        mssql_add_column(compiler, element.column, **kw)
    )

def mssql_add_column(compiler, column, **kw):
    return "ADD %s" % compiler.get_column_specification(column, **kw)

@compiles(ColumnNullable, 'mssql')
def visit_column_nullable(element, compiler, **kw):
    return "%s %s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        format_type(compiler, element.existing_type),
        "NULL" if element.nullable else "NOT NULL"
    )

@compiles(ColumnDefault, 'mssql')
def visit_column_default(element, compiler, **kw):
    # TODO: there can also be a named constraint
    # with ADD CONSTRAINT here
    return "%s ADD DEFAULT %s FOR %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_server_default(compiler, element.default),
        format_column_name(compiler, element.column_name)
    )

@compiles(ColumnName, 'mssql')
def visit_rename_column(element, compiler, **kw):
    return "EXEC sp_rename '%s.%s', %s, 'COLUMN'" % (
        format_table_name(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname)
    )

@compiles(ColumnType, 'mssql')
def visit_column_type(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        format_type(compiler, element.type_)
    )


########NEW FILE########
__FILENAME__ = mysql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import types as sqltypes
from sqlalchemy import schema

from ..compat import string_types
from .. import util
from .impl import DefaultImpl
from .base import ColumnNullable, ColumnName, ColumnDefault, \
            ColumnType, AlterColumn, format_column_name, \
            format_server_default
from .base import alter_table

class MySQLImpl(DefaultImpl):
    __dialect__ = 'mysql'

    transactional_ddl = False

    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=None,
                        existing_nullable=None,
                        existing_autoincrement=None
                    ):
        if name is not None:
            self._exec(
                MySQLChangeColumn(
                    table_name, column_name,
                    schema=schema,
                    newname=name,
                    nullable=nullable if nullable is not None else
                                    existing_nullable
                                    if existing_nullable is not None
                                    else True,
                    type_=type_ if type_ is not None else existing_type,
                    default=server_default if server_default is not False
                                                else existing_server_default,
                    autoincrement=autoincrement if autoincrement is not None
                                                else existing_autoincrement
                )
            )
        elif nullable is not None or \
            type_ is not None or \
            autoincrement is not None:
            self._exec(
                MySQLModifyColumn(
                    table_name, column_name,
                    schema=schema,
                    newname=name if name is not None else column_name,
                    nullable=nullable if nullable is not None else
                                    existing_nullable
                                    if existing_nullable is not None
                                    else True,
                    type_=type_ if type_ is not None else existing_type,
                    default=server_default if server_default is not False
                                                else existing_server_default,
                    autoincrement=autoincrement if autoincrement is not None
                                                else existing_autoincrement
                )
            )
        elif server_default is not False:
            self._exec(
                MySQLAlterDefault(
                    table_name, column_name, server_default,
                    schema=schema,
                )
            )

    def correct_for_autogen_constraints(self, conn_unique_constraints,
                                        conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes):
        removed = set()
        for idx in list(conn_indexes):
            # MySQL puts implicit indexes on FK columns, even if
            # composite and even if MyISAM, so can't check this too easily
            if idx.name == idx.columns.keys()[0]:
                conn_indexes.remove(idx)
                removed.add(idx.name)

        # then remove indexes from the "metadata_indexes"
        # that we've removed from reflected, otherwise they come out
        # as adds (see #202)
        for idx in list(metadata_indexes):
            if idx.name in removed:
                metadata_indexes.remove(idx)

class MySQLAlterDefault(AlterColumn):
    def __init__(self, name, column_name, default, schema=None):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.default = default


class MySQLChangeColumn(AlterColumn):
    def __init__(self, name, column_name, schema=None,
                        newname=None,
                        type_=None,
                        nullable=None,
                        default=False,
                        autoincrement=None):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.nullable = nullable
        self.newname = newname
        self.default = default
        self.autoincrement = autoincrement
        if type_ is None:
            raise util.CommandError(
                "All MySQL CHANGE/MODIFY COLUMN operations "
                "require the existing type."
            )

        self.type_ = sqltypes.to_instance(type_)

class MySQLModifyColumn(MySQLChangeColumn):
    pass


@compiles(ColumnNullable, 'mysql')
@compiles(ColumnName, 'mysql')
@compiles(ColumnDefault, 'mysql')
@compiles(ColumnType, 'mysql')
def _mysql_doesnt_support_individual(element, compiler, **kw):
    raise NotImplementedError(
            "Individual alter column constructs not supported by MySQL"
        )


@compiles(MySQLAlterDefault, "mysql")
def _mysql_alter_default(element, compiler, **kw):
    return "%s ALTER COLUMN %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        "SET DEFAULT %s" % format_server_default(compiler, element.default)
             if element.default is not None
            else "DROP DEFAULT"
    )

@compiles(MySQLModifyColumn, "mysql")
def _mysql_modify_column(element, compiler, **kw):
    return "%s MODIFY %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        _mysql_colspec(
            compiler,
            nullable=element.nullable,
            server_default=element.default,
            type_=element.type_,
            autoincrement=element.autoincrement
        ),
    )


@compiles(MySQLChangeColumn, "mysql")
def _mysql_change_column(element, compiler, **kw):
    return "%s CHANGE %s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname),
        _mysql_colspec(
            compiler,
            nullable=element.nullable,
            server_default=element.default,
            type_=element.type_,
            autoincrement=element.autoincrement
        ),
    )

def _render_value(compiler, expr):
    if isinstance(expr, string_types):
        return "'%s'" % expr
    else:
        return compiler.sql_compiler.process(expr)

def _mysql_colspec(compiler, nullable, server_default, type_,
                                        autoincrement):
    spec = "%s %s" % (
        compiler.dialect.type_compiler.process(type_),
        "NULL" if nullable else "NOT NULL"
    )
    if autoincrement:
        spec += " AUTO_INCREMENT"
    if server_default is not False and server_default is not None:
        spec += " DEFAULT %s" % _render_value(compiler, server_default)

    return spec

@compiles(schema.DropConstraint, "mysql")
def _mysql_drop_constraint(element, compiler, **kw):
    """Redefine SQLAlchemy's drop constraint to
    raise errors for invalid constraint type."""

    constraint = element.element
    if isinstance(constraint, (schema.ForeignKeyConstraint,
                                schema.PrimaryKeyConstraint,
                                schema.UniqueConstraint)
                                ):
        return compiler.visit_drop_constraint(element, **kw)
    elif isinstance(constraint, schema.CheckConstraint):
        raise NotImplementedError(
                "MySQL does not support CHECK constraints.")
    else:
        raise NotImplementedError(
                "No generic 'DROP CONSTRAINT' in MySQL - "
                "please specify constraint type")


########NEW FILE########
__FILENAME__ = oracle
from sqlalchemy.ext.compiler import compiles

from .impl import DefaultImpl
from .base import alter_table, AddColumn, ColumnName, \
    format_column_name, ColumnNullable, \
    format_server_default,ColumnDefault, format_type, ColumnType

class OracleImpl(DefaultImpl):
    __dialect__ = 'oracle'
    transactional_ddl = True
    batch_separator = "/"
    command_terminator = ""

    def __init__(self, *arg, **kw):
        super(OracleImpl, self).__init__(*arg, **kw)
        self.batch_separator = self.context_opts.get(
                                "oracle_batch_separator",
                                self.batch_separator)

    def _exec(self, construct, *args, **kw):
        super(OracleImpl, self)._exec(construct, *args, **kw)
        if self.as_sql and self.batch_separator:
            self.static_output(self.batch_separator)

    def emit_begin(self):
        self._exec("SET TRANSACTION READ WRITE")

    def emit_commit(self):
        self._exec("COMMIT")

@compiles(AddColumn, 'oracle')
def visit_add_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        add_column(compiler, element.column, **kw),
    )

@compiles(ColumnNullable, 'oracle')
def visit_column_nullable(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "NULL" if element.nullable else "NOT NULL"
    )

@compiles(ColumnType, 'oracle')
def visit_column_type(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "%s" % format_type(compiler, element.type_)
    )

@compiles(ColumnName, 'oracle')
def visit_column_name(element, compiler, **kw):
    return "%s RENAME COLUMN %s TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname)
    )

@compiles(ColumnDefault, 'oracle')
def visit_column_default(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "DEFAULT %s" %
            format_server_default(compiler, element.default)
        if element.default is not None
        else "DEFAULT NULL"
    )

def alter_column(compiler, name):
    return 'MODIFY %s' % format_column_name(compiler, name)

def add_column(compiler, column, **kw):
    return "ADD %s" % compiler.get_column_specification(column, **kw)

########NEW FILE########
__FILENAME__ = postgresql
import re

from sqlalchemy import types as sqltypes

from .base import compiles, alter_table, format_table_name, RenameTable
from .impl import DefaultImpl

class PostgresqlImpl(DefaultImpl):
    __dialect__ = 'postgresql'
    transactional_ddl = True

    def compare_server_default(self, inspector_column,
                            metadata_column,
                            rendered_metadata_default,
                            rendered_inspector_default):

        # don't do defaults for SERIAL columns
        if metadata_column.primary_key and \
            metadata_column is metadata_column.table._autoincrement_column:
            return False

        conn_col_default = rendered_inspector_default

        if None in (conn_col_default, rendered_metadata_default):
            return conn_col_default != rendered_metadata_default

        if metadata_column.type._type_affinity is not sqltypes.String:
            rendered_metadata_default = re.sub(r"^'|'$", "", rendered_metadata_default)

        return not self.connection.scalar(
            "SELECT %s = %s" % (
                conn_col_default,
                rendered_metadata_default
            )
        )


@compiles(RenameTable, "postgresql")
def visit_rename_table(element, compiler, **kw):
    return "%s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_table_name(compiler, element.new_table_name, None)
    )

########NEW FILE########
__FILENAME__ = sqlite
from .. import util
from .impl import DefaultImpl

#from sqlalchemy.ext.compiler import compiles
#from .base import AddColumn, alter_table
#from sqlalchemy.schema import AddConstraint

class SQLiteImpl(DefaultImpl):
    __dialect__ = 'sqlite'

    transactional_ddl = False
    """SQLite supports transactional DDL, but pysqlite does not:
    see: http://bugs.python.org/issue10740
    """

    def add_constraint(self, const):
        # attempt to distinguish between an
        # auto-gen constraint and an explicit one
        if const._create_rule is None:
            raise NotImplementedError(
                    "No support for ALTER of constraints in SQLite dialect")
        elif const._create_rule(self):
            util.warn("Skipping unsupported ALTER for "
                        "creation of implicit constraint")


    def drop_constraint(self, const):
        if const._create_rule is None:
            raise NotImplementedError(
                    "No support for ALTER of constraints in SQLite dialect")

    def correct_for_autogen_constraints(self, conn_unique_constraints, conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes):

        def uq_sig(uq):
            return tuple(sorted(uq.columns.keys()))

        conn_unique_sigs = set(
                                uq_sig(uq)
                                for uq in conn_unique_constraints
                            )

        for idx in list(metadata_unique_constraints):
            # SQLite backend can't report on unnamed UNIQUE constraints,
            # so remove these, unless we see an exact signature match
            if idx.name is None and uq_sig(idx) not in conn_unique_sigs:
                metadata_unique_constraints.remove(idx)

        for idx in list(conn_unique_constraints):
            # just in case we fix the backend such that it does report
            # on them, blow them out of the reflected collection too otherwise
            # they will come up as removed.  if the backend supports this now,
            # add a version check here for the dialect.
            if idx.name is None:
                conn_uniques.remove(idx)

#@compiles(AddColumn, 'sqlite')
#def visit_add_column(element, compiler, **kw):
#    return "%s %s" % (
#        alter_table(compiler, element.table_name, element.schema),
#        add_column(compiler, element.column, **kw)
#    )


#def add_column(compiler, column, **kw):
#    text = "ADD COLUMN %s" % compiler.get_column_specification(column, **kw)
#    # need to modify SQLAlchemy so that the CHECK associated with a Boolean
#    # or Enum gets placed as part of the column constraints, not the Table
#    # see ticket 98
#    for const in column.constraints:
#        text += compiler.process(AddConstraint(const))
#    return text

########NEW FILE########
__FILENAME__ = environment
from .operations import Operations
from .migration import MigrationContext
from . import util

class EnvironmentContext(object):
    """Represent the state made available to an ``env.py`` script.

    :class:`.EnvironmentContext` is normally instantiated
    by the commands present in the :mod:`alembic.command`
    module.  From within an ``env.py`` script, the current
    :class:`.EnvironmentContext` is available via the
    ``alembic.context`` datamember.

    :class:`.EnvironmentContext` is also a Python context
    manager, that is, is intended to be used using the
    ``with:`` statement.  A typical use of :class:`.EnvironmentContext`::

        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config()
        config.set_main_option("script_location", "myapp:migrations")
        script = ScriptDirectory.from_config(config)

        def my_function(rev, context):
            '''do something with revision "rev", which
            will be the current database revision,
            and "context", which is the MigrationContext
            that the env.py will create'''

        with EnvironmentContext(
            config,
            script,
            fn = my_function,
            as_sql = False,
            starting_rev = 'base',
            destination_rev = 'head',
            tag = "sometag"
        ):
            script.run_env()

    The above script will invoke the ``env.py`` script
    within the migration environment.  If and when ``env.py``
    calls :meth:`.MigrationContext.run_migrations`, the
    ``my_function()`` function above will be called
    by the :class:`.MigrationContext`, given the context
    itself as well as the current revision in the database.

    .. note::

        For most API usages other than full blown
        invocation of migration scripts, the :class:`.MigrationContext`
        and :class:`.ScriptDirectory` objects can be created and
        used directly.  The :class:`.EnvironmentContext` object
        is *only* needed when you need to actually invoke the
        ``env.py`` module present in the migration environment.

    """

    _migration_context = None

    config = None
    """An instance of :class:`.Config` representing the
    configuration file contents as well as other variables
    set programmatically within it."""

    script = None
    """An instance of :class:`.ScriptDirectory` which provides
    programmatic access to version files within the ``versions/``
    directory.

    """

    def __init__(self, config, script, **kw):
        """Construct a new :class:`.EnvironmentContext`.

        :param config: a :class:`.Config` instance.
        :param script: a :class:`.ScriptDirectory` instance.
        :param \**kw: keyword options that will be ultimately
         passed along to the :class:`.MigrationContext` when
         :meth:`.EnvironmentContext.configure` is called.

        """
        self.config = config
        self.script = script
        self.context_opts = kw

    def __enter__(self):
        """Establish a context which provides a
        :class:`.EnvironmentContext` object to
        env.py scripts.

        The :class:`.EnvironmentContext` will
        be made available as ``from alembic import context``.

        """
        from .context import _install_proxy
        _install_proxy(self)
        return self

    def __exit__(self, *arg, **kw):
        from . import context, op
        context._remove_proxy()
        op._remove_proxy()

    def is_offline_mode(self):
        """Return True if the current migrations environment
        is running in "offline mode".

        This is ``True`` or ``False`` depending
        on the the ``--sql`` flag passed.

        This function does not require that the :class:`.MigrationContext`
        has been configured.

        """
        return self.context_opts.get('as_sql', False)

    def is_transactional_ddl(self):
        """Return True if the context is configured to expect a
        transactional DDL capable backend.

        This defaults to the type of database in use, and
        can be overridden by the ``transactional_ddl`` argument
        to :meth:`.configure`

        This function requires that a :class:`.MigrationContext`
        has first been made available via :meth:`.configure`.

        """
        return self.get_context().impl.transactional_ddl

    def requires_connection(self):
        return not self.is_offline_mode()

    def get_head_revision(self):
        """Return the hex identifier of the 'head' revision.

        This function does not require that the :class:`.MigrationContext`
        has been configured.

        """
        return self.script._as_rev_number("head")

    def get_starting_revision_argument(self):
        """Return the 'starting revision' argument,
        if the revision was passed using ``start:end``.

        This is only meaningful in "offline" mode.
        Returns ``None`` if no value is available
        or was configured.

        This function does not require that the :class:`.MigrationContext`
        has been configured.

        """
        if self._migration_context is not None:
            return self.script._as_rev_number(
                        self.get_context()._start_from_rev)
        elif 'starting_rev' in self.context_opts:
            return self.script._as_rev_number(
                        self.context_opts['starting_rev'])
        else:
            raise util.CommandError(
                        "No starting revision argument is available.")

    def get_revision_argument(self):
        """Get the 'destination' revision argument.

        This is typically the argument passed to the
        ``upgrade`` or ``downgrade`` command.

        If it was specified as ``head``, the actual
        version number is returned; if specified
        as ``base``, ``None`` is returned.

        This function does not require that the :class:`.MigrationContext`
        has been configured.

        """
        return self.script._as_rev_number(
                            self.context_opts['destination_rev'])

    def get_tag_argument(self):
        """Return the value passed for the ``--tag`` argument, if any.

        The ``--tag`` argument is not used directly by Alembic,
        but is available for custom ``env.py`` configurations that
        wish to use it; particularly for offline generation scripts
        that wish to generate tagged filenames.

        This function does not require that the :class:`.MigrationContext`
        has been configured.

        .. seealso::

            :meth:`.EnvironmentContext.get_x_argument` - a newer and more
            open ended system of extending ``env.py`` scripts via the command
            line.

        """
        return self.context_opts.get('tag', None)

    def get_x_argument(self, as_dictionary=False):
        """Return the value(s) passed for the ``-x`` argument, if any.

        The ``-x`` argument is an open ended flag that allows any user-defined
        value or values to be passed on the command line, then available
        here for consumption by a custom ``env.py`` script.

        The return value is a list, returned directly from the ``argparse``
        structure.  If ``as_dictionary=True`` is passed, the ``x`` arguments
        are parsed using ``key=value`` format into a dictionary that is
        then returned.

        For example, to support passing a database URL on the command line,
        the standard ``env.py`` script can be modified like this::

            cmd_line_url = context.get_x_argument(as_dictionary=True).get('dbname')
            if cmd_line_url:
                engine = create_engine(cmd_line_url)
            else:
                engine = engine_from_config(
                        config.get_section(config.config_ini_section),
                        prefix='sqlalchemy.',
                        poolclass=pool.NullPool)

        This then takes effect by running the ``alembic`` script as::

            alembic -x dbname=postgresql://user:pass@host/dbname upgrade head

        This function does not require that the :class:`.MigrationContext`
        has been configured.

        .. versionadded:: 0.6.0

        .. seealso::

            :meth:`.EnvironmentContext.get_tag_argument`

            :attr:`.Config.cmd_opts`

        """
        if self.config.cmd_opts is not None:
            value = self.config.cmd_opts.x or []
        else:
            value = []
        if as_dictionary:
            value = dict(
                        arg.split('=', 1) for arg in value
                    )
        return value

    def configure(self,
            connection=None,
            url=None,
            dialect_name=None,
            transactional_ddl=None,
            transaction_per_migration=False,
            output_buffer=None,
            starting_rev=None,
            tag=None,
            template_args=None,
            target_metadata=None,
            include_symbol=None,
            include_object=None,
            include_schemas=False,
            compare_type=False,
            compare_server_default=False,
            render_item=None,
            upgrade_token="upgrades",
            downgrade_token="downgrades",
            alembic_module_prefix="op.",
            sqlalchemy_module_prefix="sa.",
            user_module_prefix=None,
            **kw
        ):
        """Configure a :class:`.MigrationContext` within this
        :class:`.EnvironmentContext` which will provide database
        connectivity and other configuration to a series of
        migration scripts.

        Many methods on :class:`.EnvironmentContext` require that
        this method has been called in order to function, as they
        ultimately need to have database access or at least access
        to the dialect in use.  Those which do are documented as such.

        The important thing needed by :meth:`.configure` is a
        means to determine what kind of database dialect is in use.
        An actual connection to that database is needed only if
        the :class:`.MigrationContext` is to be used in
        "online" mode.

        If the :meth:`.is_offline_mode` function returns ``True``,
        then no connection is needed here.  Otherwise, the
        ``connection`` parameter should be present as an
        instance of :class:`sqlalchemy.engine.Connection`.

        This function is typically called from the ``env.py``
        script within a migration environment.  It can be called
        multiple times for an invocation.  The most recent
        :class:`~sqlalchemy.engine.Connection`
        for which it was called is the one that will be operated upon
        by the next call to :meth:`.run_migrations`.

        General parameters:

        :param connection: a :class:`~sqlalchemy.engine.Connection`
         to use
         for SQL execution in "online" mode.  When present, is also
         used to determine the type of dialect in use.
        :param url: a string database url, or a
         :class:`sqlalchemy.engine.url.URL` object.
         The type of dialect to be used will be derived from this if
         ``connection`` is not passed.
        :param dialect_name: string name of a dialect, such as
         "postgresql", "mssql", etc.
         The type of dialect to be used will be derived from this if
         ``connection`` and ``url`` are not passed.
        :param transactional_ddl: Force the usage of "transactional"
         DDL on or off;
         this otherwise defaults to whether or not the dialect in
         use supports it.
        :param transaction_per_migration: if True, nest each migration script
         in a transaction rather than the full series of migrations to
         run.

         .. versionadded:: 0.6.5

        :param output_buffer: a file-like object that will be used
         for textual output
         when the ``--sql`` option is used to generate SQL scripts.
         Defaults to
         ``sys.stdout`` if not passed here and also not present on
         the :class:`.Config`
         object.  The value here overrides that of the :class:`.Config`
         object.
        :param output_encoding: when using ``--sql`` to generate SQL
         scripts, apply this encoding to the string output.

         .. versionadded:: 0.5.0

        :param starting_rev: Override the "starting revision" argument
         when using ``--sql`` mode.
        :param tag: a string tag for usage by custom ``env.py`` scripts.
         Set via the ``--tag`` option, can be overridden here.
        :param template_args: dictionary of template arguments which
         will be added to the template argument environment when
         running the "revision" command.   Note that the script environment
         is only run within the "revision" command if the --autogenerate
         option is used, or if the option "revision_environment=true"
         is present in the alembic.ini file.

         .. versionadded:: 0.3.3

        :param version_table: The name of the Alembic version table.
         The default is ``'alembic_version'``.
        :param version_table_schema: Optional schema to place version
         table within.

         .. versionadded:: 0.5.0

        Parameters specific to the autogenerate feature, when
        ``alembic revision`` is run with the ``--autogenerate`` feature:

        :param target_metadata: a :class:`sqlalchemy.schema.MetaData`
         object that
         will be consulted during autogeneration.  The tables present
         will be compared against
         what is locally available on the target
         :class:`~sqlalchemy.engine.Connection`
         to produce candidate upgrade/downgrade operations.

        :param compare_type: Indicates type comparison behavior during
         an autogenerate
         operation.  Defaults to ``False`` which disables type
         comparison.  Set to
         ``True`` to turn on default type comparison, which has varied
         accuracy depending on backend.

         To customize type comparison behavior, a callable may be
         specified which
         can filter type comparisons during an autogenerate operation.
         The format of this callable is::

            def my_compare_type(context, inspected_column,
                        metadata_column, inspected_type, metadata_type):
                # return True if the types are different,
                # False if not, or None to allow the default implementation
                # to compare these types
                return None

            context.configure(
                # ...
                compare_type = my_compare_type
            )


         ``inspected_column`` is a :class:`sqlalchemy.schema.Column` as returned by
         :meth:`sqlalchemy.engine.reflection.Inspector.reflecttable`, whereas
         ``metadata_column`` is a :class:`sqlalchemy.schema.Column` from
         the local model environment.

         A return value of ``None`` indicates to allow default type
         comparison to proceed.

         .. seealso::

            :paramref:`.EnvironmentContext.configure.compare_server_default`

        :param compare_server_default: Indicates server default comparison
         behavior during
         an autogenerate operation.  Defaults to ``False`` which disables
         server default
         comparison.  Set to  ``True`` to turn on server default comparison,
         which has
         varied accuracy depending on backend.

         To customize server default comparison behavior, a callable may
         be specified
         which can filter server default comparisons during an
         autogenerate operation.
         defaults during an autogenerate operation.   The format of this
         callable is::

            def my_compare_server_default(context, inspected_column,
                        metadata_column, inspected_default, metadata_default,
                        rendered_metadata_default):
                # return True if the defaults are different,
                # False if not, or None to allow the default implementation
                # to compare these defaults
                return None

            context.configure(
                # ...
                compare_server_default = my_compare_server_default
            )

         ``inspected_column`` is a dictionary structure as returned by
         :meth:`sqlalchemy.engine.reflection.Inspector.get_columns`, whereas
         ``metadata_column`` is a :class:`sqlalchemy.schema.Column` from
         the local model environment.

         A return value of ``None`` indicates to allow default server default
         comparison
         to proceed.  Note that some backends such as Postgresql actually
         execute
         the two defaults on the database side to compare for equivalence.

         .. seealso::

            :paramref:`.EnvironmentContext.configure.compare_type`

        :param include_object: A callable function which is given
         the chance to return ``True`` or ``False`` for any object,
         indicating if the given object should be considered in the
         autogenerate sweep.

         The function accepts the following positional arguments:

         * ``object``: a :class:`~sqlalchemy.schema.SchemaItem` object such as a
           :class:`~sqlalchemy.schema.Table` or :class:`~sqlalchemy.schema.Column`
           object
         * ``name``: the name of the object. This is typically available
           via ``object.name``.
         * ``type``: a string describing the type of object; currently
           ``"table"`` or ``"column"``
         * ``reflected``: ``True`` if the given object was produced based on
           table reflection, ``False`` if it's from a local :class:`.MetaData`
           object.
         * ``compare_to``: the object being compared against, if available,
           else ``None``.

         E.g.::

            def include_object(object, name, type_, reflected, compare_to):
                if (type_ == "column" and
                    not reflected and
                    object.info.get("skip_autogenerate", False)):
                    return False
                else:
                    return True

            context.configure(
                # ...
                include_object = include_object
            )

         :paramref:`.EnvironmentContext.configure.include_object` can also
         be used to filter on specific schemas to include or omit, when
         the :paramref:`.EnvironmentContext.configure.include_schemas`
         flag is set to ``True``.   The :attr:`.Table.schema` attribute
         on each :class:`.Table` object reflected will indicate the name of the
         schema from which the :class:`.Table` originates.

         .. versionadded:: 0.6.0

         .. seealso::

            :paramref:`.EnvironmentContext.configure.include_schemas`

        :param include_symbol: A callable function which, given a table name
         and schema name (may be ``None``), returns ``True`` or ``False``, indicating
         if the given table should be considered in the autogenerate sweep.

         .. deprecated:: 0.6.0 :paramref:`.EnvironmentContext.configure.include_symbol`
            is superceded by the more generic
            :paramref:`.EnvironmentContext.configure.include_object`
            parameter.

         E.g.::

            def include_symbol(tablename, schema):
                return tablename not in ("skip_table_one", "skip_table_two")

            context.configure(
                # ...
                include_symbol = include_symbol
            )

         .. seealso::

            :paramref:`.EnvironmentContext.configure.include_schemas`

            :paramref:`.EnvironmentContext.configure.include_object`

        :param include_schemas: If True, autogenerate will scan across
         all schemas located by the SQLAlchemy
         :meth:`~sqlalchemy.engine.reflection.Inspector.get_schema_names`
         method, and include all differences in tables found across all
         those schemas.  When using this option, you may want to also
         use the :paramref:`.EnvironmentContext.configure.include_object`
         option to specify a callable which
         can filter the tables/schemas that get included.

         .. versionadded :: 0.4.0

         .. seealso::

            :paramref:`.EnvironmentContext.configure.include_object`

        :param render_item: Callable that can be used to override how
         any schema item, i.e. column, constraint, type,
         etc., is rendered for autogenerate.  The callable receives a
         string describing the type of object, the object, and
         the autogen context.  If it returns False, the
         default rendering method will be used.  If it returns None,
         the item will not be rendered in the context of a Table
         construct, that is, can be used to skip columns or constraints
         within op.create_table()::

            def my_render_column(type_, col, autogen_context):
                if type_ == "column" and isinstance(col, MySpecialCol):
                    return repr(col)
                else:
                    return False

            context.configure(
                # ...
                render_item = my_render_column
            )

         Available values for the type string include: ``"column"``,
         ``"primary_key"``, ``"foreign_key"``, ``"unique"``, ``"check"``,
         ``"type"``, ``"server_default"``.

         .. versionadded:: 0.5.0

         .. seealso::

            :ref:`autogen_render_types`

        :param upgrade_token: When autogenerate completes, the text of the
         candidate upgrade operations will be present in this template
         variable when ``script.py.mako`` is rendered.  Defaults to
         ``upgrades``.
        :param downgrade_token: When autogenerate completes, the text of the
         candidate downgrade operations will be present in this
         template variable when ``script.py.mako`` is rendered.  Defaults to
         ``downgrades``.

        :param alembic_module_prefix: When autogenerate refers to Alembic
         :mod:`alembic.operations` constructs, this prefix will be used
         (i.e. ``op.create_table``)  Defaults to "``op.``".
         Can be ``None`` to indicate no prefix.

        :param sqlalchemy_module_prefix: When autogenerate refers to
         SQLAlchemy
         :class:`~sqlalchemy.schema.Column` or type classes, this prefix
         will be used
         (i.e. ``sa.Column("somename", sa.Integer)``)  Defaults to "``sa.``".
         Can be ``None`` to indicate no prefix.
         Note that when dialect-specific types are rendered, autogenerate
         will render them using the dialect module name, i.e. ``mssql.BIT()``,
         ``postgresql.UUID()``.

        :param user_module_prefix: When autogenerate refers to a SQLAlchemy
         type (e.g. :class:`.TypeEngine`) where the module name is not
         under the ``sqlalchemy`` namespace, this prefix will be used
         within autogenerate, if non-``None``; if left at its default of
         ``None``, the
         :paramref:`.EnvironmentContext.configure.sqlalchemy_module_prefix`
         is used instead.

         .. versionadded:: 0.6.3 added
            :paramref:`.EnvironmentContext.configure.user_module_prefix`

         .. seealso::

            :ref:`autogen_module_prefix`

        Parameters specific to individual backends:

        :param mssql_batch_separator: The "batch separator" which will
         be placed between each statement when generating offline SQL Server
         migrations.  Defaults to ``GO``.  Note this is in addition to the
         customary semicolon ``;`` at the end of each statement; SQL Server
         considers the "batch separator" to denote the end of an
         individual statement execution, and cannot group certain
         dependent operations in one step.
        :param oracle_batch_separator: The "batch separator" which will
         be placed between each statement when generating offline
         Oracle migrations.  Defaults to ``/``.  Oracle doesn't add a
         semicolon between statements like most other backends.

        """
        opts = self.context_opts
        if transactional_ddl is not None:
            opts["transactional_ddl"] = transactional_ddl
        if output_buffer is not None:
            opts["output_buffer"] = output_buffer
        elif self.config.output_buffer is not None:
            opts["output_buffer"] = self.config.output_buffer
        if starting_rev:
            opts['starting_rev'] = starting_rev
        if tag:
            opts['tag'] = tag
        if template_args and 'template_args' in opts:
            opts['template_args'].update(template_args)
        opts["transaction_per_migration"] = transaction_per_migration
        opts['target_metadata'] = target_metadata
        opts['include_symbol'] = include_symbol
        opts['include_object'] = include_object
        opts['include_schemas'] = include_schemas
        opts['upgrade_token'] = upgrade_token
        opts['downgrade_token'] = downgrade_token
        opts['sqlalchemy_module_prefix'] = sqlalchemy_module_prefix
        opts['alembic_module_prefix'] = alembic_module_prefix
        opts['user_module_prefix'] = user_module_prefix
        if render_item is not None:
            opts['render_item'] = render_item
        if compare_type is not None:
            opts['compare_type'] = compare_type
        if compare_server_default is not None:
            opts['compare_server_default'] = compare_server_default
        opts['script'] = self.script

        opts.update(kw)

        self._migration_context = MigrationContext.configure(
            connection=connection,
            url=url,
            dialect_name=dialect_name,
            environment_context=self,
            opts=opts
        )

    def run_migrations(self, **kw):
        """Run migrations as determined by the current command line
        configuration
        as well as versioning information present (or not) in the current
        database connection (if one is present).

        The function accepts optional ``**kw`` arguments.   If these are
        passed, they are sent directly to the ``upgrade()`` and
        ``downgrade()``
        functions within each target revision file.   By modifying the
        ``script.py.mako`` file so that the ``upgrade()`` and ``downgrade()``
        functions accept arguments, parameters can be passed here so that
        contextual information, usually information to identify a particular
        database in use, can be passed from a custom ``env.py`` script
        to the migration functions.

        This function requires that a :class:`.MigrationContext` has
        first been made available via :meth:`.configure`.

        """
        with Operations.context(self._migration_context):
            self.get_context().run_migrations(**kw)

    def execute(self, sql, execution_options=None):
        """Execute the given SQL using the current change context.

        The behavior of :meth:`.execute` is the same
        as that of :meth:`.Operations.execute`.  Please see that
        function's documentation for full detail including
        caveats and limitations.

        This function requires that a :class:`.MigrationContext` has
        first been made available via :meth:`.configure`.

        """
        self.get_context().execute(sql,
                execution_options=execution_options)

    def static_output(self, text):
        """Emit text directly to the "offline" SQL stream.

        Typically this is for emitting comments that
        start with --.  The statement is not treated
        as a SQL execution, no ; or batch separator
        is added, etc.

        """
        self.get_context().impl.static_output(text)


    def begin_transaction(self):
        """Return a context manager that will
        enclose an operation within a "transaction",
        as defined by the environment's offline
        and transactional DDL settings.

        e.g.::

            with context.begin_transaction():
                context.run_migrations()

        :meth:`.begin_transaction` is intended to
        "do the right thing" regardless of
        calling context:

        * If :meth:`.is_transactional_ddl` is ``False``,
          returns a "do nothing" context manager
          which otherwise produces no transactional
          state or directives.
        * If :meth:`.is_offline_mode` is ``True``,
          returns a context manager that will
          invoke the :meth:`.DefaultImpl.emit_begin`
          and :meth:`.DefaultImpl.emit_commit`
          methods, which will produce the string
          directives ``BEGIN`` and ``COMMIT`` on
          the output stream, as rendered by the
          target backend (e.g. SQL Server would
          emit ``BEGIN TRANSACTION``).
        * Otherwise, calls :meth:`sqlalchemy.engine.Connection.begin`
          on the current online connection, which
          returns a :class:`sqlalchemy.engine.Transaction`
          object.  This object demarcates a real
          transaction and is itself a context manager,
          which will roll back if an exception
          is raised.

        Note that a custom ``env.py`` script which
        has more specific transactional needs can of course
        manipulate the :class:`~sqlalchemy.engine.Connection`
        directly to produce transactional state in "online"
        mode.

        """

        return self.get_context().begin_transaction()


    def get_context(self):
        """Return the current :class:`.MigrationContext` object.

        If :meth:`.EnvironmentContext.configure` has not been
        called yet, raises an exception.

        """

        if self._migration_context is None:
            raise Exception("No context has been configured yet.")
        return self._migration_context

    def get_bind(self):
        """Return the current 'bind'.

        In "online" mode, this is the
        :class:`sqlalchemy.engine.Connection` currently being used
        to emit SQL to the database.

        This function requires that a :class:`.MigrationContext`
        has first been made available via :meth:`.configure`.

        """
        return self.get_context().bind

    def get_impl(self):
        return self.get_context().impl


########NEW FILE########
__FILENAME__ = migration
import io
import logging
import sys
from contextlib import contextmanager


from sqlalchemy import MetaData, Table, Column, String, literal_column
from sqlalchemy import create_engine
from sqlalchemy.engine import url as sqla_url

from .compat import callable, EncodedIO
from . import ddl, util

log = logging.getLogger(__name__)

class MigrationContext(object):
    """Represent the database state made available to a migration
    script.

    :class:`.MigrationContext` is the front end to an actual
    database connection, or alternatively a string output
    stream given a particular database dialect,
    from an Alembic perspective.

    When inside the ``env.py`` script, the :class:`.MigrationContext`
    is available via the
    :meth:`.EnvironmentContext.get_context` method,
    which is available at ``alembic.context``::

        # from within env.py script
        from alembic import context
        migration_context = context.get_context()

    For usage outside of an ``env.py`` script, such as for
    utility routines that want to check the current version
    in the database, the :meth:`.MigrationContext.configure`
    method to create new :class:`.MigrationContext` objects.
    For example, to get at the current revision in the
    database using :meth:`.MigrationContext.get_current_revision`::

        # in any application, outside of an env.py script
        from alembic.migration import MigrationContext
        from sqlalchemy import create_engine

        engine = create_engine("postgresql://mydatabase")
        conn = engine.connect()

        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

    The above context can also be used to produce
    Alembic migration operations with an :class:`.Operations`
    instance::

        # in any application, outside of the normal Alembic environment
        from alembic.operations import Operations
        op = Operations(context)
        op.alter_column("mytable", "somecolumn", nullable=True)

    """
    def __init__(self, dialect, connection, opts, environment_context=None):
        self.environment_context = environment_context
        self.opts = opts
        self.dialect = dialect
        self.script = opts.get('script')

        as_sql = opts.get('as_sql', False)
        transactional_ddl = opts.get("transactional_ddl")

        self._transaction_per_migration = opts.get(
                                            "transaction_per_migration", False)

        if as_sql:
            self.connection = self._stdout_connection(connection)
            assert self.connection is not None
        else:
            self.connection = connection
        self._migrations_fn = opts.get('fn')
        self.as_sql = as_sql

        if "output_encoding" in opts:
            self.output_buffer = EncodedIO(
                opts.get("output_buffer") or sys.stdout,
                opts['output_encoding']
            )
        else:
            self.output_buffer = opts.get("output_buffer", sys.stdout)

        self._user_compare_type = opts.get('compare_type', False)
        self._user_compare_server_default = opts.get(
                                            'compare_server_default',
                                            False)
        version_table = opts.get('version_table', 'alembic_version')
        version_table_schema = opts.get('version_table_schema', None)
        self._version = Table(
            version_table, MetaData(),
            Column('version_num', String(32), nullable=False),
            schema=version_table_schema)

        self._start_from_rev = opts.get("starting_rev")
        self.impl = ddl.DefaultImpl.get_by_dialect(dialect)(
                            dialect, self.connection, self.as_sql,
                            transactional_ddl,
                            self.output_buffer,
                            opts
                            )
        log.info("Context impl %s.", self.impl.__class__.__name__)
        if self.as_sql:
            log.info("Generating static SQL")
        log.info("Will assume %s DDL.",
                        "transactional" if self.impl.transactional_ddl
                        else "non-transactional")

    @classmethod
    def configure(cls,
                connection=None,
                url=None,
                dialect_name=None,
                environment_context=None,
                opts={},
    ):
        """Create a new :class:`.MigrationContext`.

        This is a factory method usually called
        by :meth:`.EnvironmentContext.configure`.

        :param connection: a :class:`~sqlalchemy.engine.Connection`
         to use for SQL execution in "online" mode.  When present,
         is also used to determine the type of dialect in use.
        :param url: a string database url, or a
         :class:`sqlalchemy.engine.url.URL` object.
         The type of dialect to be used will be derived from this if
         ``connection`` is not passed.
        :param dialect_name: string name of a dialect, such as
         "postgresql", "mssql", etc.  The type of dialect to be used will be
         derived from this if ``connection`` and ``url`` are not passed.
        :param opts: dictionary of options.  Most other options
         accepted by :meth:`.EnvironmentContext.configure` are passed via
         this dictionary.

        """
        if connection:
            dialect = connection.dialect
        elif url:
            url = sqla_url.make_url(url)
            dialect = url.get_dialect()()
        elif dialect_name:
            url = sqla_url.make_url("%s://" % dialect_name)
            dialect = url.get_dialect()()
        else:
            raise Exception("Connection, url, or dialect_name is required.")

        return MigrationContext(dialect, connection, opts, environment_context)


    def begin_transaction(self, _per_migration=False):
        transaction_now = _per_migration == self._transaction_per_migration

        if not transaction_now:
            @contextmanager
            def do_nothing():
                yield
            return do_nothing()

        elif not self.impl.transactional_ddl:
            @contextmanager
            def do_nothing():
                yield
            return do_nothing()
        elif self.as_sql:
            @contextmanager
            def begin_commit():
                self.impl.emit_begin()
                yield
                self.impl.emit_commit()
            return begin_commit()
        else:
            return self.bind.begin()

    def get_current_revision(self):
        """Return the current revision, usually that which is present
        in the ``alembic_version`` table in the database.

        If this :class:`.MigrationContext` was configured in "offline"
        mode, that is with ``as_sql=True``, the ``starting_rev``
        parameter is returned instead, if any.

        """
        if self.as_sql:
            return self._start_from_rev
        else:
            if self._start_from_rev:
                raise util.CommandError(
                    "Can't specify current_rev to context "
                    "when using a database connection")
            self._version.create(self.connection, checkfirst=True)
        return self.connection.scalar(self._version.select())

    _current_rev = get_current_revision
    """The 0.2 method name, for backwards compat."""

    def _update_current_rev(self, old, new):
        if old == new:
            return
        if new is None:
            self.impl._exec(self._version.delete())
        elif old is None:
            self.impl._exec(self._version.insert().
                        values(version_num=literal_column("'%s'" % new))
                    )
        else:
            self.impl._exec(self._version.update().
                        values(version_num=literal_column("'%s'" % new))
                    )

    def run_migrations(self, **kw):
        """Run the migration scripts established for this :class:`.MigrationContext`,
        if any.

        The commands in :mod:`alembic.command` will set up a function
        that is ultimately passed to the :class:`.MigrationContext`
        as the ``fn`` argument.  This function represents the "work"
        that will be done when :meth:`.MigrationContext.run_migrations`
        is called, typically from within the ``env.py`` script of the
        migration environment.  The "work function" then provides an iterable
        of version callables and other version information which
        in the case of the ``upgrade`` or ``downgrade`` commands are the
        list of version scripts to invoke.  Other commands yield nothing,
        in the case that a command wants to run some other operation
        against the database such as the ``current`` or ``stamp`` commands.

        :param \**kw: keyword arguments here will be passed to each
         migration callable, that is the ``upgrade()`` or ``downgrade()``
         method within revision scripts.

        """
        current_rev = rev = False
        stamp_per_migration = not self.impl.transactional_ddl or \
                                    self._transaction_per_migration

        self.impl.start_migrations()
        for change, prev_rev, rev, doc in self._migrations_fn(
                                            self.get_current_revision(),
                                            self):
            with self.begin_transaction(_per_migration=True):
                if current_rev is False:
                    current_rev = prev_rev
                    if self.as_sql and not current_rev:
                        self._version.create(self.connection)
                if doc:
                    log.info("Running %s %s -> %s, %s", change.__name__, prev_rev,
                        rev, doc)
                else:
                    log.info("Running %s %s -> %s", change.__name__, prev_rev, rev)
                if self.as_sql:
                    self.impl.static_output(
                            "-- Running %s %s -> %s" %
                            (change.__name__, prev_rev, rev)
                        )
                change(**kw)
                if stamp_per_migration:
                    self._update_current_rev(prev_rev, rev)
                prev_rev = rev

        if rev is not False:
            if not stamp_per_migration:
                self._update_current_rev(current_rev, rev)

            if self.as_sql and not rev:
                self._version.drop(self.connection)

    def execute(self, sql, execution_options=None):
        """Execute a SQL construct or string statement.

        The underlying execution mechanics are used, that is
        if this is "offline mode" the SQL is written to the
        output buffer, otherwise the SQL is emitted on
        the current SQLAlchemy connection.

        """
        self.impl._exec(sql, execution_options)

    def _stdout_connection(self, connection):
        def dump(construct, *multiparams, **params):
            self.impl._exec(construct)

        return create_engine("%s://" % self.dialect.name,
                        strategy="mock", executor=dump)

    @property
    def bind(self):
        """Return the current "bind".

        In online mode, this is an instance of
        :class:`sqlalchemy.engine.Connection`, and is suitable
        for ad-hoc execution of any kind of usage described
        in :ref:`sqlexpression_toplevel` as well as
        for usage with the :meth:`sqlalchemy.schema.Table.create`
        and :meth:`sqlalchemy.schema.MetaData.create_all` methods
        of :class:`~sqlalchemy.schema.Table`, :class:`~sqlalchemy.schema.MetaData`.

        Note that when "standard output" mode is enabled,
        this bind will be a "mock" connection handler that cannot
        return results and is only appropriate for a very limited
        subset of commands.

        """
        return self.connection

    @property
    def config(self):
        """Return the :class:`.Config` used by the current environment, if any.

        .. versionadded:: 0.6.6

        """
        if self.environment_context:
            return self.environment_context.config
        else:
            return None

    def _compare_type(self, inspector_column, metadata_column):
        if self._user_compare_type is False:
            return False

        if callable(self._user_compare_type):
            user_value = self._user_compare_type(
                self,
                inspector_column,
                metadata_column,
                inspector_column.type,
                metadata_column.type
            )
            if user_value is not None:
                return user_value

        return self.impl.compare_type(
                                    inspector_column,
                                    metadata_column)

    def _compare_server_default(self, inspector_column,
                            metadata_column,
                            rendered_metadata_default,
                            rendered_column_default):

        if self._user_compare_server_default is False:
            return False

        if callable(self._user_compare_server_default):
            user_value = self._user_compare_server_default(
                    self,
                    inspector_column,
                    metadata_column,
                    rendered_column_default,
                    metadata_column.server_default,
                    rendered_metadata_default
            )
            if user_value is not None:
                return user_value

        return self.impl.compare_server_default(
                                inspector_column,
                                metadata_column,
                                rendered_metadata_default,
                                rendered_column_default)


########NEW FILE########
__FILENAME__ = op
from .operations import Operations
from . import util

# create proxy functions for
# each method on the Operations class.
util.create_module_class_proxy(Operations, globals(), locals())

########NEW FILE########
__FILENAME__ = operations
from contextlib import contextmanager

from sqlalchemy.types import NULLTYPE, Integer
from sqlalchemy import schema as sa_schema

from . import util
from .compat import string_types
from .ddl import impl

__all__ = ('Operations',)

try:
    from sqlalchemy.sql.naming import conv
except:
    conv = None

class Operations(object):
    """Define high level migration operations.

    Each operation corresponds to some schema migration operation,
    executed against a particular :class:`.MigrationContext`
    which in turn represents connectivity to a database,
    or a file output stream.

    While :class:`.Operations` is normally configured as
    part of the :meth:`.EnvironmentContext.run_migrations`
    method called from an ``env.py`` script, a standalone
    :class:`.Operations` instance can be
    made for use cases external to regular Alembic
    migrations by passing in a :class:`.MigrationContext`::

        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        conn = myengine.connect()
        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)

        op.alter_column("t", "c", nullable=True)

    """
    def __init__(self, migration_context):
        """Construct a new :class:`.Operations`

        :param migration_context: a :class:`.MigrationContext`
         instance.

        """
        self.migration_context = migration_context
        self.impl = migration_context.impl

    @classmethod
    @contextmanager
    def context(cls, migration_context):
        from .op import _install_proxy, _remove_proxy
        op = Operations(migration_context)
        _install_proxy(op)
        yield op
        _remove_proxy()


    def _primary_key_constraint(self, name, table_name, cols, schema=None):
        m = self._metadata()
        columns = [sa_schema.Column(n, NULLTYPE) for n in cols]
        t1 = sa_schema.Table(table_name, m,
                *columns,
                schema=schema)
        p = sa_schema.PrimaryKeyConstraint(*columns, name=name)
        t1.append_constraint(p)
        return p

    def _foreign_key_constraint(self, name, source, referent,
                                    local_cols, remote_cols,
                                    onupdate=None, ondelete=None,
                                    deferrable=None, source_schema=None,
                                    referent_schema=None, initially=None,
                                    match=None, **dialect_kw):
        m = self._metadata()
        if source == referent:
            t1_cols = local_cols + remote_cols
        else:
            t1_cols = local_cols
            sa_schema.Table(referent, m,
                    *[sa_schema.Column(n, NULLTYPE) for n in remote_cols],
                    schema=referent_schema)

        t1 = sa_schema.Table(source, m,
                *[sa_schema.Column(n, NULLTYPE) for n in t1_cols],
                schema=source_schema)

        tname = "%s.%s" % (referent_schema, referent) if referent_schema \
                else referent
        f = sa_schema.ForeignKeyConstraint(local_cols,
                                            ["%s.%s" % (tname, n)
                                            for n in remote_cols],
                                            name=name,
                                            onupdate=onupdate,
                                            ondelete=ondelete,
                                            deferrable=deferrable,
                                            initially=initially,
                                            match=match,
                                            **dialect_kw
                                            )
        t1.append_constraint(f)

        return f

    def _unique_constraint(self, name, source, local_cols, schema=None, **kw):
        t = sa_schema.Table(source, self._metadata(),
                    *[sa_schema.Column(n, NULLTYPE) for n in local_cols],
                    schema=schema)
        kw['name'] = name
        uq = sa_schema.UniqueConstraint(*[t.c[n] for n in local_cols], **kw)
        # TODO: need event tests to ensure the event
        # is fired off here
        t.append_constraint(uq)
        return uq

    def _check_constraint(self, name, source, condition, schema=None, **kw):
        t = sa_schema.Table(source, self._metadata(),
                    sa_schema.Column('x', Integer), schema=schema)
        ck = sa_schema.CheckConstraint(condition, name=name, **kw)
        t.append_constraint(ck)
        return ck

    def _metadata(self):
        kw = {}
        if 'target_metadata' in self.migration_context.opts:
            mt = self.migration_context.opts['target_metadata']
            if hasattr(mt, 'naming_convention'):
                kw['naming_convention'] = mt.naming_convention
        return sa_schema.MetaData(**kw)

    def _table(self, name, *columns, **kw):
        m = self._metadata()
        t = sa_schema.Table(name, m, *columns, **kw)
        for f in t.foreign_keys:
            self._ensure_table_for_fk(m, f)
        return t

    def _column(self, name, type_, **kw):
        return sa_schema.Column(name, type_, **kw)

    def _index(self, name, tablename, columns, schema=None, **kw):
        t = sa_schema.Table(tablename or 'no_table', self._metadata(),
            *[sa_schema.Column(n, NULLTYPE) for n in columns],
            schema=schema
        )
        return sa_schema.Index(name, *[t.c[n] for n in columns], **kw)

    def _parse_table_key(self, table_key):
        if '.' in table_key:
            tokens = table_key.split('.')
            sname = ".".join(tokens[0:-1])
            tname = tokens[-1]
        else:
            tname = table_key
            sname = None
        return (sname, tname)

    def _ensure_table_for_fk(self, metadata, fk):
        """create a placeholder Table object for the referent of a
        ForeignKey.

        """
        if isinstance(fk._colspec, string_types):
            table_key, cname = fk._colspec.rsplit('.', 1)
            sname, tname = self._parse_table_key(table_key)
            if table_key not in metadata.tables:
                rel_t = sa_schema.Table(tname, metadata, schema=sname)
            else:
                rel_t = metadata.tables[table_key]
            if cname not in rel_t.c:
                rel_t.append_column(sa_schema.Column(cname, NULLTYPE))

    def get_context(self):
        """Return the :class:`.MigrationContext` object that's
        currently in use.

        """

        return self.migration_context

    def rename_table(self, old_table_name, new_table_name, schema=None):
        """Emit an ALTER TABLE to rename a table.

        :param old_table_name: old name.
        :param new_table_name: new name.
        :param schema: Optional schema name to operate within.

        """
        self.impl.rename_table(
            old_table_name,
            new_table_name,
            schema=schema
        )

    @util._with_legacy_names([('name', 'new_column_name')])
    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        new_column_name=None,
                        type_=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=False,
                        existing_nullable=None,
                        existing_autoincrement=None,
                        schema=None
    ):
        """Issue an "alter column" instruction using the
        current migration context.

        Generally, only that aspect of the column which
        is being changed, i.e. name, type, nullability,
        default, needs to be specified.  Multiple changes
        can also be specified at once and the backend should
        "do the right thing", emitting each change either
        separately or together as the backend allows.

        MySQL has special requirements here, since MySQL
        cannot ALTER a column without a full specification.
        When producing MySQL-compatible migration files,
        it is recommended that the ``existing_type``,
        ``existing_server_default``, and ``existing_nullable``
        parameters be present, if not being altered.

        Type changes which are against the SQLAlchemy
        "schema" types :class:`~sqlalchemy.types.Boolean`
        and  :class:`~sqlalchemy.types.Enum` may also
        add or drop constraints which accompany those
        types on backends that don't support them natively.
        The ``existing_server_default`` argument is
        used in this case as well to remove a previous
        constraint.

        :param table_name: string name of the target table.
        :param column_name: string name of the target column,
         as it exists before the operation begins.
        :param nullable: Optional; specify ``True`` or ``False``
         to alter the column's nullability.
        :param server_default: Optional; specify a string
         SQL expression, :func:`~sqlalchemy.sql.expression.text`,
         or :class:`~sqlalchemy.schema.DefaultClause` to indicate
         an alteration to the column's default value.
         Set to ``None`` to have the default removed.
        :param new_column_name: Optional; specify a string name here to
         indicate the new name within a column rename operation.

         .. versionchanged:: 0.5.0
            The ``name`` parameter is now named ``new_column_name``.
            The old name will continue to function for backwards
            compatibility.

        :param ``type_``: Optional; a :class:`~sqlalchemy.types.TypeEngine`
         type object to specify a change to the column's type.
         For SQLAlchemy types that also indicate a constraint (i.e.
         :class:`~sqlalchemy.types.Boolean`, :class:`~sqlalchemy.types.Enum`),
         the constraint is also generated.
        :param autoincrement: set the ``AUTO_INCREMENT`` flag of the column;
         currently understood by the MySQL dialect.
        :param existing_type: Optional; a
         :class:`~sqlalchemy.types.TypeEngine`
         type object to specify the previous type.   This
         is required for all MySQL column alter operations that
         don't otherwise specify a new type, as well as for
         when nullability is being changed on a SQL Server
         column.  It is also used if the type is a so-called
         SQLlchemy "schema" type which may define a constraint (i.e.
         :class:`~sqlalchemy.types.Boolean`,
         :class:`~sqlalchemy.types.Enum`),
         so that the constraint can be dropped.
        :param existing_server_default: Optional; The existing
         default value of the column.   Required on MySQL if
         an existing default is not being changed; else MySQL
         removes the default.
        :param existing_nullable: Optional; the existing nullability
         of the column.  Required on MySQL if the existing nullability
         is not being changed; else MySQL sets this to NULL.
        :param existing_autoincrement: Optional; the existing autoincrement
         of the column.  Used for MySQL's system of altering a column
         that specifies ``AUTO_INCREMENT``.
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        compiler = self.impl.dialect.statement_compiler(
                            self.impl.dialect,
                            None
                        )
        def _count_constraint(constraint):
            return not isinstance(constraint, sa_schema.PrimaryKeyConstraint) and \
                (not constraint._create_rule or
                    constraint._create_rule(compiler))

        if existing_type and type_:
            t = self._table(table_name,
                        sa_schema.Column(column_name, existing_type),
                        schema=schema
                    )
            for constraint in t.constraints:
                if _count_constraint(constraint):
                    self.impl.drop_constraint(constraint)

        self.impl.alter_column(table_name, column_name,
            nullable=nullable,
            server_default=server_default,
            name=new_column_name,
            type_=type_,
            schema=schema,
            autoincrement=autoincrement,
            existing_type=existing_type,
            existing_server_default=existing_server_default,
            existing_nullable=existing_nullable,
            existing_autoincrement=existing_autoincrement
        )

        if type_:
            t = self._table(table_name,
                        sa_schema.Column(column_name, type_),
                        schema=schema
                    )
            for constraint in t.constraints:
                if _count_constraint(constraint):
                    self.impl.add_constraint(constraint)

    def f(self, name):
        """Indicate a string name that has already had a naming convention
        applied to it.

        This feature combines with the SQLAlchemy ``naming_convention`` feature
        to disambiguate constraint names that have already had naming
        conventions applied to them, versus those that have not.  This is
        necessary in the case that the ``"%(constraint_name)s"`` token
        is used within a naming convention, so that it can be identified
        that this particular name should remain fixed.

        If the :meth:`.Operations.f` is used on a constraint, the naming
        convention will not take effect::

            op.add_column('t', 'x', Boolean(name=op.f('ck_bool_t_x')))

        Above, the CHECK constraint generated will have the name ``ck_bool_t_x``
        regardless of whether or not a naming convention is in use.

        Alternatively, if a naming convention is in use, and 'f' is not used,
        names will be converted along conventions.  If the ``target_metadata``
        contains the naming convention
        ``{"ck": "ck_bool_%(table_name)s_%(constraint_name)s"}``, then the
        output of the following:

            op.add_column('t', 'x', Boolean(name='x'))

        will be::

            CONSTRAINT ck_bool_t_x CHECK (x in (1, 0)))

        The function is rendered in the output of autogenerate when
        a particular constraint name is already converted, for SQLAlchemy
        version **0.9.4 and greater only**.   Even though ``naming_convention``
        was introduced in 0.9.2, the string disambiguation service is new
        as of 0.9.4.

        .. versionadded:: 0.6.4

        """
        if conv:
            return conv(name)
        else:
            raise NotImplementedError(
                    "op.f() feature requires SQLAlchemy 0.9.4 or greater.")

    def add_column(self, table_name, column, schema=None):
        """Issue an "add column" instruction using the current
        migration context.

        e.g.::

            from alembic import op
            from sqlalchemy import Column, String

            op.add_column('organization',
                Column('name', String())
            )

        The provided :class:`~sqlalchemy.schema.Column` object can also
        specify a :class:`~sqlalchemy.schema.ForeignKey`, referencing
        a remote table name.  Alembic will automatically generate a stub
        "referenced" table and emit a second ALTER statement in order
        to add the constraint separately::

            from alembic import op
            from sqlalchemy import Column, INTEGER, ForeignKey

            op.add_column('organization',
                Column('account_id', INTEGER, ForeignKey('accounts.id'))
            )

        Note that this statement uses the :class:`~sqlalchemy.schema.Column`
        construct as is from the SQLAlchemy library.  In particular,
        default values to be created on the database side are
        specified using the ``server_default`` parameter, and not
        ``default`` which only specifies Python-side defaults::

            from alembic import op
            from sqlalchemy import Column, TIMESTAMP, func

            # specify "DEFAULT NOW" along with the column add
            op.add_column('account',
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

        :param table_name: String name of the parent table.
        :param column: a :class:`sqlalchemy.schema.Column` object
         representing the new column.
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        t = self._table(table_name, column, schema=schema)
        self.impl.add_column(
            table_name,
            column,
            schema=schema
        )
        for constraint in t.constraints:
            if not isinstance(constraint, sa_schema.PrimaryKeyConstraint):
                self.impl.add_constraint(constraint)

    def drop_column(self, table_name, column_name, **kw):
        """Issue a "drop column" instruction using the current
        migration context.

        e.g.::

            drop_column('organization', 'account_id')

        :param table_name: name of table
        :param column_name: name of column
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        :param mssql_drop_check: Optional boolean.  When ``True``, on
         Microsoft SQL Server only, first
         drop the CHECK constraint on the column using a
         SQL-script-compatible
         block that selects into a @variable from sys.check_constraints,
         then exec's a separate DROP CONSTRAINT for that constraint.
        :param mssql_drop_default: Optional boolean.  When ``True``, on
         Microsoft SQL Server only, first
         drop the DEFAULT constraint on the column using a
         SQL-script-compatible
         block that selects into a @variable from sys.default_constraints,
         then exec's a separate DROP CONSTRAINT for that default.
        :param mssql_drop_foreign_key: Optional boolean.  When ``True``, on
         Microsoft SQL Server only, first
         drop a single FOREIGN KEY constraint on the column using a
         SQL-script-compatible
         block that selects into a @variable from
         sys.foreign_keys/sys.foreign_key_columns,
         then exec's a separate DROP CONSTRAINT for that default.  Only
         works if the column has exactly one FK constraint which refers to
         it, at the moment.

         .. versionadded:: 0.6.2

        """

        self.impl.drop_column(
            table_name,
            self._column(column_name, NULLTYPE),
            **kw
        )


    def create_primary_key(self, name, table_name, cols, schema=None):
        """Issue a "create primary key" instruction using the current
        migration context.

        e.g.::

            from alembic import op
            op.create_primary_key(
                        "pk_my_table", "my_table",
                        ["id", "version"]
                    )

        This internally generates a :class:`~sqlalchemy.schema.Table` object
        containing the necessary columns, then generates a new
        :class:`~sqlalchemy.schema.PrimaryKeyConstraint`
        object which it then associates with the :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        .. versionadded:: 0.5.0

        :param name: Name of the primary key constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param table_name: String name of the target table.
        :param cols: a list of string column names to be applied to the
         primary key constraint.
        :param schema: Optional schema name of the table.

        """
        self.impl.add_constraint(
                    self._primary_key_constraint(name, table_name, cols,
                                schema)
                )


    def create_foreign_key(self, name, source, referent, local_cols,
                           remote_cols, onupdate=None, ondelete=None,
                           deferrable=None, initially=None, match=None,
                           source_schema=None, referent_schema=None,
                           **dialect_kw):
        """Issue a "create foreign key" instruction using the
        current migration context.

        e.g.::

            from alembic import op
            op.create_foreign_key(
                        "fk_user_address", "address",
                        "user", ["user_id"], ["id"])

        This internally generates a :class:`~sqlalchemy.schema.Table` object
        containing the necessary columns, then generates a new
        :class:`~sqlalchemy.schema.ForeignKeyConstraint`
        object which it then associates with the :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        :param name: Name of the foreign key constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param source: String name of the source table.
        :param referent: String name of the destination table.
        :param local_cols: a list of string column names in the
         source table.
        :param remote_cols: a list of string column names in the
         remote table.
        :param onupdate: Optional string. If set, emit ON UPDATE <value> when
         issuing DDL for this constraint. Typical values include CASCADE,
         DELETE and RESTRICT.
        :param ondelete: Optional string. If set, emit ON DELETE <value> when
         issuing DDL for this constraint. Typical values include CASCADE,
         DELETE and RESTRICT.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT
         DEFERRABLE when issuing DDL for this constraint.
        :param source_schema: Optional schema name of the source table.
        :param referent_schema: Optional schema name of the destination table.

        """

        self.impl.add_constraint(
                    self._foreign_key_constraint(name, source, referent,
                            local_cols, remote_cols,
                            onupdate=onupdate, ondelete=ondelete,
                            deferrable=deferrable, source_schema=source_schema,
                            referent_schema=referent_schema,
                            initially=initially, match=match, **dialect_kw)
                )

    def create_unique_constraint(self, name, source, local_cols,
                                 schema=None, **kw):
        """Issue a "create unique constraint" instruction using the
        current migration context.

        e.g.::

            from alembic import op
            op.create_unique_constraint("uq_user_name", "user", ["name"])

        This internally generates a :class:`~sqlalchemy.schema.Table` object
        containing the necessary columns, then generates a new
        :class:`~sqlalchemy.schema.UniqueConstraint`
        object which it then associates with the :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        :param name: Name of the unique constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param source: String name of the source table. Dotted schema names are
         supported.
        :param local_cols: a list of string column names in the
         source table.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT DEFERRABLE when
         issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value> when issuing DDL
         for this constraint.
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        self.impl.add_constraint(
                    self._unique_constraint(name, source, local_cols,
                        schema=schema, **kw)
                )

    def create_check_constraint(self, name, source, condition,
                                schema=None, **kw):
        """Issue a "create check constraint" instruction using the
        current migration context.

        e.g.::

            from alembic import op
            from sqlalchemy.sql import column, func

            op.create_check_constraint(
                "ck_user_name_len",
                "user",
                func.len(column('name')) > 5
            )

        CHECK constraints are usually against a SQL expression, so ad-hoc
        table metadata is usually needed.   The function will convert the given
        arguments into a :class:`sqlalchemy.schema.CheckConstraint` bound
        to an anonymous table in order to emit the CREATE statement.

        :param name: Name of the check constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param source: String name of the source table.
        :param condition: SQL expression that's the condition of the constraint.
         Can be a string or SQLAlchemy expression language structure.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT DEFERRABLE when
         issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value> when issuing DDL
         for this constraint.
        :param schema: Optional schema name to operate within.

         ..versionadded:: 0.4.0

        """
        self.impl.add_constraint(
            self._check_constraint(name, source, condition, schema=schema, **kw)
        )

    def create_table(self, name, *columns, **kw):
        """Issue a "create table" instruction using the current migration context.

        This directive receives an argument list similar to that of the
        traditional :class:`sqlalchemy.schema.Table` construct, but without the
        metadata::

            from sqlalchemy import INTEGER, VARCHAR, NVARCHAR, Column
            from alembic import op

            op.create_table(
                'account',
                Column('id', INTEGER, primary_key=True),
                Column('name', VARCHAR(50), nullable=False),
                Column('description', NVARCHAR(200))
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

        Note that :meth:`.create_table` accepts :class:`~sqlalchemy.schema.Column`
        constructs directly from the SQLAlchemy library.  In particular,
        default values to be created on the database side are
        specified using the ``server_default`` parameter, and not
        ``default`` which only specifies Python-side defaults::

            from alembic import op
            from sqlalchemy import Column, TIMESTAMP, func

            # specify "DEFAULT NOW" along with the "timestamp" column
            op.create_table('account',
                Column('id', INTEGER, primary_key=True),
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

        :param name: Name of the table
        :param \*columns: collection of :class:`~sqlalchemy.schema.Column`
         objects within
         the table, as well as optional :class:`~sqlalchemy.schema.Constraint`
         objects
         and :class:`~.sqlalchemy.schema.Index` objects.
        :param schema: Optional schema name to operate within.
        :param \**kw: Other keyword arguments are passed to the underlying
         :class:`sqlalchemy.schema.Table` object created for the command.

        """
        self.impl.create_table(
            self._table(name, *columns, **kw)
        )

    def drop_table(self, name, **kw):
        """Issue a "drop table" instruction using the current
        migration context.


        e.g.::

            drop_table("accounts")

        :param name: Name of the table
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        :param \**kw: Other keyword arguments are passed to the underlying
         :class:`sqlalchemy.schema.Table` object created for the command.

        """
        self.impl.drop_table(
            self._table(name, **kw)
        )

    def create_index(self, name, table_name, columns, schema=None, **kw):
        """Issue a "create index" instruction using the current
        migration context.

        e.g.::

            from alembic import op
            op.create_index('ik_test', 't1', ['foo', 'bar'])

        :param name: name of the index.
        :param table_name: name of the owning table.

         .. versionchanged:: 0.5.0
            The ``tablename`` parameter is now named ``table_name``.
            As this is a positional argument, the old name is no
            longer present.

        :param columns: a list of string column names in the
         table.
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        self.impl.create_index(
            self._index(name, table_name, columns, schema=schema, **kw)
        )

    @util._with_legacy_names([('tablename', 'table_name')])
    def drop_index(self, name, table_name=None, schema=None):
        """Issue a "drop index" instruction using the current
        migration context.

        e.g.::

            drop_index("accounts")

        :param name: name of the index.
        :param table_name: name of the owning table.  Some
         backends such as Microsoft SQL Server require this.

         .. versionchanged:: 0.5.0
            The ``tablename`` parameter is now named ``table_name``.
            The old name will continue to function for backwards
            compatibility.

        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """
        # need a dummy column name here since SQLAlchemy
        # 0.7.6 and further raises on Index with no columns
        self.impl.drop_index(
            self._index(name, table_name, ['x'], schema=schema)
        )

    @util._with_legacy_names([("type", "type_")])
    def drop_constraint(self, name, table_name, type_=None, schema=None):
        """Drop a constraint of the given name, typically via DROP CONSTRAINT.

        :param name: name of the constraint.
        :param table_name: table name.

         .. versionchanged:: 0.5.0
            The ``tablename`` parameter is now named ``table_name``.
            As this is a positional argument, the old name is no
            longer present.

        :param ``type_``: optional, required on MySQL.  can be
         'foreignkey', 'primary', 'unique', or 'check'.

         .. versionchanged:: 0.5.0
            The ``type`` parameter is now named ``type_``.  The old name
            ``type`` will remain for backwards compatibility.

         .. versionadded:: 0.3.6 'primary' qualfier to enable
            dropping of MySQL primary key constraints.

        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        t = self._table(table_name, schema=schema)
        types = {
            'foreignkey': lambda name: sa_schema.ForeignKeyConstraint(
                                [], [], name=name),
            'primary': sa_schema.PrimaryKeyConstraint,
            'unique': sa_schema.UniqueConstraint,
            'check': lambda name: sa_schema.CheckConstraint("", name=name),
            None: sa_schema.Constraint
        }
        try:
            const = types[type_]
        except KeyError:
            raise TypeError("'type' can be one of %s" %
                        ", ".join(sorted(repr(x) for x in types)))

        const = const(name=name)
        t.append_constraint(const)
        self.impl.drop_constraint(const)

    def bulk_insert(self, table, rows, multiinsert=True):
        """Issue a "bulk insert" operation using the current
        migration context.

        This provides a means of representing an INSERT of multiple rows
        which works equally well in the context of executing on a live
        connection as well as that of generating a SQL script.   In the
        case of a SQL script, the values are rendered inline into the
        statement.

        e.g.::

            from alembic import op
            from datetime import date
            from sqlalchemy.sql import table, column
            from sqlalchemy import String, Integer, Date

            # Create an ad-hoc table to use for the insert statement.
            accounts_table = table('account',
                column('id', Integer),
                column('name', String),
                column('create_date', Date)
            )

            op.bulk_insert(accounts_table,
                [
                    {'id':1, 'name':'John Smith',
                            'create_date':date(2010, 10, 5)},
                    {'id':2, 'name':'Ed Williams',
                            'create_date':date(2007, 5, 27)},
                    {'id':3, 'name':'Wendy Jones',
                            'create_date':date(2008, 8, 15)},
                ]
            )

        When using --sql mode, some datatypes may not render inline automatically,
        such as dates and other special types.   When this issue is present,
        :meth:`.Operations.inline_literal` may be used::

            op.bulk_insert(accounts_table,
                [
                    {'id':1, 'name':'John Smith',
                            'create_date':op.inline_literal("2010-10-05")},
                    {'id':2, 'name':'Ed Williams',
                            'create_date':op.inline_literal("2007-05-27")},
                    {'id':3, 'name':'Wendy Jones',
                            'create_date':op.inline_literal("2008-08-15")},
                ],
                multiinsert=False
            )

        When using :meth:`.Operations.inline_literal` in conjunction with
        :meth:`.Operations.bulk_insert`, in order for the statement to work
        in "online" (e.g. non --sql) mode, the
        :paramref:`~.Operations.bulk_insert.multiinsert`
        flag should be set to ``False``, which will have the effect of
        individual INSERT statements being emitted to the database, each
        with a distinct VALUES clause, so that the "inline" values can
        still be rendered, rather than attempting to pass the values
        as bound parameters.

        .. versionadded:: 0.6.4 :meth:`.Operations.inline_literal` can now
           be used with :meth:`.Operations.bulk_insert`, and the
           :paramref:`~.Operations.bulk_insert.multiinsert` flag has
           been added to assist in this usage when running in "online"
           mode.

        :param table: a table object which represents the target of the INSERT.

        :param rows: a list of dictionaries indicating rows.

        :param multiinsert: when at its default of True and --sql mode is not
           enabled, the INSERT statement will be executed using
           "executemany()" style, where all elements in the list of dictionaries
           are passed as bound parameters in a single list.   Setting this
           to False results in individual INSERT statements being emitted
           per parameter set, and is needed in those cases where non-literal
           values are present in the parameter sets.

           .. versionadded:: 0.6.4

          """
        self.impl.bulk_insert(table, rows, multiinsert=multiinsert)

    def inline_literal(self, value, type_=None):
        """Produce an 'inline literal' expression, suitable for
        using in an INSERT, UPDATE, or DELETE statement.

        When using Alembic in "offline" mode, CRUD operations
        aren't compatible with SQLAlchemy's default behavior surrounding
        literal values,
        which is that they are converted into bound values and passed
        separately into the ``execute()`` method of the DBAPI cursor.
        An offline SQL
        script needs to have these rendered inline.  While it should
        always be noted that inline literal values are an **enormous**
        security hole in an application that handles untrusted input,
        a schema migration is not run in this context, so
        literals are safe to render inline, with the caveat that
        advanced types like dates may not be supported directly
        by SQLAlchemy.

        See :meth:`.execute` for an example usage of
        :meth:`.inline_literal`.

        :param value: The value to render.  Strings, integers, and simple
         numerics should be supported.   Other types like boolean,
         dates, etc. may or may not be supported yet by various
         backends.
        :param ``type_``: optional - a :class:`sqlalchemy.types.TypeEngine`
         subclass stating the type of this value.  In SQLAlchemy
         expressions, this is usually derived automatically
         from the Python type of the value itself, as well as
         based on the context in which the value is used.

        """
        return impl._literal_bindparam(None, value, type_=type_)

    def execute(self, sql, execution_options=None):
        """Execute the given SQL using the current migration context.

        In a SQL script context, the statement is emitted directly to the
        output stream.   There is *no* return result, however, as this
        function is oriented towards generating a change script
        that can run in "offline" mode.  For full interaction
        with a connected database, use the "bind" available
        from the context::

            from alembic import op
            connection = op.get_bind()

        Also note that any parameterized statement here *will not work*
        in offline mode - INSERT, UPDATE and DELETE statements which refer
        to literal values would need to render
        inline expressions.   For simple use cases, the
        :meth:`.inline_literal` function can be used for **rudimentary**
        quoting of string values.  For "bulk" inserts, consider using
        :meth:`.bulk_insert`.

        For example, to emit an UPDATE statement which is equally
        compatible with both online and offline mode::

            from sqlalchemy.sql import table, column
            from sqlalchemy import String
            from alembic import op

            account = table('account',
                column('name', String)
            )
            op.execute(
                account.update().\\
                    where(account.c.name==op.inline_literal('account 1')).\\
                    values({'name':op.inline_literal('account 2')})
                    )

        Note above we also used the SQLAlchemy
        :func:`sqlalchemy.sql.expression.table`
        and :func:`sqlalchemy.sql.expression.column` constructs to make a brief,
        ad-hoc table construct just for our UPDATE statement.  A full
        :class:`~sqlalchemy.schema.Table` construct of course works perfectly
        fine as well, though note it's a recommended practice to at least ensure
        the definition of a table is self-contained within the migration script,
        rather than imported from a module that may break compatibility with
        older migrations.

        :param sql: Any legal SQLAlchemy expression, including:

        * a string
        * a :func:`sqlalchemy.sql.expression.text` construct.
        * a :func:`sqlalchemy.sql.expression.insert` construct.
        * a :func:`sqlalchemy.sql.expression.update`,
          :func:`sqlalchemy.sql.expression.insert`,
          or :func:`sqlalchemy.sql.expression.delete`  construct.
        * Pretty much anything that's "executable" as described
          in :ref:`sqlexpression_toplevel`.

        :param execution_options: Optional dictionary of
         execution options, will be passed to
         :meth:`sqlalchemy.engine.Connection.execution_options`.
        """
        self.migration_context.impl.execute(sql,
                    execution_options=execution_options)

    def get_bind(self):
        """Return the current 'bind'.

        Under normal circumstances, this is the
        :class:`~sqlalchemy.engine.Connection` currently being used
        to emit SQL to the database.

        In a SQL script context, this value is ``None``. [TODO: verify this]

        """
        return self.migration_context.impl.bind


########NEW FILE########
__FILENAME__ = script
import datetime
import os
import re
import shutil
from . import util

_sourceless_rev_file = re.compile(r'(.*\.py)(c|o)?$')
_only_source_rev_file = re.compile(r'(.*\.py)$')
_legacy_rev = re.compile(r'([a-f0-9]+)\.py$')
_mod_def_re = re.compile(r'(upgrade|downgrade)_([a-z0-9]+)')
_slug_re = re.compile(r'\w+')
_default_file_template = "%(rev)s_%(slug)s"
_relative_destination = re.compile(r'(?:\+|-)\d+')

class ScriptDirectory(object):
    """Provides operations upon an Alembic script directory.

    This object is useful to get information as to current revisions,
    most notably being able to get at the "head" revision, for schemes
    that want to test if the current revision in the database is the most
    recent::

        from alembic.script import ScriptDirectory
        from alembic.config import Config
        config = Config()
        config.set_main_option("script_location", "myapp:migrations")
        script = ScriptDirectory.from_config(config)

        head_revision = script.get_current_head()



    """
    def __init__(self, dir, file_template=_default_file_template,
                    truncate_slug_length=40,
                    sourceless=False):
        self.dir = dir
        self.versions = os.path.join(self.dir, 'versions')
        self.file_template = file_template
        self.truncate_slug_length = truncate_slug_length or 40
        self.sourceless = sourceless

        if not os.access(dir, os.F_OK):
            raise util.CommandError("Path doesn't exist: %r.  Please use "
                        "the 'init' command to create a new "
                        "scripts folder." % dir)

    @classmethod
    def from_config(cls, config):
        """Produce a new :class:`.ScriptDirectory` given a :class:`.Config`
        instance.

        The :class:`.Config` need only have the ``script_location`` key
        present.

        """
        script_location = config.get_main_option('script_location')
        if script_location is None:
            raise util.CommandError("No 'script_location' key "
                                    "found in configuration.")
        truncate_slug_length = config.get_main_option("truncate_slug_length")
        if truncate_slug_length is not None:
            truncate_slug_length = int(truncate_slug_length)
        return ScriptDirectory(
                    util.coerce_resource_to_filename(script_location),
                    file_template=config.get_main_option(
                                        'file_template',
                                        _default_file_template),
                    truncate_slug_length=truncate_slug_length,
                    sourceless=config.get_main_option("sourceless") == "true"
                    )

    def walk_revisions(self, base="base", head="head"):
        """Iterate through all revisions.

        This is actually a breadth-first tree traversal,
        with leaf nodes being heads.

        """
        if head == "head":
            heads = set(self.get_heads())
        else:
            heads = set([head])
        while heads:
            todo = set(heads)
            heads = set()
            for head in todo:
                if head in heads:
                    break
                for sc in self.iterate_revisions(head, base):
                    if sc.is_branch_point and sc.revision not in todo:
                        heads.add(sc.revision)
                        break
                    else:
                        yield sc

    def get_revision(self, id_):
        """Return the :class:`.Script` instance with the given rev id."""

        id_ = self.as_revision_number(id_)
        try:
            return self._revision_map[id_]
        except KeyError:
            # do a partial lookup
            revs = [x for x in self._revision_map
                    if x is not None and x.startswith(id_)]
            if not revs:
                raise util.CommandError("No such revision '%s'" % id_)
            elif len(revs) > 1:
                raise util.CommandError(
                            "Multiple revisions start "
                            "with '%s', %s..." % (
                                id_,
                                ", ".join("'%s'" % r for r in revs[0:3])
                            ))
            else:
                return self._revision_map[revs[0]]

    _get_rev = get_revision

    def as_revision_number(self, id_):
        """Convert a symbolic revision, i.e. 'head' or 'base', into
        an actual revision number."""

        if id_ == 'head':
            id_ = self.get_current_head()
        elif id_ == 'base':
            id_ = None
        return id_

    _as_rev_number = as_revision_number

    def iterate_revisions(self, upper, lower):
        """Iterate through script revisions, starting at the given
        upper revision identifier and ending at the lower.

        The traversal uses strictly the `down_revision`
        marker inside each migration script, so
        it is a requirement that upper >= lower,
        else you'll get nothing back.

        The iterator yields :class:`.Script` objects.

        """
        if upper is not None and _relative_destination.match(upper):
            relative = int(upper)
            revs = list(self._iterate_revisions("head", lower))
            revs = revs[-relative:]
            if len(revs) != abs(relative):
                raise util.CommandError("Relative revision %s didn't "
                            "produce %d migrations" % (upper, abs(relative)))
            return iter(revs)
        elif lower is not None and _relative_destination.match(lower):
            relative = int(lower)
            revs = list(self._iterate_revisions(upper, "base"))
            revs = revs[0:-relative]
            if len(revs) != abs(relative):
                raise util.CommandError("Relative revision %s didn't "
                            "produce %d migrations" % (lower, abs(relative)))
            return iter(revs)
        else:
            return self._iterate_revisions(upper, lower)

    def _iterate_revisions(self, upper, lower):
        lower = self.get_revision(lower)
        upper = self.get_revision(upper)
        orig = lower.revision if lower else 'base', \
                upper.revision if upper else 'base'
        script = upper
        while script != lower:
            if script is None and lower is not None:
                raise util.CommandError(
                        "Revision %s is not an ancestor of %s" % orig)
            yield script
            downrev = script.down_revision
            script = self._revision_map[downrev]

    def _upgrade_revs(self, destination, current_rev):
        revs = self.iterate_revisions(destination, current_rev)
        return [
            (script.module.upgrade, script.down_revision, script.revision,
                script.doc)
            for script in reversed(list(revs))
            ]

    def _downgrade_revs(self, destination, current_rev):
        revs = self.iterate_revisions(current_rev, destination)
        return [
            (script.module.downgrade, script.revision, script.down_revision,
                script.doc)
            for script in revs
            ]

    def run_env(self):
        """Run the script environment.

        This basically runs the ``env.py`` script present
        in the migration environment.   It is called exclusively
        by the command functions in :mod:`alembic.command`.


        """
        util.load_python_file(self.dir, 'env.py')

    @property
    def env_py_location(self):
        return os.path.abspath(os.path.join(self.dir, "env.py"))

    @util.memoized_property
    def _revision_map(self):
        map_ = {}
        for file_ in os.listdir(self.versions):
            script = Script._from_filename(self, self.versions, file_)
            if script is None:
                continue
            if script.revision in map_:
                util.warn("Revision %s is present more than once" %
                                script.revision)
            map_[script.revision] = script
        for rev in map_.values():
            if rev.down_revision is None:
                continue
            if rev.down_revision not in map_:
                util.warn("Revision %s referenced from %s is not present"
                            % (rev.down_revision, rev))
                rev.down_revision = None
            else:
                map_[rev.down_revision].add_nextrev(rev.revision)
        map_[None] = None
        return map_

    def _rev_path(self, rev_id, message, create_date):
        slug = "_".join(_slug_re.findall(message or "")).lower()
        if len(slug) > self.truncate_slug_length:
            slug = slug[:self.truncate_slug_length].rsplit('_', 1)[0] + '_'
        filename = "%s.py" % (
            self.file_template % {
                'rev': rev_id,
                'slug': slug,
                'year': create_date.year,
                'month': create_date.month,
                'day': create_date.day,
                'hour': create_date.hour,
                'minute': create_date.minute,
                'second': create_date.second
            }
        )
        return os.path.join(self.versions, filename)

    def get_current_head(self):
        """Return the current head revision.

        If the script directory has multiple heads
        due to branching, an error is raised.

        Returns a string revision number.

        """
        current_heads = self.get_heads()
        if len(current_heads) > 1:
            raise util.CommandError('Only a single head is supported. The '
                'script directory has multiple heads (due to branching), which '
                'must be resolved by manually editing the revision files to '
                'form a linear sequence. Run `alembic branches` to see the '
                'divergence(s).')

        if current_heads:
            return current_heads[0]
        else:
            return None

    _current_head = get_current_head
    """the 0.2 name, for backwards compat."""

    def get_heads(self):
        """Return all "head" revisions as strings.

        Returns a list of string revision numbers.

        This is normally a list of length one,
        unless branches are present.  The
        :meth:`.ScriptDirectory.get_current_head()` method
        can be used normally when a script directory
        has only one head.

        """
        heads = []
        for script in self._revision_map.values():
            if script and script.is_head:
                heads.append(script.revision)
        return heads

    def get_base(self):
        """Return the "base" revision as a string.

        This is the revision number of the script that
        has a ``down_revision`` of None.

        Behavior is not defined if more than one script
        has a ``down_revision`` of None.

        """
        for script in self._revision_map.values():
            if script and script.down_revision is None \
                and script.revision in self._revision_map:
                return script.revision
        else:
            return None

    def _generate_template(self, src, dest, **kw):
        util.status("Generating %s" % os.path.abspath(dest),
            util.template_to_file,
            src,
            dest,
            **kw
        )

    def _copy_file(self, src, dest):
        util.status("Generating %s" % os.path.abspath(dest),
                    shutil.copy,
                    src, dest)

    def generate_revision(self, revid, message, refresh=False, **kw):
        """Generate a new revision file.

        This runs the ``script.py.mako`` template, given
        template arguments, and creates a new file.

        :param revid: String revision id.  Typically this
         comes from ``alembic.util.rev_id()``.
        :param message: the revision message, the one passed
         by the -m argument to the ``revision`` command.
        :param refresh: when True, the in-memory state of this
         :class:`.ScriptDirectory` will be updated with a new
         :class:`.Script` instance representing the new revision;
         the :class:`.Script` instance is returned.
         If False, the file is created but the state of the
         :class:`.ScriptDirectory` is unmodified; ``None``
         is returned.

        """
        current_head = self.get_current_head()
        create_date = datetime.datetime.now()
        path = self._rev_path(revid, message, create_date)
        self._generate_template(
            os.path.join(self.dir, "script.py.mako"),
            path,
            up_revision=str(revid),
            down_revision=current_head,
            create_date=create_date,
            message=message if message is not None else ("empty message"),
            **kw
        )
        if refresh:
            script = Script._from_path(self, path)
            self._revision_map[script.revision] = script
            if script.down_revision:
                self._revision_map[script.down_revision].\
                        add_nextrev(script.revision)
            return script
        else:
            return None


class Script(object):
    """Represent a single revision file in a ``versions/`` directory.

    The :class:`.Script` instance is returned by methods
    such as :meth:`.ScriptDirectory.iterate_revisions`.

    """

    nextrev = frozenset()

    def __init__(self, module, rev_id, path):
        self.module = module
        self.revision = rev_id
        self.path = path
        self.down_revision = getattr(module, 'down_revision', None)

    revision = None
    """The string revision number for this :class:`.Script` instance."""

    module = None
    """The Python module representing the actual script itself."""

    path = None
    """Filesystem path of the script."""

    down_revision = None
    """The ``down_revision`` identifier within the migration script."""

    @property
    def doc(self):
        """Return the docstring given in the script."""

        return re.split("\n\n", self.longdoc)[0]

    @property
    def longdoc(self):
        """Return the docstring given in the script."""

        doc = self.module.__doc__
        if doc:
            if hasattr(self.module, "_alembic_source_encoding"):
                doc = doc.decode(self.module._alembic_source_encoding)
            return doc.strip()
        else:
            return ""

    def add_nextrev(self, rev):
        self.nextrev = self.nextrev.union([rev])

    @property
    def is_head(self):
        """Return True if this :class:`.Script` is a 'head' revision.

        This is determined based on whether any other :class:`.Script`
        within the :class:`.ScriptDirectory` refers to this
        :class:`.Script`.   Multiple heads can be present.

        """
        return not bool(self.nextrev)

    @property
    def is_branch_point(self):
        """Return True if this :class:`.Script` is a branch point.

        A branchpoint is defined as a :class:`.Script` which is referred
        to by more than one succeeding :class:`.Script`, that is more
        than one :class:`.Script` has a `down_revision` identifier pointing
        here.

        """
        return len(self.nextrev) > 1

    @property
    def log_entry(self):
        return \
            "Rev: %s%s%s\n" \
            "Parent: %s\n" \
            "Path: %s\n" \
            "\n%s\n" % (
                self.revision,
                " (head)" if self.is_head else "",
                " (branchpoint)" if self.is_branch_point else "",
                self.down_revision,
                self.path,
                "\n".join(
                    "    %s" % para
                    for para in self.longdoc.splitlines()
                )
            )

    def __str__(self):
        return "%s -> %s%s%s, %s" % (
                        self.down_revision,
                        self.revision,
                        " (head)" if self.is_head else "",
                        " (branchpoint)" if self.is_branch_point else "",
                        self.doc)

    @classmethod
    def _from_path(cls, scriptdir, path):
        dir_, filename = os.path.split(path)
        return cls._from_filename(scriptdir, dir_, filename)

    @classmethod
    def _from_filename(cls, scriptdir, dir_, filename):
        if scriptdir.sourceless:
            py_match = _sourceless_rev_file.match(filename)
        else:
            py_match = _only_source_rev_file.match(filename)

        if not py_match:
            return None

        py_filename = py_match.group(1)

        if scriptdir.sourceless:
            is_c = py_match.group(2) == 'c'
            is_o = py_match.group(2) == 'o'
        else:
            is_c = is_o = False

        if is_o or is_c:
            py_exists = os.path.exists(os.path.join(dir_, py_filename))
            pyc_exists = os.path.exists(os.path.join(dir_, py_filename + "c"))

            # prefer .py over .pyc because we'd like to get the
            # source encoding; prefer .pyc over .pyo because we'd like to
            # have the docstrings which a -OO file would not have
            if py_exists or is_o and pyc_exists:
                return None

        module = util.load_python_file(dir_, filename)

        if not hasattr(module, "revision"):
            # attempt to get the revision id from the script name,
            # this for legacy only
            m = _legacy_rev.match(filename)
            if not m:
                raise util.CommandError(
                        "Could not determine revision id from filename %s. "
                        "Be sure the 'revision' variable is "
                        "declared inside the script (please see 'Upgrading "
                        "from Alembic 0.1 to 0.2' in the documentation)."
                        % filename)
            else:
                revision = m.group(1)
        else:
            revision = module.revision
        return Script(module, revision, os.path.join(dir_, filename))

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import logging
import re

USE_TWOPHASE = False

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# gather section names referring to different
# databases.  These are named "engine1", "engine2"
# in the sample .ini file.
db_names = config.get_main_option('databases')

# add your model's MetaData objects here
# for 'autogenerate' support.  These must be set
# up to hold just those tables targeting a
# particular database. table.tometadata() may be
# helpful here in case a "copy" of
# a MetaData is needed.
# from myapp import mymodel
# target_metadata = {
#       'engine1':mymodel.metadata1,
#       'engine2':mymodel.metadata2
#}
target_metadata = {}

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # for the --sql use case, run migrations for each URL into
    # individual files.

    engines = {}
    for name in re.split(r',\s*', db_names):
        engines[name] = rec = {}
        rec['url'] = context.config.get_section_option(name,
                                            "sqlalchemy.url")

    for name, rec in engines.items():
        logger.info("Migrating database %s" % name)
        file_ = "%s.sql" % name
        logger.info("Writing output to %s" % file_)
        with open(file_, 'w') as buffer:
            context.configure(url=rec['url'], output_buffer=buffer,
                                target_metadata=target_metadata.get(name))
            with context.begin_transaction():
                context.run_migrations(engine_name=name)

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # for the direct-to-DB use case, start a transaction on all
    # engines, then run all migrations, then commit all transactions.

    engines = {}
    for name in re.split(r',\s*', db_names):
        engines[name] = rec = {}
        rec['engine'] = engine_from_config(
                                    context.config.get_section(name),
                                    prefix='sqlalchemy.',
                                    poolclass=pool.NullPool)

    for name, rec in engines.items():
        engine = rec['engine']
        rec['connection'] = conn = engine.connect()

        if USE_TWOPHASE:
            rec['transaction'] = conn.begin_twophase()
        else:
            rec['transaction'] = conn.begin()

    try:
        for name, rec in engines.items():
            logger.info("Migrating database %s" % name)
            context.configure(
                        connection=rec['connection'],
                        upgrade_token="%s_upgrades" % name,
                        downgrade_token="%s_downgrades" % name,
                        target_metadata=target_metadata.get(name)
                    )
            context.run_migrations(engine_name=name)

        if USE_TWOPHASE:
            for rec in engines.values():
                rec['transaction'].prepare()

        for rec in engines.values():
            rec['transaction'].commit()
    except:
        for rec in engines.values():
            rec['transaction'].rollback()
        raise
    finally:
        for rec in engines.values():
            rec['connection'].close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

########NEW FILE########
__FILENAME__ = env
"""Pylons bootstrap environment.

Place 'pylons_config_file' into alembic.ini, and the application will
be loaded from there.

"""
from alembic import context
from paste.deploy import loadapp
from logging.config import fileConfig
from sqlalchemy.engine.base import Engine


try:
    # if pylons app already in, don't create a new app
    from pylons import config as pylons_config
    pylons_config['__file__']
except:
    config = context.config
    # can use config['__file__'] here, i.e. the Pylons
    # ini file, instead of alembic.ini
    config_file = config.get_main_option('pylons_config_file')
    fileConfig(config_file)
    wsgi_app = loadapp('config:%s' % config_file, relative_to='.')


# customize this section for non-standard engine configurations.
meta = __import__("%s.model.meta" % wsgi_app.config['pylons.package']).model.meta

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
                url=meta.engine.url, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # specify here how the engine is acquired
    # engine = meta.engine
    raise NotImplementedError("Please specify engine connectivity here")

    if isinstance(engine, Engine):
        connection = engine.connect()
    else:
        raise Exception(
            'Expected engine instance got %s instead' % type(engine)
        )

    context.configure(
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

########NEW FILE########
__FILENAME__ = util
import sys
import os
import textwrap
import warnings
import re
import inspect
import uuid

from mako.template import Template
from sqlalchemy.engine import url
from sqlalchemy import __version__

from .compat import callable, exec_, load_module_py, load_module_pyc, binary_type

class CommandError(Exception):
    pass

def _safe_int(value):
    try:
        return int(value)
    except:
        return value
_vers = tuple([_safe_int(x) for x in re.findall(r'(\d+|[abc]\d)', __version__)])
sqla_07 = _vers > (0, 7, 2)
sqla_08 = _vers >= (0, 8, 0, 'b2')
sqla_09 = _vers >= (0, 9, 0)
sqla_092 = _vers >= (0, 9, 2)
sqla_094 = _vers >= (0, 9, 4)
if not sqla_07:
    raise CommandError(
            "SQLAlchemy 0.7.3 or greater is required. ")

from sqlalchemy.util import format_argspec_plus, update_wrapper
from sqlalchemy.util.compat import inspect_getfullargspec


try:
    import fcntl
    import termios
    import struct
    ioctl = fcntl.ioctl(0, termios.TIOCGWINSZ,
                           struct.pack('HHHH', 0, 0, 0, 0))
    _h, TERMWIDTH, _hp, _wp = struct.unpack('HHHH', ioctl)
    if TERMWIDTH <= 0:  # can occur if running in emacs pseudo-tty
        TERMWIDTH = None
except (ImportError, IOError):
    TERMWIDTH = None


def template_to_file(template_file, dest, **kw):
    with open(dest, 'w') as f:
        f.write(
            Template(filename=template_file).render(**kw)
        )

def create_module_class_proxy(cls, globals_, locals_):
    """Create module level proxy functions for the
    methods on a given class.

    The functions will have a compatible signature
    as the methods.   A proxy is established
    using the ``_install_proxy(obj)`` function,
    and removed using ``_remove_proxy()``, both
    installed by calling this function.

    """
    attr_names = set()

    def _install_proxy(obj):
        globals_['_proxy'] = obj
        for name in attr_names:
            globals_[name] = getattr(obj, name)

    def _remove_proxy():
        globals_['_proxy'] = None
        for name in attr_names:
            del globals_[name]

    globals_['_install_proxy'] = _install_proxy
    globals_['_remove_proxy'] = _remove_proxy

    def _create_op_proxy(name):
        fn = getattr(cls, name)
        spec = inspect.getargspec(fn)
        if spec[0] and spec[0][0] == 'self':
            spec[0].pop(0)
        args = inspect.formatargspec(*spec)
        num_defaults = 0
        if spec[3]:
            num_defaults += len(spec[3])
        name_args = spec[0]
        if num_defaults:
            defaulted_vals = name_args[0 - num_defaults:]
        else:
            defaulted_vals = ()

        apply_kw = inspect.formatargspec(
                                name_args, spec[1], spec[2],
                                defaulted_vals,
                                formatvalue=lambda x: '=' + x)

        def _name_error(name):
            raise NameError(
                    "Can't invoke function '%s', as the proxy object has "\
                    "not yet been "
                    "established for the Alembic '%s' class.  "
                    "Try placing this code inside a callable." % (
                        name, cls.__name__
                    ))
        globals_['_name_error'] = _name_error

        func_text = textwrap.dedent("""\
        def %(name)s(%(args)s):
            %(doc)r
            try:
                p = _proxy
            except NameError:
                _name_error('%(name)s')
            return _proxy.%(name)s(%(apply_kw)s)
            e
        """ % {
            'name': name,
            'args': args[1:-1],
            'apply_kw': apply_kw[1:-1],
            'doc': fn.__doc__,
        })
        lcl = {}
        exec_(func_text, globals_, lcl)
        return lcl[name]

    for methname in dir(cls):
        if not methname.startswith('_'):
            if callable(getattr(cls, methname)):
                locals_[methname] = _create_op_proxy(methname)
            else:
                attr_names.add(methname)

def write_outstream(stream, *text):
    encoding = getattr(stream, 'encoding', 'ascii') or 'ascii'
    for t in text:
        if not isinstance(t, binary_type):
            t = t.encode(encoding, 'replace')
        t = t.decode(encoding)
        try:
            stream.write(t)
        except IOError:
            # suppress "broken pipe" errors.
            # no known way to handle this on Python 3 however
            # as the exception is "ignored" (noisily) in TextIOWrapper.
            break

def coerce_resource_to_filename(fname):
    """Interpret a filename as either a filesystem location or as a package resource.

    Names that are non absolute paths and contain a colon
    are interpreted as resources and coerced to a file location.

    """
    if not os.path.isabs(fname) and ":" in fname:
        import pkg_resources
        fname = pkg_resources.resource_filename(*fname.split(':'))
    return fname

def status(_statmsg, fn, *arg, **kw):
    msg(_statmsg + " ...", False)
    try:
        ret = fn(*arg, **kw)
        write_outstream(sys.stdout, " done\n")
        return ret
    except:
        write_outstream(sys.stdout, " FAILED\n")
        raise

def err(message):
    msg(message)
    sys.exit(-1)

def obfuscate_url_pw(u):
    u = url.make_url(u)
    if u.password:
        u.password = 'XXXXX'
    return str(u)

def asbool(value):
    return value is not None and \
        value.lower() == 'true'

def warn(msg):
    warnings.warn(msg)

def msg(msg, newline=True):
    if TERMWIDTH is None:
        write_outstream(sys.stdout, msg)
        if newline:
            write_outstream(sys.stdout, "\n")
    else:
        # left indent output lines
        lines = textwrap.wrap(msg, TERMWIDTH)
        if len(lines) > 1:
            for line in lines[0:-1]:
                write_outstream(sys.stdout, "  ", line, "\n")
        write_outstream(sys.stdout, "  ", lines[-1], ("\n" if newline else ""))

def load_python_file(dir_, filename):
    """Load a file from the given path as a Python module."""

    module_id = re.sub(r'\W', "_", filename)
    path = os.path.join(dir_, filename)
    _, ext = os.path.splitext(filename)
    if ext == ".py":
        if os.path.exists(path):
            module = load_module_py(module_id, path)
        elif os.path.exists(simple_pyc_file_from_path(path)):
            # look for sourceless load
            module = load_module_pyc(module_id, simple_pyc_file_from_path(path))
        else:
            raise ImportError("Can't find Python file %s" % path)
    elif ext in (".pyc", ".pyo"):
        module = load_module_pyc(module_id, path)
    del sys.modules[module_id]
    return module

def simple_pyc_file_from_path(path):
    """Given a python source path, return the so-called
    "sourceless" .pyc or .pyo path.

    This just a .pyc or .pyo file where the .py file would be.

    Even with PEP-3147, which normally puts .pyc/.pyo files in __pycache__,
    this use case remains supported as a so-called "sourceless module import".

    """
    if sys.flags.optimize:
        return path + "o"  # e.g. .pyo
    else:
        return path + "c"  # e.g. .pyc

def pyc_file_from_path(path):
    """Given a python source path, locate the .pyc.

    See http://www.python.org/dev/peps/pep-3147/
                        #detecting-pep-3147-availability
        http://www.python.org/dev/peps/pep-3147/#file-extension-checks

    """
    import imp
    has3147 = hasattr(imp, 'get_tag')
    if has3147:
        return imp.cache_from_source(path)
    else:
        return simple_pyc_file_from_path(path)

def rev_id():
    val = int(uuid.uuid4()) % 100000000000000
    return hex(val)[2:-1]

class memoized_property(object):
    """A read-only @property that is only evaluated once."""

    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result


class immutabledict(dict):

    def _immutable(self, *arg, **kw):
        raise TypeError("%s object is immutable" % self.__class__.__name__)

    __delitem__ = __setitem__ = __setattr__ = \
    clear = pop = popitem = setdefault = \
        update = _immutable

    def __new__(cls, *args):
        new = dict.__new__(cls)
        dict.__init__(new, *args)
        return new

    def __init__(self, *args):
        pass

    def __reduce__(self):
        return immutabledict, (dict(self), )

    def union(self, d):
        if not self:
            return immutabledict(d)
        else:
            d2 = immutabledict(self)
            dict.update(d2, d)
            return d2

    def __repr__(self):
        return "immutabledict(%s)" % dict.__repr__(self)


def _with_legacy_names(translations):
    def decorate(fn):

        spec = inspect_getfullargspec(fn)
        metadata = dict(target='target', fn='fn')
        metadata.update(format_argspec_plus(spec, grouped=False))

        has_keywords = bool(spec[2])

        if not has_keywords:
            metadata['args'] += ", **kw"
            metadata['apply_kw'] += ", **kw"

        def go(*arg, **kw):
            names = set(kw).difference(spec[0])
            for oldname, newname in translations:
                if oldname in kw:
                    kw[newname] = kw.pop(oldname)
                    names.discard(oldname)

                    warnings.warn(
                        "Argument '%s' is now named '%s' for function '%s'" %
                        (oldname, newname, fn.__name__))
            if not has_keywords and names:
                raise TypeError("Unknown arguments: %s" % ", ".join(names))
            return fn(*arg, **kw)

        code = 'lambda %(args)s: %(target)s(%(apply_kw)s)' % (
                metadata)
        decorated = eval(code, {"target": go})
        decorated.__defaults__ = getattr(fn, '__func__', fn).__defaults__
        update_wrapper(decorated, fn)
        if hasattr(decorated, '__wrapped__'):
            # update_wrapper in py3k applies __wrapped__, which causes
            # inspect.getargspec() to ignore the extra arguments on our
            # wrapper as of Python 3.4.  We need this for the
            # "module class proxy" thing though, so just del the __wrapped__
            # for now. See #175 as well as bugs.python.org/issue17482
            del decorated.__wrapped__
        return decorated

    return decorate




########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Alembic documentation build configuration file, created by
# sphinx-quickstart on Sat May  1 12:47:55 2010.
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

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('.'))

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.insert(0, os.path.abspath('../../'))

import alembic

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
                'changelog', 'sphinx_paramlinks']

# tags to sort on inside of sections
changelog_sections = ["feature", "bug", "moved", "changed", "removed"]

changelog_render_ticket = "https://bitbucket.org/zzzeek/alembic/issue/%s/"
changelog_render_pullreq = "https://bitbucket.org/zzzeek/alembic/pull-request/%s"

changelog_render_pullreq = {
    "bitbucket": "https://bitbucket.org/zzzeek/alembic/pull-request/%s",
    "default": "https://bitbucket.org/zzzeek/alembic/pull-request/%s",
    "github": "https://github.com/zzzeek/alembic/pull/%s",
}


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

nitpicky = True

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Alembic'
copyright = u'2010-2014, Mike Bayer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = alembic.__version__
# The full version, including alpha/beta/rc tags.
release = alembic.__version__


# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'nature'

html_style = "nature_override.css"

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Alembicdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Alembic.tex', u'Alembic Documentation',
   u'Mike Bayer', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


#{'python': ('http://docs.python.org/3.2', None)}

autoclass_content = "both"

intersphinx_mapping = {
    'sqla':('http://www.sqlalchemy.org/docs/', None),
}

########NEW FILE########
__FILENAME__ = test_autogenerate
import re
import sys
from unittest import TestCase
from . import Mock

from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, CHAR, ForeignKey, DATETIME, INTEGER, \
    TypeDecorator, CheckConstraint, Unicode, Enum,\
    UniqueConstraint, Boolean, ForeignKeyConstraint,\
    PrimaryKeyConstraint, Index, func
from sqlalchemy.types import NULLTYPE
from sqlalchemy.engine.reflection import Inspector

from alembic import autogenerate
from alembic.migration import MigrationContext
from . import staging_env, sqlite_db, clear_staging_env, eq_, \
        db_for_dialect

py3k = sys.version_info >= (3, )

names_in_this_test = set()
def _default_include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in names_in_this_test
    else:
        return True

_default_object_filters = [
    _default_include_object
]
from sqlalchemy import event
@event.listens_for(Table, "after_parent_attach")
def new_table(table, parent):
    names_in_this_test.add(table.name)

class AutogenTest(object):
    @classmethod
    def _get_bind(cls):
        return sqlite_db()

    @classmethod
    def setup_class(cls):
        staging_env()
        cls.bind = cls._get_bind()
        cls.m1 = cls._get_db_schema()
        cls.m1.create_all(cls.bind)
        cls.m2 = cls._get_model_schema()

        conn = cls.bind.connect()
        cls.context = context = MigrationContext.configure(
            connection=conn,
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': cls.m2,
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )

        connection = context.bind
        cls.autogen_context = {
            'imports': set(),
            'connection': connection,
            'dialect': connection.dialect,
            'context': context
            }

    @classmethod
    def teardown_class(cls):
        cls.m1.drop_all(cls.bind)
        clear_staging_env()

class AutogenFixtureTest(object):
    def _fixture(self, m1, m2, include_schemas=False):
        self.metadata, model_metadata = m1, m2
        self.metadata.create_all(self.bind)

        with self.bind.connect() as conn:
            self.context = context = MigrationContext.configure(
                connection=conn,
                opts={
                    'compare_type': True,
                    'compare_server_default': True,
                    'target_metadata': model_metadata,
                    'upgrade_token': "upgrades",
                    'downgrade_token': "downgrades",
                    'alembic_module_prefix': 'op.',
                    'sqlalchemy_module_prefix': 'sa.',
                }
            )

            connection = context.bind
            autogen_context = {
                'imports': set(),
                'connection': connection,
                'dialect': connection.dialect,
                'context': context
                }
            diffs = []
            autogenerate._produce_net_changes(connection, model_metadata, diffs,
                                              autogen_context,
                                              object_filters=_default_object_filters,
                                              include_schemas=include_schemas
                                        )
            return diffs

    reports_unnamed_constraints = False

    def setUp(self):
        staging_env()
        self.bind = self._get_bind()

    def tearDown(self):
        if hasattr(self, 'metadata'):
            self.metadata.drop_all(self.bind)
        clear_staging_env()

    @classmethod
    def _get_bind(cls):
        return sqlite_db()


class AutogenCrossSchemaTest(AutogenTest, TestCase):
    @classmethod
    def _get_bind(cls):
        cls.test_schema_name = "test_schema"
        return db_for_dialect('postgresql')

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()
        Table('t1', m,
                Column('x', Integer)
            )
        Table('t2', m,
                Column('y', Integer),
                schema=cls.test_schema_name
            )
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        Table('t3', m,
                Column('q', Integer)
            )
        Table('t4', m,
                Column('z', Integer),
                schema=cls.test_schema_name
            )
        return m

    def test_default_schema_omitted_upgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t3"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, None)

    def test_alt_schema_included_upgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t4"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, self.test_schema_name)

    def test_default_schema_omitted_downgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t1"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, None)

    def test_alt_schema_included_downgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t2"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, self.test_schema_name)


class AutogenDefaultSchemaTest(AutogenFixtureTest, TestCase):
    @classmethod
    def _get_bind(cls):
        cls.test_schema_name = "test_schema"
        return db_for_dialect('postgresql')

    def test_uses_explcit_schema_in_default_one(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table('a', m1, Column('x', String(50)))
        Table('a', m2, Column('x', String(50)), schema=default_schema)

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_uses_explcit_schema_in_default_two(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table('a', m1, Column('x', String(50)))
        Table('a', m2, Column('x', String(50)), schema=default_schema)
        Table('a', m2, Column('y', String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, "test_schema")
        eq_(diffs[0][1].c.keys(), ['y'])

    def test_uses_explcit_schema_in_default_three(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table('a', m1, Column('y', String(50)), schema="test_schema")

        Table('a', m2, Column('x', String(50)), schema=default_schema)
        Table('a', m2, Column('y', String(50)), schema="test_schema")


        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, default_schema)
        eq_(diffs[0][1].c.keys(), ['x'])


class ModelOne(object):
    schema = None

    @classmethod
    def _get_db_schema(cls):
        schema = cls.schema

        m = MetaData(schema=schema)

        Table('user', m,
            Column('id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('a1', Text),
            Column("pw", String(50))
        )

        Table('address', m,
            Column('id', Integer, primary_key=True),
            Column('email_address', String(100), nullable=False),
        )

        Table('order', m,
            Column('order_id', Integer, primary_key=True),
            Column("amount", Numeric(8, 2), nullable=False,
                    server_default="0"),
            CheckConstraint('amount >= 0', name='ck_order_amount')
        )

        Table('extra', m,
            Column("x", CHAR),
            Column('uid', Integer, ForeignKey('user.id'))
        )

        return m

    @classmethod
    def _get_model_schema(cls):
        schema = cls.schema

        m = MetaData(schema=schema)

        Table('user', m,
            Column('id', Integer, primary_key=True),
            Column('name', String(50), nullable=False),
            Column('a1', Text, server_default="x")
        )

        Table('address', m,
            Column('id', Integer, primary_key=True),
            Column('email_address', String(100), nullable=False),
            Column('street', String(50)),
        )

        Table('order', m,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True,
                        server_default="0"),
            Column('user_id', Integer, ForeignKey('user.id')),
            CheckConstraint('amount > -1', name='ck_order_amount'),
        )

        Table('item', m,
            Column('id', Integer, primary_key=True),
            Column('description', String(100)),
            Column('order_id', Integer, ForeignKey('order.order_id')),
            CheckConstraint('len(description) > 5')
        )
        return m



class AutogenerateDiffTest(ModelOne, AutogenTest, TestCase):

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2
        connection = self.context.bind
        diffs = []
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=_default_object_filters,
                                    )

        eq_(
            diffs[0],
            ('add_table', metadata.tables['item'])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], None)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['address'].c.street)

        eq_(diffs[3][0], "add_column")
        eq_(diffs[3][1], None)
        eq_(diffs[3][2], "order")
        eq_(diffs[3][3], metadata.tables['order'].c.user_id)

        eq_(diffs[4][0][0], "modify_type")
        eq_(diffs[4][0][1], None)
        eq_(diffs[4][0][2], "order")
        eq_(diffs[4][0][3], "amount")
        eq_(repr(diffs[4][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[4][0][6]), "Numeric(precision=10, scale=2)")

        eq_(diffs[5][0], 'remove_column')
        eq_(diffs[5][3].name, 'pw')

        eq_(diffs[6][0][0], "modify_default")
        eq_(diffs[6][0][1], None)
        eq_(diffs[6][0][2], "user")
        eq_(diffs[6][0][3], "a1")
        eq_(diffs[6][0][6].arg, "x")

        eq_(diffs[7][0][0], 'modify_nullable')
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)


    def test_render_nothing(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m1,
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set())

        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")
        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")

    def test_render_diffs_standard(self):
        """test a full render including indentation"""

        template_args = {}
        autogenerate._produce_migration_diffs(self.context, template_args, set())

        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.create_table('item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=100), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.CheckConstraint('len(description) > 5'),
    sa.ForeignKeyConstraint(['order_id'], ['order.order_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('extra')
    op.add_column('address', sa.Column('street', sa.String(length=50), nullable=True))
    op.add_column('order', sa.Column('user_id', sa.Integer(), nullable=True))
    op.alter_column('order', 'amount',
               existing_type=sa.NUMERIC(precision=8, scale=2),
               type_=sa.Numeric(precision=10, scale=2),
               nullable=True,
               existing_server_default='0')
    op.drop_column('user', 'pw')
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default='x',
               existing_nullable=True)
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    ### end Alembic commands ###""")

        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default=None,
               existing_nullable=True)
    op.add_column('user', sa.Column('pw', sa.VARCHAR(length=50), nullable=True))
    op.alter_column('order', 'amount',
               existing_type=sa.Numeric(precision=10, scale=2),
               type_=sa.NUMERIC(precision=8, scale=2),
               nullable=False,
               existing_server_default='0')
    op.drop_column('order', 'user_id')
    op.drop_column('address', 'street')
    op.create_table('extra',
    sa.Column('x', sa.CHAR(), nullable=True),
    sa.Column('uid', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['user.id'], )
    )
    op.drop_table('item')
    ### end Alembic commands ###""")

    def test_include_symbol(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m2,
                'include_symbol': lambda name, schema=None:
                                    name in ('address', 'order'),
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set())
        template_args['upgrades'] = template_args['upgrades'].replace("u'", "'")
        template_args['downgrades'] = template_args['downgrades'].\
                                        replace("u'", "'")
        assert "alter_column('user'" not in template_args['upgrades']
        assert "alter_column('user'" not in template_args['downgrades']
        assert "alter_column('order'" in template_args['upgrades']
        assert "alter_column('order'" in template_args['downgrades']

    def test_include_object(self):
        def include_object(obj, name, type_, reflected, compare_to):
            assert obj.name == name
            if type_ == "table":
                if reflected:
                    assert obj.metadata is not self.m2
                else:
                    assert obj.metadata is self.m2
                return name in ("address", "order", "user")
            elif type_ == "column":
                if reflected:
                    assert obj.table.metadata is not self.m2
                else:
                    assert obj.table.metadata is self.m2
                return name != "street"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m2,
                'include_object': include_object,
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set())

        template_args['upgrades'] = template_args['upgrades'].replace("u'", "'")
        template_args['downgrades'] = template_args['downgrades'].\
                                        replace("u'", "'")
        assert "op.create_table('item'" not in template_args['upgrades']
        assert "op.create_table('item'" not in template_args['downgrades']

        assert "alter_column('user'" in template_args['upgrades']
        assert "alter_column('user'" in template_args['downgrades']
        assert "'street'" not in template_args['upgrades']
        assert "'street'" not in template_args['downgrades']
        assert "alter_column('order'" in template_args['upgrades']
        assert "alter_column('order'" in template_args['downgrades']

    def test_skip_null_type_comparison_reflected(self):
        diff = []
        autogenerate.compare._compare_type(None, "sometable", "somecol",
            Column("somecol", NULLTYPE),
            Column("somecol", Integer()),
            diff, self.autogen_context
        )
        assert not diff

    def test_skip_null_type_comparison_local(self):
        diff = []
        autogenerate.compare._compare_type(None, "sometable", "somecol",
            Column("somecol", Integer()),
            Column("somecol", NULLTYPE),
            diff, self.autogen_context
        )
        assert not diff

    def test_affinity_typedec(self):
        class MyType(TypeDecorator):
            impl = CHAR

            def load_dialect_impl(self, dialect):
                if dialect.name == 'sqlite':
                    return dialect.type_descriptor(Integer())
                else:
                    return dialect.type_descriptor(CHAR(32))

        diff = []
        autogenerate.compare._compare_type(None, "sometable", "somecol",
            Column("somecol", Integer, nullable=True),
            Column("somecol", MyType()),
            diff, self.autogen_context
        )
        assert not diff

    def test_dont_barf_on_already_reflected(self):
        diffs = []
        from sqlalchemy.util import OrderedSet
        inspector = Inspector.from_engine(self.bind)
        autogenerate.compare._compare_tables(
            OrderedSet([(None, 'extra'), (None, 'user')]),
            OrderedSet(), [], inspector,
                MetaData(), diffs, self.autogen_context
        )
        eq_(
            [(rec[0], rec[1].name) for rec in diffs],
            [('remove_table', 'extra'), ('remove_table', 'user')]
        )

class AutogenerateDiffTestWSchema(ModelOne, AutogenTest, TestCase):
    schema = "test_schema"


    @classmethod
    def _get_bind(cls):
        return db_for_dialect('postgresql')

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2
        connection = self.context.bind
        diffs = []
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=_default_object_filters,
                                          include_schemas=True
                                          )

        eq_(
            diffs[0],
            ('add_table', metadata.tables['%s.item' % self.schema])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], self.schema)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['%s.address' % self.schema].c.street)

        eq_(diffs[3][0], "add_column")
        eq_(diffs[3][1], self.schema)
        eq_(diffs[3][2], "order")
        eq_(diffs[3][3], metadata.tables['%s.order' % self.schema].c.user_id)

        eq_(diffs[4][0][0], "modify_type")
        eq_(diffs[4][0][1], self.schema)
        eq_(diffs[4][0][2], "order")
        eq_(diffs[4][0][3], "amount")
        eq_(repr(diffs[4][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[4][0][6]), "Numeric(precision=10, scale=2)")

        eq_(diffs[5][0], 'remove_column')
        eq_(diffs[5][3].name, 'pw')

        eq_(diffs[6][0][0], "modify_default")
        eq_(diffs[6][0][1], self.schema)
        eq_(diffs[6][0][2], "user")
        eq_(diffs[6][0][3], "a1")
        eq_(diffs[6][0][6].arg, "x")

        eq_(diffs[7][0][0], 'modify_nullable')
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)

    def test_render_nothing(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m1,
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set(),
                include_symbol=lambda name, schema: False
            )
        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")
        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")

    def test_render_diffs_extras(self):
        """test a full render including indentation (include and schema)"""

        template_args = {}
        autogenerate._produce_migration_diffs(
                        self.context, template_args, set(),
                        include_object=_default_include_object,
                        include_schemas=True
                        )

        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.create_table('item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=100), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.CheckConstraint('len(description) > 5'),
    sa.ForeignKeyConstraint(['order_id'], ['%(schema)s.order.order_id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='%(schema)s'
    )
    op.drop_table('extra', schema='%(schema)s')
    op.add_column('address', sa.Column('street', sa.String(length=50), nullable=True), schema='%(schema)s')
    op.add_column('order', sa.Column('user_id', sa.Integer(), nullable=True), schema='%(schema)s')
    op.alter_column('order', 'amount',
               existing_type=sa.NUMERIC(precision=8, scale=2),
               type_=sa.Numeric(precision=10, scale=2),
               nullable=True,
               existing_server_default='0::numeric',
               schema='%(schema)s')
    op.drop_column('user', 'pw', schema='%(schema)s')
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default='x',
               existing_nullable=True,
               schema='%(schema)s')
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=False,
               schema='%(schema)s')
    ### end Alembic commands ###""" % {"schema": self.schema})

        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=True,
               schema='%(schema)s')
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default=None,
               existing_nullable=True,
               schema='%(schema)s')
    op.add_column('user', sa.Column('pw', sa.VARCHAR(length=50), autoincrement=False, nullable=True), schema='%(schema)s')
    op.alter_column('order', 'amount',
               existing_type=sa.Numeric(precision=10, scale=2),
               type_=sa.NUMERIC(precision=8, scale=2),
               nullable=False,
               existing_server_default='0::numeric',
               schema='%(schema)s')
    op.drop_column('order', 'user_id', schema='%(schema)s')
    op.drop_column('address', 'street', schema='%(schema)s')
    op.create_table('extra',
    sa.Column('x', sa.CHAR(length=1), autoincrement=False, nullable=True),
    sa.Column('uid', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['%(schema)s.user.id'], name='extra_uid_fkey'),
    schema='%(schema)s'
    )
    op.drop_table('item', schema='%(schema)s')
    ### end Alembic commands ###""" % {"schema": self.schema})





class AutogenerateCustomCompareTypeTest(AutogenTest, TestCase):
    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table('sometable', m,
              Column('id', Integer, primary_key=True),
              Column('value', Integer))
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        Table('sometable', m,
              Column('id', Integer, primary_key=True),
              Column('value', String))
        return m

    def test_uses_custom_compare_type_function(self):
        my_compare_type = Mock()
        self.context._user_compare_type = my_compare_type

        diffs = []
        autogenerate._produce_net_changes(self.context.bind, self.m2,
                                    diffs, self.autogen_context)

        first_table = self.m2.tables['sometable']
        first_column = first_table.columns['id']

        eq_(len(my_compare_type.mock_calls), 2)

        # We'll just test the first call
        _, args, _ = my_compare_type.mock_calls[0]
        context, inspected_column, metadata_column, inspected_type, metadata_type = args
        eq_(context, self.context)
        eq_(metadata_column, first_column)
        eq_(metadata_type, first_column.type)
        eq_(inspected_column.name, first_column.name)
        eq_(type(inspected_type), INTEGER)

    def test_column_type_not_modified_when_custom_compare_type_returns_False(self):
        my_compare_type = Mock()
        my_compare_type.return_value = False
        self.context._user_compare_type = my_compare_type

        diffs = []
        autogenerate._produce_net_changes(self.context.bind, self.m2,
                                                diffs, self.autogen_context)

        eq_(diffs, [])

    def test_column_type_modified_when_custom_compare_type_returns_True(self):
        my_compare_type = Mock()
        my_compare_type.return_value = True
        self.context._user_compare_type = my_compare_type

        diffs = []
        autogenerate._produce_net_changes(self.context.bind, self.m2,
                                                diffs, self.autogen_context)

        eq_(diffs[0][0][0], 'modify_type')
        eq_(diffs[1][0][0], 'modify_type')


class AutogenKeyTest(AutogenTest, TestCase):
    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table('someothertable', m,
            Column('id', Integer, primary_key=True),
            Column('value', Integer, key="somekey"),
        )
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        Table('sometable', m,
            Column('id', Integer, primary_key=True),
            Column('value', Integer, key="someotherkey"),
        )
        Table('someothertable', m,
            Column('id', Integer, primary_key=True),
            Column('value', Integer, key="somekey"),
            Column("othervalue", Integer, key="otherkey")
        )
        return m

    symbols = ['someothertable', 'sometable']
    def test_autogen(self):
        metadata = self.m2
        connection = self.context.bind

        diffs = []

        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          include_schemas=False
                                          )
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].name, "sometable")
        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][3].key, "otherkey")

class AutogenerateDiffOrderTest(AutogenTest, TestCase):
    @classmethod
    def _get_db_schema(cls):
        return MetaData()

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        Table('parent', m,
            Column('id', Integer, primary_key=True)
        )

        Table('child', m,
            Column('parent_id', Integer, ForeignKey('parent.id')),
        )

        return m

    def test_diffs_order(self):
        """
        Added in order to test that child tables(tables with FKs) are generated
        before their parent tables
        """

        metadata = self.m2
        connection = self.context.bind
        diffs = []

        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context
                                          )

        eq_(diffs[0][0], 'add_table')
        eq_(diffs[0][1].name, "parent")
        eq_(diffs[1][0], 'add_table')
        eq_(diffs[1][1].name, "child")


class CompareMetadataTest(ModelOne, AutogenTest, TestCase):
    def test_compare_metadata(self):
        metadata = self.m2

        diffs = autogenerate.compare_metadata(self.context, metadata)

        eq_(
            diffs[0],
            ('add_table', metadata.tables['item'])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], None)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['address'].c.street)

        eq_(diffs[3][0], "add_column")
        eq_(diffs[3][1], None)
        eq_(diffs[3][2], "order")
        eq_(diffs[3][3], metadata.tables['order'].c.user_id)

        eq_(diffs[4][0][0], "modify_type")
        eq_(diffs[4][0][1], None)
        eq_(diffs[4][0][2], "order")
        eq_(diffs[4][0][3], "amount")
        eq_(repr(diffs[4][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[4][0][6]), "Numeric(precision=10, scale=2)")

        eq_(diffs[5][0], 'remove_column')
        eq_(diffs[5][3].name, 'pw')

        eq_(diffs[6][0][0], "modify_default")
        eq_(diffs[6][0][1], None)
        eq_(diffs[6][0][2], "user")
        eq_(diffs[6][0][3], "a1")
        eq_(diffs[6][0][6].arg, "x")

        eq_(diffs[7][0][0], 'modify_nullable')
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)

    def test_compare_metadata_include_object(self):
        metadata = self.m2

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name in ("extra", "order")
            elif type_ == "column":
                return name != "amount"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'include_object': include_object,
            }
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(diffs[0][0], 'remove_table')
        eq_(diffs[0][1].name, "extra")

        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][1], None)
        eq_(diffs[1][2], "order")
        eq_(diffs[1][3], metadata.tables['order'].c.user_id)

    def test_compare_metadata_include_symbol(self):
        metadata = self.m2

        def include_symbol(table_name, schema_name):
            return table_name in ('extra', 'order')

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'include_symbol': include_symbol,
            }
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(diffs[0][0], 'remove_table')
        eq_(diffs[0][1].name, "extra")

        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][1], None)
        eq_(diffs[1][2], "order")
        eq_(diffs[1][3], metadata.tables['order'].c.user_id)

        eq_(diffs[2][0][0], "modify_type")
        eq_(diffs[2][0][1], None)
        eq_(diffs[2][0][2], "order")
        eq_(diffs[2][0][3], "amount")
        eq_(repr(diffs[2][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[2][0][6]), "Numeric(precision=10, scale=2)")

        eq_(diffs[2][1][0], 'modify_nullable')
        eq_(diffs[2][1][2], 'order')
        eq_(diffs[2][1][5], False)
        eq_(diffs[2][1][6], True)

class PGCompareMetaData(ModelOne, AutogenTest, TestCase):
    schema = "test_schema"

    @classmethod
    def _get_bind(cls):
        return db_for_dialect('postgresql')

    def test_compare_metadata_schema(self):
        metadata = self.m2

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                "include_schemas": True
            }
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(
            diffs[0],
            ('add_table', metadata.tables['test_schema.item'])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], "test_schema")
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['test_schema.address'].c.street)

        eq_(diffs[3][0], "add_column")
        eq_(diffs[3][1], "test_schema")
        eq_(diffs[3][2], "order")
        eq_(diffs[3][3], metadata.tables['test_schema.order'].c.user_id)

        eq_(diffs[4][0][0], 'modify_nullable')
        eq_(diffs[4][0][5], False)
        eq_(diffs[4][0][6], True)


########NEW FILE########
__FILENAME__ = test_autogen_indexes
import sys
from unittest import TestCase

from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, DATETIME, INTEGER, \
    TypeDecorator, Unicode, Enum,\
    UniqueConstraint, Boolean, \
    PrimaryKeyConstraint, Index, func, ForeignKeyConstraint

from . import sqlite_db, eq_, db_for_dialect

py3k = sys.version_info >= (3, )

from .test_autogenerate import AutogenFixtureTest

class AutogenerateUniqueIndexTest(AutogenFixtureTest, TestCase):
    reports_unique_constraints = True

    def test_index_flag_becomes_named_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('user', m1,
            Column('id', Integer, primary_key=True),
            Column('name', String(50), nullable=False, index=True),
            Column('a1', String(10), server_default="x")
        )

        Table('user', m2,
            Column('id', Integer, primary_key=True),
            Column('name', String(50), nullable=False),
            Column('a1', String(10), server_default="x"),
            UniqueConstraint("name", name="uq_user_name")
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "add_constraint")
            eq_(diffs[0][1].name, "uq_user_name")

            eq_(diffs[1][0], "remove_index")
            eq_(diffs[1][1].name, "ix_user_name")
        else:
            eq_(diffs[0][0], "remove_index")
            eq_(diffs[0][1].name, "ix_user_name")


    def test_add_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('address', m1,
            Column('id', Integer, primary_key=True),
            Column('email_address', String(100), nullable=False),
            Column('qpr', String(10), index=True),
        )
        Table('address', m2,
            Column('id', Integer, primary_key=True),
            Column('email_address', String(100), nullable=False),
            Column('qpr', String(10), index=True),
            UniqueConstraint("email_address", name="uq_email_address")
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "add_constraint")
            eq_(diffs[0][1].name, "uq_email_address")
        else:
            eq_(diffs, [])


    def test_index_becomes_unique(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            UniqueConstraint('order_id', 'user_id',
                name='order_order_id_user_id_unique'
            ),
            Index('order_user_id_amount_idx', 'user_id', 'amount')
        )

        Table('order', m2,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            UniqueConstraint('order_id', 'user_id',
                name='order_order_id_user_id_unique'
            ),
            Index('order_user_id_amount_idx', 'user_id', 'amount', unique=True),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], "remove_index")
        eq_(diffs[0][1].name, "order_user_id_amount_idx")
        eq_(diffs[0][1].unique, False)

        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].name, "order_user_id_amount_idx")
        eq_(diffs[1][1].unique, True)



    def test_mismatch_db_named_col_flag(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('item', m1,
                Column('x', Integer),
                UniqueConstraint('x', name="db_generated_name")
            )

        # test mismatch between unique=True and
        # named uq constraint
        Table('item', m2,
                Column('x', Integer, unique=True)
            )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_new_table_added(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('extra', m2,
                Column('foo', Integer, index=True),
                Column('bar', Integer),
                Index('newtable_idx', 'bar')
            )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")

        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].name, "ix_extra_foo")

        eq_(diffs[2][0], "add_index")
        eq_(diffs[2][1].name, "newtable_idx")


    def test_named_cols_changed(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('col_change', m1,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x', name="nochange")
            )
        Table('col_change', m2,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x', 'y', name="nochange")
            )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "remove_constraint")
            eq_(diffs[0][1].name, "nochange")

            eq_(diffs[1][0], "add_constraint")
            eq_(diffs[1][1].name, "nochange")
        else:
            eq_(diffs, [])

    def test_nothing_changed_one(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
            Column('x', String(20), unique=True, index=True)
            )

        Table('nothing_changed', m2,
            Column('x', String(20), unique=True, index=True)
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])


    def test_nothing_changed_two(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20), unique=True)
            )
        Table('nothing_changed_related', m1,
            Column('id1', Integer),
            Column('id2', Integer),
            ForeignKeyConstraint(['id1', 'id2'],
                    ['nothing_changed.id1', 'nothing_changed.id2'])
            )

        Table('nothing_changed', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20), unique=True)
            )
        Table('nothing_changed_related', m2,
            Column('id1', Integer),
            Column('id2', Integer),
            ForeignKeyConstraint(['id1', 'id2'],
                    ['nothing_changed.id1', 'nothing_changed.id2'])
            )


        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            Index('x', 'x')
            )

        Table('nothing_changed', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            Index('x', 'x')
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_new_idx_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('new_idx', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            )

        idx = Index('x', 'x')
        Table('new_idx', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            idx
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [('add_index', idx)])

    def test_removed_idx_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        idx = Index('x', 'x')
        Table('new_idx', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            idx
            )

        Table('new_idx', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20))
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], 'remove_index')

    def test_unnamed_cols_changed(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('col_change', m1,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x')
            )
        Table('col_change', m2,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x', 'y')
            )

        diffs = self._fixture(m1, m2)

        diffs = set((cmd,
                    ('x' in obj.name) if obj.name is not None else False)
                    for cmd, obj in diffs)
        if self.reports_unnamed_constraints:
            assert ("remove_constraint", True) in diffs
            assert ("add_constraint", False) in diffs



    def test_remove_named_unique_index(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('remove_idx', m1,
                Column('x', Integer),
                Index('xidx', 'x', unique=True)
            )
        Table('remove_idx', m2,
                Column('x', Integer),
            )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            diffs = set((cmd, obj.name) for cmd, obj in diffs)
            assert ("remove_index", "xidx") in diffs
        else:
            eq_(diffs, [])


    def test_remove_named_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('remove_idx', m1,
                Column('x', Integer),
                UniqueConstraint('x', name='xidx')
            )
        Table('remove_idx', m2,
                Column('x', Integer),
            )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            diffs = ((cmd, obj.name) for cmd, obj in diffs)
            assert ("remove_constraint", "xidx") in diffs
        else:
            eq_(diffs, [])

    def test_dont_add_uq_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('no_uq', m2, Column('x', String(50), unique=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 1)
        assert UniqueConstraint in set(type(c) for c in diffs[0][1].constraints)

    def test_add_uq_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m2, Column('x', String(50), unique=True, index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in set(type(c) for c in diffs[0][1].constraints)
        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].unique, True)

    def test_add_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m2, Column('x', String(50), index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in set(type(c) for c in diffs[0][1].constraints)
        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].unique, False)

    def test_add_idx_non_col(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m1, Column('x', String(50)))
        t2 = Table('add_ix', m2, Column('x', String(50)))
        Index('foo_idx', t2.c.x.desc())
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_index")

    def test_unchanged_idx_non_col(self):
        m1 = MetaData()
        m2 = MetaData()
        t1 = Table('add_ix', m1, Column('x', String(50)))
        Index('foo_idx', t1.c.x.desc())
        t2 = Table('add_ix', m2, Column('x', String(50)))
        Index('foo_idx', t2.c.x.desc())
        diffs = self._fixture(m1, m2)

        eq_(diffs, [])



class PGUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True

    @classmethod
    def _get_bind(cls):
        return db_for_dialect('postgresql')

    def test_idx_added_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m1, Column('x', String(50)), schema="test_schema")
        Table('add_ix', m2, Column('x', String(50)),
                Index('ix_1', 'x'), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_index")
        eq_(diffs[0][1].name, 'ix_1')

    def test_idx_unchanged_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m1, Column('x', String(50)), Index('ix_1', 'x'),
                    schema="test_schema")
        Table('add_ix', m2, Column('x', String(50)),
                Index('ix_1', 'x'), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_uq_added_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_uq', m1, Column('x', String(50)), schema="test_schema")
        Table('add_uq', m2, Column('x', String(50)),
                UniqueConstraint('x', name='ix_1'), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, 'ix_1')

    def test_uq_unchanged_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_uq', m1, Column('x', String(50)),
                    UniqueConstraint('x', name='ix_1'),
                    schema="test_schema")
        Table('add_uq', m2, Column('x', String(50)),
                    UniqueConstraint('x', name='ix_1'),
                schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_same_tname_two_schemas(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('add_ix', m1, Column('x', String(50)), Index('ix_1', 'x'))

        Table('add_ix', m2, Column('x', String(50)), Index('ix_1', 'x'))
        Table('add_ix', m2, Column('x', String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 1)


class MySQLUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True

    def test_removed_idx_index_named_as_column(self):
        # TODO: this should be an "assert fails"
        pass

    @classmethod
    def _get_bind(cls):
        return db_for_dialect('mysql')

class NoUqReflectionIndexTest(AutogenerateUniqueIndexTest):
    reports_unique_constraints = False

    @classmethod
    def _get_bind(cls):
        eng = sqlite_db()

        def unimpl(*arg, **kw):
            raise NotImplementedError()
        eng.dialect.get_unique_constraints = unimpl
        return eng

    def test_unique_not_reported(self):
        m1 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            UniqueConstraint('order_id', 'user_id',
                name='order_order_id_user_id_unique'
            )
        )

        diffs = self._fixture(m1, m1)
        eq_(diffs, [])

    def test_remove_unique_index_not_reported(self):
        m1 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            Index('oid_ix', 'order_id', 'user_id',
                unique=True
            )
        )
        m2 = MetaData()
        Table('order', m2,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_remove_plain_index_is_reported(self):
        m1 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            Index('oid_ix', 'order_id', 'user_id')
        )
        m2 = MetaData()
        Table('order', m2,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], 'remove_index')


class NoUqReportsIndAsUqTest(NoUqReflectionIndexTest):
    """this test suite simulates the condition where:

    a. the dialect doesn't report unique constraints

    b. the dialect returns unique constraints within the indexes list.

    Currently the mssql dialect does this, but here we force this
    condition so that we can test the behavior regardless of if/when
    mssql supports unique constraint reflection.

    """

    @classmethod
    def _get_bind(cls):
        eng = sqlite_db()

        _get_unique_constraints = eng.dialect.get_unique_constraints
        _get_indexes = eng.dialect.get_indexes

        def unimpl(*arg, **kw):
            raise NotImplementedError()

        def get_indexes(self, connection, tablename, **kw):
            indexes = _get_indexes(self, connection, tablename, **kw)
            for uq in _get_unique_constraints(
                            self, connection, tablename, **kw
                            ):
                uq['unique'] = True
                indexes.append(uq)
            return indexes

        eng.dialect.get_unique_constraints = unimpl
        eng.dialect.get_indexes = get_indexes
        return eng


########NEW FILE########
__FILENAME__ = test_autogen_render
import re
import sys
from unittest import TestCase

from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, CHAR, ForeignKey, DATETIME, INTEGER, \
    TypeDecorator, CheckConstraint, Unicode, Enum,\
    UniqueConstraint, Boolean, ForeignKeyConstraint,\
    PrimaryKeyConstraint, Index, func
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.sql import and_, column, literal_column

from alembic import autogenerate, util, compat
from . import eq_, eq_ignore_whitespace, requires_092, requires_09, requires_094

py3k = sys.version_info >= (3, )

class AutogenRenderTest(TestCase):
    """test individual directives"""

    @classmethod
    def setup_class(cls):
        cls.autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': mysql.dialect()
        }
        cls.pg_autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': postgresql.dialect()
        }


    def test_render_add_index(self):
        """
        autogenerate.render._add_index
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index('test_active_code_idx', 'test', "
            "['active', 'code'], unique=False)"
        )

    def test_render_add_index_schema(self):
        """
        autogenerate.render._add_index using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index('test_active_code_idx', 'test', "
            "['active', 'code'], unique=False, schema='CamelSchema')"
        )

    def test_render_add_index_pg_where(self):
        autogen_context = self.pg_autogen_context

        m = MetaData()
        t = Table('t', m,
            Column('x', String),
            Column('y', String)
            )

        idx = Index('foo_idx', t.c.x, t.c.y,
                            postgresql_where=(t.c.y == 'something'))

        if compat.sqla_08:
            eq_ignore_whitespace(
                autogenerate.render._add_index(idx, autogen_context),
                """op.create_index('foo_idx', 't', ['x', 'y'], unique=False, """
                    """postgresql_where=sa.text("t.y = 'something'"))"""
            )
        else:
            eq_ignore_whitespace(
                autogenerate.render._add_index(idx, autogen_context),
                """op.create_index('foo_idx', 't', ['x', 'y'], unique=False, """
                    """postgresql_where=sa.text('t.y = %(y_1)s'))"""
            )

    # def test_render_add_index_func(self):
    #     """
    #     autogenerate.render._drop_index using func -- TODO: SQLA needs to
    #     reflect expressions as well as columns
    #     """
    #     m = MetaData()
    #     t = Table('test', m,
    #         Column('id', Integer, primary_key=True),
    #         Column('active', Boolean()),
    #         Column('code', String(255)),
    #     )
    #     idx = Index('test_active_lower_code_idx', t.c.active, func.lower(t.c.code))
    #     eq_ignore_whitespace(
    #         autogenerate.render._add_index(idx, self.autogen_context),
    #         ""
    #     )

    def test_drop_index(self):
        """
        autogenerate.render._drop_index
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._drop_index(idx, self.autogen_context),
            "op.drop_index('test_active_code_idx', table_name='test')"
        )

    def test_drop_index_schema(self):
        """
        autogenerate.render._drop_index using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._drop_index(idx, self.autogen_context),
            "op.drop_index('test_active_code_idx', " +
                          "table_name='test', schema='CamelSchema')"
        )

    def test_add_unique_constraint(self):
        """
        autogenerate.render._add_unique_constraint
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._add_unique_constraint(uq, self.autogen_context),
            "op.create_unique_constraint('uq_test_code', 'test', ['code'])"
        )

    def test_add_unique_constraint_schema(self):
        """
        autogenerate.render._add_unique_constraint using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._add_unique_constraint(uq, self.autogen_context),
            "op.create_unique_constraint('uq_test_code', 'test', ['code'], schema='CamelSchema')"
        )

    def test_drop_constraint(self):
        """
        autogenerate.render._drop_constraint
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._drop_constraint(uq, self.autogen_context),
            "op.drop_constraint('uq_test_code', 'test')"
        )

    def test_drop_constraint_schema(self):
        """
        autogenerate.render._drop_constraint using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._drop_constraint(uq, self.autogen_context),
            "op.drop_constraint('uq_test_code', 'test', schema='CamelSchema')"
        )

    def test_render_table_upgrade(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(255)),
            Column("address_id", Integer, ForeignKey("address.id")),
            Column("timestamp", DATETIME, server_default="NOW()"),
            Column("amount", Numeric(5, 2)),
            UniqueConstraint("name", name="uq_name"),
            UniqueConstraint("timestamp"),
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('name', sa.Unicode(length=255), nullable=True),"
            "sa.Column('address_id', sa.Integer(), nullable=True),"
            "sa.Column('timestamp', sa.DATETIME(), "
                "server_default='NOW()', "
                "nullable=True),"
            "sa.Column('amount', sa.Numeric(precision=5, scale=2), nullable=True),"
            "sa.ForeignKeyConstraint(['address_id'], ['address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "sa.UniqueConstraint('name', name='uq_name'),"
            "sa.UniqueConstraint('timestamp')"
            ")"
        )

    def test_render_table_w_schema(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('address.id')),
            schema='foo'
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")"
        )

    def test_render_table_w_fk_schema(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('foo.address.id')),
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['foo.address.id'], ),"
            "sa.PrimaryKeyConstraint('id')"
            ")"
        )

    def test_render_table_w_metadata_schema(self):
        m = MetaData(schema="foo")
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('address.id')),
        )
        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._add_table(t, self.autogen_context)),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['foo.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")"
        )

    def test_render_table_w_metadata_schema_override(self):
        m = MetaData(schema="foo")
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('bar.address.id')),
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['bar.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")"
        )

    def test_render_addtl_args(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('bar.address.id')),
            sqlite_autoincrement=True, mysql_engine="InnoDB"
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['bar.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "mysql_engine='InnoDB',sqlite_autoincrement=True)"
        )

    def test_render_drop_table(self):
        eq_(
            autogenerate.render._drop_table(Table("sometable", MetaData()),
                        self.autogen_context),
            "op.drop_table('sometable')"
        )

    def test_render_drop_table_w_schema(self):
        eq_(
            autogenerate.render._drop_table(
                Table("sometable", MetaData(), schema='foo'),
                self.autogen_context),
            "op.drop_table('sometable', schema='foo')"
        )

    def test_render_table_no_implicit_check(self):
        m = MetaData()
        t = Table('test', m, Column('x', Boolean()))

        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',sa.Column('x', sa.Boolean(), nullable=True))"
        )

    def test_render_empty_pk_vs_nonempty_pk(self):
        m = MetaData()
        t1 = Table('t1', m, Column('x', Integer))
        t2 = Table('t2', m, Column('x', Integer, primary_key=True))

        eq_ignore_whitespace(
            autogenerate.render._add_table(t1, self.autogen_context),
            "op.create_table('t1',sa.Column('x', sa.Integer(), nullable=True))"
        )

        eq_ignore_whitespace(
            autogenerate.render._add_table(t2, self.autogen_context),
            "op.create_table('t2',"
            "sa.Column('x', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('x'))"
        )

    def test_render_add_column(self):
        eq_(
            autogenerate.render._add_column(
                    None, "foo", Column("x", Integer, server_default="5"),
                        self.autogen_context),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
                "server_default='5', nullable=True))"
        )

    def test_render_add_column_w_schema(self):
        eq_(
            autogenerate.render._add_column(
                    "foo", "bar", Column("x", Integer, server_default="5"),
                        self.autogen_context),
            "op.add_column('bar', sa.Column('x', sa.Integer(), "
                "server_default='5', nullable=True), schema='foo')"
        )

    def test_render_drop_column(self):
        eq_(
            autogenerate.render._drop_column(
                    None, "foo", Column("x", Integer, server_default="5"),
                        self.autogen_context),

            "op.drop_column('foo', 'x')"
        )

    def test_render_drop_column_w_schema(self):
        eq_(
            autogenerate.render._drop_column(
                    "foo", "bar", Column("x", Integer, server_default="5"),
                        self.autogen_context),

            "op.drop_column('bar', 'x', schema='foo')"
        )

    def test_render_quoted_server_default(self):
        eq_(
            autogenerate.render._render_server_default(
                "nextval('group_to_perm_group_to_perm_id_seq'::regclass)",
                    self.autogen_context),
            '"nextval(\'group_to_perm_group_to_perm_id_seq\'::regclass)"'
        )

    def test_render_col_with_server_default(self):
        c = Column('updated_at', TIMESTAMP(),
                server_default='TIMEZONE("utc", CURRENT_TIMESTAMP)',
                nullable=False)
        result = autogenerate.render._render_column(
                    c, self.autogen_context
                )
        eq_(
            result,
            'sa.Column(\'updated_at\', sa.TIMESTAMP(), '
                'server_default=\'TIMEZONE("utc", CURRENT_TIMESTAMP)\', '
                'nullable=False)'
        )

    def test_render_col_autoinc_false_mysql(self):
        c = Column('some_key', Integer, primary_key=True, autoincrement=False)
        Table('some_table', MetaData(), c)
        result = autogenerate.render._render_column(
                    c, self.autogen_context
                )
        eq_(
            result,
            'sa.Column(\'some_key\', sa.Integer(), '
                'autoincrement=False, '
                'nullable=False)'
        )

    def test_render_custom(self):

        def render(type_, obj, context):
            if type_ == "foreign_key":
                return None
            if type_ == "column":
                if obj.name == "y":
                    return None
                else:
                    return "col(%s)" % obj.name
            return "render:%s" % type_

        autogen_context = {"opts": {
            'render_item': render,
            'alembic_module_prefix': 'sa.'
        }}

        t = Table('t', MetaData(),
                Column('x', Integer),
                Column('y', Integer),
                PrimaryKeyConstraint('x'),
                ForeignKeyConstraint(['x'], ['y'])
            )
        result = autogenerate.render._add_table(
                    t, autogen_context
                )
        eq_(
            result, """sa.create_table('t',
col(x),
render:primary_key\n)"""
        )

    def test_render_modify_type(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        type_=CHAR(10), existing_type=CHAR(20)),
            "op.alter_column('sometable', 'somecolumn', "
                "existing_type=sa.CHAR(length=20), type_=sa.CHAR(length=10))"
        )

    def test_render_modify_type_w_schema(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        type_=CHAR(10), existing_type=CHAR(20),
                        schema='foo'),
            "op.alter_column('sometable', 'somecolumn', "
                "existing_type=sa.CHAR(length=20), type_=sa.CHAR(length=10), "
                "schema='foo')"
        )

    def test_render_modify_nullable(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        existing_type=Integer(),
                        nullable=True),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True)"
        )

    def test_render_modify_nullable_w_schema(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        existing_type=Integer(),
                        nullable=True, schema='foo'),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, schema='foo')"
        )

    def test_render_fk_constraint_kwarg(self):
        m = MetaData()
        t1 = Table('t', m, Column('c', Integer))
        t2 = Table('t2', m, Column('c_rem', Integer))

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], onupdate="CASCADE")
        if not util.sqla_08:
            t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], onupdate='CASCADE')"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], ondelete="CASCADE")
        if not util.sqla_08:
            t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], ondelete='CASCADE')"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], deferrable=True)
        if not util.sqla_08:
            t1.append_constraint(fk)
        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], deferrable=True)"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], initially="XYZ")
        if not util.sqla_08:
            t1.append_constraint(fk)
        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], initially='XYZ')"
        )

    def test_render_fk_constraint_use_alter(self):
        m = MetaData()
        Table('t', m, Column('c', Integer))
        t2 = Table('t2', m, Column('c_rem', Integer,
                                ForeignKey('t.c', name="fk1", use_alter=True)))
        const = list(t2.foreign_keys)[0].constraint

        eq_ignore_whitespace(
            autogenerate.render._render_constraint(const, self.autogen_context),
            "sa.ForeignKeyConstraint(['c_rem'], ['t.c'], "
                    "name='fk1', use_alter=True)"
        )

    def test_render_check_constraint_literal(self):
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint("im a constraint", name='cc1'),
                self.autogen_context
            ),
            "sa.CheckConstraint('im a constraint', name='cc1')"
        )


    def test_render_check_constraint_sqlexpr(self):
        c = column('c')
        five = literal_column('5')
        ten = literal_column('10')
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint(and_(c > five, c < ten)),
                self.autogen_context
            ),
            "sa.CheckConstraint('c > 5 AND c < 10')"
        )

    def test_render_unique_constraint_opts(self):
        m = MetaData()
        t = Table('t', m, Column('c', Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, name='uq_1', deferrable='XYZ'),
                self.autogen_context
            ),
            "sa.UniqueConstraint('c', deferrable='XYZ', name='uq_1')"
        )

    def test_render_modify_nullable_w_default(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        existing_type=Integer(),
                        existing_server_default="5",
                        nullable=True),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, "
            "existing_server_default='5')"
        )



    def test_render_enum(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                        Enum("one", "two", "three", name="myenum"),
                        self.autogen_context),
            "sa.Enum('one', 'two', 'three', name='myenum')"
        )
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                        Enum("one", "two", "three"),
                        self.autogen_context),
            "sa.Enum('one', 'two', 'three')"
        )

    def test_repr_plain_sqla_type(self):
        type_ = Integer()
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': mysql.dialect()
        }

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "sa.Integer()"
        )

    def test_repr_user_type_user_prefix_None(self):
        from sqlalchemy.types import UserDefinedType
        class MyType(UserDefinedType):
            def get_col_spec(self):
                return "MYTYPE"

        type_ = MyType()
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
                'user_module_prefix': None
            },
            'dialect': mysql.dialect()
        }

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "sa.MyType()"
        )

    def test_repr_user_type_user_prefix_present(self):
        from sqlalchemy.types import UserDefinedType
        class MyType(UserDefinedType):
            def get_col_spec(self):
                return "MYTYPE"

        type_ = MyType()
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
                'user_module_prefix': 'user.',
            },
            'dialect': mysql.dialect()
        }

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "user.MyType()"
        )

    @requires_09
    def test_repr_dialect_type(self):
        from sqlalchemy.dialects.mysql import VARCHAR

        type_ = VARCHAR(20, charset='utf8', national=True)
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
                'user_module_prefix': None,
            },
            'imports': set(),
            'dialect': mysql.dialect()
        }
        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "mysql.VARCHAR(charset='utf8', national=True, length=20)"
        )
        eq_(autogen_context['imports'],
                set(['from sqlalchemy.dialects import mysql'])
            )

class RenderNamingConventionTest(TestCase):

    @classmethod
    @requires_094
    def setup_class(cls):
        cls.autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': postgresql.dialect()
        }


    def setUp(self):

        convention = {
          "ix": 'ix_%(custom)s_%(column_0_label)s',
          "uq": "uq_%(custom)s_%(table_name)s_%(column_0_name)s",
          "ck": "ck_%(custom)s_%(table_name)s",
          "fk": "fk_%(custom)s_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
          "pk": "pk_%(custom)s_%(table_name)s",
          "custom": lambda const, table: "ct"
        }

        self.metadata = MetaData(
                            naming_convention=convention
                        )

    def test_schema_type_boolean(self):
        t = Table('t', self.metadata, Column('c', Boolean(name='xyz')))
        eq_ignore_whitespace(
            autogenerate.render._add_column(
                    None, "t", t.c.c,
                        self.autogen_context),
            "op.add_column('t', "
                "sa.Column('c', sa.Boolean(name='xyz'), nullable=True))"
        )

    def test_explicit_unique_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, deferrable='XYZ'),
                self.autogen_context
            ),
            "sa.UniqueConstraint('c', deferrable='XYZ', name=op.f('uq_ct_t_c'))"
        )

    def test_explicit_named_unique_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, name='q'),
                self.autogen_context
            ),
            "sa.UniqueConstraint('c', name='q')"
        )

    def test_render_add_index(self):
        t = Table('test', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        idx = Index(None, t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index(op.f('ix_ct_test_active'), 'test', "
            "['active', 'code'], unique=False)"
        )

    def test_render_drop_index(self):
        t = Table('test', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        idx = Index(None, t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._drop_index(idx, self.autogen_context),
            "op.drop_index(op.f('ix_ct_test_active'), table_name='test')"
        )

    def test_render_add_index_schema(self):
        t = Table('test', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        idx = Index(None, t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index(op.f('ix_ct_CamelSchema_test_active'), 'test', "
            "['active', 'code'], unique=False, schema='CamelSchema')"
        )


    def test_implicit_unique_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer, unique=True))
        uq = [c for c in t.constraints if isinstance(c, UniqueConstraint)][0]
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(uq,
                self.autogen_context
            ),
            "sa.UniqueConstraint('c', name=op.f('uq_ct_t_c'))"
        )

    def test_inline_pk_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer, primary_key=True))
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=False),"
                "sa.PrimaryKeyConstraint('c', name=op.f('pk_ct_t')))"
        )

    def test_inline_ck_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer), CheckConstraint("c > 5"))
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=True),"
                "sa.CheckConstraint('c > 5', name=op.f('ck_ct_t')))"
        )

    def test_inline_fk(self):
        t = Table('t', self.metadata, Column('c', Integer, ForeignKey('q.id')))
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=True),"
                "sa.ForeignKeyConstraint(['c'], ['q.id'], name=op.f('fk_ct_t_c_q')))"
        )

    def test_render_check_constraint_renamed(self):
        """test that constraints from autogenerate render with
        the naming convention name explicitly.  These names should
        be frozen into the migration scripts so that they remain
        the same if the application's naming convention changes.

        However, op.create_table() and others need to be careful that
        these don't double up when the "%(constraint_name)s" token is
        used.

        """
        m1 = MetaData(naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"})
        ck = CheckConstraint("im a constraint", name="cc1")
        Table('t', m1, Column('x'), ck)

        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                ck,
                self.autogen_context
            ),
            "sa.CheckConstraint('im a constraint', name=op.f('ck_t_cc1'))"
        )

########NEW FILE########
__FILENAME__ = test_bulk_insert
from unittest import TestCase

from alembic import op
from sqlalchemy import Integer, String
from sqlalchemy.sql import table, column
from sqlalchemy import Table, Column, MetaData
from sqlalchemy.types import TypeEngine

from . import op_fixture, eq_, assert_raises_message

def _table_fixture(dialect, as_sql):
    context = op_fixture(dialect, as_sql)
    t1 = table("ins_table",
                column('id', Integer),
                column('v1', String()),
                column('v2', String()),
    )
    return context, t1

def _big_t_table_fixture(dialect, as_sql):
    context = op_fixture(dialect, as_sql)
    t1 = Table("ins_table", MetaData(),
                Column('id', Integer, primary_key=True),
                Column('v1', String()),
                Column('v2', String()),
    )
    return context, t1

def _test_bulk_insert(dialect, as_sql):
    context, t1 = _table_fixture(dialect, as_sql)

    op.bulk_insert(t1, [
        {'id':1, 'v1':'row v1', 'v2':'row v5'},
        {'id':2, 'v1':'row v2', 'v2':'row v6'},
        {'id':3, 'v1':'row v3', 'v2':'row v7'},
        {'id':4, 'v1':'row v4', 'v2':'row v8'},
    ])
    return context

def _test_bulk_insert_single(dialect, as_sql):
    context, t1 = _table_fixture(dialect, as_sql)

    op.bulk_insert(t1, [
        {'id':1, 'v1':'row v1', 'v2':'row v5'},
    ])
    return context

def _test_bulk_insert_single_bigt(dialect, as_sql):
    context, t1 = _big_t_table_fixture(dialect, as_sql)

    op.bulk_insert(t1, [
        {'id':1, 'v1':'row v1', 'v2':'row v5'},
    ])
    return context

def test_bulk_insert():
    context = _test_bulk_insert('default', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (:id, :v1, :v2)'
    )

def test_bulk_insert_wrong_cols():
    context = op_fixture('postgresql')
    t1 = table("ins_table",
                column('id', Integer),
                column('v1', String()),
                column('v2', String()),
    )
    op.bulk_insert(t1, [
        {'v1':'row v1', },
    ])
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_no_rows():
    context, t1 = _table_fixture('default', False)

    op.bulk_insert(t1, [])
    context.assert_()

def test_bulk_insert_pg():
    context = _test_bulk_insert('postgresql', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_pg_single():
    context = _test_bulk_insert_single('postgresql', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_pg_single_as_sql():
    context = _test_bulk_insert_single('postgresql', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')"
    )

def test_bulk_insert_pg_single_big_t_as_sql():
    context = _test_bulk_insert_single_bigt('postgresql', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')"
    )

def test_bulk_insert_mssql():
    context = _test_bulk_insert('mssql', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (:id, :v1, :v2)'
    )

def test_bulk_insert_inline_literal_as_sql():
    context = op_fixture('postgresql', True)

    class MyType(TypeEngine):
        pass

    t1 = table('t', column('id', Integer), column('data', MyType()))

    op.bulk_insert(t1, [
        {'id': 1, 'data': op.inline_literal('d1')},
        {'id': 2, 'data': op.inline_literal('d2')},
    ])
    context.assert_(
        "INSERT INTO t (id, data) VALUES (1, 'd1')",
        "INSERT INTO t (id, data) VALUES (2, 'd2')"
    )


def test_bulk_insert_as_sql():
    context = _test_bulk_insert('default', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (2, 'row v2', 'row v6')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (3, 'row v3', 'row v7')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (4, 'row v4', 'row v8')"
    )

def test_bulk_insert_as_sql_pg():
    context = _test_bulk_insert('postgresql', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (2, 'row v2', 'row v6')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (3, 'row v3', 'row v7')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (4, 'row v4', 'row v8')"
    )

def test_bulk_insert_as_sql_mssql():
    context = _test_bulk_insert('mssql', True)
    # SQL server requires IDENTITY_INSERT
    # TODO: figure out if this is safe to enable for a table that
    # doesn't have an IDENTITY column
    context.assert_(
        'SET IDENTITY_INSERT ins_table ON',
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (2, 'row v2', 'row v6')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (3, 'row v3', 'row v7')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (4, 'row v4', 'row v8')",
        'SET IDENTITY_INSERT ins_table OFF'
    )

def test_invalid_format():
    context, t1 = _table_fixture("sqlite", False)
    assert_raises_message(
        TypeError,
        "List expected",
        op.bulk_insert, t1, {"id":5}
    )

    assert_raises_message(
        TypeError,
        "List of dictionaries expected",
        op.bulk_insert, t1, [(5, )]
    )

class RoundTripTest(TestCase):
    def setUp(self):
        from sqlalchemy import create_engine
        from alembic.migration import MigrationContext
        self.conn = create_engine("sqlite://").connect()
        self.conn.execute("""
            create table foo(
                id integer primary key,
                data varchar(50),
                x integer
            )
        """)
        context = MigrationContext.configure(self.conn)
        self.op = op.Operations(context)
        self.t1 = table('foo',
                column('id'),
                column('data'),
                column('x')
        )
    def tearDown(self):
        self.conn.close()

    def test_single_insert_round_trip(self):
        self.op.bulk_insert(self.t1,
            [{'data':"d1", "x":"x1"}]
        )

        eq_(
            self.conn.execute("select id, data, x from foo").fetchall(),
            [
                (1, "d1", "x1"),
            ]
        )

    def test_bulk_insert_round_trip(self):
        self.op.bulk_insert(self.t1, [
            {'data':"d1", "x":"x1"},
            {'data':"d2", "x":"x2"},
            {'data':"d3", "x":"x3"},
        ])

        eq_(
            self.conn.execute("select id, data, x from foo").fetchall(),
            [
                (1, "d1", "x1"),
                (2, "d2", "x2"),
                (3, "d3", "x3")
            ]
        )

    def test_bulk_insert_inline_literal(self):
        class MyType(TypeEngine):
            pass

        t1 = table('foo', column('id', Integer), column('data', MyType()))

        self.op.bulk_insert(t1, [
            {'id': 1, 'data': self.op.inline_literal('d1')},
            {'id': 2, 'data': self.op.inline_literal('d2')},
        ], multiinsert=False)

        eq_(
            self.conn.execute("select id, data from foo").fetchall(),
            [
                (1, "d1"),
                (2, "d2"),
            ]
        )


########NEW FILE########
__FILENAME__ = test_command
import unittest
from . import clear_staging_env, staging_env, \
    _sqlite_testing_config, \
    three_rev_fixture, eq_
from alembic import command
from io import TextIOWrapper, BytesIO
from alembic.script import ScriptDirectory



class StdoutCommandTest(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a, cls.b, cls.c = three_rev_fixture(cls.cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def _eq_cmd_output(self, buf, expected):
        script = ScriptDirectory.from_config(self.cfg)

        # test default encode/decode behavior as well,
        # rev B has a non-ascii char in it + a coding header.
        eq_(
            buf.getvalue().decode("ascii", 'replace').strip(),
            "\n".join([
                script.get_revision(rev).log_entry
                for rev in expected
            ]).encode("ascii", "replace").decode("ascii").strip()
        )

    def _buf_fixture(self):
        # try to simulate how sys.stdout looks - we send it u''
        # but then it's trying to encode to something.
        buf = BytesIO()
        wrapper = TextIOWrapper(buf, encoding='ascii', line_buffering=True)
        wrapper.getvalue = buf.getvalue
        return wrapper

    def test_history_full(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_num_range(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:%s" % (self.a, self.b))
        self._eq_cmd_output(buf, [self.b])

    def test_history_base_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, ":%s" % (self.b))
        self._eq_cmd_output(buf, [self.b, self.a])

    def test_history_num_to_head(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:" % (self.a))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_num_plus_relative(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:+2" % (self.a))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_relative_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "-2:%s" % (self.c))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_current_to_head_as_b(self):
        command.stamp(self.cfg, self.b)
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [self.c])

    def test_history_current_to_head_as_base(self):
        command.stamp(self.cfg, "base")
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

########NEW FILE########
__FILENAME__ = test_config
#!coding: utf-8

from alembic import config, util, compat
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import unittest
from . import Mock, call

from . import eq_, capture_db, assert_raises_message

def test_config_no_file_main_option():
    cfg = config.Config()
    cfg.set_main_option("url", "postgresql://foo/bar")

    eq_(cfg.get_main_option("url"), "postgresql://foo/bar")


def test_config_no_file_section_option():
    cfg = config.Config()
    cfg.set_section_option("foo", "url", "postgresql://foo/bar")

    eq_(cfg.get_section_option("foo", "url"), "postgresql://foo/bar")

    cfg.set_section_option("foo", "echo", "True")
    eq_(cfg.get_section_option("foo", "echo"), "True")


def test_standalone_op():
    eng, buf = capture_db()

    env = MigrationContext.configure(eng)
    op = Operations(env)

    op.alter_column("t", "c", nullable=True)
    eq_(buf, ['ALTER TABLE t ALTER COLUMN c DROP NOT NULL'])

def test_no_script_error():
    cfg = config.Config()
    assert_raises_message(
        util.CommandError,
        "No 'script_location' key found in configuration.",
        ScriptDirectory.from_config, cfg
    )


class OutputEncodingTest(unittest.TestCase):

    def test_plain(self):
        stdout = Mock(encoding='latin-1')
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout("test %s %s", "x", "y")
        eq_(
            stdout.mock_calls,
            [call.write('test x y'), call.write('\n')]
        )

    def test_utf8_unicode(self):
        stdout = Mock(encoding='latin-1')
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout(compat.u("méil %s %s"), "x", "y")
        eq_(
            stdout.mock_calls,
            [call.write(compat.u('méil x y')), call.write('\n')]
        )

    def test_ascii_unicode(self):
        stdout = Mock(encoding=None)
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout(compat.u("méil %s %s"), "x", "y")
        eq_(
            stdout.mock_calls,
            [call.write('m?il x y'), call.write('\n')]
        )


########NEW FILE########
__FILENAME__ = test_environment
#!coding: utf-8

from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext
from alembic.migration import MigrationContext
import unittest
from . import Mock, call, _no_sql_testing_config, staging_env, clear_staging_env

from . import eq_, is_

class EnvironmentTest(unittest.TestCase):
    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config()

    def tearDown(self):
        clear_staging_env()

    def _fixture(self, **kw):
        script = ScriptDirectory.from_config(self.cfg)
        env = EnvironmentContext(
            self.cfg,
            script,
            **kw
        )
        return env

    def test_x_arg(self):
        env = self._fixture()
        self.cfg.cmd_opts = Mock(x="y=5")
        eq_(
            env.get_x_argument(),
            "y=5"
        )

    def test_x_arg_asdict(self):
        env = self._fixture()
        self.cfg.cmd_opts = Mock(x=["y=5"])
        eq_(
            env.get_x_argument(as_dictionary=True),
            {"y": "5"}
        )

    def test_x_arg_no_opts(self):
        env = self._fixture()
        eq_(
            env.get_x_argument(),
            []
        )

    def test_x_arg_no_opts_asdict(self):
        env = self._fixture()
        eq_(
            env.get_x_argument(as_dictionary=True),
            {}
        )

    def test_tag_arg(self):
        env = self._fixture(tag="x")
        eq_(
            env.get_tag_argument(),
            "x"
        )

    def test_migration_context_has_config(self):
        env = self._fixture()
        env.configure(url="sqlite://")
        ctx = env._migration_context
        is_(ctx.config, self.cfg)

        ctx = MigrationContext(ctx.dialect, None, {})
        is_(ctx.config, None)

########NEW FILE########
__FILENAME__ = test_mssql
"""Test op functions against MSSQL."""

from unittest import TestCase

from sqlalchemy import Integer, Column

from alembic import op, command, util
from . import op_fixture, capture_context_buffer, \
    _no_sql_testing_config, assert_raises_message, staging_env, \
    three_rev_fixture, clear_staging_env


class FullEnvironmentTests(TestCase):
    @classmethod
    def setup_class(cls):
        env = staging_env()
        cls.cfg = cfg = _no_sql_testing_config("mssql")

        cls.a, cls.b, cls.c = \
            three_rev_fixture(cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_begin_commit(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BEGIN TRANSACTION;" in buf.getvalue()

        # ensure ends in COMMIT; GO
        assert [x for x in buf.getvalue().splitlines() if x][-2:] == ['COMMIT;', 'GO']

    def test_batch_separator_default(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "GO" in buf.getvalue()

    def test_batch_separator_custom(self):
        with capture_context_buffer(mssql_batch_separator="BYE") as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BYE" in buf.getvalue()

class OpTest(TestCase):
    def test_add_column(self):
        context = op_fixture('mssql')
        op.add_column('t1', Column('c1', Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")


    def test_add_column_with_default(self):
        context = op_fixture("mssql")
        op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL DEFAULT '12'")

    def test_alter_column_rename_mssql(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", new_column_name="x")
        context.assert_(
            "EXEC sp_rename 't.c', x, 'COLUMN'"
        )

    def test_alter_column_rename_quoted_mssql(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", new_column_name="SomeFancyName")
        context.assert_(
            "EXEC sp_rename 't.c', [SomeFancyName], 'COLUMN'"
        )

    def test_alter_column_new_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", type_=Integer)
        context.assert_(
            'ALTER TABLE t ALTER COLUMN c INTEGER'
        )

    def test_alter_column_dont_touch_constraints(self):
        context = op_fixture('mssql')
        from sqlalchemy import Boolean
        op.alter_column('tests', 'col',
            existing_type=Boolean(),
            nullable=False)
        context.assert_('ALTER TABLE tests ALTER COLUMN col BIT NOT NULL')

    def test_drop_index(self):
        context = op_fixture('mssql')
        op.drop_index('my_idx', 'my_table')
        # TODO: annoying that SQLA escapes unconditionally
        context.assert_contains("DROP INDEX my_idx ON my_table")

    def test_drop_column_w_default(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_default=True)
        op.drop_column('t1', 'c2', mssql_drop_default=True)
        context.assert_contains("exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")


    def test_alter_column_drop_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default=None)
        context.assert_contains("exec('alter table t drop constraint ' + @const_name)")

    def test_alter_column_dont_drop_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default=False)
        context.assert_()

    def test_drop_column_w_check(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_check=True)
        op.drop_column('t1', 'c2', mssql_drop_check=True)
        context.assert_contains("exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_check_quoting(self):
        context = op_fixture('mssql')
        op.drop_column('table', 'column', mssql_drop_check=True)
        context.assert_contains("exec('alter table [table] drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE [table] DROP COLUMN [column]")

    def test_alter_column_nullable_w_existing_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=True, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NULL"
        )

    def test_drop_column_w_fk(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_foreign_key=True)
        context.assert_contains("exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_alter_column_not_nullable_w_existing_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=False, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NOT NULL"
        )

    def test_alter_column_nullable_w_new_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=True, type_=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NULL"
        )

    def test_alter_column_not_nullable_w_new_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=False, type_=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NOT NULL"
        )

    def test_alter_column_nullable_type_required(self):
        context = op_fixture('mssql')
        assert_raises_message(
            util.CommandError,
            "MS-SQL ALTER COLUMN operations with NULL or "
            "NOT NULL require the existing_type or a new "
            "type_ be passed.",
            op.alter_column, "t", "c", nullable=False
        )

    def test_alter_add_server_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default="5")
        context.assert_(
            "ALTER TABLE t ADD DEFAULT '5' FOR c"
        )

    def test_alter_replace_server_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default="5", existing_server_default="6")
        context.assert_contains("exec('alter table t drop constraint ' + @const_name)")
        context.assert_contains(
            "ALTER TABLE t ADD DEFAULT '5' FOR c"
        )

    def test_alter_remove_server_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default=None)
        context.assert_contains("exec('alter table t drop constraint ' + @const_name)")

    def test_alter_do_everything(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", new_column_name="c2", nullable=True,
                            type_=Integer, server_default="5")
        context.assert_(
            'ALTER TABLE t ALTER COLUMN c INTEGER NULL',
            "ALTER TABLE t ADD DEFAULT '5' FOR c",
            "EXEC sp_rename 't.c', c2, 'COLUMN'"
        )

    # TODO: when we add schema support
    #def test_alter_column_rename_mssql_schema(self):
    #    context = op_fixture('mssql')
    #    op.alter_column("t", "c", name="x", schema="y")
    #    context.assert_(
    #        "EXEC sp_rename 'y.t.c', 'x', 'COLUMN'"
    #    )

########NEW FILE########
__FILENAME__ = test_mysql
from sqlalchemy import Integer, func
from unittest import TestCase
from sqlalchemy import TIMESTAMP, MetaData, Table, Column, text
from sqlalchemy.engine.reflection import Inspector
from alembic import op, util
from . import op_fixture, assert_raises_message, db_for_dialect, \
    staging_env, clear_staging_env
from alembic.migration import MigrationContext

class MySQLOpTest(TestCase):
    def test_rename_column(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer)
        context.assert_(
            'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL'
        )

    def test_rename_column_quotes_needed_one(self):
        context = op_fixture('mysql')
        op.alter_column('MyTable', 'ColumnOne', new_column_name="ColumnTwo",
                                existing_type=Integer)
        context.assert_(
            'ALTER TABLE `MyTable` CHANGE `ColumnOne` `ColumnTwo` INTEGER NULL'
        )

    def test_rename_column_quotes_needed_two(self):
        context = op_fixture('mysql')
        op.alter_column('my table', 'column one', new_column_name="column two",
                                existing_type=Integer)
        context.assert_(
            'ALTER TABLE `my table` CHANGE `column one` `column two` INTEGER NULL'
        )

    def test_rename_column_serv_default(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer,
                            existing_server_default="q")
        context.assert_(
            "ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL DEFAULT 'q'"
        )

    def test_rename_column_serv_compiled_default(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', existing_type=Integer,
                server_default=func.utc_thing(func.current_timestamp()))
        # this is not a valid MySQL default but the point is to just
        # test SQL expression rendering
        context.assert_(
            "ALTER TABLE t1 ALTER COLUMN c1 SET DEFAULT utc_thing(CURRENT_TIMESTAMP)"
        )

    def test_rename_column_autoincrement(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer,
                                    existing_autoincrement=True)
        context.assert_(
            'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL AUTO_INCREMENT'
        )

    def test_col_add_autoincrement(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', existing_type=Integer,
                                    autoincrement=True)
        context.assert_(
            'ALTER TABLE t1 MODIFY c1 INTEGER NULL AUTO_INCREMENT'
        )

    def test_col_remove_autoincrement(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', existing_type=Integer,
                                    existing_autoincrement=True,
                                    autoincrement=False)
        context.assert_(
            'ALTER TABLE t1 MODIFY c1 INTEGER NULL'
        )


    def test_col_dont_remove_server_default(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', existing_type=Integer,
                                    existing_server_default='1',
                                    server_default=False)

        context.assert_()

    def test_alter_column_drop_default(self):
        context = op_fixture('mysql')
        op.alter_column("t", "c", existing_type=Integer, server_default=None)
        context.assert_(
            'ALTER TABLE t ALTER COLUMN c DROP DEFAULT'
        )



    def test_alter_column_modify_default(self):
        context = op_fixture('mysql')
        # notice we dont need the existing type on this one...
        op.alter_column("t", "c", server_default='1')
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c SET DEFAULT '1'"
        )

    def test_col_not_nullable(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', nullable=False, existing_type=Integer)
        context.assert_(
            'ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL'
        )

    def test_col_not_nullable_existing_serv_default(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', nullable=False, existing_type=Integer,
                                    existing_server_default='5')
        context.assert_(
            "ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL DEFAULT '5'"
        )

    def test_col_nullable(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', nullable=True, existing_type=Integer)
        context.assert_(
            'ALTER TABLE t1 MODIFY c1 INTEGER NULL'
        )

    def test_col_multi_alter(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', nullable=False, server_default="q", type_=Integer)
        context.assert_(
            "ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL DEFAULT 'q'"
        )

    def test_alter_column_multi_alter_w_drop_default(self):
        context = op_fixture('mysql')
        op.alter_column('t1', 'c1', nullable=False, server_default=None, type_=Integer)
        context.assert_(
            "ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL"
        )

    def test_col_alter_type_required(self):
        op_fixture('mysql')
        assert_raises_message(
            util.CommandError,
            "MySQL CHANGE/MODIFY COLUMN operations require the existing type.",
            op.alter_column, 't1', 'c1', nullable=False, server_default="q"
        )

    def test_drop_fk(self):
        context = op_fixture('mysql')
        op.drop_constraint("f1", "t1", "foreignkey")
        context.assert_(
            "ALTER TABLE t1 DROP FOREIGN KEY f1"
        )

    def test_drop_constraint_primary(self):
        context = op_fixture('mysql')
        op.drop_constraint('primary', 't1', type_='primary')
        context.assert_(
            "ALTER TABLE t1 DROP PRIMARY KEY "
        )

    def test_drop_unique(self):
        context = op_fixture('mysql')
        op.drop_constraint("f1", "t1", "unique")
        context.assert_(
            "ALTER TABLE t1 DROP INDEX f1"
        )

    def test_drop_check(self):
        op_fixture('mysql')
        assert_raises_message(
            NotImplementedError,
            "MySQL does not support CHECK constraints.",
            op.drop_constraint, "f1", "t1", "check"
        )

    def test_drop_unknown(self):
        op_fixture('mysql')
        assert_raises_message(
            TypeError,
            "'type' can be one of 'check', 'foreignkey', "
            "'primary', 'unique', None",
            op.drop_constraint, "f1", "t1", "typo"
        )

    def test_drop_generic_constraint(self):
        op_fixture('mysql')
        assert_raises_message(
            NotImplementedError,
            "No generic 'DROP CONSTRAINT' in MySQL - please "
            "specify constraint type",
            op.drop_constraint, "f1", "t1"
        )

class MySQLDefaultCompareTest(TestCase):
    @classmethod
    def setup_class(cls):
        cls.bind = db_for_dialect("mysql")
        staging_env()
        context = MigrationContext.configure(
            connection=cls.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True
            }
        )
        connection = context.bind
        cls.autogen_context = {
            'imports': set(),
            'connection': connection,
            'dialect': connection.dialect,
            'context': context
            }

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def setUp(self):
        self.metadata = MetaData(self.bind)

    def tearDown(self):
        self.metadata.drop_all()

    def _compare_default_roundtrip(self, type_, txt, alternate=None):
        if alternate:
            expected = True
        else:
            alternate = txt
            expected = False
        t = Table("test", self.metadata,
            Column("somecol", type_, server_default=text(txt) if txt else None)
        )
        t2 = Table("test", MetaData(),
            Column("somecol", type_, server_default=text(alternate))
        )
        assert self._compare_default(
            t, t2, t2.c.somecol, alternate
        ) is expected

    def _compare_default(
        self,
        t1, t2, col,
        rendered
    ):
        t1.create(self.bind)
        insp = Inspector.from_engine(self.bind)
        cols = insp.get_columns(t1.name)
        ctx = self.autogen_context['context']
        return ctx.impl.compare_server_default(
            None,
            col,
            rendered,
            cols[0]['default'])

    def test_compare_timestamp_current_timestamp(self):
        self._compare_default_roundtrip(
            TIMESTAMP(),
            "CURRENT_TIMESTAMP",
        )

    def test_compare_timestamp_current_timestamp_diff(self):
        self._compare_default_roundtrip(
            TIMESTAMP(),
            None, "CURRENT_TIMESTAMP",
        )


########NEW FILE########
__FILENAME__ = test_offline_environment
import io
from unittest import TestCase

from alembic import command, util
from . import clear_staging_env, staging_env, \
    _no_sql_testing_config, \
    three_rev_fixture, env_file_fixture,\
    assert_raises_message


class OfflineEnvironmentTest(TestCase):
    def setUp(self):
        env = staging_env()
        self.cfg = _no_sql_testing_config()

        global a, b, c
        a, b, c = three_rev_fixture(self.cfg)

    def tearDown(self):
        clear_staging_env()

    def test_not_requires_connection(self):
        env_file_fixture("""
assert not context.requires_connection()
""")
        command.upgrade(self.cfg, a, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)

    def test_requires_connection(self):
        env_file_fixture("""
assert context.requires_connection()
""")
        command.upgrade(self.cfg, a)
        command.downgrade(self.cfg, a)


    def test_starting_rev_post_context(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite', starting_rev='x')
assert context.get_starting_revision_argument() == 'x'
""")
        command.upgrade(self.cfg, a, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)
        command.current(self.cfg)
        command.stamp(self.cfg, a)

    def test_starting_rev_pre_context(self):
        env_file_fixture("""
assert context.get_starting_revision_argument() == 'x'
""")
        command.upgrade(self.cfg, "x:y", sql=True)
        command.downgrade(self.cfg, "x:y", sql=True)

    def test_starting_rev_pre_context_stamp(self):
        env_file_fixture("""
assert context.get_starting_revision_argument() == 'x'
""")
        assert_raises_message(
            util.CommandError,
            "No starting revision argument is available.",
            command.stamp, self.cfg, a)

    def test_starting_rev_current_pre_context(self):
        env_file_fixture("""
assert context.get_starting_revision_argument() is None
""")
        assert_raises_message(
            util.CommandError,
            "No starting revision argument is available.",
            command.current, self.cfg
        )

    def test_destination_rev_pre_context(self):
        env_file_fixture("""
assert context.get_revision_argument() == '%s'
""" % b)
        command.upgrade(self.cfg, b, sql=True)
        command.stamp(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (c, b), sql=True)

    def test_destination_rev_post_context(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_revision_argument() == '%s'
""" % b)
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (c, b), sql=True)
        command.stamp(self.cfg, b, sql=True)

    def test_head_rev_pre_context(self):
        env_file_fixture("""
assert context.get_head_revision() == '%s'
""" % c)
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)
        command.stamp(self.cfg, b, sql=True)
        command.current(self.cfg)

    def test_head_rev_post_context(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_head_revision() == '%s'
""" % c)
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)
        command.stamp(self.cfg, b, sql=True)
        command.current(self.cfg)

    def test_tag_pre_context(self):
        env_file_fixture("""
assert context.get_tag_argument() == 'hi'
""")
        command.upgrade(self.cfg, b, sql=True, tag='hi')
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True, tag='hi')

    def test_tag_pre_context_None(self):
        env_file_fixture("""
assert context.get_tag_argument() is None
""")
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)

    def test_tag_cmd_arg(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_tag_argument() == 'hi'
""")
        command.upgrade(self.cfg, b, sql=True, tag='hi')
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True, tag='hi')

    def test_tag_cfg_arg(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite', tag='there')
assert context.get_tag_argument() == 'there'
""")
        command.upgrade(self.cfg, b, sql=True, tag='hi')
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True, tag='hi')

    def test_tag_None(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_tag_argument() is None
""")
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)

    def test_downgrade_wo_colon(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
""")
        assert_raises_message(
            util.CommandError,
            "downgrade with --sql requires <fromrev>:<torev>",
            command.downgrade,
            self.cfg, b, sql=True
        )

    def test_upgrade_with_output_encoding(self):
        env_file_fixture("""
url = config.get_main_option('sqlalchemy.url')
context.configure(url=url, output_encoding='utf-8')
assert not context.requires_connection()
""")
        command.upgrade(self.cfg, a, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)

########NEW FILE########
__FILENAME__ = test_op
"""Test against the builders in the op.* module."""

from sqlalchemy import Integer, Column, ForeignKey, \
            Table, String, Boolean, MetaData, CheckConstraint
from sqlalchemy.sql import column, func, text
from sqlalchemy import event

from alembic import op
from . import op_fixture, assert_raises_message, requires_094, eq_
from . import mock

@event.listens_for(Table, "after_parent_attach")
def _add_cols(table, metadata):
    if table.name == "tbl_with_auto_appended_column":
        table.append_column(Column('bat', Integer))


def test_rename_table():
    context = op_fixture()
    op.rename_table('t1', 't2')
    context.assert_("ALTER TABLE t1 RENAME TO t2")

def test_rename_table_schema():
    context = op_fixture()
    op.rename_table('t1', 't2', schema="foo")
    context.assert_("ALTER TABLE foo.t1 RENAME TO foo.t2")

def test_rename_table_postgresql():
    context = op_fixture("postgresql")
    op.rename_table('t1', 't2')
    context.assert_("ALTER TABLE t1 RENAME TO t2")

def test_rename_table_schema_postgresql():
    context = op_fixture("postgresql")
    op.rename_table('t1', 't2', schema="foo")
    context.assert_("ALTER TABLE foo.t1 RENAME TO t2")

def test_create_index_postgresql_where():
    context = op_fixture("postgresql")
    op.create_index(
        'geocoded',
        'locations',
        ['coordinates'],
        postgresql_where=text("locations.coordinates != Null"))
    context.assert_(
            "CREATE INDEX geocoded ON locations (coordinates) "
            "WHERE locations.coordinates != Null")

def test_add_column():
    context = op_fixture()
    op.add_column('t1', Column('c1', Integer, nullable=False))
    context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL")

def test_add_column_schema():
    context = op_fixture()
    op.add_column('t1', Column('c1', Integer, nullable=False), schema="foo")
    context.assert_("ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL")

def test_add_column_with_default():
    context = op_fixture()
    op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
    context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER DEFAULT '12' NOT NULL")

def test_add_column_schema_with_default():
    context = op_fixture()
    op.add_column('t1',
            Column('c1', Integer, nullable=False, server_default="12"),
            schema='foo')
    context.assert_("ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER DEFAULT '12' NOT NULL")

def test_add_column_fk():
    context = op_fixture()
    op.add_column('t1', Column('c1', Integer, ForeignKey('c2.id'), nullable=False))
    context.assert_(
        "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
        "ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES c2 (id)"
    )

def test_add_column_schema_fk():
    context = op_fixture()
    op.add_column('t1',
            Column('c1', Integer, ForeignKey('c2.id'), nullable=False),
            schema='foo')
    context.assert_(
        "ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL",
        "ALTER TABLE foo.t1 ADD FOREIGN KEY(c1) REFERENCES c2 (id)"
    )

def test_add_column_schema_type():
    """Test that a schema type generates its constraints...."""
    context = op_fixture()
    op.add_column('t1', Column('c1', Boolean, nullable=False))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL',
        'ALTER TABLE t1 ADD CHECK (c1 IN (0, 1))'
    )


def test_add_column_schema_schema_type():
    """Test that a schema type generates its constraints...."""
    context = op_fixture()
    op.add_column('t1', Column('c1', Boolean, nullable=False), schema='foo')
    context.assert_(
        'ALTER TABLE foo.t1 ADD COLUMN c1 BOOLEAN NOT NULL',
        'ALTER TABLE foo.t1 ADD CHECK (c1 IN (0, 1))'
    )

def test_add_column_schema_type_checks_rule():
    """Test that a schema type doesn't generate a
    constraint based on check rule."""
    context = op_fixture('postgresql')
    op.add_column('t1', Column('c1', Boolean, nullable=False))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL',
    )

def test_add_column_fk_self_referential():
    context = op_fixture()
    op.add_column('t1', Column('c1', Integer, ForeignKey('t1.c2'), nullable=False))
    context.assert_(
        "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
        "ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES t1 (c2)"
    )

def test_add_column_schema_fk_self_referential():
    context = op_fixture()
    op.add_column('t1',
            Column('c1', Integer, ForeignKey('foo.t1.c2'), nullable=False),
            schema='foo')
    context.assert_(
        "ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL",
        "ALTER TABLE foo.t1 ADD FOREIGN KEY(c1) REFERENCES foo.t1 (c2)"
    )

def test_add_column_fk_schema():
    context = op_fixture()
    op.add_column('t1', Column('c1', Integer, ForeignKey('remote.t2.c2'), nullable=False))
    context.assert_(
    'ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL',
    'ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES remote.t2 (c2)'
    )

def test_add_column_schema_fk_schema():
    context = op_fixture()
    op.add_column('t1',
            Column('c1', Integer, ForeignKey('remote.t2.c2'), nullable=False),
            schema='foo')
    context.assert_(
    'ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL',
    'ALTER TABLE foo.t1 ADD FOREIGN KEY(c1) REFERENCES remote.t2 (c2)'
    )

def test_drop_column():
    context = op_fixture()
    op.drop_column('t1', 'c1')
    context.assert_("ALTER TABLE t1 DROP COLUMN c1")

def test_drop_column_schema():
    context = op_fixture()
    op.drop_column('t1', 'c1', schema='foo')
    context.assert_("ALTER TABLE foo.t1 DROP COLUMN c1")

def test_alter_column_nullable():
    context = op_fixture()
    op.alter_column("t", "c", nullable=True)
    context.assert_(
        # TODO: not sure if this is PG only or standard
        # SQL
        "ALTER TABLE t ALTER COLUMN c DROP NOT NULL"
    )

def test_alter_column_schema_nullable():
    context = op_fixture()
    op.alter_column("t", "c", nullable=True, schema='foo')
    context.assert_(
        # TODO: not sure if this is PG only or standard
        # SQL
        "ALTER TABLE foo.t ALTER COLUMN c DROP NOT NULL"
    )

def test_alter_column_not_nullable():
    context = op_fixture()
    op.alter_column("t", "c", nullable=False)
    context.assert_(
        # TODO: not sure if this is PG only or standard
        # SQL
        "ALTER TABLE t ALTER COLUMN c SET NOT NULL"
    )

def test_alter_column_schema_not_nullable():
    context = op_fixture()
    op.alter_column("t", "c", nullable=False, schema='foo')
    context.assert_(
        # TODO: not sure if this is PG only or standard
        # SQL
        "ALTER TABLE foo.t ALTER COLUMN c SET NOT NULL"
    )

def test_alter_column_rename():
    context = op_fixture()
    op.alter_column("t", "c", new_column_name="x")
    context.assert_(
        "ALTER TABLE t RENAME c TO x"
    )

def test_alter_column_schema_rename():
    context = op_fixture()
    op.alter_column("t", "c", new_column_name="x", schema='foo')
    context.assert_(
        "ALTER TABLE foo.t RENAME c TO x"
    )

def test_alter_column_type():
    context = op_fixture()
    op.alter_column("t", "c", type_=String(50))
    context.assert_(
        'ALTER TABLE t ALTER COLUMN c TYPE VARCHAR(50)'
    )

def test_alter_column_schema_type():
    context = op_fixture()
    op.alter_column("t", "c", type_=String(50), schema='foo')
    context.assert_(
        'ALTER TABLE foo.t ALTER COLUMN c TYPE VARCHAR(50)'
    )

def test_alter_column_set_default():
    context = op_fixture()
    op.alter_column("t", "c", server_default="q")
    context.assert_(
        "ALTER TABLE t ALTER COLUMN c SET DEFAULT 'q'"
    )

def test_alter_column_schema_set_default():
    context = op_fixture()
    op.alter_column("t", "c", server_default="q", schema='foo')
    context.assert_(
        "ALTER TABLE foo.t ALTER COLUMN c SET DEFAULT 'q'"
    )

def test_alter_column_set_compiled_default():
    context = op_fixture()
    op.alter_column("t", "c",
            server_default=func.utc_thing(func.current_timestamp()))
    context.assert_(
        "ALTER TABLE t ALTER COLUMN c SET DEFAULT utc_thing(CURRENT_TIMESTAMP)"
    )

def test_alter_column_schema_set_compiled_default():
    context = op_fixture()
    op.alter_column("t", "c",
            server_default=func.utc_thing(func.current_timestamp()),
            schema='foo')
    context.assert_(
        "ALTER TABLE foo.t ALTER COLUMN c SET DEFAULT utc_thing(CURRENT_TIMESTAMP)"
    )

def test_alter_column_drop_default():
    context = op_fixture()
    op.alter_column("t", "c", server_default=None)
    context.assert_(
        'ALTER TABLE t ALTER COLUMN c DROP DEFAULT'
    )

def test_alter_column_schema_drop_default():
    context = op_fixture()
    op.alter_column("t", "c", server_default=None, schema='foo')
    context.assert_(
        'ALTER TABLE foo.t ALTER COLUMN c DROP DEFAULT'
    )


def test_alter_column_schema_type_unnamed():
    context = op_fixture('mssql')
    op.alter_column("t", "c", type_=Boolean())
    context.assert_(
        'ALTER TABLE t ALTER COLUMN c BIT',
        'ALTER TABLE t ADD CHECK (c IN (0, 1))'
    )

def test_alter_column_schema_schema_type_unnamed():
    context = op_fixture('mssql')
    op.alter_column("t", "c", type_=Boolean(), schema='foo')
    context.assert_(
        'ALTER TABLE foo.t ALTER COLUMN c BIT',
        'ALTER TABLE foo.t ADD CHECK (c IN (0, 1))'
    )

def test_alter_column_schema_type_named():
    context = op_fixture('mssql')
    op.alter_column("t", "c", type_=Boolean(name="xyz"))
    context.assert_(
        'ALTER TABLE t ALTER COLUMN c BIT',
        'ALTER TABLE t ADD CONSTRAINT xyz CHECK (c IN (0, 1))'
    )

def test_alter_column_schema_schema_type_named():
    context = op_fixture('mssql')
    op.alter_column("t", "c", type_=Boolean(name="xyz"), schema='foo')
    context.assert_(
        'ALTER TABLE foo.t ALTER COLUMN c BIT',
        'ALTER TABLE foo.t ADD CONSTRAINT xyz CHECK (c IN (0, 1))'
    )

def test_alter_column_schema_type_existing_type():
    context = op_fixture('mssql')
    op.alter_column("t", "c", type_=String(10), existing_type=Boolean(name="xyz"))
    context.assert_(
        'ALTER TABLE t DROP CONSTRAINT xyz',
        'ALTER TABLE t ALTER COLUMN c VARCHAR(10)'
    )

def test_alter_column_schema_schema_type_existing_type():
    context = op_fixture('mssql')
    op.alter_column("t", "c", type_=String(10),
            existing_type=Boolean(name="xyz"), schema='foo')
    context.assert_(
        'ALTER TABLE foo.t DROP CONSTRAINT xyz',
        'ALTER TABLE foo.t ALTER COLUMN c VARCHAR(10)'
    )

def test_alter_column_schema_type_existing_type_no_const():
    context = op_fixture('postgresql')
    op.alter_column("t", "c", type_=String(10), existing_type=Boolean())
    context.assert_(
        'ALTER TABLE t ALTER COLUMN c TYPE VARCHAR(10)'
    )

def test_alter_column_schema_schema_type_existing_type_no_const():
    context = op_fixture('postgresql')
    op.alter_column("t", "c", type_=String(10), existing_type=Boolean(),
            schema='foo')
    context.assert_(
        'ALTER TABLE foo.t ALTER COLUMN c TYPE VARCHAR(10)'
    )

def test_alter_column_schema_type_existing_type_no_new_type():
    context = op_fixture('postgresql')
    op.alter_column("t", "c", nullable=False, existing_type=Boolean())
    context.assert_(
        'ALTER TABLE t ALTER COLUMN c SET NOT NULL'
    )

def test_alter_column_schema_schema_type_existing_type_no_new_type():
    context = op_fixture('postgresql')
    op.alter_column("t", "c", nullable=False, existing_type=Boolean(),
            schema='foo')
    context.assert_(
        'ALTER TABLE foo.t ALTER COLUMN c SET NOT NULL'
    )

def test_add_foreign_key():
    context = op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2',
                    ['foo', 'bar'], ['bat', 'hoho'])
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho)"
    )

def test_add_foreign_key_schema():
    context = op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2',
                    ['foo', 'bar'], ['bat', 'hoho'],
                    source_schema='foo2', referent_schema='bar2')
    context.assert_(
        "ALTER TABLE foo2.t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES bar2.t2 (bat, hoho)"
    )

def test_add_foreign_key_onupdate():
    context = op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2',
                    ['foo', 'bar'], ['bat', 'hoho'],
                    onupdate='CASCADE')
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) ON UPDATE CASCADE"
    )

def test_add_foreign_key_ondelete():
    context = op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2',
                    ['foo', 'bar'], ['bat', 'hoho'],
                    ondelete='CASCADE')
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) ON DELETE CASCADE"
    )

def test_add_foreign_key_deferrable():
    context = op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2',
                    ['foo', 'bar'], ['bat', 'hoho'],
                    deferrable=True)
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) DEFERRABLE"
    )

def test_add_foreign_key_initially():
    context = op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2',
                    ['foo', 'bar'], ['bat', 'hoho'],
                    initially='INITIAL')
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) INITIALLY INITIAL"
    )

def test_add_foreign_key_match():
    context = op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2',
                    ['foo', 'bar'], ['bat', 'hoho'],
                    match='SIMPLE')
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) MATCH SIMPLE"
    )

def test_add_foreign_key_dialect_kw():
    context = op_fixture()
    with mock.patch("alembic.operations.sa_schema.ForeignKeyConstraint") as fkc:
        op.create_foreign_key('fk_test', 't1', 't2',
                        ['foo', 'bar'], ['bat', 'hoho'],
                        foobar_arg='xyz')
        eq_(fkc.mock_calls[0],
                mock.call(['foo', 'bar'], ['t2.bat', 't2.hoho'],
                    onupdate=None, ondelete=None, name='fk_test',
                    foobar_arg='xyz',
                    deferrable=None, initially=None, match=None))

def test_add_foreign_key_self_referential():
    context = op_fixture()
    op.create_foreign_key("fk_test", "t1", "t1", ["foo"], ["bar"])
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test "
        "FOREIGN KEY(foo) REFERENCES t1 (bar)"
    )

def test_add_primary_key_constraint():
    context = op_fixture()
    op.create_primary_key("pk_test", "t1", ["foo", "bar"])
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT pk_test PRIMARY KEY (foo, bar)"
    )

def test_add_primary_key_constraint_schema():
    context = op_fixture()
    op.create_primary_key("pk_test", "t1", ["foo"], schema="bar")
    context.assert_(
        "ALTER TABLE bar.t1 ADD CONSTRAINT pk_test PRIMARY KEY (foo)"
    )


def test_add_check_constraint():
    context = op_fixture()
    op.create_check_constraint(
        "ck_user_name_len",
        "user_table",
        func.len(column('name')) > 5
    )
    context.assert_(
        "ALTER TABLE user_table ADD CONSTRAINT ck_user_name_len "
        "CHECK (len(name) > 5)"
    )

def test_add_check_constraint_schema():
    context = op_fixture()
    op.create_check_constraint(
        "ck_user_name_len",
        "user_table",
        func.len(column('name')) > 5,
        schema='foo'
    )
    context.assert_(
        "ALTER TABLE foo.user_table ADD CONSTRAINT ck_user_name_len "
        "CHECK (len(name) > 5)"
    )

def test_add_unique_constraint():
    context = op_fixture()
    op.create_unique_constraint('uk_test', 't1', ['foo', 'bar'])
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
    )

def test_add_unique_constraint_schema():
    context = op_fixture()
    op.create_unique_constraint('uk_test', 't1', ['foo', 'bar'], schema='foo')
    context.assert_(
        "ALTER TABLE foo.t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
    )


def test_drop_constraint():
    context = op_fixture()
    op.drop_constraint('foo_bar_bat', 't1')
    context.assert_(
        "ALTER TABLE t1 DROP CONSTRAINT foo_bar_bat"
    )

def test_drop_constraint_schema():
    context = op_fixture()
    op.drop_constraint('foo_bar_bat', 't1', schema='foo')
    context.assert_(
        "ALTER TABLE foo.t1 DROP CONSTRAINT foo_bar_bat"
    )

def test_create_index():
    context = op_fixture()
    op.create_index('ik_test', 't1', ['foo', 'bar'])
    context.assert_(
        "CREATE INDEX ik_test ON t1 (foo, bar)"
    )


def test_create_index_table_col_event():
    context = op_fixture()

    op.create_index('ik_test', 'tbl_with_auto_appended_column', ['foo', 'bar'])
    context.assert_(
        "CREATE INDEX ik_test ON tbl_with_auto_appended_column (foo, bar)"
    )

def test_add_unique_constraint_col_event():
    context = op_fixture()
    op.create_unique_constraint('ik_test',
            'tbl_with_auto_appended_column', ['foo', 'bar'])
    context.assert_(
        "ALTER TABLE tbl_with_auto_appended_column "
        "ADD CONSTRAINT ik_test UNIQUE (foo, bar)"
    )


def test_create_index_schema():
    context = op_fixture()
    op.create_index('ik_test', 't1', ['foo', 'bar'], schema='foo')
    context.assert_(
        "CREATE INDEX ik_test ON foo.t1 (foo, bar)"
    )

def test_drop_index():
    context = op_fixture()
    op.drop_index('ik_test')
    context.assert_(
        "DROP INDEX ik_test"
    )

def test_drop_index_schema():
    context = op_fixture()
    op.drop_index('ik_test', schema='foo')
    context.assert_(
        "DROP INDEX foo.ik_test"
    )

def test_drop_table():
    context = op_fixture()
    op.drop_table('tb_test')
    context.assert_(
        "DROP TABLE tb_test"
    )

def test_drop_table_schema():
    context = op_fixture()
    op.drop_table('tb_test', schema='foo')
    context.assert_(
        "DROP TABLE foo.tb_test"
    )

def test_create_table_selfref():
    context = op_fixture()
    op.create_table(
        "some_table",
        Column('id', Integer, primary_key=True),
        Column('st_id', Integer, ForeignKey('some_table.id'))
    )
    context.assert_(
        "CREATE TABLE some_table ("
            "id INTEGER NOT NULL, "
            "st_id INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(st_id) REFERENCES some_table (id))"
    )

def test_create_table_fk_and_schema():
    context = op_fixture()
    op.create_table(
        "some_table",
        Column('id', Integer, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id')),
        schema='schema'
    )
    context.assert_(
        "CREATE TABLE schema.some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id))"
    )

def test_create_table_no_pk():
    context = op_fixture()
    op.create_table(
        "some_table",
        Column('x', Integer),
        Column('y', Integer),
        Column('z', Integer),
    )
    context.assert_(
        "CREATE TABLE some_table (x INTEGER, y INTEGER, z INTEGER)"
    )

def test_create_table_two_fk():
    context = op_fixture()
    op.create_table(
        "some_table",
        Column('id', Integer, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id')),
        Column('foo_bar', Integer, ForeignKey('foo.bar')),
    )
    context.assert_(
        "CREATE TABLE some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "foo_bar INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id), "
            "FOREIGN KEY(foo_bar) REFERENCES foo (bar))"
    )

def test_inline_literal():
    context = op_fixture()
    from sqlalchemy.sql import table, column
    from sqlalchemy import String, Integer

    account = table('account',
        column('name', String),
        column('id', Integer)
    )
    op.execute(
        account.update().\
            where(account.c.name == op.inline_literal('account 1')).\
            values({'name': op.inline_literal('account 2')})
            )
    op.execute(
        account.update().\
            where(account.c.id == op.inline_literal(1)).\
            values({'id': op.inline_literal(2)})
            )
    context.assert_(
        "UPDATE account SET name='account 2' WHERE account.name = 'account 1'",
        "UPDATE account SET id=2 WHERE account.id = 1"
    )

def test_cant_op():
    if hasattr(op, '_proxy'):
        del op._proxy
    assert_raises_message(
        NameError,
        "Can't invoke function 'inline_literal', as the "
        "proxy object has not yet been established "
        "for the Alembic 'Operations' class.  "
        "Try placing this code inside a callable.",
        op.inline_literal, "asdf"
    )


def test_naming_changes():
    context = op_fixture()
    op.alter_column("t", "c", name="x")
    context.assert_("ALTER TABLE t RENAME c TO x")

    context = op_fixture()
    op.alter_column("t", "c", new_column_name="x")
    context.assert_("ALTER TABLE t RENAME c TO x")

    context = op_fixture('mssql')
    op.drop_index('ik_test', tablename='t1')
    context.assert_("DROP INDEX ik_test ON t1")

    context = op_fixture('mysql')
    op.drop_constraint("f1", "t1", type="foreignkey")
    context.assert_("ALTER TABLE t1 DROP FOREIGN KEY f1")

    context = op_fixture('mysql')
    op.drop_constraint("f1", "t1", type_="foreignkey")
    context.assert_("ALTER TABLE t1 DROP FOREIGN KEY f1")

    assert_raises_message(
        TypeError,
        r"Unknown arguments: badarg\d, badarg\d",
        op.alter_column, "t", "c", badarg1="x", badarg2="y"
    )


########NEW FILE########
__FILENAME__ = test_op_naming_convention
from sqlalchemy import Integer, Column, ForeignKey, \
            Table, String, Boolean, MetaData, CheckConstraint
from sqlalchemy.sql import column, func, text
from sqlalchemy import event

from alembic import op
from . import op_fixture, assert_raises_message, requires_094

@requires_094
def test_add_check_constraint():
    context = op_fixture(naming_convention={
            "ck": "ck_%(table_name)s_%(constraint_name)s"
        })
    op.create_check_constraint(
        "foo",
        "user_table",
        func.len(column('name')) > 5
    )
    context.assert_(
        "ALTER TABLE user_table ADD CONSTRAINT ck_user_table_foo "
        "CHECK (len(name) > 5)"
    )

@requires_094
def test_add_check_constraint_name_is_none():
    context = op_fixture(naming_convention={
                    "ck": "ck_%(table_name)s_foo"
                })
    op.create_check_constraint(
        None,
        "user_table",
        func.len(column('name')) > 5
    )
    context.assert_(
        "ALTER TABLE user_table ADD CONSTRAINT ck_user_table_foo "
        "CHECK (len(name) > 5)"
    )

@requires_094
def test_add_unique_constraint_name_is_none():
    context = op_fixture(naming_convention={
                    "uq": "uq_%(table_name)s_foo"
                })
    op.create_unique_constraint(
        None,
        "user_table",
        'x'
    )
    context.assert_(
        "ALTER TABLE user_table ADD CONSTRAINT uq_user_table_foo UNIQUE (x)"
    )


@requires_094
def test_add_index_name_is_none():
    context = op_fixture(naming_convention={
                    "ix": "ix_%(table_name)s_foo"
                })
    op.create_index(
        None,
        "user_table",
        'x'
    )
    context.assert_(
        "CREATE INDEX ix_user_table_foo ON user_table (x)"
    )



@requires_094
def test_add_check_constraint_already_named_from_schema():
    m1 = MetaData(naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"})
    ck = CheckConstraint("im a constraint", name="cc1")
    Table('t', m1, Column('x'), ck)

    context = op_fixture(
                naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"})

    op.create_table(
        "some_table",
        Column('x', Integer, ck),
    )
    context.assert_(
        "CREATE TABLE some_table "
        "(x INTEGER CONSTRAINT ck_t_cc1 CHECK (im a constraint))"
    )

@requires_094
def test_add_check_constraint_inline_on_table():
    context = op_fixture(
                naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"})
    op.create_table(
        "some_table",
        Column('x', Integer),
        CheckConstraint("im a constraint", name="cc1")
    )
    context.assert_(
        "CREATE TABLE some_table "
        "(x INTEGER, CONSTRAINT ck_some_table_cc1 CHECK (im a constraint))"
    )

@requires_094
def test_add_check_constraint_inline_on_table_w_f():
    context = op_fixture(
                naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"})
    op.create_table(
        "some_table",
        Column('x', Integer),
        CheckConstraint("im a constraint", name=op.f("ck_some_table_cc1"))
    )
    context.assert_(
        "CREATE TABLE some_table "
        "(x INTEGER, CONSTRAINT ck_some_table_cc1 CHECK (im a constraint))"
    )

@requires_094
def test_add_check_constraint_inline_on_column():
    context = op_fixture(
                naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"})
    op.create_table(
        "some_table",
        Column('x', Integer, CheckConstraint("im a constraint", name="cc1"))
    )
    context.assert_(
        "CREATE TABLE some_table "
        "(x INTEGER CONSTRAINT ck_some_table_cc1 CHECK (im a constraint))"
    )

@requires_094
def test_add_check_constraint_inline_on_column_w_f():
    context = op_fixture(
                naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"})
    op.create_table(
        "some_table",
        Column('x', Integer, CheckConstraint("im a constraint", name=op.f("ck_q_cc1")))
    )
    context.assert_(
        "CREATE TABLE some_table "
        "(x INTEGER CONSTRAINT ck_q_cc1 CHECK (im a constraint))"
    )


@requires_094
def test_add_column_schema_type():
    context = op_fixture(naming_convention={
                    "ck": "ck_%(table_name)s_%(constraint_name)s"
                })
    op.add_column('t1', Column('c1', Boolean(name='foo'), nullable=False))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL',
        'ALTER TABLE t1 ADD CONSTRAINT ck_t1_foo CHECK (c1 IN (0, 1))'
    )


@requires_094
def test_add_column_schema_type_w_f():
    context = op_fixture(naming_convention={
                    "ck": "ck_%(table_name)s_%(constraint_name)s"
                })
    op.add_column('t1', Column('c1', Boolean(name=op.f('foo')), nullable=False))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL',
        'ALTER TABLE t1 ADD CONSTRAINT foo CHECK (c1 IN (0, 1))'
    )



########NEW FILE########
__FILENAME__ = test_oracle
"""Test op functions against ORACLE."""

from unittest import TestCase

from sqlalchemy import Integer, Column

from alembic import op, command
from . import op_fixture, capture_context_buffer, \
    _no_sql_testing_config, staging_env, \
    three_rev_fixture, clear_staging_env


class FullEnvironmentTests(TestCase):
    @classmethod
    def setup_class(cls):
        env = staging_env()
        cls.cfg = cfg = _no_sql_testing_config("oracle")

        cls.a, cls.b, cls.c = \
            three_rev_fixture(cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_begin_comit(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "SET TRANSACTION READ WRITE\n\n/" in buf.getvalue()
        assert "COMMIT\n\n/" in buf.getvalue()

    def test_batch_separator_default(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "/" in buf.getvalue()
        assert ";" not in buf.getvalue()

    def test_batch_separator_custom(self):
        with capture_context_buffer(oracle_batch_separator="BYE") as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BYE" in buf.getvalue()

class OpTest(TestCase):
    def test_add_column(self):
        context = op_fixture('oracle')
        op.add_column('t1', Column('c1', Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")


    def test_add_column_with_default(self):
        context = op_fixture("oracle")
        op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER DEFAULT '12' NOT NULL")

    def test_alter_column_rename_oracle(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", name="x")
        context.assert_(
            "ALTER TABLE t RENAME COLUMN c TO x"
        )

    def test_alter_column_new_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", type_=Integer)
        context.assert_(
            'ALTER TABLE t MODIFY c INTEGER'
        )

    def test_drop_index(self):
        context = op_fixture('oracle')
        op.drop_index('my_idx', 'my_table')
        context.assert_contains("DROP INDEX my_idx")

    def test_drop_column_w_default(self):
        context = op_fixture('oracle')
        op.drop_column('t1', 'c1')
        context.assert_(
            "ALTER TABLE t1 DROP COLUMN c1"
        )

    def test_drop_column_w_check(self):
        context = op_fixture('oracle')
        op.drop_column('t1', 'c1')
        context.assert_(
            "ALTER TABLE t1 DROP COLUMN c1"
        )

    def test_alter_column_nullable_w_existing_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=True, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NULL"
        )

    def test_alter_column_not_nullable_w_existing_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=False, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NOT NULL"
        )

    def test_alter_column_nullable_w_new_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=True, type_=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NULL",
            'ALTER TABLE t MODIFY c INTEGER'
        )

    def test_alter_column_not_nullable_w_new_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=False, type_=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NOT NULL",
            "ALTER TABLE t MODIFY c INTEGER"
        )

    def test_alter_add_server_default(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", server_default="5")
        context.assert_(
            "ALTER TABLE t MODIFY c DEFAULT '5'"
        )

    def test_alter_replace_server_default(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", server_default="5", existing_server_default="6")
        context.assert_(
            "ALTER TABLE t MODIFY c DEFAULT '5'"
        )

    def test_alter_remove_server_default(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", server_default=None)
        context.assert_(
            "ALTER TABLE t MODIFY c DEFAULT NULL"
        )

    def test_alter_do_everything(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", name="c2", nullable=True, type_=Integer, server_default="5")
        context.assert_(
            'ALTER TABLE t MODIFY c NULL',
            "ALTER TABLE t MODIFY c DEFAULT '5'",
            'ALTER TABLE t MODIFY c INTEGER',
            'ALTER TABLE t RENAME COLUMN c TO c2'
        )

    # TODO: when we add schema support
    #def test_alter_column_rename_oracle_schema(self):
    #    context = op_fixture('oracle')
    #    op.alter_column("t", "c", name="x", schema="y")
    #    context.assert_(
    #        'ALTER TABLE y.t RENAME COLUMN c TO c2'
    #    )


########NEW FILE########
__FILENAME__ = test_postgresql
from unittest import TestCase

from sqlalchemy import DateTime, MetaData, Table, Column, text, Integer, String
from sqlalchemy.engine.reflection import Inspector
from alembic.operations import Operations
from sqlalchemy.sql import table, column

from alembic import command, util
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from . import db_for_dialect, eq_, staging_env, \
            clear_staging_env, _no_sql_testing_config,\
            capture_context_buffer, requires_09, write_script

class PGOfflineEnumTest(TestCase):
    def setUp(self):
        staging_env()
        self.cfg = cfg = _no_sql_testing_config()

        self.rid = rid = util.rev_id()

        self.script = script = ScriptDirectory.from_config(cfg)
        script.generate_revision(rid, None, refresh=True)

    def tearDown(self):
        clear_staging_env()


    def _inline_enum_script(self):
        write_script(self.script, self.rid, """
revision = '%s'
down_revision = None

from alembic import op
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column

def upgrade():
    op.create_table("sometable",
        Column("data", ENUM("one", "two", "three", name="pgenum"))
    )

def downgrade():
    op.drop_table("sometable")
""" % self.rid)

    def _distinct_enum_script(self):
        write_script(self.script, self.rid, """
revision = '%s'
down_revision = None

from alembic import op
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column

def upgrade():
    enum = ENUM("one", "two", "three", name="pgenum", create_type=False)
    enum.create(op.get_bind(), checkfirst=False)
    op.create_table("sometable",
        Column("data", enum)
    )

def downgrade():
    op.drop_table("sometable")
    ENUM(name="pgenum").drop(op.get_bind(), checkfirst=False)

""" % self.rid)

    @requires_09
    def test_offline_inline_enum_create(self):
        self._inline_enum_script()
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.rid, sql=True)
        assert "CREATE TYPE pgenum AS ENUM ('one', 'two', 'three')" in buf.getvalue()
        assert "CREATE TABLE sometable (\n    data pgenum\n)" in buf.getvalue()

    def test_offline_inline_enum_drop(self):
        self._inline_enum_script()
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.rid, sql=True)
        assert "DROP TABLE sometable" in buf.getvalue()
        # no drop since we didn't emit events
        assert "DROP TYPE pgenum" not in buf.getvalue()

    @requires_09
    def test_offline_distinct_enum_create(self):
        self._distinct_enum_script()
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.rid, sql=True)
        assert "CREATE TYPE pgenum AS ENUM ('one', 'two', 'three')" in buf.getvalue()
        assert "CREATE TABLE sometable (\n    data pgenum\n)" in buf.getvalue()

    def test_offline_distinct_enum_drop(self):
        self._distinct_enum_script()
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.rid, sql=True)
        assert "DROP TABLE sometable" in buf.getvalue()
        assert "DROP TYPE pgenum" in buf.getvalue()


class PostgresqlInlineLiteralTest(TestCase):
    @classmethod
    def setup_class(cls):
        cls.bind = db_for_dialect("postgresql")
        cls.bind.execute("""
            create table tab (
                col varchar(50)
            )
        """)
        cls.bind.execute("""
            insert into tab (col) values
                ('old data 1'),
                ('old data 2.1'),
                ('old data 3')
        """)

    @classmethod
    def teardown_class(cls):
        cls.bind.execute("drop table tab")

    def setUp(self):
        self.conn = self.bind.connect()
        ctx = MigrationContext.configure(self.conn)
        self.op = Operations(ctx)

    def tearDown(self):
        self.conn.close()

    def test_inline_percent(self):
        # TODO: here's the issue, you need to escape this.
        tab = table('tab', column('col'))
        self.op.execute(
            tab.update().where(
                tab.c.col.like(self.op.inline_literal('%.%'))
            ).values(col=self.op.inline_literal('new data')),
            execution_options={'no_parameters': True}
        )
        eq_(
            self.conn.execute("select count(*) from tab where col='new data'").scalar(),
            1,
        )

class PostgresqlDefaultCompareTest(TestCase):
    @classmethod
    def setup_class(cls):
        cls.bind = db_for_dialect("postgresql")
        staging_env()
        context = MigrationContext.configure(
            connection=cls.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True
            }
        )
        connection = context.bind
        cls.autogen_context = {
            'imports': set(),
            'connection': connection,
            'dialect': connection.dialect,
            'context': context
            }

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def setUp(self):
        self.metadata = MetaData(self.bind)

    def tearDown(self):
        self.metadata.drop_all()

    def _compare_default_roundtrip(self, type_, txt, alternate=None):
        if alternate:
            expected = True
        else:
            alternate = txt
            expected = False
        t = Table("test", self.metadata,
            Column("somecol", type_, server_default=text(txt))
        )
        t2 = Table("test", MetaData(),
            Column("somecol", type_, server_default=text(alternate))
        )
        assert self._compare_default(
            t, t2, t2.c.somecol, alternate
        ) is expected

    def _compare_default(
        self,
        t1, t2, col,
        rendered
    ):
        t1.create(self.bind)
        insp = Inspector.from_engine(self.bind)
        cols = insp.get_columns(t1.name)
        ctx = self.autogen_context['context']
        return ctx.impl.compare_server_default(
            None,
            col,
            rendered,
            cols[0]['default'])

    def test_compare_current_timestamp(self):
        self._compare_default_roundtrip(
            DateTime(),
            "TIMEZONE('utc', CURRENT_TIMESTAMP)",
        )

    def test_compare_integer(self):
        self._compare_default_roundtrip(
            Integer(),
            "5",
        )

    def test_compare_integer_diff(self):
        self._compare_default_roundtrip(
            Integer(),
            "5", "7"
        )

    def test_compare_character_diff(self):
        self._compare_default_roundtrip(
            String(),
            "'hello'",
            "'there'"
        )

    def test_primary_key_skip(self):
        """Test that SERIAL cols are just skipped"""
        t1 = Table("sometable", self.metadata,
            Column("id", Integer, primary_key=True)
        )
        t2 = Table("sometable", MetaData(),
            Column("id", Integer, primary_key=True)
        )
        assert not self._compare_default(
            t1, t2, t2.c.id, ""
        )

########NEW FILE########
__FILENAME__ = test_revision_create
from tests import clear_staging_env, staging_env, eq_, ne_, is_, staging_directory
from tests import _no_sql_testing_config, env_file_fixture, script_file_fixture, _testing_config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext
from alembic import util
import os
import unittest
import datetime

env, abc, def_ = None, None, None

class GeneralOrderedTests(unittest.TestCase):
    def test_001_environment(self):
        assert_set = set(['env.py', 'script.py.mako', 'README'])
        eq_(
            assert_set.intersection(os.listdir(env.dir)),
            assert_set
        )

    def test_002_rev_ids(self):
        global abc, def_
        abc = util.rev_id()
        def_ = util.rev_id()
        ne_(abc, def_)

    def test_003_api_methods_clean(self):
        eq_(env.get_heads(), [])

        eq_(env.get_base(), None)

    def test_004_rev(self):
        script = env.generate_revision(abc, "this is a message", refresh=True)
        eq_(script.doc, "this is a message")
        eq_(script.revision, abc)
        eq_(script.down_revision, None)
        assert os.access(
            os.path.join(env.dir, 'versions', '%s_this_is_a_message.py' % abc), os.F_OK)
        assert callable(script.module.upgrade)
        eq_(env.get_heads(), [abc])
        eq_(env.get_base(), abc)

    def test_005_nextrev(self):
        script = env.generate_revision(def_, "this is the next rev", refresh=True)
        assert os.access(
            os.path.join(env.dir, 'versions', '%s_this_is_the_next_rev.py' % def_), os.F_OK)
        eq_(script.revision, def_)
        eq_(script.down_revision, abc)
        eq_(env._revision_map[abc].nextrev, set([def_]))
        assert script.module.down_revision == abc
        assert callable(script.module.upgrade)
        assert callable(script.module.downgrade)
        eq_(env.get_heads(), [def_])
        eq_(env.get_base(), abc)

    def test_006_from_clean_env(self):
        # test the environment so far with a
        # new ScriptDirectory instance.

        env = staging_env(create=False)
        abc_rev = env._revision_map[abc]
        def_rev = env._revision_map[def_]
        eq_(abc_rev.nextrev, set([def_]))
        eq_(abc_rev.revision, abc)
        eq_(def_rev.down_revision, abc)
        eq_(env.get_heads(), [def_])
        eq_(env.get_base(), abc)

    def test_007_no_refresh(self):
        rid = util.rev_id()
        script = env.generate_revision(rid, "dont' refresh")
        is_(script, None)
        env2 = staging_env(create=False)
        eq_(env2._as_rev_number("head"), rid)

    def test_008_long_name(self):
        rid = util.rev_id()
        env.generate_revision(rid,
                "this is a really long name with "
                "lots of characters and also "
                "I'd like it to\nhave\nnewlines")
        assert os.access(
            os.path.join(env.dir, 'versions',
                    '%s_this_is_a_really_long_name_with_lots_of_.py' % rid),
                os.F_OK)


    def test_009_long_name_configurable(self):
        env.truncate_slug_length = 60
        rid = util.rev_id()
        env.generate_revision(rid,
                "this is a really long name with "
                "lots of characters and also "
                "I'd like it to\nhave\nnewlines")
        assert os.access(
            os.path.join(env.dir, 'versions',
                    '%s_this_is_a_really_long_name_with_lots_'
                    'of_characters_and_also_.py' % rid),
                os.F_OK)


    @classmethod
    def setup_class(cls):
        global env
        env = staging_env()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

class ScriptNamingTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        _testing_config()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_args(self):
        script = ScriptDirectory(
                        staging_directory,
                        file_template="%(rev)s_%(slug)s_"
                            "%(year)s_%(month)s_"
                            "%(day)s_%(hour)s_"
                            "%(minute)s_%(second)s"
                    )
        create_date = datetime.datetime(2012, 7, 25, 15, 8, 5)
        eq_(
            script._rev_path("12345", "this is a message", create_date),
            "%s/versions/12345_this_is_a_"
            "message_2012_7_25_15_8_5.py" % staging_directory
        )


class TemplateArgsTest(unittest.TestCase):
    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config(
            directives="\nrevision_environment=true\n"
        )

    def tearDown(self):
        clear_staging_env()

    def test_args_propagate(self):
        config = _no_sql_testing_config()
        script = ScriptDirectory.from_config(config)
        template_args = {"x": "x1", "y": "y1", "z": "z1"}
        env = EnvironmentContext(
            config,
            script,
            template_args=template_args
        )
        env.configure(dialect_name="sqlite",
                        template_args={"y": "y2", "q": "q1"})
        eq_(
            template_args,
            {"x": "x1", "y": "y2", "z": "z1", "q": "q1"}
        )

    def test_tmpl_args_revision(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite', template_args={"somearg":"somevalue"})
""")
        script_file_fixture("""
# somearg: ${somearg}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
""")
        command.revision(self.cfg, message="some rev")
        script = ScriptDirectory.from_config(self.cfg)
        rev = script.get_revision('head')
        with open(rev.path) as f:
            text = f.read()
        assert "somearg: somevalue" in text


########NEW FILE########
__FILENAME__ = test_revision_paths
from tests import clear_staging_env, staging_env, eq_, \
    assert_raises_message
from alembic import util

env = None
a, b, c, d, e = None, None, None, None, None
cfg = None

def setup():
    global env
    env = staging_env()
    global a, b, c, d, e
    a = env.generate_revision(util.rev_id(), '->a', refresh=True)
    b = env.generate_revision(util.rev_id(), 'a->b', refresh=True)
    c = env.generate_revision(util.rev_id(), 'b->c', refresh=True)
    d = env.generate_revision(util.rev_id(), 'c->d', refresh=True)
    e = env.generate_revision(util.rev_id(), 'd->e', refresh=True)

def teardown():
    clear_staging_env()


def test_upgrade_path():

    eq_(
        env._upgrade_revs(e.revision, c.revision),
        [
            (d.module.upgrade, c.revision, d.revision, d.doc),
            (e.module.upgrade, d.revision, e.revision, e.doc),
        ]
    )

    eq_(
        env._upgrade_revs(c.revision, None),
        [
            (a.module.upgrade, None, a.revision, a.doc),
            (b.module.upgrade, a.revision, b.revision, b.doc),
            (c.module.upgrade, b.revision, c.revision, c.doc),
        ]
    )

def test_relative_upgrade_path():
    eq_(
        env._upgrade_revs("+2", a.revision),
        [
            (b.module.upgrade, a.revision, b.revision, b.doc),
            (c.module.upgrade, b.revision, c.revision, c.doc),
        ]
    )

    eq_(
        env._upgrade_revs("+1", a.revision),
        [
            (b.module.upgrade, a.revision, b.revision, b.doc),
        ]
    )

    eq_(
        env._upgrade_revs("+3", b.revision),
        [
            (c.module.upgrade, b.revision, c.revision, c.doc),
            (d.module.upgrade, c.revision, d.revision, d.doc),
            (e.module.upgrade, d.revision, e.revision, e.doc),
        ]
    )

def test_invalid_relative_upgrade_path():
    assert_raises_message(
        util.CommandError,
        "Relative revision -2 didn't produce 2 migrations",
        env._upgrade_revs, "-2", b.revision
    )

    assert_raises_message(
        util.CommandError,
        r"Relative revision \+5 didn't produce 5 migrations",
        env._upgrade_revs, "+5", b.revision
    )

def test_downgrade_path():

    eq_(
        env._downgrade_revs(c.revision, e.revision),
        [
            (e.module.downgrade, e.revision, e.down_revision, e.doc),
            (d.module.downgrade, d.revision, d.down_revision, d.doc),
        ]
    )

    eq_(
        env._downgrade_revs(None, c.revision),
        [
            (c.module.downgrade, c.revision, c.down_revision, c.doc),
            (b.module.downgrade, b.revision, b.down_revision, b.doc),
            (a.module.downgrade, a.revision, a.down_revision, a.doc),
        ]
    )

def test_relative_downgrade_path():
    eq_(
        env._downgrade_revs("-1", c.revision),
        [
            (c.module.downgrade, c.revision, c.down_revision, c.doc),
        ]
    )

    eq_(
        env._downgrade_revs("-3", e.revision),
        [
            (e.module.downgrade, e.revision, e.down_revision, e.doc),
            (d.module.downgrade, d.revision, d.down_revision, d.doc),
            (c.module.downgrade, c.revision, c.down_revision, c.doc),
        ]
    )

def test_invalid_relative_downgrade_path():
    assert_raises_message(
        util.CommandError,
        "Relative revision -5 didn't produce 5 migrations",
        env._downgrade_revs, "-5", b.revision
    )

    assert_raises_message(
        util.CommandError,
        r"Relative revision \+2 didn't produce 2 migrations",
        env._downgrade_revs, "+2", b.revision
    )

def test_invalid_move_rev_to_none():
    assert_raises_message(
        util.CommandError,
        "Revision %s is not an ancestor of base" % b.revision,
        env._downgrade_revs, b.revision[0:3], None
    )

def test_invalid_move_higher_to_lower():
    assert_raises_message(
       util.CommandError,
        "Revision %s is not an ancestor of %s" % (c.revision, b.revision),
        env._downgrade_revs, c.revision[0:4], b.revision
    )


########NEW FILE########
__FILENAME__ = test_sqlite
from tests import op_fixture, assert_raises_message
from alembic import op
from sqlalchemy import Integer, Column,  Boolean
from sqlalchemy.sql import column

def test_add_column():
    context = op_fixture('sqlite')
    op.add_column('t1', Column('c1', Integer))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 INTEGER'
    )

def test_add_column_implicit_constraint():
    context = op_fixture('sqlite')
    op.add_column('t1', Column('c1', Boolean))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 BOOLEAN'
    )

def test_add_explicit_constraint():
    context = op_fixture('sqlite')
    assert_raises_message(
        NotImplementedError,
        "No support for ALTER of constraints in SQLite dialect",
        op.create_check_constraint,
        "foo",
        "sometable",
        column('name') > 5
    )

def test_drop_explicit_constraint():
    context = op_fixture('sqlite')
    assert_raises_message(
        NotImplementedError,
        "No support for ALTER of constraints in SQLite dialect",
        op.drop_constraint,
        "foo",
        "sometable",
    )


########NEW FILE########
__FILENAME__ = test_sql_script
# coding: utf-8

from __future__ import unicode_literals

import unittest

from . import clear_staging_env, staging_env, \
    _no_sql_testing_config, capture_context_buffer, \
    three_rev_fixture, write_script
from alembic import command, util
from alembic.script import ScriptDirectory
import re

cfg = None
a, b, c = None, None, None

class ThreeRevTest(unittest.TestCase):

    def setUp(self):
        global cfg, env
        env = staging_env()
        cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')
        global a, b, c
        a, b, c = three_rev_fixture(cfg)

    def tearDown(self):
        clear_staging_env()

    def test_begin_commit_transactional_ddl(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(cfg, c, sql=True)
        assert re.match(
                    (r"^BEGIN;\s+CREATE TABLE.*?%s.*" % a) +
                    (r".*%s" % b) +
                    (r".*%s.*?COMMIT;.*$" % c),

                buf.getvalue(), re.S)

    def test_begin_commit_nontransactional_ddl(self):
        with capture_context_buffer(transactional_ddl=False) as buf:
            command.upgrade(cfg, a, sql=True)
        assert re.match(r"^CREATE TABLE.*?\n+$", buf.getvalue(), re.S)
        assert "COMMIT;" not in buf.getvalue()

    def test_begin_commit_per_rev_ddl(self):
        with capture_context_buffer(transaction_per_migration=True) as buf:
            command.upgrade(cfg, c, sql=True)
        assert re.match(
                    (r"^BEGIN;\s+CREATE TABLE.*%s.*?COMMIT;.*" % a) +
                    (r"BEGIN;.*?%s.*?COMMIT;.*" % b) +
                    (r"BEGIN;.*?%s.*?COMMIT;.*$" % c),

                buf.getvalue(), re.S)

    def test_version_from_none_insert(self):
        with capture_context_buffer() as buf:
            command.upgrade(cfg, a, sql=True)
        assert "CREATE TABLE alembic_version" in buf.getvalue()
        assert "INSERT INTO alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" not in buf.getvalue()

    def test_version_from_middle_update(self):
        with capture_context_buffer() as buf:
            command.upgrade(cfg, "%s:%s" % (b, c), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "UPDATE alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" not in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" in buf.getvalue()

    def test_version_to_none(self):
        with capture_context_buffer() as buf:
            command.downgrade(cfg, "%s:base" % c, sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" in buf.getvalue()

    def test_version_to_middle(self):
        with capture_context_buffer() as buf:
            command.downgrade(cfg, "%s:%s" % (c, a), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" not in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" not in buf.getvalue()

    def test_stamp(self):
        with capture_context_buffer() as buf:
            command.stamp(cfg, "head", sql=True)
        assert "UPDATE alembic_version SET version_num='%s';" % c in buf.getvalue()


class EncodingTest(unittest.TestCase):
    def setUp(self):
        global cfg, env, a
        env = staging_env()
        cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')
        a = util.rev_id()
        script = ScriptDirectory.from_config(cfg)
        script.generate_revision(a, "revision a", refresh=True)
        write_script(script, a, ("""# coding: utf-8
from __future__ import unicode_literals
revision = '%s'
down_revision = None

from alembic import op

def upgrade():
    op.execute("« S’il vous plaît…")

def downgrade():
    op.execute("drôle de petite voix m’a réveillé")

""" % a), encoding='utf-8')

    def tearDown(self):
        clear_staging_env()

    def test_encode(self):
        with capture_context_buffer(
                    bytes_io=True,
                    output_encoding='utf-8'
                ) as buf:
            command.upgrade(cfg, a, sql=True)
        assert "« S’il vous plaît…".encode("utf-8") in buf.getvalue()

########NEW FILE########
__FILENAME__ = test_versioning
import os
import unittest

from alembic import command, util
from alembic.script import ScriptDirectory
from . import clear_staging_env, staging_env, \
    _sqlite_testing_config, sqlite_db, eq_, write_script, \
    assert_raises_message

class VersioningTest(unittest.TestCase):
    sourceless = False

    def test_001_revisions(self):
        global a, b, c
        a = util.rev_id()
        b = util.rev_id()
        c = util.rev_id()

        script = ScriptDirectory.from_config(self.cfg)
        script.generate_revision(a, None, refresh=True)
        write_script(script, a, """
    revision = '%s'
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """ % a, sourceless=self.sourceless)

        script.generate_revision(b, None, refresh=True)
        write_script(script, b, """
    revision = '%s'
    down_revision = '%s'

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE bar(id integer)")

    def downgrade():
        op.execute("DROP TABLE bar")

    """ % (b, a), sourceless=self.sourceless)

        script.generate_revision(c, None, refresh=True)
        write_script(script, c, """
    revision = '%s'
    down_revision = '%s'

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE bat(id integer)")

    def downgrade():
        op.execute("DROP TABLE bat")

    """ % (c, b), sourceless=self.sourceless)


    def test_002_upgrade(self):
        command.upgrade(self.cfg, c)
        db = sqlite_db()
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert db.dialect.has_table(db.connect(), 'bat')

    def test_003_downgrade(self):
        command.downgrade(self.cfg, a)
        db = sqlite_db()
        assert db.dialect.has_table(db.connect(), 'foo')
        assert not db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def test_004_downgrade(self):
        command.downgrade(self.cfg, 'base')
        db = sqlite_db()
        assert not db.dialect.has_table(db.connect(), 'foo')
        assert not db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def test_005_upgrade(self):
        command.upgrade(self.cfg, b)
        db = sqlite_db()
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def test_006_upgrade_again(self):
        command.upgrade(self.cfg, b)


    # TODO: test some invalid movements

    @classmethod
    def setup_class(cls):
        cls.env = staging_env(sourceless=cls.sourceless)
        cls.cfg = _sqlite_testing_config(sourceless=cls.sourceless)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

class VersionNameTemplateTest(unittest.TestCase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    def test_option(self):
        self.cfg.set_main_option("file_template", "myfile_%%(slug)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, "some message", refresh=True)
        write_script(script, a, """
    revision = '%s'
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """ % a)

        script = ScriptDirectory.from_config(self.cfg)
        rev = script._get_rev(a)
        eq_(rev.revision, a)
        eq_(os.path.basename(rev.path), "myfile_some_message.py")

    def test_lookup_legacy(self):
        self.cfg.set_main_option("file_template", "%%(rev)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, None, refresh=True)
        write_script(script, a, """
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """)

        script = ScriptDirectory.from_config(self.cfg)
        rev = script._get_rev(a)
        eq_(rev.revision, a)
        eq_(os.path.basename(rev.path), "%s.py" % a)

    def test_error_on_new_with_missing_revision(self):
        self.cfg.set_main_option("file_template", "%%(slug)s_%%(rev)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, "foobar", refresh=True)
        assert_raises_message(
            util.CommandError,
            "Could not determine revision id from filename foobar_%s.py. "
            "Be sure the 'revision' variable is declared "
            "inside the script." % a,
            write_script, script, a, """
        down_revision = None

        from alembic import op

        def upgrade():
            op.execute("CREATE TABLE foo(id integer)")

        def downgrade():
            op.execute("DROP TABLE foo")

        """)


class SourcelessVersioningTest(VersioningTest):
    sourceless = True

class SourcelessNeedsFlagTest(unittest.TestCase):
    def setUp(self):
        self.env = staging_env(sourceless=False)
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    def test_needs_flag(self):
        a = util.rev_id()

        script = ScriptDirectory.from_config(self.cfg)
        script.generate_revision(a, None, refresh=True)
        write_script(script, a, """
    revision = '%s'
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """ % a, sourceless=True)

        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.get_heads(), [])

        self.cfg.set_main_option("sourceless", "true")
        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.get_heads(), [a])

########NEW FILE########
__FILENAME__ = test_version_table
import unittest

from sqlalchemy import Table, MetaData, Column, String, create_engine
from sqlalchemy.engine.reflection import Inspector

from alembic.util import CommandError

version_table = Table('version_table', MetaData(),
                      Column('version_num', String(32), nullable=False))

class TestMigrationContext(unittest.TestCase):
    _bind = []

    @property
    def bind(self):
        if not self._bind:
            engine = create_engine('sqlite:///', echo=True)
            self._bind.append(engine)
        return self._bind[0]

    def setUp(self):
        self.connection = self.bind.connect()
        self.transaction = self.connection.begin()

    def tearDown(self):
        version_table.drop(self.connection, checkfirst=True)
        self.transaction.rollback()

    def make_one(self, **kwargs):
        from alembic.migration import MigrationContext
        return MigrationContext.configure(**kwargs)

    def get_revision(self):
        result = self.connection.execute(version_table.select())
        rows = result.fetchall()
        if len(rows) == 0:
            return None
        self.assertEqual(len(rows), 1)
        return rows[0]['version_num']

    def test_config_default_version_table_name(self):
        context = self.make_one(dialect_name='sqlite')
        self.assertEqual(context._version.name, 'alembic_version')

    def test_config_explicit_version_table_name(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'version_table': 'explicit'})
        self.assertEqual(context._version.name, 'explicit')

    def test_config_explicit_version_table_schema(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'version_table_schema': 'explicit'})
        self.assertEqual(context._version.schema, 'explicit')

    def test_get_current_revision_creates_version_table(self):
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        self.assertEqual(context.get_current_revision(), None)
        insp = Inspector(self.connection)
        self.assertTrue('version_table' in insp.get_table_names())

    def test_get_current_revision(self):
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        version_table.create(self.connection)
        self.assertEqual(context.get_current_revision(), None)
        self.connection.execute(
            version_table.insert().values(version_num='revid'))
        self.assertEqual(context.get_current_revision(), 'revid')

    def test_get_current_revision_error_if_starting_rev_given_online(self):
        context = self.make_one(connection=self.connection,
                                opts={'starting_rev': 'boo'})
        self.assertRaises(CommandError, context.get_current_revision)

    def test_get_current_revision_offline(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'starting_rev': 'startrev',
                                      'as_sql': True})
        self.assertEqual(context.get_current_revision(), 'startrev')

    def test__update_current_rev(self):
        version_table.create(self.connection)
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})

        context._update_current_rev(None, 'a')
        self.assertEqual(self.get_revision(), 'a')
        context._update_current_rev('a', 'b')
        self.assertEqual(self.get_revision(), 'b')
        context._update_current_rev('b', None)
        self.assertEqual(self.get_revision(), None)

########NEW FILE########
