__FILENAME__ = context_processors
def pjaxr_information(request):
    """
    passes the pjaxr head information to the templates
    """

    response = {
        'pjaxr': request.META.get('HTTP_X_PJAX', False),
    }

    if request.META.get('HTTP_X_PJAX_NAMESPACE', False):
        response.update({
            'pjaxr_namespace': request.META['HTTP_X_PJAX_NAMESPACE'],
        })

    return response

########NEW FILE########
__FILENAME__ = mixins
class PjaxrMixin(object):
    """
    View mixin that provides pjaxr functionality
    """
    namespace = ""
    parent_namespace = ""
    matching_count = 0

    def get_matching_count(self, request):
        """
        takes current_namespace to return the matching namespaces of the previous pjaxr-request and the current
        """
        if not self.is_pjaxr_request(request):
            return 0
        current_namespaces = self.namespace.split(".")
        previous_namespaces = self.get_previous_namespace(request).split(".")
        level = 0
        matching_count = 0
        while level < len(previous_namespaces) and level < len(current_namespaces):
            if previous_namespaces[level] == current_namespaces[level]:
                level += 1
                matching_count = level
            else:
                break
        return matching_count

    def get_previous_namespace(self, request):
        if self.is_pjaxr_request(request) and request.META.get('HTTP_X_PJAX_NAMESPACE', False):
            return request.META['HTTP_X_PJAX_NAMESPACE']
        return ""

    def is_pjaxr_request(self, request):
        return True if request.META.get('HTTP_X_PJAX_NAMESPACE', False) else False

    def get_context_data(self, **kwargs):
        context = super(PjaxrMixin, self).get_context_data(**kwargs)
        context.update({'pjaxr_namespace_current': self.namespace})
        context.update({'pjaxr_namespace_parent': self.parent_namespace})
        return context


class IekadouPjaxrMixin(PjaxrMixin):
    pjaxr_site = True
    pjaxr_page = True
    pjaxr_content = True
    pjaxr_inner_content = True

    def dispatch(self, request, *args, **kwargs):
        self.matching_count = self.get_matching_count(request)
        self.pjaxr_site = self.matching_count <= 0
        self.pjaxr_page = self.matching_count <= 1
        self.pjaxr_content = self.matching_count <= 2
        self.pjaxr_inner_content = self.matching_count <= 3
        return super(IekadouPjaxrMixin, self).dispatch(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = models
# Dummy models.py for django app recognition
########NEW FILE########
__FILENAME__ = runtests
import os
import sys


# adjusting sys.path
path = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'django_pjaxr.test_settings'


import django
from django.conf import settings
from django.test.utils import get_runner


def usage():
    return """
    Usage: python runtests.py [UnitTestClass].[method]

    You can pass the Class name of the `UnitTestClass` you want to test.

    Append a method name if you only want to test a specific method of that class.
    """


def main():
    TestRunner = get_runner(settings)

    test_runner = TestRunner()

    failures = test_runner.run_tests(['django_pjaxr'])

    sys.exit(failures)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = pjaxr_extends
from django.conf import settings
from django.template.base import Library, TemplateSyntaxError, FilterExpression
from django.template.loader import get_template  # import to solve ImportErrors
from django.template.loader_tags import ExtendsNode

register = Library()


class PjaxrExtendsNode(ExtendsNode):
    def __init__(self, nodelist, parent_name, pjaxr_namespace, pjaxr_template, template_dirs=None):
        super(PjaxrExtendsNode, self).__init__(nodelist, parent_name, template_dirs=template_dirs)
        self.pjaxr_namespace = pjaxr_namespace
        self.pjaxr_template = pjaxr_template

    def __repr__(self):
        return '<PjaxrExtendsNode: extends %s>' % self.parent_name.token

    def get_parent(self, context):
        pjaxr_context = dict((k, v) for d in context.dicts for k, v in d.items() if (k == 'pjaxr' or k == 'pjaxr_namespace'))
        if pjaxr_context.get('pjaxr', False):
            try:
                namespace = pjaxr_context['pjaxr_namespace']
            except KeyError:
                pass  # no namespace given, so do not change parent_name => initial request
            else:
                if namespace.startswith(self.pjaxr_namespace.resolve(context)):
                    self.parent_name = self.pjaxr_template

        return super(PjaxrExtendsNode, self).get_parent(context)


@register.tag()
def pjaxr_extends(parser, token):
    bits = token.split_contents()
    if len(bits) != 4 and len(bits) != 3 and len(bits) != 2:
        raise TemplateSyntaxError("'%s' takes 1 - 3 arguments" % bits[0])

    nodelist = parser.parse()

    if nodelist.get_nodes_by_type(PjaxrExtendsNode) or nodelist.get_nodes_by_type(ExtendsNode):
        raise TemplateSyntaxError("'pjaxr_extends' and 'extends' cannot appear more than once in the same template!")

    if len(bits) > 2:
        try:
            # format DEFAULT_PJAXR_TEMPLATE string to fit into FilterExpression as token
            pjaxr_template = parser.compile_filter(bits[3]) if (len(bits) == 4) else FilterExpression("'{0}'".format(settings.DEFAULT_PJAXR_TEMPLATE), parser)
        except AttributeError:
            raise TemplateSyntaxError("No Pjaxr template set, even no default!")
        return PjaxrExtendsNode(nodelist, parser.compile_filter(bits[1]), parser.compile_filter(bits[2]), pjaxr_template)
    return ExtendsNode(nodelist, parser.compile_filter(bits[1]))

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.test import TestCase, Client

from django_pjaxr.test_views import *


urlpatterns = patterns('',
    url(r'^page1/$',                                Page1View.as_view(),                    name='page_1'),
    url(r'^page1/content1/$',                       Page1Content1View.as_view(),            name='content_1'),
    url(r'^page1/content1/inner_content1/$',        Page1Content1InnerContent1View.as_view(),            name='inner_content_1'),
    url(r'^page1/content1/inner_content2/$',        Page1Content1InnerContent2View.as_view(),            name='inner_content_2'),
    url(r'^page1/content2/$',                       Page1Content2View.as_view(),            name='content_2'),
    url(r'^page2/$',                                Page2View.as_view(),                    name='page_2'),
    url(r'^no-pjaxr-page/$',                        NoPjaxrView.as_view(),                  name='no_pjaxr_page'),
)


class TestPjaxrRequests(TestCase):

    urls = 'django_pjaxr.tests'
    page_1_string = 'page_1'
    content_1_string = 'content_1'
    content_2_string = 'content_2'
    # underscore to prevent detecting content_1 as part of inner_content_1
    inner_content_1_string = 'inner_con_tent_1'
    inner_content_2_string = 'inner_con_tent_2'
    page_2_string = 'page_2'
    no_pjaxr_page_string = 'no-pjaxr-page'

    # testing page level namespace
    def test_page_1_no_pjaxr(self):
        client = Client()
        response = client.get(reverse('page_1'))
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, '<html>')
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, 'Site1.Page1')

    def test_page_1_pjaxr_with_namespace(self):
        client = Client()
        response = client.get(reverse('page_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page2'})
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1')

    def test_page_1_pjaxr_different_namespace(self):
        client = Client()
        response = client.get(reverse('page_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site2'})
        self.assertContains(response, self.page_1_string)
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1')

    def test_page_1_pjaxr_no_namespace(self):
        client = Client()
        response = client.get(reverse('page_1'), **{'HTTP_X_PJAX': 'true'})
        self.assertContains(response, self.page_1_string)
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1')

    # testing content level namespace
    def test_content_1_no_pjaxr(self):
        client = Client()
        response = client.get(reverse('content_1'))
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, '<html>')
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, 'Site1.Page1.Content1')

    def test_content_1_pjaxr_current_namespace(self):
        client = Client()
        response = client.get(reverse('content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page1.Content1'})
        self.assertNotContains(response, self.page_1_string)
        self.assertNotContains(response, self.content_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1')

    def test_content_1_pjaxr_page_namespace(self):
        client = Client()
        response = client.get(reverse('content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page1'})
        self.assertNotContains(response, self.page_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1')

    def test_content_1_pjaxr_content_namespace(self):
        client = Client()
        response = client.get(reverse('content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page1.Content2'})
        self.assertNotContains(response, self.page_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1')

    def test_content_1_pjaxr_different_page_namespace(self):
        client = Client()
        response = client.get(reverse('content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page2'})
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1')

    def test_content_1_pjaxr_different_site_namespace(self):
        client = Client()
        response = client.get(reverse('content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site2.Page1'})
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1')

    def test_content_1_pjaxr_no_namespace(self):
        client = Client()
        response = client.get(reverse('content_1'), **{'HTTP_X_PJAX': 'true'})
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1')

    # testing inner_content level namespace
    def test_inner_content_1_no_pjaxr(self):
        client = Client()
        response = client.get(reverse('inner_content_1'))
        self.assertContains(response, self.inner_content_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, '<html>')
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, 'Site1.Page1.Content1.InnerContent1')

    def test_inner_content_1_pjaxr_with_namespace(self):
        client = Client()
        response = client.get(reverse('inner_content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page1.Content1.InnerContent2'})
        self.assertContains(response, self.inner_content_1_string)
        self.assertNotContains(response, self.content_1_string)
        self.assertNotContains(response, self.page_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1.InnerContent1')

    def test_inner_content_1_pjaxr_different_content_namespace(self):
        client = Client()
        response = client.get(reverse('inner_content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page1.Content2'})
        self.assertContains(response, self.inner_content_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertNotContains(response, self.page_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1.InnerContent1')

    def test_inner_content_1_pjaxr_different_page_namespace(self):
        client = Client()
        response = client.get(reverse('inner_content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site1.Page2'})
        self.assertContains(response, self.inner_content_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, self.page_1_string)
        self.assertContains(response, '<pjaxr-body>')
        self.assertNotContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1.InnerContent1')

    def test_inner_content_1_pjaxr_different_site_namespace(self):
        client = Client()
        response = client.get(reverse('inner_content_1'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site2.Page1.Content1'})
        self.assertContains(response, self.inner_content_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, self.page_1_string)
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1.InnerContent1')

    def test_inner_content_1_pjaxr_no_namespace(self):
        client = Client()
        response = client.get(reverse('inner_content_1'), **{'HTTP_X_PJAX': 'true'})
        self.assertContains(response, self.inner_content_1_string)
        self.assertContains(response, self.content_1_string)
        self.assertContains(response, self.page_1_string)
        self.assertNotContains(response, '<pjaxr-body>')
        self.assertContains(response, '<html>')
        self.assertContains(response, 'Site1.Page1.Content1.InnerContent1')

    # testing non pjaxr page
    def test_non_pjaxr_page(self):
        client = Client()
        response = client.get(reverse('no_pjaxr_page'))
        self.assertContains(response, self.no_pjaxr_page_string)
        self.assertContains(response, '<html>')
        self.assertNotContains(response, '<pjaxr-body>')

    def test_non_pjaxr_page_no_namespace(self):
        client = Client()
        response = client.get(reverse('no_pjaxr_page'), **{'HTTP_X_PJAX': 'true'})
        self.assertContains(response, self.no_pjaxr_page_string)
        self.assertContains(response, '<html>')
        self.assertNotContains(response, '<pjaxr-body>')

    def test_non_pjaxr_page_with_namespace(self):
        client = Client()
        response = client.get(reverse('no_pjaxr_page'), **{'HTTP_X_PJAX': 'true', 'HTTP_X_PJAX_NAMESPACE': 'Site2.Page1.Content1'})
        self.assertContains(response, self.no_pjaxr_page_string)
        self.assertContains(response, '<html>')
        self.assertNotContains(response, '<pjaxr-body>')

########NEW FILE########
__FILENAME__ = test_settings
# Django settings for testproject project.
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DEBUG_PROPAGATE_EXCEPTIONS = True

ALLOWED_HOSTS = ['*']

ADMINS = ()

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'sqlite.db',                     # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-uk'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'u@x-aj9(hoh#rb-^ymf#g2jx_hp0vj7u5#b@ag1n^seu9e!%cy'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

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
)

STATIC_URL = '/static/'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
)

AUTH_USER_MODEL = 'auth.User'

import django

if django.VERSION < (1, 3):
    INSTALLED_APPS += ('staticfiles',)


# django Pjaxr
from django.template import add_to_builtins
add_to_builtins('django_pjaxr.templatetags.pjaxr_extends',)

TEMPLATE_CONTEXT_PROCESSORS = ('django_pjaxr.context_processors.pjaxr_information',)

INSTALLED_APPS += ('django_pjaxr', )

DEFAULT_PJAXR_TEMPLATE = "django_pjaxr/pjaxr.html"

########NEW FILE########
__FILENAME__ = test_views
from django.views.generic import TemplateView

from django_pjaxr.mixins import IekadouPjaxrMixin


class Page1View(IekadouPjaxrMixin, TemplateView):
    template_name = 'tests/page_1.html'
    namespace = "Site1.Page1"

    def get_context_data(self, **kwargs):
        result = super(Page1View, self).get_context_data(**kwargs)
        if self.pjaxr_site:
            result.update({'site_string': 'site_1'})
        if self.pjaxr_page:
            result.update({'page_string': 'page_1'})
        return result


class Page1Content1View(IekadouPjaxrMixin, TemplateView):
    template_name = 'tests/page_1_content_1.html'
    namespace = "Site1.Page1.Content1"

    def get_context_data(self, **kwargs):
        result = super(Page1Content1View, self).get_context_data(**kwargs)
        if self.pjaxr_site:
            result.update({'site_string': 'site_1'})
        if self.pjaxr_page:
            result.update({'page_string': 'page_1'})
        if self.pjaxr_content:
            result.update({'content_string': 'content_1'})
        return result


class Page1Content1InnerContent1View(IekadouPjaxrMixin, TemplateView):
    template_name = 'tests/page_1_content_1_inner_content_1.html'
    namespace = "Site1.Page1.Content1.InnerContent1"

    def get_context_data(self, **kwargs):
        result = super(Page1Content1InnerContent1View, self).get_context_data(**kwargs)
        if self.pjaxr_site:
            result.update({'site_string': 'site_1'})
        if self.pjaxr_page:
            result.update({'page_string': 'page_1'})
        if self.pjaxr_content:
            result.update({'content_string': 'content_1'})
        if self.pjaxr_inner_content:
            result.update({'inner_content_string': 'inner_con_tent_1'})
        return result


class Page1Content1InnerContent2View(IekadouPjaxrMixin, TemplateView):
    template_name = 'tests/page_1_content_1_inner_content_2.html'
    namespace = "Site1.Page1.Content1.InnerContent2"

    def get_context_data(self, **kwargs):
        result = super(Page1Content1InnerContent2View, self).get_context_data(**kwargs)
        if self.pjaxr_site:
            result.update({'site_string': 'site_1'})
        if self.pjaxr_page:
            result.update({'page_string': 'page_1'})
        if self.pjaxr_content:
            result.update({'content_string': 'content_1'})
        if self.pjaxr_content:
            result.update({'inner_content_string': 'inner_con_tent_2'})
        return result


class Page1Content2View(IekadouPjaxrMixin, TemplateView):
    template_name = 'tests/page_1_content_2.html'
    namespace = "Site1.Page1.Content2"

    def get_context_data(self, **kwargs):
        result = super(Page1Content2View, self).get_context_data(**kwargs)
        if self.pjaxr_site:
            result.update({'site_string': 'site_1'})
        if self.pjaxr_page:
            result.update({'page_string': 'page_1'})
        if self.pjaxr_content:
            result.update({'content_string': 'content_2'})
        return result


class Page2View(IekadouPjaxrMixin, TemplateView):
    template_name = 'tests/page_2.html'
    namespace = "Site1.Page2"

    def get_context_data(self, **kwargs):
        result = super(Page2View, self).get_context_data(**kwargs)
        if self.pjaxr_site:
            result.update({'site_string': 'site_1'})
        if self.pjaxr_page:
            result.update({'page_string': 'page_2'})
        return result


class NoPjaxrView(TemplateView):
    template_name = 'tests/no_pjaxr_page.html'

    def get_context_data(self, **kwargs):
        result = super(NoPjaxrView, self).get_context_data(**kwargs)
        result.update({'no_pjaxr_page_string': 'no-pjaxr-page'})
        return result

########NEW FILE########
