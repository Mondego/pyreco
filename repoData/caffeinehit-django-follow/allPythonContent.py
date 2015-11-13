__FILENAME__ = models
from django.contrib.auth.models import User, Group
from django.db import models



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
# Create your views here.
from django.http import HttpResponse
def index(request):
    return HttpResponse("ok")

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
# Django settings for project project.
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite', # Or path to database file if using sqlite3.
        'USER': '', # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '', # Set to empty string for default. Not used with sqlite3.
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
SECRET_KEY = '&4hhsd5b_elzi1p3*cd(a-fmlufeal^3^l#v$hmuqv!3$fbh39'

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
)

ROOT_URLCONF = 'example.urls'

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
    'app',
    'follow',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'project.views.home', name='home'),
    # url(r'^project/', include('project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url('^', include('follow.urls')),
    url('^$', 'app.views.index')
)

########NEW FILE########
__FILENAME__ = admin
from follow.models import Follow
from django.contrib import admin

admin.site.register(Follow)
########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User, AnonymousUser
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, post_delete
from follow.registry import model_map
from follow.signals import followed, unfollowed
import inspect

class FollowManager(models.Manager):
    def fname(self, model_or_obj_or_qs):
        """ 
        Return the field name on the :class:`Follow` model for ``model_or_obj_or_qs``.
        """
        if isinstance(model_or_obj_or_qs, QuerySet):
            _, fname = model_map[model_or_obj_or_qs.model]
        else:
            cls = model_or_obj_or_qs if inspect.isclass(model_or_obj_or_qs) else model_or_obj_or_qs.__class__
            _, fname = model_map[cls]
        return fname
    
    def create(self, user, obj, **kwargs):
        """
        Create a new follow link between a user and an object
        of a registered model type.
        
        """
        follow = Follow(user=user)
        follow.target = obj
        follow.save()
        return follow
            
    def get_or_create(self, user, obj, **kwargs):
        """ 
        Almost the same as `FollowManager.objects.create` - behaves the same 
        as the normal `get_or_create` methods in django though. 

        Returns a tuple with the `Follow` and either `True` or `False`

        """
        if not self.is_following(user, obj):
            return self.create(user, obj, **kwargs), True
        return self.get_follows(obj).get(user=user), False
    
    def is_following(self, user, obj):
        """ Returns `True` or `False` """
        if isinstance(user, AnonymousUser):
            return False        
        return 0 < self.get_follows(obj).filter(user=user).count()

    def get_follows(self, model_or_obj_or_qs):
        """
        Returns all the followers of a model, an object or a queryset.
        """
        fname = self.fname(model_or_obj_or_qs)
        
        if isinstance(model_or_obj_or_qs, QuerySet):
            return self.filter(**{'%s__in' % fname: model_or_obj_or_qs})
        
        if inspect.isclass(model_or_obj_or_qs):
            return self.exclude(**{fname:None})

        return self.filter(**{fname:model_or_obj_or_qs})
    
class Follow(models.Model):
    """
    This model allows a user to follow any kind of object. The followed
    object is accessible through `Follow.target`.
    """
    user = models.ForeignKey(User, related_name='following')

    datetime = models.DateTimeField(auto_now_add=True)

    objects = FollowManager()

    def __unicode__(self):
        return u'%s' % self.target

    def _get_target(self):
        for Model, (_, fname) in model_map.iteritems():
            try:
                if hasattr(self, fname) and getattr(self, fname):
                    return getattr(self, fname)
            except Model.DoesNotExist:
                # In case the target was deleted in the previous transaction 
                # it's already gone from the db and this throws DoesNotExist.
                return None
    
    def _set_target(self, obj):
        for _, fname in model_map.values():
            setattr(self, fname, None)
        if obj is None:
            return
        _, fname = model_map[obj.__class__]
        setattr(self, fname, obj)
        
    target = property(fget=_get_target, fset=_set_target)

def follow_dispatch(sender, instance, created=False, **kwargs):
    if created:
        followed.send(instance.target.__class__, user=instance.user, target=instance.target, instance=instance)

def unfollow_dispatch(sender, instance, **kwargs):
    # FIXME: When deleting out of the admin, django *leaves* the transaction
    # management after the user is deleted and then starts deleting all the
    # associated objects. This breaks the unfollow signal. Looking up 
    # `instance.user` will throw a `DoesNotExist` exception.  The offending
    # code is in django/db/models/deletion.py#70
    # At least that's what the error report looks like and I'm a bit short 
    # on time to investigate properly. 
    # Unfollow handlers should be aware that both target and user can be `None`
    try:
        user = instance.user
    except User.DoesNotExist:
        user = None
    
    unfollowed.send(instance.target.__class__, user=user, target=instance.target, instance=instance)
    
    
post_save.connect(follow_dispatch, dispatch_uid='follow.follow_dispatch', sender=Follow)
post_delete.connect(unfollow_dispatch, dispatch_uid='follow.unfollow_dispatch', sender=Follow)

########NEW FILE########
__FILENAME__ = registry

registry = []
model_map = {}

########NEW FILE########
__FILENAME__ = signals
from django.dispatch.dispatcher import Signal

followed = Signal(providing_args=["user", "target", "instance"])
unfollowed = Signal(providing_args=["user", "target", "instance"])

########NEW FILE########
__FILENAME__ = follow_tags
from django import template
from django.core.urlresolvers import reverse
from follow.models import Follow
from follow import utils
import re

register = template.Library()

@register.tag
def follow_url(parser, token):
    """
    Returns either a link to follow or to unfollow.
    
    Usage::
        
        {% follow_url object %}
        {% follow_url object user %}
        
    """
    bits = token.split_contents()
    return FollowLinkNode(*bits[1:])

class FollowLinkNode(template.Node):
    def __init__(self, obj, user=None):
        self.obj = template.Variable(obj)
        self.user = user
        
    def render(self, context):
        obj = self.obj.resolve(context)
        
        if not self.user:
            try:
                user = context['request'].user
            except KeyError:
                raise template.TemplateSyntaxError('There is no request object in the template context.')
        else:
            user = template.Variable(self.user).resolve(context)
        
        return utils.follow_url(user, obj)
        

@register.filter
def is_following(user, obj):
    """
    Returns `True` in case `user` is following `obj`, else `False`
    """
    return Follow.objects.is_following(user, obj)


@register.tag
def follow_form(parser, token):
    """
    Renders the following form. This can optionally take a path to a custom 
    template. 
    
    Usage::
    
        {% follow_form object %}
        {% follow_form object "app/follow_form.html" %}
        
    """
    bits = token.split_contents()
    return FollowFormNode(*bits[1:])

class FollowFormNode(template.Node):
    def __init__(self, obj, tpl=None):
        self.obj = template.Variable(obj)
        self.template = tpl[1:-1] if tpl else 'follow/form.html'
    
    def render(self, context):
        ctx = {'object': self.obj.resolve(context)}
        return template.loader.render_to_string(self.template, ctx,
            context_instance=context)

########NEW FILE########
__FILENAME__ = tests
from django import template
from django.contrib.auth.models import User, AnonymousUser, Group
from django.core.urlresolvers import reverse
from django.test import TestCase
from follow import signals, utils
from follow.models import Follow
from follow.utils import register

register(User)
register(Group)

class FollowTest(TestCase):
    urls = 'follow.urls'

    def setUp(self):
        
        self.lennon = User.objects.create(username='lennon')
        self.lennon.set_password('test')
        self.lennon.save()
        self.hendrix = User.objects.create(username='hendrix')
        
        self.musicians = Group.objects.create()
        
        self.lennon.groups.add(self.musicians)        
    
    def test_follow(self):
        follow = Follow.objects.create(self.lennon, self.hendrix)
        
        _, result = Follow.objects.get_or_create(self.lennon, self.hendrix)
        self.assertEqual(False, result)
        
        result = Follow.objects.is_following(self.lennon, self.hendrix)
        self.assertEqual(True, result)
        
        result = Follow.objects.is_following(self.hendrix, self.lennon)
        self.assertEqual(False, result)

        result = Follow.objects.get_follows(User)
        self.assertEqual(1, len(result))
        self.assertEqual(self.lennon, result[0].user)
        
        result = Follow.objects.get_follows(self.hendrix)
        self.assertEqual(1, len(result))
        self.assertEqual(self.lennon, result[0].user)
        
        result = self.hendrix.get_follows()
        self.assertEqual(1, len(result))
        self.assertEqual(self.lennon, result[0].user)
        
        result = self.lennon.get_follows()
        self.assertEqual(0, len(result), result)
        
        utils.toggle(self.lennon, self.hendrix)
        self.assertEqual(0, len(self.hendrix.get_follows()))
        
        utils.toggle(self.lennon, self.hendrix)
        self.assertEqual(1, len(self.hendrix.get_follows()))
        
    def test_get_follows_for_queryset(self):
        utils.follow(self.hendrix, self.lennon)
        utils.follow(self.lennon, self.hendrix)
        
        result = Follow.objects.get_follows(User.objects.all())
        self.assertEqual(2, result.count())
    
    def test_follow_http(self):
        self.client.login(username='lennon', password='test')
        
        follow_url = reverse('follow', args=['auth', 'user', self.hendrix.id])
        unfollow_url = reverse('follow', args=['auth', 'user', self.hendrix.id])
        toggle_url = reverse('toggle', args=['auth', 'user', self.hendrix.id])

        response = self.client.post(follow_url)
        self.assertEqual(302, response.status_code)
        
        response = self.client.post(follow_url)
        self.assertEqual(302, response.status_code)
        
        response = self.client.post(unfollow_url)
        self.assertEqual(302, response.status_code)
        
        response = self.client.post(toggle_url)
        self.assertEqual(302, response.status_code)
    
    def test_get_fail(self):
        self.client.login(username='lennon', password='test')
        follow_url = reverse('follow', args=['auth', 'user', self.hendrix.id])
        unfollow_url = reverse('follow', args=['auth', 'user', self.hendrix.id])
        
        response = self.client.get(follow_url)
        self.assertEqual(400, response.status_code)
        
        response = self.client.get(unfollow_url)
        self.assertEqual(400, response.status_code)
        
    def test_no_absolute_url(self):
        self.client.login(username='lennon', password='test')

        get_absolute_url = User.get_absolute_url
        User.get_absolute_url = None

        follow_url = utils.follow_link(self.hendrix)

        response = self.client.post(follow_url)
        self.assertEqual(500, response.status_code)

    def test_template_tags(self):
        follow_url = reverse('follow', args=['auth', 'user', self.hendrix.id])
        unfollow_url = reverse('unfollow', args=['auth', 'user', self.hendrix.id])
        
        request = type('Request', (object,), {'user': self.lennon})()
        
        self.assertEqual(follow_url, utils.follow_link(self.hendrix))
        self.assertEqual(unfollow_url, utils.unfollow_link(self.hendrix))
        
        tpl = template.Template("""{% load follow_tags %}{% follow_url obj %}""")
        ctx = template.Context({
            'obj':self.hendrix,
            'request': request
        })
        
        self.assertEqual(follow_url, tpl.render(ctx))
        
        utils.follow(self.lennon, self.hendrix)
        
        self.assertEqual(unfollow_url, tpl.render(ctx))
        
        utils.unfollow(self.lennon, self.hendrix)
        
        self.assertEqual(follow_url, tpl.render(ctx))
        
        tpl = template.Template("""{% load follow_tags %}{% follow_url obj user %}""")
        ctx2 = template.Context({
            'obj': self.lennon,
            'user': self.hendrix,
            'request': request
        })
        
        self.assertEqual(utils.follow_url(self.hendrix, self.lennon), tpl.render(ctx2))
        
        tpl = template.Template("""{% load follow_tags %}{% if request.user|is_following:obj %}True{% else %}False{% endif %}""")
        
        self.assertEqual("False", tpl.render(ctx))
        
        utils.follow(self.lennon, self.hendrix)
        
        self.assertEqual("True", tpl.render(ctx))
        
        tpl = template.Template("""{% load follow_tags %}{% follow_form obj %}""")
        self.assertEqual(True, isinstance(tpl.render(ctx), unicode))
        
        tpl = template.Template("""{% load follow_tags %}{% follow_form obj "follow/form.html" %}""")
        self.assertEqual(True, isinstance(tpl.render(ctx), unicode))

    def test_signals(self):
        Handler = type('Handler', (object,), {
            'inc': lambda self: setattr(self, 'i', getattr(self, 'i') + 1),
            'i': 0
        })
        user_handler = Handler()
        group_handler = Handler()
        
        def follow_handler(sender, user, target, instance, **kwargs):
            self.assertEqual(sender, User)
            self.assertEqual(self.lennon, user)
            self.assertEqual(self.hendrix, target)
            self.assertEqual(True, isinstance(instance, Follow))
            user_handler.inc()
        
        def unfollow_handler(sender, user, target, instance, **kwargs):
            self.assertEqual(sender, User)
            self.assertEqual(self.lennon, user)
            self.assertEqual(self.hendrix, target)
            self.assertEqual(True, isinstance(instance, Follow))
            user_handler.inc()
        
        def group_follow_handler(sender, **kwargs):
            self.assertEqual(sender, Group)
            group_handler.inc()        
        
        def group_unfollow_handler(sender, **kwargs):
            self.assertEqual(sender, Group)
            group_handler.inc()
        
        signals.followed.connect(follow_handler, sender=User, dispatch_uid='userfollow')
        signals.unfollowed.connect(unfollow_handler, sender=User, dispatch_uid='userunfollow')
        
        signals.followed.connect(group_follow_handler, sender=Group, dispatch_uid='groupfollow')
        signals.unfollowed.connect(group_unfollow_handler, sender=Group, dispatch_uid='groupunfollow')
        
        utils.follow(self.lennon, self.hendrix)
        utils.unfollow(self.lennon, self.hendrix)
        self.assertEqual(2, user_handler.i)
        
        utils.follow(self.lennon, self.musicians)
        utils.unfollow(self.lennon, self.musicians)
        
        self.assertEqual(2, user_handler.i)
        self.assertEqual(2, group_handler.i)

    def test_anonymous_is_following(self):
        self.assertEqual(False, Follow.objects.is_following(AnonymousUser(), self.lennon))

    


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^toggle/(?P<app>[^\/]+)/(?P<model>[^\/]+)/(?P<id>\d+)/$', 'follow.views.toggle', name='toggle'),
    url(r'^toggle/(?P<app>[^\/]+)/(?P<model>[^\/]+)/(?P<id>\d+)/$', 'follow.views.toggle', name='follow'),
    url(r'^toggle/(?P<app>[^\/]+)/(?P<model>[^\/]+)/(?P<id>\d+)/$', 'follow.views.toggle', name='unfollow'),
)

########NEW FILE########
__FILENAME__ = utils
from django.core.urlresolvers import reverse
from django.db.models.fields.related import ManyToManyField, ForeignKey
from follow.models import Follow
from follow.registry import registry, model_map

def get_followers_for_object(instance):
    return Follow.objects.get_follows(instance)

def register(model, field_name=None, related_name=None, lookup_method_name='get_follows'):
    """
    This registers any model class to be follow-able.
    
    """
    if model in registry:
        return

    registry.append(model)
    
    if not field_name:
        field_name = 'target_%s' % model._meta.module_name
    
    if not related_name:
        related_name = 'follow_%s' % model._meta.module_name
    
    field = ForeignKey(model, related_name=related_name, null=True,
        blank=True, db_index=True)
    
    field.contribute_to_class(Follow, field_name)
    setattr(model, lookup_method_name, get_followers_for_object)
    model_map[model] = [related_name, field_name]
    
def follow(user, obj):
    """ Make a user follow an object """
    follow, created = Follow.objects.get_or_create(user, obj)
    return follow

def unfollow(user, obj):
    """ Make a user unfollow an object """
    try:
        follow = Follow.objects.get_follows(obj).get(user=user)
        follow.delete()
        return follow 
    except Follow.DoesNotExist:
        pass

def toggle(user, obj):
    """ Toggles a follow status. Useful function if you don't want to perform follow
    checks but just toggle it on / off. """
    if Follow.objects.is_following(user, obj):
        return unfollow(user, obj)
    return follow(user, obj)    


def follow_link(object):
    return reverse('follow.views.toggle', args=[object._meta.app_label, object._meta.object_name.lower(), object.pk])

def unfollow_link(object):
    return reverse('follow.views.toggle', args=[object._meta.app_label, object._meta.object_name.lower(), object.pk])

def toggle_link(object):
    return reverse('follow.views.toggle', args=[object._meta.app_label, object._meta.object_name.lower(), object.pk])

def follow_url(user, obj):
    """ Returns the right follow/unfollow url """
    return toggle_link(obj)


########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required
from django.db.models.loading import cache
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseServerError, HttpResponseBadRequest
from follow.utils import follow as _follow, unfollow as _unfollow, toggle as _toggle

def check(func):
    """ 
    Check the permissions, http method and login state.
    """
    def iCheck(request, *args, **kwargs):
        if not request.method == "POST":
            return HttpResponseBadRequest("Must be POST request.")
        follow = func(request, *args, **kwargs)
        if request.is_ajax():
            return HttpResponse('ok')
        try:
            if 'next' in request.GET:
                return HttpResponseRedirect(request.GET.get('next'))
            if 'next' in request.POST:
                return HttpResponseRedirect(request.POST.get('next'))
            return HttpResponseRedirect(follow.target.get_absolute_url())
        except (AttributeError, TypeError):
            if 'HTTP_REFERER' in request.META:
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            if follow:
                return HttpResponseServerError('"%s" object of type ``%s`` has no method ``get_absolute_url()``.' % (
                    unicode(follow.target), follow.target.__class__))
            return HttpResponseServerError('No follow object and `next` parameter found.')
    return iCheck

@login_required
@check
def follow(request, app, model, id):
    model = cache.get_model(app, model)
    obj = model.objects.get(pk=id)
    return _follow(request.user, obj)

@login_required
@check
def unfollow(request, app, model, id):
    model = cache.get_model(app, model)
    obj = model.objects.get(pk=id)
    return _unfollow(request.user, obj)


@login_required
@check
def toggle(request, app, model, id):
    model = cache.get_model(app, model)
    obj = model.objects.get(pk=id)
    return _toggle(request.user, obj)

########NEW FILE########
