__FILENAME__ = breadcrumbs
"""
Classes to add request.breadcrumbs as one class to have a list of breadcrumbs
TODO: maybe is better to move to contrib/breadcrumbs
"""

from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe


class BreadcrumbsInvalidFormat(Exception):
    """
    Simple exception that can be extended
    """
    pass


class BreadcrumbsNotSet(Exception):
    """
    Raised in utils.breadcrumbs_for_flatpages when we not have breadcrumbs in
    request.
    """
    pass


class Breadcrumb(object):
    """
    Breadcrumb can have methods to customize breadcrumb object, Breadcrumbs
    class send to us name and url.
    """
    def __init__(self, name, url):
        # HERE
        #
        # If I don't use force_unicode, always runs ok, but have problems on
        # template with unicode text
        self.name = name
        self.url = url

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"%s,%s" % (self.name, self.url)

    def __repr__(self):
        return u"Breadcrumb <%s,%s>" % (self.name, self.url)


class Singleton(object):

    __instance__ = None

    def __new__(cls, *a, **kw):
        if Singleton.__instance__ is None:
            Singleton.__instance__ = object.__new__(cls, *a, **kw)
            cls._Singleton__instance = Singleton.__instance__
        return Singleton.__instance__

    def _drop_it(self):
        Singleton.__instance__ = None


class Breadcrumbs(Singleton):
    """
    Breadcrumbs maintain a list of breadcrumbs that you can get interating with
    class or with get_breadcrumbs().
    """
    __bds = []
    __autohome = getattr(settings, 'BREADCRUMBS_AUTO_HOME', False)
    __urls = []
    __started = False

    def __call__(self, *args, **kwargs):
        if not len(args) and not len(kwargs):
            return self
        return self._add(*args, **kwargs)

    def __fill_home(self):
        # fill home if settings.BREADCRUMBS_AUTO_HOME is True
        if self.__autohome and len(self.__bds) == 0:
            home_title = getattr(settings, 'BREADCRUMBS_HOME_TITLE', _(u'Home'))
            self.__fill_bds((home_title, u"/"))

    def _clean(self):
        self.__bds = []
        self.__autohome = getattr(settings, 'BREADCRUMBS_AUTO_HOME', False)
        self.__urls = []
        self.__fill_home()

    def _add(self, *a, **kw):

        # match **{'name': name, 'url': url}
        if kw.get('name') and kw.get('url'):
            self.__validate((kw['name'], kw['url']), 0)
            self.__fill_bds((kw['name'], kw['url']))
        # match Breadcrumbs( 'name', 'url' )
        if len(a) == 2 and type(a[0]) not in (list, tuple):
            if(self.__validate(a, 0)):
                self.__fill_bds(a)
        # match ( ( 'name', 'url'), ..) and samething with list
        elif len(a) == 1 and type(a[0]) in (list, tuple) \
                and len(a[0]) > 0:
            for i, arg in enumerate(a[0]):
                if isinstance(arg, dict):
                    self._add(**arg)
                elif self.__validate(arg, i):
                    self.__fill_bds(arg)
        # try to ( obj1, obj2, ... ) and samething with list
        else:
            for arg in a:
                if type(arg) in (list, tuple):
                    self._add(arg)
                elif isinstance(arg, dict):
                    self._add(**arg)
                else:
                    raise BreadcrumbsInvalidFormat(_("We accept lists of "
                        "tuples, lists of dicts, or two args as name and url, "
                        "not '%s'") % a)


    def __init__(self, *a, **kw):
        """
        Call validate and if ok, call fill bd
        """
        super(Breadcrumbs, self).__init__(*a, **kw)
        if not self.__started:
            self._clean()
            self.__started = True
        if a or kw:
            self._add(*a, **kw)


    def __validate(self, obj, index):
        """
        check for object type and return a string as name for each item of a
        list or tuple with items, if error was found raise
        BreadcrumbsInvalidFormat
        """
        # for list or tuple
        if type(obj) in (list, tuple):
            if len(obj) == 2:
                if (not obj[0] and not obj[1]) or \
                        (type(obj[0]) not in (str, unicode) and \
                        type(obj[1]) not in (str, unicode)):
                    raise BreadcrumbsInvalidFormat(u"Invalid format for \
                        breadcrumb %s in %s" % (index, type(obj).__name__))
            if len(obj) != 2:
                raise BreadcrumbsInvalidFormat(
                    u"Wrong itens number in breadcrumb %s in %s. \
                    You need to send as example (name,url)" % \
                    (index, type(obj).__name__)
                )
        # for objects and dicts
        else:
            if isinstance(obj, dict) and obj.get('name') and obj.get('url'):
                obj = Breadcrumb(obj['name'], obj['url'])
            if not hasattr(obj, 'name') and not hasattr(obj, 'url'):
                raise BreadcrumbsInvalidFormat(u"You need to use a tuple like "
                    "(name, url) or dict or one object with name and url "
                    "attributes for breadcrumb.")
        return True

    def __fill_bds(self, bd):
        """
        simple interface to add Breadcrumb to bds
        """
        if hasattr(bd, 'name') and hasattr(bd, 'url'):
            bd = Breadcrumb(bd.name, bd.url)
        else:
            bd = Breadcrumb(*bd)
        if bd.url not in self.__urls:
            self.__bds.append(bd)
            self.__urls.append(bd.url)

    def __len__(self):
        return len(self.__bds)

    def __iter__(self):
        return iter(self.__bds)

    def __getitem__(self, key):
        return self.__bds[key]

    def __repr__(self):
        return self.__unicode__()

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"Breadcrumbs <%s>" % u", ".join([mark_safe(item.name) for item \
                                                    in self[:10]] + [u' ...'])

    def all(self):
        return self.__bds

# vim: ts=4 sts=4 sw=4 et ai

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from django.conf import settings
from django.http import Http404
from breadcrumbs import Breadcrumbs
from views import flatpage


class BreadcrumbsMiddleware(object):

    def process_request(self, request):
        request.breadcrumbs = Breadcrumbs()
        request.breadcrumbs._clean()


class FlatpageFallbackMiddleware(object):
    def process_response(self, request, response):
        # do nothing if flatpages middleware isn't enabled, also if response
        # code isn't 404.
        if response.status_code != 404:
            return response
        try:
            return flatpage(request, request.path_info)
        # Return the original response if any errors happened. Because this
        # is a middleware, we can't assume the errors will be caught elsewhere.
        except Http404:
            return response
        except:
            if settings.DEBUG:
                raise
            return response

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.contrib.flatpages.models import FlatPage
from django.core.cache import cache
from django.db.models.signals import post_save
from utils import make_flatpages_cache_key


def clean_flatpages_cache(sender, **kw):
    """
    Invalidate flatpages cache, because some flatpage was saved!
    """
    cache.delete(make_flatpages_cache_key())

post_save.connect(clean_flatpages_cache, sender=FlatPage)

########NEW FILE########
__FILENAME__ = breadcrumbs_tests
# # coding: utf-8
import os
from django.conf import settings
from django.test import TestCase
from django.utils.datastructures import SortedDict

from breadcrumbs.breadcrumbs import Breadcrumb, Breadcrumbs


class BreadcrumbsTest(TestCase):
    urls = 'breadcrumbs.tests.urls'

    def setUp(self):
        self.old_MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES
        breadcrumbs_middleware_class = 'breadcrumbs.middleware.BreadcrumbsMiddleware'
        if breadcrumbs_middleware_class not in settings.MIDDLEWARE_CLASSES:
            settings.MIDDLEWARE_CLASSES += (breadcrumbs_middleware_class,)

        self.old_TEMPLATE_CONTEXT_PROCESSORS = settings.TEMPLATE_CONTEXT_PROCESSORS
        request_processor = 'django.core.context_processors.request'
        if request_processor not in settings.TEMPLATE_CONTEXT_PROCESSORS:
            settings.TEMPLATE_CONTEXT_PROCESSORS += (request_processor,)

        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(
                os.path.dirname(__file__),
                'templates'
            ),
        )

        # now we start singleton. singleton are tested on singleton_tests.py
        self.breadcrumbs = Breadcrumbs()

        # set some common ta to use
        SD = SortedDict
        self.data = [
            SD([('name', 'Page1'), ('url', '/page1/')]),
            SD([('name', 'Page2'), ('url', '/page2/')]),
            SD([('name', 'Page3'), ('url', '/page2/page3/')]),
            SD([('name', 'Page4'), ('url', '/page4/')]),
            SD([('name', 'Page5'), ('url', '/page5/')]),
        ]

    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.old_MIDDLEWARE_CLASSES
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS
        settings.TEMPLATE_CONTEXT_PROCESSORS = self.old_TEMPLATE_CONTEXT_PROCESSORS

        # kill singleton
        self.breadcrumbs._drop_it()
        del self.data

    def test_breadcrumb_class(self):
        b = Breadcrumb(**self.data[0])
        self.assertEqual(b.name, self.data[0]['name'])
        self.assertEqual(b.url, self.data[0]['url'])

    def test_breadcrumbs_singleton(self):
        brd = Breadcrumbs()
        brd(**self.data[0])
        brd2 = Breadcrumbs()
        brd2(**self.data[1])
        # test 3 instances to see if singleton really works
        self.assertEqual(self.breadcrumbs[0].__dict__,
                                            Breadcrumb(**self.data[0]).__dict__)
        self.assertEqual(self.breadcrumbs[1].__dict__,
                                            Breadcrumb(**self.data[1]).__dict__)
        self.assertEqual(brd[1].__dict__, Breadcrumbs()[1].__dict__)

    def test_breadcrumbs_params_and_iteration(self):

        b = self.breadcrumbs

        b(self.data[0]['name'], self.data[0]['url'])
        b(*self.data[1].values())
        b(**self.data[2])
        b(self.data[3:5])
        for i, bd in enumerate(b):
            self.assertEqual(bd.__dict__, Breadcrumb(**self.data[i]).__dict__)


    def test_request_breadcrumbs(self):
        response = self.client.get('/page1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
            '<ul id="breadcrumbs"><li><a href="/page1/">Page 1</a></li></ul>')

########NEW FILE########
__FILENAME__ = flatpages_tests
# coding: utf-8
import os
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.test import TestCase
from django.utils.datastructures import SortedDict
from breadcrumbs.breadcrumbs import Breadcrumb, Breadcrumbs


class FlatpagesTest(TestCase):
    fixtures = ['sample_flatpages_for_breadcrumbs.json']

    def setUp(self):
        breadcrumbs_middleware_class = 'breadcrumbs.middleware.BreadcrumbsMiddleware'
        flatpages_middleware_class = 'breadcrumbs.middleware.FlatpageFallbackMiddleware'

        # remove breadcrumbs middlewares to assert that we set correct
        # order
        self.old_MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES
        settings.MIDDLEWARE_CLASSES = [mid for mid \
            in self.old_MIDDLEWARE_CLASSES if mid not in \
                (breadcrumbs_middleware_class, flatpages_middleware_class)]
        settings.MIDDLEWARE_CLASSES += [
            breadcrumbs_middleware_class,
            flatpages_middleware_class
        ]
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(
                os.path.dirname(__file__),
                'templates'
            ),
        )
        # now we start singleton. singleton are tested on singleton_tests.py
        self.breadcrumbs = Breadcrumbs()

    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.old_MIDDLEWARE_CLASSES

        # kill singleton
        self.breadcrumbs._drop_it()

    def test_flatpages_fixture_loaded(self):
        flat1 = FlatPage.objects.get(pk=1)
        self.assertEqual(flat1.title, u"Flat Page 1")
        self.assertEqual(flat1.content, u"This is flat 1")
        flat2 = FlatPage.objects.get(pk=2)
        self.assertEqual(flat2.title, u"Flat page 2")
        self.assertEqual(flat2.content, u"This is flat 2 under flat 1")

    def test_404_flatpage(self):
        response = self.client.get('/404_not_found/')
        self.assertEqual(response.status_code, 404)
        # self.assertContains(response, "<p>Isn't it flat!</p>")

    def test_fallback_flatpage(self):
        response = self.client.get('/flat01/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
            '<ul id="breadcrumbs"><li><a href="/flat01/">Flat Page 1</a></li></ul>')

        response = self.client.get('/flat01/flat02/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response,
            '<ul id="breadcrumbs"><li><a href="/flat01/">Flat Page 1</a> &raquo; </li><li><a href="/flat01/flat02/">Flat page 2</a></li></ul>')

########NEW FILE########
__FILENAME__ = singleton_tests
# coding: utf-8

from django.test import TestCase

from breadcrumbs.breadcrumbs import Singleton


class Foo(Singleton):
    """
    Class used in singleton tests
    """
    pass


class SingletonTest(TestCase):

    def test_singleton(self):
        """
        Test singleton implementation with values
        """
        a = Foo()
        a.attr_1 = 1

        b = Foo()

        self.assertEqual(b.attr_1, 1)
        self.assertTrue(a is b, "'a' isn't 'b', Singleton not works")

    def test_singleton_destruction(self):
        """
        Test singleton imsinplementation with values and than destroy it
        """
        a = Foo()
        id_a = id(a)
        a.attr_1 = 1

        b = Foo()
        id_b = id(b)

        self.assertEqual(id_a, id_b)
        self.assertEqual(b.attr_1, 1)
        self.assertTrue(a is b, "'a' isn't 'b', Singleton not works")

        a._drop_it()

        c = Foo()
        id_c = id(c)
        self.assertNotEqual(id_a, id_c)
        self.assertNotEqual(getattr(c,'attr_1',None), 1)


########NEW FILE########
__FILENAME__ = urls
import django
if django.get_version().startswith('1.4'):
    from django.conf.urls import patterns
else:
    from django.conf.urls.defaults import patterns
from .views import page1
# special urls for flatpage test cases
urlpatterns = patterns('',
    (r'^page1/', page1),
)


########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.template import RequestContext

def page1(request):
    request.breadcrumbs("Page 1", request.get_full_path())
    return render_to_response('page1.html', {},
        context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns

urlpatterns = patterns('breadcrumbs.views',
    (r'^(?P<url>.*)$', 'flatpage'),
)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from django.contrib.flatpages.models import FlatPage
from django.http import Http404
from breadcrumbs import Breadcrumbs, BreadcrumbsNotSet
from django.conf import settings
from django.core.cache import cache


def make_flatpages_cache_key():
    """
    Create a cache key based on some basic data, respecting defined site.
    """
    key = "flatpages_cache_%s-%s" % (hash(settings.SITE_ID),
                                      hash(settings.SECRET_KEY))

    return key


def get_flapage_from_cache(url):
    """
    Try get flatpage from cache entry with all flatpages by url.
    If not found, create cache and return flatpage from db.

    This probably avoid some hits on DB.
    """
    site_id = settings.SITE_ID
    cache_key = make_flatpages_cache_key()
    flatpages = cache.get(cache_key)
    if flatpages and url in flatpages:
        return flatpages[url]

    # flatpages cache not exist or flatpage not found.

    # 1. get all flatpages.
    flatpages = dict([(f.url, f) for f in
        FlatPage.objects.filter(sites__id__exact=site_id).order_by('url')])

    # 2. if url not in flatpages, raise Http404
    if url not in flatpages:
        raise Http404

    # 3. if url in flatpages, recreate cache and return flatpage
    cache.delete(cache_key)
    cache.add(cache_key, flatpages)
    return flatpages[url]


def breadcrumbs_for_flatpages(request, flatpage):
    """ given request and flatpage instance create breadcrumbs for all flat
    pages """
    if not hasattr(request, 'breadcrumbs') or \
                            not isinstance(request.breadcrumbs, Breadcrumbs):
        raise BreadcrumbsNotSet(u"You need to setup breadcrumbs to use this "
                                u"function.")

    if not isinstance(flatpage, FlatPage) or not hasattr(flatpage, 'id'):
        raise TypeError(u"flatpage argument isn't a FlatPage instance or not "
                        u"have id.")

    # URL for a flatpage can be composed of other flatpages, ex:
    #
    # We have:
    #   flatpage01 = /flat01/
    #   flatpage02 = /flat01/flat02/
    #   flatpage03 = /flat01/flat02/flat03/
    #
    # In breadcrumbs we want to know each title of each page, so we split url
    # in parts, and try to get flatpage title.
    #
    # However, you can define something like that in your urls.py:
    #   (r'^pages/', include('breadcrumbs.urls')),
    # And, we will never know what is /pages/, so we ignore it for now.
    paths = []
    for part in request.path_info.split(u"/"):
        # When split we have u"" for slashes
        if len(part) == 0:
            continue
        # Add slash agai
        if not part.startswith(u"/"):
            part = u"/" + part
        if not part.endswith(u"/"):
            part = part + u"/"
        # If we have something on paths, url for flatpage is composed of what we
        # have in path + part. Note that strings in path not have last slash, but
        # part have.
        if len(paths) > 0:
            url = u"".join(paths + [part])
        else:
            url = part
        # if part of url is same url of flatpage instance, we don't hit
        # database again, we get page from FlatPage instance.
        # If part of url isn't same url of flatpage instance, we try to get it.
        # If page doesn't exist, we just continue to next part.
        if url == flatpage.url:
            request.breadcrumbs(flatpage.title, flatpage.url)
        else:
            try:
                f = FlatPage.objects.get(url=url)
            except FlatPage.DoesNotExist:
                # TODO: this part can be a view, maybe is a good idea get that
                # view and check for viewfunc.breadcrumb_title or
                # viewclass.breadcrumb_title attributes.
                continue
            else:
                request.breadcrumbs(f.title, f.url)
        # add last part of path in paths with one slash
        paths.append(u"/" + url[1:-1].rpartition(u"/")[-1])

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.contrib.flatpages.views import render_flatpage
from django.http import Http404, HttpResponsePermanentRedirect
from utils import breadcrumbs_for_flatpages, get_flapage_from_cache


def flatpage(request, url):
    """
    Public interface to the flat page view.

    Models: `flatpages.flatpages`
    Templates: Uses the template defined by the ``template_name`` field,
        or `flatpages/default.html` if template_name is not defined.
    Context:
        flatpage
            `flatpages.flatpages` object
    """

    if not url.startswith('/'):
        url = '/' + url
    try:
        # try load flatpage from cache, else, update cache and get from DB
        f = get_flapage_from_cache(url)
    except Http404:
        if not url.endswith('/') and settings.APPEND_SLASH:
            url += '/'
            f = get_flapage_from_cache(url)
            return HttpResponsePermanentRedirect('%s/' % request.path)
        else:
            raise

    # create breadcrumbs
    breadcrumbs_for_flatpages(request, f)

    return render_flatpage(request, f)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for breadcrumbs_sample project.
import os
PROJECT_ROOT=  os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '%s/test.db' % PROJECT_ROOT, # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'fh+tvwi6aw(z_of+f!=1heme@o+r^=^=c&b%hh7r+$x+e&3pj7'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'breadcrumbs.middleware.BreadcrumbsMiddleware',
    'breadcrumbs.middleware.FlatpageFallbackMiddleware',
)

ROOT_URLCONF = 'breadcrumbs_sample.urls'

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
    'django.contrib.flatpages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'breadcrumbs_sample.webui'
)

BREADCRUMBS_AUTO_HOME = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^breadcrumbs_sample/', include('breadcrumbs_sample.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    (r'^$','webui.views.home'),
    (r'^someview/$','webui.views.someview'),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
# Create your views here.

from django.shortcuts import render_to_response
from django.template.context import RequestContext


def home(request):
    print request.breadcrumbs
    return render_to_response('home.html',
        {'text': 'Hello, this is home!'},
        context_instance=RequestContext(request))


def someview(request):
    request.breadcrumbs('just a view to show some url', request.path)

    return render_to_response('home.html',
        {'text': 'Hello, this is some second view'},
        context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import os, sys

from django.conf import settings


if not settings.configured:
    settings_dict = dict(
        SITE_ID=1,
        ROOT_URLCONF='breadcrumbs.tests.urls',
        INSTALLED_APPS=(
            'django.contrib.contenttypes',
            'django.contrib.sites',
            'django.contrib.flatpages',
            'breadcrumbs',
            ),
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3"
                }
            },
        )

    settings.configure(**settings_dict)


def runtests(*test_args):

    if not test_args:
        test_args = ['breadcrumbs']

    # try to set more used args to django test
    test_kwargs = {
        'verbosity': 1,
        'noinput': False,
        'failfast': False,
    }
    for i,arg in enumerate(sys.argv):
        if arg.startswith('-v'):
            _value = arg.replace('-v','')
            if len(_value):
                test_kwargs['verbosity'] = int(_value)
            else:
                test_kwargs['verbosity'] = int(sys.argv[i+1])
        if arg == '--noinput':
            test_kwargs['noinput'] = True
        if arg == '--failfast':
            test_kwargs['failfast'] =True

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    from django.test.simple import DjangoTestSuiteRunner
    failures = DjangoTestSuiteRunner(
        interactive=True, **test_kwargs).run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sample_d14.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for sample_d14 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '14i6-n-!v*w07gyx4is-j3z)ou2^%8u+i5t0(3$^wyme1odalz'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'breadcrumbs.middleware.BreadcrumbsMiddleware',
    'breadcrumbs.middleware.FlatpageFallbackMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request'
)

ROOT_URLCONF = 'sample_d14.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'sample_d14.wsgi.application'

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
    'django.contrib.staticfiles',
    'django.contrib.flatpages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'webui',
    'breadcrumbs',
)

BREADCRUMBS_AUTO_HOME = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'sample_d14.views.home', name='home'),
    # url(r'^sample_d14/', include('sample_d14.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'webui.views.home', name='home'),
    url(r'^someview/$', 'webui.views.someview', name='someview'),
    (r'^pages/', include('breadcrumbs.urls')),
)

urlpatterns += patterns('breadcrumbs.views',
    (r'^pages2/(?P<url>.*)$', 'flatpage'),
    url(r'^license/$', 'flatpage', {'url': '/flat04/'}, name='license'),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for sample_d14 project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sample_d14.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

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
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template.context import RequestContext


def home(request):
    return render_to_response('home.html',
        {'text': 'Hello, this is home!'},
        context_instance=RequestContext(request))


def someview(request):
    request.breadcrumbs('just a view to show some url', request.path)

    return render_to_response('home.html',
        {'text': 'Hello, this is some second view'},
        context_instance=RequestContext(request))

########NEW FILE########
