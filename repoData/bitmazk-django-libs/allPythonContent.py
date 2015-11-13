__FILENAME__ = admin
"""Additions for the django admin."""
from django.utils.translation import ugettext_lazy as _


class MultilingualPublishMixin(object):
    """Mixin to provide common methods for multilingual object admins."""

    def is_published(self, obj):
        languages = ''
        for trans in obj.translations:
            if trans.is_published:
                if languages == '':
                    languages = trans.language
                else:
                    languages += ', {0}'.format(trans.language)
        if languages == '':
            return _('Not published')
        return languages
    is_published.short_description = _('Is published')

########NEW FILE########
__FILENAME__ = compress_filters
"""Custom filters for the ``compressor`` app."""
from django.conf import settings

from compressor.filters.css_default import CssAbsoluteFilter
from compressor.utils import staticfiles


class S3CssAbsoluteFilter(CssAbsoluteFilter):
    """
    This CSS filter was built to use django-compressor in combination with a
    Amazon S3 storage. It will make sure to provide the right URLs, whether
    you're in DEBUG mode or not.

    Make sure to add the ``FULL_DOMAIN`` setting. This is your base url, e.g.
    'https://www.example.com'.

    """
    def __init__(self, *args, **kwargs):
        super(S3CssAbsoluteFilter, self).__init__(*args, **kwargs)
        self.url = '%s%s' % (settings.FULL_DOMAIN, settings.STATIC_URL)
        self.url_path = self.url

    def find(self, basename):
        # The line below is the original line.  I removed settings.DEBUG.
        # if settings.DEBUG and basename and staticfiles.finders:
        if basename and staticfiles.finders:
            return staticfiles.finders.find(basename)

########NEW FILE########
__FILENAME__ = constants
"""Commonly used constants."""
from pytz import common_timezones

TIMEZONE_CHOICES = [(tz, tz) for tz in common_timezones]

########NEW FILE########
__FILENAME__ = context_processors
"""Useful context  processors for your projects."""
from django.conf import settings


def analytics(request):
    """Adds the setting ANALYTICS_TRACKING_ID to the template context."""
    return {
        'ANALYTICS_TRACKING_ID': getattr(
            settings, 'ANALYTICS_TRACKING_ID', 'UA-XXXXXXX-XX'),
    }

########NEW FILE########
__FILENAME__ = decorators
"""Useful decorators for Django projects."""
from functools import wraps
import re

from django.http import Http404
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from lockfile import FileLock, AlreadyLocked, LockTimeout


def lockfile(lockfile_name, lock_wait_timeout=-1):
    """
    Only runs the method if the lockfile is not acquired.

    You should create a setting ``LOCKFILE_PATH`` which points to
    ``/home/username/tmp/``.

    In your management command, use it like so::

        LOCKFILE = os.path.join(
            settings.LOCKFILE_FOLDER, 'command_name')

        class Command(NoArgsCommand):
            @lockfile(LOCKFILE)
            def handle_noargs(self, **options):
                # your command here

    :lockfile_name: A unique name for a lockfile that belongs to the wrapped
      method.
    :lock_wait_timeout: Seconds to wait if lockfile is acquired. If ``-1`` we
      will not wait and just quit.

    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock = FileLock(lockfile_name)
            try:
                lock.acquire(lock_wait_timeout)
            except AlreadyLocked:
                return
            except LockTimeout:
                return
            try:
                result = func(*args, **kwargs)
            finally:
                lock.release()
            return result

        return wrapper
    return decorator


def get_username(identifier):
    """Checks if a string is a email adress or not."""
    pattern = re.compile('.+@\w+\..+')
    if pattern.match(identifier):
        try:
            user = User.objects.get(email=identifier)
        except:
            raise Http404
        else:
            return user.username
    else:
        return identifier


def http_auth(func):
    @wraps(func)
    def _decorator(request, *args, **kwargs):
        """Decorator to handle http authorizations."""
        if request.user.is_authenticated():
            return func(request, *args, **kwargs)
        if 'HTTP_AUTHORIZATION' in request.META.keys():
            authmeth, auth = request.META['HTTP_AUTHORIZATION'].split(' ', 1)
            if authmeth.lower() == 'basic':
                auth = auth.strip().decode('base64')
                identifier, password = auth.split(':', 1)
                username = get_username(identifier)
                user = authenticate(username=username, password=password)
                if user:
                    login(request, user)
                    return func(request, *args, **kwargs)
        raise Http404
    return _decorator

########NEW FILE########
__FILENAME__ = default_settings
"""
Central definition of all settings used in django-libs.

Devs and contributors, please move or add them here. That will make it easier
to maintain all the default values in the future.

"""
from django.conf import settings


# Default setting for the ``test_email_backend.WhitelistEmailBackend``
# expects tuple of regex. e.g. [r'.*@example.com']
EMAIL_BACKEND_WHITELIST = getattr(settings, 'EMAIL_BACKEND_WHITELIST', [])

# Default setting for the ``test_email_backend.WhitelistEmailBackend``
# if True, it reroutes all the emails, that don't match the
# EMAIL_BACKEND_WHITELIST setting to the emails specified in the
# TEST_EMAIL_BACKEND_RECIPIENTS setting.
EMAIL_BACKEND_REROUTE_BLACKLIST = getattr(settings,
                                          'EMAIL_BACKEND_REROUTE_BLACKLIST',
                                          False)

# Default setting for the ``test_email_backend.EmailBackend``
# format: (('This Name', 'name@example.com'), )       - like the ADMINS setting
TEST_EMAIL_BACKEND_RECIPIENTS = getattr(
    settings, 'TEST_EMAIL_BACKEND_RECIPIENTS', [])

########NEW FILE########
__FILENAME__ = format_utils
"""
Utility functions to get language specific formats.

These functions are taken from the original django implementation and updated
to fit our needs.

The original code can be found here:
https://github.com/django/django/blob/master/django/utils/formats.py

"""
from django.conf import settings
# when working with django versions prior to 1.5, we need to use smart_str
# instead of force_str
try:
    from django.utils.encoding import force_str as str_encode
except ImportError:
    from django.utils.encoding import smart_str as str_encode

from django.utils.importlib import import_module
from django.utils.translation import (
    check_for_language,
    get_language,
    to_locale
)

CUSTOM_FORMAT_MODULE_PATHS = getattr(settings, 'CUSTOM_FORMAT_MODULE_PATHS',
                                     ['localized_names.formats'])

# format_cache is a mapping from (format_type, lang) to the format string.
# By using the cache, it is possible to avoid running get_format_modules
# repeatedly.
_format_cache = {}
_format_modules_cache = {}

ISO_INPUT_FORMATS = {
    'DATE_INPUT_FORMATS': ('%Y-%m-%d',),
    'TIME_INPUT_FORMATS': ('%H:%M:%S', '%H:%M:%S.%f', '%H:%M'),
    'DATETIME_INPUT_FORMATS': (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d'
    ),
}


def iter_format_modules(lang):
    """
    Does the heavy lifting of finding format modules.

    """
    if check_for_language(lang):
        format_locations = []
        for path in CUSTOM_FORMAT_MODULE_PATHS:
            format_locations.append(path + '.%s')
        format_locations.append('django.conf.locale.%s')
        locale = to_locale(lang)
        locales = [locale]
        if '_' in locale:
            locales.append(locale.split('_')[0])
        for location in format_locations:
            for loc in locales:
                try:
                    yield import_module('.formats', location % loc)
                except ImportError:
                    pass


def get_format_modules(lang=None, reverse=False):
    """
    Returns a list of the format modules found

    """
    if lang is None:
        lang = get_language()
    modules = _format_modules_cache.setdefault(lang, list(
        iter_format_modules(lang)))
    if reverse:
        return list(reversed(modules))
    return modules


def get_format(format_type, lang=None, use_l10n=None):
    """
    For a specific format type, returns the format for the current
    language (locale), defaults to the format in the settings.
    format_type is the name of the format, e.g. 'DATE_FORMAT'

    If use_l10n is provided and is not None, that will force the value to
    be localized (or not), overriding the value of settings.USE_L10N.

    """
    format_type = str_encode(format_type)
    if use_l10n or (use_l10n is None and settings.USE_L10N):
        if lang is None:
            lang = get_language()
        cache_key = (format_type, lang)
        try:
            cached = _format_cache[cache_key]
            if cached is not None:
                return cached
            else:
                # Return the general setting by default
                return getattr(settings, format_type)
        except KeyError:
            for module in get_format_modules(lang):
                try:
                    val = getattr(module, format_type)
                    for iso_input in ISO_INPUT_FORMATS.get(format_type, ()):
                        if iso_input not in val:
                            if isinstance(val, tuple):
                                val = list(val)
                            val.append(iso_input)
                    _format_cache[cache_key] = val
                    return val
                except AttributeError:
                    pass
            _format_cache[cache_key] = None
    return getattr(settings, format_type)

########NEW FILE########
__FILENAME__ = forms
"""Forms of the ``django_libs`` app."""
from django.utils.html import strip_tags


class PlaceholderForm(object):
    """Form to add the field's label as a placeholder attribute."""
    def __init__(self, *args, **kwargs):
        super(PlaceholderForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['placeholder'] = self.fields[
                field_name].label


class StripTagsFormMixin(object):
    """
    Mixin that allows to strip html tags entered to some fields.

    Usage:

    1. In your form, inherit from this mixin
    2. In your form, add STRIP_TAGS_FIELDS = ['field_name1', 'field_name2', ]
       to the form class
    3. In your form's `__init__` call `self.strip_tags()` after your `super`
       call.

    """
    def strip_tags(self):
        form_data = self.data.copy()
        for field_name in self.STRIP_TAGS_FIELDS:
            if self.prefix:
                field_name = '{0}-{1}'.format(self.prefix, field_name)
            if field_name in form_data:
                field_data = form_data[field_name]
                field_data = strip_tags(field_data)
                form_data[field_name] = field_data
        self.data = form_data

########NEW FILE########
__FILENAME__ = loaders
"""Utility functions for loading classes from strings."""
from django.conf import settings


def load_member(fqn):
    """Loads and returns a class for a given fully qualified name."""
    modulename, member_name = split_fqn(fqn)
    module = __import__(modulename, globals(), locals(), member_name)
    return getattr(module, member_name)


def load_member_from_setting(setting_name, settings_module=None):
    settings_to_use = settings_module or settings
    setting_value = getattr(settings_to_use, setting_name)
    return load_member(setting_value)


def split_fqn(fqn):
    """
    Returns the left and right part of the import.

    ``fqn`` can be either a string of the form ``appname.modulename.ClassName``
    or a function that returns such a string.

    """
    if hasattr(fqn, '__call__'):
        fqn_string = fqn()
    else:
        fqn_string = fqn
    return fqn_string.rsplit('.', 1)

########NEW FILE########
__FILENAME__ = middleware
"""Custom middlewares for the project."""
from django.http import HttpResponseRedirect

try:
    from django.middleware.common import _is_ignorable_404
except ImportError:
    _is_ignorable_404 = None


class AjaxRedirectMiddleware(object):
    """
    Middleware that sets a made up status code when a redirect has happened.

    This is necessary for AJAX calls with jQuery. It seems to set the status
    code to 200 when in reality it was a 301 or 302.

    If you want to override this behaviour for some of your ajax calls, you
    can add `ajax_redirect_passthrough` as a hidden field or as a GET
    parameter.

    """
    def process_response(self, request, response):
        if request.is_ajax():
            if (request.GET.get('ajax_redirect_passthrough')
                    or request.POST.get('ajax_redirect_passthrough')):
                return response
            if type(response) == HttpResponseRedirect:
                response.status_code = 278
        return response


class ErrorMiddleware(object):
    """Alter HttpRequest objects on Error."""

    def process_exception(self, request, exception):
        """
        Add user details.
        """
        if request.user and hasattr(request.user, 'email'):
            request.META['USER'] = request.user.email


if _is_ignorable_404:
    from .middleware_1_5 import *  # NOQA
else:
    from .middleware_1_6 import *  # NOQA

########NEW FILE########
__FILENAME__ = middleware_1_5
"""Custom middleware for Django 1.5 projects."""
import hashlib

from django import http
from django.conf import settings
from django.core.mail import mail_managers
from django.middleware.common import (
    CommonMiddleware,
    _is_ignorable_404,
    _is_internal_request,
)


class CustomCommonMiddleware(CommonMiddleware):
    """Adds the current user to the 405 email."""
    def process_response(self, request, response):
        "Send broken link emails and calculate the Etag, if needed."
        if response.status_code == 404:
            if settings.SEND_BROKEN_LINK_EMAILS and not settings.DEBUG:
                # If the referrer was from an internal link or a
                # non-search-engine site, send a note to the managers.
                domain = request.get_host()
                referer = request.META.get('HTTP_REFERER')
                is_internal = _is_internal_request(domain, referer)
                path = request.get_full_path()
                if (referer
                        and not _is_ignorable_404(path)
                        and (is_internal or '?' not in referer)):
                    ua = request.META.get('HTTP_USER_AGENT', '<none>')
                    ip = request.META.get('REMOTE_ADDR', '<none>')

                    user = None
                    if request.user and hasattr(request.user, 'email'):
                        user = request.user.email

                    content = (
                        "Referrer: %s\n"
                        "Requested URL: %s\n"
                        "User agent: %s\n"
                        "IP address: %s\n"
                        "User: %s\n"
                    ) % (referer, request.get_full_path(), ua, ip, user)
                    internal = is_internal and 'INTERNAL ' or ''
                    mail_managers(
                        "Broken %slink on %s" % (internal, domain),
                        content,
                        fail_silently=True,
                    )
                return response

        # Use ETags, if requested.
        if settings.USE_ETAGS:
            if response.has_header('ETag'):
                etag = response['ETag']
            elif response.streaming:
                etag = None
            else:
                etag = '"%s"' % hashlib.md5(response.content).hexdigest()
            if etag is not None:
                if (200 <= response.status_code < 300
                        and request.META.get('HTTP_IF_NONE_MATCH') == etag):
                    cookies = response.cookies
                    response = http.HttpResponseNotModified()
                    response.cookies = cookies
                else:
                    response['ETag'] = etag

        return response

########NEW FILE########
__FILENAME__ = middleware_1_6
"""Custom middleware for Django 1.6 projects."""
import re

from django.conf import settings
from django.core.mail import mail_managers
from django.utils.encoding import force_text


class CustomBrokenLinkEmailsMiddleware(object):
    """Custom version that adds the user to the error email."""
    def process_response(self, request, response):
        """
        Send broken link emails for relevant 404 NOT FOUND responses.
        """
        if response.status_code == 404 and not settings.DEBUG:
            domain = request.get_host()
            path = request.get_full_path()
            referer = force_text(
                request.META.get('HTTP_REFERER', ''), errors='replace')

            if not self.is_ignorable_request(request, path, domain, referer):
                ua = request.META.get('HTTP_USER_AGENT', '<none>')
                ip = request.META.get('REMOTE_ADDR', '<none>')

                user = None
                if request.user and hasattr(request.user, 'email'):
                    user = request.user.email
                content = (
                    "Referrer: %s\n"
                    "Requested URL: %s\n"
                    "User agent: %s\n"
                    "IP address: %s\n"
                    "User: %s\n"
                ) % (referer, path, ua, ip, user)
                if self.is_internal_request(domain, referer):
                    internal = 'INTERNAL '
                else:
                    internal = ''
                mail_managers(
                    "Broken %slink on %s" % (
                        internal,
                        domain
                    ),
                    content,
                    fail_silently=True)
        return response

    def is_internal_request(self, domain, referer):
        """
        Returns True if referring URL is the same domain as current request.

        """
        # Different subdomains are treated as different domains.
        return bool(re.match("^https?://%s/" % re.escape(domain), referer))

    def is_ignorable_request(self, request, uri, domain, referer):
        """
        Returns True if the given request *shouldn't* notify the site managers.
        """
        # '?' in referer is identified as search engine source
        if (not referer or
                (not self.is_internal_request(domain, referer)
                    and '?' in referer)):
            return True
        return any(
            pattern.search(uri) for pattern in settings.IGNORABLE_404_URLS)

########NEW FILE########
__FILENAME__ = models
"""Just an empty models file to let the testrunner recognize this as app."""

########NEW FILE########
__FILENAME__ = models_mixins
"""Useful mixins for models."""
from django.db import models
from django.utils.translation import get_language

try:
    from hvad.models import TranslationManager
except ImportError:
    class TranslationManager(object):
        pass
from simple_translation.utils import get_preferred_translation_from_lang


class HvadPublishedManager(TranslationManager):
    """
    Returns all objects, which are published and in the currently
    active language if check_language is True (default).

    :param request: A Request instance.
    :param check_language: Option to disable language filtering.

    """
    def published(self, request, check_language=True):
        kwargs = {'translations__is_published': True}
        if check_language:
            language = getattr(request, 'LANGUAGE_CODE', None)
            if not language:
                self.model.objects.none()
            kwargs.update({'translations__language_code': language})
        return self.get_query_set().filter(**kwargs)


class SimpleTranslationMixin(object):
    """Adds a ``get_translation`` method to the model."""
    def get_translation(self, language=None):
        """
        Returns the translation object for this object.

        :param language: A string representing a language (i.e. 'en'). If not
          given we will use the currently active language.

        """
        lang = language or get_language()
        return get_preferred_translation_from_lang(self, lang)


class SimpleTranslationPublishedManager(models.Manager):
    """
    Can be inherited by a custom manager, to add filtering for published
    objects, optionally with language specific filtering.

    The custom Manager needs to set ``published_field`` and ``language_field``
    to point to the fields, that hold the published state and the language.

    If those fields are not set on the child manager, it is assumed, that the
    model holding the translation fields for "Object" is called
    "ObjectTranslation". That way you can use this directly as a manager, if
    you stick to that pattern.

    """
    def published(self, request, check_language=True):
        """
        Returns all objects, which are published and in the currently
        active language if check_language is True (default).

        :param request: A Request instance.
        :param check_language: Option to disable language filtering.

        """
        published_field = getattr(
            self, 'published_field',
            '{}translation__is_published'.format(
                self.model._meta.module_name))
        filter_kwargs = {published_field: True, }
        results = self.get_query_set().filter(**filter_kwargs)

        if check_language:
            language = getattr(request, 'LANGUAGE_CODE', None)
            if not language:
                self.model.objects.none()
            language_field = getattr(
                self, 'language_field',
                '{}translation__language'.format(
                    self.model._meta.module_name))
            language_filter_kwargs = {language_field: language}
            results = results.filter(**language_filter_kwargs)

        return results.distinct()

########NEW FILE########
__FILENAME__ = s3
"""Custom S3 storage backends to store files in subfolders."""
from django.core.files.storage import get_storage_class

from storages.backends.s3boto import S3BotoStorage


class CachedS3BotoStorage(S3BotoStorage):
    def __init__(self, *args, **kwargs):
        super(CachedS3BotoStorage, self).__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            'compressor.storage.CompressorFileStorage')()

    def save(self, name, content):
        name = super(CachedS3BotoStorage, self).save(name, content)
        self.local_storage._save(name, content)
        return name


CompressorS3BotoStorage = lambda: CachedS3BotoStorage(location='compressor')
MediaRootS3BotoStorage = lambda: S3BotoStorage(location='media')

########NEW FILE########
__FILENAME__ = test_settings
"""
Good defaults for your test_settings.py

Just create a test_settings.py in your own project and add the following
lines::

    from myproject.settings import *
    from django_libs.settings.test_settings import *

"""
from myproject.settings import INSTALLED_APPS, EXTERNAL_APPS, DJANGO_APPS

PREPEND_WWW = False

INSTALLED_APPS.append('django_nose')


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)


EMAIL_SUBJECT_PREFIX = '[test] '
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SOUTH_TESTS_MIGRATE = False


TEST_RUNNER = 'django_libs.testrunner.NoseCoverageTestRunner'
COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'admin.py$', 'django_extensions',
]
COVERAGE_MODULE_EXCLUDES += EXTERNAL_APPS
COVERAGE_MODULE_EXCLUDES += DJANGO_APPS
COVERAGE_REPORT_HTML_OUTPUT_DIR = "coverage"

########NEW FILE########
__FILENAME__ = libs_tags
"""Templatetags for the ``django_libs`` project."""
import datetime
import importlib

from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve, Resolver404
from django.db.models.fields import FieldDoesNotExist
from django.template.defaultfilters import truncatewords_html

from django_libs import utils

from ..loaders import load_member


register = template.Library()


@register.assignment_tag
def add_form_widget_attr(field, attr_name, attr_value, replace=0):
    """
    Adds widget attributes to a bound form field.

    This is helpful if you would like to add a certain class to all your forms
    (i.e. `form-control` to all form fields when you are using Bootstrap)::

        {% load libs_tags %}
        {% for field in form.fields %}
            {% add_form_widget_attr field 'class' 'form-control' as field_ %}
            {{ field_ }}
        {% endfor %}

    The tag will check if the attr already exists and only append your value.
    If you would like to replace existing attrs, set `replace=1`::

        {% add_form_widget_attr field 'class' 'form-control' replace=1 as
          field_ %}


    """
    if not replace:
        attr = field.field.widget.attrs.get(attr_name, '')
        attr += attr_value
        field.field.widget.attrs[attr_name] = attr
        return field
    else:
        field.field.widget.attrs[attr_name] = attr_value
        return field


@register.tag('block_anyfilter')
def block_anyfilter(parser, token):
    """
    Turn any template filter into a blocktag.

    Usage::

    {% load libs_tags %}
    {% block_anyfilter django.template.defaultfilters.truncatewords_html 15 %}
        // Something complex that generates html output
    {% endblockanyfilter %}

    """
    bits = token.contents.split()
    nodelist = parser.parse(('endblockanyfilter',))
    parser.delete_first_token()
    return BlockAnyFilterNode(nodelist, bits[1], *bits[2:])


class BlockAnyFilterNode(template.Node):
    def __init__(self, nodelist, original_tag_fqn, *args):
        self.nodelist = nodelist
        self.original_tag = load_member(original_tag_fqn)
        self.args = args

    def render(self, context):
        output = self.nodelist.render(context)
        return self.original_tag(output, *self.args)


@register.tag('block_truncatewords_html')
def block_truncatewords_html(parser, token):
    """
    DEPRECATED: Use block_anyfilter instead!

    Allows to truncate any block of content.

    This is useful when rendering other tags that generate content,
    such as django-cms' ``render_placeholder`` tag, which is not available
    as an assignment tag::

        {% load libs_tags %}
        {% block_truncatewords_html 15 %}
            {% render_placeholder object.placeholder %}
        {% endblocktruncatewordshtml %}

    """
    bits = token.contents.split()
    try:
        word_count = bits[1]
    except IndexError:
        word_count = 15
    nodelist = parser.parse(('endblocktruncatewordshtml',))
    parser.delete_first_token()
    return BlockTruncateWordsHtmlNode(nodelist, word_count)


class BlockTruncateWordsHtmlNode(template.Node):
    def __init__(self, nodelist, word_count):
        self.nodelist = nodelist
        self.word_count = word_count

    def render(self, context):
        output = self.nodelist.render(context)
        return truncatewords_html(output, self.word_count)


@register.assignment_tag
def calculate_dimensions(image, long_side, short_side):
    """Returns the thumbnail dimensions depending on the images format."""
    if image.width >= image.height:
        return '{0}x{1}'.format(long_side, short_side)
    return '{0}x{1}'.format(short_side, long_side)


@register.assignment_tag
def call(obj, method, *args, **kwargs):
    """
    Allows to call any method of any object with parameters.

    Because come on! It's bloody stupid that Django's templating engine doesn't
    allow that.

    Usage::

        {% call myobj 'mymethod' myvar foobar=myvar2 as result %}
        {% call myobj 'mydict' 'mykey' as result %}
        {% call myobj 'myattribute' as result %}

    :param obj: The object which has the method that you would like to call
    :param method: A string representing the attribute on the object that
      should be called.

    """
    function_or_dict_or_member = getattr(obj, method)
    if callable(function_or_dict_or_member):
        # If it is a function, let's call it
        return function_or_dict_or_member(*args, **kwargs)
    if not len(args):
        # If it is a member, lets return it
        return function_or_dict_or_member
    # If it is a dict, let's access one of it's keys
    return function_or_dict_or_member[args[0]]


@register.assignment_tag
def concatenate(*args, **kwargs):
    """
    Concatenates the given strings.

    Usage::

        {% load libs_tags %}
        {% concatenate "foo" "bar" as new_string %}
        {% concatenate "foo" "bar" divider="_" as another_string %}

    The above would result in the strings "foobar" and "foo_bar".

    """
    divider = kwargs.get('divider', '')
    result = ''
    for arg in args:
        if result == '':
            result += arg
        else:
            result += '{0}{1}'.format(divider, arg)
    return result


@register.filter
def get_content_type(obj, field_name=False):
    """
    Returns the content type of an object.

    :param obj: A model instance.
    :param field_name: Field of the object to return.

    """
    content_type = ContentType.objects.get_for_model(obj)
    if field_name:
        return getattr(content_type, field_name, '')
    return content_type


@register.assignment_tag
def get_form_field_type(field):
    """
    Returns the widget type of the given form field.

    This can be helpful if you want to render form fields in your own way
    (i.e. following Bootstrap standards).

    Usage::

        {% load libs_tags %}
        {% for field in form %}
            {% get_form_field_type field as field_type %}
            {% if "CheckboxInput" in field_type %}
                <div class="checkbox">
                    <label>
                        // render input here
                    </label>
                </div>
            {% else %}
                {{ field }}
            {% endif %}
        {% endfor %}

    """
    return field.field.widget.__str__()


@register.filter
def get_verbose(obj, field_name=""):
    """
    Returns the verbose name of an object's field.

    :param obj: A model instance.
    :param field_name: The requested field value in string format.

    """
    if hasattr(obj, "_meta") and hasattr(obj._meta, "get_field_by_name"):
        try:
            return obj._meta.get_field_by_name(field_name)[0].verbose_name
        except FieldDoesNotExist:
            pass
    return ""


@register.assignment_tag
def get_profile_for(user):
    """
    Allows to call the get_profile utility function from django-libs in a
    template.

    """
    return utils.get_profile(user)


@register.assignment_tag
def get_query_params(request, *args):
    """
    Allows to change one of the URL get parameter while keeping all the others.

    Usage::

      {% load libs_tags %}
      {% get_query_params request "page" page_obj.next_page_number as query %}
      <a href="?{{ query }}">Next</a>

    You can also pass in several pairs of keys and values::

      {% get_query_params request "page" 1 "foobar" 2 as query %}

    You often need this when you have a paginated set of objects with filters.

    Your url would look something like ``/?region=1&gender=m``. Your paginator
    needs to create links with ``&page=2`` in them but you must keep the
    filter values when switching pages.

    :param request: The request instance.
    :param *args: Make sure to always pass in paris of args. One is the key,
      one is the value. If you set the value of a key to "!remove" that
      parameter will not be included in the returned query.

    """
    query = request.GET.copy()
    index = 1
    key = ''
    for arg in args:
        if index % 2 != 0:
            key = arg
        else:
            if arg == "!remove":
                try:
                    query.pop(key)
                except KeyError:
                    pass
            else:
                query[key] = arg
        index += 1
    return query.urlencode()


class LoadContextNode(template.Node):
    def __init__(self, fqn):
        self.fqn = fqn

    def render(self, context):
        module = importlib.import_module(self.fqn)
        for attr in dir(module):
            if not attr.startswith('__'):
                context[attr] = getattr(module, attr)
        return ''


@register.tag
def load_context(parser, token):
    # TODO Docstring!
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, fqn = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag requires a single argument' % token.contents.split()[0])
    if not (fqn[0] == fqn[-1] and fqn[0] in ('"', "'")):
        raise template.TemplateSyntaxError(
            "%r tag's argument should be in quotes" % tag_name)
    return LoadContextNode(fqn[1:-1])


@register.simple_tag
def navactive(request, url, exact=0, use_resolver=1):
    """
    Returns ``active`` if the given URL is in the url path, otherwise ''.

    Usage::

        {% load libs_tags %}
        ...
        <li class="{% navactive request "/news/" exact=1 %}">

    :param request: A request instance.
    :param url: A string representing a part of the URL that needs to exist
      in order for this method to return ``True``.
    :param exact: If ``1`` then the parameter ``url`` must be equal to
      ``request.path``, otherwise the parameter ``url`` can just be a part of
      ``request.path``.
    :use_resolver: If ``0`` we will not try to compare ``url`` with existing
      view names but we will only compare it with ``request.path``.

    """
    if use_resolver:
        try:
            if url == resolve(request.path).url_name:
                # Checks the url pattern in case a view_name is posted
                return 'active'
            elif url == request.path:
                # Workaround to catch URLs with more than one part, which don't
                # raise a Resolver404 (e.g. '/index/info/')
                match = request.path
            else:
                return ''
        except Resolver404:
            # Indicates, that a simple url string is used (e.g. '/index/')
            match = request.path

    if exact and url == match:
        return 'active'
    elif not exact and url in request.path:
        return 'active'
    return ''


@register.filter
def get_range(value, max_num=None):
    """
    Returns the range over a given value.

    Usage::

        {% load libs_tags %}

        {% for item in object_list.count|get_range %}
            {{ item }} // render real items here
        {% endfor %}
        {% for item in object_list.count|get_range:5 %}
            // render placeholder items here
        {% endfor %}

    :param value: The number to pass to the range function
    :param max_num: Optional. Use this if you want to get a range over the
      difference between the actual number and a maximum amount. This can
      be useful to display placeholder items in a situation where the
      space must always be filled up with 5 items but your actual list
      might only have 2 items.

    """
    if max_num:
        value = max_num - value
    return range(value)


@register.assignment_tag
def get_range_around(range_value, current_item, padding):
    """
    Returns a range of numbers around the given number.

    This is useful for pagination, where you might want to show something
    like this::

        << < ... 4 5 (6) 7 8 .. > >>

    In this example `6` would be the current page and we show 2 items around
    that page (including the page itself).

    Usage::

        {% load libs_tags %}
        {% get_range_around page_obj.paginator.num_pages page_obj.number 5
          as pages %}

    :param range_amount: Number of total items in your range (1 indexed)
    :param current_item: The item around which the result should be centered
      (1 indexed)
    :param padding: Number of items to show left and right from the current
      item.

    """
    total_items = 1 + padding * 2
    left_bound = padding
    right_bound = range_value - padding
    if range_value <= total_items:
        range_items = range(1, range_value+1)
        return {
            'range_items': range_items,
            'left_padding': False,
            'right_padding': False,
        }
    if current_item <= left_bound:
        range_items = range(1, range_value+1)[:total_items]
        return {
            'range_items': range_items,
            'left_padding': range_items[0] > 1,
            'right_padding': range_items[-1] < range_value,
        }

    if current_item >= right_bound:
        range_items = range(1, range_value+1)[-total_items:]
        return {
            'range_items': range_items,
            'left_padding': range_items[0] > 1,
            'right_padding': range_items[-1] < range_value,
        }

    range_items = range(current_item-padding, current_item+padding+1)
    return {
        'range_items': range_items,
        'left_padding': True,
        'right_padding': True,
    }


@register.inclusion_tag('django_libs/analytics.html')
def render_analytics_code(anonymize_ip='anonymize'):
    """
    Renders the google analytics snippet.

    :anonymize_ip: Use to add/refuse the anonymizeIp setting.

    """
    return {
        'ANALYTICS_TRACKING_ID': getattr(
            settings, 'ANALYTICS_TRACKING_ID', 'UA-XXXXXXX-XX'),
        'anonymize_ip': anonymize_ip,
    }


@register.inclusion_tag('django_libs/analytics2.html')
def render_analytics2_code():
    """
    Renders the new google analytics snippet.

    """
    return {
        'ANALYTICS_TRACKING_ID': getattr(
            settings, 'ANALYTICS_TRACKING_ID', 'UA-XXXXXXX-XX'),
        'ANALYTICS_DOMAIN': getattr(
            settings, 'ANALYTICS_DOMAIN', 'example.com')
    }


class VerbatimNode(template.Node):
    def __init__(self, text):
        self.text = text

    def render(self, context):
        return self.text


@register.simple_tag(takes_context=True)
def save(context, key, value):
    """
    Saves any value to the template context.

    Usage::

        {% save "MYVAR" 42 %}
        {{ MYVAR }}

    """
    context.dicts[0][key] = value
    return ''


@register.simple_tag(takes_context=True)
def sum(context, key, value, multiplier=1):
    """
    Adds the given value to the total value currently held in ``key``.

    Use the multiplier if you want to turn a positive value into a negative
    and actually substract from the current total sum.

    Usage::

        {% sum "MY_TOTAL" 42 -1 %}
        {{ MY_TOTAL }}

    """
    if key not in context.dicts[0]:
        context.dicts[0][key] = 0
    context.dicts[0][key] += value * multiplier
    return ''


@register.assignment_tag
def set_context(value):
    return value


@register.tag
def verbatim(parser, token):
    """Tag to render x-tmpl templates with Django template code."""
    text = []
    while 1:
        token = parser.tokens.pop(0)
        if token.contents == 'endverbatim':
            break
        if token.token_type == template.TOKEN_VAR:
            text.append('{{ ')
        elif token.token_type == template.TOKEN_BLOCK:
            text.append('{%')
        text.append(token.contents)
        if token.token_type == template.TOKEN_VAR:
            text.append(' }}')
        elif token.token_type == template.TOKEN_BLOCK:
            if not text[-1].startswith('='):
                text[-1:-1] = [' ']
            text.append(' %}')
    return VerbatimNode(''.join(text))


@register.filter
def exclude(qs, qs_to_exclude):
    """Tag to exclude a qs from another."""
    return qs.exclude(pk__in=qs_to_exclude.values_list('pk'))


@register.assignment_tag
def time_until(date_or_datetime):
    if isinstance(date_or_datetime, datetime.date):
        datetime_ = datetime.datetime(
            date_or_datetime.year,
            date_or_datetime.month,
            date_or_datetime.day,
            0, 0)
    else:
        datetime_ = date_or_datetime
    return datetime_ - datetime.datetime.now()


@register.assignment_tag
def days_until(date_or_datetime):
    days = time_until(date_or_datetime).days
    if days >= 0:
        return days
    return 0


@register.assignment_tag
def hours_until(date_or_datetime):
    closes_in = time_until(date_or_datetime)
    if closes_in.days < 0:
        return 0
    return closes_in.seconds / 3600


@register.assignment_tag
def minutes_until(date_or_datetime):
    closes_in = time_until(date_or_datetime)
    if closes_in.days < 0:
        return 0
    return closes_in.seconds / 60 - hours_until(date_or_datetime) * 60

########NEW FILE########
__FILENAME__ = testrunner
"""Custom test runner for the project."""
from django_coverage.coverage_runner import CoverageRunner
from django_nose import NoseTestSuiteRunner


class NoseCoverageTestRunner(CoverageRunner, NoseTestSuiteRunner):
    """Custom test runner that uses nose and coverage"""
    pass

########NEW FILE########
__FILENAME__ = context_processors_tests
"""Tests for the context processors of ``django_libs``."""
from django.test import TestCase

from ..context_processors import analytics


class AnalyticsTestCase(TestCase):
    """Tests for the ``analytics`` context processor."""
    longMessage = True

    def test_analytics(self):
        self.assertEqual(analytics(''),
                         {'ANALYTICS_TRACKING_ID': 'UA-THISISNOREAL-ID'})

########NEW FILE########
__FILENAME__ = factories
"""
Factories that are common to most Django apps.

The factories in this module shall help to create test fixtures for models that
are global to all Django projects and could be shared by tests of specialized
apps.

For example each app will need to create a user, therefore this module shall
provide facilities for user generation.

"""
from hashlib import md5

from django.contrib.auth.models import User

import factory


class HvadFactoryMixin(object):
    """
    Overrides ``_create`` and takes care of creating a translation.

    """
    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        obj = target_class(*args, **kwargs)

        # Factory boy and hvad behave a bit weird. When getting the object,
        # obj.some_translatable_field is actually set although no tranlsation
        # object exists, yet. We have to cache the translatable values ...
        cached_values = {}
        for field in obj._translated_field_names:
            if field in ['id', 'master', 'language_code']:
                continue
            cached_values[field] = getattr(obj, field)

        # ... because when calling translate, the translatable values will be
        # lost on the obj ...
        obj.translate(obj.language_code)
        for field in obj._translated_field_names:
            if field in ['id', 'master', 'language_code']:
                continue
            # ... so here we will put them back on the object, this time they
            # will be saved on the translatable object.
            setattr(obj, field, cached_values[field])

        obj.save()
        return obj


class SimpleTranslationMixin(object):
    """
    Adds a ``_prepare`` method that takes care of creating a translation.

    """

    @staticmethod
    def _get_translation_factory_and_field(self):
        """
        Should return a tuple of (TranslationFactory, 'fieldname').

        ``TranslationFactory`` is the factory class that can create translation
        objects for this objects.

        ``fieldname`` is the name of the FK on the translation class that
        points back to this object.

        """
        raise NotImplementedError()

    @classmethod
    def _prepare(cls, create, **kwargs):
        """
        Creates a ``PersonTranslation`` for this ``Person``.

        Note that we will only create a translation if you create a new object
        instead of just building it, because otherwise this object has no PK
        and cannot be used to instantiate the translation.

        """
        language = kwargs.pop('language', 'en')
        obj = super(SimpleTranslationMixin, cls)._prepare(create, **kwargs)
        if create:
            if language:
                translation_factory, fk_field = \
                    cls._get_translation_factory_and_field()
                kwargs_ = {
                    fk_field: obj,
                    'language': language,
                }
                translation_factory(**kwargs_)
        return obj


class UserFactory(factory.DjangoModelFactory):
    """
    Creates a new ``User`` object.

    We use ``django-registration-email`` which allows users to sign in with
    their email instead of a username. Since the username field is too short
    for most emails, we don't really use the username field at all and just
    store a md5 hash in there.

    Username will be a random 30 character md5 value.
    Email will be ``userN@example.com`` with ``N`` being a counter.
    Password will be ``test123`` by default.

    """
    FACTORY_FOR = User

    username = factory.Sequence(lambda n: md5(str(n)).hexdigest()[0:30])
    email = factory.Sequence(lambda n: 'user{0}@example.com'.format(n))

    @classmethod
    def _prepare(cls, create, **kwargs):
        password = 'test123'
        if 'password' in kwargs:
            password = kwargs.pop('password')
        user = super(UserFactory, cls)._prepare(create, **kwargs)
        user.set_password(password)
        if create:
            user.save()
        return user

########NEW FILE########
__FILENAME__ = forms_tests
"""Tests for the forms utilities of django_libs."""
from django import forms
from django.test import TestCase

from .. import forms as libs_forms


class DummyForm(libs_forms.StripTagsFormMixin, forms.Form):
    text = forms.CharField(max_length=1024)

    STRIP_TAGS_FIELDS = ['text', ]

    def __init__(self, *args, **kwargs):
        super(DummyForm, self).__init__(*args, **kwargs)
        self.strip_tags()


class StripTagsFormMixinTestCase(TestCase):
    """Tests for the ``StripTagsFormMixin``."""
    longMessage = True

    def test_mixin(self):
        form = DummyForm(data={'text': '<em>Foo</em>'})
        self.assertEqual(form.data['text'], 'Foo', msg=(
            'The mixin should strip away the tags from the given form data'))

        form = DummyForm(prefix='bar', data={'bar-text': '<em>Foo</em>'})
        self.assertEqual(form.data['bar-text'], 'Foo', msg=(
            'The mixin still works when the form has a prefix'))

########NEW FILE########
__FILENAME__ = libs_tags_tests
"""Tests for the templatetags of the ``project-kairos`` project."""
from mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from django_libs.templatetags import libs_tags as tags
from .test_app.factories import DummyProfileFactory
from .test_app.models import DummyProfile


class CalculateDimensionsTestCase(TestCase):
    """Tests for the ``calculate_dimensions`` templatetag."""
    longMessage = True

    def test_tag(self):
        image = Mock()
        image.width = 1
        image.height = 2
        result = tags.calculate_dimensions(image, 20, 10)
        self.assertEqual(result, '10x20', msg=(
            'If the width is smaller than the height, the thumbnail should'
            ' also have a smaller width'))

        image.width = 2
        image.height = 1
        result = tags.calculate_dimensions(image, 20, 10)
        self.assertEqual(result, '20x10', msg=(
            'If the width is bigger than the height, the thumbnail should'
            ' also have a bigger width'))

        image.width = 1
        image.height = 1
        result = tags.calculate_dimensions(image, 20, 10)
        self.assertEqual(result, '20x10', msg=(
            'If the width is equal to the height, the thumbnail should'
            ' be in landscape format.'))


class CallTestCase(TestCase):
    """Tests for the ``call`` templatetag."""
    longMessage = True

    def setUp(self):
        self.func = lambda args: args
        self.obj = Mock(func=self.func)
        self.obj.member = 'foobar'
        self.obj.dictionary = {'foo': 'bar', }

    def test_tag(self):
        self.assertEqual(
            tags.call(self.obj, 'func', 'test_string'), 'test_string', msg=(
                "When using it against an object's function, that function"
                " should be called and it's return value should be returned"))

        self.assertEqual(
            tags.call(self.obj, 'member'), 'foobar', msg=(
                "When using it against an object's member, that member"
                " should be returned"))

        self.assertEqual(
            tags.call(self.obj, 'dictionary', 'foo'), 'bar', msg=(
                "When using it against an object's member and that member"
                " is a dict it should return the value of the given key"))


class ConcatenateTestCase(TestCase):
    """Tests for the ``concatenate`` templatetag."""
    longMessage = True

    def test_tag(self):
        result = tags.concatenate('foo', 'bar')
        self.assertEqual(result, 'foobar', msg=(
            'If no divider is specified, the given strings should just be'
            ' concatenated'))
        result = tags.concatenate('foo', 'bar', 'foobar')
        self.assertEqual(result, 'foobarfoobar', msg=(
            'We can concatenate any number of strings'))
        result = tags.concatenate('foo', 'bar', divider='_')
        self.assertEqual(result, 'foo_bar', msg=(
            'If divider kwarg is given, the strings should be concatenated'
            ' with the given divider.'))


class GetContentTypeTestCase(TestCase):
    """Tests for the ``get_content_type`` templatetag."""
    longMessage = True

    def setUp(self):
        self.profile = DummyProfileFactory()

    def test_tag(self):
        self.assertIsInstance(
            tags.get_content_type(self.profile), ContentType,
            msg='Should return the profile\'s content type.')
        self.assertEqual(
            tags.get_content_type(self.profile, 'model'), 'dummyprofile',
            msg='Should return the profile\'s content type field model.')


class GetVerboseTestCase(TestCase):
    """Tests for the ``get_verbose`` templatetag."""
    longMessage = True

    def setUp(self):
        self.profile = DummyProfileFactory()

    def test_tag(self):
        self.assertEqual(
            tags.get_verbose(self.profile, 'dummy_field'), 'Dummy Field',
            msg='Returned the wrong verbose name for the "dummy_field".')
        self.assertEqual(
            tags.get_verbose(self.profile, 'non_existant_field'), '', msg=(
                'Should return "" for a non-existant field.'))


class GetProfileForTestCase(TestCase):
    """Tests for the ``get_profile_for`` templatetag."""
    longMessage = True

    def setUp(self):
        self.profile = DummyProfileFactory()
        self.user = self.profile.user

    def test_tag(self):
        self.assertEqual(tags.get_profile_for(self.user), self.profile)


class GetQueryParamsTestCase(TestCase):
    """Tests for the ``get_query_params`` templatetag."""
    longMessage = True

    def test_tag(self):
        req = RequestFactory().get('/?foobar=1&barfoo=2')

        result = tags.get_query_params(req, 'foobar', 2)
        self.assertEqual(result, 'foobar=2&barfoo=2', msg=(
            'Should change the existing query parameter'))

        result = tags.get_query_params(req, 'page', 2)
        self.assertEqual(result, 'foobar=1&barfoo=2&page=2', msg=(
            'Should add the new parameter to the query'))

        result = tags.get_query_params(req, 'page', 2, 'new', 42)
        self.assertEqual(result, 'foobar=1&barfoo=2&page=2&new=42', msg=(
            'Should add the new parameters to the query'))

        result = tags.get_query_params(req, 'page', 2, 'barfoo', '!remove')
        self.assertEqual(result, 'foobar=1&page=2', msg=(
            'Should add new parameters and remove the ones marked for'
            ' removal'))

        result = tags.get_query_params(req, 'page', 2, 'ghost', '!remove')
        self.assertEqual(result, 'foobar=1&barfoo=2&page=2', msg=(
            'Should not crash if the parameter marked for removal does not'
            ' exist'))


class LoadContextNodeTestCase(TestCase):
    """Tests for the ``LoadContextNode`` template node."""
    def test_node(self):
        node = tags.LoadContextNode('django_libs.tests.test_context')
        context = {}
        node.render(context)
        self.assertEqual(context['FOO'], 'bar')
        self.assertEqual(context['BAR'], 'foo')


class NavactiveTestCase(TestCase):
    """Tests for the ``navactive`` templatetag."""
    longMessage = True

    def test_tag(self):
        req = RequestFactory().get('/home/')
        result = tags.navactive(req, '/home/')
        self.assertEqual(result, 'active', msg=(
            "When the given string is part of the current request's URL path"
            " it should return ``active`` but returned %s" % result))
        result = tags.navactive(req, '/foo/')
        self.assertEqual(result, '', msg=(
            "When the given string is not part of the current request's URL"
            " path it should return '' but returned %s" % result))

        req = RequestFactory().get('/')
        result = tags.navactive(req, '/', exact=True)
        self.assertEqual(result, 'active', msg=(
            "When the given string is equal to the current request's URL path"
            " it should return ``active`` but returned %s" % result))
        result = tags.navactive(req, '/foo/', exact=True)
        self.assertEqual(result, '', msg=(
            "When the given string is not equal to the current request's URL"
            " path it should return '' but returned %s" % result))

        req = RequestFactory().get('/index/test/')
        result = tags.navactive(req, 'index')
        self.assertEqual(result, 'active', msg=(
            "When the given string is a url name, it should return"
            " 'active', if it matches the path, but returned %s" % result))

        req = RequestFactory().get('/index/test/')
        result = tags.navactive(req, '/index/test/')
        self.assertEqual(result, 'active', msg=(
            "When the given string is a long string, it should return"
            " 'active', if it matches the path, but returned %s" % result))

        result = tags.navactive(req, 'home')
        self.assertEqual(result, '', msg=(
            "When the given string is a url name, it should return"
            " '', if it matches the path, but returned %s" % result))

    @patch('django_libs.templatetags.libs_tags.resolve')
    def test_use_resolver_true(self, mock_resolve):
        req = RequestFactory().get('/index/test/')
        tags.navactive(req, '/index/test/')
        self.assertTrue(mock_resolve.called, msg=(
            'When calling the tag normally, we will try to resolve the given'
            ' url.'))

    @patch('django_libs.templatetags.libs_tags.resolve')
    def test_use_resolver_false(self, mock_resolve):
        req = RequestFactory().get('/index/test/')
        tags.navactive(req, '/index/test/', use_resolver=False)
        self.assertFalse(mock_resolve.called, msg=(
            'When calling the tag with use_resolve=False the resolver should'
            ' not be called at all'))


class GetRangeTestCase(TestCase):
    """Tests for the ``get_range`` filter."""
    longMessage = True

    def test_filter(self):
        result = tags.get_range(5)
        self.assertEqual(result, range(5), msg=(
            "Filter should behave exactly like Python's range function"))

    def test_filter_with_max_num(self):
        result = tags.get_range(3, 5)
        self.assertEqual(result, range(2), msg=(
            'Filter should return the difference between value and max_num'))


class GetRangeAround(TestCase):
    """Tests for the ``get_range_around`` assignment tag."""
    longMessage = True

    def test_tag(self):
        result = tags.get_range_around(1, 1, 2)
        self.assertEqual(result['range_items'], [1], msg=(
            'If only one value given, return that value'))
        self.assertFalse(result['left_padding'])
        self.assertFalse(result['right_padding'])

        result = tags.get_range_around(5, 1, 2)
        self.assertEqual(result['range_items'], [1, 2, 3, 4, 5], msg=(
            'If padding is so small, that all values fit into the range,'
            ' return all values.'))
        self.assertFalse(result['left_padding'])
        self.assertFalse(result['right_padding'])

        result = tags.get_range_around(6, 1, 2)
        self.assertEqual(result['range_items'], [1, 2, 3, 4, 5], msg=(
            'If center value is at the beginning of the range, return desired'
            ' amount of values after the center value.'))
        self.assertFalse(result['left_padding'])
        self.assertTrue(result['right_padding'])

        result = tags.get_range_around(6, 6, 2)
        self.assertEqual(result['range_items'], [2, 3, 4, 5, 6], msg=(
            'If center value is at the end of the range, return desired'
            ' amount of values from the end of the range.'))
        self.assertTrue(result['left_padding'])
        self.assertFalse(result['right_padding'])

        result = tags.get_range_around(8, 2, 2)
        self.assertEqual(result['range_items'], [1, 2, 3, 4, 5], msg=(
            'If center value is so close to the left bound that the distance'
            ' from left bound to center value is less or equal to the'
            ' padding, return the range beginning from the left bound'))
        self.assertFalse(result['left_padding'])
        self.assertTrue(result['right_padding'])

        result = tags.get_range_around(8, 6, 2)
        self.assertEqual(result['range_items'], [4, 5, 6, 7, 8], msg=(
            'If center value is so close to the right bound that the distance'
            ' from right bound to center value is less or equal to the'
            ' padding, return the range so that it ends at the center value'))
        self.assertTrue(result['left_padding'])
        self.assertFalse(result['right_padding'])

        result = tags.get_range_around(10, 5, 2)
        self.assertEqual(result['range_items'], [3, 4, 5, 6, 7], msg=(
            'If center value is in the middle of the range, return center'
            ' value surrounded by padding values'))
        self.assertTrue(result['left_padding'])
        self.assertTrue(result['right_padding'])


class RenderAnalyticsCodeTestCase(TestCase):
    """Tests for the ``render_analytics_code`` templatetag."""
    longMessage = True

    def test_tag(self):
        result = tags.render_analytics_code()
        expected = {
            'ANALYTICS_TRACKING_ID': 'UA-THISISNOREAL-ID',
            'anonymize_ip': 'anonymize'
        }
        self.assertEqual(result, expected, msg=('Should return a dict.'))


class VerbatimTestCase(TestCase):
    """Tests for the ``verbatim`` template tag."""
    longMessage = True

    def test_tag(self):
        template = Template(
            '{% load libs_tags %}{% verbatim %}{% if test1 %}{% test1 %}'
            '{% endif %}{{ test2 }}{% endverbatim %}')
        self.assertEqual(template.render(Context()),
                         '{% if test1 %}{% test1 %}{% endif %}{{ test2 }}')


class ExcludeTestCase(TestCase):
    """Tests for the ``exclude`` templatetag."""
    longMessage = True

    def setUp(self):
        self.dummy = DummyProfileFactory()
        DummyProfileFactory()
        DummyProfileFactory()
        DummyProfileFactory()

    def test_tag(self):
        qs = DummyProfile.objects.all()
        self.assertFalse(tags.exclude(qs, qs), msg=(
            'Should return an empty queryset, if both provided querysets are'
            ' identical.'))
        self.assertEqual(
            tags.exclude(qs, qs.exclude(pk=self.dummy.pk)).count(), 1,
            msg=('Should return one profile.'))

########NEW FILE########
__FILENAME__ = loaders_tests
"""Tests for the utility functions in ``loaders.py``."""
from django.test import TestCase

from ..loaders import load_member, load_member_from_setting, split_fqn


def callable_that_returns_fqn_string():
    """Dummy function Used by tests."""
    return 'django_libs.loaders.load_member'


class LoadMemberTestCase(TestCase):
    """Tests for the ``load_member`` utility function."""
    def test_function(self):
        member = load_member('django_libs.loaders.load_member')
        self.assertEqual(member.func_name, 'load_member')


class LoadMemberFromSetting(TestCase):
    """Tests for the ``load_member_from_setting`` utility function."""
    def test_function(self):
        member = load_member_from_setting('TEST_LOAD_MEMBER')
        self.assertEqual(member.func_name, 'load_member')


class SplitFqnTestCase(TestCase):
    """Tests for the ``split_fqn`` utility function."""
    def test_with_string(self):
        modulename, membername = split_fqn('django_libs.loaders.load_member')
        self.assertEqual(modulename, 'django_libs.loaders')
        self.assertEqual(membername, 'load_member')

    def test_with_callable(self):
        modulename, membername = split_fqn(callable_that_returns_fqn_string)
        self.assertEqual(modulename, 'django_libs.loaders')
        self.assertEqual(membername, 'load_member')

########NEW FILE########
__FILENAME__ = mixins
"""
Generally useful mixins for view tests (integration tests) of any project.

"""
import sys

from django.conf import settings

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import RequestFactory

from django_libs.tests.factories import UserFactory


class ViewTestMixin(object):
    """Mixin that provides commonly tested assertions."""
    longMessage = True

    def _check_callable(self, method='get', data=None, message=None,
                        kwargs=None, user=None, anonymous=False,
                        and_redirects_to=None, status_code=None,
                        called_by='is_callable', ajax=False, extra=None):
        """
        The method that does the actual assertions for ``is_callable`` and
        ``is_not_callable``.

        :method: 'get' or 'post'. Default is 'get'.
        :data: Post data or get data payload.
        :message: Lets you override the assertion message.
        :kwargs: Lets you override the view kwargs.
        :user: If user argument is given, it logs it in first.
        :anonymous: If True, it logs out the user first. Default is False
        :and_redirects_to: If set, it additionally makes an assertRedirect on
            whatever string is given. This can be either a relative url or a
            name.
        :status_code: Overrides the expected status code. Default is 200.
            Can either be a list of status codes or a single integer.
        :called_by: A string that is either 'is_callable' or 'is_not_callable'.
        :extra: Additional parameters to be passed to the client GET/POST. For
            example, follow = True if you want the client to follow redirects.


        """
        # Setting up defaults if not overwritten.
        if extra is None:
            extra = {}
        if called_by == 'is_not_callable':
            message_addin = ' not'
        elif called_by == 'is_callable':
            message_addin = ''
        if user:
            self.login(user)
        if anonymous:
            self.client.logout()
        if not status_code and and_redirects_to:
            status_code = 302
        if not status_code and called_by == 'is_callable':
            status_code = 200
        if not status_code and called_by == 'is_not_callable':
            status_code = 404
        client_args = (
            self.get_url(view_kwargs=kwargs or self.get_view_kwargs()),
            data or self.get_data_payload(),
        )
        if ajax:
            extra.update({'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})

        # making the request
        if method.lower() == 'get':
            resp = self.client.get(*client_args, **extra)
        elif method.lower() == 'post':
            resp = self.client.post(*client_args, **extra)
        else:
            raise Exception('Not a valid request method: "{0}"'.format(method))

        # usage validation
        if resp.status_code == 302 and not and_redirects_to and not (
                status_code in [200, 404]):
            # TODO change the defaults and remove this warning
            sys.stderr.write(
                '\n\033[1;31mDeprecationWarning:\033[1;m'
                ' Your response status code'
                ' was 302, although ``and_redirects_to`` was not set.\n'
                'Please use ``and_redirects_to`` for a test on redirects since'
                ' the callable methods will default to 200 or 404 in the'
                ' future.\n'
            )

        # assertions
        if and_redirects_to:
            self.assertRedirects(
                resp, and_redirects_to, status_code=status_code,
                msg_prefix=('The view did not redirect as expected.'))

        else:
            self.assertIn(resp.status_code, [status_code, 302], msg=(
                message or
                'The view should{0} be callable'.format(message_addin)))

        return resp

    def is_callable(self, method='get', data=None, message=None, kwargs=None,
                    user=None, anonymous=False, and_redirects_to=None,
                    status_code=None, ajax=False, extra=None):
        """
        A shortcut for an assertion on status code 200 or 302.

        :method: 'get' or 'post'. Default is 'get'.
        :data: Post data or get data payload.
        :message: Lets you override the assertion message.
        :kwargs: Lets you override the view kwargs.
        :user: If user argument is given, it logs it in first.
        :anonymous: If True, it logs out the user first. Default is False
        :and_redirects_to: If set, it additionally makes an assertRedirect on
            whatever string is given. This can be either a relative url or a
            name.
        :status_code: Overrides the expected status code. Default is 200.
            Can either be a list of status codes or a single integer.
        :extra: Additional parameters to be passed to the client GET/POST. For
            example, follow = True if you want the client to follow redirects.

        If no arguments are given, it makes the assertion according to the
        current test situation.

        """
        return self._check_callable(
            method=method, data=data, message=message, kwargs=kwargs,
            user=user, anonymous=anonymous, and_redirects_to=and_redirects_to,
            status_code=status_code, ajax=ajax, called_by='is_callable',
            extra=extra)

    def is_not_callable(self, method='get', message=None, data=None,
                        kwargs=None, user=None, anonymous=False,
                        and_redirects_to=None, status_code=None, ajax=False,
                        extra=None):
        """
        A shortcut for a common assertion on a 404 status code.

        :method: 'get' or 'post'. Default is 'get'.
        :message: The message to display if the assertion fails
        :data: Get data payload or post data.
        :kwargs: View kwargs can be overridden. This is e.g. necessary if
            you call is_not_callable for a deleted object, where the object.pk
            was assigned in get_view_kwargs.
        :user: If a user is given, it logs it in first.
        :anonymous: If True, it logs out the user first. Default is False
            :status_code: Overrides the expected status code. Default is 404.
            Can either be a list of status codes or a single integer.
        :extra: Additional parameters to be passed to the client GET/POST. For
            example, follow = True if you want the client to follow redirects.

        If no arguments are given, it makes the assertion according to the
        current test situation.

        """
        return self._check_callable(
            method=method, data=data, message=message, kwargs=kwargs,
            user=user, anonymous=anonymous, and_redirects_to=and_redirects_to,
            status_code=status_code, ajax=ajax, called_by='is_not_callable',
            extra=extra)

    def get_data_payload(self):
        """
        Returns a dictionairy providing GET data payload sent to the view.

        If the view expects request.GET data to include this, you can override
        this method and return the proper data for the test.

        """
        if hasattr(self, 'data_payload'):
            return self.data_payload
        return {}

    def get_view_name(self):
        """
        Returns a string representing the view name as set in the ``urls.py``.

        You must implement this when inheriting this mixin. If your ``urls.py``
        looks like this::

            ...
            url(r'^$', HomeView.as_view(), name='home_view'

        Then you should simply return::

            return 'home_view'

        """
        return NotImplementedError

    def get_view_args(self):
        """
        Returns a list representing the view's args, if necessary.

        If the URL of this view is constructed via args, you can override this
        method and return the proper args for the test.

        """
        return None

    def get_view_kwargs(self):
        """
        Returns a dictionary representing the view's kwargs, if necessary.

        If the URL of this view is constructed via kwargs, you can override
        this method and return the proper args for the test.

        """
        return None

    def get_url(self, view_name=None, view_args=None, view_kwargs=None):
        """
        Returns the url to be consumed by ``self.client.get``.

        When calling ``self.client.get`` we usually need three parameter:

            * The URL, which we construct from the view name using ``reverse``
            * The args
            * The kwargs

        In most cases ``args`` and ``kwargs`` are ``None``, so this method will
        help to return the proper URL by calling instance methods that can
        be overridden where necessary.

        :param view_name: A string representing the view name. If ``None``,
          the return value of ``get_view_name()`` will be used.
        :param view_args: A list representing the view args. If ``None``,
          the return value of ``get_view_args()`` will be used.
        :param view_kwargs: A dict representing the view kwargs. If ``None``,
          the return value of ``get_view_kwargs()`` will be used.

        """
        if view_name is None:
            view_name = self.get_view_name()
        if view_args is None:
            view_args = self.get_view_args()
        if view_kwargs is None:
            view_kwargs = self.get_view_kwargs()
        return reverse(view_name, args=view_args, kwargs=view_kwargs)

    def login(self, user, password='test123'):
        """
        Performs a login for the given user.

        By convention we always use ``test123`` in our test fixutres. When you
        create your users with the UserFactory, that password will be set by
        default.

        If you must you can provide a password to this method in order to
        override the ``test123`` default.

        :param user: A ``User`` instance.
        :param password: A string if you want to login with another password
          than 'test123'.

        """
        self.client.login(username=user.username, password=password)

    def get_login_url(self):
        """
        Returns the URL when testing the redirect for anonymous users to the
        login page.
        Can be overwritten if you do not use the auth_login as default or
        configure your urls.py file in a specific way.
        """
        return getattr(settings, 'LOGIN_URL', reverse('auth_login'))

    def should_redirect_to_login_when_anonymous(self, url=None):
        """
        Tests if the view redirects to login when the user is anonymous.

        :param url: A string representing the URL to be called. If ``None``,
          the return value of ``get_url()`` will be used.

        """
        if not url:
            url = self.get_url()
        resp = self.client.get(url)
        self.assertRedirects(resp,
                             '{0}?next={1}'.format(self.get_login_url(), url))
        return resp

    def should_be_callable_when_anonymous(self, url=None):
        """
        Tests if the view returns 200 when the user is anonymous.

        :param url: A string representing the URL to be called. If ``None``,
          the return value of ``get_url()`` will be used.

        """
        if not url:
            url = self.get_url()
        resp = self.client.get(url, data=self.get_data_payload())
        self.assertEqual(resp.status_code, 200)
        return resp

    def should_be_callable_when_authenticated(self, user, url=None):
        """
        Tests if the view returns 200 when the user is logged in.

        :param user: A ``User`` instance.
        :param url: A string representing the URL to be called. If ``None``,
          the return value of ``get_url()`` will be used.

        """
        if not url:
            url = self.get_url()
        self.login(user)
        resp = self.client.get(url, data=self.get_data_payload())
        self.assertEqual(resp.status_code, 200)
        return resp

    def should_be_callable_when_has_correct_permissions(self, user, url=None):
        """
        Tests if the view returns 200 when the user has permissions.

        Also tests if the view redirects to login if the user is logged in but
        does not have the correct permissions.

        :param user: A ``User`` instance that has the correct permissions.
        :param url: A string representing the URL to be called. If ``None``,
          the return value of ``get_url()`` will be used.

        """
        if not url:
            url = self.get_url()
        user_no_permissions = UserFactory()
        self.login(user_no_permissions)
        resp = self.client.get(url, data=self.get_data_payload())
        self.assertRedirects(resp,
                             '{0}?next={1}'.format(reverse('auth_login'), url))

        self.login(user)
        resp = self.client.get(url, data=self.get_data_payload())
        self.assertEqual(resp.status_code, 200)


class ViewRequestFactoryTestMixin(object):
    longMessage = True
    _logged_in_user = None
    view_class = None

    def assertRedirects(self, resp, redirect_url, msg=None):
        """
        Overrides the method that comes with Django's TestCase.

        This is necessary because the original method relies on self.client
        which we are not using here.

        """
        self.assertEqual(resp.status_code, 302, msg=msg or ('Should redirect'))
        self.assertEqual(resp._headers['location'][1], redirect_url,
                         msg=msg or ('Should redirect to correct `next_url`'))

    def get_request(self, method=RequestFactory().get, ajax=False, data=None,
                    user=AnonymousUser(), add_session=False, **kwargs):
        if data is not None:
            kwargs.update({'data': data})
        req = method(self.get_url(), **kwargs)
        req.user = user
        # the messages framework only works with the FallbackStorage in case of
        # requestfactory tests
        if add_session:
            middleware = SessionMiddleware()
            middleware.process_request(req)
            req.session.save()
        else:
            setattr(req, 'session', {})
        messages = FallbackStorage(req)
        setattr(req, '_messages', messages)
        if ajax:
            req.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        req = self.setUpRequest(req)
        if req is None:
            raise RuntimeError(
                'The request has become None. You probably forgot to return'
                ' the request again, when implementing `setUpRequest`.')
        return req

    def get_get_request(self, ajax=False, data=None, user=None,
                        add_session=False, **kwargs):
        if user is None:
            user = self.get_user()
        return self.get_request(
            ajax=ajax, data=data, user=user, add_session=add_session, **kwargs)

    def get_post_request(self, ajax=False, data=None, user=None,
                         add_session=False, **kwargs):
        method = RequestFactory().post
        if user is None:
            user = self.get_user()
        return self.get_request(
            method=method, ajax=ajax, data=data, user=user,
            add_session=add_session, **kwargs)

    def get_user(self):
        if self._logged_in_user is None:
            return AnonymousUser()
        return self._logged_in_user

    def get_login_url(self):
        """
        Returns the URL when testing the redirect for anonymous users to the
        login page.

        Can be overwritten if you do not use the auth_login as default or
        configure your urls.py file in a specific way.

        """
        login_url = getattr(settings, 'LOGIN_URL', None)
        if login_url is None:
            return reverse('auth_login')
        return login_url

    def get_view_name(self):
        """
        Returns a string representing the view name as set in the ``urls.py``.

        You must implement this when inheriting this mixin. If your ``urls.py``
        looks like this::

            ...
            url(r'^$', HomeView.as_view(), name='home_view'

        Then you should simply return::

            return 'home_view'

        """
        raise NotImplementedError

    def get_view_args(self):
        """
        Returns a list representing the view's args, if necessary.

        If the URL of this view is constructed via args, you can override this
        method and return the proper args for the test.

        """
        return ()

    def get_view_kwargs(self):
        """
        Returns a dictionary representing the view's kwargs, if necessary.

        If the URL of this view is constructed via kwargs, you can override
        this method and return the proper args for the test.

        """
        return {}

    def get_url(self):
        """
        Returns the url to be used in the request factory.

        Going the "old" way of implementing `get_view_name` is entirely
        optional. If you just leave it out, the url will fall back to '/'.

        """
        try:
            view_name = self.get_view_name()
        except NotImplementedError:
            # if the above is not implemented, we don't need the exact view, or
            # just don't care and return '/', which in most cases is enough
            return '/'
        view_args = self.get_view_args()
        view_kwargs = self.get_view_kwargs()
        return reverse(view_name, args=view_args, kwargs=view_kwargs)

    def get_view_class(self):
        """Returns the view class."""
        return self.view_class

    def get_view(self):
        """Returns the view ``.as_view()``"""
        view_class = self.get_view_class()
        if view_class is None:
            raise NotImplementedError('You need to define a view class.')
        return view_class.as_view()

    def get(self, user=None, data=None, ajax=False, add_session=False,
            kwargs=None):
        """Creates a response from a GET request."""
        req = self.get_get_request(
            user=user, data=data, ajax=ajax, add_session=add_session)
        view = self.get_view()
        if kwargs is None:
            kwargs = {}
            kwargs.update(self.get_view_kwargs())
        resp = view(req, **kwargs)
        return resp

    def post(self, user=None, data=None, ajax=False, add_session=False,
             kwargs=None):
        """Creates a response from a POST request."""
        req = self.get_post_request(
            user=user, data=data, ajax=ajax, add_session=add_session)
        view = self.get_view()
        if kwargs is None:
            kwargs = {}
            kwargs.update(self.get_view_kwargs())
        resp = view(req, **kwargs)
        return resp

    def login(self, user):
        """Sets the user as permanently logged in for all tests."""
        self._logged_in_user = user

    def logout(self):
        """'Logs out' the currently set default user."""
        self._logged_in_user = None

    def assert200(self, resp, user=None, msg=False):
        """Asserts if a response has returnd a status code of 200."""
        user_msg = user or self.get_user()
        if self.get_view_class() is not None:
            # if it's a view class, we can append it to the message as class
            # name
            view_msg = self.get_view_class()
        else:
            # if no view class is set, we assume function based view
            view_msg = self.get_view()
        if not msg:
            msg = ('The `{0}` view should have been callable for'
                   ' user `{1}`.').format(view_msg, user_msg)
        self.assertEqual(resp.status_code, 200, msg=msg)
        return resp

    def is_callable(self, user=None, data=None, ajax=False, add_session=False,
                    kwargs=None, msg=False):
        """Checks if the view can be called view GET."""
        resp = self.get(
            user=user, data=data, ajax=ajax, add_session=add_session,
            kwargs=kwargs)
        self.assert200(resp, user, msg=msg)
        return resp

    def is_not_callable(self, user=None, data=None, ajax=False,
                        add_session=False, post=False, kwargs=None):
        """Checks if the view can not be called view GET."""
        if post:
            call_obj = self.post
        else:
            call_obj = self.get
        self.assertRaises(
            Http404, call_obj, user=user, data=data, ajax=ajax,
            add_session=add_session, kwargs=kwargs)

    def is_postable(self, user=None, data=None, ajax=False, to=None,
                    next_url='', add_session=False, kwargs=None, msg=False):
        """Checks if the view handles POST correctly."""
        resp = self.post(
            user=user, data=data, add_session=add_session, kwargs=kwargs,
            ajax=ajax)
        if not ajax or to:
            if next_url:
                next_url = '?next={0}'.format(next_url)
            redirect_url = '{0}{1}'.format(to, next_url)
            self.assertRedirects(resp, redirect_url, msg=msg)
        else:
            self.assert200(resp, user, msg=msg)
        return resp

    def redirects(self, to, next_url='', user=None, add_session=False,
                  kwargs=None, msg=None):
        """Checks for redirects from a GET request."""
        resp = self.get(user=user, add_session=add_session, kwargs=kwargs)
        if next_url:
            next_url = '?next={0}'.format(next_url)
        redirect_url = '{0}{1}'.format(to, next_url)
        self.assertRedirects(resp, redirect_url, msg=msg)
        return resp

    def setUpRequest(self, request):
        """
        The request is passed through this method on each run to allow
        adding additional attributes to it or change certain values.

        """
        return request

    def should_redirect_to_login_when_anonymous(self, add_session=False):
        resp = self.redirects(
            to=self.get_login_url(), next_url=self.get_url(),
            add_session=add_session)
        return resp

########NEW FILE########
__FILENAME__ = model_mixins_tests
"""Tests for the model mixins of ``django_libs``."""
from mock import Mock

from django.test import TestCase

from .test_app.factories import DummyProfileTranslationFactory
from .test_app.models import DummyProfile


class SimpleTranslationMixinTestCase(TestCase):
    """Tests for the ``SimpleTranslationMixin`` mixin."""
    longMessage = True

    def setUp(self):
        self.dummyprofile_trans = DummyProfileTranslationFactory()
        self.dummyprofile = self.dummyprofile_trans.dummyprofile

    def test_mixin(self):
        self.assertEqual(self.dummyprofile.get_translation(),
                         self.dummyprofile_trans)


class SimpleTranslationPublishedManagerTestCase(TestCase):
    """Tests for the ``SimpleTranslationPublishedManager`` manager."""
    longMessage = True

    def setUp(self):
        DummyProfileTranslationFactory()
        DummyProfileTranslationFactory(is_published=False)
        DummyProfileTranslationFactory(language='de')
        DummyProfileTranslationFactory(language='de', is_published=False)

    def test_manager(self):
        request = Mock(LANGUAGE_CODE='en')
        self.assertEqual(DummyProfile.objects.published(request).count(), 1,
                         msg='There should be one published english dummy.')

        request = Mock(LANGUAGE_CODE='de')
        self.assertEqual(DummyProfile.objects.published(request).count(), 1,
                         msg='There should be one published german dummy.')

        request = Mock(LANGUAGE_CODE=None)
        self.assertEqual(DummyProfile.objects.published(request).count(), 0,
                         msg=(
                             'There should be no published dummy, if no'
                             ' language is set.'))

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
"""
This script is a trick to setup a fake Django environment, since this reusable
app will be developed and tested outside any specifiv Django project.

Via ``settings.configure`` you will be able to set all necessary settings
for your app and run the tests as if you were calling ``./manage.py test``.

"""
import sys

from django.conf import settings

import test_settings


if not settings.configured:
    settings.configure(**test_settings.__dict__)


from django_coverage.coverage_runner import CoverageRunner
from django_nose import NoseTestSuiteRunner


class NoseCoverageTestRunner(CoverageRunner, NoseTestSuiteRunner):
    """Custom test runner that uses nose and coverage"""
    pass


def runtests(*test_args):
    failures = NoseCoverageTestRunner(verbosity=2, interactive=True).run_tests(
        test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = factories
"""Just some factories for the test app."""
import factory

from ..factories import UserFactory
from models import DummyProfile, DummyProfileTranslation


class DummyProfileFactory(factory.DjangoModelFactory):
    """Factory for the ``DummyProfile`` model."""
    FACTORY_FOR = DummyProfile

    user = factory.SubFactory(UserFactory)
    dummy_field = factory.Sequence(lambda n: 'dummyfield{}'.format(n))


class DummyProfileTranslationFactory(factory.DjangoModelFactory):
    """Factory for the ``DummyProfileTranslation`` model."""
    FACTORY_FOR = DummyProfileTranslation

    dummy_translation = factory.Sequence(lambda n: 'trans {}'.format(n))
    dummyprofile = factory.SubFactory(DummyProfileFactory)

########NEW FILE########
__FILENAME__ = models
"""Models for the ``test_app`` app."""
from django.db import models
from django.utils.translation import ugettext_lazy as _

from simple_translation.translation_pool import translation_pool

from ...models_mixins import (
    SimpleTranslationMixin,
    SimpleTranslationPublishedManager,
)


class DummyProfile(SimpleTranslationMixin, models.Model):
    """Just a dummy profile model for testing purposes."""
    user = models.ForeignKey('auth.User')
    dummy_field = models.CharField(
        verbose_name=_('Dummy Field'),
        max_length=128,
    )

    objects = SimpleTranslationPublishedManager()


class DummyProfileTranslation(models.Model):
    """Just a translation of the dummy profile."""
    dummy_translation = models.CharField(max_length=128)

    is_published = models.BooleanField(default=True)
    language = models.CharField(max_length=8, default='en')

    dummyprofile = models.ForeignKey(DummyProfile)


translation_pool.register_translation(DummyProfile, DummyProfileTranslation)

########NEW FILE########
__FILENAME__ = urls
"""URLs for the test app."""
from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse
from django.views.generic import View

from django_libs.views import HybridView

View.get = lambda req, *args, **kwargs: HttpResponse('SUCCESS!')
authed_view = View.as_view()
authed_view_kwargs = {'authed': True}
anonymous_view = View.as_view()
anonymous_view_kwargs = {'anonymous': True}


urlpatterns = patterns(
    '',
    url(r'^$', HybridView.as_view(
        authed_view=authed_view,
        authed_view_kwargs=authed_view_kwargs,
        anonymous_view=anonymous_view,
        anonymous_view_kwargs=anonymous_view_kwargs,
        ), name='dummy_hybrid'),
)

########NEW FILE########
__FILENAME__ = test_context
"""This file is used by the ``LoadContextNodeTestCase`` test."""
FOO = 'bar'
BAR = 'foo'

########NEW FILE########
__FILENAME__ = test_settings
"""Settings that need to be set in order to run the tests."""
import os


PROJECT_ROOT = os.path.dirname(__file__)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

ROOT_URLCONF = 'django_libs.tests.urls'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(__file__, '../../static/')
MEDIA_ROOT = os.path.join(__file__, '../../media/')
STATICFILES_DIRS = (
    os.path.join(__file__, 'test_static'),
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'test_app/templates'),
)

COVERAGE_REPORT_HTML_OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), 'coverage')
COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'admin$', 'django_extensions',
    'testrunner',
]

EXTERNAL_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django_jasmine',
    'django_nose',
    'mailer',
]

INTERNAL_APPS = [
    'django_libs',
    'django_libs.tests.test_app',
]

INSTALLED_APPS = EXTERNAL_APPS + INTERNAL_APPS
COVERAGE_MODULE_EXCLUDES += EXTERNAL_APPS

TEST_LOAD_MEMBER = 'django_libs.loaders.load_member'

AUTH_PROFILE_MODULE = 'test_app.DummyProfile'

ANALYTICS_TRACKING_ID = 'UA-THISISNOREAL-ID'

########NEW FILE########
__FILENAME__ = urls
"""URLs to run the tests."""
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from django.http import HttpResponse

admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^index/test/$', lambda x: HttpResponse('Success'), name='index'),
    url(r'^admin-.+/', include(admin.site.urls)),
    url(r'^', include('test_app.urls')),
)

########NEW FILE########
__FILENAME__ = utils_email_tests
"""Tests for the email utils of ``django_libs``."""
from django.test import TestCase

from mailer.models import Message
from mock import Mock

from ..utils_email import send_email


class SendEmailTestCase(TestCase):
    """Tests for the ``send_email`` function."""
    longMessage = True

    def test_send_email(self):
        send_email(Mock(), {}, 'subject.html', 'html_email.html',
                   'info@example.com', ['recipient@example.com'])
        self.assertEqual(Message.objects.count(), 1, msg=(
            'An email should\'ve been sent'))
        send_email(None, {}, 'subject.html', 'html_email.html',
                   'info@example.com', ['recipient@example.com'])
        self.assertEqual(Message.objects.count(), 2, msg=(
            'An email should\'ve been sent'))

########NEW FILE########
__FILENAME__ = utils_tests
"""Tests for the utils of ``django_libs``."""
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import SiteProfileNotAvailable

from ..utils import conditional_decorator, get_profile, html_to_plain_text
from .factories import UserFactory
from test_app.models import DummyProfile


def dummy_decorator(func):
    def wrapper():
        return 0
    return wrapper


@conditional_decorator(dummy_decorator, False)
def test_method():
    """Used to test the ``conditional_decorator``."""
    return 1


@conditional_decorator(dummy_decorator, True)
def test_method_true():
    """Used to test the ``conditional_decorator``."""
    return 1


def get_profile_method(user):
    return DummyProfile.objects.get_or_create(user=user)[0]


class ConditionalDecoratorTestCase(TestCase):
    """Tests for the ``conditional_decorator``."""
    longMessage = True

    def test_decorator_with_condition_false(self):
        result = test_method()
        self.assertEqual(result, 1, msg=(
            'The method should have been executed normally, without calling'
            ' the decorator'))

    def test_decorator_with_condition_true(self):
        result = test_method_true()
        self.assertEqual(result, 0, msg=(
            'The method should have been executed with the decorator'))


class GetProfileTestCase(TestCase):
    """Tests for the ``get_profile`` function."""
    longMessage = True

    def setUp(self):
        self.user = UserFactory()
        self.old_get_profile_method = getattr(
            settings, 'GET_PROFILE_METHOD', None)
        self.old_auth_profile_module = getattr(
            settings, 'AUTH_PROFILE_MODULE', None)
        settings.AUTH_PROFILE_MODULE = (
            'test_app.DummyProfile')

    def tearDown(self):
        if self.old_get_profile_method:
            settings.GET_PROFILE_METHOD = self.old_get_profile_method
        if self.old_auth_profile_module:
            settings.AUTH_PROFILE_MODULE = self.old_auth_profile_module

    def test_returns_profile(self):
        """Test if the ``get_profile`` method returns a profile."""
        profile = get_profile(self.user)
        self.assertEqual(type(profile), DummyProfile, msg=(
            'The method should return a DummyProfile instance.'))

        settings.AUTH_PROFILE_MODULE = 'user_profileUserProfile'
        self.assertRaises(SiteProfileNotAvailable, get_profile, self.user)

        settings.AUTH_PROFILE_MODULE = 'test_app.DummyProfile'

        settings.GET_PROFILE_METHOD = (
            'django_libs.tests.utils_tests.get_profile_method')
        DummyProfile.objects.all().delete()

        profile = get_profile(self.user)
        self.assertEqual(type(profile), DummyProfile, msg=(
            'The method should return a DummyProfile instance.'))


class HTMLToPlainTextTestCase(TestCase):
    """Tests for the ``html_to_plain_text`` function."""
    longMessage = True

    def test_html_to_plain_text(self):
        html = (
            """
            <html>
                    <head></head>
                    <body>
                        <ul>
                            <li>List element</li>
                            <li>List element</li>
                            <li>List element</li>
                        </ul>
                    </body>
                </html>
            """
        )
        self.assertEqual(
            html_to_plain_text(html),
            '\n  * List element\n  * List element\n  * List element',
            msg='Should return a formatted plain text.')
        with open('test_app/templates/html_email.html', 'rb') as file:
            self.assertIn('[1]: *|ARCHIVE|*\n', html_to_plain_text(file), msg=(
                'Should return a formatted plain text.'))

    def test_replace_links(self):
        html = (
            """
            <span>T1<span> <a href="www.example.com">link</a> <span>T2</span>
            <br />
            <span>T3</span>
            """
        )
        expected = (
            "T1 link[1] T2\nT3\n\n[1]: www.example.com\n"
        )
        result = html_to_plain_text(html)
        self.assertEqual(result, expected, msg=(
            'Should replace links nicely'))

    def test_replace_br(self):
        html = (
            """
            <span>Text1</span>
            <br />
            <br />
            <span>Text2</span>
            """
        )
        expected = (
            "Text1\n\nText2"
        )
        result = html_to_plain_text(html)
        self.assertEqual(result, expected, msg=(
            'Should replace links nicely'))

########NEW FILE########
__FILENAME__ = views_mixins_tests
"""Tests for the view mixins of ``django-libs``."""
from django.test import TestCase
from django.test.client import RequestFactory
from django.views.generic import TemplateView

from django_libs.views_mixins import AjaxResponseMixin


class DummyView(AjaxResponseMixin, TemplateView):
    """Just a test view."""
    template_name = "test_template.html"


class AjaxResponseMixinTestCase(TestCase):
    longMessage = True

    def setUp(self):
        self.view = DummyView()

    def test_mixin(self):
        """Test for the ``AjaxResponseMixin`` class."""
        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        req = RequestFactory().get('/', **extra)
        self.view.request = req
        self.assertEqual(self.view.get_template_names(),
                         ['ajax_test_template.html'],
                         msg='Got the wrong template name.')

########NEW FILE########
__FILENAME__ = views_tests
"""Tests for the view classes of ``django-libs``."""
from django.test import TestCase
from django.views.generic import TemplateView, View

from ..views import HybridView
from .factories import UserFactory
from .mixins import ViewTestMixin


class HybridViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``HybridView`` view class."""
    longMessage = True

    def setUp(self):
        self.user = UserFactory()

        self.authed_view = TemplateView.as_view(template_name='base.html')
        self.authed_view_kwargs = {'authed': True}
        self.anonymous_view = TemplateView.as_view(template_name='base.html')
        self.anonymous_view_kwargs = {'anonymous': True}
        self.other_anonymous_view = View.as_view()
        self.view_kwargs = {
            'authed_view': self.authed_view,
            'authed_view_kwargs': self.authed_view_kwargs,
            'anonymous_view': self.anonymous_view,
            'anonymous_view_kwargs': self.anonymous_view_kwargs}

    def get_view_name(self):
        return self.view_name

    def test_view(self):
        self.view_name = 'dummy_hybrid'
        self.should_be_callable_when_anonymous()

        bad_kwargs = self.view_kwargs.copy()
        bad_kwargs.update({'post': 'this should not be defined here'})
        self.assertRaises(TypeError, HybridView.as_view, **bad_kwargs)

        bad_kwargs = self.view_kwargs.copy()
        bad_kwargs.update({'wrongattr': 'this is not defined on the view'})
        self.assertRaises(TypeError, HybridView.as_view, **bad_kwargs)

        self.should_be_callable_when_authenticated(self.user)


# class RapidPrototypingViewTestCase(ViewTestMixin, TestCase):
#     """Tests for the ``RapidPrototypingView`` view class."""
#     longMessage = True

#     def get_view_name(self):
#         return 'prototype'

#     def test_view(self):
#         self.should_be_callable_when_anonymous()

########NEW FILE########
__FILENAME__ = test_email_backend
"""Custom email backend for testing the project."""
import re

from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend
from django.core.mail.message import sanitize_address

from . import default_settings as settings


class EmailBackend(SmtpEmailBackend):
    """
    Email backend that sends all emails to a defined address, no matter what
    the recipient really is.

    In order to use it, set this in your local_settings.py::

        EMAIL_BACKEND = 'django_libs.test_email_backend.EmailBackend'
        TEST_EMAIL_BACKEND_RECIPIENTS = (
            ('Name', 'email@gmail.com'),
        )

    """
    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients() or \
                not settings.TEST_EMAIL_BACKEND_RECIPIENTS:
            return False
        from_email = sanitize_address(
            email_message.from_email, email_message.encoding)
        recipients = [sanitize_address(addr, email_message.encoding)
                      for name, addr in settings.TEST_EMAIL_BACKEND_RECIPIENTS]
        try:
            self.connection.sendmail(
                from_email, recipients, email_message.message().as_string())
        except:
            if not self.fail_silently:
                raise
            return False
        return True


class WhitelistEmailBackend(SmtpEmailBackend):
    """
    Email backend that sends only these emails, that match the whitelist
    setting.

    In order to use it, set this in your local_settings.py::

        EMAIL_BACKEND = 'django_libs.test_email_backend.EmailBackend'
        EMAIL_BACKEND_WHITELIST = [
            r'.*@example\.com',
        ]

    This setting would allow all emails to @example.com to be sent and all
    others are discarded. The setting expects regex, so better test it before
    adding it here to prevent errors.

    If the setting does not exist, no emails are sent at all.

    """
    def _send(self, email_message):
        """A helper method that does the actual sending."""
        from_email = sanitize_address(
            email_message.from_email, email_message.encoding)
        recipients = self.clean_recipients(email_message)

        if not recipients:
            return False

        try:
            self.connection.sendmail(
                from_email, recipients, email_message.message().as_string())
        except:
            if not self.fail_silently:
                raise
            return False
        return True

    def clean_recipients(self, email_message):
        """Removes all the unallowed recipients."""
        new_recipients = []

        recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in email_message.recipients()]
        for recipient in recipients:
            if self.matches_whitelist(recipient):
                new_recipients.append(recipient)
            elif settings.EMAIL_BACKEND_REROUTE_BLACKLIST:
                for name, addr in settings.TEST_EMAIL_BACKEND_RECIPIENTS:
                    new_recipients.append(addr)
        # remove duplicates
        new_recipients = list(set(new_recipients))
        return new_recipients

    def matches_whitelist(self, recipient):
        """Checks if the email address matches one of the whitelist entries."""
        matches = False
        for entry in settings.EMAIL_BACKEND_WHITELIST:
            if re.match(entry, recipient):
                matches = True
        return matches

########NEW FILE########
__FILENAME__ = utils
"""Additional helpful utility functions."""
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from bs4 import BeautifulSoup
from HTMLParser import HTMLParser

from .loaders import load_member_from_setting


class conditional_decorator(object):
    """
    Allows you to use decorators based on a condition.

    Useful to require login only if a setting is set::

        @conditional_decorator(method_decorator(login_required), settings.FOO)
        def dispatch(self, request, *args, **kwargs):
            return super(...).dispatch(...)

    """
    def __init__(self, dec, condition):
        self.decorator = dec
        self.condition = condition

    def __call__(self, func):
        if not self.condition:
            # Return the function unchanged, not decorated.
            return func
        return self.decorator(func)


def get_profile(user):
    """
    Makes sure to always return a valid profile for the user.

    If none exists, it creates one.

    :user: A Django ``User`` instance.

    """
    # try if we get a profile via the regular method
    try:
        return user.get_profile()
    except ObjectDoesNotExist:
        pass

    # check if we set a custom method for profile fetching
    setting = getattr(settings, 'GET_PROFILE_METHOD', None)
    if setting:
        method = load_member_from_setting('GET_PROFILE_METHOD')
        return method(user)

    app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')

    # the models.get_model method allows to read load the model from the app's
    # model cache to allow the setting to be written as 'app_name.ModelName'
    profile_cls = models.get_model(app_label, model_name)
    return profile_cls.objects.create(user=user)


class HTML2PlainParser(HTMLParser):
    """Custom html parser to convert html code to plain text."""
    def __init__(self):
        self.reset()
        self.text = ''  # Used to push the results into a variable
        self.links = []  # List of aggregated links

        # Settings
        self.ignored_elements = getattr(
            settings, 'HTML2PLAINTEXT_IGNORED_ELEMENTS',
            ['html', 'head', 'style', 'meta', 'title', 'img']
        )
        self.newline_before_elements = getattr(
            settings, 'HTML2PLAINTEXT_NEWLINE_BEFORE_ELEMENTS',
            ['br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'p', 'li']
        )
        self.newline_after_elements = getattr(
            settings, 'HTML2PLAINTEXT_NEWLINE_AFTER_ELEMENTS',
            ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'p', 'td']
        )
        self.stroke_before_elements = getattr(
            settings, 'HTML2PLAINTEXT_STROKE_BEFORE_ELEMENTS',
            ['tr']
        )
        self.stroke_after_elements = getattr(
            settings, 'HTML2PLAINTEXT_STROKE_AFTER_ELEMENTS',
            ['tr']
        )
        self.stroke_text = getattr(settings, 'HTML2PLAINTEXT_STROKE_TEXT',
                                   '------------------------------\n')

    def handle_starttag(self, tag, attrs):
        """Handles every start tag like e.g. <p>."""
        if (tag in self.newline_before_elements):
            self.text += '\n'
        if (tag in self.stroke_before_elements
                and not self.text.endswith(self.stroke_text)):
            # Put a stroke in front of every relevant element, if there is some
            # content between it and its predecessor
            self.text += self.stroke_text
        if tag == 'a':
            # If it's a link, append it to the link list
            for attr in attrs:
                if attr[0] == 'href':
                    self.links.append((len(self.links) + 1, attr[1]))

    def handle_data(self, data):
        """Handles data between tags."""
        # Only proceed with unignored elements
        if not self.lasttag in self.ignored_elements:
            # Remove any predefined linebreaks
            text = data.replace('\n', '')
            # If there's some text left, proceed!
            if text:
                if self.lasttag == 'li':
                    # Use a special prefix for list elements
                    self.text += '  * '
                self.text += text
                if self.lasttag in self.newline_after_elements:
                    # Add a linebreak at the end of the content
                    self.text += '\n'

    def handle_endtag(self, tag):
        """Handles every end tag like e.g. </p>."""
        if tag in self.stroke_after_elements:
            if self.text.endswith(self.stroke_text):
                # Only add a stroke if there isn't already a stroke posted
                # In this case, there was no content between the tags, so
                # remove the starting stroke
                self.text = self.text[:-len(self.stroke_text)]
            else:
                # If there's no linebreak before the stroke, add one!
                if not self.text.endswith('\n'):
                    self.text += '\n'
                self.text += self.stroke_text
        if tag == 'a':
            # If it's a link, add a footnote
            self.text += '[{}]'.format(len(self.links))
        elif tag == 'br' and self.text and not self.text.endswith('\n'):
            # If it's a break, check if there's no break at the end of the
            # content. If there's none, add one!
            self.text += '\n'
        # Reset the lasttag, otherwise this parse can geht confused, if the
        # next element is not wrapped in a new tag.
        if tag == self.lasttag:
            self.lasttag = None


def html_to_plain_text(html):
    """Converts html code into formatted plain text."""
    # Use BeautifulSoup to normalize the html
    soup = BeautifulSoup(html)
    # Init the parser
    parser = HTML2PlainParser()
    parser.feed(str(soup))
    # Strip the end of the plain text
    result = parser.text.rstrip()
    # Add footnotes
    if parser.links:
        result += '\n\n'
        for link in parser.links:
            result += '[{}]: {}\n'.format(link[0], link[1])
    return result

########NEW FILE########
__FILENAME__ = utils_email
"""Utility functions for sending emails."""
from django.template import RequestContext
from django.template.loader import render_to_string

import mailer

from .utils import html_to_plain_text


def send_email(request, extra_context, subject_template, body_template,
               from_email, recipients, priority="medium"):
    """
    Sends an email based on templates for subject and body.

    :param request: The current request instance.
    :param extra_context: A dictionary of items that should be added to the
        templates' contexts.
    :param subject_template: A string representing the path to the template of
        of the email's subject.
    :param body_template: A string representing the path to the template of
        the email's body.
    :param from_email: String that represents the sender of the email.
    :param recipients: A list of tuples of recipients. The tuples are similar
        to the ADMINS setting.

    """
    if request:
        context = RequestContext(request, extra_context)
    else:
        context = extra_context
    subject = render_to_string(subject_template, context)
    subject = ''.join(subject.splitlines())
    message_html = render_to_string(body_template, context)
    message_plaintext = html_to_plain_text(message_html)
    mailer.send_html_mail(subject, message_plaintext, message_html, from_email,
                          recipients, priority=priority)

########NEW FILE########
__FILENAME__ = views
"""Views for testing 404 and 500 templates."""
from functools import update_wrapper

from django.views.generic import TemplateView, View


class Http404TestView(TemplateView):
    """
    WARNING: This view is deprecated. Use the ``RapidPrototypingView`` instead.

    """
    template_name = '404.html'


class Http500TestView(TemplateView):
    """
    WARNING: This view is deprecated. Use the ``RapidPrototypingView`` instead.

    """
    template_name = '500.html'


class HybridView(View):
    """
    View that renders different views depending on wether the user is authed.

    If the user is authenticated, it will render ``authed_view``, otherwise
    it will render ``anonymous_view``.

    If you are passing in a function based view you can also define
    ``authed_view_kwargs`` and ``anonymous_view_kwargs`` which, of course,
    should be dictionaries.

    """
    authed_view = None
    authed_view_kwargs = None
    anonymous_view = None
    anonymous_view_kwargs = None

    @classmethod
    def as_view(cls, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r. as_view "
                                "only accepts arguments that are already "
                                "attributes of the class." % (
                                    cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.args = args
            self.kwargs = kwargs
            self.authed_view = initkwargs.get('authed_view')
            self.authed_view_kwargs = initkwargs.get('authed_view_kwargs')
            self.anonymous_view = initkwargs.get('anonymous_view')
            self.anonymous_view_kwargs = initkwargs.get(
                'anonymous_view_kwargs')
            return self.dispatch(request, *args, **kwargs)
        # take name and docstring from class
        update_wrapper(view, cls, updated=())
        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            view_kwargs = self.authed_view_kwargs or {}
            return self.authed_view(request, **view_kwargs)

        view_kwargs = self.anonymous_view_kwargs or {}
        return self.anonymous_view(request, **view_kwargs)


class RapidPrototypingView(TemplateView):
    """
    View that can render any given template.

    This can be useful when you want your designers to be bale to go ahead and
    create templates although no views have been created for those templates,
    yet.

    """
    def dispatch(self, request, *args, **kwargs):
        self.template_name = kwargs.get('template_path')
        return super(RapidPrototypingView, self).dispatch(request, *args,
                                                          **kwargs)

########NEW FILE########
__FILENAME__ = views_mixins
"""Useful mixins for class based views."""
import json
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import DetailView


class AccessMixin(object):
    """Mixin to controls access to the view based on a setting."""
    access_mixin_setting_name = None

    def dispatch(self, request, *args, **kwargs):
        # Check, if user needs to be logged in
        if self.access_mixin_setting_name is None:
            raise Exception(
                'Please set `access_mixin_setting_name` on the view that'
                ' inherits the AccessMixin')
        if getattr(settings, self.access_mixin_setting_name, False):
            return super(AccessMixin, self).dispatch(
                request, *args, **kwargs)
        return login_required(super(AccessMixin, self).dispatch)(
            request, *args, **kwargs)


class AjaxResponseMixin(object):
    """
    A mixin that prepends `ajax_` to the template name when it is an ajax call.

    This gives you the chance to return partial templates when it is an ajax
    call, so you can render the output inside of a modal, for example.

    """
    ajax_template_prefix = 'ajax_'

    def get_template_names(self):
        names = super(AjaxResponseMixin, self).get_template_names()
        if self.request.is_ajax():
            count = 0
            for name in names:
                filename_split = list(os.path.split(name))
                old_filename = filename_split[-1]
                new_filename = '{0}{1}'.format(
                    self.ajax_template_prefix, old_filename)
                filename_split[-1] = new_filename
                names[count] = os.path.join(*filename_split)
                count += 1
        return names


class DetailViewWithPostAction(DetailView):
    """
    Generic class based view to handle custom post actions in a DetailView.

    When you derive from this class, your buttons need to be called
    `post_actionname` and you have to implement action handlers with the
    name `post_actionname` and url retrievers with the name
    `get_success_url_post_actionname`.

    If all actions should have the same success url, you can also implement
    `get_success_url`, which will be used as a fallback in case that no
    specific url retrieve has been implemented.

    """
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        for key in self.request.POST.keys():
            if key.startswith('post_'):
                getattr(self, key)()
                break
        success_url_handler = getattr(self, 'get_success_url_%s' % key, False)
        if not success_url_handler:
            success_url_handler = getattr(self, 'get_success_url')
        success_url = success_url_handler()
        return HttpResponseRedirect(success_url)


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.

    Taken from here: https://docs.djangoproject.com/en/dev/topics/
    class-based-views/#more-than-just-html

    """
    response_class = HttpResponse

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.

        """
        response_kwargs['content_type'] = 'application/json'
        return self.response_class(
            self.convert_context_to_json(context),
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        """
        Convert the context dictionary into a JSON object.

        If your context has complex Django objects, you need to override this
        method and make sure that the context gets transformed into something
        that ``json.dumps`` can handle.

        """
        return json.dumps(context)

########NEW FILE########
__FILENAME__ = widgets
"""Custom form widgets."""
from django.forms import widgets
from django.forms.util import flatatt
from django.template import Context
from django.template.loader import get_template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy


class LibsImageWidget(widgets.ClearableFileInput):
    """
    A better file input widget.

    Remember to include the js file as well. See docs for details.

    """

    initial_text = ugettext_lazy('Currently')
    input_text = ugettext_lazy('Change')
    clear_checkbox_label = ugettext_lazy('Clear')
    template_path = 'django_libs/partials/libs_image_widget.html'

    def __init__(self, attrs=None):
        self.classes = attrs.get('class', '')
        super(LibsImageWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)
        context = {
            'checkbox_name': conditional_escape(checkbox_name),
            'checkbox_id': conditional_escape(checkbox_id),
            'checkbox_label': self.clear_checkbox_label,
            'input_id': '#{0}'.format(final_attrs['id']),
            'initial_text': self.initial_text,
            'input_text': self.input_text,
            'classes': self.classes,
            'widget': self,
            'value': value,
            'input': mark_safe('<input{0}/>'.format(flatatt(final_attrs))),
        }

        if value is None:
            value = ''
        if value and hasattr(value, "url"):
            # Only add the 'value' attribute if a value is non-empty.
            context.update({'initial': True})
            if value.url:
                context.update({
                    'src': value.url,
                    'file_name': value.url.split('/')[-1]})
                if not self.is_required:
                    context.update({
                        'clear_widget': widgets.CheckboxInput().render(
                            checkbox_name, False, attrs={'id': checkbox_id})})

        t = get_template(self.template_path)
        c = Context(context)
        return t.render(c)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-libs documentation build configuration file, created by
# sphinx-quickstart on Fri Jun 29 10:05:46 2012.
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath(os.path.join(__file__, '../..')))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'sphinx.ext.todo', 'sphinx.ext.pngmath', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-libs'
copyright = u'2012, Martin Brochhaus'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-libsdoc'


# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
# documentclass [howto/manual]).
latex_documents = [
    ('index', 'django-libs.tex', u'django-libs Documentation',
     u'Martin Brochhaus', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-libs', u'django-libs Documentation',
     [u'Martin Brochhaus'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'django-libs', u'django-libs Documentation',
     u'Martin Brochhaus', 'django-libs', 'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
