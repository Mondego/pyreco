__FILENAME__ = access
from django.conf import settings
from rosetta.conf import settings as rosetta_settings

from django.utils import importlib


def can_translate(user):
    return get_access_control_function()(user)


def get_access_control_function():
    """
    Return a predicate for determining if a user can access the Rosetta views
    """
    fn_path = getattr(settings, 'ROSETTA_ACCESS_CONTROL_FUNCTION', None)
    if fn_path is None:
        return is_superuser_staff_or_in_translators_group
    # Dynamically load a permissions function
    perm_module, perm_func = fn_path.rsplit('.', 1)
    perm_module = importlib.import_module(perm_module)
    return getattr(perm_module, perm_func)


# Default access control test
def is_superuser_staff_or_in_translators_group(user):
    if not getattr(settings, 'ROSETTA_REQUIRES_AUTH', True):
        return True
    if not user.is_authenticated():
        return False
    elif user.is_superuser and user.is_staff:
        return True
    else:
        return user.groups.filter(name='translators').exists()


def can_translate_language(user, langid):
    if not rosetta_settings.ROSETTA_LANGUAGE_GROUPS:
        return can_translate(user)
    elif not user.is_authenticated():
        return False
    elif user.is_superuser and user.is_staff:
        return True
    else:
        return user.groups.filter(name='translators-%s' % langid).exists()

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

# Number of messages to display per page.
MESSAGES_PER_PAGE = getattr(settings, 'ROSETTA_MESSAGES_PER_PAGE', 10)


# Enable Google translation suggestions
ENABLE_TRANSLATION_SUGGESTIONS = getattr(settings, 'ROSETTA_ENABLE_TRANSLATION_SUGGESTIONS', False)


# Can be obtained for free here: https://translate.yandex.com/apikeys
YANDEX_TRANSLATE_KEY = getattr(settings, 'YANDEX_TRANSLATE_KEY', None)

# Can be obtained for free here: https://ssl.bing.com/webmaster/Developers/AppIds/
AZURE_CLIENT_ID = getattr(settings, 'AZURE_CLIENT_ID', None)
AZURE_CLIENT_SECRET = getattr(settings, 'AZURE_CLIENT_SECRET', None)

# Displays this language beside the original MSGID in the admin
MAIN_LANGUAGE = getattr(settings, 'ROSETTA_MAIN_LANGUAGE', None)

# Change these if the source language in your PO files isn't English
MESSAGES_SOURCE_LANGUAGE_CODE = getattr(settings, 'ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE', 'en')
MESSAGES_SOURCE_LANGUAGE_NAME = getattr(settings, 'ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME', 'English')

ACCESS_CONTROL_FUNCTION = getattr(
    settings, 'ROSETTA_ACCESS_CONTROL_FUNCTION', None)


"""
When running WSGI daemon mode, using mod_wsgi 2.0c5 or later, this setting
controls whether the contents of the gettext catalog files should be
automatically reloaded by the WSGI processes each time they are modified.

Notes:

 * The WSGI daemon process must have write permissions on the WSGI script file
   (as defined by the WSGIScriptAlias directive.)
 * WSGIScriptReloading must be set to On (it is by default)
 * For performance reasons, this setting should be disabled in production environments
 * When a common rosetta installation is shared among different Django projects,
   each one running in its own distinct WSGI virtual host, you can activate
   auto-reloading in individual projects by enabling this setting in the project's
   own configuration file, i.e. in the project's settings.py

Refs:

 * http://code.google.com/p/modwsgi/wiki/ReloadingSourceCode
 * http://code.google.com/p/modwsgi/wiki/ConfigurationDirectives#WSGIReloadMechanism

"""
WSGI_AUTO_RELOAD = getattr(settings, 'ROSETTA_WSGI_AUTO_RELOAD', False)
UWSGI_AUTO_RELOAD = getattr(settings, 'ROSETTA_UWSGI_AUTO_RELOAD', False)


# Exclude applications defined in this list from being translated
EXCLUDED_APPLICATIONS = getattr(settings, 'ROSETTA_EXCLUDED_APPLICATIONS', ())

# Line length of the updated PO file
POFILE_WRAP_WIDTH = getattr(settings, 'ROSETTA_POFILE_WRAP_WIDTH', 78)

# Storage class to handle temporary data storage
STORAGE_CLASS = getattr(settings, 'ROSETTA_STORAGE_CLASS', 'rosetta.storage.CacheRosettaStorage')


# Allow overriding of the default filenames, you mostly won't need to change this
POFILENAMES = getattr(settings, 'ROSETTA_POFILENAMES', ('django.po', 'djangojs.po'))

ROSETTA_CACHE_NAME = getattr(settings, 'ROSETTA_CACHE_NAME', 'default'
                             if settings.CACHES.get('rosetta', None) is None
                             else 'rosetta')

# Require users to be authenticated (and Superusers or in group "translators").
# Set this to False at your own risk
ROSETTA_REQUIRES_AUTH = getattr(settings, 'ROSETTA_REQUIRES_AUTH', True)

# Exclude paths defined in this list from being searched (usually ends with "locale")
ROSETTA_EXCLUDED_PATHS =  getattr(settings, 'ROSETTA_EXCLUDED_PATHS', ())

# Set to True to enable language-specific groups, which can be used to give
# different translators access to different languages. Instead of creating a
# 'translators` group, create individual per-language groups, e.g.
# 'translators-de', 'translators-fr', ...
ROSETTA_LANGUAGE_GROUPS = getattr(settings, 'ROSETTA_LANGUAGE_GROUPS', False)

########NEW FILE########
__FILENAME__ = models
from django.db import models
# Create your models here.

########NEW FILE########
__FILENAME__ = poutil
from datetime import datetime
from django.conf import settings
from django.core.cache import get_cache
from rosetta.conf import settings as rosetta_settings
import django
import os

try:
    from django.utils import timezone
except:
    timezone = None


try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

cache = get_cache(rosetta_settings.ROSETTA_CACHE_NAME)


def timestamp_with_timezone(dt=None):
    """
    Return a timestamp with a timezone for the configured locale.  If all else
    fails, consider localtime to be UTC.
    """
    dt = dt or datetime.now()
    if timezone is None:
        return dt.strftime('%Y-%m-%d %H:%M%z')
    if not dt.tzinfo:
        tz = timezone.get_current_timezone()
        if not tz:
            tz = timezone.utc
        dt = dt.replace(tzinfo=timezone.get_current_timezone())
    return dt.strftime("%Y-%m-%d %H:%M%z")


def find_pos(lang, project_apps=True, django_apps=False, third_party_apps=False):
    """
    scans a couple possible repositories of gettext catalogs for the given
    language code

    """

    paths = []

    # project/locale
    parts = settings.SETTINGS_MODULE.split('.')
    project = __import__(parts[0], {}, {}, [])
    abs_project_path = os.path.normpath(os.path.abspath(os.path.dirname(project.__file__)))
    if project_apps:
        if os.path.exists(os.path.abspath(os.path.join(os.path.dirname(project.__file__), 'locale'))):
            paths.append(os.path.abspath(os.path.join(os.path.dirname(project.__file__), 'locale')))
        if os.path.exists(os.path.abspath(os.path.join(os.path.dirname(project.__file__), '..', 'locale'))):
            paths.append(os.path.abspath(os.path.join(os.path.dirname(project.__file__), '..', 'locale')))

    # django/locale
    if django_apps:
        django_paths = cache.get('rosetta_django_paths')
        if django_paths is None:
            django_paths = []
            for root, dirnames, filename in os.walk(os.path.abspath(os.path.dirname(django.__file__))):
                if 'locale' in dirnames:
                    django_paths.append(os.path.join(root, 'locale'))
                    continue
            cache.set('rosetta_django_paths', django_paths, 60 * 60)
        paths = paths + django_paths
    # settings
    for localepath in settings.LOCALE_PATHS:
        if os.path.isdir(localepath):
            paths.append(localepath)

    # project/app/locale
    for appname in settings.INSTALLED_APPS:
        if rosetta_settings.EXCLUDED_APPLICATIONS and appname in rosetta_settings.EXCLUDED_APPLICATIONS:
            continue
        p = appname.rfind('.')
        if p >= 0:
            app = getattr(__import__(appname[:p], {}, {}, [str(appname[p + 1:])]), appname[p + 1:])
        else:
            app = __import__(appname, {}, {}, [])

        apppath = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(app.__file__), 'locale')))

        # django apps
        if 'contrib' in apppath and 'django' in apppath and not django_apps:
            continue

        # third party external
        if not third_party_apps and abs_project_path not in apppath:
            continue

        # local apps
        if not project_apps and abs_project_path in apppath:
            continue


        if os.path.isdir(apppath):
            paths.append(apppath)

    ret = set()
    langs = [lang, ]
    if u'-' in lang:
        _l, _c = map(lambda x: x.lower(), lang.split(u'-'))
        langs += [u'%s_%s' % (_l, _c), u'%s_%s' % (_l, _c.upper()), ]
    elif u'_' in lang:
        _l, _c = map(lambda x: x.lower(), lang.split(u'_'))
        langs += [u'%s-%s' % (_l, _c), u'%s-%s' % (_l, _c.upper()), ]

    paths = map(os.path.normpath, paths)
    paths = list(set(paths))
    for path in paths:
        # Exclude paths
        if not path in rosetta_settings.ROSETTA_EXCLUDED_PATHS:
            for lang_ in langs:
                dirname = os.path.join(path, lang_, 'LC_MESSAGES')
                for fn in rosetta_settings.POFILENAMES:
                    filename = os.path.join(dirname, fn)
                    if os.path.isfile(filename):
                        ret.add(os.path.abspath(filename))
    return list(sorted(ret))


def pagination_range(first, last, current):
    r = []

    r.append(first)
    if first + 1 < last:
        r.append(first + 1)

    if current - 2 > first and current - 2 < last:
        r.append(current - 2)
    if current - 1 > first and current - 1 < last:
        r.append(current - 1)
    if current > first and current < last:
        r.append(current)
    if current + 1 < last and current + 1 > first:
        r.append(current + 1)
    if current + 2 < last and current + 2 > first:
        r.append(current + 2)

    if last - 1 > first:
        r.append(last - 1)
    r.append(last)

    r = list(set(r))
    r.sort()
    prev = 10000
    for e in r[:]:
        if prev + 1 < e:
            try:
                r.insert(r.index(e), '...')
            except ValueError:
                pass
        prev = e
    return r

########NEW FILE########
__FILENAME__ = signals
from django import dispatch
entry_changed = dispatch.Signal(
    providing_args=["user", "old_msgstr", "old_fuzzy", "pofile", "language_code",]
)

post_save = dispatch.Signal(
    providing_args=["language_code","request",]
)

########NEW FILE########
__FILENAME__ = storage
from django.core.cache import get_cache
from django.conf import settings
from django.utils import importlib
from django.core.exceptions import ImproperlyConfigured
from rosetta.conf import settings as rosetta_settings
import hashlib
import time
import six
import django


cache = get_cache(rosetta_settings.ROSETTA_CACHE_NAME)


class BaseRosettaStorage(object):
    def __init__(self, request):
        self.request = request

    def get(self, key, default=None):
        raise NotImplementedError

    def set(self, key, val):
        raise NotImplementedError

    def has(self, key):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError


class DummyRosettaStorage(BaseRosettaStorage):
    def get(self, key, default=None):
        return default

    def set(self, key, val):
        pass

    def has(self, key):
        return False

    def delete(self, key):
        pass


class SessionRosettaStorage(BaseRosettaStorage):
    def __init__(self, request):
        super(SessionRosettaStorage, self).__init__(request)

        if 'signed_cookies' in settings.SESSION_ENGINE and django.VERSION[1] >= 6 and 'pickle' not in settings.SESSION_SERIALIZER.lower():
            raise ImproperlyConfigured("Sorry, but django-rosetta doesn't support the `signed_cookies` SESSION_ENGINE in Django >= 1.6, because rosetta specific session files cannot be serialized.")

    def get(self, key, default=None):
        if key in self.request.session:
            return self.request.session[key]
        return default

    def set(self, key, val):
        self.request.session[key] = val

    def has(self, key):
        return key in self.request.session

    def delete(self, key):
        del(self.request.session[key])


class CacheRosettaStorage(BaseRosettaStorage):
    # unlike the session storage backend, cache is shared among all users
    # so we need to per-user key prefix, which we store in the session
    def __init__(self, request):
        super(CacheRosettaStorage, self).__init__(request)

        if 'rosetta_cache_storage_key_prefix' in self.request.session:
            self._key_prefix = self.request.session['rosetta_cache_storage_key_prefix']
        else:
            self._key_prefix = hashlib.new('sha1', six.text_type(time.time()).encode('utf8')).hexdigest()
            self.request.session['rosetta_cache_storage_key_prefix'] = self._key_prefix

        if self.request.session['rosetta_cache_storage_key_prefix'] != self._key_prefix:
            raise ImproperlyConfigured("You can't use the CacheRosettaStorage because your Django Session storage doesn't seem to be working. The CacheRosettaStorage relies on the Django Session storage to avoid conflicts.")

        # Make sure we're not using DummyCache
        if 'dummycache' in settings.CACHES[rosetta_settings.ROSETTA_CACHE_NAME]['BACKEND'].lower():
            raise ImproperlyConfigured("You can't use the CacheRosettaStorage if your cache isn't correctly set up (you are use the DummyCache cache backend).")

        # Make sure the actually actually works
        try:
            self.set('rosetta_cache_test', 'rosetta')
            if not self.get('rosetta_cache_test') == 'rosetta':
                raise ImproperlyConfigured("You can't use the CacheRosettaStorage if your cache isn't correctly set up, please double check your Django DATABASES setting and that the cache server is responding.")
        finally:
            self.delete('rosetta_cache_test')

    def get(self, key, default=None):
        #print ('get', self._key_prefix + key)
        return cache.get(self._key_prefix + key, default)

    def set(self, key, val):
        #print ('set', self._key_prefix + key)
        cache.set(self._key_prefix + key, val, 86400)

    def has(self, key):
        #print ('has', self._key_prefix + key)
        return (self._key_prefix + key) in cache

    def delete(self, key):
        #print ('del', self._key_prefix + key)
        cache.delete(self._key_prefix + key)


def get_storage(request):
    from rosetta.conf import settings
    storage_module, storage_class = settings.STORAGE_CLASS.rsplit('.', 1)
    storage_module = importlib.import_module(storage_module)
    return getattr(storage_module, storage_class)(request)

########NEW FILE########
__FILENAME__ = rosetta
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
import re
from django.template import Node
import six


register = template.Library()
rx = re.compile(r'(%(\([^\s\)]*\))?[sd])')


def format_message(message):
    return mark_safe(rx.sub('<code>\\1</code>', escape(message).replace(r'\n', '<br />\n')))
format_message = register.filter(format_message)


def lines_count(message):
    return 1 + sum([len(line) / 50 for line in message.split('\n')])
lines_count = register.filter(lines_count)


def mult(a, b):
    return int(a) * int(b)
mult = register.filter(mult)


def minus(a, b):
    try:
        return int(a) - int(b)
    except:
        return 0
minus = register.filter(minus)


def gt(a, b):
    try:
        return int(a) > int(b)
    except:
        return False
gt = register.filter(gt)


def do_incr(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise SyntaxError("'incr' tag requires at least one argument")
    name = args[1]
    if not hasattr(parser, '_namedIncrNodes'):
        parser._namedIncrNodes = {}
    if not name in parser._namedIncrNodes:
        parser._namedIncrNodes[name] = IncrNode(0)
    return parser._namedIncrNodes[name]
do_incr = register.tag('increment', do_incr)


class IncrNode(template.Node):
    def __init__(self, init_val=0):
        self.val = init_val

    def render(self, context):
        self.val += 1
        return six.text_type(self.val)


def is_fuzzy(message):
    return message and hasattr(message, 'flags') and 'fuzzy' in message.flags
is_fuzzy = register.filter(is_fuzzy)


class RosettaCsrfTokenPlaceholder(Node):
    def render(self, context):
        return mark_safe(u"<!-- csrf token placeholder -->")


def rosetta_csrf_token(parser, token):
    try:
        from django.template.defaulttags import csrf_token
        return csrf_token(parser, token)
    except ImportError:
        return RosettaCsrfTokenPlaceholder()
rosetta_csrf_token = register.tag(rosetta_csrf_token)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse, resolve
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import cache
from django.template.defaultfilters import floatformat
from django.test import TestCase
from django.test.client import Client
from rosetta.conf import settings as rosetta_settings
from rosetta.signals import entry_changed, post_save
import os
import shutil
import six
import django


try:
    from django.dispatch import receiver
except ImportError:
    # We might be in django < 1.3, so backport this function
    def receiver(signal, **kwargs):
        def _decorator(func):
            signal.connect(func, **kwargs)
            return func
        return _decorator


class RosettaTestCase(TestCase):
    urls = 'rosetta.tests.urls'

    def __init__(self, *args, **kwargs):
        super(RosettaTestCase, self).__init__(*args, **kwargs)
        self.curdir = os.path.dirname(__file__)
        self.dest_file = os.path.normpath(os.path.join(self.curdir, '../locale/xx/LC_MESSAGES/django.po'))
        self.django_version_major, self.django_version_minor = django.VERSION[0], django.VERSION[1]

    def setUp(self):
        user = User.objects.create_user('test_admin', 'test@test.com', 'test_password')
        user2 = User.objects.create_user('test_admin2', 'test@test2.com', 'test_password')
        user3 = User.objects.create_user('test_admin3', 'test@test2.com', 'test_password')

        user.is_superuser, user2.is_superuser, user3.is_superuser = True, True, True
        user.is_staff, user2.is_staff, user3.is_staff = True, True, False

        user.save()
        user2.save()
        user3.save()

        self.client2 = Client()

        self.client.login(username='test_admin', password='test_password')
        self.client2.login(username='test_admin2', password='test_password')

        self.__old_settings_languages = settings.LANGUAGES
        settings.LANGUAGES = (('xx', 'dummy language'), ('fr_FR.utf8', 'French (France), UTF8'))

        self.__session_engine = settings.SESSION_ENGINE
        self.__storage_class = rosetta_settings.STORAGE_CLASS
        self.__require_auth = rosetta_settings.ROSETTA_REQUIRES_AUTH

        shutil.copy(self.dest_file, self.dest_file + '.orig')

    def tearDown(self):
        settings.LANGUAGES = self.__old_settings_languages
        settings.SESSION_ENGINE = self.__session_engine
        rosetta_settings.STORAGE_CLASS = self.__storage_class
        rosetta_settings.ROSETTA_REQUIRES_AUTH = self.__require_auth
        shutil.move(self.dest_file + '.orig', self.dest_file)

    def test_1_ListLoading(self):
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))

    def test_2_PickFile(self):
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0,), kwargs=dict()) + '?rosetta')
        r = self.client.get(reverse('rosetta-home'))

        self.assertTrue('dummy language' in str(r.content))

    def test_3_DownloadZIP(self):
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')

        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()) + '?rosetta')
        r = self.client.get(reverse('rosetta-home'))
        r = self.client.get(reverse('rosetta-download-file') + '?rosetta')
        self.assertTrue('content-type' in r._headers.keys())
        self.assertTrue('application/x-zip' in r._headers.get('content-type'))

    def test_4_DoChanges(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.template')), self.dest_file)

        # Load the template file
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home') + '?filter=untranslated')
        r = self.client.get(reverse('rosetta-home'))
        # make sure both strings are untranslated
        self.assertTrue('dummy language' in str(r.content))
        self.assertTrue('String 1' in str(r.content))
        self.assertTrue('String 2' in str(r.content))
        self.assertTrue('m_e48f149a8b2e8baa81b816c0edf93890' in str(r.content))

        # post a translation
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world', _next='_next'))

        # reload all untranslated strings
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()) + '?rosetta')
        r = self.client.get(reverse('rosetta-home') + '?filter=untranslated')
        r = self.client.get(reverse('rosetta-home'))

        # the translated string no longer is up for translation
        self.assertTrue('String 1'  in str(r.content))
        self.assertTrue('String 2' not in str(r.content))

        # display only translated strings
        r = self.client.get(reverse('rosetta-home') + '?filter=translated')
        r = self.client.get(reverse('rosetta-home'))

        # The tranlsation was persisted
        self.assertTrue('String 1' not  in str(r.content))
        self.assertTrue('String 2' in str(r.content))
        self.assertTrue('Hello, world' in str(r.content))

    def test_5_TestIssue67(self):
        # testcase for issue 67: http://code.google.com/p/django-rosetta/issues/detail?id=67
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue67.template')), self.dest_file)
        # Make sure the plurals string is valid
        f_ = open(self.dest_file, 'rb')
        content = f_.read()
        f_.close()
        self.assertTrue('Hello, world' not in six.text_type(content))
        self.assertTrue('|| n%100>=20) ? 1 : 2)' in six.text_type(content))
        del(content)

        # Load the template file
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')

        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()) + '?rosetta')
        r = self.client.get(reverse('rosetta-home') + '?filter=untranslated')
        r = self.client.get(reverse('rosetta-home'))

        # make sure all strings are untranslated
        self.assertTrue('dummy language' in str(r.content))
        self.assertTrue('String 1' in str(r.content))
        self.assertTrue('String 2' in str(r.content))
        self.assertTrue('m_e48f149a8b2e8baa81b816c0edf93890' in str(r.content))

        # post a translation
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world', _next='_next'))

        # Make sure the plurals string is still valid
        f_ = open(self.dest_file, 'rb')
        content = f_.read()
        f_.close()
        self.assertTrue('Hello, world' in str(content))
        self.assertTrue('|| n%100>=20) ? 1 : 2)' in str(content))
        self.assertTrue('or n%100>=20) ? 1 : 2)' not in str(content))
        del(content)

    def test_6_ExcludedApps(self):

        rosetta_settings.EXCLUDED_APPLICATIONS = ('rosetta',)

        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue('rosetta/locale/xx/LC_MESSAGES/django.po' not in str(r.content))

        rosetta_settings.EXCLUDED_APPLICATIONS = ()

        r = self.client.get(reverse('rosetta-pick-file') + '?rosetta')
        self.assertTrue('rosetta/locale/xx/LC_MESSAGES/django.po' in str(r.content))

    def test_7_selfInApplist(self):
        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue('rosetta/locale/xx/LC_MESSAGES/django.po' in str(r.content))

        self.client.get(reverse('rosetta-pick-file') + '?filter=project')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue('rosetta/locale/xx/LC_MESSAGES/django.po' not in str(r.content))

    def test_8_hideObsoletes(self):
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))

        # not in listing
        for p in range(1, 5):
            r = self.client.get(reverse('rosetta-home') + '?page=%d' % p)
            self.assertTrue('dummy language' in str(r.content))
            self.assertTrue('Les deux' not in str(r.content))

        r = self.client.get(reverse('rosetta-home') + '?query=Les%20Deux')
        self.assertTrue('dummy language' in str(r.content))
        self.assertTrue('Les deux' not in str(r.content))

    def test_9_concurrency(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.template')), self.dest_file)

        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client2.get(reverse('rosetta-pick-file') + '?filter=third-party')

        self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        self.client2.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))

        # Load the template file
        r = self.client.get(reverse('rosetta-home') + '?filter=untranslated')
        r = self.client.get(reverse('rosetta-home'))
        r2 = self.client2.get(reverse('rosetta-home') + '?filter=untranslated')
        r2 = self.client2.get(reverse('rosetta-home'))

        self.assertTrue('String 1' in str(r.content))
        self.assertTrue('String 1' in str(r2.content))
        self.assertTrue('m_08e4e11e2243d764fc45a5a4fba5d0f2' in str(r.content))
        r = self.client.post(reverse('rosetta-home'), dict(m_08e4e11e2243d764fc45a5a4fba5d0f2='Hello, world', _next='_next'), follow=True)
        r2 = self.client2.get(reverse('rosetta-home'))

        # Client 2 reloads the home, forces a reload of the catalog,
        # the untranslated string1 is now translated
        self.assertTrue('String 1' not in str(r2.content))
        self.assertTrue('String 2' in str(r2.content))

        r = self.client.get(reverse('rosetta-home') + '?filter=untranslated')
        r = self.client.get(reverse('rosetta-home'))
        r2 = self.client2.get(reverse('rosetta-home') + '?filter=untranslated')
        r2 = self.client2.get(reverse('rosetta-home'))

        self.assertTrue('String 2' in str(r2.content) and 'm_e48f149a8b2e8baa81b816c0edf93890' in str(r2.content))
        self.assertTrue('String 2' in str(r.content) and 'm_e48f149a8b2e8baa81b816c0edf93890' in str(r.content))

        # client 2 posts!
        r2 = self.client2.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world, from client two!', _next='_next'), follow=True)

        self.assertTrue('save-conflict' not in str(r2.content))

        # uh-oh here comes client 1
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world, from client one!', _next='_next'), follow=True)
        # An error message is displayed
        self.assertTrue('save-conflict' in str(r.content))

        # client 2 won
        pofile_content = open(self.dest_file, 'r').read()
        self.assertTrue('Hello, world, from client two!' in pofile_content)

        # Both clients show all strings, error messages are gone
        r = self.client.get(reverse('rosetta-home') + '?filter=translated')
        self.assertTrue('save-conflict' not in str(r.content))
        r2 = self.client2.get(reverse('rosetta-home') + '?filter=translated')
        self.assertTrue('save-conflict' not in str(r2.content))
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('save-conflict' not in str(r.content))
        r2 = self.client2.get(reverse('rosetta-home'))
        self.assertTrue('save-conflict' not in str(r2.content))

        # Both have client's two version
        self.assertTrue('Hello, world, from client two!' in str(r.content))
        self.assertTrue('Hello, world, from client two!' in str(r2.content))
        self.assertTrue('save-conflict' not in str(r2.content))
        self.assertTrue('save-conflict' not in str(r.content))

    def test_10_issue_79_num_entries(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue79.template')), self.dest_file)
        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))

        self.assertTrue('<td class="ch-messages r">1</td>' in str(r.content))
        self.assertTrue('<td class="ch-progress r">%s%%</td>' % str(floatformat(0.0, 2)) in str(r.content))
        self.assertTrue('<td class="ch-obsolete r">1</td>' in str(r.content))

    def test_11_issue_80_tab_indexes(self):
        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0,), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('tabindex="3"' in str(r.content))

    def test_12_issue_82_staff_user(self):
        settings.ROSETTA_REQUIRES_AUTH = True

        self.client3 = Client()
        self.client3.login(username='test_admin3', password='test_password')

        self.client3.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client3.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client3.get(reverse('rosetta-home'))
        self.assertTrue(not r.content)

        settings.ROSETTA_REQUIRES_AUTH = False

        self.client3.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client3.get(reverse('rosetta-language-selection', args=('xx', 0,), kwargs=dict()))
        r = self.client3.get(reverse('rosetta-home'))
        self.assertFalse(not r.content)

    def test_13_catalog_filters(self):
        settings.LANGUAGES = (('fr', 'French'), ('xx', 'Dummy Language'),)
        cache.delete('rosetta_django_paths')
        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))
        self.assertTrue(('contrib') not in str(r.content))

        self.client.get(reverse('rosetta-pick-file') + '?filter=django')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') not in str(r.content))

        if self.django_version_major >= 1 and self.django_version_minor >= 3:
            self.assertTrue(('contrib') in str(r.content))

        self.client.get(reverse('rosetta-pick-file') + '?filter=all')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))

        if self.django_version_major >= 1 and self.django_version_minor >= 3:
            self.assertTrue(('contrib') in str(r.content))

        self.client.get(reverse('rosetta-pick-file') + '?filter=project')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') not in str(r.content))
        if self.django_version_major >= 1 and self.django_version_minor >= 3:
            self.assertTrue(('contrib') not in str(r.content))

    def test_14_issue_99_context_and_comments(self):
        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('This is a text of the base template' in str(r.content))
        self.assertTrue('Context hint' in str(r.content))

    def test_15_issue_87_entry_changed_signal(self):
        # copy the template file
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.template')), self.dest_file)

        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0,), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))

        @receiver(entry_changed)
        def test_receiver(sender, **kwargs):
            self.test_old_msgstr = kwargs.get('old_msgstr')
            self.test_new_msgstr = sender.msgstr
            self.test_msg_id = sender.msgid
        self.assertTrue('m_e48f149a8b2e8baa81b816c0edf93890' in str(r.content))

        # post a translation
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world', _next='_next'))

        self.assertTrue(self.test_old_msgstr == '')
        self.assertTrue(self.test_new_msgstr == 'Hello, world')
        self.assertTrue(self.test_msg_id == 'String 2')

        del(self.test_old_msgstr, self.test_new_msgstr, self.test_msg_id)

    def test_16_issue_101_post_save_signal(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.template')), self.dest_file)
        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))

        @receiver(post_save)
        def test_receiver(sender, **kwargs):
            self.test_sig_lang = kwargs.get('language_code')

        self.assertTrue('m_e48f149a8b2e8baa81b816c0edf93890' in str(r.content))

        # post a translation
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world', _next='_next'))

        self.assertTrue(self.test_sig_lang == 'xx')
        del(self.test_sig_lang)

    def test_17_issue_103_post_save_signal_has_request(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.template')), self.dest_file)

        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))

        @receiver(post_save)
        def test_receiver(sender, **kwargs):
            self.test_16_has_request = 'request' in kwargs

        self.assertTrue('m_e48f149a8b2e8baa81b816c0edf93890' in str(r.content))

        # post a translation
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world', _next='_next'))

        self.assertTrue(self.test_16_has_request)
        del(self.test_16_has_request)
        # reset the original file

    def test_18_Test_Issue_gh24(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue24gh.template')), self.dest_file)

        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0, ), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))

        self.assertTrue('m_bb9d8fe6159187b9ea494c1b313d23d4' in str(r.content))

        # post a translation, it should have properly wrapped lines
        r = self.client.post(reverse('rosetta-home'), dict(m_bb9d8fe6159187b9ea494c1b313d23d4='Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim. Donec pede justo, fringilla vel, aliquet nec, vulputate eget, arcu. In enim justo, rhoncus ut, imperdiet a, venenatis vitae, justo. Nullam dictum felis eu pede mollis pretium.', _next='_next'))
        pofile_content = open(self.dest_file, 'r').read()
        self.assertTrue('"pede mollis pretium."' in pofile_content)

        # Again, with unwrapped lines
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue24gh.template')), self.dest_file)
        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0, ), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('m_bb9d8fe6159187b9ea494c1b313d23d4' in str(r.content))
        rosetta_settings.POFILE_WRAP_WIDTH = 0
        r = self.client.post(reverse('rosetta-home'), dict(m_bb9d8fe6159187b9ea494c1b313d23d4='Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim. Donec pede justo, fringilla vel, aliquet nec, vulputate eget, arcu. In enim justo, rhoncus ut, imperdiet a, venenatis vitae, justo. Nullam dictum felis eu pede mollis pretium.', _next='_next'))
        pofile_content = open(self.dest_file, 'r').read()
        self.assertTrue('felis eu pede mollis pretium."' in pofile_content)

    def test_19_Test_Issue_gh34(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue34gh.template')), self.dest_file)

        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0, ), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('m_ff7060c1a9aae9c42af4d54ac8551f67_1' in str(r.content))
        self.assertTrue('m_ff7060c1a9aae9c42af4d54ac8551f67_0' in str(r.content))
        self.assertTrue('m_09f7e02f1290be211da707a266f153b3' in str(r.content))

        # post a translation, it should have properly wrapped lines
        r = self.client.post(reverse('rosetta-home'), dict(
            m_ff7060c1a9aae9c42af4d54ac8551f67_0='Foo %s',
            m_ff7060c1a9aae9c42af4d54ac8551f67_1='Bar %s',
            m_09f7e02f1290be211da707a266f153b3='Salut', _next='_next'))
        pofile_content = open(self.dest_file, 'r').read()
        self.assertTrue('msgstr "Salut\\n"' in pofile_content)
        self.assertTrue('msgstr[0] ""\n"\\n"\n"Foo %s\\n"' in pofile_content)
        self.assertTrue('msgstr[1] ""\n"\\n"\n"Bar %s\\n"' in pofile_content)

    def test_20_Test_Issue_gh38(self):
        if self.django_version_minor >= 4 and self.django_version_major >= 1:
            self.assertTrue('django.contrib.sessions.middleware.SessionMiddleware' in settings.MIDDLEWARE_CLASSES)

            settings.SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

            # One: cache backend
            rosetta_settings.STORAGE_CLASS = 'rosetta.storage.CacheRosettaStorage'

            shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue38gh.template')), self.dest_file)

            self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
            self.client.get(reverse('rosetta-language-selection', args=('xx', 0, ), kwargs=dict()))
            r = self.client.get(reverse('rosetta-home'))
            self.assertFalse(len(str(self.client.cookies.get('sessionid'))) > 4096)
            self.assertTrue('m_9efd113f7919952523f06e0d88da9c54' in str(r.content))
            r = self.client.post(reverse('rosetta-home'), dict(
                m_9efd113f7919952523f06e0d88da9c54='Testing cookie length',
                _next='_next'
            ))
            pofile_content = open(self.dest_file, 'r').read()
            self.assertTrue('Testing cookie length' in pofile_content)

            self.client.get(reverse('rosetta-home') + '?filter=translated')
            r = self.client.get(reverse('rosetta-home'))
            self.assertTrue('Testing cookie length' in str(r.content))
            self.assertTrue('m_9f6c442c6d579707440ba9dada0fb373' in str(r.content))

            # Two, the cookie backend
            if self.django_version_minor < 6:
                rosetta_settings.STORAGE_CLASS = 'rosetta.storage.SessionRosettaStorage'

                shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue38gh.template')), self.dest_file)

                self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
                self.client.get(reverse('rosetta-language-selection', args=('xx', 0, ), kwargs=dict()))
                r = self.client.get(reverse('rosetta-home'))
                self.assertTrue(len(str(self.client.cookies.get('sessionid'))) > 4096)
                # boom: be a good browser, truncate the cookie
                self.client.cookies['sessionid'] = six.text_type(self.client.cookies.get('sessionid'))[:4096]
                r = self.client.get(reverse('rosetta-home'))

                self.assertFalse('m_9efd113f7919952523f06e0d88da9c54' in str(r.content))

    def test_21_concurrency_of_cache_backend(self):
        rosetta_settings.STORAGE_CLASS = 'rosetta.storage.CacheRosettaStorage'
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue38gh.template')), self.dest_file)

        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        self.client.get(reverse('rosetta-language-selection', args=('xx', 0, ), kwargs=dict()))

        self.client2.get(reverse('rosetta-pick-file') + '?filter=third-party')
        self.client2.get(reverse('rosetta-language-selection', args=('xx', 0, ), kwargs=dict()))

        self.assertTrue(self.client.session.get('rosetta_cache_storage_key_prefix') != self.client2.session.get('rosetta_cache_storage_key_prefix'))

    def test_22_Test_Issue_gh39(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.issue39gh.template')), self.dest_file)

        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))
        # We have distinct hashes, even though the msgid and msgstr are identical
        #print (r.content)
        self.assertTrue('m_4765f7de94996d3de5975fa797c3451f' in str(r.content))
        self.assertTrue('m_08e4e11e2243d764fc45a5a4fba5d0f2' in str(r.content))

    def test_23_save_header_data(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.template')), self.dest_file)

        unicode_user = User.objects.create_user('test_unicode', 'save_header_data@test.com', 'test_unicode')
        unicode_user.first_name = "aéaéaé aàaàaàa"
        unicode_user.last_name = "aâââ üüüü"
        unicode_user.is_superuser, unicode_user.is_staff = True, True
        unicode_user.save()

        self.client.login(username='test_unicode', password='test_unicode')

        # Load the template file
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home') + '?filter=untranslated')
        r = self.client.get(reverse('rosetta-home'))
        # make sure both strings are untranslated
        self.assertTrue('dummy language' in str(r.content))
        self.assertTrue('String 1' in str(r.content))
        self.assertTrue('String 2' in str(r.content))
        self.assertTrue('m_e48f149a8b2e8baa81b816c0edf93890' in str(r.content))

        # post a translation
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world', _next='_next'))
        # read the result
        f_ = open(self.dest_file, 'rb')
        content = six.text_type(f_.read())
        f_.close()
        #print (content)
        # make sure unicode data was properly converted to ascii
        self.assertTrue('Hello, world' in content)
        self.assertTrue('save_header_data@test.com' in content)
        self.assertTrue('aeaeae aaaaaaa aaaa uuuu' in content)

    def test_24_percent_transaltion(self):
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './django.po.template')), self.dest_file)

        # Load the template file
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home') + '?filter=untranslated')
        r = self.client.get(reverse('rosetta-home'))

        self.assertTrue('Progress: 0.00%' in str(r.content))
        r = self.client.post(reverse('rosetta-home'), dict(m_e48f149a8b2e8baa81b816c0edf93890='Hello, world', _next='_next'))
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('Progress: 25.00%' in str(r.content))

    def test_25_replace_access_control(self):
        # Test default access control allows access
        url = reverse('rosetta-home')
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        # Now replace access control, and check we get redirected
        settings.ROSETTA_ACCESS_CONTROL_FUNCTION = 'rosetta.tests.no_access'
        response = self.client.get(url)
        self.assertEqual(302, response.status_code)

        # Restore setting to default
        settings.ROSETTA_ACCESS_CONTROL_FUNCTION = None

    def test_26_urlconf_accept_dots_and_underscores(self):
        resolver_match = resolve("/rosetta/select/fr_FR.utf8/0/")
        self.assertEqual(resolver_match.url_name, "rosetta-language-selection")
        self.assertEqual(resolver_match.kwargs['langid'], 'fr_FR.utf8')

    def test_27_extended_urlconf_language_code_loads_file(self):
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=all')
        r = self.client.get(reverse('rosetta-language-selection', args=('fr_FR.utf8', 0), kwargs=dict()))
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('French (France), UTF8' in str(r.content))
        self.assertTrue('m_71a6479faf8712e37dd5755cd1d11804' in str(r.content))

    def test_28_issue_gh87(self):
        "make sure that rosetta_i18n_catalog_filter is passed into the context"
        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue('<li class="active"><a href="?filter=third-party">' in str(r.content))

    def test_29_unsupported_p3_django_16_storage(self):
        if self.django_version_minor >= 6 and self.django_version_major >= 1:
            self.assertTrue('django.contrib.sessions.middleware.SessionMiddleware' in settings.MIDDLEWARE_CLASSES)

            settings.SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
            rosetta_settings.STORAGE_CLASS = 'rosetta.storage.SessionRosettaStorage'

            try:
                self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
                self.fail()
            except ImproperlyConfigured:
                pass

    def test_30_pofile_names(self):
        POFILENAMES = rosetta_settings.POFILENAMES
        rosetta_settings.POFILENAMES = ('pr44.po', )

        os.unlink(self.dest_file)
        destfile = os.path.normpath(os.path.join(self.curdir, '../locale/xx/LC_MESSAGES/pr44.po'))
        shutil.copy(os.path.normpath(os.path.join(self.curdir, './pr44.po.template')), destfile)

        self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-home'))
        self.assertTrue('xx/LC_MESSAGES/pr44.po' in str(r.content))

        r = self.client.get(reverse('rosetta-language-selection', args=('xx', 0,), kwargs=dict()) + '?rosetta')
        r = self.client.get(reverse('rosetta-home'))

        self.assertTrue('dummy language' in str(r.content))

        os.unlink(destfile)
        rosetta_settings.POFILENAMES = POFILENAMES


    def test_31_pr_102__exclude_paths(self):
        ROSETTA_EXCLUDED_PATHS = rosetta_settings.ROSETTA_EXCLUDED_PATHS

        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))

        exclude_path = os.path.normpath(os.path.join(self.curdir, '../locale'))
        rosetta_settings.ROSETTA_EXCLUDED_PATHS = [exclude_path, ]

        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertFalse(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))

        rosetta_settings.ROSETTA_EXCLUDED_PATHS = ROSETTA_EXCLUDED_PATHS

    def test_32_pr_103__language_groups(self):
        ROSETTA_LANGUAGE_GROUPS = rosetta_settings.ROSETTA_LANGUAGE_GROUPS
        rosetta_settings.ROSETTA_LANGUAGE_GROUPS = False

        # Default behavior: non admins need to be in a translators group, they see
        # all catalogs
        translators = Group.objects.create(name='translators')
        translators_xx = Group.objects.create(name='translators-xx')

        user4 = User.objects.create_user('test_admin4', 'test@test3.com', 'test_password')
        user4.groups.add(translators)
        user4.is_superuser = False
        user4.is_staff = True
        user4.save()
        self.client.login(username='test_admin4', password='test_password')

        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))

        # Activate the option, user doesn't see the XX catalog
        rosetta_settings.ROSETTA_LANGUAGE_GROUPS = True

        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertFalse(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))

        # Now add them to the custom group
        user4.groups.add(translators_xx)

        r = self.client.get(reverse('rosetta-pick-file') + '?filter=third-party')
        r = self.client.get(reverse('rosetta-pick-file'))
        self.assertTrue(os.path.normpath('rosetta/locale/xx/LC_MESSAGES/django.po') in str(r.content))

        rosetta_settings.ROSETTA_LANGUAGE_GROUPS = ROSETTA_LANGUAGE_GROUPS


# Stubbed access control function
def no_access(user):
    return False

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('',
    url(r'^rosetta/',include('rosetta.urls')),
    url(r'^admin/$','rosetta.tests.views.dummy', name='dummy-login')
)

########NEW FILE########
__FILENAME__ = views
def dummy(request):
    pass


########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('rosetta.views',
    url(r'^$', 'home', name='rosetta-home'),
    url(r'^pick/$', 'list_languages', name='rosetta-pick-file'),
    url(r'^download/$', 'download_file', name='rosetta-download-file'),
    url(r'^select/(?P<langid>[\w\-_\.]+)/(?P<idx>\d+)/$', 'lang_sel', name='rosetta-language-selection'),
    url(r'^translate/$', 'translate_text', name='translate_text'),
)

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
"""
    test

    Test the translator

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest
from rosetta.utils.microsofttranslator import Translator, TranslateApiException

client_id = "translaterpythonapi"
client_secret = "FLghnwW4LJmNgEG+EZkL8uE+wb7+6tkOS8eejHg3AaI="


class TestTranslator(unittest.TestCase):

    def test_translate(self):
        client = Translator(client_id, client_secret, debug=False)
        self.assertEqual(client.translate("hello", "pt"), u'Ol\xe1')

    def test_invalid_client_id(self):
        client = Translator("foo", "bar")
        with self.assertRaises(TranslateApiException):
            client.translate("hello", "pt")


def test_all():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestTranslator))
    return suite


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.encoding import iri_to_uri
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache

from rosetta.utils.microsofttranslator import Translator, TranslateApiException

from rosetta.conf import settings as rosetta_settings
from polib import pofile
from rosetta.poutil import find_pos, pagination_range, timestamp_with_timezone
from rosetta.signals import entry_changed, post_save
from rosetta.storage import get_storage
from rosetta.access import can_translate, can_translate_language

import json
import re
import rosetta
import unicodedata
import hashlib
import os
import six


@never_cache
@user_passes_test(lambda user: can_translate(user), settings.LOGIN_URL)
def home(request):
    """
    Displays a list of messages to be translated
    """

    def fix_nls(in_, out_):
        """Fixes submitted translations by filtering carriage returns and pairing
        newlines at the begging and end of the translated string with the original
        """
        if 0 == len(in_) or 0 == len(out_):
            return out_

        if "\r" in out_ and "\r" not in in_:
            out_ = out_.replace("\r", '')

        if "\n" == in_[0] and "\n" != out_[0]:
            out_ = "\n" + out_
        elif "\n" != in_[0] and "\n" == out_[0]:
            out_ = out_.lstrip()
        if "\n" == in_[-1] and "\n" != out_[-1]:
            out_ = out_ + "\n"
        elif "\n" != in_[-1] and "\n" == out_[-1]:
            out_ = out_.rstrip()
        return out_

    storage = get_storage(request)
    query = ''
    if storage.has('rosetta_i18n_fn'):
        rosetta_i18n_fn = storage.get('rosetta_i18n_fn')
        rosetta_i18n_app = get_app_name(rosetta_i18n_fn)
        rosetta_i18n_lang_code = storage.get('rosetta_i18n_lang_code')
        rosetta_i18n_lang_bidi = rosetta_i18n_lang_code.split('-')[0] in settings.LANGUAGES_BIDI
        rosetta_i18n_write = storage.get('rosetta_i18n_write', True)
        if rosetta_i18n_write:
            rosetta_i18n_pofile = pofile(rosetta_i18n_fn, wrapwidth=rosetta_settings.POFILE_WRAP_WIDTH)
            for entry in rosetta_i18n_pofile:
                entry.md5hash = hashlib.md5(
                    (six.text_type(entry.msgid) +
                    six.text_type(entry.msgstr) +
                    six.text_type(entry.msgctxt or "")).encode('utf8')
                ).hexdigest()

        else:
            rosetta_i18n_pofile = storage.get('rosetta_i18n_pofile')

        if 'filter' in request.GET:
            if request.GET.get('filter') in ('untranslated', 'translated', 'fuzzy', 'all'):
                filter_ = request.GET.get('filter')
                storage.set('rosetta_i18n_filter', filter_)
                return HttpResponseRedirect(reverse('rosetta-home'))

        rosetta_i18n_filter = storage.get('rosetta_i18n_filter', 'all')

        if '_next' in request.POST:
            rx = re.compile(r'^m_([0-9a-f]+)')
            rx_plural = re.compile(r'^m_([0-9a-f]+)_([0-9]+)')
            file_change = False
            for key, value in request.POST.items():
                md5hash = None
                plural_id = None

                if rx_plural.match(key):
                    md5hash = str(rx_plural.match(key).groups()[0])
                    # polib parses .po files into unicode strings, but
                    # doesn't bother to convert plural indexes to int,
                    # so we need unicode here.
                    plural_id = six.text_type(rx_plural.match(key).groups()[1])

                    # Above no longer true as of Polib 1.0.4
                    if plural_id and plural_id.isdigit():
                        plural_id = int(plural_id)

                elif rx.match(key):
                    md5hash = str(rx.match(key).groups()[0])

                if md5hash is not None:
                    entry = rosetta_i18n_pofile.find(md5hash, 'md5hash')
                    # If someone did a makemessage, some entries might
                    # have been removed, so we need to check.
                    if entry:
                        old_msgstr = entry.msgstr
                        if plural_id is not None:
                            #plural_string = fix_nls(entry.msgstr_plural[plural_id], value)
                            plural_string = fix_nls(entry.msgid_plural, value)
                            entry.msgstr_plural[plural_id] = plural_string
                        else:
                            entry.msgstr = fix_nls(entry.msgid, value)

                        is_fuzzy = bool(request.POST.get('f_%s' % md5hash, False))
                        old_fuzzy = 'fuzzy' in entry.flags

                        if old_fuzzy and not is_fuzzy:
                            entry.flags.remove('fuzzy')
                        elif not old_fuzzy and is_fuzzy:
                            entry.flags.append('fuzzy')

                        file_change = True

                        if old_msgstr != value or old_fuzzy != is_fuzzy:
                            entry_changed.send(sender=entry,
                                               user=request.user,
                                               old_msgstr=old_msgstr,
                                               old_fuzzy=old_fuzzy,
                                               pofile=rosetta_i18n_fn,
                                               language_code=rosetta_i18n_lang_code,
                                               )

                    else:
                        storage.set('rosetta_last_save_error', True)

            if file_change and rosetta_i18n_write:
                try:
                    # Provide defaults in case authorization is not required.
                    request.user.first_name = getattr(request.user, 'first_name', 'Anonymous')
                    request.user.last_name = getattr(request.user, 'last_name', 'User')
                    request.user.email = getattr(request.user, 'email', 'anonymous@user.tld')

                    rosetta_i18n_pofile.metadata['Last-Translator'] = unicodedata.normalize('NFKD', u"%s %s <%s>" % (request.user.first_name, request.user.last_name, request.user.email)).encode('ascii', 'ignore')
                    rosetta_i18n_pofile.metadata['X-Translated-Using'] = u"django-rosetta %s" % rosetta.get_version(False)
                    rosetta_i18n_pofile.metadata['PO-Revision-Date'] = timestamp_with_timezone()
                except UnicodeDecodeError:
                    pass

                try:
                    rosetta_i18n_pofile.save()
                    po_filepath, ext = os.path.splitext(rosetta_i18n_fn)
                    save_as_mo_filepath = po_filepath + '.mo'
                    rosetta_i18n_pofile.save_as_mofile(save_as_mo_filepath)

                    post_save.send(sender=None, language_code=rosetta_i18n_lang_code, request=request)
                    # Try auto-reloading via the WSGI daemon mode reload mechanism
                    if rosetta_settings.WSGI_AUTO_RELOAD and \
                        'mod_wsgi.process_group' in request.environ and \
                        request.environ.get('mod_wsgi.process_group', None) and \
                        'SCRIPT_FILENAME' in request.environ and \
                        int(request.environ.get('mod_wsgi.script_reloading', '0')):
                            try:
                                os.utime(request.environ.get('SCRIPT_FILENAME'), None)
                            except OSError:
                                pass
                    # Try auto-reloading via uwsgi daemon reload mechanism
                    if rosetta_settings.UWSGI_AUTO_RELOAD:
                        try:
                            import uwsgi
                            # pretty easy right?
                            uwsgi.reload()
                        except:
                            # we may not be running under uwsgi :P
                            pass

                except:
                    storage.set('rosetta_i18n_write', False)
                storage.set('rosetta_i18n_pofile', rosetta_i18n_pofile)

                # Retain query arguments
                query_arg = '?_next=1'
                if 'query' in request.GET or 'query' in request.POST:
                    query_arg += '&query=%s' % request.REQUEST.get('query')
                if 'page' in request.GET:
                    query_arg += '&page=%d&_next=1' % int(request.GET.get('page'))
                return HttpResponseRedirect(reverse('rosetta-home') + iri_to_uri(query_arg))
        rosetta_i18n_lang_code = storage.get('rosetta_i18n_lang_code')

        if 'query' in request.REQUEST and request.REQUEST.get('query', '').strip():
            query = request.REQUEST.get('query').strip()
            rx = re.compile(re.escape(query), re.IGNORECASE)
            paginator = Paginator([e for e in rosetta_i18n_pofile if not e.obsolete and rx.search(six.text_type(e.msgstr) + six.text_type(e.msgid) + u''.join([o[0] for o in e.occurrences]))], rosetta_settings.MESSAGES_PER_PAGE)
        else:
            if rosetta_i18n_filter == 'untranslated':
                paginator = Paginator(rosetta_i18n_pofile.untranslated_entries(), rosetta_settings.MESSAGES_PER_PAGE)
            elif rosetta_i18n_filter == 'translated':
                paginator = Paginator(rosetta_i18n_pofile.translated_entries(), rosetta_settings.MESSAGES_PER_PAGE)
            elif rosetta_i18n_filter == 'fuzzy':
                paginator = Paginator([e for e in rosetta_i18n_pofile.fuzzy_entries() if not e.obsolete], rosetta_settings.MESSAGES_PER_PAGE)
            else:
                paginator = Paginator([e for e in rosetta_i18n_pofile if not e.obsolete], rosetta_settings.MESSAGES_PER_PAGE)

        if 'page' in request.GET and int(request.GET.get('page')) <= paginator.num_pages and int(request.GET.get('page')) > 0:
            page = int(request.GET.get('page'))
        else:
            page = 1

        if '_next' in request.GET or '_next' in request.POST:
            page += 1
            if page > paginator.num_pages:
                page = 1
            query_arg = '?page=%d' % page
            return HttpResponseRedirect(reverse('rosetta-home') + iri_to_uri(query_arg))

        rosetta_messages = paginator.page(page).object_list
        main_language = None
        if rosetta_settings.MAIN_LANGUAGE and rosetta_settings.MAIN_LANGUAGE != rosetta_i18n_lang_code:
            for language in settings.LANGUAGES:
                if language[0] == rosetta_settings.MAIN_LANGUAGE:
                    main_language = _(language[1])
                    break

            fl = ("/%s/" % rosetta_settings.MAIN_LANGUAGE).join(rosetta_i18n_fn.split("/%s/" % rosetta_i18n_lang_code))
            po = pofile(fl)

            for message in rosetta_messages:
                message.main_lang = po.find(message.msgid).msgstr

        needs_pagination = paginator.num_pages > 1
        if needs_pagination:
            if paginator.num_pages >= 10:
                page_range = pagination_range(1, paginator.num_pages, page)
            else:
                page_range = range(1, 1 + paginator.num_pages)
        try:
            ADMIN_MEDIA_PREFIX = settings.ADMIN_MEDIA_PREFIX
            ADMIN_IMAGE_DIR = ADMIN_MEDIA_PREFIX + 'img/admin/'
        except AttributeError:
            ADMIN_MEDIA_PREFIX = settings.STATIC_URL + 'admin/'
            ADMIN_IMAGE_DIR = ADMIN_MEDIA_PREFIX + 'img/'

        if storage.has('rosetta_last_save_error'):
            storage.delete('rosetta_last_save_error')
            rosetta_last_save_error = True
        else:
            rosetta_last_save_error = False

        return render_to_response('rosetta/pofile.html', dict(
            version=rosetta.get_version(True),
            ADMIN_MEDIA_PREFIX=ADMIN_MEDIA_PREFIX,
            ADMIN_IMAGE_DIR=ADMIN_IMAGE_DIR,
            rosetta_settings=rosetta_settings,
            rosetta_i18n_lang_name=_(storage.get('rosetta_i18n_lang_name')),
            rosetta_i18n_lang_code=rosetta_i18n_lang_code,
            rosetta_i18n_lang_bidi=rosetta_i18n_lang_bidi,
            rosetta_last_save_error=rosetta_last_save_error,
            rosetta_i18n_filter=rosetta_i18n_filter,
            rosetta_i18n_write=rosetta_i18n_write,
            rosetta_messages=rosetta_messages,
            page_range=needs_pagination and page_range,
            needs_pagination=needs_pagination,
            main_language=main_language,
            rosetta_i18n_app=rosetta_i18n_app,
            page=page,
            query=query,
            paginator=paginator,
            rosetta_i18n_pofile=rosetta_i18n_pofile
        ), context_instance=RequestContext(request))
    else:
        return list_languages(request, do_session_warn=True)


@never_cache
@user_passes_test(lambda user: can_translate(user), settings.LOGIN_URL)
def download_file(request):
    import zipfile
    storage = get_storage(request)
    # original filename
    rosetta_i18n_fn = storage.get('rosetta_i18n_fn', None)
    # in-session modified catalog
    rosetta_i18n_pofile = storage.get('rosetta_i18n_pofile', None)
    # language code
    rosetta_i18n_lang_code = storage.get('rosetta_i18n_lang_code', None)

    if not rosetta_i18n_lang_code or not rosetta_i18n_pofile or not rosetta_i18n_fn:
        return HttpResponseRedirect(reverse('rosetta-home'))
    try:
        if len(rosetta_i18n_fn.split('/')) >= 5:
            offered_fn = '_'.join(rosetta_i18n_fn.split('/')[-5:])
        else:
            offered_fn = rosetta_i18n_fn.split('/')[-1]
        po_fn = str(rosetta_i18n_fn.split('/')[-1])
        mo_fn = str(po_fn.replace('.po', '.mo'))  # not so smart, huh
        zipdata = six.BytesIO()
        zipf = zipfile.ZipFile(zipdata, mode="w")
        zipf.writestr(po_fn, six.text_type(rosetta_i18n_pofile).encode("utf8"))
        zipf.writestr(mo_fn, rosetta_i18n_pofile.to_binary())
        zipf.close()
        zipdata.seek(0)

        response = HttpResponse(zipdata.read())
        response['Content-Disposition'] = 'attachment; filename=%s.%s.zip' % (offered_fn, rosetta_i18n_lang_code)
        response['Content-Type'] = 'application/x-zip'
        return response

    except Exception:
        return HttpResponseRedirect(reverse('rosetta-home'))


@never_cache
@user_passes_test(lambda user: can_translate(user), settings.LOGIN_URL)
def list_languages(request, do_session_warn=False):
    """
    Lists the languages for the current project, the gettext catalog files
    that can be translated and their translation progress
    """
    storage = get_storage(request)
    languages = []

    if 'filter' in request.GET:
        if request.GET.get('filter') in ('project', 'third-party', 'django', 'all'):
            filter_ = request.GET.get('filter')
            storage.set('rosetta_i18n_catalog_filter', filter_)
            return HttpResponseRedirect(reverse('rosetta-pick-file'))

    rosetta_i18n_catalog_filter = storage.get('rosetta_i18n_catalog_filter', 'project')

    third_party_apps = rosetta_i18n_catalog_filter in ('all', 'third-party')
    django_apps = rosetta_i18n_catalog_filter in ('all', 'django')
    project_apps = rosetta_i18n_catalog_filter in ('all', 'project')

    has_pos = False
    for language in settings.LANGUAGES:
        if not can_translate_language(request.user, language[0]):
            continue
        
        pos = find_pos(language[0], project_apps=project_apps, django_apps=django_apps, third_party_apps=third_party_apps)
        has_pos = has_pos or len(pos)
        languages.append(
            (language[0],
            _(language[1]),
            sorted([(get_app_name(l), os.path.realpath(l), pofile(l)) for l in pos], key=lambda app: app[0]),
            )
        )
    try:
        ADMIN_MEDIA_PREFIX = settings.ADMIN_MEDIA_PREFIX
    except AttributeError:
        ADMIN_MEDIA_PREFIX = settings.STATIC_URL + 'admin/'
    do_session_warn = do_session_warn and 'SessionRosettaStorage' in rosetta_settings.STORAGE_CLASS and 'signed_cookies' in settings.SESSION_ENGINE

    return render_to_response('rosetta/languages.html', dict(
        version=rosetta.get_version(True),
        ADMIN_MEDIA_PREFIX=ADMIN_MEDIA_PREFIX,
        do_session_warn=do_session_warn,
        languages=languages,
        has_pos=has_pos,
        rosetta_i18n_catalog_filter=rosetta_i18n_catalog_filter
    ), context_instance=RequestContext(request))


def get_app_name(path):
    app = path.split("/locale")[0].split("/")[-1]
    return app


@never_cache
@user_passes_test(lambda user: can_translate(user), settings.LOGIN_URL)
def lang_sel(request, langid, idx):
    """
    Selects a file to be translated
    """
    storage = get_storage(request)
    if langid not in [l[0] for l in settings.LANGUAGES] or not can_translate_language(request.user, langid):
        raise Http404
    else:

        rosetta_i18n_catalog_filter = storage.get('rosetta_i18n_catalog_filter', 'project')

        third_party_apps = rosetta_i18n_catalog_filter in ('all', 'third-party')
        django_apps = rosetta_i18n_catalog_filter in ('all', 'django')
        project_apps = rosetta_i18n_catalog_filter in ('all', 'project')
        file_ = sorted(find_pos(langid, project_apps=project_apps, django_apps=django_apps, third_party_apps=third_party_apps), key=get_app_name)[int(idx)]

        storage.set('rosetta_i18n_lang_code', langid)
        storage.set('rosetta_i18n_lang_name', six.text_type([l[1] for l in settings.LANGUAGES if l[0] == langid][0]))
        storage.set('rosetta_i18n_fn', file_)
        po = pofile(file_)
        for entry in po:
            entry.md5hash = hashlib.new('md5',
                (six.text_type(entry.msgid) +
                six.text_type(entry.msgstr) +
                six.text_type(entry.msgctxt or "")).encode('utf8')
            ).hexdigest()

        storage.set('rosetta_i18n_pofile', po)
        try:
            os.utime(file_, None)
            storage.set('rosetta_i18n_write', True)
        except OSError:
            storage.set('rosetta_i18n_write', False)

        return HttpResponseRedirect(reverse('rosetta-home'))


@user_passes_test(lambda user: can_translate(user), settings.LOGIN_URL)
def translate_text(request):
    language_from = request.GET.get('from', None)
    language_to = request.GET.get('to', None)
    text = request.GET.get('text', None)

    if language_from == language_to:
        data = {'success': True, 'translation': text}
    else:
        # run the translation:
        AZURE_CLIENT_ID = getattr(settings, 'AZURE_CLIENT_ID', None)
        AZURE_CLIENT_SECRET = getattr(settings, 'AZURE_CLIENT_SECRET', None)

        translator = Translator(AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)

        try:
            translated_text = translator.translate(text, language_to)
            data = {'success': True, 'translation': translated_text}
        except TranslateApiException as e:
            data = {'success': False, 'error': "Translation API Exception: {0}".format(e.message)}

    return HttpResponse(json.dumps(data), mimetype='application/json')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
import os
try:
    from django.core.management import execute_manager
    OLD_DJANGO = True
except ImportError:
    from django.core.management import execute_from_command_line
    OLD_DJANGO = False

if OLD_DJANGO:
    try:
        import settings  # Assumed to be in the same directory.
    except ImportError:
        sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
        sys.exit(1)

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASEDIR)

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "testproject.settings"
    if OLD_DJANGO:
        execute_manager(settings)
    else:
        execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
#from __future__ import unicode_literals
import django
import os
import sys


SITE_ID = 1

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

PYTHON_VERSION = '%s.%s' % sys.version_info[:2]
DJANGO_VERSION = django.get_version()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_PATH, 'rosetta.db')
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'KEY_PREFIX': 'ROSETTA_TEST'
    }
}


#CACHES = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}

TEST_DATABASE_CHARSET = "utf8"
TEST_DATABASE_COLLATION = "utf8_general_ci"

DATABASE_SUPPORTS_TRANSACTIONS = True

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    'rosetta',
]
LANGUAGE_CODE = "en"

LANGUAGES = (
    ('ja', u'日本語'),
    ('xx', u'XXXXX'),
    ('fr', u'French'),
    ('fr_FR.utf8', u'French (France), UTF8'),
)
LOCALE_PATHS = [
    os.path.join(PROJECT_PATH, 'locale'),
]

SOUTH_TESTS_MIGRATE = False

FIXTURE_DIRS = (
    os.path.join(PROJECT_PATH, 'fixtures'),
)
STATIC_URL = '/static/'
ROOT_URLCONF = 'testproject.urls'

DEBUG = True
TEMPLATE_DEBUG = True

STATIC_URL = '/static/'
#SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
#ROSETTA_STORAGE_CLASS = 'rosetta.storage.SessionRosettaStorage'
ROSETTA_STORAGE_CLASS = 'rosetta.storage.CacheRosettaStorage'
SECRET_KEY = 'empty'

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, include, url

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproject.views.home', name='home'),
    # url(r'^testproject/', include('testproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^rosetta/', include('rosetta.urls'))
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
