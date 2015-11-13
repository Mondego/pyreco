__FILENAME__ = admin
from django.contrib import admin

from garfield.models import ComicStrip


class ComicStripAdmin(admin.ModelAdmin):
    list_display = ('name', 'language', 'publication_date')
    list_filter = ('language',)


admin.site.register(ComicStrip, ComicStripAdmin)

########NEW FILE########
__FILENAME__ = extra_urls
from django.utils.translation import ugettext_noop as _

from transurlvania.defaults import *


urlpatterns = patterns('garfield.views',
    url(r'^jim-davis/$', 'jim_davis', name='garfield_jim_davis'),
)

########NEW FILE########
__FILENAME__ = models
import datetime

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from transurlvania.decorators import permalink_in_lang


class ComicStrip(models.Model):
    """
    A Garfield comic strip
    """
    name = models.CharField(_('name'), max_length=255)
    comic = models.URLField(_('comic'))
    publication_date = models.DateTimeField(_('publish date/time'),
        default=datetime.datetime.now)
    public = models.BooleanField(_('public'), default=True)
    language = models.CharField(_('language'), max_length=5,
            choices=settings.LANGUAGES)

    class Meta:
        verbose_name = _('comic strip')
        verbose_name_plural = _('comic strips')

    def __unicode__(self):
        return self.name

    @permalink_in_lang
    def get_absolute_url(self):
        return ('garfield_comic_strip_detail', self.language, (), {'slug': self.slug,})

########NEW FILE########
__FILENAME__ = tests
#encoding=utf-8
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_resolver, reverse, clear_url_caches
from django.core.urlresolvers import NoReverseMatch
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, Client
from django.utils import translation, http

import transurlvania.settings
from transurlvania import urlresolvers as transurlvania_resolvers
from transurlvania.translators import NoTranslationError
from transurlvania.urlresolvers import reverse_for_language
from transurlvania.utils import complete_url
from transurlvania.views import detect_language_and_redirect

from garfield.views import home, about_us, the_president
from garfield.views import comic_strip_list, comic_strip_detail, landing
from garfield.views import jim_davis


french_version_anchor_re = re.compile(r'<a class="french-version-link" href="([^"]*)">')


class TransURLTestCase(TestCase):
    """
    Test the translatable URL functionality
    These tests require that English (en) and French (fr) are both listed in
    the LANGUAGES list in settings.
    """
    def setUp(self):
        translation.activate('en')

    def tearDown(self):
        translation.deactivate()
        clear_url_caches()

    def testNormalURL(self):
        self.assertEqual(get_resolver(None).resolve('/en/garfield/')[0], landing)
        translation.activate('fr')
        self.assertEqual(get_resolver(None).resolve('/fr/garfield/')[0], landing)

    def testTransMatches(self):
        self.assertEqual(get_resolver(None).resolve('/en/about-us/')[0], about_us)
        translation.activate('fr')
        self.assertEqual(get_resolver(None).resolve('/fr/a-propos-de-nous/')[0], about_us)

    def testMultiModuleMixedURL(self):
        self.assertEqual(get_resolver(None).resolve('/en/garfield/jim-davis/')[0], jim_davis)
        translation.activate('fr')
        self.assertEqual(get_resolver(None).resolve('/fr/garfield/jim-davis/')[0], jim_davis)

    def testMultiModuleTransURL(self):
        self.assertEqual(get_resolver(None).resolve(u'/en/garfield/the-president/')[0], the_president)
        translation.activate('fr')
        self.assertEqual(get_resolver(None).resolve(u'/fr/garfield/le-président/')[0], the_president)

    def testRootURLReverses(self):
        self.assertEqual(reverse(detect_language_and_redirect, 'tests.urls'), '/')
        translation.activate('fr')
        self.assertEqual(reverse(detect_language_and_redirect, 'tests.urls'), '/')

    def testNormalURLReverses(self):
        translation.activate('en')
        self.assertEqual(reverse(landing), '/en/garfield/')
        clear_url_caches()
        translation.activate('fr')
        self.assertEqual(reverse(landing), '/fr/garfield/')

    def testTransReverses(self):
        translation.activate('en')
        self.assertEqual(reverse(the_president), '/en/garfield/the-president/')
        # Simulate URLResolver cache reset between requests
        clear_url_caches()
        translation.activate('fr')
        self.assertEqual(reverse(the_president), http.urlquote(u'/fr/garfield/le-président/'))

    def testReverseForLangSupportsAdmin(self):
        try:
            reverse_for_language('admin:garfield_comicstrip_add', 'en')
        except NoReverseMatch, e:
            self.fail("Reverse lookup failed: %s" % e)


class LangInPathTestCase(TestCase):
    """
    Test language setting via URL path
    LocaleMiddleware and LangInPathMiddleware must be listed in
    MIDDLEWARE_CLASSES for these tests to run properly.
    """
    def setUp(self):
        translation.activate('en')

    def tearDown(self):
        translation.deactivate()

    def testLangDetectionViewRedirectsToLang(self):
        self.client.cookies['django_language'] = 'de'
        response = self.client.get('/')
        self.assertRedirects(response, '/de/')

    def testNormalURL(self):
        response = self.client.get('/en/garfield/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'garfield/landing.html')
        self.assertEqual(response.context.get('LANGUAGE_CODE', None), 'en')
        response = self.client.get('/fr/garfield/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'garfield/landing.html')
        self.assertEqual(response.context.get('LANGUAGE_CODE', None), 'fr')

    def testTranslatedURL(self):
        response = self.client.get('/en/garfield/the-cat/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'garfield/comicstrip_list.html')
        self.assertEqual(response.context.get('LANGUAGE_CODE', None), 'en')
        response = self.client.get('/fr/garfield/le-chat/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'garfield/comicstrip_list.html')
        self.assertEqual(response.context.get('LANGUAGE_CODE', None), 'fr')

    def testReverseForLanguage(self):
        translation.activate('en')
        self.assertEquals(
            reverse_for_language(the_president, 'en'),
            '/en/garfield/the-president/'
        )
        self.assertEquals(
            reverse_for_language(the_president, 'fr'),
            http.urlquote('/fr/garfield/le-président/')
        )

        translation.activate('fr')
        self.assertEquals(
            reverse_for_language(the_president, 'fr'),
            http.urlquote('/fr/garfield/le-président/')
        )
        self.assertEquals(
            reverse_for_language(the_president, 'en'),
            '/en/garfield/the-president/'
        )


class LangInDomainTestCase(TestCase):
    """
    Test language setting via URL path
    LangInDomainMiddleware must be listed in MIDDLEWARE_CLASSES for these tests
    to run properly.
    """
    urls = 'tests.urls_without_lang_prefix'

    def setUp(self):
        transurlvania.settings.LANGUAGE_DOMAINS = {
            'en': ('www.trapeze-en.com', 'English Site'),
            'fr': ('www.trapeze-fr.com', 'French Site')
        }

    def tearDown(self):
        translation.deactivate()
        transurlvania.settings.LANGUAGE_DOMAINS = {}

    def testRootURL(self):
        translation.activate('en')
        client = Client(SERVER_NAME='www.trapeze-fr.com')
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('LANGUAGE_CODE'), 'fr')
        transurlvania.settings.LANGUAGE_DOMAINS = {}

        translation.activate('fr')
        self.client = Client(SERVER_NAME='www.trapeze-en.com')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('LANGUAGE_CODE'), 'en')

    def testURLWithPrefixes(self):
        translation.activate('en')
        response = self.client.get('/en/garfield/', SERVER_NAME='www.trapeze-fr.com')
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/fr/garfield/', SERVER_NAME='www.trapeze-fr.com')
        self.assertEqual(response.context.get('LANGUAGE_CODE'), 'fr')

        translation.activate('fr')
        client = Client(SERVER_NAME='www.trapeze-en.com')
        response = client.get('/fr/garfield/')
        self.assertEqual(response.status_code, 404)
        response = client.get('/en/garfield/')
        self.assertEqual(response.context.get('LANGUAGE_CODE'), 'en')

    def testReverseForLangWithOneDifferentDomain(self):
        transurlvania.settings.LANGUAGE_DOMAINS = {
            'fr': ('www.trapeze-fr.com', 'French Site')
        }

        fr_domain = transurlvania.settings.LANGUAGE_DOMAINS['fr'][0]

        translation.activate('en')
        self.assertEquals(reverse_for_language(about_us, 'en'), '/about-us/')
        self.assertEquals(
            reverse_for_language(about_us, 'fr'),
            u'http://%s/a-propos-de-nous/' % fr_domain
        )

        translation.activate('fr')
        self.assertEquals(
            reverse_for_language(about_us, 'fr'),
            u'http://%s/a-propos-de-nous/' % fr_domain
        )
        self.assertEquals(
            reverse_for_language(about_us, 'en'),
            '/about-us/'
        )

    def testBothDifferentDomains(self):
        transurlvania.settings.LANGUAGE_DOMAINS = {
            'en': ('www.trapeze.com', 'English Site'),
            'fr': ('www.trapeze-fr.com', 'French Site')
        }

        en_domain = transurlvania.settings.LANGUAGE_DOMAINS['en'][0]
        fr_domain = transurlvania.settings.LANGUAGE_DOMAINS['fr'][0]

        translation.activate('en')
        self.assertEquals(
            reverse_for_language(about_us, 'en', 'tests.urls'),
            'http://%s/en/about-us/' % en_domain
        )
        self.assertEquals(
            reverse_for_language(about_us, 'fr', 'tests.urls'),
            'http://%s/fr/a-propos-de-nous/' % fr_domain
        )

        translation.activate('fr')
        self.assertEquals(
            reverse_for_language(about_us, 'fr', 'tests.urls'),
            'http://%s/fr/a-propos-de-nous/' % fr_domain
        )
        self.assertEquals(
            reverse_for_language(about_us, 'en', 'tests.urls'),
            'http://%s/en/about-us/' % en_domain
        )

    def testDefaultViewBasedSwitchingWithSeparateDomains(self):
        transurlvania.settings.LANGUAGE_DOMAINS = {
            'fr': ('www.trapeze-fr.com', 'French Site')
        }

        response = self.client.get('/about-us/')
        french_version_url = french_version_anchor_re.search(response.content).group(1)
        self.assertEqual(french_version_url,
            'http://www.trapeze-fr.com/a-propos-de-nous/'
        )



class LanguageSwitchingTestCase(TestCase):
    fixtures = ['test.json']
    """
    Test the language switching functionality of transurlvania (which also tests
    the `this_page_in_lang` template tag).
    """
    def tearDown(self):
        translation.deactivate()

    def testDefaultViewBasedSwitching(self):
        response = self.client.get('/en/about-us/')
        self.assertTemplateUsed(response, 'about_us.html')
        french_version_url = french_version_anchor_re.search(response.content).group(1)
        self.assertEqual(french_version_url, '/fr/a-propos-de-nous/')

    def testThisPageInLangTagWithFallBack(self):

        template = Template('{% load transurlvania_tags %}'
            '{% this_page_in_lang "fr" "/en/home/" %}'
        )
        output = template.render(Context({}))
        self.assertEquals(output, "/en/home/")

    def testThisPageInLangTagWithVariableFallBack(self):
        translation.activate('en')
        template = Template('{% load transurlvania_tags %}'
            '{% url garfield_landing as myurl %}'
            '{% this_page_in_lang "fr" myurl %}'
        )
        output = template.render(Context({}))
        self.assertEquals(output, '/en/garfield/')

    def testThisPageInLangTagNoArgs(self):
        try:
            template = Template('{% load transurlvania_tags %}'
                '{% this_page_in_lang %}'
            )
        except TemplateSyntaxError, e:
            self.assertEquals(unicode(e), u'this_page_in_lang tag requires at least one argument')
        else:
            self.fail()

    def testThisPageInLangTagExtraArgs(self):
        try:
            template = Template('{% load transurlvania_tags %}'
                '{% this_page_in_lang "fr" "/home/" "/sadf/" %}'
            )
        except TemplateSyntaxError, e:
            self.assertEquals(unicode(e), u'this_page_in_lang tag takes at most two arguments')
        else:
            self.fail()

# TODO: Add tests for views that implement the view-based and object-based
# translation schemes.


class TransInLangTagTestCase(TestCase):
    """Tests for the `trans_in_lang` template tag."""

    def tearDown(self):
        translation.deactivate()

    def testBasic(self):
        """
        Tests the basic usage of the tag.
        """
        translation.activate('en')
        template_content = '{% load transurlvania_tags %}{% with "French" as myvar %}{{ myvar|trans_in_lang:"fr" }}{% endwith %}'
        template = Template(template_content)
        output = template.render(Context())
        self.assertEquals(output, u'Français')

        translation.activate('fr')
        template_content = '{% load transurlvania_tags %}{% with "French" as myvar %}{{ myvar|trans_in_lang:"en" }}{% endwith %}'
        template = Template(template_content)
        output = template.render(Context())
        self.assertEquals(output, u'French')

    def testVariableArgument(self):
        """
        Tests the tag when using a variable as the lang argument.
        """
        translation.activate('en')
        template_content = '{% load transurlvania_tags %}{% with "French" as myvar %}{% with "fr" as lang %}{{ myvar|trans_in_lang:lang }}{% endwith %}{% endwith %}'
        template = Template(template_content)
        output = template.render(Context())
        self.assertEquals(output, u'Français')

    def testKeepsPresetLanguage(self):
        """
        Tests that the tag does not change the language.
        """
        translation.activate('en')
        template_content = '{% load i18n %}{% load transurlvania_tags %}{% with "French" as myvar %}{{ myvar|trans_in_lang:"fr" }}|{% trans "French" %}{% endwith %}'
        template = Template(template_content)
        output = template.render(Context())
        self.assertEquals(output, u'Français|French')

        translation.activate('fr')
        template_content = '{% load i18n %}{% load transurlvania_tags %}{% with "French" as myvar %}{{ myvar|trans_in_lang:"en" }}|{% trans "French" %}{% endwith %}'
        template = Template(template_content)
        output = template.render(Context())
        self.assertEquals(output, u'French|Français')

    def testNoTranslation(self):
        """
        Tests the tag when there is no translation for the given string.
        """
        translation.activate('en')
        template_content = '{% load transurlvania_tags %}{% with "somethinginvalid" as myvar %}{{ myvar|trans_in_lang:"fr" }}{% endwith %}'
        template = Template(template_content)
        output = template.render(Context())
        self.assertEquals(output, u'somethinginvalid')

    def testRepeated(self):
        """
        Tests the tag when it is used repeatedly for different languages.
        """
        translation.activate('en')
        template_content = '{% load transurlvania_tags %}{% with "French" as myvar %}{{ myvar|trans_in_lang:"en" }}|{{ myvar|trans_in_lang:"fr" }}|{{ myvar|trans_in_lang:"de" }}{% endwith %}'
        template = Template(template_content)
        output = template.render(Context())
        self.assertEquals(output, u'French|Français|Französisch')


def CompleteURLTestCase(TestCase):
    """
    Tests the `complete_url` utility function.
    """
    def tearDown(self):
        translation.deactivate()

    def testPath(self):
        translation.activate('en')
        self.assertEquals(complete_url('/path/'),
            'http://www.trapeze-en.com/path/'
        )
        translation.activate('fr')
        self.assertEquals(complete_url('/path/'),
            'http://www.trapeze-fr.com/path/'
        )

    def testFullUrl(self):
        translation.activate('fr')
        self.assertEquals(complete_url('http://www.google.com/path/'),
            'http://www.google.com/path/'
        )

    def testNoDomain(self):
        translation.activate('de')
        self.assertRaises(ImproperlyConfigured, complete_url, '/path/')

    def testExplicitLang(self):
        translation.activate('en')
        self.assertEquals(complete_url('/path/', 'fr'),
            'http://www.trapeze-fr.com/path/'
        )
        translation.activate('en')
        self.assertEquals(complete_url('/path/', 'en'),
            'http://www.trapeze-en.com/path/'
        )

########NEW FILE########
__FILENAME__ = urls
from django.utils.translation import ugettext_noop as _

from transurlvania.defaults import *


urlpatterns = patterns('garfield.views',
    url(r'^$', 'landing', name='garfield_landing'),
    url(_(r'^the-president/$'), 'the_president', name='garfield_the_president'),
    (_(r'^the-cat/$'), 'comic_strip_list', {}, 'garfield_the_cat'),
    url(_(r'^the-cat/(?:P<strip_id>\d+)/$'), 'comic_strip_detail',
            name='garfield_comic_strip_detail'),
    url(r'', include('garfield.extra_urls')),
)

########NEW FILE########
__FILENAME__ = views
from django.views.generic import simple, list_detail
from django.http import HttpResponse

from garfield.models import ComicStrip


def home(request):
    return simple.direct_to_template(request, 'home.html')


def about_us(request):
    return simple.direct_to_template(request, 'about_us.html')


def landing(request):
    return simple.direct_to_template(request, 'garfield/landing.html')


def the_president(request):
    return simple.direct_to_template(request, 'garfield/the_president.html')


def comic_strip_list(request):
    return list_detail.object_list(
            request,
            queryset=ComicStrip.objects.filter(language=request.LANGUAGE_CODE),
            template_object_name='comic_strip',
            )


def comic_strip_detail(request, strip_id):
    return list_detail.object_detail(
            request,
            ComicStrip.objects.filter(language=request.LANGUAGE_CODE),
            id=strip_id,
            template_object_name='comic_strip',
            )


def jim_davis(request):
    return HttpResponse('Jim Davis is the creator of Garfield')

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python

import os, os.path
import sys
import pprint

path, scriptname = os.path.split(__file__)

sys.path.append(os.path.abspath(path))
sys.path.append(os.path.abspath(os.path.join(path, '..')))

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

from django.core import management

management.call_command('test', 'garfield')

########NEW FILE########
__FILENAME__ = settings
import os

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(os.path.dirname(__file__), 'transurlvania_test.db')

LANGUAGE_CODE = 'en'

gettext = lambda s: s

LANGUAGES = (
    ('en', gettext('English')),
    ('fr', gettext('French')),
    ('de', gettext('German')),
)

MULTILANG_LANGUAGE_DOMAINS = {
    'en': ('www.trapeze-en.com', 'English Site'),
    'fr': ('www.trapeze-fr.com', 'French Site')
}

MIDDLEWARE_CLASSES = (
    'transurlvania.middleware.URLCacheResetMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'transurlvania.middleware.LangInPathMiddleware',
    'transurlvania.middleware.LangInDomainMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'transurlvania.middleware.URLTransMiddleware',
)

ROOT_URLCONF = 'tests.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'transurlvania.context_processors.translate',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',

    'transurlvania',
    'garfield',
)

TEMPLATE_DIRS = (
    os.path.join(os.path.realpath(os.path.dirname(__file__)), 'templates/'),
)

########NEW FILE########
__FILENAME__ = urls
from django.contrib import admin
from django.utils.translation import ugettext_noop as _

from transurlvania.defaults import *

admin.autodiscover()

urlpatterns = lang_prefixed_patterns('garfield.views',
    url(r'^$', 'home'),
    url(r'^admin/', include(admin.site.urls)),
    (r'^garfield/', include('garfield.urls')),
    url(_(r'^about-us/$'), 'about_us', name='about_us'),
)


urlpatterns += patterns('transurlvania.views',
    (r'^$', 'detect_language_and_redirect'),
    )

########NEW FILE########
__FILENAME__ = urls_without_lang_prefix
from django.contrib import admin
from django.utils.translation import ugettext_noop as _

from transurlvania.defaults import *

admin.autodiscover()

urlpatterns = patterns('garfield.views',
    url(r'^$', 'home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^garfield/', include('garfield.urls')),
    url(_(r'^about-us/$'), 'about_us', name='about_us'),
)

########NEW FILE########
__FILENAME__ = choices
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


# We need to wrap the language description in the real ugettext if we
# want the translation of the language names to be available (in the admin for
# instance).

LANGUAGES_CHOICES = [
    (code, _(description)) for (code, description) in settings.LANGUAGES
]

########NEW FILE########
__FILENAME__ = context_processors
def translate(request):
    url_translator = getattr(request, 'url_translator', None)
    if url_translator:
        return {'_url_translator': url_translator}
    else:
        return {}
########NEW FILE########
__FILENAME__ = decorators
from transurlvania.translators import BasicScheme, ObjectBasedScheme, DirectToURLScheme


def translate_using_url(url_name):
    return _translate_using(DirectToURLScheme(url_name))


def translate_using_object(object_name):
    return _translate_using(ObjectBasedScheme(object_name))


def translate_using_custom_scheme(scheme):
    return _translate_using(scheme)


def do_not_translate(view_func):
    return _translate_using(BasicScheme())(view_func)


def _translate_using(scheme):
    def translate_decorator(view_func):
        def inner(request, *args, **kwargs):
            if hasattr(request, 'url_translator'):
                request.url_translator.scheme = scheme
            return view_func(request, *args, **kwargs)
        return inner
    return translate_decorator


def permalink_in_lang(func):
    from transurlvania.urlresolvers import reverse_for_language
    def inner(*args, **kwargs):
        bits = func(*args, **kwargs)
        return reverse_for_language(bits[0], bits[1], None, *bits[2:4])
    return inner

########NEW FILE########
__FILENAME__ = defaults
from django.conf.urls.defaults import *
from django.core.urlresolvers import RegexURLPattern

from transurlvania.urlresolvers import LangSelectionRegexURLResolver
from transurlvania.urlresolvers import MultilangRegexURLResolver
from transurlvania.urlresolvers import MultilangRegexURLPattern
from transurlvania.urlresolvers import PocketURLModule


def lang_prefixed_patterns(prefix, *args):
    pattern_list = patterns(prefix, *args)
    return [LangSelectionRegexURLResolver(PocketURLModule(pattern_list))]


def url(regex, view, kwargs=None, name=None, prefix=''):
    # Copied from django.conf.urls.defaults.url
    if isinstance(view, (list,tuple)):
        # For include(...) processing.
        urlconf_module, app_name, namespace = view
        return MultilangRegexURLResolver(regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
    else:
        if isinstance(view, basestring):
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % regex)
            if prefix:
                view = prefix + '.' + view
        return MultilangRegexURLPattern(regex, view, kwargs, name)

# Copied from django.conf.urls.defaults so that it's invoking the url func
# defined here instead of the built-in one.
def patterns(prefix, *args):
    pattern_list = []
    for t in args:
        if isinstance(t, (list, tuple)):
            t = url(prefix=prefix, *t)
        elif isinstance(t, RegexURLPattern):
            t.add_prefix(prefix)
        pattern_list.append(t)
    return pattern_list

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.core import urlresolvers
from django.utils import translation

from transurlvania.settings import LANGUAGE_DOMAINS
from transurlvania.translators import URLTranslator, AutodetectScheme


class LangInPathMiddleware(object):
    """
    Middleware for determining site's language via a language code in the path
    This needs to be installed after the LocaleMiddleware so it can override
    that middleware's decisions.
    """
    def __init__(self):
        self.lang_codes = set(dict(settings.LANGUAGES).keys())

    def process_request(self, request):
        potential_lang_code = request.path_info.lstrip('/').split('/', 1)[0]
        if potential_lang_code in self.lang_codes:
            translation.activate(potential_lang_code)
            request.LANGUAGE_CODE = translation.get_language()


class LangInDomainMiddleware(object):
    """
    Middleware for determining site's language via the domain name used in
    the request.
    This needs to be installed after the LocaleMiddleware so it can override
    that middleware's decisions.
    """

    def process_request(self, request):
        for lang in LANGUAGE_DOMAINS.keys():
            if LANGUAGE_DOMAINS[lang][0] == request.META['SERVER_NAME']:
                translation.activate(lang)
                request.LANGUAGE_CODE = translation.get_language()


class URLTransMiddleware(object):
    def process_request(self, request):
        request.url_translator = URLTranslator(request.build_absolute_uri())

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.url_translator.set_view_info(view_func, view_args, view_kwargs)
        request.url_translator.scheme = AutodetectScheme()
        return None


class BlockLocaleMiddleware(object):
    """
    This middleware will prevent users from accessing the site in a specified
    list of languages unless the user is authenticated and a staff member.
    It should be installed below LocaleMiddleware and AuthenticationMiddleware.
    """
    def __init__(self):
        self.default_lang = settings.LANGUAGE_CODE
        self.blocked_langs = set(getattr(settings, 'BLOCKED_LANGUAGES', []))

    def process_request(self, request):
        lang = getattr(request, 'LANGUAGE_CODE', None)
        if lang in self.blocked_langs and (not hasattr(request, 'user') or not request.user.is_staff):
            request.LANGUAGE_CODE = self.default_lang
            translation.activate(self.default_lang)


class URLCacheResetMiddleware(object):
    """
    Middleware that resets the URL resolver cache after each response.

    Install this as the first middleware in the list so it gets run last as the
    response goes out. It will clear the URLResolver cache. The cache needs to
    be cleared between requests because the URLResolver objects in the cache
    are locked into one language, and the next request might be in a different
    language.

    This middleware is required if the project uses translated URLs.
    """
    def process_response(self, request, response):
        urlresolvers.clear_url_caches()
        return response

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings


HIDE_TRANSLATABLE_APPS = getattr(settings, "MULTILANG_HIDE_TRANSLATABLE_APPS", False)


LANGUAGE_DOMAINS = getattr(settings, "MULTILANG_LANGUAGE_DOMAINS", {})

########NEW FILE########
__FILENAME__ = transurlvania_tags
from django import template
from django.template.defaultfilters import stringfilter

from django.utils.translation import check_for_language
from django.utils.translation.trans_real import translation

from transurlvania.translators import NoTranslationError


register = template.Library()


def token_splitter(token, unquote=False):
    """
    Splits a template tag token and returns a dict containing:
    * tag_name  - The template tag name (ie. first piece in the token)
    * args      - List of arguments to the template tag
    * context_var - Context variable name if the "as" keyword is used,
                    or None otherwise.
    """
    pieces = token.split_contents()

    tag_name = pieces[0]
    args = []
    context_var = None
    if len(pieces) > 2 and pieces[-2] == 'as':
        args = pieces[1:-2]
        context_var = pieces[-1]
    elif len(pieces) > 1:
        args = pieces[1:]

    if unquote:
        args = [strip_quotes(arg) for arg in args]

    return {
        'tag_name':tag_name,
        'args':args,
        'context_var':context_var,
    }


def strip_quotes(string):
    """
    Strips quotes off the ends of `string` if it is quoted
    and returns it.
    """
    if len(string) >= 2:
        if string[0] == string[-1]:
            if string[0] in ('"', "'"):
                string = string[1:-1]
    return string


@register.tag
def this_page_in_lang(parser, token):
    """
    Returns the URL for the equivalent of the current page in the requested language.
    If no URL can be generated, returns nothing.

    Usage:

        {% this_page_in_lang "fr" %}
        {% this_page_in_lang "fr" as var_name %}

    """
    bits = token_splitter(token)
    fallback = None
    if len(bits['args']) < 1:
        raise template.TemplateSyntaxError, "%s tag requires at least one argument" % bits['tag_name']
    elif len(bits['args']) == 2:
        fallback = bits['args'][1]
    elif len(bits['args']) > 2:
        raise template.TemplateSyntaxError, "%s tag takes at most two arguments" % bits['tag_name']

    return ThisPageInLangNode(bits['args'][0], fallback, bits['context_var'])


class ThisPageInLangNode(template.Node):
    def __init__(self, lang, fallback=None, context_var=None):
        self.context_var = context_var
        self.lang = template.Variable(lang)
        if fallback:
            self.fallback = template.Variable(fallback)
        else:
            self.fallback = None

    def render(self, context):
        try:
            output = context['_url_translator'].get_url(
                self.lang.resolve(context), context
            )
        except (KeyError, NoTranslationError), e:
            output = ''

        if (not output) and self.fallback:
            output = self.fallback.resolve(context)

        if self.context_var:
            context[self.context_var] = output
            return ''
        else:
            return output


@register.filter
@stringfilter
def trans_in_lang(string, lang):
    """
    Translate a string into a specific language (which can be different
    than the set language).

    Usage:

        {{ var|trans_in_lang:"fr" }}

    """
    if check_for_language(lang):
        return translation(lang).ugettext(string)
    return string

########NEW FILE########
__FILENAME__ = translators
from django.core.urlresolvers import NoReverseMatch

from transurlvania.urlresolvers import reverse_for_language


class NoTranslationError(Exception):
    pass


class ViewInfo(object):
    def __init__(self, current_url, view_func, view_args, view_kwargs):
        self.current_url = current_url
        self.view_func = view_func
        self.view_args = view_args
        self.view_kwargs = view_kwargs

    def __unicode__(self):
        return 'URL:%s, handled by %s(*%s, **%s)' % (self.current_url,
            self.view_func, self.view_args, self.view_kwargs)

class BasicScheme(object):
    def get_url(self, lang, view_info, context=None):
        "The basic translation scheme just returns the current URL"
        return view_info.current_url


class ObjectBasedScheme(BasicScheme):
    """
    Translates by finding the specified object in the context dictionary,
    getting that object's translation in teh requested language, and
    returning the object's URL.
    """

    DEFAULT_OBJECT_NAME = 'object'

    def __init__(self, object_name=None):
        self.object_name = object_name or self.DEFAULT_OBJECT_NAME

    def get_url(self, lang, view_info, context=None):
        try:
            return context[self.object_name].get_translation(lang).get_absolute_url()
        except KeyError:
            raise NoTranslationError(u'Could not find object named %s in context.' % self.object_name)
        except AttributeError:
            raise NoTranslationError(u'Unable to get translation of object %s '
                                     u'in language %s' % (context[self.object_name], lang))


class DirectToURLScheme(BasicScheme):
    """
    Translates using a view function (or URL name) and the args and kwargs that
    need to be passed to it. The URL is found by doing a reverse lookup for the
    specified view in the requested language.
    """

    def __init__(self, url_name=None):
        self.url_name = url_name

    def get_url(self, lang, view_info, context=None):
        view_func = self.url_name or view_info.view_func
        try:
            return reverse_for_language(view_func, lang, None,
                view_info.view_args, view_info.view_kwargs)
        except NoReverseMatch:
            raise NoTranslationError('Unable to find URL for %s' % view_func)


class AutodetectScheme(BasicScheme):
    """
    Tries to translate using an "object" entry in the context, or, failing
    that, tries to find the URL for the view function it was given in the
    requested language.
    """
    def __init__(self, object_name=None):
        self.object_translator = ObjectBasedScheme(object_name)
        self.view_translator = DirectToURLScheme()

    def get_url(self, lang, view_info, context=None):
        """
        Tries translating with the object based scheme and falls back to the
        direct-to-URL based scheme if that fails.
        """
        try:
            return self.object_translator.get_url(lang, view_info, context)
        except NoTranslationError:
            try:
                return self.view_translator.get_url(lang, view_info, context)
            except NoTranslationError:
                return super(AutodetectScheme, self).get_url(lang, view_info, context)


class URLTranslator(object):
    def __init__(self, current_url, scheme=None):
        self.scheme = scheme or BasicScheme()
        self.view_info = ViewInfo(current_url, None, None, None)

    def set_view_info(self, view_func, view_args, view_kwargs):
        self.view_info.view_func = view_func
        self.view_info.view_args = view_args
        self.view_info.view_kwargs = view_kwargs

    def __unicode__(self):
        return 'URL Translator for %s. Using scheme: %s.' % (self.view_info,
                                                             self.scheme)

    def get_url(self, lang, context=None):
        return self.scheme.get_url(lang, self.view_info, context)
########NEW FILE########
__FILENAME__ = urlresolvers
import re

from django.conf import settings
from django.conf.urls.defaults import handler404, handler500
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver, get_callable
from django.core.urlresolvers import NoReverseMatch
from django.core.urlresolvers import get_script_prefix
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import iri_to_uri, force_unicode
from django.utils.regex_helper import normalize
from django.utils.translation import get_language
from django.utils.translation.trans_real import translation

import transurlvania.settings


_resolvers = {}
def get_resolver(urlconf, lang):
    if urlconf is None:
        from django.conf import settings
        urlconf = settings.ROOT_URLCONF
    key = (urlconf, lang)
    if key not in _resolvers:
        _resolvers[key] = MultilangRegexURLResolver(r'^/', urlconf)
    return _resolvers[key]


def reverse_for_language(viewname, lang, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    # Based on code in Django 1.1.1 in reverse and RegexURLResolver.reverse 
    # in django.core.urlresolvers.
    args = args or []
    kwargs = kwargs or {}
    if prefix is None:
        prefix = get_script_prefix()
    resolver = get_resolver(urlconf, lang)

    if not isinstance(viewname, basestring):
        view = viewname
    else:
        parts = viewname.split(':')
        parts.reverse()
        view = parts[0]
        path = parts[1:]

        resolved_path = []
        while path:
            ns = path.pop()

            # Lookup the name to see if it could be an app identifier
            try:
                app_list = resolver.app_dict[ns]
                # Yes! Path part matches an app in the current Resolver
                if current_app and current_app in app_list:
                    # If we are reversing for a particular app, use that namespace
                    ns = current_app
                elif ns not in app_list:
                    # The name isn't shared by one of the instances (i.e., the default)
                    # so just pick the first instance as the default.
                    ns = app_list[0]
            except KeyError:
                pass

            try:
                extra, resolver = resolver.namespace_dict[ns]
                resolved_path.append(ns)
                prefix = prefix + extra
            except KeyError, key:
                if resolved_path:
                    raise NoReverseMatch("%s is not a registered namespace inside '%s'" % (key, ':'.join(resolved_path)))
                else:
                    raise NoReverseMatch("%s is not a registered namespace" % key)

    if args and kwargs:
        raise ValueError("Don't mix *args and **kwargs in call to reverse()!")
    try:
        lookup_view = get_callable(view, True)
    except (ImportError, AttributeError), e:
        raise NoReverseMatch("Error importing '%s': %s." % (lookup_view, e))
    if hasattr(resolver, 'get_reverse_dict'):
        possibilities = resolver.get_reverse_dict(lang).getlist(lookup_view)
    else:
        possibilities = resolver.reverse_dict.getlist(lookup_view)
    for possibility, pattern in possibilities:
        for result, params in possibility:
            if args:
                if len(args) != len(params):
                    continue
                unicode_args = [force_unicode(val) for val in args]
                candidate =  result % dict(zip(params, unicode_args))
            else:
                if set(kwargs.keys()) != set(params):
                    continue
                unicode_kwargs = dict([(k, force_unicode(v)) for (k, v) in kwargs.items()])
                candidate = result % unicode_kwargs
            if re.search(u'^%s' % pattern, candidate, re.UNICODE):
                iri = u'%s%s' % (prefix, candidate)
                # If we have a separate domain for lang, put that in the iri
                domain = transurlvania.settings.LANGUAGE_DOMAINS.get(lang, None)
                if domain:
                    iri = u'http://%s%s' % (domain[0], iri)
                return iri_to_uri(iri)
    # lookup_view can be URL label, or dotted path, or callable, Any of
    # these can be passed in at the top, but callables are not friendly in
    # error messages.
    m = getattr(lookup_view, '__module__', None)
    n = getattr(lookup_view, '__name__', None)
    if m is not None and n is not None:
        lookup_view_s = "%s.%s" % (m, n)
    else:
        lookup_view_s = lookup_view
    raise NoReverseMatch("Reverse for '%s' with arguments '%s' and keyword "
            "arguments '%s' not found." % (lookup_view_s, args, kwargs))


class MultilangRegexURLPattern(RegexURLPattern):
    def __init__(self, regex, callback, default_args=None, name=None):
        # Copied from django.core.urlresolvers.RegexURLPattern, with one change:
        # The regex here is stored as a string instead of as a compiled re object.
        # This allows the code to use the gettext system to translate the URL
        # pattern at resolve time.
        self._raw_regex = regex

        if callable(callback):
            self._callback = callback
        else:
            self._callback = None
            self._callback_str = callback
        self.default_args = default_args or {}
        self.name = name
        self._regex_dict = {}

    def get_regex(self, lang=None):
        lang = lang or get_language()
        return self._regex_dict.setdefault(lang, re.compile(translation(lang).ugettext(self._raw_regex), re.UNICODE))
    regex = property(get_regex)


class MultilangRegexURLResolver(RegexURLResolver):
    def __init__(self, regex, urlconf_name, default_kwargs=None, app_name=None, namespace=None):
        # regex is a string representing a regular expression.
        # urlconf_name is a string representing the module containing urlconfs.
        self._raw_regex = regex
        self.urlconf_name = urlconf_name
        if not isinstance(urlconf_name, basestring):
            self._urlconf_module = self.urlconf_name
        self.callback = None
        self.default_kwargs = default_kwargs or {}
        self.namespace = namespace
        self.app_name = app_name
        self._lang_reverse_dicts = {}
        self._namespace_dict = None
        self._app_dict = None
        self._regex_dict = {}

    def get_regex(self, lang=None):
        lang = lang or get_language()
        # Only attempt to get the translation of the regex if the regex string
        # is not empty. The empty string is handled as a special case by
        # Django's gettext. It's where it stores its metadata.
        if self._raw_regex != '':
            regex_in_lang = translation(lang).ugettext(self._raw_regex)
        else:
            regex_in_lang = self._raw_regex
        return self._regex_dict.setdefault(lang, re.compile(regex_in_lang, re.UNICODE))
    regex = property(get_regex)

    def _build_reverse_dict_for_lang(self, lang):
        reverse_dict = MultiValueDict()
        namespaces = {}
        apps = {}
        for pattern in reversed(self.url_patterns):
            if hasattr(pattern, 'get_regex'):
                p_pattern = pattern.get_regex(lang).pattern
            else:
                p_pattern = pattern.regex.pattern
            if p_pattern.startswith('^'):
                p_pattern = p_pattern[1:]
            if isinstance(pattern, RegexURLResolver):
                if pattern.namespace:
                    namespaces[pattern.namespace] = (p_pattern, pattern)
                    if pattern.app_name:
                        apps.setdefault(pattern.app_name, []).append(pattern.namespace)
                else:
                    if hasattr(pattern, 'get_regex'):
                        parent = normalize(pattern.get_regex(lang).pattern)
                    else:
                        parent = normalize(pattern.regex.pattern)
                    if hasattr(pattern, 'get_reverse_dict'):
                        sub_reverse_dict = pattern.get_reverse_dict(lang)
                    else:
                        sub_reverse_dict = pattern.reverse_dict
                    for name in sub_reverse_dict:
                        for matches, pat in sub_reverse_dict.getlist(name):
                            new_matches = []
                            for piece, p_args in parent:
                                new_matches.extend([(piece + suffix, p_args + args) for (suffix, args) in matches])
                            reverse_dict.appendlist(name, (new_matches, p_pattern + pat))
                    for namespace, (prefix, sub_pattern) in pattern.namespace_dict.items():
                        namespaces[namespace] = (p_pattern + prefix, sub_pattern)
                    for app_name, namespace_list in pattern.app_dict.items():
                        apps.setdefault(app_name, []).extend(namespace_list)
            else:
                bits = normalize(p_pattern)
                reverse_dict.appendlist(pattern.callback, (bits, p_pattern))
                reverse_dict.appendlist(pattern.name, (bits, p_pattern))
        self._namespace_dict = namespaces
        self._app_dict = apps
        return reverse_dict

    def get_reverse_dict(self, lang=None):
        if lang is None:
            lang = get_language()
        if lang not in self._lang_reverse_dicts:
            self._lang_reverse_dicts[lang] = self._build_reverse_dict_for_lang(lang)
        return self._lang_reverse_dicts[lang]
    reverse_dict = property(get_reverse_dict)


class LangSelectionRegexURLResolver(MultilangRegexURLResolver):
    def __init__(self, urlconf_name, default_kwargs=None, app_name=None, namespace=None):
        # urlconf_name is a string representing the module containing urlconfs.
        self.urlconf_name = urlconf_name
        if not isinstance(urlconf_name, basestring):
            self._urlconf_module = self.urlconf_name
        self.callback = None
        self.default_kwargs = default_kwargs or {}
        self.namespace = namespace
        self.app_name = app_name
        self._lang_reverse_dicts = {}
        self._namespace_dict = None
        self._app_dict = None
        self._regex_dict = {}

    def get_regex(self, lang=None):
        lang = lang or get_language()
        return re.compile('^%s/' % lang)
    regex = property(get_regex)


class PocketURLModule(object):
    handler404 = handler404
    handler500 = handler500

    def __init__(self, pattern_list):
        self.urlpatterns = pattern_list


########NEW FILE########
__FILENAME__ = utils
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import get_language

from transurlvania.settings import LANGUAGE_DOMAINS


def complete_url(url, lang=None):
    """
    Takes a url (or path) and returns a full url including the appropriate
    domain name (based on the LANGUAGE_DOMAINS setting).
    """
    if not url.startswith('http://'):
        lang = lang or get_language()
        domain = LANGUAGE_DOMAINS.get(lang)
        if domain:
            url = u'http://%s%s' % (domain[0], url)
        else:
            raise ImproperlyConfigured(
                'Not domain specified for language code %s' % lang
            )
    return url

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.utils.translation import get_language_from_request


def detect_language_and_redirect(request):
    return HttpResponseRedirect(
        '/%s/' % get_language_from_request(request)
    )

########NEW FILE########
