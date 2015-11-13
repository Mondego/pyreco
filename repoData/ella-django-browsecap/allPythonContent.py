__FILENAME__ = browser
from ConfigParser import SafeConfigParser as ConfigParser
import re
import os

from django.core.cache import cache
from django.conf import settings

CACHE_KEY = 'browsecap'
CACHE_TIMEOUT = 60*60*2 # 2 hours
DEFAULT_BC_PATH = os.path.abspath(os.path.dirname(__file__ or os.getcwd()))

class MobileBrowserParser(object):
    def __new__(cls, *args, **kwargs):
        # Only create one instance of this clas
        if "instance" not in cls.__dict__:
            cls.instance = object.__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self):
        self.mobile_cache = {}
        self.crawler_cache = {}
        self.parse()

    def parse(self):
        # try egtting the parsed definitions from cache
        data = cache.get(CACHE_KEY)
        if data:
            self.mobile_browsers = map(re.compile, data['mobile_browsers'])
            self.crawlers = map(re.compile, data['crawlers'])
            return

        # parse browscap.ini
        cfg = ConfigParser()
        files = ("browscap.ini", "bupdate.ini")
        base_path = getattr(settings, 'BROWSCAP_DIR', DEFAULT_BC_PATH)
        read_ok = cfg.read([os.path.join(base_path, name) for name in files])
        if len(read_ok) == 0:
            raise IOError, "Could not read browscap.ini, " + \
                  "please get it from http://www.GaryKeith.com"

        browsers = {}
        parents = set()

        # go through all the browsers and record their parents
        for name in cfg.sections():
            sec = dict(cfg.items(name))
            p = sec.get("parent")
            if p:
                parents.add(p)
            browsers[name] = sec

        self.mobile_browsers = []
        self.crawlers = []
        for name, conf in browsers.items():
            # only process those that are not abstract parents
            if name in parents:
                continue

            p = conf.get('parent')
            if p:
                # update config based on parent's settings
                parent = browsers[p]
                conf.update(parent)

            # we only care for mobiles and crawlers
            if conf.get('ismobiledevice', 'false') == 'true' or conf.get('crawler', 'false') == 'true':
                qname = re.escape(name)
                qname = qname.replace("\\?", ".").replace("\\*", ".*?")
                qname = "^%s$" % qname

            # register the user agent
            if conf.get('ismobiledevice', 'false') == 'true':
                self.mobile_browsers.append(qname)

            if conf.get('crawler', 'false') == 'true':
                self.crawlers.append(qname)

        # store in cache to speed up next load
        cache.set(CACHE_KEY, {'mobile_browsers': self.mobile_browsers, 'crawlers': self.crawlers}, CACHE_TIMEOUT)

        # compile regexps
        self.mobile_browsers = map(re.compile, self.mobile_browsers)
        self.crawlers = map(re.compile, self.crawlers)

    def find_in_list(self, useragent, agent_list, cache):
        'Check useragent against agent_list of regexps.'
        try:
            return cache[useragent]
        except KeyError, e:
            pass

        for sec_pat in agent_list:
            if sec_pat.match(useragent):
                out = True
                break
        else:
            out = False
        cache[useragent] = out
        return out

    def is_mobile(self, useragent):
        'Returns True if the given useragent is a known mobile browser, False otherwise.'
        return self.find_in_list(useragent, self.mobile_browsers, self.mobile_cache)

    def is_crawler(self, useragent):
        'Returns True if the given useragent is a known crawler, False otherwise.'
        return self.find_in_list(useragent, self.crawlers, self.crawler_cache)


# instantiate the parser
browsers = MobileBrowserParser()

# provide access to methods as functions for convenience
is_mobile = browsers.is_mobile
is_crawler = browsers.is_crawler


def update():
    'Download new version of browsecap.ini'
    import urllib
    urllib.urlretrieve("http://browsers.garykeith.com/stream.asp?BrowsCapINI",
                       "browscap.ini")



########NEW FILE########
__FILENAME__ = middleware
import time

from django.http import HttpResponseRedirect
from django.utils.http import cookie_date
from django.conf import settings

from browsecap.browser import is_mobile

# default cookie expire time is one month
DEFAULT_COOKIE_MAX_AGE = 3600*24*31

class MobileRedirectMiddleware(object):
    def process_request(self, request):
        if not getattr(settings, 'MOBILE_DOMAIN', False):
            return 

        # test for mobile browser
        if (
                # check for override cookie, do not check if present
                request.COOKIES.get('ismobile', '0') == '1' or (
                    # browser info present
                    'HTTP_USER_AGENT' in request.META
                    and 
                    # desktop browser override not set
                    request.COOKIES.get('isbrowser', '0') != '1' 
                    and 
                    # check browser type
                    is_mobile(request.META['HTTP_USER_AGENT'])
                )
            ):
            redirect = settings.MOBILE_DOMAIN
            if getattr(settings, 'MOBILE_REDIRECT_PRESERVE_URL', False):
                redirect = redirect.rstrip('/') + request.path_info
            # redirect to mobile domain
            response = HttpResponseRedirect(redirect)

            # set cookie to identify the browser as mobile
            max_age = getattr(settings, 'MOBILE_COOKIE_MAX_AGE', DEFAULT_COOKIE_MAX_AGE)
            expires_time = time.time() + max_age
            expires = cookie_date(expires_time)
            response.set_cookie('ismobile', '1', domain=settings.SESSION_COOKIE_DOMAIN, max_age=max_age, expires=expires)
            return response


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
from os.path import join, pardir, abspath, dirname, split
import sys

from django.core.management import execute_from_command_line


# fix PYTHONPATH and DJANGO_SETTINGS for us
# django settings module
DJANGO_SETTINGS_MODULE = '%s.%s' % (split(abspath(dirname(__file__)))[1], 'settings')
# pythonpath dirs
PYTHONPATH = [
    abspath(join( dirname(__file__), pardir, pardir)),
    abspath(join( dirname(__file__), pardir)),
]

# inject few paths to pythonpath
for p in PYTHONPATH:
    if p not in sys.path:
        sys.path.insert(0, p)

# django needs this env variable
os.environ['DJANGO_SETTINGS_MODULE'] = DJANGO_SETTINGS_MODULE


if __name__ == "__main__":
    execute_from_command_line()


########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python

'''
simple shortcut for running nosetests via python
replacement for *.bat or *.sh wrappers
'''

import os
import sys
from os.path import join, pardir, abspath, dirname, split

import nose


# django settings module
DJANGO_SETTINGS_MODULE = '%s.%s' % (split(abspath(dirname(__file__)))[1], 'settings')
# pythonpath dirs
PYTHONPATH = [
    abspath(join( dirname(__file__), pardir, pardir)),
    abspath(join( dirname(__file__), pardir)),
]


# inject few paths to pythonpath
for p in PYTHONPATH:
    if p not in sys.path:
        sys.path.insert(0, p)

# django needs this env variable
os.environ['DJANGO_SETTINGS_MODULE'] = DJANGO_SETTINGS_MODULE


# TODO: ugly hack to inject django plugin to nose.run
#
#
for i in ['--with-django',]:
    if i not in sys.argv:
        sys.argv.insert(1, i)


nose.run_exit(
    defaultTest=dirname(__file__),
)


########NEW FILE########
__FILENAME__ = base
from os.path import dirname, join, normpath, pardir

FILE_ROOT = normpath(join(dirname(__file__), pardir))

USE_I18N = True

MEDIA_ROOT = join(FILE_ROOT, 'static')

MEDIA_URL = '/static'

ADMIN_MEDIA_PREFIX = '/admin_media/'


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'unit_project.template_loader.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'browsecap.sample.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    join(FILE_ROOT, 'templates'),

)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.media',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.redirects',
    'django.contrib.admin',
)

DEFAULT_PAGE_ID = 1

VERSION = 1



########NEW FILE########
__FILENAME__ = config
from tempfile import gettempdir
from os.path import join

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS


DEBUG = True
TEMPLATE_DEBUG = DEBUG
DISABLE_CACHE_TEMPLATE = DEBUG


DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = join(gettempdir(), 'browsecap_unit_project.db')
TEST_DATABASE_NAME =join(gettempdir(), 'test_unit_project.db')
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''


TIME_ZONE = 'Europe/Prague'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# Make this unique, and don't share it with anybody.
SECRET_KEY = '88b-01f^x4lh$-s5-hdccnicekg07)niir2g6)93!0#k(=mfv$'

# TODO: Fix logging
# init logger
#LOGGING_CONFIG_FILE = join(dirname(testbed.__file__), 'settings', 'logger.ini')
#if isinstance(LOGGING_CONFIG_FILE, basestring) and isfile(LOGGING_CONFIG_FILE):
#    logging.config.fileConfig(LOGGING_CONFIG_FILE)

# we want to reset whole cache in test
# until we do that, don't use cache
CACHE_BACKEND = 'dummy://'



########NEW FILE########
__FILENAME__ = local_example
"""
Rename to local.py and set variables from config.py that
You want to override.
"""

########NEW FILE########
__FILENAME__ = test_browser_detection
from djangosanetesting import UnitTestCase

from browsecap.browser import is_mobile, is_crawler

class TestIsMobileDetection(UnitTestCase):
    mobile = [
            'Opera/9.60 (J2ME/MIDP; Opera Mini/4.2.13337/504; U; cs) Presto/2.2.0',
            'BlackBerry9000/4.6.0.126 Profile/MIDP-2.0 Configuration/CLDC-1.1 VendorID/170',
            'Mozilla/5.0 (PLAYSTATION 3; 1.00)',
            'Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; cs-cz) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16',
            'Mozilla/5.0 (SymbianOS/9.2; U; Series60/3.1 NokiaN95/31.0.017; Profile/MIDP-2.0 Configuration/CLDC-1.1 ) AppleWebKit/413 (KHTML, like Gecko) Safari/413',
            'Mozilla/5.0 (SymbianOS/9.1; U; en-us) AppleWebKit/413 (KHTML, like Gecko) Safari/413',
        ]
    desktop = [
            'Windows-RSS-Platform/2.0 (MSIE 8.0; Windows NT 5.1)',
            'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; GTB6; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
            'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
            'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; GTB6; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
            'Mozilla/4.0 (compatible; MSIE 5.5; Windows 98)',
            'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.19) Gecko/20081202 Iceweasel/2.0.0.19 (Debian-2.0.0.19-0etch1)',
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; cs; rv:1.9.0.11) Gecko/2009060215 (CK-Stahuj.cz) Firefox/3.0.11 (.NET CLR 2.0.50727)',
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_4_11; cs-cz) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/(null) Safari/525.27.1',
            'Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.4; cs; rv:1.9.0.11) Gecko/2009060214 Firefox/3.0.11',
            'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.4.4',
            'Opera/9.64 (Windows NT 5.1; U; cs) Presto/2.1.1',
            'Opera/9.52 (X11; Linux i686; U; en)',
            'Wget/1.10.2',

        ]
    def test_returns_false_for_empty_user_agent(self):
        self.assert_false(is_mobile(''))

    def test_returns_false_for_unknown_browser(self):
        self.assert_false(is_mobile('Unknown'))

    def test_identify_known_desktop_browsers(self):
        fails = []
        for m in self.desktop:
            if is_mobile(m):
                fails.append(m)
        self.assert_equals([], fails)

    def test_identify_known_mobile_browsers(self):
        fails = []
        for m in self.mobile:
            if not is_mobile(m):
                fails.append(m)
        self.assert_equals([], fails)

class TestIsCrawlerDetection(UnitTestCase):
    crawler = [
            'Googlebot-Image/1.0 ( http://www.googlebot.com/bot.html)',
            'Mozilla/5.0 (compatible; Yahoo! Slurp/3.0; http://help.yahoo.com/help/us/ysearch/slurp)',
            'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'SeznamBot/2.0 (+http://fulltext.sblog.cz/robot/)',
            'SeznamBot/1.0 (+http://fulltext.seznam.cz/) ',
            'msnbot/1.1 (+http://search.msn.com/msnbot.htm)',
            'Baiduspider+(+http://www.baidu.com/search/spider_jp.html) ',
        ]
    
    desktop = [
            'Windows-RSS-Platform/2.0 (MSIE 8.0; Windows NT 5.1)',
            'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; GTB6; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
            'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
            'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; GTB6; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
            'Mozilla/4.0 (compatible; MSIE 5.5; Windows 98)',
            'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.19) Gecko/20081202 Iceweasel/2.0.0.19 (Debian-2.0.0.19-0etch1)',
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; cs; rv:1.9.0.11) Gecko/2009060215 (CK-Stahuj.cz) Firefox/3.0.11 (.NET CLR 2.0.50727)',
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_4_11; cs-cz) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/(null) Safari/525.27.1',
            'Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.4; cs; rv:1.9.0.11) Gecko/2009060214 Firefox/3.0.11',
            'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.4.4',
            'Opera/9.64 (Windows NT 5.1; U; cs) Presto/2.1.1',
            'Opera/9.52 (X11; Linux i686; U; en)',
        ]
    def test_returns_false_for_empty_user_agent(self):
        self.assert_false(is_crawler(''))

    def test_returns_false_for_unknown_browser(self):
        self.assert_false(is_crawler('Unknown'))

    def test_identify_known_desktop_browsers(self):
        fails = []
        for m in self.desktop:
            if is_crawler(m):
                fails.append(m)
        self.assert_equals([], fails)
    
    def test_identify_known_crawler_browsers(self):
        fails = []
        for m in self.crawler:
            if not is_crawler(m):
                fails.append(m)
        self.assert_equals([], fails)
########NEW FILE########
__FILENAME__ = test_middleware
from djangosanetesting import UnitTestCase

from django.http import HttpRequest, HttpResponseRedirect
from django.conf import settings

from browsecap.middleware import MobileRedirectMiddleware

def build_request(user_agent='', cookies={}):
    """ 
    Returns request object with useful attributes
    """
    request = HttpRequest()
    # Session and cookies
    request.session = {}
    request.COOKIES = cookies
    request.META['HTTP_USER_AGENT'] = user_agent
    return request

class TestMobileRedirectMiddleware(UnitTestCase):
    def setUp(self):
        super(TestMobileRedirectMiddleware, self).setUp()
        settings.MOBILE_DOMAIN = 'http://mobile.example.com/'
        self.middleware = MobileRedirectMiddleware()

    def tearDown(self):
        super(TestMobileRedirectMiddleware, self).tearDown()
        if hasattr(settings, 'MOBILE_REDIRECT_PRESERVE_URL'):
            del settings.MOBILE_REDIRECT_PRESERVE_URL

    def test_does_nothing_if_mobile_domain_not_set(self):
        settings.MOBILE_DOMAIN = None
        response = self.middleware.process_request(build_request('Mozilla/5.0 (PLAYSTATION 3; 1.00)'))
        self.assert_equals(None, response)

    def test_does_nothing_for_desktop_browser(self):
        self.assert_equals(None, self.middleware.process_request(build_request()))

    def test_does_nothing_if_isbrowser_cookie_set(self):
        response = self.middleware.process_request(build_request('Mozilla/5.0 (PLAYSTATION 3; 1.00)', {'isbrowser': '1'}))
        self.assert_equals(None, response)

    def test_sets_cookie_for_mobile_browser(self):
        response = self.middleware.process_request(build_request('Mozilla/5.0 (PLAYSTATION 3; 1.00)'))
        self.assert_true('ismobile' in response.cookies)
        self.assert_equals('1', response.cookies['ismobile'].value)

    def test_redirects_for_mobile_browser(self):
        response = self.middleware.process_request(build_request('Mozilla/5.0 (PLAYSTATION 3; 1.00)'))
        self.assert_true(isinstance(response, HttpResponseRedirect))
        self.assert_equals(settings.MOBILE_DOMAIN, response['Location'])

    def test_redirects_if_ismobile_cookie_set(self):
        response = self.middleware.process_request(build_request(cookies={'ismobile': '1'}))
        self.assert_true(isinstance(response, HttpResponseRedirect))
        self.assert_equals(settings.MOBILE_DOMAIN, response['Location'])

    def test_redirects_if_ismobile_cookie_set(self):
        settings.MOBILE_REDIRECT_PRESERVE_URL = True
        request = build_request(cookies={'ismobile': '1'})
        request.path_info = '/some/url/'
        response = self.middleware.process_request(request)
        self.assert_true(isinstance(response, HttpResponseRedirect))
        self.assert_equals(settings.MOBILE_DOMAIN + 'some/url/', response['Location'])

########NEW FILE########
