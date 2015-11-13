__FILENAME__ = forms
import os
from django.template import Context,RequestContext
from django.template.loader import get_template, select_template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django import forms
from django.utils.encoding import force_unicode

class NoSuchFormField(Exception):
    """""The form field couldn't be resolved."""""
    pass

class BootstrapMixin(object):

    def __init__(self, *args, **kwargs):
        super(BootstrapMixin, self).__init__(*args, **kwargs)
        if hasattr(self, 'Meta') and hasattr(self.Meta, 'custom_fields'):
            self.custom_fields = self.Meta.custom_fields
        else:
            self.custom_fields = {}

        if hasattr(self, 'Meta') and hasattr(self.Meta, 'template_base'):
            self.template_base = self.Meta.template_base
        else:
            self.template_base = "bootstrap"

        if hasattr(self, 'Meta') and hasattr(self.Meta, 'help_style'):
            self.help_style = self.Meta.help_style
        else:
            self.help_style = "block"

    # For backward compatibility
    __bootstrap__ = __init__

    def top_errors_as_html(self):
        """ Render top errors as set of <div>'s. """
        return ''.join(["<div class=\"alert alert-error\">%s</div>" % error
                        for error in self.top_errors])

    def get_layout(self):
        """ Return the user-specified layout if one is available, otherwise
            build a default layout containing all fields.
        """
        if hasattr(self, 'Meta') and hasattr(self.Meta, 'layout'):
            return self.Meta.layout
        else:
            # Construct a simple layout using the keys from the fields
            return self.fields.keys()

    def as_div(self):
        """ Render the form as a set of <div>s. """

        self.top_errors = self.non_field_errors()
        self.prefix_fields = []

        output = self.render_fields(self.get_layout())

        if self.top_errors:
            errors = self.top_errors_as_html()
        else:
            errors = u''

        prefix = u''.join(self.prefix_fields)

        return mark_safe(prefix + errors + output)

    def render_fields(self, fields, separator=u""):
        """ Render a list of fields and join the fields by the value in separator. """

        output = []

        for field in fields:
            if isinstance(field, Fieldset):
                output.append(field.as_html(self))
            else:
                output.append(self.render_field(field))


        return separator.join(output)

    def render_field(self, field):
        """ Render a named field to HTML. """

        try:
            field_instance = self.fields[field]
        except KeyError:
            raise NoSuchFormField("Could not resolve form field '%s'." % field)

        bf = forms.forms.BoundField(self, field_instance, field)

        output = ''

        if bf.errors:
            # If the field contains errors, render the errors to a <ul>
            # using the error_list helper function.
            # bf_errors = error_list([escape(error) for error in bf.errors])
            bf_errors = ', '.join([e for e in bf.errors])
        else:
            bf_errors = ''

        if bf.is_hidden:
            # If the field is hidden, add it at the top of the form
            self.prefix_fields.append(unicode(bf))

            # If the hidden field has errors, append them to the top_errors
            # list which will be printed out at the top of form
            if bf_errors:
                self.top_errors.extend(bf.errors)

        else:

            # Find field + widget type css classes
            css_class = type(field_instance).__name__ + " " +  type(field_instance.widget).__name__

            # Add an extra class, Required, if applicable
            if field_instance.required:
                css_class += " required"

            if field_instance.help_text:
                # The field has a help_text, construct <span> tag
                help_text = '<span class="help-%s">%s</span>' % (self.help_style, force_unicode(field_instance.help_text))
            else:
                help_text = u''

            field_hash = {
                'class' : mark_safe(css_class),
                'label' : mark_safe(bf.label or ''),
                'help_text' :mark_safe(help_text),
                'field' : field_instance,
                'bf' : mark_safe(unicode(bf)),
                'bf_raw' : bf,
                'errors' : mark_safe(bf_errors),
                'field_type' : mark_safe(field.__class__.__name__),
                'label_id': bf._auto_id(),
            }

            if self.custom_fields.has_key(field):
                template = get_template(self.custom_fields[field])
            else:
                template = select_template([
                    os.path.join(self.template_base, 'field_%s.html' % type(field_instance.widget).__name__.lower()),
                    os.path.join(self.template_base, 'field_default.html'), ])

            # Finally render the field
            output = template.render(Context(field_hash))

        return mark_safe(output)

    def __unicode__(self):
        # Default output is now as <div> tags.
        return self.as_div()


class BootstrapForm(BootstrapMixin, forms.Form):
    pass


class BootstrapModelForm(BootstrapMixin, forms.ModelForm):
    pass


class Fieldset(object):
    """ Fieldset container. Renders to a <fieldset>. """

    def __init__(self, legend, *fields, **kwargs):
        self.legend = legend
        self.fields = fields
        self.css_class = kwargs.get('css_class', '_'.join(legend.lower().split()))

    def as_html(self, form):
        legend_html = self.legend and (u'<legend>%s</legend>' % self.legend) or ''
        return u'<fieldset class="%s">%s%s</fieldset>' % (self.css_class, legend_html, form.render_fields(self.fields))


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = runtests
import os, sys
from django.conf import settings

DIRNAME = os.path.dirname(__file__)
print settings.configured
settings.configure(DEBUG = True,
                   DATABASE_ENGINE = 'django.db.backends.sqlite3',
                   DATABASE_NAME = os.path.join(DIRNAME, 'database.db'),
                   INSTALLED_APPS = ('django.contrib.auth',
                                     'django.contrib.contenttypes',
                                     'django.contrib.sessions',
                                     'django.contrib.admin',
                                     'bootstrap',
                                     'bootstrap.tests',))


from django.test.simple import DjangoTestSuiteRunner

tr = DjangoTestSuiteRunner(verbosity=1)
failures = tr.run_tests(['bootstrap',])
if failures:
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django import forms
from forms import BootstrapForm, Fieldset

class LoginForm(BootstrapForm):
    class Meta:
        layout = (
            Fieldset("Please Login", "username", "password", ),
        )

    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


class InlineHelpForm(BootstrapForm):
    class Meta:
        help_style = "inline"
        layout = (
            Fieldset("Please Login", "username", "password", ),
        )

    username = forms.CharField(max_length=100, help_text="A username")
    password = forms.CharField(widget=forms.PasswordInput(), max_length=100)


class FormTests(TestCase):
    def test_form_fieldsets(self):
        """
        Tests that fieldsets are rendered properly.
        """
        expected = """<fieldset class="please_login"><legend>Please Login</legend><div id="div_id_username" class="control-group">
    <label class="control-label" for="id_username">Username</label>
    <div class="controls">
        <input id="id_username" type="text" name="username" maxlength="100" />
        
        
    </div>
</div> <!-- /clearfix -->
<div id="div_id_password" class="control-group">
    <label class="control-label" for="id_password">Password</label>
    <div class="controls">
        <input id="id_password" type="password" name="password" maxlength="100" />
        
        
    </div>
</div> <!-- /clearfix -->
</fieldset>"""
        form = LoginForm()
        self.assertEqual(str(form), expected)

    def test_help_inline(self):
        """
        Tests that inline help spans are rendered properly.
        """
        expected = """<fieldset class="please_login"><legend>Please Login</legend><div id="div_id_username" class="control-group">
    <label class="control-label" for="id_username">Username</label>
    <div class="controls">
        <input id="id_username" type="text" name="username" maxlength="100" />
        
        
        <span class="help-inline">A username</span>
        
    </div>
</div> <!-- /clearfix -->
<div id="div_id_password" class="control-group">
    <label class="control-label" for="id_password">Password</label>
    <div class="controls">
        <input id="id_password" type="password" name="password" maxlength="100" />
        
        
    </div>
</div> <!-- /clearfix -->
</fieldset>"""
        form = InlineHelpForm()
        self.assertEqual(str(form), expected)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = widgets
from django.forms.widgets import Input, RadioInput, RadioFieldRenderer, RadioSelect, TextInput
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe


class OptionsRadioInput(RadioInput):
    def __unicode__(self):
        if 'id' in self.attrs:
            label_for = ' for="%s_%s"' % (self.attrs['id'], self.index)
        else:
            label_for = ''
        choice_label = conditional_escape(force_unicode(self.choice_label))
        return mark_safe(u'<label%s>%s <span>%s</span></label>' %
                         (label_for, self.tag(), choice_label))


class OptionsRadioRenderer(RadioFieldRenderer):
    def render(self):
        return mark_safe(u'<ul class="inputs-list">\n%s\n</ul>' %
                         u'\n'.join([u'<li>%s</li>' %
                         force_unicode(w) for w in self]))


class OptionsRadio(RadioSelect):
    renderer = OptionsRadioRenderer


class AppendedText(TextInput):
    def render(self, name, value, attrs=None):
        append_text = self.attrs.get('text', '')
        return mark_safe(u'%s<span class="add-on">%s</span>' % (super(AppendedText, self).render(name, value, attrs),
                                                     append_text))


class PrependedText(TextInput):
    def render(self, name, value, attrs=None):
        prepend_text = self.attrs.get('text', '')
        return mark_safe(u'<span class="add-on">%s</span>%s' % (prepend_text, super(PrependedText, self).render(name, value, attrs)))


class AppendPrependText(TextInput):
    def render(self, name, value, attrs=None):
        append_text, prepend_text = self.attrs.get('append_text', ''), self.attrs.get('prepend_text', '')
        return mark_safe(u'<span class="add-on">%s</span>%s<span class="add-on">%s</span>' % (prepend_text, super(AppendPrependText, self).render(name, value, attrs), append_text))


class EmailInput(Input):
    input_type = 'email'
    def render(self, name, value, attrs=None):
        append_text = self.attrs.get('text', '@')
        return mark_safe(u'%s<span class="add-on">%s</span>' % (super(EmailInput, self).render(name, value, attrs),
                                                     append_text))

########NEW FILE########
__FILENAME__ = runtests
import os, sys
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'testing.settings'

from django.test.simple import DjangoTestSuiteRunner

tr = DjangoTestSuiteRunner(verbosity=1)
failures = tr.run_tests(['bootstrap',])
if failures:
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = settings
import os

DIRNAME = os.path.dirname(__file__)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'database.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'bootstrap',
    'bootstrap.tests',
)

########NEW FILE########
