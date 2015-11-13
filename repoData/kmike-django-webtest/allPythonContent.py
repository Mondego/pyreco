__FILENAME__ = backends
from __future__ import absolute_import
from django.contrib.auth.backends import RemoteUserBackend
from .compat import from_wsgi_safe_string

class WebtestUserBackend(RemoteUserBackend):
    """ Auth backend for django-webtest auth system """

    def authenticate(self, django_webtest_user):
        return super(WebtestUserBackend, self).authenticate(django_webtest_user)

    def clean_username(self, username):
        return from_wsgi_safe_string(username)


########NEW FILE########
__FILENAME__ = compat
import sys
import urllib

PY3 = sys.version_info[0] == 3

if PY3:
    from urllib import parse as urlparse

    def to_string(s):
        if isinstance(s, str):
            return s
        return str(s, 'latin1')

    def to_wsgi_safe_string(s):
        return urlparse.quote(to_string(s))

    def from_wsgi_safe_string(s):
        return urlparse.unquote(s)

else:
    import urlparse

    def to_string(s):
        return str(s)

    def to_wsgi_safe_string(s):
        return to_string(urllib.quote(s.encode('utf8')))

    def from_wsgi_safe_string(s):
        return urllib.unquote(s).decode('utf8')




########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.contrib import auth

class WebtestUserMiddleware(RemoteUserMiddleware):
    """
    Middleware for utilizing django-webtest simplified auth
    ('user' arg for self.app.post and self.app.get).

    Mostly copied from RemoteUserMiddleware, but the auth backend is changed
    (by changing ``auth.authenticate`` arguments) in order to keep
    RemoteUser backend untouched during django-webtest auth.
    """

    header = "WEBTEST_USER"

    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The django-webtest auth middleware requires the "
                "'django.contrib.auth.middleware.AuthenticationMiddleware' "
                "to be installed. Add it to your MIDDLEWARE_CLASSES setting "
                "or disable django-webtest auth support "
                "by setting 'setup_auth' property of your WebTest subclass "
                "to False."
            )
        try:
            username = request.META[self.header]
        except KeyError:
            # If specified header doesn't exist then return (leaving
            # request.user set to AnonymousUser by the
            # AuthenticationMiddleware).
            return
        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        if request.user.is_authenticated():
            if hasattr(request.user, "get_username"):
                authenticated_username = request.user.get_username()
            else:
                authenticated_username = request.user.username
            if authenticated_username == self.clean_username(username, request):
                return
        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        user = auth.authenticate(django_webtest_user=username)
        if user:
            # User is valid.  Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            auth.login(request, user)


class DisableCSRFCheckMiddleware(object):
    def process_request(self, request):
        request._dont_enforce_csrf_checks = True

########NEW FILE########
__FILENAME__ = response
# -*- coding: utf-8 -*-
from django.test import Client
from django.http import SimpleCookie
from webtest import TestResponse
from django_webtest.compat import urlparse

class DjangoWebtestResponse(TestResponse):
    """
    WebOb's Response quacking more like django's HttpResponse.

    This is here to make more django's TestCase asserts work,
    not to provide a generally useful proxy.
    """
    streaming = False

    @property
    def status_code(self):
        return self.status_int

    @property
    def _charset(self):
        return self.charset

    @property
    def content(self):
        return self.body

    @property
    def url(self):
        return self['location']

    @property
    def client(self):
        client = Client()
        client.cookies = SimpleCookie()
        for k,v in self.test_app.cookies.items():
            client.cookies[k] = v
        return client

    def __getitem__(self, item):
        item = item.lower()
        if item == 'location':
            # django's test response returns location as http://testserver/,
            # WebTest returns it as http://localhost:80/
            e_scheme, e_netloc, e_path, e_query, e_fragment = urlparse.urlsplit(self.location)
            if e_netloc == 'localhost:80':
                e_netloc = 'testserver'
            return urlparse.urlunsplit([e_scheme, e_netloc, e_path, e_query, e_fragment])
        for header, value in self.headerlist:
            if header.lower() == item:
                return value
        raise KeyError(item)

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
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    sys.argv.insert(1, 'test')

    if len(sys.argv) == 2:
        sys.argv.append('testapp_tests')

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for django_webtest_tests project.
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
join = lambda p: os.path.abspath(os.path.join(PROJECT_ROOT, p))

sys.path.insert(0, join('..'))


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': join('db.sqlite'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

if os.environ.get('USE_POSTGRES'):
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
    DATABASES['default']['NAME'] = 'django_webtest_tests'

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
MEDIA_ROOT = join('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5mcs97ar-(nnxhfkx0%^+0^sr!e(ax=x$2-!8dqy25ff-l1*a='

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
    'testapp_tests.middleware.UserMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    join('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    'django_webtest',
    'django_webtest_tests',
    'django_webtest_tests.testapp_tests',
)

LOGIN_REDIRECT_URL = '/template/index.html'

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from __future__ import absolute_import

class UserMiddleware(object):
    def process_request(self, request):
        request.user.processed = True
########NEW FILE########
__FILENAME__ = models
import django

if django.get_version() >= "1.5":
    from django.contrib.auth.models import AbstractBaseUser
    from django.db import models


    class CustomUser(AbstractBaseUser):
        email = models.EmailField(
            max_length=255,
            unique=True,
            db_index=True,
        )
        USERNAME_FIELD = 'email'

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
from webtest import AppError, TestApp

import django
from django_webtest import WebTest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

class MethodsTest(WebTest):

    csrf_checks = False

    def assertMethodWorks(self, meth, name):
        response = meth('/')
        self.assertEqual(response.status_int, 200)
        response.mustcontain(name)
        #self.assertTrue(name in response)

    def assertMethodWorksXHR(self, meth, name):
        try:
            response = meth('/', xhr=True)
        except TypeError as e:
            # for webtest < 2
            self.assertIn('xhr', e.message)
        else:
            # for webtest == 2
            self.assertEqual(response.status_int, 200)
            response.mustcontain(name)

    def test_get(self):
        self.assertMethodWorks(self.app.get, 'GET')

    def test_post(self):
        self.assertMethodWorks(self.app.post, 'POST')

    def test_put(self):
        self.assertMethodWorks(self.app.put, 'PUT')

    def test_delete(self):
        self.assertMethodWorks(self.app.delete, 'DELETE')

    def test_get_xhr(self):
        self.assertMethodWorksXHR(self.app.get, 'GET')

    def test_post_xhr(self):
        self.assertMethodWorksXHR(self.app.post, 'POST')

    def test_put_xhr(self):
        self.assertMethodWorksXHR(self.app.put, 'PUT')

    def test_delete_xhr(self):
        self.assertMethodWorksXHR(self.app.delete, 'DELETE')

    if hasattr(TestApp, 'patch'):  # old WebTest versions don't have 'patch' method
        def test_patch(self):
            self.assertMethodWorks(self.app.patch, 'PATCH')

    def test_head(self):
        response = self.app.head('/')
        self.assertEqual(response.status_int, 200)
        assert response.body == b''

    def test_options(self):
        self.assertMethodWorks(self.app.options, 'OPTIONS')


class PostRequestTest(WebTest):
    csrf_checks = False

    def test_post_request(self):
        response = self.app.post('/')
        self.assertEqual(response.status_int, 200)
        self.assertTrue('POST' in response)

    def test_404_response(self):
        self.assertRaises(AppError, self.app.get, '/404/')


class CsrfProtectionTest(WebTest):
    def test_csrf_failed(self):
        response = self.app.post('/', expect_errors=True)
        self.assertEqual(response.status_int, 403)


class FormSubmitTest(WebTest):

    def test_form_submit(self):
        page = self.app.get(reverse('check_password'))
        page.form['password'] = 'bar'
        page_with_errors = page.form.submit()

        assert 'Incorrect password' in page_with_errors

        page_with_errors.form['password'] = 'foo'
        page_with_errors.form.submit().follow() # check for 302 response


class GetFormSubmitTest(WebTest):

    def test_form_submit(self):
        page = self.app.get(reverse('search'))
        page.form['q'] = 'bar'
        response = page.form.submit()
        self.assertEqual(response.context['q'], 'bar')


class TemplateContextTest(WebTest):
    def test_rendered_templates(self):
        response = self.app.get('/template/index.html')
        self.assertTrue(hasattr(response, 'context'))
        self.assertTrue(hasattr(response, 'template'))

        self.assertEqual(response.template.name, 'index.html')
        self.assertEqual(response.context['bar'], True)
        self.assertEqual(response.context['spam'], None)
        self.assertRaises(KeyError, response.context.__getitem__, 'invalid')

    def test_multiple_templates(self):
        response = self.app.get('/template/complex.html')
        self.assertEqual(len(response.template), 4)
        self.assertEqual(response.template[0].name, 'complex.html')
        self.assertEqual(response.template[1].name, 'include.html')
        self.assertEqual(response.template[2].name, 'include.html')
        self.assertEqual(response.template[3].name, 'include.html')

        self.assertEqual(response.context['foo'], ('a', 'b', 'c'))
        self.assertEqual(response.context['bar'], True)
        self.assertEqual(response.context['spam'], None)


class BaseAuthTest(WebTest):

    def setUp(self):
        self.user = User.objects.create_user('foo', 'example@example.com', '123')

    def _login(self, username, password):
        form = self.app.get(reverse('auth_login')).form
        form['username'] = username
        form['password'] = password
        return form.submit()

    def assertCanLogin(self, user):
        response = self.app.get('/template/index.html', user=user)
        res_user = response.context['user']
        assert res_user.is_authenticated()

        if isinstance(user, User):
            self.assertEqual(res_user, user)
        else:
            self.assertEqual(res_user.username, user)


class AuthTest(BaseAuthTest):

    def test_not_logged_in(self):
        response = self.app.get('/template/index.html')
        user = response.context['user']
        assert not user.is_authenticated()

    def test_logged_using_username(self):
        self.assertCanLogin('foo')

    def test_logged_using_native_username(self):
        self.assertCanLogin(str('foo'))

    def test_logged_using_unicode_username(self):
        self.assertCanLogin('ƒøø')

    def test_logged_using_instance(self):
        self.assertCanLogin(self.user)

    def test_logged_using_unicode_instance(self):
        user = User.objects.create_user('ƒøø', 'example@example.com', '123')
        self.assertCanLogin(user)

    def test_auth_is_enabled(self):
        from django.conf import settings

        auth_middleware = 'django_webtest.middleware.WebtestUserMiddleware'
        assert auth_middleware in settings.MIDDLEWARE_CLASSES
        assert 'django_webtest.backends.WebtestUserBackend' in settings.AUTHENTICATION_BACKENDS

        dependency_index = settings.MIDDLEWARE_CLASSES.index(
            'django.contrib.auth.middleware.AuthenticationMiddleware')

        self.assertEqual(
            settings.MIDDLEWARE_CLASSES.index(auth_middleware),
            dependency_index +1,
        )

    def test_custom_middleware(self):
        response = self.app.get('/template/index.html', user=self.user)
        user = response.context['user']
        self.assertTrue(user.processed)

    def test_standard_auth(self):
        resp = self._login(self.user.username, '123').follow()
        user = resp.context['user']
        self.assertEqual(user, self.user)

    def test_reusing_custom_user(self):
        if django.get_version() >= "1.5":
            from testapp_tests.models import CustomUser
            with self.settings(AUTH_USER_MODEL = 'testapp_tests.CustomUser'):
                custom_user = CustomUser.objects.create(
                        email="custom@example.com")
                custom_user.set_password("123")
                custom_user.save()

                # Let the middleware logs the user in
                self.app.get('/template/index.html', user=custom_user)

                # Middleware authentication check shouldn't crash
                response = self.app.get('/template/index.html',
                        user=custom_user)
                user = response.context['user']
                assert user.is_authenticated()
                self.assertEqual(user, custom_user)

    def test_normal_user(self):
        """Make sure the fix for custom users in django 1.5 doesn't break
        normal django users"""
        self.app.get('/template/index.html', user=self.user)
        self.app.get('/template/index.html', user=self.user)


class EnvironTest(BaseAuthTest):

    extra_environ = {'REMOTE_ADDR': '127.0.0.2'}

    def test_extra_environ_reset(self):
        resp = self.app.get('/template/index.html', user=self.user)
        environ = resp.request.environ
        self.assertEqual(environ['WEBTEST_USER'], 'foo')
        self.assertEqual(environ['REMOTE_ADDR'], '127.0.0.2')

        resp2 = self.app.get('/template/index.html')
        environ = resp2.request.environ
        self.assertTrue('WEBTEST_USER' not in environ)
        self.assertEqual(environ['REMOTE_ADDR'], '127.0.0.2')

        resp3 = self.app.get('/template/index.html',
                             extra_environ={'REMOTE_ADDR': '127.0.0.1'})
        environ = resp3.request.environ
        self.assertEqual(environ['REMOTE_ADDR'], '127.0.0.1')


class RenewAppTest(BaseAuthTest):

    def test_renew_app(self):
        self._login(self.user.username, '123').follow()

        # auth cookie is preserved between self.app.get calls
        page1 = self.app.get('/template/form.html')
        self.assertEqual(page1.context['user'], self.user)

        self.renew_app()

        # cookies were dropped
        page2 = self.app.get('/template/form.html')
        self.assertTrue(page2.context['user'].is_anonymous())

        # but cookies are still there while browsing from stored page
        page1_1 = page1.click('Login')
        self.assertEqual(page1_1.context['user'], self.user)



class DjangoAssertsTest(BaseAuthTest):

    def test_assert_template_used(self):
        response = self.app.get('/template/index.html')
        self.assertTemplateUsed(response, 'index.html')
        self.assertTemplateNotUsed(response, 'complex.html')

        complex_response = self.app.get('/template/complex.html')
        self.assertTemplateUsed(complex_response, 'complex.html')
        self.assertTemplateUsed(complex_response, 'include.html')
        self.assertTemplateNotUsed(complex_response, 'foo.html')

    def test_assert_form_error(self):
        page = self.app.get(reverse('check_password'))
        page.form['password'] = 'bar'
        page_with_errors = page.form.submit()
        self.assertFormError(page_with_errors, 'form', 'password', 'Incorrect password.')

    def test_assert_contains(self):
        response = self.app.get('/template/index.html')
        self.assertContains(response, 'Hello', 1)
        self.assertNotContains(response, 'Good bye!')

    def test_assert_contains_unicode(self):
        response = self.app.get('/template/index.html')
        self.assertContains(response, 'привет', 2)

    def test_assert_redirects(self):
        page = self.app.get(reverse('check_password'))
        page.form['password'] = 'foo'
        resp = page.form.submit()
        self.assertRedirects(resp, '/')

    def test_redirects_noauth(self):
        self.app.get(reverse('redirect-to-protected')).follow(status=302)

    def test_redirects(self):
        self.app.get(reverse('redirect-to-protected'), user=self.user).follow()

    def test_assert_redirects_auth(self):
        page = self.app.get(reverse('redirect-to-protected'), user=self.user)
        self.assertRedirects(page, reverse('protected'))



class DisableAuthSetupTest(WebTest):
    setup_auth = False

    def test_no_auth(self):
        from django.conf import settings
        assert 'django_webtest.middleware.WebtestUserMiddleware' not in settings.MIDDLEWARE_CLASSES
        assert 'django_webtest.backends.WebtestUserBackend' not in settings.AUTHENTICATION_BACKENDS


class TestSession(WebTest):

    def test_session_not_set(self):
        response = self.app.get('/')
        self.assertEqual(response.status_int, 200)
        self.assertEqual({}, self.app.session)

    def test_sessions_disabled(self):
        from django.conf import settings

        apps = list(settings.INSTALLED_APPS)
        apps.remove("django.contrib.sessions")
        settings.INSTALLED_APPS= apps

        response = self.app.get('/')
        self.assertEqual(response.status_int, 200)
        self.assertEqual({}, self.app.session)

    def test_session_not_empty(self):
        response = self.app.get(reverse('set_session'))
        self.assertEqual('foo', self.app.session['test'])


class TestHeaderAccess(WebTest):
    def test_headers(self):
        response = self.app.get('/')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        self.assertEqual(response['content-type'], 'text/html; charset=utf-8')

    def test_bad_header(self):
        def access_bad_header():
            response = self.app.get('/')
            response['X-Unknown-Header']
        self.assertRaises(KeyError, access_bad_header)


########NEW FILE########
__FILENAME__ = views
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext

class PasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput())

    def clean_password(self):
        if self.cleaned_data['password'] != 'foo':
            raise forms.ValidationError('Incorrect password.')
        return self.cleaned_data['password']

def check_password(request):
    form = PasswordForm(request.POST or None)
    if form.is_valid():
        return HttpResponseRedirect('/')
    ctx = RequestContext(request, {'form': form})
    return render_to_response('form.html', ctx)


class SearchForm(forms.Form):
    q = forms.CharField(required=False)

def search(request):
    form = SearchForm(request.GET)
    q = None
    if form.is_valid():
        q = form.cleaned_data['q']
    ctx = RequestContext(request, {'form': form, 'q': q})
    return render_to_response('get_form.html', ctx)

def set_session(request):
    request.session['test'] = 'foo'
    return HttpResponseRedirect('/')

def redirect_to_protected(request):
    return redirect('protected')

@login_required
def protected(request):
    return HttpResponse('ok')

########NEW FILE########
__FILENAME__ = urls

# prevent DeprecationWarning for more recent django versions
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url, handler404, handler500

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

def simple_method_test(request):
    return HttpResponse(str(request.method))

def simple_template_render(request, template_name):
    return render_to_response(template_name, {
        'foo': ('a', 'b', 'c'),
        'bar': True,
        'spam': None,
    }, context_instance=RequestContext(request))

urlpatterns = patterns('',
    url(r'^$', simple_method_test, name='simple-method-test'),
    url(r'^template/(.*)$', simple_template_render, name='simple-template-test'),
    url(r'^check-password/$', 'testapp_tests.views.check_password', name='check_password'),
    url(r'^search/$', 'testapp_tests.views.search', name='search'),
    url(r'^login/$', 'django.contrib.auth.views.login', name='auth_login'),
    url(r'^set-session/$', 'testapp_tests.views.set_session', name='set_session'),
    url(r'^protected/$', 'testapp_tests.views.protected', name='protected'),
    url(r'^redirect-to-protected/$', 'testapp_tests.views.redirect_to_protected', name='redirect-to-protected'),
)

########NEW FILE########
