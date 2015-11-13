__FILENAME__ = admin
# -*- coding: utf-8 -*-
from django.contrib import admin
from example.testapp.models import Car, ParkingArea


class ParkingAreaAdmin(admin.ModelAdmin):
    fieldsets = (
        ('bla', {
            'classes': ('wide',),
            'fields': (
                'name',
                'cars',
            ),
        }),
    )


admin.site.register(Car)
admin.site.register(ParkingArea, ParkingAreaAdmin)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from sortedm2m.fields import SortedManyToManyField


class Car(models.Model):
    plate = models.CharField(max_length=50)

    def __unicode__(self):
        return self.plate


class ParkingArea(models.Model):
    name = models.CharField(max_length=50)
    cars = SortedManyToManyField(Car)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'parkingarea', (self.pk,), {}

########NEW FILE########
__FILENAME__ = views
from django.views.generic import UpdateView
from .models import ParkingArea


class ParkingAreaUpdate(UpdateView):
    model = ParkingArea


parkingarea_update = ParkingAreaUpdate.as_view()

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
from django.http import HttpResponse


admin.autodiscover()

def handle404(request):
    return HttpResponse('404')
def handle500(request):
    return HttpResponse('404')

handler404 = 'example.urls.handle404'
handler500 = 'example.urls.handle500'


urlpatterns = patterns('',
    url(r'^media/(.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    url(r'^admin/', include(admin.site.urls), name="admin"),
    url(r'^parkingarea/(?P<pk>\d+)/$', 'example.testapp.views.parkingarea_update', name='parkingarea'),
    url(r'^', include('django.contrib.staticfiles.urls')),
)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys


parent = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, parent)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")


import django
from django.core.management import call_command


if django.VERSION < (1, 6):
    default_test_apps = [
        'sortedm2m_tests',
        'sortedm2m_field',
        'sortedm2m_form',
        'south_support',
        'south_support_new_model',
        'south_support_new_field',
        'south_support_custom_sort_field_name',
    ]
else:
    default_test_apps = [
        'sortedm2m_tests.sortedm2m_field',
        'sortedm2m_tests.sortedm2m_form',
        'sortedm2m_tests.south_support',
        'sortedm2m_tests.south_support.south_support_new_model',
        'sortedm2m_tests.south_support.south_support_new_field',
        'sortedm2m_tests.south_support.south_support_custom_sort_field_name',
    ]


def runtests(*args):
    test_apps = args or default_test_apps
    call_command('test', *test_apps, verbosity=1)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
from operator import attrgetter
import sys
from django.db import connections
from django.db import router
from django.db.models import signals
from django.db.models.fields.related import add_lazy_relation, create_many_related_manager
from django.db.models.fields.related import ManyToManyField, ReverseManyRelatedObjectsDescriptor
from django.db.models.fields.related import RECURSIVE_RELATIONSHIP_CONSTANT
from django.conf import settings
from django.utils.functional import curry
from sortedm2m.forms import SortedMultipleChoiceField


if sys.version_info[0] < 3:
    string_types = basestring
else:
    string_types = str


SORT_VALUE_FIELD_NAME = 'sort_value'


def create_sorted_many_to_many_intermediate_model(field, klass):
    from django.db import models
    managed = True
    if isinstance(field.rel.to, string_types) and field.rel.to != RECURSIVE_RELATIONSHIP_CONSTANT:
        to_model = field.rel.to
        to = to_model.split('.')[-1]
        def set_managed(field, model, cls):
            field.rel.through._meta.managed = model._meta.managed or cls._meta.managed
        add_lazy_relation(klass, field, to_model, set_managed)
    elif isinstance(field.rel.to, string_types):
        to = klass._meta.object_name
        to_model = klass
        managed = klass._meta.managed
    else:
        to = field.rel.to._meta.object_name
        to_model = field.rel.to
        managed = klass._meta.managed or to_model._meta.managed
    name = '%s_%s' % (klass._meta.object_name, field.name)
    if field.rel.to == RECURSIVE_RELATIONSHIP_CONSTANT or to == klass._meta.object_name:
        from_ = 'from_%s' % to.lower()
        to = 'to_%s' % to.lower()
    else:
        from_ = klass._meta.object_name.lower()
        to = to.lower()
    meta = type(str('Meta'), (object,), {
        'db_table': field._get_m2m_db_table(klass._meta),
        'managed': managed,
        'auto_created': klass,
        'app_label': klass._meta.app_label,
        'unique_together': (from_, to),
        'ordering': (field.sort_value_field_name,),
        'verbose_name': '%(from)s-%(to)s relationship' % {'from': from_, 'to': to},
        'verbose_name_plural': '%(from)s-%(to)s relationships' % {'from': from_, 'to': to},
    })
    # Construct and return the new class.
    def default_sort_value(name):
        model = models.get_model(klass._meta.app_label, name)
        return model._default_manager.count()

    default_sort_value = curry(default_sort_value, name)

    return type(str(name), (models.Model,), {
        'Meta': meta,
        '__module__': klass.__module__,
        from_: models.ForeignKey(klass, related_name='%s+' % name),
        to: models.ForeignKey(to_model, related_name='%s+' % name),
        field.sort_value_field_name: models.IntegerField(default=default_sort_value),
        '_sort_field_name': field.sort_value_field_name,
        '_from_field_name': from_,
        '_to_field_name': to,
    })


def create_sorted_many_related_manager(superclass, rel):
    RelatedManager = create_many_related_manager(superclass, rel)

    class SortedRelatedManager(RelatedManager):
        def get_query_set(self):
            # We use ``extra`` method here because we have no other access to
            # the extra sorting field of the intermediary model. The fields
            # are hidden for joins because we set ``auto_created`` on the
            # intermediary's meta options.
            try:
                return self.instance._prefetched_objects_cache[self.prefetch_cache_name]
            except (AttributeError, KeyError):
                return super(SortedRelatedManager, self).\
                    get_query_set().\
                    extra(order_by=['%s.%s' % (
                        rel.through._meta.db_table,
                        rel.through._sort_field_name,
                    )])

        if not hasattr(RelatedManager, '_get_fk_val'):
            @property
            def _fk_val(self):
                return self._pk_val

        def get_prefetch_query_set(self, instances):
            # mostly a copy of get_prefetch_query_set from ManyRelatedManager
            # but with addition of proper ordering
            db = self._db or router.db_for_read(instances[0].__class__, instance=instances[0])
            query = {'%s__pk__in' % self.query_field_name:
                         set(obj._get_pk_val() for obj in instances)}
            qs = super(RelatedManager, self).get_query_set().using(db)._next_is_sticky().filter(**query)

            # M2M: need to annotate the query in order to get the primary model
            # that the secondary model was actually related to. We know that
            # there will already be a join on the join table, so we can just add
            # the select.

            # For non-autocreated 'through' models, can't assume we are
            # dealing with PK values.
            fk = self.through._meta.get_field(self.source_field_name)
            source_col = fk.column
            join_table = self.through._meta.db_table
            connection = connections[db]
            qn = connection.ops.quote_name
            qs = qs.extra(select={'_prefetch_related_val':
                                      '%s.%s' % (qn(join_table), qn(source_col))},
                          order_by=['%s.%s' % (
                    rel.through._meta.db_table,
                    rel.through._sort_field_name,
                )])
            select_attname = fk.rel.get_related_field().get_attname()
            return (qs,
                    attrgetter('_prefetch_related_val'),
                    attrgetter(select_attname),
                    False,
                    self.prefetch_cache_name)

        def _add_items(self, source_field_name, target_field_name, *objs):
            # source_field_name: the PK fieldname in join_table for the source object
            # target_field_name: the PK fieldname in join_table for the target object
            # *objs - objects to add. Either object instances, or primary keys of object instances.

            # If there aren't any objects, there is nothing to do.
            from django.db.models import Model
            if objs:
                new_ids = []
                for obj in objs:
                    if isinstance(obj, self.model):
                        if not router.allow_relation(obj, self.instance):
                           raise ValueError('Cannot add "%r": instance is on database "%s", value is on database "%s"' %
                                               (obj, self.instance._state.db, obj._state.db))
                        if hasattr(self, '_get_fk_val'):  # Django>=1.5
                            fk_val = self._get_fk_val(obj, target_field_name)
                            if fk_val is None:
                                raise ValueError('Cannot add "%r": the value for field "%s" is None' %
                                                 (obj, target_field_name))
                            new_ids.append(self._get_fk_val(obj, target_field_name))
                        else:  # Django<1.5
                            new_ids.append(obj.pk)
                    elif isinstance(obj, Model):
                        raise TypeError("'%s' instance expected, got %r" % (self.model._meta.object_name, obj))
                    else:
                        new_ids.append(obj)
                db = router.db_for_write(self.through, instance=self.instance)
                vals = self.through._default_manager.using(db).values_list(target_field_name, flat=True)
                vals = vals.filter(**{
                    source_field_name: self._fk_val,
                    '%s__in' % target_field_name: new_ids,
                })
                for val in vals:
                    if val in new_ids:
                        new_ids.remove(val)
                _new_ids = []
                for pk in new_ids:
                    if pk not in _new_ids:
                        _new_ids.append(pk)
                new_ids = _new_ids
                new_ids_set = set(new_ids)

                if self.reverse or source_field_name == self.source_field_name:
                    # Don't send the signal when we are inserting the
                    # duplicate data row for symmetrical reverse entries.
                    signals.m2m_changed.send(sender=rel.through, action='pre_add',
                        instance=self.instance, reverse=self.reverse,
                        model=self.model, pk_set=new_ids_set, using=db)
                # Add the ones that aren't there already
                sort_field_name = self.through._sort_field_name
                sort_field = self.through._meta.get_field_by_name(sort_field_name)[0]
                for obj_id in new_ids:
                    self.through._default_manager.using(db).create(**{
                        '%s_id' % source_field_name: self._fk_val,  # Django 1.5 compatibility
                        '%s_id' % target_field_name: obj_id,
                        sort_field_name: sort_field.get_default(),
                    })
                if self.reverse or source_field_name == self.source_field_name:
                    # Don't send the signal when we are inserting the
                    # duplicate data row for symmetrical reverse entries.
                    signals.m2m_changed.send(sender=rel.through, action='post_add',
                        instance=self.instance, reverse=self.reverse,
                        model=self.model, pk_set=new_ids_set, using=db)

    return SortedRelatedManager


class ReverseSortedManyRelatedObjectsDescriptor(ReverseManyRelatedObjectsDescriptor):
    @property
    def related_manager_cls(self):
        return create_sorted_many_related_manager(
            self.field.rel.to._default_manager.__class__,
            self.field.rel
        )


class SortedManyToManyField(ManyToManyField):
    '''
    Providing a many to many relation that remembers the order of related
    objects.

    Accept a boolean ``sorted`` attribute which specifies if relation is
    ordered or not. Default is set to ``True``. If ``sorted`` is set to
    ``False`` the field will behave exactly like django's ``ManyToManyField``.
    '''
    def __init__(self, to, sorted=True, **kwargs):
        self.sorted = sorted
        self.sort_value_field_name = kwargs.pop(
            'sort_value_field_name',
            SORT_VALUE_FIELD_NAME)
        super(SortedManyToManyField, self).__init__(to, **kwargs)
        if self.sorted:
            self.help_text = kwargs.get('help_text', None)

    def contribute_to_class(self, cls, name):
        if not self.sorted:
            return super(SortedManyToManyField, self).contribute_to_class(cls, name)

        # To support multiple relations to self, it's useful to have a non-None
        # related name on symmetrical relations for internal reasons. The
        # concept doesn't make a lot of sense externally ("you want me to
        # specify *what* on my non-reversible relation?!"), so we set it up
        # automatically. The funky name reduces the chance of an accidental
        # clash.
        if self.rel.symmetrical and (self.rel.to == "self" or self.rel.to == cls._meta.object_name):
            self.rel.related_name = "%s_rel_+" % name

        super(ManyToManyField, self).contribute_to_class(cls, name)

        # The intermediate m2m model is not auto created if:
        #  1) There is a manually specified intermediate, or
        #  2) The class owning the m2m field is abstract.
        if not self.rel.through and not cls._meta.abstract:
            self.rel.through = create_sorted_many_to_many_intermediate_model(self, cls)

        # Add the descriptor for the m2m relation
        setattr(cls, self.name, ReverseSortedManyRelatedObjectsDescriptor(self))

        # Set up the accessor for the m2m table name for the relation
        self.m2m_db_table = curry(self._get_m2m_db_table, cls._meta)

        # Populate some necessary rel arguments so that cross-app relations
        # work correctly.
        if isinstance(self.rel.through, string_types):
            def resolve_through_model(field, model, cls):
                field.rel.through = model
            add_lazy_relation(cls, self, self.rel.through, resolve_through_model)

        if hasattr(cls._meta, 'duplicate_targets'):  # Django<1.5
            if isinstance(self.rel.to, string_types):
                target = self.rel.to
            else:
                target = self.rel.to._meta.db_table
            cls._meta.duplicate_targets[self.column] = (target, "m2m")

    def formfield(self, **kwargs):
        defaults = {}
        if self.sorted:
            defaults['form_class'] = SortedMultipleChoiceField
        defaults.update(kwargs)
        return super(SortedManyToManyField, self).formfield(**defaults)


# Add introspection rules for South database migrations
# See http://south.aeracode.org/docs/customfields.html
try:
    import south
except ImportError:
    south = None

if south is not None and 'south' in settings.INSTALLED_APPS:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(
        [(
            (SortedManyToManyField,),
            [],
            {"sorted": ["sorted", {"default": True}]},
        )],
        [r'^sortedm2m\.fields\.SortedManyToManyField']
    )

    # Monkeypatch South M2M actions to create the sorted through model.
    # FIXME: This doesn't detect if you changed the sorted argument to the field.
    import south.creator.actions
    from south.creator.freezer import model_key

    class AddM2M(south.creator.actions.AddM2M):
        SORTED_FORWARDS_TEMPLATE = '''
        # Adding SortedM2M table for field %(field_name)s on '%(model_name)s'
        db.create_table(%(table_name)r, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            (%(left_field)r, models.ForeignKey(orm[%(left_model_key)r], null=False)),
            (%(right_field)r, models.ForeignKey(orm[%(right_model_key)r], null=False)),
            (%(sort_field)r, models.IntegerField())
        ))
        db.create_unique(%(table_name)r, [%(left_column)r, %(right_column)r])'''

        def console_line(self):
            if isinstance(self.field, SortedManyToManyField) and self.field.sorted:
                return " + Added SortedM2M table for %s on %s.%s" % (
                    self.field.name,
                    self.model._meta.app_label,
                    self.model._meta.object_name,
                )
            else:
                return super(AddM2M, self).console_line()

        def forwards_code(self):
            if isinstance(self.field, SortedManyToManyField) and self.field.sorted:
                return self.SORTED_FORWARDS_TEMPLATE % {
                    "model_name": self.model._meta.object_name,
                    "field_name": self.field.name,
                    "table_name": self.field.m2m_db_table(),
                    "left_field": self.field.m2m_column_name()[:-3], # Remove the _id part
                    "left_column": self.field.m2m_column_name(),
                    "left_model_key": model_key(self.model),
                    "right_field": self.field.m2m_reverse_name()[:-3], # Remove the _id part
                    "right_column": self.field.m2m_reverse_name(),
                    "right_model_key": model_key(self.field.rel.to),
                    "sort_field": self.field.sort_value_field_name,
                }
            else:
                return super(AddM2M, self).forwards_code()

    class DeleteM2M(AddM2M):
        def console_line(self):
            return " - Deleted M2M table for %s on %s.%s" % (
                self.field.name,
                self.model._meta.app_label,
                self.model._meta.object_name,
            )

        def forwards_code(self):
            return AddM2M.backwards_code(self)

        def backwards_code(self):
            return AddM2M.forwards_code(self)

    south.creator.actions.AddM2M = AddM2M
    south.creator.actions.DeleteM2M = DeleteM2M

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
import sys
from itertools import chain
from django import forms
from django.conf import settings
from django.db.models.query import QuerySet
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.html import conditional_escape, escape
from django.utils.safestring import mark_safe


if sys.version_info[0] < 3:
    iteritems = lambda d: iter(d.iteritems())
    string_types = basestring,
    str_ = unicode
else:
    iteritems = lambda d: iter(d.items())
    string_types = str,
    str_ = str


STATIC_URL = getattr(settings, 'STATIC_URL', settings.MEDIA_URL)


class SortedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    class Media:
        js = (
            STATIC_URL + 'sortedm2m/widget.js',
            STATIC_URL + 'sortedm2m/jquery-ui.js',
        )
        css = {'screen': (
            STATIC_URL + 'sortedm2m/widget.css',
        )}

    def build_attrs(self, attrs=None, **kwargs):
        attrs = super(SortedCheckboxSelectMultiple, self).\
            build_attrs(attrs, **kwargs)
        classes = attrs.setdefault('class', '').split()
        classes.append('sortedm2m')
        attrs['class'] = ' '.join(classes)
        return attrs

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)

        # Normalize to strings
        str_values = [force_text(v) for v in value]

        selected = []
        unselected = []

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = ' for="%s"' % conditional_escape(final_attrs['id'])
            else:
                label_for = ''

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_text(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_text(option_label))
            item = {'label_for': label_for, 'rendered_cb': rendered_cb, 'option_label': option_label, 'option_value': option_value}
            if option_value in str_values:
                selected.append(item)
            else:
                unselected.append(item)

        # re-order `selected` array according str_values which is a set of `option_value`s in the order they should be shown on screen
        ordered = []
        for value in str_values:
            for select in selected:
                if value == select['option_value']:
                    ordered.append(select)
        selected = ordered

        html = render_to_string(
            'sortedm2m/sorted_checkbox_select_multiple_widget.html',
            {'selected': selected, 'unselected': unselected})
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if isinstance(value, string_types):
            return [v for v in value.split(',') if v]
        return value


class SortedMultipleChoiceField(forms.ModelMultipleChoiceField):
    widget = SortedCheckboxSelectMultiple

    def clean(self, value):
        queryset = super(SortedMultipleChoiceField, self).clean(value)
        if value is None or not isinstance(queryset, QuerySet):
            return queryset
        object_list = dict((
            (str_(key), value)
            for key, value in iteritems(queryset.in_bulk(value))))
        return [object_list[str_(pk)] for pk in value]

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from sortedm2m.fields import SortedManyToManyField


class Shelf(models.Model):
    books = SortedManyToManyField('Book', related_name='shelves')


class Book(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name


class DoItYourselfShelf(models.Model):
    books = SortedManyToManyField(Book,
        sort_value_field_name='diy_sort_number',
        related_name='diy_shelves')


class Store(models.Model):
    books = SortedManyToManyField('sortedm2m_tests.Book', related_name='stores')


class MessyStore(models.Model):
    books = SortedManyToManyField('Book',
        sorted=False,
        related_name='messy_stores')


class SelfReference(models.Model):
    me = SortedManyToManyField('self', related_name='hide+')

    def __unicode__(self):
        return unicode(self.pk)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django.db import connection
from django.db.models.fields import FieldDoesNotExist
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six
from sortedm2m_tests.models import Book, Shelf, DoItYourselfShelf, Store, \
    MessyStore, SelfReference

str_ = six.text_type


class TestSortedManyToManyField(TestCase):
    model = Shelf

    def setUp(self):
        self.books = [Book.objects.create(name=c) for c in 'abcdefghik']

    def test_adding_items(self):
        shelf = self.model.objects.create()
        self.assertEqual(list(shelf.books.all()), [])

        shelf.books.add(self.books[2])
        self.assertEqual(list(shelf.books.all()), [self.books[2]])

        # adding many with each in one call
        shelf.books.add(self.books[5])
        shelf.books.add(self.books[1])
        self.assertEqual(list(shelf.books.all()), [
            self.books[2],
            self.books[5],
            self.books[1]])

        # adding the same item again won't append another one, order remains
        # the same
        shelf.books.add(self.books[2])
        self.assertEqual(list(shelf.books.all()), [
            self.books[2],
            self.books[5],
            self.books[1]])

        shelf.books.clear()
        self.assertEqual(list(shelf.books.all()), [])

        # adding many with all in the same call
        shelf.books.add(self.books[3], self.books[1], self.books[2])
        self.assertEqual(list(shelf.books.all()), [
            self.books[3],
            self.books[1],
            self.books[2]])

    def test_adding_items_by_pk(self):
        shelf = self.model.objects.create()
        self.assertEqual(list(shelf.books.all()), [])

        shelf.books.add(self.books[2].pk)
        self.assertEqual(list(shelf.books.all()), [self.books[2]])

        shelf.books.add(self.books[5].pk, str_(self.books[1].pk))
        self.assertEqual(list(shelf.books.all()), [
            self.books[2],
            self.books[5],
            self.books[1]])

        shelf.books.clear()
        self.assertEqual(list(shelf.books.all()), [])

        shelf.books.add(self.books[3].pk, self.books[1], str_(self.books[2].pk))
        self.assertEqual(list(shelf.books.all()), [
            self.books[3],
            self.books[1],
            self.books[2]])

    def test_set_items(self):
        shelf = self.model.objects.create()
        self.assertEqual(list(shelf.books.all()), [])

        books = self.books[5:2:-1]
        shelf.books = books
        self.assertEqual(list(shelf.books.all()), books)

        books.reverse()
        shelf.books = books
        self.assertEqual(list(shelf.books.all()), books)

        shelf.books.add(self.books[8])
        self.assertEqual(list(shelf.books.all()), books + [self.books[8]])

        shelf.books = []
        self.assertEqual(list(shelf.books.all()), [])

        shelf.books = [self.books[9]]
        self.assertEqual(list(shelf.books.all()), [
            self.books[9]])

        shelf.books = []
        self.assertEqual(list(shelf.books.all()), [])

    def test_set_items_by_pk(self):
        shelf = self.model.objects.create()
        self.assertEqual(list(shelf.books.all()), [])

        books = self.books[5:2:-1]
        shelf.books = [b.pk for b in books]
        self.assertEqual(list(shelf.books.all()), books)

        shelf.books = [self.books[5].pk, self.books[2]]
        self.assertEqual(list(shelf.books.all()), [
            self.books[5],
            self.books[2]])

        shelf.books = [str_(self.books[8].pk)]
        self.assertEqual(list(shelf.books.all()), [self.books[8]])

    def test_remove_items(self):
        shelf = self.model.objects.create()
        shelf.books = self.books[2:5]
        self.assertEqual(list(shelf.books.all()), [
            self.books[2],
            self.books[3],
            self.books[4]])

        shelf.books.remove(self.books[3])
        self.assertEqual(list(shelf.books.all()), [
            self.books[2],
            self.books[4]])

        shelf.books.remove(self.books[2], self.books[4])
        self.assertEqual(list(shelf.books.all()), [])

    def test_remove_items_by_pk(self):
        shelf = self.model.objects.create()
        shelf.books = self.books[2:5]
        self.assertEqual(list(shelf.books.all()), [
            self.books[2],
            self.books[3],
            self.books[4]])

        shelf.books.remove(self.books[3].pk)
        self.assertEqual(list(shelf.books.all()), [
            self.books[2],
            self.books[4]])

        shelf.books.remove(self.books[2], str_(self.books[4].pk))
        self.assertEqual(list(shelf.books.all()), [])

#    def test_add_relation_by_hand(self):
#        shelf = self.model.objects.create()
#        shelf.books = self.books[2:5]
#        self.assertEqual(list(shelf.books.all()), [
#            self.books[2],
#            self.books[3],
#            self.books[4]])
#
#        shelf.books.create()
#        self.assertEqual(list(shelf.books.all()), [
#            self.books[2],
#            self.books[3],
#            self.books[4]])

    # to enable population of connection.queries
    @override_settings(DEBUG=True)
    def test_prefetch_related_queries_num(self):
        shelf = self.model.objects.create()
        shelf.books.add(self.books[0])

        shelf = self.model.objects.filter(pk=shelf.pk).prefetch_related('books')[0]
        queries_num = len(connection.queries)
        name = shelf.books.all()[0].name
        self.assertEqual(queries_num, len(connection.queries))

    def test_prefetch_related_sorting(self):
        shelf = self.model.objects.create()
        books = [self.books[0], self.books[2], self.books[1]]
        shelf.books = books

        shelf = self.model.objects.filter(pk=shelf.pk).prefetch_related('books')[0]
        def get_ids(queryset):
            return [obj.id for obj in queryset]
        self.assertEqual(get_ids(shelf.books.all()), get_ids(books))

class TestStringReference(TestSortedManyToManyField):
    '''
    Test the same things as ``TestSortedManyToManyField`` but using a model
    that using a string to reference the relation where the m2m field should
    point to.
    '''
    model = Store


class TestStringReference(TestSortedManyToManyField):
    '''
    Test the same things as ``TestSortedManyToManyField`` but using a model
    that using a string to reference the relation where the m2m field should
    point to.
    '''
    model = DoItYourselfShelf

    def test_custom_sort_value_field_name(self):
        from sortedm2m.fields import SORT_VALUE_FIELD_NAME

        self.assertEqual(len(self.model._meta.many_to_many), 1)
        sortedm2m = self.model._meta.many_to_many[0]
        intermediate_model = sortedm2m.rel.through

        # make sure that standard sort field is not used
        self.assertRaises(
            FieldDoesNotExist,
            intermediate_model._meta.get_field_by_name,
            SORT_VALUE_FIELD_NAME)

        field = intermediate_model._meta.get_field_by_name('diy_sort_number')
        self.assertTrue(field)


class TestSelfReference(TestCase):
    def test_self_adding(self):
        s1 = SelfReference.objects.create()
        s2 = SelfReference.objects.create()
        s3 = SelfReference.objects.create()
        s4 = SelfReference.objects.create()
        s1.me.add(s3)
        s1.me.add(s4, s2)

        self.assertEqual(list(s1.me.all()), [s3,s4,s2])

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django import forms
from django.test import TestCase
from django.utils import six
from sortedm2m.forms import SortedMultipleChoiceField
from sortedm2m_tests.models import Book, Shelf, Store, MessyStore


str_ = six.text_type


class SortedForm(forms.Form):
    values = SortedMultipleChoiceField(
        queryset=Book.objects.all(),
        required=False)


class TestSortedFormField(TestCase):
    def setUp(self):
        self.books = [Book.objects.create(name=c) for c in 'abcdefghik']

    def test_empty_field(self):
        form = SortedForm({'values': []})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data['values'])

    def test_sorted_field_input(self):
        form = SortedForm({'values': [4,2,9]})
        self.assertTrue(form.is_valid())
        self.assertEqual(list(form.cleaned_data['values']), [
                self.books[3],
                self.books[1],
                self.books[8]])

        form = SortedForm({'values': [book.pk for book in self.books[::-1]]})
        self.assertTrue(form.is_valid())
        self.assertEqual(list(form.cleaned_data['values']), self.books[::-1])

    def test_form_field_on_model_field(self):
        class ShelfForm(forms.ModelForm):
            class Meta:
                model = Shelf

        form = ShelfForm()
        self.assertTrue(
            isinstance(form.fields['books'], SortedMultipleChoiceField))

        class MessyStoreForm(forms.ModelForm):
            class Meta:
                model = MessyStore

        form = MessyStoreForm()
        self.assertFalse(
            isinstance(form.fields['books'], SortedMultipleChoiceField))
        self.assertTrue(
            isinstance(form.fields['books'], forms.ModelMultipleChoiceField))

    # regression test
    def test_form_field_with_only_one_value(self):
        form = SortedForm({'values': ''})
        self.assertEqual(len(form.errors), 0)
        form = SortedForm({'values': '1'})
        self.assertEqual(len(form.errors), 0)
        form = SortedForm({'values': '1,2'})
        self.assertEqual(len(form.errors), 0)

    def test_for_attribute_in_label(self):
        form = SortedForm()
        rendered = str_(form['values'])
        self.assertTrue(' for="id_values_0"' in rendered)

        form = SortedForm(prefix='prefix')
        rendered = str_(form['values'])
        self.assertTrue(' for="id_prefix-values_0"' in rendered)

        # check that it will be escaped properly

        form = SortedForm(prefix='hacking"><a href="TRAP">')
        rendered = str_(form['values'])
        self.assertTrue(' for="id_hacking&quot;&gt;&lt;a href=&quot;TRAP&quot;&gt;-values_0"' in rendered)

    def test_input_id_is_escaped(self):
        form = SortedForm(prefix='hacking"><a href="TRAP">')
        rendered = str_(form['values'])
        self.assertTrue(' id="id_hacking&quot;&gt;&lt;a href=&quot;TRAP&quot;&gt;-values_0"' in rendered)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Photo'
        db.create_table('south_support_photo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('south_support', ['Photo'])

        # Adding model 'Gallery'
        db.create_table('south_support_gallery', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('south_support', ['Gallery'])

        # Adding SortedM2M table for field photos on 'Gallery'
        db.create_table('south_support_gallery_photos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('gallery', models.ForeignKey(orm['south_support.gallery'], null=False)),
            ('photo', models.ForeignKey(orm['south_support.photo'], null=False)),
            ('sort_value', models.IntegerField())
        ))
        db.create_unique('south_support_gallery_photos', ['gallery_id', 'photo_id'])

        # Adding model 'UnsortedGallery'
        db.create_table('south_support_unsortedgallery', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('south_support', ['UnsortedGallery'])

        # Adding M2M table for field photos on 'UnsortedGallery'
        db.create_table('south_support_unsortedgallery_photos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('unsortedgallery', models.ForeignKey(orm['south_support.unsortedgallery'], null=False)),
            ('photo', models.ForeignKey(orm['south_support.photo'], null=False))
        ))
        db.create_unique('south_support_unsortedgallery_photos', ['unsortedgallery_id', 'photo_id'])


    def backwards(self, orm):
        
        # Deleting model 'Photo'
        db.delete_table('south_support_photo')

        # Deleting model 'Gallery'
        db.delete_table('south_support_gallery')

        # Removing M2M table for field photos on 'Gallery'
        db.delete_table('south_support_gallery_photos')

        # Deleting model 'UnsortedGallery'
        db.delete_table('south_support_unsortedgallery')

        # Removing M2M table for field photos on 'UnsortedGallery'
        db.delete_table('south_support_unsortedgallery_photos')


    models = {
        'south_support.gallery': {
            'Meta': {'object_name': 'Gallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'photos': ('sortedm2m.fields.SortedManyToManyField', [], {'to': "orm['south_support.Photo']", 'symmetrical': 'False'})
        },
        'south_support.photo': {
            'Meta': {'object_name': 'Photo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'south_support.unsortedgallery': {
            'Meta': {'object_name': 'UnsortedGallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'photos': ('sortedm2m.fields.SortedManyToManyField', [], {'sorted': 'False', 'symmetrical': 'False', 'to': "orm['south_support.Photo']"})
        }
    }

    complete_apps = ['south_support']

########NEW FILE########
__FILENAME__ = 0002_auto
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing M2M table for field photos on 'Gallery'
        db.delete_table('south_support_gallery_photos')


    def backwards(self, orm):
        
        # Adding SortedM2M table for field photos on 'Gallery'
        db.create_table('south_support_gallery_photos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('gallery', models.ForeignKey(orm['south_support.gallery'], null=False)),
            ('photo', models.ForeignKey(orm['south_support.photo'], null=False)),
            ('sort_value', models.IntegerField())
        ))
        db.create_unique('south_support_gallery_photos', ['gallery_id', 'photo_id'])


    models = {
        'south_support.gallery': {
            'Meta': {'object_name': 'Gallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'south_support.photo': {
            'Meta': {'object_name': 'Photo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'south_support.unsortedgallery': {
            'Meta': {'object_name': 'UnsortedGallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'photos': ('sortedm2m.fields.SortedManyToManyField', [], {'sorted': 'False', 'symmetrical': 'False', 'to': "orm['south_support.Photo']"})
        }
    }

    complete_apps = ['south_support']

########NEW FILE########
__FILENAME__ = 0003_auto
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding SortedM2M table for field photos on 'Gallery'
        db.create_table('south_support_gallery_photos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('gallery', models.ForeignKey(orm['south_support.gallery'], null=False)),
            ('photo', models.ForeignKey(orm['south_support.photo'], null=False)),
            ('sort_value', models.IntegerField())
        ))
        db.create_unique('south_support_gallery_photos', ['gallery_id', 'photo_id'])


    def backwards(self, orm):
        
        # Removing M2M table for field photos on 'Gallery'
        db.delete_table('south_support_gallery_photos')


    models = {
        'south_support.gallery': {
            'Meta': {'object_name': 'Gallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'photos': ('sortedm2m.fields.SortedManyToManyField', [], {'to': "orm['south_support.Photo']", 'symmetrical': 'False'})
        },
        'south_support.photo': {
            'Meta': {'object_name': 'Photo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'south_support.unsortedgallery': {
            'Meta': {'object_name': 'UnsortedGallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'photos': ('sortedm2m.fields.SortedManyToManyField', [], {'sorted': 'False', 'symmetrical': 'False', 'to': "orm['south_support.Photo']"})
        }
    }

    complete_apps = ['south_support']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from sortedm2m.fields import SortedManyToManyField


class Photo(models.Model):
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return self.name


class Gallery(models.Model):
    name = models.CharField(max_length=30)
    photos = SortedManyToManyField(Photo)

    def __unicode__(self):
        return self.name


class UnsortedGallery(models.Model):
    name = models.CharField(max_length=30)
    photos = SortedManyToManyField(Photo, sorted=False)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['south_support_custom_sort_field_name']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from ..models import Photo
from sortedm2m.fields import SortedManyToManyField


# this model is not considered in the existing migrations. South will try to
# create this model.
class FeaturedPhotos(models.Model):
    name = models.CharField(max_length=30)
    photos = SortedManyToManyField(Photo,
        sort_value_field_name='featured_nr')

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PhotoStream'
        db.create_table('south_support_new_field_photostream', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('south_support_new_field', ['PhotoStream'])


    def backwards(self, orm):
        # Deleting model 'PhotoStream'
        db.delete_table('south_support_new_field_photostream')


    models = {
        'south_support_new_field.photostream': {
            'Meta': {'object_name': 'PhotoStream'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        }
    }

    complete_apps = ['south_support_new_field']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from ..models import Photo
from sortedm2m.fields import SortedManyToManyField


# this model is already created in the schemamigrations but the ``photos``
# field is missing from the DB. So south will try to create it.
class PhotoStream(models.Model):
    name = models.CharField(max_length=30)
    photos = SortedManyToManyField(Photo, sorted=True)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['south_support_new_model']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from ..models import Photo
from sortedm2m.fields import SortedManyToManyField


# this model is not considered in the existing migrations. South will try to
# create this model.
class CompleteNewPhotoStream(models.Model):
    name = models.CharField(max_length=30)
    new_photos = SortedManyToManyField(Photo, sorted=True)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import with_statement
import sys
import mock
from django.core.management import call_command
from django.test import TestCase
from sortedm2m_tests.south_support.models import Gallery, Photo, \
    UnsortedGallery

if sys.version_info[0] < 3:
    from StringIO import StringIO

else:
    from io import StringIO


class SouthMigratedModelTests(TestCase):
    def test_sorted_m2m(self):
        pic1 = Photo.objects.create(name='Picture 1')
        pic2 = Photo.objects.create(name='Picture 1')
        gallery = Gallery.objects.create(name='Gallery')
        gallery.photos.add(pic1)
        gallery.photos.add(pic2)
        self.assertEqual(list(gallery.photos.all()), [pic1, pic2])

    def test_unsorted_sorted_m2m(self):
        pic1 = Photo.objects.create(name='Picture 1')
        pic2 = Photo.objects.create(name='Picture 1')
        gallery = UnsortedGallery.objects.create(name='Gallery')
        gallery.photos.add(pic1)
        gallery.photos.add(pic2)
        self.assertEqual(set(gallery.photos.all()), set((pic1, pic2)))


class SouthSchemaMigrationTests(TestCase):
    def perform_migration(self, *args, **kwargs):
        stdout = StringIO()
        stderr = StringIO()
        with mock.patch('sys.stdout', stdout):
            with mock.patch('sys.stderr', stderr):
                call_command(*args, **kwargs)
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read()
        errput = stderr.read()
        return output, errput

    def assertExpectedStrings(self, expected_strings, output):
        last = 0
        for expect in expected_strings:
            current = output.find(expect)
            if current == -1:
                self.fail(
                    "Following string is missing from "
                    "south migration: %s" % expect)
            self.assertTrue(
                last < current,
                "Following string is not in correct position in "
                "south migration: %s" % expect)
            last = current

    def assertUnexpectedStrings(self, unexpected_strings, output):
        for unexpected in unexpected_strings:
            current = output.find(unexpected)
            if current != -1:
                self.fail(
                    "Following string is content of "
                    "south migration: %s" % unexpected)


    def test_new_model(self):
        from sortedm2m.fields import SORT_VALUE_FIELD_NAME

        output, errput = self.perform_migration(
            'schemamigration',
            'south_support_new_model',
            stdout=True,
            auto=True)

        self.assertExpectedStrings([
            "Adding SortedM2M table for field new_photos on 'CompleteNewPhotoStream'",
            "('%s', models.IntegerField())" % SORT_VALUE_FIELD_NAME,
        ], output)

        self.assertExpectedStrings([
            "+ Added model south_support_new_model.CompleteNewPhotoStream",
            "+ Added SortedM2M table for new_photos on south_support_new_model.CompleteNewPhotoStream",
        ], errput)

    def test_new_field(self):
        from sortedm2m.fields import SORT_VALUE_FIELD_NAME

        output, errput = self.perform_migration(
            'schemamigration',
            'south_support_new_field',
            stdout=True,
            auto=True)

        self.assertExpectedStrings([
            "Adding SortedM2M table for field photos on 'PhotoStream'",
            "('%s', models.IntegerField())" % SORT_VALUE_FIELD_NAME,
        ], output)

        self.assertExpectedStrings([
            "+ Added SortedM2M table for photos on south_support_new_field.PhotoStream",
        ], errput)
        self.assertUnexpectedStrings([
            "+ Added model south_support_new_field.PhotoStream",
        ], errput)

    def test_custom_sort_field_name(self):
        output, errput = self.perform_migration(
            'schemamigration',
            'south_support_custom_sort_field_name',
            stdout=True,
            auto=True)

        self.assertExpectedStrings([
            "Adding SortedM2M table for field photos on 'FeaturedPhotos'",
            "('featured_nr', models.IntegerField())",
        ], output)

        self.assertExpectedStrings([
            "+ Added model south_support_custom_sort_field_name.FeaturedPhotos",
            "+ Added SortedM2M table for photos on south_support_custom_sort_field_name.FeaturedPhotos",
        ], errput)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testsite project.
import os
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'db.sqlite'),
    },
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'define in local settings file'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.staticfiles',

    'south',

    'sortedm2m',
    'sortedm2m_tests',
    'sortedm2m_tests.sortedm2m_field',
    'sortedm2m_tests.sortedm2m_form',
    'sortedm2m_tests.south_support',
    'sortedm2m_tests.south_support.south_support_new_model',
    'sortedm2m_tests.south_support.south_support_new_field',
    'sortedm2m_tests.south_support.south_support_custom_sort_field_name',

    'example.testapp',
)

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
