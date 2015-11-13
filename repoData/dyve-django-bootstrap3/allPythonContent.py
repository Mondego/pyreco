__FILENAME__ = bootstrap
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.utils.importlib import import_module


# Default settings
BOOTSTRAP3_DEFAULTS = {
    'jquery_url': '//code.jquery.com/jquery.min.js',
    'base_url': '//netdna.bootstrapcdn.com/bootstrap/3.1.1/',
    'css_url': None,
    'theme_url': None,
    'javascript_url': None,
    'javascript_in_head': False,
    'include_jquery': False,
    'horizontal_label_class': 'col-md-2',
    'horizontal_field_class': 'col-md-4',
    'set_required': True,
    'form_required_class': '',
    'form_error_class': '',
    'formset_renderers':{
        'default': 'bootstrap3.renderers.FormsetRenderer',
    },
    'form_renderers': {
        'default': 'bootstrap3.renderers.FormRenderer',
    },
    'field_renderers': {
        'default': 'bootstrap3.renderers.FieldRenderer',
        'inline': 'bootstrap3.renderers.InlineFieldRenderer',
    },
}

# Start with a copy of default settings
BOOTSTRAP3 = BOOTSTRAP3_DEFAULTS.copy()

# Override with user settings from settings.py
BOOTSTRAP3.update(getattr(settings, 'BOOTSTRAP3', {}))


def get_bootstrap_setting(setting, default=None):
    """
    Read a setting
    """
    return BOOTSTRAP3.get(setting, default)


def bootstrap_url(postfix):
    """
    Prefix a relative url with the bootstrap base url
    """
    return get_bootstrap_setting('base_url') + postfix


def jquery_url():
    """
    Return the full url to jQuery file to use
    """
    return get_bootstrap_setting('jquery_url')


def javascript_url():
    """
    Return the full url to the Bootstrap JavaScript file
    """
    return get_bootstrap_setting('javascript_url') or bootstrap_url('js/bootstrap.min.js')


def css_url():
    """
    Return the full url to the Bootstrap CSS file
    """
    return get_bootstrap_setting('css_url') or bootstrap_url('css/bootstrap.min.css')


def theme_url():
    """
    Return the full url to the theme CSS file
    """
    return get_bootstrap_setting('theme_url')


def get_renderer(renderers, layout):
    path = renderers.get(layout, renderers['default'])
    mod, cls = path.rsplit(".", 1)
    return getattr(import_module(mod), cls)


def get_formset_renderer(layout):
    renderers = get_bootstrap_setting('formset_renderers')
    return get_renderer(renderers, layout)


def get_form_renderer(layout):
    renderers = get_bootstrap_setting('form_renderers')
    return get_renderer(renderers, layout)


def get_field_renderer(layout):
    renderers = get_bootstrap_setting('field_renderers')
    return get_renderer(renderers, layout)


########NEW FILE########
__FILENAME__ = components
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from bootstrap3.text import text_value


def render_icon(icon):
    """
    Render a Bootstrap glyphicon icon
    """
    return '<span class="glyphicon glyphicon-{icon}"></span>'.format(icon=icon)


def render_alert(content, alert_type=None, dismissable=True):
    """
    Render a Bootstrap alert
    """
    button = ''
    if not alert_type:
        alert_type = 'info'
    css_classes = ['alert', 'alert-' + text_value(alert_type)]
    if dismissable:
        css_classes.append('alert-dismissable')
        button = '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>'
    return '<div class="{css_classes}">{button}{content}</div>'.format(
        css_classes=' '.join(css_classes),
        button=button,
        content=text_value(content),
    )

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class BootstrapException(Exception):
    """
    Any exception from this package
    """
    pass


class BootstrapError(BootstrapException):
    """
    Any exception that is an error
    """
    pass

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.admin.widgets import AdminFileWidget
from django.forms import HiddenInput, FileInput, CheckboxSelectMultiple, Textarea, TextInput, DateInput, Select
from django.forms.formsets import BaseFormSet

from .bootstrap import get_bootstrap_setting, get_form_renderer, get_field_renderer, get_formset_renderer
from .text import text_concat, text_value
from .exceptions import BootstrapError
from .html import add_css_class, render_tag
from .components import render_icon


FORM_GROUP_CLASS = 'form-group'


def render_formset(formset, layout='', **kwargs):
    """
    Render a formset to a Bootstrap layout
    """
    # if not isinstance(formset, BaseFormSet):
    #     raise BootstrapError('Parameter "formset" should contain a valid Django FormSet.')
    # forms = [render_form(f, **kwargs) for f in formset]
    # return text_value(formset.management_form) + '\n' + '\n'.join(forms)
    renderer_cls = get_formset_renderer(layout)
    return renderer_cls(formset, layout, **kwargs).render()


def render_formset_errors(form, layout='', **kwargs):
    """
    Render formset errors to a Bootstrap layout
    """
    renderer_cls = get_formset_renderer(layout)
    return renderer_cls(form, layout, **kwargs).render_errors()


def render_form(form, layout='', **kwargs):
    """
    Render a formset to a Bootstrap layout
    """
    renderer_cls = get_form_renderer(layout)
    return renderer_cls(form, layout, **kwargs).render()


def render_form_errors(form, layout='', type='all', **kwargs):
    """
    Render form errors to a Bootstrap layout
    """
    renderer_cls = get_form_renderer(layout)
    return renderer_cls(form, layout, **kwargs).render_errors(type)


def render_field(field, layout='', **kwargs):
    """
    Render a formset to a Bootstrap layout
    """
    renderer_cls = get_field_renderer(layout)
    return renderer_cls(field, layout, **kwargs).render()


def render_label(content, label_for=None, label_class=None, label_title=''):
    """
    Render a label with content
    """
    attrs = {}
    if label_for:
        attrs['for'] = label_for
    if label_class:
        attrs['class'] = label_class
    if label_title:
        attrs['title'] = label_title
    return render_tag('label', attrs=attrs, content=content)


def render_button(content, button_type=None, icon=None, button_class=''):
    """
    Render a button with content
    """
    attrs = {}
    attrs['class'] = add_css_class('btn', button_class)
    if button_type:
        if button_type == 'submit':
            attrs['class'] = add_css_class(attrs['class'], 'btn-primary')
        elif button_type != 'reset' and button_type != 'button':
            raise BootstrapError('Parameter "button_type" should be "submit", "reset", "button" or empty.')
        attrs['type'] = button_type
    icon_content = render_icon(icon) if icon else ''
    return render_tag('button', attrs=attrs, content=text_concat(icon_content, content, separator=' '))


def render_field_and_label(field, label, field_class='', label_for=None, label_class='', layout='', **kwargs):
    """
    Render a field with its label
    """
    if layout == 'horizontal':
        if not label_class:
            label_class = get_bootstrap_setting('horizontal_label_class')
        if not field_class:
            field_class = get_bootstrap_setting('horizontal_field_class')
        if not label:
            label = '&#160;'
        label_class = add_css_class(label_class, 'control-label')
    html = field
    if field_class:
        html = '<div class="{klass}">{html}</div>'.format(klass=field_class, html=html)
    if label:
        html = render_label(label, label_for=label_for, label_class=label_class) + html
    return html


def render_form_group(content, css_class=FORM_GROUP_CLASS):
    """
    Render a Bootstrap form group
    """
    return '<div class="{klass}">{content}</div>'.format(
        klass=css_class,
        content=content,
    )


def is_widget_required_attribute(widget):
    """
    Is this widget required?
    """
    if not get_bootstrap_setting('set_required'):
        return False
    if not widget.is_required:
        return False
    if isinstance(widget, (AdminFileWidget, HiddenInput, FileInput, CheckboxSelectMultiple)):
        return False
    return True


def is_widget_with_placeholder(widget):
    """
    Is this a widget that should have a placeholder?
    Only text, search, url, tel, e-mail, password, number have placeholders
    These are all derived form TextInput, except for Textarea
    """
    return isinstance(widget, (TextInput, Textarea))


########NEW FILE########
__FILENAME__ = html
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.forms.widgets import flatatt

from .text import text_value


# Handle HTML and CSS manipulation


def split_css_classes(css_classes):
    """
    Turn string into a list of CSS classes
    """
    classes_list = text_value(css_classes).split(' ')
    return [c for c in classes_list if c]


def add_css_class(css_classes, css_class):
    """
    Add a CSS class to a string of CSS classes
    """
    classes_list = split_css_classes(css_classes)
    for c in split_css_classes(css_class):
        if c not in classes_list:
            classes_list.append(c)
    return ' '.join(classes_list)


def remove_css_class(css_classes, css_class):
    """
    Remove a CSS class from a string of CSS classes
    """
    remove = set(split_css_classes(css_class))
    classes_list = [c for c in split_css_classes(css_classes) if c not in remove]
    return ' '.join(classes_list)


def render_link_tag(url, rel='stylesheet', media='all'):
    """
    Build a link tag
    """
    return render_tag('link', attrs = {'href': url, 'rel': rel, 'media': media}, close=False)


def render_tag(tag, attrs=None, content=None, close=True):
    """
    Render a HTML tag
    """
    builder = '<{tag}{attrs}>{content}'
    if content or close:
        builder += '</{tag}>'
    return builder.format(
        tag=tag,
        attrs=flatatt(attrs) if attrs else '',
        content=text_value(content),
    )

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

# Empty models.py, required file for Django tests

########NEW FILE########
__FILENAME__ = renderers
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.forms import (TextInput, DateInput, FileInput, CheckboxInput,
                          ClearableFileInput, Select, RadioSelect, CheckboxSelectMultiple)
from django.forms.extras import SelectDateWidget
from django.forms.forms import BaseForm, BoundField
from django.forms.formsets import BaseFormSet
from django.utils.html import conditional_escape, strip_tags
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from .bootstrap import get_bootstrap_setting
from .text import text_value
from .exceptions import BootstrapError
from .html import add_css_class
from .forms import (render_form, render_field, render_label, render_form_group,
                    is_widget_with_placeholder, is_widget_required_attribute, FORM_GROUP_CLASS)


class FormsetRenderer(object):
    """
    Default formset renderer
    """

    def __init__(self, formset, layout='', form_group_class=FORM_GROUP_CLASS,
                 field_class='', label_class='', show_help=True, exclude='',
                 set_required=True):
        if not isinstance(formset, BaseFormSet):
            raise BootstrapError(
                'Parameter "formset" should contain a valid Django Formset.')
        self.formset = formset
        self.layout = layout
        self.form_group_class = form_group_class
        self.field_class = field_class
        self.label_class = label_class
        self.show_help = show_help
        self.exclude = exclude
        self.set_required = set_required

    def render_forms(self):
        rendered_forms = []
        for form in self.formset.forms:
            rendered_forms.append(render_form(
                form,
                layout=self.layout,
                form_group_class=self.form_group_class,
                field_class=self.field_class,
                label_class=self.label_class,
                show_help=self.show_help,
                exclude=self.exclude,
                set_required=self.set_required,
            ))
        return '\n'.join(rendered_forms)

    def get_formset_errors(self):
        return self.formset.non_form_errors()

    def render_errors(self):
        formset_errors = self.get_formset_errors()
        if formset_errors:
            return get_template(
                'bootstrap3/form_errors.html').render(Context({
                'errors': formset_errors,
                'form': self.formset,
                'layout': self.layout,
            }))
        return ''

    def render(self):
        return self.render_errors() + self.render_forms()



class FormRenderer(object):
    """
    Default form renderer
    """

    def __init__(self, form, layout='', form_group_class=FORM_GROUP_CLASS,
                 field_class='', label_class='', show_help=True, exclude='',
                 set_required=True):
        if not isinstance(form, BaseForm):
            raise BootstrapError('Parameter "form" should contain a valid Django Form.')
        self.form = form
        self.layout = layout
        self.form_group_class = form_group_class
        self.field_class = field_class
        self.label_class = label_class
        self.show_help = show_help
        self.exclude = exclude
        self.set_required = set_required

    def render_fields(self):
        rendered_fields = []
        for field in self.form:
            rendered_fields.append(render_field(
                field,
                layout=self.layout,
                form_group_class=self.form_group_class,
                field_class=self.field_class,
                label_class=self.label_class,
                show_help=self.show_help,
                exclude=self.exclude,
                set_required=self.set_required,
            ))
        return '\n'.join(rendered_fields)

    def get_fields_errors(self):
        form_errors = []
        for field in self.form:
            if field.is_hidden and field.errors:
                form_errors += field.errors
        return form_errors

    def render_errors(self, type='all'):
        form_errors = None
        if type == 'all':
            form_errors = self.get_fields_errors() + self.form.non_field_errors()
        elif type == 'fields':
            form_errors = self.get_fields_errors()
        elif type == 'non_fields':
            form_errors = self.form.non_field_errors()

        if form_errors:
            return get_template(
                'bootstrap3/form_errors.html').render(Context({
                    'errors': form_errors,
                    'form': self.form,
                    'layout': self.layout,
                }))
        return ''

    def render(self):
        return self.render_errors() + self.render_fields()


class FieldRenderer(object):
    """
    Default field renderer
    """

    def __init__(self, field, layout='', form_group_class=FORM_GROUP_CLASS,
                 field_class=None, label_class=None, show_label=True,
                 show_help=True, exclude='', set_required=True,
                 addon_before=None, addon_after=None,
                 error_css_class='', required_css_class=''):
        # Only allow BoundField
        if not isinstance(field, BoundField):
            raise BootstrapError('Parameter "field" should contain a valid Django BoundField.')

        self.field = field
        self.layout = layout
        self.form_group_class = form_group_class
        self.field_class = field_class
        self.label_class = label_class
        self.show_label = show_label
        self.exclude = exclude
        self.set_required = set_required
        self.widget = field.field.widget
        self.initial_attrs = self.widget.attrs.copy()
        self.field_help = text_value(mark_safe(field.help_text)) if show_help and field.help_text else ''
        self.field_errors = [conditional_escape(text_value(error)) for error in field.errors]
        self.placeholder = field.label
        self.addon_before = addon_before
        self.addon_after = addon_after

        # These are set in Django or in the global BOOTSTRAP3 settings, and they can be overwritten in the template
        if error_css_class:
            self.form_error_class = error_css_class
        else:
            self.form_error_class = getattr(field.form, 'error_css_class', get_bootstrap_setting('error_css_class'))
        if required_css_class:
            self.form_required_class = required_css_class
        else:
            self.form_required_class = getattr(field.form, 'required_css_class',  get_bootstrap_setting('required_css_class'))

    def restore_widget_attrs(self):
        self.widget.attrs = self.initial_attrs

    def add_class_attrs(self):
        self.widget.attrs['class'] = self.widget.attrs.get('class', '')
        if not isinstance(self.widget, (CheckboxInput,
                                        RadioSelect,
                                        CheckboxSelectMultiple,
                                        FileInput)):
            self.widget.attrs['class'] = add_css_class(
                self.widget.attrs['class'], 'form-control')

    def add_placeholder_attrs(self):
        placeholder = self.widget.attrs.get('placeholder', self.placeholder)
        if placeholder and is_widget_with_placeholder(self.widget):
            self.widget.attrs['placeholder'] = placeholder

    def add_help_attrs(self):
        title = self.widget.attrs.get('title', strip_tags(self.field_help))
        if not isinstance(self.widget, CheckboxInput):
            self.widget.attrs['title'] = title

    def add_required_attrs(self):
        if self.set_required and is_widget_required_attribute(self.widget):
            self.widget.attrs['required'] = 'required'

    def add_widget_attrs(self):
        self.add_class_attrs()
        self.add_placeholder_attrs()
        self.add_help_attrs()
        self.add_required_attrs()

    def list_to_class(self, html, klass):
        mapping = [
            ('<ul', '<div'),
            ('</ul>', '</div>'),
            ('<li', '<div class="{klass}"'.format(klass=klass)),
            ('</li>', '</div>'),
        ]
        for k, v in mapping:
            html = html.replace(k, v)
        return html

    def put_inside_label(self, html):
        content = '{field} {label}'.format(field=html, label=self.field.label)
        return render_label(content=content, label_for=self.field.id_for_label, label_title=strip_tags(self.field_help))

    def fix_date_select_input(self, html):
        div1 = '<div class="col-xs-4">'
        div2 = '</div>'
        html = html.replace('<select', div1 + '<select')
        html = html.replace('</select>', '</select>' + div2)
        return '<div class="row bootstrap3-multi-input">' + html + '</div>'

    def fix_clearable_file_input(self, html):
        """
        Fix a clearable file input
        TODO: This needs improvement

        Currently Django returns
        Currently: <a href="dummy.txt">dummy.txt</a> <input id="file4-clear_id" name="file4-clear" type="checkbox" /> <label for="file4-clear_id">Clear</label><br />Change: <input id="id_file4" name="file4" type="file" /><span class=help-block></span></div>

        """
        # TODO This needs improvement
        return '<div class="row bootstrap3-multi-input"><div class="col-xs-12">' + html + '</div></div>'

    def post_widget_render(self, html):
        if isinstance(self.widget, RadioSelect):
            html = self.list_to_class(html, 'radio')
        elif isinstance(self.widget, CheckboxSelectMultiple):
            html = self.list_to_class(html, 'checkbox')
        elif isinstance(self.widget, SelectDateWidget):
            html = self.fix_date_select_input(html)
        elif isinstance(self.widget, ClearableFileInput):
            html = self.fix_clearable_file_input(html)
        elif isinstance(self.widget, CheckboxInput):
            html = self.put_inside_label(html)
        return html

    def wrap_widget(self, html):
        if isinstance(self.widget, CheckboxInput):
            html = '<div class="checkbox">{content}</div>'.format(content=html)
        return html

    def make_input_group(self, html):
        if ((self.addon_before or self.addon_after) and
                isinstance(self.widget, (TextInput, DateInput, Select))
        ):
            before = '<span class="input-group-addon">{addon}</span>'.format(
                addon=self.addon_before) if self.addon_before else ''
            after = '<span class="input-group-addon">{addon}</span>'.format(
                addon=self.addon_after) if self.addon_after else ''
            html = '<div class="input-group">{before}{html}{after}</div>'.format(
                before=before, after=after, html=html)
        return html

    def append_to_field(self, html):
        help_text_and_errors = [self.field_help] + self.field_errors \
            if self.field_help else self.field_errors
        if help_text_and_errors:
            help_html = get_template(
                'bootstrap3/field_help_text_and_errors.html').render(Context({
                'field': self.field,
                'help_text_and_errors': help_text_and_errors,
                'layout': self.layout,
            }))
            html += '<span class="help-block">{help}</span>'.format(help=help_html)
        return html

    def get_field_class(self):
        field_class = self.field_class
        if not field_class and self.layout == 'horizontal':
            field_class = get_bootstrap_setting('horizontal_field_class')
        return field_class

    def wrap_field(self, html):
        field_class = self.get_field_class()
        if field_class:
            html = '<div class="{klass}">{html}</div>'.format(klass=field_class, html=html)
        return html

    def get_label_class(self):
        label_class = self.label_class
        if not label_class and self.layout == 'horizontal':
            label_class = get_bootstrap_setting('horizontal_label_class')
        label_class = text_value(label_class)
        if not self.show_label:
            label_class = add_css_class(label_class, 'sr-only')
        return add_css_class(label_class, 'control-label')

    def get_label(self):
        if isinstance(self.widget, CheckboxInput):
            label = None
        else:
            label = self.field.label
        if self.layout == 'horizontal' and not label:
            return '&#160;'
        return label

    def add_label(self, html):
        label = self.get_label()
        if label:
            html = render_label(label, label_for=self.field.id_for_label, label_class=self.get_label_class()) + html
        return html

    def get_form_group_class(self):
        form_group_class = self.form_group_class
        if self.field.errors and self.form_error_class:
            form_group_class = add_css_class(
                form_group_class, self.form_error_class)
        if self.field.field.required and self.form_required_class:
            form_group_class = add_css_class(
                form_group_class, self.form_required_class)
        if self.field_errors:
            form_group_class = add_css_class(form_group_class, 'has-error')
        elif self.field.form.is_bound:
            form_group_class = add_css_class(form_group_class, 'has-success')
        return form_group_class

    def wrap_label_and_field(self, html):
        return render_form_group(html, self.get_form_group_class())

    def render(self):
        # See if we're not excluded
        if self.field.name in self.exclude.replace(' ', '').split(','):
            return ''
        # Hidden input requires no special treatment
        if self.field.is_hidden:
            return text_value(self.field)
        self.add_widget_attrs()
        html = self.field.as_widget(attrs=self.widget.attrs)
        self.restore_widget_attrs()
        html = self.post_widget_render(html)
        html = self.wrap_widget(html)
        html = self.make_input_group(html)
        html = self.append_to_field(html)
        html = self.wrap_field(html)
        html = self.add_label(html)
        html = self.wrap_label_and_field(html)
        return html


class InlineFieldRenderer(FieldRenderer):
    """
    Inline field renderer
    """

    def add_error_attrs(self):
        field_title = self.widget.attrs.get('title', '')
        field_title += ' ' + ' '.join([strip_tags(e) for e in self.field_errors])
        self.widget.attrs['title'] = field_title.strip()

    def add_widget_attrs(self):
        super(InlineFieldRenderer, self).add_widget_attrs()
        self.add_error_attrs()

    def append_to_field(self, html):
        return html

    def get_field_class(self):
        return self.field_class

    def get_label_class(self):
        return add_css_class(self.label_class, 'sr-only')

########NEW FILE########
__FILENAME__ = templates
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.template import Variable, VariableDoesNotExist
from django.template.base import FilterExpression, kwarg_re, TemplateSyntaxError

# Extra features for template file handling

QUOTED_STRING = re.compile(r'^["\'](?P<noquotes>.+)["\']$')


def handle_var(value, context):
    # Resolve FilterExpression and Variable immediately
    if isinstance(value, FilterExpression) or isinstance(value, Variable):
        return value.resolve(context)
    # Return quoted strings unquotes, from djangosnippets.org/snippets/886
    stringval = QUOTED_STRING.search(value)
    if stringval:
        return stringval.group('noquotes')
    # Resolve variable or return string value
    try:
        return Variable(value).resolve(context)
    except VariableDoesNotExist:
        return value


def parse_token_contents(parser, token):
    bits = token.split_contents()
    tag = bits.pop(0)
    args = []
    kwargs = {}
    asvar = None
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)
            if not match:
                raise TemplateSyntaxError(
                    'Malformed arguments to tag "{}"'.format(tag))
            name, value = match.groups()
            if name:
                kwargs[name] = parser.compile_filter(value)
            else:
                args.append(parser.compile_filter(value))
    return {
        'tag': tag,
        'args': args,
        'kwargs': kwargs,
        'asvar': asvar,
    }

########NEW FILE########
__FILENAME__ = bootstrap3
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from math import floor

from django import template
from django.template.loader import get_template

from ..bootstrap import css_url, javascript_url, jquery_url, theme_url, get_bootstrap_setting
from ..html import render_link_tag
from ..forms import render_button, render_field, render_field_and_label, render_form, render_form_group, render_formset, \
    render_label, render_form_errors, render_formset_errors
from ..components import render_icon, render_alert
from ..templates import handle_var, parse_token_contents
from ..text import force_text


register = template.Library()


@register.filter
def bootstrap_setting(value):
    """
    A simple way to read bootstrap settings in a template.
    Please consider this filter private for now, do not use it in your own templates.
    """
    return get_bootstrap_setting(value)


@register.simple_tag
def bootstrap_jquery_url():
    """
    **Tag name**::

        bootstrap_jquery_url

    Return the full url to jQuery file to use

    Default value: ``//code.jquery.com/jquery.min.js``

    This value is configurable, see Settings section

    **usage**::

        {% bootstrap_jquery_url %}

    **example**::

        {% bootstrap_jquery_url %}
    """
    return jquery_url()


@register.simple_tag
def bootstrap_javascript_url():
    """
    Return the full url to the Bootstrap JavaScript library

    Default value: ``None``

    This value is configurable, see Settings section

    **Tag name**::

        bootstrap_javascript_url

    **usage**::

        {% bootstrap_javascript_url %}

    **example**::

        {% bootstrap_javascript_url %}
    """
    return javascript_url()


@register.simple_tag
def bootstrap_css_url():
    """
    Return the full url to the Bootstrap CSS library

    Default value: ``None``

    This value is configurable, see Settings section

    **Tag name**::

        bootstrap_css_url

    **usage**::

        {% bootstrap_css_url %}

    **example**::

        {% bootstrap_css_url %}
    """
    return css_url()


@register.simple_tag
def bootstrap_theme_url():
    """
    Return the full url to a Bootstrap theme CSS library

    Default value: ``None``

    This value is configurable, see Settings section

    **Tag name**::

        bootstrap_css_url

    **usage**::

        {% bootstrap_css_url %}

    **example**::

        {% bootstrap_css_url %}
    """
    return theme_url()


@register.simple_tag
def bootstrap_css():
    """
    Return HTML for Bootstrap CSS
    Adjust url in settings. If no url is returned, we don't want this statement to return any HTML.
    This is intended behavior.

    Default value: ``FIXTHIS``

    This value is configurable, see Settings section

    **Tag name**::

        bootstrap_css

    **usage**::

        {% bootstrap_css %}

    **example**::

        {% bootstrap_css %}
    """
    urls = [url for url in [bootstrap_css_url(), bootstrap_theme_url()] if url]
    return ''.join([render_link_tag(url, media='screen') for url in urls])


@register.simple_tag
def bootstrap_javascript(jquery=None):
    """
    Return HTML for Bootstrap JavaScript
    Adjust url in settings. If no url is returned, we don't want this statement to return any HTML.
    This is intended behavior.

    Default value: ``None``

    This value is configurable, see Settings section

    **Tag name**::

        bootstrap_javascript

    **Parameters**:

        :jquery: Truthy to include jQuery as well as Bootstrap

    **usage**::

        {% bootstrap_javascript %}

    **example**::

        {% bootstrap_javascript jquery=1 %}
    """

    javascript = ''
    # See if we have to include jQuery
    if jquery is None:
        jquery = get_bootstrap_setting('include_jquery', False)
    # NOTE: No async on scripts, not mature enough. See issue #52 and #56
    if jquery:
        url = bootstrap_jquery_url()
        if url:
            javascript += '<script src="{url}"></script>'.format(url=url)
    url = bootstrap_javascript_url()
    if url:
        javascript += '<script src="{url}"></script>'.format(url=url)
    return javascript


@register.simple_tag
def bootstrap_formset(*args, **kwargs):
    """
    Render a formset


    **Tag name**::

        bootstrap_formset

    **Parameters**:

        :args:
        :kwargs:

    **usage**::

        {% bootstrap_formset formset %}

    **example**::

        {% bootstrap_formset formset layout='horizontal' %}

    """
    return render_formset(*args, **kwargs)


@register.simple_tag
def bootstrap_formset_errors(*args, **kwargs):
    """
    Render form errors

    **Tag name**::

        bootstrap_form_errors

    **Parameters**:

        :args:
        :kwargs:

    **usage**::

        {% bootstrap_form_errors form %}

    **example**::

        {% bootstrap_form_errors form layout='inline' %}
    """
    return render_formset_errors(*args, **kwargs)


@register.simple_tag
def bootstrap_form(*args, **kwargs):
    """
    Render a form

    **Tag name**::

        bootstrap_form

    **Parameters**:

        :args:
        :kwargs:

    **usage**::

        {% bootstrap_form form %}

    **example**::

        {% bootstrap_form form layout='inline' %}
    """
    return render_form(*args, **kwargs)


@register.simple_tag
def bootstrap_form_errors(*args, **kwargs):
    """
    Render form errors

    **Tag name**::

        bootstrap_form_errors

    **Parameters**:

        :args:
        :kwargs:

    **usage**::

        {% bootstrap_form_errors form %}

    **example**::

        {% bootstrap_form_errors form layout='inline' %}
    """
    return render_form_errors(*args, **kwargs)


@register.simple_tag
def bootstrap_field(*args, **kwargs):
    """
    Render a field

    **Tag name**::

        bootstrap_field

    **Parameters**:

        :args:
        :kwargs:

    **usage**::

        {% bootstrap_field form_field %}

    **example**::

        {% bootstrap_form form_field FIXTHIS %}
    """
    return render_field(*args, **kwargs)


@register.simple_tag()
def bootstrap_label(*args, **kwargs):
    """
    Render a label

    **Tag name**::

        bootstrap_label

    **Parameters**:

        :args:
        :kwargs:

    **usage**::

        {% bootstrap_label FIXTHIS %}

    **example**::

        {% bootstrap_label FIXTHIS %}
    """
    return render_label(*args, **kwargs)


@register.simple_tag
def bootstrap_button(*args, **kwargs):
    """
    Render a button

    **Tag name**::

        bootstrap_button

    **Parameters**:

        :args:
        :kwargs:

    **usage**::

        {% bootstrap_button FIXTHIS %}

    **example**::

        {% bootstrap_button FIXTHIS %}
    """
    return render_button(*args, **kwargs)


@register.simple_tag
def bootstrap_icon(icon):
    """
    Render an icon

    **Tag name**::

        bootstrap_icon

    **Parameters**:

        :icon: icon name

    **usage**::

        {% bootstrap_icon "icon_name" %}

    **example**::

        {% bootstrap_icon "star" %}

    """
    return render_icon(icon)


@register.simple_tag
def bootstrap_alert(content, alert_type='info', dismissable=True):
    """
    Render an alert

    **Tag name**::

        bootstrap_alert

    **Parameters**:

        :content: HTML content of alert
        :alert_type: one of 'info', 'warning', 'danger' or 'success'
        :dismissable: boolean, is alert dismissable

    **usage**::

        {% bootstrap_alert "my_content" %}

    **example**::

        {% bootstrap_alert "Something went wrong" alert_type='error' %}

    """
    return render_alert(content, alert_type, dismissable)


@register.tag('buttons')
def bootstrap_buttons(parser, token):
    """
    Render buttons for form

    **Tag name**::

        bootstrap_buttons

    **Parameters**:

        :parser:
        :token:

    **usage**::

        {% bootstrap_buttons FIXTHIS %}

    **example**::

        {% bootstrap_buttons FIXTHIS %}
    """
    kwargs = parse_token_contents(parser, token)
    kwargs['nodelist'] = parser.parse(('endbuttons', ))
    parser.delete_first_token()
    return ButtonsNode(**kwargs)


class ButtonsNode(template.Node):
    def __init__(self, nodelist, args, kwargs, asvar, **kwargs2):
        self.nodelist = nodelist
        self.args = args
        self.kwargs = kwargs
        self.asvar = asvar

    def render(self, context):
        output_kwargs = {}
        for key in self.kwargs:
            output_kwargs[key] = handle_var(self.kwargs[key], context)
        buttons = []
        submit = output_kwargs.get('submit', None)
        reset = output_kwargs.get('reset', None)
        if submit:
            buttons.append(bootstrap_button(submit, 'submit'))
        if reset:
            buttons.append(bootstrap_button(reset, 'reset'))
        buttons = ' '.join(buttons) + self.nodelist.render(context)
        output_kwargs.update({
            'label': None,
            'field': buttons,
        })
        output = render_form_group(render_field_and_label(**output_kwargs))
        if self.asvar:
            context[self.asvar] = output
            return ''
        else:
            return output


@register.simple_tag(takes_context=True)
def bootstrap_messages(context, *args, **kwargs):
    """
    Show django.contrib.messages Messages in Bootstrap alert containers

    **Tag name**::

        bootstrap_messages

    **Parameters**:

        :context:
        :args:
        :kwargs:

    **usage**::

        {% bootstrap_messages FIXTHIS %}

    **example**::

        {% bootstrap_messages FIXTHIS %}

    """
    return get_template('bootstrap3/messages.html').render(context)


@register.inclusion_tag('bootstrap3/pagination.html')
def bootstrap_pagination(page, **kwargs):
    """
    Render pagination for a page

    **Tag name**::

        bootstrap_pagination

    **Parameters**:

        :page:
        :kwargs:

    **usage**::

        {% bootstrap_pagination FIXTHIS %}

    **example**::

        {% bootstrap_pagination FIXTHIS %}
    """

    pagination_kwargs = kwargs.copy()
    pagination_kwargs['page'] = page
    return get_pagination_context(**pagination_kwargs)


def get_pagination_context(page, pages_to_show=11,
                           url=None, size=None, extra=None):
    """
    Generate Bootstrap pagination context from a page object
    """
    pages_to_show = int(pages_to_show)
    if pages_to_show < 1:
        raise ValueError("Pagination pages_to_show should be a positive " +
                         "integer, you specified {pages}".format(pages=pages_to_show))
    num_pages = page.paginator.num_pages
    current_page = page.number
    half_page_num = int(floor(pages_to_show / 2)) - 1
    if half_page_num < 0:
        half_page_num = 0
    first_page = current_page - half_page_num
    if first_page <= 1:
        first_page = 1
    if first_page > 1:
        pages_back = first_page - half_page_num
        if pages_back < 1:
            pages_back = 1
    else:
        pages_back = None
    last_page = first_page + pages_to_show - 1
    if pages_back is None:
        last_page += 1
    if last_page > num_pages:
        last_page = num_pages
    if last_page < num_pages:
        pages_forward = last_page + half_page_num
        if pages_forward > num_pages:
            pages_forward = num_pages
    else:
        pages_forward = None
        if first_page > 1:
            first_page -= 1
        if pages_back is not None and pages_back > 1:
            pages_back -= 1
        else:
            pages_back = None
    pages_shown = []
    for i in range(first_page, last_page + 1):
        pages_shown.append(i)
        # Append proper character to url
    if url:
        # Remove existing page GET parameters
        url = force_text(url)
        url = re.sub(r'\?page\=[^\&]+', '?', url)
        url = re.sub(r'\&page\=[^\&]+', '', url)
        # Append proper separator
        if '?' in url:
            url += '&'
        else:
            url += '?'
            # Append extra string to url
    if extra:
        if not url:
            url = '?'
        url += force_text(extra) + '&'
    if url:
        url = url.replace('?&', '?')
    # Set CSS classes, see http://getbootstrap.com/components/#pagination
    pagination_css_classes = ['pagination']
    if size == 'small':
        pagination_css_classes.append('pagination-sm')
    elif size == 'large':
        pagination_css_classes.append('pagination-lg')
        # Build context object
    return {
        'bootstrap_pagination_url': url,
        'num_pages': num_pages,
        'current_page': current_page,
        'first_page': first_page,
        'last_page': last_page,
        'pages_shown': pages_shown,
        'pages_back': pages_back,
        'pages_forward': pages_forward,
        'pagination_css_classes': ' '.join(pagination_css_classes),
    }

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template import Template, Context
from django.utils.unittest import TestCase

from .exceptions import BootstrapError


RADIO_CHOICES = (
    ('1', 'Radio 1'),
    ('2', 'Radio 2'),
)

MEDIA_CHOICES = (
    ('Audio', (
        ('vinyl', 'Vinyl'),
        ('cd', 'CD'),
    )
    ),
    ('Video', (
        ('vhs', 'VHS Tape'),
        ('dvd', 'DVD'),
    )
    ),
    ('unknown', 'Unknown'),
)


class TestForm(forms.Form):
    """
    Form with a variety of widgets to test bootstrap3 rendering.
    """
    date = forms.DateField(required=False)
    subject = forms.CharField(
        max_length=100,
        help_text='my_help_text',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'placeholdertest'}),
    )
    message = forms.CharField(required=False, help_text='<i>my_help_text</i>')
    sender = forms.EmailField(label='Sender © unicode')
    secret = forms.CharField(initial=42, widget=forms.HiddenInput)
    cc_myself = forms.BooleanField(required=False, help_text='You will get a copy in your mailbox.')
    select1 = forms.ChoiceField(choices=RADIO_CHOICES)
    select2 = forms.MultipleChoiceField(
        choices=RADIO_CHOICES,
        help_text='Check as many as you like.',
    )
    select3 = forms.ChoiceField(choices=MEDIA_CHOICES)
    select4 = forms.MultipleChoiceField(
        choices=MEDIA_CHOICES,
        help_text='Check as many as you like.',
    )
    category1 = forms.ChoiceField(choices=RADIO_CHOICES, widget=forms.RadioSelect)
    category2 = forms.MultipleChoiceField(
        choices=RADIO_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text='Check as many as you like.',
    )
    category3 = forms.ChoiceField(widget=forms.RadioSelect, choices=MEDIA_CHOICES)
    category4 = forms.MultipleChoiceField(
        choices=MEDIA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text='Check as many as you like.',
    )

    required_css_class = 'bootstrap3-req'

    def clean(self):
        cleaned_data = super(TestForm, self).clean()
        raise forms.ValidationError("This error was added to show the non field errors styling.")
        return cleaned_data


class TestFormWithoutRequiredClass(TestForm):
    required_css_class = ''


def render_template(text, **context_args):
    """
    Create a template ``text`` that first loads bootstrap3.
    """
    template = Template("{% load bootstrap3 %}" + text)
    if not 'form' in context_args:
        context_args['form'] = TestForm()
    return template.render(Context(context_args))


def render_formset(formset=None, **context_args):
    """
    Create a template that renders a formset
    """
    context_args['formset'] = formset
    return render_template('{% bootstrap_formset formset %}', **context_args)


def render_form(form=None, **context_args):
    """
    Create a template that renders a form
    """
    if form:
        context_args['form'] = form
    return render_template('{% bootstrap_form form %}', **context_args)


def render_form_field(field, **context_args):
    """
    Create a template that renders a field
    """
    form_field = 'form.%s' % field
    return render_template('{% bootstrap_field ' + form_field + ' %}', **context_args)


def render_field(field, **context_args):
    """
    Create a template that renders a field
    """
    context_args['field'] = field
    return render_template('{% bootstrap_field field %}', **context_args)


class SettingsTest(TestCase):
    def test_settings(self):
        from .bootstrap import BOOTSTRAP3

        self.assertTrue(BOOTSTRAP3)

    def test_settings_filter(self):
        res = render_template('{% load bootstrap3 %}{{ "form_required_class"|bootstrap_setting }}')
        self.assertEqual(res.strip(), 'bootstrap3-req')
        res = render_template(
            '{% load bootstrap3 %}{% if "javascript_in_head"|bootstrap_setting %}head{% else %}body{% endif %}')
        self.assertEqual(res.strip(), 'head')


class TemplateTest(TestCase):
    def test_empty_template(self):
        res = render_template('')
        self.assertEqual(res.strip(), '')

    def test_text_template(self):
        res = render_template('some text')
        self.assertEqual(res.strip(), 'some text')

    def test_bootstrap_template(self):
        template = Template((
            '{% extends "bootstrap3/bootstrap3.html" %}{% block bootstrap3_content %}test_bootstrap3_content{% endblock %}'))
        res = template.render(Context({}))
        self.assertIn('test_bootstrap3_content', res)

    def test_javascript_without_jquery(self):
        res = render_template('{% bootstrap_javascript jquery=0 %}')
        self.assertIn('bootstrap', res)
        self.assertNotIn('jquery', res)

    def test_javascript_with_jquery(self):
        res = render_template('{% bootstrap_javascript jquery=1 %}')
        self.assertIn('bootstrap', res)
        self.assertIn('jquery', res)


class FormSetTest(TestCase):
    def test_illegal_formset(self):
        with self.assertRaises(BootstrapError):
            render_formset(formset='illegal')


class FormTest(TestCase):
    def test_illegal_form(self):
        with self.assertRaises(BootstrapError):
            render_form(form='illegal')

    def test_field_names(self):
        form = TestForm()
        res = render_form(form)
        for field in form:
            self.assertIn('name="%s"' % field.name, res)

    def test_exclude(self):
        form = TestForm()
        res = render_template('{% bootstrap_form form exclude="cc_myself" %}', form=form)
        self.assertNotIn('cc_myself', res)

    def test_layout_horizontal(self):
        form = TestForm()
        res = render_template('{% bootstrap_form form layout="horizontal" %}', form=form)
        self.assertIn('col-md-2', res)
        self.assertIn('col-md-4', res)

    def test_buttons_tag(self):
        form = TestForm()
        res = render_template('{% buttons layout="horizontal" %}{% endbuttons %}', form=form)
        self.assertIn('col-md-2', res)
        self.assertIn('col-md-4', res)


class FieldTest(TestCase):
    def test_illegal_field(self):
        with self.assertRaises(BootstrapError):
            render_field(field='illegal')

    def test_show_help(self):
        res = render_form_field('subject')
        self.assertIn('my_help_text', res)
        self.assertNotIn('<i>my_help_text</i>', res)
        res = render_template('{% bootstrap_field form.subject show_help=0 %}')
        self.assertNotIn('my_help_text', res)

    def test_subject(self):
        res = render_form_field('subject')
        self.assertIn('type="text"', res)
        self.assertIn('placeholder="placeholdertest"', res)

    def test_required_field(self):
        required_field = render_form_field('subject')
        self.assertIn('required', required_field)
        self.assertIn('bootstrap3-req', required_field)
        not_required_field = render_form_field('message')
        self.assertNotIn('required', not_required_field)
        # Required field with required=0
        form_field = 'form.subject'
        rendered = render_template('{% bootstrap_field ' + form_field + ' set_required=0 %}')
        self.assertNotIn('required', rendered)
        # Required settings in field
        form_field = 'form.subject'
        rendered = render_template('{% bootstrap_field ' + form_field + ' required_css_class="test-required" %}')
        self.assertIn('test-required', rendered)

    def test_input_group(self):
        res = render_template('{% bootstrap_field form.subject addon_before="$" addon_after=".00" %}')
        self.assertIn('class="input-group"', res)
        self.assertIn('class="input-group-addon">$', res)
        self.assertIn('class="input-group-addon">.00', res)


class ComponentsTest(TestCase):
    def test_icon(self):
        res = render_template('{% bootstrap_icon "star" %}')
        self.assertEqual(res.strip(), '<span class="glyphicon glyphicon-star"></span>')

    def test_alert(self):
        res = render_template('{% bootstrap_alert "content" alert_type="danger" %}')
        self.assertEqual(res.strip(), '<div class="alert alert-danger alert-dismissable"><button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>content</div>')


class MessagesTest(TestCase):
    def test_messages(self):
        class FakeMessage(object):
            """
            Follows the `django.contrib.messages.storage.base.Message` API.
            """

            def __init__(self, message, tags):
                self.tags = tags
                self.message = message

            def __str__(self):
                return self.message

        messages = [FakeMessage("hello", "warning")]
        res = render_template('{% bootstrap_messages messages %}', messages=messages)
        expected = """
    <div class="alert alert-warning alert-dismissable">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&#215;</button>
        hello
    </div>
"""
        self.assertEqual(res.strip(), expected.strip())

        messages = [FakeMessage("hello", "error")]
        res = render_template('{% bootstrap_messages messages %}', messages=messages)
        expected = """
    <div class="alert alert-danger alert-dismissable">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&#215;</button>
        hello
    </div>
        """
        self.assertEqual(res.strip(), expected.strip())

        messages = [FakeMessage("hello", None)]
        res = render_template('{% bootstrap_messages messages %}', messages=messages)
        expected = """
    <div class="alert alert-dismissable">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&#215;</button>
        hello
    </div>
"""
        self.assertEqual(res.strip(), expected.strip())

########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


def text_value(value):
    """
    Force a value to text, render None as an empty string
    """
    if value is None:
        return ''
    return force_text(value)


def text_concat(*args, **kwargs):
    """
    Concatenate several values as a text string with an optional separator
    """
    separator = text_value(kwargs.get('separator', ''))
    skip_empty = kwargs.get('skip_empty', False)
    values = [text_value(v) for v in args]
    if skip_empty:
        values = [v for v in values if v]
    return separator.join(values)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms.formsets import BaseFormSet, formset_factory


from bootstrap3.tests import TestForm

RADIO_CHOICES = (
    ('1', 'Radio 1'),
    ('2', 'Radio 2'),
)

MEDIA_CHOICES = (
    ('Audio', (
        ('vinyl', 'Vinyl'),
        ('cd', 'CD'),
    )
    ),
    ('Video', (
        ('vhs', 'VHS Tape'),
        ('dvd', 'DVD'),
    )
    ),
    ('unknown', 'Unknown'),
)


class ContactForm(TestForm):
    pass


class ContactBaseFormSet(BaseFormSet):
    def add_fields(self, form, index):
        super(ContactBaseFormSet, self).add_fields(form, index)

    def clean(self):
        super(ContactBaseFormSet, self).clean()
        raise forms.ValidationError("This error was added to show the non form errors styling")

ContactFormSet = formset_factory(TestForm, formset=ContactBaseFormSet,
                                 extra=2,
                                 max_num=4,
                                 validate_max=True)


class FilesForm(forms.Form):
    text1 = forms.CharField()
    file1 = forms.FileField()
    file2 = forms.FileField(required=False)
    file3 = forms.FileField(widget=forms.ClearableFileInput)
    file4 = forms.FileField(required=False, widget=forms.ClearableFileInput)


class ArticleForm(forms.Form):
    title = forms.CharField()
    pub_date = forms.DateField()

    def clean(self):
        cleaned_data = super(ArticleForm, self).clean()
        raise forms.ValidationError("This error was added to show the non field errors styling.")
        return cleaned_data

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Include BOOTSTRAP3_FOLDER in path
BOOTSTRAP3_FOLDER = os.path.abspath(os.path.join(PROJECT_ROOT, '..', 'bootstrap3'))
if BOOTSTRAP3_FOLDER not in sys.path:
    sys.path.insert(0, BOOTSTRAP3_FOLDER)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', ]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Amsterdam'

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
SECRET_KEY = '8s)l4^2s&&0*31-)+6lethmfy3#r1egh^6y^=b9@g!q63r649_'

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
)

ROOT_URLCONF = 'demo.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'demo.wsgi.application'

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
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'bootstrap3',
    'demo',
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

# Settings for django-bootstrap3
BOOTSTRAP3 = {
    'set_required': False,
    'form_error_class': 'bootstrap3-error',
    'form_required_class': 'bootstrap3-required',
    'javascript_in_head': True,
}

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import HomePageView, FormHorizontalView, FormInlineView, PaginationView, FormWithFilesView, \
    DefaultFormView, MiscView, DefaultFormsetView, DefaultFormByFieldView

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# urlpatterns = patterns('',
#     # Examples:
#     # url(r'^$', 'demo.views.home', name='home'),
#     # url(r'^demo/', include('demo.foo.urls')),
#
#     # Uncomment the admin/doc line below to enable admin documentation:
#     # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
#
#     # Uncomment the next line to enable the admin:
#     # url(r'^admin/', include(admin.site.urls)),
# )

urlpatterns = patterns('',
    url(r'^$', HomePageView.as_view(), name='home'),
    url(r'^formset$', DefaultFormsetView.as_view(), name='formset_default'),
    url(r'^form$', DefaultFormView.as_view(), name='form_default'),
    url(r'^form_by_field$', DefaultFormByFieldView.as_view(), name='form_by_field'),
    url(r'^form_horizontal$', FormHorizontalView.as_view(), name='form_horizontal'),
    url(r'^form_inline$', FormInlineView.as_view(), name='form_inline'),
    url(r'^form_with_files$', FormWithFilesView.as_view(), name='form_with_files'),
    url(r'^pagination$', PaginationView.as_view(), name='pagination'),
    url(r'^misc$', MiscView.as_view(), name='misc'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.files.storage import default_storage

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models.fields.files import FieldFile
from django.views.generic import FormView
from django.views.generic.base import TemplateView
from django.contrib import messages

from .forms import ContactForm, FilesForm, ContactFormSet


# http://yuji.wordpress.com/2013/01/30/django-form-field-in-initial-data-requires-a-fieldfile-instance/
class FakeField(object):
    storage = default_storage


fieldfile = FieldFile(None, FakeField, 'dummy.txt')


class HomePageView(TemplateView):
    template_name = 'demo/home.html'

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        messages.info(self.request, 'This is a demo of a message.')
        return context


class DefaultFormsetView(FormView):
    template_name = 'demo/formset.html'
    form_class = ContactFormSet


class DefaultFormView(FormView):
    template_name = 'demo/form.html'
    form_class = ContactForm


class DefaultFormByFieldView(FormView):
    template_name = 'demo/form_by_field.html'
    form_class = ContactForm


class FormHorizontalView(FormView):
    template_name = 'demo/form_horizontal.html'
    form_class = ContactForm


class FormInlineView(FormView):
    template_name = 'demo/form_inline.html'
    form_class = ContactForm


class FormWithFilesView(FormView):
    template_name = 'demo/form_with_files.html'
    form_class = FilesForm

    def get_context_data(self, **kwargs):
        context = super(FormWithFilesView, self).get_context_data(**kwargs)
        context['layout'] = self.request.GET.get('layout', 'vertical')
        return context

    def get_initial(self):
        return {
            'file4': fieldfile,
        }

class PaginationView(TemplateView):
    template_name = 'demo/pagination.html'

    def get_context_data(self, **kwargs):
        context = super(PaginationView, self).get_context_data(**kwargs)
        lines = []
        for i in range(10000):
            lines.append('Line %s' % (i + 1))
        paginator = Paginator(lines, 10)
        page = self.request.GET.get('page')
        try:
            show_lines = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            show_lines = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            show_lines = paginator.page(paginator.num_pages)
        context['lines'] = show_lines
        return context


class MiscView(TemplateView):
    template_name = 'demo/misc.html'


########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for django_bootstrap3 project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "demo.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

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
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# complexity documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  9 22:26:36 2013.
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
#sys.path.insert(0, os.path.abspath('.'))

sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'testsettings'


import bootstrap3

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-bootstrap3'
copyright = u'2014, Dylan Verheul'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = bootstrap3.__version__
# The full version, including alpha/beta/rc tags.
release = bootstrap3.__version__

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
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
# html_static_path = ['_static']

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
htmlhelp_basename = 'django-bootstrap3doc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-bootstrap3.tex', u'django-bootstrap3 Documentation',
   u'Dylan Verheul', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-bootstrap3', u'django-bootstrap3 Documentation',
     [u'Dylan Verheul'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-bootstrap3', u'django-bootstrap3 Documentation',
   u'Dylan Verheul', 'django-bootstrap3', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    try:
        import sphinx_rtd_theme
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    except:
        pass


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testsettings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = testsettings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'bootstrap3',
)

BOOTSTRAP3 = {
    'javascript_in_head': True,
    'form_required_class': 'bootstrap3-req',
}

SECRET_KEY = 'bootstrap3isawesome'

########NEW FILE########
