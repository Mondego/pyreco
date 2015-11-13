__FILENAME__ = helpers
from collections import defaultdict


def queryset_to_dict(qs, key='pk', singular=True):
    """
    Given a queryset will transform it into a dictionary based on ``key``.
    """
    if singular:
        result = {}
        for u in qs:
            result.setdefault(getattr(u, key), u)
    else:
        result = defaultdict(list)
        for u in qs:
            result[getattr(u, key)].append(u)
    return result


def distinct(l):
    """
    Given an iterable will return a list of all distinct values.
    """
    return list(set(l))


from django.db.models.fields.related import SingleRelatedObjectDescriptor


def attach_foreignkey(objects, field, related=[], database='default'):
    """
    Shortcut method which handles a pythonic LEFT OUTER JOIN.

    ``attach_foreignkey(posts, Post.thread)``

    Works with both ForeignKey and OneToOne (reverse) lookups.
    """
    is_foreignkey = isinstance(field, SingleRelatedObjectDescriptor)

    if not is_foreignkey:
        field = field.field
        accessor = '_%s_cache' % field.name
        model = field.rel.to
        lookup = 'pk'
        column = field.column
        key = lookup
    else:
        accessor = field.cache_name
        field = field.related.field
        model = field.model
        lookup = field.name
        column = 'pk'
        key = field.column

    # Ensure values are unique, do not contain already present values, and are not missing
    # values specified in select_related
    values = distinct(getattr(o, column) for o in objects if (related or getattr(o, accessor, False) is False))
    if not values:
        return

    qs = model.objects.filter(**{'%s__in' % lookup: values})\
              .using(database)
    if related:
        qs = qs.select_related(*related)
    queryset = queryset_to_dict(qs, key=key)
    for o in objects:
        setattr(o, accessor, queryset.get(getattr(o, column)))


def attach_foreignkeys(*object_sets, **kwargs):
    """
    Shortcut method which handles a pythonic LEFT OUTER JOIN. Allows you to attach the same object type
    to multiple different sets of data.

    ``attach_foreignkeys((posts, Post.author), (threads, Thread.creator), related=['profile'])``

    Works with only ForeignKeys
    """

    related = kwargs.get('related', [])
    database = kwargs.get('database', 'default')

    values = set()

    model = None

    for objects, field in object_sets:
        if not model:
            model = field.field.rel.to
        elif model != field.field.rel.to:
            raise ValueError('You cannot attach foreign keys that do not reference the same models (%s != %s)' % (model, field.field.rel.to))
        # Ensure values are unique, do not contain already present values, and are not missing
        # values specified in select_related
        values.update(distinct(getattr(o, field.field.column) for o in objects if (related or getattr(o, '_%s_cache' % field.field.name, False) is False)))

    if not values:
        return

    qs = model.objects.filter(pk__in=values).using(database)
    if related:
        qs = qs.select_related(*related)
    queryset = queryset_to_dict(qs)

    for objects, field in object_sets:
        for o in objects:
            setattr(o, '_%s_cache' % field.field.name, queryset.get(getattr(o, field.field.column)))

########NEW FILE########
__FILENAME__ = querysets
from django.db.models.manager import Manager
from django.db.models.query import QuerySet
from django.db.models.fields import AutoField, IntegerField
from django.db.models import Min, Max

from dbutils.helpers import attach_foreignkey


class QuerySetDoubleIteration(Exception):
    "A QuerySet was iterated over twice, you probably want to list() it."
    pass


# "Skinny" here means we use iterator by default, rather than
# ballooning in memory.
class SkinnyManager(Manager):
    def get_query_set(self):
        return SkinnyQuerySet(self.model, using=self._db)


class SkinnyQuerySet(QuerySet):
    """
    A QuerySet which eliminates the in-memory result cache.
    """
    def __len__(self):
        if getattr(self, 'has_run_before', False):
            raise TypeError("SkinnyQuerySet doesn't support __len__ after __iter__, if you *only* need a count you should use .count(), if you need to reuse the results you should coerce to a list and then len() that.")
        return super(SkinnyQuerySet, self).__len__()

    def __iter__(self):
        if self._result_cache is not None:
            # __len__ must have been run
            return iter(self._result_cache)

        has_run_before = getattr(self, 'has_run_before', False)
        if has_run_before:
            raise QuerySetDoubleIteration("This SkinnyQuerySet has already been iterated over once, you should assign it to a list if you want to reuse the data.")
        self.has_run_before = True

        return self.iterator()

    def list(self):
        return list(self)


class InvalidQuerySetError(ValueError):
    pass


class IterableQuerySetWrapper(object):
    """
    Iterates through a QuerySet using limit and offset.

    For efficiency use ``RangeQuerySetWrapper``.
    """
    def __init__(self, queryset, step=10000, limit=None):
        self.limit = limit
        if limit:
            self.step = min(limit, step)
        else:
            self.step = step
        self.queryset = queryset

    def __iter__(self):
        at = 0

        results = list(self.queryset[at:(at + self.step)])
        while results and (not self.limit or at < self.limit):
            for result in results:
                yield result
            at += self.step
            results = list(self.queryset[at:(at + self.step)])

    def iterator(self):
        return iter(self)



class RangeQuerySet(SkinnyQuerySet):
    """
    See ``RangeQuerySetWrapper``
    """
    def __init__(self, model, step=10000, sorted=False, *args, **kwargs):
        super(SkinnyQuerySet, self).__init__(model, *args, **kwargs)
        self.step = step
        self.sorted = sorted

    def iterator(self, bypass=False):
        # Only execute if low mark is 0
        if not bypass and self.query.low_mark == 0 and not\
          (self.query.order_by or self.query.extra_order_by):
            # Clear the actual limit/offset
            high_mark = self.query.high_mark
            self.query.clear_limits()
            results = RangeQuerySetWrapper(self, step=self.step, limit=high_mark, sorted=self.sorted)
        elif not bypass:
            results = IterableQuerySetWrapper(self, step=self.step)
        else:
            results = super(RangeQuerySet, self).iterator()
        for result in results:
            yield result


class RangeQuerySetWrapper(object):
    """
    Iterates through a queryset by chunking results by ``step`` and using GREATER THAN
    and LESS THAN queries on the primary key.

    Very efficient, but ORDER BY statements will not work.
    """

    def __init__(self, queryset, step=1000, limit=None, min_id=None, max_id=None, sorted=True,
                 select_related=[], callbacks=[]):
        # Support for slicing
        if queryset.query.low_mark == 0 and not\
          (queryset.query.order_by or queryset.query.extra_order_by):
            if limit is None:
                limit = queryset.query.high_mark
            queryset.query.clear_limits()
        else:
            raise InvalidQuerySetError

        self.limit = limit
        if limit:
            self.step = min(limit, abs(step))
            self.desc = step < 0
        else:
            self.step = abs(step)
            self.desc = step < 0
        self.queryset = queryset
        self.min_id, self.max_id = min_id, max_id
        # if max_id isnt set we sort by default for optimization
        self.sorted = sorted or not max_id
        self.select_related = select_related
        self.callbacks = callbacks

    def __iter__(self):
        pk = self.queryset.model._meta.pk
        if not isinstance(pk, (IntegerField, AutoField)):
            for result in iter(IterableQuerySetWrapper(self.queryset, self.step, self.limit)):
                yield result
        else:
            max_id = self.max_id
            if self.min_id is not None:
                at = self.min_id
            elif not self.sorted:
                at = 0
            else:
                at = None

            num = 0
            limit = self.limit or max_id

            if isinstance(self.queryset, RangeQuerySet):
                extra_kwargs = {'bypass': True}
            else:
                extra_kwargs = {}

            has_results = True
            while ((max_id and at <= max_id) or has_results) and (not self.limit or num < self.limit):
                start = num

                if at is None:
                    results = self.queryset
                elif self.desc:
                    results = self.queryset.filter(id__lte=at)
                elif not self.desc:
                    results = self.queryset.filter(id__gte=at)

                # Adjust the sort order if we're stepping through reverse
                if self.sorted:
                    if self.desc:
                        results = results.order_by('-id')
                    else:
                        results = results.order_by('id')

                if self.max_id:
                    results = results.filter(id__lte=max_id)

                results = results[:self.step].iterator(**extra_kwargs)
                if self.select_related:
                    # we have to pull them all into memory to do the select_related
                    results = list(results)
                    for fkey in self.select_related:
                        if '__' in fkey:
                            fkey, related = fkey.split('__')
                        else:
                            related = []
                        attach_foreignkey(results, getattr(self.queryset.model, fkey, related))

                if self.callbacks:
                    results = list(results)
                    for callback in self.callbacks:
                        callback(results)

                for result in results:
                    yield result
                    num += 1
                    at = result.id
                    if (max_id and result.id >= max_id) or (limit and num >= limit):
                        break

                if at is None:
                    break

                has_results = num > start
                if self.desc:
                    at -= 1
                else:
                    at += 1

########NEW FILE########
