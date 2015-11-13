__FILENAME__ = admin
import json

from django import VERSION as DJANGO_VERSION
from django.contrib.contenttypes.generic import (GenericStackedInline,
    GenericTabularInline)

DJANGO_MINOR_VERSION = DJANGO_VERSION[1]

from django.conf import settings

if DJANGO_MINOR_VERSION < 5:
    from django.conf.urls.defaults import patterns, url
else:
    from django.conf.urls import patterns, url

from django.contrib.admin import ModelAdmin, TabularInline, StackedInline
from django.contrib.admin.options import InlineModelAdmin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import render
from django.template.defaultfilters import capfirst

from adminsortable.utils import get_is_sortable
from adminsortable.fields import SortableForeignKey
from adminsortable.models import Sortable

STATIC_URL = settings.STATIC_URL


class SortableAdminBase(object):
    def changelist_view(self, request, extra_context=None):
        """
        If the model that inherits Sortable has more than one object,
        its sort order can be changed. This view adds a link to the
        object_tools block to take people to the view to change the sorting.
        """

        # get sort group index from querystring
        sort_filter_index = request.GET.get('sort_filter')

        if get_is_sortable(self.queryset(request)):
            self.change_list_template = \
                self.sortable_change_list_with_sort_link_template
            self.is_sortable = True

        if extra_context is None:
            extra_context = {}

        extra_context.update({
            'change_list_template_extends': self.change_list_template_extends,
            'sorting_filters': [sort_filter[0] for sort_filter in self.model.sorting_filters]
        })
        return super(SortableAdminBase, self).changelist_view(request,
            extra_context=extra_context)


class SortableAdmin(SortableAdminBase, ModelAdmin):
    """
    Admin class to add template overrides and context objects to enable
    drag-and-drop ordering.
    """
    ordering = ('order', 'id')

    sortable_change_list_with_sort_link_template = \
        'adminsortable/change_list_with_sort_link.html'
    sortable_change_form_template = 'adminsortable/change_form.html'
    sortable_change_list_template = 'adminsortable/change_list.html'

    change_form_template_extends = 'admin/change_form.html'
    change_list_template_extends = 'admin/change_list.html'

    class Meta:
        abstract = True

    def _get_sortable_foreign_key(self):
        sortable_foreign_key = None
        for field in self.model._meta.fields:
            if isinstance(field, SortableForeignKey):
                sortable_foreign_key = field
                break
        return sortable_foreign_key

    def get_urls(self):
        urls = super(SortableAdmin, self).get_urls()
        admin_urls = patterns('',

            # this view changes the order
            url(r'^sorting/do-sorting/(?P<model_type_id>\d+)/$',
                self.admin_site.admin_view(self.do_sorting_view),
                name='admin_do_sorting'),

            # this view shows a link to the drag-and-drop view
            url(r'^sort/$', self.admin_site.admin_view(self.sort_view),
                name='admin_sort'),
        )
        return admin_urls + urls

    def sort_view(self, request):
        """
        Custom admin view that displays the objects as a list whose sort
        order can be changed via drag-and-drop.
        """
        opts = self.model._meta
        has_perm = request.user.has_perm('{}.{}'.format(opts.app_label,
            opts.get_change_permission()))

        # get sort group index from querystring if present
        sort_filter_index = request.GET.get('sort_filter')

        filters = {}
        if sort_filter_index:
            try:
                filters = self.model.sorting_filters[int(sort_filter_index)][1]
            except (IndexError, ValueError):
                pass

        # Apply any sort filters to create a subset of sortable objects
        objects = self.queryset(request).filter(**filters)

        # Determine if we need to regroup objects relative to a
        # foreign key specified on the model class that is extending Sortable.
        # Legacy support for 'sortable_by' defined as a model property
        sortable_by_property = getattr(self.model, 'sortable_by', None)

        # `sortable_by` defined as a SortableForeignKey
        sortable_by_fk = self._get_sortable_foreign_key()
        sortable_by_class_is_sortable = get_is_sortable(objects)

        if sortable_by_property:
            # backwards compatibility for < 1.1.1, where sortable_by was a
            # classmethod instead of a property
            try:
                sortable_by_class, sortable_by_expression = \
                    sortable_by_property()
            except (TypeError, ValueError):
                sortable_by_class = self.model.sortable_by
                sortable_by_expression = sortable_by_class.__name__.lower()

            sortable_by_class_display_name = sortable_by_class._meta \
                .verbose_name_plural

        elif sortable_by_fk:
            # get sortable by properties from the SortableForeignKey
            # field - supported in 1.3+
            sortable_by_class_display_name = sortable_by_fk.rel.to \
                ._meta.verbose_name_plural
            sortable_by_class = sortable_by_fk.rel.to
            sortable_by_expression = sortable_by_fk.name.lower()

        else:
            # model is not sortable by another model
            sortable_by_class = sortable_by_expression = \
                sortable_by_class_display_name = \
                sortable_by_class_is_sortable = None

        if sortable_by_property or sortable_by_fk:
            # Order the objects by the property they are sortable by,
            # then by the order, otherwise the regroup
            # template tag will not show the objects correctly
            objects = objects.order_by(sortable_by_expression, 'order')

        try:
            verbose_name_plural = opts.verbose_name_plural.__unicode__()
        except AttributeError:
            verbose_name_plural = opts.verbose_name_plural

        context = {
            'title': u'Drag and drop {0} to change display order'.format(
                capfirst(verbose_name_plural)),
            'opts': opts,
            'app_label': opts.app_label,
            'has_perm': has_perm,
            'objects': objects,
            'group_expression': sortable_by_expression,
            'sortable_by_class': sortable_by_class,
            'sortable_by_class_is_sortable': sortable_by_class_is_sortable,
            'sortable_by_class_display_name': sortable_by_class_display_name
        }
        return render(request, self.sortable_change_list_template, context)

    def add_view(self, request, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}

        extra_context.update({
            'change_form_template_extends': self.change_form_template_extends
        })
        return super(SortableAdmin, self).add_view(request, form_url,
            extra_context=extra_context)

    def change_view(self, request, object_id, extra_context=None):
        self.has_sortable_tabular_inlines = False
        self.has_sortable_stacked_inlines = False

        if extra_context is None:
            extra_context = {}

        extra_context.update({
            'change_form_template_extends': self.change_form_template_extends
        })

        for klass in self.inlines:
            if issubclass(klass, SortableTabularInline) or issubclass(klass,
                SortableGenericTabularInline):
                self.has_sortable_tabular_inlines = True
            if issubclass(klass, SortableStackedInline) or issubclass(klass,
                SortableGenericStackedInline):
                self.has_sortable_stacked_inlines = True

        if self.has_sortable_tabular_inlines or \
                self.has_sortable_stacked_inlines:

            self.change_form_template = self.sortable_change_form_template

            extra_context.update({
                'has_sortable_tabular_inlines':
                self.has_sortable_tabular_inlines,
                'has_sortable_stacked_inlines':
                self.has_sortable_stacked_inlines
            })

        return super(SortableAdmin, self).change_view(request, object_id,
            extra_context=extra_context)

    def do_sorting_view(self, request, model_type_id=None):
        """
        This view sets the ordering of the objects for the model type
        and primary keys passed in. It must be an Ajax POST.
        """
        response = {'objects_sorted': False}

        if request.is_ajax() and request.method == 'POST':
            try:
                indexes = list(map(str, request.POST.get('indexes', []).split(',')))
                klass = ContentType.objects.get(id=model_type_id).model_class()
                objects_dict = dict([(str(obj.pk), obj) for obj in
                    klass.objects.filter(pk__in=indexes)])
                if '-order' in klass._meta.ordering:  # desc order
                    start_object = max(objects_dict.values(),
                        key=lambda x: getattr(x, 'order'))
                    start_index = getattr(start_object, 'order') \
                        or len(indexes)
                    step = -1
                else:  # 'order' is default, asc order
                    start_object = min(objects_dict.values(),
                        key=lambda x: getattr(x, 'order'))
                    start_index = getattr(start_object, 'order') or 0
                    step = 1

                for index in indexes:
                    obj = objects_dict.get(index)
                    setattr(obj, 'order', start_index)
                    obj.save()
                    start_index += step
                response = {'objects_sorted': True}
            except (KeyError, IndexError, klass.DoesNotExist, AttributeError, ValueError):
                pass

        return HttpResponse(json.dumps(response, ensure_ascii=False),
            content_type='application/json')


class SortableInlineBase(SortableAdminBase, InlineModelAdmin):
    def __init__(self, *args, **kwargs):
        super(SortableInlineBase, self).__init__(*args, **kwargs)

        if not issubclass(self.model, Sortable):
            raise Warning(u'Models that are specified in SortableTabluarInline'
                ' and SortableStackedInline must inherit from Sortable')

    def queryset(self, request):
        qs = super(SortableInlineBase, self).queryset(request)
        if get_is_sortable(qs):
            self.model.is_sortable = True
        else:
            self.model.is_sortable = False
        return qs


class SortableTabularInline(TabularInline, SortableInlineBase):
    """Custom template that enables sorting for tabular inlines"""
    if DJANGO_MINOR_VERSION <= 5:
        template = 'adminsortable/edit_inline/tabular-1.5.x.html'
    else:
        template = 'adminsortable/edit_inline/tabular.html'


class SortableStackedInline(StackedInline, SortableInlineBase):
    """Custom template that enables sorting for stacked inlines"""
    if DJANGO_MINOR_VERSION <= 5:
        template = 'adminsortable/edit_inline/stacked-1.5.x.html'
    else:
        template = 'adminsortable/edit_inline/stacked.html'


class SortableGenericTabularInline(GenericTabularInline, SortableInlineBase):
    """Custom template that enables sorting for tabular inlines"""
    if DJANGO_MINOR_VERSION <= 5:
        template = 'adminsortable/edit_inline/tabular-1.5.x.html'
    else:
        template = 'adminsortable/edit_inline/tabular.html'


class SortableGenericStackedInline(GenericStackedInline, SortableInlineBase):
    """Custom template that enables sorting for stacked inlines"""
    if DJANGO_MINOR_VERSION <= 5:
        template = 'adminsortable/edit_inline/stacked-1.5.x.html'
    else:
        template = 'adminsortable/edit_inline/stacked.html'

########NEW FILE########
__FILENAME__ = fields
from django.db.models.fields.related import ForeignKey


class SortableForeignKey(ForeignKey):
    """
    Field simply acts as a flag to determine the class to sort by.
    This field replaces previous functionality where `sortable_by` was
    definied as a model property that specified another model class.
    """

    def south_field_triple(self):
        try:
            from south.modelsinspector import introspector
            cls_name = '{0}.{1}'.format(
                self.__class__.__module__,
                self.__class__.__name__)
            args, kwargs = introspector(self)
            return cls_name, args, kwargs
        except ImportError:
            pass

########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes.models import ContentType
from django.db import models

from adminsortable.fields import SortableForeignKey


class MultipleSortableForeignKeyException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Sortable(models.Model):
    """
    `is_sortable` determines whether or not the Model is sortable by
    determining if the last value of `order` is greater than the default
    of 1, which should be present if there is only one object.

    `model_type_id` returns the ContentType.id for the Model that
    inherits Sortable

    `save` the override of save increments the last/highest value of
    order by 1
    """

    order = models.PositiveIntegerField(editable=False, default=1,
        db_index=True)
    is_sortable = False
    sorting_filters = ()

    # legacy support
    sortable_by = None

    class Meta:
        abstract = True
        ordering = ['order']

    @classmethod
    def model_type_id(cls):
        return ContentType.objects.get_for_model(cls).id

    def __init__(self, *args, **kwargs):
        super(Sortable, self).__init__(*args, **kwargs)

        # Validate that model only contains at most one SortableForeignKey
        sortable_foreign_keys = []
        for field in self._meta.fields:
            if isinstance(field, SortableForeignKey):
                sortable_foreign_keys.append(field)
        if len(sortable_foreign_keys) > 1:
            raise MultipleSortableForeignKeyException(
                u'{} may only have one SortableForeignKey'.format(self))

    def save(self, *args, **kwargs):
        if not self.id:
            try:
                self.order = self.__class__.objects.aggregate(
                    models.Max('order'))['order__max'] + 1
            except (TypeError, IndexError):
                pass

        super(Sortable, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = adminsortable_tags
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def render_sortable_objects(context, objects,
        sortable_objects_template='adminsortable/shared/objects.html'):
    context.update({'objects': objects})
    tmpl = template.loader.get_template(sortable_objects_template)
    return tmpl.render(context)


@register.simple_tag(takes_context=True)
def render_nested_sortable_objects(context, objects, group_expression,
        sortable_nested_objects_template='adminsortable/shared/nested_objects.html'):
    context.update({'objects': objects, 'group_expression': group_expression})
    tmpl = template.loader.get_template(sortable_nested_objects_template)
    return tmpl.render(context)


@register.simple_tag(takes_context=True)
def render_list_items(context, list_objects,
        sortable_list_items_template='adminsortable/shared/list_items.html'):
    context.update({'list_objects': list_objects})
    tmpl = template.loader.get_template(sortable_list_items_template)
    return tmpl.render(context)


@register.simple_tag(takes_context=True)
def render_object_rep(context, obj,
        sortable_object_rep_template='adminsortable/shared/object_rep.html'):
    context.update({'object': obj})
    tmpl = template.loader.get_template(sortable_object_rep_template)
    return tmpl.render(context)

########NEW FILE########
__FILENAME__ = django_template_additions
from itertools import groupby
from django import template
try:
    from django import TemplateSyntaxError
except ImportError:
    #support for django 1.3
    from django.template.base import TemplateSyntaxError

register = template.Library()


class DynamicRegroupNode(template.Node):
    """
    Extends Django's regroup tag to accept a variable instead of a string literal
    for the property you want to regroup on
    """

    def __init__(self, target, parser, expression, var_name):
        self.target = target
        self.expression = template.Variable(expression)
        self.var_name = var_name
        self.parser = parser

    def render(self, context):
        obj_list = self.target.resolve(context, True)
        if obj_list == None:
            # target variable wasn't found in context; fail silently.
            context[self.var_name] = []
            return ''
        # List of dictionaries in the format:
        # {'grouper': 'key', 'list': [list of contents]}.

        #Try to resolve the filter expression from the template context.
        #If the variable doesn't exist, accept the value that passed to the
        #template tag and convert it to a string
        try:
            exp = self.expression.resolve(context)
        except template.VariableDoesNotExist:
            exp = str(self.expression)

        filter_exp = self.parser.compile_filter(exp)

        context[self.var_name] = [
            {'grouper': key, 'list': list(val)}
            for key, val in
            groupby(obj_list, lambda v, f=filter_exp.resolve: f(v, True))
        ]

        return ''


@register.tag
def dynamic_regroup(parser, token):
    """
    Django expects the value of `expression` to be an attribute available on
    your objects. The value you pass to the template tag gets converted into a
    FilterExpression object from the literal.

    Sometimes we need the attribute to group on to be dynamic. So, instead
    of converting the value to a FilterExpression here, we're going to pass the
    value as-is and convert it in the Node.
    """
    firstbits = token.contents.split(None, 3)
    if len(firstbits) != 4:
        raise TemplateSyntaxError("'regroup' tag takes five arguments")
    target = parser.compile_filter(firstbits[1])
    if firstbits[2] != 'by':
        raise TemplateSyntaxError("second argument to 'regroup' tag must be 'by'")
    lastbits_reversed = firstbits[3][::-1].split(None, 2)
    if lastbits_reversed[1][::-1] != 'as':
        raise TemplateSyntaxError("next-to-last argument to 'regroup' tag must"
                                  " be 'as'")

    expression = lastbits_reversed[2][::-1]
    var_name = lastbits_reversed[0][::-1]
    #We also need to hand the parser to the node in order to convert the value
    #for `expression` to a FilterExpression.
    return DynamicRegroupNode(target, parser, expression, var_name)

########NEW FILE########
__FILENAME__ = utils
def get_is_sortable(objects):
    if objects:
        if objects.count() > 1:
            return True
    return False

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from adminsortable.admin import (SortableAdmin, SortableTabularInline,
    SortableStackedInline, SortableGenericStackedInline)
from adminsortable.utils import get_is_sortable
from app.models import (Category, Widget, Project, Credit, Note, GenericNote,
    Component, Person)


admin.site.register(Category, SortableAdmin)


class ComponentInline(SortableStackedInline):
    model = Component

    def queryset(self, request):
        qs = super(ComponentInline, self).queryset(
            request).exclude(title__icontains='2')
        if get_is_sortable(qs):
            self.model.is_sortable = True
        else:
            self.model.is_sortable = False
        return qs


class WidgetAdmin(SortableAdmin):
    def queryset(self, request):
        """
        A simple example demonstrating that adminsortable works even in
        situations where you need to filter the queryset in admin. Here,
        we are just filtering out `widget` instances with an pk higher
        than 3
        """
        qs = super(WidgetAdmin, self).queryset(request)
        return qs.filter(id__lte=3)

    inlines = [ComponentInline]

admin.site.register(Widget, WidgetAdmin)


class CreditInline(SortableTabularInline):
    model = Credit


class NoteInline(SortableStackedInline):
    model = Note
    extra = 0


class GenericNoteInline(SortableGenericStackedInline):
    model = GenericNote
    extra = 0


class ProjectAdmin(SortableAdmin):
    inlines = [CreditInline, NoteInline, GenericNoteInline]
    list_display = ['__unicode__', 'category']

admin.site.register(Project, ProjectAdmin)


class PersonAdmin(SortableAdmin):
    list_display = ['__unicode__', 'is_board_member']

admin.site.register(Person, PersonAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Category'
        db.create_table(u'app_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'app', ['Category'])

        # Adding model 'Project'
        db.create_table(u'app_project', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('category', self.gf('adminsortable.fields.SortableForeignKey')(to=orm['app.Category'])),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'app', ['Project'])

        # Adding model 'Credit'
        db.create_table(u'app_credit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app.Project'])),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal(u'app', ['Credit'])

        # Adding model 'Note'
        db.create_table(u'app_note', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app.Project'])),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'app', ['Note'])

        # Adding model 'GenericNote'
        db.create_table(u'app_genericnote', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='generic_notes', to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal(u'app', ['GenericNote'])


    def backwards(self, orm):
        # Deleting model 'Category'
        db.delete_table(u'app_category')

        # Deleting model 'Project'
        db.delete_table(u'app_project')

        # Deleting model 'Credit'
        db.delete_table(u'app_credit')

        # Deleting model 'Note'
        db.delete_table(u'app_note')

        # Deleting model 'GenericNote'
        db.delete_table(u'app_genericnote')


    models = {
        u'app.category': {
            'Meta': {'ordering': "['order']", 'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.credit': {
            'Meta': {'ordering': "['order']", 'object_name': 'Credit'},
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"})
        },
        u'app.genericnote': {
            'Meta': {'ordering': "['order']", 'object_name': 'GenericNote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'generic_notes'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.note': {
            'Meta': {'ordering': "['order']", 'object_name': 'Note'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'app.project': {
            'Meta': {'ordering': "['order']", 'object_name': 'Project'},
            'category': ('adminsortable.fields.SortableForeignKey', [], {'to': u"orm['app.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['app']
########NEW FILE########
__FILENAME__ = 0002_add_widget
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Widget'
        db.create_table(u'app_widget', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'app', ['Widget'])


    def backwards(self, orm):
        # Deleting model 'Widget'
        db.delete_table(u'app_widget')


    models = {
        u'app.category': {
            'Meta': {'ordering': "['order']", 'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.credit': {
            'Meta': {'ordering': "['order']", 'object_name': 'Credit'},
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"})
        },
        u'app.genericnote': {
            'Meta': {'ordering': "['order']", 'object_name': 'GenericNote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'generic_notes'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.note': {
            'Meta': {'ordering': "['order']", 'object_name': 'Note'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'app.project': {
            'Meta': {'ordering': "['order']", 'object_name': 'Project'},
            'category': ('adminsortable.fields.SortableForeignKey', [], {'to': u"orm['app.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.widget': {
            'Meta': {'ordering': "['order']", 'object_name': 'Widget'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['app']
########NEW FILE########
__FILENAME__ = 0003_add_component
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Component'
        db.create_table(u'app_component', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('widget', self.gf('adminsortable.fields.SortableForeignKey')(to=orm['app.Widget'])),
        ))
        db.send_create_signal(u'app', ['Component'])


    def backwards(self, orm):
        # Deleting model 'Component'
        db.delete_table(u'app_component')


    models = {
        u'app.category': {
            'Meta': {'ordering': "['order']", 'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.component': {
            'Meta': {'ordering': "['order']", 'object_name': 'Component'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'widget': ('adminsortable.fields.SortableForeignKey', [], {'to': u"orm['app.Widget']"})
        },
        u'app.credit': {
            'Meta': {'ordering': "['order']", 'object_name': 'Credit'},
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"})
        },
        u'app.genericnote': {
            'Meta': {'ordering': "['order']", 'object_name': 'GenericNote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'generic_notes'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.note': {
            'Meta': {'ordering': "['order']", 'object_name': 'Note'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'app.project': {
            'Meta': {'ordering': "['order']", 'object_name': 'Project'},
            'category': ('adminsortable.fields.SortableForeignKey', [], {'to': u"orm['app.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.widget': {
            'Meta': {'ordering': "['order']", 'object_name': 'Widget'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['app']
########NEW FILE########
__FILENAME__ = 0004_add_person
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Person'
        db.create_table(u'app_person', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('is_board_member', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'app', ['Person'])


    def backwards(self, orm):
        # Deleting model 'Person'
        db.delete_table(u'app_person')


    models = {
        u'app.category': {
            'Meta': {'ordering': "['order']", 'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.component': {
            'Meta': {'ordering': "['order']", 'object_name': 'Component'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'widget': ('adminsortable.fields.SortableForeignKey', [], {'to': u"orm['app.Widget']"})
        },
        u'app.credit': {
            'Meta': {'ordering': "['order']", 'object_name': 'Credit'},
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"})
        },
        u'app.genericnote': {
            'Meta': {'ordering': "['order']", 'object_name': 'GenericNote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'generic_notes'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.note': {
            'Meta': {'ordering': "['order']", 'object_name': 'Note'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Project']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'app.person': {
            'Meta': {'ordering': "['order']", 'object_name': 'Person'},
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_board_member': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'})
        },
        u'app.project': {
            'Meta': {'ordering': "['order']", 'object_name': 'Project'},
            'category': ('adminsortable.fields.SortableForeignKey', [], {'to': u"orm['app.Category']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'app.widget': {
            'Meta': {'ordering': "['order']", 'object_name': 'Widget'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['app']
########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

from adminsortable.fields import SortableForeignKey
from adminsortable.models import Sortable


class SimpleModel(models.Model):
    class Meta:
        abstract = True

    title = models.CharField(max_length=50)

    def __unicode__(self):
        return self.title


# A model that is sortable
class Category(SimpleModel, Sortable):
    class Meta(Sortable.Meta):
        """
        Classes that inherit from Sortable must define an inner
        Meta class that inherits from Sortable.Meta or ordering
        won't work as expected
        """
        verbose_name_plural = 'Categories'


# A model with an override of its queryset for admin
class Widget(SimpleModel, Sortable):
    class Meta(Sortable.Meta):
        pass

    def __unicode__(self):
        return self.title


# A model that is sortable relative to a foreign key that is also sortable
# uses SortableForeignKey field. Works with versions 1.3+
class Project(SimpleModel, Sortable):
    class Meta(Sortable.Meta):
        pass

    category = SortableForeignKey(Category)
    description = models.TextField()


# Registered as a tabular inline on `Project`
class Credit(Sortable):
    class Meta(Sortable.Meta):
        pass

    project = models.ForeignKey(Project)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __unicode__(self):
        return '{0} {1}'.format(self.first_name, self.last_name)


# Registered as a stacked inline on `Project`
class Note(Sortable):
    class Meta(Sortable.Meta):
        pass

    project = models.ForeignKey(Project)
    text = models.CharField(max_length=100)

    def __unicode__(self):
        return self.text


# A generic bound model
class GenericNote(SimpleModel, Sortable):
    content_type = models.ForeignKey(ContentType,
        verbose_name=u"Content type", related_name="generic_notes")
    object_id = models.PositiveIntegerField(u"Content id")
    content_object = generic.GenericForeignKey(ct_field='content_type',
        fk_field='object_id')

    class Meta(Sortable.Meta):
        pass

    def __unicode__(self):
        return u'{}: {}'.format(self.title, self.content_object)


# An model registered as an inline that has a custom queryset
class Component(SimpleModel, Sortable):
    class Meta(Sortable.Meta):
        pass

    widget = SortableForeignKey(Widget)

    def __unicode__(self):
        return self.title


class Person(Sortable):
    class Meta(Sortable.Meta):
        verbose_name_plural = 'People'

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_board_member = models.BooleanField('Board Member', default=False)

    # Sorting Filters allow you to set up sub-sets of objects that need
    # to have independent sorting. They are listed in order, from left
    # to right in the sorting change list. You can use any standard
    # Django ORM filter method.
    sorting_filters = (
        ('Board Members', {'is_board_member': True}),
        ('Non-Board Members', {'is_board_member': False}),
    )

    def __unicode__(self):
        return '{} {}'.format(self.first_name, self.last_name)

########NEW FILE########
__FILENAME__ = tests
import httplib
import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.test import TestCase
from django.test.client import Client, RequestFactory

from adminsortable.fields import SortableForeignKey
from adminsortable.models import Sortable
from adminsortable.utils import get_is_sortable
from app.models import Category, Credit, Note


class BadSortableModel(models.Model):
    note = SortableForeignKey(Note)
    credit = SortableForeignKey(Credit)


class TestSortableModel(Sortable):
    title = models.CharField(max_length=100)

    def __unicode__(self):
        return self.title


class SortableTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user_raw_password = 'admin'
        self.user = User.objects.create_user('admin', 'admin@admin.com',
            self.user_raw_password)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

    def create_category(self, title='Category 1'):
        category = Category.objects.create(title=title)
        return category

    def test_new_user_is_authenticated(self):
        self.assertEqual(self.user.is_authenticated(), True,
            'User is not authenticated')

    def test_new_user_is_staff(self):
        self.assertEqual(self.user.is_staff, True, 'User is not staff')

    def test_is_not_sortable(self):
        """
        A model should only become sortable if it has more than
        record to sort.
        """
        self.create_category()
        self.assertFalse(get_is_sortable(Category.objects.all()),
            'Category only has one record. It should not be sortable.')

    def test_is_sortable(self):
        self.create_category()
        self.create_category(title='Category 2')
        self.assertTrue(get_is_sortable(Category.objects.all()),
            'Category has more than one record. It should be sortable.')

    def test_save_order_incremented(self):
        category1 = self.create_category()
        self.assertEqual(category1.order, 1, 'Category 1 order should be 1.')

        category2 = self.create_category(title='Category 2')
        self.assertEqual(category2.order, 2, 'Category 2 order should be 2.')

    def test_adminsortable_change_list_view(self):
        self.client.login(username=self.user.username,
            password=self.user_raw_password)
        response = self.client.get('/admin/app/category/sort/')
        self.assertEquals(response.status_code, httplib.OK,
            'Unable to reach sort view.')

    def make_test_categories(self):
        category1 = self.create_category()
        category2 = self.create_category(title='Category 2')
        category3 = self.create_category(title='Category 3')
        return category1, category2, category3

    def get_sorting_url(self):
        return '/admin/app/category/sorting/do-sorting/{0}/'.format(
            Category.model_type_id())

    def get_category_indexes(self, *categories):
        return {'indexes': ','.join([str(c.id) for c in categories])}

    def test_adminsortable_changelist_templates(self):
        logged_in = self.client.login(username=self.user.username,
            password=self.user_raw_password)
        self.assertTrue(logged_in, 'User is not logged in')

        response = self.client.get('/admin/app/category/sort/')
        self.assertEqual(response.status_code, httplib.OK,
            'Admin sort request failed.')

        #assert adminsortable change list templates are used
        template_names = [t.name for t in response.templates]
        self.assertTrue('adminsortable/change_list.html' in template_names,
                        'adminsortable/change_list.html was not rendered')

    def test_adminsortable_change_list_sorting_fails_if_not_ajax(self):
        logged_in = self.client.login(username=self.user.username,
            password=self.user_raw_password)
        self.assertTrue(logged_in, 'User is not logged in')

        category1, category2, category3 = self.make_test_categories()
        #make a normal POST
        response = self.client.post(self.get_sorting_url(),
            data=self.get_category_indexes(category1, category2, category3))
        content = json.loads(response.content)
        self.assertFalse(content.get('objects_sorted'),
            'Objects should not have been sorted. An ajax post is required.')

    def test_adminsortable_change_list_sorting_successful(self):
        logged_in = self.client.login(username=self.user.username,
            password=self.user_raw_password)
        self.assertTrue(logged_in, 'User is not logged in')

        #make categories
        category1, category2, category3 = self.make_test_categories()

        #make an Ajax POST
        response = self.client.post(self.get_sorting_url(),
            data=self.get_category_indexes(category3, category2, category1),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        content = json.loads(response.content)
        self.assertTrue(content.get('objects_sorted'),
            'Objects should have been sorted.')

        #assert order is correct
        categories = Category.objects.all()
        cat1 = categories[0]
        cat2 = categories[1]
        cat3 = categories[2]

        self.assertEqual(cat1.order, 1,
            'First category returned should have order == 1')
        self.assertEqual(cat1.pk, 3,
            'Category ID 3 should have been first in queryset')

        self.assertEqual(cat2.order, 2,
            'Second category returned should have order == 2')
        self.assertEqual(cat2.pk, 2,
            'Category ID 2 should have been second in queryset')

        self.assertEqual(cat3.order, 3,
            'Third category returned should have order == 3')
        self.assertEqual(cat3.pk, 1,
            'Category ID 1 should have been third in queryset')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

# Adds the adminsortable package from the cloned repository instead of site_packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sample_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.
from utils import map_path

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': map_path('database/test_project.sqlite'),
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': ''
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '8**a!c8$1x)p@j2pj0yq!*v+dzp24g*$918ws#x@k+gf%0%rct'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'sample_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'sample_project.wsgi.application'

TEMPLATE_DIRS = (
    map_path('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',

    'adminsortable',
    'app',
    'south',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_project.views.home', name='home'),
    # url(r'^test_project/', include('test_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = utils
import os


def map_path(directory_name):
    return os.path.join(os.path.dirname(__file__),
        '../' + directory_name).replace('\\', '/')

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for test_project project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "test_project.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
