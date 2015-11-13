__FILENAME__ = admin
from django.contrib import admin
from django import forms
from django.utils.translation import ugettext_lazy as _

from .genericcollection import GenericCollectionTabularInline
from .settings import RELATION_MODELS, JAVASCRIPT_URL, REGISTER_ADMIN
from .models import Category
from .base import CategoryBaseAdminForm, CategoryBaseAdmin
from .settings import MODEL_REGISTRY


class NullTreeNodeChoiceField(forms.ModelChoiceField):
    """A ModelChoiceField for tree nodes."""
    def __init__(self, level_indicator=u'---', *args, **kwargs):
        self.level_indicator = level_indicator
        super(NullTreeNodeChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        """
        Creates labels which represent the tree level of each node when
        generating option labels.
        """
        return u'%s %s' % (self.level_indicator * getattr(
                                        obj, obj._mptt_meta.level_attr), obj)
if RELATION_MODELS:
    from .models import CategoryRelation

    class InlineCategoryRelation(GenericCollectionTabularInline):
        model = CategoryRelation


class CategoryAdminForm(CategoryBaseAdminForm):
    class Meta:
        model = Category

    def clean_alternate_title(self):
        if self.instance is None or not self.cleaned_data['alternate_title']:
            return self.cleaned_data['name']
        else:
            return self.cleaned_data['alternate_title']


class CategoryAdmin(CategoryBaseAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'alternate_title', 'active')
    fieldsets = (
        (None, {
            'fields': ('parent', 'name', 'thumbnail', 'active')
        }),
        (_('Meta Data'), {
            'fields': ('alternate_title', 'alternate_url', 'description',
                        'meta_keywords', 'meta_extra'),
            'classes': ('collapse',),
        }),
        (_('Advanced'), {
            'fields': ('order', 'slug'),
            'classes': ('collapse',),
        }),
    )

    if RELATION_MODELS:
        inlines = [InlineCategoryRelation, ]

    class Media:
        js = (JAVASCRIPT_URL + 'genericcollections.js',)

if REGISTER_ADMIN:
    admin.site.register(Category, CategoryAdmin)

for model, modeladmin in admin.site._registry.items():
    if model in MODEL_REGISTRY.values() and modeladmin.fieldsets:
        fieldsets = getattr(modeladmin, 'fieldsets', ())
        fields = [cat.split('.')[2] for cat in MODEL_REGISTRY if MODEL_REGISTRY[cat] == model]
        # check each field to see if already defined
        for cat in fields:
            for k, v in fieldsets:
                if cat in v['fields']:
                    fields.remove(cat)
        # if there are any fields left, add them under the categories fieldset
        if len(fields) > 0:
            admin.site.unregister(model)
            admin.site.register(model, type('newadmin', (modeladmin.__class__,), {
                'fieldsets': fieldsets + (('Categories', {
                    'fields': fields
                }),)
            }))

########NEW FILE########
__FILENAME__ = base
"""
This is the base class on which to build a hierarchical category-like model
with customizable metadata and its own name space.
"""

from django.contrib import admin
from django.db import models
from django import forms
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

from mptt.models import MPTTModel
from mptt.fields import TreeForeignKey
from mptt.managers import TreeManager
from slugify import slugify

from .editor.tree_editor import TreeEditor
from .settings import ALLOW_SLUG_CHANGE, SLUG_TRANSLITERATOR


class CategoryManager(models.Manager):
    """
    A manager that adds an "active()" method for all active categories
    """
    def active(self):
        """
        Only categories that are active
        """
        return self.get_query_set().filter(active=True)


class CategoryBase(MPTTModel):
    """
    This base model includes the absolute bare bones fields and methods. One
    could simply subclass this model and do nothing else and it should work.
    """
    parent = TreeForeignKey('self',
        blank=True,
        null=True,
        related_name='children',
        verbose_name=_('parent'))
    name = models.CharField(max_length=100, verbose_name=_('name'))
    slug = models.SlugField(verbose_name=_('slug'))
    active = models.BooleanField(default=True, verbose_name=_('active'))

    objects = CategoryManager()
    tree = TreeManager()

    def save(self, *args, **kwargs):
        """
        While you can activate an item without activating its descendants,
        It doesn't make sense that you can deactivate an item and have its
        decendants remain active.
        """
        if not self.slug:
            self.slug = slugify(SLUG_TRANSLITERATOR(self.name))[:50]

        super(CategoryBase, self).save(*args, **kwargs)

        if not self.active:
            for item in self.get_descendants():
                if item.active != self.active:
                    item.active = self.active
                    item.save()

    def __unicode__(self):
        ancestors = self.get_ancestors()
        return ' > '.join([force_unicode(i.name) for i in ancestors] + [self.name, ])

    class Meta:
        abstract = True
        unique_together = ('parent', 'name')
        ordering = ('tree_id', 'lft')

    class MPTTMeta:
        order_insertion_by = 'name'


class CategoryBaseAdminForm(forms.ModelForm):
    def clean_slug(self):
        if not self.cleaned_data.get('slug', None):
            if self.instance is None or not ALLOW_SLUG_CHANGE:
                self.cleaned_data['slug'] = slugify(SLUG_TRANSLITERATOR(self.cleaned_data['name']))
        return self.cleaned_data['slug'][:50]

    def clean(self):

        super(CategoryBaseAdminForm, self).clean()

        if not self.is_valid():
            return self.cleaned_data

        opts = self._meta

        # Validate slug is valid in that level
        kwargs = {}
        if self.cleaned_data.get('parent', None) is None:
            kwargs['parent__isnull'] = True
        else:
            kwargs['parent__pk'] = int(self.cleaned_data['parent'].id)
        this_level_slugs = [c['slug'] for c in opts.model.objects.filter(
                                **kwargs).values('id', 'slug'
                                ) if c['id'] != self.instance.id]
        if self.cleaned_data['slug'] in this_level_slugs:
            raise forms.ValidationError(_('The slug must be unique among '
                                          'the items at its level.'))

        # Validate Category Parent
        # Make sure the category doesn't set itself or any of its children as
        # its parent.
        decendant_ids = self.instance.get_descendants().values_list('id', flat=True)
        if self.cleaned_data.get('parent', None) is None or self.instance.id is None:
            return self.cleaned_data
        elif self.cleaned_data['parent'].id == self.instance.id:
            raise forms.ValidationError(_("You can't set the parent of the "
                                          "item to itself."))
        elif self.cleaned_data['parent'].id in decendant_ids:
            raise forms.ValidationError(_("You can't set the parent of the "
                                          "item to a descendant."))
        return self.cleaned_data


class CategoryBaseAdmin(TreeEditor, admin.ModelAdmin):
    form = CategoryBaseAdminForm
    list_display = ('name', 'active')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    actions = ['activate', 'deactivate']

    def get_actions(self, request):
        actions = super(CategoryBaseAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def deactivate(self, request, queryset):
        """
        Set active to False for selected items
        """
        selected_cats = self.model.objects.filter(
            pk__in=[int(x) for x in request.POST.getlist('_selected_action')])

        for item in selected_cats:
            if item.active:
                item.active = False
                item.save()
                item.children.all().update(active=False)
    deactivate.short_description = _('Deactivate selected categories and their children')

    def activate(self, request, queryset):
        """
        Set active to True for selected items
        """
        selected_cats = self.model.objects.filter(
            pk__in=[int(x) for x in request.POST.getlist('_selected_action')])

        for item in selected_cats:
            item.active = True
            item.save()
            item.children.all().update(active=True)
    activate.short_description = _('Activate selected categories and their children')

########NEW FILE########
__FILENAME__ = models
# Placeholder for Django
########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
import django

DJANGO10_COMPAT = django.VERSION[0] < 1 or (django.VERSION[0] == 1 and django.VERSION[1] < 1)

STATIC_URL = getattr(settings, 'STATIC_URL', settings.MEDIA_URL)
if STATIC_URL == None:
    STATIC_URL = settings.MEDIA_URL
MEDIA_PATH = getattr(settings, 'EDITOR_MEDIA_PATH', '%seditor/' % STATIC_URL)

TREE_INITIAL_STATE = getattr(settings, 'EDITOR_TREE_INITIAL_STATE', 'collapsed')

IS_GRAPPELLI_INSTALLED = 'grappelli' in settings.INSTALLED_APPS

########NEW FILE########
__FILENAME__ = admin_tree_list
import django
from django.db import models
from django.template import Library
from django.contrib.admin.templatetags.admin_list import result_headers, _boolean_icon
try:
    from django.contrib.admin.util import lookup_field, display_for_field, label_for_field
except ImportError:
    from categories.editor.utils import lookup_field, display_for_field, label_for_field
from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe

from categories.editor import settings

register = Library()

TREE_LIST_RESULTS_TEMPLATE = 'admin/editor/tree_list_results.html'
if settings.IS_GRAPPELLI_INSTALLED:
    TREE_LIST_RESULTS_TEMPLATE = 'admin/editor/grappelli_tree_list_results.html'


def items_for_tree_result(cl, result, form):
    """
    Generates the actual list of data.
    """
    first = True
    pk = cl.lookup_opts.pk.attname
    for field_name in cl.list_display:
        row_class = ''
        try:
            f, attr, value = lookup_field(field_name, result, cl.model_admin)
        except (AttributeError, ObjectDoesNotExist):
            result_repr = EMPTY_CHANGELIST_VALUE
        else:
            if f is None:
                if django.VERSION[1] == 4:
                    if field_name == 'action_checkbox':
                        row_class = ' class="action-checkbox disclosure"'
                allow_tags = getattr(attr, 'allow_tags', False)
                boolean = getattr(attr, 'boolean', False)
                if boolean:
                    allow_tags = True
                    result_repr = _boolean_icon(value)
                else:
                    result_repr = smart_unicode(value)
                # Strip HTML tags in the resulting text, except if the
                # function has an "allow_tags" attribute set to True.
                if not allow_tags:
                    result_repr = escape(result_repr)
                else:
                    result_repr = mark_safe(result_repr)
            else:
                if value is None:
                    result_repr = EMPTY_CHANGELIST_VALUE
                if isinstance(f.rel, models.ManyToOneRel):
                    result_repr = escape(getattr(result, f.name))
                else:
                    result_repr = display_for_field(value, f)
                if isinstance(f, models.DateField) or isinstance(f, models.TimeField):
                    row_class = ' class="nowrap"'
            if first:
                if django.VERSION[1] < 4:
                    try:
                        f, attr, checkbox_value = lookup_field('action_checkbox', result, cl.model_admin)
                        #result_repr = mark_safe("%s%s" % (value, result_repr))
                        if row_class:
                            row_class = "%s%s" % (row_class[:-1], ' disclosure"')
                        else:
                            row_class = ' class="disclosure"'
                    except (AttributeError, ObjectDoesNotExist):
                        pass

        if force_unicode(result_repr) == '':
            result_repr = mark_safe('&nbsp;')
        # If list_display_links not defined, add the link tag to the first field
        if (first and not cl.list_display_links) or field_name in cl.list_display_links:
            if django.VERSION[1] < 4:
                table_tag = 'td'  # {True:'th', False:'td'}[first]
            else:
                table_tag = {True:'th', False:'td'}[first]

            url = cl.url_for_result(result)
            # Convert the pk to something that can be used in Javascript.
            # Problem cases are long ints (23L) and non-ASCII strings.
            if cl.to_field:
                attr = str(cl.to_field)
            else:
                attr = pk
            value = result.serializable_value(attr)
            result_id = repr(force_unicode(value))[1:]
            first = False
            if django.VERSION[1] < 4:
                yield mark_safe(u'<%s%s>%s<a href="%s"%s>%s</a></%s>' % \
                    (table_tag, row_class, checkbox_value, url, (cl.is_popup and ' onclick="opener.dismissRelatedLookupPopup(window, %s); return false;"' % result_id or ''), conditional_escape(result_repr), table_tag))
            else:
                yield mark_safe(u'<%s%s><a href="%s"%s>%s</a></%s>' % \
                    (table_tag, row_class, url, (cl.is_popup and ' onclick="opener.dismissRelatedLookupPopup(window, %s); return false;"' % result_id or ''), conditional_escape(result_repr), table_tag))

        else:
            # By default the fields come from ModelAdmin.list_editable, but if we pull
            # the fields out of the form instead of list_editable custom admins
            # can provide fields on a per request basis
            if form and field_name in form.fields:
                bf = form[field_name]
                result_repr = mark_safe(force_unicode(bf.errors) + force_unicode(bf))
            else:
                result_repr = conditional_escape(result_repr)
            yield mark_safe(u'<td%s>%s</td>' % (row_class, result_repr))
    if form and not form[cl.model._meta.pk.name].is_hidden:
        yield mark_safe(u'<td>%s</td>' % force_unicode(form[cl.model._meta.pk.name]))


class TreeList(list):
    pass


def tree_results(cl):
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            result = TreeList(items_for_tree_result(cl, res, form))
            if hasattr(res, 'pk'):
                result.pk = res.pk
                if res.parent:
                    result.parent_pk = res.parent.pk
                else:
                    res.parent_pk = None
            yield result
    else:
        for res in cl.result_list:
            result = TreeList(items_for_tree_result(cl, res, None))
            if hasattr(res, 'pk'):
                result.pk = res.pk
                if res.parent:
                    result.parent_pk = res.parent.pk
                else:
                    res.parent_pk = None
            yield result


def result_tree_list(cl):
    """
    Displays the headers and data list together
    """
    import django
    result = {'cl': cl,
            'result_headers': list(result_headers(cl)),
            'results': list(tree_results(cl))}
    if django.VERSION[1] > 2:
        from django.contrib.admin.templatetags.admin_list import result_hidden_fields
        result['result_hidden_fields'] = list(result_hidden_fields(cl))
    return result
result_tree_list = register.inclusion_tag(TREE_LIST_RESULTS_TEMPLATE)(result_tree_list)

########NEW FILE########
__FILENAME__ = tree_editor
from django.contrib import admin
from django.db.models.query import QuerySet
from django.contrib.admin.views.main import ChangeList
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.options import IncorrectLookupParameters
from django import template
from django.shortcuts import render_to_response

import django

import settings


class TreeEditorQuerySet(QuerySet):
    """
    The TreeEditorQuerySet is a special query set used only in the TreeEditor
    ChangeList page. The only difference to a regular QuerySet is that it
    will enforce:

        (a) The result is ordered in correct tree order so that
            the TreeAdmin works all right.

        (b) It ensures that all ancestors of selected items are included
            in the result set, so the resulting tree display actually
            makes sense.
    """
    def iterator(self):
        qs = self
        # Reaching into the bowels of query sets to find out whether the qs is
        # actually filtered and we need to do the INCLUDE_ANCESTORS dance at all.
        # INCLUDE_ANCESTORS is quite expensive, so don't do it if not needed.
        is_filtered = bool(qs.query.where.children)
        if is_filtered:
            include_pages = set()
            # Order by 'rght' will return the tree deepest nodes first;
            # this cuts down the number of queries considerably since all ancestors
            # will already be in include_pages when they are checked, thus not
            # trigger additional queries.
            for p in super(TreeEditorQuerySet, self.order_by('rght')).iterator():
                if p.parent_id and p.parent_id not in include_pages and \
                                   p.id not in include_pages:
                    ancestor_id_list = p.get_ancestors().values_list('id', flat=True)
                    include_pages.update(ancestor_id_list)

            if include_pages:
                qs = qs | self.model._default_manager.filter(id__in=include_pages)

            qs = qs.distinct()

        for obj in super(TreeEditorQuerySet, qs).iterator():
            yield obj

    # Although slicing isn't nice in a tree, it is used in the deletion action
    #  in the admin changelist. This causes github issue #25
    # def __getitem__(self, index):
    #     return self   # Don't even try to slice

    def get(self, *args, **kwargs):
        """
        Quick and dirty hack to fix change_view and delete_view; they use
        self.queryset(request).get(...) to get the object they should work
        with. Our modifications to the queryset when INCLUDE_ANCESTORS is
        enabled make get() fail often with a MultipleObjectsReturned
        exception.
        """
        return self.model._default_manager.get(*args, **kwargs)


class TreeChangeList(ChangeList):
    def _get_default_ordering(self):
        if django.VERSION[1] < 4:
            return '', ''  # ('tree_id', 'lft')
        else:
            return []

    def get_ordering(self, request=None, queryset=None):
        if django.VERSION[1] < 4:
            return '', ''  # ('tree_id', 'lft')
        else:
            return []

    def get_query_set(self, *args, **kwargs):
        qs = super(TreeChangeList, self).get_query_set(*args, **kwargs).order_by('tree_id', 'lft')
        return qs


class TreeEditor(admin.ModelAdmin):
    list_per_page = 999999999  # We can't have pagination
    list_max_show_all = 200  # new in django 1.4

    class Media:
        css = {'all': (settings.MEDIA_PATH + "jquery.treeTable.css", )}
        js = []

        js.extend((settings.MEDIA_PATH + "jquery.treeTable.js", ))

    def __init__(self, *args, **kwargs):
        super(TreeEditor, self).__init__(*args, **kwargs)

        self.list_display = list(self.list_display)

        if 'action_checkbox' in self.list_display:
            self.list_display.remove('action_checkbox')

        opts = self.model._meta

        grappelli_prefix = ""
        if settings.IS_GRAPPELLI_INSTALLED:
            grappelli_prefix = "grappelli_"

        self.change_list_template = [
            'admin/%s/%s/editor/%stree_editor.html' % (opts.app_label, opts.object_name.lower(), grappelli_prefix),
            'admin/%s/editor/%stree_editor.html' % (opts.app_label, grappelli_prefix),
            'admin/editor/%stree_editor.html' % grappelli_prefix,
        ]

    def get_changelist(self, request, **kwargs):
        """
        Returns the ChangeList class for use on the changelist page.
        """
        return TreeChangeList

    def old_changelist_view(self, request, extra_context=None):
        "The 'change list' admin view for this model."
        from django.contrib.admin.views.main import ERROR_FLAG
        from django.core.exceptions import PermissionDenied
        from django.utils.encoding import force_unicode
        from django.utils.translation import ungettext
        opts = self.model._meta
        app_label = opts.app_label
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        # Check actions to see if any are available on this changelist
        actions = self.get_actions(request)

        # Remove action checkboxes if there aren't any actions available.
        list_display = list(self.list_display)
        if not actions:
            try:
                list_display.remove('action_checkbox')
            except ValueError:
                pass

        try:
            if django.VERSION[1] < 4:
                params = (request, self.model, list_display,
                    self.list_display_links, self.list_filter, self.date_hierarchy,
                    self.search_fields, self.list_select_related,
                    self.list_per_page, self.list_editable, self)
            else:
                params = (request, self.model, list_display,
                    self.list_display_links, self.list_filter, self.date_hierarchy,
                    self.search_fields, self.list_select_related,
                    self.list_per_page, self.list_max_show_all,
                    self.list_editable, self)
            cl = TreeChangeList(*params)
        except IncorrectLookupParameters:
            # Wacky lookup parameters were given, so redirect to the main
            # changelist page, without parameters, and pass an 'invalid=1'
            # parameter via the query string. If wacky parameters were given and
            # the 'invalid=1' parameter was already in the query string, something
            # is screwed up with the database, so display an error page.
            if ERROR_FLAG in request.GET.keys():
                return render_to_response(
                    'admin/invalid_setup.html', {'title': _('Database error')})
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

        # If the request was POSTed, this might be a bulk action or a bulk edit.
        # Try to look up an action first, but if this isn't an action the POST
        # will fall through to the bulk edit check, below.
        if actions and request.method == 'POST':
            response = self.response_action(request, queryset=cl.get_query_set())
            if response:
                return response

        # If we're allowing changelist editing, we need to construct a formset
        # for the changelist given all the fields to be edited. Then we'll
        # use the formset to validate/process POSTed data.
        formset = cl.formset = None

        # Handle POSTed bulk-edit data.
        if request.method == "POST" and self.list_editable:
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(
                request.POST, request.FILES, queryset=cl.result_list
            )
            if formset.is_valid():
                changecount = 0
                for form in formset.forms:
                    if form.has_changed():
                        obj = self.save_form(request, form, change=True)
                        self.save_model(request, obj, form, change=True)
                        form.save_m2m()
                        change_msg = self.construct_change_message(request, form, None)
                        self.log_change(request, obj, change_msg)
                        changecount += 1

                if changecount:
                    if changecount == 1:
                        name = force_unicode(opts.verbose_name)
                    else:
                        name = force_unicode(opts.verbose_name_plural)
                    msg = ungettext(
                        "%(count)s %(name)s was changed successfully.",
                        "%(count)s %(name)s were changed successfully.",
                        changecount) % {'count': changecount,
                                        'name': name,
                                        'obj': force_unicode(obj)}
                    self.message_user(request, msg)

                return HttpResponseRedirect(request.get_full_path())

        # Handle GET -- construct a formset for display.
        elif self.list_editable:
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(queryset=cl.result_list)

        # Build the list of media to be used by the formset.
        if formset:
            media = self.media + formset.media
        else:
            media = self.media

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
        else:
            action_form = None

        context = {
            'title': cl.title,
            'is_popup': cl.is_popup,
            'cl': cl,
            'media': media,
            'has_add_permission': self.has_add_permission(request),
            'app_label': app_label,
            'action_form': action_form,
            'actions_on_top': self.actions_on_top,
            'actions_on_bottom': self.actions_on_bottom,
        }
        if django.VERSION[1] < 4:
            context['root_path'] = self.admin_site.root_path
        else:
            selection_note_all = ungettext('%(total_count)s selected',
                'All %(total_count)s selected', cl.result_count)

            context.update({
                'module_name': force_unicode(opts.verbose_name_plural),
                'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(cl.result_list)},
                'selection_note_all': selection_note_all % {'total_count': cl.result_count},
            })
        context.update(extra_context or {})
        context_instance = template.RequestContext(
            request, current_app=self.admin_site.name
        )
        return render_to_response(self.change_list_template or [
            'admin/%s/%s/change_list.html' % (app_label, opts.object_name.lower()),
            'admin/%s/change_list.html' % app_label,
            'admin/change_list.html'
        ], context, context_instance=context_instance)

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """
        Handle the changelist view, the django view for the model instances
        change list/actions page.
        """
        extra_context = extra_context or {}
        extra_context['EDITOR_MEDIA_PATH'] = settings.MEDIA_PATH
        extra_context['EDITOR_TREE_INITIAL_STATE'] = settings.TREE_INITIAL_STATE
        if django.VERSION[1] >= 2:
            return super(TreeEditor, self).changelist_view(
                                    request, extra_context, *args, **kwargs)
        else:
            return self.old_changelist_view(request, extra_context)

    def queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = self.model._default_manager.get_query_set()
        qs.__class__ = TreeEditorQuerySet
        return qs

########NEW FILE########
__FILENAME__ = utils
"""
Provides compatibility with Django 1.1

Copied from django.contrib.admin.util
"""
from django.forms.forms import pretty_name
from django.db import models
from django.db.models.related import RelatedObject
from django.utils.encoding import force_unicode, smart_unicode, smart_str
from django.utils.translation import get_date_formats
from django.utils.text import capfirst
from django.utils import dateformat
from django.utils.html import escape


def lookup_field(name, obj, model_admin=None):
    opts = obj._meta
    try:
        f = opts.get_field(name)
    except models.FieldDoesNotExist:
        # For non-field values, the value is either a method, property or
        # returned via a callable.
        if callable(name):
            attr = name
            value = attr(obj)
        elif (model_admin is not None and hasattr(model_admin, name) and
          not name == '__str__' and not name == '__unicode__'):
            attr = getattr(model_admin, name)
            value = attr(obj)
        else:
            attr = getattr(obj, name)
            if callable(attr):
                value = attr()
            else:
                value = attr
        f = None
    else:
        attr = None
        value = getattr(obj, name)
    return f, attr, value


def label_for_field(name, model, model_admin=None, return_attr=False):
    """
    Returns a sensible label for a field name. The name can be a callable or the
    name of an object attributes, as well as a genuine fields. If return_attr is
    True, the resolved attribute (which could be a callable) is also returned.
    This will be None if (and only if) the name refers to a field.
    """
    attr = None
    try:
        field = model._meta.get_field_by_name(name)[0]
        if isinstance(field, RelatedObject):
            label = field.opts.verbose_name
        else:
            label = field.verbose_name
    except models.FieldDoesNotExist:
        if name == "__unicode__":
            label = force_unicode(model._meta.verbose_name)
            attr = unicode
        elif name == "__str__":
            label = smart_str(model._meta.verbose_name)
            attr = str
        else:
            if callable(name):
                attr = name
            elif model_admin is not None and hasattr(model_admin, name):
                attr = getattr(model_admin, name)
            elif hasattr(model, name):
                attr = getattr(model, name)
            else:
                message = "Unable to lookup '%s' on %s" % (name, model._meta.object_name)
                if model_admin:
                    message += " or %s" % (model_admin.__class__.__name__,)
                raise AttributeError(message)

            if hasattr(attr, "short_description"):
                label = attr.short_description
            elif callable(attr):
                if attr.__name__ == "<lambda>":
                    label = "--"
                else:
                    label = pretty_name(attr.__name__)
            else:
                label = pretty_name(name)
    if return_attr:
        return (label, attr)
    else:
        return label


def display_for_field(value, field):
    from django.contrib.admin.templatetags.admin_list import _boolean_icon
    from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE

    if field.flatchoices:
        return dict(field.flatchoices).get(value, EMPTY_CHANGELIST_VALUE)
    # NullBooleanField needs special-case null-handling, so it comes
    # before the general null test.
    elif isinstance(field, models.BooleanField) or isinstance(field, models.NullBooleanField):
        return _boolean_icon(value)
    elif value is None:
        return EMPTY_CHANGELIST_VALUE
    elif isinstance(field, models.DateField) or isinstance(field, models.TimeField):
        if value:
            (date_format, datetime_format, time_format) = get_date_formats()
            if isinstance(field, models.DateTimeField):
                return capfirst(dateformat.format(value, datetime_format))
            elif isinstance(field, models.TimeField):
                return capfirst(dateformat.time_format(value, time_format))
            else:
                return capfirst(dateformat.format(value, date_format))
        else:
            return EMPTY_CHANGELIST_VALUE

    elif isinstance(field, models.DecimalField):
        if value is not None:
            return ('%%.%sf' % field.decimal_places) % value
        else:
            return EMPTY_CHANGELIST_VALUE
    elif isinstance(field, models.FloatField):
        return escape(value)
    else:
        return smart_unicode(value)

########NEW FILE########
__FILENAME__ = fields
from django.db.models import ForeignKey, ManyToManyField

from .models import Category


class CategoryM2MField(ManyToManyField):
    def __init__(self, **kwargs):
        if 'to' in kwargs:
            kwargs.pop('to')
        super(CategoryM2MField, self).__init__(to=Category, **kwargs)


class CategoryFKField(ForeignKey):
    def __init__(self, **kwargs):
        if 'to' in kwargs:
            kwargs.pop('to')
        super(CategoryFKField, self).__init__(to=Category, **kwargs)

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^categories\.fields\.CategoryFKField"])
    add_introspection_rules([], ["^categories\.fields\.CategoryM2MField"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = genericcollection
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

class GenericCollectionInlineModelAdmin(admin.options.InlineModelAdmin):
    ct_field = "content_type"
    ct_fk_field = "object_id"
    
    def __init__(self, parent_model, admin_site):
        super(GenericCollectionInlineModelAdmin, self).__init__(parent_model, admin_site)
        ctypes = ContentType.objects.all().order_by('id').values_list('id', 'app_label', 'model')
        elements = ["%s: '%s/%s'" % (x, y, z) for x, y, z in ctypes]
        self.content_types = "{%s}" % ",".join(elements)
    
    def get_formset(self, request, obj=None):
        result = super(GenericCollectionInlineModelAdmin, self).get_formset(request, obj)
        result.content_types = self.content_types
        result.ct_fk_field = self.ct_fk_field
        return result

class GenericCollectionTabularInline(GenericCollectionInlineModelAdmin):
    template = 'admin/edit_inline/gen_coll_tabular.html'


class GenericCollectionStackedInline(GenericCollectionInlineModelAdmin):
    template = 'admin/edit_inline/gen_coll_stacked.html'

########NEW FILE########
__FILENAME__ = add_category_fields
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Alter one or more models' tables with the registered attributes
    """
    help = "Alter the tables for all registered models, or just specified models"
    args = "[appname ...]"
    can_import_settings = True
    requires_model_validation = False

    def handle(self, *args, **options):
        """
        Alter the tables
        """
        from django.core.exceptions import ImproperlyConfigured
        try:
            from south.db import db
        except ImportError:
            raise ImproperlyConfigured("South must be installed for this command to work")

        from categories.migration import migrate_app
        from categories.settings import MODEL_REGISTRY
        if args:
            for app in args:
                migrate_app(None, app)
        else:
            for app in MODEL_REGISTRY:
                migrate_app(None, app)

########NEW FILE########
__FILENAME__ = drop_category_field
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Alter one or more models' tables with the registered attributes
    """
    help = "Drop the given field from the given model's table"
    args = "appname modelname fieldname"
    can_import_settings = True
    requires_model_validation = False

    def handle(self, *args, **options):
        """
        Alter the tables
        """
        try:
            from south.db import db
        except ImportError:
            raise ImproperlyConfigured("South must be installed for this command to work")

        from categories.migration import drop_field
        if len(args) != 3:
            print "You must specify an Application name, a Model name and a Field name"

        drop_field(*args)

########NEW FILE########
__FILENAME__ = import_categories
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from slugify import slugify

from categories.models import Category
from categories.settings import SLUG_TRANSLITERATOR


class Command(BaseCommand):
    """Import category trees from a file."""

    help = "Imports category tree(s) from a file. Sub categories must be indented by the same multiple of spaces or tabs."
    args = "file_path [file_path ...]"

    def get_indent(self, string):
        """
        Look through the string and count the spaces
        """
        indent_amt = 0

        if string[0] == '\t':
            return '\t'
        for char in string:
            if char == ' ':
                indent_amt += 1
            else:
                return ' ' * indent_amt

    @transaction.commit_on_success
    def make_category(self, string, parent=None, order=1):
        """
        Make and save a category object from a string
        """
        cat = Category(
            name=string.strip(),
            slug=slugify(SLUG_TRANSLITERATOR(string.strip()))[:49],
            #parent=parent,
            order=order
        )
        cat._tree_manager.insert_node(cat, parent, 'last-child', True)
        cat.save()
        if parent:
            parent.rght = cat.rght + 1
            parent.save()
        return cat

    def parse_lines(self, lines):
        """
        Do the work of parsing each line
        """
        indent = ''
        level = 0

        if lines[0][0] == ' ' or lines[0][0] == '\t':
            raise CommandError("The first line in the file cannot start with a space or tab.")

        # This keeps track of the current parents at a given level
        current_parents = {0: None}

        for line in lines:
            if len(line) == 0:
                continue
            if line[0] == ' ' or line[0] == '\t':
                if indent == '':
                    indent = self.get_indent(line)
                elif not line[0] in indent:
                    raise CommandError("You can't mix spaces and tabs for indents")
                level = line.count(indent)
                current_parents[level] = self.make_category(line, parent=current_parents[level - 1])
            else:
                # We are back to a zero level, so reset the whole thing
                current_parents = {0: self.make_category(line)}
        current_parents[0]._tree_manager.rebuild()

    def handle(self, *file_paths, **options):
        """
        Handle the basic import
        """
        import os

        for file_path in file_paths:
            if not os.path.isfile(file_path):
                print "File %s not found." % file_path
                continue
            f = file(file_path, 'r')
            data = f.readlines()
            f.close()

            self.parse_lines(data)

########NEW FILE########
__FILENAME__ = migration
from django.db import models, DatabaseError
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _


def migrate_app(sender, app, created_models=None, verbosity=False, *args, **kwargs):
    """
    Migrate all models of this app registered
    """
    from .fields import CategoryM2MField, CategoryFKField
    from .models import Category
    from .settings import FIELD_REGISTRY
    import sys
    import StringIO

    org_stderror = sys.stderr
    sys.stderr = StringIO.StringIO()  # south will print out errors to stderr
    try:
        from south.db import db
    except ImportError:
        raise ImproperlyConfigured(_('%(dependency) must be installed for this command to work') %
                                   {'dependency': 'South'})
    # pull the information from the registry
    if isinstance(app, basestring):
        app_name = app
    else:
        app_name = app.__name__.split('.')[-2]

    fields = [fld for fld in FIELD_REGISTRY.keys() if fld.startswith(app_name)]
    # call the south commands to add the fields/tables
    for fld in fields:
        app_name, model_name, field_name = fld.split('.')

        # Table is typically appname_modelname, but it could be different
        #   always best to be sure.
        mdl = models.get_model(app_name, model_name)

        if isinstance(FIELD_REGISTRY[fld], CategoryFKField):
            try:
                db.start_transaction()
                table_name = mdl._meta.db_table
                FIELD_REGISTRY[fld].default = -1
                db.add_column(table_name, field_name, FIELD_REGISTRY[fld], keep_default=False)
                db.commit_transaction()
                if verbosity:
                    print (_('Added ForeignKey %(field_name) to %(model_name)') %
                           {'field_name': field_name, 'model_name': model_name})
            except DatabaseError, e:
                db.rollback_transaction()
                if "already exists" in str(e):
                    if verbosity > 1:
                        print (_('ForeignKey %(field_name) to %(model_name) already exists') %
                               {'field_name': field_name, 'model_name': model_name})
                else:
                    sys.stderr = org_stderror
                    raise e
        elif isinstance(FIELD_REGISTRY[fld], CategoryM2MField):
            table_name = '%s_%s' % (mdl._meta.db_table, 'categories')
            try:
                db.start_transaction()
                db.create_table(table_name, (
                    ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
                    (model_name, models.ForeignKey(mdl, null=False)),
                    ('category', models.ForeignKey(Category, null=False))
                ))
                db.create_unique(table_name, ['%s_id' % model_name, 'category_id'])
                db.commit_transaction()
                if verbosity:
                    print (_('Added Many2Many table between %(model_name) and %(category_table)') %
                           {'model_name': model_name, 'category_table': 'category'})
            except DatabaseError, e:
                db.rollback_transaction()
                if "already exists" in str(e):
                    if verbosity > 1:
                        print (_('Many2Many table between %(model_name) and %(category_table) already exists') %
                               {'model_name': model_name, 'category_table': 'category'})
                else:
                    sys.stderr = org_stderror
                    raise e
    sys.stderr = org_stderror


def drop_field(app_name, model_name, field_name):
    """
    Drop the given field from the app's model
    """
    # Table is typically appname_modelname, but it could be different
    #   always best to be sure.
    from .fields import CategoryM2MField, CategoryFKField
    from .settings import FIELD_REGISTRY
    try:
        from south.db import db
    except ImportError:
        raise ImproperlyConfigured(_('%(dependency) must be installed for this command to work') %
                                   {'dependency': 'South'})
    mdl = models.get_model(app_name, model_name)

    fld = '%s.%s.%s' % (app_name, model_name, field_name)

    if isinstance(FIELD_REGISTRY[fld], CategoryFKField):
        print (_('Dropping ForeignKey %(field_name) from %(model_name)') %
               {'field_name': field_name, 'model_name': model_name})
        try:
            db.start_transaction()
            table_name = mdl._meta.db_table
            db.delete_column(table_name, field_name)
            db.commit_transaction()
        except DatabaseError, e:
            db.rollback_transaction()
            raise e
    elif isinstance(FIELD_REGISTRY[fld], CategoryM2MField):
        print (_('Dropping Many2Many table between %(model_name) and %(category_table)') %
               {'model_name': model_name, 'category_table': 'category'})
        try:
            db.start_transaction()
            db.delete_table(table_name, cascade=False)
            db.commit_transaction()
        except DatabaseError, e:
            db.rollback_transaction()
            raise e

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Category'
        db.create_table('categories_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['categories.Category'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('order', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal('categories', ['Category'])

        # Adding unique constraint on 'Category', fields ['parent', 'name']
        db.create_unique('categories_category', ['parent_id', 'name'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Category', fields ['parent', 'name']
        db.delete_unique('categories_category', ['parent_id', 'name'])

        # Deleting model 'Category'
        db.delete_table('categories_category')


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_category_alternate_title__add_field_category_descripti
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Category.alternate_title'
        db.add_column('categories_category', 'alternate_title', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True), keep_default=False)

        # Adding field 'Category.description'
        db.add_column('categories_category', 'description', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # Adding field 'Category.meta_keywords'
        db.add_column('categories_category', 'meta_keywords', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True), keep_default=False)

        # Adding field 'Category.meta_extra'
        db.add_column('categories_category', 'meta_extra', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Category.alternate_title'
        db.delete_column('categories_category', 'alternate_title')

        # Deleting field 'Category.description'
        db.delete_column('categories_category', 'description')

        # Deleting field 'Category.meta_keywords'
        db.delete_column('categories_category', 'meta_keywords')

        # Deleting field 'Category.meta_extra'
        db.delete_column('categories_category', 'meta_extra')


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_category_thumbnail
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Category.thumbnail'
        db.add_column('categories_category', 'thumbnail', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Category.thumbnail'
        db.delete_column('categories_category', 'thumbnail')


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_category_thumbnail_width__add_field_category_thumbnail
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Category.thumbnail_width'
        db.add_column('categories_category', 'thumbnail_width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True), keep_default=False)

        # Adding field 'Category.thumbnail_height'
        db.add_column('categories_category', 'thumbnail_height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True), keep_default=False)

        # Changing field 'Category.thumbnail'
        db.alter_column('categories_category', 'thumbnail', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True))


    def backwards(self, orm):
        
        # Deleting field 'Category.thumbnail_width'
        db.delete_column('categories_category', 'thumbnail_width')

        # Deleting field 'Category.thumbnail_height'
        db.delete_column('categories_category', 'thumbnail_height')

        # Changing field 'Category.thumbnail'
        db.alter_column('categories_category', 'thumbnail', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True))


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_category_alternate_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Category.alternate_url'
        db.add_column('categories_category', 'alternate_url', self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Category.alternate_url'
        db.delete_column('categories_category', 'alternate_url')


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0006_auto__add_categoryrelation
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'CategoryRelation'
        db.create_table('categories_categoryrelation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('story', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['categories.Category'])),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('relation_type', self.gf('django.db.models.fields.CharField')(max_length='200', null=True, blank=True)),
        ))
        db.send_create_signal('categories', ['CategoryRelation'])


    def backwards(self, orm):
        
        # Deleting model 'CategoryRelation'
        db.delete_table('categories_categoryrelation')


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'}),
            'story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_category_active
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Category.active'
        db.add_column('categories_category', 'active', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Category.active'
        db.delete_column('categories_category', 'active')


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'}),
            'story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0008_changed_alternate_url_type
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Category.alternate_url'
        db.alter_column('categories_category', 'alternate_url', self.gf('django.db.models.fields.CharField')(max_length=200))


    def backwards(self, orm):
        
        # Changing field 'Category.alternate_url'
        db.alter_column('categories_category', 'alternate_url', self.gf('django.db.models.fields.URLField')(max_length=200))


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'}),
            'story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0009_setdefaultorder
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        orm.Category.objects.filter(order__isnull=True).update(order=0)

    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0010_add_field_categoryrelation_category
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Changing field 'Category.parent'
        db.alter_column('categories_category', 'parent_id', self.gf('mptt.fields.TreeForeignKey')(null=True, to=orm['categories.Category']))

        # Changing field 'Category.order'
        db.alter_column('categories_category', 'order', self.gf('django.db.models.fields.IntegerField')())

        # Adding field 'CategoryRelation.category'
        db.add_column('categories_categoryrelation', 'category', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['categories.Category']))


    def backwards(self, orm):
        # Changing field 'Category.parent'
        db.alter_column('categories_category', 'parent_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['categories.Category']))

        # Changing field 'Category.order'
        db.alter_column('categories_category', 'order', self.gf('django.db.models.fields.IntegerField')(null=True))
        
        # Deleting field 'CategoryRelation.category'
        db.delete_column('categories_categoryrelation', 'category_id')


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'new_cats'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'}),
            'story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0011_move_category_fks
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        orm.CategoryRelation.objects.update(category=models.F('story'))

    def backwards(self, orm):
        "Write your backwards methods here."
        orm.CategoryRelation.objects.update(story=models.F('category'))


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'new_cats'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'}),
            'story': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0012_remove_story_field
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'CategoryRelation.story'
        db.delete_column('categories_categoryrelation', 'story_id')
        


    def backwards(self, orm):
        # Adding field 'CategoryRelation.story'
        db.add_column('categories_categoryrelation', 'story', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['categories.Category']))


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = 0013_null_category_id
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'CategoryRelation.story'
        db.alter_column('categories_categoryrelation', 'category_id', self.gf('mptt.fields.TreeForeignKey')(null=True, to=orm['categories.Category']))
        


    def backwards(self, orm):
        # Adding field 'CategoryRelation.story'
        db.add_column('categories_categoryrelation', 'category_id', self.gf('mptt.fields.TreeForeignKey')(null=True, to=orm['categories.Category']))


    models = {
        'categories.category': {
            'Meta': {'ordering': "('tree_id', 'lft')", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Category'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'alternate_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'alternate_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'meta_extra': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'meta_keywords': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['categories.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'thumbnail': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'thumbnail_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'categories.categoryrelation': {
            'Meta': {'object_name': 'CategoryRelation'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['categories.Category']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': "'200'", 'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['categories']

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import force_unicode
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.files.storage import get_storage_class

from django.utils.translation import ugettext_lazy as _

from .settings import (RELATION_MODELS, RELATIONS, THUMBNAIL_UPLOAD_PATH,
                        THUMBNAIL_STORAGE)

from .base import CategoryBase

STORAGE = get_storage_class(THUMBNAIL_STORAGE)


class Category(CategoryBase):
    thumbnail = models.FileField(
        upload_to=THUMBNAIL_UPLOAD_PATH,
        null=True, blank=True,
        storage=STORAGE(),)
    thumbnail_width = models.IntegerField(blank=True, null=True)
    thumbnail_height = models.IntegerField(blank=True, null=True)
    order = models.IntegerField(default=0)
    alternate_title = models.CharField(
        blank=True,
        default="",
        max_length=100,
        help_text="An alternative title to use on pages with this category.")
    alternate_url = models.CharField(
        blank=True,
        max_length=200,
        help_text="An alternative URL to use instead of the one derived from "
                  "the category hierarchy.")
    description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(
        blank=True,
        default="",
        max_length=255,
        help_text="Comma-separated keywords for search engines.")
    meta_extra = models.TextField(
        blank=True,
        default="",
        help_text="(Advanced) Any additional HTML to be placed verbatim "
                  "in the &lt;head&gt;")

    @property
    def short_title(self):
        return self.name

    def get_absolute_url(self):
        """Return a path"""
        if self.alternate_url:
            return self.alternate_url
        prefix = reverse('categories_tree_list')
        ancestors = list(self.get_ancestors()) + [self, ]
        return prefix + '/'.join([force_unicode(i.slug) for i in ancestors]) + '/'

    if RELATION_MODELS:
        def get_related_content_type(self, content_type):
            """
            Get all related items of the specified content type
            """
            return self.categoryrelation_set.filter(
                content_type__name=content_type)

        def get_relation_type(self, relation_type):
            """
            Get all relations of the specified relation type
            """
            return self.categoryrelation_set.filter(relation_type=relation_type)

    def save(self, *args, **kwargs):
        if self.thumbnail:
            from django.core.files.images import get_image_dimensions
            import django
            if django.VERSION[1] < 2:
                width, height = get_image_dimensions(self.thumbnail.file)
            else:
                width, height = get_image_dimensions(self.thumbnail.file, close=True)
        else:
            width, height = None, None

        self.thumbnail_width = width
        self.thumbnail_height = height

        super(Category, self).save(*args, **kwargs)

    class Meta(CategoryBase.Meta):
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    class MPTTMeta:
        order_insertion_by = ('order', 'name')


if RELATIONS:
    CATEGORY_RELATION_LIMITS = reduce(lambda x, y: x | y, RELATIONS)
else:
    CATEGORY_RELATION_LIMITS = []


class CategoryRelationManager(models.Manager):
    def get_content_type(self, content_type):
        """
        Get all the items of the given content type related to this item.
        """
        qs = self.get_query_set()
        return qs.filter(content_type__name=content_type)

    def get_relation_type(self, relation_type):
        """
        Get all the items of the given relationship type related to this item.
        """
        qs = self.get_query_set()
        return qs.filter(relation_type=relation_type)


class CategoryRelation(models.Model):
    """Related category item"""
    category = models.ForeignKey(Category, verbose_name=_('category'))
    content_type = models.ForeignKey(
        ContentType, limit_choices_to=CATEGORY_RELATION_LIMITS, verbose_name=_('content type'))
    object_id = models.PositiveIntegerField(verbose_name=_('object id'))
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    relation_type = models.CharField(verbose_name=_('relation type'),
        max_length="200",
        blank=True,
        null=True,
        help_text=_("A generic text field to tag a relation, like 'leadphoto'."))

    objects = CategoryRelationManager()

    def __unicode__(self):
        return u"CategoryRelation"

try:
    from south.db import db  # South is required for migrating. Need to check for it
    from django.db.models.signals import post_syncdb
    from categories.migration import migrate_app
    post_syncdb.connect(migrate_app)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = registration
"""
These functions handle the adding of fields to other models
"""
from django.db.models import FieldDoesNotExist
import fields
from settings import FIELD_REGISTRY, MODEL_REGISTRY


def register_m2m(model, field_name='categories', extra_params={}):
    return _register(model, field_name, extra_params, fields.CategoryM2MField)


def register_fk(model, field_name='category', extra_params={}):
    return _register(model, field_name, extra_params, fields.CategoryFKField)


def _register(model, field_name, extra_params={}, field=fields.CategoryFKField):
    app_label = model._meta.app_label
    registry_name = ".".join((app_label, model.__name__, field_name)).lower()

    if registry_name in FIELD_REGISTRY:
        return  # raise AlreadyRegistered
    opts = model._meta
    try:
        opts.get_field(field_name)
    except FieldDoesNotExist:
        if app_label not in MODEL_REGISTRY:
            MODEL_REGISTRY[app_label] = []
        if model not in MODEL_REGISTRY[app_label]:
            MODEL_REGISTRY[app_label].append(model)
        FIELD_REGISTRY[registry_name] = field(**extra_params)
        FIELD_REGISTRY[registry_name].contribute_to_class(model, field_name)


def _process_registry(registry, call_func):
    """
    Given a dictionary, and a registration function, process the registry
    """
    from django.core.exceptions import ImproperlyConfigured
    from django.db.models.loading import get_model

    for key, value in registry.items():
        model = get_model(*key.split('.'))
        if model is None:
            raise ImproperlyConfigured(_('%(key) is not a model') % {'key' : key})
        if isinstance(value, (tuple, list)):
            for item in value:
                if isinstance(item, basestring):
                    call_func(model, item)
                elif isinstance(item, dict):
                    field_name = item.pop('name')
                    call_func(model, field_name, extra_params=item)
                else:
                    raise ImproperlyConfigured(_("%(settings) doesn't recognize the value of %(key)") %
                                               {'settings' : 'CATEGORY_SETTINGS', 'key' : key})
        elif isinstance(value, basestring):
            call_func(model, value)
        elif isinstance(value, dict):
            field_name = value.pop('name')
            call_func(model, field_name, extra_params=value)
        else:
            raise ImproperlyConfigured(_("%(settings) doesn't recognize the value of %(key)") %
                                       {'settings' : 'CATEGORY_SETTINGS', 'key' : key})

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

DEFAULT_SETTINGS = {
    'ALLOW_SLUG_CHANGE': False,
    'RELATION_MODELS': [],
    'M2M_REGISTRY': {},
    'FK_REGISTRY': {},
    'THUMBNAIL_UPLOAD_PATH': 'uploads/categories/thumbnails',
    'THUMBNAIL_STORAGE': settings.DEFAULT_FILE_STORAGE,
    'JAVASCRIPT_URL': getattr(settings, 'STATIC_URL', settings.MEDIA_URL) + 'js/',
    'SLUG_TRANSLITERATOR': '',
    'REGISTER_ADMIN': True,
    'RELATION_MODELS': [],
}

DEFAULT_SETTINGS.update(getattr(settings, 'CATEGORIES_SETTINGS', {}))

if DEFAULT_SETTINGS['SLUG_TRANSLITERATOR']:
    if callable(DEFAULT_SETTINGS['SLUG_TRANSLITERATOR']):
        pass
    elif isinstance(DEFAULT_SETTINGS['SLUG_TRANSLITERATOR'], basestring):
        from django.utils.importlib import import_module
        bits = DEFAULT_SETTINGS['SLUG_TRANSLITERATOR'].split(".")
        module = import_module(".".join(bits[:-1]))
        DEFAULT_SETTINGS['SLUG_TRANSLITERATOR'] = getattr(module, bits[-1])
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(_('%(transliterator) must be a callable or a string.') %
                                   {'transliterator': 'SLUG_TRANSLITERATOR'})
else:
    DEFAULT_SETTINGS['SLUG_TRANSLITERATOR'] = lambda x: x


# Add all the keys/values to the module's namespace
globals().update(DEFAULT_SETTINGS)

RELATIONS = [Q(app_label=al, model=m) for al, m in [x.split('.') for x in RELATION_MODELS]]

# The field registry keeps track of the individual fields created.
#  {'app.model.field': Field(**extra_params)}
#  Useful for doing a schema migration
FIELD_REGISTRY = {}

# The model registry keeps track of which models have one or more fields
# registered.
# {'app': [model1, model2]}
# Useful for admin alteration
MODEL_REGISTRY = {}

########NEW FILE########
__FILENAME__ = category_tags
from django import template
from django.db.models import get_model
from django.template import (Node, TemplateSyntaxError, VariableDoesNotExist,
                             FilterExpression)
from categories.base import CategoryBase
from categories.models import Category
from mptt.utils import drilldown_tree_for_node
from mptt.templatetags.mptt_tags import (tree_path, tree_info, RecurseTreeNode,
                                         full_tree_for_model)

register = template.Library()

register.filter("category_path", tree_path)
register.filter(tree_info)
register.tag("full_tree_for_category", full_tree_for_model)


def resolve(var, context):
    try:
        return var.resolve(context)
    except VariableDoesNotExist:
        try:
            return var.var
        except AttributeError:
            return var


def get_cat_model(model):
    """
    Return a class from a string or class
    """
    try:
        if isinstance(model, basestring):
            model_class = get_model(*model.split("."))
        elif issubclass(model, CategoryBase):
            model_class = model
        if model_class is None:
            raise TypeError
    except TypeError:
        raise TemplateSyntaxError("Unknown model submitted: %s" % model)
    return model_class


def get_category(category_string, model=Category):
    """
    Convert a string, including a path, and return the Category object
    """
    model_class = get_cat_model(model)
    category = str(category_string).strip("'\"")
    category = category.strip('/')

    cat_list = category.split('/')
    if len(cat_list) == 0:
        return None
    try:
        categories = model_class.objects.filter(name=cat_list[-1],
                                          level=len(cat_list) - 1)
        if len(cat_list) == 1 and len(categories) > 1:
            return None
        # If there is only one, use it. If there is more than one, check
        # if the parent matches the parent passed in the string
        if len(categories) == 1:
            return categories[0]
        else:
            for item in categories:
                if item.parent.name == cat_list[-2]:
                    return item
    except model_class.DoesNotExist:
        return None


class CategoryDrillDownNode(template.Node):
    def __init__(self, category, varname, model):
        self.category = category
        self.varname = varname
        self.model = model

    def render(self, context):
        category = resolve(self.category, context)
        if isinstance(category, CategoryBase):
            cat = category
        else:
            cat = get_category(category, self.model)
        try:
            if cat is not None:
                context[self.varname] = drilldown_tree_for_node(cat)
            else:
                context[self.varname] = []
        except:
            context[self.varname] = []
        return ''


@register.tag
def get_category_drilldown(parser, token):
    """
    Retrieves the specified category, its ancestors and its immediate children
    as an iterable.

    Syntax::

        {% get_category_drilldown "category name" [using "app.Model"] as varname %}

    Example::

        {% get_category_drilldown "/Grandparent/Parent" [using "app.Model"] as family %}

    or ::

        {% get_category_drilldown category_obj as family %}

    Sets family to::

        Grandparent, Parent, Child 1, Child 2, Child n
    """
    bits = token.split_contents()
    error_str = '%(tagname)s tag should be in the format {%% %(tagname)s ' \
                '"category name" [using "app.Model"] as varname %%} or ' \
                '{%% %(tagname)s category_obj as varname %%}.'
    if len(bits) == 4:
        if bits[2] != 'as':
            raise template.TemplateSyntaxError, error_str % {'tagname': bits[0]}
        if bits[2] == 'as':
            varname = bits[3].strip("'\"")
            model = "categories.category"
    if len(bits) == 6:
        if bits[2] not in ('using', 'as') or bits[4] not in ('using', 'as'):
            raise template.TemplateSyntaxError, error_str % {'tagname': bits[0]}
        if bits[2] == 'as':
            varname = bits[3].strip("'\"")
            model = bits[5].strip("'\"")
        if bits[2] == 'using':
            varname = bits[5].strip("'\"")
            model = bits[3].strip("'\"")
    category = FilterExpression(bits[1], parser)
    return CategoryDrillDownNode(category, varname, model)


@register.inclusion_tag('categories/breadcrumbs.html')
def breadcrumbs(category_string, separator=' > ', using='categories.category'):
    """
    {% breadcrumbs category separator="::" using="categories.category" %}

    Render breadcrumbs, using the ``categories/breadcrumbs.html`` template,
    using the optional ``separator`` argument.
    """
    cat = get_category(category_string, using)

    return {'category': cat, 'separator': separator}


@register.inclusion_tag('categories/ul_tree.html')
def display_drilldown_as_ul(category, using='categories.Category'):
    """
    Render the category with ancestors and children using the
    ``categories/ul_tree.html`` template.

    Example::

        {% display_drilldown_as_ul "/Grandparent/Parent" %}

    or ::

        {% display_drilldown_as_ul category_obj %}

    Returns::

        <ul>
          <li><a href="/categories/">Top</a>
          <ul>
            <li><a href="/categories/grandparent/">Grandparent</a>
            <ul>
              <li><a href="/categories/grandparent/parent/">Parent</a>
              <ul>
                <li><a href="/categories/grandparent/parent/child1">Child1</a></li>
                <li><a href="/categories/grandparent/parent/child2">Child2</a></li>
                <li><a href="/categories/grandparent/parent/child3">Child3</a></li>
              </ul>
              </li>
            </ul>
            </li>
          </ul>
          </li>
        </ul>
    """
    cat = get_category(category, using)
    if cat is None:
        return {'category': cat, 'path': []}
    else:                          
        return {'category': cat, 'path': drilldown_tree_for_node(cat)}


@register.inclusion_tag('categories/ul_tree.html')
def display_path_as_ul(category, using='categories.Category'):
    """
    Render the category with ancestors, but no children using the
    ``categories/ul_tree.html`` template.

    Example::

        {% display_path_as_ul "/Grandparent/Parent" %}

    or ::

        {% display_path_as_ul category_obj %}

    Returns::

        <ul>
            <li><a href="/categories/">Top</a>
            <ul>
                <li><a href="/categories/grandparent/">Grandparent</a></li>
            </ul>
            </li>
        </ul>
    """
    if isinstance(category, CategoryBase):
        cat = category
    else:
        cat = get_category(category)

    return {'category': cat, 'path': cat.get_ancestors() or []}


class TopLevelCategoriesNode(template.Node):
    def __init__(self, varname, model):
        self.varname = varname
        self.model = model

    def render(self, context):
        model = get_cat_model(self.model)
        context[self.varname] = model.objects.filter(parent=None).order_by('name')
        return ''


@register.tag
def get_top_level_categories(parser, token):
    """
    Retrieves an alphabetical list of all the categories that have no parents.

    Syntax::

        {% get_top_level_categories [using "app.Model"] as categories %}

    Returns an list of categories [<category>, <category>, <category, ...]
    """
    bits = token.split_contents()
    usage = 'Usage: {%% %s [using "app.Model"] as <variable> %%}' % bits[0]
    if len(bits) == 3:
        if bits[1] != 'as':
            raise template.TemplateSyntaxError(usage)
        varname = bits[2]
        model = "categories.category"
    elif len(bits) == 5:
        if bits[1] not in ('as', 'using') and bits[3] not in ('as', 'using'):
            raise template.TemplateSyntaxError(usage)
        if bits[1] == 'using':
            model = bits[2].strip("'\"")
            varname = bits[4].strip("'\"")
        else:
            model = bits[4].strip("'\"")
            varname = bits[2].strip("'\"")

    return TopLevelCategoriesNode(varname, model)


def get_latest_objects_by_category(category, app_label, model_name, set_name,
                                    date_field='pub_date', num=15):
    m = get_model(app_label, model_name)
    if not isinstance(category, CategoryBase):
        category = Category.objects.get(slug=str(category))
    children = category.children.all()
    ids = []
    for cat in list(children) + [category]:
        if hasattr(cat, '%s_set' % set_name):
            ids.extend([x.pk for x in getattr(cat, '%s_set' % set_name).all()[:num]])

    return m.objects.filter(pk__in=ids).order_by('-%s' % date_field)[:num]


class LatestObjectsNode(Node):
    def __init__(self, var_name, category, app_label, model_name, set_name,
                 date_field='pub_date', num=15):
        """
        Get latest objects of app_label.model_name
        """
        self.category = category
        self.app_label = app_label
        self.model_name = model_name
        self.set_name = set_name
        self.date_field = date_field
        self.num = num
        self.var_name = var_name

    def render(self, context):
        """
        Render this sucker
        """
        category = resolve(self.category, context)
        app_label = resolve(self.app_label, context)
        model_name = resolve(self.model_name, context)
        set_name = resolve(self.set_name, context)
        date_field = resolve(self.date_field, context)
        num = resolve(self.num, context)

        result = get_latest_objects_by_category(category, app_label, model_name,
                            set_name, date_field, num)
        context[self.var_name] = result

        return ''


def do_get_latest_objects_by_category(parser, token):
    """
    Get the latest objects by category

    {% get_latest_objects_by_category category app_name model_name set_name [date_field] [number] as [var_name] %}
    """
    proper_form = "{% get_latest_objects_by_category category app_name model_name set_name [date_field] [number] as [var_name] %}"
    bits = token.split_contents()

    if bits[-2] != 'as':
        raise TemplateSyntaxError("%s tag shoud be in the form: %s" % (bits[0], proper_form))
    if len(bits) < 7:
        raise TemplateSyntaxError("%s tag shoud be in the form: %s" % (bits[0], proper_form))
    if len(bits) > 9:
        raise TemplateSyntaxError("%s tag shoud be in the form: %s" % (bits[0], proper_form))
    category = FilterExpression(bits[1], parser)
    app_label = FilterExpression(bits[2], parser)
    model_name = FilterExpression(bits[3], parser)
    set_name = FilterExpression(bits[4], parser)
    var_name = bits[-1]
    if bits[5] != 'as':
        date_field = FilterExpression(bits[5], parser)
    else:
        date_field = FilterExpression(None, parser)
    if bits[6] != 'as':
        num = FilterExpression(bits[6], parser)
    else:
        num = FilterExpression(None, parser)
    return LatestObjectsNode(var_name, category, app_label, model_name, set_name,
                     date_field, num)

register.tag("get_latest_objects_by_category", do_get_latest_objects_by_category)


@register.filter
def tree_queryset(value):
    """
    Converts a normal queryset from an MPTT model to include all the ancestors
    so a filtered subset of items can be formatted correctly
    """
    from django.db.models.query import QuerySet
    from copy import deepcopy
    if not isinstance(value, QuerySet):
        return value

    qs = value
    qs2 = deepcopy(qs)
    # Reaching into the bowels of query sets to find out whether the qs is
    # actually filtered and we need to do the INCLUDE_ANCESTORS dance at all.
    # INCLUDE_ANCESTORS is quite expensive, so don't do it if not needed.
    is_filtered = bool(qs.query.where.children)
    if is_filtered:
        include_pages = set()
        # Order by 'rght' will return the tree deepest nodes first;
        # this cuts down the number of queries considerably since all ancestors
        # will already be in include_pages when they are checked, thus not
        # trigger additional queries.
        for p in qs2.order_by('rght').iterator():
            if p.parent_id and p.parent_id not in include_pages and \
                               p.id not in include_pages:
                ancestor_id_list = p.get_ancestors().values_list('id', flat=True)
                include_pages.update(ancestor_id_list)

        if include_pages:
            qs = qs | qs.model._default_manager.filter(id__in=include_pages)

        qs = qs.distinct()
    return qs


@register.tag
def recursetree(parser, token):
    """
    Iterates over the nodes in the tree, and renders the contained block for each node.
    This tag will recursively render children into the template variable {{ children }}.
    Only one database query is required (children are cached for the whole tree)

    Usage:
            <ul>
                {% recursetree nodes %}
                    <li>
                        {{ node.name }}
                        {% if not node.is_leaf_node %}
                            <ul>
                                {{ children }}
                            </ul>
                        {% endif %}
                    </li>
                {% endrecursetree %}
            </ul>
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError('%s tag requires a queryset' % bits[0])
    queryset_var = FilterExpression(bits[1], parser)

    template_nodes = parser.parse(('endrecursetree',))
    parser.delete_first_token()

    return RecurseTreeNode(template_nodes, queryset_var)

########NEW FILE########
__FILENAME__ = category_import
# test spaces in hierarchy
# test tabs in hierarchy
# test mixed
import unittest
import os
from categories.models import Category
from categories.management.commands.import_categories import Command
from django.core.management.base import CommandError


class CategoryImportTest(unittest.TestCase):
    def setUp(self):
        pass

    def _import_file(self, filename):
        root_cats = ['Category 1', 'Category 2', 'Category 3']
        testfile = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures', filename))
        cmd = Command()
        cmd.execute(testfile)
        roots = Category.tree.root_nodes()

        self.assertEqual(len(roots), 3)
        for item in roots:
            assert item.name in root_cats

        cat2 = Category.objects.get(name='Category 2')
        cat21 = cat2.children.all()[0]
        self.assertEqual(cat21.name, 'Category 2-1')
        cat211 = cat21.children.all()[0]
        self.assertEqual(cat211.name, 'Category 2-1-1')

    def testImportSpaceDelimited(self):
        Category.objects.all().delete()
        self._import_file('test_category_spaces.txt')

        items = Category.objects.all()

        self.assertEqual(items[0].name, 'Category 1')
        self.assertEqual(items[1].name, 'Category 1-1')
        self.assertEqual(items[2].name, 'Category 1-2')

    def testImportTabDelimited(self):
        Category.objects.all().delete()
        self._import_file('test_category_tabs.txt')

        items = Category.objects.all()

        self.assertEqual(items[0].name, 'Category 1')
        self.assertEqual(items[1].name, 'Category 1-1')
        self.assertEqual(items[2].name, 'Category 1-2')

    def testMixingTabsSpaces(self):
        """
        Should raise an exception.
        """
        string1 = ["cat1", "    cat1-1", "\tcat1-2-FAIL!", ""]
        string2 = ["cat1", "\tcat1-1", "    cat1-2-FAIL!", ""]
        cmd = Command()

        # raise Exception
        self.assertRaises(CommandError, cmd.parse_lines, string1)
        self.assertRaises(CommandError, cmd.parse_lines, string2)

########NEW FILE########
__FILENAME__ = manager
# test active returns only active items
import unittest
from categories.models import Category


class CategoryManagerTest(unittest.TestCase):
    def setUp(self):
        pass

    def testActive(self):
        """
        Should raise an exception.
        """
        all_count = Category.objects.all().count()
        self.assertEqual(Category.objects.active().count(), all_count)

        cat1 = Category.objects.get(name='Category 1')
        cat1.active = False
        cat1.save()

        active_count = all_count - cat1.get_descendants(True).count()
        self.assertEqual(Category.objects.active().count(), active_count)

########NEW FILE########
__FILENAME__ = registration
# Test adding 1 fk string
# Test adding 1 fk dict
# test adding many-to-many
# test adding 1 fk, 1 m2m

from django.test import TestCase

from categories.registration import (_process_registry, register_fk,
                                        register_m2m)


class CategoryRegistrationTest(TestCase):
    """
    Test various aspects of adding fields to a model.
    """

    def test_foreignkey_string(self):
        FK_REGISTRY = {
            'flatpages.flatpage': 'category'
        }
        _process_registry(FK_REGISTRY, register_fk)
        from django.contrib.flatpages.models import FlatPage
        self.assertTrue('category' in FlatPage()._meta.get_all_field_names())

    def test_foreignkey_dict(self):
        FK_REGISTRY = {
            'flatpages.flatpage': {'name': 'category'}
        }
        _process_registry(FK_REGISTRY, register_fk)
        from django.contrib.flatpages.models import FlatPage
        self.assertTrue('category' in FlatPage()._meta.get_all_field_names())

    def test_foreignkey_list(self):
        FK_REGISTRY = {
            'flatpages.flatpage': (
                {'name': 'category', 'related_name': 'cats'},
            )
        }
        _process_registry(FK_REGISTRY, register_fk)
        from django.contrib.flatpages.models import FlatPage
        self.assertTrue('category' in FlatPage()._meta.get_all_field_names())


# class Categorym2mTest(TestCase):
#     def test_m2m_string(self):
#         M2M_REGISTRY = {
#             'flatpages.flatpage': 'categories'
#         }
#         _process_registry(M2M_REGISTRY, register_m2m)
#         from django.contrib.flatpages.models import FlatPage
#         self.assertTrue('category' in FlatPage()._meta.get_all_field_names())

########NEW FILE########
__FILENAME__ = templatetags
from django.test import TestCase
from django import template

from categories.models import Category


class CategoryTagsTest(TestCase):

    fixtures = ['musicgenres.json']

    def render_template(self, template_string, context={}):
        """
        Return the rendered string or raise an exception.
        """
        tpl = template.Template(template_string)
        ctxt = template.Context(context)
        return tpl.render(ctxt)

    def testTooFewArguments(self):
        """
        Ensure that get_category raises an exception if there aren't enough arguments.
        """
        self.assertRaises(template.TemplateSyntaxError, self.render_template, '{% load category_tags %}{% get_category %}')

    def testBasicUsage(self):
        """
        Test that we can properly retrieve a category.
        """
        # display_path_as_ul
        rock_resp = u'<ul><li><a href="/categories/">Top</a></li></ul>'
        resp = self.render_template('{% load category_tags %}{% display_path_as_ul "/Rock" %}')
        self.assertEqual(resp, rock_resp)

        # display_drilldown_as_ul
        expected_resp = u'<ul><li><a href="/categories/">Top</a><ul><li><a href="/categories/world/">World</a><ul><li><strong>Worldbeat</strong><ul><li><a href="/categories/world/worldbeat/afrobeat/">Afrobeat</a></li></ul></li></ul></li></ul></li></ul>'
        resp = self.render_template('{% load category_tags %}'
            '{% display_drilldown_as_ul "/World/Worldbeat" "categories.category" %}')
        self.assertEqual(resp, expected_resp)

        # breadcrumbs
        expected_resp = u'<a href="/categories/world/">World</a> &gt; Worldbeat'
        resp = self.render_template('{% load category_tags %}'
            '{% breadcrumbs "/World/Worldbeat" " &gt; " "categories.category" %}')
        self.assertEqual(resp, expected_resp)

        # get_top_level_categories
        expected_resp = u'Avant-garde|Blues|Country|Easy listening|Electronic|Hip hop/Rap music|Jazz|Latin|Modern folk|Pop|Reggae|Rhythm and blues|Rock|World|'
        resp = self.render_template('{% load category_tags %}'
            '{% get_top_level_categories using "categories.category" as varname %}'
            '{% for item in varname %}{{ item }}|{% endfor %}')
        self.assertEqual(resp, expected_resp)

        # get_category_drilldown
        expected_resp = u"World|World &gt; Worldbeat|"
        resp = self.render_template('{% load category_tags %}'
            '{% get_category_drilldown "/World" using "categories.category" as var %}'
            '{% for item in var %}{{ item }}|{% endfor %}')
        self.assertEqual(resp, expected_resp)

        # recursetree
        expected_resp = u'<ul><li>Country<ul><li>Country pop<ul><li>Urban Cowboy</li></ul></li></ul></li><li>World<ul><li>Worldbeat<ul></ul></li></ul></li></ul>'
        ctxt = {'nodes': Category.objects.filter(name__in=("Worldbeat", "Urban Cowboy"))}
        resp = self.render_template('{% load category_tags %}'
            '<ul>{% recursetree nodes|tree_queryset %}<li>{{ node.name }}'
            '{% if not node.is_leaf_node %}<ul>{{ children }}'
            '</ul>{% endif %}</li>{% endrecursetree %}</ul>', ctxt)
        self.assertEqual(resp, expected_resp)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from .models import Category

try:
    from django.views.generic import DetailView, ListView
except ImportError:
    try:
        from cbv import DetailView, ListView
    except ImportError:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("For older versions of Django, you need django-cbv.")


categorytree_dict = {
    'queryset': Category.objects.filter(level=0)
}

urlpatterns = patterns('',
    url(
        r'^$', ListView.as_view(**categorytree_dict), name='categories_tree_list'
    ),
)

urlpatterns += patterns('categories.views',
    url(r'^(?P<path>.+)/$', 'category_detail', name='categories_category'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.template import RequestContext
from django.http import HttpResponse, Http404
from django.template.loader import select_template
from django.utils.translation import ugettext_lazy as _
try:
    from django.views.generic import DetailView, ListView
except ImportError:
    try:
        from cbv import DetailView, ListView
    except ImportError:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("For older versions of Django, you need django-cbv.")


from .models import Category


def category_detail(request, path,
    template_name='categories/category_detail.html', extra_context={}):
    path_items = path.strip('/').split('/')
    if len(path_items) >= 2:
        category = get_object_or_404(Category,
            slug__iexact=path_items[-1],
            level=len(path_items) - 1,
            parent__slug__iexact=path_items[-2])
    else:
        category = get_object_or_404(Category,
            slug__iexact=path_items[-1],
            level=len(path_items) - 1)

    templates = []
    while path_items:
        templates.append('categories/%s.html' % '_'.join(path_items))
        path_items.pop()
    templates.append(template_name)

    context = RequestContext(request)
    context.update({'category': category})
    if extra_context:
        context.update(extra_context)
    return HttpResponse(select_template(templates).render(context))


def get_category_for_path(path, queryset=Category.objects.all()):
    path_items = path.strip('/').split('/')
    if len(path_items) >= 2:
        queryset = queryset.filter(
            slug__iexact=path_items[-1],
            level=len(path_items) - 1,
            parent__slug__iexact=path_items[-2])
    else:
        queryset = queryset.filter(
            slug__iexact=path_items[-1],
            level=len(path_items) - 1)
    return queryset.get()


class CategoryDetailView(DetailView):
    model = Category
    path_field = 'path'

    def get_object(self, **kwargs):
        if self.path_field not in self.kwargs:
            raise AttributeError(u"Category detail view %s must be called with "
                                 u"a %s." % self.__class__.__name__, self.path_field)
        if self.queryset is None:
            queryset = self.get_queryset()
        try:
            return get_category_for_path(self.kwargs[self.path_field], self.model.objects.all())
        except ObjectDoesNotExist:
            raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

    def get_template_names(self):
        names = []
        path_items = self.kwargs[self.path_field].strip('/').split('/')
        while path_items:
            names.append('categories/%s.html' % '_'.join(path_items))
            path_items.pop()
        names.extend(super(CategoryDetailView, self).get_template_names())
        return names


class CategoryRelatedDetail(DetailView):
    path_field = 'category_path'
    object_name_field = None

    def get_object(self, **kwargs):
        queryset = super(CategoryRelatedDetail, self).get_queryset()
        category = get_category_for_path(self.kwargs[self.path_field])
        return queryset.get(category=category, slug=self.kwargs[self.slug_field])

    def get_template_names(self):
        names = []
        opts = self.object._meta
        path_items = self.kwargs[self.path_field].strip('/').split('/')
        if self.object_name_field:
            path_items.append(getattr(self.object, self.object_name_field))
        while path_items:
            names.append('%s/category_%s_%s%s.html' % (
                opts.app_label,
                '_'.join(path_items),
                opts.object_name.lower(),
                self.template_name_suffix)
            )
            path_items.pop()
        names.append('%s/category_%s%s.html' % (
            opts.app_label,
            opts.object_name.lower(),
            self.template_name_suffix)
        )
        names.extend(super(CategoryRelatedDetail, self).get_template_names())
        return names


class CategoryRelatedList(ListView):
    path_field = 'category_path'

    def get_queryset(self):
        queryset = super(CategoryRelatedList, self).get_queryset()
        category = get_category_for_path(self.kwargs['category_path'])
        return queryset.filter(category=category)

    def get_template_names(self):
        names = []
        if hasattr(self.object_list, 'model'):
            opts = self.object_list.model._meta
            path_items = self.kwargs[self.path_field].strip('/').split('/')
            while path_items:
                names.append('%s/category_%s_%s%s.html' % (
                    opts.app_label,
                    '_'.join(path_items),
                    opts.object_name.lower(),
                    self.template_name_suffix)
                )
                path_items.pop()
            names.append('%s/category_%s%s.html' % (
                opts.app_label,
                opts.object_name.lower(),
                self.template_name_suffix)
            )
        names.extend(super(CategoryRelatedList, self).get_template_names())
        return names

########NEW FILE########
__FILENAME__ = custom_categories1
from categories.models import CategoryBase

class SimpleCategory(CategoryBase):
    """
    A simple of catgorizing example
    """
    
    class Meta:
        verbose_name_plural = 'simple categories'

########NEW FILE########
__FILENAME__ = custom_categories2
from django.contrib import admin

from categories.admin import CategoryBaseAdmin

from .models import SimpleCategory

class SimpleCategoryAdmin(CategoryBaseAdmin):
    pass

admin.site.register(SimpleCategory, SimpleCategoryAdmin)
########NEW FILE########
__FILENAME__ = custom_categories3
class Category(CategoryBase):
    thumbnail = models.FileField(
        upload_to=THUMBNAIL_UPLOAD_PATH, 
        null=True, blank=True,
        storage=STORAGE(),)
    thumbnail_width = models.IntegerField(blank=True, null=True)
    thumbnail_height = models.IntegerField(blank=True, null=True)
    order = models.IntegerField(default=0)
    alternate_title = models.CharField(
        blank=True,
        default="",
        max_length=100,
        help_text="An alternative title to use on pages with this category.")
    alternate_url = models.CharField(
        blank=True, 
        max_length=200, 
        help_text="An alternative URL to use instead of the one derived from "
                  "the category hierarchy.")
    description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(
        blank=True,
        default="",
        max_length=255,
        help_text="Comma-separated keywords for search engines.")
    meta_extra = models.TextField(
        blank=True,
        default="",
        help_text="(Advanced) Any additional HTML to be placed verbatim "
                  "in the &lt;head&gt;")
########NEW FILE########
__FILENAME__ = custom_categories4
def save(self, *args, **kwargs):
    if self.thumbnail:
        from django.core.files.images import get_image_dimensions
        import django
        if django.VERSION[1] < 2:
            width, height = get_image_dimensions(self.thumbnail.file)
        else:
            width, height = get_image_dimensions(self.thumbnail.file, close=True)
    else:
        width, height = None, None
    
    self.thumbnail_width = width
    self.thumbnail_height = height
    
    super(Category, self).save(*args, **kwargs)
########NEW FILE########
__FILENAME__ = custom_categories5
class Meta(CategoryBase.Meta):
    verbose_name_plural = 'categories'

class MPTTMeta:
    order_insertion_by = ('order', 'name')

########NEW FILE########
__FILENAME__ = custom_categories6
class CategoryAdminForm(CategoryBaseAdminForm):
    class Meta:
        model = Category
    
    def clean_alternate_title(self):
        if self.instance is None or not self.cleaned_data['alternate_title']:
            return self.cleaned_data['name']
        else:
            return self.cleaned_data['alternate_title']
########NEW FILE########
__FILENAME__ = custom_categories7
class CategoryAdmin(CategoryBaseAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'alternate_title', 'active')
    fieldsets = (
        (None, {
            'fields': ('parent', 'name', 'thumbnail', 'active')
        }),
        ('Meta Data', {
            'fields': ('alternate_title', 'alternate_url', 'description', 
                        'meta_keywords', 'meta_extra'),
            'classes': ('collapse',),
        }),
        ('Advanced', {
            'fields': ('order', 'slug'),
            'classes': ('collapse',),
        }),
    )
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Categories documentation build configuration file, created by
# sphinx-quickstart on Tue Oct  6 07:53:33 2009.
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
sys.path.append(os.path.abspath('..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'example.settings'

import categories

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Categories'
copyright = u'2010-2012, Corey Oordt'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = categories.get_version(short=True)
# The full version, including alpha/beta/rc tags.
release = categories.get_version()

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
exclude_trees = ['_build']

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
htmlhelp_basename = 'DjangoCategoriesdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'DjangoCategories.tex', u'Django Categories Documentation',
   u'CoreyOordt', 'manual'),
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

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for sample project.
import os
import sys
import django

APP = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PROJ_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, APP)
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dev.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
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

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.abspath(os.path.join(PROJ_ROOT, 'media', 'uploads'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/uploads/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.abspath(os.path.join(PROJ_ROOT, 'media', 'static'))

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
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
SECRET_KEY = 'bwq#m)-zsey-fs)0#4*o=2z(v5g!ei=zytl9t-1hesh4b&-u^d'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
)


CATEGORIES_SETTINGS = {
    'ALLOW_SLUG_CHANGE': True,
    'RELATION_MODELS': ['simpletext.simpletext', 'flatpages.flatpage'],
    'FK_REGISTRY': {
        'flatpages.flatpage': 'category',
        'simpletext.simpletext': (
            'primary_category',
            {'name': 'secondary_category', 'related_name': 'simpletext_sec_cat'},
        ),
    },
    'M2M_REGISTRY': {
        'simpletext.simpletext': {'name': 'categories', 'related_name': 'm2mcats'},
        'flatpages.flatpage': (
            {'name': 'other_categories', 'related_name': 'other_cats'},
            {'name': 'more_categories', 'related_name': 'more_cats'},
        ),
    },
}

if django.VERSION[1] >= 4:
    from settings14 import *
if django.VERSION[1] == 3:
    from settings13 import *

########NEW FILE########
__FILENAME__ = settings13
ADMIN_MEDIA_PREFIX = '/static/admin/'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.flatpages',
    'categories',
    'categories.editor',
    'mptt',
    'simpletext',
    # 'south',
)

########NEW FILE########
__FILENAME__ = settings14
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.flatpages',
    'categories',
    'categories.editor',
    'mptt',
    'simpletext',
    # 'south',
)

########NEW FILE########
__FILENAME__ = admin
from models import SimpleText, SimpleCategory
from django.contrib import admin

from categories.admin import CategoryBaseAdmin, CategoryBaseAdminForm

class SimpleTextAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('name', 'description', )
        }),
    )


class SimpleCategoryAdminForm(CategoryBaseAdminForm):
    class Meta:
        model = SimpleCategory

class SimpleCategoryAdmin(CategoryBaseAdmin):
    form = SimpleCategoryAdminForm

admin.site.register(SimpleText, SimpleTextAdmin)
admin.site.register(SimpleCategory, SimpleCategoryAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models

from categories.base import CategoryBase

class SimpleText(models.Model):
    """
    (SimpleText description)
    """

    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created     = models.DateTimeField(auto_now_add=True)
    updated     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Simple Text'
        ordering = ('-created',)
        get_latest_by = 'updated'

    def __unicode__(self):
        return self.name

    # If using the get_absolute_url method, put the following line at the top of this file:
    from django.db.models import permalink

    @permalink
    def get_absolute_url(self):
        return ('simpletext_detail_view_name', [str(self.id)])

class SimpleCategory(CategoryBase):
    """A Test of catgorizing"""
    class Meta:
        verbose_name_plural = 'simple categories'


#import categories

#categories.register_fk(SimpleText, 'primary_category', {'related_name':'simpletext_primary_set'})
#categories.register_m2m(SimpleText, 'cats', )

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


import os

ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

urlpatterns = patterns('',
    # Example:
    # (r'^sample/', include('sample.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    (r'^categories/', include('categories.urls')),
    #(r'^cats/', include('categories.urls')),

    (r'^static/categories/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': ROOT_PATH + '/categories/media/categories/'}),

    # (r'^static/editor/(?P<path>.*)$', 'django.views.static.serve',
    #     {'document_root': ROOT_PATH + '/editor/media/editor/',
    #      'show_indexes':True}),

     (r'^static/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': os.path.join(ROOT_PATH, 'example', 'static')}),

)

########NEW FILE########
