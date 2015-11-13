__FILENAME__ = admin_urls
from django.conf.urls.defaults import *


urlpatterns = patterns('django_inlines.views',
    url(r'^inline_config\.js$', 'js_inline_config', name='js_inline_config'),
    url(r'^get_inline_form/$', 'get_inline_form', name='get_inline_form'),
)

########NEW FILE########
__FILENAME__ = forms
from django.db import models
from django.contrib.admin.widgets import AdminTextareaWidget


class DelayedUrlReverse(object):
    def __init__(self, reverse_arg):
        self.reverse_arg = reverse_arg

    def __str__(self):
        from django.core.urlresolvers import reverse, NoReverseMatch
        try:
            url = reverse(self.reverse_arg)
        except NoReverseMatch:
            url = ''
        return url

    def startswith(self, value):
        return str(self).startswith(value)


class InlineWidget(AdminTextareaWidget):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'vLargeTextField vInlineTextArea'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(InlineWidget, self).__init__(attrs=final_attrs)

    class Media:
        css = { 'all': [ 'django_inlines/inlines.css' ] }

        js = [
                'admin/jquery.js',
                DelayedUrlReverse('js_inline_config'),
                'js/admin/RelatedObjectLookups.js',
                'django_inlines/jquery-fieldselection.js',
                'django_inlines/inlines.js'
            ]


class InlineField(models.TextField):
    def formfield(self, **kwargs):
        defaults = {}
        defaults.update(kwargs)
        defaults = {'widget': InlineWidget}
        return super(InlineField, self).formfield(**defaults)
########NEW FILE########
__FILENAME__ = inlines
import re
from django.template.loader import render_to_string
from django.template import Context, RequestContext
from django.db.models.base import ModelBase
from django.conf import settings

INLINE_SPLITTER = re.compile(r"""
    (?P<name>[a-z_]+)       # Must start with a lowercase + underscores name
    (?::(?P<variant>\w+))?  # Variant is optional, ":variant"
    (?:(?P<args>[^\Z]+))? # args is everything up to the end
    """, re.VERBOSE)

INLINE_KWARG_PARSER = re.compile(r"""
    (?P<kwargs>(?:\s\b[a-z_]+=\w+\s?)+)?\Z # kwargs match everything at the end in groups " name=arg"
    """, re.VERBOSE)


class InlineUnrenderableError(Exception):
    """
    Any errors that are children of this error will be silenced by inlines.process
    unless settings.INLINE_DEBUG is true.
    """
    pass

class InlineInputError(InlineUnrenderableError):
    pass

class InlineValueError(InlineUnrenderableError):
    pass

class InlineAttributeError(InlineUnrenderableError):
    pass

class InlineNotRegisteredError(InlineUnrenderableError):
    pass

class InlineUnparsableError(InlineUnrenderableError):
    pass


def parse_inline(text):
    """
    Takes a string of text from a text inline and returns a 3 tuple of
    (name, value, **kwargs).
    """

    m = INLINE_SPLITTER.match(text)
    if not m:
        raise InlineUnparsableError
    args = m.group('args')
    name = m.group('name')
    value = ""
    kwtxt = ""
    kwargs = {}
    if args:
        kwtxt = INLINE_KWARG_PARSER.search(args).group('kwargs')
        value = re.sub("%s\Z" % kwtxt, "", args)
        value = value.strip()
    if m.group('variant'):
        kwargs['variant'] = m.group('variant')
    if kwtxt:
        for kws in kwtxt.split():
            k, v = kws.split('=')
            kwargs[str(k)] = v
    return (name, value, kwargs)


def inline_for_model(model, variants=[], inline_args={}):
    """
    A shortcut function to produce ModelInlines for django models
    """

    if not isinstance(model, ModelBase):
        raise ValueError("inline_for_model requires it's argument to be a Django Model")
    d = dict(model=model)
    if variants:
        d['variants'] = variants
    if inline_args:
        d['args'] = inline_args
    class_name = "%sInline" % model._meta.module_name.capitalize()
    return type(class_name, (ModelInline,), d)


class InlineBase(object):
    """
    A base class for overriding to provide simple inlines.
    The `render` method is the only required override. It should return a string.
    or at least something that can be coerced into a string.
    """

    def __init__(self, value, variant=None, context=None, template_dir="", **kwargs):
        self.value = value
        self.variant = variant
        self.kwargs = kwargs

    def render(self):
        raise NotImplementedError('This method must be defined in a subclass')


class TemplateInline(object):
    """
    A base class for overriding to provide templated inlines.
    The `get_context` method is the only required override. It should return
    dictionary-like object that will be fed to the template as the context.

    If you instantiate your inline class with a context instance, it'll use
    that to set up your base context.

    Any extra arguments assigned to your inline are passed directly though to
    the context.
    """

    def __init__(self, value, variant=None, context=None, template_dir=None, **kwargs):
        self.value = value
        self.variant = variant
        self.context = context
        self.kwargs = kwargs

        self.template_dirs = []
        if template_dir:
            self.template_dirs.append(template_dir.strip('/').replace("'", '').replace('"', ''))
        self.template_dirs.append('inlines')

    def get_context(self):
        """
        This method must be defined in a subclass
        """
        raise NotImplementedError('This method must be defined in a subclass')

    def get_template_name(self):
        templates = []
        name = self.__class__.name
        for dir in self.template_dirs:
            if self.variant:
                templates.append('%s/%s.%s.html' % (dir, name, self.variant))
            templates.append('%s/%s.html' % (dir, name))
        return templates

    def render(self):
        if self.context:
            context = self.context
        else:
            context = Context()
        context.update(self.kwargs)
        context['variant'] = self.variant
        output = render_to_string(self.get_template_name(), self.get_context(), context)
        context.pop()
        return output


class ModelInline(TemplateInline):
    """
    A base class for creating inlines for Django models. The `model` class
    attribute is the only required override. It should be assigned a django
    model class.
    """

    model = None
    help_text = "Takes the id of the desired object"

    @classmethod
    def get_app_label(self):
        return "%s/%s" % (self.model._meta.app_label, self.model._meta.module_name)

    def get_context(self):
        model = self.__class__.model
        if not isinstance(model, ModelBase):
            raise InlineAttributeError('ModelInline requires model to be set to a django model class')
        try:
            value = int(self.value)
            object = model.objects.get(pk=value)
        except ValueError:
            raise InlineInputError("'%s' could not be converted to an int" % self.value)
        except model.DoesNotExist:
            raise InlineInputError("'%s' could not be found in %s.%s" % (self.value, model._meta.app_label, model._meta.module_name))
        return { 'object': object }


class Registry(object):

    def __init__(self):
        self._registry = {}
        self.START_TAG = getattr(settings, 'INLINES_START_TAG', '{{')
        self.END_TAG = getattr(settings, 'INLINES_END_TAG', '}}')

    @property
    def inline_finder(self):
        return re.compile(r'%(start)s\s*(.+?)\s*%(end)s' % {'start':self.START_TAG, 'end':self.END_TAG})

    def register(self, name, cls):
        if not hasattr(cls, 'render'):
            raise TypeError("You may only register inlines with a `render` method")
        cls.name = name
        self._registry[name] = cls

    def unregister(self, name):
        if not name in self._registry:
            raise InlineNotRegisteredError("Inline '%s' not registered. Unable to remove." % name)
        del(self._registry[name])

    def process(self, text, context=None, template_dir=None, **kwargs):
        def render(matchobj):
            try:
                text = matchobj.group(1)
                name, value, inline_kwargs = parse_inline(text)
                try:
                    cls = self._registry[name]
                except KeyError:
                    raise InlineNotRegisteredError('"%s" was not found as a registered inline' % name)
                inline = cls(value, context=context, template_dir=template_dir, **inline_kwargs)
                return str(inline.render())
            # Silence any InlineUnrenderableErrors unless INLINE_DEBUG is True
            except InlineUnrenderableError:
                debug = getattr(settings, "INLINE_DEBUG", False)
                if debug:
                    raise
                else:
                    return ""
        text = self.inline_finder.sub(render, text)
        return text


# The default registry.
registry = Registry()

########NEW FILE########
__FILENAME__ = samples
import re
from django_inlines.inlines import TemplateInline


class YoutubeInline(TemplateInline):
    """
    An inline that takes a youtube URL or video id and returns the proper embed.

    Examples::

        {{ youtube http://www.youtube.com/watch?v=4R-7ZO4I1pI&hd=1 }}
        {{ youtube 4R-7ZO4I1pI }}

    The inluded template supports width and height arguments::

        {{ youtube 4R-7ZO4I1pI width=850 height=500 }}

    """
    help_text = "Takes a youtube URL or video ID: http://www.youtube.com/watch?v=4R-7ZO4I1pI or 4R-7ZO4I1pI"
    inline_args = [
        dict(name='height', help_text="In pixels"),
        dict(name='width', help_text="In pixels"),
        ]

    def get_context(self):
        video_id = self.value
        match = re.search(r'(?<=v\=)[\w]+', video_id)
        if match:
            video_id = match.group()
        return { 'video_id': video_id }

########NEW FILE########
__FILENAME__ = inlines
from django import template
from django.conf import settings

register = template.Library()


@register.filter
def stripinlines(value):
    from django_inlines.inlines import registry
    return registry.inline_finder.sub('', value)


class InlinesNode(template.Node):

    def __init__(self, var_name, template_directory=None, asvar=None):
        self.var_name = template.Variable(var_name)
        self.template_directory = template_directory
        self.asvar = asvar

    def render(self, context):
        try:
            from django_inlines.inlines import registry

            if self.template_directory is None:
                rendered = registry.process(self.var_name.resolve(context), context=context)
            else:
                rendered = registry.process(self.var_name.resolve(context), context=context, template_dir=self.template_directory)
            if self.asvar:
                context[self.asvar] = rendered
                return ''
            else:
                return rendered
        except:
            if getattr(settings, 'INLINE_DEBUG', False): # Should use settings.TEMPLATE_DEBUG?
                raise
            return ''


@register.tag
def process_inlines(parser, token):
    """
    Searches through the provided content and applies inlines where ever they
    are found.

    Syntax::

        {% process_inlines entry.body [in template_dir] [as varname] }

    Examples::

        {% process_inlines entry.body %}

        {% process_inlines entry.body as body %}

        {% process_inlines entry.body in 'inlines/sidebar' %}

        {% process_inlines entry.body in 'inlines/sidebar' as body %}

    """

    args = token.split_contents()

    if not len(args) in (2, 4, 6):
        raise template.TemplateSyntaxError("%r tag requires either 1, 3 or 5 arguments." % args[0])

    var_name = args[1]

    ALLOWED_ARGS = ['as', 'in']
    kwargs = { 'template_directory': None }
    if len(args) > 2:
        tuples = zip(*[args[2:][i::2] for i in range(2)])
        for k,v in tuples:
            if not k in ALLOWED_ARGS:
                raise template.TemplateSyntaxError("%r tag options arguments must be one of %s." % (args[0], ', '.join(ALLOWED_ARGS)))
            if k == 'in':
                kwargs['template_directory'] = v
            if k == 'as':
                kwargs['asvar'] = v

    return InlinesNode(var_name, **kwargs)

########NEW FILE########
__FILENAME__ = views
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response
from django.http import Http404
from django.conf import settings

from django_inlines import inlines


@staff_member_required
def js_inline_config(request):
    registered = []
    sorted_inlines = sorted(inlines.registry._registry.items())
    for inline in sorted_inlines:
        d = {'name': inline[0]}
        inline_cls = inline[1]
        d['help'] = getattr(inline_cls, 'help', '')
        d['variants'] = getattr(inline_cls, 'variants', [])
        args = getattr(inline_cls, 'inline_args', [])
        d['args'] = sorted(args)
        if issubclass(inline_cls, inlines.ModelInline):
            d['app_path'] = "%s/%s" % (inline_cls.model._meta.app_label, inline_cls.model._meta.module_name)
        registered.append(d)
    return render_to_response('admin/django_inlines/js_inline_config.js', { 'inlines': registered }, mimetype="text/javascript")

@staff_member_required
def get_inline_form(request):
    inline = request.GET.get('inline', None)
    target = request.GET.get('target', None)
    if not inline or not target:
        raise Http404('"inline" and "target" must be specified as a GET args')
    inline_cls = inlines.registry._registry.get(inline, None)
    if not inline_cls:
        raise Http404('Requested inline does not exist')
    admin_media_prefix = settings.ADMIN_MEDIA_PREFIX
    return render_to_response('admin/django_inlines/inline_form.html', { 'inline': inline_cls, 'target':target, 'ADMIN_MEDIA_PREFIX': admin_media_prefix })

########NEW FILE########
__FILENAME__ = models
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=255)
    title = models.CharField(blank=True, max_length=255)
    email = models.EmailField()
    phone = models.CharField(blank=True, max_length=255)
########NEW FILE########
__FILENAME__ = base
import unittest
from django.conf import settings
from django_inlines.inlines import Registry, parse_inline, InlineUnparsableError
from core.tests.test_inlines import DoubleInline, QuineInline, KeyErrorInline

class ParserTestCase(unittest.TestCase):

    def testParser(self):
        OUT = ('simple', '', {})
        self.assertEqual(parse_inline('simple'), OUT)
        OUT = ('with', 'a value', {})
        self.assertEqual(parse_inline('with a value'), OUT)
        OUT = ('with', 'a value', {'and': 'args'})
        self.assertEqual(parse_inline('with a value and=args'), OUT)
        OUT = ('with', '', {'just': 'args'})
        self.assertEqual(parse_inline('with just=args'), OUT)
        OUT = ('with', 'complex value http://www.youtube.com/watch?v=nsBAj6eopzc&hd=1&feature=hd#top', {})
        self.assertEqual(parse_inline('with complex value http://www.youtube.com/watch?v=nsBAj6eopzc&hd=1&feature=hd#top'), OUT)
        OUT = ('with', 'complex value http://www.youtube.com/watch?v=nsBAj6eopzc&hd=1&feature=hd#top', {'and': 'args'})
        self.assertEqual(parse_inline('with complex value http://www.youtube.com/watch?v=nsBAj6eopzc&hd=1&feature=hd#top and=args'), OUT)
        OUT = (u'with', u'complex value http://www.youtube.com/watch?v=nsBAj6eopzc', {'and': 'args'})
        self.assertEqual(parse_inline(u'with complex value http://www.youtube.com/watch?v=nsBAj6eopzc and=args'), OUT)
        OUT = ('with', 'a value', {'variant': 'variant', 'and': 'args', 'more': 'arg'})
        self.assertEqual(parse_inline('with:variant a value and=args more=arg'), OUT)
        OUT = ('with', '', {'variant': 'avariant'})
        self.assertEqual(parse_inline('with:avariant'), OUT)

class RegistrySartEndTestCase(unittest.TestCase):

    def setUp(self):
        inlines = Registry()
        inlines.register('double', DoubleInline)
        inlines.START_TAG = '<<'
        inlines.END_TAG = '>>'
        self.inlines = inlines

    def testDifferentSartEnds(self):
        # self.assertEqual(self.inlines.START_TAG, "<<")
        IN = """<< double makes more  >>"""
        OUT = """makes moremakes more"""
        self.assertEqual(self.inlines.process(IN), OUT)
        IN = """<< double 2 >> / << double 2 multiplier=3 >>"""
        OUT = """4 / 6"""
        self.assertEqual(self.inlines.process(IN), OUT)

class InlineTestCase(unittest.TestCase):

    def setUp(self):
        inlines = Registry()
        inlines.register('quine', QuineInline)
        inlines.register('double', DoubleInline)
        self.inlines = inlines

    def tearDown(self):
        settings.INLINE_DEBUG = False

    def testQuineInline(self):
        IN = """{{ quine should be the same }}"""
        OUT = """{{ quine should be the same }}"""
        self.assertEqual(self.inlines.process(IN), OUT)
        IN = """the {{ quine }}"""
        OUT = """the {{ quine }}"""
        self.assertEqual(self.inlines.process(IN), OUT)
        IN = """the {{ quine with value }}
        {{ quine with=args }}
        {{ quine:with_variant }}
        {{ quine:with everything even=args }}
        """
        OUT = """the {{ quine with value }}
        {{ quine with=args }}
        {{ quine:with_variant }}
        {{ quine:with everything even=args }}
        """
        self.assertEqual(self.inlines.process(IN), OUT)

    def testDoubleInline(self):
        IN = """{{ double makes more  }}"""
        OUT = """makes moremakes more"""
        self.assertEqual(self.inlines.process(IN), OUT)
        IN = """{{ double 2 }} / {{ double 2 multiplier=3 }}"""
        OUT = """4 / 6"""
        self.assertEqual(self.inlines.process(IN), OUT)

    def testMultipleInlines(self):
        IN = """{{ quine }} and {{ nothing }}"""
        OUT = """{{ quine }} and """
        self.assertEqual(self.inlines.process(IN), OUT)

    def testRemovalOfUnassignedInline(self):
        IN = """this {{ should }} be removed"""
        OUT = """this  be removed"""
        self.assertEqual(self.inlines.process(IN), OUT)

    def test_empty_inline(self):
        IN = """this {{ 234 }} be removed"""
        OUT = """this  be removed"""
        self.assertEqual(self.inlines.process(IN), OUT)
        settings.INLINE_DEBUG = True
        self.assertRaises(InlineUnparsableError, self.inlines.process, IN)

    def test_keyerrors(self):
        """
        A regression test to make sure KeyErrors thrown by inlines
        aren't silenced in render anymore.
        """
        self.inlines.register('keyerror', KeyErrorInline)
        IN = "{{ keyerror fail! }}"
        self.assertRaises(KeyError, self.inlines.process, IN)
########NEW FILE########
__FILENAME__ = modelinline
from django.test import TestCase
from django_inlines.inlines import Registry, inline_for_model, InlineInputError
from django.conf import settings
from test_inlines import UserInline
from core.models import User

class ModelInlineTestCase(TestCase):

    fixtures = ['users']

    def setUp(self):
        inlines = Registry()
        inlines.register('user', UserInline)
        self.inlines = inlines

    def testModelInlines(self):
        self.assertEqual(self.inlines.process("{{ user 1 }}"), "Xian")
        self.assertEqual(self.inlines.process("{{ user 1 }} vs {{ user 2 }}"), "Xian vs Evil Xian")

    def testModelInlineVariants(self):
        self.assertEqual(self.inlines.process("{{ user:contact 1 }}"), "Xian, (708) 555-1212, xian@example.com")
        self.assertEqual(self.inlines.process("{{ user:nonexistant_variant 1 }}"), "Xian")


class BadInputModelInlineTestCase(TestCase):

    fixtures = ['users']

    def setUp(self):
        inlines = Registry()
        inlines.register('user', UserInline)
        self.inlines = inlines

    def tearDown(self):
        settings.INLINE_DEBUG = False

    def testAgainstNonexistentObject(self):
        self.assertEqual(self.inlines.process("{{ user 111 }}"), "")

    def testAgainstCrapInput(self):
        self.assertEqual(self.inlines.process("{{ user asdf }}"), "")

    def testErrorRaising(self):
        settings.INLINE_DEBUG = True
        process = self.inlines.process
        self.assertRaises(InlineInputError, process, "{{ user 111 }}",)
        self.assertRaises(InlineInputError, process, "{{ user asdf }}",)

class InlineForModelTestCase(TestCase):

    fixtures = ['users']

    def setUp(self):
        inlines = Registry()
        self.inlines = inlines

    def testInlineForModel(self):
        self.inlines.register('user', inline_for_model(User))
        self.assertEqual(self.inlines.process("{{ user 1 }}"), "Xian")
        self.assertEqual(self.inlines.process("{{ user 1 }} vs {{ user 2 }}"), "Xian vs Evil Xian")

    def testInlineForModelBadInput(self):
        self.assertRaises(ValueError, inline_for_model, "User")

########NEW FILE########
__FILENAME__ = templateinline
import unittest
from django_inlines.inlines import Registry
from django_inlines.samples import YoutubeInline


class YoutubeTestCase(unittest.TestCase):
    
    def setUp(self):
        inlines = Registry()
        inlines.register('youtube', YoutubeInline)
        self.inlines = inlines

    def testYoutubeInlines(self):
        IN = """{{ youtube RXJKdh1KZ0w }}"""
        OUT = """<div class="youtube_video">\n<object width="480" height="295">\n  <param name="movie" value="http://www.youtube.com/v/RXJKdh1KZ0w&hl=en&fs=1"></param>\n  <param name="allowFullScreen" value="true"></param>\n  <param name="allowscriptaccess" value="always"></param>\n  <embed src="http://www.youtube.com/v/RXJKdh1KZ0w&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="480" height="295"></embed>\n</object>  \n</div>\n"""
        self.assertEqual(self.inlines.process(IN), OUT)
        IN = """{{ youtube RXJKdh1KZ0w width=200 height=100 }}"""
        OUT = """<div class="youtube_video">\n<object width="200" height="100">\n  <param name="movie" value="http://www.youtube.com/v/RXJKdh1KZ0w&hl=en&fs=1"></param>\n  <param name="allowFullScreen" value="true"></param>\n  <param name="allowscriptaccess" value="always"></param>\n  <embed src="http://www.youtube.com/v/RXJKdh1KZ0w&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="200" height="100"></embed>\n</object>  \n</div>\n"""
        self.assertEqual(self.inlines.process(IN), OUT)
        IN = """{{ youtube http://www.youtube.com/watch?v=RXJKdh1KZ0w&hd=1&feature=hd }}"""
        OUT = """<div class="youtube_video">\n<object width="480" height="295">\n  <param name="movie" value="http://www.youtube.com/v/RXJKdh1KZ0w&hl=en&fs=1"></param>\n  <param name="allowFullScreen" value="true"></param>\n  <param name="allowscriptaccess" value="always"></param>\n  <embed src="http://www.youtube.com/v/RXJKdh1KZ0w&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="480" height="295"></embed>\n</object>  \n</div>\n"""
        self.assertEqual(self.inlines.process(IN), OUT)

########NEW FILE########
__FILENAME__ = templatetags
from django.test import TestCase
from django.template import Template, Context
from django_inlines import inlines
from django_inlines.samples import YoutubeInline
from django_inlines.templatetags.inlines import stripinlines
from test_inlines import QuineInline, DoubleInline


class StripInlinesTestCase(TestCase):
    def render(self, template_string, context_dict=None):
        """A shortcut for testing template output."""
        if context_dict is None:
            context_dict = {}

        c = Context(context_dict)
        t = Template(template_string)
        return t.render(c)

    def test_strip_inlines(self):
        IN = "This is my YouTube video: {{ youtube C_ZebDKv1zo }}"
        self.assertEqual(stripinlines(IN), "This is my YouTube video: ")

    def test_simple_usage(self):
        inlines.registry.register('youtube', YoutubeInline)

        template = u"{% load inlines %}<p>{{ body|stripinlines }}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: </p>')


class ProcessInlinesTestCase(TestCase):
    def render(self, template_string, context_dict=None):
        """A shortcut for testing template output."""
        if context_dict is None:
            context_dict = {}

        c = Context(context_dict)
        t = Template(template_string)
        return t.render(c)

    def setUp(self):
        super(ProcessInlinesTestCase, self).setUp()

        # Stow.
        self.old_registry = inlines.registry
        inlines.registry = inlines.Registry()

    def tearDown(self):
        inlines.registry = self.old_registry
        super(ProcessInlinesTestCase, self).tearDown()

    def test_simple_usage(self):
        inlines.registry.register('youtube', YoutubeInline)

        template = u"{% load inlines %}<p>{% process_inlines body %}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\n<object width="480" height="295">\n  <param name="movie" value="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1"></param>\n  <param name="allowFullScreen" value="true"></param>\n  <param name="allowscriptaccess" value="always"></param>\n  <embed src="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="480" height="295"></embed>\n</object>  \n</div>\n</p>')

    def test_usage_with_args_and_unicode(self):
        inlines.registry.register('youtube', YoutubeInline)

        template = u"{% load inlines %}<p>{% process_inlines body %}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo height=295 width=480 }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\n<object width="480" height="295">\n  <param name="movie" value="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1"></param>\n  <param name="allowFullScreen" value="true"></param>\n  <param name="allowscriptaccess" value="always"></param>\n  <embed src="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="480" height="295"></embed>\n</object>  \n</div>\n</p>')

    def test_asvar(self):
        inlines.registry.register('youtube', YoutubeInline)

        template = u"{% load inlines %}{% process_inlines body as body %}<p>{{ body|safe }}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\n<object width="480" height="295">\n  <param name="movie" value="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1"></param>\n  <param name="allowFullScreen" value="true"></param>\n  <param name="allowscriptaccess" value="always"></param>\n  <embed src="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="480" height="295"></embed>\n</object>  \n</div>\n</p>')

    def test_asvar_and_template_dir(self):
        """
        The template tag shouldn't care what order the arguments are in.
        """
        inlines.registry.register('youtube', YoutubeInline)

        template = "{% load inlines %}{% process_inlines body as body in 'youtube_inlines' %}<p>{{ body|safe }}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\nC_ZebDKv1zo\n</div>\n</p>')

        template = "{% load inlines %}{% process_inlines body in 'youtube_inlines' as body %}<p>{{ body|safe }}</p>"
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\nC_ZebDKv1zo\n</div>\n</p>')

    def test_usage_with_multiple_inlines(self):
        inlines.registry.register('quine', QuineInline)
        inlines.registry.register('double', DoubleInline)

        template = "{% load inlines %}<p>{% process_inlines body %}</p>"
        context = {
            'body': u"Some text {{ quine Why hello }} but {{ double your fun }}.",
        }
        self.assertEqual(inlines.registry.process(context['body']), 'Some text {{ quine Why hello }} but your funyour fun.')
        self.assertEqual(self.render(template, context), u'<p>Some text {{ quine Why hello }} but your funyour fun.</p>')

    def test_usage_with_template_dirs(self):
        inlines.registry.register('youtube', YoutubeInline)

        template = "{% load inlines %}<p>{% process_inlines body in 'youtube_inlines' %}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\nC_ZebDKv1zo\n</div>\n</p>')

    def test_that_context_gets_passed_through(self):
        inlines.registry.register('youtube', YoutubeInline)

        template = "{% load inlines %}<p>{% with 'b' as bold %}{% process_inlines body in 'youtube_inlines' %}{% endwith %}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\n<b>C_ZebDKv1zo</b>\n</div>\n</p>')

    def test_that_context_gets_popped(self):
        inlines.registry.register('youtube', YoutubeInline)

        template = """{% load inlines %}<p>{% process_inlines body in 'youtube_inlines' %} {{ test }}</p>"""
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo bold=bold }} {{ youtube C_ZebDKv1zo }}",
            'test': u"green"
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\n<b>C_ZebDKv1zo</b>\n</div>\n <div class="youtube_video">\nC_ZebDKv1zo\n</div>\n green</p>')

    def test_usage_with_template_dirs_fallback(self):
        """
        A if the a template in the specified dir doesn't exist it should fallback
        to using the default of inlines.
        """

        from django.conf import settings
        inlines.registry.register('youtube', YoutubeInline)

        template = "{% load inlines %}<p>{% process_inlines body in 'nonexistent_inlines' %}</p>"
        context = {
            'body': u"This is my YouTube video: {{ youtube C_ZebDKv1zo }}",
        }
        self.assertEqual(self.render(template, context), u'<p>This is my YouTube video: <div class="youtube_video">\n<object width="480" height="295">\n  <param name="movie" value="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1"></param>\n  <param name="allowFullScreen" value="true"></param>\n  <param name="allowscriptaccess" value="always"></param>\n  <embed src="http://www.youtube.com/v/C_ZebDKv1zo&hl=en&fs=1" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="480" height="295"></embed>\n</object>  \n</div>\n</p>')

########NEW FILE########
__FILENAME__ = test_inlines
from django_inlines.inlines import InlineBase, ModelInline
from core.models import User


class QuineInline(InlineBase):
    """
    A simple inline that returns itself.
    """
    def render(self):
        bits = []
        if self.variant:
            bits.append(':%s' % self.variant)
        else:
            bits.append('')
        if self.value:
            bits.append(self.value)
        for k, v in self.kwargs.items():
            bits.append("%s=%s" % (k,v))
        else:
            return "{{ quine%s }}" % " ".join(bits)


class DoubleInline(InlineBase):
    """
    A simple inline that doubles itself.
    """
    def render(self):
        value = self.value
        multiplier = 2
        if self.kwargs.has_key('multiplier'):
            try:
                multiplier = int(self.kwargs['multiplier'])
            except ValueError:
                pass
        try:
            value = int(self.value)
        except ValueError:
            pass
        return value*multiplier


class KeyErrorInline(InlineBase):
    """
    An inline that raises a KeyError. For regression testing.
    """
    def render(self):
        empty = {}
        return empty['this will fail']


class UserInline(ModelInline):
    """
    A inline for the mock user model.
    """
    model = User

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import sys
from os.path import dirname, abspath
sys.path += [dirname(dirname(abspath(__file__)))]

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'django_inlines_tests.db'
 
INSTALLED_APPS = [
    'core',
    'django_inlines',
]
TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.load_template_source',
)

########NEW FILE########
