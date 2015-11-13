__FILENAME__ = middleware
from django_mobile import get_flavour, _set_request_header
from django.utils.cache import patch_vary_headers


class CacheFlavourMiddleware(object):
    def process_request(self, request):
        _set_request_header(request, get_flavour(request))

    def process_response(self, request, response):
        patch_vary_headers(response, ['X-Flavour'])
        return response

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
from django.conf import settings as django_settings

CACHE_LOADER_NAME = 'django_mobile.loader.CachedLoader'
DJANGO_MOBILE_LOADER = 'django_mobile.loader.Loader'


class SettingsProxy(object):
    def __init__(self, settings, defaults):
        self.settings = settings
        self.defaults = defaults

    def __getattr__(self, attr):
        try:
            return getattr(self.settings, attr)
        except AttributeError:
            try:
                return getattr(self.defaults, attr)
            except AttributeError:
                raise AttributeError(u'settings object has no attribute "%s"' % attr)


class defaults(object):
    FLAVOURS = (u'full', u'mobile',)
    DEFAULT_MOBILE_FLAVOUR = u'mobile'
    FLAVOURS_TEMPLATE_PREFIX = u''
    FLAVOURS_GET_PARAMETER = u'flavour'
    FLAVOURS_STORAGE_BACKEND = u'cookie'
    FLAVOURS_COOKIE_KEY = u'flavour'
    FLAVOURS_COOKIE_HTTPONLY = False
    FLAVOURS_SESSION_KEY = u'flavour'
    FLAVOURS_TEMPLATE_LOADERS = []
    for loader in django_settings.TEMPLATE_LOADERS:
        if isinstance(loader, (tuple, list)) and loader[0] == CACHE_LOADER_NAME:
            for cached_loader in loader[1]:
                if cached_loader != DJANGO_MOBILE_LOADER:
                    FLAVOURS_TEMPLATE_LOADERS.append(cached_loader)
        elif loader != DJANGO_MOBILE_LOADER:
            FLAVOURS_TEMPLATE_LOADERS.append(loader)
    FLAVOURS_TEMPLATE_LOADERS = tuple(FLAVOURS_TEMPLATE_LOADERS)

settings = SettingsProxy(django_settings, defaults)

########NEW FILE########
__FILENAME__ = context_processors
from django_mobile import get_flavour
from django_mobile.conf import settings


def flavour(request):
    return {
        'flavour': get_flavour(),
    }


def is_mobile(request):
    return {
        'is_mobile': get_flavour() == settings.DEFAULT_MOBILE_FLAVOUR,
    }

########NEW FILE########
__FILENAME__ = loader
import hashlib
from django.template import TemplateDoesNotExist
from django.template.loader import find_template_loader, BaseLoader
from django.template.loader import get_template_from_string
from django.template.loaders.cached import Loader as DjangoCachedLoader
from django_mobile import get_flavour
from django_mobile.conf import settings


class Loader(BaseLoader):
    is_usable = True

    def __init__(self, *args, **kwargs):
        loaders = []
        for loader_name in settings.FLAVOURS_TEMPLATE_LOADERS:
            loader = find_template_loader(loader_name)
            if loader is not None:
                loaders.append(loader)
        self.template_source_loaders = tuple(loaders)
        super(BaseLoader, self).__init__(*args, **kwargs)

    def get_template_sources(self, template_name, template_dirs=None):
        template_name = self.prepare_template_name(template_name)
        for loader in self.template_source_loaders:
            if hasattr(loader, 'get_template_sources'):
                try:
                    for result in  loader.get_template_sources(
                                        template_name,
                                        template_dirs):
                        yield result
                except UnicodeDecodeError:
                    # The template dir name was a bytestring that wasn't valid UTF-8.
                    raise
                except ValueError:
                    # The joined path was located outside of this particular
                    # template_dir (it might be inside another one, so this isn't
                    # fatal).
                    pass

    def prepare_template_name(self, template_name):
        template_name = u'%s/%s' % (get_flavour(), template_name)
        if settings.FLAVOURS_TEMPLATE_PREFIX:
            template_name = settings.FLAVOURS_TEMPLATE_PREFIX + template_name
        return template_name

    def load_template(self, template_name, template_dirs=None):
        template_name = self.prepare_template_name(template_name)
        for loader in self.template_source_loaders:
            try:
                return loader(template_name, template_dirs)
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist("Tried %s" % template_name)

    def load_template_source(self, template_name, template_dirs=None):
        template_name = self.prepare_template_name(template_name)
        for loader in self.template_source_loaders:
            if hasattr(loader, 'load_template_source'):
                try:
                    return loader.load_template_source(
                        template_name,
                        template_dirs)
                except TemplateDoesNotExist:
                    pass
        raise TemplateDoesNotExist("Tried %s" % template_name)


class CachedLoader(DjangoCachedLoader):
    is_usable = True

    def load_template(self, template_name, template_dirs=None):
        key = "{0}:{1}".format(get_flavour(), template_name)
        if template_dirs:
            # If template directories were specified, use a hash to differentiate
            key = '-'.join([
                template_name,
                hashlib.sha1('|'.join(template_dirs)).hexdigest()])

        if key not in self.template_cache:
            template, origin = self.find_template(template_name, template_dirs)
            if not hasattr(template, 'render'):
                try:
                    template = get_template_from_string(template, origin, template_name)
                except TemplateDoesNotExist:
                    # If compiling the template we found raises TemplateDoesNotExist,
                    # back off to returning the source and display name for
                    # the template we were asked to load. This allows for
                    # correct identification (later) of the actual template
                    # that does not exist.
                    return template, origin
            self.template_cache[key] = template
        return self.template_cache[key], None

########NEW FILE########
__FILENAME__ = middleware
import re
from django_mobile import flavour_storage
from django_mobile import set_flavour, _init_flavour
from django_mobile.conf import settings


class SetFlavourMiddleware(object):
    def process_request(self, request):
        _init_flavour(request)

        if settings.FLAVOURS_GET_PARAMETER in request.GET:
            flavour = request.GET[settings.FLAVOURS_GET_PARAMETER]
            if flavour in settings.FLAVOURS:
                set_flavour(flavour, request, permanent=True)

    def process_response(self, request, response):
        flavour_storage.save(request, response)
        return response


class MobileDetectionMiddleware(object):
    user_agents_test_match = (
        "w3c ", "acs-", "alav", "alca", "amoi", "audi",
        "avan", "benq", "bird", "blac", "blaz", "brew",
        "cell", "cldc", "cmd-", "dang", "doco", "eric",
        "hipt", "inno", "ipaq", "java", "jigs", "kddi",
        "keji", "leno", "lg-c", "lg-d", "lg-g", "lge-",
        "maui", "maxo", "midp", "mits", "mmef", "mobi",
        "mot-", "moto", "mwbp", "nec-", "newt", "noki",
        "xda",  "palm", "pana", "pant", "phil", "play",
        "port", "prox", "qwap", "sage", "sams", "sany",
        "sch-", "sec-", "send", "seri", "sgh-", "shar",
        "sie-", "siem", "smal", "smar", "sony", "sph-",
        "symb", "t-mo", "teli", "tim-", "tosh", "tsm-",
        "upg1", "upsi", "vk-v", "voda", "wap-", "wapa",
        "wapi", "wapp", "wapr", "webc", "winw", "xda-",)
    user_agents_test_search = u"(?:%s)" % u'|'.join((
        'up.browser', 'up.link', 'mmp', 'symbian', 'smartphone', 'midp',
        'wap', 'phone', 'windows ce', 'pda', 'mobile', 'mini', 'palm',
        'netfront', 'opera mobi',
    ))
    user_agents_exception_search = u"(?:%s)" % u'|'.join((
        'ipad',
    ))
    http_accept_regex = re.compile("application/vnd\.wap\.xhtml\+xml", re.IGNORECASE)

    def __init__(self):
        user_agents_test_match = r'^(?:%s)' % '|'.join(self.user_agents_test_match)
        self.user_agents_test_match_regex = re.compile(user_agents_test_match, re.IGNORECASE)
        self.user_agents_test_search_regex = re.compile(self.user_agents_test_search, re.IGNORECASE)
        self.user_agents_exception_search_regex = re.compile(self.user_agents_exception_search, re.IGNORECASE)

    def process_request(self, request):
        is_mobile = False

        if request.META.has_key('HTTP_USER_AGENT'):
            user_agent = request.META['HTTP_USER_AGENT']

            # Test common mobile values.
            if self.user_agents_test_search_regex.search(user_agent) and \
                not self.user_agents_exception_search_regex.search(user_agent):
                is_mobile = True
            else:
                # Nokia like test for WAP browsers.
                # http://www.developershome.com/wap/xhtmlmp/xhtml_mp_tutorial.asp?page=mimeTypesFileExtension

                if request.META.has_key('HTTP_ACCEPT'):
                    http_accept = request.META['HTTP_ACCEPT']
                    if self.http_accept_regex.search(http_accept):
                        is_mobile = True

            if not is_mobile:
                # Now we test the user_agent from a big list.
                if self.user_agents_test_match_regex.match(user_agent):
                    is_mobile = True

        if is_mobile:
            set_flavour(settings.DEFAULT_MOBILE_FLAVOUR, request)
        else:
            set_flavour(settings.FLAVOURS[0], request)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = cache_settings
from settings import *


MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
) + MIDDLEWARE_CLASSES + (
    'django_mobile.cache.middleware.CacheFlavourMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'django_mobile_tests.settings'
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, parent)


if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    execute_from_command_line()


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'django_mobile_tests.settings'
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, parent)


def runtests(*args):
    from django.core import management

    if not args:
        args = [
            'django_mobile',
            'django_mobile_tests',
        ]
    args = ['runtests.py', 'test'] + list(args)
    management.execute_from_command_line(args)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = settings
# Django settings for testsite project.
import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'db.sqlite'),
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'django_mobile_tests', 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '<REPLACE:SECRET_KEY>'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    ('django_mobile.loader.CachedLoader', (
        'django_mobile.loader.Loader',
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django_mobile.middleware.MobileDetectionMiddleware',
    'django_mobile.middleware.SetFlavourMiddleware',
)

ROOT_URLCONF = 'django_mobile_tests.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'django_mobile_tests', 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',

    'django_mobile',
    'django_mobile_tests',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django_mobile.context_processors.flavour",
    "django_mobile.context_processors.is_mobile",
)

try:
    from local_settings import *
except ImportError:
    pass


########NEW FILE########
__FILENAME__ = tests
import threading
from django.contrib.sessions.models import Session
from django.template import RequestContext, TemplateDoesNotExist
from django.test import Client, TestCase
from mock import MagicMock, Mock, patch
from django_mobile import get_flavour, set_flavour
from django_mobile.conf import settings
from django_mobile.middleware import MobileDetectionMiddleware, \
    SetFlavourMiddleware


def _reset():
    '''
    Reset the thread local.
    '''
    import django_mobile
    del django_mobile._local
    django_mobile._local = threading.local()


class BaseTestCase(TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()


class BasicFunctionTests(BaseTestCase):
    def test_set_flavour(self):
        set_flavour('full')
        self.assertEqual(get_flavour(), 'full')
        set_flavour('mobile')
        self.assertEqual(get_flavour(), 'mobile')
        self.assertRaises(ValueError, set_flavour, 'spam')

    def test_set_flavour_with_cookie_backend(self):
        original_FLAVOURS_STORAGE_BACKEND = settings.FLAVOURS_STORAGE_BACKEND
        try:
            settings.FLAVOURS_STORAGE_BACKEND = 'cookie'
            response = self.client.get('/')
            self.assertFalse(settings.FLAVOURS_COOKIE_KEY in response.cookies)
            response = self.client.get('/', {
                settings.FLAVOURS_GET_PARAMETER: 'mobile',
            })
            self.assertTrue(settings.FLAVOURS_COOKIE_KEY in response.cookies)
            self.assertTrue(response.cookies[settings.FLAVOURS_COOKIE_KEY], u'mobile')
            self.assertContains(response, 'Mobile!')
        finally:
            settings.FLAVOURS_STORAGE_BACKEND = original_FLAVOURS_STORAGE_BACKEND

    def test_set_flavour_with_session_backend(self):
        original_FLAVOURS_STORAGE_BACKEND = settings.FLAVOURS_STORAGE_BACKEND
        try:
            settings.FLAVOURS_STORAGE_BACKEND = 'session'
            request = Mock()
            request.session = {}
            set_flavour('mobile', request=request)
            self.assertEqual(request.session, {})
            set_flavour('mobile', request=request, permanent=True)
            self.assertEqual(request.session, {
                settings.FLAVOURS_SESSION_KEY: u'mobile'
            })
            self.assertEqual(get_flavour(request), 'mobile')

            response = self.client.get('/')
            self.assertFalse('sessionid' in response.cookies)
            response = self.client.get('/', {
                settings.FLAVOURS_GET_PARAMETER: 'mobile',
            })
            self.assertTrue('sessionid' in response.cookies)
            sessionid = response.cookies['sessionid'].value
            session = Session.objects.get(session_key=sessionid)
            session_data = session.get_decoded()
            self.assertTrue(settings.FLAVOURS_SESSION_KEY in session_data)
            self.assertEqual(session_data[settings.FLAVOURS_SESSION_KEY], 'mobile')
        finally:
            settings.FLAVOURS_STORAGE_BACKEND = original_FLAVOURS_STORAGE_BACKEND


class TemplateLoaderTests(BaseTestCase):
    def test_load_template_on_filesystem(self):
        from django.template.loaders import app_directories, filesystem

        @patch.object(app_directories.Loader, 'load_template')
        @patch.object(filesystem.Loader, 'load_template')
        def testing(filesystem_loader, app_directories_loader):
            filesystem_loader.side_effect = TemplateDoesNotExist()
            app_directories_loader.side_effect = TemplateDoesNotExist()

            from django_mobile.loader import Loader
            loader = Loader()

            set_flavour('mobile')
            try:
                loader.load_template('base.html', template_dirs=None)
            except TemplateDoesNotExist:
                pass
            self.assertEqual(filesystem_loader.call_args[0][0], 'mobile/base.html')
            self.assertEqual(app_directories_loader.call_args[0][0], 'mobile/base.html')

            set_flavour('full')
            try:
                loader.load_template('base.html', template_dirs=None)
            except TemplateDoesNotExist:
                pass
            self.assertEqual(filesystem_loader.call_args[0][0], 'full/base.html')
            self.assertEqual(app_directories_loader.call_args[0][0], 'full/base.html')

        testing()

    def test_load_template_source_on_filesystem(self):
        from django.template.loaders import app_directories, filesystem

        @patch.object(app_directories.Loader, 'load_template_source')
        @patch.object(filesystem.Loader, 'load_template_source')
        def testing(filesystem_loader, app_directories_loader):
            filesystem_loader.side_effect = TemplateDoesNotExist()
            app_directories_loader.side_effect = TemplateDoesNotExist()

            from django_mobile.loader import Loader
            loader = Loader()

            set_flavour('mobile')
            try:
                loader.load_template_source('base.html', template_dirs=None)
            except TemplateDoesNotExist:
                pass
            self.assertEqual(filesystem_loader.call_args[0][0], 'mobile/base.html')
            self.assertEqual(app_directories_loader.call_args[0][0], 'mobile/base.html')

            set_flavour('full')
            try:
                loader.load_template_source('base.html', template_dirs=None)
            except TemplateDoesNotExist:
                pass
            self.assertEqual(filesystem_loader.call_args[0][0], 'full/base.html')
            self.assertEqual(app_directories_loader.call_args[0][0], 'full/base.html')

        testing()

    def test_functional(self):
        from django.template.loader import render_to_string
        set_flavour('full')
        result = render_to_string('index.html')
        result = result.strip()
        self.assertEqual(result, 'Hello .')
        # simulate RequestContext
        result = render_to_string('index.html', context_instance=RequestContext(Mock()))
        result = result.strip()
        self.assertEqual(result, 'Hello full.')
        set_flavour('mobile')
        result = render_to_string('index.html')
        result = result.strip()
        self.assertEqual(result, 'Mobile!')

    def test_loading_unexisting_template(self):
        from django.template.loader import render_to_string
        try:
            render_to_string('not_existent.html')
        except TemplateDoesNotExist, e:
            self.assertEqual(e.args, ('not_existent.html',))
        else:
            self.fail('TemplateDoesNotExist was not raised.')


class MobileDetectionMiddlewareTests(BaseTestCase):
    @patch('django_mobile.middleware.set_flavour')
    def test_mobile_browser_agent(self, set_flavour):
        request = Mock()
        request.META = {
            'HTTP_USER_AGENT': 'My Mobile Browser',
        }
        middleware = MobileDetectionMiddleware()
        middleware.process_request(request)
        self.assertEqual(set_flavour.call_args, (('mobile', request), {}))

    @patch('django_mobile.middleware.set_flavour')
    def test_desktop_browser_agent(self, set_flavour):
        request = Mock()
        request.META = {
            'HTTP_USER_AGENT': 'My Desktop Browser',
        }
        middleware = MobileDetectionMiddleware()
        middleware.process_request(request)
        self.assertEqual(set_flavour.call_args, (('full', request), {}))


class SetFlavourMiddlewareTests(BaseTestCase):
    def test_set_default_flavour(self):
        request = Mock()
        request.META = MagicMock()
        request.GET = {}
        middleware = SetFlavourMiddleware()
        middleware.process_request(request)
        # default flavour is set
        self.assertEqual(get_flavour(), 'full')

    @patch('django_mobile.middleware.set_flavour')
    def test_set_flavour_through_get_parameter(self, set_flavour):
        request = Mock()
        request.META = MagicMock()
        request.GET = {'flavour': 'mobile'}
        middleware = SetFlavourMiddleware()
        middleware.process_request(request)
        self.assertEqual(set_flavour.call_args,
            (('mobile', request), {'permanent': True}))


class RealAgentNameTests(BaseTestCase):
    def assertFullFlavour(self, agent):
        client = Client(HTTP_USER_AGENT=agent)
        response = client.get('/')
        if response.content.strip() != 'Hello full.':
            self.fail(u'Agent is matched as mobile: %s' % agent)

    def assertMobileFlavour(self, agent):
        client = Client(HTTP_USER_AGENT=agent)
        response = client.get('/')
        if response.content.strip() != 'Mobile!':
            self.fail(u'Agent is not matched as mobile: %s' % agent)

    def test_ipad(self):
        self.assertFullFlavour(u'Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B334b Safari/531.21.10')

    def test_iphone(self):
        self.assertMobileFlavour(u'Mozilla/5.0 (iPhone; U; CPU like Mac OS X; en) AppleWebKit/420+ (KHTML, like Gecko) Version/3.0 Mobile/1A543a Safari/419.3')

    def test_motorola_xoom(self):
        self.assertFullFlavour(u'Mozilla/5.0 (Linux; U; Android 3.0; en-us; Xoom Build/HRI39) AppleWebKit/534.13 (KHTML, like Gecko) Version/4.0 Safari/534.13')

    def test_opera_mobile_on_android(self):
        '''
        Regression test of issue #9
        '''
        self.assertMobileFlavour(u'Opera/9.80 (Android 2.3.3; Linux; Opera Mobi/ADR-1111101157; U; en) Presto/2.9.201 Version/11.50')


class RegressionTests(BaseTestCase):
    def setUp(self):
        self.desktop = Client()
        # wap triggers mobile behaviour
        self.mobile = Client(HTTP_USER_AGENT='wap')

    def test_multiple_browser_access(self):
        '''
        Regression test of issue #2
        '''
        response = self.desktop.get('/')
        self.assertEqual(response.content.strip(), 'Hello full.')

        response = self.mobile.get('/')
        self.assertEqual(response.content.strip(), 'Mobile!')

        response = self.desktop.get('/')
        self.assertEqual(response.content.strip(), 'Hello full.')

        response = self.mobile.get('/')
        self.assertEqual(response.content.strip(), 'Mobile!')

    def test_cache_page_decorator(self):
        response = self.mobile.get('/cached/')
        self.assertEqual(response.content.strip(), 'Mobile!')

        response = self.desktop.get('/cached/')
        self.assertEqual(response.content.strip(), 'Hello full.')

        response = self.mobile.get('/cached/')
        self.assertEqual(response.content.strip(), 'Mobile!')

        response = self.desktop.get('/cached/')
        self.assertEqual(response.content.strip(), 'Hello full.')

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls.defaults import *
except ImportError:
    from django.conf.urls import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django_mobile.cache import cache_page


def index(request):
    return render_to_response('index.html', {
    }, context_instance=RequestContext(request))


urlpatterns = patterns('',
    url(r'^$', index),
    url(r'^cached/$', cache_page(60*10)(index)),
)

########NEW FILE########
