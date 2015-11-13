__FILENAME__ = forms
from django import forms
from .widgets import AdminPagedownWidget, PagedownWidget


class PagedownField(forms.CharField):
    ''' A simple CharField that allows us avoid having to write widget code '''
    widget = PagedownWidget


class AdminPagedownField(forms.CharField):
    ''' A simple CharField that allows us avoid having to write widget code '''
    widget = AdminPagedownWidget


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^pagedown\.forms\.PagedownField"])
    add_introspection_rules([], ["^pagedown\.forms\.AdminPagedownField"])
except ImportError:
    raise
########NEW FILE########
__FILENAME__ = models
from django.db import models


########NEW FILE########
__FILENAME__ = settings
from django.conf import settings


SHOW_PREVIEW = getattr(settings, 'PAGEDOWN_SHOW_PREVIEW', True)
WIDGET_TEMPLATE = getattr(settings, 'PAGEDOWN_WIDGET_TEMPLATE', 'pagedown/widgets/default.html')
WIDGET_CSS = getattr(settings, 'PAGEDOWN_WIDGET_CSS', ('pagedown/demo/browser/demo.css', ))
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings


def compatible_staticpath(path):
    '''
    Try to return a path compatible all the way back to Django 1.2. If anyone
    has a cleaner or better way to do this let me know!
    '''
    try:
        # >= 1.4
        from django.contrib.staticfiles.storage import staticfiles_storage
        return staticfiles_storage.url(path)
    except ImportError:
        pass
    try:
        # >= 1.3
        return '%s/%s' % (settings.STATIC_URL.rstrip('/'), path)
    except AttributeError:
        pass
    try:
        return '%s/%s' % (settings.PAGEDOWN_URL.rstrip('/'), path)
    except AttributeError:
        pass
    return '%s/%s' % (settings.MEDIA_URL.rstrip('/'), path)
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.forms.widgets import flatatt
from django.utils.html import conditional_escape
from django.template.loader import render_to_string

from pagedown import settings as pagedown_settings
from pagedown.utils import compatible_staticpath


try:
    from django.utils.encoding import force_unicode
except ImportError: #python3
    # https://docs.djangoproject.com/en/1.5/topics/python3/#string-handling
    from django.utils.encoding import force_text as force_unicode
from django.utils.safestring import mark_safe


class PagedownWidget(forms.Textarea):

    def __init__(self, *args, **kwargs):
        self.show_preview = kwargs.pop('show_preview', pagedown_settings.SHOW_PREVIEW)
        self.template = kwargs.pop('template', pagedown_settings.WIDGET_TEMPLATE)
        self.css = kwargs.pop('css', pagedown_settings.WIDGET_CSS)
        super(PagedownWidget, self).__init__(*args, **kwargs)

    def _media(self):
        return forms.Media(
            css={
                'all': self.css
            },
            js=(
                compatible_staticpath('pagedown/Markdown.Converter.js'),
                compatible_staticpath('pagedown/Markdown.Sanitizer.js'),
                compatible_staticpath('pagedown/Markdown.Editor.js'),
                compatible_staticpath('pagedown_init.js'),
            ))
    media = property(_media)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        if 'class' not in attrs:
            attrs['class'] = ""
        attrs['class'] += " wmd-input"
        final_attrs = self.build_attrs(attrs, name=name)
        return render_to_string(self.template, {
            'attrs': flatatt(final_attrs),
            'body': conditional_escape(force_unicode(value)),
            'id': final_attrs['id'],
            'show_preview': self.show_preview,
        })



class AdminPagedownWidget(PagedownWidget, admin_widgets.AdminTextareaWidget):
    class Media:
        css = {
            'all': (compatible_staticpath('admin/css/pagedown.css'),)
        }
        js = (
            compatible_staticpath('admin/js/pagedown.js'),
        )

########NEW FILE########
