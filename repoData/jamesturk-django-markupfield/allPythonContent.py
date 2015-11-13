__FILENAME__ = fields
import django
from django.conf import settings
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.encoding import smart_text

from markupfield import widgets
from markupfield import markup

_rendered_field_name = lambda name: '_%s_rendered' % name
_markup_type_field_name = lambda name: '%s_markup_type' % name

# for fields that don't set markup_types: detected types or from settings
_MARKUP_TYPES = getattr(settings, 'MARKUP_FIELD_TYPES',
                        markup.DEFAULT_MARKUP_TYPES)


class Markup(object):

    def __init__(self, instance, field_name, rendered_field_name,
                 markup_type_field_name):
        # instead of storing actual values store a reference to the instance
        # along with field names, this makes assignment possible
        self.instance = instance
        self.field_name = field_name
        self.rendered_field_name = rendered_field_name
        self.markup_type_field_name = markup_type_field_name

    # raw is read/write
    def _get_raw(self):
        return self.instance.__dict__[self.field_name]

    def _set_raw(self, val):
        setattr(self.instance, self.field_name, val)

    raw = property(_get_raw, _set_raw)

    # markup_type is read/write
    def _get_markup_type(self):
        return self.instance.__dict__[self.markup_type_field_name]

    def _set_markup_type(self, val):
        return setattr(self.instance, self.markup_type_field_name, val)

    markup_type = property(_get_markup_type, _set_markup_type)

    # rendered is a read only property
    def _get_rendered(self):
        return getattr(self.instance, self.rendered_field_name)
    rendered = property(_get_rendered)

    # allows display via templates to work without safe filter
    def __unicode__(self):
        return mark_safe(smart_text(self.rendered))

    __str__ = __unicode__


class MarkupDescriptor(object):

    def __init__(self, field):
        self.field = field
        self.rendered_field_name = _rendered_field_name(self.field.name)
        self.markup_type_field_name = _markup_type_field_name(self.field.name)

    def __get__(self, instance, owner):
        if instance is None:
            raise AttributeError('Can only be accessed via an instance.')
        markup = instance.__dict__[self.field.name]
        if markup is None:
            return None
        return Markup(instance, self.field.name, self.rendered_field_name,
                      self.markup_type_field_name)

    def __set__(self, obj, value):
        if isinstance(value, Markup):
            obj.__dict__[self.field.name] = value.raw
            setattr(obj, self.rendered_field_name, value.rendered)
            setattr(obj, self.markup_type_field_name, value.markup_type)
        else:
            obj.__dict__[self.field.name] = value


class MarkupField(models.TextField):

    def __init__(self, verbose_name=None, name=None, markup_type=None,
                 default_markup_type=None, markup_choices=_MARKUP_TYPES,
                 escape_html=False, **kwargs):

        if markup_type and default_markup_type:
            raise ValueError('Cannot specify both markup_type and '
                             'default_markup_type')

        self.default_markup_type = markup_type or default_markup_type
        self.markup_type_editable = markup_type is None
        self.escape_html = escape_html

        self.markup_choices_list = [mc[0] for mc in markup_choices]
        self.markup_choices_dict = dict(markup_choices)

        if (self.default_markup_type and
                self.default_markup_type not in self.markup_choices_list):
            raise ValueError("Invalid default_markup_type for field '%s', "
                             "allowed values: %s" %
                             (name, ', '.join(self.markup_choices_list)))

        # for South FakeORM compatibility: the frozen version of a
        # MarkupField can't try to add a _rendered field, because the
        # _rendered field itself is frozen as well. See introspection
        # rules below.
        self.rendered_field = not kwargs.pop('rendered_field', False)

        super(MarkupField, self).__init__(verbose_name, name, **kwargs)

    def contribute_to_class(self, cls, name):
        if not cls._meta.abstract:
            choices = zip([''] + self.markup_choices_list,
                          ['--'] + self.markup_choices_list)
            markup_type_field = models.CharField(
                max_length=30,
                choices=choices, default=self.default_markup_type,
                editable=self.markup_type_editable, blank=self.blank)
            rendered_field = models.TextField(editable=False)
            markup_type_field.creation_counter = self.creation_counter + 1
            rendered_field.creation_counter = self.creation_counter + 2
            cls.add_to_class(_markup_type_field_name(name), markup_type_field)
            cls.add_to_class(_rendered_field_name(name), rendered_field)
        super(MarkupField, self).contribute_to_class(cls, name)

        setattr(cls, self.name, MarkupDescriptor(self))

    def pre_save(self, model_instance, add):
        value = super(MarkupField, self).pre_save(model_instance, add)
        if value.markup_type not in self.markup_choices_list:
            raise ValueError('Invalid markup type (%s), allowed values: %s' %
                             (value.markup_type,
                              ', '.join(self.markup_choices_list)))
        if self.escape_html:
            raw = escape(value.raw)
        else:
            raw = value.raw
        rendered = self.markup_choices_dict[value.markup_type](raw)
        setattr(model_instance, _rendered_field_name(self.attname), rendered)
        return value.raw

    def get_prep_value(self, value):
        if isinstance(value, Markup):
            return value.raw
        else:
            return value

    # copy get_prep_value to get_db_prep_value if pre-1.2
    if django.VERSION < (1, 2):
        get_db_prep_value = get_prep_value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        if hasattr(value, 'raw'):
            return value.raw
        return value

    def formfield(self, **kwargs):
        defaults = {'widget': widgets.MarkupTextarea}
        defaults.update(kwargs)
        return super(MarkupField, self).formfield(**defaults)

# register MarkupField to use the custom widget in the Admin
from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS
FORMFIELD_FOR_DBFIELD_DEFAULTS[MarkupField] = {
    'widget': widgets.AdminMarkupTextareaWidget}

# allow South to handle MarkupField smoothly
try:
    from south.modelsinspector import add_introspection_rules
    # For a normal MarkupField, the add_rendered_field attribute is
    # always True, which means no_rendered_field arg will always be
    # True in a frozen MarkupField, which is what we want.
    add_introspection_rules(rules=[
        ((MarkupField, ), [], {'rendered_field': ['rendered_field', {}], })
    ], patterns=['markupfield\.fields\.MarkupField'])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = markup
from django.utils.html import escape, linebreaks, urlize
from django.utils.functional import curry
from django.conf import settings

# build DEFAULT_MARKUP_TYPES
DEFAULT_MARKUP_TYPES = [
    ('html', lambda markup: markup),
    ('plain', lambda markup: linebreaks(urlize(escape(markup)))),
]

try:
    import pygments     # noqa
    PYGMENTS_INSTALLED = True

    def _register_pygments_rst_directive():
        from docutils import nodes
        from docutils.parsers.rst import directives
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.formatters import HtmlFormatter

        DEFAULT = HtmlFormatter()
        VARIANTS = {
            'linenos': HtmlFormatter(linenos=True),
        }

        def pygments_directive(name, arguments, options, content, lineno,
                               content_offset, block_text, state,
                               state_machine):
            try:
                lexer = get_lexer_by_name(arguments[0])
            except ValueError:
                # no lexer found - use the text one instead of an exception
                lexer = TextLexer()
            formatter = options and VARIANTS[options.keys()[0]] or DEFAULT
            parsed = highlight(u'\n'.join(content), lexer, formatter)
            return [nodes.raw('', parsed, format='html')]
        pygments_directive.arguments = (1, 0, 1)
        pygments_directive.content = 1
        directives.register_directive('code', pygments_directive)

except ImportError:
    PYGMENTS_INSTALLED = False

try:
    import markdown

    md_filter = markdown.markdown

    # try and replace if pygments & codehilite are available
    if PYGMENTS_INSTALLED:
        try:
            from markdown.extensions.codehilite import makeExtension   # noqa
            md_filter = curry(markdown.markdown,
                              extensions=['codehilite(css_class=highlight)'])
        except ImportError:
            pass

    # whichever markdown_filter was available
    DEFAULT_MARKUP_TYPES.append(('markdown', md_filter))

except ImportError:
    pass

try:
    from docutils.core import publish_parts

    if PYGMENTS_INSTALLED:
        _register_pygments_rst_directive()

    def render_rest(markup):
        overrides = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
        parts = publish_parts(source=markup, writer_name="html4css1",
                              settings_overrides=overrides)
        return parts["fragment"]

    DEFAULT_MARKUP_TYPES.append(('restructuredtext', render_rest))
except ImportError:
    pass

try:
    import textile
    textile_filter = curry(textile.textile, encoding='utf-8', output='utf-8')
    DEFAULT_MARKUP_TYPES.append(('textile', textile_filter))
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from markupfield.fields import MarkupField


@python_2_unicode_compatible
class Post(models.Model):
    title = models.CharField(max_length=50)
    body = MarkupField('body of post')
    comment = MarkupField(escape_html=True, default_markup_type='markdown')

    def __str__(self):
        return self.title


class Article(models.Model):
    normal_field = MarkupField()
    markup_choices_field = MarkupField(markup_choices=(
        ('pandamarkup', lambda x: 'panda'),
        ('nomarkup', lambda x: x)))
    default_field = MarkupField(default_markup_type='markdown')
    markdown_field = MarkupField(markup_type='markdown')


class Abstract(models.Model):
    content = MarkupField()

    class Meta:
        abstract = True


class Concrete(Abstract):
    pass

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'markuptest.db'
    }
}

import markdown
from django.utils.html import escape, linebreaks, urlize
from docutils.core import publish_parts


def render_rest(markup):
    parts = publish_parts(source=markup, writer_name="html4css1")
    return parts["fragment"]

MARKUP_FIELD_TYPES = [
    ('markdown', markdown.markdown),
    ('ReST', render_rest),
    ('plain', lambda markup: urlize(linebreaks(escape(markup)))),
]

INSTALLED_APPS = (
    'markupfield.tests',
)

SECRET_KEY = 'sekrit'

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

import json

from django.test import TestCase
from django.core import serializers
from django.utils.encoding import smart_text
from markupfield.markup import DEFAULT_MARKUP_TYPES
from markupfield.fields import MarkupField, Markup
from markupfield.widgets import MarkupTextarea, AdminMarkupTextareaWidget
from markupfield.tests.models import Post, Article, Concrete

from django.forms.models import modelform_factory
ArticleForm = modelform_factory(Article, fields=['normal_field', 'normal_field_markup_type',
                                                 'markup_choices_field',
                                                 'markup_choices_field_markup_type',
                                                 'default_field', 'default_field_markup_type',
                                                 'markdown_field'])


class MarkupFieldTestCase(TestCase):
    def setUp(self):
        self.xss_str = "<script>alert('xss');</script>"
        self.mp = Post(title='example markdown post', body='**markdown**',
                       body_markup_type='markdown')
        self.mp.save()
        self.rp = Post(title='example restructuredtext post', body='*ReST*',
                       body_markup_type='ReST')
        self.rp.save()
        self.xss_post = Post(title='example xss post', body=self.xss_str,
                             body_markup_type='markdown', comment=self.xss_str)
        self.xss_post.save()
        self.plain_str = ('<span style="color: red">plain</span> post\n\n'
                          'http://example.com')
        self.pp = Post(title='example plain post', body=self.plain_str,
                       body_markup_type='plain', comment=self.plain_str,
                       comment_markup_type='plain')
        self.pp.save()

    def test_verbose_name(self):
        self.assertEqual(self.mp._meta.get_field('body').verbose_name,
                         'body of post')

    def test_markup_body(self):
        self.assertEqual(self.mp.body.raw, '**markdown**')
        self.assertEqual(self.mp.body.rendered,
                         '<p><strong>markdown</strong></p>')
        self.assertEqual(self.mp.body.markup_type, 'markdown')

    def test_markup_unicode(self):
        u = smart_text(self.rp.body.rendered)
        self.assertEqual(u, '<p><em>ReST</em></p>\n')

    def test_from_database(self):
        """ Test that data loads back from the database correctly and 'post'
        has the right type."""
        p1 = Post.objects.get(pk=self.mp.pk)
        self.assertTrue(isinstance(p1.body, Markup))
        self.assertEqual(smart_text(p1.body),
                         '<p><strong>markdown</strong></p>')

    ## Assignment ##
    def test_body_assignment(self):
        self.rp.body = '**ReST**'
        self.rp.save()
        self.assertEqual(smart_text(self.rp.body),
                         '<p><strong>ReST</strong></p>\n')

    def test_raw_assignment(self):
        self.rp.body.raw = '*ReST*'
        self.rp.save()
        self.assertEqual(smart_text(self.rp.body), '<p><em>ReST</em></p>\n')

    def test_rendered_assignment(self):
        def f():
            self.rp.body.rendered = 'this should fail'
        self.assertRaises(AttributeError, f)

    def test_body_type_assignment(self):
        self.rp.body.markup_type = 'markdown'
        self.rp.save()
        self.assertEqual(self.rp.body.markup_type, 'markdown')
        self.assertEqual(smart_text(self.rp.body), '<p><em>ReST</em></p>')

    ## Serialization ##

    def test_serialize_to_json(self):
        stream = serializers.serialize('json', Post.objects.all())

        # Load the data back into Python so that a failed comparison gives a
        # better diff output.
        actual = json.loads(stream)
        expected = [
            {"pk": 1, "model": "tests.post",
             "fields": {"body": "**markdown**",
                        "comment": "",
                        "_comment_rendered": "",
                        "_body_rendered": "<p><strong>markdown</strong></p>",
                        "title": "example markdown post",
                        "comment_markup_type": "markdown",
                        "body_markup_type": "markdown"}},
            {"pk": 2, "model": "tests.post",
             "fields": {"body": "*ReST*",
                        "comment": "",
                        "_comment_rendered": "",
                        "_body_rendered": "<p><em>ReST</em></p>\n",
                        "title": "example restructuredtext post",
                        "comment_markup_type": "markdown",
                        "body_markup_type": "ReST"}},
            {"pk": 3, "model": "tests.post",
             "fields": {"body": "<script>alert(\'xss\');</script>",
                        "comment": "<script>alert(\'xss\');</script>",
                        "_comment_rendered": (
                            "<p>&lt;script&gt;alert("
                            "&#39;xss&#39;);&lt;/script&gt;</p>"),
                        "_body_rendered": "<script>alert(\'xss\');</script>",
                        "title": "example xss post",
                        "comment_markup_type": "markdown",
                        "body_markup_type": "markdown"}},
            {"pk": 4, "model": "tests.post",
             "fields": {"body": ('<span style="color: red">plain</span> '
                                 'post\n\nhttp://example.com'),
                        "comment": ('<span style="color: red">plain</span> '
                                    'post\n\nhttp://example.com'),
                        "_comment_rendered": (
                            '<p>&amp;lt;span style=&amp;quot;color: red'
                            '&amp;quot;&amp;gt;plain&amp;lt;/span&amp;gt; '
                            'post</p>\n\n<p>http://example.com</p>'),
                        "_body_rendered": ('<p>&lt;span style=&quot;color: '
                                           'red&quot;&gt;plain&lt;/span&gt; '
                                           'post</p>\n\n<p>http://example.com'
                                           '</p>'),
                        "title": "example plain post",
                        "comment_markup_type": "plain",
                        "body_markup_type": "plain"}},
        ]
        self.assertEqual(expected, actual)

    def test_deserialize_json(self):
        stream = serializers.serialize('json', Post.objects.all())
        obj = list(serializers.deserialize('json', stream))[0]
        self.assertEqual(obj.object, self.mp)

    def test_value_to_string(self):
        """
        Ensure field converts to string during _meta access

        Other libraries (Django REST framework, etc) go directly to the
        field layer to serialize, which can cause a "unicode object has no
        property called 'raw'" error. This tests the bugfix.
        """
        obj = self.rp
        field = self.rp._meta.get_field_by_name('body')[0]
        self.assertNotEqual(field.value_to_string(obj), u'')    # expected
        self.assertEqual(field.value_to_string(None), u'')      # edge case

    ## Other ##

    def test_escape_html(self):
        # the rendered string has been escaped
        self.assertEqual(self.xss_post.comment.raw, self.xss_str)
        self.assertEqual(
            smart_text(self.xss_post.comment.rendered),
            '<p>&lt;script&gt;alert(&#39;xss&#39;);&lt;/script&gt;</p>')

    def test_escape_html_false(self):
        # both strings here are the xss_str, no escaping was done
        self.assertEqual(self.xss_post.body.raw, self.xss_str)
        self.assertEqual(smart_text(self.xss_post.body.rendered), self.xss_str)

    def test_inheritance(self):
        # test that concrete correctly got the added fields
        concrete_fields = [f.name for f in Concrete._meta.fields]
        self.assertEqual(concrete_fields, ['id', 'content',
                                           'content_markup_type',
                                           '_content_rendered'])

    def test_markup_type_validation(self):
        self.assertRaises(ValueError, MarkupField, 'verbose name',
                          'markup_field', 'bad_markup_type')

    def test_default_markup_types(self):
        for markup_type in DEFAULT_MARKUP_TYPES:
            rendered = markup_type[1]('test')
            self.assertTrue(hasattr(rendered, '__str__'))

    def test_plain_markup_urlize(self):
        for key, func in DEFAULT_MARKUP_TYPES:
            if key != 'plain':
                continue
            txt1 = 'http://example.com some text'
            txt2 = 'Some http://example.com text'
            txt3 = 'Some text http://example.com'
            txt4 = 'http://example.com. some text'
            txt5 = 'Some http://example.com. text'
            txt6 = 'Some text http://example.com.'
            txt7 = '.http://example.com some text'
            txt8 = 'Some .http://example.com text'
            txt9 = 'Some text .http://example.com'
            self.assertEqual(
                func(txt1),
                '<p><a href="http://example.com">http://example.com</a> some text</p>')
            self.assertEqual(
                func(txt2),
                '<p>Some <a href="http://example.com">http://example.com</a> text</p>')
            self.assertEqual(
                func(txt3),
                '<p>Some text <a href="http://example.com">http://example.com</a></p>')
            self.assertEqual(
                func(txt4),
                '<p><a href="http://example.com">http://example.com</a>. some text</p>')
            self.assertEqual(
                func(txt5),
                '<p>Some <a href="http://example.com">http://example.com</a>. text</p>')
            self.assertEqual(
                func(txt6),
                '<p>Some text <a href="http://example.com">http://example.com</a>.</p>')
            self.assertEqual(func(txt7), '<p>.http://example.com some text</p>')
            self.assertEqual(func(txt8), '<p>Some .http://example.com text</p>')
            self.assertEqual(func(txt9), '<p>Some text .http://example.com</p>')
            break


class MarkupWidgetTests(TestCase):

    def test_markuptextarea_used(self):
        self.assertTrue(isinstance(MarkupField().formfield().widget,
                                   MarkupTextarea))
        self.assertTrue(isinstance(ArticleForm()['normal_field'].field.widget,
                                   MarkupTextarea))

    def test_markuptextarea_render(self):
        a = Article(normal_field='**normal**',
                    normal_field_markup_type='markdown',
                    default_field='**default**',
                    markdown_field='**markdown**',
                    markup_choices_field_markup_type='nomarkup')
        a.save()
        af = ArticleForm(instance=a)
        self.assertHTMLEqual(
            smart_text(af['normal_field']),
            '<textarea id="id_normal_field" rows="10" cols="40" '
            'name="normal_field">**normal**</textarea>'
        )

    def test_no_markup_type_field_if_set(self):
        """ensure that a field with non-editable markup_type set does not
        have a _markup_type field"""
        self.assertTrue('markdown_field_markup_type' not in
                        ArticleForm().fields.keys())

    def test_markup_type_choices(self):
        self.assertEqual(
            ArticleForm().fields['normal_field_markup_type'].choices,
            [('', '--'), ('markdown', 'markdown'), ('ReST', 'ReST'),
             ('plain', 'plain')])
        self.assertEqual(
            ArticleForm().fields['markup_choices_field_markup_type'].choices,
            [('', '--'), ('pandamarkup', 'pandamarkup'),
             ('nomarkup', 'nomarkup')])

    def test_default_markup_type(self):
        self.assertTrue(
            ArticleForm().fields['normal_field_markup_type'].initial is None)
        self.assertEqual(
            ArticleForm().fields['default_field_markup_type'].initial,
            'markdown')

    def test_model_admin_field(self):
        # borrows from regressiontests/admin_widgets/tests.py
        from django.contrib import admin
        ma = admin.ModelAdmin(Post, admin.site)
        self.assertTrue(isinstance(ma.formfield_for_dbfield(
            Post._meta.get_field('body')).widget, AdminMarkupTextareaWidget))

########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.contrib.admin.widgets import AdminTextareaWidget
from django.utils import six


class MarkupTextarea(forms.widgets.Textarea):

    def render(self, name, value, attrs=None):
        if value is not None and not isinstance(value, six.text_type):
            value = value.raw
        return super(MarkupTextarea, self).render(name, value, attrs)


class AdminMarkupTextareaWidget(MarkupTextarea, AdminTextareaWidget):
    pass

########NEW FILE########
