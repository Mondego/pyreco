__FILENAME__ = admin
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django import forms

from .fields import ClearableFileField


class ClearableFileFieldsAdmin(admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super(ClearableFileFieldsAdmin, self).formfield_for_dbfield(
            db_field, **kwargs)
        if isinstance(field, forms.FileField):
            field = ClearableFileField(field)
        return field

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.utils.encoding import python_2_unicode_compatible
from django.utils import six

from .widgets import ClearableFileInput


@python_2_unicode_compatible
class FakeEmptyFieldFile(object):
    """
    A fake FieldFile that will convice a FileField model field to
    actually replace an existing file name with an empty string.

    FileField.save_form_data only overwrites its instance data if the
    incoming form data evaluates to True in a boolean context (because
    an empty file input is assumed to mean "no change"). We want to be
    able to clear it without requiring the use of a model FileField
    subclass (keeping things at the form level only). In order to do
    this we need our form field to return a value that evaluates to
    True in a boolean context, but to the empty string when coerced to
    unicode. This object fulfills that requirement.

    It also needs the _committed attribute to satisfy the test in
    FileField.pre_save.

    This is, of course, hacky and fragile, and depends on internal
    knowledge of the FileField and FieldFile classes. But it will
    serve until Django FileFields acquire a native ability to be
    cleared (ticket 7048).

    """
    def __str__(self):
        return six.text_type('')
    _committed = True


class ClearableFileField(forms.MultiValueField):
    default_file_field_class = forms.FileField
    widget = ClearableFileInput

    def __init__(self, file_field=None, template=None, *args, **kwargs):
        file_field = file_field or self.default_file_field_class(*args,
                                                                 **kwargs)
        fields = (file_field, forms.BooleanField(required=False))
        kwargs['required'] = file_field.required
        kwargs['widget'] = self.widget(file_widget=file_field.widget,
                                       template=template)
        super(ClearableFileField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list[1] and not data_list[0]:
            return FakeEmptyFieldFile()
        return data_list[0]


class ClearableImageField(ClearableFileField):
    default_file_field_class = forms.ImageField

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
"""
forms for django-form-utils

Time-stamp: <2010-04-28 02:57:16 carljm forms.py>

"""
from __future__ import unicode_literals
from copy import deepcopy

from django import forms
from django.forms.util import flatatt, ErrorDict
from django.utils import six
from django.utils.safestring import mark_safe


class Fieldset(object):
    """An iterable Fieldset with a legend and a set of BoundFields."""
    def __init__(self, form, name, boundfields, legend='', classes='',
                 description=''):
        self.form = form
        self.boundfields = boundfields
        if legend is None:
            legend = name
        self.legend = legend and mark_safe(legend)
        self.classes = classes
        self.description = mark_safe(description)
        self.name = name

    def _errors(self):
        return ErrorDict(((k, v) for (k, v) in six.iteritems(self.form.errors)
                          if k in [f.name for f in self.boundfields]))
    errors = property(_errors)

    def __iter__(self):
        for bf in self.boundfields:
            yield _mark_row_attrs(bf, self.form)

    def __repr__(self):
        return "%s('%s', %s, legend='%s', classes='%s', description='%s')" % (
            self.__class__.__name__, self.name,
            [f.name for f in self.boundfields], self.legend, self.classes,
            self.description)


class FieldsetCollection(object):
    def __init__(self, form, fieldsets):
        self.form = form
        self.fieldsets = fieldsets
        self._cached_fieldsets = []

    def __len__(self):
        return len(self.fieldsets) or 1

    def __iter__(self):
        if not self._cached_fieldsets:
            self._gather_fieldsets()
        for field in self._cached_fieldsets:
            yield field

    def __getitem__(self, key):
        if not self._cached_fieldsets:
            self._gather_fieldsets()
        for field in self._cached_fieldsets:
            if field.name == key:
                return field
        raise KeyError

    def _gather_fieldsets(self):
        if not self.fieldsets:
            self.fieldsets = (('main', {'fields': self.form.fields.keys(),
                                        'legend': ''}),)
        for name, options in self.fieldsets:
            try:
                field_names = [n for n in options['fields']
                               if n in self.form.fields]
            except KeyError:
                message = "Fieldset definition must include 'fields' option."
                raise ValueError(message)
            boundfields = [forms.forms.BoundField(self.form,
                                                  self.form.fields[n], n)
                           for n in field_names]
            self._cached_fieldsets.append(Fieldset(self.form, name,
                boundfields, options.get('legend', None),
                ' '.join(options.get('classes', ())),
                options.get('description', '')))


def _get_meta_attr(attrs, attr, default):
    try:
        ret = getattr(attrs['Meta'], attr)
    except (KeyError, AttributeError):
        ret = default
    return ret


def _set_meta_attr(attrs, attr, value):
    try:
        setattr(attrs['Meta'], attr, value)
        return True
    except KeyError:
        return False


def get_fieldsets(bases, attrs):
    """Get the fieldsets definition from the inner Meta class."""
    fieldsets = _get_meta_attr(attrs, 'fieldsets', None)
    if fieldsets is None:
        #grab the fieldsets from the first base class that has them
        for base in bases:
            fieldsets = getattr(base, 'base_fieldsets', None)
            if fieldsets is not None:
                break
    fieldsets = fieldsets or []
    return fieldsets


def get_fields_from_fieldsets(fieldsets):
    """Get a list of all fields included in a fieldsets definition."""
    fields = []
    try:
        for name, options in fieldsets:
            fields.extend(options['fields'])
    except (TypeError, KeyError):
        raise ValueError('"fieldsets" must be an iterable of two-tuples, '
                         'and the second tuple must be a dictionary '
                         'with a "fields" key')
    return fields or None


def get_row_attrs(bases, attrs):
    """Get the row_attrs definition from the inner Meta class."""
    return _get_meta_attr(attrs, 'row_attrs', {})


def _mark_row_attrs(bf, form):
    row_attrs = deepcopy(form._row_attrs.get(bf.name, {}))
    if bf.field.required:
        req_class = 'required'
    else:
        req_class = 'optional'
    if bf.errors:
        req_class += ' error'
    if 'class' in row_attrs:
        row_attrs['class'] = row_attrs['class'] + ' ' + req_class
    else:
        row_attrs['class'] = req_class
    bf.row_attrs = mark_safe(flatatt(row_attrs))
    return bf


class BetterFormBaseMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['base_fieldsets'] = get_fieldsets(bases, attrs)
        fields = get_fields_from_fieldsets(attrs['base_fieldsets'])
        if (_get_meta_attr(attrs, 'fields', None) is None and
            _get_meta_attr(attrs, 'exclude', None) is None):
            _set_meta_attr(attrs, 'fields', fields)
        attrs['base_row_attrs'] = get_row_attrs(bases, attrs)

        new_class = super(BetterFormBaseMetaclass,
                          cls).__new__(cls, name, bases, attrs)
        return new_class


class BetterFormMetaclass(BetterFormBaseMetaclass,
                          forms.forms.DeclarativeFieldsMetaclass):
    pass


class BetterModelFormMetaclass(BetterFormBaseMetaclass,
                               forms.models.ModelFormMetaclass):
    pass


class BetterBaseForm(object):
    """
    ``BetterForm`` and ``BetterModelForm`` are subclasses of Form
    and ModelForm that allow for declarative definition of fieldsets
    and row_attrs in an inner Meta class.

    The row_attrs declaration is a dictionary mapping field names to
    dictionaries of attribute/value pairs.  The attribute/value
    dictionaries will be flattened into HTML-style attribute/values
    (i.e. {'style': 'display: none'} will become ``style="display:
    none"``), and will be available as the ``row_attrs`` attribute of
    the ``BoundField``.  Also, a CSS class of "required" or "optional"
    will automatically be added to the row_attrs of each
    ``BoundField``, depending on whether the field is required.

    There is no automatic inheritance of ``row_attrs``.

    The fieldsets declaration is a list of two-tuples very similar to
    the ``fieldsets`` option on a ModelAdmin class in
    ``django.contrib.admin``.

    The first item in each two-tuple is a name for the fieldset, and
    the second is a dictionary of fieldset options.

    Valid fieldset options in the dictionary include:

    ``fields`` (required): A tuple of field names to display in this
    fieldset.

    ``classes``: A list of extra CSS classes to apply to the fieldset.

    ``legend``: This value, if present, will be the contents of a ``legend``
    tag to open the fieldset.

    ``description``: A string of optional extra text to be displayed
    under the ``legend`` of the fieldset.

    When iterated over, the ``fieldsets`` attribute of a
    ``BetterForm`` (or ``BetterModelForm``) yields ``Fieldset``s.
    Each ``Fieldset`` has a ``name`` attribute, a ``legend``
    attribute, , a ``classes`` attribute (the ``classes`` tuple
    collapsed into a space-separated string), and a description
    attribute, and when iterated over yields its ``BoundField``s.

    Subclasses of a ``BetterForm`` will inherit their parent's
    fieldsets unless they define their own.

    A ``BetterForm`` or ``BetterModelForm`` can still be iterated over
    directly to yield all of its ``BoundField``s, regardless of
    fieldsets.

    """
    def __init__(self, *args, **kwargs):
        self._fieldsets = deepcopy(self.base_fieldsets)
        self._row_attrs = deepcopy(self.base_row_attrs)
        self._fieldset_collection = None
        super(BetterBaseForm, self).__init__(*args, **kwargs)

    @property
    def fieldsets(self):
        if not self._fieldset_collection:
            self._fieldset_collection = FieldsetCollection(
                self, self._fieldsets)
        return self._fieldset_collection

    def __iter__(self):
        for bf in super(BetterBaseForm, self).__iter__():
            yield _mark_row_attrs(bf, self)

    def __getitem__(self, name):
        bf = super(BetterBaseForm, self).__getitem__(name)
        return _mark_row_attrs(bf, self)


class BetterForm(six.with_metaclass(BetterFormMetaclass, BetterBaseForm),
                 forms.Form):
    __doc__ = BetterBaseForm.__doc__


class BetterModelForm(six.with_metaclass(BetterModelFormMetaclass,
                                         BetterBaseForm), forms.ModelForm):
    __doc__ = BetterBaseForm.__doc__


class BasePreviewFormMixin(object):
    """
    Mixin to add preview functionality to a form.  If the form is submitted
    with the following k/v pair in its ``data`` dictionary:

        'submit': 'preview'    (value string is case insensitive)

    Then ``PreviewForm.preview`` will be marked ``True`` and the form will
    be marked invalid (though this invalidation will not put an error in
    its ``errors`` dictionary).

    """
    def __init__(self, *args, **kwargs):
        super(BasePreviewFormMixin, self).__init__(*args, **kwargs)
        self.preview = self.check_preview(kwargs.get('data', None))

    def check_preview(self, data):
        if data and data.get('submit', '').lower() == u'preview':
            return True
        return False

    def is_valid(self, *args, **kwargs):
        if self.preview:
            return False
        return super(BasePreviewFormMixin, self).is_valid()


class PreviewModelForm(BasePreviewFormMixin, BetterModelForm):
    pass


class PreviewForm(BasePreviewFormMixin, BetterForm):
    pass

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import posixpath

from django.conf import settings

JQUERY_URL = getattr(
    settings, 'JQUERY_URL',
    'http://ajax.googleapis.com/ajax/libs/jquery/1.8/jquery.min.js')

if not ((':' in JQUERY_URL) or (JQUERY_URL.startswith('/'))):
    JQUERY_URL = posixpath.join(settings.STATIC_URL, JQUERY_URL)

########NEW FILE########
__FILENAME__ = form_utils
# -*- coding: utf-8 -*-
"""
templatetags for django-form-utils

"""
from __future__ import unicode_literals

from django import forms
from django import template
from django.template.loader import render_to_string
from django.utils import six

from ..forms import BetterForm, BetterModelForm
from ..utils import select_template_from_string

register = template.Library()


@register.filter
def render(form, template_name=None):
    """
    Renders a ``django.forms.Form`` or
    ``form_utils.forms.BetterForm`` instance using a template.

    The template name(s) may be passed in as the argument to the
    filter (use commas to separate multiple template names for
    template selection).

    If not provided, the default template name is
    ``form_utils/form.html``.

    If the form object to be rendered is an instance of
    ``form_utils.forms.BetterForm`` or
    ``form_utils.forms.BetterModelForm``, the template
    ``form_utils/better_form.html`` will be used instead if present.

    """
    default = 'form_utils/form.html'
    if isinstance(form, (BetterForm, BetterModelForm)):
        default = ','.join(['form_utils/better_form.html', default])
    tpl = select_template_from_string(template_name or default)

    return tpl.render(template.Context({'form': form}))


@register.filter
def label(boundfield, contents=None):
    """Render label tag for a boundfield, optionally with given contents."""
    label_text = contents or boundfield.label
    id_ = boundfield.field.widget.attrs.get('id') or boundfield.auto_id

    return render_to_string("forms/_label.html", {
        "label_text": label_text,
        "id": id_,
        "field": boundfield})


@register.filter
def value_text(boundfield):
    """Return the value for given boundfield as human-readable text."""
    val = boundfield.value()
    # If choices is set, use the display label
    return six.text_type(
        dict(getattr(boundfield.field, "choices", [])).get(val, val))


@register.filter
def selected_values(boundfield):
    """Return the values for given multiple-select as human-readable text."""
    val = boundfield.value()
    # If choices is set, use the display label
    choice_dict = dict(getattr(boundfield.field, "choices", []))
    return [six.text_type(choice_dict.get(v, v)) for v in val]


@register.filter
def optional(boundfield):
    """Return True if given boundfield is optional, else False."""
    return not boundfield.field.required


@register.filter
def is_checkbox(boundfield):
    """Return True if this field's widget is a CheckboxInput."""
    return isinstance(boundfield.field.widget, forms.CheckboxInput)


@register.filter
def is_multiple(boundfield):
    """Return True if this field is a MultipleChoiceField."""
    return isinstance(boundfield.field, forms.MultipleChoiceField)


@register.filter
def is_select(boundfield):
    """Return True if this field is a ChoiceField (or subclass)."""
    return isinstance(boundfield.field, forms.ChoiceField)


@register.filter
def is_radio(boundfield):
    """
    Return True if this field's widget's class name contains 'radio'.

    This hacky approach is necessary in order to support django-floppyforms,
    whose RadioSelect does not inherit from Django's built-in RadioSelect.

    """
    return 'radio' in boundfield.field.widget.__class__.__name__.lower()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
utility functions for django-form-utils

Time-stamp: <2009-03-26 12:32:41 carljm utils.py>

"""
from __future__ import unicode_literals

from django.template import loader


def select_template_from_string(arg):
    """
    Select a template from a string, which can include multiple
    template paths separated by commas.
    """
    if ',' in arg:
        tpl = loader.select_template(
            [tn.strip() for tn in arg.split(',')])
    else:
        tpl = loader.get_template(arg)
    return tpl

########NEW FILE########
__FILENAME__ = widgets
# -*- coding: utf-8 -*-
"""
widgets for django-form-utils

parts of this code taken from http://www.djangosnippets.org/snippets/934/
 - thanks baumer1122

"""
from __future__ import unicode_literals

import posixpath

from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe

from .settings import JQUERY_URL

try:
    from sorl.thumbnail import get_thumbnail

    def thumbnail(image_path, width, height):
        geometry_string = 'x'.join([str(width), str(height)])
        t = get_thumbnail(image_path, geometry_string)
        return u'<img src="%s" alt="%s" />' % (t.url, image_path)
except ImportError:
    try:
        from easy_thumbnails.files import get_thumbnailer

        def thumbnail(image_path, width, height):
            thumbnail_options = dict(size=(width, height), crop=True)
            thumbnail = get_thumbnailer(image_path).get_thumbnail(
                thumbnail_options)
            return u'<img src="%s" alt="%s" />' % (thumbnail.url, image_path)
    except ImportError:
        def thumbnail(image_path, width, height):
            absolute_url = posixpath.join(settings.MEDIA_URL, image_path)
            return u'<img src="%s" alt="%s" />' % (absolute_url, image_path)


class ImageWidget(forms.FileInput):
    template = '%(input)s<br />%(image)s'

    def __init__(self, attrs=None, template=None, width=200, height=200):
        if template is not None:
            self.template = template
        self.width = width
        self.height = height
        super(ImageWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        input_html = super(ImageWidget, self).render(name, value, attrs)
        if hasattr(value, 'width') and hasattr(value, 'height'):
            image_html = thumbnail(value.name, self.width, self.height)
            output = self.template % {'input': input_html,
                                      'image': image_html}
        else:
            output = input_html
        return mark_safe(output)


class ClearableFileInput(forms.MultiWidget):
    default_file_widget_class = forms.FileInput
    template = '%(input)s Clear: %(checkbox)s'

    def __init__(self, file_widget=None,
                 attrs=None, template=None):
        if template is not None:
            self.template = template
        file_widget = file_widget or self.default_file_widget_class()
        super(ClearableFileInput, self).__init__(
            widgets=[file_widget, forms.CheckboxInput()],
            attrs=attrs)

    def render(self, name, value, attrs=None):
        if isinstance(value, list):
            self.value = value[0]
        else:
            self.value = value
        return super(ClearableFileInput, self).render(name, value, attrs)

    def decompress(self, value):
        # the clear checkbox is never initially checked
        return [value, None]

    def format_output(self, rendered_widgets):
        if self.value:
            return self.template % {'input': rendered_widgets[0],
                                    'checkbox': rendered_widgets[1]}
        return rendered_widgets[0]

root = lambda path: posixpath.join(settings.STATIC_URL, path)


class AutoResizeTextarea(forms.Textarea):
    """
    A Textarea widget that automatically resizes to accomodate its contents.
    """
    class Media:
        js = (JQUERY_URL,
              root('form_utils/js/jquery.autogrow.js'),
              root('form_utils/js/autoresize.js'))

    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        try:
            attrs['class'] = "%s autoresize" % (attrs['class'],)
        except KeyError:
            attrs['class'] = 'autoresize'
        attrs.setdefault('cols', 80)
        attrs.setdefault('rows', 5)
        super(AutoResizeTextarea, self).__init__(*args, **kwargs)


class InlineAutoResizeTextarea(AutoResizeTextarea):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        try:
            attrs['class'] = "%s inline" % (attrs['class'],)
        except KeyError:
            attrs['class'] = 'inline'
        attrs.setdefault('cols', 40)
        attrs.setdefault('rows', 2)
        super(InlineAutoResizeTextarea, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Person(models.Model):
    age = models.IntegerField()
    name = models.CharField(max_length=100)

class Document(models.Model):
    myfile = models.FileField(upload_to='uploads')
    

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import os, sys

from django.conf import settings


if not settings.configured:
    settings_dict = dict(
        INSTALLED_APPS=['form_utils', 'tests'],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                }
            },
        MEDIA_ROOT=os.path.join(os.path.dirname(__file__), 'media'),
        MEDIA_URL='/media/',
        STATIC_URL='/static/',
        )

    settings.configure(**settings_dict)


def runtests(*test_args):
    if not test_args:
        test_args = ['tests']

    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent)

    from django.test.simple import DjangoTestSuiteRunner
    failures = DjangoTestSuiteRunner(
        verbosity=1, interactive=True, failfast=False).run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django
from django import forms
from django import template
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import (
    FieldFile, ImageFieldFile, FileField, ImageField)
from django.test import TestCase
from django.utils import six

from mock import patch

from form_utils.forms import BetterForm, BetterModelForm
from form_utils.widgets import ImageWidget, ClearableFileInput
from form_utils.fields import ClearableFileField, ClearableImageField

from .models import Person, Document


class ApplicationForm(BetterForm):
    """
    A sample form with fieldsets.

    """
    name = forms.CharField()
    position = forms.CharField()
    reference = forms.CharField(required=False)

    class Meta:
        fieldsets = (('main', {'fields': ('name', 'position'), 'legend': ''}),
                     ('Optional', {'fields': ('reference',),
                                   'classes': ('optional',)}))


class InheritedForm(ApplicationForm):
    """
    An inherited form that does not define its own fieldsets inherits
    its parents'.

    """
    pass


class MudSlingerApplicationForm(ApplicationForm):
    """
    Inherited forms can manually inherit and change/override the
    parents' fieldsets by using the logical Python code in Meta:

    """
    target = forms.CharField()

    class Meta:
        fieldsets = list(ApplicationForm.Meta.fieldsets)
        fieldsets[0] = ('main', {'fields': ('name', 'position', 'target'),
                                 'description': 'Basic mudslinging info',
                                 'legend': 'basic info'})


class FeedbackForm(BetterForm):
    """
    A ``BetterForm`` that defines no fieldsets explicitly gets a
    single fieldset by default.

    """
    title = forms.CharField()
    name = forms.CharField()


class HoneypotForm(BetterForm):
    """
    A ``BetterForm`` demonstrating the use of ``row_attrs``.

    In ``django.contrib.comments``, this effect (hiding an entire form
    input along with its label) can only be achieved through a
    customized template; here, we achieve it in a way that allows us
    to still use a generic form-rendering template.

    """
    honeypot = forms.CharField()
    name = forms.CharField()

    class Meta:
        row_attrs = {'honeypot': {'style': 'display: none'}}

    def clean_honeypot(self):
        if self.cleaned_data.get("honeypot"):
            raise forms.ValidationError("Honeypot field must be empty.")


class PersonForm(BetterModelForm):
    """
    A ``BetterModelForm`` with fieldsets.

    """
    title = forms.CharField()

    class Meta:
        model = Person
        fieldsets = [('main', {'fields': ['name'],
                               'legend': '',
                               'classes': ['main']}),
                     ('More', {'fields': ['age'],
                               'description': 'Extra information',
                               'classes': ['more', 'collapse']}),
                     (None, {'fields': ['title']})]


class PartialPersonForm(BetterModelForm):
    """
    A ``BetterModelForm`` whose fieldsets don't contain all fields
    from the model.

    """
    class Meta:
        model = Person
        fieldsets = [('main', {'fields': ['name']})]


class ManualPartialPersonForm(BetterModelForm):
    """
    A ``BetterModelForm`` whose fieldsets don't contain all fields
    from the model, but we set ``fields`` manually.

    """
    class Meta:
        model = Person
        fieldsets = [('main', {'fields': ['name']})]
        fields = ['name', 'age']


class ExcludePartialPersonForm(BetterModelForm):
    """
    A ``BetterModelForm`` whose fieldsets don't contain all fields
    from the model, but we set ``exclude`` manually.

    """
    class Meta:
        model = Person
        fieldsets = [('main', {'fields': ['name']})]
        exclude = ['age']


class AcrobaticPersonForm(PersonForm):
    """
    A ``BetterModelForm`` that inherits from another and overrides one
    of its fieldsets.

    """
    agility = forms.IntegerField()
    speed = forms.IntegerField()

    class Meta(PersonForm.Meta):
        fieldsets = list(PersonForm.Meta.fieldsets)
        fieldsets = fieldsets[:1] + [
            ('Acrobatics', {'fields': ('age', 'speed', 'agility')})]


class AbstractPersonForm(BetterModelForm):
    """
    An abstract ``BetterModelForm`` without fieldsets.

    """
    title = forms.CharField()

    class Meta:
        pass


class InheritedMetaAbstractPersonForm(AbstractPersonForm):
    """
    A ``BetterModelForm`` that inherits from abstract one and its Meta class
    and adds fieldsets

    """
    class Meta(AbstractPersonForm.Meta):
        model = Person
        fieldsets = [('main', {'fields': ['name'],
                               'legend': '',
                               'classes': ['main']}),
                     ('More', {'fields': ['age'],
                               'description': 'Extra information',
                               'classes': ['more', 'collapse']}),
                     (None, {'fields': ['title']})]


class BetterFormTests(TestCase):
    fieldset_target_data = {
        ApplicationForm:
            [
                    (['name', 'position'],
                     {
                                'name': 'main',
                                'legend': '',
                                'description': '',
                                'classes': '',
                                }),
                    (['reference'],
                    {
                                'name': 'Optional',
                                'legend': 'Optional',
                                'description': '',
                                'classes': 'optional'
                                }),
                    ],
        InheritedForm:
            [
                    (['name', 'position'],
                     {
                                'name': 'main',
                                'legend': '',
                                'description': '',
                                'classes': '',
                                }),
                    (['reference'],
                    {
                                'name': 'Optional',
                                'legend': 'Optional',
                                'description': '',
                                'classes': 'optional'
                                }),
                    ],
        MudSlingerApplicationForm:
            [
                    (['name', 'position', 'target'],
                     {
                                'name': 'main',
                                'legend': 'basic info',
                                'description': 'Basic mudslinging info',
                                'classes': '',
                                }),
                    (['reference'],
                    {
                                'name': 'Optional',
                                'legend': 'Optional',
                                'description': '',
                                'classes': 'optional'
                                }),
                    ],
        FeedbackForm:
            [
                    (['title', 'name'],
                     {
                                'name': 'main',
                                'legend': '',
                                'description': '',
                                'classes': '',
                                }),
                    ],
        PersonForm:
            [
                    (['name'],
                     {
                                'name': 'main',
                                'legend': '',
                                'description': '',
                                'classes': 'main',
                                }),
                    (['age'],
                    {
                                'name': 'More',
                                'legend': 'More',
                                'description': 'Extra information',
                                'classes': 'more collapse'
                                }),
                    (['title'],
                    {
                                'name': None,
                                'legend': None,
                                'description': '',
                                'classes': ''
                                }),
                    ],
        AcrobaticPersonForm:
            [
                    (['name'],
                     {
                                'name': 'main',
                                'legend': '',
                                'description': '',
                                'classes': 'main',
                                }),
                    (['age', 'speed', 'agility'],
                    {
                                'name': 'Acrobatics',
                                'legend': 'Acrobatics',
                                'description': '',
                                'classes': ''
                                }),
                    ],
            InheritedMetaAbstractPersonForm:
            [
                    (['name'],
                     {
                                'name': 'main',
                                'legend': '',
                                'description': '',
                                'classes': 'main',
                                }),
                    (['age'],
                    {
                                'name': 'More',
                                'legend': 'More',
                                'description': 'Extra information',
                                'classes': 'more collapse'
                                }),
                    (['title'],
                    {
                                'name': None,
                                'legend': None,
                                'description': '',
                                'classes': ''
                                }),
                    ],


        }

    def test_iterate_fieldsets(self):
        """
        Test the definition and inheritance of fieldsets, by matching
        sample form classes' ``fieldsets`` attribute with the target
        data in ``self.fieldsets_target_data``.

        """
        for form_class, targets in self.fieldset_target_data.items():
            form = form_class()
            # verify len(form.fieldsets) tells us the truth
            self.assertEqual(len(form.fieldsets), len(targets))
            for i, fs in enumerate(form.fieldsets):
                target_data = targets[i]
                # verify fieldset contains correct fields
                self.assertEqual([f.name for f in fs],
                                  target_data[0])
                # verify fieldset has correct attributes
                for attr, val in target_data[1].items():
                    self.assertEqual(getattr(fs, attr), val)

    def test_fieldset_errors(self):
        """
        We can access the ``errors`` attribute of a bound form and get
        an ``ErrorDict``.

        """
        form = ApplicationForm(data={'name': 'John Doe',
                                     'reference': 'Jane Doe'})
        self.assertEqual([fs.errors for fs in form.fieldsets],
                          [{'position': [u'This field is required.']}, {}])

    def test_iterate_fields(self):
        """
        We can still iterate over a ``BetterForm`` and get its fields
        directly, regardless of fieldsets (backward-compatibility with
        regular ``Forms``).

        """
        form = ApplicationForm()
        self.assertEqual([field.name for field in form],
                          ['name', 'position', 'reference'])

    def test_getitem_fields(self):
        """
        We can use dictionary style look up of fields in a fieldset using the
        name as the key.

        """
        form = ApplicationForm()
        fieldset = form.fieldsets['main']
        self.assertEqual(fieldset.name, 'main')
        self.assertEqual(len(fieldset.boundfields), 2)

    def test_row_attrs_by_name(self):
        """
        Fields of a ``BetterForm`` accessed by name have ``row_attrs``
        as defined in the inner ``Meta`` class.

        """
        form = HoneypotForm()
        attrs = form['honeypot'].row_attrs
        self.assertTrue(u'style="display: none"' in attrs)
        self.assertTrue(u'class="required"' in attrs)

    def test_row_attrs_by_iteration(self):
        """
        Fields of a ``BetterForm`` accessed by form iteration have
        ``row_attrs`` as defined in the inner ``Meta`` class.

        """
        form = HoneypotForm()
        honeypot = [field for field in form if field.name=='honeypot'][0]
        attrs = honeypot.row_attrs
        self.assertTrue(u'style="display: none"' in attrs)
        self.assertTrue(u'class="required"' in attrs)

    def test_row_attrs_by_fieldset_iteration(self):
        """
        Fields of a ``BetterForm`` accessed by fieldset iteration have
        ``row_attrs`` as defined in the inner ``Meta`` class.

        """
        form = HoneypotForm()
        fieldset = [fs for fs in form.fieldsets][0]
        honeypot = [field for field in fieldset if field.name=='honeypot'][0]
        attrs = honeypot.row_attrs
        self.assertTrue(u'style="display: none"' in attrs)
        self.assertTrue(u'class="required"' in attrs)

    def test_row_attrs_error_class(self):
        """
        row_attrs adds an error class if a field has errors.

        """
        form = HoneypotForm({"honeypot": "something"})

        attrs = form['honeypot'].row_attrs
        self.assertTrue(u'style="display: none"' in attrs)
        self.assertTrue(u'class="required error"' in attrs)

    def test_friendly_typo_error(self):
        """
        If we define a single fieldset and leave off the trailing , in
        a tuple, we get a friendly error.

        """
        def _define_fieldsets_with_missing_comma():
            class ErrorForm(BetterForm):
                one = forms.CharField()
                two = forms.CharField()
                class Meta:
                    fieldsets = ((None, {'fields': ('one', 'two')}))
        # can't test the message here, but it would be TypeError otherwise
        self.assertRaises(ValueError,
                          _define_fieldsets_with_missing_comma)

    def test_modelform_fields(self):
        """
        The ``fields`` Meta option of a ModelForm is automatically
        populated with the fields present in a fieldsets definition.

        """
        self.assertEqual(PartialPersonForm._meta.fields, ['name'])

    def test_modelform_manual_fields(self):
        """
        The ``fields`` Meta option of a ModelForm is not automatically
        populated if it's set manually.

        """
        self.assertEqual(ManualPartialPersonForm._meta.fields, ['name', 'age'])

    def test_modelform_fields_exclude(self):
        """
        The ``fields`` Meta option of a ModelForm is not automatically
        populated if ``exclude`` is set manually.

        """
        self.assertEqual(ExcludePartialPersonForm._meta.fields, None)


number_field_type = 'number' if django.VERSION > (1, 6, 0) else 'text'
label_suffix = ':' if django.VERSION > (1, 6, 0) else ''


class BoringForm(forms.Form):
    boredom = forms.IntegerField()
    excitement = forms.IntegerField()

class TemplatetagTests(TestCase):
    boring_form_html = (
        u'<fieldset class="fieldset_main">'
        u'<ul>'
        u'<li>'
        u'<label for="id_boredom">Boredom%(suffix)s</label>'
        u'<input type="%(type)s" name="boredom" id="id_boredom" />'
        u'</li>'
        u'<li>'
        u'<label for="id_excitement">Excitement%(suffix)s</label>'
        u'<input type="%(type)s" name="excitement" id="id_excitement" />'
        u'</li>'
        u'</ul>'
        u'</fieldset>'
        ) % {'type': number_field_type, 'suffix': label_suffix}

    def test_render_form(self):
        """
        A plain ``forms.Form`` renders as a list of fields.

        """
        form = BoringForm()
        tpl = template.Template('{% load form_utils %}{{ form|render }}')
        html = tpl.render(template.Context({'form': form}))
        self.assertHTMLEqual(html, self.boring_form_html)

    betterform_html = (
        u'<fieldset class="">'
        u'<ul>'
        u'<li class="required">'
        u'<label for="id_name">Name%(suffix)s</label>'
        u'<input type="text" name="name" id="id_name" />'
        u'</li>'
        u'<li class="required">'
        u'<label for="id_position">Position%(suffix)s</label>'
        u'<input type="text" name="position" id="id_position" />'
        u'</li>'
        u'</ul>'
        u'</fieldset>'
        u'<fieldset class="optional">'
        u'<legend>Optional</legend>'
        u'<ul>'
        u'<li class="optional">'
        u'<label for="id_reference">Reference%(suffix)s</label>'
        u'<input type="text" name="reference" id="id_reference" />'
        u'</li>'
        u'</ul>'
        u'</fieldset>'
        ) % {'suffix': label_suffix}

    def test_render_betterform(self):
        """
        A ``BetterForm`` renders as a list of fields within each fieldset.

        """
        form = ApplicationForm()
        tpl = template.Template('{% load form_utils %}{{ form|render }}')
        html = tpl.render(template.Context({'form': form}))
        self.assertHTMLEqual(html, self.betterform_html)


class ImageWidgetTests(TestCase):
    def test_render(self):
        """
        ``ImageWidget`` renders the file input and the image thumb.

        """
        widget = ImageWidget()
        html = widget.render('fieldname', ImageFieldFile(None, ImageField(), 'tiny.png'))
        # test only this much of the html, because the remainder will
        # vary depending on whether we have sorl-thumbnail
        self.assertTrue('<img' in html)
        self.assertTrue('/media/tiny' in html)

    def test_render_nonimage(self):
        """
        ``ImageWidget`` renders the file input only, if given a non-image.

        """
        widget = ImageWidget()
        html = widget.render('fieldname', FieldFile(None, FileField(), 'something.txt'))
        self.assertHTMLEqual(html, '<input type="file" name="fieldname" />')

    def test_custom_template(self):
        """
        ``ImageWidget`` respects a custom template.

        """
        widget = ImageWidget(template='<div>%(image)s</div>'
                             '<div>%(input)s</div>')
        html = widget.render('fieldname', ImageFieldFile(None, ImageField(), 'tiny.png'))
        self.assertTrue(html.startswith('<div><img'))


class ClearableFileInputTests(TestCase):
    def test_render(self):
        """
        ``ClearableFileInput`` renders the file input and an unchecked
        clear checkbox.

        """
        widget = ClearableFileInput()
        html = widget.render('fieldname', 'tiny.png')
        self.assertHTMLEqual(
            html,
            '<input type="file" name="fieldname_0" />'
            ' Clear: '
            '<input type="checkbox" name="fieldname_1" />'
            )

    def test_custom_file_widget(self):
        """
        ``ClearableFileInput`` respects its ``file_widget`` argument.

        """
        widget = ClearableFileInput(file_widget=ImageWidget())
        html = widget.render('fieldname', ImageFieldFile(None, ImageField(), 'tiny.png'))
        self.assertTrue('<img' in html)

    def test_custom_file_widget_via_subclass(self):
        """
        Default ``file_widget`` class can also be customized by
        subclassing.

        """
        class ClearableImageWidget(ClearableFileInput):
            default_file_widget_class = ImageWidget
        widget = ClearableImageWidget()
        html = widget.render('fieldname', ImageFieldFile(None, ImageField(), 'tiny.png'))
        self.assertTrue('<img' in html)

    def test_custom_template(self):
        """
        ``ClearableFileInput`` respects its ``template`` argument.

        """
        widget = ClearableFileInput(template='Clear: %(checkbox)s %(input)s')
        html = widget.render('fieldname', ImageFieldFile(None, ImageField(), 'tiny.png'))
        self.assertHTMLEqual(
            html,
            'Clear: '
            '<input type="checkbox" name="fieldname_1" /> '
            '<input type="file" name="fieldname_0" />'
            )

    def test_custom_template_via_subclass(self):
        """
        Template can also be customized by subclassing.

        """
        class ReversedClearableFileInput(ClearableFileInput):
            template = 'Clear: %(checkbox)s %(input)s'
        widget = ReversedClearableFileInput()
        html = widget.render('fieldname', 'tiny.png')
        self.assertHTMLEqual(
            html,
            'Clear: '
            '<input type="checkbox" name="fieldname_1" /> '
            '<input type="file" name="fieldname_0" />'
            )


class ClearableFileFieldTests(TestCase):
    upload = SimpleUploadedFile('something.txt', b'Something')

    def test_bound_redisplay(self):
        class TestForm(forms.Form):
            f = ClearableFileField()
        form = TestForm(files={'f_0': self.upload})
        self.assertHTMLEqual(
            six.text_type(form['f']),
            u'<input type="file" name="f_0" id="id_f_0" />'
            u' Clear: <input type="checkbox" name="f_1" id="id_f_1" />'
            )

    def test_not_cleared(self):
        """
        If the clear checkbox is not checked, the ``FileField`` data
        is returned normally.

        """
        field = ClearableFileField()
        result = field.clean([self.upload, '0'])
        self.assertEqual(result, self.upload)

    def test_cleared(self):
        """
        If the clear checkbox is checked and the file input empty, the
        field returns a value that is able to get a normal model
        ``FileField`` to clear itself.

        This is actually a bit tricky/hacky in the implementation, see
        the docstring of ``form_utils.fields.FakeEmptyFieldFile`` for
        details. Here we just test the results.

        """
        doc = Document.objects.create(myfile='something.txt')
        field = ClearableFileField(required=False)
        result = field.clean(['', '1'])
        doc._meta.get_field('myfile').save_form_data(doc, result)
        doc.save()
        doc = Document.objects.get(pk=doc.pk)
        self.assertEqual(doc.myfile, '')

    def test_cleared_but_file_given(self):
        """
        If we check the clear checkbox, but also submit a file, the
        file overrides.

        """
        field = ClearableFileField()
        result = field.clean([self.upload, '1'])
        self.assertEqual(result, self.upload)

    def test_custom_file_field(self):
        """
        We can pass in our own ``file_field`` rather than using the
        default ``forms.FileField``.

        """
        file_field = forms.ImageField()
        field = ClearableFileField(file_field=file_field)
        self.assertTrue(field.fields[0] is file_field)

    def test_custom_file_field_required(self):
        """
        If we pass in our own ``file_field`` its required value is
        used for the composite field.

        """
        file_field = forms.ImageField(required=False)
        field = ClearableFileField(file_field=file_field)
        self.assertFalse(field.required)

    def test_custom_file_field_widget_used(self):
        """
        If we pass in our own ``file_field`` its widget is used for
        the internal file field.

        """
        widget = ImageWidget()
        file_field = forms.ImageField(widget=widget)
        field = ClearableFileField(file_field=file_field)
        self.assertTrue(field.fields[0].widget is widget)

    def test_clearable_image_field(self):
        """
        We can override the default ``file_field`` class by
        subclassing.

        ``ClearableImageField`` is provided, and does just this.

        """
        field = ClearableImageField()
        self.assertTrue(isinstance(field.fields[0], forms.ImageField))

    def test_custom_template(self):
        """
        We can pass in a custom template and it will be passed on to
        the widget.

        """
        tpl = 'Clear: %(checkbox)s %(input)s'
        field = ClearableFileField(template=tpl)
        self.assertEqual(field.widget.template, tpl)

    def test_custom_widget_by_subclassing(self):
        """
        We can set a custom default widget by subclassing.

        """
        class ClearableImageWidget(ClearableFileInput):
            default_file_widget_class = ImageWidget
        class ClearableImageWidgetField(ClearableFileField):
            widget = ClearableImageWidget
        field = ClearableImageWidgetField()
        self.assertTrue(isinstance(field.widget, ClearableImageWidget))




class FieldFilterTests(TestCase):
    """Tests for form field filters."""
    @property
    def form_utils(self):
        """The module under test."""
        from form_utils.templatetags import form_utils
        return form_utils


    @property
    def form(self):
        """A sample form."""
        class PersonForm(forms.Form):
            name = forms.CharField(initial="none", required=True)
            level = forms.ChoiceField(
                choices=(("b", "Beginner"), ("a", "Advanced")), required=False)
            colors = forms.MultipleChoiceField(
                choices=[("red", "red"), ("blue", "blue")])
            gender = forms.ChoiceField(
                choices=(("m", "Male"), ("f", "Female"), ("o", "Other")),
                widget=forms.RadioSelect(),
                required=False,
                )
            awesome = forms.BooleanField(required=False)

        return PersonForm


    @patch("form_utils.templatetags.form_utils.render_to_string")
    def test_label(self, render_to_string):
        """``label`` filter renders field label from template."""
        render_to_string.return_value = "<label>something</label>"
        bf = self.form()["name"]

        label = self.form_utils.label(bf)

        self.assertEqual(label, "<label>something</label>")
        render_to_string.assert_called_with(
            "forms/_label.html",
            {
                "label_text": "Name",
                "id": "id_name",
                "field": bf
                }
            )


    @patch("form_utils.templatetags.form_utils.render_to_string")
    def test_label_override(self, render_to_string):
        """label filter allows overriding the label text."""
        bf = self.form()["name"]

        self.form_utils.label(bf, "override")

        render_to_string.assert_called_with(
            "forms/_label.html",
            {
                "label_text": "override",
                "id": "id_name",
                "field": bf
                }
            )


    def test_value_text(self):
        """``value_text`` filter returns value of field."""
        self.assertEqual(
            self.form_utils.value_text(self.form({"name": "boo"})["name"]), "boo")


    def test_value_text_unbound(self):
        """``value_text`` filter returns default value of unbound field."""
        self.assertEqual(self.form_utils.value_text(self.form()["name"]), "none")


    def test_value_text_choices(self):
        """``value_text`` filter returns human-readable value of choicefield."""
        self.assertEqual(
            self.form_utils.value_text(
                self.form({"level": "a"})["level"]), "Advanced")


    def test_selected_values_choices(self):
        """``selected_values`` filter returns values of multiple select."""
        f = self.form({"level": ["a", "b"]})

        self.assertEqual(
            self.form_utils.selected_values(f["level"]),
            ["Advanced", "Beginner"],
            )


    def test_optional_false(self):
        """A required field should not be marked optional."""
        self.assertFalse(self.form_utils.optional(self.form()["name"]))


    def test_optional_true(self):
        """A non-required field should be marked optional."""
        self.assertTrue(self.form_utils.optional(self.form()["level"]))


    def test_detect_checkbox(self):
        """``is_checkbox`` detects checkboxes."""
        f = self.form()

        self.assertTrue(self.form_utils.is_checkbox(f["awesome"]))


    def test_detect_non_checkbox(self):
        """``is_checkbox`` detects that select fields are not checkboxes."""
        f = self.form()

        self.assertFalse(self.form_utils.is_checkbox(f["level"]))


    def test_is_multiple(self):
        """`is_multiple` detects a MultipleChoiceField."""
        f = self.form()

        self.assertTrue(self.form_utils.is_multiple(f["colors"]))


    def test_is_not_multiple(self):
        """`is_multiple` detects a non-multiple widget."""
        f = self.form()

        self.assertFalse(self.form_utils.is_multiple(f["level"]))


    def test_is_select(self):
        """`is_select` detects a ChoiceField."""
        f = self.form()

        self.assertTrue(self.form_utils.is_select(f["level"]))


    def test_is_not_select(self):
        """`is_select` detects a non-ChoiceField."""
        f = self.form()

        self.assertFalse(self.form_utils.is_select(f["name"]))


    def test_is_radio(self):
        """`is_radio` detects a radio select widget."""
        f = self.form()

        self.assertTrue(self.form_utils.is_radio(f["gender"]))


    def test_is_not_radio(self):
        """`is_radio` detects a non-radio select."""
        f = self.form()

        self.assertFalse(self.form_utils.is_radio(f["level"]))

########NEW FILE########
__FILENAME__ = test_settings
from os.path import dirname, join

INSTALLED_APPS = ('form_utils', 'tests')
DATABASE_ENGINE = 'sqlite3'

MEDIA_ROOT = join(dirname(__file__), 'media')
MEDIA_URL = '/media/'

STATIC_URL = '/static/'

########NEW FILE########
