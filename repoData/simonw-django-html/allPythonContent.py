__FILENAME__ = models

########NEW FILE########
__FILENAME__ = html
"""
{% doctype "html4" %}
{% doctype "html4" silent %} # set internal doctype but do NOT output it
{% doctype "html4trans" %}
{% doctype "html5" %}
{% doctype "xhtml1" %}
{% doctype "xhtml1trans" %}

{% field form.name %} # Outputs correct widget based on current doctype
{% field form.name class="my-form-class" %} # Adds an attribute
"""
import re

doctypes = {
  'html4': """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
    "http://www.w3.org/TR/html4/strict.dtd">""",
  'html4trans': """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">""",
  'xhtml1': """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">""",
  'xhtml1trans': """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">""",
  'html5': '<!DOCTYPE html>',
}
html_doctypes = ('html4', 'html5', 'html4trans')

from django import template
register = template.Library()

def do_doctype(parser, token):
    bits = token.split_contents()
    if len(bits) not in (2, 3):
        raise template.TemplateSyntaxError, \
            "%r tag requires 1-2 arguments" % bits[0]
    if len(bits) == 3 and bits[2] != 'silent':
        raise template.TemplateSyntaxError, \
            "If provided, %r tag second argument must be 'silent'" % bits[0]
    # If doctype is wrapped in quotes, they should balance
    doctype = bits[1]
    if doctype[0] in ('"', "'") and doctype[-1] != doctype[0]:
        raise template.TemplateSyntaxError, \
            "%r tag quotes need to balance" % bits[0]
    return DoctypeNode(bits[1], is_silent = (len(bits) == 3))

class DoctypeNode(template.Node):
    def __init__(self, doctype, is_silent=False):
        self.doctype = doctype
        self.is_silent = is_silent
    
    def render(self, context):
        if self.doctype[0] in ('"', "'"):
            doctype = self.doctype[1:-1]
        else:
            try:
                doctype = template.resolve_variable(self.doctype, context)
            except template.VariableDoesNotExist:
                # Cheeky! Assume that they typed a doctype without quotes
                doctype = self.doctype
        # Set doctype in the context
        context._doctype = doctype
        if self.is_silent:
            return ''
        else:
            return doctypes.get(doctype, '')

register.tag('doctype', do_doctype)

xhtml_end_re = re.compile('\s*/>')

class FieldNode(template.Node):
    def __init__(self, field_var, extra_attrs):
        self.field_var = field_var
        self.extra_attrs = extra_attrs
    
    def render(self, context):
        field = template.resolve_variable(self.field_var, context)
        # Caling bound_field.as_widget() returns the HTML, but we need to 
        # intercept this to manipulate the attributes - so we have to 
        # duplicate the logic from as_widget here.
        widget = field.field.widget
        attrs = self.extra_attrs or {}
        auto_id = field.auto_id
        if auto_id and 'id' not in attrs and 'id' not in widget.attrs:
            attrs['id'] = auto_id
        if not field.form.is_bound:
            data = field.form.initial.get(field.name, field.field.initial)
            if callable(data):
                data = data()
        else:
            data = field.data
        html = widget.render(field.html_name, data, attrs=attrs)
        # Finally, if we're NOT in xhtml mode ensure no '/>'
        doctype = getattr(context, '_doctype', 'xhtml1')
        if doctype in html_doctypes:
            html = xhtml_end_re.sub('>', html)
        return html

def do_field(parser, token):
    # Can't use split_contents here as we need to process 'class="foo"' etc
    bits = token.contents.split()
    if len(bits) == 1:
        raise template.TemplateSyntaxError, \
            "%r tag takes arguments" % bits[0]
    field_var = bits[1]
    extra_attrs = {}
    if len(bits) > 1:
        # There are extra name="value" arguments to consume
        extra_attrs = parse_extra_attrs(' '.join(bits[2:]))
    return FieldNode(field_var, extra_attrs)

register.tag('field', do_field)

class SlashNode(template.Node):
    def render(self, context):
        doctype = getattr(context, '_doctype', 'xhtml1')
        if doctype in html_doctypes:
            return ''
        else:
            return ' /'

def do_slash(parser, token):
    bits = token.contents.split()
    if len(bits) != 1:
        raise template.TemplateSyntaxError, \
            "%r tag takes no arguments" % bits[0]
    return SlashNode()

register.tag('slash', do_slash)

extra_attrs_re = re.compile(r'''([a-zA-Z][0-9a-zA-Z_-]*)="(.*?)"\s*''')

def parse_extra_attrs(contents):
    """
    Input should be 'foo="bar" baz="bat"' - output is corresponding dict. 
    Raises TemplateSyntaxError if something is wrong with the input.
    """
    unwanted = extra_attrs_re.sub('', contents)
    if unwanted.strip():
        raise template.TemplateSyntaxError, \
            "Invalid field tag arguments: '%s'" % unwanted.strip()
    return dict(extra_attrs_re.findall(contents))

########NEW FILE########
__FILENAME__ = tests
from django import template
from django import forms
from templatetags.html import doctypes, html_doctypes
import unittest

class TemplateTestHelper(unittest.TestCase):
    def assertRenders(self, template_string, expected, context = None):
        context = context or {}
        actual = template.Template(template_string).render(
            template.Context(context)
        )
        self.assertEqual(expected, actual)

class DoctypeTest(TemplateTestHelper):
    
    def test_doctype(self):
        'Doctype tag with one argument should output a doctype'
        for doctype in doctypes:
            t = '{% load html %}{% doctype "!!!" %}'.replace('!!!', doctype)
            self.assertRenders(t, doctypes[doctype])
        t = '{% load html %}{% doctype "html5" %}'
        self.assertRenders(t, '<!DOCTYPE html>')
    
    def test_doctype_variable(self):
        'Doctype tag can take a variable as well as a hard-coded string'
        t = '{% load html %}{% doctype foo %}'
        self.assertRenders(t, '<!DOCTYPE html>', {'foo': 'html5'})
        self.assertRenders(t, doctypes['xhtml1'], {'foo': 'xhtml1'})
    
    def test_doctype_silent(self):
        "Optional 'silent' argument should NOT output doctype"
        context = template.Context({})
        self.assert_(not hasattr(context, '_doctype'))
        actual = template.Template(
            '{% load html %}{% doctype "html5" silent %}'
        ).render(context)
        self.assertEqual(actual, '')
        self.assert_(hasattr(context, '_doctype'))
        self.assertEqual(context._doctype, 'html5')

class MyForm(forms.Form):
    name = forms.CharField()
    happy = forms.BooleanField()
    select = forms.ChoiceField(choices=(
        ('a', 'Ape'),
        ('b', 'Bun'),
        ('c', 'Cog')
    ))

expected_select = """<select name="select" id="id_select">
<option value="a">Ape</option>
<option value="b">Bun</option>
<option value="c">Cog</option>
</select>"""

class FieldTest(TemplateTestHelper):
    
    def test_field_no_doctype(self):
        'Field tag should output in XHTML if no doctype'
        self.assertRenders(
            '{% load html %}{% field form.name %}',
            '<input type="text" name="name" id="id_name" />',
            {'form': MyForm()}
        )
    
    def test_field_xhtml1(self):
        'Field tag should output in XHTML if XHTML doctype'
        self.assertRenders(
            '{%load html%}{% doctype "xhtml1" silent %}{% field form.name %}',
            '<input type="text" name="name" id="id_name" />',
            {'form': MyForm()}
        )
        self.assertRenders(
            '{%load html%}{%doctype "xhtml1" silent %}{% field form.happy %}',
            '<input type="checkbox" name="happy" id="id_happy" />',
            {'form': MyForm()}
        )
    
    def test_field_html4(self):
        'No XHTML trailing slash in HTML4 mode'
        self.assertRenders(
            '{%load html%}{% doctype "html4" silent %}{% field form.name %}',
            '<input type="text" name="name" id="id_name">',
            {'form': MyForm()}
        )
        self.assertRenders(
            '{%load html %}{% doctype "html4" silent%}{% field form.happy %}',
            '<input type="checkbox" name="happy" id="id_happy">',
            {'form': MyForm()}
        )
        self.assertRenders(
            '{%load html%}{%doctype "html4" silent %}{% field form.select %}',
            expected_select,
            {'form': MyForm()}
        )
    
    def assertHasAttrs(self, template_string, context, expected_attrs):
        'Order of attributes is not garuanteed, so use this instead'
        actual = template.Template(template_string).render(
            template.Context(context)
        )
        for (attr, value) in expected_attrs.items():
            attrstring = '%s="%s"' % (attr, value)
            self.assert_(
                (attrstring in actual),
                'Did not find %s in %s' % (attrstring, actual)
            )

    def test_field_extra_attrs(self):
        self.assertHasAttrs(
            '{% load html %}{% doctype "html4" silent %}' +
            '{% field form.name class="hello" %}',
            {'form': MyForm()},
            {'class': 'hello', 'id': 'id_name'}
        )
        self.assertHasAttrs(
            '{% load html %}{% doctype "html4" silent %}' +
            '{% field form.happy class="foo" %}',
            {'form': MyForm()},
            {'type': 'checkbox', 'class': 'foo', 'id': 'id_happy'}
        )
        self.assertHasAttrs(
            '{% load html %}{% doctype "html4" silent %}' +
            '{% field form.select class="foo" %}',
            {'form': MyForm()},
            {'name': 'select', 'class': 'foo', 'id': 'id_select'}
        )
        self.assertHasAttrs(
            '{% load html %}{% doctype "html4" silent %}' +
            '{% field form.select class="foo" id="hi" %}',
            {'form': MyForm()},
            {'name': 'select', 'class': 'foo', 'id': 'hi'}
        )

class SlashTest(TemplateTestHelper):
    def test_xhtml1(self):
        self.assertRenders(
            '{%load html%}{% doctype "xhtml1" silent %}<br{% slash %}>',
            '<br />', {}
        )
    
    def test_html4(self):
        self.assertRenders(
            '{%load html%}{% doctype "html4" silent %}<br{% slash %}>',
            '<br>', {}
        )

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
sys.path.append('..')
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
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'

TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

SECRET_KEY = 'mjq@mq5^gqzt*a6^0m)bt4%d)xur!)6b)^890vhsag42z@s!cp'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
)

ROOT_URLCONF = 'examples.urls'

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'django_html',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
)

########NEW FILE########
