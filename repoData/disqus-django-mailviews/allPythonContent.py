__FILENAME__ = conf
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mailviews import __version__

import django
from django.conf import settings

if not settings.configured:
    settings.configure()


extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']

project = u'django-mailviews'
copyright = u'2012, DISQUS'
version = release = '.'.join(map(str, __version__))

html_static_path = ['_static']
htmlhelp_basename = 'django-mailviews'

intersphinx_mapping = {
    'python': ('http://docs.python.org/release/%s.%s' % sys.version_info[:2], None),
    'django': ('http://docs.djangoproject.com/en/%s.%s/' % django.VERSION[:2],
        'http://docs.djangoproject.com/en/%s.%s/_objects/' % django.VERSION[:2]),
}

autodoc_member_order = 'bysource'
autodoc_default_flags = ('members',)

########NEW FILE########
__FILENAME__ = helpers
from django.conf import settings


def should_use_staticfiles():
    return 'django.contrib.staticfiles' in settings.INSTALLED_APPS

########NEW FILE########
__FILENAME__ = messages
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.template import Context
from django.template.loader import get_template, select_template

from mailviews.utils import unescape


class EmailMessageView(object):
    """
    Base class for encapsulating the logic for the rendering and sending
    class-based email messages.
    """
    message_class = EmailMessage

    @property
    def headers(self):
        """
        A dictionary containing the headers for this message.
        """
        if not hasattr(self, '_headers'):
            self._headers = {}
        return self._headers

    def render_subject(self, context):
        raise NotImplementedError  # Must be implemented by subclasses.

    def render_body(self, context):
        raise NotImplementedError  # Must be implemented by subclasses.

    def get_context_data(self, **kwargs):
        """
        Returns the context that will be used for rendering this message.

        :rtype: :class:`django.template.Context`
        """
        return Context(kwargs)

    def render_to_message(self, extra_context=None, **kwargs):
        """
        Renders and returns an unsent message with the provided context.

        Any extra keyword arguments passed will be passed through as keyword
        arguments to the message constructor.

        :param extra_context: Any additional context to use when rendering the
            templated content.
        :type extra_context: :class:`dict`
        :returns: A message instance.
        :rtype: :attr:`.message_class`
        """
        if extra_context is None:
            extra_context = {}

        # Ensure our custom headers are added to the underlying message class.
        kwargs.setdefault('headers', {}).update(self.headers)

        context = self.get_context_data(**extra_context)
        return self.message_class(
            subject=self.render_subject(context),
            body=self.render_body(context),
            **kwargs)

    def send(self, extra_context=None, **kwargs):
        """
        Renders and sends an email message.

        All keyword arguments other than ``extra_context`` are passed through
        as keyword arguments when constructing a new :attr:`message_class`
        instance for this message.

        This method exists primarily for convenience, and the proper
        rendering of your message should not depend on the behavior of this
        method. To alter how a message is created, override
        :meth:``render_to_message`` instead, since that should always be
        called, even if a message is not sent.

        :param extra_context: Any additional context data that will be used
            when rendering this message.
        :type extra_context: :class:`dict`
        """
        message = self.render_to_message(extra_context=extra_context, **kwargs)
        return message.send()


class TemplatedEmailMessageView(EmailMessageView):
    """
    An email message view that uses Django templates for rendering the message
    subject and plain text body.
    """
    #: A template name (or list of template names) that will be used to render
    #: the subject of this message. The rendered subject should be plain text
    #: without any linebreaks. (Any trailing whitespace will be automatically
    #: stripped.) :attr:`.subject_template` will precedence over this value,
    #: if set.
    subject_template_name = None

    #: A template name (or list of template names) that will be used to render
    #: the plain text body of this message. :attr:`.body_template` will take
    #: precedence over this value, if set.
    body_template_name = None

    def _get_template(self, value):
        if isinstance(value, (list, tuple)):
            return select_template(value)
        else:
            return get_template(value)

    def _get_subject_template(self):
        if getattr(self, '_subject_template', None) is not None:
            return self._subject_template

        if self.subject_template_name is None:
            raise ImproperlyConfigured('A `subject_template` or '
                '`subject_template_name` must be provided to render this '
                'message subject.')

        return self._get_template(self.subject_template_name)

    def _set_subject_template(self, template):
        self._subject_template = template

    #: Returns the subject template that will be used for rendering this
    #: message. If the subject template has been explicitly set, that template
    #: will be used. If not, the template(s) defined as
    #: :attr:`.subject_template_name` will be used instead.
    subject_template = property(_get_subject_template, _set_subject_template)

    def _get_body_template(self):
        if getattr(self, '_body_template', None) is not None:
            return self._body_template

        if self.body_template_name is None:
            raise ImproperlyConfigured('A `body_template` or '
                '`body_template_name` must be provided to render this '
                'message subject.')

        return self._get_template(self.body_template_name)

    def _set_body_template(self, template):
        self._body_template = template

    #: Returns the body template that will be used for rendering this message.
    #: If the body template has been explicitly set, that template will be
    #: used. If not, the template(s) defined as :attr:`.body_template_name`
    #: will be used instead.
    body_template = property(_get_body_template, _set_body_template)

    def render_subject(self, context):
        """
        Renders the message subject for the given context.

        The context data is automatically unescaped to avoid rendering HTML
        entities in ``text/plain`` content.

        :param context: The context to use when rendering the subject template.
        :type context: :class:`~django.template.Context`
        :returns: A rendered subject.
        :rtype: :class:`str`
        """
        rendered = self.subject_template.render(unescape(context))
        return rendered.strip()

    def render_body(self, context):
        """
        Renders the message body for the given context.

        The context data is automatically unescaped to avoid rendering HTML
        entities in ``text/plain`` content.

        :param context: The context to use when rendering the body template.
        :type context: :class:`~django.template.Context`
        :returns: A rendered body.
        :rtype: :class:`str`
        """
        return self.body_template.render(unescape(context))


class TemplatedHTMLEmailMessageView(TemplatedEmailMessageView):
    """
    An email message view that uses Django templates for rendering the message
    subject, plain text and HTML body.
    """
    message_class = EmailMultiAlternatives

    #: A template name (or list of template names) that will be used to render
    #: the HTML body of this message. :attr:`.html_body_template` will take
    #: precedence over this value, if set.
    html_body_template_name = None

    def _get_html_body_template(self):
        if getattr(self, '_html_body_template', None) is not None:
            return self._html_body_template

        if self.html_body_template_name is None:
            raise ImproperlyConfigured('An `html_body_template` or '
                '`html_body_template_name` must be provided to render this '
                'message HTML body.')

        return self._get_template(self.html_body_template_name)

    def _set_html_body_template(self, template):
        self._html_body_template = template

    #: Returns the body template that will be used for rendering the HTML body
    #: of this message. If the HTML body template has been explicitly set, that
    #: template will be used. If not, the template(s) defined as
    #: :attr:`.html_body_template_name` will be used instead.
    html_body_template = property(_get_html_body_template,
        _set_html_body_template)

    def render_html_body(self, context):
        """
        Renders the message body for the given context.

        :param context: The context to use when rendering the body template.
        :type context: :class:`~django.template.Context`
        :returns: A rendered HTML body.
        :rtype: :class:`str`
        """
        return self.html_body_template.render(context)

    def render_to_message(self, extra_context=None, *args, **kwargs):
        """
        Renders and returns an unsent message with the given context.

        Any extra keyword arguments passed will be passed through as keyword
        arguments to the message constructor.

        :param extra_context: Any additional context to use when rendering
            templated content.
        :type extra_context: :class:`dict`
        :returns: A message instance.
        :rtype: :attr:`.message_class`
        """
        message = super(TemplatedHTMLEmailMessageView, self)\
            .render_to_message(extra_context, *args, **kwargs)

        if extra_context is None:
            extra_context = {}

        context = self.get_context_data(**extra_context)
        content = self.render_html_body(context)
        message.attach_alternative(content, mimetype='text/html')
        return message

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = previews
import logging
import os
from base64 import b64encode
from collections import namedtuple
from email.header import decode_header

try:
    from django.conf.urls import patterns, include, url
except ImportError:
    # Django <1.4 compat
    from django.conf.urls.defaults import patterns, include, url

from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule

from mailviews.helpers import should_use_staticfiles
from mailviews.utils import split_docstring, unimplemented


logger = logging.getLogger(__name__)


URL_NAMESPACE = 'mailviews'

ModulePreviews = namedtuple('ModulePreviews', ('module', 'previews'))


def maybe_decode_header(header):
    """
    Decodes an encoded 7-bit ASCII header value into it's actual value.
    """
    value, encoding = decode_header(header)[0]
    if encoding:
        return value.decode(encoding)
    else:
        return value


class PreviewSite(object):
    def __init__(self):
        self.__previews = {}

    def __iter__(self):
        """
        Returns an iterator of :class:`ModulePreviews` tuples, sorted by module nae.
        """
        for module in sorted(self.__previews.keys()):
            previews = ModulePreviews(module, sorted(self.__previews[module].values(), key=str))
            yield previews

    def register(self, cls):
        """
        Adds a preview to the index.
        """
        preview = cls(site=self)
        logger.debug('Registering %r with %r', preview, self)
        index = self.__previews.setdefault(preview.module, {})
        index[cls.__name__] = preview

    @property
    def urls(self):
        urlpatterns = patterns('',
            url(regex=r'^$',
                view=self.list_view,
                name='list'),
            url(regex=r'^(?P<module>.+)/(?P<preview>.+)/$',
                view=self.detail_view,
                name='detail'),
        )

        if not should_use_staticfiles():
            urlpatterns += patterns('',
                url(regex=r'^static/(?P<path>.*)$',
                    view='django.views.static.serve',
                    kwargs={
                        'document_root': os.path.join(os.path.dirname(__file__), 'static'),
                    },
                    name='static'),
                )

        return include(urlpatterns, namespace=URL_NAMESPACE)

    def list_view(self, request):
        """
        Returns a list view response containing all of the registered previews.
        """
        return render(request, 'mailviews/previews/list.html', {
            'site': self,
        })

    def detail_view(self, request, module, preview):
        """
        Looks up a preview in the index, returning a detail view response.
        """
        try:
            preview = self.__previews[module][preview]
        except KeyError:
            raise Http404  # The provided module/preview does not exist in the index.
        return preview.detail_view(request)


class Preview(object):
    #: The message view class that will be instantiated to render the preview
    #: message. This must be defined by subclasses.
    message_view = property(unimplemented)

    #: The subset of headers to show in the preview panel.
    headers = ('Subject', 'From', 'To')

    #: The title of this email message to use in the previewer. If not provided,
    #: this will default to the name of the message view class.
    verbose_name = None

    #: A form class that will be used to customize the instantiation behavior
    # of the message view class.
    form_class = None

    #: The template that will be rendered for this preview.
    template_name = 'mailviews/previews/detail.html'

    def __init__(self, site):
        self.site = site

    def __unicode__(self):
        return self.verbose_name or self.message_view.__name__

    @property
    def module(self):
        return '%s' % self.message_view.__module__

    @property
    def description(self):
        """
        A longer description of this preview that is used in the preview index.

        If not provided, this defaults to the first paragraph of the underlying
        message view class' docstring.
        """
        return getattr(split_docstring(self.message_view), 'summary', None)

    @property
    def url(self):
        """
        The URL to access this preview.
        """
        return reverse('%s:detail' % URL_NAMESPACE, kwargs={
            'module': self.module,
            'preview': type(self).__name__,
        })

    def get_message_view(self, request, **kwargs):
        return self.message_view(**kwargs)

    def detail_view(self, request):
        """
        Renders the message view to a response.
        """
        context = {
            'preview': self,
        }

        kwargs = {}
        if self.form_class:
            if request.GET:
                form = self.form_class(data=request.GET)
            else:
                form = self.form_class()

            context['form'] = form
            if not form.is_bound or not form.is_valid():
                return render(request, 'mailviews/previews/detail.html', context)

            kwargs.update(form.get_message_view_kwargs())

        message_view = self.get_message_view(request, **kwargs)

        message = message_view.render_to_message()
        raw = message.message()
        headers = SortedDict((header, maybe_decode_header(raw[header])) for header in self.headers)

        context.update({
            'message': message,
            'subject': message.subject,
            'body': message.body,
            'headers': headers,
            'raw': raw.as_string(),
        })

        alternatives = getattr(message, 'alternatives', [])
        try:
            html = next(alternative[0] for alternative in alternatives
                if alternative[1] == 'text/html')
            context.update({
                'html': html,
                'escaped_html': b64encode(html.encode('utf-8')),
            })
        except StopIteration:
            pass

        return render(request, self.template_name, context)


def autodiscover():
    """
    Imports all available previews classes.
    """
    from django.conf import settings
    for application in settings.INSTALLED_APPS:
        module = import_module(application)

        if module_has_submodule(module, 'emails'):
            emails = import_module('%s.emails' % application)
            try:
                import_module('%s.emails.previews' % application)
            except ImportError:
                # Only raise the exception if this module contains previews and
                # there was a problem importing them. (An emails module that
                # does not contain previews is not an error.)
                if module_has_submodule(emails, 'previews'):
                    raise


#: The default preview site.
site = PreviewSite()

########NEW FILE########
__FILENAME__ = mailviews
from __future__ import absolute_import

from django import template

from mailviews.helpers import should_use_staticfiles
from mailviews.previews import URL_NAMESPACE


register = template.Library()


def mailviews_static(path):
    if should_use_staticfiles():
        from django.contrib.staticfiles.templatetags import staticfiles
        return staticfiles.static(path)
    else:
        from django.core.urlresolvers import reverse
        return reverse('%s:static' % URL_NAMESPACE, kwargs={
            'path': path,
        })


register.simple_tag(mailviews_static)

########NEW FILE########
__FILENAME__ = previews
import random

from django import forms
from django.contrib.webdesign.lorem_ipsum import paragraphs, words

from mailviews.previews import Preview, site
from mailviews.tests.emails.views import (BasicEmailMessageView,
    BasicHTMLEmailMessageView)


class BasicPreview(Preview):
    message_view = BasicEmailMessageView
    verbose_name = 'Basic Message'
    description = 'A basic text email message.'

    def get_message_view(self, request):
        subject = words(random.randint(5, 20), common=False)
        content = '\n'.join(paragraphs(random.randint(3, 6)))
        return self.message_view(subject, content)


class BasicHTMLPreview(BasicPreview):
    message_view = BasicHTMLEmailMessageView
    verbose_name = 'Basic HTML Message'
    description = 'A basic HTML email message.'


class CustomizationForm(forms.Form):
    subject = forms.CharField()
    content = forms.CharField(widget=forms.Textarea)

    def get_message_view_kwargs(self):
        return self.cleaned_data


class CustomizablePreview(Preview):
    message_view = BasicEmailMessageView
    verbose_name = 'Basic Message, with Form'
    description = 'A basic text email message, but customizable.'
    form_class = CustomizationForm


site.register(BasicPreview)
site.register(BasicHTMLPreview)
site.register(CustomizablePreview)

########NEW FILE########
__FILENAME__ = views
from django.template import Template

from mailviews.messages import (TemplatedEmailMessageView,
    TemplatedHTMLEmailMessageView)


class TemplateContextMixin(object):
    subject_template = Template('{{ subject }}')
    body_template = Template('{{ content }}')

    def __init__(self, subject, content):
        self.subject = subject
        self.content = content

    def get_context_data(self, *args, **kwargs):
        data = super(TemplateContextMixin, self).get_context_data(*args, **kwargs)
        data.update({
            'subject': self.subject,
            'content': self.content,
        })
        return data


class BasicEmailMessageView(TemplateContextMixin, TemplatedEmailMessageView):
    pass


class BasicHTMLEmailMessageView(TemplateContextMixin, TemplatedHTMLEmailMessageView):
    html_body_template = Template('{{ content|linebreaks }}')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import logging

from django.core.management import execute_manager

from mailviews.tests import settings


logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = tests
import functools
import os

from django.core.exceptions import ImproperlyConfigured
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from django.template import Context, Template, TemplateDoesNotExist
from django.template.loader import get_template

from mailviews.messages import (TemplatedEmailMessageView,
                                TemplatedHTMLEmailMessageView)
from mailviews.previews import URL_NAMESPACE
from mailviews.tests.emails.views import (BasicEmailMessageView,
                                          BasicHTMLEmailMessageView)
from mailviews.tests.emails.previews import (BasicPreview,
                                             BasicHTMLPreview,
                                             CustomizablePreview)
from mailviews.utils import split_docstring


try:
    from django.test.utils import override_settings
except ImportError:
    from mailviews.tests.utils import override_settings  # noqa


using_test_templates = override_settings(
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(__file__), 'templates'),
    ),
    TEMPLATE_LOADERS=(
        'django.template.loaders.filesystem.Loader',
    )
)


class EmailMessageViewTestCase(TestCase):
    def run(self, *args, **kwargs):
        with using_test_templates:
            return super(EmailMessageViewTestCase, self).run(*args, **kwargs)

    def assertTemplateExists(self, name):
        try:
            get_template(name)
        except TemplateDoesNotExist:
            raise AssertionError('Template does not exist: %s' % name)

    def assertTemplateDoesNotExist(self, name):
        try:
            self.assertTemplateExists(name)
        except AssertionError:
            return
        raise AssertionError('Template exists: %s' % name)

    def assertOutboxLengthEquals(self, length):
        self.assertEqual(len(mail.outbox), length)


class TemplatedEmailMessageViewTestCase(EmailMessageViewTestCase):
    message_class = TemplatedEmailMessageView

    def setUp(self):
        self.message = self.message_class()

        self.template = 'Hello, world!'

        self.subject = 'subject'
        self.subject_template = Template('{{ subject }}')

        self.body = 'body'
        self.body_template = Template('{{ body }}')

        self.context_dict = {
            'subject': self.subject,
            'body': self.body,
        }

        self.context = Context(self.context_dict)

        self.render_subject = functools.partial(self.message.render_subject,
            context=self.context)
        self.render_body = functools.partial(self.message.render_body,
            context=self.context)

    def add_templates_to_message(self):
        """
        Adds templates to the fixture message, ensuring it can be rendered.
        """
        self.message.subject_template = self.subject_template
        self.message.body_template = self.body_template

    def test_subject_template_unconfigured(self):
        self.assertRaises(ImproperlyConfigured, self.render_subject)

    def test_subject_invalid_template_name(self):
        template = 'invalid.txt'
        self.assertTemplateDoesNotExist(template)

        self.message.subject_template_name = template
        self.assertRaises(TemplateDoesNotExist, self.render_subject)

    def test_subject_template_name(self):
        template = 'subject.txt'
        self.assertTemplateExists(template)

        self.message.subject_template_name = template
        self.assertEqual(self.render_subject(), self.subject)

    def test_subject_template(self):
        self.message.subject_template = self.subject_template
        self.assertEqual(self.render_subject(), self.subject)

    def test_body_template_unconfigured(self):
        self.assertRaises(ImproperlyConfigured, self.render_body)

    def test_body_invalid_template_name(self):
        template = 'invalid.txt'
        self.assertTemplateDoesNotExist(template)

        self.message.body_template_name = template
        self.assertRaises(TemplateDoesNotExist, self.render_body)

    def test_body_template_name(self):
        template = 'body.txt'
        self.assertTemplateExists(template)

        self.message.body_template_name = template
        self.assertEqual(self.render_body(), self.body + '\n')

    def test_body_template(self):
        self.message.body_template = self.body_template
        self.assertEqual(self.render_body(), self.body)

    def test_render_to_message(self):
        self.add_templates_to_message()
        message = self.message.render_to_message(self.context_dict)
        self.assertEqual(message.subject, self.subject)
        self.assertEqual(message.body, self.body)

    def test_send(self):
        self.add_templates_to_message()
        self.message.send(self.context_dict, to=('ted@disqus.com',))
        self.assertOutboxLengthEquals(1)

    def test_custom_headers(self):
        self.add_templates_to_message()
        address = 'ted@disqus.com'
        self.message.headers['Reply-To'] = address
        self.assertEqual(self.message.headers['Reply-To'], address)

        rendered = self.message.render_to_message()
        self.assertEqual(rendered.extra_headers['Reply-To'], address)

        rendered = self.message.render_to_message(headers={
            'References': 'foo',
        })
        self.assertEqual(rendered.extra_headers['Reply-To'], address)
        self.assertEqual(rendered.extra_headers['References'], 'foo')


class TemplatedHTMLEmailMessageViewTestCase(TemplatedEmailMessageViewTestCase):
    message_class = TemplatedHTMLEmailMessageView

    def setUp(self):
        super(TemplatedHTMLEmailMessageViewTestCase, self).setUp()

        self.html_body = 'html body'
        self.html_body_template = Template('{{ html }}')

        self.context_dict['html'] = self.html_body
        self.context['html'] = self.html_body

        self.render_html_body = functools.partial(
            self.message.render_html_body,
            context=self.context)

    def add_templates_to_message(self):
        """
        Adds templates to the fixture message, ensuring it can be rendered.
        """
        super(TemplatedHTMLEmailMessageViewTestCase, self)\
            .add_templates_to_message()
        self.message.html_body_template = self.html_body_template

    def test_html_body_template_unconfigured(self):
        self.assertRaises(ImproperlyConfigured, self.render_html_body)

    def test_html_body_invalid_template_name(self):
        template = 'invalid.txt'
        self.assertTemplateDoesNotExist(template)

        self.message.html_body_template_name = template
        self.assertRaises(TemplateDoesNotExist, self.render_html_body)

    def test_html_body_template_name(self):
        template = 'body.html'
        self.assertTemplateExists(template)

        self.message.html_body_template_name = template
        self.assertEqual(self.render_html_body(), self.html_body + '\n')

    def test_html_body_template(self):
        self.message.html_body_template = self.html_body_template
        self.assertEqual(self.render_html_body(), self.html_body)

    def test_render_to_message(self):
        self.add_templates_to_message()
        message = self.message.render_to_message(self.context_dict)
        self.assertEqual(message.subject, self.subject)
        self.assertEqual(message.body, self.body)
        self.assertEqual(message.alternatives, [(self.html_body, 'text/html')])

    def test_send(self):
        self.add_templates_to_message()
        self.message.send(self.context_dict, to=('ted@disqus.com',))
        self.assertOutboxLengthEquals(1)


class SplitDocstringTestCase(TestCase):
    def test_split_docstring(self):
        header, body = split_docstring(split_docstring)
        self.assertEqual(header, "Splits the docstring of the given value into it's summary and body.")

    def test_split_docstring_no_body(self):
        def fn():
            """Does a thing."""

        header, body = split_docstring(fn)
        self.assertEqual(header, "Does a thing.")


class PreviewSiteTestCase(TestCase):

    def setUp(self):
        super(PreviewSiteTestCase, self).setUp()
        self.client = Client()

    def test_basic_preview(self):
        url = reverse('%s:detail' % URL_NAMESPACE, kwargs={
            'module': BasicEmailMessageView.__module__,
            'preview': BasicPreview.__name__
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('#body-plain', response.content)
        self.assertIn('#raw', response.content)

    def test_basic_html_preview(self):
        url = reverse('%s:detail' % URL_NAMESPACE, kwargs={
            'module': BasicHTMLEmailMessageView.__module__,
            'preview': BasicHTMLPreview.__name__
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('#html', response.content)
        self.assertIn('#body-plain', response.content)
        self.assertIn('#raw', response.content)

    def test_customizable_preview(self):
        url = reverse('%s:detail' % URL_NAMESPACE, kwargs={
            'module': BasicEmailMessageView.__module__,
            'preview': CustomizablePreview.__name__
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<form', response.content)
        self.assertIn('#body-plain', response.content)
        self.assertIn('#raw', response.content)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import include, patterns, url

from mailviews.previews import autodiscover, site


autodiscover()

urlpatterns = patterns('',
    url(regex=r'', view=site.urls),
)

########NEW FILE########
__FILENAME__ = utils
# flake8: noqa
"""
Backport of `django.test.utils.override_settings` from Django 1.3 and above.
"""
from functools import wraps

from django.conf import settings, UserSettingsHolder


class override_settings(object):
    """
    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, **kwargs):
        self.options = kwargs
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import TransactionTestCase
        if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
            original_pre_setup = test_func._pre_setup
            original_post_teardown = test_func._post_teardown

            def _pre_setup(innerself):
                self.enable()
                original_pre_setup(innerself)
            def _post_teardown(innerself):
                original_post_teardown(innerself)
                self.disable()
            test_func._pre_setup = _pre_setup
            test_func._post_teardown = _post_teardown
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def enable(self):
        override = UserSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        settings._wrapped = override
        # for key, new_value in self.options.items():
        #     setting_changed.send(sender=settings._wrapped.__class__,
        #                          setting=key, value=new_value)

    def disable(self):
        settings._wrapped = self.wrapped
        for key in self.options:
            new_value = getattr(settings, key, None)
            # setting_changed.send(sender=settings._wrapped.__class__,
            #                      setting=key, value=new_value)

########NEW FILE########
__FILENAME__ = utils
import textwrap
from collections import namedtuple

from django.template import Context


Docstring = namedtuple('Docstring', ('summary', 'body'))


def split_docstring(value):
    """
    Splits the docstring of the given value into it's summary and body.

    :returns: a 2-tuple of the format ``(summary, body)``
    """
    docstring = textwrap.dedent(getattr(value, '__doc__', ''))
    if not docstring:
        return None

    pieces = docstring.strip().split('\n\n', 1)
    try:
        body = pieces[1]
    except IndexError:
        body = None

    return Docstring(pieces[0], body)


def unimplemented(*args, **kwargs):
    raise NotImplementedError


def unescape(context):
    """
    Accepts a context object, returning a new context with autoescape off.

    Useful for rendering plain-text templates without having to wrap the entire
    template in an `{% autoescape off %}` tag.
    """
    return Context(context, autoescape=False)

########NEW FILE########
