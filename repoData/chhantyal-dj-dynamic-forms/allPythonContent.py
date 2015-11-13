__FILENAME__ = conf
#!/usr/bin/env python
import sys
from os.path import abspath, dirname, join

sys.path.insert(0, abspath(join(dirname(__file__), '..', '..')))

from dynamic_forms import get_version

# -- General configuration -----------------------------------------------------

project = 'django-dynamic-forms'
copyright = '2013, Markus Holtermann'
version = get_version(full=False)
release = get_version()

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
exclude_patterns = []

master_doc = 'index'
source_suffix = '.rst'

pygments_style = 'sphinx'
templates_path = ['_templates']

intersphinx_mapping = {
    'django': ('https://docs.djangoproject.com/en/dev/',
               'https://docs.djangoproject.com/en/dev/_objects/'),
    'python2': ('http://docs.python.org/2/', None),
    'python3': ('http://docs.python.org/3/', None),
}

# -- Options for HTML output ---------------------------------------------------
html_theme = 'nature'
html_static_path = ['_static']
htmlhelp_basename = 'django-dynamic-formsdoc'
modindex_common_prefix = ['dynamic_forms.']

########NEW FILE########
__FILENAME__ = actions
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import ugettext, ugettext_lazy as _

from dynamic_forms.conf import settings


class ActionRegistry(object):

    def __init__(self):
        self._actions = {}

    def get(self, key):
        return self._actions.get(key, None)

    def get_as_choices(self):
        return sorted([(k, f.label) for k, f in six.iteritems(self._actions)],
                      key=lambda x: x[1])

    def register(self, func, label):
        if not callable(func):
            raise ValueError('%r must be a callable' % func)
        func.label = label
        key = '%s.%s' % (func.__module__, func.__name__)
        self._actions[key] = func

    def unregister(self, key):
        if key in self._actions:
            del self._actions[key]


action_registry = ActionRegistry()


def formmodel_action(label):
    def decorator(func):
        action_registry.register(func, label)
        return func
    return decorator


@formmodel_action(ugettext('Send via email'))
def dynamic_form_send_email(form_model, form):
    mapped_data = form.get_mapped_data()

    subject = _('Form “%(formname)s” submitted') % {'formname': form_model}
    message = render_to_string('dynamic_forms/email.txt', {
        'form': form_model,
        'data': sorted(mapped_data.items()),
    })
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = settings.DYNAMIC_FORMS_EMAIL_RECIPIENTS
    send_mail(subject, message, from_email, recipient_list)


@formmodel_action(ugettext('Store in database'))
def dynamic_form_store_database(form_model, form):
    from dynamic_forms.models import FormModelData
    cleaned_data = form.cleaned_data
    FormModelData.objects.create(form=form_model, value=cleaned_data)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import six

from django import forms
from django.contrib import admin
from django.forms.util import flatatt
from django.utils.encoding import force_text
# TODO: Django >1.4:
# from django.utils.html import format_html
from django.utils.html import conditional_escape

from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from dynamic_forms.formfields import dynamic_form_field_registry
from dynamic_forms.models import FormFieldModel, FormModel, FormModelData


class ReadOnlyWidget(forms.Widget):

    def __init__(self, attrs=None, **kwargs):
        self.show_text = kwargs.pop('show_text', None)
        super(ReadOnlyWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        content = ''
        if value is not None:
            content = value
        if self.show_text is not None:
            content = self.show_text
        final_attrs = self.build_attrs(attrs)
        # TODO: Django >1.4:
        # return format_html('<span{0}>{1}</span>',
        #    flatatt(final_attrs),
        #    force_text(content))
        return mark_safe('<span{0}>{1}</span>'.format(
            conditional_escape(flatatt(final_attrs)),
            conditional_escape(force_text(content))
        ))


class OptionsWidget(forms.MultiWidget):

    def __init__(self, option_names, widgets, attrs=None):
        self.option_names = option_names
        super(OptionsWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        mapping = json.loads(value) if value else {}
        return [mapping.get(key, None) for key in self.option_names]

    def format_output(self, rendered_widgets, id_):
        output = []
        i = 0
        for n, (r, w) in six.moves.zip(self.option_names, rendered_widgets):
            # TODO: Django >1.4:
            #output.append(format_html('<label for="{0}_{1}">{2}:</label>{3}',
            #    w.id_for_label(id_), i, n, r))
            output.append(
                mark_safe('<label for="{0}_{1}">{2}:</label>{3}'.format(
                    conditional_escape(w.id_for_label(id_)),
                    conditional_escape(i),
                    conditional_escape(n),
                    conditional_escape(r)
                )))

            i += 1
        return mark_safe('<div style="display:inline-block;">' +
            ('<br />\n'.join(output)) + '</div>')

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            rendered = widget.render(name + '_%s' % i, widget_value,
                final_attrs)
            output.append((rendered, widget))
        return mark_safe(self.format_output(output, id_))


class OptionsField(forms.MultiValueField):

    def __init__(self, meta, *args, **kwargs):
        self.option_names = []
        self.option_fields = []
        self.option_widgets = []
        initial = {}
        for name, option in sorted(meta.items()):
            self.option_names.append(name)
            initial[name] = option[1]
            formfield = option[2]
            if isinstance(formfield, forms.Field):
                self.option_fields.append(formfield)
                self.option_widgets.append(formfield.widget)
            elif isinstance(formfield, (tuple, list)):
                if isinstance(formfield[0], forms.Field):
                    self.option_fields.append(formfield[0])
                else:
                    self.option_fields.append(formfield[0]())
                if isinstance(formfield[1], forms.Widget):
                    self.option_widgets.append(formfield[1])
                else:
                    self.option_widgets.append(formfield[1]())
            elif isinstance(formfield, type):
                self.option_fields.append(formfield())
                self.option_widgets.append(formfield.widget)
        kwargs['widget'] = OptionsWidget(self.option_names,
            self.option_widgets)
        if 'initial' in kwargs:
            kwargs['initial'].update(initial)
        else:
            kwargs['initial'] = initial
        super(OptionsField, self).__init__(self.option_fields, *args, **kwargs)

    def compress(self, data_list):
        data = {}
        for name, value in six.moves.zip(self.option_names, data_list):
            if value is not None:
                data[name] = value
        return json.dumps(data)


class AdminFormFieldInlineForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        meta = None
        if instance:
            df = dynamic_form_field_registry.get(instance.field_type)
            if df:
                meta = df._meta
        super(AdminFormFieldInlineForm, self).__init__(*args, **kwargs)
        if meta is not None:
            self.fields['_options'] = OptionsField(meta, required=False,
                label=_('Options'))
        else:
            self.fields['_options'].widget = ReadOnlyWidget(show_text=_(
                'The options for this field will be available once it has '
                'been stored the first time.'
            ))


class FormFieldModelInlineAdmin(admin.StackedInline):
    extra = 3
    form = AdminFormFieldInlineForm
    list_display = ('field_type', 'name', 'label')
    model = FormFieldModel
    prepopulated_fields = {"name": ("label",)}


class FormModelAdmin(admin.ModelAdmin):
    inlines = (FormFieldModelInlineAdmin,)
    list_display = ('name', 'submit_url', 'success_url')
    model = FormModel

admin.site.register(FormModel, FormModelAdmin)


class FormModelDataAdmin(admin.ModelAdmin):
    list_display = ('form', 'value', 'submitted')
    model = FormModelData

admin.site.register(FormModelData, FormModelDataAdmin)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
from django.conf import settings

from appconf import AppConf


class DynamicFormsConf(AppConf):
    EMAIL_RECIPIENTS = [mail[1] for mail in settings.ADMINS]

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from django.db import models, migrations
import django.db.models.deletion
import dynamic_forms.fields


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            bases = (models.Model,),
            fields = [
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID'),),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Name'),),
                ('submit_url', models.CharField(max_length=100, unique=True, help_text='The full URL path to the form. It should start and end with a forward slash (<code>/</code>).', verbose_name='Submit URL'),),
                ('success_url', models.CharField(max_length=100, help_text='The full URL path where the user will be redirected after successfully sending the form. It should start and end with a forward slash (<code>/</code>). If empty, the success URL is generated by appending <code>done/</code> to the “Submit URL”.', default='', blank=True, verbose_name='Success URL'),),
                ('actions', dynamic_forms.fields.TextMultiSelectField(default='', choices=[
                    ('dynamic_forms.actions.dynamic_form_send_email', 'Send via email',),
                    ('dynamic_forms.actions.dynamic_form_store_database', 'Store in database',)], verbose_name='Actions'),),
                ('form_template', models.CharField(max_length=100, default='dynamic_forms/form.html', verbose_name='Form template path'),),
                ('success_template', models.CharField(max_length=100, default='dynamic_forms/form_success.html', verbose_name='Success template path'),)],
            options = {'ordering': ['name'], 'verbose_name_plural': 'Dynamic forms', 'verbose_name': 'Dynamic form'},
            name = 'FormModel',
        ),
        migrations.CreateModel(
            bases = (models.Model,),
            fields = [
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID'),),
                ('parent_form', models.ForeignKey(to_field='id', to='dynamic_forms.FormModel'),),
                ('field_type', models.CharField(max_length=255, choices=[
                    ('dynamic_forms.formfields.BooleanField', 'Boolean',),
                    ('dynamic_forms.formfields.ChoiceField', 'Choices',),
                    ('dynamic_forms.formfields.DateField', 'Date',),
                    ('dynamic_forms.formfields.DateTimeField', 'Date and Time',),
                    ('dynamic_forms.formfields.EmailField', 'Email',),
                    ('dynamic_forms.formfields.IntegerField', 'Integer',),
                    ('dynamic_forms.formfields.MultiLineTextField', 'Multi Line Text',),
                    ('dynamic_forms.formfields.SingleLineTextField', 'Single Line Text',),
                    ('dynamic_forms.formfields.TimeField', 'Time',)], verbose_name='Type'),),
                ('label', models.CharField(max_length=20, verbose_name='Label'),),
                ('name', models.SlugField(blank=True, verbose_name='Name'),),
                ('_options', models.TextField(null=True, blank=True, verbose_name='Options'),),
                ('position', models.SmallIntegerField(default=0, blank=True, verbose_name='Position'),)],
            options = {'unique_together': set(['parent_form', 'name']), 'ordering': ['parent_form', 'position'], 'verbose_name_plural': 'Form fields', 'verbose_name': 'Form field'},
            name = 'FormFieldModel',
        ),
        migrations.CreateModel(
            bases = (models.Model,),
            fields = [
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID'),),
                ('form', models.ForeignKey(null=True, to_field='id', to='dynamic_forms.FormModel', on_delete=django.db.models.deletion.SET_NULL),),
                ('value', models.TextField(default='', blank=True, verbose_name='Form data'),),
                ('submitted', models.DateTimeField(auto_now_add=True, verbose_name='Submitted on'),)],
            options = {'verbose_name_plural': 'Form data', 'verbose_name': 'Form data'},
            name = 'FormModelData',
        ),
    ]

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.core.exceptions import ValidationError
from django.db import models
from django.forms import CheckboxSelectMultiple
from django.utils.text import capfirst

from dynamic_forms.conf import settings
from dynamic_forms.forms import MultiSelectFormField


class TextMultiSelectField(six.with_metaclass(models.SubfieldBase,
                                              models.TextField)):
    # http://djangosnippets.org/snippets/2753/

    widget = CheckboxSelectMultiple

    def __init__(self, *args, **kwargs):
        self.separate_values_by = kwargs.pop('separate_values_by', '\n')
        super(TextMultiSelectField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(TextMultiSelectField, self).contribute_to_class(cls, name)
        if self.choices:
            def _func(self, fieldname=name, choicedict=dict(self.choices)):
                return self.separate_values_by.join([
                    choicedict.get(value, value) for value in
                    getattr(self, fieldname)
                ])
            setattr(cls, 'get_%s_display' % self.name, _func)

    def formfield(self, **kwargs):
        # don't call super, as that overrides default widget if it has choices
        defaults = {
            'choices': self.choices,
            'help_text': self.help_text,
            'label': capfirst(self.verbose_name),
            'required': not self.blank,
            'separate_values_by': self.separate_values_by,
        }
        if self.has_default():
            defaults['initial'] = self.get_default()
        defaults.update(kwargs)
        defaults['widget'] = self.widget
        return MultiSelectFormField(**defaults)

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, six.string_types):
            return value
        elif isinstance(value, list):
            return self.separate_values_by.join(value)

    def get_choices_default(self):
        return self.get_choices(include_blank=False)

    def get_choices_selected(self, arr_choices=''):
        if not arr_choices:
            return False
        chces = []
        for choice_selected in arr_choices:
            chces.append(choice_selected[0])
        return chces

    def get_prep_value(self, value):
        return value

    def to_python(self, value):
        if value is not None:
            return (value if isinstance(value, list) else
                value.split(self.separate_values_by))
        return []

    def validate(self, value, model_instance):
        """
        :param callable convert: A callable to be applied for each choice
        """
        arr_choices = self.get_choices_selected(self.get_choices_default())
        for opt_select in value:
            if opt_select not in arr_choices:
                raise ValidationError(
                    self.error_messages['invalid_choice'] % value)
        return

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def get_internal_type(self):
        return "TextField"


if 'south' in settings.INSTALLED_APPS:  # pragma: no cover
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(patterns=['dynamic_forms\.fields'],
        rules=[((TextMultiSelectField,), [], {})])

########NEW FILE########
__FILENAME__ = formfields
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import re
import six

from django import forms
from django.utils.decorators import classonlymethod
from django.utils.encoding import python_2_unicode_compatible
from django.utils.importlib import import_module
from django.utils.translation import ugettext


def format_display_type(cls_name):
    if cls_name.endswith('Field'):
        cls_name = cls_name[:-5]  # Strip trailing 'Field'

    # Precedes each group of capital letters by a whitespace except first
    return re.sub(r'([A-Z]+)', r' \1', cls_name).lstrip()


def load_class_from_string(cls_string):
    mod, cls = cls_string.rsplit('.', 1)
    module = import_module(mod)
    return getattr(module, cls)


class DynamicFormFieldRegistry(object):

    def __init__(self):
        self._fields = {}

    def get(self, key):
        return self._fields.get(key, None)

    def get_as_choices(self):
        return sorted([(k, c.get_display_type()) for k, c in
                       six.iteritems(self._fields)], key=lambda x: x[1])

    def register(self, cls):
        if not issubclass(cls, BaseDynamicFormField):
            raise ValueError('%r must inherit from %r' % (
                cls, BaseDynamicFormField))
        key = '%s.%s' % (cls.__module__, cls.__name__)
        self._fields[key] = cls

    def unregister(self, key):
        if key in self._fields:
            del self._fields[key]


dynamic_form_field_registry = DynamicFormFieldRegistry()


def dynamic_form_field(cls):
    """
    A class decorator to register the class as a dynamic form field in the
    :class:`DynamicFormFieldRegistry`.
    """
    dynamic_form_field_registry.register(cls)
    return cls


class DFFMetaclass(type):

    def __new__(cls, name, bases, attrs):
        meta = attrs.pop('Meta', None)

        new_class = super(DFFMetaclass, cls).__new__(cls, name, bases, attrs)

        opts = {}
        super_opts = getattr(new_class, '_meta', {})
        if meta:
            excludes = getattr(meta, '_exclude', ())
            # Copy all attributes from super's options not excluded here. No
            # need to check for leading _ as this is already sorted out on the
            # super class
            for k, v in six.iteritems(super_opts):
                if k in excludes:
                    continue
                opts[k] = v
            # Copy all attributes not starting with a '_' from this Meta class
            for k, v in six.iteritems(meta.__dict__):
                if k.startswith('_') or k in excludes:
                    continue
                opts[k] = v
        else:
            opts = copy.deepcopy(super_opts)
        setattr(new_class, '_meta', opts)
        return new_class


@python_2_unicode_compatible
class BaseDynamicFormField(six.with_metaclass(DFFMetaclass)):

    cls = None
    display_type = None
    widget = None

    class Meta:
        help_text = [six.string_types, '', (forms.CharField, forms.Textarea)]
        required = [bool, True, forms.NullBooleanField]

    def __new__(cls, *args, **kwargs):
        self = super(BaseDynamicFormField, cls).__new__(cls)
        self._meta = copy.deepcopy(self.__class__._meta)
        return self

    def __init__(self, name, label, widget_attrs={}, **kwargs):
        self.name = name
        self.label = label
        self.widget_attrs = widget_attrs
        self.set_options(**kwargs)

    def __str__(self):
        if isinstance(self.cls, six.string_types):
            clsname = self.cls
        else:
            clsname = '%s.%s' % (self.cls.__module__, self.cls.__name__)
        return '<%(class)s, name=%(name)s, label=%(label)s>' % {
            'class': clsname,
            'name': self.name,
            'label': self.label,
        }

    def construct(self, **kwargs):
        if isinstance(self.cls, six.string_types):
            cls_type = load_class_from_string(self.cls)
        else:
            cls_type = self.cls

        f_kwargs = {}
        for key, val in six.iteritems(self.options):
            f_kwargs[key] = val[1]

        f_kwargs['label'] = self.label

        if self.widget is not None:
            if isinstance(self.widget, six.string_types):
                widget_type = load_class_from_string(self.widget)
            else:
                widget_type = self.widget
            f_kwargs['widget'] = widget_type(**self.get_widget_attrs())

        f_kwargs.update(kwargs)  # Update the field kwargs by those given

        return cls_type(**f_kwargs)

    def contribute_to_form(self, form):
        form.fields[self.name] = self.construct()

    @classonlymethod
    def get_display_type(cls):
        if cls.display_type:
            return cls.display_type
        return format_display_type(cls.__name__)

    @property
    def options(self):
        return self._meta

    def get_widget_attrs(self):
        return self.widget_attrs

    def set_options(self, **kwargs):
        for key, value in six.iteritems(kwargs):
            if not key in self.options:
                raise KeyError('%s is not a valid option.' % key)

            expected_type = self.options[key][0]
            if not isinstance(value, expected_type) and value is not None:
                raise TypeError('Neither of type %r nor None' % expected_type)

            self.options[key][1] = value
        self.options_valid()

    def options_valid(self):
        return True


@dynamic_form_field
class BooleanField(BaseDynamicFormField):

    cls = 'django.forms.BooleanField'
    display_type = ugettext('Boolean')

    class Meta:
        _exclude = ('required',)


@dynamic_form_field
class ChoiceField(BaseDynamicFormField):

    cls = 'django.forms.ChoiceField'
    display_type = ugettext('Choices')

    class Meta:
        choices = [six.string_types, '', (forms.CharField, forms.Textarea)]

    def construct(self, **kwargs):
        value = self.options.get('choices')[1]
        choices = [(row, row) for row in value.splitlines() if row]
        return super(ChoiceField, self).construct(choices=choices)

    def options_valid(self):
        if not self.options['choices'] or not self.options['choices'][1]:
            raise ValueError('choices must not be defined for %r' % self)
        return True


@dynamic_form_field
class DateField(BaseDynamicFormField):

    cls = 'django.forms.DateField'
    display_type = ugettext('Date')

    class Meta:
        localize = [bool, True, forms.NullBooleanField]


@dynamic_form_field
class DateTimeField(BaseDynamicFormField):

    cls = 'django.forms.DateTimeField'
    display_type = ugettext('Date and Time')

    class Meta:
        localize = [bool, True, forms.NullBooleanField]


@dynamic_form_field
class EmailField(BaseDynamicFormField):

    cls = 'django.forms.EmailField'
    display_type = ugettext('Email')


@dynamic_form_field
class IntegerField(BaseDynamicFormField):

    cls = 'django.forms.IntegerField'
    display_type = ugettext('Integer')

    class Meta:
        localize = [bool, True, forms.NullBooleanField]
        max_value = [int, None, forms.IntegerField]
        min_value = [int, None, forms.IntegerField]


@dynamic_form_field
class MultiLineTextField(BaseDynamicFormField):

    cls = 'django.forms.CharField'
    display_type = ugettext('Multi Line Text')
    widget = 'django.forms.widgets.Textarea'


@dynamic_form_field
class SingleLineTextField(BaseDynamicFormField):

    cls = 'django.forms.CharField'
    display_type = ugettext('Single Line Text')

    class Meta:
        max_length = [int, None, forms.IntegerField]
        min_length = [int, None, forms.IntegerField]


@dynamic_form_field
class TimeField(BaseDynamicFormField):

    cls = 'django.forms.TimeField'
    display_type = ugettext('Time')

    class Meta:
        localize = [bool, True, forms.NullBooleanField]

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from django.utils.datastructures import SortedDict as OrderedDict

from django import forms


class MultiSelectFormField(forms.MultipleChoiceField):
    # http://djangosnippets.org/snippets/2753/

    widget = forms.CheckboxSelectMultiple

    def __init__(self, *args, **kwargs):
        self.widget = kwargs.pop('widget', self.widget)
        self.separate_values_by = kwargs.pop('separate_values_by', ',')
        super(MultiSelectFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value and self.required:
            raise forms.ValidationError(self.error_messages['required'])
        return value

    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return value.split(self.separate_values_by)


class FormModelForm(forms.Form):

    def __init__(self, model, *args, **kwargs):
        self.model = model
        super(FormModelForm, self).__init__(*args, **kwargs)
        for field in self.model.fields.all():
            field.generate_form_field(self)

    def get_mapped_data(self, exclude_missing=False):
        """
        Returns an dictionary sorted by the position of the respective field
        in its form.

        :param boolean exclude_missing: If ``True``, non-filled fields (those
            whose value evaluates to ``False`` are not present in the returned
            dictionary. Default: ``False``
        """
        data = self.cleaned_data
        fields = self.model.get_fields_as_dict()
        mapped_data = OrderedDict()
        for key, name in six.iteritems(fields):
            value = data.get(key, None)
            if exclude_missing and not bool(value):
                continue
            mapped_data[name] = value
        return mapped_data

########NEW FILE########
__FILENAME__ = middlewares
# -*- coding: utf-8 -*-
from django.http import Http404

from dynamic_forms.conf import settings
from dynamic_forms.models import FormModel
from dynamic_forms.views import DynamicFormView, DynamicTemplateView


class FormModelMiddleware(object):

    def process_response(self, request, response):
        if response.status_code != 404:
            # Don't check for a form if another request succeeds
            return response
        try:
            path = request.path_info
            form_model = None
            try:
                form_model = FormModel.objects.get(submit_url=path)
                viewfunc = DynamicFormView.as_view()
            except FormModel.DoesNotExist:
                # success_url is not unique
                form_models = FormModel.objects.filter(success_url=path).all()
                if not form_models:
                    raise Http404
                form_model = form_models[0]
                viewfunc = DynamicTemplateView.as_view()

            new_resp = viewfunc(request, model=form_model)
            if hasattr(new_resp, 'render') and callable(new_resp.render):
                new_resp.render()
            return new_resp
        except Http404:
            # Return the original response if no form can be found
            return response
        except Exception as exc:
            if settings.DEBUG:
                raise exc
            # Return the original response if any error occurs
            return response

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'FormModel'
        db.create_table(u'dynamic_forms_formmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('submit_url', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('success_url', self.gf('django.db.models.fields.CharField')(default=u'', max_length=100, blank=True)),
            ('actions', self.gf('dynamic_forms.fields.TextMultiSelectField')(default=u'')),
            ('form_template', self.gf('django.db.models.fields.CharField')(default=u'dynamic_forms/form.html', max_length=100)),
            ('success_template', self.gf('django.db.models.fields.CharField')(default=u'dynamic_forms/form_success.html', max_length=100)),
        ))
        db.send_create_signal(u'dynamic_forms', ['FormModel'])

        # Adding model 'FormFieldModel'
        db.create_table(u'dynamic_forms_formfieldmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent_form', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'fields', to=orm['dynamic_forms.FormModel'])),
            ('field_type', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('name', self.gf('django.db.models.fields.SlugField')(max_length=50, blank=True)),
            ('_options', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('position', self.gf('django.db.models.fields.SmallIntegerField')(default=0, blank=True)),
        ))
        db.send_create_signal(u'dynamic_forms', ['FormFieldModel'])

        # Adding unique constraint on 'FormFieldModel', fields ['parent_form', 'name']
        db.create_unique(u'dynamic_forms_formfieldmodel', ['parent_form_id', 'name'])

        # Adding model 'FormModelData'
        db.create_table(u'dynamic_forms_formmodeldata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('form', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'data', null=True, on_delete=models.SET_NULL, to=orm['dynamic_forms.FormModel'])),
            ('value', self.gf('djorm_hstore.fields.DictionaryField')(default=u'', blank=True)),
            ('submitted', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'dynamic_forms', ['FormModelData'])


    def backwards(self, orm):
        # Removing unique constraint on 'FormFieldModel', fields ['parent_form', 'name']
        db.delete_unique(u'dynamic_forms_formfieldmodel', ['parent_form_id', 'name'])

        # Deleting model 'FormModel'
        db.delete_table(u'dynamic_forms_formmodel')

        # Deleting model 'FormFieldModel'
        db.delete_table(u'dynamic_forms_formfieldmodel')

        # Deleting model 'FormModelData'
        db.delete_table(u'dynamic_forms_formmodeldata')


    models = {
        u'dynamic_forms.formfieldmodel': {
            'Meta': {'ordering': "[u'parent_form', u'position']", 'unique_together': "((u'parent_form', u'name'),)", 'object_name': 'FormFieldModel'},
            '_options': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'field_type': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'blank': 'True'}),
            'parent_form': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'fields'", 'to': u"orm['dynamic_forms.FormModel']"}),
            'position': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'blank': 'True'})
        },
        u'dynamic_forms.formmodel': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'FormModel'},
            'actions': ('dynamic_forms.fields.TextMultiSelectField', [], {'default': "u''"}),
            'form_template': ('django.db.models.fields.CharField', [], {'default': "u'dynamic_forms/form.html'", 'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'submit_url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'success_template': ('django.db.models.fields.CharField', [], {'default': "u'dynamic_forms/form_success.html'", 'max_length': '100'}),
            'success_url': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '100', 'blank': 'True'})
        },
        u'dynamic_forms.formmodeldata': {
            'Meta': {'object_name': 'FormModelData'},
            'form': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'data'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['dynamic_forms.FormModel']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'submitted': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'value': ('djorm_hstore.fields.DictionaryField', [], {'default': "u''", 'blank': 'True'})
        }
    }

    complete_apps = ['dynamic_forms']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from django.utils.datastructures import SortedDict as OrderedDict

from django.db import models
from django.template.defaultfilters import slugify
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.html import escape, mark_safe
from django.utils.translation import ugettext as _

from djorm_hstore.fields import DictionaryField
from djorm_hstore.models import HStoreManager

from dynamic_forms.actions import action_registry
from dynamic_forms.fields import TextMultiSelectField
from dynamic_forms.formfields import dynamic_form_field_registry


@python_2_unicode_compatible
class FormModel(models.Model):
    name = models.CharField(_('Name'), max_length=50, unique=True)
    submit_url = models.CharField(_('Submit URL'), max_length=100, unique=True,
        help_text=mark_safe(_('The full URL path to the form. It should start '
            'and end with a forward slash (<code>/</code>).')))
    success_url = models.CharField(_('Success URL'), max_length=100,
        help_text=mark_safe(_('The full URL path where the user will be '
            'redirected after successfully sending the form. It should start '
            'and end with a forward slash (<code>/</code>). If empty, the '
            'success URL is generated by appending <code>done/</code> to the '
            '“Submit URL”.')), blank=True, default='')
    actions = TextMultiSelectField(_('Actions'), default='',
        choices=action_registry.get_as_choices())
    form_template = models.CharField(_('Form template path'), max_length=100,
        default='dynamic_forms/form.html')
    success_template = models.CharField(_('Success template path'),
        max_length=100, default='dynamic_forms/form_success.html')

    class Meta:
        ordering = ['name']
        verbose_name = _('Dynamic form')
        verbose_name_plural = _('Dynamic forms')

    def __str__(self):
        return self.name

    def get_fields_as_dict(self):
        return OrderedDict(self.fields.values_list('name', 'label').all())

    def save(self, *args, **kwargs):
        """
        Makes sure that the ``submit_url`` and -- if defined the
        ``success_url`` -- end with a forward slash (``'/'``).
        """
        if not self.submit_url.endswith('/'):
            self.submit_url = self.submit_url + '/'
        if self.success_url:
            if not self.success_url.endswith('/'):
                self.success_url = self.success_url + '/'
        else:
            self.success_url = self.submit_url + 'done/'
        return super(FormModel, self).save(*args, **kwargs)


@python_2_unicode_compatible
class FormFieldModel(models.Model):

    parent_form = models.ForeignKey(FormModel, on_delete=models.CASCADE,
        related_name='fields')
    field_type = models.CharField(_('Type'), max_length=255,
        choices=dynamic_form_field_registry.get_as_choices())
    label = models.CharField(_('Label'), max_length=20)
    name = models.SlugField(_('Name'), max_length=50, blank=True)
    _options = models.TextField(_('Options'), blank=True, null=True)
    position = models.SmallIntegerField(_('Position'), blank=True, default=0)

    class Meta:
        ordering = ['parent_form', 'position']
        unique_together = ("parent_form", "name",)
        verbose_name = _('Form field')
        verbose_name_plural = _('Form fields')

    def __str__(self):
        return _('Field “%(field_name)s” in form “%(form_name)s”') % {
            'field_name': self.label,
            'form_name': self.parent_form.name,
        }

    def generate_form_field(self, form):
        field_type_cls = dynamic_form_field_registry.get(self.field_type)
        field = field_type_cls(**self.get_form_field_kwargs())
        field.contribute_to_form(form)
        return field

    def get_form_field_kwargs(self):
        kwargs = self.options
        kwargs.update({
            'name': self.name,
            'label': self.label,
        })
        return kwargs

    @property
    def options(self):
        """Options passed to the form field during construction."""
        if not hasattr(self, '_options_cached'):
            self._options_cached = {}
            if self._options:
                try:
                    self._options_cached = json.loads(self._options)
                except ValueError:
                    pass
        return self._options_cached

    @options.setter
    def options(self, opts):
        if hasattr(self, '_options_cached'):
            del self._options_cached
        self._options = json.dumps(opts)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = slugify(self.label)

        given_options = self.options
        field_type_cls = dynamic_form_field_registry.get(self.field_type)
        invalid = set(self.options.keys()) - set(field_type_cls._meta.keys())
        if invalid:
            for key in invalid:
                del given_options[key]
            self.options = given_options

        return super(FormFieldModel, self).save(*args, **kwargs)


@python_2_unicode_compatible
class FormModelData(models.Model):
    form = models.ForeignKey(FormModel, on_delete=models.SET_NULL,
        related_name='data', null=True)
    value = DictionaryField(_('Form data'), blank=True, default='')
    submitted = models.DateTimeField(_('Submitted on'), auto_now_add=True)
    objects = HStoreManager()

    class Meta:
        verbose_name = _('Form data')
        verbose_name_plural = _('Form data')

    def __str__(self):
        return _('Form: “%(form)s” on %(date)s') % {
            'form': self.form,
            'date': self.submitted,
        }

    def pretty_value(self):
        try:
            data = json.loads(self.value)
            output = ['<dl>']
            for k, v in sorted(data.items()):
                output.append('<dt>%(key)s</dt><dd>%(value)s</dd>' % {
                    'key': escape(force_text(k)),
                    'value': escape(force_text(v)),
                })
            output.append('</dl>')
            return mark_safe(''.join(output))
        except ValueError:
            return self.value
    pretty_value.allow_tags = True

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from dynamic_forms.actions import action_registry
from dynamic_forms.forms import FormModelForm


class DynamicFormView(FormView):

    form_class = FormModelForm

    def dispatch(self, request, *args, **kwargs):
        # TODO: Django >1.4
        # self.form_model = self.kwargs.pop('model')

        return super(DynamicFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DynamicFormView, self).get_context_data(**kwargs)
        context.update({
            'model': self.form_model,
            'name': self.form_model.name,
            'submit_url': self.form_model.submit_url,
        })
        return context

    def get_form_kwargs(self):
        kwargs = super(DynamicFormView, self).get_form_kwargs()
        kwargs['model'] = self.form_model
        return kwargs

    def get_success_url(self):
        return self.form_model.success_url

    def get_template_names(self):
        return self.form_model.form_template

    def form_valid(self, form):
        for actionkey in self.form_model.actions:
            action = action_registry.get(actionkey)
            if action is None:
                continue
            action(self.form_model, form)
        messages.success(self.request,
            _('Thank you for submitting this form.'))
        return super(DynamicFormView, self).form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request,
            _('An error occurred during submitting this form.'))
        return super(DynamicFormView, self).form_invalid(form)

    # TODO: Django <1.5
    def get(self, request, *args, **kwargs):
        self.form_model = self.kwargs.pop('model')
        return super(DynamicFormView, self).get(request, *args, **kwargs)

    # TODO: Django <1.5
    def post(self, request, *args, **kwargs):
        self.form_model = self.kwargs.pop('model')
        return super(DynamicFormView, self).post(request, *args, **kwargs)


class DynamicTemplateView(TemplateView):

    def dispatch(self, request, *args, **kwargs):
        # TODO: Django >1.4
        # self.form_model = self.kwargs.pop('model')
        return super(DynamicTemplateView, self).dispatch(request, *args,
            **kwargs)

    def get_template_names(self):
        return self.form_model.success_template

    # TODO: Django <1.5
    def get(self, request, *args, **kwargs):
        self.form_model = self.kwargs.pop('model')
        return super(DynamicTemplateView, self).get(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = settings
import os
import urlparse
import dj_database_url

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Postgres FTW :)
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL', 'postgres://localhost/dynamic_forms')),
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
SECRET_KEY = '1#iw$j_-_0wck+us8p4adv-h5^swz_)%i2iqj3ys8$3d#p9#t('

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
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dynamic_forms.middlewares.FormModelMiddleware',
)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'dynamic_forms',
)

MIGRATION_MODULES = {
    'dynamic_forms': 'dynamic_forms.dj_migrations',
}

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

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

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
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import os.path
import django

RUNTESTS_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'dynamic_forms',
    'tests',
)

SECRET_KEY = 'test-secret-key'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'dynamic_forms.middlewares.FormModelMiddleware',
)

MIGRATION_MODULES = {
    'dynamic_forms': 'dynamic_forms.dj_migrations',
}

ROOT_URLCONF = 'tests.urls'

TEMPLATE_DIRS = (
    os.path.join(RUNTESTS_DIR, 'templates'),
)

if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'

########NEW FILE########
__FILENAME__ = test_actions
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

from copy import deepcopy

from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings

from dynamic_forms.actions import (action_registry, dynamic_form_send_email,
    dynamic_form_store_database)
from dynamic_forms.forms import FormModelForm
from dynamic_forms.models import FormFieldModel, FormModel, FormModelData


def some_action(model, form):
    pass


class TestActionRegistry(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.key1 = 'dynamic_forms.actions.dynamic_form_send_email'
        cls.key2 = 'dynamic_forms.actions.dynamic_form_store_database'
        cls.key3 = 'tests.test_actions.some_action'

        cls.action_registry_backup = deepcopy(action_registry)

    def tearDown(self):
        global action_registry
        action_registry = deepcopy(self.action_registry_backup)

    def test_default(self):
        self.assertEqual(action_registry._actions, {
            self.key1: dynamic_form_send_email,
            self.key2: dynamic_form_store_database,
        })

    def test_get_default_action(self):
        self.assertEqual(action_registry.get(self.key1),
            dynamic_form_send_email)
        self.assertEqual(action_registry.get(self.key2),
            dynamic_form_store_database)

    def test_get_default_actions_as_choices(self):
        self.assertEqual(action_registry.get_as_choices(), [
            (self.key1, 'Send via email'),
            (self.key2, 'Store in database')
        ])

    def test_register(self):
        action_registry.register(some_action, 'My Label')
        func = action_registry.get(self.key3)
        self.assertEqual(func, some_action)
        self.assertEqual(func.label, 'My Label')

    def test_register_not_callable(self):
        self.assertRaises(ValueError, action_registry.register,
            'not a callable', 'Label')

    def test_unregister(self):
        action_registry.register(some_action, 'My Label')
        action_registry.unregister(self.key3)

        self.assertIsNone(action_registry.get(self.key3))
        self.assertEqual(action_registry.get_as_choices(), [
            ('dynamic_forms.actions.dynamic_form_send_email',
                'Send via email'),
            ('dynamic_forms.actions.dynamic_form_store_database',
                'Store in database')
        ])

    def test_unregister_not_exists(self):
        action_registry.unregister('key-does-not-exist')


class TestActions(TestCase):

    def setUp(self):
        self.form_model = FormModel.objects.create(name='Form',
            submit_url='/form/', success_url='/form/done/')
        FormFieldModel.objects.create(parent_form=self.form_model, label='Str',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            position=1)
        FormFieldModel.objects.create(parent_form=self.form_model, label='DT',
            field_type='dynamic_forms.formfields.DateTimeField',
            position=2)
        self.form = FormModelForm(model=self.form_model, data={
            'str': 'Some string to store',
            'dt': datetime.datetime(2013, 8, 29, 12, 34, 56, 789000),
        })

    def test_store_database(self):
        self.assertTrue(self.form.is_valid())
        dynamic_form_store_database(self.form_model, self.form)
        self.assertEqual(FormModelData.objects.count(), 1)
        data = FormModelData.objects.get()
        self.assertEqual(
            data.value,
            '{"Str": "Some string to store", "DT": "2013-08-29T12:34:56.789"}'
        )

    @override_settings(DYNAMIC_FORMS_EMAIL_RECIPIENTS=['mail@example.com'])
    def test_send_email(self):
        self.assertTrue(self.form.is_valid())
        self.assertEqual(mail.outbox, [])
        dynamic_form_send_email(self.form_model, self.form)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Form “Form” submitted')
        self.assertEqual(message.body, '''Hello,

you receive this e-mail because someone submitted the form “Form”.

DT: Aug. 29, 2013, 12:34 p.m.
Str: Some string to store
''')
        self.assertEqual(message.recipients(), ['mail@example.com'])
        self.assertEqual(message.from_email, 'webmaster@localhost')

########NEW FILE########
__FILENAME__ = test_admin
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import VERSION
from django.contrib.auth.models import User
from django.test import TestCase
# TODO: Django >1.4:
# from django.utils.html import format_html, format_html_join
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from django.utils.translation import ugettext as _

from dynamic_forms.formfields import dynamic_form_field_registry as dffr
from dynamic_forms.models import FormModel, FormFieldModel, FormModelData


def get_fields_html():
    # TODO: Django >1.4:
    # reutrn format_html_join('\n', '<option value="{0}">{1}</option>',
    #     (df for df in dffr.get_as_choices()))
    return mark_safe(
        '\n'.join(
            '<option value="{0}">{1}</option>'.format(
                conditional_escape(df[0]),
                conditional_escape(df[1])
            )
            for df in dffr.get_as_choices()
        )
    )


class TestAdmin(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='admin',
            password='password', email='admin@localhost')
        self.client.login(username='admin', password='password')

    def tearDown(self):
        self.client.logout()

    def test_add_form(self):
        response = self.client.get('/admin/dynamic_forms/formmodel/add/')
        # TODO: Django >1.4: assertInHTML
        self.assertContains(response, '<input type="hidden" value="3" name="fields-TOTAL_FORMS" id="id_fields-TOTAL_FORMS">', count=1, html=True)
        self.assertContains(response, '<input type="hidden" value="0" name="fields-INITIAL_FORMS" id="id_fields-INITIAL_FORMS">', count=1, html=True)

        # 3 extra forms + 1 empty for construction
        # TODO: Django >1.4: assertInHTML
        if VERSION < (1, 7):
            self.assertContains(response, 'Form Field:', count=4, html=False)
        else:
            self.assertContains(response, 'Form field:', count=4, html=False)

        # 3 extra forms + 1 empty for construction
        # don't use html=True as we don't care about the <select>-Tag
        self.assertContains(response, get_fields_html(), count=4)

        # 3 extra forms + 1 empty for construction
        self.assertContains(response, _('The options for this field will be '
            'available once it has been stored the first time.'), count=4)

    def test_change(self):
        form = FormModel.objects.create(name='Form', submit_url='/some-form/')
        response = self.client.get('/admin/dynamic_forms/formmodel/%d/' % form.pk)
        # TODO: Django >1.4: assertInHTML
        self.assertContains(response, '<input type="hidden" value="3" name="fields-TOTAL_FORMS" id="id_fields-TOTAL_FORMS">', count=1, html=True)
        self.assertContains(response, '<input type="hidden" value="0" name="fields-INITIAL_FORMS" id="id_fields-INITIAL_FORMS">', count=1, html=True)

        # 3 extra forms + 1 empty for construction
        # TODO: Django >1.4: assertInHTML
        if VERSION < (1, 7):
            self.assertContains(response, 'Form Field:', count=4, html=False)
        else:
            self.assertContains(response, 'Form field:', count=4, html=False)

        # 3 extra forms + 1 empty for construction
        # don't use html=True as we don't care about the <select>-Tag
        self.assertContains(response, get_fields_html(), count=4)

        # 3 extra forms + 1 empty for construction
        self.assertContains(response, _('The options for this field will be '
            'available once it has been stored the first time.'), count=4)

    def test_add_and_change_post(self):
        data = {
            'name': 'Some Name',
            'submit_url': '/form/',
            'success_url': '/done/form/',
            'actions': 'dynamic_forms.actions.dynamic_form_send_email',
            'form_template': 'template1.html',
            'success_template': 'template2.html',

            'fields-TOTAL_FORMS': 1,
            'fields-INITIAL_FORMS': 0,
            'fields-MAX_NUM_FORMS': 1000,

            'fields-0-field_type': 'dynamic_forms.formfields.SingleLineTextField',
            'fields-0-label': 'String Field',
            'fields-0-name': 'string-field',
            'fields-0-position': 0,
            '_save': True,
        }
        response = self.client.post('/admin/dynamic_forms/formmodel/add/', data)
        self.assertRedirects(response, '/admin/dynamic_forms/formmodel/')
        self.assertEqual(FormModel.objects.all().count(), 1)
        self.assertEqual(FormFieldModel.objects.all().count(), 1)

        form_pk = FormModel.objects.get().pk
        field_pk = FormFieldModel.objects.get().pk

        data = {
            'name': 'Some Name',
            'submit_url': '/form/',
            'success_url': '/done/form/',
            'actions': 'dynamic_forms.actions.dynamic_form_send_email',
            'form_template': 'template1.html',
            'success_template': 'template2.html',

            'fields-TOTAL_FORMS': 1,
            'fields-INITIAL_FORMS': 1,
            'fields-MAX_NUM_FORMS': 1000,

            'fields-0-field_type': 'dynamic_forms.formfields.SingleLineTextField',
            'fields-0-label': 'String Field',
            'fields-0-name': 'string-field',
            'fields-0-position': 0,
            'fields-0-_options_0': 'Some help text',
            'fields-0-_options_1': 100,
            'fields-0-_options_2': 5,
            'fields-0-_options_3': 3,  # No
            'fields-0-id': field_pk,
            'fields-0-parent_form': form_pk,
            '_save': True,
        }
        response = self.client.post('/admin/dynamic_forms/formmodel/%d/' % form_pk, data)
        self.assertRedirects(response, '/admin/dynamic_forms/formmodel/')
        self.assertEqual(FormModel.objects.all().count(), 1)
        self.assertEqual(FormFieldModel.objects.all().count(), 1)

        options = FormFieldModel.objects.get().options
        self.assertEqual(options, {
            'min_length': 5, 
            'help_text': 'Some help text',
            'max_length': 100, 
            'required': False
        })

    def test_change_with_fields(self):
        form = FormModel.objects.create(name='Form', submit_url='/some-form/')
        ffb = FormFieldModel.objects.create(parent_form=form, label='B',
            field_type='dynamic_forms.formfields.BooleanField', position=0)
        ffb.options = {'help_text': 'Some help for boolean'}
        ffb.save()
        ffsl = FormFieldModel.objects.create(parent_form=form, label='SL',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            position=1)
        ffsl.options = {
            'help_text': 'Some help for single line',
            'required': False,
            'max_length': 100,
        }
        ffsl.save()
        ffd = FormFieldModel.objects.create(parent_form=form, label='D',
            field_type='dynamic_forms.formfields.DateField', position=2)
        ffd.options = {
            'localize': True,
        }
        ffd.save()

        response = self.client.get('/admin/dynamic_forms/formmodel/%d/' % form.pk)
        # TODO: Django >1.4: assertInHTML
        self.assertContains(response, '<input type="hidden" value="6" name="fields-TOTAL_FORMS" id="id_fields-TOTAL_FORMS">', count=1, html=True)
        self.assertContains(response, '<input type="hidden" value="3" name="fields-INITIAL_FORMS" id="id_fields-INITIAL_FORMS">', count=1, html=True)

        # 3 existing + 3 extra forms + 1 empty for construction
        # TODO: Django >1.4: assertInHTML
        if VERSION < (1, 7):
            self.assertContains(response, 'Form Field:', count=7, html=False)
        else:
            self.assertContains(response, 'Form field:', count=7, html=False)

        # 3 extra forms + 1 empty for construction
        # don't use html=True as we don't care about the <select>-Tag
        self.assertContains(response, get_fields_html(), count=4)

        # 3 extra forms + 1 empty for construction
        self.assertContains(response, _('The options for this field will be '
            'available once it has been stored the first time.'), count=4)

        # Boolean Field
        # TODO: Django >1.4: assertInHTML
        self.assertContains(response, '''
            <div>
                <label for="id_fields-0-_options_0"> Options:</label>
                <div style="display:inline-block;">
                    <label for="id_fields-0-_options_0">help_text:</label>
                        <textarea rows="10" name="fields-0-_options_0" id="id_fields-0-_options_0" cols="40">
                            Some help for boolean
                        </textarea>
                </div>
            </div>''', count=1, html=True)

        # Single Line Text Field
        # TODO: Django >1.4: assertInHTML
        self.assertContains(response, '''
            <div>
                <label for="id_fields-1-_options_0"> Options:</label>
                <div style="display:inline-block;">
                    <label for="id_fields-1-_options_0">help_text:</label>
                        <textarea rows="10" name="fields-1-_options_0" id="id_fields-1-_options_0" cols="40">
                            Some help for single line
                        </textarea><br>
                    <label for="id_fields-1-_options_1">max_length:</label>
                        <input type="text" name="fields-1-_options_1" id="id_fields-1-_options_1" value="100"><br>
                    <label for="id_fields-1-_options_2">min_length:</label>
                        <input type="text" name="fields-1-_options_2" id="id_fields-1-_options_2"><br>
                    <label for="id_fields-1-_options_3">required:</label>
                        <select name="fields-1-_options_3" id="id_fields-1-_options_3">
                            <option value="1">Unknown</option>
                            <option value="2">Yes</option>
                            <option selected="selected" value="3">No</option>
                        </select>
                </div>
            </div>''', count=1, html=True)

        # Date Field
        # TODO: Django >1.4: assertInHTML
        self.assertContains(response, '''
            <div>
                <label for="id_fields-2-_options_0"> Options:</label>
                <div style="display:inline-block;">
                    <label for="id_fields-2-_options_0">help_text:</label>
                        <textarea rows="10" name="fields-2-_options_0" id="id_fields-2-_options_0" cols="40">
                        </textarea><br>
                    <label for="id_fields-2-_options_1">localize:</label>
                        <select name="fields-2-_options_1" id="id_fields-2-_options_1">
                            <option value="1">Unknown</option>
                            <option selected="selected" value="2">Yes</option>
                            <option value="3">No</option>
                        </select><br>
                    <label for="id_fields-2-_options_2">required:</label>
                        <select name="fields-2-_options_2" id="id_fields-2-_options_2">
                            <option selected="selected" value="1">Unknown</option>
                            <option value="2">Yes</option>
                            <option value="3">No</option>
                        </select>
                </div>
            </div>''', count=1, html=True)

    def test_delete(self):
        form = FormModel.objects.create(name='Form', submit_url='/some-form/')
        FormFieldModel.objects.create(parent_form=form, label='SL',
            field_type='dynamic_forms.formfields.SingleLineTextField')

        FormModelData.objects.create(form=form, value='{"SL": "Some String"}')

        self.assertEqual(FormModel.objects.all().count(), 1)
        self.assertEqual(FormFieldModel.objects.all().count(), 1)
        self.assertEqual(FormModelData.objects.all().count(), 1)

        response = self.client.post('/admin/dynamic_forms/formmodel/%d/delete/' % form.pk, {'post': 'yes',})
        self.assertRedirects(response, '/admin/dynamic_forms/formmodel/')

        self.assertEqual(FormModel.objects.all().count(), 0)
        self.assertEqual(FormFieldModel.objects.all().count(), 0)
        self.assertEqual(FormModelData.objects.all().count(), 1)

########NEW FILE########
__FILENAME__ = test_formfields
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import six

from copy import deepcopy

from django import forms
from django.test import TestCase

from dynamic_forms.formfields import (dynamic_form_field_registry as registry,
    BaseDynamicFormField, BooleanField, ChoiceField, DateField, DateTimeField,
    EmailField, IntegerField, MultiLineTextField, SingleLineTextField,
    TimeField, format_display_type)


class CharField(BaseDynamicFormField):
    cls = forms.CharField


class Char2Field(BaseDynamicFormField):
    cls = 'django.forms.fields.CharField'


class MetaField(BaseDynamicFormField):
    cls = 'django.forms.fields.CharField'

    class Meta:
        _not_an_option = 'ignore in options'
        _exclude = ('help_text', 'required', 'pointless', '_exclude')
        max_length = [int, None, forms.IntegerField]
        pointless = [bool, True, forms.BooleanField]


class WidgetedField(BaseDynamicFormField):
    cls = 'django.forms.fields.CharField'
    widget = 'django.forms.widgets.Textarea'


class Widgeted2Field(BaseDynamicFormField):
    cls = forms.CharField
    widget = forms.Textarea


class NotAField(object):
    cls = 'django.forms.CharField'


class TestUtils(TestCase):

    def test_format_display_type(self):
        self.assertEqual(format_display_type('SomeClassField'), 'Some Class')
        self.assertEqual(format_display_type('SomeClass'), 'Some Class')
        self.assertEqual(format_display_type('SomeFOOClass'), 'Some FOOClass')


class TestDynamicFormFieldRegistry(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.key = 'dynamic_forms.formfields.%s'

        cls.names = ('BooleanField', 'ChoiceField', 'DateField',
            'DateTimeField', 'EmailField', 'IntegerField',
            'MultiLineTextField', 'SingleLineTextField', 'TimeField')

        cls.registry_backup = deepcopy(registry)

    def tearDown(self):
        global registry
        registry = deepcopy(self.registry_backup)

    def test_default(self):
        self.assertEqual(registry._fields, {
            self.key % 'BooleanField': BooleanField,
            self.key % 'ChoiceField': ChoiceField,
            self.key % 'DateField': DateField,
            self.key % 'DateTimeField': DateTimeField,
            self.key % 'EmailField': EmailField,
            self.key % 'IntegerField': IntegerField,
            self.key % 'MultiLineTextField': MultiLineTextField,
            self.key % 'SingleLineTextField': SingleLineTextField,
            self.key % 'TimeField': TimeField,
        })

    def test_get_default_action(self):
        self.assertEqual(registry.get(self.key % 'BooleanField'), BooleanField)
        self.assertEqual(registry.get(self.key % 'ChoiceField'), ChoiceField)

    def test_get_default_actions_as_choices(self):
        self.assertEqual(registry.get_as_choices(), [
            (self.key % 'BooleanField', 'Boolean'),
            (self.key % 'ChoiceField', 'Choices'),
            (self.key % 'DateField', 'Date'),
            (self.key % 'DateTimeField', 'Date and Time'),
            (self.key % 'EmailField', 'Email'),
            (self.key % 'IntegerField', 'Integer'),
            (self.key % 'MultiLineTextField', 'Multi Line Text'),
            (self.key % 'SingleLineTextField', 'Single Line Text'),
            (self.key % 'TimeField', 'Time'),
        ])

    def test_register(self):
        registry.register(CharField)
        cls = registry.get('tests.test_formfields.CharField')
        self.assertEqual(cls, CharField)
        self.assertEqual(cls.get_display_type(), 'Char')

    def test_register_not_inherit(self):
        self.assertRaises(ValueError, registry.register, NotAField)

    def test_unregister(self):
        key = 'tests.test_formfields.CharField'
        registry.register(CharField)
        registry.unregister(key)

        self.assertIsNone(registry.get(key))

    def test_unregister_not_exists(self):
        registry.unregister('key-does-not-exist')


class TestGenericDynamicFormFields(TestCase):

    def test_str(self):
        charfield = CharField('name', 'Label')
        self.assertEqual(six.text_type(charfield),
            '<django.forms.fields.CharField, name=name, label=Label>')

        charfield = Char2Field('name', 'Label')
        self.assertEqual(six.text_type(charfield),
            '<django.forms.fields.CharField, name=name, label=Label>')

    def test_construct_from_class(self):
        charfield = CharField('name', 'Label')
        formfield = charfield.construct()
        self.assertTrue(isinstance(formfield, forms.CharField))

    def test_construct_from_string(self):
        charfield = Char2Field('name', 'Label')
        formfield = charfield.construct()
        self.assertTrue(isinstance(formfield, forms.CharField))

    def test_construct_options(self):
        charfield = CharField('name', 'Label', required=False, 
            help_text='Some help')
        formfield = charfield.construct()
        self.assertFalse(formfield.required)
        self.assertEqual(formfield.help_text, 'Some help')

    def test_construct_widget(self):
        textfield1 = WidgetedField('name', 'label',
            widget_attrs={'attrs': {'rows': 10}})
        formfield1 = textfield1.construct()
        self.assertTrue(isinstance(formfield1.widget, forms.Textarea))

        textfield2 = Widgeted2Field('name', 'label',
            widget_attrs={'attrs': {'rows': 10}})
        formfield2 = textfield2.construct()
        self.assertTrue(isinstance(formfield2.widget, forms.Textarea))

    def test_options(self):
        metafield = MetaField('name', 'label')
        # This check implies, that neither Meta attributes starting with a _
        # not those part of the _exclude list are available
        self.assertEqual(metafield.options, {
            'max_length': [int, None, forms.IntegerField],
        })

    def test_options_invalid(self):
        self.assertRaises(KeyError, CharField, 'name', 'Label', something=123)
        self.assertRaises(KeyError, CharField, 'name', 'Label', something=123,
            required=True)

        self.assertRaises(TypeError, CharField, 'name', 'Label', required=123)
        self.assertRaises(TypeError, CharField, 'name', 'Label', help_text=42)


class TestChoiceField(TestCase):

    def test_options_valid(self):
        self.assertRaises(ValueError, ChoiceField, 'name', 'label')
        self.assertRaises(ValueError, ChoiceField, 'name', 'label',
            choices=None)

    def test_construct(self):
        # Empty rows are not treated as choices
        choices = """Lorem ipsum
dolor sit

amet equm"""
        dynamicfield = ChoiceField('name', 'Label', choices=choices)
        formfield = dynamicfield.construct()
        self.assertTrue(isinstance(formfield, forms.ChoiceField))
        self.assertEqual(formfield.choices, [('Lorem ipsum', 'Lorem ipsum'),
            ('dolor sit', 'dolor sit'), ('amet equm', 'amet equm')])

########NEW FILE########
__FILENAME__ = test_forms
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict


from django.contrib.auth.models import User
from django.test import TestCase

from dynamic_forms.forms import FormModelForm
from dynamic_forms.models import FormModel, FormFieldModel


class TestForms(TestCase):

    def test_generate_form_wo_data(self):
        fm = FormModel.objects.create(name='No data', submit_url='/form/')
        form = FormModelForm(model=fm)
        self.assertEqual(form.data, {})

    def test_generate_form_with_data(self):
        fm = FormModel.objects.create(name='With data', submit_url='/form/')
        data = {
            'afield': 'a value',
            'anotherfield': 'another value'
        }
        form = FormModelForm(model=fm, data=data)
        self.assertEqual(form.data, {
            'afield': 'a value',
            'anotherfield': 'another value'
        })

    def test_get_mapped_data(self):
        fm = FormModel.objects.create(name='Form', submit_url='/form/')
        FormFieldModel.objects.create(parent_form=fm, label='Label 1',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            position=3, _options='{"required": false}')
        FormFieldModel.objects.create(parent_form=fm, label='Label 2',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            position=1, _options='{"required": false}')
        FormFieldModel.objects.create(parent_form=fm, label='Label 3',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            position=2, _options='{"required": false}')
        data = {
            'label-1': 'Value 1',
            'label-2': 'Value 2',
        }
        form = FormModelForm(model=fm, data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_mapped_data(), OrderedDict([
            ('Label 2', 'Value 2',),
            ('Label 3', '',),
            ('Label 1', 'Value 1',),
        ]))
        self.assertEqual(form.get_mapped_data(exclude_missing=True),
            OrderedDict([
                ('Label 2', 'Value 2',),
                ('Label 1', 'Value 1',),
            ]
        ))

    def test_multi_select_form_field(self):
        data = {
            'name': 'Some Name',
            'submit_url': '/form/',
            'success_url': '/done/form/',
            'form_template': 'template1.html',
            'success_template': 'template2.html',

            'fields-TOTAL_FORMS': 0,
            'fields-INITIAL_FORMS': 0,
            'fields-MAX_NUM_FORMS': 1000,
            '_save': True,
        }
        self.user = User.objects.create_superuser(username='admin',
            password='password', email='admin@localhost')
        self.client.login(username='admin', password='password')

        response = self.client.post('/admin/dynamic_forms/formmodel/add/', data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<li>This field is required.</li>', count=1, html=True)

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import json
import six

from django import forms
from django.db.utils import IntegrityError
from django.test import TestCase

from dynamic_forms.models import FormFieldModel, FormModel, FormModelData


class TestModels(TestCase):

    def test_str(self):
        fm1 = FormModel.objects.create(name='Form 1', submit_url='/')
        self.assertEqual(six.text_type(fm1), 'Form 1')

    def test_unique_name(self):
        FormModel.objects.create(name='Form', submit_url='/')
        self.assertRaises(IntegrityError, FormModel.objects.create,
            name='Form', submit_url='/2/')

    def test_unique_submit_url(self):
        FormModel.objects.create(name='Form 1', submit_url='/')
        self.assertRaises(IntegrityError, FormModel.objects.create,
            name='Form 2', submit_url='/')

    def test_suplicate_success_url(self):
        FormModel.objects.create(name='Form 1', submit_url='/1/')
        FormModel.objects.create(name='Form 2', submit_url='/2/',
            success_url='/2/done/')

    def test_urls_no_trailing(self):
        fm1 = FormModel.objects.create(name='No Trailing 1',
            submit_url='/some/form', success_url='/some/form/send')
        self.assertEqual(fm1.submit_url, '/some/form/')
        self.assertEqual(fm1.success_url, '/some/form/send/')

        fm2 = FormModel.objects.create(name='No Trailing 2',
            submit_url='/some/form2')
        self.assertEqual(fm2.submit_url, '/some/form2/')
        self.assertEqual(fm2.success_url, '/some/form2/done/')

    def test_urls_trailing(self):
        fm1 = FormModel.objects.create(name='With Trailing 1',
            submit_url='/some/form/', success_url='/some/form/send/')
        self.assertEqual(fm1.submit_url, '/some/form/')
        self.assertEqual(fm1.success_url, '/some/form/send/')

        fm2 = FormModel.objects.create(name='With Trailing 2',
            submit_url='/some/form2/')
        self.assertEqual(fm2.submit_url, '/some/form2/')
        self.assertEqual(fm2.success_url, '/some/form2/done/')

    def test_get_fields_as_dict(self):
        fm = FormModel.objects.create(name='Form', submit_url='/form/')
        names = ('sapiente', 'nihil', 'quidem', 'earum', 'quod')
        labels = ('quo', 'adipisci', 'nesciunt', 'aspernatur', 'molestiae')
        for i, (name, label) in enumerate(six.moves.zip(names, labels), 1):
            FormFieldModel.objects.create(parent_form=fm, name=name,
                label=label, position=i,
                field_type='dynamic_forms.formfields.SingleLineTextField')
        self.assertEqual(
            list(fm.get_fields_as_dict().items()),
            list(six.moves.zip(names, labels))
        )


class TestFormFieldModel(TestCase):

    def setUp(self):
        self.form = FormModel.objects.create(name='Form', submit_url='/form/')

    def test_str(self):
        ff = FormFieldModel.objects.create(parent_form=self.form,
            field_type='dynamic_forms.formfields.SingleLineTextField',
            label='Field')
        self.assertEqual(six.text_type(ff), 'Field “Field” in form “Form”')

    def test_options_update(self):
        ff = FormFieldModel.objects.create(parent_form=self.form, label='F',
            field_type='dynamic_forms.formfields.SingleLineTextField')
        self.assertEqual(ff.options, {})

        opts = {'required': True}
        ff.options = opts
        self.assertEqual(ff.options, opts)

        opts = {'min_length': 10, 'max_length': 100}
        ff.options = opts
        self.assertEqual(ff.options, opts)

    def test_options_subsequent_get(self):
        ff = FormFieldModel.objects.create(parent_form=self.form, label='F',
            field_type='dynamic_forms.formfields.SingleLineTextField')
        self.assertEqual(ff.options, {})

        opts = {'required': True}
        ff.options = opts
        self.assertFalse(hasattr(ff, '_options_cached'))
        self.assertEqual(ff.options, opts)
        self.assertTrue(hasattr(ff, '_options_cached'))
        self.assertEqual(ff.options, opts)
        self.assertTrue(hasattr(ff, '_options_cached'))

        opts = {'min_length': 10, 'max_length': 100}
        ff.options = opts
        self.assertFalse(hasattr(ff, '_options_cached'))
        self.assertEqual(ff.options, opts)
        self.assertTrue(hasattr(ff, '_options_cached'))
        self.assertEqual(ff.options, opts)
        self.assertTrue(hasattr(ff, '_options_cached'))

    def test_options_subsequent_set(self):
        ff = FormFieldModel.objects.create(parent_form=self.form, label='F',
            field_type='dynamic_forms.formfields.SingleLineTextField')
        self.assertEqual(ff.options, {})

        opts = {'required': True}
        ff.options = opts
        self.assertFalse(hasattr(ff, '_options_cached'))

        opts = {'min_length': 10, 'max_length': 100}
        ff.options = opts
        self.assertFalse(hasattr(ff, '_options_cached'))

    def test_options_fallback_empty(self):
        ff1 = FormFieldModel.objects.create(parent_form=self.form, label='F1',
            field_type='dynamic_forms.formfields.SingleLineTextField')
        ff2 = FormFieldModel.objects.create(parent_form=self.form, label='F2',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            _options=None)
        ff3 = FormFieldModel.objects.create(parent_form=self.form, label='F3',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            _options='')
        ff4 = FormFieldModel.objects.create(parent_form=self.form, label='F4',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            _options='{}')
        ff5 = FormFieldModel.objects.create(parent_form=self.form, label='F5',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            _options='Something')
        self.assertEqual(ff1.options, {})
        self.assertEqual(ff2.options, {})
        self.assertEqual(ff3.options, {})
        self.assertEqual(ff4.options, {})
        self.assertEqual(ff5.options, {})

    def test_invalid_option(self):
        ff = FormFieldModel.objects.create(parent_form=self.form, label='F1',
            field_type='dynamic_forms.formfields.SingleLineTextField',
            _options='{"invalid_key": "invalid value"}')
        self.assertEqual(ff.options, {})

    def test_get_form_field_kwargs(self):
        ff = FormFieldModel(label='Label', name="my-label",
            field_type='dynamic_forms.formfields.SingleLineTextField')
        self.assertEqual(ff.get_form_field_kwargs(), {
            'label': 'Label',
            'name': 'my-label',
        })

        ff = FormFieldModel(label='Label', name="my-label",
            field_type='dynamic_forms.formfields.SingleLineTextField',
            _options='{"max_length": 123}')
        self.assertEqual(ff.get_form_field_kwargs(), {
            'label': 'Label',
            'max_length': 123,
            'name': 'my-label',
        })

        ff = FormFieldModel(label='Label', name="my-label",
            field_type='dynamic_forms.formfields.SingleLineTextField',
            _options='{"name": "some-name", "label": "some label", "a": "b"}')
        self.assertEqual(ff.get_form_field_kwargs(), {
            'a': 'b',
            'label': 'Label',
            'name': 'my-label',
        })

    def test_generate_form_field(self):
        form = forms.Form()
        ff1 = FormFieldModel(label='Label', name="my-label",
            field_type='dynamic_forms.formfields.SingleLineTextField')
        ff1.generate_form_field(form)
        ff2 = FormFieldModel(label='Label2', name="label2",
            field_type='dynamic_forms.formfields.BooleanField')
        ff2.generate_form_field(form)

        self.assertHTMLEqual(form.as_p(),
            '<p><label for="id_my-label">Label:</label> <input type="text" '
            'id="id_my-label" name="my-label" /></p>\n<p><label '
            'for="id_label2">Label2:</label> <input id="id_label2" '
            'name="label2" type="checkbox" /></p>')


class TestFormModelData(TestCase):

    def setUp(self):
        self.fm = FormModel.objects.create(name='Form', submit_url='/form/')

    def test_str(self):
        FormModelData.objects.create(form=self.fm, value={})
        fmd = FormModelData.objects.get()
        self.assertEqual(six.text_type(fmd), 'Form: “Form” on %s' % (
            fmd.submitted,))

    def test_submitted(self):
        now = datetime.datetime.now()
        past = now - datetime.timedelta(seconds=2)
        future = now + datetime.timedelta(seconds=2)
        FormModelData.objects.create(form=self.fm, value={})
        fmd = FormModelData.objects.get()
        self.assertLess(past, fmd.submitted)
        self.assertGreater(future, fmd.submitted)

    def test_pretty_value(self):
        data = json.dumps({
            'Some Key': 'Some value',
            'Another key': 'Another value',
            'Test': 'data',
        })
        fmd = FormModelData.objects.create(form=self.fm, value=data)
        self.assertEqual(fmd.pretty_value(), '<dl>'
            '<dt>Another key</dt><dd>Another value</dd>'
            '<dt>Some Key</dt><dd>Some value</dd>'
            '<dt>Test</dt><dd>data</dd>'
            '</dl>')

    def test_pretty_value_not_json(self):
        data = 'Some plain text value that is not JSON'
        fmd = FormModelData.objects.create(form=self.fm, value=data)
        self.assertEqual(fmd.pretty_value(), data)

########NEW FILE########
__FILENAME__ = test_views
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

try:
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict

from django.test import TestCase
from django.test.utils import override_settings
from django.utils.decorators import classonlymethod

from dynamic_forms.actions import action_registry
from dynamic_forms.forms import FormModelForm
from dynamic_forms.models import FormFieldModel, FormModel


class TestAction(object):

    calls = 0
    args = []

    __name__ = "TestAction"

    def __call__(self, form_model, form):
        TestAction.calls += 1
        TestAction.args.append((form_model, form))

    @classonlymethod
    def clear(cls):
        cls.calls = 0
        cls.args = []


class TestAction2(object):

    __name__ = "TestAction2"

    def __call__(self):
        pass



class TestViews(TestCase):

    def setUp(self):
        action_registry.register(TestAction(), 'Some action')
        action_registry.register(TestAction2(), 'Some action2')

        self.fm = FormModel.objects.create(name='Form', submit_url='/form/',
            success_url='/done/', actions=['tests.test_views.TestAction'],
            form_template='dynamic_forms/form.html',
            success_template='dynamic_forms/form_success.html')
        self.field1 = FormFieldModel.objects.create(parent_form=self.fm,
            field_type='dynamic_forms.formfields.SingleLineTextField',
            label='String Field', position=1)
        self.field2 = FormFieldModel.objects.create(parent_form=self.fm,
            field_type='dynamic_forms.formfields.BooleanField',
            label='Field for Boolean', position=2)
        self.field3 = FormFieldModel.objects.create(parent_form=self.fm,
            field_type='dynamic_forms.formfields.DateTimeField',
            label='Date and time', position=3)
        self.form = FormModelForm(model=self.fm)

    def tearDown(self):
        TestAction.clear()
        action_registry.unregister('tests.test_views.TestAction')
        action_registry.unregister('tests.test_views.TestAction2')

    def test_get_form(self):
        response = self.client.get('/form/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], FormModelForm)
        self.assertTemplateUsed(response, 'dynamic_forms/form.html')

    def test_post_form(self):
        response = self.client.post('/form/', {
            'string-field': 'Some submitted string',
            'field-for-boolean': True,
            'date-and-time': '2013-09-07 12:34:56'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/done/')
        self.assertEqual(TestAction.calls, 1)
        self.assertEqual(TestAction.args[0][0], self.fm)
        self.assertIsInstance(TestAction.args[0][1], FormModelForm)
        self.assertEqual(TestAction.args[0][1].get_mapped_data(), OrderedDict([
            ('String Field', 'Some submitted string',),
            ('Field for Boolean', True,),
            ('Date and time', datetime.datetime(2013, 9, 7, 12, 34, 56),),
        ]))

    def test_post_form_invalid_form(self):
        response = self.client.post('/form/', {
            'field-for-boolean': 'foo',
            'date-and-time': 'Hello world'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<li>This field is required.</li>',
            count=1, html=True)
        self.assertContains(response, '<li>Enter a valid date/time.</li>',
            count=1, html=True)
        self.assertEqual(TestAction.calls, 0)
        self.assertEqual(TestAction.args, [])

    def test_post_form_invalid_action(self):
        self.fm.actions = ['tests.test_views.TestAction', 'invalid.action']
        self.fm.save()
        response = self.client.post('/form/', {
            'string-field': 'Some submitted string',
            'field-for-boolean': True,
            'date-and-time': '2013-09-07 12:34:56'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/done/')
        self.assertEqual(TestAction.calls, 1)
        self.assertEqual(TestAction.args[0][0], self.fm)
        self.assertIsInstance(TestAction.args[0][1], FormModelForm)
        self.assertEqual(TestAction.args[0][1].get_mapped_data(), OrderedDict([
            ('String Field', 'Some submitted string',),
            ('Field for Boolean', True,),
            ('Date and time', datetime.datetime(2013, 9, 7, 12, 34, 56),),
        ]))

    def test_get_done(self):
        response = self.client.get('/done/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dynamic_forms/form_success.html')

    def test_form_not_found(self):
        response = self.client.get('/form/does/not/exist/')
        self.assertEqual(response.status_code, 404)

    def test_form_error(self):
        self.fm.actions = ['tests.test_views.TestAction2']
        self.fm.save()
        response = self.client.post('/form/', {
            'string-field': 'Some submitted string',
            'field-for-boolean': True,
            'date-and-time': '2013-09-07 12:34:56'
        })
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=True)
    def test_form_error_debug(self):
        self.fm.actions = ['tests.test_views.TestAction2']
        self.fm.save()
        self.assertRaises(TypeError, self.client.post, '/form/', {
            'string-field': 'Some submitted string',
            'field-for-boolean': True,
            'date-and-time': '2013-09-07 12:34:56'
        })

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
