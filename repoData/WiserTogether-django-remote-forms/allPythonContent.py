__FILENAME__ = fields
import datetime

from django.conf import settings
from django.utils.datastructures import SortedDict

from django_remote_forms import logger, widgets


class RemoteField(object):
    """
    A base object for being able to return a Django Form Field as a Python
    dictionary.

    This object also takes into account if there is initial data for the field
    coming in from the form directly, which overrides any initial data
    specified on the field per Django's rules:

    https://docs.djangoproject.com/en/dev/ref/forms/api/#dynamic-initial-values
    """

    def __init__(self, field, form_initial_data=None, field_name=None):
        self.field_name = field_name
        self.field = field
        self.form_initial_data = form_initial_data

    def as_dict(self):
        field_dict = SortedDict()
        field_dict['title'] = self.field.__class__.__name__
        field_dict['required'] = self.field.required
        field_dict['label'] = self.field.label
        field_dict['initial'] = self.form_initial_data or self.field.initial
        field_dict['help_text'] = self.field.help_text

        field_dict['error_messages'] = self.field.error_messages

        # Instantiate the Remote Forms equivalent of the widget if possible
        # in order to retrieve the widget contents as a dictionary.
        remote_widget_class_name = 'Remote%s' % self.field.widget.__class__.__name__
        try:
            remote_widget_class = getattr(widgets, remote_widget_class_name)
            remote_widget = remote_widget_class(self.field.widget, field_name=self.field_name)
        except Exception, e:
            logger.warning('Error serializing %s: %s', remote_widget_class_name, str(e))
            widget_dict = {}
        else:
            widget_dict = remote_widget.as_dict()

        field_dict['widget'] = widget_dict

        return field_dict


class RemoteCharField(RemoteField):
    def as_dict(self):
        field_dict = super(RemoteCharField, self).as_dict()

        field_dict.update({
            'max_length': self.field.max_length,
            'min_length': self.field.min_length
        })

        return field_dict


class RemoteIntegerField(RemoteField):
    def as_dict(self):
        field_dict = super(RemoteIntegerField, self).as_dict()

        field_dict.update({
            'max_value': self.field.max_value,
            'min_value': self.field.min_value
        })

        return field_dict


class RemoteFloatField(RemoteIntegerField):
    def as_dict(self):
        return super(RemoteFloatField, self).as_dict()


class RemoteDecimalField(RemoteIntegerField):
    def as_dict(self):
        field_dict = super(RemoteDecimalField, self).as_dict()

        field_dict.update({
            'max_digits': self.field.max_digits,
            'decimal_places': self.field.decimal_places
        })

        return field_dict


class RemoteTimeField(RemoteField):
    def as_dict(self):
        field_dict = super(RemoteTimeField, self).as_dict()

        field_dict['input_formats'] = self.field.input_formats

        if (field_dict['initial']):
            if callable(field_dict['initial']):
                field_dict['initial'] = field_dict['initial']()

            # If initial value is datetime then convert it using first available input format
            if (isinstance(field_dict['initial'], (datetime.datetime, datetime.time, datetime.date))):
                if not len(field_dict['input_formats']):
                    if isinstance(field_dict['initial'], datetime.date):
                        field_dict['input_formats'] = settings.DATE_INPUT_FORMATS
                    elif isinstance(field_dict['initial'], datetime.time):
                        field_dict['input_formats'] = settings.TIME_INPUT_FORMATS
                    elif isinstance(field_dict['initial'], datetime.datetime):
                        field_dict['input_formats'] = settings.DATETIME_INPUT_FORMATS

                input_format = field_dict['input_formats'][0]
                field_dict['initial'] = field_dict['initial'].strftime(input_format)

        return field_dict


class RemoteDateField(RemoteTimeField):
    def as_dict(self):
        return super(RemoteDateField, self).as_dict()


class RemoteDateTimeField(RemoteTimeField):
    def as_dict(self):
        return super(RemoteDateTimeField, self).as_dict()


class RemoteRegexField(RemoteCharField):
    def as_dict(self):
        field_dict = super(RemoteRegexField, self).as_dict()

        # We don't need the pattern object in the frontend
        # field_dict['regex'] = self.field.regex

        return field_dict


class RemoteEmailField(RemoteCharField):
    def as_dict(self):
        return super(RemoteEmailField, self).as_dict()


class RemoteFileField(RemoteField):
    def as_dict(self):
        field_dict = super(RemoteFileField, self).as_dict()

        field_dict['max_length'] = self.field.max_length

        return field_dict


class RemoteImageField(RemoteFileField):
    def as_dict(self):
        return super(RemoteImageField, self).as_dict()


class RemoteURLField(RemoteCharField):
    def as_dict(self):
        return super(RemoteURLField, self).as_dict()


class RemoteBooleanField(RemoteField):
    def as_dict(self):
        return super(RemoteBooleanField, self).as_dict()


class RemoteNullBooleanField(RemoteBooleanField):
    def as_dict(self):
        return super(RemoteNullBooleanField, self).as_dict()


class RemoteChoiceField(RemoteField):
    def as_dict(self):
        field_dict = super(RemoteChoiceField, self).as_dict()

        field_dict['choices'] = []
        for key, value in self.field.choices:
            field_dict['choices'].append({
                'value': key,
                'display': value
            })

        return field_dict


class RemoteModelChoiceField(RemoteChoiceField):
    def as_dict(self):
        return super(RemoteModelChoiceField, self).as_dict()


class RemoteTypedChoiceField(RemoteChoiceField):
    def as_dict(self):
        field_dict = super(RemoteTypedChoiceField, self).as_dict()

        field_dict.update({
            'coerce': self.field.coerce,
            'empty_value': self.field.empty_value
        })

        return field_dict


class RemoteMultipleChoiceField(RemoteChoiceField):
    def as_dict(self):
        return super(RemoteMultipleChoiceField, self).as_dict()


class RemoteModelMultipleChoiceField(RemoteMultipleChoiceField):
    def as_dict(self):
        return super(RemoteModelMultipleChoiceField, self).as_dict()


class RemoteTypedMultipleChoiceField(RemoteMultipleChoiceField):
    def as_dict(self):
        field_dict = super(RemoteTypedMultipleChoiceField, self).as_dict()

        field_dict.update({
            'coerce': self.field.coerce,
            'empty_value': self.field.empty_value
        })

        return field_dict


class RemoteComboField(RemoteField):
    def as_dict(self):
        field_dict = super(RemoteComboField, self).as_dict()

        field_dict.update(fields=self.field.fields)

        return field_dict


class RemoteMultiValueField(RemoteField):
    def as_dict(self):
        field_dict = super(RemoteMultiValueField, self).as_dict()

        field_dict['fields'] = self.field.fields

        return field_dict


class RemoteFilePathField(RemoteChoiceField):
    def as_dict(self):
        field_dict = super(RemoteFilePathField, self).as_dict()

        field_dict.update({
            'path': self.field.path,
            'match': self.field.match,
            'recursive': self.field.recursive
        })

        return field_dict


class RemoteSplitDateTimeField(RemoteMultiValueField):
    def as_dict(self):
        field_dict = super(RemoteSplitDateTimeField, self).as_dict()

        field_dict.update({
            'input_date_formats': self.field.input_date_formats,
            'input_time_formats': self.field.input_time_formats
        })

        return field_dict


class RemoteIPAddressField(RemoteCharField):
    def as_dict(self):
        return super(RemoteIPAddressField, self).as_dict()


class RemoteSlugField(RemoteCharField):
    def as_dict(self):
        return super(RemoteSlugField, self).as_dict()

########NEW FILE########
__FILENAME__ = forms
from django.utils.datastructures import SortedDict

from django_remote_forms import fields, logger
from django_remote_forms.utils import resolve_promise


class RemoteForm(object):
    def __init__(self, form, *args, **kwargs):
        self.form = form

        self.all_fields = set(self.form.fields.keys())

        self.excluded_fields = set(kwargs.pop('exclude', []))
        self.included_fields = set(kwargs.pop('include', []))
        self.readonly_fields = set(kwargs.pop('readonly', []))
        self.ordered_fields = kwargs.pop('ordering', [])

        self.fieldsets = kwargs.pop('fieldsets', {})

        # Make sure all passed field lists are valid
        if self.excluded_fields and not (self.all_fields >= self.excluded_fields):
            logger.warning('Excluded fields %s are not present in form fields' % (self.excluded_fields - self.all_fields))
            self.excluded_fields = set()

        if self.included_fields and not (self.all_fields >= self.included_fields):
            logger.warning('Included fields %s are not present in form fields' % (self.included_fields - self.all_fields))
            self.included_fields = set()

        if self.readonly_fields and not (self.all_fields >= self.readonly_fields):
            logger.warning('Readonly fields %s are not present in form fields' % (self.readonly_fields - self.all_fields))
            self.readonly_fields = set()

        if self.ordered_fields and not (self.all_fields >= set(self.ordered_fields)):
            logger.warning('Readonly fields %s are not present in form fields' % (set(self.ordered_fields) - self.all_fields))
            self.ordered_fields = []

        if self.included_fields | self.excluded_fields:
            logger.warning('Included and excluded fields have following fields %s in common' % (set(self.ordered_fields) - self.all_fields))
            self.excluded_fields = set()
            self.included_fields = set()

        # Extend exclude list from include list
        self.excluded_fields |= (self.included_fields - self.all_fields)

        if not self.ordered_fields:
            if self.form.fields.keyOrder:
                self.ordered_fields = self.form.fields.keyOrder
            else:
                self.ordered_fields = self.form.fields.keys()

        self.fields = []

        # Construct ordered field list considering exclusions
        for field_name in self.ordered_fields:
            if field_name in self.excluded_fields:
                continue

            self.fields.append(field_name)

        # Validate fieldset
        fieldset_fields = set()
        if self.fieldsets:
            for fieldset_name, fieldsets_data in self.fieldsets:
                if 'fields' in fieldsets_data:
                    fieldset_fields |= set(fieldsets_data['fields'])

        if not (self.all_fields >= fieldset_fields):
            logger.warning('Following fieldset fields are invalid %s' % (fieldset_fields - self.all_fields))
            self.fieldsets = {}

        if not (set(self.fields) >= fieldset_fields):
            logger.warning('Following fieldset fields are excluded %s' % (fieldset_fields - set(self.fields)))
            self.fieldsets = {}

    def as_dict(self):
        """
        Returns a form as a dictionary that looks like the following:

        form = {
            'non_field_errors': [],
            'label_suffix': ':',
            'is_bound': False,
            'prefix': 'text'.
            'fields': {
                'name': {
                    'type': 'type',
                    'errors': {},
                    'help_text': 'text',
                    'label': 'text',
                    'initial': 'data',
                    'max_length': 'number',
                    'min_length: 'number',
                    'required': False,
                    'bound_data': 'data'
                    'widget': {
                        'attr': 'value'
                    }
                }
            }
        }
        """
        form_dict = SortedDict()
        form_dict['title'] = self.form.__class__.__name__
        form_dict['non_field_errors'] = self.form.non_field_errors()
        form_dict['label_suffix'] = self.form.label_suffix
        form_dict['is_bound'] = self.form.is_bound
        form_dict['prefix'] = self.form.prefix
        form_dict['fields'] = SortedDict()
        form_dict['errors'] = self.form.errors
        form_dict['fieldsets'] = getattr(self.form, 'fieldsets', [])

        # If there are no fieldsets, specify order
        form_dict['ordered_fields'] = self.fields

        initial_data = {}

        for name, field in [(x, self.form.fields[x]) for x in self.fields]:
            # Retrieve the initial data from the form itself if it exists so
            # that we properly handle which initial data should be returned in
            # the dictionary.

            # Please refer to the Django Form API documentation for details on
            # why this is necessary:
            # https://docs.djangoproject.com/en/dev/ref/forms/api/#dynamic-initial-values
            form_initial_field_data = self.form.initial.get(name)

            # Instantiate the Remote Forms equivalent of the field if possible
            # in order to retrieve the field contents as a dictionary.
            remote_field_class_name = 'Remote%s' % field.__class__.__name__
            try:
                remote_field_class = getattr(fields, remote_field_class_name)
                remote_field = remote_field_class(field, form_initial_field_data, field_name=name)
            except Exception, e:
                logger.warning('Error serializing field %s: %s', remote_field_class_name, str(e))
                field_dict = {}
            else:
                field_dict = remote_field.as_dict()

            if name in self.readonly_fields:
                field_dict['readonly'] = True

            form_dict['fields'][name] = field_dict

            # Load the initial data, which is a conglomerate of form initial and field initial
            if 'initial' not in form_dict['fields'][name]:
                form_dict['fields'][name]['initial'] = None

            initial_data[name] = form_dict['fields'][name]['initial']

        if self.form.data:
            form_dict['data'] = self.form.data
        else:
            form_dict['data'] = initial_data

        return resolve_promise(form_dict)

########NEW FILE########
__FILENAME__ = utils
from django.utils.functional import Promise
from django.utils.encoding import force_unicode


def resolve_promise(o):
    if isinstance(o, dict):
        for k, v in o.items():
            o[k] = resolve_promise(v)
    elif isinstance(o, (list, tuple)):
        o = [resolve_promise(x) for x in o]
    elif isinstance(o, Promise):
        try:
            o = force_unicode(o)
        except:
            # Item could be a lazy tuple or list
            try:
                o = [resolve_promise(x) for x in o]
            except:
                raise Exception('Unable to resolve lazy object %s' % o)
    elif callable(o):
        o = o()

    return o

########NEW FILE########
__FILENAME__ = widgets
import datetime

from django.utils.dates import MONTHS
from django.utils.datastructures import SortedDict


class RemoteWidget(object):
    def __init__(self, widget, field_name=None):
        self.field_name = field_name
        self.widget = widget

    def as_dict(self):
        widget_dict = SortedDict()
        widget_dict['title'] = self.widget.__class__.__name__
        widget_dict['is_hidden'] = self.widget.is_hidden
        widget_dict['needs_multipart_form'] = self.widget.needs_multipart_form
        widget_dict['is_localized'] = self.widget.is_localized
        widget_dict['is_required'] = self.widget.is_required
        widget_dict['attrs'] = self.widget.attrs

        return widget_dict


class RemoteInput(RemoteWidget):
    def as_dict(self):
        widget_dict = super(RemoteInput, self).as_dict()

        widget_dict['input_type'] = self.widget.input_type

        return widget_dict


class RemoteTextInput(RemoteInput):
    def as_dict(self):
        return super(RemoteTextInput, self).as_dict()


class RemotePasswordInput(RemoteInput):
    def as_dict(self):
        return super(RemotePasswordInput, self).as_dict()


class RemoteHiddenInput(RemoteInput):
    def as_dict(self):
        return super(RemoteHiddenInput, self).as_dict()


class RemoteEmailInput(RemoteInput):
    def as_dict(self):
        widget_dict = super(RemoteEmailInput, self).as_dict()

        widget_dict['title'] = 'TextInput'
        widget_dict['input_type'] = 'text'

        return widget_dict


class RemoteNumberInput(RemoteInput):
    def as_dict(self):
        widget_dict = super(RemoteNumberInput, self).as_dict()

        widget_dict['title'] = 'TextInput'
        widget_dict['input_type'] = 'text'

        return widget_dict


class RemoteURLInput(RemoteInput):
    def as_dict(self):
        widget_dict = super(RemoteURLInput, self).as_dict()

        widget_dict['title'] = 'TextInput'
        widget_dict['input_type'] = 'text'

        return widget_dict


class RemoteMultipleHiddenInput(RemoteHiddenInput):
    def as_dict(self):
        widget_dict = super(RemoteMultipleHiddenInput, self).as_dict()

        widget_dict['choices'] = self.widget.choices

        return widget_dict


class RemoteFileInput(RemoteInput):
    def as_dict(self):
        return super(RemoteFileInput, self).as_dict()


class RemoteClearableFileInput(RemoteFileInput):
    def as_dict(self):
        widget_dict = super(RemoteClearableFileInput, self).as_dict()

        widget_dict['initial_text'] = self.widget.initial_text
        widget_dict['input_text'] = self.widget.input_text
        widget_dict['clear_checkbox_label'] = self.widget.clear_checkbox_label

        return widget_dict


class RemoteTextarea(RemoteWidget):
    def as_dict(self):
        widget_dict = super(RemoteTextarea, self).as_dict()
        widget_dict['input_type'] = 'textarea'
        return widget_dict


class RemoteTimeInput(RemoteInput):
    def as_dict(self):
        widget_dict = super(RemoteTimeInput, self).as_dict()

        widget_dict['format'] = self.widget.format
        widget_dict['manual_format'] = self.widget.manual_format
        widget_dict['date'] = self.widget.manual_format
        widget_dict['input_type'] = 'time'

        return widget_dict


class RemoteDateInput(RemoteTimeInput):
    def as_dict(self):
        widget_dict = super(RemoteDateInput, self).as_dict()

        widget_dict['input_type'] = 'date'

        current_year = datetime.datetime.now().year
        widget_dict['choices'] = [{
            'title': 'day',
            'data': [{'key': x, 'value': x} for x in range(1, 32)]
        }, {
            'title': 'month',
            'data': [{'key': x, 'value': y} for (x, y) in MONTHS.items()]
        }, {
            'title': 'year',
            'data': [{'key': x, 'value': x} for x in range(current_year - 100, current_year + 1)]
        }]

        return widget_dict


class RemoteDateTimeInput(RemoteTimeInput):
    def as_dict(self):
        widget_dict = super(RemoteDateTimeInput, self).as_dict()

        widget_dict['input_type'] = 'datetime'

        return widget_dict


class RemoteCheckboxInput(RemoteWidget):
    def as_dict(self):
        widget_dict = super(RemoteCheckboxInput, self).as_dict()

        # If check test is None then the input should accept null values
        check_test = None
        if self.widget.check_test is not None:
            check_test = True

        widget_dict['check_test'] = check_test
        widget_dict['input_type'] = 'checkbox'

        return widget_dict


class RemoteSelect(RemoteWidget):
    def as_dict(self):
        widget_dict = super(RemoteSelect, self).as_dict()

        widget_dict['choices'] = []
        for key, value in self.widget.choices:
            widget_dict['choices'].append({
                'value': key,
                'display': value
            })

        widget_dict['input_type'] = 'select'

        return widget_dict


class RemoteNullBooleanSelect(RemoteSelect):
    def as_dict(self):
        return super(RemoteNullBooleanSelect, self).as_dict()


class RemoteSelectMultiple(RemoteSelect):
    def as_dict(self):
        widget_dict = super(RemoteSelectMultiple, self).as_dict()

        widget_dict['input_type'] = 'selectmultiple'
        widget_dict['size'] = len(widget_dict['choices'])

        return widget_dict


class RemoteRadioInput(RemoteWidget):
    def as_dict(self):
        widget_dict = SortedDict()
        widget_dict['title'] = self.widget.__class__.__name__
        widget_dict['name'] = self.widget.name
        widget_dict['value'] = self.widget.value
        widget_dict['attrs'] = self.widget.attrs
        widget_dict['choice_value'] = self.widget.choice_value
        widget_dict['choice_label'] = self.widget.choice_label
        widget_dict['index'] = self.widget.index
        widget_dict['input_type'] = 'radio'

        return widget_dict


class RemoteRadioFieldRenderer(RemoteWidget):
    def as_dict(self):
        widget_dict = SortedDict()
        widget_dict['title'] = self.widget.__class__.__name__
        widget_dict['name'] = self.widget.name
        widget_dict['value'] = self.widget.value
        widget_dict['attrs'] = self.widget.attrs
        widget_dict['choices'] = self.widget.choices
        widget_dict['input_type'] = 'radio'

        return widget_dict


class RemoteRadioSelect(RemoteSelect):
    def as_dict(self):
        widget_dict = super(RemoteRadioSelect, self).as_dict()

        widget_dict['choices'] = []
        for key, value in self.widget.choices:
            widget_dict['choices'].append({
                'name': self.field_name or '',
                'value': key,
                'display': value
            })

        widget_dict['input_type'] = 'radio'

        return widget_dict


class RemoteCheckboxSelectMultiple(RemoteSelectMultiple):
    def as_dict(self):
        return super(RemoteCheckboxSelectMultiple, self).as_dict()


class RemoteMultiWidget(RemoteWidget):
    def as_dict(self):
        widget_dict = super(RemoteMultiWidget, self).as_dict()

        widget_list = []
        for widget in self.widget.widgets:
            # Fetch remote widget and convert to dict
            widget_list.append()

        widget_dict['widgets'] = widget_list

        return widget_dict


class RemoteSplitDateTimeWidget(RemoteMultiWidget):
    def as_dict(self):
        widget_dict = super(RemoteSplitDateTimeWidget, self).as_dict()

        widget_dict['date_format'] = self.widget.date_format
        widget_dict['time_format'] = self.widget.time_format

        return widget_dict


class RemoteSplitHiddenDateTimeWidget(RemoteSplitDateTimeWidget):
    def as_dict(self):
        return super(RemoteSplitHiddenDateTimeWidget, self).as_dict()

########NEW FILE########
