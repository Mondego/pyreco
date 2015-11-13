__FILENAME__ = models
from django.db import models

from social_login.abstract_models import (
    AbstractBaseSiteUser,
    AbstractInnerUserAuth,
    AbstractUserInfo,
)


class UserAuth(AbstractInnerUserAuth):
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=128)
    
    

class UserInfo(AbstractUserInfo):
    pass


# If you wanna extend the default SiteUser fields
# just inherit it, and adding your extra fields like bellow:
#
#class MyCustomSiteUser(AbstractBaseSiteUser):
#   ...
#   ...
#    
#    class Meta:
#        abstract = True

# finally, add SOCIAL_LOGIN_ABSTRACT_SITEUSER = 'app.MyCustomSiteUser'
# in settings.py


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
__FILENAME__ = urls
# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.home, name="home"),
    url(r'^account/login/?$', views.login, name="login"),
    url(r'^account/logout/?$', views.logout, name="logout"),
    url(r'^account/register/?$', views.register, name="register"),
    url(r'^account/register2/?$', views.register_step_2, name="register_step_2"),
    url(r'^account/login/error/?$', views.login_error, name="login_error"),
)
########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse

# in this example, import SiteUser just for get all users,
# to display at the home page.
# In a real project, It's not necessary import SiteUser usually
from social_login.models import SiteUser

# as same as SiteUser, import the following two just for this example
# to get the siet_name_zh
from socialoauth import socialsites
from socialoauth.utils import import_oauth_class



from .models import UserAuth, UserInfo


class RegisterLoginError(Exception):
    pass



def home(request):
    if request.siteuser:
        if not UserInfo.objects.filter(user_id=request.siteuser.id).exists():
            return HttpResponseRedirect(reverse('register_step_2'))
    
    
    all_users = SiteUser.objects.select_related('user_info', 'social_user').all()
    
    def _make_user_info(u):
        info = {}
        info['id'] = u.id
        info['social'] = u.is_social
        
        if info['social']:
            site_id = u.social_user.site_id
            s = import_oauth_class( socialsites.get_site_class_by_id(site_id) )()
            info['social'] = s.site_name_zh
            
        info['username'] = u.user_info.username
        info['avatar'] = u.user_info.avatar
        
        info['current'] = request.siteuser and request.siteuser.id == u.id
        return info
    
    users = map(_make_user_info, all_users)
    
    
    return render_to_response(
        'home.html',
        {
            'users': users,
        },
        context_instance=RequestContext(request)
    )



def register(request):
    if request.method == 'GET':
        return render_to_response(
            'register.html', context_instance=RequestContext(request)
        )
    
    def _register():
        email = request.POST.get('email', None)
        password = request.POST.get('password', None)
        if not email or not password:
            raise RegisterLoginError("Fill email and password")
        
        if UserAuth.objects.filter(email=email).exists():
            raise RegisterLoginError("Email has been taken")
        
        user = UserAuth.objects.create(email=email, password=password)
        return user
    
    try:
        user = _register()
        request.session['uid'] = user.user_id
        return HttpResponseRedirect(reverse('register_step_2'))
    except RegisterLoginError as e:
        return render_to_response(
            'register.html',
            {'error_msg': e},
            context_instance=RequestContext(request)
        )
    



def register_step_2(request):
    if not request.siteuser:
        return HttpResponseRedirect(reverse('home'))
    
    if request.method == 'GET':
        return render_to_response(
            'register_step_2.html',
            {'email': UserAuth.objects.get(user_id=request.siteuser.id).email},
            context_instance=RequestContext(request)
        )
    
    def _register_step_2():
        username = request.POST.get('username', None)
        if not username:
            raise RegisterLoginError("Fill in username")
        
        UserInfo.objects.create(user_id=request.siteuser.id, username=username)
        
    try:
        _register_step_2()
        return HttpResponseRedirect(reverse('home'))
    except RegisterLoginError as e:
        return render_to_response(
            'register_step_2.html',
            {
                'email': UserAuth.objects.get(user_id=request.siteuser.id).email,
                'error_msg': e
            },
            context_instance=RequestContext(request)
        )





def login(request):
    if request.siteuser:
        # already logged in
        return HttpResponseRedirect(reverse('home'))
    
    if request.method == 'GET':
        return render_to_response(
            'login.html',
            context_instance=RequestContext(request)
        )
    
    def _login():
        email = request.POST.get('email', None)
        password = request.POST.get('password', None)
        if not email or not password:
            raise RegisterLoginError("Fill email and password")
        
        if not UserAuth.objects.filter(email=email, password=password).exists():
            raise RegisterLoginError("Invalid account")
        
        user = UserAuth.objects.get(email=email, password=password)
        return user
    
    try:
        user = _login()
        request.session['uid'] = user.user_id
        return HttpResponseRedirect(reverse('home'))
    except RegisterLoginError as e:
        return render_to_response(
            'login.html',
            {'error_msg': e},
            context_instance=RequestContext(request)
        )



def logout(request):
    try:
        del request.session['uid']
    except:
        pass
    finally:
        return HttpResponseRedirect(reverse('home'))




def login_error(request):
    return HttpResponse("OAuth Failure!")

########NEW FILE########
__FILENAME__ = settings
import os
import sys

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.dirname(CURRENT_PATH)
PROJECT_PATH = os.path.dirname(ROOT_PATH)


try:
    import social_login
except ImportError:
    sys.path.insert(0, PROJECT_PATH)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(ROOT_PATH, 'test.db'),                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        #'NAME': '',
        #'USER': '',
        #'PASSWORD': '',
        #'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        #'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Asia/Shanghai'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = False
USE_L10N = False
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(ROOT_PATH, 'static'),
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
SECRET_KEY = 'hp_p()zv$@f-n5=_al&nn-2h=v!^^31tp0g%9z0)@35o+*63yk'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    #'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    #'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'social_login.context_processors.social_sites',
)



MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_login.middleware.SocialLoginUser',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
)

#INTERNAL_IPS = ('127.0.0.1',)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    
    'app',
    'social_login',
    #'debug_toolbar',
)

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


SOCIAL_LOGIN_USER_INFO_MODEL = 'app.UserInfo'
SOCIAL_LOGIN_ERROR_REDIRECT_URL = '/account/login/error'
#SOCIAL_LOGIN_SITEUSER_SELECT_RELATED = ('user_info', 'social_user', 'inner_user')
#SOCIAL_LOGIN_ABSTARCT_SITEUSER = 'yourapp.YourCustomAbstractSiteUser'

try:
    from local_settings import *
except:
    pass
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('app.urls')),
    url(r'', include('social_login.urls')),
)



from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = abstract_models
# -*- coding: utf-8 -*-

from django.db import models

from .manager import InnerUserManager


class AbstractBaseSiteUser(models.Model):
    """
    Abstract model for store the common info of social user and inner user.
    You can extend the abstract model like this:
    
    class CustomAbstractSiteUser(AbstractBaseSiteUser):
        # some extra fields...
        
        class Meta:
            abstract = True
            
    then, and your model in settings.py file:
    SOCIAL_LOGIN_ABSTRACT_SITEUSER = 'myapp.CustomAbstractSiteUser'
    """
    is_social = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        abstract = True
        
        
        

# your project's user model must inherit from the following two abstarct model

class AbstractInnerUserAuth(models.Model):
    user = models.OneToOneField('social_login.SiteUser', related_name='inner_user')
    objects = InnerUserManager()
    
    class Meta:
        abstract = True
        
        
class AbstractUserInfo(models.Model):
    user = models.OneToOneField('social_login.SiteUser', related_name='user_info')
    username = models.CharField(max_length=32)
    avatar = models.CharField(max_length=255, blank=True)
    
    class Meta:
        abstract = True

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from .app_settings import SOCIAL_LOGIN_ENABLE_ADMIN

if SOCIAL_LOGIN_ENABLE_ADMIN:
    from django.contrib import admin
    from .models import SiteUser
    
    class SiteUserAdmin(admin.ModelAdmin):
        list_display = ('id', 'Username', 'Avatar', 'is_social', 'is_active',
                        'date_joined', 'SiteId')
        list_filter = ('is_social',)
        
        def Username(self, obj):
            return obj.user_info.username
        
        def Avatar(self, obj):
            return '<img src="%s" />' % obj.user_info.avatar
        Avatar.allow_tags = True
        
        def SiteId(self, obj):
            #return SocialUser.objects.get(id=obj.id).site_id
            return obj.social_user.site_id
        
        
    admin.site.register(SiteUser, SiteUserAdmin)

########NEW FILE########
__FILENAME__ = app_settings
# -*- coding: utf-8 -*-

from django.conf import settings

# the following three are REQUIRED in django.conf.settings
SOCIALOAUTH_SITES = settings.SOCIALOAUTH_SITES
SOCIAL_LOGIN_USER_INFO_MODEL = settings.SOCIAL_LOGIN_USER_INFO_MODEL
SOCIAL_LOGIN_ERROR_REDIRECT_URL = settings.SOCIAL_LOGIN_ERROR_REDIRECT_URL


SOCIAL_LOGIN_UID_LENGTH = getattr(settings, 'SOCIAL_LOGIN_UID_LENGTH', 255)
SOCIAL_LOGIN_ENABLE_ADMIN = getattr(settings, 'SOCIAL_LOGIN_ENABLE_ADMIN', True)


SOCIAL_LOGIN_CALLBACK_URL_PATTERN = getattr(settings,
                                            'SOCIAL_LOGIN_CALLBACK_URL_PATTERN',
                                            r'^account/oauth/(?P<sitename>\w+)/?$'
                                            )

SOCIAL_LOGIN_DONE_REDIRECT_URL = getattr(settings,
                                         'SOCIAL_LOGIN_DONE_REDIRECT_URL',
                                         '/'
                                         )

SOCIAL_LOGIN_SITEUSER_SELECT_RELATED = getattr(settings,
                                               'SOCIAL_LOGIN_SITEUSER_SELECT_RELATED',
                                               ('user_info',)
                                               )
########NEW FILE########
__FILENAME__ = context_processors
# -*- coding: utf-8 -*-

from socialoauth import socialsites
from socialoauth.utils import import_oauth_class

from .utils import LazyList

# add 'social_login.context_processors.social_sites' in TEMPLATE_CONTEXT_PROCESSORS
# then in template, you can get this sites via {% for s in social_sites %} ... {% endfor %}
# Don't worry about the performance,
# `social_sites` is a lazy object, it readly called just access the `social_sites`


def social_sites(request):
    def _social_sites():
        def make_site(s):
            s = import_oauth_class(s)()
            return {
                'site_id': s.site_id,
                'site_name': s.site_name,
                'site_name_zh': s.site_name_zh,
                'authorize_url': s.authorize_url,
            }
        return [make_site(s) for s in socialsites.list_sites()]
    
    return {'social_sites': LazyList(_social_sites)}

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

from django.db import models


class BaseManager(models.Manager):
    def create(self, is_social, **kwargs):
        if 'user' not in kwargs and 'user_id' not in kwargs:
            siteuser_model = models.get_model('social_login', 'SiteUser')
            user = siteuser_model.objects.create(is_social=is_social)
            kwargs['user_id'] = user.id
            
        return super(BaseManager, self).create(**kwargs)



class SocialUserManager(BaseManager):
    def create(self, **kwargs):
        return super(SocialUserManager, self).create(True, **kwargs)
        
        
class InnerUserManager(BaseManager):
    def create(self, **kwargs):
        return super(InnerUserManager, self).create(False, **kwargs)
        

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-

from django.utils.functional import SimpleLazyObject

from .models import SiteUser
from .app_settings import SOCIAL_LOGIN_SITEUSER_SELECT_RELATED

# add 'social_login.middleware.SocialLoginUser' in MIDDLEWARE_CLASSES
# then the request object will has a `siteuser` property
#
# you can using it like this:
# if request.siteuser:
#     # there has a logged user,
#     uid = request.siteuser.id
# else:
#     # no one is logged
#
# Don't worry about the performance,
# `siteuser` is a lazy object, it readly called just access the `request.siteuser`



class SocialLoginUser(object):
    def process_request(self, request):
        def get_user():
            uid = request.session.get('uid', None)
            if not uid:
                return None
            
            try:
                user = SiteUser.objects.select_related(
                    *SOCIAL_LOGIN_SITEUSER_SELECT_RELATED).get(id=int(uid))
            except SiteUser.DoesNotExist:
                return None
            
            if not user.is_active:
                user = None
            return user
        
        request.siteuser = SimpleLazyObject(get_user)
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings

from .app_settings import SOCIAL_LOGIN_UID_LENGTH
from .manager import SocialUserManager




def _abstract_siteuser():
    custom_siteuser = getattr(settings, 'SOCIAL_LOGIN_ABSTRACT_SITEUSER', None)
    if not custom_siteuser:
        from .abstract_models import AbstractBaseSiteUser
        return AbstractBaseSiteUser
    
    _app, _model = custom_siteuser.split('.')
    _module = __import__('%s.models' % _app, fromlist=[_model])
    _model = getattr(_module, _model)
    
    if not _model._meta.abstract:
        raise AttributeError("%s must be abstract model" % custom_siteuser)
    return _model



class SiteUser(_abstract_siteuser()):
    
    def __unicode__(self):
        return '<SiteUser %d>' % self.id




class SocialUser(models.Model):
    user = models.OneToOneField(SiteUser, related_name='social_user')
    site_uid = models.CharField(max_length=SOCIAL_LOGIN_UID_LENGTH)
    site_id = models.SmallIntegerField()
    
    objects = SocialUserManager()
    
    class Meta:
        unique_together = (('site_uid', 'site_id'),)



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
__FILENAME__ = urls
# -*- coding:utf-8 -*-

from django.conf.urls import patterns, url


from .views import social_login_callback
from .app_settings import SOCIAL_LOGIN_CALLBACK_URL_PATTERN


# SOCIAL_LOGIN_CALLBACK_URL_PATTERN is the OAuth2 call back url format.
# settings this in Social site which you are using the OAuth2 services.

urlpatterns = patterns('',
    url(SOCIAL_LOGIN_CALLBACK_URL_PATTERN,
        social_login_callback,
        name='social_login_callback'),
)
########NEW FILE########
__FILENAME__ = utils
# -*- coding:utf-8 -*-

from django.utils.functional import empty, SimpleLazyObject

class LazyList(SimpleLazyObject):
    def __iter__(self):
        if self._wrapped is empty:
            self._setup()
            
        for i in self._wrapped:
            yield i
            
            
    def __len__(self):
        if self._wrapped is empty:
            self._setup()
            
        return len(self._wrapped)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.db.models import get_model

from socialoauth import socialsites
from socialoauth.utils import import_oauth_class
from socialoauth.exception import SocialAPIError

from .models import SocialUser


from .app_settings import (
    SOCIALOAUTH_SITES,
    SOCIAL_LOGIN_USER_INFO_MODEL,
    SOCIAL_LOGIN_DONE_REDIRECT_URL,
    SOCIAL_LOGIN_ERROR_REDIRECT_URL,
)


socialsites.config(SOCIALOAUTH_SITES)


def social_login_callback(request, sitename):
    code = request.GET.get('code', None)
    if not code:
        # Maybe user not authorize
        return HttpResponseRedirect(SOCIAL_LOGIN_ERROR_REDIRECT_URL)
    
    s = import_oauth_class(socialsites[sitename])()
    
    try:
        s.get_access_token(code)
    except SocialAPIError:
        # see social_oauth example and docs
        return HttpResponseRedirect(SOCIAL_LOGIN_ERROR_REDIRECT_URL)
    
    
    user_info_model = get_model(*SOCIAL_LOGIN_USER_INFO_MODEL.split('.'))
    try:
        user = SocialUser.objects.get(site_uid=s.uid, site_id=s.site_id)
        #got user, update username and avatar
        user_info_model.objects.filter(user_id=user.user_id).update(
            username=s.name, avatar=s.avatar
        )
        
    except SocialUser.DoesNotExist:
        user = SocialUser.objects.create(site_uid=s.uid, site_id=s.site_id)
        user_info_model.objects.create(
            user_id=user.user_id,
            username=s.name,
            avatar=s.avatar
        )
        
    # set uid in session, then next time, this user will be auto loggin
    request.session['uid'] = user.user_id
    
    # done
    return HttpResponseRedirect(SOCIAL_LOGIN_DONE_REDIRECT_URL)


########NEW FILE########
