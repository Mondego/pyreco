__FILENAME__ = base
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from .utils import _setup_joins_for_fields
from .tree import AND, OR

import sys

if sys.version_info[0] == 3:
    basestring = str

class SqlNode(object):
    negated = False

    sql_negated_template = "NOT %s"

    @property
    def field_parts(self):
        raise NotImplementedError

    def as_sql(self, qn, queryset):
        raise NotImplementedError

    def __invert__(self):
        # TODO: use clone insetead self modification.
        self.negated = True
        return self


class SqlExpression(SqlNode):
    sql_template = "%(field)s %(operator)s %%s"

    def __init__(self, field_or_func, operator, value=None, **kwargs):
        self.operator = operator
        self.value = value
        self.extra = kwargs

        if isinstance(field_or_func, SqlNode):
            self.field = field_or_func.field
            self.sql_function = field_or_func
        else:
            self.field = field_or_func
            self.sql_function = None

    @property
    def field_parts(self):
        return self.field.split("__")

    def as_sql(self, qn, queryset):
        """
        Return the statement rendered as sql.
        """

        # setup joins if needed
        if self.sql_function is None:
            _setup_joins_for_fields(self.field_parts, self, queryset)

        # build sql
        params, args = {}, []

        if self.operator is not None:
            params['operator'] = self.operator

        if self.sql_function is None:
            if isinstance(self.field, basestring):
                params['field'] = qn(self.field)
            elif isinstance(self.field, (tuple, list)):
                _tbl, _fld, _alias = self.field
                if _tbl == _alias:
                    params['field'] = "%s.%s" % (qn(_tbl), qn(_fld))
                else:
                    params['field'] = "%s.%s" % (_alias, qn(_fld))
            else:
                raise ValueError("Invalid field value")
        else:
            params['field'], _args = self.sql_function.as_sql(qn, queryset)
            args.extend(_args)

        params.update(self.extra)
        if self.value is not None:
            args.extend([self.value])

        template_result = self.sql_template % params

        if self.negated:
            return self.sql_negated_template % (template_result), args

        return template_result, args


class RawExpression(SqlExpression):
    field_parts = []

    def __init__(self, sqlstatement, *args):
        self.statement = sqlstatement
        self.params = args

    def as_sql(self, qn, queryset):
        return self.statement, self.params


# TODO: add function(function()) feature.

class SqlFunction(SqlNode):
    sql_template = '%(function)s(%(field)s)'
    sql_function = None
    args = []

    def __init__(self, field, *args, **kwargs):
        self.field = field
        self.args = args
        self.extern_params = kwargs

    @property
    def field_parts(self):
        return self.field.split("__")

    def as_sql(self, qn, queryset):
        """
        Return the aggregate/annotation rendered as sql.
        """

        _setup_joins_for_fields(self.field_parts, self, queryset)

        params = {}
        if self.sql_function is not None:
            params['function'] = self.sql_function
        if isinstance(self.field, basestring):
            params['field'] = qn(self.field)
        elif isinstance(self.field, (tuple, list)):
            _tbl, _fld, _alias = self.field
            if _tbl == _alias:
                params['field'] = "%s.%s" % (qn(_tbl), qn(_fld))
            else:
                params['field'] = "%s.%s" % (_alias, qn(_fld))
            #_tbl, _fld = self.field
            #params['field'] = "%s.%s" % (qn(_tbl), qn(_fld))
        else:
            raise ValueError("Invalid field value")

        params.update(self.extern_params)
        return self.sql_template % params, self.args

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.utils.datastructures import SortedDict
from django.db.models.sql.where import ExtraWhere
from django.db.models.query import QuerySet
from django.db import models

from .base import AND


class ExpressionQuerySetMixin(object):
    def annotate_functions(self, **kwargs):
        extra_select, params = SortedDict(), []
        clone = self._clone()

        for alias, node in kwargs.items():
            _sql, _params = node.as_sql(self.quote_name, self)

            extra_select[alias] = _sql
            params.extend(_params)

        clone.query.add_extra(extra_select, params, None, None, None, None)
        return clone

    def where(self, *args):
        clone = self._clone()
        statement = AND(*args)

        _sql, _params = statement.as_sql(self.quote_name, clone)
        if hasattr(_sql, 'to_str'):
            _sql = _sql.to_str()

        clone.query.where.add(ExtraWhere([_sql], _params), "AND")
        return clone

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name



class ExpressionManagerMixin(object):
    def annotate_functions(self, **kwargs):
        return self.get_query_set().annotate_functions(**kwargs)

    def where(self, *args):
        return self.get_query_set().where(*args)


class ExpressionQuerySet(ExpressionQuerySetMixin, QuerySet):
    """
    Predefined expression queryset. Usefull if you only use expresions.
    """
    pass


class ExpressionManager(ExpressionManagerMixin, models.Manager):
    """
    Prededined expression manager what uses `ExpressionQuerySet`.
    """

    use_for_related_fields = True

    def get_query_set(self):
        return ExpressionQuerySet(model=self.model, using=self._db)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.db import models

from ..models import ExpressionManager

class Person(models.Model):
    name = models.CharField(max_length=200)
    objects = ExpressionManager()


class Profile(models.Model):
    person = models.ForeignKey("Person", related_name="profiles")
    objects = ExpressionManager()


class Node(models.Model):
    name = models.CharField(max_length=200)
    parent = models.ForeignKey("self", related_name="childs",
                                        null=True, default=None)

    objects = ExpressionManager()

########NEW FILE########
__FILENAME__ = tree
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.utils import tree
from django.db.models.sql.datastructures import MultiJoin

# Python3 compatibility
import sys

if sys.version_info[0] == 3:
    text = str
else:
    text = unicode


class CommonBaseTree(tree.Node):
    """
    Encapsulates filters as objects that can then be combined logically (using
    & and |).
    """
    # Connection types
    AND = 'AND'
    OR = 'OR'
    default = AND
    query = None

    def __init__(self, *args, **kwargs):
        super(CommonBaseTree, self).__init__(children=list(args) + list(kwargs.items()))

    def _combine(self, other, conn):
        if not isinstance(other, (BaseTree)):
            raise TypeError(other)
        obj = type(self)()
        obj.add(self, conn)
        obj.add(other, conn)
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def __invert__(self):
        obj = type(self)()
        obj.add(self, self.AND)
        obj.negate()
        return obj

    def set_query(self, query):
        self.query = query
        return self


class RawSQL(object):
    def __init__(self, items, connector, query=None):
        self.items = items
        self.connector = connector
        self.query = query

    if sys.version_info[0] == 3:
        def __str__(self):
            connector = " %s " % (self.connector)
            return connector.join(self.items)
    else:
        def __str__(self):
            connector = b" %s " % (self.connector)
            return connector.join(self.items)

        def __unicode__(self):
            return self.__str__().decode('utf-8')

    def to_str(self, closure=False):
        if closure:
            return "(%s)" % text(self)
        return text(self)


class OperatorTree(CommonBaseTree):
    """
    Base operator node class.
    """
    def as_sql(self, qn, queryset):
        items, params = [], []

        for child in self.children:
            _sql, _params = child.as_sql(qn, queryset)

            if isinstance(_sql, RawSQL):
                _sql = _sql.to_str(True)

            items.extend([_sql])
            params.extend(_params)

        sql_obj = RawSQL(items, self._connector, queryset)
        return sql_obj, params


class AND(OperatorTree):
    _connector = "AND"


class OR(OperatorTree):
    _connector = "OR"

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import django
from django.db.models.fields import FieldDoesNotExist


def _setup_joins_for_fields(parts, node, queryset):
    version = django.VERSION[:2]
    version_lt_1_5, version_gt_1_5, version_ge_1_7 = version < (1, 5), version >= (1, 6), version >= (1, 7)

    parts_num = len(parts)
    if parts_num == 0:
        return

    if parts_num == 1:
        node.field = (queryset.model._meta.db_table, parts[0])

    setup_joins_args = (parts, queryset.model._meta,
                        queryset.query.get_initial_alias())
    if version_gt_1_5:
        # Django 1.6+ compatibility.
        field, source, opts, join_list, last = queryset.query.setup_joins(
            *setup_joins_args)
    else:
        field, source, opts, join_list, last, _ = queryset.query.setup_joins(
            *setup_joins_args, dupe_multis=False)

    # Process the join chain to see if it can be trimmed
    if version_gt_1_5:
        # Django 1.6+ compatibility.
        trim_joins_args = source, join_list, last
    else:
        trim_joins_args = source, join_list, last, False

    col, alias, join_list = queryset.query.trim_joins(*trim_joins_args)

    if version_lt_1_5:
        for column_alias in join_list:
            queryset.query.promote_alias(column_alias, unconditional=True)
    elif version_ge_1_7:
        # Django 1.7+ compatibility
        queryset.query.promote_joins(join_list)
    else:
        # Django 1.5-1.6 compatibility
        queryset.query.promote_joins(join_list, unconditional=True)

    # this works for one level of depth
    #lookup_model = self.query.model._meta.get_field(parts[-2]).rel.to
    #lookup_field = lookup_model._meta.get_field(parts[-1])

    if parts_num >= 2:
        lookup_model = queryset.model
        for counter, field_name in enumerate(parts):
            try:
                lookup_field = lookup_model._meta.get_field_by_name(field_name)[0]
                if hasattr(lookup_field, 'field'):
                    # this step is needed for backwards relations
                    lookup_field = lookup_field.field
            except FieldDoesNotExist:
                parts.pop()
                break

            try:
                lookup_model = lookup_field.rel.to
            except AttributeError:
                parts.pop()
                break

        node.field = (lookup_model._meta.db_table, lookup_field.attname)
    node.field = node.field + (alias,)

########NEW FILE########
__FILENAME__ = runtests
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from django.core.management import call_command

if __name__ == "__main__":
    args = sys.argv[1:]
    call_command("test", *args, verbosity=2)

########NEW FILE########
__FILENAME__ = settings
import os, sys

sys.path.insert(0, '..')

PROJECT_ROOT = os.path.dirname(__file__)
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

SECRET_KEY = 'di!n($kqa3)nd%ikad#kcjpkd^uw*h%*kj=*pm7$vbo6ir7h=l'
INSTALLED_APPS = (
    'djorm_core',
    'djorm_expressions',
    'djorm_expressions.tests',
)

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

########NEW FILE########
