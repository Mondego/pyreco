__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = siteuser_custom
from django.db import models

class SiteUserExtend(models.Model):
    score = models.IntegerField(default=0)
    nimei = models.CharField(max_length=12)

    class Meta:
        abstract = True


class AccountMixIn(object):
    login_template = 'login.html'
    register_template = 'register.html'
    reset_passwd_template = 'reset_password.html'
    change_passwd_template = 'change_password.html'
    notify_template = 'notify.html'

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
    url(r'^account/settings/?$', views.account_settings, name="account_settings"),
)
########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from siteuser.users.models import SiteUser
from siteuser import settings as siteuser_settings

if siteuser_settings.USING_SOCIAL_LOGIN:
    from socialoauth import SocialSites

def home(request):
    if siteuser_settings.USING_SOCIAL_LOGIN:
        socialsites = SocialSites(settings.SOCIALOAUTH_SITES)

    def _make_user_info(u):
        info = {}
        info['id'] = u.id
        info['social'] = u.is_social
        
        if siteuser_settings.USING_SOCIAL_LOGIN and info['social']:
            info['social'] = socialsites.get_site_object_by_name(u.social_user.site_name).site_name_zh
            
        info['username'] = u.username
        info['avatar'] = u.avatar
        info['current'] = request.siteuser and request.siteuser.id == u.id
        return info

    all_users = SiteUser.objects.all()
    users = map(_make_user_info, all_users)
    
    return render_to_response(
        'home.html',
        {
            'users': users,
        },
        context_instance = RequestContext(request)
    )

def account_settings(request):
    return render_to_response(
        'account_settings.html', context_instance=RequestContext(request)
    )

def _test(request, *args, **kwargs):
    return HttpResponse("here")
########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
import os
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
EXAMPLE_PATH = os.path.dirname(CURRENT_PATH)
PROJECT_PATH = os.path.dirname(EXAMPLE_PATH)

import djcelery
djcelery.setup_loader()

try:
    import siteuser
except ImportError:
    import sys
    sys.path.append(PROJECT_PATH)
    import siteuser

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        #'NAME': os.path.join(EXAMPLE_PATH, 'test.db'),
        'NAME': 'siteuser',
        # The following settings are not used with sqlite3:
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3306',
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
USE_TZ = True

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
SECRET_KEY = 'ye01zdn5rdgbi(#s^krsd#$oqc_7azv9l!a@&=eb3pwwy7m6u*'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    #'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    #'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    #'django.contrib.messages.context_processors.messages',
    'siteuser.context_processors.social_sites',
)


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'siteuser.middleware.User',
)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    siteuser.SITEUSER_TEMPLATE,
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    #'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
    #'django.contrib.messages',
    #'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'djcelery',
    'app',
    'siteuser.users',
    'siteuser.upload_avatar',
    'siteuser.notify',
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

BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

USING_SOCIAL_LOGIN = False
AVATAR_DIR = os.path.join(EXAMPLE_PATH, 'avatar')

SITEUSER_ACCOUNT_MIXIN = 'app.siteuser_custom.AccountMixIn'
SITEUSER_EXTEND_MODEL = 'app.siteuser_custom.SiteUserExtend'

USER_LINK = lambda uid: '/user/{0}'.format(uid)

try:
    from local_settings import *
except ImportError:
    pass
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    url(r'', include('siteuser.urls')),
    url(r'', include('app.urls')),
)


from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()

# for test
from app.views import _test
urlpatterns += patterns('',
    url(r'^.+/?$', _test),
)
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
__FILENAME__ = context_processors
# -*- coding: utf-8 -*-

from siteuser.utils import LazyList
from siteuser.settings import USING_SOCIAL_LOGIN, SOCIALOAUTH_SITES

if USING_SOCIAL_LOGIN:
    from socialoauth import SocialSites

# add 'siteuser.context_processors.social_sites' in TEMPLATE_CONTEXT_PROCESSORS
# then in template, you can get this sites via {% for s in social_sites %} ... {% endfor %}
# Don't worry about the performance,
# `social_sites` is a lazy object, it readly called just access the `social_sites`


def social_sites(request):
    def _social_sites():
        def make_site(site_class):
            s = socialsites.get_site_object_by_class(site_class)
            return {
                'site_name': s.site_name,
                'site_name_zh': s.site_name_zh,
                'authorize_url': s.authorize_url,
            }
        socialsites = SocialSites(SOCIALOAUTH_SITES)
        return [make_site(site_class) for site_class in socialsites.list_sites_class()]

    if SOCIALOAUTH_SITES:
        return {'social_sites': LazyList(_social_sites)}
    return {'social_sites': []}

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
from functools import wraps

from django.http import HttpResponseRedirect
from django.http import Http404

def login_needed(login_url=None):
    def deco(func):
        @wraps(func)
        def wrap(request, *args, **kwargs):
            if not request.siteuser:
                # No login
                if login_url:
                    return HttpResponseRedirect(login_url)
                raise Http404

            return func(request, *args, **kwargs)
        return wrap
########NEW FILE########
__FILENAME__ = mail
# -*- coding: utf-8 -*-
import smtplib
from email.mime.text import MIMEText


def send_mail(host, port, username, password, mail_from, mail_to, mail_subject, mail_content, mail_type, display_from=None):
    if isinstance(mail_content, unicode):
        mail_content = mail_content.encode('utf-8')
    content = MIMEText(mail_content, mail_type, 'utf-8')
    content['From'] = display_from or mail_from
    if isinstance(mail_to, (list, tuple)):
        content['To'] = ', '.join(mail_to)
    else:
        content['To'] = mail_to
    content['Subject'] = mail_subject

    s = smtplib.SMTP()
    s.connect(host, port)
    s.login(username, password)
    s.sendmail(mail_from, mail_to, content.as_string())
    s.quit()

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-

from django.utils.functional import SimpleLazyObject

from siteuser.users.models import SiteUser

# add 'siteuser.middleware.User' in MIDDLEWARE_CLASSES
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



class User(object):
    def process_request(self, request):
        def get_user():
            uid = request.session.get('uid', None)
            if not uid:
                return None

            try:
                user = SiteUser.objects.get(id=int(uid))
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
from django.utils import timezone


class Notify(models.Model):
    """
    link - 此通知链接到的页面
    text - 此通知的文字，也就是展示出来的内容
    """
    user = models.ForeignKey('users.SiteUser', related_name='notifies')
    sender = models.ForeignKey('users.SiteUser')
    link = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    notify_at = models.DateTimeField()
    has_read = models.BooleanField(default=False)

    def __unicode__(self):
        return u'<Notify %d>' % self.id

    @classmethod
    def create(cls, **kwargs):
        kwargs['notify_at'] = timezone.now()
        cls.objects.create(**kwargs)
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
from siteuser.notify import views

urlpatterns = patterns('',
    # ajax 获取通知
    url(r'^notifies.json/$', views.notifies_json),
    # 普通页面浏览获取通知
    url(r'^notifies/$', views.get_notifies, name="siteuser_nofities"),

    # 点击一个通知
    url(r'^notify/confirm/(?P<notify_id>\d+)/$', views.notify_confirm, name='siteuser_notify_confirm')
)
########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.template import RequestContext

from siteuser.notify.models import Notify
from siteuser.utils import load_user_define

"""
这只是一个简单的通知系统，产生的通知格式如下：
［谁］在［哪个条目/帖子］中回复了你
因为在生成的通知里有 ［谁］ 这个用户链接，所以用户必须自己在settings.py中定义 USER_LINK
这个方法，它接受一个参数：用户id，然后返回用户个人页面的url

有两种方式获取通知：
    1. GET /notifies.json/ 返回的是未读的通知，只要用js将返回的html组织在合适dom元素中即可
    2. GET /notifies/      用一个页面来展示全部的通知。包括已经处理过的通知

所以就必须设置 SITEUSER_ACCOUNT_MIXIN, 在其中指定 notify_template

点击一个未读的通知:
    GET /notify/confirm/<notify_id>/ 如果正确，就会跳转到相应的页面
"""


user_define = load_user_define.user_defined_mixin()()
notify_template = getattr(user_define, 'notify_template', None)
if not notify_template:
    raise ImproperlyConfigured('SITEUSER_ACCOUNT_MIXIN has no attribute "notify_template"')

get_notify_context = getattr(user_define, 'get_notify_context', None)
if not get_notify_context:
    get_notify_context = lambda x: {}

def notifies_json(request):
    """由Ajax获取的未读通知"""
    user = request.siteuser
    if not user:
        return HttpResponse(json.dumps([]), mimetype='application/json')

    notifies = Notify.objects.filter(user=user, has_read=False).select_related('sender').order_by('-notify_at')
    def _make_html(n):
        return u'<a href="{0}" target="_blank">{1}</a> 在 <a href="{2}" target="_blank">{3}</a> 中回复了你'.format(
            settings.USER_LINK(n.sender.id),
            n.sender.username,
            reverse('siteuser_notify_confirm', kwargs={'notify_id': n.id}),
            n.text,
        )
    html = [_make_html(n) for n in notifies]
    return HttpResponse(json.dumps(html), mimetype='application/json')


def get_notifies(request):
    """页面展示全部通知"""
    user = request.siteuser
    if not user:
        return HttpResponseRedirect(reverse('siteuser_login'))

    notifies = Notify.objects.filter(user=user).select_related('sender').order_by('-notify_at')
    # TODO 分页
    ctx = get_notify_context(request)
    ctx['notifies'] = notifies
    return render_to_response(
        notify_template,
        ctx,
        context_instance=RequestContext(request)
    )


def notify_confirm(request, notify_id):
    """点击通知上的链接，将此通知设置为has_read=True，然后转至此通知的link"""
    try:
        n = Notify.objects.get(id=notify_id)
    except Notify.DoesNotExist:
        raise Http404

    if not n.has_read:
        n.has_read = True
        n.save()

    return HttpResponseRedirect(n.link)
########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import os
from django.conf import settings

# 默认不打开第三方登录
USING_SOCIAL_LOGIN = getattr(settings, 'USING_SOCIAL_LOGIN', False)

if USING_SOCIAL_LOGIN:
    ### 第三方帐号登录 - 配置见soicaloauth文档和例子
    SOCIALOAUTH_SITES = settings.SOCIALOAUTH_SITES
else:
    SOCIALOAUTH_SITES = None

### 头像目录 - 需要在项目的settings.py中设置
AVATAR_DIR = settings.AVATAR_DIR

# 上传的原始图片目录, 默认和头像目录相同
AVATAR_UPLOAD_DIR = getattr(settings, 'AVATAR_UPLOAD_DIR', AVATAR_DIR)

# 默认头像的文件名，需要将其放入AVATAR_DIR 头像目录
DEFAULT_AVATAR = getattr(settings, 'DEFAULT_AVATAR', 'default_avatar.png')

if not os.path.isdir(AVATAR_DIR):
    os.mkdir(AVATAR_DIR)
if not os.path.isdir(AVATAR_UPLOAD_DIR):
    os.mkdir(AVATAR_UPLOAD_DIR)

# 头像url的前缀
AVATAR_URL_PREFIX = getattr(settings, 'AVATAR_URL_PREFIX', '/static/avatar/')

# 原始上传的图片url前缀，用于在裁剪选择区域显示原始图片
AVATAR_UPLOAD_URL_PREFIX = getattr(settings, 'AVATAR_UPLOAD_URL_PREFIX', AVATAR_URL_PREFIX)

# 最大可上传图片大小 MB
AVATAR_UPLOAD_MAX_SIZE =  getattr(settings, 'AVATAR_UPLOAD_MAX_SIZE', 5)

# 剪裁后的大小 px
AVATAR_RESIZE_SIZE = getattr(settings, 'AVATAR_RESIZE_SIZE', 50)

# 头像处理完毕后保存的格式和质量， 格式还可以是 jpep, gif
AVATAR_SAVE_FORMAT = getattr(settings, 'AVATAR_SAVE_FORMAT', 'png')
AVATAR_SAVE_QUALITY = getattr(settings, 'AVATAR_SAVE_QUALITY', 90)


# 注册用户的电子邮件最大长度
MAX_EMAIL_LENGTH = getattr(settings, 'MAX_EMAIL_LENGTH', 128)

# 注册用户的用户名最大长度
MAX_USERNAME_LENGTH = getattr(settings, 'MAX_USERNAME_LENGTH', 12)


# 第三方帐号授权成功后跳转的URL
SOCIAL_LOGIN_DONE_REDIRECT_URL = getattr(settings, 'SOCIAL_LOGIN_DONE_REDIRECT_URL', '/')
# 授权失败后跳转的URL
SOCIAL_LOGIN_ERROR_REDIRECT_URL = getattr(settings, 'SOCIAL_LOGIN_ERROR_REDIRECT_URL', '/')
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import os

from django.db import models
from django.db.models.signals import post_delete


from siteuser.settings import (
    AVATAR_DIR,
)


class UploadedImage(models.Model):
    uid = models.IntegerField(unique=True)
    image = models.CharField(max_length=128)

    def get_image_path(self):
        path = os.path.join(AVATAR_DIR, self.image)
        if not os.path.exists(path):
            return None
        return path

    def delete_image(self):
        path = self.get_image_path()
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


def _delete_avatar_on_disk(sender, instance, *args, **kwargs):
    instance.delete_image()


post_delete.connect(_delete_avatar_on_disk, sender=UploadedImage)

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-

from django.dispatch import Signal

avatar_upload_done = Signal(providing_args=['uid', 'avatar_name'])
avatar_crop_done = Signal(providing_args=['uid', 'avatar_name'])
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

from siteuser.upload_avatar import views

urlpatterns = patterns('',
    url(r'^uploadavatar_upload/?$', views.upload_avatar, name="uploadavatar_upload"),
    url(r'^uploadavatar_crop/?$', views.crop_avatar, name="uploadavatar_crop"),
)
########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

import os
import hashlib
import time
from functools import wraps

from PIL import Image

from django.http import HttpResponse
from django.utils.crypto import get_random_string

from siteuser.settings import (
    AVATAR_UPLOAD_MAX_SIZE,
    AVATAR_UPLOAD_DIR,
    AVATAR_DIR,
    AVATAR_UPLOAD_URL_PREFIX,
    AVATAR_RESIZE_SIZE,
    AVATAR_SAVE_FORMAT,
    AVATAR_SAVE_QUALITY,
)

from siteuser.upload_avatar.signals import avatar_upload_done, avatar_crop_done
from siteuser.upload_avatar.models import UploadedImage

"""
用户上传图片分三步：
    1.  上传一张图片，服务器将其保存起来，并且把url返回给浏览器
    2.  浏览器在预览区域显示这张图片，然后加载js库来剪裁图片。
    3.  其实js库只是获取了选框四个顶点对应于图片的坐标，然后还要将这个坐标发送到服务器，服务器剪裁图片
"""

border_size = 300

test_func = lambda request: request.method == 'POST' and request.siteuser
get_uid = lambda request: request.siteuser.id


class UploadAvatarError(Exception):
    pass


def protected(func):
    @wraps(func)
    def deco(request, *args, **kwargs):
        if not test_func(request):
            return HttpResponse(
                "<script>window.parent.upload_avatar_error('%s')</script>" % '禁止操作'
            )
        try:
            return func(request, *args, **kwargs)
        except UploadAvatarError as e:
            return HttpResponse(
                "<script>window.parent.upload_avatar_error('%s')</script>" % e
            )
    return deco


@protected
def upload_avatar(request):
    """上传图片"""
    try:
        uploaded_file = request.FILES['uploadavatarfile']
    except KeyError:
        raise UploadAvatarError('请正确上传图片')

    if uploaded_file.size > AVATAR_UPLOAD_MAX_SIZE * 1024 * 1024:
        raise UploadAvatarError('图片不能大于{0}MB'.format(AVATAR_UPLOAD_MAX_SIZE))

    name, ext = os.path.splitext(uploaded_file.name)
    new_name = hashlib.md5('{0}{1}'.format(get_random_string(), time.time())).hexdigest()
    new_name = '%s%s' % (new_name, ext.lower())

    fpath = os.path.join(AVATAR_UPLOAD_DIR, new_name)

    try:
        with open(fpath, 'wb') as f:
            for c in uploaded_file.chunks(10240):
                f.write(c)
    except IOError:
        raise UploadAvatarError('发生错误，稍后再试')

    try:
        Image.open(fpath)
    except IOError:
        try:
            os.unlink(fpath)
        except:
            pass
        raise UploadAvatarError('请正确上传图片')

    # uploaed image has been saved on disk, now save it's name in db
    if UploadedImage.objects.filter(uid=get_uid(request)).exists():
        _obj = UploadedImage.objects.get(uid=get_uid(request))
        _obj.delete_image()
        _obj.image = new_name
        _obj.save()
    else:
        UploadedImage.objects.create(uid=get_uid(request), image=new_name)

    # 上传完毕
    avatar_upload_done.send(sender=None,
                            uid=get_uid(request),
                            avatar_name=new_name,
                            dispatch_uid='siteuser_avatar_upload_done'
                            )

    return HttpResponse(
        "<script>window.parent.upload_avatar_success('%s')</script>" % (
            AVATAR_UPLOAD_URL_PREFIX + new_name
        )
    )


@protected
def crop_avatar(request):
    """剪裁头像"""
    try:
        upim = UploadedImage.objects.get(uid=get_uid(request))
    except UploadedImage.DoesNotExist:
        raise UploadAvatarError('请先上传图片')

    image_orig = upim.get_image_path()
    if not image_orig:
        raise UploadAvatarError('请先上传图片')

    try:
        x1 = int(float(request.POST['x1']))
        y1 = int(float(request.POST['y1']))
        x2 = int(float(request.POST['x2']))
        y2 = int(float(request.POST['y2']))
    except:
        raise UploadAvatarError('发生错误，稍后再试')


    try:
        orig = Image.open(image_orig)
    except IOError:
        raise UploadAvatarError('发生错误，请重新上传图片')

    orig_w, orig_h = orig.size
    if orig_w <= border_size and orig_h <= border_size:
        ratio = 1
    else:
        if orig_w > orig_h:
            ratio = float(orig_w) / border_size
        else:
            ratio = float(orig_h) / border_size

    box = [int(x * ratio) for x in [x1, y1, x2, y2]]
    avatar = orig.crop(box)
    avatar_name, _ = os.path.splitext(upim.image)


    size = AVATAR_RESIZE_SIZE
    try:
        res = avatar.resize((size, size), Image.ANTIALIAS)
        res_name = '%s-%d.%s' % (avatar_name, size, AVATAR_SAVE_FORMAT)
        res_path = os.path.join(AVATAR_DIR, res_name)
        res.save(res_path, AVATAR_SAVE_FORMAT, quality=AVATAR_SAVE_QUALITY)
    except:
        raise UploadAvatarError('发生错误，请稍后重试')


    avatar_crop_done.send(sender = None,
                          uid = get_uid(request),
                          avatar_name = res_name,
                          dispatch_uid = 'siteuser_avatar_crop_done'
                          )

    return HttpResponse(
        "<script>window.parent.crop_avatar_success('%s')</script>"  % '成功'
    )

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings

from siteuser.users.urls import urlpatterns
from siteuser.upload_avatar.urls import urlpatterns as upurls
from siteuser.notify.urls import urlpatterns as nourls

siteuser_url_table = {
    'siteuser.upload_avatar': upurls,
    'siteuser.notify': nourls,
}

for app in settings.INSTALLED_APPS:
    if app in siteuser_url_table:
        urlpatterns += siteuser_url_table[app]

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.db import models
from django.utils import timezone

from siteuser.settings import (
    MAX_EMAIL_LENGTH,
    MAX_USERNAME_LENGTH,
    AVATAR_URL_PREFIX,
    DEFAULT_AVATAR,
    AVATAR_DIR,
)

from siteuser.upload_avatar.signals import avatar_crop_done

"""
siteuser的核心，
    SocialUser - 保存第三方帐号
    InnerUser  - 网站自身注册用户
    SiteUser   - 用户信息表

目前 SocialUser, InnerUser 都不支持扩展，方法直接写死。
这种在只支持第三方登录的应用情况下，是够用的。

SiteUser 之定义了最基本的数据，用户可以自由的扩展字段。
需要注意的是， SiteUser中的 username 不能设置为 unique = True
因为第三方社交帐号的username也保存在这个表里，
然而不同社交站点的用户完全有可能重名。
"""



class SiteUserManager(models.Manager):
    def create(self, is_social, **kwargs):
        if 'user' not in kwargs and 'user_id' not in kwargs:
            siteuser_kwargs = {
                'is_social': is_social,
                'username': kwargs.pop('username'),
                'date_joined': timezone.now(),
            }
            if 'avatar_url' in kwargs:
                siteuser_kwargs['avatar_url'] = kwargs.pop('avatar_url')
            user = SiteUser.objects.create(**siteuser_kwargs)
            kwargs['user_id'] = user.id

        return super(SiteUserManager, self).create(**kwargs)


class SocialUserManager(SiteUserManager):
    def create(self, **kwargs):
        return super(SocialUserManager, self).create(True, **kwargs)


class InnerUserManager(SiteUserManager):
    def create(self, **kwargs):
        return super(InnerUserManager, self).create(False, **kwargs)


class SocialUser(models.Model):
    """第三方帐号"""
    user = models.OneToOneField('SiteUser', related_name='social_user')
    site_uid = models.CharField(max_length=128)
    site_name = models.CharField(max_length=32)

    objects = SocialUserManager()

    class Meta:
        unique_together = (('site_uid', 'site_name'),)


class InnerUser(models.Model):
    """自身注册用户"""
    user = models.OneToOneField('SiteUser', related_name='inner_user')
    email = models.CharField(max_length=MAX_EMAIL_LENGTH, unique=True)
    passwd = models.CharField(max_length=40)

    objects = InnerUserManager()


def _siteuser_extend():
    siteuser_extend_model = getattr(settings, 'SITEUSER_EXTEND_MODEL', None)
    if not siteuser_extend_model:
        return models.Model

    if isinstance(siteuser_extend_model, models.base.ModelBase):
        # 直接定义的 SITEUSER_EXTEND_MODEL
        if not siteuser_extend_model._meta.abstract:
            raise AttributeError("%s must be an abstract model" % siteuser_extend_model.__name__)
        return siteuser_extend_model

    # 以string的方式定义的 SITEUSER_EXTEND_MODEL
    _module, _model = siteuser_extend_model.rsplit('.', 1)
    try:
        m = __import__(_module, fromlist=['.'])
        _model = getattr(m, _model)
    except:
        m = __import__(_module + '.models', fromlist=['.'])
        _model = getattr(m, _model)
    
    if not _model._meta.abstract:
        raise AttributeError("%s must be an abstract model" % siteuser_extend_model)
    return _model



class SiteUser(_siteuser_extend()):
    """用户信息，如果需要（大部分情况也确实是需要）扩展SiteUser的字段，
    需要定义SITEUSER_EXTEND_MODEL.此model必须设置 abstract=True
    """
    is_social = models.BooleanField()
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField()

    username = models.CharField(max_length=MAX_USERNAME_LENGTH, db_index=True)
    # avatar_url for social user
    avatar_url = models.CharField(max_length=255, blank=True)
    # avatar_name for inner user uploaded avatar
    avatar_name = models.CharField(max_length=64, blank=True)

    def __unicode__(self):
        return u'<SiteUser %d, %s>' % (self.id, self.username)

    @property
    def avatar(self):
        if not self.avatar_url and not self.avatar_name:
            return AVATAR_URL_PREFIX + DEFAULT_AVATAR
        if self.is_social:
            return self.avatar_url
        return AVATAR_URL_PREFIX + self.avatar_name


def _save_avatar_in_db(sender, uid, avatar_name, **kwargs):
    if not SiteUser.objects.filter(id=uid, is_social=False).exists():
        return

    old_avatar_name = SiteUser.objects.get(id=uid).avatar_name
    if old_avatar_name == avatar_name:
        # 上传一张图片后，连续剪裁的情况
        return

    if old_avatar_name:
        _path = os.path.join(AVATAR_DIR, old_avatar_name)
        try:
            os.unlink(_path)
        except:
            pass

    SiteUser.objects.filter(id=uid).update(avatar_name=avatar_name)


avatar_crop_done.connect(_save_avatar_in_db)

########NEW FILE########
__FILENAME__ = tasks
# -*- coding: utf-8 -*-

from celery import task

from siteuser.functional import send_html_mail as _send_mail

@task
def send_mail(to, subject, context):
    _send_mail(to, subject, context)

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

from siteuser.users import views
from siteuser.settings import USING_SOCIAL_LOGIN

urlpatterns = patterns('',
    url(r'^account/login/$', views.SiteUserLoginView.as_view(), name='siteuser_login'),
    url(r'^account/register/$', views.SiteUserRegisterView.as_view(), name='siteuser_register'),

    # 丢失密码，重置第一步，填写注册邮件
    url(r'^account/resetpw/step1/$', views.SiteUserResetPwStepOneView.as_view(), name='siteuser_reset_step1'),
    url(r'^account/resetpw/step1/done/$', views.SiteUserResetPwStepOneDoneView.as_view(), name='siteuser_reset_step1_done'),

    # 第二布，重置密码。token是django.core.signing模块生成的带时间戳的加密字符串
    url(r'^account/resetpw/step2/done/$', views.SiteUserResetPwStepTwoDoneView.as_view(), name='siteuser_reset_step2_done'),
    url(r'^account/resetpw/step2/(?P<token>.+)/$', views.SiteUserResetPwStepTwoView.as_view(), name='siteuser_reset_step2'),

    # 登录用户修改密码
    url(r'^account/changepw/$', views.SiteUserChangePwView.as_view(), name='siteuser_changepw'),
    url(r'^account/changepw/done/$', views.SiteUserChangePwDoneView.as_view(), name='siteuser_changepw_done'),

    # 以上关于密码管理的url只能有本网站注册用户才能访问，第三方帐号不需要此功能


    url(r'^account/logout/$', views.logout, name='siteuser_logout'),
)


# 只有设置 USING_SOCIAL_LOGIN = True 的情况下，才会开启第三方登录功能
if USING_SOCIAL_LOGIN:
    urlpatterns += patterns('',
        url(r'^account/oauth/(?P<sitename>\w+)/?$', views.social_login_callback),
    )

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
import re
import json
import hashlib
from functools import wraps

from django.core import signing
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import loader, RequestContext
from django.views.generic import View


from siteuser.users.models import InnerUser, SiteUser, SocialUser
from siteuser.users.tasks import send_mail
from siteuser.settings import (
    USING_SOCIAL_LOGIN,
    MAX_EMAIL_LENGTH,
    MAX_USERNAME_LENGTH,
    SOCIALOAUTH_SITES,
    SOCIAL_LOGIN_DONE_REDIRECT_URL,
    SOCIAL_LOGIN_ERROR_REDIRECT_URL,
)
from siteuser.utils.load_user_define import user_defined_mixin

if USING_SOCIAL_LOGIN:
    from socialoauth import SocialSites, SocialAPIError, SocialSitesConfigError

# 注册，登录，退出等都通过 ajax 的方式进行

EMAIL_PATTERN = re.compile('^.+@.+\..+$')

class InnerAccoutError(Exception):
    pass

make_password = lambda passwd: hashlib.sha1(passwd).hexdigest()

def inner_account_ajax_guard(func):
    @wraps(func)
    def deco(self, request, *args, **kwargs):
        dump = lambda d: HttpResponse(json.dumps(d), mimetype='application/json')
        if request.siteuser:
            return dump({'ok': False, 'msg': '你已登录'})

        try:
            func(self, request, *args, **kwargs)
        except InnerAccoutError as e:
            return dump({'ok': False, 'msg': str(e)})

        return dump({'ok': True})
    return deco

def inner_account_http_guard(func):
    @wraps(func)
    def deco(self, request, *args, **kwargs):
        if request.siteuser:
            return HttpResponseRedirect('/')
        try:
            return func(self, request, *args, **kwargs)
        except InnerAccoutError as e:
            ctx = self.ctx_getter(request)
            ctx.update(getattr(self, 'ctx', {}))
            ctx.update({'error_msg': e})
            return render_to_response(
                self.tpl,
                ctx,
                context_instance=RequestContext(request)
            )
    return deco


class SiteUserMixIn(object):
    """用户可以自定义 SITEUSER_ACCOUNT_MIXIN 来覆盖这些配置"""
    login_template = 'siteuser/login.html'
    register_template = 'siteuser/register.html'
    reset_passwd_template = 'siteuser/reset_password.html'
    change_passwd_template = 'siteuser/change_password.html'

    # 用于生成重置密码链接的key,用于加密解密
    sign_key = 'siteuser_signkey'

    # 重置密码邮件的标题
    reset_passwd_email_title = u'重置密码'
    reset_passwd_email_template = 'siteuser/reset_password_email.html'

    # 多少小时后重置密码的链接失效
    reset_passwd_link_expired_in = 24

    # 在渲染这些模板的时候，如果你有额外的context需要传入，请重写这些方法
    def get_login_context(self, request):
        return {}

    def get_register_context(self, request):
        return {}

    def get_reset_passwd_context(self, request):
        return {}

    def get_change_passwd_context(self, request):
        return {}

    def get(self, request, *args, **kwargs):
        """使用此get方法的Class，必须制定这两个属性：
        self.tpl - 此view要渲染的模板名
        self.ctx_getter - 渲染模板是获取额外context的方法名
        """
        if request.siteuser:
            return HttpResponseRedirect('/')
        ctx = self.ctx_getter(request)
        ctx.update(getattr(self, 'ctx', {}))
        return render_to_response(
            self.tpl,
            ctx,
            context_instance=RequestContext(request)
        )

    def _reset_passwd_default_ctx(self):
        return {
            'step1': False,
            'step1_done': False,
            'step2': False,
            'step2_done': False,
            'expired': False,
        }

    def _normalize_referer(self, request):
        referer = request.META.get('HTTP_REFERER', '/')
        if referer.endswith('done/'):
            referer = '/'
        return referer



class SiteUserLoginView(user_defined_mixin(), SiteUserMixIn, View):
    """登录"""
    def __init__(self, **kwargs):
        self.tpl = self.login_template
        self.ctx_getter = self.get_login_context
        super(SiteUserLoginView, self).__init__(**kwargs)

    def get_login_context(self, request):
        """注册和登录都是通过ajax进行的，这里渲染表单模板的时候传入referer，
        当ajax post返回成功标识的时候，js就到此referer的页面。
        以此来完成注册/登录完毕后自动回到上个页面
        """
        ctx = super(SiteUserLoginView, self).get_login_context(request)
        ctx['referer'] = self._normalize_referer(request)
        return ctx

    @inner_account_ajax_guard
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', None)
        passwd = request.POST.get('passwd', None)

        if not email or not passwd:
            raise InnerAccoutError('请填写email和密码')

        try:
            user = InnerUser.objects.get(email=email)
        except InnerUser.DoesNotExist:
            raise InnerAccoutError('用户不存在')

        if user.passwd != hashlib.sha1(passwd).hexdigest():
            raise InnerAccoutError('密码错误')

        request.session['uid'] = user.user.id


class SiteUserRegisterView(user_defined_mixin(), SiteUserMixIn, View):
    """注册"""
    def __init__(self, **kwargs):
        self.tpl = self.register_template
        self.ctx_getter = self.get_register_context
        super(SiteUserRegisterView, self).__init__(**kwargs)

    def get_register_context(self, request):
        ctx = super(SiteUserRegisterView, self).get_register_context(request)
        ctx['referer'] = self._normalize_referer(request)
        return ctx

    @inner_account_ajax_guard
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', None)
        username = request.POST.get('username', None)
        passwd = request.POST.get('passwd', None)

        if not email or not username or not passwd:
            raise InnerAccoutError('请完整填写注册信息')

        if len(email) > MAX_EMAIL_LENGTH:
            raise InnerAccoutError('电子邮件地址太长')

        if EMAIL_PATTERN.search(email) is None:
            raise InnerAccoutError('电子邮件格式不正确')

        if InnerUser.objects.filter(email=email).exists():
            raise InnerAccoutError('此电子邮件已被占用')

        if len(username) > MAX_USERNAME_LENGTH:
            raise InnerAccoutError('用户名太长，不要超过{0}个字符'.format(MAX_USERNAME_LENGTH))

        if SiteUser.objects.filter(username=username).exists():
            raise InnerAccoutError('用户名已存在')

        passwd = make_password(passwd)
        user = InnerUser.objects.create(email=email, passwd=passwd, username=username)
        request.session['uid'] = user.user.id


class SiteUserResetPwStepOneView(user_defined_mixin(), SiteUserMixIn, View):
    """丢失密码重置第一步，填写注册时的电子邮件"""
    def __init__(self, **kwargs):
        self.tpl = self.reset_passwd_template
        self.ctx_getter = self.get_reset_passwd_context
        self.ctx = self._reset_passwd_default_ctx()
        self.ctx['step1'] = True
        super(SiteUserResetPwStepOneView, self).__init__(**kwargs)

    @inner_account_http_guard
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', None)
        if not email:
            raise InnerAccoutError('请填写电子邮件')
        if EMAIL_PATTERN.search(email) is None:
            raise InnerAccoutError('电子邮件格式不正确')
        try:
            user = InnerUser.objects.get(email=email)
        except InnerUser.DoesNotExist:
            raise InnerAccoutError('请填写您注册时的电子邮件地址')

        token = signing.dumps(user.user.id, key=self.sign_key)
        link = reverse('siteuser_reset_step2', kwargs={'token': token})
        link = request.build_absolute_uri(link)
        context = {
            'hour': self.reset_passwd_link_expired_in,
            'link': link
        }
        body = loader.render_to_string(self.reset_passwd_email_template, context)
        # 异步发送邮件
        body = unicode(body)
        send_mail.delay(email, self.reset_passwd_email_title, body)
        return HttpResponseRedirect(reverse('siteuser_reset_step1_done'))


class SiteUserResetPwStepOneDoneView(user_defined_mixin(), SiteUserMixIn, View):
    """发送重置邮件完成"""
    def __init__(self, **kwargs):
        self.tpl = self.reset_passwd_template
        self.ctx_getter = self.get_reset_passwd_context
        self.ctx = self._reset_passwd_default_ctx()
        self.ctx['step1_done'] = True
        super(SiteUserResetPwStepOneDoneView, self).__init__(**kwargs)


class SiteUserResetPwStepTwoView(user_defined_mixin(), SiteUserMixIn, View):
    """丢失密码重置第二步，填写新密码"""
    def __init__(self, **kwargs):
        self.tpl = self.reset_passwd_template
        self.ctx_getter = self.get_reset_passwd_context
        self.ctx = self._reset_passwd_default_ctx()
        self.ctx['step2'] = True
        super(SiteUserResetPwStepTwoView, self).__init__(**kwargs)

    def get(self, request, *args, **kwargs):
        token = kwargs['token']
        try:
            self.uid = signing.loads(token, key=self.sign_key, max_age=self.reset_passwd_link_expired_in*3600)
        except signing.SignatureExpired:
            # 通过context来控制到底显示表单还是过期信息
            self.ctx['expired'] = True
        except signing.BadSignature:
            raise Http404
        return super(SiteUserResetPwStepTwoView, self).get(request, *args, **kwargs)


    @inner_account_http_guard
    def post(self, request, *args, **kwargs):
        password = request.POST.get('password', None)
        password1 = request.POST.get('password1', None)
        if not password or not password1:
            raise InnerAccoutError('请填写密码')
        if password != password1:
            raise InnerAccoutError('两次密码不一致')
        uid = signing.loads(kwargs['token'], key=self.sign_key)
        password = make_password(password)
        InnerUser.objects.filter(user_id=uid).update(passwd=password)
        return HttpResponseRedirect(reverse('siteuser_reset_step2_done'))


class SiteUserResetPwStepTwoDoneView(user_defined_mixin(), SiteUserMixIn, View):
    """重置完成"""
    def __init__(self, **kwargs):
        self.tpl = self.reset_passwd_template
        self.ctx_getter = self.get_reset_passwd_context
        self.ctx = self._reset_passwd_default_ctx()
        self.ctx['step2_done'] = True
        super(SiteUserResetPwStepTwoDoneView, self).__init__(**kwargs)


class SiteUserChangePwView(user_defined_mixin(), SiteUserMixIn, View):
    """已登录用户修改密码"""
    def render_to_response(self, request, **kwargs):
        ctx = self.get_change_passwd_context(request)
        ctx['done'] = False
        ctx.update(kwargs)
        return render_to_response(
            self.change_passwd_template,
            ctx,
            context_instance=RequestContext(request)
        )

    def get(self, request, *args, **kwargs):
        if not request.siteuser:
            return HttpResponseRedirect('/')
        if not request.siteuser.is_active or request.siteuser.is_social:
            return HttpResponseRedirect('/')
        return self.render_to_response(request)

    def post(self, request, *args, **kwargs):
        if not request.siteuser:
            return HttpResponseRedirect('/')
        if not request.siteuser.is_active or request.siteuser.is_social:
            return HttpResponseRedirect('/')

        password = request.POST.get('password', None)
        password1 = request.POST.get('password1', None)
        if not password or not password1:
            return self.render_to_response(request, error_msg='请填写新密码')
        if password != password1:
            return self.render_to_response(request, error_msg='两次密码不一致')
        password = make_password(password)
        if request.siteuser.inner_user.passwd == password:
            return self.render_to_response(request, error_msg='不能与旧密码相同')
        InnerUser.objects.filter(user_id=request.siteuser.id).update(passwd=password)
        # 清除登录状态
        try:
            del request.session['uid']
        except:
            pass

        return HttpResponseRedirect(reverse('siteuser_changepw_done'))


class SiteUserChangePwDoneView(user_defined_mixin(), SiteUserMixIn, View):
    """已登录用户修改密码成功"""
    def get(self, request, *args, **kwargs):
        if request.siteuser:
            return HttpResponseRedirect('/')
        ctx = self.get_change_passwd_context(request)
        ctx['done'] = True
        return render_to_response(
            self.change_passwd_template,
            ctx,
            context_instance=RequestContext(request)
        )


def logout(request):
    """登出，ajax请求，然后刷新页面"""
    try:
        del request.session['uid']
    except:
        pass

    return HttpResponse('', mimetype='application/json')



def social_login_callback(request, sitename):
    """第三方帐号OAuth认证登录，只有设置了USING_SOCIAL_LOGIN=True才会使用到此功能"""
    code = request.GET.get('code', None)
    if not code:
        return HttpResponseRedirect(SOCIAL_LOGIN_ERROR_REDIRECT_URL)

    socialsites = SocialSites(SOCIALOAUTH_SITES)
    try:
        site = socialsites.get_site_object_by_name(sitename)
        site.get_access_token(code)
    except(SocialSitesConfigError, SocialAPIError):
        return HttpResponseRedirect(SOCIAL_LOGIN_ERROR_REDIRECT_URL)

    # 首先根据site_name和site uid查找此用户是否已经在自身网站认证，
    # 如果查不到，表示这个用户第一次认证登陆，创建新用户记录
    # 如果查到，就跟新其用户名和头像
    try:
        user = SocialUser.objects.get(site_uid=site.uid, site_name=site.site_name)
        SiteUser.objects.filter(id=user.user.id).update(username=site.name, avatar_url=site.avatar)
    except SocialUser.DoesNotExist:
        user = SocialUser.objects.create(
            site_uid=site.uid,
            site_name=site.site_name,
            username=site.name,
            avatar_url=site.avatar
        )

    # set uid in session, then this user will be auto login
    request.session['uid'] = user.user.id
    return HttpResponseRedirect(SOCIAL_LOGIN_DONE_REDIRECT_URL)

########NEW FILE########
__FILENAME__ = load_user_define
# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

class UserNotDefined(object):pass

def user_defined_mixin():
    mixin = getattr(settings, 'SITEUSER_ACCOUNT_MIXIN', UserNotDefined)
    if mixin is UserNotDefined:
        raise ImproperlyConfigured("No Settings For SITEUSER_ACCOUNT_MIXIN")
    if mixin is object:
        raise ImproperlyConfigured("Invalid SITEUSER_ACCOUNT_MIXIN")
    if isinstance(mixin, type):
        return mixin

    _module, _class = mixin.rsplit('.', 1)
    m = __import__(_module, fromlist=['.'])
    return getattr(m, _class)
########NEW FILE########
