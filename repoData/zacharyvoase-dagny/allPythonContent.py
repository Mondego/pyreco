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
# -*- coding: utf-8 -*-
# Django settings for example project.

import os
import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Zachary Voase', 'z@zacharyvoase'),
)

MANAGERS = ADMINS

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

DB_DIR = os.path.join(PROJECT_ROOT, 'db')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DB_DIR, 'development.sqlite3'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

TIME_ZONE = 'GMT'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1

USE_I18N = False
USE_L10N = True

MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/media/admin/'

SECRET_KEY = 'c-!9fgws_aa5fyybk97da5xz63dxhuuxczlal76k!5d#i7vuo&'

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
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',

    'users',
)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

from dagny.urls import resources, resource, rails, atompub
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^users/', resources('users.resources.User', name='User')),

    # Stub routes for the routing tests.
    (r'^users-atompub/', atompub.resources('users.resources.User',
                                           name='UserAtomPub')),
    (r'^users-rails', rails.resources('users.resources.User',
                                      name='UserRails')),

    (r'^account/', resource('users.resources.Account', name='Account')),
    (r'^account-atompub/', atompub.resource('users.resources.Account',
                                            name='AccountAtomPub')),
    (r'^account-rails', rails.resource('users.resources.Account',
                                        name='AccountRails')),

    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = models
## Empty files deserve poetry.

# She dwelt among the untrodden ways
# Beside the springs of Dove,
# A Maid whom there were none to praise
# And very few to love:
#
# A violet by a mossy stone
# Half hidden from the eye!
# Fair as a star, when only one
# Is shining in the sky.
#
# She lived unknown, and few could know
# When Lucy ceased to be;
# But she is in her grave, and oh,
# The difference to me!
#
# -- William Wordsworth

########NEW FILE########
__FILENAME__ = resources
# -*- coding: utf-8 -*-

from dagny import Resource, action
from dagny.renderer import Skip
from django.contrib.auth import forms, models
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
import simplejson


class User(Resource):

    template_path_prefix = 'auth/'

    @action
    def index(self):
        self.users = models.User.objects.all()

    @index.render.json
    def index(self):
        return json_response([user_to_dict(user) for user in self.users])

    # Stub to test that skipping works.
    @index.render.xml
    def index(self):
        raise Skip

    @action
    def new(self):
        self.form = forms.UserCreationForm()

    @action
    def create(self):
        self.form = forms.UserCreationForm(self.request.POST)
        if self.form.is_valid():
            self.user = self.form.save()
            return redirect('User#show', str(self.user.id))

        return self.new.render(status=403)

    @action
    def show(self, user_id):
        self.user = get_object_or_404(models.User, id=int(user_id))

    @show.render.json
    def show(self):
        return json_response(user_to_dict(self.user))

    @action
    def edit(self, user_id):
        self.user = get_object_or_404(models.User, id=int(user_id))
        self.form = forms.UserChangeForm(instance=self.user)

    @action
    def update(self, user_id):
        self.user = get_object_or_404(models.User, id=int(user_id))
        self.form = forms.UserChangeForm(self.request.POST, instance=self.user)
        if self.form.is_valid():
            self.form.save()
            return redirect('User#show', str(self.user.id))

        return self.edit.render(status=403)

    @action
    def destroy(self, user_id):
        self.user = get_object_or_404(models.User, id=int(user_id))
        self.user.delete()
        return redirect('User#index')


# A stub resource for the routing tests.
class Account(Resource):

    template_path_prefix = 'auth/'

    @action
    @action.deco(login_required)
    def show(self):
        return

    @show.render.json
    def show(self):
        return json_response({'username': self.request.user.username})


def json_response(data):
    return HttpResponse(content=simplejson.dumps(data),
                        content_type='application/json')

def user_to_dict(user):
    return {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }

########NEW FILE########
__FILENAME__ = test_decoration
import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase


class DecoratorTest(TestCase):

    def test_login_required_when_logged_out_redirects_to_login_url(self):
        response = self.client.get('/account/')
        assert response.status_code == 302
        redirected_to = urlparse.urlparse(response['location'])
        assert redirected_to.path == settings.LOGIN_URL

    def test_login_required_when_logged_in_does_not_redirect(self):
        user = User.objects.create_user(username='someuser',
                                        email='someuser@example.com',
                                        password='password')
        assert self.client.login(username='someuser', password='password')

        response = self.client.get('/account/')
        assert response.status_code == 200
        assert response.templates[0].name == 'auth/account/show.html'

    def test_login_required_when_logged_in_dispatches_to_renderer_correctly(self):
        user = User.objects.create_user(username='someuser',
                                        email='someuser@example.com',
                                        password='password')
        assert self.client.login(username='someuser', password='password')

        response = self.client.get('/account/?format=json')
        assert response.status_code == 200
        assert response['content-type'] == 'application/json'

########NEW FILE########
__FILENAME__ = test_integration
# -*- coding: utf-8 -*-

import datetime

from django.contrib.auth import models
from django.test import TestCase
from django.utils import formats, simplejson


class UserResourceTest(TestCase):

    def create_user(self):
        self.user = models.User.objects.create_user("zack", "z@zacharyvoase.com", "hello")

    def user_json(self):
        return {
            "username": self.user.username,
            "first_name": "",
            "last_name": ""
        }

    def test_index(self):
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 200)
        self.assert_('<a href="/users/new/">' in response.content)

    def test_index_json(self):
        self.create_user()

        response1 = self.client.get("/users/?format=json")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(simplejson.loads(response1.content), [self.user_json()])

        response2 = self.client.get("/users/", HTTP_ACCEPT="application/json")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(simplejson.loads(response2.content), [self.user_json()])

    def test_new(self):
        response = self.client.get("/users/new/")
        self.assertEqual(response.status_code, 200)
        self.assert_('<form method="post" action="/users/">' in response.content)

    def test_create(self):
        initial_user_count = models.User.objects.count()

        response = self.client.post("/users/", {
            "username": "zack",
            "password1": "hello",
            "password2": "hello"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/users/1/')

        eventual_user_count = models.User.objects.count()
        self.assertEqual(eventual_user_count, initial_user_count + 1)

    def test_create_invalid(self):
        initial_user_count = models.User.objects.count()
        response = self.client.post("/users/", {
            "username": "!!",
            "password1": "foo",
            "password2": "bar"
        })
        self.assertEqual(response.status_code, 403)
        eventual_user_count = models.User.objects.count()
        self.assertEqual(eventual_user_count, initial_user_count)

    def test_show(self):
        self.create_user()

        response = self.client.get("/users/%d/" % self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assert_("Username: %s" % self.user.username in response.content)

    def test_show_json(self):
        self.create_user()

        response1 = self.client.get("/users/%d/?format=json" % self.user.id)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(simplejson.loads(response1.content), self.user_json())

        response2 = self.client.get("/users/%d/" % self.user.id,
                                    HTTP_ACCEPT="application/json")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(simplejson.loads(response2.content), self.user_json())

    def test_edit(self):
        self.create_user()

        response = self.client.get("/users/%d/edit/" % self.user.id)
        self.assertEqual(response.status_code, 200)
        self.assert_('<form method="post" action="/users/%d/">' % self.user.id in response.content)

    def test_update(self):
        self.create_user()

        response = self.client.post("/users/%d/" % self.user.id, {
            "username": self.user.username,
            "first_name": "Zachary",
            "last_name": "Voase",
            "email": "z@zacharyvoase.com",
            "password": self.user.password,
            "last_login": formats.localize_input(datetime.datetime.now()),
            "date_joined": formats.localize_input(datetime.datetime.now()),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/users/1/')

        self.user = models.User.objects.get(id=self.user.id)
        self.assertEqual(self.user.first_name, "Zachary")
        self.assertEqual(self.user.last_name, "Voase")

    def test_destroy(self):
        self.create_user()

        initial_user_count = models.User.objects.count()

        response = self.client.delete("/users/%d/" % self.user.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], "http://testserver/users/")

        eventual_user_count = models.User.objects.count()
        self.assertEqual(eventual_user_count, initial_user_count - 1)

########NEW FILE########
__FILENAME__ = test_rendering
from django.test import TestCase


def assert_content_type(response, expected):
    actual = response['content-type'].split(';', 1)[0]
    assert actual == expected, \
            "Expected a Content-Type of %r, got %r" % (expected, actual)

class SkipTest(TestCase):

    def test_quality(self):
        # Even though XML has a much higher quality score than JSON, because it
        # raises Skip it should never be processed.
        response = self.client.get("/users/",
                                   HTTP_ACCEPT=("application/xml;q=1,"
                                                "application/json;q=0.1"))

        self.assertEqual(response.status_code, 200)
        assert_content_type(response, 'application/json')

    def test_html_fallback(self):
        # Because XML raises skip, even when it is the only acceptable response
        # type it should still cause the HTML fallback to be used.
        response = self.client.get("/users/", HTTP_ACCEPT="application/xml")

        self.assertEqual(response.status_code, 200)
        assert_content_type(response, 'text/html')


class HTMLFallbackTest(TestCase):

    def test_undefined(self):
        # Asking for an undefined type should trigger the HTML fallback.
        response = self.client.get("/users/", HTTP_ACCEPT="image/png")

        self.assertEqual(response.status_code, 200)
        assert_content_type(response, 'text/html')

    def test_undefined_with_quality(self):
        # Asking for an undefined type with a higher quality than HTML should
        # produce an HTML response.
        response = self.client.get("/users/",
                                   HTTP_ACCEPT=("image/png;q=1.0,"
                                                "text/html;q=0.1"))

        self.assertEqual(response.status_code, 200)
        assert_content_type(response, 'text/html')

########NEW FILE########
__FILENAME__ = test_routing
from django.core.urlresolvers import NoReverseMatch, Resolver404, reverse, resolve
from django.test import TestCase

from users import resources


COLLECTION_METHODS = {
    'GET': 'index',
    'POST': 'create'
}
MEMBER_METHODS = {
    'GET': 'show',
    'POST': 'update',
    'PUT': 'update',
    'DELETE': 'destroy'
}
SINGLETON_METHODS = {
    'GET': 'show',
    'POST': 'update',
    'PUT': 'update',
    'DELETE': 'destroy'
}
EDIT_METHODS = {'GET': 'edit'}
NEW_METHODS = {'GET': 'new'}


class RoutingTest(TestCase):

    def assert_resolves(self, url, func, *args, **kwargs):
        resolved = resolve(url)
        self.assertEqual(resolved.func, func)
        self.assertEqual(resolved.args, args)
        # Check that `resolved.kwargs` is a superset of `kwargs`.
        for kw, value in kwargs.items():
            self.assertIn(kw, resolved.kwargs)
            self.assertEqual(resolved.kwargs[kw], value)
        # Allows for further user-level assertions.
        return resolved


class DefaultRoutingTest(RoutingTest):

    def test_index(self):
        self.assertEqual(reverse('User#index'), '/users/')
        self.assert_resolves('/users/', resources.User,
                             methods=COLLECTION_METHODS)

    def test_show(self):
        self.assertEqual(reverse('User#show', args=(1,)), '/users/1/')
        self.assert_resolves('/users/1/', resources.User,
                             '1', methods=MEMBER_METHODS)

        # Fails for invalid IDs.
        self.assertRaises(NoReverseMatch, reverse, 'User#show',
                          args=('invalid',))

    def test_new(self):
        self.assertEqual(reverse('User#new'), '/users/new/')
        self.assert_resolves('/users/new/', resources.User,
                             methods=NEW_METHODS)

    def test_edit(self):
        self.assertEqual(reverse('User#edit', args=(1,)), '/users/1/edit/')
        self.assert_resolves('/users/1/edit/', resources.User,
                             '1', methods=EDIT_METHODS)

    def test_singleton(self):
        self.assertEqual(reverse('Account#show'), '/account/')
        self.assertEqual(reverse('Account#update'), '/account/')
        self.assertEqual(reverse('Account#destroy'), '/account/')
        self.assert_resolves('/account/', resources.Account,
                             methods=SINGLETON_METHODS)

    def test_singleton_new(self):
        self.assertEqual(reverse('Account#new'), '/account/new/')
        self.assert_resolves('/account/new/', resources.Account,
                             methods=NEW_METHODS)

    def test_singleton_edit(self):
        self.assertEqual(reverse('Account#edit'), '/account/edit/')
        self.assert_resolves('/account/edit/', resources.Account,
                             methods=EDIT_METHODS)


class AtomPubRoutingTest(DefaultRoutingTest):

    def test_index(self):
        self.assertEqual(reverse('UserAtomPub#index'), '/users-atompub/')
        self.assert_resolves('/users-atompub/', resources.User,
                             methods=COLLECTION_METHODS)

    def test_show(self):
        self.assertEqual(reverse('UserAtomPub#show', args=(1,)),
                         '/users-atompub/1')
        self.assert_resolves('/users-atompub/1', resources.User,
                             '1', methods=MEMBER_METHODS)

        # Fails for invalid IDs.
        self.assertRaises(NoReverseMatch, reverse, 'UserAtomPub#show',
                          args=('invalid',))

    def test_new(self):
        self.assertEqual(reverse('UserAtomPub#new'), '/users-atompub/new')
        self.assert_resolves('/users-atompub/new', resources.User,
                             methods=NEW_METHODS)

    def test_edit(self):
        self.assertEqual(reverse('UserAtomPub#edit', args=(1,)),
                         '/users-atompub/1/edit')
        self.assert_resolves('/users-atompub/1/edit', resources.User,
                             '1', methods=EDIT_METHODS)

    def test_singleton(self):
        self.assertEqual(reverse('AccountAtomPub#show'), '/account-atompub/')
        self.assertEqual(reverse('AccountAtomPub#update'), '/account-atompub/')
        self.assertEqual(reverse('AccountAtomPub#destroy'), '/account-atompub/')
        self.assert_resolves('/account-atompub/', resources.Account,
                             methods=SINGLETON_METHODS)

    def test_singleton_new(self):
        self.assertEqual(reverse('AccountAtomPub#new'), '/account-atompub/new')
        self.assert_resolves('/account-atompub/new', resources.Account,
                             methods=NEW_METHODS)

    def test_singleton_edit(self):
        self.assertEqual(reverse('AccountAtomPub#edit'), '/account-atompub/edit')
        self.assert_resolves('/account-atompub/edit', resources.Account,
                             methods=EDIT_METHODS)


class RailsRoutingTest(DefaultRoutingTest):

    def test_index(self):
        self.assertEqual(reverse('UserRails#index'), '/users-rails')
        self.assert_resolves('/users-rails', resources.User,
                             methods=COLLECTION_METHODS)
        self.assert_resolves('/users-rails/', resources.User,
                             methods=COLLECTION_METHODS)

    def test_index_with_format(self):
        self.assertEqual(reverse('UserRails#index', kwargs={'format': '.json'}),
                         '/users-rails.json')
        self.assert_resolves('/users-rails.json', resources.User,
                             methods=COLLECTION_METHODS, format='.json')

    def test_show(self):
        self.assertEqual(reverse('UserRails#show', kwargs={'id': 1}),
                         '/users-rails/1')
        self.assert_resolves('/users-rails/1',
                             resources.User,
                             id='1', methods=MEMBER_METHODS)
        self.assert_resolves('/users-rails/1/',
                             resources.User,
                             id='1', methods=MEMBER_METHODS)

        # Fails for invalid IDs.
        self.assertRaises(NoReverseMatch, reverse, 'UserRails#show',
                          kwargs={'id': 'invalid'})
        self.assertRaises(Resolver404, resolve, '/users-rails/invalid')
        self.assertRaises(Resolver404, resolve, '/users-rails/invalid.json')
        self.assertRaises(Resolver404, resolve, '/users-rails/invalid/')

    def test_show_with_format(self):
        self.assertEqual(reverse('UserRails#show',
                                 kwargs={'id': 1, 'format': '.json'}),
                         '/users-rails/1.json')
        self.assert_resolves('/users-rails/1.json',
                             resources.User,
                             id='1', methods=MEMBER_METHODS, format='.json')

    def test_new(self):
        self.assertEqual(reverse('UserRails#new'), '/users-rails/new')
        self.assert_resolves('/users-rails/new', resources.User,
                             methods=NEW_METHODS)
        self.assert_resolves('/users-rails/new/', resources.User,
                             methods=NEW_METHODS)
        self.assertRaises(Resolver404, resolve, '/users-rails/new/foobar')
        self.assertRaises(Resolver404, resolve, '/users-rails/new.foobar')

    def test_edit(self):
        self.assertEqual(reverse('UserRails#edit', kwargs={'id': 1}),
                         '/users-rails/1/edit')
        self.assert_resolves('/users-rails/1/edit', resources.User,
                             id='1', methods=EDIT_METHODS)
        self.assert_resolves('/users-rails/1/edit/', resources.User,
                             id='1', methods=EDIT_METHODS)
        self.assertRaises(Resolver404, resolve, '/users-rails/1/edit/foobar')
        self.assertRaises(Resolver404, resolve, '/users-rails/1/edit.foobar')

    def test_singleton(self):
        self.assertEqual(reverse('AccountRails#show'), '/account-rails')
        self.assertEqual(reverse('AccountRails#update'), '/account-rails')
        self.assertEqual(reverse('AccountRails#destroy'), '/account-rails')
        self.assert_resolves('/account-rails', resources.Account,
                             methods=SINGLETON_METHODS)
        self.assert_resolves('/account-rails/', resources.Account,
                             methods=SINGLETON_METHODS)

    def test_singleton_with_format(self):
        self.assertEqual(reverse('AccountRails#show', kwargs={'format': '.json'}),
                         '/account-rails.json')

    def test_singleton_new(self):
        self.assertEqual(reverse('AccountRails#new'), '/account-rails/new')
        self.assert_resolves('/account-rails/new', resources.Account,
                             methods=NEW_METHODS)

    def test_singleton_edit(self):
        self.assertEqual(reverse('AccountRails#edit'), '/account-rails/edit')
        self.assert_resolves('/account-rails/edit', resources.Account,
                             methods=EDIT_METHODS)

########NEW FILE########
__FILENAME__ = action
# -*- coding: utf-8 -*-

from functools import wraps

from dagny.renderer import Renderer
from dagny.resource import Resource
from dagny.utils import resource_name


class Action(object):

    """
    A descriptor for wrapping an action method.

        >>> action = Action
        >>> class X(Resource):
        ...     @action
        ...     def show(self):
        ...         self.attr1 = 'a'

    Appears as an `Action` on the class (and other objects):

        >>> X.show  # doctest: +ELLIPSIS
        <Action '#show' at 0x...>
        >>> X.show.render  # doctest: +ELLIPSIS
        <BoundRenderer on <Action '#show' at 0x...>>

    Appears as a `BoundAction` on an instance:

        >>> x = X._new(object())
        >>> x.show  # doctest: +ELLIPSIS
        <BoundAction 'X#show' at 0x...>
        >>> x.show.render  # doctest: +ELLIPSIS
        <bound method BoundAction.render of <BoundAction 'X#show' at 0x...>>

    ## Actions and Rendering

    The API for `Action` instances has been fine-tuned to allow an easy
    interface with the renderer system. When accessed from inside the class
    definition, `show.render` is a `BoundRenderer` instance, so you're just
    using the standard decorator syntax for defining new renderer backends:

        class User(Resource):

            @action
            def show(self, username):
                self.user = get_object_or_404(User, username=username)

            @show.render.json
            def show(self):
                return JSONResponse(self.user.as_dict())

            # You can also un-define renderer backends for a single action:
            del show.render['html']

            # Or assign generic backends for a particular action:
            show.render['html'] = my_generic_html_backend

    When accessed via a resource *instance*, `show.render` will be the
    `render()` method of a `BoundAction`, and calling it will invoke the full
    rendering process for that particular action, on the current resource. This
    is very useful when handling forms; for example:

        class User(Resource):

            @action
            def edit(self, username):
                self.user = get_object_or_404(User, username=username)
                self.form = UserForm(instance=self.user)
                # Here the default HTML renderer will kick in; you should
                # display the edit user form in a "user/edit.html" template.

            @action
            def update(self, username):
                self.user = get_object_or_404(User, username=username)
                self.form = UserForm(instance=self.user)
                if self.form.is_valid():
                    self.form.save()
                    # Returns a response, action ends here.
                    return redirect(self.user)

                # Applies the `edit` renderer to *this* request, thus rendering
                # the "user/edit.html" template but with this resource (and
                # hence this `UserForm` instance, which contains errors).
                response = self.edit.render()
                response.status_code = 403  # Forbidden
                return response

    It makes sense to write the `user/edit.html` template so that it renders
    forms dynamically; this means the filled-in fields and error messages will
    propagate automatically, without any extra work on your part.
    """

    # Global renderer to allow definition of generic renderer backends.
    RENDERER = Renderer()

    @staticmethod
    def deco(decorator):

        """
        Static method to wrap a typical view decorator as an action decorator.

        Usage is relatively simple, but remember that `@action.deco()` must come
        *below* `@action`:

            class User(Resource):

                @action
                @action.deco(auth_required)
                def edit(self, username):
                    ...

        This will wrap the decorator so that *it* sees a function with a
        signature of `view(request, *args, **kwargs)`; this function is an
        adapter which will then call the action appropriately.

            >>> def decorator(view):
            ...     def wrapper(request, *args, **kwargs):
            ...         print "WRAPPER (In):"
            ...         print "  ", repr(request), args, kwargs
            ...
            ...         request = "ModifiedRequest"
            ...         args = ("another_user",)
            ...         kwargs.update(authenticated=True)
            ...
            ...         print "WRAPPER (Out):"
            ...         print "  ", repr(request), args, kwargs
            ...
            ...         return view(request, *args, **kwargs)
            ...     return wrapper

            >>> def view(self, username):
            ...     print "VIEW:"
            ...     print "  ", repr(self.request), self.args, self.params

            >>> resource = type('Resource', (object,), {})()
            >>> resource.request = "Request"
            >>> resource.args = ("some_user",)
            >>> resource.params = {}

            >>> view(resource, "some_user")
            VIEW:
               'Request' ('some_user',) {}

            >>> Action.deco(decorator)(view)(resource, "some_user")
            WRAPPER (In):
               'Request' ('some_user',) {}
            WRAPPER (Out):
               'ModifiedRequest' ('another_user',) {'authenticated': True}
            VIEW:
               'ModifiedRequest' ('another_user',) {'authenticated': True}

        """

        @wraps(decorator)
        def deco_wrapper(action_func):
            @wraps(action_func)
            def action_wrapper(self, *args):
                @wraps(action_func)
                def adapter(request, *adapter_args, **params):
                    self.request = request
                    self.args = adapter_args
                    self.params = params
                    return action_func(self, *self.args)
                return decorator(adapter)(self.request, *args, **self.params)
            return action_wrapper
        return deco_wrapper

    def __init__(self, method):
        self.method = method
        self.name = method.__name__
        self.render = self.RENDERER._bind(self)

    def __repr__(self):
        return "<Action '#%s' at 0x%x>" % (self.name, id(self))

    def __get__(self, resource, resource_cls):
        if isinstance(resource, Resource):
            return BoundAction(self, resource, resource_cls)
        return self


class BoundAction(object):

    """An action which has been bound to a specific resource instance."""

    def __init__(self, action, resource, resource_cls):
        self.action = action
        self.resource = resource
        self.resource_cls = resource_cls
        self.resource_name = resource_name(resource_cls)

    def __repr__(self):
        return "<BoundAction '%s#%s' at 0x%x>" % (self.resource_name, self.action.name, id(self))

    def __call__(self):
        response = self.action.method(self.resource, *self.resource.args)
        if response:
            return response
        return self.render()

    def render(self, *args, **kwargs):
        return self.action.render(self.resource, *args, **kwargs)

    @property
    def name(self):
        return self.action.name

########NEW FILE########
__FILENAME__ = conneg
# -*- coding: utf-8 -*-

"""
Helpers and global mappings for content negotiation.

If you want to define a custom mimetype shortcode, add it to the `MIMETYPES`
dictionary in this module (without the leading '.' character). For example:

    from dagny.conneg import MIMETYPES

    MIMETYPES['png'] = 'image/png'
    MIMETYPES['json'] = 'text/javascript'

"""

import mimetypes

from webob.acceptparse import MIMEAccept

__all__ = ['MIMETYPES', 'match_accept']


# Maps renderer shortcodes => mimetypes.
MIMETYPES = {
    'rss': 'application/rss+xml',
    'json': 'application/json',
    'rdf_xml': 'application/rdf+xml',
    'xhtml': 'application/xhtml+xml',
    'xml': 'application/xml',
}


# Load all extension => mimetype mappings from `mimetypes` stdlib module.
for ext, mimetype in mimetypes.types_map.iteritems():
    shortcode = ext.lstrip(".").replace(".", "_")  # .tar.bz2 => tar_bz2
    MIMETYPES.setdefault(shortcode, mimetype)
del ext, shortcode, mimetype  # Clean up


def match_accept(header, shortcodes):

    """
    Match an Accept header against a list of shortcodes, in order of preference.

    A few examples:

        >>> header = "application/xml,application/xhtml+xml,text/html"

        >>> match_accept(header, ['html', 'json', 'xml'])
        ['html', 'xml']

        >>> header2 = "application/json,application/xml"

        >>> match_accept(header2, ['html', 'json', 'xml'])
        ['json', 'xml']

        >>> match_accept(header2, ['html', 'xml', 'json'])
        ['xml', 'json']

    """

    server_types = map(MIMETYPES.__getitem__, shortcodes)
    client_types = list(MIMEAccept(header))
    matches = []
    for mimetype in server_types:
        if mimetype in client_types:
            matches.append(mimetype)

    return map(shortcodes.__getitem__, map(server_types.index, matches))

########NEW FILE########
__FILENAME__ = renderer
# -*- coding: utf-8 -*-

from functools import wraps

import odict

from dagny import conneg


class Skip(Exception):

    """
    Move on to the next renderer backend.

    This exception can be raised by a renderer backend to instruct the
    `Renderer` to ignore the current backend and move on to the next-best one.
    """


class Renderer(object):

    """
    Manage a collection of renderer backends, and their execution on an action.

    A renderer backend is a callable which accepts an `Action` and a `Resource`
    and returns an instance of `django.http.HttpResponse`. For example:

        >>> def render_html(action, resource):
        ...     from django.http import HttpResponse
        ...     return HttpResponse(content="<html>...</html>")

    Backends are associated with mimetypes on the `Renderer`, through mimetype
    shortcodes (see `dagny.conneg` for more information on shortcodes). The
    `Renderer` exports a dictionary-like interface for managing these
    associations:

        >>> r = Renderer()

        >>> r['html'] = render_html

        >>> r['html']  # doctest: +ELLIPSIS
        <function render_html at 0x...>

        >>> 'html' in r
        True

        >>> del r['html']

        >>> r['html']
        Traceback (most recent call last):
            ...
        KeyError: 'html'

        >>> 'html' in r
        False

    A few helpful dictionary methods have also been added, albeit
    underscore-prefixed to prevent naming clashes. Behind the scenes, `Renderer`
    uses [odict](http://pypi.python.org/pypi/odict), which will keep the keys in
    the order they were *first* defined. Here are a few examples:

        >>> r['html'] = 1
        >>> r['json'] = 2
        >>> r['xml'] = 3

        >>> r._keys()
        ['html', 'json', 'xml']

        >>> r._items()
        [('html', 1), ('json', 2), ('xml', 3)]

        >>> r._values()
        [1, 2, 3]

    This order preservation is useful for ConNeg, since you can define backends
    in order of server preference and the negotiator will consider them
    appropriately. You can push something to the end of the queue by removing
    and then re-adding it:

        >>> r['html'] = r._pop('html')

        >>> r._keys()
        ['json', 'xml', 'html']

    You can also define backends using a handy decorator-based syntax:

        >>> @r.html
        ... def render_html_2(action, resource):
        ...     from django.http import HttpResponse
        ...     return HttpResponse(content="<html>...</html>")

        >>> r['html'] is render_html_2
        True

    Remember that your shortcode *must* be pre-registered with
    `dagny.conneg.MIMETYPES` for this to work, otherwise an `AttributeError`
    will be raised. This also introduces the constraint that your shortcode must
    be a valid Python identifier.
    """

    def __init__(self, backends=None):
        if backends is None:
            backends = odict.odict()
        else:
            backends = backends.copy()
        self._backends = backends

    def __getattr__(self, shortcode):

        """
        Support use of decorator syntax to define new renderer backends.

            >>> r = Renderer()

            >>> @r.html
            ... def render_html(action, resource):
            ...     return "<html>...</html>"

            >>> render_html  # doctest: +ELLIPSIS
            <function render_html at 0x...>

            >>> r['html']  # doctest: +ELLIPSIS
            <function render_html at 0x...>

            >>> r['html'] is render_html
            True

        """

        if shortcode not in conneg.MIMETYPES:
            raise AttributeError(shortcode)

        def decorate(function):
            self[shortcode] = function
            return function
        return decorate

    def __call__(self, action, resource, *args, **kwargs):
        matches = self._match(action, resource)

        for shortcode in matches:
            try:
                return self[shortcode](action, resource, *args, **kwargs)
            except Skip:
                continue

        # One last-ditch attempt to render HTML, pursuant to the note about
        # HTTP/1.1 here:
        #   <http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.7>
        # It's better to give an 'unacceptable' response than none at all.
        if 'html' not in matches and 'html' in self:
            try:
                return self['html'](action, resource, *args, **kwargs)
            except Skip:
                pass

        return not_acceptable(action, resource)

    def _match(self, action, resource):
        """Return all matching shortcodes for a given action and resource."""

        matches = []

        format_override = resource._format()
        if format_override and (format_override in self._keys()):
            matches.append(format_override)

        accept_header = resource.request.META.get('HTTP_ACCEPT')
        if accept_header:
            matches.extend(conneg.match_accept(accept_header, self._keys()))

        if (not matches) and ('html' in self):
            matches.append('html')

        return matches

    def _bind(self, action):

        """
        Bind this `Renderer` to an action, returning a `BoundRenderer`.

            >>> r = Renderer()
            >>> action = object()
            >>> r['html'] = 1

            >>> br = r._bind(action)
            >>> br  # doctest: +ELLIPSIS
            <BoundRenderer on <object object at 0x...>>

        Associations should be preserved, albeit on a copied `odict`, so that
        modifications to the `BoundRenderer` do not propagate back to this.

            >>> br['html']
            1
            >>> br['html'] = 2
            >>> br['html']
            2
            >>> r['html']
            1
            >>> r['html'] = 3
            >>> r['html']
            3
            >>> br['html']
            2

        """

        return BoundRenderer(action, backends=self._backends)

    def _copy(self):
        return type(self)(backends=self._backends)

    ### <meta>
    #
    #   This chunk of code creates several proxy methods going through to
    #   `_backends`. A group of them are underscore-prefixed to prevent naming
    #   clashes with the `__getattr__`-based decorator syntax (so you could
    #   still associate a backend with a shortcode of 'pop', for example).

    proxy = lambda meth: property(lambda self: getattr(self._backends, meth))

    for method in ('__contains__', '__getitem__', '__setitem__', '__delitem__'):
        vars()[method] = proxy(method)

    for method in ('clear', 'get', 'items', 'iteritems', 'iterkeys',
                   'itervalues', 'keys', 'pop', 'popitem', 'ritems',
                   'riteritems', 'riterkeys', 'ritervalues', 'rkeys', 'rvalues',
                   'setdefault', 'sort', 'update', 'values'):
        vars()['_' + method] = proxy(method)

    _dict = proxy('as_dict')

    del method, proxy

    #
    ### </meta>


class BoundRenderer(Renderer):

    def __init__(self, action, backends=None):
        super(BoundRenderer, self).__init__(backends=backends)
        self._action = action

    def __repr__(self):
        return "<BoundRenderer on %r>" % (self._action,)

    def __getattr__(self, shortcode):

        """
        Support use of decorator syntax to define new renderer backends.

        In this case, decorated functions should be methods which operate on a
        resource, and take no other arguments.

            >>> action = object()
            >>> r = BoundRenderer(action)
            >>> old_action_id = id(action)

            >>> @r.html
            ... def action(resource):
            ...     return "<html>...</html>"

            >>> id(action) == old_action_id # Object has not changed.
            True

        Functions will be wrapped internally, so that their function signature
        is that of a generic renderer backend. Accessing the

            >>> resource = object()
            >>> r['html'](action, resource)
            '<html>...</html>'

        """

        if shortcode not in conneg.MIMETYPES:
            raise AttributeError(shortcode)

        def decorate(method):
            self[shortcode] = resource_method_wrapper(method)
            return self._action
        return decorate

    def __call__(self, resource, *args, **kwargs):
        return super(BoundRenderer, self).__call__(self._action, resource,
                                                   *args, **kwargs)


def resource_method_wrapper(method):

    """
    Wrap a 0-ary resource method as a generic renderer backend.

        >>> @resource_method_wrapper
        ... def func(resource):
        ...     print repr(resource)

        >>> action = "abc"
        >>> resource = "def"

        >>> func(action, resource)
        'def'

    """

    def generic_renderer_backend(action, resource):
        return method(resource)
    return generic_renderer_backend


def not_acceptable(action, resource):
    """Respond, indicating that no acceptable entity could be generated."""

    from django.http import HttpResponse

    response = HttpResponse(status=406)  # Not Acceptable
    del response['Content-Type']
    return response

########NEW FILE########
__FILENAME__ = renderers
"""Generic, built-in renderers."""

from dagny.action import Action
from dagny.utils import camel_to_underscore, resource_name


@Action.RENDERER.html
def render_html(action, resource, content_type=None, status=None,
                current_app=None):

    """
    Render an appropriate HTML response for an action.

    This is a generic renderer backend which produces HTML responses. It uses
    the name of the resource and current action to generate a template name,
    then renders the template with a `RequestContext`.

    To retrieve the template name, the resource name is first turned from
    CamelCase to lowercase_underscore_separated; if the class name ends in
    `Resource`, this is first removed from the end. For example:

        User => user
        UserResource => user
        NameXYZ => name_xyz
        XYZName => xyz_name

    You can optionally define a template path prefix on your `Resource` like
    so:

        class User(Resource):
            template_path_prefix = 'auth/'
            # ...

    The template name is assembled from the template path prefix, the
    re-formatted resource name, and the current action name. So, for a `User`
    resource, with `template_path_prefix = 'auth/'`, and an action of `show`,
    the template name would be:

        auth/user/show.html

    Finally, this is rendered using `django.shortcuts.render()`. The resource
    is passed into the context as `self`, so that attribute assignments from
    the action will be available in the template. This also uses
    `RequestContext`, so configured context processors will also be available.
    """

    from django.shortcuts import render

    resource_label = camel_to_underscore(resource_name(resource))
    template_path_prefix = getattr(resource, 'template_path_prefix', "")
    template_name = "%s%s/%s.html" % (template_path_prefix, resource_label,
                                      action.name)

    return render(resource.request, template_name, {'self': resource},
                  content_type=content_type, status=status,
                  current_app=current_app)

########NEW FILE########
__FILENAME__ = resource
# -*- coding: utf-8 -*-

from django.http import Http404, HttpResponseNotAllowed
from djclsview import View

__all__ = ['Resource']


class Resource(View):

    def __init__(self, request, *args, **params):
        self.request = request
        self.args = args
        self.params = params
        self._called_yet = False

    def __call__(self):
        """Dispatch to an action based on HTTP method + URL."""

        # The problem with defining a resource as a callable is that a
        # reference to `self` from a Django template (in v1.3) will attempt to
        # call the resource again.
        if self._called_yet:
            return self
        self._called_yet = True

        method = self.request.POST.get('_method', self.request.method).upper()
        try:
            method_action_map = self.params.pop('methods')
        except KeyError:
            raise ValueError("Expected 'methods' dict in view kwargs")
        return self._route(method, method_action_map)()

    def _route(self, method, method_action_map):

        """
        Resolve an HTTP method and an HTTP method -> action mapping to a view.

        There are two sources for the list of 'defined methods' on a given URL:
        the HTTP method -> action map passed in to this method, and the actions
        which are defined on this `Resource` class. If the intersection of
        these two lists is empty--to wit, no methods are defined for the
        current URL--return a stub 404 view. Otherwise, if an HTTP method is
        sent which is not in *both* these lists, return a 405 'Not Allowed'
        view (which will contain the list of accepted methods at this URL).

        If the HTTP method sent is in the method -> action map, and the mapped
        action is defined on this `Resource`, return that action (which will be
        a callable `BoundAction` instance).
        """

        allowed_methods = self._allowed_methods(method_action_map)
        if method not in allowed_methods:
            # If *no* methods are defined for this URL, return a 404.
            if not allowed_methods:
                return not_found
            return lambda: HttpResponseNotAllowed(allowed_methods)

        action_name = method_action_map[method]
        return getattr(self, action_name)

    def _allowed_methods(self, method_action_map):
        allowed_methods = []
        for meth, action_name in method_action_map.items():
            if hasattr(self, action_name):
                allowed_methods.append(meth)
        return allowed_methods

    def _format(self):
        """Return a mimetype shortcode, in case there's no Accept header."""

        if self.params.get('format'):
            return self.params['format'].lstrip('.')
        return self.request.GET.get('format')


def not_found():
    """Stub function to raise `django.http.Http404`."""

    raise Http404

########NEW FILE########
__FILENAME__ = atompub
import styles
import router


__all__ = ['resources', 'resource']


_router = router.URLRouter(style=styles.AtomPubURLStyle())
resources = _router.resources
resource = _router.resource

########NEW FILE########
__FILENAME__ = rails
import styles
import router


__all__ = ['resources', 'resource']


_router = router.URLRouter(style=styles.RailsURLStyle())
resources = _router.resources
resource = _router.resource

########NEW FILE########
__FILENAME__ = router
from django.conf.urls import defaults


class URLRouter(object):

    """
    Responsible for generating include()-able URLconfs for resources.

    Accepts only one argument on instantiation, `style`. This should be a
    callable which accepts an action parameter, a routing mode and an ID regex,
    and returns a regular expression with a route for that action. You should
    only need to use the styles already defined in `dagny.urls.styles`.
    """

    def __init__(self, style):
        self.style = style

    def _make_patterns(self, resource_name, id, name, actions, urls):

        """
        Construct an `include()` with all the URLs for a resource.

        :param resource_name:
            The full path to the resource (e.g.  `myapp.resources.User`).
        :param id:
            The ID parameter, either as a regex fragment or a `(name, regex)`
            pair, which will normally be translated by the URL style to a named
            group in the URL.
        :param name:
            The name for this resource, which will be used to generate named
            URL patterns (e.g. if name is 'User', URLs will be 'User#index',
            'User#show' etc.). If `None`, defaults to `resource_name`.
        :param actions:
            The actions to generate (named) routes for. If `None`, a route and
            a name will be generated for every one defined by the chosen URL
            style.
        :param urls:
            A list of the URLs to define patterns for. Must be made up only of
            'member', 'collection', 'new', 'edit', 'singleton' and
            'singleton_edit'.
        """

        if actions is not None:
            actions = set(actions)
        if name is None:
            name = resource_name

        urlpatterns = []
        for url in urls:
            # URLStyle.__call__(url_name, id_pattern)
            #     => (url_pattern, {method: action, ...})
            pattern, methods = self.style(url, id)
            # Filter methods dict to only contain the selected actions.
            methods = dict(
                (method, action) for method, action in methods.iteritems()
                if (actions is None) or (action in actions))
            # Add named url patterns, one per action. Note that we will have
            # duplicate URLs in some cases, but this is so that
            # `{% url User#show %}` can be distinguished from
            # `{% url User#update %}` when it makes sense.
            for action in methods.itervalues():
                urlpatterns.append(defaults.url(pattern, resource_name,
                                                kwargs={'methods': methods},
                                                name=("%s#%s" % (name, action))))
        return defaults.include(defaults.patterns('', *urlpatterns))

    def resources(self, resource_name, id=r'\d+', actions=None, name=None):
        return self._make_patterns(resource_name, id, name, actions,
                                   ['collection', 'new', 'member', 'edit'])

    def resource(self, resource_name, actions=None, name=None):
        return self._make_patterns(resource_name, '', name, actions,
                                   ['singleton', 'new', 'singleton_edit'])

########NEW FILE########
__FILENAME__ = styles
class URLStyle(object):

    """
    Generic class for defining resource URL styles.

    `URLStyle` can be used to create callables which will work for the
    interface defined in `dagny.urls.router.URLRouter`. Subclass and override
    the `collection()`, `new()`, `member()`, `edit()`, `singleton()` and
    `singleton_edit()` methods to customize your URLs. You can use one of the
    several defined styles in this module as a template.
    """

    METHODS = {
        'collection': {
            'GET': 'index',
            'POST': 'create'
        },
        'member': {
            'GET': 'show',
            'POST': 'update',
            'PUT': 'update',
            'DELETE': 'destroy'
        },
        'new': {'GET': 'new'},
        'edit': {'GET': 'edit'},
        'singleton': {
            'GET': 'show',
            'POST': 'update',
            'PUT': 'update',
            'DELETE': 'destroy'
        },
        'singleton_edit': {'GET': 'edit'},
    }

    def __call__(self, url, id_param):
        id_regex = self._get_id_regex(id_param)

        if url in ('member', 'edit'):
            return getattr(self, url)(id_regex), self.METHODS[url]
        return getattr(self, url)(), self.METHODS[url]

    def _get_id_regex(self, id_param):

        """
        Resolve `(name, regex)` => `'?P<name>regex'`.

        Since the style methods should add parentheses around the ID regex
        fragment, the output for named ID parameters is not surrounded by
        parentheses itself.
        """

        if isinstance(id_param, basestring):
            return id_param
        elif isinstance(id_param, tuple):
            if len(id_param) != 2:
                raise ValueError("id param must be a (name, regex) pair")
            name, regex = id_param
            return '?P<%s>%s' % (name, regex)
        raise TypeError('id param must be a string or (name, regex) pair, '
                        'not %r' % (type(id_param),))

    # Publicly-overrideable methods for customizing style behaviour.

    def collection(self):
        raise NotImplementedError

    def new(self):
        raise NotImplementedError

    def member(self, id_regex):
        raise NotImplementedError

    def edit(self, id_regex):
        raise NotImplementedError

    def singleton(self):
        raise NotImplementedError

    def singleton_edit(self):
        raise NotImplementedError


class DjangoURLStyle(URLStyle):

    """
    Standard Django-style URLs.

       URL            | action | args   | kwargs
       ---------------+--------+--------+--------
       /posts/        | index  | ()     | {}
       /posts/new/    | new    | ()     | {}
       /posts/1/      | show   | ('1',) | {}
       /posts/1/edit/ | edit   | ('1',) | {}
    """

    def collection(self):
        return r'^$'

    def new(self):
        return r'^new/$'

    def member(self, id_regex):
        return r'^(%s)/$' % (id_regex,)

    def edit(self, id_regex):
        return r'^(%s)/edit/$' % (id_regex,)

    def singleton(self):
        return r'^$'

    def singleton_edit(self):
        return r'^edit/$'


class AtomPubURLStyle(URLStyle):

    """
    Atom Publishing Protocol-style URLs.

    The main difference between this and Django-style URLs is the lack of
    trailing slashes on leaf nodes.

        URL           | action | args   | kwargs
        --------------+--------+--------+--------
        /posts/       | index  | ()     | {}
        /posts/new    | new    | ()     | {}
        /posts/1      | show   | ('1',) | {}
        /posts/1/edit | edit   | ('1',) | {}
    """

    def collection(self):
        return r'^$'

    def new(self):
        return r'^new$'

    def member(self, id_regex):
        return r'^(%s)$' % (id_regex,)

    def edit(self, id_regex):
        return r'^(%s)/edit$' % (id_regex,)

    def singleton(self):
        return r'^$'

    def singleton_edit(self):
        return r'^edit$'


class RailsURLStyle(URLStyle):

    r"""
    Ruby on Rails-style URLs.

    This URL style is quite advanced; it will also capture format extensions
    and pass them through as a kwarg. As with `AtomPubURLStyle`, trailing
    slashes are not mandatory on leaf nodes.

        URL           | action | args | kwargs
        --------------+--------+------+------------------------------
        /posts        | index  | ()   | {}
        /posts.json   | index  | ()   | {'format': 'json'}
        /posts/       | index  | ()   | {}
        /posts/new    | new    | ()   | {}
        /posts/1      | show   | ()   | {'id': '1'}
        /posts/1.json | show   | ()   | {'id': '1', 'format': 'json'}
        /posts/1/     | show   | ()   | {'id': '1'}
        /posts/1/edit | edit   | ()   | {'id': '1'}

    **Note**: due to limitations of the URLconf system, your IDs/slugs have to
    come in as named parameters. By default, the parameter will be called `id`,
    but you can select a different one using the `id` keyword argument to the
    URL helpers:

        urlpatterns = patterns('',
            (r'posts', resources('myapp.resources.Post', name='Post',
                                 id=('slug', r'[\w\-]+'))),
        )

    Another caveat: do not terminate your inclusion regex with a slash, or the
    format extension on the resource index won't work.

    You can customize the format extension regex (and hence the kwarg name) by
    subclassing and overriding the `FORMAT_EXTENSION_RE` attribute, e.g.:

        class MyRailsURLStyle(RailsURLStyle):
            FORMAT_EXTENSION_RE = r'(?P<accept>[A-Za-z0-9]+)'
    """

    FORMAT_EXTENSION_RE = r'(?P<format>\.\w[\w\-\.]*)'

    def _get_id_regex(self, id_param):
        """Co-erce *all* IDs to named parameters, defaulting to `'id'`."""

        if isinstance(id_param, basestring) and not id_param.startswith('?P<'):
            return super(RailsURLStyle, self)._get_id_regex(('id', id_param))
        return super(RailsURLStyle, self)._get_id_regex(id_param)

    def collection(self):
        return r'^%s?/?$' % (self.FORMAT_EXTENSION_RE,)

    def new(self):
        return r'^/new/?$'

    def member(self, id_regex):
        return r'^/(%s)%s?/?$' % (id_regex, self.FORMAT_EXTENSION_RE)

    def edit(self, id_regex):
        return r'^/(%s)/edit/?$' % (id_regex,)

    def singleton(self):
        return r'^%s?/?$' % (self.FORMAT_EXTENSION_RE,)

    def singleton_edit(self):
        return r'^/edit/?$'

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import re


def camel_to_underscore(camel_string):

    """
    Convert a CamelCase string to under_score.

    Examples:

        >>> camel_to_underscore('SplitAtTheBoundaries')
        'split_at_the_boundaries'

        >>> camel_to_underscore('XYZResource')
        'xyz_resource'

        >>> camel_to_underscore('ResourceXYZ')
        'resource_xyz'

        >>> camel_to_underscore('XYZ')
        'xyz'

    """

    return re.sub(
        r'(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', r'_\1',
        camel_string).lower().strip('_')


def resource_name(resource_cls):
    """Return the name of a given resource, stripping 'Resource' off the end."""

    from dagny import Resource

    if isinstance(resource_cls, Resource):
        resource_cls = resource_cls.__class__

    name = resource_cls.__name__
    if name.endswith('Resource'):
        return name[:-8]
    return name

########NEW FILE########
