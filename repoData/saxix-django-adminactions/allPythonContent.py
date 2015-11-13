__FILENAME__ = actions
# pylint: disable-msg= W0611
from .merge import merge
from .mass_update import mass_update
from .export import export_as_fixture, export_as_csv, export_delete_tree, export_as_xls
from .graph import graph_queryset

actions = [export_as_fixture,
           export_as_csv,
           export_as_xls,
           export_delete_tree,
           merge, mass_update,
           graph_queryset]


def add_to_site(site, exclude=None):
    """
    Register all the adminactions into passed site

    :param site: AdminSite instance
    :type site: django.contrib.admin.AdminSite

    :param exclude: name of the actions to exclude
    :type exclude: List
    :return: None

    Examples:

    >>> from django.contrib.admin import site
    >>> add_to_site(site)

    >>> from django.contrib.admin import site
    >>> add_to_site(site, exclude=['merge'])

    """
    exclude = exclude or []
    for action in actions:
        if action.__name__ not in exclude:
            site.add_action(action)

########NEW FILE########
__FILENAME__ = api
# -*- encoding: utf-8 -*-
import datetime
import xlwt
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ManyToManyField, OneToOneField
from django.http import HttpResponse
from adminactions.templatetags.actions import get_field_value

try:
    import unicodecsv as csv
except ImportError:
    import csv
from django.utils.encoding import smart_str
from django.utils import dateformat
from adminactions.utils import clone_instance, get_field_by_path, get_copy_of_instance, getattr_or_item  # NOQA

csv_options_default = {'date_format': 'd/m/Y',
                       'datetime_format': 'N j, Y, P',
                       'time_format': 'P',
                       'header': False,
                       'quotechar': '"',
                       'quoting': csv.QUOTE_ALL,
                       'delimiter': ';',
                       'escapechar': '\\', }

delimiters = ",;|:"
quotes = "'\"`"
escapechars = " \\"
ALL_FIELDS = -999


def merge(master, other, fields=None, commit=False, m2m=None, related=None):
    """
        Merge 'other' into master.

        `fields` is a list of fieldnames that must be readed from ``other`` to put into master.
        If ``fields`` is None ``master`` will get all the ``other`` values except primary_key.
        Finally ``other`` will be deleted and master will be preserved

    @param master:  Model instance
    @param other: Model instance
    @param fields: list of fieldnames to  merge
    @param m2m: list of m2m fields to merge. If empty will be removed
    @param related: list of related fieldnames to merge. If empty will be removed
    @return:
    """

    fields = fields or [f.name for f in master._meta.fields]

    all_m2m = {}
    all_related = {}

    if related == ALL_FIELDS:
        related = [rel.get_accessor_name()
                   for rel in master._meta.get_all_related_objects(False, False, False)]

    if m2m == ALL_FIELDS:
        m2m = [field.name for field in master._meta.many_to_many]

    if m2m and not commit:
        raise ValueError('Cannot save related with `commit=False`')
    with transaction.commit_manually():
        try:
            result = clone_instance(master)

            for fieldname in fields:
                f = get_field_by_path(master, fieldname)
                if f and not f.primary_key:
                    setattr(result, fieldname, getattr(other, fieldname))

            if m2m:
                for fieldname in set(m2m):
                    all_m2m[fieldname] = []
                    field_object = get_field_by_path(master, fieldname)
                    if not isinstance(field_object, ManyToManyField):
                        raise ValueError('{0} is not a ManyToManyField field'.format(fieldname))
                    source_m2m = getattr(other, field_object.name)
                    for r in source_m2m.all():
                        all_m2m[fieldname].append(r)
            if related:
                for name in set(related):
                    related_object = get_field_by_path(master, name)
                    all_related[name] = []
                    if related_object and isinstance(related_object.field, OneToOneField):
                        try:
                            accessor = getattr(other, name)
                            all_related[name] = [(related_object.field.name, accessor)]
                        except ObjectDoesNotExist:
                            #nothing to merge
                            pass
                    else:
                        accessor = getattr(other, name)
                        rel_fieldname = accessor.core_filters.keys()[0].split('__')[0]
                        for r in accessor.all():
                            all_related[name].append((rel_fieldname, r))

            if commit:
                for name, elements in all_related.items():
                    for rel_fieldname, element in elements:
                        setattr(element, rel_fieldname, master)
                        element.save()

                other.delete()
                result.save()
                for fieldname, elements in all_m2m.items():
                    dest_m2m = getattr(result, fieldname)
                    for element in elements:
                        dest_m2m.add(element)

        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()
    return result


def export_as_csv(queryset, fields=None, header=None, filename=None, options=None, out=None):
    """
        Exports a queryset as csv from a queryset with the given fields.

    :param queryset: queryset to export
    :param fields: list of fields names to export. None for all fields
    :param header: if True, the exported file will have the first row as column names
    :param filename: name of the filename
    :param options: CSVOptions() instance or none
    :param: out: object that implements File protocol. HttpResponse if None.

    :return: HttpResponse instance
    """
    if out is None:
        if filename is None:
            filename = filename or "%s.csv" % queryset.model._meta.verbose_name_plural.lower().replace(" ", "_")
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename="%s"' % filename.encode('us-ascii', 'replace')
    else:
        response = out

    if options is None:
        config = csv_options_default
    else:
        config = csv_options_default.copy()
        config.update(options)

    if fields is None:
        fields = [f.name for f in queryset.model._meta.fields]

    dialect = config.get('dialect', None)
    if dialect is not None:
        writer = csv.writer(response, dialect=dialect)
    else:
        writer = csv.writer(response,
                            escapechar=str(config['escapechar']),
                            delimiter=str(config['delimiter']),
                            quotechar=str(config['quotechar']),
                            quoting=int(config['quoting']))

    if bool(header):
        if isinstance(header, (list, tuple)):
            writer.writerow(header)
        else:
            writer.writerow([f for f in fields])

    for obj in queryset:
        row = []
        for fieldname in fields:
            value = get_field_value(obj, fieldname)
            if isinstance(value, datetime.datetime):
                value = dateformat.format(value, config['datetime_format'])
            elif isinstance(value, datetime.date):
                value = dateformat.format(value, config['date_format'])
            elif isinstance(value, datetime.time):
                value = dateformat.format(value, config['time_format'])
            row.append(smart_str(value))
        writer.writerow(row)

    return response


xls_options_default = {'date_format': 'd/m/Y',
                       'datetime_format': 'N j, Y, P',
                       'time_format': 'P',
                       'sheet_name': 'Sheet1',
                       'DateField': 'DD MMM-YY',
                       'DateTimeField': 'DD MMD YY hh:mm',
                       'TimeField': 'hh:mm',
                       'IntegerField': '#,##',
                       'PositiveIntegerField': '#,##',
                       'PositiveSmallIntegerField': '#,##',
                       'BigIntegerField': '#,##',
                       'DecimalField': '#,##0.00',
                       'BooleanField': 'boolean',
                       'NullBooleanField': 'boolean',
                       'EmailField': lambda value: 'HYPERLINK("mailto:%s","%s")' % (value, value),
                       'URLField': lambda value: 'HYPERLINK("%s","%s")' % (value, value),
                       'CurrencyColumn': '"$"#,##0.00);[Red]("$"#,##0.00)', }


def export_as_xls(queryset, fields=None, header=None, filename=None, options=None, out=None):
# sheet_name=None,  header_alt=None,
#             formatting=None, out=None):
    """
    Exports a queryset as xls from a queryset with the given fields.

    :param queryset: queryset to export (can also be list of namedtuples)
    :param fields: list of fields names to export. None for all fields
    :param header: if True, the exported file will have the first row as column names
    :param out: object that implements File protocol.
    :param header_alt: if is not None, and header is True, the first row will be as header_alt (same nr columns)
    :param formatting: if is None will use formatting_default
    :return: HttpResponse instance if out not supplied, otherwise out
    """

    def _get_qs_formats(queryset):
        formats = {}
        if hasattr(queryset, 'model'):
            for i, fieldname in enumerate(fields):
                try:
                    f, __, __, __, = queryset.model._meta.get_field_by_name(fieldname)
                    fmt = xls_options_default.get(f.name, xls_options_default.get(f.__class__.__name__, 'general'))
                    formats[i] = fmt
                except FieldDoesNotExist:
                    pass
                    # styles[i] = xlwt.easyxf(num_format_str=xls_options_default.get(col_class, 'general'))
                    # styles[i] = xls_options_default.get(col_class, 'general')

        return formats

    if out is None:
        if filename is None:
            filename = filename or "%s.xls" % queryset.model._meta.verbose_name_plural.lower().replace(" ", "_")
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment;filename="%s"' % filename.encode('us-ascii', 'replace')
    else:
        response = out

    config = xls_options_default.copy()
    if options:
        config.update(options)

    if fields is None:
        fields = [f.name for f in queryset.model._meta.fields]

    book = xlwt.Workbook(encoding="UTF-8", style_compression=2)
    sheet_name = config.pop('sheet_name')

    sheet = book.add_sheet(sheet_name)
    style = xlwt.XFStyle()
    row = 0
    heading_xf = xlwt.easyxf('font:height 200; font: bold on; align: wrap on, vert centre, horiz center')
    sheet.write(row, 0, '#', style)
    if header:
        if not isinstance(header, (list, tuple)):
            header = [unicode(f.verbose_name) for f in queryset.model._meta.fields if f.name in fields]

        for col, fieldname in enumerate(header, start=1):
            sheet.write(row, col, fieldname, heading_xf)
            sheet.col(col).width = 5000

    sheet.row(row).height = 500
    formats = _get_qs_formats(queryset)

    for rownum, row in enumerate(queryset):
        sheet.write(rownum + 1, 0, rownum + 1)
        for idx, fieldname in enumerate(fields):
            fmt = formats.get(idx, 'general')
            try:
                value = get_field_value(row, fieldname, usedisplay=False, raw_callable=False)
                if callable(fmt):
                    value = xlwt.Formula(fmt(value))
                    style = xlwt.easyxf(num_format_str='formula')
                else:
                    style = xlwt.easyxf(num_format_str=fmt)
                sheet.write(rownum + 1, idx + 1, value, style)
            except Exception as e:
                #logger.warning("TODO refine this exception: %s" % e)
                sheet.write(rownum + 1, idx + 1, str(e), style)

    book.save(response)
    return response

########NEW FILE########
__FILENAME__ = compat
from contextlib import contextmanager
import django.db.transaction as t

try:  # django >= 1.6
    from django.db.transaction import atomic  # noqa

    @contextmanager
    def nocommit(using=None):
        backup = t.get_autocommit(using)
        t.set_autocommit(False, using)
        t.enter_transaction_management(managed=True, using=using)
        yield
        t.rollback(using)
        t.leave_transaction_management(using)
        t.set_autocommit(backup, using)

except ImportError:  # django <=1.5

    @contextmanager
    def nocommit(using=None):
        t.enter_transaction_management(using=using)
        t.managed(True, using=using)
        yield
        t.rollback()
        t.leave_transaction_management(using=using)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-


class ActionInterrupted(Exception):
    """
    This exception can be raised by a :ref:`adminaction_requested` or :ref:`adminaction_start`
     to prevent action to be executed
    """


class FakeTransaction(Exception):
    pass

########NEW FILE########
__FILENAME__ = export
# -*- encoding: utf-8 -*-
from itertools import chain
from django.core.serializers import get_serializer_formats
from django.db import router
from django.db.models import ManyToManyField, ForeignKey
from django.db.models.deletion import Collector
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.safestring import mark_safe
from django.contrib.admin import helpers
from django.core import serializers as ser
from adminactions.exceptions import ActionInterrupted
from adminactions.forms import CSVOptions, XLSOptions
from adminactions.models import get_permission_codename
from adminactions.signals import adminaction_requested, adminaction_start, adminaction_end
from adminactions.api import export_as_csv as _export_as_csv, export_as_xls as _export_as_xls


def base_export(modeladmin, request, queryset, title, impl, name, template, form_class, ):
    """
        export a queryset to csv file
    """
    opts = modeladmin.model._meta
    perm = "{0}.{1}".format(opts.app_label.lower(), get_permission_codename('adminactions_export', opts))
    if not request.user.has_perm(perm):
        messages.error(request, _('Sorry you do not have rights to execute this action (%s)' % perm))
        return

    try:
        adminaction_requested.send(sender=modeladmin.model,
                                   action=name,
                                   request=request,
                                   queryset=queryset,
                                   modeladmin=modeladmin)
    except ActionInterrupted as e:
        messages.error(request, str(e))
        return

    cols = [(f.name, f.verbose_name) for f in queryset.model._meta.fields]
    initial = {'_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
               'select_across': request.POST.get('select_across') == '1',
               'action': request.POST.get('action'),
               'columns': [x for x, v in cols]}
    # initial.update(csv_options_default)

    if 'apply' in request.POST:
        form = form_class(request.POST)
        form.fields['columns'].choices = cols
        if form.is_valid():
            try:
                adminaction_start.send(sender=modeladmin.model,
                                       action=name,
                                       request=request,
                                       queryset=queryset,
                                       modeladmin=modeladmin,
                                       form=form)
            except ActionInterrupted as e:
                messages.error(request, str(e))
                return

            if hasattr(modeladmin, 'get_%s_filename' % name):
                filename = modeladmin.get_export_as_csv_filename(request, queryset)
            else:
                filename = None
            try:
                response = impl(queryset,
                                fields=form.cleaned_data['columns'],
                                header=form.cleaned_data.get('header', False),
                                filename=filename,
                                options=form.cleaned_data)
            except Exception as e:
                messages.error(request, "Error: (%s)" % str(e))
            else:
                adminaction_end.send(sender=modeladmin.model,
                                     action=name,
                                     request=request,
                                     queryset=queryset,
                                     modeladmin=modeladmin,
                                     form=form)
                return response
    else:
        form = form_class(initial=initial)
        form.fields['columns'].choices = cols

    adminForm = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, [], model_admin=modeladmin)
    media = modeladmin.media + adminForm.media
    # tpl = 'adminactions/export_csv.html'
    ctx = {'adminform': adminForm,
           'change': True,
           'title': title,
           'is_popup': False,
           'save_as': False,
           'has_delete_permission': False,
           'has_add_permission': False,
           'has_change_permission': True,
           'queryset': queryset,
           'opts': queryset.model._meta,
           'app_label': queryset.model._meta.app_label,
           'media': mark_safe(media)}
    return render_to_response(template, RequestContext(request, ctx))


def export_as_csv(modeladmin, request, queryset):
    return base_export(modeladmin, request, queryset,
                       impl=_export_as_csv,
                       name='export_as_csv',
                       title=_('Export as CSV'),
                       template='adminactions/export_csv.html',
                       form_class=CSVOptions)


export_as_csv.short_description = _("Export as CSV")


def export_as_xls(modeladmin, request, queryset):
    return base_export(modeladmin, request, queryset,
                       impl=_export_as_xls,
                       name='export_as_xls',
                       title=_('Export as XLS'),
                       template='adminactions/export_xls.html',
                       form_class=XLSOptions)


export_as_xls.short_description = _("Export as XLS")


class FlatCollector(object):
    def __init__(self, using):
        self._visited = []
        super(FlatCollector, self).__init__()

    def collect(self, objs):
        self.data = objs
        self.models = set([o.__class__ for o in self.data])


class ForeignKeysCollector(object):
    def __init__(self, using):
        self._visited = []
        super(ForeignKeysCollector, self).__init__()

    def _collect(self, objs):
        objects = []
        for obj in objs:
            if obj and obj not in self._visited:
                concrete_model = obj._meta.concrete_model
                obj = concrete_model.objects.get(pk=obj.pk)
                opts = obj._meta

                self._visited.append(obj)
                objects.append(obj)
                for field in chain(opts.fields, opts.local_many_to_many):
                    if isinstance(field, ManyToManyField):
                        target = getattr(obj, field.name).all()
                        objects.extend(self._collect(target))
                    elif isinstance(field, ForeignKey):
                        target = getattr(obj, field.name)
                        objects.extend(self._collect([target]))
        return objects

    def collect(self, objs):
        self._visited = []
        self.data = self._collect(objs)
        self.models = set([o.__class__ for o in self.data])

    def __str__(self):
        return mark_safe(self.data)


class FixtureOptions(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    select_across = forms.BooleanField(label='', required=False, initial=0,
                                       widget=forms.HiddenInput({'class': 'select-across'}))
    action = forms.CharField(label='', required=True, initial='', widget=forms.HiddenInput())

    use_natural_key = forms.BooleanField(required=False)
    on_screen = forms.BooleanField(label='Dump on screen', required=False)
    add_foreign_keys = forms.BooleanField(required=False)

    indent = forms.IntegerField(required=True, max_value=10, min_value=0)
    serializer = forms.ChoiceField(choices=zip(get_serializer_formats(), get_serializer_formats()))


def _dump_qs(form, queryset, data, filename):
    fmt = form.cleaned_data.get('serializer')

    json = ser.get_serializer(fmt)()
    ret = json.serialize(data, use_natural_keys=form.cleaned_data.get('use_natural_key', False),
                         indent=form.cleaned_data.get('indent'))

    response = HttpResponse(content_type='application/json')
    if not form.cleaned_data.get('on_screen', False):
        filename = filename or "%s.%s" % (queryset.model._meta.verbose_name_plural.lower().replace(" ", "_"), fmt)
        response['Content-Disposition'] = 'attachment;filename="%s"' % filename.encode('us-ascii', 'replace')
    response.content = ret
    return response


def export_as_fixture(modeladmin, request, queryset):
    initial = {'_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
               'select_across': request.POST.get('select_across') == '1',
               'action': request.POST.get('action'),
               'serializer': 'json',
               'indent': 4}
    opts = modeladmin.model._meta
    perm = "{0}.{1}".format(opts.app_label.lower(), get_permission_codename('adminactions_export', opts))
    if not request.user.has_perm(perm):
        messages.error(request, _('Sorry you do not have rights to execute this action (%s)' % perm))
        return

    try:
        adminaction_requested.send(sender=modeladmin.model,
                                   action='export_as_fixture',
                                   request=request,
                                   queryset=queryset,
                                   modeladmin=modeladmin)
    except ActionInterrupted as e:
        messages.error(request, str(e))
        return

    if 'apply' in request.POST:
        form = FixtureOptions(request.POST)
        if form.is_valid():
            try:
                adminaction_start.send(sender=modeladmin.model,
                                       action='export_as_fixture',
                                       request=request,
                                       queryset=queryset,
                                       modeladmin=modeladmin,
                                       form=form)
            except ActionInterrupted as e:
                messages.error(request, str(e))
                return
            try:
                _collector = ForeignKeysCollector if form.cleaned_data.get('add_foreign_keys') else FlatCollector
                c = _collector(None)
                c.collect(queryset)
                adminaction_end.send(sender=modeladmin.model,
                                     action='export_as_fixture',
                                     request=request,
                                     queryset=queryset,
                                     modeladmin=modeladmin,
                                     form=form)

                if hasattr(modeladmin, 'get_export_as_fixture_filename'):
                    filename = modeladmin.get_export_as_fixture_filename(request, queryset)
                else:
                    filename = None
                return _dump_qs(form, queryset, c.data, filename)
            except AttributeError as e:
                messages.error(request, str(e))
                return HttpResponseRedirect(request.path)
    else:
        form = FixtureOptions(initial=initial)

    adminForm = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, model_admin=modeladmin)
    media = modeladmin.media + adminForm.media
    tpl = 'adminactions/export_fixture.html'
    ctx = {'adminform': adminForm,
           'change': True,
           'title': _('Export as Fixture'),
           'is_popup': False,
           'save_as': False,
           'has_delete_permission': False,
           'has_add_permission': False,
           'has_change_permission': True,
           'queryset': queryset,
           'opts': queryset.model._meta,
           'app_label': queryset.model._meta.app_label,
           'media': mark_safe(media)}
    return render_to_response(tpl, RequestContext(request, ctx))


export_as_fixture.short_description = _("Export as fixture")


def export_delete_tree(modeladmin, request, queryset):
    """
    Export as fixture selected queryset and all the records that belong to.
    That mean that dump what will be deleted if the queryset was deleted
    """
    opts = modeladmin.model._meta
    perm = "{0}.{1}".format(opts.app_label.lower(), get_permission_codename('adminactions_export', opts))
    if not request.user.has_perm(perm):
        messages.error(request, _('Sorry you do not have rights to execute this action (%s)' % perm))
        return
    try:
        adminaction_requested.send(sender=modeladmin.model,
                                   action='export_delete_tree',
                                   request=request,
                                   queryset=queryset,
                                   modeladmin=modeladmin)
    except ActionInterrupted as e:
        messages.error(request, str(e))
        return

    initial = {'_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
               'select_across': request.POST.get('select_across') == '1',
               'action': request.POST.get('action'),
               'serializer': 'json',
               'indent': 4}

    if 'apply' in request.POST:
        form = FixtureOptions(request.POST)
        if form.is_valid():
            try:
                adminaction_start.send(sender=modeladmin.model,
                                       action='export_delete_tree',
                                       request=request,
                                       queryset=queryset,
                                       modeladmin=modeladmin,
                                       form=form)
            except ActionInterrupted as e:
                messages.error(request, str(e))
                return
            try:
                collect_related = form.cleaned_data.get('add_foreign_keys')
                using = router.db_for_write(modeladmin.model)

                c = Collector(using)
                c.collect(queryset, collect_related=collect_related)
                data = []
                for model, instances in c.data.items():
                    data.extend(instances)
                adminaction_end.send(sender=modeladmin.model,
                                     action='export_delete_tree',
                                     request=request,
                                     queryset=queryset,
                                     modeladmin=modeladmin,
                                     form=form)
                if hasattr(modeladmin, 'get_export_delete_tree_filename'):
                    filename = modeladmin.get_export_delete_tree_filename(request, queryset)
                else:
                    filename = None
                return _dump_qs(form, queryset, data, filename)
            except AttributeError as e:
                messages.error(request, str(e))
                return HttpResponseRedirect(request.path)
    else:
        form = FixtureOptions(initial=initial)

    adminForm = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, model_admin=modeladmin)
    media = modeladmin.media + adminForm.media
    tpl = 'adminactions/export_fixture.html'
    ctx = {'adminform': adminForm,
           'change': True,
           'title': _('Export Delete Tree'),
           'is_popup': False,
           'save_as': False,
           'has_delete_permission': False,
           'has_add_permission': False,
           'has_change_permission': True,
           'queryset': queryset,
           'opts': queryset.model._meta,
           'app_label': queryset.model._meta.app_label,
           'media': mark_safe(media)}
    return render_to_response(tpl, RequestContext(request, ctx))


export_delete_tree.short_description = _("Export delete tree")

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.forms.models import ModelForm
from .api import csv
from django.forms.widgets import SelectMultiple
from django.utils import formats
from adminactions.api import delimiters, quotes


class GenericActionForm(ModelForm):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    select_across = forms.BooleanField(label='', required=False, initial=0,
                                       widget=forms.HiddenInput({'class': 'select-across'}))
    action = forms.CharField(label='', required=True, initial='', widget=forms.HiddenInput())

    def configured_fields(self):
        return [field for field in self if not field.is_hidden and field.name.startswith('_')]

    def model_fields(self):
        """
        Returns a list of BoundField objects that aren't "private" fields.
        """
        return [field for field in self if
                not (field.name.startswith('_') or field.name in ['select_across', 'action'])]


class CSVOptions(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    select_across = forms.BooleanField(label='', required=False, initial=0,
                                       widget=forms.HiddenInput({'class': 'select-across'}))
    action = forms.CharField(label='', required=True, initial='', widget=forms.HiddenInput())

    header = forms.BooleanField(required=False)
    delimiter = forms.ChoiceField(choices=zip(delimiters, delimiters), initial=',')
    quotechar = forms.ChoiceField(choices=zip(quotes, quotes), initial="'")
    quoting = forms.ChoiceField(
        choices=((csv.QUOTE_ALL, 'All'),
                 (csv.QUOTE_MINIMAL, 'Minimal'),
                 (csv.QUOTE_NONE, 'None'),
                 (csv.QUOTE_NONNUMERIC, 'Non Numeric')), initial=csv.QUOTE_ALL)

    escapechar = forms.ChoiceField(choices=(('', ''), ('\\', '\\')), required=False)
    datetime_format = forms.CharField(initial=formats.get_format('DATETIME_FORMAT'))
    date_format = forms.CharField(initial=formats.get_format('DATE_FORMAT'))
    time_format = forms.CharField(initial=formats.get_format('TIME_FORMAT'))
    columns = forms.MultipleChoiceField(widget=SelectMultiple(attrs={'size': 20}))


class XLSOptions(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    select_across = forms.BooleanField(label='', required=False, initial=0,
                                       widget=forms.HiddenInput({'class': 'select-across'}))
    action = forms.CharField(label='', required=True, initial='', widget=forms.HiddenInput())

    header = forms.BooleanField(required=False)
    # delimiter = forms.ChoiceField(choices=zip(delimiters, delimiters), initial=',')
    # quotechar = forms.ChoiceField(choices=zip(quotes, quotes), initial="'")
    # quoting = forms.ChoiceField(
    #     choices=((csv.QUOTE_ALL, 'All'),
    #              (csv.QUOTE_MINIMAL, 'Minimal'),
    #              (csv.QUOTE_NONE, 'None'),
    #              (csv.QUOTE_NONNUMERIC, 'Non Numeric')), initial=csv.QUOTE_ALL)
    #
    # escapechar = forms.ChoiceField(choices=(('', ''), ('\\', '\\')), required=False)
    # datetime_format = forms.CharField(initial=formats.get_format('DATETIME_FORMAT'))
    # date_format = forms.CharField(initial=formats.get_format('DATE_FORMAT'))
    # time_format = forms.CharField(initial=formats.get_format('TIME_FORMAT'))
    columns = forms.MultipleChoiceField(widget=SelectMultiple(attrs={'size': 20}))

#

########NEW FILE########
__FILENAME__ = graph
# -*- coding: utf-8 -*-
'''
Created on 28/ott/2009

@author: sax
'''
from django.db.models.aggregates import Count
from django.db.models.fields.related import ForeignKey
from django.forms.fields import CharField, BooleanField, ChoiceField
from django.forms.forms import Form, DeclarativeFieldsMetaclass
from django.forms.widgets import HiddenInput, MultipleHiddenInput
import json
from django.contrib import messages
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.encoding import force_unicode
from django.contrib.admin import helpers

from adminactions.exceptions import ActionInterrupted
from adminactions.signals import adminaction_requested, adminaction_start, adminaction_end


def graph_form_factory(model):
    app_name = model._meta.app_label
    model_name = model.__name__

    model_fields = [(f.name, f.verbose_name) for f in model._meta.fields if not f.primary_key]
    graphs = [('PieChart', 'PieChart'), ('BarChart', 'BarChart')]
    model_fields.insert(0, ('', 'N/A'))
    class_name = "%s%sGraphForm" % (app_name, model_name)
    attrs = {'initial': {'app': app_name, 'model': model_name},
             '_selected_action': CharField(widget=MultipleHiddenInput),
             'select_across': BooleanField(initial='0', widget=HiddenInput, required=False),
             'app': CharField(initial=app_name, widget=HiddenInput),
             'model': CharField(initial=model_name, widget=HiddenInput),
             'graph_type': ChoiceField(label="Graph type", choices=graphs, required=True),
             'axes_x': ChoiceField(label="Group by and count by", choices=model_fields, required=True)}

    return DeclarativeFieldsMetaclass(str(class_name), (Form,), attrs)


def graph_queryset(modeladmin, request, queryset):
    MForm = graph_form_factory(modeladmin.model)

    graph_type = table = None
    extra = '{}'
    try:
        adminaction_requested.send(sender=modeladmin.model,
                                   action='graph_queryset',
                                   request=request,
                                   queryset=queryset,
                                   modeladmin=modeladmin)
    except ActionInterrupted as e:
        messages.error(request, str(e))
        return

    if 'apply' in request.POST:
        form = MForm(request.POST)
        if form.is_valid():
            try:
                adminaction_start.send(sender=modeladmin.model,
                                       action='graph_queryset',
                                       request=request,
                                       queryset=queryset,
                                       modeladmin=modeladmin,
                                       form=form)
            except ActionInterrupted as e:
                messages.error(request, str(e))
                return
            try:
                x = form.cleaned_data['axes_x']
                #            y = form.cleaned_data['axes_y']
                graph_type = form.cleaned_data['graph_type']

                field, model, direct, m2m = modeladmin.model._meta.get_field_by_name(x)
                cc = queryset.values_list(x).annotate(Count(x)).order_by()
                if isinstance(field, ForeignKey):
                    data_labels = []
                    for value, cnt in cc:
                        data_labels.append(str(field.rel.to.objects.get(pk=value)))
                elif isinstance(field, BooleanField):
                    data_labels = [str(l) for l, v in cc]
                elif hasattr(modeladmin.model, 'get_%s_display' % field.name):
                    data_labels = []
                    for value, cnt in cc:
                        data_labels.append(force_unicode(dict(field.flatchoices).get(value, value), strings_only=True))
                else:
                    data_labels = [str(l) for l, v in cc]
                data = [v for l, v in cc]

                if graph_type == 'BarChart':
                    table = [[10, 20]]
                    extra = """{seriesDefaults:{renderer:$.jqplot.BarRenderer,
                                                rendererOptions: {fillToZero: true,
                                                                  barDirection: 'horizontal'},
                                                shadowAngle: -135,
                                               },
                                series:[%s],
                                axes: {yaxis: {renderer: $.jqplot.CategoryAxisRenderer,
                                                ticks: %s},
                                       xaxis: {pad: 1.05,
                                               tickOptions: {formatString: '%%d'}}
                                      }
                                }""" % (json.dumps(data_labels), json.dumps(data_labels))
                elif graph_type == 'PieChart':
                    table = [zip(data_labels, data)]
                    extra = """{seriesDefaults: {renderer: jQuery.jqplot.PieRenderer,
                                                rendererOptions: {fill: true,
                                                                    showDataLabels: true,
                                                                    sliceMargin: 4,
                                                                    lineWidth: 5}},
                             legend: {show: true, location: 'e'}}"""

            except Exception as e:
                messages.error(request, 'Unable to produce valid data: %s' % str(e))
            else:
                adminaction_end.send(sender=modeladmin.model,
                                     action='graph_queryset',
                                     request=request,
                                     queryset=queryset,
                                     modeladmin=modeladmin,
                                     form=form)
    elif request.method == 'POST':
        # total = queryset.all().count()
        initial = {helpers.ACTION_CHECKBOX_NAME: request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
                   'select_across': request.POST.get('select_across', 0)}
        form = MForm(initial=initial)
    else:
        initial = {helpers.ACTION_CHECKBOX_NAME: request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
                   'select_across': request.POST.get('select_across', 0)}
        form = MForm(initial=initial)

    adminForm = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, [], model_admin=modeladmin)
    media = modeladmin.media + adminForm.media

    ctx = {'adminform': adminForm,
           'action': 'graph_queryset',
           'opts': modeladmin.model._meta,
            'title': u"Graph %s" % force_unicode(modeladmin.opts.verbose_name_plural),
           'app_label': queryset.model._meta.app_label,
           'media': media,
           'extra': extra,
           'as_json': json.dumps(table),
           'graph_type': graph_type}
    return render_to_response('adminactions/charts.html', RequestContext(request, ctx))


graph_queryset.short_description = "Graph selected records"

########NEW FILE########
__FILENAME__ = mass_update
import re
import json
import datetime
import string
from collections import defaultdict

from django import forms
from django.db import IntegrityError, transaction
from django.db.models import fields as df
from django.forms import fields as ff
from django.forms.models import modelform_factory, ModelMultipleChoiceField, construct_instance, InlineForeignKeyField
from django.contrib import messages
from django.contrib.admin import helpers
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.encoding import force_unicode
from django.utils.functional import curry
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from adminactions.models import get_permission_codename
from adminactions.exceptions import ActionInterrupted
from adminactions.forms import GenericActionForm
from adminactions.signals import adminaction_requested, adminaction_start, adminaction_end


DO_NOT_MASS_UPDATE = 'do_NOT_mass_UPDATE'

add = lambda arg, value: value + arg
sub = lambda arg, value: value - arg
add_percent = lambda arg, value: value + (value * arg / 100)
sub_percent = lambda arg, value: value - (value * arg / 100)
negate = lambda value: not value
trim = lambda arg, value: value.strip(arg)

change_domain = lambda arg, value: re.sub('@.*', arg, value)
change_protocol = lambda arg, value: re.sub('^[a-z]*://', "%s://" % arg, value)

disable_if_not_nullable = lambda field: field.null
disable_if_unique = lambda field: not field.unique


class OperationManager(object):
    """
    Operate like a dictionary where the key are django.form.Field classes
    and value are tuple of function, param_allowed, enabler, description

    function: callable that can accept one or two arguments
                :param arg is the value set in the MassUpdateForm
                :param value is the existing field's value of the record
                :return new value to store
    param_allowed: boolean that enable the MassUpdateForm argument:
    enabler: boolean or callable that receive the specific Model field as argument
            and should returns True/False to indicate the `function` can be used with this
            specific field. i.e. disable 'set null` if the field cannot be null, or disable `set` if
            the field is unique
    description: string description of the operator
    """

    COMMON = [('set', (None, True, disable_if_unique, "")),
              ('set null', (lambda old_value: None, False, disable_if_not_nullable, ""))]

    def __init__(self, _dict):
        self._dict = dict()
        for field_class, args in _dict.items():
            self._dict[field_class] = SortedDict(self.COMMON + args)

    def get(self, field_class, d=None):
        return self._dict.get(field_class, SortedDict(self.COMMON))

    def get_for_field(self, field):
        """ returns valid functions for passed field
            :param field Field django Model Field
            :return list of (label, (__, param, enabler, help))
        """
        valid = SortedDict()
        operators = self.get(field.__class__)
        for label, (func, param, enabler, help) in operators.items():
            if (callable(enabler) and enabler(field)) or enabler is True:
                valid[label] = (func, param, enabler, help)
        return valid

    def __getitem__(self, field_class):
        return self.get(field_class)


OPERATIONS = OperationManager({
    df.CharField: [('upper', (string.upper, False, True, "convert to uppercase")),
                   ('lower', (string.lower, False, True, "convert to lowercase")),
                   ('capitalize', (string.capitalize, False, True, "capitalize first character")),
                   ('capwords', (string.capwords, False, True, "capitalize each word")),
                   ('swapcase', (string.swapcase, False, True, "")),
                   ('trim', (string.strip, False, True, "leading and trailing whitespace"))],
    df.IntegerField: [('add percent', (add_percent, True, True, "add <arg> percent to existing value")),
                      ('sub percent', (sub_percent, True, True, "")),
                      ('sub', (sub_percent, True, True, "")),
                      ('add', (add, True, True, ""))],
    df.BooleanField: [('swap', (negate, False, True, ""))],
    df.NullBooleanField: [('swap', (negate, False, True, ""))],
    df.EmailField: [('change domain', (change_domain, True, True, ""))],
    df.URLField: [('change protocol', (change_protocol, True, True, ""))]
})


class MassUpdateForm(GenericActionForm):
    _no_sample_for = []
    _clean = forms.BooleanField(label='clean()',
                                required=False,
                                help_text="if checked calls obj.clean()")

    _validate = forms.BooleanField(label='Validate',
                                   help_text="if checked use obj.save() instead of manager.update()")
    _unique_transaction = forms.BooleanField(label='Unique transaction',
                                             required=False,
                                             help_text="If checked create one transaction for the whole update. "
                                                       "If any record cannot be updated everything will be rolled-back")

    def __init__(self, *args, **kwargs):
        super(MassUpdateForm, self).__init__(*args, **kwargs)
        self._errors = None

    #def is_valid(self):
    #    return super(MassUpdateForm, self).is_valid()

    def _get_validation_exclusions(self):
        exclude = super(MassUpdateForm, self)._get_validation_exclusions()
        for name, field in self.fields.items():
            function = self.data.get('func_id_%s' % name, False)
            if function:
                exclude.append(name)
        return exclude

    #def _clean_fields(self):
    #    if self.cleaned_data.get('_clean', False):
    #        super(MassUpdateForm, self)._clean_fields()
    #
    def _post_clean(self):
        # must be overriden to bypass instance.clean()
        if self.cleaned_data.get('_clean', False):
            opts = self._meta
            self.instance = construct_instance(self, self.instance, opts.fields, opts.exclude)
            exclude = self._get_validation_exclusions()
            for f_name, field in self.fields.items():
                if isinstance(field, InlineForeignKeyField):
                    exclude.append(f_name)
                    # Clean the model instance's fields.
            try:
                self.instance.clean_fields(exclude=exclude)
            except ValidationError, e:
                self._update_errors(e.message_dict)

    def _clean_fields(self):
        for name, field in self.fields.items():
            raw_value = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(name))
            try:
                if isinstance(field, ff.FileField):
                    initial = self.initial.get(name, field.initial)
                    value = field.clean(raw_value, initial)
                else:
                    enabler = 'chk_id_%s' % name
                    function = self.data.get('func_id_%s' % name, False)
                    if self.data.get(enabler, False):
                        field_object, model, direct, m2m = self._meta.model._meta.get_field_by_name(name)
                        value = field.clean(raw_value)
                        if function:
                            func, hasparm, __, __ = OPERATIONS.get_for_field(field_object)[function]
                            if func is None:
                                pass
                            elif hasparm:
                                value = curry(func, value)
                            else:
                                value = func

                        self.cleaned_data[name] = value
                    if hasattr(self, 'clean_%s' % name):
                        value = getattr(self, 'clean_%s' % name)()
                        self.cleaned_data[name] = value
            except ValidationError, e:
                self._errors[name] = self.error_class(e.messages)
                if name in self.cleaned_data:
                    del self.cleaned_data[name]

    def clean__validate(self):
        return bool(self.data.get('_validate', 0))

    def clean__unique_transaction(self):
        return bool(self.data.get('_unique_transaction', 0))

    def clean__clean(self):
        return bool(self.data.get('_clean', 0))


def mass_update(modeladmin, request, queryset):
    """
        mass update queryset
    """

    def not_required(field, **kwargs):
        """ force all fields as not required"""
        kwargs['required'] = False
        return field.formfield(**kwargs)

    opts = modeladmin.model._meta
    perm = "{0}.{1}".format(opts.app_label.lower(), get_permission_codename('adminactions_massupdate', opts))
    if not request.user.has_perm(perm):
        messages.error(request, _('Sorry you do not have rights to execute this action'))
        return

    try:
        adminaction_requested.send(sender=modeladmin.model,
                                   action='mass_update',
                                   request=request,
                                   queryset=queryset,
                                   modeladmin=modeladmin)
    except ActionInterrupted as e:
        messages.error(request, str(e))
        return

    # Allows to specified a custom mass update Form in the ModelAdmin
    mass_update_form = getattr(modeladmin, 'mass_update_form', MassUpdateForm)

    MForm = modelform_factory(modeladmin.model, form=mass_update_form, formfield_callback=not_required)
    grouped = defaultdict(lambda: [])
    selected_fields = []
    initial = {'_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
               'select_across': request.POST.get('select_across') == '1',
               'action': 'mass_update'}

    if 'apply' in request.POST:
        form = MForm(request.POST)
        if form.is_valid():
            try:
                adminaction_start.send(sender=modeladmin.model,
                                       action='mass_update',
                                       request=request,
                                       queryset=queryset,
                                       modeladmin=modeladmin,
                                       form=form)
            except ActionInterrupted as e:
                messages.error(request, str(e))
                return HttpResponseRedirect(request.get_full_path())

            need_transaction = form.cleaned_data.get('_unique_transaction', False)
            validate = form.cleaned_data.get('_validate', False)
            clean = form.cleaned_data.get('_clean', False)

            updated = 0
            errors = {}
            if validate:
                if need_transaction:
                    transaction.enter_transaction_management()
                    transaction.managed(True)
                for record in queryset:
                    for field_name, value_or_func in form.cleaned_data.items():
                        if callable(value_or_func):
                            old_value = getattr(record, field_name)
                            setattr(record, field_name, value_or_func(old_value))
                        else:
                            setattr(record, field_name, value_or_func)
                    try:
                        if clean:
                            record.clean()
                        record.save()
                    except IntegrityError as e:
                        errors[record.pk] = str(e)
                        if need_transaction:
                            transaction.rollback()
                            updated = 0
                            break
                    else:
                        updated += 1
                if updated:
                    messages.info(request, _("Updated %s records") % updated)
                if len(errors):
                    messages.error(request, "%s records not updated due errors" % len(errors))
                try:
                    adminaction_end.send(sender=modeladmin.model,
                                         action='mass_update',
                                         request=request,
                                         queryset=queryset,
                                         modeladmin=modeladmin,
                                         form=form,
                                         errors=errors,
                                         updated=updated)
                    if need_transaction:
                        transaction.commit()
                except ActionInterrupted:
                    if need_transaction:
                        transaction.rollback()
                finally:
                    if need_transaction:
                        transaction.leave_transaction_management()

            else:
                values = {}
                for field_name, value in form.cleaned_data.items():
                    if isinstance(form.fields[field_name], ModelMultipleChoiceField):
                        messages.error(request, "Unable no mass update ManyToManyField without 'validate'")
                        return HttpResponseRedirect(request.get_full_path())
                    elif callable(value):
                        messages.error(request, "Unable no mass update using operators without 'validate'")
                        return HttpResponseRedirect(request.get_full_path())
                    elif field_name not in ['_selected_action', '_validate', 'select_across', 'action']:
                        values[field_name] = value
                queryset.update(**values)

            return HttpResponseRedirect(request.get_full_path())
    else:
        initial.update({'action': 'mass_update', '_validate': 1})
        #form = MForm(initial=initial)
        prefill_with = request.POST.get('prefill-with', None)
        prefill_instance = None
        try:
            # Gets the instance directly from the queryset for data security
            prefill_instance = queryset.get(pk=prefill_with)
        except ObjectDoesNotExist:
            pass

        form = MForm(initial=initial, instance=prefill_instance)

    for el in queryset.all()[:10]:
        for f in modeladmin.model._meta.fields:
            if f.name not in form._no_sample_for:
                if hasattr(f, 'flatchoices') and f.flatchoices:
                    grouped[f.name] = dict(getattr(f, 'flatchoices')).values()
                elif hasattr(f, 'choices') and f.choices:
                    grouped[f.name] = dict(getattr(f, 'choices')).values()
                elif isinstance(f, df.BooleanField):
                    grouped[f.name] = [True, False]
                else:
                    value = getattr(el, f.name)
                    if value is not None and value not in grouped[f.name]:
                        grouped[f.name].append(value)
                    initial[f.name] = initial.get(f.name, value)

    adminForm = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, [], model_admin=modeladmin)
    media = modeladmin.media + adminForm.media
    dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.date) else str(obj)
    tpl = 'adminactions/mass_update.html'
    ctx = {'adminform': adminForm,
           'form': form,
           'title': u"Mass update %s" % force_unicode(modeladmin.opts.verbose_name_plural),
           'grouped': grouped,
           'fieldvalues': json.dumps(grouped, default=dthandler),
           'change': True,
           'selected_fields': selected_fields,
           'is_popup': False,
           'save_as': False,
           'has_delete_permission': False,
           'has_add_permission': False,
           'has_change_permission': True,
           'opts': modeladmin.model._meta,
           'app_label': modeladmin.model._meta.app_label,
           #           'action': 'mass_update',
           #           'select_across': request.POST.get('select_across')=='1',
           'media': mark_safe(media),
           'selection': queryset}

    return render_to_response(tpl, RequestContext(request, ctx))


mass_update.short_description = "Mass update"

########NEW FILE########
__FILENAME__ = merge
# -*- coding: utf-8 -*-
# from django.db import transaction
import django
from datetime import datetime
from django.utils.encoding import force_unicode
from adminactions import api
from django.contrib import messages
from django.contrib.admin import helpers
from django import forms
from django.forms import TextInput, HiddenInput, DateTimeField
from django.db import models
from django.forms.formsets import formset_factory
from django.forms.models import modelform_factory, model_to_dict
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from adminactions.forms import GenericActionForm
from adminactions.models import get_permission_codename
from adminactions.utils import clone_instance, model_supports_transactions
import adminactions.compat as transaction


class MergeForm(GenericActionForm):
    DEP_MOVE = 1
    DEP_DELETE = 2
    GEN_IGNORE = 1
    GEN_RELATED = 2
    GEN_DEEP = 3

    dependencies = forms.ChoiceField(label=_('Dependencies'),
                                     choices=((DEP_MOVE, _("Move")), (DEP_DELETE, _("Delete"))))

    # generic = forms.ChoiceField(label=_('Search GenericForeignKeys'),
    #                             help_text=_("Search for generic relation"),
    #                             choices=((GEN_IGNORE, _("No")),
    #                                      (GEN_RELATED, _("Only Related (look for Managers)")),
    #                                      (GEN_DEEP, _("Analyze Mode (very slow)"))))

    master_pk = forms.CharField(widget=HiddenInput)
    other_pk = forms.CharField(widget=HiddenInput)
    field_names = forms.CharField(required=False, widget=HiddenInput)

    def action_fields(self):
        for fieldname in ['dependencies', 'master_pk', 'other_pk', 'field_names']:
            bf = self[fieldname]
            yield HiddenInput().render(fieldname, bf.value())

    def clean_dependencies(self):
        return int(self.cleaned_data['dependencies'])

    def clean_field_names(self):
        return self.cleaned_data['field_names'].split(',')

    def full_clean(self):
        super(MergeForm, self).full_clean()

    def clean(self):
        return super(MergeForm, self).clean()

    def is_valid(self):
        return super(MergeForm, self).is_valid()

    class Media:
        js = ['adminactions/js/merge.min.js']
        css = {'all': ['adminactions/css/adminactions.min.css']}


def merge(modeladmin, request, queryset):
    """
    Merge two model instances. Move all foreign keys.

    """

    opts = modeladmin.model._meta
    perm = "{0}.{1}".format(opts.app_label.lower(), get_permission_codename('adminactions_merge', opts))
    if not request.user.has_perm(perm):
        messages.error(request, _('Sorry you do not have rights to execute this action (%s)' % perm))
        return

    def raw_widget(field, **kwargs):
        """ force all fields as not required"""
        kwargs['widget'] = TextInput({'class': 'raw-value'})
        return field.formfield(**kwargs)

    merge_form = getattr(modeladmin, 'merge_form', MergeForm)
    MForm = modelform_factory(modeladmin.model, form=merge_form, formfield_callback=raw_widget)
    OForm = modelform_factory(modeladmin.model, formfield_callback=raw_widget)

    tpl = 'adminactions/merge.html'
    transaction_supported = model_supports_transactions(modeladmin.model)
    transaction_supported = True
    ctx = {
        '_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
        'transaction_supported': transaction_supported,
        'select_across': request.POST.get('select_across') == '1',
        'action': request.POST.get('action'),
        'fields': [f for f in queryset.model._meta.fields if not f.primary_key and f.editable],
        'app_label': queryset.model._meta.app_label,
        'result': '',
        'opts': queryset.model._meta}

    if 'preview' in request.POST:
        master = queryset.get(pk=request.POST.get('master_pk'))
        original = clone_instance(master)
        other = queryset.get(pk=request.POST.get('other_pk'))
        formset = formset_factory(OForm)(initial=[model_to_dict(master), model_to_dict(other)])
        with transaction.nocommit():
            form = MForm(request.POST, instance=master)
            other.delete()
            form_is_valid = form.is_valid()
        if form_is_valid:
            ctx.update({'original': original})
            tpl = 'adminactions/merge_preview.html'
        else:
            master = queryset.get(pk=request.POST.get('master_pk'))
            other = queryset.get(pk=request.POST.get('other_pk'))

    elif 'apply' in request.POST:
        master = queryset.get(pk=request.POST.get('master_pk'))
        other = queryset.get(pk=request.POST.get('other_pk'))
        formset = formset_factory(OForm)(initial=[model_to_dict(master), model_to_dict(other)])
        with transaction.nocommit():
            form = MForm(request.POST, instance=master)
            stored_pk = other.pk
            other.delete()
            ok = form.is_valid()
            other.pk = stored_pk
        if ok:
            if form.cleaned_data['dependencies'] == MergeForm.DEP_MOVE:
                related = api.ALL_FIELDS
            else:
                related = None
            fields = form.cleaned_data['field_names']
            api.merge(master, other, fields=fields, commit=True, related=related)
            return HttpResponseRedirect(request.path)
        else:
            messages.error(request, form.errors)
    else:
        try:
            master, other = queryset.all()
            # django 1.4 need to remove the trailing milliseconds
            for field in master._meta.fields:
                if isinstance(field, models.DateTimeField):
                    for target in (master, other):
                        raw_value = getattr(target, field.name)
                        fixed_value = datetime(raw_value.year, raw_value.month, raw_value.day,
                                               raw_value.hour, raw_value.minute, raw_value.second)
                        setattr(target, field.name, fixed_value)
        except ValueError:
            messages.error(request, _('Please select exactly 2 records'))
            return

        initial = {'_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
                   'select_across': 0,
                   'generic': MergeForm.GEN_IGNORE,
                   'dependencies': MergeForm.DEP_MOVE,
                   'action': 'merge',
                   'master_pk': master.pk,
                   'other_pk': other.pk}
        formset = formset_factory(OForm)(initial=[model_to_dict(master), model_to_dict(other)])
        form = MForm(initial=initial, instance=master)

    adminForm = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, [], model_admin=modeladmin)
    media = modeladmin.media + adminForm.media
    ctx.update({'adminform': adminForm,
                'formset': formset,
                'media': mark_safe(media),
                'title': u"Merge %s" % force_unicode(modeladmin.opts.verbose_name_plural),
                'master': master,
                'other': other})
    return render_to_response(tpl, RequestContext(request, ctx))


merge.short_description = _("Merge selected %(verbose_name_plural)s")

########NEW FILE########
__FILENAME__ = models
from django.db.models import signals


def get_permission_codename(action, opts):
    return '%s_%s' % (action, opts.object_name.lower())


def create_extra_permission(sender, **kwargs):
    from django.contrib.auth.models import Permission
    from django.db.models.loading import get_models
    from django.contrib.contenttypes.models import ContentType

    for model in get_models(sender):
        for action in ('adminactions_export', 'adminactions_massupdate', 'adminactions_merge'):
            opts = model._meta
            codename = get_permission_codename(action, opts)
            label = u'Can %s %s (adminactions)' % (action.replace('adminactions_', ""), opts.verbose_name_raw)
            ct = ContentType.objects.get_for_model(model)
            Permission.objects.get_or_create(codename=codename, content_type=ct, defaults={'name': label[:50]})


signals.post_syncdb.connect(create_extra_permission)

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
import django.dispatch


adminaction_requested = django.dispatch.Signal(
    providing_args=["action", "request", "queryset", "modeladmin"])

adminaction_start = django.dispatch.Signal(
    providing_args=["action", "request", "queryset", "modeladmin", "form"])

adminaction_end = django.dispatch.Signal(
    providing_args=["action", "request", "queryset", "modeladmin", "form",
                    "errors", "updated"])

########NEW FILE########
__FILENAME__ = actions
# -*- coding: utf-8 -*-
from django.template import Library
from adminactions.utils import get_field_value, get_verbose_name


register = Library()


@register.filter()
def raw_value(obj, field):
    """
        returns the value  a field

        see `adminactions.utils.get_field_value`_
    """
    value = get_field_value(obj, field, False)
    return str(field.formfield().to_python(value))


@register.filter()
def field_display(obj, field):
    """
        returns the representation (value or ``get_FIELD_display()``) of  a field

        see `adminactions.utils.get_field_value`_
    """
    return get_field_value(obj, field)


@register.filter
def verbose_name(model_or_queryset, field):
    """
        templatetag wrapper to `adminactions.utils.get_verbose_name`_
    """
    return get_verbose_name(model_or_queryset, field)

########NEW FILE########
__FILENAME__ = massupdate
from django.forms import widgets
from django.forms.util import flatatt
from django.template import Library
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from adminactions.mass_update import OPERATIONS


register = Library()


@register.simple_tag
def fields_values(d, k):
    """
    >>> data = {'name1': ['value1.1', 'value1.2'], 'name2': ['value2.1', 'value2.2'], }
    >>> fields_values(data, 'name1')
    value1.1, value1.2
    """
    values = d.get(k, [])
    return ",".join(map(str, values))


@register.simple_tag
def link_fields_values(d, k):
    """
    >>> data = {'name1': ['value1.1', 'value1.2'], 'name2': ['value2.1', 'value2.2'], }
    >>> link_fields_values(data, 'name1')
    u'<a href="#" class="fastfieldvalue name1">value1.1</a>, <a href="#" class="fastfieldvalue name1">value1.2</a>'
    """
    ret = []
    for v in d.get(k, []):
        if v == '':  # ignore empty
            continue
        ret.append('<a href="#" class="fastfieldvalue %s value">%s</a>' % (k, force_unicode(v)))

    return mark_safe(", ".join(ret))


@register.simple_tag(takes_context=True)
def checkbox_enabler(context, field):
    selected = context['selected_fields']
    name = "chk_id_%s" % field.name
    checked = {True: 'checked="checked"', False: ''}[name in selected]
    return mark_safe('<input type="checkbox" name="%s" %s class="enabler">' % (name, checked))


class SelectOptionsAttribute(widgets.Select):
    """
        Select widget with the capability to render option's attributes
    """
    def __init__(self, attrs=None, choices=(), options_attributes=None):
        self.options_attributes = options_attributes or {}
        super(SelectOptionsAttribute, self).__init__(attrs, choices)

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_unicode(option_value)
        attrs = flatatt(self.options_attributes.get(option_value, {}))
        if option_value in selected_choices:
            selected_html = u' selected="selected"'
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return u'<option%s value="%s"%s>%s</option>' % (
            attrs,
            escape(option_value), selected_html,
            conditional_escape(force_unicode(option_label)))


@register.simple_tag
def field_function(model, form_field):
    model_object, model, direct, m2m = model._meta.get_field_by_name(form_field.name)
    attrs = {'class': 'func_select'}
    options_attrs = {}
    choices = []
    classes = {True: 'param', False: 'noparam'}
    for label, (__, param, enabler, __) in OPERATIONS.get_for_field(model_object).items():
        options_attrs[label] = {'class': classes[param], 'label': label}
        choices.append((label, label))
    return SelectOptionsAttribute(attrs, choices, options_attrs).render("func_id_%s" % form_field.name, "")

########NEW FILE########
__FILENAME__ = merge
from django.template import Library


register = Library()


@register.filter(name="widget")
def form_widget(form, fieldname):
    return form[fieldname]


@register.filter(name="errors")
def form_widget_error(form, fieldname):
    return form[fieldname].errors


@register.filter(name="value")
def form_widget_value(form, fieldname):
    return form[fieldname].value()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from adminactions.views import format_date


urlpatterns = patterns('',
                       url(r'^s/format/date/$', format_date, name='adminactions.format_date'))

########NEW FILE########
__FILENAME__ = utils
from django.db import models
from django.db.models.query import QuerySet
from django.db import connections, router


def clone_instance(instance, fieldnames=None):
    """
        returns a copy of the passed instance.

        .. warning: All fields are copied, even primary key

    :param instance: :py:class:`django.db.models.Model` instance
    :return: :py:class:`django.db.models.Model` instance
    """

    if fieldnames is None:
        fieldnames = [fld.name for fld in instance._meta.fields]

    new_kwargs = dict([(name, getattr(instance, name)) for name in fieldnames])
    return instance.__class__(**new_kwargs)


def get_copy_of_instance(instance):
    return instance.__class__.objects.get(pk=instance.pk)


def get_attr(obj, attr, default=None):
    """Recursive get object's attribute. May use dot notation.

    >>> class C(object): pass
    >>> a = C()
    >>> a.b = C()
    >>> a.b.c = 4
    >>> get_attr(a, 'b.c')
    4

    >>> get_attr(a, 'b.c.y', None)

    >>> get_attr(a, 'b.c.y', 1)
    1
    """
    if '.' not in attr:
        ret = getattr(obj, attr, default)
    else:
        L = attr.split('.')
        ret = get_attr(getattr(obj, L[0], default), '.'.join(L[1:]), default)

    if isinstance(ret, BaseException):
        raise ret
    return ret


def getattr_or_item(obj, name):
    try:
        ret = get_attr(obj, name, AttributeError())
    except AttributeError:
        try:
            ret = obj[name]
        except KeyError:
            raise AttributeError("%s object has no attribute/item '%s'" % (obj.__class__.__name__, name))
    return ret


def get_field_value(obj, field, usedisplay=True, raw_callable=False):
    """
    returns the field value or field representation if get_FIELD_display exists

    :param obj: :class:`django.db.models.Model` instance
    :param field: :class:`django.db.models.Field` instance or ``basestring`` fieldname
    :param usedisplay: boolean if True return the get_FIELD_display() result
    :return: field value

    >>> from django.contrib.auth.models import Permission
    >>> p = Permission(name='perm')
    >>> print get_field_value(p, 'name')
    perm

    """
    if isinstance(field, basestring):
        fieldname = field
    elif isinstance(field, models.Field):
        fieldname = field.name
    else:
        raise ValueError('Invalid value for parameter `field`: Should be a field name or a Field instance ')

    if usedisplay and hasattr(obj, 'get_%s_display' % fieldname):
        value = getattr(obj, 'get_%s_display' % fieldname)()
    else:
        value = getattr_or_item(obj, fieldname)

    if not raw_callable and callable(value):
        return value()

    return value


def get_field_by_path(model, field_path):
    """
    get a Model class or instance and a path to a attribute, returns the field object

    :param model: :class:`django.db.models.Model`
    :param field_path: string path to the field
    :return: :class:`django.db.models.Field`


    >>> from django.contrib.auth.models import Permission

    >>> p = Permission(name='perm')
    >>> f = get_field_by_path(Permission, 'content_type')
    >>> print f
    <django.db.models.fields.related.ForeignKey: content_type>

    >>> p = Permission(name='perm')
    >>> f = get_field_by_path(p, 'content_type.app_label')
    >>> print f
    <django.db.models.fields.CharField: app_label>

    """
    parts = field_path.split('.')
    target = parts[0]
    if target in model._meta.get_all_field_names():
        field_object, model, direct, m2m = model._meta.get_field_by_name(target)
        if isinstance(field_object, models.fields.related.ForeignKey):
            if parts[1:]:
                return get_field_by_path(field_object.rel.to, '.'.join(parts[1:]))
            else:
                return field_object
        else:
            return field_object
    return None


def get_verbose_name(model_or_queryset, field):
    """
    returns the value of the ``verbose_name`` of a field

    typically used in the templates where you can have a dynamic queryset

    :param model_or_queryset:  target object
    :type model_or_queryset: :class:`django.db.models.Model`, :class:`django.db.query.Queryset`

    :param field: field to get the verbose name
    :type field: :class:`django.db.models.Field`, basestring

    :return: translated field verbose name
    :rtype: unicode

    Valid uses:

    >>> from django.contrib.auth.models import User, Permission
    >>> user = User()
    >>> p = Permission()
    >>> print unicode(get_verbose_name(user, 'username'))
    username
    >>> print unicode(get_verbose_name(User, 'username'))
    username
    >>> print unicode(get_verbose_name(User.objects.all(), 'username'))
    username
    >>> print unicode(get_verbose_name(User.objects, 'username'))
    username
    >>> print unicode(get_verbose_name(User.objects, user._meta.get_field_by_name('username')[0]))
    username
    >>> print unicode(get_verbose_name(p, 'content_type.model'))
    python model class name
    >>> get_verbose_name(object, 'aaa')
    Traceback (most recent call last):
    ...
    ValueError: `get_verbose_name` expects Manager, Queryset or Model as first parameter (got <type 'type'>)
    """

    if isinstance(model_or_queryset, models.Manager):
        model = model_or_queryset.model
    elif isinstance(model_or_queryset, QuerySet):
        model = model_or_queryset.model
    elif isinstance(model_or_queryset, models.Model):
        model = model_or_queryset
    elif type(model_or_queryset) is models.base.ModelBase:
        model = model_or_queryset
    else:
        raise ValueError('`get_verbose_name` expects Manager, Queryset or Model as first parameter (got %s)' % type(
            model_or_queryset))

    if isinstance(field, basestring):
        field = get_field_by_path(model, field)
    elif isinstance(field, models.Field):
        field = field
    else:
        raise ValueError('`get_verbose_name` field_path must be string or Field class')

    return field.verbose_name


def flatten(iterable):
    """
    flatten(sequence) -> list

    Returns a single, flat list which contains all elements retrieved
    from the sequence and all recursively contained sub-sequences
    (iterables).

    :param sequence: any object that implements iterable protocol (see: :ref:`typeiter`)
    :return: list

    Examples:

    >>> from adminactions.utils import flatten
    >>> [1, 2, [3,4], (5,6)]
    [1, 2, [3, 4], (5, 6)]

    >>> flatten([[[1,2,3], (42,None)], [4,5], [6], 7, (8,9,10)])
    [1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10]"""

    result = list()
    for el in iterable:
        if hasattr(el, "__iter__") and not isinstance(el, basestring):
            result.extend(flatten(el))
        else:
            result.append(el)
    return list(result)


def model_supports_transactions(instance):
    alias = router.db_for_write(instance)
    return connections[alias].features.supports_transactions

########NEW FILE########
__FILENAME__ = views
import datetime
from django.http import HttpResponse
from django.utils import dateformat


def format_date(request):
    d = datetime.datetime.now()
    return HttpResponse(dateformat.format(d, request.GET.get('fmt', '')))

########NEW FILE########
__FILENAME__ = conftest
import os
import sys
from django.conf import settings


def pytest_configure(config):
    here = os.path.dirname(__file__)
    sys.path.insert(0, os.path.join(here, 'demo'))

    if not settings.configured:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

    try:
        from django.apps import AppConfig
        import django

        django.setup()
    except ImportError:
        pass


def runtests(args=None):
    import pytest

    if not args:
        args = []

    if not any(a for a in args[1:] if not a.startswith('-')):
        args.append('adminactions')

    sys.exit(pytest.main(args))


if __name__ == '__main__':
    runtests(sys.argv)

########NEW FILE########
__FILENAME__ = backends
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class AnyUserBackend(ModelBackend):
    supports_object_permissions = False
    supports_anonymous_user = True

    def get_all_permissions(self, user_obj, obj=None):
        if settings.DEBUG:
            return Permission.objects.all().values_list('content_type__app_label', 'codename').order_by()
        return super(AnyUserBackend, self).get_all_permissions(user_obj, obj)

    def get_group_permissions(self, user_obj, obj=None):
        if settings.DEBUG:
            return Permission.objects.all().values_list('content_type__app_label', 'codename').order_by()
        return super(AnyUserBackend, self).get_group_permissions(user_obj, obj)

    def has_perm(self, user_obj, perm, obj=None):
        if settings.DEBUG:
            return True
        return super(AnyUserBackend, self).has_perm(user_obj, perm, obj)

    def has_module_perms(self, user_obj, app_label):
        if settings.DEBUG:
            return True
        return super(AnyUserBackend, self).has_module_perms(user_obj, app_label)

########NEW FILE########
__FILENAME__ = admin
from django.contrib.admin import ModelAdmin, site
from .models import DemoModel, UserDetail


class UserDetailModelAdmin(ModelAdmin):
    list_display = [f.name for f in UserDetail._meta.fields]

class DemoModelAdmin(ModelAdmin):
#    list_display = ('char', 'integer', 'logic', 'null_logic',)
    list_display = [f.name for f in DemoModel._meta.fields]



site.register(DemoModel, DemoModelAdmin)
site.register(UserDetail, UserDetailModelAdmin)

########NEW FILE########
__FILENAME__ = demo_data
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django_dynamic_fixture import G


class Command(BaseCommand):
    args = ''
    help = 'Help text here....'
    """
    option_list = BaseCommand.option_list + (
        make_option('--delete',
            action='store_true',
            dest='delete',
            default=False,
            help='Delete poll instead of closing it'),
        )
    """

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        from demoproject.demoapp.models import DemoModel,  UserDetail, UserProfile

        for x in range(100):
            G(DemoModel)

        for x in range(10):
            G(UserProfile)
            G(UserDetail)

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from django.db import models


class DemoModel(models.Model):
    char = models.CharField(max_length=255)
    integer = models.IntegerField()
    logic = models.BooleanField()
    null_logic = models.NullBooleanField()
    date = models.DateField()
    datetime = models.DateTimeField()
    time = models.TimeField()
    decimal = models.DecimalField(max_digits=10, decimal_places=3)
    email = models.EmailField()
    #    filepath = models.FilePathField(path=__file__)
    float = models.FloatField()
    bigint = models.BigIntegerField()
    ip = models.IPAddressField()
    generic_ip = models.GenericIPAddressField()
    url = models.URLField()
    text = models.TextField()

    unique = models.CharField(max_length=255, unique=True)
    nullable = models.CharField(max_length=255, null=True)
    blank = models.CharField(max_length=255, blank=True, null=True)
    not_editable = models.CharField(max_length=255, editable=False, blank=True, null=True)
    choices = models.IntegerField(choices=((1, 'Choice 1'), (2, 'Choice 2'), (3, 'Choice 3')))

    class Meta:
        app_label = 'demoapp'


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    note = models.CharField(max_length=10, blank=True)

    class Meta:
        app_label = 'demoapp'



class UserDetail(models.Model):
    user = models.ForeignKey(User)
    note = models.CharField(max_length=10, blank=True)

    class Meta:
        app_label = 'demoapp'

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from django.utils.translation import gettext as _

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns


urlpatterns = patterns('',)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

from django.utils.translation import gettext as _
from random import randrange, choice, shuffle
from django_dynamic_fixture.fixture_algorithms.random_fixture import RandomDataFixture


def ipaddress(not_valid=None):
    """
        returns a string representing a random ip address

    :param not_valid: if passed must be a list of integers representing valid class A netoworks that must be ignored
    """
    not_valid_class_A = not_valid or []

    class_a = [r for r in range(1, 256) if r not in not_valid_class_A]
    shuffle(class_a)
    first = class_a.pop()

    return ".".join([str(first), str(randrange(1, 256)),
                     str(randrange(1, 256)), str(randrange(1, 256))])


class DataFixtureClass(RandomDataFixture): # it can inherit of SequentialDataFixture, RandomDataFixture etc.
    def genericipaddressfield_config(self, field, key): # method name must have the format: FIELDNAME_config
        return ipaddress()

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = settings
from tests.settings import *
# ROOT_URLCONF = 'demoproject.urls'
# SECRET_KEY = ';klkj;okj;lkn;lklj;lkj;kjmlliuewhy2ioqwjdkh'
#
# INSTALLED_APPS = ['django.contrib.auth',
#                   'django.contrib.contenttypes',
#                   'django.contrib.sessions',
#                   'django.contrib.sites',
#                   'django.contrib.messages',
#                   'django.contrib.staticfiles',
#                   'django.contrib.admin',
#                   'adminactions',
#                   'demoproject.demoapp',
#                   'webtests']
# AUTHENTICATION_BACKENDS = ('demoproject.backends.AnyUserBackend',)

########NEW FILE########
__FILENAME__ = urls
from tests.urls import *

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for demoproject project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

here = os.path.abspath(os.path.join(os.path.dirname(__file__)))
rel = lambda *args: os.path.join(here, *args)

sys.path.insert(0, rel(os.pardir))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django site maintenance documentation build configuration file, created by
# sphinx-quickstart on Sun Dec  5 19:11:46 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

here = os.path.abspath(os.path.join(os.path.dirname(__file__)))
up = lambda base, level: os.path.abspath(os.path.join(base, *([os.pardir] * level)))
sys.path.insert(0, up(here, 2))

import adminactions as app
from django.conf import settings

settings.configure(SITE_ID=1)


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "_ext")))
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.todo',
              'sphinx.ext.graphviz',
              'sphinx.ext.intersphinx',
              'sphinx.ext.doctest',
              'sphinx.ext.extlinks',
              'sphinx.ext.autosummary',
              'sphinx.ext.coverage',
              'sphinx.ext.viewcode',
              # 'djangodocs',
              'version',
              'github']


#issuetracker = 'github'
#issuetracker_project = 'saxix/django-adminactions'
#issuetracker_plaintext_issues = True
next_version = '0.5'
github_project_url = 'https://github.com/saxix/django-adminactions/'
github_project_url_basesource = 'https://github.com/saxix/django-adminactions/'

todo_include_todos = True
intersphinx_mapping = {
    'python': ('http://python.readthedocs.org/en/latest/', None),
    'django': ('http://django.readthedocs.org/en/1.5.x/', None),
    'sphinx': ('http://sphinx.readthedocs.org/en/latest/', None)}
intersphinx_cache_limit = 90 # days

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Admin Actions'
copyright = u'2012, Stefano Apostolico'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = app.get_version()
# The full version, including alpha/beta/rc tags.
release = app.get_version()

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
import os

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    html_theme = 'default'
else:
    html_theme = 'nature'


# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['.']

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
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# HTML translator class for the builder
# html_translator_class = "version.HTMLTranslator"

# Content template for the index page.
#html_index = ''

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
htmlhelp_basename = 'djangoadminactionsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'DjangoAdminActions.tex', u"Django Admin Actions Documentation",
     u'Stefano Apostolico', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'djangoadminactions', u"Django Admin Actions Documentation",
     [u'Stefano Apostolico'], 1)
]

########NEW FILE########
__FILENAME__ = djangodocs
"""
Sphinx plugins for Django documentation.
"""
import json
import os
import re

from docutils import nodes, transforms

from sphinx import addnodes, roles, __version__ as sphinx_ver
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.writers.html import SmartyPantsHTMLTranslator
from sphinx.util.console import bold
from sphinx.util.compat import Directive

# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(
    r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')

def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = "pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename      = "lookup",
        indextemplate = "pair: %s; field lookup type",
    )
    app.add_description_unit(
        directivename = "django-admin",
        rolename      = "djadmin",
        indextemplate = "pair: %s; django-admin command",
        parse_node    = parse_django_admin_node,
    )
    app.add_description_unit(
        directivename = "django-admin-option",
        rolename      = "djadminopt",
        indextemplate = "pair: %s; django-admin command-line option",
        parse_node    = parse_django_adminopt_node,
    )
    # app.add_config_value('django_next_version', '0.0', True)
    # app.add_directive('versionadded', VersionDirective)
    # app.add_directive('versionchanged', VersionDirective)
    app.add_builder(DjangoStandaloneHTMLBuilder)


class VersionDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        env = self.state.document.settings.env
        ret = []
        node = addnodes.versionmodified()
        ret.append(node)
        if self.arguments[0] == env.config.django_next_version:
            node['version'] = "Development version"
        else:
            node['version'] = self.arguments[0]
        node['type'] = self.name
        if len(self.arguments) == 2:
            inodes, messages = self.state.inline_text(self.arguments[1], self.lineno+1)
            node.extend(inodes)
            if self.content:
                self.state.nested_parse(self.content, self.content_offset, node)
            ret = ret + messages
        env.note_versionchange(node['type'], node['version'], node, self.lineno)
        return ret


class DjangoHTMLTranslator(SmartyPantsHTMLTranslator):
    """
    Django-specific reST to HTML tweaks.
    """

    # Don't use border=1, which docutils does by default.
    def visit_table(self, node):
        self._table_row_index = 0 # Needed by Sphinx
        self.body.append(self.starttag(node, 'table', CLASS='docutils'))

    # <big>? Really?
    def visit_desc_parameterlist(self, node):
        self.body.append('(')
        self.first_param = 1
        self.param_separator = node.child_text_separator

    def depart_desc_parameterlist(self, node):
        self.body.append(')')

    if sphinx_ver < '1.0.8':
        #
        # Don't apply smartypants to literal blocks
        #
        def visit_literal_block(self, node):
            self.no_smarty += 1
            SmartyPantsHTMLTranslator.visit_literal_block(self, node)

        def depart_literal_block(self, node):
            SmartyPantsHTMLTranslator.depart_literal_block(self, node)
            self.no_smarty -= 1

    #
    # Turn the "new in version" stuff (versionadded/versionchanged) into a
    # better callout -- the Sphinx default is just a little span,
    # which is a bit less obvious that I'd like.
    #
    # FIXME: these messages are all hardcoded in English. We need to change
    # that to accomodate other language docs, but I can't work out how to make
    # that work.
    #
    version_text = {
        'deprecated':       'Deprecated in Django %s',
        'versionchanged':   'Changed in Django %s',
        'versionadded':     'New in Django %s',
    }

    def visit_versionmodified(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS=node['type'])
        )
        title = "%s%s" % (
            self.version_text[node['type']] % node['version'],
            len(node) and ":" or "."
        )
        self.body.append('<span class="title">%s</span> ' % title)

    def depart_versionmodified(self, node):
        self.body.append("</div>\n")

    # Give each section a unique ID -- nice for custom CSS hooks
    def visit_section(self, node):
        old_ids = node.get('ids', [])
        node['ids'] = ['s-' + i for i in old_ids]
        node['ids'].extend(old_ids)
        SmartyPantsHTMLTranslator.visit_section(self, node)
        node['ids'] = old_ids

def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env._django_curr_admin_command = command
    title = "django-admin.py %s" % sig
    signode += addnodes.desc_name(title, title)
    return sig

def parse_django_adminopt_node(env, sig, signode):
    """A copy of sphinx.directives.CmdoptionDesc.parse_signature()"""
    from sphinx.domains.std import option_desc_re
    count = 0
    firstname = ''
    for m in option_desc_re.finditer(sig):
        optname, args = m.groups()
        if count:
            signode += addnodes.desc_addname(', ', ', ')
        signode += addnodes.desc_name(optname, optname)
        signode += addnodes.desc_addname(args, args)
        if not count:
            firstname = optname
        count += 1
    if not count:
        for m in simple_option_desc_re.finditer(sig):
            optname, args = m.groups()
            if count:
                signode += addnodes.desc_addname(', ', ', ')
            signode += addnodes.desc_name(optname, optname)
            signode += addnodes.desc_addname(args, args)
            if not count:
                firstname = optname
            count += 1
    if not firstname:
        raise ValueError
    return firstname


class DjangoStandaloneHTMLBuilder(StandaloneHTMLBuilder):
    """
    Subclass to add some extra things we need.
    """

    name = 'djangohtml'

    def finish(self):
        super(DjangoStandaloneHTMLBuilder, self).finish()
        self.info(bold("writing templatebuiltins.js..."))
        xrefs = self.env.domaindata["std"]["objects"]
        templatebuiltins = {
            "ttags": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatetag" and l == "ref/templates/builtins"],
            "tfilters": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatefilter" and l == "ref/templates/builtins"],
        }
        outfilename = os.path.join(self.outdir, "templatebuiltins.js")
        with open(outfilename, 'wb') as fp:
            fp.write('var django_template_builtins = ')
            json.dump(templatebuiltins, fp)
            fp.write(';\n')

########NEW FILE########
__FILENAME__ = github
"""Define text roles for GitHub

* ghissue - Issue
* ghpull - Pull Request
* ghuser - User

Adapted from bitbucket example here:
https://bitbucket.org/birkenfeld/sphinx-contrib/src/tip/bitbucket/sphinxcontrib/bitbucket.py

Authors
-------

* Doug Hellmann
* Min RK
"""
#
# Original Copyright (c) 2010 Doug Hellmann.  All rights reserved.
#

from docutils import nodes, utils
from docutils.parsers.rst.roles import set_classes


def make_link_node(rawtext, app, type, slug, options):
    """Create a link to a github resource.

    :param rawtext: Text being replaced with link node.
    :param app: Sphinx application context
    :param type: Link type (issues, changeset, etc.)
    :param slug: ID of the thing to link to
    :param options: Options dictionary passed to role func.
    """

    try:
        base = app.config.github_project_url
        if not base:
            raise AttributeError
        if not base.endswith('/'):
            base += '/'
    except AttributeError as err:
        raise ValueError('github_project_url configuration value is not set (%s)' % str(err))

    ref = base + type + '/' + slug + '/'
    set_classes(options)
    prefix = "#"
    if type == 'pull':
        prefix = "PR " + prefix
    node = nodes.reference(rawtext, prefix + utils.unescape(slug), refuri=ref,
                           **options)
    return node


def ghissue_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Link to a GitHub issue.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """

    try:
        issue_num = int(text)
        if issue_num <= 0:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'GitHub issue number must be a number greater than or equal to 1; '
            '"%s" is invalid.' % text, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    app = inliner.document.settings.env.app
    #app.info('issue %r' % text)
    if 'pull' in name.lower():
        category = 'pull'
    elif 'issue' in name.lower():
        category = 'issues'
    else:
        msg = inliner.reporter.error(
            'GitHub roles include "ghpull" and "ghissue", '
            '"%s" is invalid.' % name, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    node = make_link_node(rawtext, app, category, str(issue_num), options)
    return [node], []


def ghuser_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Link to a GitHub user.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """
    # app = inliner.document.settings.env.app
    #app.info('user link %r' % text)
    ref = 'https://www.github.com/' + text
    node = nodes.reference(rawtext, text, refuri=ref, **options)
    return [node], []


def ghcommit_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Link to a GitHub commit.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """
    app = inliner.document.settings.env.app
    #app.info('user link %r' % text)
    try:
        base = app.config.github_project_url
        if not base:
            raise AttributeError
        if not base.endswith('/'):
            base += '/'
    except AttributeError as err:
        raise ValueError('github_project_url configuration value is not set (%s)' % str(err))

    ref = base + text
    node = nodes.reference(rawtext, text[:6], refuri=ref, **options)
    return [node], []


def setup(app):
    """Install the plugin.

    :param app: Sphinx application context.
    """
    app.info('Initializing GitHub plugin')
    app.add_role('ghissue', ghissue_role)
    app.add_role('ghpull', ghissue_role)
    app.add_role('ghuser', ghuser_role)
    app.add_role('ghcommit', ghcommit_role)
    app.add_config_value('github_project_url', None, 'env')
    return

########NEW FILE########
__FILENAME__ = version
import re
from sphinx import addnodes, roles
from sphinx.util.compat import Directive
from sphinx.writers.html import SmartyPantsHTMLTranslator

simple_option_desc_re = re.compile(
    r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')


def setup(app):
    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )
    app.add_crossref_type(
        directivename="templatetag",
        rolename="ttag",
        indextemplate="pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename="templatefilter",
        rolename="tfilter",
        indextemplate="pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename="fieldlookup",
        rolename="lookup",
        indextemplate="pair: %s; field lookup type",
    )
    app.add_config_value('next_version', '0.0', True)
    app.add_directive('versionadded', VersionDirective)
    app.add_directive('versionchanged', VersionDirective)
    app.add_crossref_type(
        directivename="release",
        rolename="release",
        indextemplate="pair: %s; release",
    )

class VersionDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}
    version_text = {
        'deprecated':       'Deprecated in %s.',
        'versionchanged':   'Changed in %s.',
        'versionadded':     'New in %s.',
    }

    def run(self):
        env = self.state.document.settings.env
        arg0 = self.arguments[0]
        ret = []
        node = addnodes.versionmodified()
        ret.append(node)

        node['type'] = self.name
        if env.config.next_version == arg0:
            version = "Development version"
            link = None
        else:
            version = arg0
            link = 'release-%s' % arg0

        node['version'] = version
        # inodes, messages = self.state.inline_text(self.version_text[self.name] % version, self.lineno+1)
        # node.extend(inodes)
        if link:
            text = ' Please see the changelog <%s>' % link
            xrefs = roles.XRefRole()('std:ref', text, text, self.lineno, self.state)
            node.extend(xrefs[0])
        env.note_versionchange(node['type'], node['version'], node, self.lineno)
        return ret


########NEW FILE########
__FILENAME__ = common
import os
from django.conf import global_settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from django.test.testcases import TestCase

TEST_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), os.pardir, 'tests', 'templates')
SETTINGS = {'MIDDLEWARE_CLASSES': global_settings.MIDDLEWARE_CLASSES,
            'TEMPLATE_DIRS': [TEST_TEMPLATES_DIR],
            'AUTHENTICATION_BACKENDS': ('django.contrib.auth.backends.ModelBackend',),
            'TEMPLATE_LOADERS': ('django.template.loaders.filesystem.Loader',
                                 'django.template.loaders.app_directories.Loader'),
            # 'AUTH_PROFILE_MODULE': None,
            'TEMPLATE_CONTEXT_PROCESSORS': ("django.contrib.auth.context_processors.auth",
                                            "django.core.context_processors.debug",
                                            "django.core.context_processors.i18n",
                                            "django.core.context_processors.media",
                                            "django.core.context_processors.static",
                                            "django.core.context_processors.request",
                                            "django.core.context_processors.tz",
                                            "django.contrib.messages.context_processors.messages")}


class BaseTestCaseMixin(object):
    fixtures = ['adminactions.json', ]

    def setUp(self):
        super(BaseTestCaseMixin, self).setUp()
        self.sett = self.settings(**SETTINGS)
        self.sett.enable()
        self.login()

    def tearDown(self):
        self.sett.disable()

    def login(self, username='user_00', password='123'):
        logged = self.client.login(username=username, password=password)
        assert logged, 'Unable login with credentials'
        self._user = authenticate(username=username, password=password)

    def add_permission(self, *perms, **kwargs):
        """ add the right permission to the user """
        target = kwargs.pop('user', self._user)
        if hasattr(target, '_perm_cache'):
            del target._perm_cache
        for perm_name in perms:
            app_label, code = perm_name.split('.')
            if code == '*':
                perms = Permission.objects.filter(content_type__app_label=app_label)
            else:
                perms = Permission.objects.filter(codename=code, content_type__app_label=app_label)
            target.user_permissions.add(*perms)

        target.save()


class BaseTestCase(BaseTestCaseMixin, TestCase):
    pass

########NEW FILE########
__FILENAME__ = test_massupdate
import os.path
from casper.tests import CasperTestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client
from django_dynamic_fixture import G
from django_webtest import WebTestMixin

list_to_string = lambda q: ','.join(map(str, q))


class MassUpdateTest(WebTestMixin, CasperTestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser('sax', '', '123')
        self.client.login(username=self.user.username, password='123')
        G(User, n=5)

    def test_success(self):
        new_first_name = '**FIRST_NAME**'
        new_last_name = '**LAST_NAME**'

        selection = User.objects.filter(is_superuser=False)
        ids = list_to_string(selection.values_list('pk', flat=True))

        url = reverse('admin:auth_user_changelist')
        test_file = os.path.join(os.path.dirname(__file__), 'casper-tests/massupdate_success.js')
        self.assertTrue(self.casper(test_file,
                                    url=url,
                                    first_name=new_first_name,
                                    last_name=new_last_name,
                                    ids=ids,
                                    engine='phantomjs'))

        result = User.objects.filter(last_name=new_last_name,
                                     first_name=new_first_name)

        self.assertEquals(result.count(), selection.count())

    def test_check_clean(self):
        new_first_name = '**FIRST_NAME**'
        new_last_name = '**LAST_NAME**'

        selection = User.objects.filter(is_superuser=False)
        ids = list_to_string(selection.values_list('pk', flat=True))

        url = reverse('admin:auth_user_changelist')
        test_file = os.path.join(os.path.dirname(__file__), 'casper-tests/massupdate_clean.js')
        self.assertTrue(self.casper(test_file,
                                    url=url,
                                    first_name=new_first_name,
                                    last_name=new_last_name,
                                    ids=ids,
                                    engine='phantomjs'))

        result = User.objects.filter(last_name=new_last_name,
                                     first_name=new_first_name)

        self.assertEquals(result.count(), selection.count())

########NEW FILE########
__FILENAME__ = test_merge
import os.path
from functools import partial
from casper.tests import CasperTestCase
import django
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client
from django_dynamic_fixture import G
from sample_data_utils.utils import sequence
from django_webtest import WebTestMixin
import pytest

list_to_string = lambda q: ','.join(map(str, q))

xfail14 = pytest.mark.skipif(django.VERSION[0:2] == [1, 4],
                          reason="fail on django==1.4")


@pytest.mark.functional
class MergeTest(WebTestMixin, CasperTestCase):
    def setUp(self):
        names = partial(sequence, 'username', cache={})()
        first_names = partial(sequence, 'First', cache={})()
        last_names = partial(sequence, 'Last', cache={})()

        self.client = Client()
        self.user = User.objects.create_superuser('sax', '', '123')
        self.client.login(username=self.user.username, password='123')
        G(User, n=5, username=lambda x: next(names),
          first_name=lambda x: next(first_names),
          last_name=lambda x: next(last_names))

    @xfail14
    def test_success(self):
        master = User.objects.get(username='username-0')
        other = User.objects.get(username='username-1')
        ids = list_to_string([master.pk, other.pk])

        url = reverse('admin:auth_user_changelist')
        test_file = os.path.join(os.path.dirname(__file__), 'casper-tests/merge.js')
        assert os.path.exists(test_file)
        self.assertTrue(self.casper(test_file,
                                    url=url,
                                    ids=ids,
                                    master_id=master.pk,
                                    other_id=other.pk,
                                    engine='phantomjs'))

        result = User.objects.get(id=master.pk)
        assert result.username == master.username
        assert result.last_name == other.last_name
        assert result.first_name == other.first_name
        assert not User.objects.filter(pk=other.pk).exists()


    def test_swap(self):
        master = User.objects.get(username='username-0')
        other = User.objects.get(username='username-1')
        ids = list_to_string([master.pk, other.pk])

        url = reverse('admin:auth_user_changelist')
        test_file = os.path.join(os.path.dirname(__file__), 'casper-tests/merge_swap.js')
        self.assertTrue(self.casper(test_file,
                                    url=url,
                                    ids=ids,
                                    master_id=master.pk,
                                    other_id=other.pk,
                                    engine='phantomjs'))

        result = User.objects.get(id=other.pk)
        assert result.username == other.username
        assert result.last_name == master.last_name
        assert result.first_name == master.first_name
        assert not User.objects.filter(pk=master.pk).exists()

########NEW FILE########
__FILENAME__ = settings
# Django settings for demoproject project.
import os
import sys

here = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(here, os.pardir)))
sys.path.append(os.path.abspath(os.path.join(here, os.pardir, 'demo')))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

db = os.environ.get('DBENGINE', None)
if db == 'pg':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'adminactions',
            'HOST': '127.0.0.1',
            'PORT': '',
            'USER': 'postgres',
            'PASSWORD': ''}}
elif db == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'adminactions',
            'HOST': '127.0.0.1',
            'PORT': '',
            'USER': 'root',
            'PASSWORD': '',
            'CHARSET': 'utf8',
            'COLLATION': 'utf8_general_ci',
            'TEST_CHARSET': 'utf8',
            'TEST_COLLATION': 'utf8_general_ci'}}
elif db == 'myisam':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'adminactions',
            'HOST': '127.0.0.1',
            'PORT': '',
            'USER': 'root',
            'PASSWORD': '',
            'CHARSET': 'utf8',
            'OPTIONS': {'init_command': 'SET storage_engine=MyISAM', },
            'COLLATION': 'utf8_general_ci',
            'TEST_CHARSET': 'utf8',
            'TEST_COLLATION': 'utf8_general_ci'}}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'adminactions.sqlite',
            'TEST_NAME': 'test_adminactions.sqlite',
            'HOST': '',
            'PORT': ''}}

TIME_ZONE = 'Asia/Bangkok'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
MEDIA_ROOT = os.path.join(here, 'media')
MEDIA_URL = ''
STATIC_ROOT =  os.path.join(here, 'static')
STATIC_URL = '/static/'
SECRET_KEY = 'c73*n!y=)tziu^2)y*@5i2^)$8z$tx#b9*_r3i6o1ohxo%*2^a'
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',)

ROOT_URLCONF = 'tests.urls'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'adminactions',
    'demoproject.demoapp',  # for demo fixtures
    'tests']

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

DDF_DEFAULT_DATA_FIXTURE = 'demoproject.demoapp.util.DataFixtureClass'
WSGI_APPLICATION = 'demoproject.wsgi.application'

########NEW FILE########
__FILENAME__ = test_api
# -*- encoding: utf-8 -*-
from django.http import HttpResponse
import unicodecsv as csv
import unittest
import xlrd
from django.contrib.auth.models import Permission
from django.test import TestCase
from adminactions.api import export_as_csv, export_as_xls
import StringIO
from collections import namedtuple


class TestExportQuerySetAsCsv(TestCase):
    def test_default_params(self):
        with self.assertNumQueries(1):
            qs = Permission.objects.select_related().filter(codename='add_user')
            ret = export_as_csv(queryset=qs)
        self.assertIsInstance(ret, HttpResponse)
        self.assertEquals(ret.content.decode('utf8'), u'"%s";"Can add user";"user";"add_user"\r\n' % qs[0].pk)

    def test_header_is_true(self):
        mem = StringIO.StringIO()
        with self.assertNumQueries(1):
            qs = Permission.objects.select_related().filter(codename='add_user')
            export_as_csv(queryset=qs, header=True, out=mem)
        mem.seek(0)
        csv_reader = csv.reader(mem)
        self.assertEqual(csv_reader.next(), [u'id;"name";"content_type";"codename"'])

    def test_queryset_values(self):
        fields = ['codename', 'content_type__app_label']
        header = ['Name', 'Application']
        mem = StringIO.StringIO()
        with self.assertNumQueries(1):
            qs = Permission.objects.filter(codename='add_user').values('codename', 'content_type__app_label')
            export_as_csv(queryset=qs, fields=fields, header=header, out=mem)
        mem.seek(0)
        csv_dump = mem.read()
        self.assertEquals(csv_dump.decode('utf8'), u'"Name";"Application"\r\n"add_user";"auth"\r\n')

    def test_callable_method(self):
        fields = ['codename', 'natural_key']
        mem = StringIO.StringIO()
        with self.assertNumQueries(2):
            qs = Permission.objects.filter(codename='add_user')
            export_as_csv(queryset=qs, fields=fields, out=mem)
        mem.seek(0)
        csv_dump = mem.read()
        self.assertEquals(csv_dump.decode('utf8'), u'"add_user";"(u\'add_user\', u\'auth\', u\'user\')"\r\n')

    def test_deep_attr(self):
        fields = ['codename', 'content_type.app_label']
        mem = StringIO.StringIO()
        with self.assertNumQueries(1):
            qs = Permission.objects.select_related().filter(codename='add_user')
            export_as_csv(queryset=qs, fields=fields, out=mem)
        mem.seek(0)
        csv_dump = mem.read()
        self.assertEquals(csv_dump.decode('utf8'), u'"add_user";"auth"\r\n')


class TestExportAsCsv(unittest.TestCase):
    def test_export_as_csv(self):
        fields = ['field1', 'field2']
        header = ['Field 1', 'Field 2']
        Row = namedtuple('Row', fields)
        rows = [Row(1, 4),
                Row(2, 5),
                Row(3, u'ӼӳӬԖԊ')]
        mem = StringIO.StringIO()
        export_as_csv(queryset=rows, fields=fields, header=header, out=mem)
        mem.seek(0)
        csv_dump = mem.read()
        self.assertEquals(csv_dump.decode('utf8'), u'"Field 1";"Field 2"\r\n"1";"4"\r\n"2";"5"\r\n"3";"ӼӳӬԖԊ"\r\n')


class TestExportAsExcel(TestCase):
    def test_default_params(self):
        with self.assertNumQueries(1):
            qs = Permission.objects.select_related().filter(codename='add_user')
            ret = export_as_xls(queryset=qs)
        self.assertIsInstance(ret, HttpResponse)

    def test_header_is_true(self):
        mem = StringIO.StringIO()
        with self.assertNumQueries(1):
            qs = Permission.objects.select_related().filter(codename='add_user')
            export_as_xls(queryset=qs, header=True, out=mem)
        mem.seek(0)
        xls_workbook = xlrd.open_workbook(file_contents=mem.read())
        xls_sheet = xls_workbook.sheet_by_index(0)
        self.assertEqual(xls_sheet.row_values(0)[:], [u'#', u'ID', u'name', u'content type', u'codename'])

    def test_export_as_xls(self):
        fields = ['field1', 'field2']
        header = ['Field 1', 'Field 2']
        Row = namedtuple('Row', fields)
        rows = [Row(111, 222),
                Row(333, 444),
                Row(555, u'ӼӳӬԖԊ')]
        mem = StringIO.StringIO()
        export_as_xls(queryset=rows, fields=fields, header=header, out=mem)
        mem.seek(0)
        xls_workbook = xlrd.open_workbook(file_contents=mem.read())
        xls_sheet = xls_workbook.sheet_by_index(0)
        self.assertEqual(xls_sheet.row_values(0)[:], ['#', 'Field 1', 'Field 2'])
        self.assertEqual(xls_sheet.row_values(1)[:], [1.0, 111.0, 222.0])
        self.assertEqual(xls_sheet.row_values(2)[:], [2.0, 333.0, 444.0])
        self.assertEqual(xls_sheet.row_values(3)[:], [3.0, 555.0, u'ӼӳӬԖԊ'])


class TestExportQuerySetAsExcel(TestCase):
    def test_queryset_values(self):
        fields = ['codename', 'content_type__app_label']
        header = ['Name', 'Application']
        qs = Permission.objects.filter(codename='add_user').values('codename', 'content_type__app_label')
        mem = StringIO.StringIO()
        export_as_xls(queryset=qs, fields=fields, header=header, out=mem)
        mem.seek(0)
        w = xlrd.open_workbook(file_contents=mem.read())
        sheet = w.sheet_by_index(0)
        self.assertEquals(sheet.cell_value(1, 1), u'add_user')
        self.assertEquals(sheet.cell_value(1, 2), u'auth')

    def test_callable_method(self):
        fields = ['codename', 'natural_key']
        qs = Permission.objects.filter(codename='add_user')
        mem = StringIO.StringIO()
        export_as_xls(queryset=qs, fields=fields, out=mem)
        mem.seek(0)
        w = xlrd.open_workbook(file_contents=mem.read())
        sheet = w.sheet_by_index(0)
        self.assertEquals(sheet.cell_value(1, 1), u'add_user')
        self.assertEquals(sheet.cell_value(1, 2), u'add_userauthuser')

########NEW FILE########
__FILENAME__ = test_exports
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import StringIO
import xlrd
import csv
import mock
from django_webtest import WebTest
from django_dynamic_fixture import G
from django.contrib.auth.models import User
from .utils import user_grant_permission, admin_register, CheckSignalsMixin, SelectRowsMixin

__all__ = ['ExportAsCsvTest', 'ExportAsFixtureTest', 'ExportAsCsvTest', 'ExportDeleteTreeTest',
           'ExportAsXlsTest']


class ExportMixin(object):
    fixtures = ['adminactions', 'demoproject']
    urls = 'demoproject.urls'

    def setUp(self):
        super(ExportMixin, self).setUp()
        self.user = G(User, username='user', is_staff=True, is_active=True)


class ExportAsFixtureTest(ExportMixin, SelectRowsMixin, CheckSignalsMixin, WebTest):
    sender_model = User
    action_name = 'export_as_fixture'
    _selected_rows = [0, 1, 2]

    def test_no_permission(self):
        with user_grant_permission(self.user, ['auth.change_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = self.action_name
            form.set('_selected_action', True, 0)
            res = form.submit().follow()
            assert 'Sorry you do not have rights to execute this action' in res.body

    def test_success(self):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = self.action_name
            form.set('_selected_action', True, 0)
            form.set('_selected_action', True, 1)
            res = form.submit()
            res.form['use_natural_key'] = True
            res = res.form.submit('apply')
            assert res.json[0]['pk'] == 1

    def test_add_foreign_keys(self):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = self.action_name
            form.set('_selected_action', True, 0)
            form.set('_selected_action', True, 1)
            res = form.submit()
            res.form['use_natural_key'] = True
            res.form['add_foreign_keys'] = True
            res = res.form.submit('apply')
            assert res.json[0]['pk'] == 1

    def _run_action(self, steps=2):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            if steps >= 1:
                form = res.forms['changelist-form']
                form['action'] = self.action_name
                self._select_rows(form)
                res = form.submit()
            if steps >= 2:
                res = res.form.submit('apply')
        return res


class ExportDeleteTreeTest(ExportMixin, SelectRowsMixin, CheckSignalsMixin, WebTest):
    sender_model = User
    action_name = 'export_delete_tree'
    _selected_rows = [0, 1, 2]

    def test_no_permission(self):
        with user_grant_permission(self.user, ['auth.change_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = self.action_name
            form.set('_selected_action', True, 0)
            res = form.submit().follow()
            assert 'Sorry you do not have rights to execute this action' in res.body

    def test_success(self):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = self.action_name
            self._select_rows(form, [0, 1])
            res = form.submit()
            res.form['use_natural_key'] = True
            res = res.form.submit('apply')
            assert res.json[0]['pk'] == 1

    def _run_action(self, steps=2):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            if steps >= 1:
                form = res.forms['changelist-form']
                form['action'] = self.action_name
                self._select_rows(form)
                res = form.submit()
            if steps >= 2:
                res = res.form.submit('apply')
        return res

    def test_custom_filename(self):
        """
            if the ModelAdmin has `get_export_as_csv_filename()` use that method to get the
            attachment filename
        """
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            with admin_register(User) as md:
                with mock.patch.object(md, 'get_export_delete_tree_filename', lambda r, q: 'new.test', create=True):
                    res = res.click('Users')
                    form = res.forms['changelist-form']
                    form['action'] = self.action_name
                    form.set('_selected_action', True, 0)
                    form['select_across'] = 1
                    res = form.submit()
                    res = res.form.submit('apply')
                    self.assertEqual(res.content_disposition, u'attachment;filename="new.test"')


class ExportAsCsvTest(ExportMixin, SelectRowsMixin, CheckSignalsMixin, WebTest):
    sender_model = User
    action_name = 'export_as_csv'
    _selected_rows = [0, 1]

    def test_no_permission(self):
        with user_grant_permission(self.user, ['auth.change_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'export_as_csv'
            form.set('_selected_action', True, 0)
            res = form.submit().follow()
            assert 'Sorry you do not have rights to execute this action' in res.body

    def test_success(self):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = self.action_name
            #form.set('_selected_action', True, 1)
            self._select_rows(form)
            res = form.submit()
            res = res.form.submit('apply')
            io = StringIO.StringIO(res.body)
            csv_reader = csv.reader(io)
            rows = 0
            for c in csv_reader:
                rows += 1
            self.assertEqual(rows, 2)

    def test_custom_filename(self):
        """
            if the ModelAdmin has `get_export_as_csv_filename()` use that method to get the
            attachment filename
        """
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            with admin_register(User) as md:
                with mock.patch.object(md, 'get_export_as_csv_filename', lambda r, q: 'new.test', create=True):
                    res = res.click('Users')
                    form = res.forms['changelist-form']
                    form['action'] = 'export_as_csv'
                    form.set('_selected_action', True, 0)
                    form['select_across'] = 1
                    res = form.submit()
                    res = res.form.submit('apply')
                    self.assertEqual(res.content_disposition, u'attachment;filename="new.test"')

    def _run_action(self, steps=2):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            if steps >= 1:
                form = res.forms['changelist-form']
                form['action'] = self.action_name
                self._select_rows(form)
                res = form.submit()
            if steps >= 2:
                res = res.form.submit('apply')
        return res


class ExportAsXlsTest(ExportMixin, SelectRowsMixin, CheckSignalsMixin, WebTest):
    sender_model = User
    action_name = 'export_as_xls'
    _selected_rows = [0, 1]

    def _run_action(self, step=3):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            if step >= 1:
                form = res.forms['changelist-form']
                form['action'] = self.action_name
                self._select_rows(form)
                res = form.submit()
            if step >= 2:
                res.form['header'] = 1
                res = res.form.submit('apply')
            return res

    def test_no_permission(self):
        with user_grant_permission(self.user, ['auth.change_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'export_as_xls'
            form.set('_selected_action', True, 0)
            res = form.submit().follow()
            assert 'Sorry you do not have rights to execute this action' in res.body

    def test_success(self):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_export_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = self.action_name
            #form.set('_selected_action', True, 0)
            #form.set('_selected_action', True, 1)
            #form.set('_selected_action', True, 2)
            self._select_rows(form)
            res = form.submit()
            res.form['header'] = 1
            res.form['columns'] = ['id', 'username', 'first_name'
                                                     '']
            res = res.form.submit('apply')
            io = StringIO.StringIO(res.body)

            io.seek(0)
            w = xlrd.open_workbook(file_contents=io.read())
            sheet = w.sheet_by_index(0)
            self.assertEquals(sheet.cell_value(0, 0), u'#')
            self.assertEquals(sheet.cell_value(0, 1), u'ID')
            self.assertEquals(sheet.cell_value(0, 2), u'username')
            self.assertEquals(sheet.cell_value(0, 3), u'first name')
            self.assertEquals(sheet.cell_value(1, 1), 1.0)
            self.assertEquals(sheet.cell_value(1, 2), u'sax')
            self.assertEquals(sheet.cell_value(2, 2), u'user')
            #self.assertEquals(sheet.cell_value(3, 2), u'user_00')

########NEW FILE########
__FILENAME__ = test_graph
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django_dynamic_fixture import G
from django_webtest import WebTest
from .utils import CheckSignalsMixin, user_grant_permission, SelectRowsMixin


class TestGraph(SelectRowsMixin, CheckSignalsMixin, WebTest):
    fixtures = ['adminactions', 'demoproject']
    urls = 'demoproject.urls'
    sender_model = User
    action_name = 'graph_queryset'
    _selected_rows = [0, 1]

    def setUp(self):
        super(TestGraph, self).setUp()
        self.user = G(User, username='user', is_staff=True, is_active=True)

    def _run_action(self, steps=2):
        with user_grant_permission(self.user, ['auth.change_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            if steps >= 1:
                form = res.forms['changelist-form']
                form['action'] = 'graph_queryset'
                self._select_rows(form)
                #form.set('_selected_action', True, 0)
                #form.set('_selected_action', True, 1)
                res = form.submit()
            if steps >= 2:
                res.form['axes_x'] = 'username'
                res = res.form.submit('apply')

            return res

    def test_graph_apply(self):
        url = reverse('admin:auth_user_changelist')
        res = self.app.get(url, user='sax')
        form = res.forms['changelist-form']
        form['action'] = 'graph_queryset'
        for i in range(0, 11):
            form.set('_selected_action', True, i)
        res = form.submit()
        res.form['graph_type'] = 'PieChart'
        res.form['axes_x'] = 'is_staff'
        res = res.form.submit('apply')

    def test_graph_post(self):
        url = reverse('admin:auth_user_changelist')
        res = self.app.get(url, user='sax')
        form = res.forms['changelist-form']
        form['action'] = 'graph_queryset'
        for i in range(0, 11):
            form.set('_selected_action', True, i)
        res = form.submit()
        res.form['graph_type'] = 'PieChart'
        res.form['axes_x'] = 'is_staff'
        res = res.form.submit()

########NEW FILE########
__FILENAME__ = test_mass_update
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django_dynamic_fixture import G
from django_webtest import WebTestMixin
from django.test import TransactionTestCase
from .utils import CheckSignalsMixin, user_grant_permission, SelectRowsMixin


__all__ = ['MassUpdateTest', ]


class MassUpdateTest(SelectRowsMixin, CheckSignalsMixin, WebTestMixin, TransactionTestCase):
    fixtures = ['adminactions', 'demoproject']
    urls = 'demoproject.urls'

    _selected_rows = [1, 2, 3, 4]

    action_name = 'mass_update'
    sender_model = User

    def setUp(self):
        super(MassUpdateTest, self).setUp()
        self._url = reverse('admin:auth_user_changelist')
        self.user = G(User, username='user', is_staff=True, is_active=True)

    def _run_action(self, steps=2, **kwargs):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_massupdate_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            if steps >= 1:
                form = res.forms['changelist-form']
                form['action'] = 'mass_update'
                self._select_rows(form)
                res = form.submit()
            if steps >= 2:
                for k, v in kwargs.items():
                    res.form[k] = v
                res.form['chk_id_username'].checked = True
                res.form['chk_id_last_name'].checked = True
                res.form['func_id_username'] = 'upper'
                res.form['func_id_last_name'] = 'set'
                res.form['last_name'] = 'LASTNAME'
                res = res.form.submit('apply')
        return res

    def test_no_permission(self):
        with user_grant_permission(self.user, ['auth.change_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'mass_update'
            form.set('_selected_action', True, 0)
            res = form.submit().follow()
            assert 'Sorry you do not have rights to execute this action' in res.body

    def test_validate_on(self):
        self._run_action(**{'_validate': 1})
        assert User.objects.filter(username='USER').exists()
        assert not User.objects.filter(username='user').exists()
        assert User.objects.filter(last_name='LASTNAME').count() == len(self._selected_rows)

    def test_validate_off(self):
        self._run_action(**{'_validate': 0})
        self.assertIn("Unable no mass update using operators without", self.app.cookies['messages'])
        #assert "Unable no mass update using operators without" in res.body

    def test_clean_on(self):
        self._run_action(**{'_clean': 1})
        assert User.objects.filter(username='USER').exists()
        assert not User.objects.filter(username='user').exists()
        assert User.objects.filter(last_name='LASTNAME').count() == len(self._selected_rows)

    def test_unique_transaction(self):
        self._run_action(**{'_unique_transaction': 1})
        assert User.objects.filter(username='USER').exists()
        assert not User.objects.filter(username='user').exists()
        assert User.objects.filter(last_name='LASTNAME').count() == len(self._selected_rows)

########NEW FILE########
__FILENAME__ = test_merge
# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User, Group, Permission
from django.core.urlresolvers import reverse
from django.test import TransactionTestCase
from django_dynamic_fixture import G
from django_webtest import WebTestMixin
from adminactions.api import merge, ALL_FIELDS


from .common import BaseTestCaseMixin
from .utils import SelectRowsMixin
from .utils import user_grant_permission

PROFILE_MODULE = getattr(settings, 'AUTH_PROFILE_MODULE', 'demoapp.UserProfile')

def assert_profile(user):
    p = None
    try:
        get_profile(user)
    except ObjectDoesNotExist:
        app_label, model_name = PROFILE_MODULE.split('.')
        model = models.get_model(app_label, model_name)
        p, __ = model.objects.get_or_create(user=user)

    return p


def get_profile(user):
    app_label, model_name = PROFILE_MODULE.split('.')
    model = models.get_model(app_label, model_name)
    return model.objects.get(user=user)


class MergeTestApi(BaseTestCaseMixin, TransactionTestCase):
    def setUp(self):
        super(MergeTestApi, self).setUp()
        self.master_pk = 2
        self.other_pk = 3

    def tearDown(self):
        super(MergeTestApi, self).tearDown()

    def test_merge_success_no_commit(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        result = merge(master, other)

        self.assertTrue(User.objects.filter(pk=master.pk).exists())
        self.assertTrue(User.objects.filter(pk=other.pk).exists())

        self.assertEqual(result.pk, master.pk)
        self.assertEqual(result.first_name, other.first_name)
        self.assertEqual(result.last_name, other.last_name)
        self.assertEqual(result.password, other.password)

    def test_merge_success_fields_no_commit(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        result = merge(master, other, ['password', 'last_login'])

        master = User.objects.get(pk=master.pk)

        self.assertTrue(User.objects.filter(pk=master.pk).exists())
        self.assertTrue(User.objects.filter(pk=other.pk).exists())

        self.assertNotEqual(result.last_login, master.last_login)
        self.assertEqual(result.last_login, other.last_login)
        self.assertEqual(result.password, other.password)

        self.assertNotEqual(result.last_name, other.last_name)

    def test_merge_success_commit(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        result = merge(master, other, commit=True)

        master = User.objects.get(pk=result.pk)  # reload
        self.assertTrue(User.objects.filter(pk=master.pk).exists())
        self.assertFalse(User.objects.filter(pk=other.pk).exists())

        self.assertEqual(result.pk, master.pk)
        self.assertEqual(master.first_name, other.first_name)
        self.assertEqual(master.last_name, other.last_name)
        self.assertEqual(master.password, other.password)

    def test_merge_success_m2m(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        group = Group.objects.get_or_create(name='G1')[0]
        other.groups.add(group)
        other.save()

        result = merge(master, other, commit=True, m2m=['groups'])
        master = User.objects.get(pk=result.pk)  # reload
        self.assertSequenceEqual(master.groups.all(), [group])

    def test_merge_success_m2m_all(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        group = Group.objects.get_or_create(name='G1')[0]
        perm = Permission.objects.all()[0]
        other.groups.add(group)
        other.user_permissions.add(perm)
        other.save()

        merge(master, other, commit=True, m2m=ALL_FIELDS)
        self.assertSequenceEqual(master.groups.all(), [group])
        self.assertSequenceEqual(master.user_permissions.all(), [perm])

    def test_merge_success_related_all(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        entry = other.logentry_set.get_or_create(object_repr='test', action_flag=1)[0]

        result = merge(master, other, commit=True, related=ALL_FIELDS)

        master = User.objects.get(pk=result.pk)  # reload
        self.assertSequenceEqual(master.logentry_set.all(), [entry])
        self.assertTrue(LogEntry.objects.filter(pk=entry.pk).exists())

    # @skipIf(not hasattr(settings, 'AUTH_PROFILE_MODULE'), "")
    def test_merge_one_to_one_field(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        profile = assert_profile(other)
        if profile:
            entry = other.logentry_set.get_or_create(object_repr='test', action_flag=1)[0]

            result = merge(master, other, commit=True, related=ALL_FIELDS)

            master = User.objects.get(pk=result.pk)  # reload
            self.assertSequenceEqual(master.logentry_set.all(), [entry])
            self.assertTrue(LogEntry.objects.filter(pk=entry.pk).exists())
            self.assertEqual(get_profile(result), profile)
            # self.assertEqual(master.get_profile(), profile)

    def test_merge_ignore_related(self):
        master = User.objects.get(pk=self.master_pk)
        other = User.objects.get(pk=self.other_pk)
        entry = other.logentry_set.get_or_create(object_repr='test', action_flag=1)[0]
        result = merge(master, other, commit=True, related=None)

        master = User.objects.get(pk=result.pk)  # reload
        self.assertSequenceEqual(master.logentry_set.all(), [])
        self.assertFalse(User.objects.filter(pk=other.pk).exists())
        self.assertFalse(LogEntry.objects.filter(pk=entry.pk).exists())


class TestMergeAction(SelectRowsMixin, WebTestMixin, TransactionTestCase):
    fixtures = ['adminactions.json', 'demoproject.json']
    urls = 'demoproject.urls'
    sender_model = User
    action_name = 'merge'
    _selected_rows = [1, 2]

    def setUp(self):
        super(TestMergeAction, self).setUp()
        self.url = reverse('admin:auth_user_changelist')
        self.user = G(User, username='user', is_staff=True, is_active=True)

    def _run_action(self, steps=3, page_start=None):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_merge_user']):
            if isinstance(steps, int):
                steps = range(1, steps + 1)
                res = self.app.get('/', user='user')
                res = res.click('Users')
            else:
                res = page_start
            if 1 in steps:
                form = res.forms['changelist-form']
                form['action'] = 'merge'
                self._select_rows(form)
                res = form.submit()
                assert not hasattr(res.form, 'errors')

            if 2 in steps:
                res.form['username'] = res.form['form-1-username'].value
                res.form['email'] = res.form['form-1-email'].value
                res.form['last_login'] = res.form['form-1-last_login'].value
                res.form['date_joined'] = res.form['form-1-date_joined'].value
                res = res.form.submit('preview')
                assert not hasattr(res.form, 'errors')

            if 3 in steps:
                res = res.form.submit('apply')
            return res

    def test_no_permission(self):
        with user_grant_permission(self.user, ['auth.change_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'merge'
            self._select_rows(form)
            res = form.submit().follow()
            assert 'Sorry you do not have rights to execute this action' in res.body

    def test_success(self):
        res = self._run_action(1)
        preserved = User.objects.get(pk=self._selected_values[0])
        removed = User.objects.get(pk=self._selected_values[1])

        assert preserved.email != removed.email  # sanity check

        res = self._run_action([2, 3], res)

        self.assertFalse(User.objects.filter(pk=removed.pk).exists())
        self.assertTrue(User.objects.filter(pk=preserved.pk).exists())

        preserved_after = User.objects.get(pk=self._selected_values[0])
        self.assertEqual(preserved_after.email, removed.email)
        self.assertFalse(LogEntry.objects.filter(pk=removed.pk).exists())

    def test_error_if_too_many_records(self):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_merge_user']):
            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'merge'
            self._select_rows(form, [1, 2, 3])
            res = form.submit().follow()
            self.assertContains(res, 'Please select exactly 2 records')

    def test_swap(self):
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_merge_user']):
            #removed = User.objects.get(pk=self._selected_rows[0])
            #preserved = User.objects.get(pk=self._selected_rows[1])

            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'merge'
            self._select_rows(form, [1, 2])
            res = form.submit()
            removed = User.objects.get(pk=self._selected_values[0])
            preserved = User.objects.get(pk=self._selected_values[1])

            # steps = 2 (swap):
            res.form['master_pk'] = self._selected_values[1]
            res.form['other_pk'] = self._selected_values[0]

            res.form['username'] = res.form['form-0-username'].value
            res.form['email'] = res.form['form-0-email'].value
            res.form['last_login'] = res.form['form-1-last_login'].value
            res.form['date_joined'] = res.form['form-1-date_joined'].value

            # res.form['field_names'] = 'username,email'

            res = res.form.submit('preview')
            # steps = 3:
            res = res.form.submit('apply')

            preserved_after = User.objects.get(pk=self._selected_values[1])
            self.assertFalse(User.objects.filter(pk=removed.pk).exists())
            self.assertTrue(User.objects.filter(pk=preserved.pk).exists())

            self.assertEqual(preserved_after.email, removed.email)
            self.assertFalse(LogEntry.objects.filter(pk=removed.pk).exists())

    def test_merge_move_detail(self):
        from adminactions.merge import MergeForm
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_merge_user']):
            #removed = User.objects.get(pk=self._selected_rows[0])
            #preserved = User.objects.get(pk=self._selected_rows[1])

            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'merge'
            self._select_rows(form, [1, 2])
            res = form.submit()
            removed = User.objects.get(pk=self._selected_values[0])
            preserved = User.objects.get(pk=self._selected_values[1])

            removed.userdetail_set.create(note='1')
            preserved.userdetail_set.create(note='2')

            # steps = 2:
            res.form['master_pk'] = self._selected_values[1]
            res.form['other_pk'] = self._selected_values[0]

            res.form['username'] = res.form['form-0-username'].value
            res.form['email'] = res.form['form-0-email'].value
            res.form['last_login'] = res.form['form-1-last_login'].value
            res.form['date_joined'] = res.form['form-1-date_joined'].value
            res.form['dependencies'] = MergeForm.DEP_MOVE
            res = res.form.submit('preview')
            # steps = 3:
            res = res.form.submit('apply')

            preserved_after = User.objects.get(pk=self._selected_values[1])
            self.assertEqual(preserved_after.userdetail_set.count(), 2)
            self.assertFalse(User.objects.filter(pk=removed.pk).exists())

    def test_merge_delete_detail(self):
        from adminactions.merge import MergeForm
        with user_grant_permission(self.user, ['auth.change_user', 'auth.adminactions_merge_user']):
            #removed = User.objects.get(pk=self._selected_rows[0])
            #preserved = User.objects.get(pk=self._selected_rows[1])

            res = self.app.get('/', user='user')
            res = res.click('Users')
            form = res.forms['changelist-form']
            form['action'] = 'merge'
            self._select_rows(form, [1, 2])
            res = form.submit()
            removed = User.objects.get(pk=self._selected_values[0])
            preserved = User.objects.get(pk=self._selected_values[1])

            removed.userdetail_set.create(note='1')
            preserved.userdetail_set.create(note='2')

            # steps = 2:
            res.form['master_pk'] = self._selected_values[1]
            res.form['other_pk'] = self._selected_values[0]

            res.form['username'] = res.form['form-0-username'].value
            res.form['email'] = res.form['form-0-email'].value
            res.form['last_login'] = res.form['form-1-last_login'].value
            res.form['date_joined'] = res.form['form-1-date_joined'].value
            res.form['dependencies'] = MergeForm.DEP_DELETE
            res = res.form.submit('preview')
            # steps = 3:
            res = res.form.submit('apply')

            preserved_after = User.objects.get(pk=self._selected_values[1])
            self.assertEqual(preserved_after.userdetail_set.count(), 1)
            self.assertFalse(User.objects.filter(pk=removed.pk).exists())

########NEW FILE########
__FILENAME__ = test_transaction
import pytest
from django.contrib.auth.models import Group
from django_dynamic_fixture import G
from adminactions import compat


@pytest.mark.django_db(transaction=True)
def test_nocommit():
    with compat.nocommit():
        G(Group, name='name')
    assert not Group.objects.filter(name='name').exists()

########NEW FILE########
__FILENAME__ = test_utils
import pytest
from adminactions.utils import get_verbose_name


def test_get_verbose_name():
    from django.contrib.auth.models import User, Permission

    user = User()
    p = Permission()
    assert unicode(get_verbose_name(user, 'username')) == 'username'

    assert unicode(get_verbose_name(User, 'username')) == 'username'

    assert unicode(get_verbose_name(User.objects.all(), 'username')) == 'username'

    assert unicode(get_verbose_name(User.objects, 'username')) == 'username'

    assert unicode(get_verbose_name(User.objects, user._meta.get_field_by_name('username')[0])) == 'username'

    assert unicode(get_verbose_name(p, 'content_type.model')) == 'python model class name'

    with pytest.raises(ValueError):
        get_verbose_name(object, 'aaa')


def test_flatten():
    from adminactions.utils import flatten

    assert flatten([[[1, 2, 3], (42, None)], [4, 5], [6], 7, (8, 9, 10)]) == [1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10]

########NEW FILE########
__FILENAME__ = urls
from django.contrib import admin
from django.conf.urls import patterns, include
from adminactions import actions
import adminactions.urls

try:
    from django.apps import AppConfig
    import django

    django.setup()
except ImportError:
    pass

admin.autodiscover()
actions.add_to_site(admin.site)

urlpatterns = patterns('',
                       (r'', include(admin.site.urls)),
                       (r'admin/', include(admin.site.urls)),
                       (r'as/', include(adminactions.urls)),
                       )

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
import string
from random import choice
import django
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.models import Group, Permission
from django.forms import BaseForm
from django_dynamic_fixture import G
from adminactions.exceptions import ActionInterrupted
from adminactions.signals import adminaction_requested, adminaction_start, adminaction_end


class admin_register(object):
    def __init__(self, model, model_admin=None, unregister=False):
        self.model = model
        self.model_admin = model_admin
        self.unregister = unregister

    def __enter__(self):
        try:
            admin.site.register(self.model, self.model_admin)
            self.unregister = True
        except AlreadyRegistered:
            pass
        return admin.site._registry[self.model]

    def __exit__(self, *exc_info):
        if self.unregister:
            admin.site.unregister(self.model)

    def start(self):
        """Activate a patch, returning any created mock."""
        result = self.__enter__()
        return result

    def stop(self):
        """Stop an active patch."""
        return self.__exit__()

#def admin_register(model):
#    try:
#        admin.site.register(model)
#    except AlreadyRegistered:
#        pass
#
#    return admin.site._registry[model]


def text(length, choices=string.ascii_letters):
    """ returns a random (fixed length) string

    :param length: string length
    :param choices: string containing all the chars can be used to build the string

    .. seealso::
       :py:func:`rtext`
    """
    return ''.join(choice(choices) for x in range(length))


def get_group(name=None, permissions=None):
    group = G(Group, name=(name or text(5)))
    permission_names = permissions or []
    for permission_name in permission_names:
        try:
            app_label, codename = permission_name.split('.')
        except ValueError:
            raise ValueError("Invalid permission name `{0}`".format(permission_name))
        try:
            permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
        except Permission.DoesNotExist:
            raise Permission.DoesNotExist('Permission `{0}` does not exists', permission_name)

        group.permissions.add(permission)
    return group


class user_grant_permission(object):
    def __init__(self, user, permissions=None):
        self.user = user
        self.permissions = permissions
        self.group = None

    def __enter__(self):
        if hasattr(self.user, '_group_perm_cache'):
            del self.user._group_perm_cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache
        self.group = get_group(permissions=self.permissions or [])
        self.user.groups.add(self.group)

    def __exit__(self, *exc_info):
        if self.group:
            self.user.groups.remove(self.group)
            self.group.delete()

    def start(self):
        """Activate a patch, returning any created mock."""
        result = self.__enter__()
        return result

    def stop(self):
        """Stop an active patch."""
        return self.__exit__()


class SelectRowsMixin(object):
    _selected_rows = []
    _selected_values = []

    def _select_rows(self, form, selected_rows=None):
        if selected_rows is None:
            selected_rows = self._selected_rows

        self._selected_values = []
        for r in selected_rows:
            chk = form.get('_selected_action', r, default=None)
            if chk:
                form.set('_selected_action', True, r)
                self._selected_values.append(int(chk.value))


class CheckSignalsMixin(object):
    MESSAGE = 'Action Interrupted Test'

    def test_signal_sent(self):
        def handler_factory(name):
            def myhandler(sender, action, request, queryset, **kwargs):
                handler_factory.invoked[name] = True
                self.assertEqual(action, self.action_name)
                self.assertSequenceEqual(queryset.order_by('id').values_list('id', flat=True),
                                         sorted(self._selected_values))

            return myhandler

        handler_factory.invoked = {}

        try:
            m1 = handler_factory('adminaction_requested')
            adminaction_requested.connect(m1, sender=self.sender_model)

            m2 = handler_factory('adminaction_start')
            adminaction_start.connect(m2, sender=self.sender_model)

            m3 = handler_factory('adminaction_end')
            adminaction_end.connect(m3, sender=self.sender_model)

            self._run_action()
            self.assertIn('adminaction_requested', handler_factory.invoked)
            self.assertIn('adminaction_start', handler_factory.invoked)
            self.assertIn('adminaction_end', handler_factory.invoked)

        finally:
            adminaction_requested.disconnect(m1, sender=self.sender_model)
            adminaction_start.disconnect(m2, sender=self.sender_model)
            adminaction_end.disconnect(m3, sender=self.sender_model)

    def test_signal_requested(self):
        # test if adminaction_requested Signal can stop the action

        def myhandler(sender, action, request, queryset, **kwargs):
            myhandler.invoked = True
            self.assertEqual(action, self.action_name)
            self.assertSequenceEqual(queryset.order_by('id').values_list('id', flat=True),
                                     sorted(self._selected_values))
            raise ActionInterrupted(self.MESSAGE)

        try:
            adminaction_requested.connect(myhandler, sender=self.sender_model)
            self._run_action(1)
            self.assertTrue(myhandler.invoked)
            self.assertIn(self.MESSAGE, self.app.cookies['messages'])
        finally:
            adminaction_requested.disconnect(myhandler, sender=self.sender_model)

    def test_signal_start(self):
        # test if adminaction_start Signal can stop the action

        def myhandler(sender, action, request, queryset, form, **kwargs):
            myhandler.invoked = True
            self.assertEqual(action, self.action_name)
            self.assertSequenceEqual(queryset.order_by('id').values_list('id', flat=True),
                                     sorted(self._selected_values))
            self.assertTrue(isinstance(form, BaseForm))
            raise ActionInterrupted(self.MESSAGE)

        try:
            adminaction_start.connect(myhandler, sender=self.sender_model)
            self._run_action(2)
            self.assertTrue(myhandler.invoked)
            self.assertIn(self.MESSAGE, self.app.cookies['messages'])
        finally:
            adminaction_start.disconnect(myhandler, sender=self.sender_model)

    def test_signal_end(self):
        # test if adminaction_start Signal can stop the action

        def myhandler(sender, action, request, queryset, **kwargs):
            myhandler.invoked = True
            self.assertEqual(action, self.action_name)
            self.assertSequenceEqual(queryset.order_by('id').values_list('id', flat=True),
                                     sorted(self._selected_values))

        try:
            adminaction_end.connect(myhandler, sender=self.sender_model)
            self._run_action(2)
            self.assertTrue(myhandler.invoked)
        finally:
            adminaction_end.disconnect(myhandler, sender=self.sender_model)

########NEW FILE########
