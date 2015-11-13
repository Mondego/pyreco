__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _, ugettext
from django.conf.urls import patterns, url
from django.contrib.admin.views.main import ChangeList
from django.http import Http404

from form_designer.forms import FormDefinitionForm, FormDefinitionFieldInlineForm
from form_designer.models import FormDefinition, FormDefinitionField, FormLog, FormValue
from form_designer import settings
from form_designer.utils import get_class


class FormDefinitionFieldInline(admin.StackedInline):
    form = FormDefinitionFieldInlineForm
    model = FormDefinitionField
    extra = 1
    fieldsets = [
        (_('Basic'), {'fields': ['name', 'field_class', 'required', 'initial']}),
        (_('Display'), {'fields': ['label', 'widget', 'help_text', 'position', 'include_result']}),
        (_('Text'), {'fields': ['max_length', 'min_length']}),
        (_('Numbers'), {'fields': ['max_value', 'min_value', 'max_digits', 'decimal_places']}),
        (_('Regex'), {'fields': ['regex']}),
        (_('Choices'), {'fields': ['choice_values', 'choice_labels']}),
        (_('Model Choices'), {'fields': ['choice_model', 'choice_model_empty_label']}),
    ]


class FormDefinitionAdmin(admin.ModelAdmin):
    fieldsets = [
        (_('Basic'), {'fields': ['name', 'require_hash', 'method', 'action', 'title', 'body']}),
        (_('Settings'), {'fields': ['allow_get_initial', 'log_data', 'success_redirect', 'success_clear', 'display_logged', 'save_uploaded_files'], 'classes': ['collapse']}),
        (_('Mail form'), {'fields': ['mail_to', 'mail_from', 'mail_subject', 'mail_uploaded_files'], 'classes': ['collapse']}),
        (_('Templates'), {'fields': ['message_template', 'form_template_name'], 'classes': ['collapse']}),
        (_('Messages'), {'fields': ['success_message', 'error_message', 'submit_label'], 'classes': ['collapse']}),
    ]
    list_display = ('name', 'title', 'method', 'count_fields')
    form = FormDefinitionForm
    inlines = [
        FormDefinitionFieldInline,
    ]


class FormLogAdmin(admin.ModelAdmin):
    list_display = ('form_no_link', 'created', 'id', 'created_by', 'data_html')
    list_filter = ('form_definition',)
    list_display_links = ()
    date_hierarchy = 'created'

    exporter_classes = {}
    exporter_classes_ordered = []
    for class_path in settings.EXPORTER_CLASSES:
        cls = get_class(class_path)
        if cls.is_enabled():
            exporter_classes[cls.export_format()] = cls 
            exporter_classes_ordered.append(cls)

    def get_exporter_classes(self):
        return self.__class__.exporter_classes_ordered

    def get_actions(self, request):
        actions = super(FormLogAdmin, self).get_actions(request)

        for cls in self.get_exporter_classes():
            desc = _("Export selected %%(verbose_name_plural)s as %s") % cls.export_format()
            actions[cls.export_format()] = (cls.export_view, cls.export_format(), desc)
            
        return actions

    # Disabling all edit links: Hack as found at http://stackoverflow.com/questions/1618728/disable-link-to-edit-object-in-djangos-admin-display-list-only
    def form_no_link(self, obj):
        return '<a>'+obj.form_definition.__unicode__()+'</a>'
    form_no_link.admin_order_field = 'form_definition'
    form_no_link.allow_tags = True
    form_no_link.short_description = _('Form')

    def get_urls(self):
        urls = patterns('',
            url(r'^export/(?P<format>[a-zA-Z0-9_-]+)/$', self.admin_site.admin_view(self.export_view), name='form_designer_export'),
        )
        return urls + super(FormLogAdmin, self).get_urls()

    def data_html(self, obj):
        return obj.form_definition.compile_message(obj.data, 'html/formdefinition/data_message.html')
    data_html.allow_tags = True
    data_html.short_description = _('Data')

    def get_change_list_query_set(self, request, extra_context=None):
        """
        The 'change list' admin view for this model.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_filter = self.get_list_filter(request)
        ChangeList = self.get_changelist(request)

        cl = ChangeList(request, self.model, list_display,
            list_display_links, list_filter, self.date_hierarchy,
            self.search_fields, self.list_select_related,
            self.list_per_page, self.list_max_show_all, self.list_editable,
            self)
        return cl.get_query_set(request)

    def export_view(self, request, format):
        queryset = self.get_change_list_query_set(request)
        if not format in self.exporter_classes:
            raise Http404()
        return self.exporter_classes[format](self.model).export(request, queryset)

    def changelist_view(self, request, extra_context=None):
        from django.core.urlresolvers import reverse, NoReverseMatch
        extra_context = extra_context or {}
        try:
            query_string = '?'+request.META['QUERY_STRING']
        except (TypeError, KeyError):
            query_string = ''

        exporter_links = [] 
        for cls in self.get_exporter_classes():
            url = reverse('admin:form_designer_export', args=(cls.export_format(),))+query_string
            exporter_links.append({'url': url, 'label': _('Export view as %s') % cls.export_format()})

        extra_context['exporters'] = exporter_links

        return super(FormLogAdmin, self).changelist_view(request, extra_context)


admin.site.register(FormDefinition, FormDefinitionAdmin)
admin.site.register(FormLog, FormLogAdmin)

########NEW FILE########
__FILENAME__ = cms_plugins
from form_designer.contrib.cms_plugins.form_designer_form.models import CMSFormDefinition
from form_designer.views import process_form
from form_designer import settings

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from django.utils.translation import ugettext as _


class FormDesignerPlugin(CMSPluginBase):
    model = CMSFormDefinition
    module = _('Form Designer')
    name = _('Form')
    admin_preview = False
    render_template = False

    def render(self, context, instance, placeholder):
        if instance.form_definition.form_template_name:
            self.render_template = instance.form_definition.form_template_name
        else:
            self.render_template = settings.DEFAULT_FORM_TEMPLATE

        # Redirection does not work with CMS plugin, hence disable:
        return process_form(context['request'], instance.form_definition, context, disable_redirection=True)


plugin_pool.register_plugin(FormDesignerPlugin)

########NEW FILE########
__FILENAME__ = models
from form_designer.models import FormDefinition
from cms.models import CMSPlugin
from django.db import models
from django.utils.translation import ugettext_lazy as _


class CMSFormDefinition(CMSPlugin):
    form_definition = models.ForeignKey(FormDefinition, verbose_name=_('form'))

    def __unicode__(self):
        return self.form_definition.__unicode__()

########NEW FILE########
__FILENAME__ = csv_exporter
from form_designer.contrib.exporters import FormLogExporterBase
from form_designer import settings
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse

import csv

class CsvExporter(FormLogExporterBase):

    @staticmethod
    def export_format():
        return 'CSV'

    def init_writer(self):
        self.writer = csv.writer(self.response, delimiter=settings.CSV_EXPORT_DELIMITER)

    def init_response(self):
        self.response = HttpResponse(mimetype='text/csv')
        self.response['Content-Disposition'] = 'attachment; filename=%s.csv' %  \
            unicode(self.model._meta.verbose_name_plural)

    def writerow(self, row):
        self.writer.writerow(row)

    def export(self, request, queryset=None):
        return super(CsvExporter, self).export(request, queryset)

########NEW FILE########
__FILENAME__ = xls_exporter
from form_designer.contrib.exporters import FormLogExporterBase
from form_designer import settings
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from django.utils.encoding import smart_unicode

try:
    import xlwt
except ImportError:
    XLWT_INSTALLED = False
else:
    XLWT_INSTALLED = True


class XlsExporter(FormLogExporterBase):

    @staticmethod
    def export_format():
        return 'XLS'

    @staticmethod
    def is_enabled():
        return XLWT_INSTALLED 

    def init_writer(self):
        self.wb = xlwt.Workbook()
        self.ws = self.wb.add_sheet(unicode(self.model._meta.verbose_name_plural))
        self.rownum = 0

    def init_response(self):
        self.response = HttpResponse(mimetype='application/ms-excel')
        self.response['Content-Disposition'] = 'attachment; filename=%s.xls' %  \
            unicode(self.model._meta.verbose_name_plural)

    def writerow(self, row):
        for i, f in enumerate(row):
            self.ws.write(self.rownum, i, smart_unicode(f, encoding=settings.CSV_EXPORT_ENCODING))
        self.rownum += 1

    def close(self):
        self.wb.save(self.response)

    def export(self, request, queryset=None):
        return super(XlsExporter, self).export(request, queryset)

########NEW FILE########
__FILENAME__ = fields
from django.db import models
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


class ModelNameFormField(forms.CharField):

    @staticmethod
    def get_model_from_string(model_path):
        try:
            app_label, model_name = model_path.rsplit('.models.')
            return models.get_model(app_label, model_name)
        except:
            return None

    def clean(self, value):
        """
        Validates that the input matches the regular expression. Returns a
        Unicode object.
        """
        value = super(ModelNameFormField, self).clean(value)
        if value == u'':
            return value
        if not ModelNameFormField.get_model_from_string(value):
            raise ValidationError(
                _('Model could not be imported: %(value)s. Please use a valid model path.'),
                    code='invalid',
                    params={'value': value},
                )
        return value

class ModelNameField(models.CharField):

    @staticmethod
    def get_model_from_string(model_path):
        return ModelNameFormField.get_model_from_string(model_path)

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {'form_class': ModelNameFormField}
        defaults.update(kwargs)
        return super(ModelNameField, self).formfield(**defaults)

class TemplateFormField(forms.CharField):

    def clean(self, value):
        """
        Validates that the input can be compiled as a template.
        """
        value = super(TemplateFormField, self).clean(value)
        from django.template import Template, TemplateSyntaxError
        try:
            Template(value)
        except TemplateSyntaxError, error:
            raise ValidationError(error)
        return value

class TemplateCharField(models.CharField):

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {'form_class': TemplateFormField}
        defaults.update(kwargs)
        return super(TemplateCharField, self).formfield(**defaults)

class TemplateTextField(models.TextField):

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {'form_class': TemplateFormField}
        defaults.update(kwargs)
        return super(TemplateTextField, self).formfield(**defaults)

class RegexpExpressionFormField(forms.CharField):

    def clean(self, value):
        """
        Validates that the input can be compiled as a Regular Expression.
        """
        value = super(RegexpExpressionFormField, self).clean(value)
        import re
        try:
            re.compile(value)
        except Exception, error:
            raise ValidationError(error)
        return value

class RegexpExpressionField(models.CharField):

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {'form_class': RegexpExpressionFormField}
        defaults.update(kwargs)
        return super(RegexpExpressionField, self).formfield(**defaults)

########NEW FILE########
__FILENAME__ = forms
import os

from django import forms
from django.forms import widgets
from django.conf import settings as django_settings
from django.utils.translation import ugettext as _

from form_designer import settings
from form_designer.models import FormDefinitionField, FormDefinition
from form_designer.uploads import clean_files
from form_designer.utils import get_class


class DesignedForm(forms.Form):

    def __init__(self, form_definition, initial_data=None, *args, **kwargs):
        super(DesignedForm, self).__init__(*args, **kwargs)
        self.file_fields = []
        for def_field in form_definition.formdefinitionfield_set.all():
            self.add_defined_field(def_field, initial_data)
        self.fields[form_definition.submit_flag_name] = forms.BooleanField(required=False, initial=1, widget=widgets.HiddenInput)

    def add_defined_field(self, def_field, initial_data=None):
        if initial_data and initial_data.has_key(def_field.name):
            if not def_field.field_class in ('django.forms.MultipleChoiceField', 'django.forms.ModelMultipleChoiceField'):
                def_field.initial = initial_data.get(def_field.name)
            else:
                def_field.initial = initial_data.getlist(def_field.name)
        field = get_class(def_field.field_class)(**def_field.get_form_field_init_args())
        self.fields[def_field.name] = field
        if isinstance(field, forms.FileField):
            self.file_fields.append(def_field)

    def clean(self):
        return clean_files(self)
        

class FormDefinitionFieldInlineForm(forms.ModelForm):
    class Meta:
        model = FormDefinitionField

    def clean_regex(self):
        if not self.cleaned_data['regex'] and self.cleaned_data.has_key('field_class') and self.cleaned_data['field_class'] in ('django.forms.RegexField',):
            raise forms.ValidationError(_('This field class requires a regular expression.'))
        return self.cleaned_data['regex']

    def clean_choice_model(self):
        if not self.cleaned_data['choice_model'] and self.cleaned_data.has_key('field_class') and self.cleaned_data['field_class'] in ('django.forms.ModelChoiceField', 'django.forms.ModelMultipleChoiceField'):
            raise forms.ValidationError(_('This field class requires a model.'))
        return self.cleaned_data['choice_model']


class FormDefinitionForm(forms.ModelForm):
    class Meta:
        model = FormDefinition

    def _media(self):
        js = []
        plugins = [
            'js/jquery-ui.js',
            'js/jquery-inline-positioning.js',
            'js/jquery-inline-rename.js',
            'js/jquery-inline-collapsible.js',
            'js/jquery-inline-fieldset-collapsible.js',
            'js/jquery-inline-prepopulate-label.js',
        ]
        if hasattr(django_settings, 'JQUERY_URL'):
            js.append(django_settings.JQUERY_URL)
        else:
            plugins = ['js/jquery.js'] + plugins
        js.extend(
            [os.path.join(settings.STATIC_URL, path) for path in plugins])
        return forms.Media(js=js)
    media = property(_media)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FormDefinition'
        db.create_table('form_designer_formdefinition', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=255, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('action', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('mail_to', self.gf('form_designer.fields.TemplateCharField')(max_length=255, null=True, blank=True)),
            ('mail_from', self.gf('form_designer.fields.TemplateCharField')(max_length=255, null=True, blank=True)),
            ('mail_subject', self.gf('form_designer.fields.TemplateCharField')(max_length=255, null=True, blank=True)),
            ('method', self.gf('django.db.models.fields.CharField')(default='POST', max_length=10)),
            ('success_message', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('error_message', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('submit_label', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('log_data', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('success_redirect', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('success_clear', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('allow_get_initial', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('message_template', self.gf('form_designer.fields.TemplateTextField')(null=True, blank=True)),
            ('form_template_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal('form_designer', ['FormDefinition'])

        # Adding model 'FormLog'
        db.create_table('form_designer_formlog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('form_definition', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['form_designer.FormDefinition'])),
            ('data', self.gf(DATA_FIELD_TYPE)(null=True, blank=True)),
        ))
        db.send_create_signal('form_designer', ['FormLog'])

        # Adding model 'FormDefinitionField'
        db.create_table('form_designer_formdefinitionfield', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('form_definition', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['form_designer.FormDefinition'])),
            ('field_class', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('position', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('required', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('include_result', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('widget', self.gf('django.db.models.fields.CharField')(default='', max_length=255, null=True, blank=True)),
            ('initial', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('help_text', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('choice_values', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('choice_labels', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('max_length', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('min_length', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('max_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('min_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('max_digits', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('decimal_places', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('regex', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('choice_model', self.gf('form_designer.fields.ModelNameField')(max_length=255, null=True, blank=True)),
            ('choice_model_empty_label', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal('form_designer', ['FormDefinitionField'])


    def backwards(self, orm):
        
        # Deleting model 'FormDefinition'
        db.delete_table('form_designer_formdefinition')

        # Deleting model 'FormLog'
        db.delete_table('form_designer_formlog')

        # Deleting model 'FormDefinitionField'
        db.delete_table('form_designer_formdefinitionfield')


    models = {
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'data': (DATA_FIELD_TYPE, [], {'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_formdefinitionfield_initial
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'FormDefinitionField.initial'
        db.alter_column('form_designer_formdefinitionfield', 'initial', self.gf('django.db.models.fields.TextField')(null=True, blank=True))


    def backwards(self, orm):
        
        # Changing field 'FormDefinitionField.initial'
        db.alter_column('form_designer_formdefinitionfield', 'initial', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True))


    models = {
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'data': (DATA_FIELD_TYPE, [], {'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_formdefinition_display_logged
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FormDefinition.display_logged'
        db.add_column('form_designer_formdefinition', 'display_logged', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'FormDefinition.display_logged'
        db.delete_column('form_designer_formdefinition', 'display_logged')


    models = {
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'display_logged': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'data': (DATA_FIELD_TYPE, [], {'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_formdefinition_body
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FormDefinition.body'
        db.add_column('form_designer_formdefinition', 'body', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'FormDefinition.body'
        db.delete_column('form_designer_formdefinition', 'body')


    models = {
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_logged': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'data': (DATA_FIELD_TYPE, [], {'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_formdefinition_require_hash__add_field_formdefinition_
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FormDefinition.require_hash'
        db.add_column('form_designer_formdefinition', 'require_hash', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)

        # Adding field 'FormDefinition.private_hash'
        db.add_column('form_designer_formdefinition', 'private_hash', self.gf('django.db.models.fields.CharField')(default='', max_length=40), keep_default=False)

        # Adding field 'FormDefinition.public_hash'
        db.add_column('form_designer_formdefinition', 'public_hash', self.gf('django.db.models.fields.CharField')(default='', max_length=40), keep_default=False)

        # Changing field 'FormDefinitionField.regex'
        db.alter_column('form_designer_formdefinitionfield', 'regex', self.gf('form_designer.fields.RegexpExpressionField')(max_length=255, null=True, blank=True))


    def backwards(self, orm):
        
        # Deleting field 'FormDefinition.require_hash'
        db.delete_column('form_designer_formdefinition', 'require_hash')

        # Deleting field 'FormDefinition.private_hash'
        db.delete_column('form_designer_formdefinition', 'private_hash')

        # Deleting field 'FormDefinition.public_hash'
        db.delete_column('form_designer_formdefinition', 'public_hash')

        # Changing field 'FormDefinitionField.regex'
        db.alter_column('form_designer_formdefinitionfield', 'regex', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True))


    models = {
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_logged': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'private_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'public_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'require_hash': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('form_designer.fields.RegexpExpressionField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'data': (DATA_FIELD_TYPE, [], {'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_formdefinition_save_uploaded_files
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FormDefinition.save_uploaded_files'
        db.add_column('form_designer_formdefinition', 'save_uploaded_files', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'FormDefinition.save_uploaded_files'
        db.delete_column('form_designer_formdefinition', 'save_uploaded_files')


    models = {
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_logged': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'private_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'public_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'require_hash': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'save_uploaded_files': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('form_designer.fields.RegexpExpressionField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'data': (DATA_FIELD_TYPE, [], {'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_formdefinition_mail_uploaded_files
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FormDefinition.mail_uploaded_files'
        db.add_column('form_designer_formdefinition', 'mail_uploaded_files', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'FormDefinition.mail_uploaded_files'
        db.delete_column('form_designer_formdefinition', 'mail_uploaded_files')


    models = {
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_logged': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_uploaded_files': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'private_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'public_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'require_hash': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'save_uploaded_files': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('form_designer.fields.RegexpExpressionField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'data': (DATA_FIELD_TYPE, [], {'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0008_auto__add_formvalue__del_field_formlog_data__add_field_formlog_created
# encoding: utf-8
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError: # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_column('form_designer_formlog', 'data', 'tmp_data')
        # Adding field 'FormLog.created_by'
        db.add_column('form_designer_formlog', 'created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm["%s.%s" % (User._meta.app_label, User._meta.object_name)], null=True, blank=True), keep_default=False)

        # Adding model 'FormValue'
        db.create_table('form_designer_formvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('form_log', self.gf('django.db.models.fields.related.ForeignKey')(related_name='values', to=orm['form_designer.FormLog'])),
            ('field_name', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('value', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('form_designer', ['FormValue'])

    def backwards(self, orm):
        # Adding field 'FormLog.data'
        db.add_column('form_designer_formlog', 'data', self.gf(DATA_FIELD_TYPE)(null=True, blank=True), keep_default=False)

        # Deleting field 'FormLog.created_by'
        db.delete_column('form_designer_formlog', 'created_by_id')

        # Deleting model 'FormValue'
        db.delete_table('form_designer_formvalue')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
         "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User.__name__},
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_logged': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_uploaded_files': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'private_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'public_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'require_hash': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'save_uploaded_files': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'ordering': "['position']", 'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('form_designer.fields.RegexpExpressionField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "User", 'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'form_designer.formvalue': {
            'Meta': {'object_name': 'FormValue'},
            'field_name': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'form_log': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'values'", 'to': "orm['form_designer.FormLog']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['form_designer']

########NEW FILE########
__FILENAME__ = 0009_set_data_to_form_log
# -*- coding: utf-8 -*-
from form_designer.settings import VALUE_PICKLEFIELD
DATA_FIELD_TYPE = 'picklefield.fields.PickledObjectField' if VALUE_PICKLEFIELD else 'django.db.models.fields.TextField'

import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        if VALUE_PICKLEFIELD:
            from picklefield.fields import PickledObjectField
            tmp_data = PickledObjectField(null=True, blank=True)
        else:
            tmp_data = models.TextField(null=True, blank=True)
        tmp_data.contribute_to_class(orm['form_designer.FormLog'], 'tmp_data')

        for log in orm['form_designer.FormLog'].objects.all():
            log.set_data(log.tmp_data)
            log.save()

        # Deleting field 'FormLog.data'
        db.delete_column('form_designer_formlog', 'tmp_data')

    def backwards(self, orm):
        for log in orm['form_designer.FormLog'].objects.all():
            log.data = log.get_data()
            raise Exception(log.data)
            log.save()

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'form_designer.formdefinition': {
            'Meta': {'object_name': 'FormDefinition'},
            'action': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'allow_get_initial': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'body': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_logged': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'error_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'form_template_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_data': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'mail_from': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_subject': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_to': ('form_designer.fields.TemplateCharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mail_uploaded_files': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'message_template': ('form_designer.fields.TemplateTextField', [], {'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'default': "'POST'", 'max_length': '10'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255'}),
            'private_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'public_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'require_hash': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'save_uploaded_files': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'submit_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_clear': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'success_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'success_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formdefinitionfield': {
            'Meta': {'ordering': "['position']", 'object_name': 'FormDefinitionField'},
            'choice_labels': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'choice_model': ('form_designer.fields.ModelNameField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_model_empty_label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'choice_values': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'decimal_places': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'field_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['form_designer.FormDefinition']"}),
            'help_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_result': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'max_digits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'max_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'min_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'position': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'regex': ('form_designer.fields.RegexpExpressionField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'widget': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'form_designer.formlog': {
            'Meta': {'object_name': 'FormLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'form_definition': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['form_designer.FormDefinition']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'form_designer.formvalue': {
            'Meta': {'object_name': 'FormValue'},
            'field_name': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            'form_log': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'values'", 'to': "orm['form_designer.FormLog']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['form_designer']
    symmetrical = True

########NEW FILE########
__FILENAME__ = models
import re
import hashlib, uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from django.forms import widgets
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils.datastructures import SortedDict
from django.core.exceptions import ImproperlyConfigured

# support for custom User models in Django 1.5+
try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from form_designer.fields import TemplateTextField, TemplateCharField, ModelNameField, RegexpExpressionField
from form_designer.utils import get_class
from form_designer import settings

if settings.VALUE_PICKLEFIELD:
    try:
        from picklefield.fields import PickledObjectField
    except ImportError:
        raise ImproperlyConfigured('FORM_DESIGNER_VALUE_PICKLEFIELD is True, but django-picklefield is not installed.')


class FormValueDict(dict):
    def __init__(self, name, value, label):
        self['name'] = name
        self['value'] = value
        self['label'] = label
        super(FormValueDict, self).__init__()


class FormDefinition(models.Model):
    name = models.SlugField(_('name'), max_length=255, unique=True)
    require_hash = models.BooleanField(_('obfuscate URL to this form'), default=False, help_text=_('If enabled, the form can only be reached via a secret URL.'))
    private_hash = models.CharField(editable=False, max_length=40, default='')
    public_hash = models.CharField(editable=False, max_length=40, default='')
    title = models.CharField(_('title'), max_length=255, blank=True, null=True)
    body = models.TextField(_('body'), blank=True, null=True)
    action = models.URLField(_('target URL'), help_text=_('If you leave this empty, the page where the form resides will be requested, and you can use the mail form and logging features. You can also send data to external sites: For instance, enter "http://www.google.ch/search" to create a search form.'), max_length=255, blank=True, null=True)
    mail_to = TemplateCharField(_('send form data to e-mail address'), help_text=('Separate several addresses with a comma. Your form fields are available as template context. Example: "admin@domain.com, {{ from_email }}" if you have a field named `from_email`.'), max_length=255, blank=True, null=True)
    mail_from = TemplateCharField(_('sender address'), max_length=255, help_text=('Your form fields are available as template context. Example: "{{ first_name }} {{ last_name }} <{{ from_email }}>" if you have fields named `first_name`, `last_name`, `from_email`.'), blank=True, null=True)
    mail_subject = TemplateCharField(_('email subject'), max_length=255, help_text=('Your form fields are available as template context. Example: "Contact form {{ subject }}" if you have a field named `subject`.'), blank=True, null=True)
    mail_uploaded_files  = models.BooleanField(_('Send uploaded files as email attachments'), default=True)
    method = models.CharField(_('method'), max_length=10, default="POST", choices = (('POST', 'POST'), ('GET', 'GET')))
    success_message = models.CharField(_('success message'), max_length=255, blank=True, null=True)
    error_message = models.CharField(_('error message'), max_length=255, blank=True, null=True)
    submit_label = models.CharField(_('submit button label'), max_length=255, blank=True, null=True)
    log_data = models.BooleanField(_('log form data'), help_text=_('Logs all form submissions to the database.'), default=True)
    save_uploaded_files  = models.BooleanField(_('save uploaded files'), help_text=_('Saves all uploaded files using server storage.'), default=True)
    success_redirect = models.BooleanField(_('HTTP redirect after successful submission'), default=True)
    success_clear = models.BooleanField(_('clear form after successful submission'), default=True)
    allow_get_initial = models.BooleanField(_('allow initial values via URL'), help_text=_('If enabled, you can fill in form fields by adding them to the query string.'), default=True)
    message_template = TemplateTextField(_('message template'), help_text=_('Your form fields are available as template context. Example: "{{ message }}" if you have a field named `message`. To iterate over all fields, use the variable `data` (a list containing a dictionary for each form field, each containing the elements `name`, `label`, `value`).'), blank=True, null=True)
    form_template_name = models.CharField(_('form template'), max_length=255, choices=settings.FORM_TEMPLATES, blank=True, null=True)
    display_logged = models.BooleanField(_('display logged submissions with form'), default=False)

    class Meta:
        verbose_name = _('Form')
        verbose_name_plural = _('Forms')

    def save(self, *args, **kwargs):
        if not self.private_hash:
            self.private_hash = hashlib.sha1(str(uuid.uuid4())).hexdigest()
        if not self.public_hash:
            self.public_hash = hashlib.sha1(str(uuid.uuid4())).hexdigest()
        super(FormDefinition, self).save()

    def get_field_dict(self):
        field_dict = SortedDict()
        names = []
        for field in self.formdefinitionfield_set.all():
            field_dict[field.name] = field
        return field_dict

    @models.permalink
    def get_absolute_url(self):
        if self.require_hash:
            return ('form_designer.views.detail_by_hash', [str(self.public_hash)])
        return ('form_designer.views.detail', [str(self.name)])

    def get_form_data(self, form):
        # TODO: refactor, move to utils or views
        data = []
        field_dict = self.get_field_dict()
        form_keys = form.fields.keys()
        def_keys = field_dict.keys()
        for key in form_keys:
            if key in def_keys and field_dict[key].include_result:
                value = form.cleaned_data[key]
                if getattr(value, '__form_data__', False):
                    value = value.__form_data__()
                data.append(FormValueDict(key, value, form.fields[key].label))
        return data

    def get_form_data_context(self, form_data):
        # TODO: refactor, move to utils
        dict = {}
        if form_data:
            for field in form_data:
                dict[field['name']] = field['value']
        return dict

    def compile_message(self, form_data, template=None):
        # TODO: refactor, move to utils
        from django.template.loader import get_template
        from django.template import Context, Template
        if template:
            t = get_template(template)
        elif not self.message_template:
            t = get_template('txt/formdefinition/data_message.txt')
        else:
            t = Template(self.message_template)
        context = Context(self.get_form_data_context(form_data))
        context['data'] = form_data
        return t.render(context)

    def count_fields(self):
        return self.formdefinitionfield_set.count()
    count_fields.short_description = _('Fields')

    def __unicode__(self):
        return self.title or self.name

    def log(self, form, user=None):
        form_data = self.get_form_data(form)
        created_by = None
        if user and user.is_authenticated():
            created_by = user
        FormLog(form_definition=self, data=form_data, created_by=created_by).save()

    def string_template_replace(self, text, context_dict):
        # TODO: refactor, move to utils
        from django.template import Context, Template, TemplateSyntaxError
        try:
            t = Template(text)
            return t.render(Context(context_dict))
        except TemplateSyntaxError:
            return text

    def send_mail(self, form, files=[]):
        # TODO: refactor, move to utils
        form_data = self.get_form_data(form)
        message = self.compile_message(form_data)
        context_dict = self.get_form_data_context(form_data)

        mail_to = re.compile('\s*[,;]+\s*').split(self.mail_to)
        for key, email in enumerate(mail_to):
            mail_to[key] = self.string_template_replace(email, context_dict)

        mail_from = self.mail_from or None
        if mail_from:
            mail_from = self.string_template_replace(mail_from, context_dict)

        if self.mail_subject:
            mail_subject = self.string_template_replace(self.mail_subject, context_dict)
        else:
            mail_subject = self.title

        from django.core.mail import EmailMessage
        message = EmailMessage(mail_subject, message, mail_from or None, mail_to)

        if self.mail_uploaded_files:
            for file_path in files:
                message.attach_file(file_path)

        message.send(fail_silently=False)

    @property
    def submit_flag_name(self):
        name = settings.SUBMIT_FLAG_NAME % self.name
        # make sure we are not overriding one of the actual form fields 
        while self.formdefinitionfield_set.filter(name__exact=name).count() > 0:
            name += '_'
        return name


class FormDefinitionField(models.Model):

    form_definition = models.ForeignKey(FormDefinition)
    field_class = models.CharField(_('field class'), choices=settings.FIELD_CLASSES, max_length=100)
    position = models.IntegerField(_('position'), blank=True, null=True)

    name = models.SlugField(_('name'), max_length=255)
    label = models.CharField(_('label'), max_length=255, blank=True, null=True)
    required = models.BooleanField(_('required'), default=True)
    include_result = models.BooleanField(_('include in result'), help_text=('If this is disabled, the field value will not be included in logs and e-mails generated from form data.'), default=True)
    widget = models.CharField(_('widget'), default='', choices=settings.WIDGET_CLASSES, max_length=255, blank=True, null=True)
    initial = models.TextField(_('initial value'), blank=True, null=True)
    help_text = models.CharField(_('help text'), max_length=255, blank=True, null=True)

    choice_values = models.TextField(_('values'), help_text=_('One value per line'), blank=True, null=True)
    choice_labels = models.TextField(_('labels'), help_text=_('One label per line'), blank=True, null=True)

    max_length = models.IntegerField(_('max. length'), blank=True, null=True)
    min_length = models.IntegerField(_('min. length'), blank=True, null=True)
    max_value = models.FloatField(_('max. value'), blank=True, null=True)
    min_value = models.FloatField(_('min. value'), blank=True, null=True)
    max_digits = models.IntegerField(_('max. digits'), blank=True, null=True)
    decimal_places = models.IntegerField(_('decimal places'), blank=True, null=True)

    regex = RegexpExpressionField(_('regular Expression'), max_length=255, blank=True, null=True)

    choice_model_choices = settings.CHOICE_MODEL_CHOICES
    choice_model = ModelNameField(_('data model'), max_length=255, blank=True, null=True, choices=choice_model_choices, help_text=('your_app.models.ModelName' if not choice_model_choices else None))
    choice_model_empty_label = models.CharField(_('empty label'), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _('field')
        verbose_name_plural = _('fields')
        ordering = ['position']

    def save(self, *args, **kwargs):
        if self.position == None:
            self.position = 0
        super(FormDefinitionField, self).save(*args, **kwargs)

    def ____init__(self, field_class=None, name=None, required=None, widget=None, label=None, initial=None, help_text=None, *args, **kwargs):
        super(FormDefinitionField, self).__init__(*args, **kwargs)
        self.name = name
        self.field_class = field_class  
        self.required = required
        self.widget = widget
        self.label = label
        self.initial = initial
        self.help_text = help_text

    def get_form_field_init_args(self):
        args = {
            'required': self.required,
            'label': self.label if self.label else '',
            'initial': self.initial if self.initial else None,
            'help_text': self.help_text,
        }

        if self.field_class in ('django.forms.CharField', 'django.forms.EmailField', 'django.forms.RegexField'):
            args.update({
                'max_length': self.max_length,
                'min_length': self.min_length,
            })

        if self.field_class in ('django.forms.IntegerField', 'django.forms.DecimalField'):
            args.update({
                'max_value': int(self.max_value) if self.max_value != None else None,
                'min_value': int(self.min_value) if self.min_value != None else None,
            })

        if self.field_class == 'django.forms.DecimalField':
            args.update({
                'max_value': Decimal(str(self.max_value)) if self.max_value != None else None,
                'min_value': Decimal(str(self.min_value)) if self.max_value != None else None,
                'max_digits': self.max_digits,
                'decimal_places': self.decimal_places,
            })

        if self.field_class == 'django.forms.RegexField':
            if self.regex:
                args.update({
                    'regex': self.regex
                })

        if self.field_class in ('django.forms.ChoiceField', 'django.forms.MultipleChoiceField'):
            if self.choice_values:
                choices = []
                regex = re.compile('[\s]*\n[\s]*')
                values = regex.split(self.choice_values)
                labels = regex.split(self.choice_labels) if self.choice_labels else []
                for index, value in enumerate(values):
                    try:
                        label = labels[index]
                    except:
                        label = value
                    choices.append((value, label))
                args.update({
                    'choices': tuple(choices)
                })

        if self.field_class in ('django.forms.ModelChoiceField', 'django.forms.ModelMultipleChoiceField'):
            args.update({
                'queryset': ModelNameField.get_model_from_string(self.choice_model).objects.all()
            })

        if self.field_class == 'django.forms.ModelChoiceField':
            args.update({
                'empty_label': self.choice_model_empty_label
            })

        if self.widget:
            args.update({
                'widget': get_class(self.widget)()
            })

        return args

    def __unicode__(self):
        return self.label if self.label else self.name


class FormLog(models.Model):
    form_definition = models.ForeignKey(FormDefinition, related_name='logs')
    created = models.DateTimeField(_('Created'), auto_now=True)
    created_by = models.ForeignKey(User, null=True, blank=True)
    _data = None

    def __unicode__(self):
        return "%s (%s)" % (self.form_definition.title or  \
            self.form_definition.name, self.created) 

    def get_data(self):
        if self._data:
            # before instance is saved
            return self._data
        data = []
        fields = self.form_definition.get_field_dict()
        values_with_header = {}
        values_without_header = []
        for item in self.values.all():
            field = fields.get(item.field_name, None)
            if field:
                # get field label if field definition still exists
                label = field.label
            else:
                # field may have been removed
                label = None

            value_dict = FormValueDict(item.field_name, item.value,
                label)

            if item.field_name in fields:
                values_with_header[item.field_name] = value_dict
            else:
                values_without_header.append(value_dict)

        for field_name, field in fields.items():
            if field_name in values_with_header:
                data.append(values_with_header[field_name])
            else:
                data.append(FormValueDict(field.name, None, field.label))
        for value in values_without_header:
            data.append(value)

        return data

    def set_data(self, form_data):
        # keep form data in temporary variable since instance must
        # be saved before saving values
        self._data = form_data

    data = property(get_data, set_data)

    def save(self, *args, **kwargs):
        super(FormLog, self).save(*args, **kwargs)
        if self._data: 
            # safe form data and then clear temporary variable
            for value in self.values.all():
                value.delete()
            for item in self._data:
                value = FormValue()
                value.field_name = item['name']
                value.value = item['value']
                self.values.add(value)
            self._data = None


class FormValue(models.Model):
    form_log = models.ForeignKey(FormLog, related_name='values')
    field_name = models.SlugField(_('field name'), max_length=255)
    if settings.VALUE_PICKLEFIELD:
        # use PickledObjectField if available because it preserves the
        # original data type
        value = PickledObjectField(_('value'), null=True, blank=True)
    else:
        # otherwise just use a TextField, with the drawback that
        # all values will just be stored as unicode strings, 
        # but you can easily query the database for form results.
        value = models.TextField(_('value'), null=True, blank=True)

    def __unicode__(self):
        return u'%s = %s' % (self.field_name, self.value)


if 'south' in django_settings.INSTALLED_APPS:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^form_designer\.fields\..*"])



########NEW FILE########
__FILENAME__ = settings
import os.path

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import get_storage_class

STATIC_URL = os.path.join(getattr(settings, 'STATIC_URL', settings.MEDIA_URL), 'form_designer')

FIELD_CLASSES = getattr(settings, 'FORM_DESIGNER_FIELD_CLASSES', (
    ('django.forms.CharField', _('Text')),
    ('django.forms.EmailField', _('E-mail address')),
    ('django.forms.URLField', _('Web address')),
    ('django.forms.IntegerField', _('Number')),
    ('django.forms.DecimalField', _('Decimal number')),
    ('django.forms.BooleanField', _('Yes/No')),
    ('django.forms.DateField', _('Date')),
    ('django.forms.DateTimeField', _('Date & time')),
    ('django.forms.TimeField', _('Time')),
    ('django.forms.ChoiceField', _('Choice')),
    ('django.forms.MultipleChoiceField', _('Multiple Choice')),
    ('django.forms.ModelChoiceField', _('Model Choice')),
    ('django.forms.ModelMultipleChoiceField', _('Model Multiple Choice')),
    ('django.forms.RegexField', _('Regex')),
    ('django.forms.FileField', _('File')),
    # ('captcha.fields.CaptchaField', _('Captcha')),
))

WIDGET_CLASSES = getattr(settings, 'FORM_DESIGNER_WIDGET_CLASSES', (
    ('', _('Default')),
    ('django.forms.widgets.Textarea', _('Text area')),
    ('django.forms.widgets.PasswordInput', _('Password input')),
    ('django.forms.widgets.HiddenInput', _('Hidden input')),
    ('django.forms.widgets.RadioSelect', _('Radio button')),
))

EXPORTER_CLASSES = getattr(settings, 'FORM_DESIGNER_EXPORTER_CLASSES', (
    'form_designer.contrib.exporters.csv_exporter.CsvExporter',
    'form_designer.contrib.exporters.xls_exporter.XlsExporter',
))

FORM_TEMPLATES = getattr(settings, 'FORM_DESIGNER_FORM_TEMPLATES', (
    ('', _('Default')),
    ('html/formdefinition/forms/as_p.html', _('as paragraphs')),
    ('html/formdefinition/forms/as_table.html', _('as table')),
    ('html/formdefinition/forms/as_table_h.html', _('as table (horizontal)')),
    ('html/formdefinition/forms/as_ul.html', _('as unordered list')),
    ('html/formdefinition/forms/custom.html', _('custom implementation')),
))

# Sequence of two-tuples like (('your_app.models.ModelName', 'My Model'), ...) for limiting the models available to ModelChoiceField and ModelMultipleChoiceField.
# If None, any model can be chosen by entering it as a string
CHOICE_MODEL_CHOICES = getattr(settings, 'FORM_DESIGNER_CHOICE_MODEL_CHOICES', None)

DEFAULT_FORM_TEMPLATE = getattr(settings, 'FORM_DESIGNER_DEFAULT_FORM_TEMPLATE', 'html/formdefinition/forms/as_p.html')

# semicolon is Microsoft Excel default
CSV_EXPORT_DELIMITER = getattr(settings, 'FORM_DESIGNER_CSV_EXPORT_DELIMITER', ';')

# include log timestamp in export
CSV_EXPORT_INCLUDE_CREATED = getattr(settings, 'FORM_DESIGNER_CSV_EXPORT_INCLUDE_CREATED', True)

CSV_EXPORT_INCLUDE_PK = getattr(settings, 'FORM_DESIGNER_CSV_EXPORT_INCLUDE_PK', True)

# include field labels/names in first row if exporting logs for one form only
CSV_EXPORT_INCLUDE_HEADER = getattr(settings, 'FORM_DESIGNER_CSV_EXPORT_INCLUDE_HEADER', True)

# include form title if exporting logs for more than one form
CSV_EXPORT_INCLUDE_FORM = getattr(settings, 'FORM_DESIGNER_CSV_EXPORT_INCLUDE_FORM', True)

CSV_EXPORT_ENCODING = getattr(settings, 'FORM_DESIGNER_CSV_EXPORT_ENCODING', 'utf-8')

CSV_EXPORT_NULL_VALUE = getattr(settings, 'FORM_DESIGNER_CSV_EXPORT_NULL_VALUE', '')

SUBMIT_FLAG_NAME = getattr(settings, 'FORM_DESIGNER_SUBMIT_FLAG_NAME', 'submit__%s')

FILE_STORAGE_CLASS = getattr(settings, 'FORM_DESIGNER_FILE_STORAGE_CLASS', get_storage_class())

FILE_STORAGE_DIR = 'form_uploads'

ALLOWED_FILE_TYPES = getattr(settings, 'FORM_DESIGNER_ALLOWED_FILE_TYPES', (
    'aac', 'ace', 'ai', 'aiff', 'avi', 'bmp', 'dir', 'doc', 'docx', 'dmg', 'eps', 'fla', 'flv', 
    'gif', 'gz', 'hqx', 'ico', 'indd', 'inx', 'jpg', 'jar', 'jpeg', 'md', 'mov', 
    'mp3', 'mp4', 'mpc', 'mkv', 'mpg', 'mpeg', 'ogg', 'odg', 'odf', 'odp', 'ods', 'odt', 'otf', 
    'pdf', 'png', 'pps', 'ppsx', 'ps', 'psd', 'rar', 'rm', 'rtf', 'sit', 'swf', 'tar', 'tga', 
    'tif', 'tiff', 'ttf', 'txt', 'wav', 'wma', 'wmv', 'xls', 'xlsx', 'xml', 'zip'
))

MAX_UPLOAD_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 5242880) # 5M
MAX_UPLOAD_TOTAL_SIZE = getattr(settings, 'MAX_UPLOAD_TOTAL_SIZE', 10485760) # 10M

# If true, submitted values won't be stored as strings, but serialized to a PickleField,
# preserving the original type.
VALUE_PICKLEFIELD = getattr(settings, 'FORM_DESIGNER_VALUE_PICKLEFIELD', True)

########NEW FILE########
__FILENAME__ = signals
from django import dispatch

designedform_submit = dispatch.Signal(providing_args=["designed_form"])
designedform_success = dispatch.Signal(providing_args=["designed_form"])
designedform_error = dispatch.Signal(providing_args=["designed_form"])
designedform_render = dispatch.Signal(providing_args=["designed_form"])

########NEW FILE########
__FILENAME__ = friendly
from django import template
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import yesno

register = template.Library()

# Returns a more "human-friendly" representation of value than repr()
def friendly(value, null_value=None): 
    if value is None and not (null_value is None):
        return null_value
    if type(value) is QuerySet:
        qs = value
        value = []        
        for object in qs:
            value.append(object.__unicode__())
    if type(value) is list:
        value = ", ".join(value)
    if type(value) is bool:
        value = yesno(value, u"%s,%s" % (_('yes'), _('no')),)
    if hasattr(value, 'url'):
        value = value.url
    if not isinstance(value, basestring):
        value = unicode(value)
    return value

register.filter(friendly)
########NEW FILE########
__FILENAME__ = widget_type
from django import template
register = template.Library()

@register.filter('field_type')
def field_type(obj):
    return obj.__class__.__name__

########NEW FILE########
__FILENAME__ = uploads
from form_designer import settings as app_settings
from django.core.files.base import File
from django.forms.forms import NON_FIELD_ERRORS
from django.utils.translation import ugettext_lazy as _
from django.db.models.fields.files import FieldFile
from django.template.defaultfilters import filesizeformat
import os
import hashlib, uuid


def get_storage():
    return app_settings.FILE_STORAGE_CLASS()


def clean_files(form):
    total_upload_size = 0
    for field in form.file_fields:
        uploaded_file = form.cleaned_data.get(field.name, None)
        msg = None
        if uploaded_file is None:
            if field.required:
                msg = _('This field is required.')
            else:
                continue
        else:
            total_upload_size += uploaded_file._size
            if not os.path.splitext(uploaded_file.name)[1].lstrip('.').lower() in  \
                app_settings.ALLOWED_FILE_TYPES:
                    msg = _('This file type is not allowed.')
            elif uploaded_file._size > app_settings.MAX_UPLOAD_SIZE:
                msg = _('Please keep file size under %(max_size)s. Current size is %(size)s.') %  \
                    {'max_size': filesizeformat(app_settings.MAX_UPLOAD_SIZE),
                    'size': filesizeformat(uploaded_file._size)}
        if msg:
            form._errors[field.name] = form.error_class([msg])

    if total_upload_size > app_settings.MAX_UPLOAD_TOTAL_SIZE:
        msg = _('Please keep total file size under %(max)s. Current total size is %(current)s.') %  \
            {"max": filesizeformat(app_settings.MAX_UPLOAD_TOTAL_SIZE), "current": filesizeformat(total_upload_size)}

        if NON_FIELD_ERRORS in form._errors:
            form._errors[NON_FIELD_ERRORS].append(msg)
        else:
            form._errors[NON_FIELD_ERRORS] = form.error_class([msg])

    return form.cleaned_data
    

def handle_uploaded_files(form_definition, form):
    files = []
    if form_definition.save_uploaded_files and len(form.file_fields):
        storage = get_storage()
        secret_hash = hashlib.sha1(str(uuid.uuid4())).hexdigest()[:10]
        for field in form.file_fields:
            uploaded_file = form.cleaned_data.get(field.name, None)
            if uploaded_file is None:
                continue
            valid_file_name = storage.get_valid_name(uploaded_file.name)
            root, ext = os.path.splitext(valid_file_name)
            filename = storage.get_available_name(
                os.path.join(app_settings.FILE_STORAGE_DIR, 
                form_definition.name, 
                '%s_%s%s' % (root, secret_hash, ext)))
            storage.save(filename, uploaded_file)
            form.cleaned_data[field.name] = StoredUploadedFile(filename)
            files.append(storage.path(filename))
    return files


class StoredUploadedFile(FieldFile):
    """
    A wrapper for uploaded files that is compatible to the FieldFile class, i.e.
    you can use instances of this class in templates just like you use the value
    of FileFields (e.g. `{{ my_file.url }}`) 
    """
    def __init__(self, name):
        File.__init__(self, None, name)
        self.field = self

    @property
    def storage(self):
        return get_storage()
        
    def save(self, *args, **kwargs):
        raise NotImplementedError('Static files are read-only')

    def delete(self, *args, **kwargs):
        raise NotImplementedError('Static files are read-only')

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^(?P<object_name>[-\w]+)/$', 'form_designer.views.detail', name='form_designer_detail'),
    url(r'^h/(?P<public_hash>[-\w]+)/$', 'form_designer.views.detail_by_hash', name='form_designer_detail_by_hash'),
)

########NEW FILE########
__FILENAME__ = utils
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module

def get_class(import_path):
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a Python path." % import_path)
    module, classname = import_path[:dot], import_path[dot + 1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing module %s: "%s"' %
                                   (module, e))
    try:
        return getattr(mod, classname)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a "%s" '
                                   'class.' % (module, classname))

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect
from django.conf import settings
from form_designer import settings as app_settings
from django.contrib import messages
from django.core.context_processors import csrf

import os
import random
from datetime import datetime

from form_designer.forms import DesignedForm
from form_designer.models import FormDefinition, FormLog
from form_designer.uploads import handle_uploaded_files
from form_designer.signals import (designedform_submit, designedform_success, 
                                designedform_error, designedform_render)


def process_form(request, form_definition, extra_context={}, disable_redirection=False):
    context = extra_context
    success_message = form_definition.success_message or _('Thank you, the data was submitted successfully.')
    error_message = form_definition.error_message or _('The data could not be submitted, please try again.')
    form_error = False
    form_success = False
    is_submit = False
    # If the form has been submitted...
    if request.method == 'POST' and request.POST.get(form_definition.submit_flag_name):
        form = DesignedForm(form_definition, None, request.POST, request.FILES)
        is_submit = True
    if request.method == 'GET' and request.GET.get(form_definition.submit_flag_name):
        form = DesignedForm(form_definition, None, request.GET)
        is_submit = True

    if is_submit:
        designedform_submit.send(sender=process_form, context=context,
            form_definition=form_definition, request=request)
        if form.is_valid():
            # Handle file uploads using storage object
            files = handle_uploaded_files(form_definition, form)

            # Successful submission
            messages.success(request, success_message)
            form_success = True

            designedform_success.send(sender=process_form, context=context,
                form_definition=form_definition, request=request)

            if form_definition.log_data:
                form_definition.log(form, request.user)
            if form_definition.mail_to:
                form_definition.send_mail(form, files)
            if form_definition.success_redirect and not disable_redirection:
                return HttpResponseRedirect(form_definition.action or '?')
            if form_definition.success_clear:
                form = DesignedForm(form_definition) # clear form
        else:
            form_error = True
            designedform_error.send(sender=process_form, context=context,
                form_definition=form_definition, request=request)
            messages.error(request, error_message)
    else:
        if form_definition.allow_get_initial:
            form = DesignedForm(form_definition, initial_data=request.GET)
        else:
            form = DesignedForm(form_definition)
        designedform_render.send(sender=process_form, context=context,
            form_definition=form_definition, request=request)

    context.update({
        'form_error': form_error,
        'form_success': form_success,
        'form': form,
        'form_definition': form_definition
    })
    context.update(csrf(request))
    
    if form_definition.display_logged:
        logs = form_definition.logs.all().order_by('created')
        context.update({'logs': logs})
        
    return context

def _form_detail_view(request, form_definition):
    result = process_form(request, form_definition)
    if isinstance(result, HttpResponseRedirect):
        return result
    result.update({
        'form_template': form_definition.form_template_name or app_settings.DEFAULT_FORM_TEMPLATE
    })
    return render_to_response('html/formdefinition/detail.html', result,
        context_instance=RequestContext(request))

def detail(request, object_name):
    form_definition = get_object_or_404(FormDefinition, name=object_name, require_hash=False)
    return _form_detail_view(request, form_definition) 

def detail_by_hash(request, public_hash):
    form_definition = get_object_or_404(FormDefinition, public_hash=public_hash)
    return _form_detail_view(request, form_definition) 

########NEW FILE########
