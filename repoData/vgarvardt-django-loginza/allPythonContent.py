__FILENAME__ = admin
# -*- coding:utf-8 -*-
from django.contrib.admin import site

from loginza import models

site.register(
    models.Identity,
    list_display=['id', 'provider', 'identity'],
    list_filter=['provider'],
)
site.register(
    models.UserMap,
    list_display=['id', 'identity', 'user']
)
########NEW FILE########
__FILENAME__ = authentication
# -*- coding:utf-8 -*-
try:
    from django.contrib.auth import get_user_model
except ImportError: # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

class LoginzaBackend(object):
    supports_object_permissions = False
    supports_anonymous_user = False

    def authenticate(self, user_map=None):
        return user_map.user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class LoginzaError(object):
    type = None
    message = None

    def __init__(self, data):
        self.type = data['error_type']
        self.message = data['error_message']

########NEW FILE########
__FILENAME__ = settings
# -*- coding:utf-8 -*-
from django.conf import settings

lang = 'en'
if 'ru' in settings.LANGUAGE_CODE: lang = 'ru'
elif 'uk' in settings.LANGUAGE_CODE: lang = 'uk'
# Default language that wil be used for loginza widgets when not explicitly set for widget template tag.
DEFAULT_LANGUAGE = getattr(settings, 'LOGINZA_DEFAULT_LANGUAGE', lang)

# Comma separated providers list, that will be used for widgets w/out providers_set parameter explicitly set.
DEFAULT_PROVIDERS_SET = getattr(settings, 'LOGINZA_DEFAULT_PROVIDERS_SET', None)

# Default provider for widgets w/out provider parameter explicitly set.
DEFAULT_PROVIDER = getattr(settings, 'LOGINZA_DEFAULT_PROVIDER', None)

# Comma-separated providers names for providers icons that will be shown for loginza_icons widget.
# Only used when providers_set is not set for widget template tag and DEFAULT_PROVIDERS_SET is None.
# When empty - all available providers icons will be shown.
ICONS_PROVIDERS = getattr(settings, 'LOGINZA_ICONS_PROVIDERS', None)

# Dict with keys as provider names and values as provider titles to use as alt and title
# for loginza_icons widget. Values will be used to override default titles.
PROVIDER_TITLES = getattr(settings, 'LOGINZA_PROVIDER_TITLES', {})

# Default email that will be used for new users when loginza data does not have one.
DEFAULT_EMAIL = getattr(settings, 'LOGINZA_DEFAULT_EMAIL', 'user@loginza')

# List or tuple of paths, that will not be stored for return.
AMNESIA_PATHS = getattr(settings, 'LOGINZA_AMNESIA_PATHS', ())

# Button widget image url.
BUTTON_IMG_URL = getattr(settings, 'LOGINZA_BUTTON_IMG_URL', 'http://loginza.ru/img/sign_in_button_gray.gif')

# Icons widget images urls.
ICONS_IMG_URLS = getattr(settings, 'LOGINZA_ICONS_IMG_URLS', {})

# iframe widget size
IFRAME_WIDTH = getattr(settings, 'LOGINZA_IFRAME_WIDTH', '359px')
IFRAME_HEIGHT = getattr(settings, 'LOGINZA_IFRAME_HEIGHT', '300px')

# Widget settings
WIDGET_ID = getattr(settings, 'LOGINZA_WIDGET_ID', None)
API_SIGNATURE = getattr(settings, 'LOGINZA_API_SIGNATURE', None)
########NEW FILE########
__FILENAME__ = decorators
# -*- coding:utf-8 -*-
from django import http
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.decorators import available_attrs
from django.utils.functional import wraps
from django.utils.http import urlquote
from django.contrib.sites.models import Site

from loginza import signals

def user_passes_test(test_func, login_url=None, fail_callback=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    if not login_url:
        from django.conf import settings

        login_url = settings.LOGIN_URL

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            if fail_callback is not None:
                return fail_callback(request)
            else:
                path = urlquote(request.get_full_path())
                tup = login_url, redirect_field_name, path
                return http.HttpResponseRedirect('%s?%s=%s' % tup)

        return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)

    return decorator


def _user_anonymous_callback(request):
    response = None

    results = signals.login_required.send(request)
    for callback, result in results:
        if isinstance(result, http.HttpResponse):
            response = result
            break

    if response is None:
        referer = request.META.get('HTTP_REFERER', '/')
        domain = Site.objects.get_current().domain
        abs_url = 'http://%s' % domain

        back_url = referer.replace(abs_url, '')
        response = http.HttpResponseRedirect(back_url if request.path != back_url else '/')

    return response


def login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated(),
        redirect_field_name=redirect_field_name,
        fail_callback=_user_anonymous_callback
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
try:
    from django.contrib.auth import get_user_model
except ImportError: # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()
from django.db import models
from django.utils import simplejson as json
from django.utils.translation import ugettext_lazy as _

from loginza import signals
from loginza.conf import settings

class IdentityManager(models.Manager):
    def from_loginza_data(self, loginza_data):
        try:
            identity = self.get(identity=loginza_data['identity'])
            # update data as some apps can use it, e.g. avatars
            identity.data = json.dumps(loginza_data)
            identity.save()
        except self.model.DoesNotExist:
            identity = self.create(
                identity=loginza_data['identity'],
                provider=loginza_data['provider'],
                data=json.dumps(loginza_data)
            )
        return identity


class UserMapManager(models.Manager):
    def for_identity(self, identity, request):
        try:
            user_map = self.get(identity=identity)
        except self.model.DoesNotExist:
            # if there is authenticated user - map identity to that user
            # if not - create new user and mapping for him
            if request.user.is_authenticated():
                user = request.user
            else:
                loginza_data = json.loads(identity.data)

                loginza_email = loginza_data.get('email', '')
                email = loginza_email if '@' in loginza_email else settings.DEFAULT_EMAIL

                # if nickname is not set - try to get it from email
                # e.g. vgarvardt@gmail.com -> vgarvardt
                loginza_nickname = loginza_data.get('nickname', None)
                if loginza_nickname is None or loginza_nickname == "":
                    username = email.split('@')[0]
                else:
                    username = loginza_nickname

                # check duplicate user name
                while True:
                    try:
                        existing_user = User.objects.get(username=username)
                        username = '%s%d' % (username, existing_user.id)
                    except User.DoesNotExist:
                        break

                user = User.objects.create_user(
                    username,
                    email
                )
            user_map = UserMap.objects.create(identity=identity, user=user)
            signals.created.send(request, user_map=user_map)
        return user_map


class Identity(models.Model):
    identity = models.CharField(_('identity'), max_length=255, unique=True)
    provider = models.CharField(_('provider'), max_length=255)
    data = models.TextField(_('data'))

    objects = IdentityManager()

    def __unicode__(self):
        return self.identity

    class Meta:
        ordering = ['id']
        verbose_name = _('identity')
        verbose_name_plural = _('identities')


class UserMap(models.Model):
    identity = models.OneToOneField(Identity, verbose_name=_('identity'))
    user = models.ForeignKey(User, verbose_name=_('user'))
    verified = models.BooleanField(_('active'), default=False, db_index=True)

    objects = UserMapManager()

    def __unicode__(self):
        return '%s [%s]' % (unicode(self.user), self.identity.provider)

    class Meta:
        ordering = ['user']
        verbose_name = _('user map')
        verbose_name_plural = _('user maps')

########NEW FILE########
__FILENAME__ = signals
# -*- coding:utf-8 -*-
from django import dispatch

# Creation of a new link between Django user and Loginza identity.
# Parameters:
# - sender - HttpRequest instance
# - user_map - loginza.models.UserMap instance
created = dispatch.Signal(providing_args=['user_map'])

# Loginza athentication returned error
# Parameters:
# - sender - HttpRequest instance
# - error - loginza.authentication.LoginzaError instance
error = dispatch.Signal(providing_args=['error'])

# Successfull completion Loginza authentication
# Parameters:
# - sender: HttpRequest instance
# - user: authenticated (may be newly created) user
# - identity: loginza identity (loginza.models.Identity) used for authentication
#
# A handler may return a HttpRespose instance which will be eventually
# returned from the completion view. If omitted a standard redirect will be
# used.
authenticated = dispatch.Signal(providing_args=['user', 'identity'])

# login_required decorator found that user is not logged in
# Parameters:
# - sender: HttpRequest instance
#
# A handler may return a HttpRespose instance which will be eventually
# returned from called view. If omitted redirect to previous page will be
# used.
login_required = dispatch.Signal()
########NEW FILE########
__FILENAME__ = loginza_widget
# -*- coding:utf-8 -*-
import urllib

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.template import Library, Node, TemplateSyntaxError
from django.template.defaulttags import kwarg_re
from django.utils.encoding import smart_str
from django.utils.translation import ugettext_lazy as _

from loginza.conf import settings

register = Library()

allowed_providers_def = {
    'google': _(u'Google Accounts'),
    'yandex': _(u'Yandex'),
    'mailruapi': _(u'Mail.ru API'),
    'mailru': _(u'Mail.ru'),
    'vkontakte': _(u'Vkontakte'),
    'facebook': _(u'Facebook'),
    'twitter': _(u'Twitter'),
    'odnoklassniki': _(u'Odnoklassniki'),
    'loginza': _(u'Loginza'),
    'myopenid': _(u'MyOpenID'),
    'webmoney': _(u'WebMoney'),
    'rambler': _(u'Rambler'),
    'flickr': _(u'Flickr'),
    'lastfm': _(u'Last.fm'),
    'verisign': _(u'Verisign'),
    'aol': _(u'AOL'),
    'openid': _(u'OpenID'),
    'livejournal': _(u'LiveJournal')
}

allowed_providers = {}
for key, value in allowed_providers_def.items():
    allowed_providers[key] = settings.PROVIDER_TITLES.get(key, value)

def _return_path(request, path=None):
    if path is not None and path not in settings.AMNESIA_PATHS:
        request.session['loginza_return_path'] = path
    return request.session.get('loginza_return_path', '/')


def _absolute_url(url):
    return 'http://%s%s' % (Site.objects.get_current().domain, url)


def return_url():
    return urllib.quote(_absolute_url(reverse('loginza.views.return_callback')), '')


def _providers_set(kwargs):
    providers_set = []

    providers_list = kwargs['providers_set'] if 'providers_set' in kwargs else settings.DEFAULT_PROVIDERS_SET
    if providers_list is not None:
        providers = providers_list.split(',')
        for provider in providers:
            if provider in allowed_providers:
                providers_set.append(provider)

    return providers_set


def providers(kwargs):
    params = []

    providers_set = _providers_set(kwargs)
    if len(providers_set) > 0:
        params.append('providers_set=' + ','.join(providers_set))

    provider = kwargs['provider'] if 'provider' in kwargs else settings.DEFAULT_PROVIDER
    if provider in allowed_providers:
        params.append('provider=' + provider)

    return ('&'.join(params) + '&') if len(params) > 0 else ''


def id_attr(kwargs):
    return 'id="%s"' % kwargs.get('id') if kwargs.get('id') else ''


def iframe_template(kwargs, caption=''):
    return """<script src="http://loginza.ru/js/widget.js" type="text/javascript"></script>
<iframe src="http://loginza.ru/api/widget?overlay=loginza&%(providers)slang=%(lang)s&token_url=%(return-url)s"
style="width:%(width)s;height:%(height)s;" scrolling="no" frameborder="no" %(id)s></iframe>""" % {
        'return-url': return_url(),
        'lang': kwargs['lang'],
        'providers': providers(kwargs),
        'caption': caption,
        'width': kwargs.get('width', settings.IFRAME_WIDTH),
        'height': kwargs.get('height', settings.IFRAME_HEIGHT),
        'id': id_attr(kwargs)
    }


def button_template(kwargs, caption):
    return """<script src="http://loginza.ru/js/widget.js" type="text/javascript"></script>
<a href="http://loginza.ru/api/widget?%(providers)slang=%(lang)s&token_url=%(return-url)s" rel="nofollow" class="loginza" %(id)s>
    <img src="%(button-img)s" alt="%(caption)s" title="%(caption)s"/>
</a>""" % {
        'button-img': settings.BUTTON_IMG_URL,
        'return-url': return_url(),
        'caption': caption,
        'lang': kwargs['lang'],
        'providers': providers(kwargs),
        'id': id_attr(kwargs)
    }


def icons_template(kwargs, caption):
    def icons():
        providers_set = _providers_set(kwargs)
        # if providers set is not set explicitly - all providers are used
        if len(providers_set) < 1:
            setting_icons = settings.ICONS_PROVIDERS
            providers_set = setting_icons.split(',') if setting_icons is not None else allowed_providers.keys()

        imgs = []
        for provider in providers_set:
            if provider in settings.ICONS_IMG_URLS:
                img_url = settings.ICONS_IMG_URLS[provider]
            else:
                img_url = 'http://loginza.ru/img/widget/%s_ico.gif' % provider

            imgs.append('<img src="%(img_url)s" alt="%(title)s" title="%(title)s">' % {
                'img_url': img_url,
                'title': allowed_providers[provider]
            })
        return '\r\n'.join(imgs)

    return """<script src="http://loginza.ru/js/widget.js" type="text/javascript"></script>
%(caption)s
<a href="https://loginza.ru/api/widget?%(providers)slang=%(lang)s&token_url=%(return-url)s" rel="nofollow" class="loginza" %(id)s>
    %(icons)s
</a>""" % {
        'return-url': return_url(),
        'caption': caption,
        'lang': kwargs['lang'],
        'providers': providers(kwargs),
        'icons': icons(),
        'id': id_attr(kwargs)
    }


def string_template(kwargs, caption):
    return """<script src="http://loginza.ru/js/widget.js" type="text/javascript"></script>
<a href="http://loginza.ru/api/widget?%(providers)slang=%(lang)s&token_url=%(return-url)s" rel="nofollow" class="loginza" %(id)s>
    %(caption)s
</a>""" % {
        'return-url': return_url(),
        'caption': caption,
        'lang': kwargs['lang'],
        'providers': providers(kwargs),
        'id': id_attr(kwargs)
    }


class LoginzaWidgetNode(Node):
    def __init__(self, html_template, caption, kwargs, asvar):
        self.html_template = html_template
        self.caption = caption
        self.kwargs = kwargs
        self.asvar = asvar

    def render(self, context):
        kwargs = dict([(smart_str(k, 'ascii'), v.resolve(context)) for k, v in self.kwargs.items()])
        if 'lang' not in kwargs:
            kwargs['lang'] = settings.DEFAULT_LANGUAGE

        # save current path, so if user will be logged with loginza
        # he will be redirected back to the page he for login
        _return_path(context['request'], context['request'].path)

        html = self.html_template(kwargs, self.caption)
        if self.asvar:
            context[self.asvar] = html
            html = ''

        return html


def _loginza_widget(parser, token, html_template):
    def unquote(s):
        if s[0] in ('"', "'"): s = s[1:]
        if s[-1] in ('"', "'"): s = s[:-1]
        return s

    bits = token.split_contents()
    if len(bits) < 2 and html_template != iframe_template:
        raise TemplateSyntaxError("'%s' takes at least one argument (caption)" % bits[0])

    caption = '' if html_template == iframe_template else unquote(bits[1])

    kwargs = {}
    asvar = None
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]

    # Now all the bits are parsed into new format,
    # process them as template vars
    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)
            if not match:
                raise TemplateSyntaxError("Malformed arguments to loginza widget tag")
            name, value = match.groups()
            kwargs[name] = parser.compile_filter(value)

    return LoginzaWidgetNode(html_template, caption, kwargs, asvar)


@register.tag
def loginza_iframe(parser, token):
    return _loginza_widget(parser, token, iframe_template)


@register.tag
def loginza_button(parser, token):
    return _loginza_widget(parser, token, button_template)


@register.tag
def loginza_icons(parser, token):
    return _loginza_widget(parser, token, icons_template)


@register.tag
def loginza_string(parser, token):
    return _loginza_widget(parser, token, string_template)

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
__FILENAME__ = urls
from django.conf.urls.defaults import *

from loginza import views

urlpatterns = patterns(
    '',
    url(r'return_callback/$', views.return_callback, name='loginza_return')
)
  
########NEW FILE########
__FILENAME__ = views
# -*- coding:utf-8 -*-
from urllib import urlencode
from urllib2 import urlopen
from hashlib import md5

from django import http
from django.utils import simplejson as json
from django.contrib import auth
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from loginza import models, signals
from loginza.authentication import LoginzaError
from loginza.templatetags.loginza_widget import _return_path
from loginza.conf import settings

@require_POST
@csrf_exempt
def return_callback(request):
    token = request.POST.get('token', None)
    if token is None:
        return http.HttpResponseBadRequest()

    params = {'token': token}
    if settings.WIDGET_ID is not None and settings.API_SIGNATURE is not None:
        sig = md5(token + settings.API_SIGNATURE).hexdigest()
        params.update(id=settings.WIDGET_ID, sig=sig)

    f = urlopen('http://loginza.ru/api/authinfo?%s' % urlencode(params))
    result = f.read()
    f.close()

    data = json.loads(result)

    if 'error_type' in data:
        signals.error.send(request, error=LoginzaError(data))
        return redirect(_return_path(request))

    identity = models.Identity.objects.from_loginza_data(data)
    user_map = models.UserMap.objects.for_identity(identity, request)
    response = redirect(_return_path(request))
    if request.user.is_anonymous():
        user = auth.authenticate(user_map=user_map)
        results = signals.authenticated.send(request, user=user, identity=identity)
        for callback, result in results:
            if isinstance(result, http.HttpResponse):
                response = result
                break

    return response

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.normpath(os.path.abspath(PROJECT_ROOT))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_ROOT, 'sqlite.db'),                      # Or path to database file if using sqlite3.
#        'USER': '',                      # Not used with sqlite3.
#        'PASSWORD': '',                  # Not used with sqlite3.
#        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Moscow'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'ru'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'public', 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'public', 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = 'nk(2htuqhim#)=t(8rs_^*e8e@nnacmjr+_v3xnxc@t!f(do5#'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'loginza.authentication.LoginzaBackend',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
#    'django.core.context_processors.debug',
    'django.core.context_processors.request',
#    'django.core.context_processors.i18n',
#    'django.core.context_processors.media',
#    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'loginza',
    'users',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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

# can't use reverse url resolver here (raises ImportError),
# so we should carefully control paths
LOGINZA_AMNESIA_PATHS = ('/users/complete_registration/',)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()


urlpatterns = patterns('',
	url(r'^admin/', include(admin.site.urls)),

    url(r'^$', TemplateView.as_view(template_name='base.html')),

    url(r'^loginza/', include('loginza.urls')),
    url(r'^users/', include('users.urls')),  
)

########NEW FILE########
__FILENAME__ = forms
# -*- coding:utf-8 -*-
from django import forms
from django.contrib.auth.models import User


class CompleteReg(forms.Form):

    username = forms.RegexField(label=u'Имя пользователя', max_length=30, min_length=4, 
                                required=True, regex=r'^[\w.@+-]+$') 
    email = forms.EmailField(label=u'Email', required=True) 


    def __init__(self, user_id, *args, **kwargs):
        super(CompleteReg, self).__init__(*args, **kwargs)
        self.user_id = user_id

    def clean_username(self):
        if self.cleaned_data['username']:
            try: 
                u = User.objects.exclude(id=self.user_id).get(username=self.cleaned_data['username'])
            # if username is unique - it's ok
            except User.DoesNotExist: 
                u = None

            if u is not None:
                raise forms.ValidationError(u'Пользователь с таким именем уже зарегистрирован')
        return self.cleaned_data['username']

    def clean_email(self):
        if self.cleaned_data['email']:
            try: 
                u = User.objects.exclude(id=self.user_id).get(email=self.cleaned_data['email'])
            # if email is unique - it's ok
            except User.DoesNotExist: 
                u = None

            if u is not None:
                raise forms.ValidationError(u'Пользователь с этим адресом уже зарегистрирован')
        return self.cleaned_data['email']
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from .views import complete_registration


urlpatterns = patterns('',
    url(r'^complete_registration/$', complete_registration, name='users_complete_registration'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', name='users_logout'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding:utf-8 -*-
from django import http
from django.contrib import messages, auth
from django.shortcuts import redirect, render_to_response
from django.core.urlresolvers import reverse
from django.template.context import RequestContext

from .forms import CompleteReg

from loginza import signals, models
from loginza.templatetags.loginza_widget import _return_path


def loginza_error_handler(sender, error, **kwargs):
    messages.error(sender, error.message)

signals.error.connect(loginza_error_handler)

def loginza_auth_handler(sender, user, identity, **kwargs):
    try:
        # it's enough to have single identity verified to treat user as verified
        models.UserMap.objects.get(user=user, verified=True)
        auth.login(sender, user)
    except models.UserMap.DoesNotExist:
        sender.session['users_complete_reg_id'] = identity.id
        return redirect(reverse('users.views.complete_registration'))

signals.authenticated.connect(loginza_auth_handler)

def loginza_login_required(sender, **kwargs):
    messages.warning(sender, u'Функция доступна только авторизованным пользователям.')

signals.login_required.connect(loginza_login_required)


def complete_registration(request):
    if request.user.is_authenticated():
        return http.HttpResponseForbidden(u'Вы попали сюда по ошибке')
    try:
        identity_id = request.session.get('users_complete_reg_id', None)
        user_map = models.UserMap.objects.get(identity__id=identity_id)
    except models.UserMap.DoesNotExist:
        return http.HttpResponseForbidden(u'Вы попали сюда по ошибке')
    if request.method == 'POST':
        form = CompleteReg(user_map.user.id, request.POST)
        if form.is_valid():
            user_map.user.username = form.cleaned_data['username']
            user_map.user.email = form.cleaned_data['email']
            user_map.user.save()

            user_map.verified = True
            user_map.save()

            user = auth.authenticate(user_map=user_map)
            auth.login(request, user)

            messages.info(request, u'Добро пожаловать!')
            del request.session['users_complete_reg_id']
            return redirect(_return_path(request))
    else:
        form = CompleteReg(user_map.user.id, initial={
            'username': user_map.user.username, 'email': user_map.user.email,
            })

    return render_to_response('users/complete_reg.html',
                              {'form': form},
                              context_instance=RequestContext(request),
                              )
########NEW FILE########
