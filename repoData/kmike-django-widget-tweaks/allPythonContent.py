__FILENAME__ = runtests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from django.conf import settings
from django.core.management import call_command

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

settings.configure(
    INSTALLED_APPS=('widget_tweaks',),
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':MEMORY:',
        }
    }
)

if __name__ == "__main__":
    call_command('test', 'widget_tweaks')
########NEW FILE########
__FILENAME__ = models


########NEW FILE########
__FILENAME__ = widget_tweaks
import re
from django.template import Library, Node, Variable, TemplateSyntaxError
register = Library()


def silence_without_field(fn):
    def wrapped(field, attr):
        if not field:
            return ""
        return fn(field, attr)
    return wrapped


def _process_field_attributes(field, attr, process):

    # split attribute name and value from 'attr:value' string
    params = attr.split(':', 1)
    attribute = params[0]
    value = params[1] if len(params) == 2 else ''

    # decorate field.as_widget method with updated attributes
    old_as_widget = field.as_widget

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        attrs = attrs or {}
        process(widget or self.field.widget, attrs, attribute, value)
        return old_as_widget(widget, attrs, only_initial)

    bound_method = type(old_as_widget)
    try:
        field.as_widget = bound_method(as_widget, field, field.__class__)
    except TypeError:  # python 3
        field.as_widget = bound_method(as_widget, field)
    return field


@register.filter("attr")
@silence_without_field
def set_attr(field, attr):

    def process(widget, attrs, attribute, value):
        attrs[attribute] = value

    return _process_field_attributes(field, attr, process)


@register.filter("add_error_attr")
@silence_without_field
def add_error_attr(field, attr):
    if hasattr(field, 'errors') and field.errors:
        return set_attr(field, attr)
    return field


@register.filter("append_attr")
@silence_without_field
def append_attr(field, attr):
    def process(widget, attrs, attribute, value):
        if attrs.get(attribute):
            attrs[attribute] += ' ' + value
        elif widget.attrs.get(attribute):
            attrs[attribute] = widget.attrs[attribute] + ' ' + value
        else:
            attrs[attribute] = value
    return _process_field_attributes(field, attr, process)


@register.filter("add_class")
@silence_without_field
def add_class(field, css_class):
    return append_attr(field, 'class:' + css_class)


@register.filter("add_error_class")
@silence_without_field
def add_error_class(field, css_class):
    if hasattr(field, 'errors') and field.errors:
        return add_class(field, css_class)
    return field


@register.filter("set_data")
@silence_without_field
def set_data(field, data):
    return set_attr(field, 'data-' + data)


@register.filter(name='field_type')
def field_type(field):
    """
    Template filter that returns field class name (in lower case).
    E.g. if field is CharField then {{ field|field_type }} will
    return 'charfield'.
    """
    if hasattr(field, 'field') and field.field:
        return field.field.__class__.__name__.lower()
    return ''


@register.filter(name='widget_type')
def widget_type(field):
    """
    Template filter that returns field widget class name (in lower case).
    E.g. if field's widget is TextInput then {{ field|widget_type }} will
    return 'textinput'.
    """
    if hasattr(field, 'field') and hasattr(field.field, 'widget') and field.field.widget:
        return field.field.widget.__class__.__name__.lower()
    return ''


# ======================== render_field tag ==============================

ATTRIBUTE_RE = re.compile(r"""
    (?P<attr>
        [\w_-]+
    )
    (?P<sign>
        \+?=
    )
    (?P<value>
    ['"]? # start quote
        [^"']*
    ['"]? # end quote
    )
""", re.VERBOSE | re.UNICODE)

@register.tag
def render_field(parser, token):
    """
    Render a form field using given attribute-value pairs

    Takes form field as first argument and list of attribute-value pairs for
    all other arguments.  Attribute-value pairs should be in the form of
    attribute=value or attribute="a value" for assignment and attribute+=value
    or attribute+="value" for appending.
    """
    error_msg = '%r tag requires a form field followed by a list of attributes and values in the form attr="value"' % token.split_contents()[0]
    try:
        bits = token.split_contents()
        tag_name = bits[0]
        form_field = bits[1]
        attr_list = bits[2:]
    except ValueError:
        raise TemplateSyntaxError(error_msg)

    form_field = parser.compile_filter(form_field)

    set_attrs = []
    append_attrs = []
    for pair in attr_list:
        match = ATTRIBUTE_RE.match(pair)
        if not match:
            raise TemplateSyntaxError(error_msg + ": %s" % pair)
        dct = match.groupdict()
        attr, sign, value = dct['attr'], dct['sign'], parser.compile_filter(dct['value'])
        if sign == "=":
            set_attrs.append((attr, value))
        else:
            append_attrs.append((attr, value))

    return FieldAttributeNode(form_field, set_attrs, append_attrs)


class FieldAttributeNode(Node):
    def __init__(self, field, set_attrs, append_attrs):
        self.field = field
        self.set_attrs = set_attrs
        self.append_attrs = append_attrs

    def render(self, context):
        bounded_field = self.field.resolve(context)
        field = getattr(bounded_field, 'field', None)
        if (getattr(bounded_field, 'errors', None) and
            'WIDGET_ERROR_CLASS' in context):
            bounded_field = append_attr(bounded_field, 'class:%s' %
                                        context['WIDGET_ERROR_CLASS'])
        if field and field.required and 'WIDGET_REQUIRED_CLASS' in context:
            bounded_field = append_attr(bounded_field, 'class:%s' %
                                        context['WIDGET_REQUIRED_CLASS'])
        for k, v in self.set_attrs:
            bounded_field = set_attr(bounded_field, '%s:%s' % (k,v.resolve(context)))
        for k, v in self.append_attrs:
            bounded_field = append_attr(bounded_field, '%s:%s' % (k,v.resolve(context)))
        return bounded_field

########NEW FILE########
__FILENAME__ = tests
import string
try:
    from django.utils.unittest import expectedFailure
except ImportError:
    def expectedFailure(func):
        return lambda *args, **kwargs: None

from django.test import TestCase
from django.forms import Form, CharField, TextInput
from django import forms
from django.template import Template, Context
from django.forms.extras.widgets import SelectDateWidget

# ==============================
#       Testing helpers
# ==============================

class MyForm(Form):
    """
    Test form. If you want to test rendering of a field,
    add it to this form and use one of 'render_...' functions
    from this module.
    """
    simple = CharField()
    with_attrs = CharField(widget=TextInput(attrs={
                    'foo': 'baz',
                    'egg': 'spam'
                 }))
    with_cls = CharField(widget=TextInput(attrs={'class':'class0'}))
    date = forms.DateField(widget=SelectDateWidget(attrs={'egg': 'spam'}))


def render_form(text, form=None, **context_args):
    """
    Renders template ``text`` with widget_tweaks library loaded
    and MyForm instance available in context as ``form``.
    """
    tpl = Template("{% load widget_tweaks %}" + text)
    context_args.update({'form': MyForm() if form is None else form})
    context = Context(context_args)
    return tpl.render(context)


def render_field(field, template_filter, params, *args, **kwargs):
    """
    Renders ``field`` of MyForm with filter ``template_filter`` applied.
    ``params`` are filter arguments.

    If you want to apply several filters (in a chain),
    pass extra ``template_filter`` and ``params`` as positional arguments.

    In order to use custom form, pass form instance as ``form``
    keyword argument.
    """
    filters = [(template_filter, params)]
    filters.extend(zip(args[::2], args[1::2]))
    filter_strings = ['|%s:"%s"' % (f[0], f[1],) for f in filters]
    render_field_str = '{{ form.%s%s }}' % (field, ''.join(filter_strings))
    return render_form(render_field_str, **kwargs)


def render_field_from_tag(field, *attributes):
    """
    Renders MyForm's field ``field`` with attributes passed
    as positional arguments.
    """
    attr_strings = [' %s' % f for f in attributes]
    tpl = string.Template('{% render_field form.$field$attrs %}')
    render_field_str = tpl.substitute(field=field, attrs=''.join(attr_strings))
    return render_form(render_field_str)


def assertIn(value, obj):
    assert value in obj, "%s not in %s" % (value, obj,)


def assertNotIn(value, obj):
    assert value not in obj, "%s in %s" % (value, obj,)


# ===============================
#           Test cases
# ===============================

class SimpleAttrTest(TestCase):
    def test_attr(self):
        res = render_field('simple', 'attr', 'foo:bar')
        assertIn('type="text"', res)
        assertIn('name="simple"', res)
        assertIn('id="id_simple"', res)
        assertIn('foo="bar"', res)

    def test_attr_chaining(self):
        res = render_field('simple', 'attr', 'foo:bar', 'attr', 'bar:baz')
        assertIn('type="text"', res)
        assertIn('name="simple"', res)
        assertIn('id="id_simple"', res)
        assertIn('foo="bar"', res)
        assertIn('bar="baz"', res)

    def test_add_class(self):
        res = render_field('simple', 'add_class', 'foo')
        assertIn('class="foo"', res)

    def test_add_multiple_classes(self):
        res = render_field('simple', 'add_class', 'foo bar')
        assertIn('class="foo bar"', res)

    def test_add_class_chaining(self):
        res = render_field('simple', 'add_class', 'foo', 'add_class', 'bar')
        assertIn('class="bar foo"', res)

    def test_set_data(self):
        res = render_field('simple', 'set_data', 'key:value')
        assertIn('data-key="value"', res)


class ErrorsTest(TestCase):

    def _err_form(self):
        form = MyForm({'foo': 'bar'})  # some random data
        form.is_valid()  # trigger form validation
        return form

    def test_error_class_no_error(self):
        res = render_field('simple', 'add_error_class', 'err')
        assertNotIn('class="err"', res)

    def test_error_class_error(self):
        form = self._err_form()
        res = render_field('simple', 'add_error_class', 'err', form=form)
        assertIn('class="err"', res)

    def test_error_attr_no_error(self):
        res = render_field('simple', 'add_error_attr', 'aria-invalid:true')
        assertNotIn('aria-invalid="true"', res)

    def test_error_attr_error(self):
        form = self._err_form()
        res = render_field('simple', 'add_error_attr', 'aria-invalid:true', form=form)
        assertIn('aria-invalid="true"', res)


class SilenceTest(TestCase):
    def test_silence_without_field(self):
        res = render_field("nothing", 'attr', 'foo:bar')
        self.assertEqual(res, "")
        res = render_field("nothing", 'add_class', 'some')
        self.assertEqual(res, "")


class CustomizedWidgetTest(TestCase):
    def test_attr(self):
        res = render_field('with_attrs', 'attr', 'foo:bar')
        assertIn('foo="bar"', res)
        assertNotIn('foo="baz"', res)
        assertIn('egg="spam"', res)

    # see https://code.djangoproject.com/ticket/16754
    @expectedFailure
    def test_selectdatewidget(self):
        res = render_field('date', 'attr', 'foo:bar')
        assertIn('egg="spam"', res)
        assertIn('foo="bar"', res)

    def test_attr_chaining(self):
        res = render_field('with_attrs', 'attr', 'foo:bar', 'attr', 'bar:baz')
        assertIn('foo="bar"', res)
        assertNotIn('foo="baz"', res)
        assertIn('egg="spam"', res)
        assertIn('bar="baz"', res)

    def test_attr_class(self):
        res = render_field('with_cls', 'attr', 'foo:bar')
        assertIn('foo="bar"', res)
        assertIn('class="class0"', res)

    def test_default_attr(self):
        res = render_field('with_cls', 'attr', 'type:search')
        assertIn('class="class0"', res)
        assertIn('type="search"', res)

    def test_add_class(self):
        res = render_field('with_cls', 'add_class', 'class1')
        assertIn('class0', res)
        assertIn('class1', res)

    def test_add_class_chaining(self):
        res = render_field('with_cls', 'add_class', 'class1', 'add_class', 'class2')
        assertIn('class0', res)
        assertIn('class1', res)
        assertIn('class2', res)


class FieldReuseTest(TestCase):

    def test_field_double_rendering_simple(self):
        res = render_form('{{ form.simple }}{{ form.simple|attr:"foo:bar" }}{{ form.simple }}')
        self.assertEqual(res.count("bar"), 1)

    def test_field_double_rendering_simple_css(self):
        res = render_form('{{ form.simple }}{{ form.simple|add_class:"bar" }}{{ form.simple|add_class:"baz" }}')
        self.assertEqual(res.count("baz"), 1)
        self.assertEqual(res.count("bar"), 1)

    def test_field_double_rendering_attrs(self):
        res = render_form('{{ form.with_cls }}{{ form.with_cls|add_class:"bar" }}{{ form.with_cls }}')
        self.assertEqual(res.count("class0"), 3)
        self.assertEqual(res.count("bar"), 1)


class SimpleRenderFieldTagTest(TestCase):
    def test_attr(self):
        res = render_field_from_tag('simple', 'foo="bar"')
        assertIn('type="text"', res)
        assertIn('name="simple"', res)
        assertIn('id="id_simple"', res)
        assertIn('foo="bar"', res)

    def test_multiple_attrs(self):
        res = render_field_from_tag('simple', 'foo="bar"', 'bar="baz"')
        assertIn('type="text"', res)
        assertIn('name="simple"', res)
        assertIn('id="id_simple"', res)
        assertIn('foo="bar"', res)
        assertIn('bar="baz"', res)


class RenderFieldTagSilenceTest(TestCase):
    def test_silence_without_field(self):
        res = render_field_from_tag("nothing", 'foo="bar"')
        self.assertEqual(res, "")
        res = render_field_from_tag("nothing", 'class+="some"')
        self.assertEqual(res, "")


class RenderFieldTagCustomizedWidgetTest(TestCase):
    def test_attr(self):
        res = render_field_from_tag('with_attrs', 'foo="bar"')
        assertIn('foo="bar"', res)
        assertNotIn('foo="baz"', res)
        assertIn('egg="spam"', res)

    # see https://code.djangoproject.com/ticket/16754
    @expectedFailure
    def test_selectdatewidget(self):
        res = render_field_from_tag('date', 'foo="bar"')
        assertIn('egg="spam"', res)
        assertIn('foo="bar"', res)

    def test_multiple_attrs(self):
        res = render_field_from_tag('with_attrs', 'foo="bar"', 'bar="baz"')
        assertIn('foo="bar"', res)
        assertNotIn('foo="baz"', res)
        assertIn('egg="spam"', res)
        assertIn('bar="baz"', res)

    def test_attr_class(self):
        res = render_field_from_tag('with_cls', 'foo="bar"')
        assertIn('foo="bar"', res)
        assertIn('class="class0"', res)

    def test_default_attr(self):
        res = render_field_from_tag('with_cls', 'type="search"')
        assertIn('class="class0"', res)
        assertIn('type="search"', res)

    def test_append_attr(self):
        res = render_field_from_tag('with_cls', 'class+="class1"')
        assertIn('class0', res)
        assertIn('class1', res)

    def test_duplicate_append_attr(self):
        res = render_field_from_tag('with_cls', 'class+="class1"', 'class+="class2"')
        assertIn('class0', res)
        assertIn('class1', res)
        assertIn('class2', res)

    def test_hyphenated_attributes(self):
        res = render_field_from_tag('with_cls', 'data-foo="bar"')
        assertIn('data-foo="bar"', res)
        assertIn('class="class0"', res)


class RenderFieldWidgetClassesTest(TestCase):
    def test_use_widget_required_class(self):
        res = render_form('{% render_field form.simple %}',
                          WIDGET_REQUIRED_CLASS='required_class')
        assertIn('class="required_class"', res)

    def test_use_widget_error_class(self):
        res = render_form('{% render_field form.simple %}', form=MyForm({}),
                          WIDGET_ERROR_CLASS='error_class')
        assertIn('class="error_class"', res)

    def test_use_widget_error_class_with_other_classes(self):
        res = render_form('{% render_field form.simple class="blue" %}',
                          form=MyForm({}), WIDGET_ERROR_CLASS='error_class')
        assertIn('class="blue error_class"', res)

    def test_use_widget_required_class_with_other_classes(self):
        res = render_form('{% render_field form.simple class="blue" %}',
                          form=MyForm({}), WIDGET_REQUIRED_CLASS='required_class')
        assertIn('class="blue required_class"', res)


class RenderFieldTagFieldReuseTest(TestCase):
    def test_field_double_rendering_simple(self):
        res = render_form('{{ form.simple }}{% render_field form.simple foo="bar" %}{% render_field form.simple %}')
        self.assertEqual(res.count("bar"), 1)

    def test_field_double_rendering_simple_css(self):
        res = render_form('{% render_field form.simple %}{% render_field form.simple class+="bar" %}{% render_field form.simple class+="baz" %}')
        self.assertEqual(res.count("baz"), 1)
        self.assertEqual(res.count("bar"), 1)

    def test_field_double_rendering_attrs(self):
        res = render_form('{% render_field form.with_cls %}{% render_field form.with_cls class+="bar" %}{% render_field form.with_cls %}')
        self.assertEqual(res.count("class0"), 3)
        self.assertEqual(res.count("bar"), 1)


class RenderFieldTagUseTemplateVariableTest(TestCase):
    def test_use_template_variable_in_parametrs(self):
        res = render_form('{% render_field form.with_attrs egg+="pahaz" placeholder=form.with_attrs.label %}')
        assertIn('egg="spam pahaz"', res)
        assertIn('placeholder="With attrs"', res)


class RenderFieldFilter_field_type_widget_type_Test(TestCase):
    def test_field_type_widget_type_rendering_simple(self):
        res = render_form('<div class="{{ form.simple|field_type }} {{ form.simple|widget_type }} {{ form.simple.html_name }}">{{ form.simple }}</div>')
        assertIn('class="charfield textinput simple"', res)

########NEW FILE########
