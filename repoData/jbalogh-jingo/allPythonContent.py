__FILENAME__ = conf
import os
import sys

sys.path.append(os.path.abspath('..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'fake_settings'

import jingo

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

extensions = ['sphinx.ext.autodoc']

# General information about the project.
project = u'Jingo'
copyright = u'2010-2014, The Mozilla Foundation'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# version: The short X.Y version.
# release: The full version, including alpha/beta/rc tags.
version = release = jingo.__version__

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

########NEW FILE########
__FILENAME__ = settings
import os

# Make filepaths relative to settings.
ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

JINJA_CONFIG = {}

SECRET_KEY = 'jingo'

########NEW FILE########
__FILENAME__ = fake_settings
import os

path = lambda *a: os.path.join(ROOT, *a)

ROOT = os.path.dirname(os.path.abspath(__file__))
INSTALLED_APPS = (
    'jingo.tests.jinja_app',
    'jingo.tests.django_app',
)
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
TEMPLATE_DIRS = (path('jingo/tests/templates'),)
JINGO_EXCLUDE_APPS = ('django_app',)
ROOT_URLCONF = 'jingo.tests.urls'

SECRET_KEY = 'jingo'

########NEW FILE########
__FILENAME__ = helpers
# coding: utf-8

from __future__ import unicode_literals, print_function

from django.utils import six
from django.utils.translation import ugettext as _
from django.template.defaulttags import CsrfTokenNode
try:
    from django.utils.encoding import smart_unicode as smart_text
except ImportError:
    from django.utils.encoding import smart_text
from django.core.urlresolvers import reverse

import jinja2

from jingo import register


@register.function
@jinja2.contextfunction
def csrf(context):
    """Equivalent of Django's ``{% crsf_token %}``."""
    return jinja2.Markup(CsrfTokenNode().render(context))


@register.filter
def f(string, *args, **kwargs):
    """
    Uses ``str.format`` for string interpolation.

    >>> {{ "{0} arguments and {x} arguments"|f('positional', x='keyword') }}
    "positional arguments and keyword arguments"
    """
    return string.format(*args, **kwargs)


@register.filter
def fe(string, *args, **kwargs):
    """Format a safe string with potentially unsafe arguments, then return a
    safe string."""

    string = six.text_type(string)

    args = [jinja2.escape(smart_text(v)) for v in args]

    for k in kwargs:
        kwargs[k] = jinja2.escape(smart_text(kwargs[k]))

    return jinja2.Markup(string.format(*args, **kwargs))


@register.filter
def nl2br(string):
    """Turn newlines into <br>."""
    if not string:
        return ''
    return jinja2.Markup('<br>'.join(jinja2.escape(string).splitlines()))


@register.filter
def datetime(t, fmt=None):
    """Call ``datetime.strftime`` with the given format string."""
    if fmt is None:
        fmt = _(u'%B %e, %Y')
    if not six.PY3:
        # The datetime.strftime function strictly does not
        # support Unicode in Python 2 but is Unicode only in 3.x.
        fmt = fmt.encode('utf-8')
    return smart_text(t.strftime(fmt)) if t else ''


@register.filter
def ifeq(a, b, text):
    """Return ``text`` if ``a == b``."""
    return jinja2.Markup(text if a == b else '')


@register.filter
def class_selected(a, b):
    """Return ``'class="selected"'`` if ``a == b``."""
    return ifeq(a, b, 'class="selected"')


@register.filter
def field_attrs(field_inst, **kwargs):
    """Adds html attributes to django form fields"""
    field_inst.field.widget.attrs.update(kwargs)
    return field_inst


@register.function(override=False)
def url(viewname, *args, **kwargs):
    """Return URL using django's ``reverse()`` function."""
    return reverse(viewname, args=args, kwargs=kwargs)

########NEW FILE########
__FILENAME__ = monkey
"""
Django marks its form HTML "safe" according to its own rules, which Jinja2 does
not recognize.

This monkeypatches Django to support the ``__html__`` protocol used in Jinja2
templates. ``Form``, ``BoundField``, ``ErrorList``, and other form objects that
render HTML through their ``__unicode__`` method are extended with ``__html__``
so they can be rendered in Jinja2 templates without adding ``|safe``.

Call the ``patch()`` function to execute the patch. It must be called
before ``django.forms`` is imported for the conditional_escape patch to work
properly. The root URLconf is the recommended location for calling ``patch()``.

Usage::

    import jingo.monkey
    jingo.monkey.patch()

This patch was originally developed by Jeff Balogh and this version is taken
from the nuggets project at
https://github.com/mozilla/nuggets/blob/master/safe_django_forms.py

"""

from __future__ import unicode_literals

import django.utils.encoding
import django.utils.html
import django.utils.safestring
from django.utils import six


# This function gets directly imported within Django, so this change needs to
# happen before too many Django imports happen.
def conditional_escape(html):
    """
    Similar to escape(), except that it doesn't operate on pre-escaped strings.
    """
    if hasattr(html, '__html__'):
        return html.__html__()
    elif isinstance(html, django.utils.safestring.SafeData):
        return html
    return django.utils.html.escape(html)


# Django uses SafeData to mark a string that has already been escaped or
# otherwise deemed safe. This __html__ method lets Jinja know about that too.
def __html__(self):
    """
    Returns the html representation of a string.

    Allows interoperability with other template engines.
    """
    return six.text_type(self)


# Django uses StrAndUnicode for classes like Form, BoundField, Widget which
# have a __unicode__ method which returns escaped html. We replace
# StrAndUnicode with SafeStrAndUnicode to get the __html__ method.
class SafeStrAndUnicode(django.utils.encoding.StrAndUnicode):
    """A class whose __str__ and __html__ returns __unicode__."""

    def __html__(self):
        return six.text_type(self)


def patch():
    django.utils.html.conditional_escape = conditional_escape
    django.utils.safestring.SafeData.__html__ = __html__

    # forms imports have to come after we patch conditional_escape.
    from django.forms import forms, formsets, util, widgets

    # Replace StrAndUnicode with SafeStrAndUnicode in the inheritance
    # for all these classes.
    classes = (
        forms.BaseForm,
        forms.BoundField,
        formsets.BaseFormSet,
        util.ErrorDict,
        util.ErrorList,
        widgets.Media,
        widgets.RadioInput,
        widgets.RadioFieldRenderer,
    )

    for cls in classes:
        bases = list(cls.__bases__)
        if django.utils.encoding.StrAndUnicode in bases:
            idx = bases.index(django.utils.encoding.StrAndUnicode)
            bases[idx] = SafeStrAndUnicode
            cls.__bases__ = tuple(bases)
    for cls in classes:
        if not hasattr(cls, '__html__'):
            cls.__html__ = __html__

########NEW FILE########
__FILENAME__ = test_basics
from __future__ import unicode_literals

from django.shortcuts import render
import jinja2

from nose.tools import eq_
try:
    from unittest.mock import Mock, patch, sentinel
except ImportError:
    from mock import Mock, patch, sentinel

import jingo


@patch('jingo.env')
def test_render(mock_env):
    mock_template = Mock()
    mock_env.get_template.return_value = mock_template

    response = render(Mock(), sentinel.template, status=32)
    mock_env.get_template.assert_called_with(sentinel.template)
    assert mock_template.render.called

    eq_(response.status_code, 32)


@patch('jingo.env')
def test_render_to_string(mock_env):
    template = jinja2.environment.Template('The answer is {{ answer }}')
    rendered = jingo.render_to_string(Mock(), template, {'answer': 42})

    eq_(rendered, 'The answer is 42')


@patch('jingo.env.get_template')
def test_inclusion_tag(get_template):
    @jingo.register.inclusion_tag('xx.html')
    def tag(x):
        return {'z': x}
    get_template.return_value = jinja2.environment.Template('<{{ z }}>')
    t = jingo.env.from_string('{{ tag(1) }}')
    eq_('<1>', t.render())

########NEW FILE########
__FILENAME__ = test_helpers
# -*- coding: utf-8 -*-
"""Tests for the jingo's builtin helpers."""

from __future__ import unicode_literals

from datetime import datetime
from collections import namedtuple

from django.utils import six
from jinja2 import Markup
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from nose.tools import eq_

from jingo import helpers
from jingo import register

from .utils import htmleq_, render


def test_f():
    s = render('{{ "{0} : {z}"|f("a", z="b") }}')
    eq_(s, 'a : b')


def test_fe_helper():
    context = {'var': '<bad>'}
    template = '{{ "<em>{t}</em>"|fe(t=var) }}'
    eq_('<em>&lt;bad&gt;</em>', render(template, context))


def test_fe_positional():
    context = {'var': '<bad>'}
    template = '{{ "<em>{0}</em>"|fe(var) }}'
    eq_('<em>&lt;bad&gt;</em>', render(template, context))


def test_fe_unicode():
    context = {'var': 'Français'}
    template = '{{ "Speak {0}"|fe(var) }}'
    eq_('Speak Français', render(template, context))


def test_fe_markup():
    context = {'var': Markup('<mark>safe</mark>')}
    template = '{{ "<em>{0}</em>"|fe(var) }}'
    eq_('<em><mark>safe</mark></em>', render(template, context))
    template = '{{ "<em>{t}</em>"|fe(t=var) }}'
    eq_('<em><mark>safe</mark></em>', render(template, context))


def test_nl2br():
    text = "some\ntext\n\nwith\nnewlines"
    s = render('{{ x|nl2br }}', {'x': text})
    eq_(s, "some<br>text<br><br>with<br>newlines")

    text = None
    s = render('{{ x|nl2br }}', {'x': text})
    eq_(s, '')


def test_datetime():
    time = datetime(2009, 12, 25, 10, 11, 12)
    s = render('{{ d|datetime }}', {'d': time})
    eq_(s, 'December 25, 2009')

    s = render('{{ d|datetime("%Y-%m-%d %H:%M:%S") }}', {'d': time})
    eq_(s, '2009-12-25 10:11:12')

    s = render('{{ None|datetime }}')
    eq_(s, '')


def test_datetime_unicode():
    fmt = u"%Y 年 %m 月 %e 日"
    helpers.datetime(datetime.now(), fmt)


def test_ifeq():
    eq_context = {'a': 1, 'b': 1}
    neq_context = {'a': 1, 'b': 2}

    s = render('{{ a|ifeq(b, "<b>something</b>") }}', eq_context)
    eq_(s, '<b>something</b>')

    s = render('{{ a|ifeq(b, "<b>something</b>") }}', neq_context)
    eq_(s, '')


def test_class_selected():
    eq_context = {'a': 1, 'b': 1}
    neq_context = {'a': 1, 'b': 2}

    s = render('{{ a|class_selected(b) }}', eq_context)
    eq_(s, 'class="selected"')

    s = render('{{ a|class_selected(b) }}', neq_context)
    eq_(s, '')


def test_csrf():
    s = render('{{ csrf() }}', {'csrf_token': 'fffuuu'})
    csrf = "<input type='hidden' name='csrfmiddlewaretoken' value='fffuuu' />"
    assert csrf in s


def test_field_attrs():
    class field(object):
        def __init__(self):
            self.field = namedtuple('_', 'widget')
            self.field.widget = namedtuple('_', 'attrs')
            self.field.widget.attrs = {'class': 'foo'}

        def __str__(self):
            attrs = self.field.widget.attrs
            attr_str = ' '.join('%s="%s"' % (k, v)
                                for (k, v) in six.iteritems(attrs))
            return Markup('<input %s />' % attr_str)

        def __html__(self):
            return self.__str__()

    f = field()
    s = render('{{ field|field_attrs(class="bar",name="baz") }}',
               {'field': f})
    htmleq_(s, '<input class="bar" name="baz" />')


def test_url():
    # urls defined in jingo/tests/urls.py
    s = render('{{ url("url-args", 1, "foo") }}')
    eq_(s, "/url/1/foo/")
    s = render('{{ url("url-kwargs", word="bar", num=1) }}')
    eq_(s, "/url/1/bar/")


def url(x, *y, **z):
    return '/' + x + '!'


@patch('django.conf.settings')
def test_custom_url(s):
    # register our url method
    register.function(url)
    # re-register Jinja's
    register.function(helpers.url, override=False)

    # urls defined in jingo/tests/urls.py
    s = render('{{ url("url-args", 1, "foo") }}')
    eq_(s, "/url-args!")
    s = render('{{ url("url-kwargs", word="bar", num=1) }}')
    eq_(s, "/url-kwargs!")

    # teardown
    register.function(helpers.url, override=True)


def test_filter_override():
    def f(s):
        return s.upper()
    # See issue 7688: http://bugs.python.org/issue7688
    f.__name__ = 'a' if six.PY3 else b'a'
    register.filter(f)
    s = render('{{ s|a }}', {'s': 'Str'})
    eq_(s, 'STR')

    def g(s):
        return s.lower()
    g.__name__ = 'a' if six.PY3 else b'a'
    register.filter(override=False)(g)
    s = render('{{ s|a }}', {'s': 'Str'})
    eq_(s, 'STR')

    register.filter(g)
    s = render('{{ s|a }}', {'s': 'Str'})
    eq_(s, 'str')

########NEW FILE########
__FILENAME__ = test_loader
from __future__ import unicode_literals

from django.shortcuts import render

from nose.tools import eq_
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


def test_render():
    r = render(Mock(), 'jinja_app/test.html', {})
    eq_(r.content, b'HELLO')


def test_render_no_toplevel_override():
    r = render(Mock(), 'jinja_app/test_nonoverride.html', {})
    eq_(r.content, b'HELLO')


def test_render_toplevel_override():
    r = render(Mock(), 'jinja_app/test_override.html', {})
    eq_(r.content, b'HELLO')


def test_render_django():
    r = render(Mock(), 'django_app/test.html', {})
    eq_(r.content, b'HELLO ...\n')


def test_render_django_no_toplevel_override():
    r = render(Mock(), 'django_app/test_nonoverride.html', {})
    eq_(r.content, b'HELLO ...\n')


def test_render_django_toplevel_override():
    r = render(Mock(), 'django_app/test_override.html', {})
    eq_(r.content, b'HELLO ...\n')

########NEW FILE########
__FILENAME__ = test_monkey
from __future__ import unicode_literals

from django import forms
from django.utils import six

from jinja2 import escape
from nose.tools import eq_

import jingo.monkey

from .utils import render


class MyForm(forms.Form):
    email = forms.EmailField()


def test_monkey_patch():
    form = MyForm()
    html = form.as_ul()
    context = {'form': form}
    t = '{{ form.as_ul() }}'

    eq_(escape(html), render(t, context))

    jingo.monkey.patch()
    eq_(html, render(t, context))

    s = six.text_type(form['email'])
    eq_(s, render('{{ form.email }}', {'form': form}))

########NEW FILE########
__FILENAME__ = test_views
from __future__ import unicode_literals

from django.utils import translation

try:
    from unittest.mock import sentinel
except ImportError:
    from mock import sentinel
from nose.tools import eq_

from jingo import get_env, render_to_string


def test_template_substitution_crash():
    translation.activate('xx')

    env = get_env()

    # The localized string has the wrong variable name in it
    s = '{% trans string="heart" %}Broken {{ string }}{% endtrans %}'
    template = env.from_string(s)
    rendered = render_to_string(sentinel.request, template, {})
    eq_(rendered, 'Broken heart')

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals

from django.conf.urls import patterns


urlpatterns = patterns('',
    (r'^url/(\d+)/(\w+)/$', lambda r: None, {}, "url-args"),
    (r'^url/(?P<num>\d+)/(?P<word>\w+)/$', lambda r: None, {}, "url-kwargs"),
)

########NEW FILE########
__FILENAME__ = utils
from django.test.html import HTMLParseError, parse_html
from nose.tools import eq_

from jingo import env


def htmleq_(html1, html2, msg=None):
    """
    Asserts that two HTML snippets are semantically the same.
    Whitespace in most cases is ignored, and attribute ordering is not
    significant. The passed-in arguments must be valid HTML.

    See ticket 16921: https://code.djangoproject.com/ticket/16921

    """
    dom1 = assert_and_parse_html(html1, msg,
                                 'First argument is not valid HTML:')
    dom2 = assert_and_parse_html(html2, msg,
                                 'Second argument is not valid HTML:')

    eq_(dom1, dom2)


def assert_and_parse_html(html, user_msg, msg):
    try:
        dom = parse_html(html)
    except HTMLParseError as e:
        standard_msg = '%s\n%s\n%s' % (user_msg, msg, e.msg)
        raise AssertionError(standard_msg)
    return dom


def render(s, context={}):
    t = env.from_string(s)
    return t.render(context)

########NEW FILE########
__FILENAME__ = run_tests
import os

import nose

NAME = os.path.basename(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.dirname(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = 'fake_settings'
os.environ['PYTHONPATH'] = os.pathsep.join([ROOT,
                                            os.path.join(ROOT, 'examples')])

if __name__ == '__main__':
    nose.main()

########NEW FILE########
