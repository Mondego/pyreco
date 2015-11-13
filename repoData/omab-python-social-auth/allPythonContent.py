__FILENAME__ = conf
# -*- coding: utf-8 -*-
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'sphinx.ext.todo', 'sphinx.ext.viewcode']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'Python Social Auth'
copyright = u'2012, Matías Aguirre'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'nature'
html_static_path = []
htmlhelp_basename = 'PythonSocialAuthdoc'
latex_documents = [
  ('index', 'PythonSocialAuth.tex', u'Python Social Auth Documentation',
   u'Matías Aguirre', 'manual'),
]
man_pages = [
    ('index', 'pythonsocialauth', u'Python Social Auth Documentation',
     [u'Matías Aguirre'], 1)
]
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = saplugin
# -*- coding: utf-8 -*-
from cherrypy.process import plugins

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


class SAEnginePlugin(plugins.SimplePlugin):
    def __init__(self, bus, connection_string=None):
        self.sa_engine = None
        self.connection_string = connection_string
        self.session = scoped_session(sessionmaker(autoflush=True,
                                                   autocommit=False))
        super(SAEnginePlugin, self).__init__(bus)

    def start(self):
        self.sa_engine = create_engine(self.connection_string, echo=False)
        self.bus.subscribe('bind-session', self.bind)
        self.bus.subscribe('commit-session', self.commit)

    def stop(self):
        self.bus.unsubscribe('bind-session', self.bind)
        self.bus.unsubscribe('commit-session', self.commit)
        if self.sa_engine:
            self.sa_engine.dispose()
            self.sa_engine = None

    def bind(self):
        self.session.configure(bind=self.sa_engine)
        return self.session

    def commit(self):
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        finally:
            self.session.remove()

########NEW FILE########
__FILENAME__ = satool
# -*- coding: utf-8 -*-
import cherrypy


class SATool(cherrypy.Tool):
    def __init__(self):
        super(SATool, self).__init__('before_handler', self.bind_session,
                                     priority=20)

    def _setup(self):
        super(SATool, self)._setup()
        cherrypy.request.hooks.attach('on_end_resource',
                                      self.commit_transaction,
                                      priority=80)

    def bind_session(self):
        session = cherrypy.engine.publish('bind-session').pop()
        cherrypy.request.db = session

    def commit_transaction(self):
        if not hasattr(cherrypy.request, 'db'):
            return
        cherrypy.request.db = None
        cherrypy.engine.publish('commit-session')

########NEW FILE########
__FILENAME__ = user
from sqlalchemy import Column, Integer, String, Boolean

from db import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(200))
    password = Column(String(200), default='')
    name = Column(String(100))
    email = Column(String(200))
    active = Column(Boolean, default=True)

    def is_active(self):
        return self.active

########NEW FILE########
__FILENAME__ = syncbd
import sys

sys.path.append('../..')

from sqlalchemy import create_engine

import cherrypy


cherrypy.config.update({
    'SOCIAL_AUTH_USER_MODEL': 'db.user.User',
})


from social.apps.cherrypy_app.models import SocialBase
from db import Base
from db.user import User



if __name__ == '__main__':
    engine = create_engine('sqlite:///test.db')
    Base.metadata.create_all(engine)
    SocialBase.metadata.create_all(engine)

########NEW FILE########
__FILENAME__ = mail
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse


def send_validation(strategy, code):
    url = reverse('social:complete', args=(strategy.backend.name,)) + \
            '?verification_code=' + code.code
    send_mail('Validate your account',
              'Validate your account {0}'.format(url),
              settings.EMAIL_FROM,
              [code.email],
              fail_silently=False)

########NEW FILE########
__FILENAME__ = models
# Define a custom User class to work with django-social-auth
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    pass

########NEW FILE########
__FILENAME__ = pipeline
from django.shortcuts import redirect

from social.pipeline.partial import partial


@partial
def require_email(strategy, details, user=None, is_new=False, *args, **kwargs):
    if kwargs.get('ajax') or user and user.email:
        return
    elif is_new and not details.get('email'):
        if strategy.session_get('saved_email'):
            details['email'] = strategy.session_pop('saved_email')
        else:
            return redirect('require_email')

########NEW FILE########
__FILENAME__ = views
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout, login

from social.backends.oauth import BaseOAuth1, BaseOAuth2
from social.backends.google import GooglePlusAuth
from social.apps.django_app.utils import strategy


def logout(request):
    """Logs out user"""
    auth_logout(request)
    return render_to_response('home.html', {}, RequestContext(request))


def home(request):
    """Home view, displays login mechanism"""
    if request.user.is_authenticated():
        return redirect('done')
    return render_to_response('home.html', {
        'plus_id': getattr(settings, 'SOCIAL_AUTH_GOOGLE_PLUS_KEY', None)
    }, RequestContext(request))


@login_required
def done(request):
    """Login complete view, displays user data"""
    scope = ' '.join(GooglePlusAuth.DEFAULT_SCOPE)
    return render_to_response('done.html', {
        'user': request.user,
        'plus_id': getattr(settings, 'SOCIAL_AUTH_GOOGLE_PLUS_KEY', None),
        'plus_scope': scope
    }, RequestContext(request))


def signup_email(request):
    return render_to_response('email_signup.html', {}, RequestContext(request))


def validation_sent(request):
    return render_to_response('validation_sent.html', {
        'email': request.session.get('email_validation_address')
    }, RequestContext(request))


def require_email(request):
    if request.method == 'POST':
        request.session['saved_email'] = request.POST.get('email')
        backend = request.session['partial_pipeline']['backend']
        return redirect('social:complete', backend=backend)
    return render_to_response('email.html', RequestContext(request))


@strategy('social:complete')
def ajax_auth(request, backend):
    backend = request.strategy.backend
    if isinstance(backend, BaseOAuth1):
        token = {
            'oauth_token': request.REQUEST.get('access_token'),
            'oauth_token_secret': request.REQUEST.get('access_token_secret'),
        }
    elif isinstance(backend, BaseOAuth2):
        token = request.REQUEST.get('access_token')
    else:
        raise HttpResponseBadRequest('Wrong backend type')
    user = request.strategy.backend.do_auth(token, ajax=True)
    login(request, user)
    data = {'id': user.id, 'username': user.username}
    return HttpResponse(json.dumps(data), mimetype='application/json')

########NEW FILE########
__FILENAME__ = settings
import sys
from os.path import abspath, dirname, join


sys.path.insert(0, '../..')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ROOT_PATH = abspath(dirname(__file__))

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db'
    }
}

TIME_ZONE = 'America/Montevideo'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
MEDIA_ROOT = ''
MEDIA_URL = ''

STATIC_ROOT = ''
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = '#$5btppqih8=%ae^#&amp;7en#kyi!vh%he9rg=ed#hm6fnw9^=umc'

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
)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    join(ROOT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social.apps.django_app.default',
    'example.app',
)

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

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
    'social.apps.django_app.context_processors.backends',
)

AUTHENTICATION_BACKENDS = (
    'social.backends.amazon.AmazonOAuth2',
    'social.backends.angel.AngelOAuth2',
    'social.backends.aol.AOLOpenId',
    'social.backends.appsfuel.AppsfuelOAuth2',
    'social.backends.beats.BeatsOAuth2',
    'social.backends.behance.BehanceOAuth2',
    'social.backends.belgiumeid.BelgiumEIDOpenId',
    'social.backends.bitbucket.BitbucketOAuth',
    'social.backends.box.BoxOAuth2',
    'social.backends.clef.ClefOAuth2',
    'social.backends.coinbase.CoinbaseOAuth2',
    'social.backends.dailymotion.DailymotionOAuth2',
    'social.backends.disqus.DisqusOAuth2',
    'social.backends.douban.DoubanOAuth2',
    'social.backends.dropbox.DropboxOAuth',
    'social.backends.evernote.EvernoteSandboxOAuth',
    'social.backends.facebook.FacebookAppOAuth2',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.fedora.FedoraOpenId',
    'social.backends.fitbit.FitbitOAuth',
    'social.backends.flickr.FlickrOAuth',
    'social.backends.foursquare.FoursquareOAuth2',
    'social.backends.github.GithubOAuth2',
    'social.backends.google.GoogleOAuth',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOpenId',
    'social.backends.google.GooglePlusAuth',
    'social.backends.instagram.InstagramOAuth2',
    'social.backends.jawbone.JawboneOAuth2',
    'social.backends.linkedin.LinkedinOAuth',
    'social.backends.linkedin.LinkedinOAuth2',
    'social.backends.live.LiveOAuth2',
    'social.backends.livejournal.LiveJournalOpenId',
    'social.backends.mailru.MailruOAuth2',
    'social.backends.mendeley.MendeleyOAuth',
    'social.backends.mendeley.MendeleyOAuth2',
    'social.backends.mixcloud.MixcloudOAuth2',
    'social.backends.odnoklassniki.OdnoklassnikiOAuth2',
    'social.backends.open_id.OpenIdAuth',
    'social.backends.openstreetmap.OpenStreetMapOAuth',
    'social.backends.orkut.OrkutOAuth',
    'social.backends.persona.PersonaAuth',
    'social.backends.podio.PodioOAuth2',
    'social.backends.rdio.RdioOAuth1',
    'social.backends.rdio.RdioOAuth2',
    'social.backends.readability.ReadabilityOAuth',
    'social.backends.reddit.RedditOAuth2',
    'social.backends.runkeeper.RunKeeperOAuth2',
    'social.backends.skyrock.SkyrockOAuth',
    'social.backends.soundcloud.SoundcloudOAuth2',
    'social.backends.spotify.SpotifyOAuth2',
    'social.backends.stackoverflow.StackoverflowOAuth2',
    'social.backends.steam.SteamOpenId',
    'social.backends.stocktwits.StocktwitsOAuth2',
    'social.backends.stripe.StripeOAuth2',
    'social.backends.suse.OpenSUSEOpenId',
    'social.backends.thisismyjam.ThisIsMyJamOAuth1',
    'social.backends.trello.TrelloOAuth',
    'social.backends.tripit.TripItOAuth',
    'social.backends.tumblr.TumblrOAuth',
    'social.backends.twilio.TwilioAuth',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.vk.VKOAuth2',
    'social.backends.weibo.WeiboOAuth2',
    'social.backends.xing.XingOAuth',
    'social.backends.yahoo.YahooOAuth',
    'social.backends.yahoo.YahooOpenId',
    'social.backends.yammer.YammerOAuth2',
    'social.backends.yandex.YandexOAuth2',
    'social.backends.vimeo.VimeoOAuth1',
    'social.backends.lastfm.LastFmAuth',
    'social.backends.email.EmailAuth',
    'social.backends.username.UsernameAuth',
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_USER_MODEL = 'app.CustomUser'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/done/'
URL_PATH = ''
SOCIAL_AUTH_STRATEGY = 'social.strategies.django_strategy.DjangoStrategy'
SOCIAL_AUTH_STORAGE = 'social.apps.django_app.default.models.DjangoStorage'
SOCIAL_AUTH_GOOGLE_OAUTH_SCOPE = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/userinfo.profile'
]
# SOCIAL_AUTH_EMAIL_FORM_URL = '/signup-email'
SOCIAL_AUTH_EMAIL_FORM_HTML = 'email_signup.html'
SOCIAL_AUTH_EMAIL_VALIDATION_FUNCTION = 'example.app.mail.send_validation'
SOCIAL_AUTH_EMAIL_VALIDATION_URL = '/email-sent/'
# SOCIAL_AUTH_USERNAME_FORM_URL = '/signup-username'
SOCIAL_AUTH_USERNAME_FORM_HTML = 'username_signup.html'

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'example.app.pipeline.require_email',
    'social.pipeline.mail.mail_validation',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details'
)

# SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['first_name', 'last_name', 'email',
#                                         'username']

try:
    from example.local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'example.app.views.home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^signup-email/', 'example.app.views.signup_email'),
    url(r'^email-sent/', 'example.app.views.validation_sent'),
    url(r'^login/$', 'example.app.views.home'),
    url(r'^logout/$', 'example.app.views.logout'),
    url(r'^done/$', 'example.app.views.done', name='done'),
    url(r'^ajax-auth/(?P<backend>[^/]+)/$', 'example.app.views.ajax_auth',
        name='ajax-auth'),
    url(r'^email/$', 'example.app.views.require_email', name='require_email'),
    url(r'', include('social.apps.django_app.urls', namespace='social'))
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for dj project.

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

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'example.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = mail
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse


def send_validation(strategy, code):
    url = reverse('social:complete', args=(strategy.backend_name,)) \
            + '?verification_code=' + code.code
    send_mail('Validate your account',
              'Validate your account {0}'.format(url),
              settings.EMAIL_FROM,
              [code.email],
              fail_silently=False)

########NEW FILE########
__FILENAME__ = models
from mongoengine.fields import ListField
from mongoengine.django.auth import User


class User(User):
    """Extend Mongo Engine User model"""
    foo = ListField(default=[])

########NEW FILE########
__FILENAME__ = pipeline
from django.shortcuts import redirect

from social.pipeline.partial import partial


@partial
def require_email(strategy, details, user=None, is_new=False, *args, **kwargs):
    if user and user.email:
        return
    elif is_new and not details.get('email'):
        if strategy.session_get('saved_email'):
            details['email'] = strategy.session_pop('saved_email')
        else:
            return redirect('require_email')

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect


def home(request):
    """Home view, displays login mechanism"""
    if request.user.is_authenticated():
        return redirect('done')
    return render_to_response('home.html', {}, RequestContext(request))


@login_required
def done(request):
    """Login complete view, displays user data"""
    return render_to_response('done.html', {'user': request.user},
                              RequestContext(request))


def signup_email(request):
    return render_to_response('email_signup.html', {}, RequestContext(request))


def validation_sent(request):
    return render_to_response('validation_sent.html', {
        'email': request.session.get('email_validation_address')
    }, RequestContext(request))


def require_email(request):
    if request.method == 'POST':
        request.session['saved_email'] = request.POST.get('email')
        backend = request.session['partial_pipeline']['backend']
        return redirect('social:complete', backend=backend)
    return render_to_response('email.html', RequestContext(request))

########NEW FILE########
__FILENAME__ = settings
import sys
from os.path import abspath, dirname, join

import mongoengine


sys.path.insert(0, '../..')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ROOT_PATH = abspath(dirname(__file__))

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db'
    }
}

TIME_ZONE = 'America/Montevideo'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
MEDIA_ROOT = ''
MEDIA_URL = ''

STATIC_ROOT = ''
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = '#$5btppqih8=%ae^#&amp;7en#kyi!vh%he9rg=ed#hm6fnw9^=umc'

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
)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    join(ROOT_PATH, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mongoengine.django.mongo_auth',
    'social.apps.django_app.me',
    'example.app',
)

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

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
    'social.apps.django_app.context_processors.backends',
)

SESSION_ENGINE = 'mongoengine.django.sessions'
mongoengine.connect('psa', host='mongodb://localhost/psa')
MONGOENGINE_USER_DOCUMENT = 'example.app.models.User'
SOCIAL_AUTH_USER_MODEL = 'example.app.models.User'


AUTHENTICATION_BACKENDS = (
    'social.backends.open_id.OpenIdAuth',
    'social.backends.google.GoogleOpenId',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.yahoo.YahooOpenId',
    'social.backends.stripe.StripeOAuth2',
    'social.backends.persona.PersonaAuth',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.facebook.FacebookAppOAuth2',
    'social.backends.yahoo.YahooOAuth',
    'social.backends.angel.AngelOAuth2',
    'social.backends.behance.BehanceOAuth2',
    'social.backends.bitbucket.BitbucketOAuth',
    'social.backends.box.BoxOAuth2',
    'social.backends.linkedin.LinkedinOAuth',
    'social.backends.linkedin.LinkedinOAuth2',
    'social.backends.github.GithubOAuth2',
    'social.backends.foursquare.FoursquareOAuth2',
    'social.backends.instagram.InstagramOAuth2',
    'social.backends.live.LiveOAuth2',
    'social.backends.vk.VKOAuth2',
    'social.backends.dailymotion.DailymotionOAuth2',
    'social.backends.disqus.DisqusOAuth2',
    'social.backends.dropbox.DropboxOAuth',
    'social.backends.evernote.EvernoteSandboxOAuth',
    'social.backends.fitbit.FitbitOAuth',
    'social.backends.flickr.FlickrOAuth',
    'social.backends.livejournal.LiveJournalOpenId',
    'social.backends.soundcloud.SoundcloudOAuth2',
    'social.backends.thisismyjam.ThisIsMyJamOAuth1',
    'social.backends.stocktwits.StocktwitsOAuth2',
    'social.backends.tripit.TripItOAuth',
    'social.backends.twilio.TwilioAuth',
    'social.backends.clef.ClefOAuth2',
    'social.backends.xing.XingOAuth',
    'social.backends.yandex.YandexOAuth2',
    'social.backends.douban.DoubanOAuth2',
    'social.backends.mixcloud.MixcloudOAuth2',
    'social.backends.rdio.RdioOAuth1',
    'social.backends.rdio.RdioOAuth2',
    'social.backends.yammer.YammerOAuth2',
    'social.backends.stackoverflow.StackoverflowOAuth2',
    'social.backends.readability.ReadabilityOAuth',
    'social.backends.skyrock.SkyrockOAuth',
    'social.backends.tumblr.TumblrOAuth',
    'social.backends.reddit.RedditOAuth2',
    'social.backends.steam.SteamOpenId',
    'social.backends.podio.PodioOAuth2',
    'social.backends.amazon.AmazonOAuth2',
    'social.backends.email.EmailAuth',
    'social.backends.username.UsernameAuth',
    'django.contrib.auth.backends.ModelBackend',
)

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/done/'
URL_PATH = ''
SOCIAL_AUTH_STRATEGY = 'social.strategies.django_strategy.DjangoStrategy'
SOCIAL_AUTH_STORAGE = 'social.apps.django_app.me.models.DjangoStorage'
SOCIAL_AUTH_GOOGLE_OAUTH_SCOPE = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/userinfo.profile'
]
# SOCIAL_AUTH_EMAIL_FORM_URL = '/signup-email'
SOCIAL_AUTH_EMAIL_FORM_HTML = 'email_signup.html'
SOCIAL_AUTH_EMAIL_VALIDATION_FUNCTION = 'example.app.mail.send_validation'
SOCIAL_AUTH_EMAIL_VALIDATION_URL = '/email-sent/'
# SOCIAL_AUTH_USERNAME_FORM_URL = '/signup-username'
SOCIAL_AUTH_USERNAME_FORM_HTML = 'username_signup.html'

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'example.app.pipeline.require_email',
    'social.pipeline.mail.mail_validation',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details'
)

try:
    from example.local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'example.app.views.home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^signup-email/', 'example.app.views.signup_email'),
    url(r'^email-sent/', 'example.app.views.validation_sent'),
    url(r'^login/$', 'example.app.views.home'),
    url(r'^done/$', 'example.app.views.done', name='done'),
    url(r'^email/$', 'example.app.views.require_email', name='require_email'),
    url(r'', include('social.apps.django_app.urls', namespace='social'))
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

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'example.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys

from flask.ext.script import Server, Manager, Shell

sys.path.append('..')

from flask_example import app, db


manager = Manager(app)
manager.add_command('runserver', Server())
manager.add_command('shell', Shell(make_context=lambda: {
    'app': app,
    'db': db
}))


@manager.command
def syncdb():
    from flask_example.models import user
    from social.apps.flask_app import models
    db.drop_all()
    db.create_all()

if __name__ == '__main__':
    manager.run()

########NEW FILE########
__FILENAME__ = user
from flask.ext.login import UserMixin

from flask_example import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200))
    password = db.Column(db.String(200), default='')
    name = db.Column(db.String(100))
    email = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=True)

    def is_active(self):
        return self.active

########NEW FILE########
__FILENAME__ = main
from flask import render_template, redirect
from flask.ext.login import login_required, logout_user

from flask_example import app


@app.route('/')
def main():
    return render_template('home.html')


@login_required
@app.route('/done/')
def done():
    return render_template('done.html')


@app.route('/logout')
def logout():
    """Logout view"""
    logout_user()
    return redirect('/')

########NEW FILE########
__FILENAME__ = settings
from flask_example import app


app.debug = True

SECRET_KEY = 'random-secret-key'
SESSION_COOKIE_NAME = 'psa_session'
DEBUG = False
from os.path import dirname, abspath
SQLALCHEMY_DATABASE_URI = 'sqlite:////%s/test.db' % dirname(abspath(__file__))

DEBUG_TB_INTERCEPT_REDIRECTS = False
SESSION_PROTECTION = 'strong'

SOCIAL_AUTH_LOGIN_URL = '/'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/done/'
SOCIAL_AUTH_USER_MODEL = 'flask_example.models.user.User'
SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    'social.backends.open_id.OpenIdAuth',
    'social.backends.google.GoogleOpenId',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.yahoo.YahooOpenId',
    'social.backends.stripe.StripeOAuth2',
    'social.backends.persona.PersonaAuth',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.facebook.FacebookAppOAuth2',
    'social.backends.yahoo.YahooOAuth',
    'social.backends.angel.AngelOAuth2',
    'social.backends.behance.BehanceOAuth2',
    'social.backends.bitbucket.BitbucketOAuth',
    'social.backends.box.BoxOAuth2',
    'social.backends.linkedin.LinkedinOAuth',
    'social.backends.github.GithubOAuth2',
    'social.backends.foursquare.FoursquareOAuth2',
    'social.backends.instagram.InstagramOAuth2',
    'social.backends.live.LiveOAuth2',
    'social.backends.vk.VKOAuth2',
    'social.backends.dailymotion.DailymotionOAuth2',
    'social.backends.disqus.DisqusOAuth2',
    'social.backends.dropbox.DropboxOAuth',
    'social.backends.evernote.EvernoteSandboxOAuth',
    'social.backends.fitbit.FitbitOAuth',
    'social.backends.flickr.FlickrOAuth',
    'social.backends.livejournal.LiveJournalOpenId',
    'social.backends.soundcloud.SoundcloudOAuth2',
    'social.backends.thisismyjam.ThisIsMyJamOAuth1',
    'social.backends.stocktwits.StocktwitsOAuth2',
    'social.backends.tripit.TripItOAuth',
    'social.backends.clef.ClefOAuth2',
    'social.backends.twilio.TwilioAuth',
    'social.backends.xing.XingOAuth',
    'social.backends.yandex.YandexOAuth2',
    'social.backends.podio.PodioOAuth2',
    'social.backends.reddit.RedditOAuth2',
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys

from flask.ext.script import Server, Manager, Shell

sys.path.append('..')

from flask_me_example import app, db


manager = Manager(app)
manager.add_command('runserver', Server())
manager.add_command('shell', Shell(make_context=lambda: {
    'app': app,
    'db': db
}))


if __name__ == '__main__':
    manager.run()

########NEW FILE########
__FILENAME__ = user
from mongoengine import StringField, EmailField, BooleanField

from flask.ext.login import UserMixin

from flask_me_example import db


class User(db.Document, UserMixin):
    username = StringField(max_length=200)
    password = StringField(max_length=200, default='')
    name = StringField(max_length=100)
    email = EmailField()
    active = BooleanField(default=True)

    def is_active(self):
        return self.active

########NEW FILE########
__FILENAME__ = main
from flask import render_template, redirect
from flask.ext.login import login_required, logout_user

from flask_me_example import app


@app.route('/')
def main():
    return render_template('home.html')


@login_required
@app.route('/done/')
def done():
    return render_template('done.html')


@app.route('/logout')
def logout():
    """Logout view"""
    logout_user()
    return redirect('/')

########NEW FILE########
__FILENAME__ = settings
from flask_me_example import app


app.debug = True

SECRET_KEY = 'random-secret-key'
SESSION_COOKIE_NAME = 'psa_session'
DEBUG = False

MONGODB_SETTINGS = {'DB': 'psa_db'}

DEBUG_TB_INTERCEPT_REDIRECTS = False
SESSION_PROTECTION = 'strong'

SOCIAL_AUTH_LOGIN_URL = '/'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/done/'
SOCIAL_AUTH_USER_MODEL = 'flask_me_example.models.user.User'
SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    'social.backends.open_id.OpenIdAuth',
    'social.backends.google.GoogleOpenId',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.yahoo.YahooOpenId',
    'social.backends.stripe.StripeOAuth2',
    'social.backends.persona.PersonaAuth',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.facebook.FacebookAppOAuth2',
    'social.backends.yahoo.YahooOAuth',
    'social.backends.angel.AngelOAuth2',
    'social.backends.behance.BehanceOAuth2',
    'social.backends.bitbucket.BitbucketOAuth',
    'social.backends.box.BoxOAuth2',
    'social.backends.linkedin.LinkedinOAuth',
    'social.backends.github.GithubOAuth2',
    'social.backends.foursquare.FoursquareOAuth2',
    'social.backends.instagram.InstagramOAuth2',
    'social.backends.live.LiveOAuth2',
    'social.backends.vk.VKOAuth2',
    'social.backends.dailymotion.DailymotionOAuth2',
    'social.backends.disqus.DisqusOAuth2',
    'social.backends.dropbox.DropboxOAuth',
    'social.backends.evernote.EvernoteSandboxOAuth',
    'social.backends.fitbit.FitbitOAuth',
    'social.backends.flickr.FlickrOAuth',
    'social.backends.livejournal.LiveJournalOpenId',
    'social.backends.soundcloud.SoundcloudOAuth2',
    'social.backends.lastfm.LastFmAuth',
    'social.backends.thisismyjam.ThisIsMyJamOAuth1',
    'social.backends.stocktwits.StocktwitsOAuth2',
    'social.backends.tripit.TripItOAuth',
    'social.backends.clef.ClefOAuth2',
    'social.backends.twilio.TwilioAuth',
    'social.backends.xing.XingOAuth',
    'social.backends.yandex.YandexOAuth2',
    'social.backends.podio.PodioOAuth2',
    'social.backends.reddit.RedditOAuth2',
)

########NEW FILE########
__FILENAME__ = auth
from pyramid.events import subscriber, BeforeRender

from social.apps.pyramid_app.utils import backends

from example.models import DBSession, User


def login_user(strategy, user):
    strategy.request.session['user_id'] = user.id


def login_required(request):
    return getattr(request, 'user', None) is not None


def get_user(request):
    user_id = request.session.get('user_id')
    if user_id:
        user = DBSession.query(User)\
                        .filter(User.id == user_id)\
                        .first()
    else:
        user = None
    return user


@subscriber(BeforeRender)
def add_social(event):
    request = event['request']
    event['social'] = backends(request, request.user)

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(200))
    email = Column(String(200))
    password = Column(String(200), default='')
    name = Column(String(100))
    email = Column(String(200))
    active = Column(Boolean, default=True)

########NEW FILE########
__FILENAME__ = initializedb
import os
import sys

sys.path.append('../..')

from sqlalchemy import engine_from_config

from pyramid.paster import get_appsettings, setup_logging
from pyramid.scripts.common import parse_vars

from social.apps.pyramid_app.models import init_social

from example.models import DBSession, Base
from example.settings import SOCIAL_AUTH_SETTINGS


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    init_social(SOCIAL_AUTH_SETTINGS, Base, DBSession)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
SOCIAL_AUTH_SETTINGS = {
    'SOCIAL_AUTH_LOGIN_URL': '/',
    'SOCIAL_AUTH_LOGIN_REDIRECT_URL': '/done',
    'SOCIAL_AUTH_USER_MODEL': 'example.models.User',
    'SOCIAL_AUTH_LOGIN_FUNCTION': 'example.auth.login_user',
    'SOCIAL_AUTH_LOGGEDIN_FUNCTION': 'example.auth.login_required',
    'SOCIAL_AUTH_AUTHENTICATION_BACKENDS': (
        'social.backends.twitter.TwitterOAuth',
        'social.backends.open_id.OpenIdAuth',
        'social.backends.google.GoogleOpenId',
        'social.backends.google.GoogleOAuth2',
        'social.backends.google.GoogleOAuth',
        'social.backends.yahoo.YahooOpenId',
        'social.backends.stripe.StripeOAuth2',
        'social.backends.persona.PersonaAuth',
        'social.backends.facebook.FacebookOAuth2',
        'social.backends.facebook.FacebookAppOAuth2',
        'social.backends.yahoo.YahooOAuth',
        'social.backends.angel.AngelOAuth2',
        'social.backends.behance.BehanceOAuth2',
        'social.backends.bitbucket.BitbucketOAuth',
        'social.backends.box.BoxOAuth2',
        'social.backends.linkedin.LinkedinOAuth',
        'social.backends.github.GithubOAuth2',
        'social.backends.foursquare.FoursquareOAuth2',
        'social.backends.instagram.InstagramOAuth2',
        'social.backends.live.LiveOAuth2',
        'social.backends.vk.VKOAuth2',
        'social.backends.dailymotion.DailymotionOAuth2',
        'social.backends.disqus.DisqusOAuth2',
        'social.backends.dropbox.DropboxOAuth',
        'social.backends.evernote.EvernoteSandboxOAuth',
        'social.backends.fitbit.FitbitOAuth',
        'social.backends.flickr.FlickrOAuth',
        'social.backends.livejournal.LiveJournalOpenId',
        'social.backends.soundcloud.SoundcloudOAuth2',
        'social.backends.thisismyjam.ThisIsMyJamOAuth1',
        'social.backends.stocktwits.StocktwitsOAuth2',
        'social.backends.tripit.TripItOAuth',
        'social.backends.twilio.TwilioAuth',
        'social.backends.clef.ClefOAuth2',
        'social.backends.xing.XingOAuth',
        'social.backends.yandex.YandexOAuth2',
        'social.backends.podio.PodioOAuth2',
        'social.backends.reddit.RedditOAuth2',
    )
}


def includeme(config):
    config.registry.settings.update(SOCIAL_AUTH_SETTINGS)

########NEW FILE########
__FILENAME__ = tests
import unittest
import transaction

from pyramid import testing

from .models import DBSession


class TestMyViewSuccessCondition(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from .models import (
            Base,
            MyModel,
            )
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)
        with transaction.manager:
            model = MyModel(name='one', value=55)
            DBSession.add(model)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_passing_view(self):
        from .views import my_view
        request = testing.DummyRequest()
        info = my_view(request)
        self.assertEqual(info['one'].name, 'one')
        self.assertEqual(info['project'], 'example')


class TestMyViewFailureCondition(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from .models import (
            Base,
            MyModel,
            )
        DBSession.configure(bind=engine)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_failing_view(self):
        from .views import my_view
        request = testing.DummyRequest()
        info = my_view(request)
        self.assertEqual(info.status_int, 500)

########NEW FILE########
__FILENAME__ = views
from pyramid.view import view_config


@view_config(route_name='home', renderer='templates/home.pt')
def home(request):
    return {}


@view_config(route_name='done', renderer='templates/done.pt')
def done(request):
    return {}

########NEW FILE########
__FILENAME__ = app
import sys

sys.path.append('../..')

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from social.apps.tornado_app.models import init_social
from social.apps.tornado_app.routes import SOCIAL_AUTH_ROUTES

import settings


engine = create_engine('sqlite:///test.db', echo=False)
session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('templates/home.html')


class DoneHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        from models import User
        user_id = self.get_secure_cookie('user_id')
        user = session.query(User).get(int(user_id))
        self.render('templates/done.html', user=user)


class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.request.redirect('/')


tornado.options.parse_command_line()
tornado_settings = dict((k, getattr(settings, k)) for k in dir(settings)
                        if not k.startswith('__'))
application = tornado.web.Application(SOCIAL_AUTH_ROUTES + [
    (r'/', MainHandler),
    (r'/done/', DoneHandler),
    (r'/logout/', LogoutHandler),
], cookie_secret='adb528da-20bb-4386-8eaf-09f041b569e0',
   **tornado_settings)


def main():
    init_social(Base, session, tornado_settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()


def syncdb():
    from models import User
    init_social(Base, session, tornado_settings)
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'syncdb':
        syncdb()
    else:
        main()

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String

from app import Base, engine


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(30), nullable=False)
    first_name = Column(String(30), nullable=True)
    last_name = Column(String(30), nullable=True)
    email = Column(String(75), nullable=False)
    password = Column(String(128), nullable=True)


if __name__ == '__main__':
    Base.metadata.create_all(engine)

########NEW FILE########
__FILENAME__ = settings
SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'

SOCIAL_AUTH_LOGIN_URL = '/'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/done/'
SOCIAL_AUTH_USER_MODEL = 'models.User'
SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    'social.backends.open_id.OpenIdAuth',
    'social.backends.google.GoogleOpenId',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.yahoo.YahooOpenId',
    'social.backends.stripe.StripeOAuth2',
    'social.backends.persona.PersonaAuth',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.facebook.FacebookAppOAuth2',
    'social.backends.yahoo.YahooOAuth',
    'social.backends.angel.AngelOAuth2',
    'social.backends.behance.BehanceOAuth2',
    'social.backends.bitbucket.BitbucketOAuth',
    'social.backends.box.BoxOAuth2',
    'social.backends.linkedin.LinkedinOAuth',
    'social.backends.github.GithubOAuth2',
    'social.backends.foursquare.FoursquareOAuth2',
    'social.backends.instagram.InstagramOAuth2',
    'social.backends.live.LiveOAuth2',
    'social.backends.vk.VKOAuth2',
    'social.backends.dailymotion.DailymotionOAuth2',
    'social.backends.disqus.DisqusOAuth2',
    'social.backends.dropbox.DropboxOAuth',
    'social.backends.evernote.EvernoteSandboxOAuth',
    'social.backends.fitbit.FitbitOAuth',
    'social.backends.flickr.FlickrOAuth',
    'social.backends.livejournal.LiveJournalOpenId',
    'social.backends.soundcloud.SoundcloudOAuth2',
    'social.backends.thisismyjam.ThisIsMyJamOAuth1',
    'social.backends.stocktwits.StocktwitsOAuth2',
    'social.backends.tripit.TripItOAuth',
    'social.backends.clef.ClefOAuth2',
    'social.backends.twilio.TwilioAuth',
    'social.backends.xing.XingOAuth',
    'social.backends.yandex.YandexOAuth2',
    'social.backends.podio.PodioOAuth2',
    'social.backends.reddit.RedditOAuth2',
)

from local_settings import *

########NEW FILE########
__FILENAME__ = app
import sys

sys.path.append('../..')

import web
from web.contrib.template import render_jinja

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from social.utils import setting_name
from social.apps.webpy_app.utils import strategy, backends
from social.apps.webpy_app import app as social_app

import local_settings

web.config.debug = False
web.config[setting_name('USER_MODEL')] = 'models.User'
web.config[setting_name('AUTHENTICATION_BACKENDS')] = (
    'social.backends.open_id.OpenIdAuth',
    'social.backends.google.GoogleOpenId',
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.yahoo.YahooOpenId',
    'social.backends.stripe.StripeOAuth2',
    'social.backends.persona.PersonaAuth',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.facebook.FacebookAppOAuth2',
    'social.backends.yahoo.YahooOAuth',
    'social.backends.angel.AngelOAuth2',
    'social.backends.behance.BehanceOAuth2',
    'social.backends.bitbucket.BitbucketOAuth',
    'social.backends.box.BoxOAuth2',
    'social.backends.linkedin.LinkedinOAuth',
    'social.backends.github.GithubOAuth2',
    'social.backends.foursquare.FoursquareOAuth2',
    'social.backends.instagram.InstagramOAuth2',
    'social.backends.live.LiveOAuth2',
    'social.backends.vk.VKOAuth2',
    'social.backends.dailymotion.DailymotionOAuth2',
    'social.backends.disqus.DisqusOAuth2',
    'social.backends.dropbox.DropboxOAuth',
    'social.backends.evernote.EvernoteSandboxOAuth',
    'social.backends.fitbit.FitbitOAuth',
    'social.backends.flickr.FlickrOAuth',
    'social.backends.livejournal.LiveJournalOpenId',
    'social.backends.soundcloud.SoundcloudOAuth2',
    'social.backends.thisismyjam.ThisIsMyJamOAuth1',
    'social.backends.stocktwits.StocktwitsOAuth2',
    'social.backends.tripit.TripItOAuth',
    'social.backends.clef.ClefOAuth2',
    'social.backends.twilio.TwilioAuth',
    'social.backends.xing.XingOAuth',
    'social.backends.yandex.YandexOAuth2',
    'social.backends.podio.PodioOAuth2',
)
web.config[setting_name('LOGIN_REDIRECT_URL')] = '/done/'


urls = (
    '^/$', 'main',
    '^/done/$', 'done',
    '', social_app.app_social
)


render = render_jinja('templates/')


class main(object):
    def GET(self):
        return render.home()


class done(social_app.BaseViewClass):
    @strategy()
    def GET(self):
        user = self.get_current_user()
        return render.done(user=user, backends=backends(user))


engine = create_engine('sqlite:///test.db', echo=True)


def load_sqla(handler):
    web.ctx.orm = scoped_session(sessionmaker(bind=engine))
    try:
        return handler()
    except web.HTTPError:
        web.ctx.orm.commit()
        raise
    except:
        web.ctx.orm.rollback()
        raise
    finally:
        web.ctx.orm.commit()
        # web.ctx.orm.expunge_all()


Session = sessionmaker(bind=engine)
Session.configure(bind=engine)

app = web.application(urls, locals())
app.add_processor(load_sqla)
session = web.session.Session(app, web.session.DiskStore('sessions'))

web.db_session = Session()
web.web_session = session


if __name__ == "__main__":
    app.run()

########NEW FILE########
__FILENAME__ = migrate
from app import engine
from models import Base
from social.apps.webpy_app.models import SocialBase


if __name__ == '__main__':
    Base.metadata.create_all(engine)
    SocialBase.metadata.create_all(engine)

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(200))
    password = Column(String(200), default='')
    name = Column(String(100))
    email = Column(String(200))
    active = Column(Boolean, default=True)

    def is_active(self):
        return self.active

    def is_authenticated(self):
        return True

########NEW FILE########
__FILENAME__ = actions
from social.p3 import quote
from social.utils import sanitize_redirect, user_is_authenticated, \
                         user_is_active, partial_pipeline_data, setting_url


def do_auth(strategy, redirect_name='next'):
    # Save any defined next value into session
    data = strategy.request_data(merge=False)

    # Save extra data into session.
    for field_name in strategy.setting('FIELDS_STORED_IN_SESSION', []):
        if field_name in data:
            strategy.session_set(field_name, data[field_name])

    if redirect_name in data:
        # Check and sanitize a user-defined GET/POST next field value
        redirect_uri = data[redirect_name]
        if strategy.setting('SANITIZE_REDIRECTS', True):
            redirect_uri = sanitize_redirect(strategy.request_host(),
                                             redirect_uri)
        strategy.session_set(
            redirect_name,
            redirect_uri or strategy.setting('LOGIN_REDIRECT_URL')
        )
    return strategy.start()


def do_complete(strategy, login, user=None, redirect_name='next',
                *args, **kwargs):
    # pop redirect value before the session is trashed on login()
    data = strategy.request_data()
    redirect_value = strategy.session_get(redirect_name, '') or \
                     data.get(redirect_name, '')

    is_authenticated = user_is_authenticated(user)
    user = is_authenticated and user or None

    partial = partial_pipeline_data(strategy, user, *args, **kwargs)
    if partial:
        xargs, xkwargs = partial
        user = strategy.continue_pipeline(*xargs, **xkwargs)
    else:
        user = strategy.complete(user=user, request=strategy.request,
                                 *args, **kwargs)

    if user and not isinstance(user, strategy.storage.user.user_model()):
        return user

    if is_authenticated:
        if not user:
            url = setting_url(strategy, redirect_value, 'LOGIN_REDIRECT_URL')
        else:
            url = setting_url(strategy, redirect_value,
                              'NEW_ASSOCIATION_REDIRECT_URL',
                              'LOGIN_REDIRECT_URL')
    elif user:
        if user_is_active(user):
            # catch is_new/social_user in case login() resets the instance
            is_new = getattr(user, 'is_new', False)
            social_user = user.social_user
            login(strategy, user, social_user)
            # store last login backend name in session
            strategy.session_set('social_auth_last_login_backend',
                                 social_user.provider)

            if is_new:
                url = setting_url(strategy,
                                  'NEW_USER_REDIRECT_URL',
                                  redirect_value,
                                  'LOGIN_REDIRECT_URL')
            else:
                url = setting_url(strategy, redirect_value,
                                  'LOGIN_REDIRECT_URL')
        else:
            url = setting_url(strategy, 'INACTIVE_USER_URL', 'LOGIN_ERROR_URL',
                              'LOGIN_URL')
    else:
        url = setting_url(strategy, 'LOGIN_ERROR_URL', 'LOGIN_URL')

    if redirect_value and redirect_value != url:
        redirect_value = quote(redirect_value)
        url += ('?' in url and '&' or '?') + \
               '{0}={1}'.format(redirect_name, redirect_value)

    if strategy.setting('SANITIZE_REDIRECTS', True):
        url = sanitize_redirect(strategy.request_host(), url) or \
              strategy.setting('LOGIN_REDIRECT_URL')
    return strategy.redirect(url)


def do_disconnect(strategy, user, association_id=None, redirect_name='next',
                  *args, **kwargs):
    partial = partial_pipeline_data(strategy, user, *args, **kwargs)
    if partial:
        xargs, xkwargs = partial
        if association_id and not xkwargs.get('association_id'):
            xkwargs['association_id'] = association_id
        response = strategy.disconnect(*xargs, **xkwargs)
    else:
        response = strategy.disconnect(user=user,
                                       association_id=association_id,
                                       *args, **kwargs)

    if isinstance(response, dict):
        response = strategy.redirect(
            strategy.request_data().get(redirect_name, '') or
            strategy.setting('DISCONNECT_REDIRECT_URL') or
            strategy.setting('LOGIN_REDIRECT_URL')
        )
    return response

########NEW FILE########
__FILENAME__ = models
"""Flask SQLAlchemy ORM models for Social Auth"""
import cherrypy

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

from social.utils import setting_name, module_member
from social.storage.sqlalchemy_orm import SQLAlchemyUserMixin, \
                                          SQLAlchemyAssociationMixin, \
                                          SQLAlchemyNonceMixin, \
                                          BaseSQLAlchemyStorage
from social.apps.flask_app.fields import JSONType


SocialBase = declarative_base()

DB_SESSION_ATTR = cherrypy.config.get(setting_name('DB_SESSION_ATTR'), 'db')
UID_LENGTH = cherrypy.config.get(setting_name('UID_LENGTH'), 255)
User = module_member(cherrypy.config[setting_name('USER_MODEL')])


class CherryPySocialBase(object):
    @classmethod
    def _session(cls):
        return getattr(cherrypy.request, DB_SESSION_ATTR)


class UserSocialAuth(CherryPySocialBase, SQLAlchemyUserMixin, SocialBase):
    """Social Auth association model"""
    __tablename__ = 'social_auth_usersocialauth'
    __table_args__ = (UniqueConstraint('provider', 'uid'),)
    id = Column(Integer, primary_key=True)
    provider = Column(String(32))
    uid = Column(String(UID_LENGTH))
    extra_data = Column(JSONType)
    user_id = Column(Integer, ForeignKey(User.id),
                     nullable=False, index=True)
    user = relationship(User, backref='social_auth')

    @classmethod
    def username_max_length(cls):
        return User.__table__.columns.get('username').type.length

    @classmethod
    def user_model(cls):
        return User


class Nonce(CherryPySocialBase, SQLAlchemyNonceMixin, SocialBase):
    """One use numbers"""
    __tablename__ = 'social_auth_nonce'
    __table_args__ = (UniqueConstraint('server_url', 'timestamp', 'salt'),)
    id = Column(Integer, primary_key=True)
    server_url = Column(String(255))
    timestamp = Column(Integer)
    salt = Column(String(40))


class Association(CherryPySocialBase, SQLAlchemyAssociationMixin, SocialBase):
    """OpenId account association"""
    __tablename__ = 'social_auth_association'
    __table_args__ = (UniqueConstraint('server_url', 'handle'),)
    id = Column(Integer, primary_key=True)
    server_url = Column(String(255))
    handle = Column(String(255))
    secret = Column(String(255))  # base64 encoded
    issued = Column(Integer)
    lifetime = Column(Integer)
    assoc_type = Column(String(64))


class CherryPyStorage(BaseSQLAlchemyStorage):
    user = UserSocialAuth
    nonce = Nonce
    association = Association

########NEW FILE########
__FILENAME__ = utils
import cherrypy

from functools import wraps

from social.utils import setting_name, module_member
from social.strategies.utils import get_strategy
from social.backends.utils import user_backends_data


DEFAULTS = {
    'STRATEGY': 'social.strategies.cherrypy_strategy.CherryPyStrategy',
    'STORAGE': 'social.apps.cherrypy_app.models.CherryPyStorage'
}


def get_helper(name, do_import=False):
    config = cherrypy.config.get(setting_name(name), DEFAULTS.get(name, None))
    return do_import and module_member(config) or config


def strategy(redirect_uri=None):
    def decorator(func):
        @wraps(func)
        def wrapper(self, backend=None, *args, **kwargs):
            uri = redirect_uri

            if uri and backend and '%(backend)s' in uri:
                uri = uri % {'backend': backend}

            backends = get_helper('AUTHENTICATION_BACKENDS')
            strategy = get_helper('STRATEGY')
            storage = get_helper('STORAGE')
            self.strategy = get_strategy(backends, strategy, storage,
                                         cherrypy.request, backend,
                                         redirect_uri=uri, *args, **kwargs)
            if backend:
                return func(self, backend=backend, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


def backends(user):
    """Load Social Auth current user data to context under the key 'backends'.
    Will return the output of social.backends.utils.user_backends_data."""
    return user_backends_data(user, get_helper('AUTHENTICATION_BACKENDS'),
                              get_helper('STORAGE', do_import=True))

########NEW FILE########
__FILENAME__ = views
import cherrypy

from social.utils import setting_name, module_member
from social.actions import do_auth, do_complete, do_disconnect
from social.apps.cherrypy_app.utils import strategy


class CherryPyPSAViews(object):
    @cherrypy.expose
    @strategy('/complete/%(backend)s')
    def login(self, backend):
        return do_auth(self.strategy)

    @cherrypy.expose
    @strategy('/complete/%(backend)s')
    def complete(self, backend, *args, **kwargs):
        login = cherrypy.config.get(setting_name('LOGIN_METHOD'))
        do_login = module_member(login) if login else self.do_login
        user = getattr(cherrypy.request, 'user', None)
        return do_complete(self.strategy, do_login, user=user, *args, **kwargs)

    @cherrypy.expose
    def disconnect(self, backend, association_id=None):
        user = getattr(cherrypy.request, 'user', None)
        return do_disconnect(self.strategy, user, association_id)

    def do_login(self, strategy, user, social_user):
        strategy.session_set('user_id', user.id)

########NEW FILE########
__FILENAME__ = context_processors
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.functional import SimpleLazyObject

try:
    from django.utils.functional import empty as _empty
    empty = _empty
except ImportError:  # django < 1.4
    empty = None


from social.backends.utils import user_backends_data
from social.apps.django_app.utils import Storage, BACKENDS


class LazyDict(SimpleLazyObject):
    """Lazy dict initialization."""
    def __getitem__(self, name):
        if self._wrapped is empty:
            self._setup()
        return self._wrapped[name]

    def __setitem__(self, name, value):
        if self._wrapped is empty:
            self._setup()
        self._wrapped[name] = value


def backends(request):
    """Load Social Auth current user data to context under the key 'backends'.
    Will return the output of social.backends.utils.user_backends_data."""
    return {'backends': LazyDict(lambda: user_backends_data(request.user,
                                                            BACKENDS,
                                                            Storage))}


def login_redirect(request):
    """Load current redirect to context."""
    value = request.method == 'POST' and \
                request.POST.get(REDIRECT_FIELD_NAME) or \
                request.GET.get(REDIRECT_FIELD_NAME)
    querystring = value and (REDIRECT_FIELD_NAME + '=' + value) or ''
    return {
        'REDIRECT_FIELD_NAME': REDIRECT_FIELD_NAME,
        'REDIRECT_FIELD_VALUE': value,
        'REDIRECT_QUERYSTRING': querystring
    }

########NEW FILE########
__FILENAME__ = admin
"""Admin settings"""
from django.conf import settings
from django.contrib import admin

from social.utils import setting_name
from social.apps.django_app.default.models import UserSocialAuth, Nonce, \
                                                  Association


class UserSocialAuthOption(admin.ModelAdmin):
    """Social Auth user options"""
    list_display = ('id', 'user', 'provider', 'uid')
    list_filter = ('provider',)
    raw_id_fields = ('user',)
    list_select_related = True

    def get_search_fields(self, request=None):
        search_fields = getattr(
            settings, setting_name('ADMIN_USER_SEARCH_FIELDS'), None
        )
        if search_fields is None:
            _User = UserSocialAuth.user_model()
            username = getattr(_User, 'USERNAME_FIELD', None) or \
                       hasattr(_User, 'username') and 'username' or \
                       None
            fieldnames = ('first_name', 'last_name', 'email', username)
            all_names = _User._meta.get_all_field_names()
            search_fields = [name for name in fieldnames
                                if name and name in all_names]
        return ['user_' + name for name in search_fields]


class NonceOption(admin.ModelAdmin):
    """Nonce options"""
    list_display = ('id', 'server_url', 'timestamp', 'salt')
    search_fields = ('server_url',)


class AssociationOption(admin.ModelAdmin):
    """Association options"""
    list_display = ('id', 'server_url', 'assoc_type')
    list_filter = ('assoc_type',)
    search_fields = ('server_url',)


admin.site.register(UserSocialAuth, UserSocialAuthOption)
admin.site.register(Nonce, NonceOption)
admin.site.register(Association, AssociationOption)

########NEW FILE########
__FILENAME__ = fields
import json
import six

from django.core.exceptions import ValidationError
from django.db import models

try:
    from django.utils.encoding import smart_unicode as smart_text
    smart_text  # placate pyflakes
except ImportError:
    from django.utils.encoding import smart_text


class JSONField(six.with_metaclass(models.SubfieldBase, models.TextField)):
    """Simple JSON field that stores python structures as JSON strings
    on database.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', '{}')
        super(JSONField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Convert the input JSON value into python structures, raises
        django.core.exceptions.ValidationError if the data can't be converted.
        """
        if self.blank and not value:
            return {}
        value = value or '{}'
        if isinstance(value, six.binary_type):
            value = six.text_type(value, 'utf-8')
        if isinstance(value, six.string_types):
            try:
                # with django 1.6 i have '"{}"' as default value here
                if value[0] == value[-1] == '"':
                    value = value[1:-1]

                return json.loads(value)
            except Exception as err:
                raise ValidationError(str(err))
        else:
            return value

    def validate(self, value, model_instance):
        """Check value is a valid JSON string, raise ValidationError on
        error."""
        if isinstance(value, six.string_types):
            super(JSONField, self).validate(value, model_instance)
            try:
                json.loads(value)
            except Exception as err:
                raise ValidationError(str(err))

    def get_prep_value(self, value):
        """Convert value to JSON string before save"""
        try:
            return json.dumps(value)
        except Exception as err:
            raise ValidationError(str(err))

    def value_to_string(self, obj):
        """Return value from object converted to string properly"""
        return smart_text(self.get_prep_value(self._get_val_from_obj(obj)))

    def value_from_object(self, obj):
        """Return value dumped to string."""
        return self.get_prep_value(self._get_val_from_obj(obj))


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(
        [],
        ["^social\.apps\.django_app\.default\.fields\.JSONField"]
    )
except:
    pass

########NEW FILE########
__FILENAME__ = models
"""Django ORM models for Social Auth"""
import six

from django.db import models
from django.conf import settings
from django.db.utils import IntegrityError

from social.utils import setting_name
from social.storage.django_orm import DjangoUserMixin, \
                                      DjangoAssociationMixin, \
                                      DjangoNonceMixin, \
                                      DjangoCodeMixin, \
                                      BaseDjangoStorage
from social.apps.django_app.default.fields import JSONField


USER_MODEL = getattr(settings, setting_name('USER_MODEL'), None) or \
             getattr(settings, 'AUTH_USER_MODEL', None) or \
             'auth.User'
UID_LENGTH = getattr(settings, setting_name('UID_LENGTH'), 255)
NONCE_SERVER_URL_LENGTH = getattr(
    settings, setting_name('NONCE_SERVER_URL_LENGTH'), 255)
ASSOCIATION_SERVER_URL_LENGTH = getattr(
    settings, setting_name('ASSOCIATION_SERVER_URL_LENGTH'), 255)
ASSOCIATION_HANDLE_LENGTH = getattr(
    settings, setting_name('ASSOCIATION_HANDLE_LENGTH'), 255)


class UserSocialAuth(models.Model, DjangoUserMixin):
    """Social Auth association model"""
    user = models.ForeignKey(USER_MODEL, related_name='social_auth')
    provider = models.CharField(max_length=32)
    uid = models.CharField(max_length=UID_LENGTH)
    extra_data = JSONField()

    class Meta:
        """Meta data"""
        unique_together = ('provider', 'uid')
        db_table = 'social_auth_usersocialauth'

    @classmethod
    def get_social_auth(cls, provider, uid):
        try:
            return cls.objects.select_related('user').get(provider=provider,
                                                          uid=uid)
        except UserSocialAuth.DoesNotExist:
            return None

    @classmethod
    def username_max_length(cls):
        username_field = cls.username_field()
        field = UserSocialAuth.user_model()._meta.get_field(username_field)
        return field.max_length

    @classmethod
    def user_model(cls):
        user_model = UserSocialAuth._meta.get_field('user').rel.to
        if isinstance(user_model, six.string_types):
            app_label, model_name = user_model.split('.')
            return models.get_model(app_label, model_name)
        return user_model


class Nonce(models.Model, DjangoNonceMixin):
    """One use numbers"""
    server_url = models.CharField(max_length=NONCE_SERVER_URL_LENGTH)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=65)

    class Meta:
        db_table = 'social_auth_nonce'


class Association(models.Model, DjangoAssociationMixin):
    """OpenId account association"""
    server_url = models.CharField(max_length=ASSOCIATION_SERVER_URL_LENGTH)
    handle = models.CharField(max_length=ASSOCIATION_HANDLE_LENGTH)
    secret = models.CharField(max_length=255)  # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.CharField(max_length=64)

    class Meta:
        db_table = 'social_auth_association'


class Code(models.Model, DjangoCodeMixin):
    email = models.EmailField()
    code = models.CharField(max_length=32, db_index=True)
    verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'social_auth_code'
        unique_together = ('email', 'code')


class DjangoStorage(BaseDjangoStorage):
    user = UserSocialAuth
    nonce = Nonce
    association = Association
    code = Code

    @classmethod
    def is_integrity_error(cls, exception):
        return exception.__class__ is IntegrityError

########NEW FILE########
__FILENAME__ = tests
from social.apps.django_app.tests import *

########NEW FILE########
__FILENAME__ = models
"""
MongoEngine models for Social Auth

Requires MongoEngine 0.6.10
"""
import six

from django.conf import settings

from mongoengine import DictField, Document, IntField, ReferenceField, \
                        StringField, EmailField, BooleanField
from mongoengine.queryset import OperationError

from social.utils import setting_name, module_member
from social.storage.django_orm import DjangoUserMixin, \
                                      DjangoAssociationMixin, \
                                      DjangoNonceMixin, \
                                      DjangoCodeMixin, \
                                      BaseDjangoStorage


UNUSABLE_PASSWORD = '!'  # Borrowed from django 1.4


def _get_user_model():
    """
    Get the User Document class user for MongoEngine authentication.

    Use the model defined in SOCIAL_AUTH_USER_MODEL if defined, or
    defaults to MongoEngine's configured user document class.
    """
    custom_model = getattr(settings, setting_name('USER_MODEL'), None)
    if custom_model:
        return module_member(custom_model)

    try:
        # Custom user model support with MongoEngine 0.8
        from mongoengine.django.mongo_auth.models import get_user_document
        return get_user_document()
    except ImportError:
        return module_member('mongoengine.django.auth.User')


USER_MODEL = _get_user_model()


class UserSocialAuth(Document, DjangoUserMixin):
    """Social Auth association model"""
    user = ReferenceField(USER_MODEL)
    provider = StringField(max_length=32)
    uid = StringField(max_length=255, unique_with='provider')
    extra_data = DictField()

    def str_id(self):
        return str(self.id)

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        qs = cls.objects
        if provider:
            qs = qs.filter(provider=provider)
        if id:
            qs = qs.filter(id=id)
        return qs.filter(user=user)

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        if not isinstance(type(uid), six.string_types):
            uid = str(uid)
        return cls.objects.create(user=user, uid=uid, provider=provider)

    @classmethod
    def username_max_length(cls):
        username_field = cls.username_field()
        field = getattr(UserSocialAuth.user_model(), username_field)
        return field.max_length

    @classmethod
    def user_model(cls):
        return USER_MODEL

    @classmethod
    def create_user(cls, *args, **kwargs):
        kwargs['password'] = UNUSABLE_PASSWORD
        if 'email' in kwargs:
            # Empty string makes email regex validation fail
            kwargs['email'] = kwargs['email'] or None
        return cls.user_model().create_user(*args, **kwargs)

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None):
        if association_id is not None:
            qs = cls.objects.filter(id__ne=association_id)
        else:
            qs = cls.objects.filter(provider__ne=backend_name)
        qs = qs.filter(user=user)

        if hasattr(user, 'has_usable_password'):
            valid_password = user.has_usable_password()
        else:
            valid_password = True

        return valid_password or qs.count() > 0


class Nonce(Document, DjangoNonceMixin):
    """One use numbers"""
    server_url = StringField(max_length=255)
    timestamp = IntField()
    salt = StringField(max_length=40)


class Association(Document, DjangoAssociationMixin):
    """OpenId account association"""
    server_url = StringField(max_length=255)
    handle = StringField(max_length=255)
    secret = StringField(max_length=255)  # Stored base64 encoded
    issued = IntField()
    lifetime = IntField()
    assoc_type = StringField(max_length=64)


class Code(Document, DjangoCodeMixin):
    email = EmailField()
    code = StringField(max_length=32)
    verified = BooleanField(default=False)


class DjangoStorage(BaseDjangoStorage):
    user = UserSocialAuth
    nonce = Nonce
    association = Association
    code = Code

    @classmethod
    def is_integrity_error(cls, exception):
        return exception.__class__ is OperationError and \
               'E11000' in exception.message

########NEW FILE########
__FILENAME__ = tests
from social.apps.django_app.tests import *

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
import six

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.shortcuts import redirect
from django.utils.http import urlquote

from social.exceptions import SocialAuthBaseException


class SocialAuthExceptionMiddleware(object):
    """Middleware that handles Social Auth AuthExceptions by providing the user
    with a message, logging an error, and redirecting to some next location.

    By default, the exception message itself is sent to the user and they are
    redirected to the location specified in the SOCIAL_AUTH_LOGIN_ERROR_URL
    setting.

    This middleware can be extended by overriding the get_message or
    get_redirect_uri methods, which each accept request and exception.
    """
    def process_exception(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy is None or self.raise_exception(request, exception):
            return

        if isinstance(exception, SocialAuthBaseException):
            backend_name = strategy.backend.name
            message = self.get_message(request, exception)
            url = self.get_redirect_uri(request, exception)
            try:
                messages.error(request, message,
                               extra_tags='social-auth ' + backend_name)
            except MessageFailure:
                url += ('?' in url and '&' or '?') + \
                       'message={0}&backend={1}'.format(urlquote(message),
                                                        backend_name)
            return redirect(url)

    def raise_exception(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy is not None:
            return strategy.setting('RAISE_EXCEPTIONS', settings.DEBUG)

    def get_message(self, request, exception):
        return six.text_type(exception)

    def get_redirect_uri(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        return strategy.setting('LOGIN_ERROR_URL')

########NEW FILE########
__FILENAME__ = tests
from social.tests.test_exceptions import *
from social.tests.test_pipeline import *
from social.tests.test_storage import *
from social.tests.test_utils import *
from social.tests.actions.test_associate import *
from social.tests.actions.test_disconnect import *
from social.tests.actions.test_login import *
from social.tests.backends.test_amazon import *
from social.tests.backends.test_angel import *
from social.tests.backends.test_behance import *
from social.tests.backends.test_bitbucket import *
from social.tests.backends.test_box import *
from social.tests.backends.test_broken import *
from social.tests.backends.test_coinbase import *
from social.tests.backends.test_dailymotion import *
from social.tests.backends.test_disqus import *
from social.tests.backends.test_dropbox import *
from social.tests.backends.test_dummy import *
from social.tests.backends.test_email import *
from social.tests.backends.test_evernote import *
from social.tests.backends.test_facebook import *
from social.tests.backends.test_fitbit import *
from social.tests.backends.test_flickr import *
from social.tests.backends.test_foursquare import *
from social.tests.backends.test_google import *
from social.tests.backends.test_instagram import *
from social.tests.backends.test_linkedin import *
from social.tests.backends.test_live import *
from social.tests.backends.test_livejournal import *
from social.tests.backends.test_mixcloud import *
from social.tests.backends.test_podio import *
from social.tests.backends.test_readability import *
from social.tests.backends.test_reddit import *
from social.tests.backends.test_skyrock import *
from social.tests.backends.test_soundcloud import *
from social.tests.backends.test_stackoverflow import *
from social.tests.backends.test_steam import *
from social.tests.backends.test_stocktwits import *
from social.tests.backends.test_stripe import *
from social.tests.backends.test_thisismyjam import *
from social.tests.backends.test_tripit import *
from social.tests.backends.test_tumblr import *
from social.tests.backends.test_twitter import *
from social.tests.backends.test_username import *
from social.tests.backends.test_utils import *
from social.tests.backends.test_vk import *
from social.tests.backends.test_xing import *
from social.tests.backends.test_yahoo import *
from social.tests.backends.test_yammer import *
from social.tests.backends.test_yandex import *

########NEW FILE########
__FILENAME__ = urls
"""URLs module"""
try:
    from django.conf.urls import patterns, url
except ImportError:
    # Django < 1.4
    from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('social.apps.django_app.views',
    # authentication / association
    url(r'^login/(?P<backend>[^/]+)/$', 'auth',
        name='begin'),
    url(r'^complete/(?P<backend>[^/]+)/$', 'complete',
        name='complete'),
    # disconnection
    url(r'^disconnect/(?P<backend>[^/]+)/$', 'disconnect',
        name='disconnect'),
    url(r'^disconnect/(?P<backend>[^/]+)/(?P<association_id>[^/]+)/$',
        'disconnect', name='disconnect_individual'),
)

########NEW FILE########
__FILENAME__ = utils
from functools import wraps

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404

from social.utils import setting_name, module_member
from social.exceptions import MissingBackend
from social.strategies.utils import get_strategy


BACKENDS = settings.AUTHENTICATION_BACKENDS
STRATEGY = getattr(settings, setting_name('STRATEGY'),
                   'social.strategies.django_strategy.DjangoStrategy')
STORAGE = getattr(settings, setting_name('STORAGE'),
                  'social.apps.django_app.default.models.DjangoStorage')
Strategy = module_member(STRATEGY)
Storage = module_member(STORAGE)


def load_strategy(*args, **kwargs):
    return get_strategy(BACKENDS, STRATEGY, STORAGE, *args, **kwargs)


def strategy(redirect_uri=None, load_strategy=load_strategy):
    def decorator(func):
        @wraps(func)
        def wrapper(request, backend, *args, **kwargs):
            uri = redirect_uri
            if uri and not uri.startswith('/'):
                uri = reverse(redirect_uri, args=(backend,))

            try:
                request.social_strategy = load_strategy(
                    request=request, backend=backend,
                    redirect_uri=uri, *args, **kwargs
                )
            except MissingBackend:
                raise Http404('Backend not found')

            # backward compatibility in attribute name, only if not already
            # defined
            if not hasattr(request, 'strategy'):
                request.strategy = request.social_strategy
            return func(request, backend, *args, **kwargs)
        return wrapper
    return decorator


def setting(name, default=None):
    try:
        return getattr(settings, setting_name(name))
    except AttributeError:
        return getattr(settings, name, default)


class BackendWrapper(object):
    # XXX: Deprecated, restored to avoid session issues
    def authenticate(self, *args, **kwargs):
        return None

    def get_user(self, user_id):
        return Strategy(storage=Storage).get_user(user_id)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth import login, REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST

from social.actions import do_auth, do_complete, do_disconnect
from social.apps.django_app.utils import strategy


@strategy('social:complete')
def auth(request, backend):
    return do_auth(request.social_strategy, redirect_name=REDIRECT_FIELD_NAME)


@csrf_exempt
@strategy('social:complete')
def complete(request, backend, *args, **kwargs):
    """Authentication complete view, override this view if transaction
    management doesn't suit your needs."""
    return do_complete(request.social_strategy, _do_login, request.user,
                       redirect_name=REDIRECT_FIELD_NAME, *args, **kwargs)


@login_required
@strategy()
@require_POST
@csrf_protect
def disconnect(request, backend, association_id=None):
    """Disconnects given backend from current logged in user."""
    return do_disconnect(request.social_strategy, request.user, association_id,
                         redirect_name=REDIRECT_FIELD_NAME)


def _do_login(strategy, user, social_user):
    login(strategy.request, user)
    if strategy.setting('SESSION_EXPIRATION', True):
        # Set session expiration date if present and not disabled
        # by setting. Use last social-auth instance for current
        # provider, users can associate several accounts with
        # a same provider.
        expiration = social_user.expiration_datetime()
        if expiration:
            try:
                strategy.request.session.set_expiry(
                    expiration.seconds + expiration.days * 86400
                )
            except OverflowError:
                # Handle django time zone overflow
                strategy.request.session.set_expiry(None)

########NEW FILE########
__FILENAME__ = fields
import json

from sqlalchemy.types import PickleType, Text


class JSONType(PickleType):
    impl = Text

    def __init__(self, *args, **kwargs):
        kwargs['pickler'] = json
        super(JSONType, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
"""Flask SQLAlchemy ORM models for Social Auth"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from social.utils import setting_name, module_member
from social.storage.sqlalchemy_orm import SQLAlchemyUserMixin, \
                                          SQLAlchemyAssociationMixin, \
                                          SQLAlchemyNonceMixin, \
                                          SQLAlchemyCodeMixin, \
                                          BaseSQLAlchemyStorage
from social.apps.flask_app.fields import JSONType


class FlaskStorage(BaseSQLAlchemyStorage):
    user = None
    nonce = None
    association = None
    code = None


def init_social(app, db):
    UID_LENGTH = app.config.get(setting_name('UID_LENGTH'), 255)
    User = module_member(app.config[setting_name('USER_MODEL')])
    app_session = db.session

    class _AppSession(object):
        @classmethod
        def _session(cls):
            return app_session

    class UserSocialAuth(_AppSession, db.Model, SQLAlchemyUserMixin):
        """Social Auth association model"""
        __tablename__ = 'social_auth_usersocialauth'
        __table_args__ = (UniqueConstraint('provider', 'uid'),)
        id = Column(Integer, primary_key=True)
        provider = Column(String(32))
        uid = Column(String(UID_LENGTH))
        extra_data = Column(JSONType)
        user_id = Column(Integer, ForeignKey(User.id),
                         nullable=False, index=True)
        user = relationship(User, backref=backref('social_auth',
                                                  lazy='dynamic'))

        @classmethod
        def username_max_length(cls):
            return User.__table__.columns.get('username').type.length

        @classmethod
        def user_model(cls):
            return User

    class Nonce(_AppSession, db.Model, SQLAlchemyNonceMixin):
        """One use numbers"""
        __tablename__ = 'social_auth_nonce'
        __table_args__ = (UniqueConstraint('server_url', 'timestamp', 'salt'),)
        id = Column(Integer, primary_key=True)
        server_url = Column(String(255))
        timestamp = Column(Integer)
        salt = Column(String(40))

    class Association(_AppSession, db.Model, SQLAlchemyAssociationMixin):
        """OpenId account association"""
        __tablename__ = 'social_auth_association'
        __table_args__ = (UniqueConstraint('server_url', 'handle'),)
        id = Column(Integer, primary_key=True)
        server_url = Column(String(255))
        handle = Column(String(255))
        secret = Column(String(255))  # base64 encoded
        issued = Column(Integer)
        lifetime = Column(Integer)
        assoc_type = Column(String(64))

    class Code(_AppSession, db.Model, SQLAlchemyCodeMixin):
        __tablename__ = 'social_auth_code'
        __table_args__ = (UniqueConstraint('code', 'email'),)
        id = Column(Integer, primary_key=True)
        email = Column(String(200))
        code = Column(String(32), index=True)

    # Set the references in the storage class
    FlaskStorage.user = UserSocialAuth
    FlaskStorage.nonce = Nonce
    FlaskStorage.association = Association
    FlaskStorage.code = Code

########NEW FILE########
__FILENAME__ = routes
from flask import g, Blueprint, request
from flask.ext.login import login_required, login_user

from social.actions import do_auth, do_complete, do_disconnect
from social.apps.flask_app.utils import strategy


social_auth = Blueprint('social', __name__)


@social_auth.route('/login/<string:backend>/', methods=('GET', 'POST'))
@strategy('social.complete')
def auth(backend):
    return do_auth(g.strategy)


@social_auth.route('/complete/<string:backend>/', methods=('GET', 'POST'))
@strategy('social.complete')
def complete(backend, *args, **kwargs):
    """Authentication complete view, override this view if transaction
    management doesn't suit your needs."""
    return do_complete(g.strategy, login=do_login, user=g.user,
                       *args, **kwargs)


@social_auth.route('/disconnect/<string:backend>/', methods=('POST',))
@social_auth.route('/disconnect/<string:backend>/<int:association_id>/',
                   methods=('POST',))
@login_required
@strategy()
def disconnect(backend, association_id=None):
    """Disconnects given backend from current logged in user."""
    return do_disconnect(g.strategy, g.user, association_id)


def do_login(strategy, user, social_user):
    return login_user(user, remember=request.cookies.get('remember') or
                                     request.args.get('remember') or
                                     request.form.get('remember') or False)

########NEW FILE########
__FILENAME__ = template_filters
from flask import g, request

from social.backends.utils import user_backends_data
from social.apps.flask_app.utils import get_helper


def backends():
    """Load Social Auth current user data to context under the key 'backends'.
    Will return the output of social.backends.utils.user_backends_data."""
    return {
        'backends': user_backends_data(g.user,
                                       get_helper('AUTHENTICATION_BACKENDS'),
                                       get_helper('STORAGE', do_import=True))
    }


def login_redirect():
    """Load current redirect to context."""
    value = request.form.get('next', '') or \
            request.args.get('next', '')
    return {
        'REDIRECT_FIELD_NAME': 'next',
        'REDIRECT_FIELD_VALUE': value,
        'REDIRECT_QUERYSTRING': value and ('next=' + value) or ''
    }

########NEW FILE########
__FILENAME__ = utils
from functools import wraps

from flask import current_app, url_for, g, request

from social.utils import module_member, setting_name
from social.strategies.utils import get_strategy


DEFAULTS = {
    'STORAGE': 'social.apps.flask_app.models.FlaskStorage',
    'STRATEGY': 'social.strategies.flask_strategy.FlaskStrategy'
}


def get_helper(name, do_import=False):
    config = current_app.config.get(setting_name(name),
                                    DEFAULTS.get(name, None))
    return do_import and module_member(config) or config


def load_strategy(*args, **kwargs):
    backends = get_helper('AUTHENTICATION_BACKENDS')
    strategy = get_helper('STRATEGY')
    storage = get_helper('STORAGE')
    return get_strategy(backends, strategy, storage, *args, **kwargs)


def strategy(redirect_uri=None):
    def decorator(func):
        @wraps(func)
        def wrapper(backend, *args, **kwargs):
            uri = redirect_uri
            if uri and not uri.startswith('/'):
                uri = url_for(uri, backend=backend)
            g.strategy = load_strategy(request=request, backend=backend,
                                       redirect_uri=uri, *args, **kwargs)
            return func(backend, *args, **kwargs)
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = models
"""Flask SQLAlchemy ORM models for Social Auth"""
from mongoengine import ReferenceField

from social.utils import setting_name, module_member
from social.storage.mongoengine_orm import MongoengineUserMixin, \
                                           MongoengineAssociationMixin, \
                                           MongoengineNonceMixin, \
                                           MongoengineCodeMixin, \
                                           BaseMongoengineStorage


class FlaskStorage(BaseMongoengineStorage):
    user = None
    nonce = None
    association = None
    code = None


def init_social(app, db):
    User = module_member(app.config[setting_name('USER_MODEL')])

    class UserSocialAuth(db.Document, MongoengineUserMixin):
        """Social Auth association model"""
        user = ReferenceField(User)

        @classmethod
        def user_model(cls):
            return User

    class Nonce(db.Document, MongoengineNonceMixin):
        """One use numbers"""
        pass

    class Association(db.Document, MongoengineAssociationMixin):
        """OpenId account association"""
        pass

    class Code(db.Document, MongoengineCodeMixin):
        pass

    # Set the references in the storage class
    FlaskStorage.user = UserSocialAuth
    FlaskStorage.nonce = Nonce
    FlaskStorage.association = Association
    FlaskStorage.code = Code

########NEW FILE########
__FILENAME__ = routes
from flask import g, Blueprint, request
from flask.ext.login import login_required, login_user

from social.actions import do_auth, do_complete, do_disconnect
from social.apps.flask_me_app.utils import strategy


social_auth = Blueprint('social', __name__)


@social_auth.route('/login/<string:backend>/', methods=('GET', 'POST'))
@strategy('social.complete')
def auth(backend):
    return do_auth(g.strategy)


@social_auth.route('/complete/<string:backend>/', methods=('GET', 'POST'))
@strategy('social.complete')
def complete(backend, *args, **kwargs):
    """Authentication complete view, override this view if transaction
    management doesn't suit your needs."""
    return do_complete(g.strategy, login=do_login, user=g.user,
                       *args, **kwargs)


@social_auth.route('/disconnect/<string:backend>/', methods=('POST',))
@social_auth.route('/disconnect/<string:backend>/<string:association_id>/',
                   methods=('POST',))
@login_required
@strategy()
def disconnect(backend, association_id=None):
    """Disconnects given backend from current logged in user."""
    return do_disconnect(g.strategy, g.user, association_id)


def do_login(strategy, user, social_user):
    return login_user(user, remember=request.cookies.get('remember') or
                                     request.args.get('remember') or
                                     request.form.get('remember') or False)

########NEW FILE########
__FILENAME__ = template_filters
from flask import g, request

from social.backends.utils import user_backends_data
from social.apps.flask_me_app.utils import get_helper


def backends():
    """Load Social Auth current user data to context under the key 'backends'.
    Will return the output of social.backends.utils.user_backends_data."""
    return {
        'backends': user_backends_data(g.user,
                                       get_helper('AUTHENTICATION_BACKENDS'),
                                       get_helper('STORAGE', do_import=True))
    }


def login_redirect():
    """Load current redirect to context."""
    value = request.form.get('next', '') or \
            request.args.get('next', '')
    return {
        'REDIRECT_FIELD_NAME': 'next',
        'REDIRECT_FIELD_VALUE': value,
        'REDIRECT_QUERYSTRING': value and ('next=' + value) or ''
    }

########NEW FILE########
__FILENAME__ = utils
from functools import wraps

from flask import current_app, url_for, g, request

from social.utils import module_member, setting_name
from social.strategies.utils import get_strategy


DEFAULTS = {
    'STORAGE': 'social.apps.flask_me_app.models.FlaskStorage',
    'STRATEGY': 'social.strategies.flask_strategy.FlaskStrategy'
}


def get_helper(name, do_import=False):
    config = current_app.config.get(setting_name(name),
                                    DEFAULTS.get(name, None))
    return do_import and module_member(config) or config


def load_strategy(*args, **kwargs):
    backends = get_helper('AUTHENTICATION_BACKENDS')
    strategy = get_helper('STRATEGY')
    storage = get_helper('STORAGE')
    return get_strategy(backends, strategy, storage, *args, **kwargs)


def strategy(redirect_uri=None):
    def decorator(func):
        @wraps(func)
        def wrapper(backend, *args, **kwargs):
            uri = redirect_uri
            if uri and not uri.startswith('/'):
                uri = url_for(uri, backend=backend)
            g.strategy = load_strategy(request=request, backend=backend,
                                       redirect_uri=uri, *args, **kwargs)
            return func(backend, *args, **kwargs)
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = fields
import json

from sqlalchemy.types import PickleType, Text


class JSONType(PickleType):
    impl = Text

    def __init__(self, *args, **kwargs):
        kwargs['pickler'] = json
        super(JSONType, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
"""Pyramid SQLAlchemy ORM models for Social Auth"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from social.utils import setting_name, module_member
from social.storage.sqlalchemy_orm import SQLAlchemyUserMixin, \
                                          SQLAlchemyAssociationMixin, \
                                          SQLAlchemyNonceMixin, \
                                          SQLAlchemyCodeMixin, \
                                          BaseSQLAlchemyStorage
from social.apps.pyramid_app.fields import JSONType


class PyramidStorage(BaseSQLAlchemyStorage):
    user = None
    nonce = None
    association = None


def init_social(config, Base, session):
    if hasattr(config, 'registry'):
        config = config.registry.settings
    UID_LENGTH = config.get(setting_name('UID_LENGTH'), 255)
    User = module_member(config[setting_name('USER_MODEL')])
    app_session = session

    class _AppSession(object):
        COMMIT_SESSION = False

        @classmethod
        def _session(cls):
            return app_session

    class UserSocialAuth(_AppSession, Base, SQLAlchemyUserMixin):
        """Social Auth association model"""
        __tablename__ = 'social_auth_usersocialauth'
        __table_args__ = (UniqueConstraint('provider', 'uid'),)
        id = Column(Integer, primary_key=True)
        provider = Column(String(32))
        uid = Column(String(UID_LENGTH))
        extra_data = Column(JSONType)
        user_id = Column(Integer, ForeignKey(User.id),
                         nullable=False, index=True)
        user = relationship(User, backref=backref('social_auth',
                                                  lazy='dynamic'))

        @classmethod
        def username_max_length(cls):
            return User.__table__.columns.get('username').type.length

        @classmethod
        def user_model(cls):
            return User

    class Nonce(_AppSession, Base, SQLAlchemyNonceMixin):
        """One use numbers"""
        __tablename__ = 'social_auth_nonce'
        __table_args__ = (UniqueConstraint('server_url', 'timestamp', 'salt'),)
        id = Column(Integer, primary_key=True)
        server_url = Column(String(255))
        timestamp = Column(Integer)
        salt = Column(String(40))

    class Association(_AppSession, Base, SQLAlchemyAssociationMixin):
        """OpenId account association"""
        __tablename__ = 'social_auth_association'
        __table_args__ = (UniqueConstraint('server_url', 'handle'),)
        id = Column(Integer, primary_key=True)
        server_url = Column(String(255))
        handle = Column(String(255))
        secret = Column(String(255))  # base64 encoded
        issued = Column(Integer)
        lifetime = Column(Integer)
        assoc_type = Column(String(64))

    class Code(_AppSession, Base, SQLAlchemyCodeMixin):
        __tablename__ = 'social_auth_code'
        __table_args__ = (UniqueConstraint('code', 'email'),)
        id = Column(Integer, primary_key=True)
        email = Column(String(200))
        code = Column(String(32), index=True)

    # Set the references in the storage class
    PyramidStorage.user = UserSocialAuth
    PyramidStorage.nonce = Nonce
    PyramidStorage.association = Association
    PyramidStorage.code = Code

########NEW FILE########
__FILENAME__ = utils
from functools import wraps

from pyramid.threadlocal import get_current_registry
from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden

from social.utils import setting_name, module_member
from social.strategies.utils import get_strategy
from social.backends.utils import user_backends_data


DEFAULTS = {
    'STORAGE': 'social.apps.pyramid_app.models.PyramidStorage',
    'STRATEGY': 'social.strategies.pyramid_strategy.PyramidStrategy'
}


def get_helper(name):
    settings = get_current_registry().settings
    return settings.get(setting_name(name), DEFAULTS.get(name, None))


def load_strategy(*args, **kwargs):
    backends = get_helper('AUTHENTICATION_BACKENDS')
    strategy = get_helper('STRATEGY')
    storage = get_helper('STORAGE')
    return get_strategy(backends, strategy, storage, *args, **kwargs)


def strategy(redirect_uri=None):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            backend = request.matchdict.get('backend')
            if not backend:
                return HTTPNotFound('Missing backend')

            uri = redirect_uri
            if uri and not uri.startswith('/'):
                uri = request.route_url(uri, backend=backend)
            request.strategy = load_strategy(
                backend=backend, redirect_uri=uri, request=request,
                *args, **kwargs
            )
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        is_logged_in = module_member(
            request.strategy.setting('LOGGEDIN_FUNCTION')
        )
        if not is_logged_in(request):
            raise HTTPForbidden('Not authorized user')
        return func(request, *args, **kwargs)
    return wrapper


def backends(request, user):
    """Load Social Auth current user data to context under the key 'backends'.
    Will return the output of social.backends.utils.user_backends_data."""
    storage = module_member(get_helper('STORAGE'))
    return {
        'backends': user_backends_data(
            user, get_helper('AUTHENTICATION_BACKENDS'), storage
        )
    }

########NEW FILE########
__FILENAME__ = views
from pyramid.view import view_config

from social.utils import module_member
from social.actions import do_auth, do_complete, do_disconnect
from social.apps.pyramid_app.utils import strategy, login_required


@view_config(route_name='social.auth', request_method='GET')
@strategy('social.complete')
def auth(request):
    return do_auth(request.strategy, redirect_name='next')


@view_config(route_name='social.complete', request_method=('GET', 'POST'))
@strategy('social.complete')
def complete(request, *args, **kwargs):
    do_login = module_member(request.strategy.setting('LOGIN_FUNCTION'))
    return do_complete(request.strategy, do_login, request.user,
                       redirect_name='next', *args, **kwargs)


@view_config(route_name='social.disconnect', request_method=('POST',))
@view_config(route_name='social.disconnect_association',
             request_method=('POST',))
@strategy()
@login_required
def disconnect(request):
    return do_disconnect(request.strategy, request.user,
                         request.matchdict.get('association_id'),
                         redirect_name='next')

########NEW FILE########
__FILENAME__ = fields
import json

from sqlalchemy.types import PickleType, Text


class JSONType(PickleType):
    impl = Text

    def __init__(self, *args, **kwargs):
        kwargs['pickler'] = json
        super(JSONType, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = handlers
from tornado.web import RequestHandler

from social.apps.tornado_app.utils import strategy
from social.actions import do_auth, do_complete, do_disconnect


class BaseHandler(RequestHandler):
    def user_id(self):
        return self.get_secure_cookie('user_id')

    def get_current_user(self):
        user_id = self.user_id()
        if user_id:
            return self.strategy.get_user(int(user_id))

    def login_user(self, user):
        self.set_secure_cookie('user_id', str(user.id))


class AuthHandler(BaseHandler):
    def get(self, backend):
        self._auth(backend)

    def post(self, backend):
        self._auth(backend)

    @strategy('complete')
    def _auth(self, backend):
        do_auth(self.strategy)


class CompleteHandler(BaseHandler):
    def get(self, backend):
        self._complete(backend)

    def post(self, backend):
        self._complete(backend)

    @strategy('complete')
    def _complete(self, backend):
        do_complete(
            self.strategy,
            login=lambda strategy, user, social_user: self.login_user(user),
            user=self.get_current_user()
        )


class DisconnectHandler(BaseHandler):
    def post(self):
        do_disconnect()

########NEW FILE########
__FILENAME__ = models
"""Tornado SQLAlchemy ORM models for Social Auth"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from social.utils import setting_name, module_member
from social.storage.sqlalchemy_orm import SQLAlchemyUserMixin, \
                                          SQLAlchemyAssociationMixin, \
                                          SQLAlchemyNonceMixin, \
                                          SQLAlchemyCodeMixin, \
                                          BaseSQLAlchemyStorage
from social.apps.tornado_app.fields import JSONType


class TornadoStorage(BaseSQLAlchemyStorage):
    user = None
    nonce = None
    association = None
    code = None


def init_social(Base, session, settings):
    UID_LENGTH = settings.get(setting_name('UID_LENGTH'), 255)
    User = module_member(settings[setting_name('USER_MODEL')])
    app_session = session

    class _AppSession(object):
        @classmethod
        def _session(cls):
            return app_session

    class UserSocialAuth(_AppSession, Base, SQLAlchemyUserMixin):
        """Social Auth association model"""
        __tablename__ = 'social_auth_usersocialauth'
        __table_args__ = (UniqueConstraint('provider', 'uid'),)
        id = Column(Integer, primary_key=True)
        provider = Column(String(32))
        uid = Column(String(UID_LENGTH))
        extra_data = Column(JSONType)
        user_id = Column(Integer, ForeignKey(User.id),
                         nullable=False, index=True)
        user = relationship(User, backref=backref('social_auth',
                                                  lazy='dynamic'))

        @classmethod
        def username_max_length(cls):
            return User.__table__.columns.get('username').type.length

        @classmethod
        def user_model(cls):
            return User

    class Nonce(_AppSession, Base, SQLAlchemyNonceMixin):
        """One use numbers"""
        __tablename__ = 'social_auth_nonce'
        __table_args__ = (UniqueConstraint('server_url', 'timestamp', 'salt'),)
        id = Column(Integer, primary_key=True)
        server_url = Column(String(255))
        timestamp = Column(Integer)
        salt = Column(String(40))

    class Association(_AppSession, Base, SQLAlchemyAssociationMixin):
        """OpenId account association"""
        __tablename__ = 'social_auth_association'
        __table_args__ = (UniqueConstraint('server_url', 'handle'),)
        id = Column(Integer, primary_key=True)
        server_url = Column(String(255))
        handle = Column(String(255))
        secret = Column(String(255))  # base64 encoded
        issued = Column(Integer)
        lifetime = Column(Integer)
        assoc_type = Column(String(64))

    class Code(_AppSession, Base, SQLAlchemyCodeMixin):
        __tablename__ = 'social_auth_code'
        __table_args__ = (UniqueConstraint('code', 'email'),)
        id = Column(Integer, primary_key=True)
        email = Column(String(200))
        code = Column(String(32), index=True)

    # Set the references in the storage class
    TornadoStorage.user = UserSocialAuth
    TornadoStorage.nonce = Nonce
    TornadoStorage.association = Association
    TornadoStorage.code = Code

########NEW FILE########
__FILENAME__ = routes
from tornado.web import url

from handlers import AuthHandler, CompleteHandler, DisconnectHandler


SOCIAL_AUTH_ROUTES = [
    url(r'/login/(?P<backend>[^/]+)/?', AuthHandler, name='begin'),
    url(r'/complete/(?P<backend>[^/]+)/?', CompleteHandler, name='complete'),
    url(r'/disconnect/(?P<backend>[^/]+)/?', DisconnectHandler,
        name='disconnect'),
    url(r'/disconnect/(?P<backend>[^/]+)/(?P<association_id>\d+)/?',
        DisconnectHandler, name='disconect_individual'),
]

########NEW FILE########
__FILENAME__ = utils
from functools import wraps

from social.utils import setting_name
from social.strategies.utils import get_strategy


DEFAULTS = {
    'STORAGE': 'social.apps.tornado_app.models.TornadoStorage',
    'STRATEGY': 'social.strategies.tornado_strategy.TornadoStrategy'
}


def get_helper(request_handler, name):
    return request_handler.settings.get(setting_name(name),
                                        DEFAULTS.get(name, None))


def load_strategy(request_handler, *args, **kwargs):
    backends = get_helper(request_handler, 'AUTHENTICATION_BACKENDS')
    strategy = get_helper(request_handler, 'STRATEGY')
    storage = get_helper(request_handler, 'STORAGE')
    return get_strategy(backends, strategy, storage, request_handler.request,
                        request_handler=request_handler, *args, **kwargs)


def strategy(redirect_uri=None):
    def decorator(func):
        @wraps(func)
        def wrapper(self, backend, *args, **kwargs):
            uri = redirect_uri
            if uri and not uri.startswith('/'):
                uri = self.reverse_url(uri, backend)
            self.strategy = load_strategy(self,
                                          backend=backend,
                                          redirect_uri=uri, *args, **kwargs)
            return func(self, backend, *args, **kwargs)
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = app
import web

from social.actions import do_auth, do_complete, do_disconnect
from social.apps.webpy_app.utils import strategy


urls = (
  '/login/(?P<backend>[^/]+)/?', 'auth',
  '/complete/(?P<backend>[^/]+)/?', 'complete',
  '/disconnect/(?P<backend>[^/]+)/?', 'disconnect',
  '/disconnect/(?P<backend>[^/]+)/(?P<association_id>\d+)/?', 'disconnect',
)


class BaseViewClass(object):
    def __init__(self, *args, **kwargs):
        self.session = web.web_session
        method = web.ctx.method == 'POST' and 'post' or 'get'
        self.data = web.input(_method=method)
        super(BaseViewClass, self).__init__(*args, **kwargs)

    def get_current_user(self):
        if not hasattr(self, '_user'):
            if self.session.get('logged_in'):
                self._user = self.strategy.get_user(
                    self.session.get('user_id')
                )
            else:
                self._user = None
        return self._user

    def login_user(self, user):
        self.session['logged_in'] = True
        self.session['user_id'] = user.id


class auth(BaseViewClass):
    def GET(self, backend):
        return self._auth(backend)

    def POST(self, backend):
        return self._auth(backend)

    @strategy('/complete/%(backend)s/')
    def _auth(self, backend):
        return do_auth(self.strategy)


class complete(BaseViewClass):
    def GET(self, backend, *args, **kwargs):
        return self._complete(backend, *args, **kwargs)

    def POST(self, backend, *args, **kwargs):
        return self._complete(backend, *args, **kwargs)

    @strategy('/complete/%(backend)s/')
    def _complete(self, backend, *args, **kwargs):
        return do_complete(
            self.strategy,
            login=lambda strat, user, social_user: self.login_user(user),
            user=self.get_current_user(), *args, **kwargs
        )


class disconnect(BaseViewClass):
    @strategy()
    def POST(self, backend, association_id=None):
        return do_disconnect(self.strategy, self.get_current_user(),
                             association_id)


app_social = web.application(urls, locals())

########NEW FILE########
__FILENAME__ = fields
import json

from sqlalchemy.types import PickleType, Text


class JSONType(PickleType):
    impl = Text

    def __init__(self, *args, **kwargs):
        kwargs['pickler'] = json
        super(JSONType, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
"""Flask SQLAlchemy ORM models for Social Auth"""
import web

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

from social.utils import setting_name, module_member
from social.storage.sqlalchemy_orm import SQLAlchemyUserMixin, \
                                          SQLAlchemyAssociationMixin, \
                                          SQLAlchemyNonceMixin, \
                                          SQLAlchemyCodeMixin, \
                                          BaseSQLAlchemyStorage
from social.apps.webpy_app.fields import JSONType


SocialBase = declarative_base()

UID_LENGTH = web.config.get(setting_name('UID_LENGTH'), 255)
User = module_member(web.config[setting_name('USER_MODEL')])


class UserSocialAuth(SQLAlchemyUserMixin, SocialBase):
    """Social Auth association model"""
    __tablename__ = 'social_auth_usersocialauth'
    __table_args__ = (UniqueConstraint('provider', 'uid'),)
    id = Column(Integer, primary_key=True)
    provider = Column(String(32))
    uid = Column(String(UID_LENGTH))
    extra_data = Column(JSONType)
    user_id = Column(Integer, ForeignKey(User.id),
                     nullable=False, index=True)
    user = relationship(User, backref='social_auth')

    @classmethod
    def username_max_length(cls):
        return User.__table__.columns.get('username').type.length

    @classmethod
    def user_model(cls):
        return User

    @classmethod
    def _session(cls):
        return web.db_session


class Nonce(SQLAlchemyNonceMixin, SocialBase):
    """One use numbers"""
    __tablename__ = 'social_auth_nonce'
    __table_args__ = (UniqueConstraint('server_url', 'timestamp', 'salt'),)
    id = Column(Integer, primary_key=True)
    server_url = Column(String(255))
    timestamp = Column(Integer)
    salt = Column(String(40))

    @classmethod
    def _session(cls):
        return web.db_session


class Association(SQLAlchemyAssociationMixin, SocialBase):
    """OpenId account association"""
    __tablename__ = 'social_auth_association'
    __table_args__ = (UniqueConstraint('server_url', 'handle'),)
    id = Column(Integer, primary_key=True)
    server_url = Column(String(255))
    handle = Column(String(255))
    secret = Column(String(255))  # base64 encoded
    issued = Column(Integer)
    lifetime = Column(Integer)
    assoc_type = Column(String(64))

    @classmethod
    def _session(cls):
        return web.db_session


class Code(SQLAlchemyCodeMixin, SocialBase):
    __tablename__ = 'social_auth_code'
    __table_args__ = (UniqueConstraint('code', 'email'),)
    id = Column(Integer, primary_key=True)
    email = Column(String(200))
    code = Column(String(32), index=True)

    @classmethod
    def _session(cls):
        return web.db_session


class WebpyStorage(BaseSQLAlchemyStorage):
    user = UserSocialAuth
    nonce = Nonce
    association = Association
    code = Code

########NEW FILE########
__FILENAME__ = utils
import web

from functools import wraps

from social.utils import setting_name, module_member
from social.backends.utils import user_backends_data
from social.strategies.utils import get_strategy


DEFAULTS = {
    'STRATEGY': 'social.strategies.webpy_strategy.WebpyStrategy',
    'STORAGE': 'social.apps.webpy_app.models.WebpyStorage'
}


def get_helper(name, do_import=False):
    config = web.config.get(setting_name(name),
                            DEFAULTS.get(name, None))
    return do_import and module_member(config) or config


def load_strategy(*args, **kwargs):
    backends = get_helper('AUTHENTICATION_BACKENDS')
    strategy = get_helper('STRATEGY')
    storage = get_helper('STORAGE')
    return get_strategy(backends, strategy, storage, *args, **kwargs)


def strategy(redirect_uri=None):
    def decorator(func):
        @wraps(func)
        def wrapper(self, backend=None, *args, **kwargs):
            uri = redirect_uri
            if uri and backend and '%(backend)s' in uri:
                uri = uri % {'backend': backend}
            self.strategy = load_strategy(request=web.ctx, backend=backend,
                                          redirect_uri=uri, *args, **kwargs)
            if backend:
                return func(self, backend=backend, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


def backends(user):
    """Load Social Auth current user data to context under the key 'backends'.
    Will return the output of social.backends.utils.user_backends_data."""
    return user_backends_data(user, get_helper('AUTHENTICATION_BACKENDS'),
                              get_helper('STORAGE', do_import=True))


def login_redirect():
    """Load current redirect to context."""
    method = web.ctx.method == 'POST' and 'post' or 'get'
    data = web.input(_method=method)
    value = data.get('next')
    return {
        'REDIRECT_FIELD_NAME': 'next',
        'REDIRECT_FIELD_VALUE': value,
        'REDIRECT_QUERYSTRING': value and ('next=' + value) or ''
    }

########NEW FILE########
__FILENAME__ = amazon
"""
Amazon OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/amazon.html
"""
from social.backends.oauth import BaseOAuth2


class AmazonOAuth2(BaseOAuth2):
    name = 'amazon'
    ID_KEY = 'user_id'
    AUTHORIZATION_URL = 'http://www.amazon.com/ap/oa'
    ACCESS_TOKEN_URL = 'https://api.amazon.com/auth/o2/token'
    DEFAULT_SCOPE = ['profile']
    REDIRECT_STATE = False
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [
        ('refresh_token', 'refresh_token', True),
        ('user_id', 'user_id'),
        ('postal_code', 'postal_code')
    ]

    def get_user_details(self, response):
        """Return user details from amazon account"""
        name = response.get('name') or ''
        fullname, first_name, last_name = self.get_user_names(name)
        return {'username': name,
                'email': response.get('email'),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Grab user profile information from amazon."""
        response = self.get_json('https://www.amazon.com/ap/user/profile',
                                 params={'access_token': access_token})
        if 'Profile' in response:
            response = {
                'user_id': response['Profile']['CustomerId'],
                'name': response['Profile']['Name'],
                'email': response['Profile']['PrimaryEmail']
            }
        return response

########NEW FILE########
__FILENAME__ = angel
"""
Angel OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/angel.html
"""
from social.backends.oauth import BaseOAuth2


class AngelOAuth2(BaseOAuth2):
    name = 'angel'
    AUTHORIZATION_URL = 'https://angel.co/api/oauth/authorize/'
    ACCESS_TOKEN_METHOD = 'POST'
    ACCESS_TOKEN_URL = 'https://angel.co/api/oauth/token/'
    REDIRECT_STATE = False
    STATE_PARAMETER = False

    def get_user_details(self, response):
        """Return user details from Angel account"""
        username = response['angellist_url'].split('/')[-1]
        email = response.get('email', '')
        fullname, first_name, last_name = self.get_user_names(response['name'])
        return {'username': username,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://api.angel.co/1/me/', params={
            'access_token': access_token
        })

########NEW FILE########
__FILENAME__ = aol
"""
AOL OpenId backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/aol.html
"""
from social.backends.open_id import OpenIdAuth


class AOLOpenId(OpenIdAuth):
    name = 'aol'
    URL = 'http://openid.aol.com'

########NEW FILE########
__FILENAME__ = appsfuel
"""
Appsfueld OAuth2 backend (with sandbox mode support), docs at:
    http://psa.matiasaguirre.net/docs/backends/appsfuel.html
"""
from social.backends.oauth import BaseOAuth2


class AppsfuelOAuth2(BaseOAuth2):
    name = 'appsfuel'
    ID_KEY = 'user_id'
    AUTHORIZATION_URL = 'http://app.appsfuel.com/content/permission'
    ACCESS_TOKEN_URL = 'https://api.appsfuel.com/v1/live/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    USER_DETAILS_URL = 'https://api.appsfuel.com/v1/live/user'

    def get_user_details(self, response):
        """Return user details from Appsfuel account"""
        email = response.get('email', '')
        username = email.split('@')[0] if email else ''
        fullname, first_name, last_name = self.get_user_names(
            response.get('display_name', '')
        )
        return {
            'username': username,
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(self.USER_DETAILS_URL, params={
            'access_token': access_token
        })


class AppsfuelOAuth2Sandbox(AppsfuelOAuth2):
    name = 'appsfuel-sandbox'
    AUTHORIZATION_URL = 'https://api.appsfuel.com/v1/sandbox/choose'
    ACCESS_TOKEN_URL = 'https://api.appsfuel.com/v1/sandbox/oauth/token'
    USER_DETAILS_URL = 'https://api.appsfuel.com/v1/sandbox/user'

########NEW FILE########
__FILENAME__ = base
from requests import request, ConnectionError

from social.utils import module_member, parse_qs
from social.exceptions import AuthFailed


class BaseAuth(object):
    """A django.contrib.auth backend that authenticates the user based on
    a authentication provider response"""
    name = ''  # provider name, it's stored in database
    supports_inactive_user = False  # Django auth
    ID_KEY = None
    EXTRA_DATA = None
    REQUIRES_EMAIL_VALIDATION = False

    def __init__(self, strategy=None, redirect_uri=None, *args, **kwargs):
        self.strategy = strategy
        self.redirect_uri = redirect_uri
        self.data = {}
        if strategy:
            self.data = self.strategy.request_data()
            self.redirect_uri = self.strategy.absolute_uri(
                self.redirect_uri
            )

    def setting(self, name, default=None):
        """Return setting value from strategy"""
        return self.strategy.setting(name, default=default, backend=self)

    def auth_url(self):
        """Must return redirect URL to auth provider"""
        raise NotImplementedError('Implement in subclass')

    def auth_html(self):
        """Must return login HTML content returned by provider"""
        raise NotImplementedError('Implement in subclass')

    def auth_complete(self, *args, **kwargs):
        """Completes loging process, must return user instance"""
        raise NotImplementedError('Implement in subclass')

    def process_error(self, data):
        """Process data for errors, raise exception if needed.
        Call this method on any override of auth_complete."""
        pass

    def authenticate(self, *args, **kwargs):
        """Authenticate user using social credentials

        Authentication is made if this is the correct backend, backend
        verification is made by kwargs inspection for current backend
        name presence.
        """
        # Validate backend and arguments. Require that the Social Auth
        # response be passed in as a keyword argument, to make sure we
        # don't match the username/password calling conventions of
        # authenticate.
        if 'backend' not in kwargs or kwargs['backend'].name != self.name or \
           'strategy' not in kwargs or 'response' not in kwargs:
            return None

        self.strategy = self.strategy or kwargs.get('strategy')
        self.redirect_uri = self.redirect_uri or kwargs.get('redirect_uri')
        self.data = self.strategy.request_data()
        pipeline = self.strategy.get_pipeline()
        kwargs.setdefault('is_new', False)
        if 'pipeline_index' in kwargs:
            pipeline = pipeline[kwargs['pipeline_index']:]
        return self.pipeline(pipeline, *args, **kwargs)

    def pipeline(self, pipeline, pipeline_index=0, *args, **kwargs):
        out = self.run_pipeline(pipeline, pipeline_index, *args, **kwargs)
        if not isinstance(out, dict):
            return out
        user = out.get('user')
        if user:
            user.social_user = out.get('social')
            user.is_new = out.get('is_new')
        return user

    def disconnect(self, *args, **kwargs):
        pipeline = self.strategy.get_disconnect_pipeline()
        if 'pipeline_index' in kwargs:
            pipeline = pipeline[kwargs['pipeline_index']:]
        kwargs['name'] = self.strategy.backend.name
        kwargs['user_storage'] = self.strategy.storage.user
        return self.run_pipeline(pipeline, *args, **kwargs)

    def run_pipeline(self, pipeline, pipeline_index=0, *args, **kwargs):
        out = kwargs.copy()
        out.setdefault('strategy', self.strategy)
        out.setdefault('backend', out.pop(self.name, None) or self)
        out.setdefault('request', self.strategy.request)

        for idx, name in enumerate(pipeline):
            out['pipeline_index'] = pipeline_index + idx
            func = module_member(name)
            result = func(*args, **out) or {}
            if not isinstance(result, dict):
                return result
            out.update(result)
        self.strategy.clean_partial_pipeline()
        return out

    def extra_data(self, user, uid, response, details):
        """Return deafault extra data to store in extra_data field"""
        data = {}
        for entry in (self.EXTRA_DATA or []) + self.setting('EXTRA_DATA', []):
            if not isinstance(entry, (list, tuple)):
                entry = (entry,)
            size = len(entry)
            if size >= 1 and size <= 3:
                if size == 3:
                    name, alias, discard = entry
                elif size == 2:
                    (name, alias), discard = entry, False
                elif size == 1:
                    name = alias = entry[0]
                    discard = False
                value = response.get(name) or details.get(name)
                if discard and not value:
                    continue
                data[alias] = value
        return data

    def auth_allowed(self, response, details):
        """Return True if the user should be allowed to authenticate, by
        default check if email is whitelisted (if there's a whitelist)"""
        emails = self.setting('WHITELISTED_EMAILS', [])
        domains = self.setting('WHITELISTED_DOMAINS', [])
        email = details.get('email')
        allowed = True
        if email and (emails or domains):
            domain = email.split('@', 1)[1]
            allowed = email in emails or domain in domains
        return allowed

    def get_user_id(self, details, response):
        """Return a unique ID for the current user, by default from server
        response."""
        return response.get(self.ID_KEY)

    def get_user_details(self, response):
        """Must return user details in a know internal struct:
            {'username': <username if any>,
             'email': <user email if any>,
             'fullname': <user full name if any>,
             'first_name': <user first name if any>,
             'last_name': <user last name if any>}
        """
        raise NotImplementedError('Implement in subclass')

    def get_user_names(self, fullname='', first_name='', last_name=''):
        # Avoid None values
        fullname = fullname or ''
        first_name = first_name or ''
        last_name = last_name or ''
        if fullname and not (first_name or last_name):
            try:
                first_name, last_name = fullname.split(' ', 1)
            except ValueError:
                first_name = first_name or fullname or ''
                last_name = last_name or ''
        fullname = fullname or ' '.join((first_name, last_name))
        return fullname.strip(), first_name.strip(), last_name.strip()

    def get_user(self, user_id):
        """
        Return user with given ID from the User model used by this backend.
        This is called by django.contrib.auth.middleware.
        """
        from social.strategies.utils import get_current_strategy
        strategy = self.strategy or get_current_strategy()
        return strategy.get_user(user_id)

    def continue_pipeline(self, *args, **kwargs):
        """Continue previous halted pipeline"""
        kwargs.update({'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def request_token_extra_arguments(self):
        """Return extra arguments needed on request-token process"""
        return self.setting('REQUEST_TOKEN_EXTRA_ARGUMENTS', {})

    def auth_extra_arguments(self):
        """Return extra arguments needed on auth process. The defaults can be
        overriden by GET parameters."""
        extra_arguments = self.setting('AUTH_EXTRA_ARGUMENTS', {}).copy()
        extra_arguments.update((key, self.data[key]) for key in extra_arguments
                                    if key in self.data)
        return extra_arguments

    def uses_redirect(self):
        """Return True if this provider uses redirect url method,
        otherwise return false."""
        return True

    def request(self, url, method='GET', *args, **kwargs):
        kwargs.setdefault('timeout', self.setting('REQUESTS_TIMEOUT') or
                                     self.setting('URLOPEN_TIMEOUT'))
        try:
            response = request(method, url, *args, **kwargs)
        except ConnectionError as err:
            raise AuthFailed(self, str(err))
        response.raise_for_status()
        return response

    def get_json(self, url, *args, **kwargs):
        return self.request(url, *args, **kwargs).json()

    def get_querystring(self, url, *args, **kwargs):
        return parse_qs(self.request(url, *args, **kwargs).text)

    def get_key_and_secret(self):
        """Return tuple with Consumer Key and Consumer Secret for current
        service provider. Must return (key, secret), order *must* be respected.
        """
        return self.setting('KEY'), self.setting('SECRET')

########NEW FILE########
__FILENAME__ = beats
"""
Beats backend, docs at:
    https://developer.beatsmusic.com/docs
"""
import base64

from requests import HTTPError

from social.exceptions import AuthCanceled, AuthUnknownError
from social.backends.oauth import BaseOAuth2


class BeatsOAuth2(BaseOAuth2):
    name = 'beats'
    SCOPE_SEPARATOR = ' '
    ID_KEY = 'user_context'
    AUTHORIZATION_URL = \
        'https://partner.api.beatsmusic.com/v1/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://partner.api.beatsmusic.com/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False

    def get_user_id(self, details, response):
        return response['result'][BeatsOAuth2.ID_KEY]

    def auth_headers(self):
        return {
            'Authorization': 'Basic {0}'.format(base64.urlsafe_b64encode(
                ('{0}:{1}'.format(*self.get_key_and_secret()).encode())
            ))
        }

    def auth_complete(self, *args, **kwargs):
        """Completes loging process, must return user instance"""
        self.process_error(self.data)
        try:
            response = self.request_access_token(
                self.ACCESS_TOKEN_URL,
                data=self.auth_complete_params(self.validate_state()),
                headers=self.auth_headers(),
                method=self.ACCESS_TOKEN_METHOD
            )
        except HTTPError as err:
            if err.response.status_code == 400:
                raise AuthCanceled(self)
            else:
                raise
        except KeyError:
            raise AuthUnknownError(self)
        self.process_error(response)
        # mashery wraps in jsonrpc
        if response.get('jsonrpc', None):
            response = response.get('result', None)
        return self.do_auth(response['access_token'], response=response,
                            *args, **kwargs)

    def get_user_details(self, response):
        """Return user details from Beats account"""
        response = response['result']
        fullname, first_name, last_name = self.get_user_names(
            response.get('display_name')
        )
        return {'username': response.get('id'),
                'email': response.get('email'),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://partner.api.beatsmusic.com/v1/api/me',
            headers={'Authorization': 'Bearer {0}'.format(access_token)}
        )

########NEW FILE########
__FILENAME__ = behance
"""
Behance OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/behance.html
"""
from social.backends.oauth import BaseOAuth2


class BehanceOAuth2(BaseOAuth2):
    """Behance OAuth authentication backend"""
    name = 'behance'
    AUTHORIZATION_URL = 'https://www.behance.net/v2/oauth/authenticate'
    ACCESS_TOKEN_URL = 'https://www.behance.net/v2/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = '|'
    EXTRA_DATA = [('username', 'username')]
    REDIRECT_STATE = False

    def get_user_id(self, details, response):
        return response['user']['id']

    def get_user_details(self, response):
        """Return user details from Behance account"""
        user = response['user']
        fullname, first_name, last_name = self.get_user_names(
            user['display_name'], user['first_name'], user['last_name']
        )
        return {'username': user['username'],
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': ''}

    def extra_data(self, user, uid, response, details):
        # Pull up the embedded user attributes so they can be found as extra
        # data. See the example token response for possible attributes:
        # http://www.behance.net/dev/authentication#step-by-step
        data = response.copy()
        data.update(response['user'])
        return super(BehanceOAuth2, self).extra_data(user, uid, data, details)

########NEW FILE########
__FILENAME__ = belgiumeid
"""
Belgium EID OpenId backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/belgium_eid.html
"""
from social.backends.open_id import OpenIdAuth


class BelgiumEIDOpenId(OpenIdAuth):
    """Belgium e-ID OpenID authentication backend"""
    name = 'belgiumeid'
    URL = 'https://www.e-contract.be/eid-idp/endpoints/openid/auth'

########NEW FILE########
__FILENAME__ = bitbucket
"""
Bitbucket OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/bitbucket.html
"""
from social.exceptions import AuthForbidden
from social.backends.oauth import BaseOAuth1


class BitbucketOAuth(BaseOAuth1):
    """Bitbucket OAuth authentication backend"""
    name = 'bitbucket'
    ID_KEY = 'username'
    AUTHORIZATION_URL = 'https://bitbucket.org/api/1.0/oauth/authenticate'
    REQUEST_TOKEN_URL = 'https://bitbucket.org/api/1.0/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://bitbucket.org/api/1.0/oauth/access_token'
    EXTRA_DATA = [
        ('username', 'username'),
        ('expires', 'expires'),
        ('email', 'email'),
        ('first_name', 'first_name'),
        ('last_name', 'last_name')
    ]

    def get_user_details(self, response):
        """Return user details from Bitbucket account"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response.get('first_name', ''),
            last_name=response.get('last_name', '')
        )
        return {'username': response.get('username') or '',
                'email': response.get('email') or '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token):
        """Return user data provided"""
        # Bitbucket has a bit of an indirect route to obtain user data from an
        # authenticated query: First obtain the user's email via an
        # authenticated GET, then retrieve the user's primary email address or
        # the top email
        emails = self.get_json('https://bitbucket.org/api/1.0/emails/',
                               auth=self.oauth_auth(access_token))
        email = None
        for address in reversed(emails):
            if address['active']:
                email = address['email']
                if address['primary']:
                    break

        if email:
            return dict(self.get_json('https://bitbucket.org/api/1.0/users/' +
                                      email)['user'],
                        email=email)
        elif self.setting('VERIFIED_EMAILS_ONLY', False):
            raise AuthForbidden(self,
                                'Bitbucket account has any verified email')
        else:
            return {}

########NEW FILE########
__FILENAME__ = box
"""
Box.net OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/box.html
"""
from social.backends.oauth import BaseOAuth2


class BoxOAuth2(BaseOAuth2):
    """Box.net OAuth authentication backend"""
    name = 'box'
    AUTHORIZATION_URL = 'https://www.box.com/api/oauth2/authorize'
    ACCESS_TOKEN_METHOD = 'POST'
    ACCESS_TOKEN_URL = 'https://www.box.com/api/oauth2/token'
    REVOKE_TOKEN_URL = 'https://www.box.com/api/oauth2/revoke'
    SCOPE_SEPARATOR = ','
    EXTRA_DATA = [
        ('refresh_token', 'refresh_token', True),
        ('id', 'id'),
        ('expires', 'expires'),
    ]

    def do_auth(self, access_token, response=None, *args, **kwargs):
        response = response or {}
        data = self.user_data(access_token)

        data['access_token'] = response.get('access_token')
        data['refresh_token'] = response.get('refresh_token')
        data['expires'] = response.get('expires_in')
        kwargs.update({'backend': self, 'response': data})
        return self.strategy.authenticate(*args, **kwargs)

    def get_user_details(self, response):
        """Return user details Box.net account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('name')
        )
        return {'username': response.get('login'),
                'email': response.get('login') or '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        params = self.setting('PROFILE_EXTRA_PARAMS', {})
        params['access_token'] = access_token
        return self.get_json('https://api.box.com/2.0/users/me',
                             params=params)

    def refresh_token(self, token, *args, **kwargs):
        params = self.refresh_token_params(token, *args, **kwargs)
        request = self.request(self.REFRESH_TOKEN_URL or self.ACCESS_TOKEN_URL,
                               data=params, headers=self.auth_headers(),
                               method='POST')
        return self.process_refresh_token_response(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = clef
"""
Clef OAuth support.

This contribution adds support for Clef OAuth service. The settings
SOCIAL_AUTH_CLEF_KEY and SOCIAL_AUTH_CLEF_SECRET must be defined with the
values given by Clef application registration process.
"""

from social.backends.oauth import BaseOAuth2


class ClefOAuth2(BaseOAuth2):
    """Clef OAuth authentication backend"""
    name = 'clef'
    AUTHORIZATION_URL = 'https://clef.io/iframes/qr'
    ACCESS_TOKEN_URL = 'https://clef.io/api/v1/authorize'
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','

    def auth_params(self, *args, **kwargs):
        params = super(ClefOAuth2, self).auth_params(*args, **kwargs)
        params['app_id'] = params.pop('client_id')
        params['redirect_url'] = params.pop('redirect_uri')
        return params

    def get_user_details(self, response):
        """Return user details from Github account"""
        info = response.get('info')
        fullname, first_name, last_name = self.get_user_names(
            first_name=info.get('first_name'),
            last_name=info.get('last_name')
        )
        return {
            'username': response.get('clef_id'),
            'email': info.get('email', ''),
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': info.get('phone_number', '')
        }

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json('https://clef.io/api/v1/info',
                             params={'access_token': access_token})

########NEW FILE########
__FILENAME__ = coinbase
"""
Coinbase OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/coinbase.html
"""
from social.backends.oauth import BaseOAuth2


class CoinbaseOAuth2(BaseOAuth2):
    name = 'coinbase'
    SCOPE_SEPARATOR = '+'
    DEFAULT_SCOPE = ['user', 'balance']
    AUTHORIZATION_URL = 'https://coinbase.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://coinbase.com/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False

    def get_user_id(self, details, response):
        return response['users'][0]['user']['id']

    def get_user_details(self, response):
        """Return user details from Coinbase account"""
        user_data = response['users'][0]['user']
        email = user_data.get('email', '')
        name = user_data['name']
        fullname, first_name, last_name = self.get_user_names(name)
        return {'username': name,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://coinbase.com/api/v1/users',
                             params={'access_token': access_token})

########NEW FILE########
__FILENAME__ = dailymotion
"""
DailyMotion OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/dailymotion.html
"""
from social.backends.oauth import BaseOAuth2


class DailymotionOAuth2(BaseOAuth2):
    """Dailymotion OAuth authentication backend"""
    name = 'dailymotion'
    EXTRA_DATA = [('id', 'id')]
    ID_KEY = 'username'
    AUTHORIZATION_URL = 'https://api.dailymotion.com/oauth/authorize'
    REQUEST_TOKEN_URL = 'https://api.dailymotion.com/oauth/token'
    ACCESS_TOKEN_URL = 'https://api.dailymotion.com/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'

    def get_user_details(self, response):
        return {'username': response.get('screenname')}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json('https://api.dailymotion.com/me/',
                             params={'access_token': access_token})

########NEW FILE########
__FILENAME__ = disqus
"""
Disqus OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/disqus.html
"""
from social.backends.oauth import BaseOAuth2


class DisqusOAuth2(BaseOAuth2):
    name = 'disqus'
    AUTHORIZATION_URL = 'https://disqus.com/api/oauth/2.0/authorize/'
    ACCESS_TOKEN_URL = 'https://disqus.com/api/oauth/2.0/access_token/'
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [
        ('avatar', 'avatar'),
        ('connections', 'connections'),
        ('user_id', 'user_id'),
        ('email', 'email'),
        ('email_hash', 'emailHash'),
        ('expires', 'expires'),
        ('location', 'location'),
        ('meta', 'response'),
        ('name', 'name'),
        ('username', 'username'),
    ]

    def get_user_id(self, details, response):
        return response['response']['id']

    def get_user_details(self, response):
        """Return user details from Disqus account"""
        rr = response.get('response', {})
        return {
            'username': rr.get('username', ''),
            'user_id': response.get('user_id', ''),
            'email': rr.get('email', ''),
            'name': rr.get('name', ''),
        }

    def extra_data(self, user, uid, response, details):
        meta_response = dict(response, **response.get('response', {}))
        return super(DisqusOAuth2, self).extra_data(user, uid, meta_response,
                     details)

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        key, secret = self.get_key_and_secret()
        return self.get_json(
            'https://disqus.com/api/3.0/users/details.json',
            params={'access_token': access_token, 'api_secret': secret}
        )

########NEW FILE########
__FILENAME__ = docker
"""
Docker.io OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/docker.html
"""
from social.backends.oauth import BaseOAuth2


class DockerOAuth2(BaseOAuth2):
    name = 'docker'
    ID_KEY = 'user_id'
    AUTHORIZATION_URL = 'https://www.docker.io/api/v1.1/o/authorize/'
    ACCESS_TOKEN_URL = 'https://www.docker.io/api/v1.1/o/token/'
    REFRESH_TOKEN_URL = 'https://www.docker.io/api/v1.1/o/token/'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('refresh_token', 'refresh_token', True),
        ('user_id', 'user_id'),
        ('email', 'email'),
        ('full_name', 'fullname'),
        ('location', 'location'),
        ('url', 'url'),
        ('company', 'company'),
        ('gravatar_email', 'gravatar_email'),
    ]

    def get_user_details(self, response):
        """Return user details from Docker.io account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('full_name') or response.get('username') or ''
        )
        return {
            'username': response.get('username'),
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name,
            'email': response.get('email', '')
        }

    def user_data(self, access_token, *args, **kwargs):
        """Grab user profile information from Docker.io."""
        username = kwargs['response']['username']
        return self.get_json(
            'https://www.docker.io/api/v1.1/users/%s/' % username,
            headers={'Authorization': 'Bearer %s' % access_token}
        )

########NEW FILE########
__FILENAME__ = douban
"""
Douban OAuth1 and OAuth2 backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/douban.html
"""
from social.backends.oauth import BaseOAuth2, BaseOAuth1


class DoubanOAuth(BaseOAuth1):
    """Douban OAuth authentication backend"""
    name = 'douban'
    EXTRA_DATA = [('id', 'id')]
    AUTHORIZATION_URL = 'http://www.douban.com/service/auth/authorize'
    REQUEST_TOKEN_URL = 'http://www.douban.com/service/auth/request_token'
    ACCESS_TOKEN_URL = 'http://www.douban.com/service/auth/access_token'

    def get_user_id(self, details, response):
        return response['db:uid']['$t']

    def get_user_details(self, response):
        """Return user details from Douban"""
        return {'username': response["db:uid"]["$t"],
                'email': ''}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json('http://api.douban.com/people/%40me?&alt=json',
                             auth=self.oauth_auth(access_token))


class DoubanOAuth2(BaseOAuth2):
    """Douban OAuth authentication backend"""
    name = 'douban-oauth2'
    AUTHORIZATION_URL = 'https://www.douban.com/service/auth2/auth'
    ACCESS_TOKEN_URL = 'https://www.douban.com/service/auth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('id', 'id'),
        ('uid', 'username'),
        ('refresh_token', 'refresh_token'),
    ]

    def get_user_details(self, response):
        """Return user details from Douban"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('name', '')
        )
        return {'username': response.get('uid', ''),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': ''}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json(
            'https://api.douban.com/v2/user/~me',
            headers={'Authorization': 'Bearer {0}'.format(access_token)}
        )

########NEW FILE########
__FILENAME__ = dropbox
"""
Dropbox OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/dropbox.html
"""
from social.backends.oauth import BaseOAuth1, BaseOAuth2


class DropboxOAuth(BaseOAuth1):
    """Dropbox OAuth authentication backend"""
    name = 'dropbox'
    ID_KEY = 'uid'
    AUTHORIZATION_URL = 'https://www.dropbox.com/1/oauth/authorize'
    REQUEST_TOKEN_URL = 'https://api.dropbox.com/1/oauth/request_token'
    REQUEST_TOKEN_METHOD = 'POST'
    ACCESS_TOKEN_URL = 'https://api.dropbox.com/1/oauth/access_token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_URI_PARAMETER_NAME = 'oauth_callback'
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Dropbox account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('display_name')
        )
        return {'username': str(response.get('uid')),
                'email': response.get('email'),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://api.dropbox.com/1/account/info',
                             auth=self.oauth_auth(access_token))


class DropboxOAuth2(BaseOAuth2):
    name = 'dropbox-oauth2'
    ID_KEY = 'uid'
    AUTHORIZATION_URL = 'https://www.dropbox.com/1/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://api.dropbox.com/1/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('uid', 'username'),
    ]

    def get_user_details(self, response):
        """Return user details from Dropbox account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('display_name')
        )
        return {'username': str(response.get('uid')),
                'email': response.get('email'),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://api.dropbox.com/1/account/info',
            headers={'Authorization': 'Bearer {0}'.format(access_token)}
        )

########NEW FILE########
__FILENAME__ = email
"""
Legacy Email backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/email.html
"""
from social.backends.legacy import LegacyAuth


class EmailAuth(LegacyAuth):
    name = 'email'
    ID_KEY = 'email'
    REQUIRES_EMAIL_VALIDATION = True
    EXTRA_DATA = ['email']

########NEW FILE########
__FILENAME__ = evernote
"""
Evernote OAuth1 backend (with sandbox mode support), docs at:
    http://psa.matiasaguirre.net/docs/backends/evernote.html
"""
from requests import HTTPError

from social.exceptions import AuthCanceled
from social.backends.oauth import BaseOAuth1


class EvernoteOAuth(BaseOAuth1):
    """
    Evernote OAuth authentication backend.

    Possible Values:
       {'edam_expires': ['1367525289541'],
        'edam_noteStoreUrl': [
            'https://sandbox.evernote.com/shard/s1/notestore'
        ],
        'edam_shard': ['s1'],
        'edam_userId': ['123841'],
        'edam_webApiUrlPrefix': ['https://sandbox.evernote.com/shard/s1/'],
        'oauth_token': [
            'S=s1:U=1e3c1:E=13e66dbee45:C=1370f2ac245:P=185:A=my_user:' \
            'H=411443c5e8b20f8718ed382a19d4ae38'
        ]}
    """
    name = 'evernote'
    ID_KEY = 'edam_userId'
    AUTHORIZATION_URL = 'https://www.evernote.com/OAuth.action'
    REQUEST_TOKEN_URL = 'https://www.evernote.com/oauth'
    ACCESS_TOKEN_URL = 'https://www.evernote.com/oauth'
    EXTRA_DATA = [
        ('access_token', 'access_token'),
        ('oauth_token', 'oauth_token'),
        ('edam_noteStoreUrl', 'store_url'),
        ('edam_expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Evernote account"""
        return {'username': response['edam_userId'],
                'email': ''}

    def access_token(self, token):
        """Return request for access token value"""
        try:
            return self.get_querystring(self.ACCESS_TOKEN_URL,
                                        auth=self.oauth_auth(token))
        except HTTPError as err:
            # Evernote returns a 401 error when AuthCanceled
            if err.response.status_code == 401:
                raise AuthCanceled(self)
            else:
                raise

    def extra_data(self, user, uid, response, details=None):
        data = super(EvernoteOAuth, self).extra_data(user, uid, response,
                                                     details)
        # Evernote returns expiration timestamp in miliseconds, so it needs to
        # be normalized.
        if 'expires' in data:
            data['expires'] = int(data['expires']) / 1000
        return data

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return access_token.copy()


class EvernoteSandboxOAuth(EvernoteOAuth):
    name = 'evernote-sandbox'
    AUTHORIZATION_URL = 'https://sandbox.evernote.com/OAuth.action'
    REQUEST_TOKEN_URL = 'https://sandbox.evernote.com/oauth'
    ACCESS_TOKEN_URL = 'https://sandbox.evernote.com/oauth'

########NEW FILE########
__FILENAME__ = exacttarget
"""
ExactTarget OAuth support.
Support Authentication from IMH using JWT token and pre-shared key.
Requires package pyjwt
"""
from datetime import timedelta, datetime

import jwt

from social.exceptions import AuthFailed, AuthCanceled
from social.backends.oauth import BaseOAuth2


class ExactTargetOAuth2(BaseOAuth2):
    name = 'exacttarget'

    def get_user_details(self, response):
        """Use the email address of the user, suffixed by _et"""
        user = response.get('token', {})\
                       .get('request', {})\
                       .get('user', {})
        if 'email' in user:
            user['username'] = user['email']
        return user

    def uses_redirect(self):
        return False

    def auth_url(self):
        return None

    def process_error(self, data):
        if data.get('error'):
            error = self.data.get('error_description') or self.data['error']
            raise AuthFailed(self, error)

    def do_auth(self, token, *args, **kwargs):
        dummy, secret = self.get_key_and_secret()
        try:  # Decode the token, using the Application Signature from settings
            decoded = jwt.decode(token, secret)
        except jwt.DecodeError:  # Wrong signature, fail authentication
            raise AuthCanceled(self)
        kwargs.update({'response': {'token': decoded}, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance"""
        token = self.data.get('jwt', {})
        if not token:
            raise AuthFailed(self, 'Authentication Failed')
        return self.do_auth(token, *args, **kwargs)

    def extra_data(self, user, uid, response, details):
        """Load extra details from the JWT token"""
        data = {
            'id': details.get('id'),
            'email': details.get('email'),
            # OAuth token, for use with legacy SOAP API calls:
            #   http://bit.ly/13pRHfo
            'internalOauthToken': details.get('internalOauthToken'),
            # Token for use with the Application ClientID for the FUEL API
            'oauthToken': details.get('oauthToken'),
            # If the token has expired, use the FUEL API to get a new token see
            # http://bit.ly/10v1K5l and http://bit.ly/11IbI6F - set legacy=1
            'refreshToken': details.get('refreshToken'),
        }

        # The expiresIn value determines how long the tokens are valid for.
        # Take a bit off, then convert to an int timestamp
        expiresSeconds = details.get('expiresIn', 0) - 30
        expires = datetime.utcnow() + timedelta(seconds=expiresSeconds)
        data['expires'] = (expires - datetime(1970, 1, 1)).total_seconds()

        if response.get('token'):
            token = response['token']
            org = token.get('request', {}).get('organization')
            if org:
                data['stack'] = org.get('stackKey')
                data['enterpriseId'] = org.get('enterpriseId')
        return data

########NEW FILE########
__FILENAME__ = facebook
"""
Facebook OAuth2 and Canvas Application backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/facebook.html
"""
import hmac
import time
import json
import base64
import hashlib

from social.utils import parse_qs, constant_time_compare
from social.backends.oauth import BaseOAuth2
from social.exceptions import AuthException, AuthCanceled, AuthUnknownError, \
                              AuthMissingParameter


class FacebookOAuth2(BaseOAuth2):
    """Facebook OAuth2 authentication backend"""
    name = 'facebook'
    RESPONSE_TYPE = None
    SCOPE_SEPARATOR = ','
    AUTHORIZATION_URL = 'https://www.facebook.com/dialog/oauth'
    ACCESS_TOKEN_URL = 'https://graph.facebook.com/oauth/access_token'
    REVOKE_TOKEN_URL = 'https://graph.facebook.com/{uid}/permissions'
    REVOKE_TOKEN_METHOD = 'DELETE'
    USER_DATA_URL = 'https://graph.facebook.com/me'
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Facebook account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('name', ''),
            response.get('first_name', ''),
            response.get('last_name', '')
        )
        return {'username': response.get('username', response.get('name')),
                'email': response.get('email', ''),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        params = self.setting('PROFILE_EXTRA_PARAMS', {})
        params['access_token'] = access_token
        return self.get_json(self.USER_DATA_URL, params=params)

    def process_error(self, data):
        super(FacebookOAuth2, self).process_error(data)
        if data.get('error_code'):
            raise AuthCanceled(self, data.get('error_message') or
                                     data.get('error_code'))

    def auth_complete(self, *args, **kwargs):
        """Completes loging process, must return user instance"""
        self.process_error(self.data)
        if not self.data.get('code'):
            raise AuthMissingParameter(self, 'code')
        state = self.validate_state()
        key, secret = self.get_key_and_secret()
        url = self.ACCESS_TOKEN_URL
        response = self.get_querystring(url, params={
            'client_id': key,
            'redirect_uri': self.get_redirect_uri(state),
            'client_secret': secret,
            'code': self.data['code']
        })
        access_token = response['access_token']
        return self.do_auth(access_token, response, *args, **kwargs)

    def process_refresh_token_response(self, response, *args, **kwargs):
        return parse_qs(response.content)

    def refresh_token_params(self, token, *args, **kwargs):
        client_id, client_secret = self.get_key_and_secret()
        return {
            'fb_exchange_token': token,
            'grant_type': 'fb_exchange_token',
            'client_id': client_id,
            'client_secret': client_secret
        }

    def do_auth(self, access_token, response=None, *args, **kwargs):
        response = response or {}

        data = self.user_data(access_token)

        if not isinstance(data, dict):
            # From time to time Facebook responds back a JSON with just
            # False as value, the reason is still unknown, but since the
            # data is needed (it contains the user ID used to identify the
            # account on further logins), this app cannot allow it to
            # continue with the auth process.
            raise AuthUnknownError(self, 'An error ocurred while retrieving '
                                         'users Facebook data')

        data['access_token'] = access_token
        if 'expires' in response:
            data['expires'] = response['expires']
        kwargs.update({'backend': self, 'response': data})
        return self.strategy.authenticate(*args, **kwargs)

    def revoke_token_url(self, token, uid):
        return self.REVOKE_TOKEN_URL.format(uid=uid)

    def revoke_token_params(self, token, uid):
        return {'access_token': token}

    def process_revoke_token_response(self, response):
        return super(FacebookOAuth2, self).process_revoke_token_response(
            response
        ) and response.content == 'true'


class FacebookAppOAuth2(FacebookOAuth2):
    """Facebook Application Authentication support"""
    name = 'facebook-app'

    def uses_redirect(self):
        return False

    def auth_complete(self, *args, **kwargs):
        access_token = None
        response = {}

        if 'signed_request' in self.data:
            key, secret = self.get_key_and_secret()
            response = self.load_signed_request(self.data['signed_request'])
            if not 'user_id' in response and not 'oauth_token' in response:
                raise AuthException(self)

            if response is not None:
                access_token = response.get('access_token') or \
                               response.get('oauth_token') or \
                               self.data.get('access_token')

        if access_token is None:
            if self.data.get('error') == 'access_denied':
                raise AuthCanceled(self)
            else:
                raise AuthException(self)
        return self.do_auth(access_token, response, *args, **kwargs)

    def auth_html(self):
        key, secret = self.get_key_and_secret()
        namespace = self.setting('NAMESPACE', None)
        scope = self.setting('SCOPE', '')
        if scope:
            scope = self.SCOPE_SEPARATOR.join(scope)
        ctx = {
            'FACEBOOK_APP_NAMESPACE': namespace or key,
            'FACEBOOK_KEY': key,
            'FACEBOOK_EXTENDED_PERMISSIONS': scope,
            'FACEBOOK_COMPLETE_URI': self.redirect_uri,
        }
        tpl = self.setting('LOCAL_HTML', 'facebook.html')
        return self.strategy.render_html(tpl=tpl, context=ctx)

    def load_signed_request(self, signed_request):
        def base64_url_decode(data):
            data = data.encode('ascii')
            data += '=' * (4 - (len(data) % 4))
            return base64.urlsafe_b64decode(data)

        key, secret = self.get_key_and_secret()
        try:
            sig, payload = signed_request.split('.', 1)
        except ValueError:
            pass  # ignore if can't split on dot
        else:
            sig = base64_url_decode(sig)
            data = json.loads(base64_url_decode(payload))
            expected_sig = hmac.new(secret, msg=payload,
                                    digestmod=hashlib.sha256).digest()
            # allow the signed_request to function for upto 1 day
            if constant_time_compare(sig, expected_sig) and \
               data['issued_at'] > (time.time() - 86400):
                return data


class Facebook2OAuth2(FacebookOAuth2):
    """Facebook OAuth2 authentication backend using Facebook Open Graph 2.0"""
    AUTHORIZATION_URL = 'https://www.facebook.com/v2.0/dialog/oauth'
    ACCESS_TOKEN_URL = 'https://graph.facebook.com/v2.0/oauth/access_token'
    REVOKE_TOKEN_URL = 'https://graph.facebook.com/v2.0/{uid}/permissions'
    USER_DATA_URL = 'https://graph.facebook.com/v2.0/me'


class Facebook2AppOAuth2(Facebook2OAuth2, FacebookAppOAuth2):
    pass

########NEW FILE########
__FILENAME__ = fedora
"""
Fedora OpenId backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/fedora.html
"""
from social.backends.open_id import OpenIdAuth


class FedoraOpenId(OpenIdAuth):
    name = 'fedora'
    URL = 'https://id.fedoraproject.org'
    USERNAME_KEY = 'nickname'

########NEW FILE########
__FILENAME__ = fitbit
"""
Fitbit OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/fitbit.html
"""
from social.backends.oauth import BaseOAuth1


class FitbitOAuth(BaseOAuth1):
    """Fitbit OAuth authentication backend"""
    name = 'fitbit'
    AUTHORIZATION_URL = 'https://api.fitbit.com/oauth/authorize'
    REQUEST_TOKEN_URL = 'https://api.fitbit.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.fitbit.com/oauth/access_token'
    ID_KEY = 'encodedId'
    EXTRA_DATA = [('encodedId', 'id'),
                  ('displayName', 'username')]

    def get_user_details(self, response):
        """Return user details from Fitbit account"""
        return {'username': response.get('displayName'),
                'email': ''}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://api.fitbit.com/1/user/-/profile.json',
            auth=self.oauth_auth(access_token)
        )['user']

########NEW FILE########
__FILENAME__ = flickr
"""
Flickr OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/flickr.html
"""
from social.backends.oauth import BaseOAuth1


class FlickrOAuth(BaseOAuth1):
    """Flickr OAuth authentication backend"""
    name = 'flickr'
    AUTHORIZATION_URL = 'https://www.flickr.com/services/oauth/authorize'
    REQUEST_TOKEN_URL = 'https://www.flickr.com/services/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://www.flickr.com/services/oauth/access_token'
    EXTRA_DATA = [
        ('id', 'id'),
        ('username', 'username'),
        ('expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Flickr account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('fullname')
        )
        return {'username': response.get('username') or response.get('id'),
                'email': '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return {
            'id': access_token['user_nsid'],
            'username': access_token['username'],
            'fullname': access_token.get('fullname', ''),
        }

    def auth_extra_arguments(self):
        params = super(FlickrOAuth, self).auth_extra_arguments() or {}
        if not 'perms' in params:
            params['perms'] = 'read'
        return params

########NEW FILE########
__FILENAME__ = foursquare
"""
Foursquare OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/foursquare.html
"""
from social.backends.oauth import BaseOAuth2


class FoursquareOAuth2(BaseOAuth2):
    name = 'foursquare'
    AUTHORIZATION_URL = 'https://foursquare.com/oauth2/authenticate'
    ACCESS_TOKEN_URL = 'https://foursquare.com/oauth2/access_token'
    ACCESS_TOKEN_METHOD = 'POST'
    API_VERSION = '20140128'

    def get_user_id(self, details, response):
        return response['response']['user']['id']

    def get_user_details(self, response):
        """Return user details from Foursquare account"""
        info = response['response']['user']
        email = info['contact']['email']
        fullname, first_name, last_name = self.get_user_names(
            first_name=info.get('firstName', ''),
            last_name=info.get('lastName', '')
        )
        return {'username': first_name + ' ' + last_name,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://api.foursquare.com/v2/users/self',
                             params={'oauth_token': access_token,
                                     'v': self.API_VERSION})

########NEW FILE########
__FILENAME__ = gae
"""
Google App Engine support using User API
"""
from __future__ import absolute_import

from google.appengine.api import users

from social.backends.base import BaseAuth
from social.exceptions import AuthException


class GoogleAppEngineAuth(BaseAuth):
    """GoogleAppengine authentication backend"""
    name = 'google-appengine'

    def get_user_id(self, details, response):
        """Return current user id."""
        user = users.get_current_user()
        if user:
            return user.user_id()

    def get_user_details(self, response):
        """Return user basic information (id and email only)."""
        user = users.get_current_user()
        return {'username': user.user_id(),
                'email': user.email(),
                'fullname': '',
                'first_name': '',
                'last_name': ''}

    def auth_url(self):
        """Build and return complete URL."""
        return users.create_login_url(self.redirect_uri)

    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance."""
        if not users.get_current_user():
            raise AuthException('Authentication error')
        kwargs.update({'response': '', 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

########NEW FILE########
__FILENAME__ = github
"""
Github OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/github.html
"""
from requests import HTTPError

from social.exceptions import AuthFailed
from social.backends.oauth import BaseOAuth2


class GithubOAuth2(BaseOAuth2):
    """Github OAuth authentication backend"""
    name = 'github'
    AUTHORIZATION_URL = 'https://github.com/login/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'
    SCOPE_SEPARATOR = ','
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Github account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('name')
        )
        return {'username': response.get('login'),
                'email': response.get('email') or '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        data = self._user_data(access_token)
        if not data.get('email'):
            try:
                email = self._user_data(access_token, '/emails')[0]
            except (HTTPError, IndexError, ValueError, TypeError):
                email = ''

            if isinstance(email, dict):
                email = email.get('email', '')
            data['email'] = email
        return data

    def _user_data(self, access_token, path=None):
        url = 'https://api.github.com/user{0}'.format(path or '')
        return self.get_json(url, params={'access_token': access_token})


class GithubOrganizationOAuth2(GithubOAuth2):
    """Github OAuth2 authentication backend for organizations"""
    name = 'github-org'

    def get_user_details(self, response):
        """Return user details from Github account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('name')
        )
        return {'username': response.get('login'),
                'email': response.get('email') or '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        user_data = super(GithubOrganizationOAuth2, self).user_data(
            access_token, *args, **kwargs
        )
        url = 'https://api.github.com/orgs/{org}/members/{username}'\
                    .format(org=self.setting('NAME'),
                            username=user_data.get('login'))
        try:
            self.request(url, params={'access_token': access_token})
        except HTTPError as err:
            # if the user is a member of the organization, response code
            # will be 204, see http://bit.ly/ZS6vFl
            if err.response.status_code != 204:
                raise AuthFailed(self,
                                 'User doesn\'t belong to the organization')
        return user_data

########NEW FILE########
__FILENAME__ = google
"""
Google OpenId, OAuth2, OAuth1, Google+ Sign-in backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/google.html
"""
from requests import HTTPError

from social.backends.open_id import OpenIdAuth
from social.backends.oauth import BaseOAuth2, BaseOAuth1
from social.exceptions import AuthMissingParameter, AuthCanceled


class BaseGoogleAuth(object):
    def get_user_id(self, details, response):
        """Use google email as unique id"""
        if self.setting('USE_UNIQUE_USER_ID', False):
            return response['id']
        else:
            return details['email']

    def get_user_details(self, response):
        """Return user details from Google API account"""
        if response.get('emails'):
            email = response['emails'][0]['value']
        elif response.get('email'):
            email = response['email']
        else:
            email = ''

        names = response.get('name') or {}
        fullname, first_name, last_name = self.get_user_names(
            response.get('displayName', ''),
            names.get('givenName', ''),
            names.get('familyName', '')
        )
        return {'username': email.split('@', 1)[0],
                'email': email,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}


class BaseGoogleOAuth2API(BaseGoogleAuth):
    def user_data(self, access_token, *args, **kwargs):
        """Return user data from Google API"""
        return self.get_json(
            'https://www.googleapis.com/plus/v1/people/me',
            params={'access_token': access_token, 'alt': 'json'}
        )


class GoogleOAuth2(BaseGoogleOAuth2API, BaseOAuth2):
    """Google OAuth2 authentication backend"""
    name = 'google-oauth2'
    REDIRECT_STATE = False
    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/auth'
    ACCESS_TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REVOKE_TOKEN_URL = 'https://accounts.google.com/o/oauth2/revoke'
    REVOKE_TOKEN_METHOD = 'GET'
    DEFAULT_SCOPE = ['email', 'profile']
    EXTRA_DATA = [
        ('refresh_token', 'refresh_token', True),
        ('expires_in', 'expires'),
        ('token_type', 'token_type', True)
    ]

    def revoke_token_params(self, token, uid):
        return {'token': token}

    def revoke_token_headers(self, token, uid):
        return {'Content-type': 'application/json'}


class GooglePlusAuth(BaseGoogleOAuth2API, BaseOAuth2):
    name = 'google-plus'
    REDIRECT_STATE = False
    STATE_PARAMETER = False
    ACCESS_TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REVOKE_TOKEN_URL = 'https://accounts.google.com/o/oauth2/revoke'
    REVOKE_TOKEN_METHOD = 'GET'
    DEFAULT_SCOPE = ['plus.login', 'email']
    EXTRA_DATA = [
        ('id', 'user_id'),
        ('refresh_token', 'refresh_token', True),
        ('expires_in', 'expires'),
        ('access_type', 'access_type', True),
        ('code', 'code')
    ]

    def auth_complete_params(self, state=None):
        params = super(GooglePlusAuth, self).auth_complete_params(state)
        params['redirect_uri'] = 'postmessage'
        return params

    def auth_complete(self, *args, **kwargs):
        token = self.data.get('access_token')
        if not token:
            raise AuthMissingParameter(self, 'access_token')

        self.process_error(self.get_json(
            'https://www.googleapis.com/oauth2/v1/tokeninfo',
            params={'access_token': token}
        ))

        try:
            response = self.request_access_token(
                self.ACCESS_TOKEN_URL,
                data=self.auth_complete_params(),
                headers=self.auth_headers(),
                method=self.ACCESS_TOKEN_METHOD
            )
        except HTTPError as err:
            if err.response.status_code == 400:
                raise AuthCanceled(self)
            else:
                raise
        self.process_error(response)
        return self.do_auth(response['access_token'], response=response,
                            *args, **kwargs)


class GoogleOAuth(BaseGoogleAuth, BaseOAuth1):
    """Google OAuth authorization mechanism"""
    name = 'google-oauth'
    AUTHORIZATION_URL = 'https://www.google.com/accounts/OAuthAuthorizeToken'
    REQUEST_TOKEN_URL = 'https://www.google.com/accounts/OAuthGetRequestToken'
    ACCESS_TOKEN_URL = 'https://www.google.com/accounts/OAuthGetAccessToken'
    DEFAULT_SCOPE = ['https://www.googleapis.com/auth/userinfo#email']

    def user_data(self, access_token, *args, **kwargs):
        """Return user data from Google API"""
        return self.get_querystring(
            'https://www.googleapis.com/userinfo/email',
            auth=self.oauth_auth(access_token)
        )

    def get_key_and_secret(self):
        """Return Google OAuth Consumer Key and Consumer Secret pair, uses
        anonymous by default, beware that this marks the application as not
        registered and a security badge is displayed on authorization page.
        http://code.google.com/apis/accounts/docs/OAuth_ref.html#SigningOAuth
        """
        key_secret = super(GoogleOAuth, self).get_key_and_secret()
        if key_secret == (None, None):
            key_secret = ('anonymous', 'anonymous')
        return key_secret


class GoogleOpenId(OpenIdAuth):
    name = 'google'
    URL = 'https://www.google.com/accounts/o8/id'

    def get_user_id(self, details, response):
        """
        Return user unique id provided by service. For google user email
        is unique enought to flag a single user. Email comes from schema:
        http://axschema.org/contact/email
        """
        return details['email']

########NEW FILE########
__FILENAME__ = instagram
"""
Instagram OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/instagram.html
"""
from social.backends.oauth import BaseOAuth2


class InstagramOAuth2(BaseOAuth2):
    name = 'instagram'
    AUTHORIZATION_URL = 'https://instagram.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://instagram.com/oauth/access_token'
    ACCESS_TOKEN_METHOD = 'POST'

    def get_user_id(self, details, response):
        return response['user']['id']

    def get_user_details(self, response):
        """Return user details from Instagram account"""
        username = response['user']['username']
        email = response['user'].get('email', '')
        fullname, first_name, last_name = self.get_user_names(
            response['user'].get('full_name', '')
        )
        return {'username': username,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://api.instagram.com/v1/users/self',
                             params={'access_token': access_token})

########NEW FILE########
__FILENAME__ = jawbone
"""
Jawbone OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/jawbone.html
"""
from social.backends.oauth import BaseOAuth2
from social.exceptions import AuthCanceled, AuthUnknownError


class JawboneOAuth2(BaseOAuth2):
    name = 'jawbone'
    AUTHORIZATION_URL = 'https://jawbone.com/auth/oauth2/auth'
    ACCESS_TOKEN_URL = 'https://jawbone.com/auth/oauth2/token'
    SCOPE_SEPARATOR = ' '
    REDIRECT_STATE = False

    def get_user_id(self, details, response):
        return response['data']['xid']

    def get_user_details(self, response):
        """Return user details from Jawbone account"""
        data = response['data']
        fullname, first_name, last_name = self.get_user_names(
            first_name=data.get('first', ''),
            last_name=data.get('last', '')
        )
        return {
            'username': first_name + ' ' + last_name,
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name,
            'dob': data.get('dob', ''),
            'gender': data.get('gender', ''),
            'height': data.get('height', ''),
            'weight': data.get('weight', '')
        }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://jawbone.com/nudge/api/users/@me',
            headers={'Authorization': 'Bearer ' + access_token},
        )

    def process_error(self, data):
        error = data.get('error')
        if error:
            if error == 'access_denied':
                raise AuthCanceled(self)
            else:
                raise AuthUnknownError(self, 'Jawbone error was {0}'.format(
                    error
                ))
        return super(JawboneOAuth2, self).process_error(data)

########NEW FILE########
__FILENAME__ = kakao
"""
Kakao OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/kakao.html
"""
from social.backends.oauth import BaseOAuth2


class KakaoOAuth2(BaseOAuth2):
    """Kakao OAuth authentication backend"""
    name = 'kakao'
    AUTHORIZATION_URL = 'https://kauth.kakao.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://kauth.kakao.com/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'

    def get_user_id(self, details, response):
        return response['id']

    def get_user_details(self, response):
        """Return user details from Kakao account"""
        nickname = response['properties']['nickname']
        thumbnail_image = response['properties']['thumbnail_image']
        profile_image = response['properties']['profile_image']
        return {
            'username': nickname,
            'email': '',
            'fullname': '',
            'first_name': '',
            'last_name': ''
        }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://kapi.kakao.com/v1/user/me',
                             params={'access_token': access_token})

########NEW FILE########
__FILENAME__ = lastfm
import hashlib

from social.backends.base import BaseAuth


class LastFmAuth(BaseAuth):
    """
    Last.Fm authentication backend. Requires two settings:
        SOCIAL_AUTH_LASTFM_KEY
        SOCIAL_AUTH_LASTFM_SECRET

    Don't forget to set the Last.fm callback to something sensible like
        http://your.site/lastfm/complete
    """
    name = 'lastfm'
    AUTH_URL = 'http://www.last.fm/api/auth/?api_key={api_key}'
    EXTRA_DATA = [
        ('key', 'session_key')
    ]

    def auth_url(self):
        return self.AUTH_URL.format(api_key=self.setting('KEY'))

    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance"""
        key, secret = self.get_key_and_secret()
        token = self.data['token']

        signature = hashlib.md5(''.join(
            ('api_key', key, 'methodauth.getSession', 'token', token, secret)
        ).encode()).hexdigest()

        response = self.get_json('http://ws.audioscrobbler.com/2.0/', data={
            'method': 'auth.getSession',
            'api_key': key,
            'token': token,
            'api_sig': signature,
            'format': 'json'
        }, method='POST')

        kwargs.update({'response': response['session'], 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def get_user_id(self, details, response):
        """Return a unique ID for the current user, by default from server
        response."""
        return response.get('name')

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(response['name'])
        return {
            'username': response['name'],
            'email': '',
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name
        }

########NEW FILE########
__FILENAME__ = legacy
from social.backends.base import BaseAuth
from social.exceptions import AuthMissingParameter


class LegacyAuth(BaseAuth):
    def get_user_id(self, details, response):
        return details.get(self.ID_KEY) or \
               response.get(self.ID_KEY)

    def auth_url(self):
        return self.setting('FORM_URL')

    def auth_html(self):
        return self.strategy.render_html(tpl=self.setting('FORM_HTML'))

    def uses_redirect(self):
        return self.setting('FORM_URL') and not \
               self.setting('FORM_HTML')

    def auth_complete(self, *args, **kwargs):
        """Completes loging process, must return user instance"""
        if self.ID_KEY not in self.data:
            raise AuthMissingParameter(self, self.ID_KEY)
        kwargs.update({'response': self.data, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def get_user_details(self, response):
        """Return user details"""
        email = response.get('email', '')
        username = response.get('username', '')
        fullname, first_name, last_name = self.get_user_names(
            response.get('fullname', ''),
            response.get('first_name', ''),
            response.get('last_name', '')
        )
        if email and not username:
            username = email.split('@', 1)[0]
        return {
            'username': username,
            'email': email,
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name
        }

########NEW FILE########
__FILENAME__ = linkedin
"""
LinkedIn OAuth1 and OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/linkedin.html
"""
from social.backends.oauth import BaseOAuth1, BaseOAuth2


class BaseLinkedinAuth(object):
    EXTRA_DATA = [('id', 'id'),
                  ('first-name', 'first_name', True),
                  ('last-name', 'last_name', True),
                  ('firstName', 'first_name', True),
                  ('lastName', 'last_name', True)]
    USER_DETAILS = 'https://api.linkedin.com/v1/people/~:({0})'

    def get_user_details(self, response):
        """Return user details from Linkedin account"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response['firstName'],
            last_name=response['lastName']
        )
        email = response.get('emailAddress', '')
        return {'username': first_name + last_name,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_details_url(self):
        # use set() since LinkedIn fails when values are duplicated
        fields_selectors = list(set(['first-name', 'id', 'last-name'] +
                                self.setting('FIELD_SELECTORS', [])))
        # user sort to ease the tests URL mocking
        fields_selectors.sort()
        fields_selectors = ','.join(fields_selectors)
        return self.USER_DETAILS.format(fields_selectors)

    def user_data_headers(self):
        lang = self.setting('FORCE_PROFILE_LANGUAGE')
        if lang:
            return {
                'Accept-Language': lang if lang is not True
                                        else self.strategy.get_language()
            }


class LinkedinOAuth(BaseLinkedinAuth, BaseOAuth1):
    """Linkedin OAuth authentication backend"""
    name = 'linkedin'
    SCOPE_SEPARATOR = '+'
    AUTHORIZATION_URL = 'https://www.linkedin.com/uas/oauth/authenticate'
    REQUEST_TOKEN_URL = 'https://api.linkedin.com/uas/oauth/requestToken'
    ACCESS_TOKEN_URL = 'https://api.linkedin.com/uas/oauth/accessToken'

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json(
            self.user_details_url(),
            params={'format': 'json'},
            auth=self.oauth_auth(access_token),
            headers=self.user_data_headers()
        )

    def unauthorized_token(self):
        """Makes first request to oauth. Returns an unauthorized Token."""
        scope = self.get_scope() or ''
        if scope:
            scope = '?scope=' + self.SCOPE_SEPARATOR.join(scope)
        return self.request(self.REQUEST_TOKEN_URL + scope,
                            params=self.request_token_extra_arguments(),
                            auth=self.oauth_auth()).content


class LinkedinOAuth2(BaseLinkedinAuth, BaseOAuth2):
    name = 'linkedin-oauth2'
    SCOPE_SEPARATOR = ' '
    AUTHORIZATION_URL = 'https://www.linkedin.com/uas/oauth2/authorization'
    ACCESS_TOKEN_URL = 'https://www.linkedin.com/uas/oauth2/accessToken'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json(
            self.user_details_url(),
            params={'oauth2_access_token': access_token,
                    'format': 'json'},
            headers=self.user_data_headers()
        )

    def request_access_token(self, *args, **kwargs):
        # LinkedIn expects a POST request with querystring parameters, despite
        # the spec http://tools.ietf.org/html/rfc6749#section-4.1.3
        kwargs['params'] = kwargs.pop('data')
        return super(LinkedinOAuth2, self).request_access_token(
            *args, **kwargs
        )

########NEW FILE########
__FILENAME__ = live
"""
Live OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/live.html
"""
from social.backends.oauth import BaseOAuth2


class LiveOAuth2(BaseOAuth2):
    name = 'live'
    AUTHORIZATION_URL = 'https://login.live.com/oauth20_authorize.srf'
    ACCESS_TOKEN_URL = 'https://login.live.com/oauth20_token.srf'
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','
    DEFAULT_SCOPE = ['wl.basic', 'wl.emails']
    EXTRA_DATA = [
        ('id', 'id'),
        ('access_token', 'access_token'),
        ('authentication_token', 'authentication_token'),
        ('refresh_token', 'refresh_token'),
        ('expires_in', 'expires'),
        ('email', 'email'),
        ('first_name', 'first_name'),
        ('last_name', 'last_name'),
        ('token_type', 'token_type'),
    ]

    def get_user_details(self, response):
        """Return user details from Live Connect account"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response.get('first_name'),
            last_name=response.get('last_name')
        )
        return {'username': response.get('name'),
                'email': response.get('emails', {}).get('account', ''),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://apis.live.net/v5.0/me', params={
            'access_token': access_token
        })

########NEW FILE########
__FILENAME__ = livejournal
"""
LiveJournal OpenId backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/livejournal.html
"""
from social.p3 import urlsplit
from social.backends.open_id import OpenIdAuth
from social.exceptions import AuthMissingParameter


class LiveJournalOpenId(OpenIdAuth):
    """LiveJournal OpenID authentication backend"""
    name = 'livejournal'

    def get_user_details(self, response):
        """Generate username from identity url"""
        values = super(LiveJournalOpenId, self).get_user_details(response)
        values['username'] = values.get('username') or \
                             urlsplit(response.identity_url)\
                                .netloc.split('.', 1)[0]
        return values

    def openid_url(self):
        """Returns LiveJournal authentication URL"""
        if not self.data.get('openid_lj_user'):
            raise AuthMissingParameter(self, 'openid_lj_user')
        return 'http://{0}.livejournal.com'.format(self.data['openid_lj_user'])

########NEW FILE########
__FILENAME__ = loginradius
"""
LoginRadius BaseOAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/loginradius.html
"""
from social.backends.oauth import BaseOAuth2


class LoginRadiusAuth(BaseOAuth2):
    """LoginRadius BaseOAuth2 authentication backend."""
    name = 'loginradius'
    ID_KEY = 'ID'
    ACCESS_TOKEN_URL = 'https://api.loginradius.com/api/v2/access_token'
    PROFILE_URL = 'https://api.loginradius.com/api/v2/userprofile'
    ACCESS_TOKEN_METHOD = 'GET'
    REDIRECT_STATE = False
    STATE_PARAMETER = False

    def uses_redirect(self):
        """Return False because we return HTML instead."""
        return False

    def auth_html(self):
        key, secret = self.get_key_and_secret()
        tpl = self.setting('TEMPLATE', 'loginradius.html')
        return self.strategy.render_html(tpl=tpl, context={
            'backend': self,
            'LOGINRADIUS_KEY': key,
            'LOGINRADIUS_REDIRECT_URL': self.get_redirect_uri()
        })

    def request_access_token(self, *args, **kwargs):
        return self.get_json(params={
            'token': self.data.get('token'),
            'secret': self.setting('SECRET')
        }, *args, **kwargs)

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service. Implement in subclass."""
        return self.get_json(
            self.PROFILE_URL,
            params={'access_token': access_token},
            data=self.auth_complete_params(self.validate_state()),
            headers=self.auth_headers(),
            method=self.ACCESS_TOKEN_METHOD
        )

    def get_user_details(self, response):
        """Must return user details in a know internal struct:
            {'username': <username if any>,
             'email': <user email if any>,
             'fullname': <user full name if any>,
             'first_name': <user first name if any>,
             'last_name': <user last name if any>}
        """
        profile = {
            'username': response['NickName'] or '',
            'email': response['Email'][0]['Value'] or '',
            'fullname': response['FullName'] or '',
            'first_name': response['FirstName'] or '',
            'last_name': response['LastName'] or ''
        }
        return profile

    def get_user_id(self, details, response):
        """Return a unique ID for the current user, by default from server
        response. Since LoginRadius handles multiple providers, we need to
        distinguish them to prevent conflicts."""
        return '{0}-{1}'.format(response.get('Provider'),
                                response.get(self.ID_KEY))

########NEW FILE########
__FILENAME__ = mailru
"""
Mail.ru OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/mailru.html
"""
from hashlib import md5

from social.p3 import unquote
from social.backends.oauth import BaseOAuth2


class MailruOAuth2(BaseOAuth2):
    """Mail.ru authentication backend"""
    name = 'mailru-oauth2'
    ID_KEY = 'uid'
    AUTHORIZATION_URL = 'https://connect.mail.ru/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://connect.mail.ru/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [('refresh_token', 'refresh_token'),
                  ('expires_in', 'expires')]

    def get_user_details(self, response):
        """Return user details from Mail.ru request"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=unquote(response['first_name']),
            last_name=unquote(response['last_name'])
        )
        return {'username': unquote(response['nick']),
                'email': unquote(response['email']),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data from Mail.ru REST API"""
        key, secret = self.get_key_and_secret()
        data = {'method': 'users.getInfo',
                'session_key': access_token,
                'app_id': key,
                'secure': '1'}
        param_list = sorted(list(item + '=' + data[item] for item in data))
        data['sig'] = md5(
            (''.join(param_list) + secret).encode('utf-8')
        ).hexdigest()
        return self.get_json('http://www.appsmail.ru/platform/api',
                             params=data)[0]

########NEW FILE########
__FILENAME__ = mapmyfitness
"""
MapMyFitness OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/mapmyfitness.html
"""
from social.backends.oauth import BaseOAuth2


class MapMyFitnessOAuth2(BaseOAuth2):
    """MapMyFitness OAuth authentication backend"""
    name = 'mapmyfitness'
    AUTHORIZATION_URL = 'https://www.mapmyfitness.com/v7.0/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://oauth2-api.mapmyapi.com/v7.0/oauth2/access_token'
    REQUEST_TOKEN_METHOD = 'POST'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('refresh_token', 'refresh_token'),
    ]

    def auth_headers(self):
        key = self.get_key_and_secret()[0]
        return {
            'Api-Key': key
        }

    def get_user_id(self, details, response):
        return response['id']

    def get_user_details(self, response):
        first = response.get('first_name', '')
        last = response.get('last_name', '')
        full = (first + last).strip()
        return {
            'username': response['username'],
            'email': response['email'],
            'fullname': full,
            'first_name': first,
            'last_name': last,
        }

    def user_data(self, access_token, *args, **kwargs):
        key = self.get_key_and_secret()[0]
        url = 'https://oauth2-api.mapmyapi.com/v7.0/user/self/'
        headers = {
            'Authorization': 'Bearer {0}'.format(access_token),
            'Api-Key': key
        }
        return self.get_json(url, headers=headers)        

########NEW FILE########
__FILENAME__ = mendeley
"""
Mendeley OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/mendeley.html
"""
from social.backends.oauth import BaseOAuth1, BaseOAuth2


class MendeleyMixin(object):
    SCOPE_SEPARATOR = '+'
    EXTRA_DATA = [('profile_id', 'profile_id'),
                  ('name', 'name'),
                  ('bio', 'bio')]

    def get_user_id(self, details, response):
        return response['main']['profile_id']

    def get_user_details(self, response):
        """Return user details from Mendeley account"""
        profile_id = response['main']['profile_id']
        name = response['main']['name']
        bio = response['main']['bio']
        return {'profile_id': profile_id,
                'name': name,
                'bio': bio}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        values = self.get_user_data(access_token)
        values.update(values['main'])
        return values

    def get_user_data(self, access_token):
        raise NotImplementedError('Implement in subclass')


class MendeleyOAuth(MendeleyMixin, BaseOAuth1):
    name = 'mendeley'
    AUTHORIZATION_URL = 'http://api.mendeley.com/oauth/authorize/'
    REQUEST_TOKEN_URL = 'http://api.mendeley.com/oauth/request_token/'
    ACCESS_TOKEN_URL = 'http://api.mendeley.com/oauth/access_token/'

    def get_user_data(self, access_token):
        return self.get_json(
            'http://api.mendeley.com/oapi/profiles/info/me/',
            auth=self.oauth_auth(access_token)
        )


class MendeleyOAuth2(MendeleyMixin, BaseOAuth2):
    name = 'mendeley-oauth2'
    AUTHORIZATION_URL = 'https://api-oauth2.mendeley.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://api-oauth2.mendeley.com/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    DEFAULT_SCOPE = ['all']
    REDIRECT_STATE = False
    EXTRA_DATA = MendeleyMixin.EXTRA_DATA + [
        ('refresh_token', 'refresh_token'),
        ('expires_in', 'expires_in'),
        ('token_type', 'token_type'),
    ]

    def get_user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://api-oauth2.mendeley.com/oapi/profiles/info/me/',
            headers={'Authorization': 'Bearer {0}'.format(access_token)}
        )

########NEW FILE########
__FILENAME__ = mixcloud
"""
Mixcloud OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/mixcloud.html
"""
from social.backends.oauth import BaseOAuth2


class MixcloudOAuth2(BaseOAuth2):
    name = 'mixcloud'
    ID_KEY = 'username'
    AUTHORIZATION_URL = 'https://www.mixcloud.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://www.mixcloud.com/oauth/access_token'
    ACCESS_TOKEN_METHOD = 'POST'

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(response['name'])
        return {'username': response['username'],
                'email': None,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json('https://api.mixcloud.com/me/',
                             params={'access_token': access_token,
                                     'alt': 'json'})

########NEW FILE########
__FILENAME__ = oauth
import six

from requests import HTTPError
from requests_oauthlib import OAuth1
from oauthlib.oauth1 import SIGNATURE_TYPE_AUTH_HEADER

from social.p3 import urlencode, unquote
from social.utils import url_add_parameters, parse_qs
from social.exceptions import AuthFailed, AuthCanceled, AuthUnknownError, \
                              AuthMissingParameter, AuthStateMissing, \
                              AuthStateForbidden, AuthTokenError
from social.backends.base import BaseAuth


class OAuthAuth(BaseAuth):
    """OAuth authentication backend base class.

    Also settings will be inspected to get more values names that should be
    stored on extra_data field. Setting name is created from current backend
    name (all uppercase) plus _EXTRA_DATA.

    access_token is always stored.
    """
    SCOPE_PARAMETER_NAME = 'scope'
    DEFAULT_SCOPE = None
    SCOPE_SEPARATOR = ' '
    ID_KEY = 'id'
    ACCESS_TOKEN_METHOD = 'GET'
    REVOKE_TOKEN_URL = None
    REVOKE_TOKEN_METHOD = 'POST'

    def extra_data(self, user, uid, response, details=None):
        """Return access_token and extra defined names to store in
        extra_data field"""
        data = super(OAuthAuth, self).extra_data(user, uid, response, details)
        data['access_token'] = response.get('access_token', '')
        return data

    def get_scope(self):
        """Return list with needed access scope"""
        scope = self.setting('SCOPE', [])
        if not self.setting('IGNORE_DEFAULT_SCOPE', False):
            scope += self.DEFAULT_SCOPE or []
        return scope

    def get_scope_argument(self):
        param = {}
        scope = self.get_scope()
        if scope:
            param[self.SCOPE_PARAMETER_NAME] = self.SCOPE_SEPARATOR.join(scope)
        return param

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service. Implement in subclass"""
        return {}

    def revoke_token_url(self, token, uid):
        return self.REVOKE_TOKEN_URL

    def revoke_token_params(self, token, uid):
        return {}

    def revoke_token_headers(self, token, uid):
        return {}

    def process_revoke_token_response(self, response):
        return response.status_code == 200

    def revoke_token(self, token, uid):
        if self.REVOKE_TOKEN_URL:
            url = self.revoke_token_url(token, uid)
            params = self.revoke_token_params(token, uid)
            headers = self.revoke_token_headers(token, uid)
            data = urlencode(params) if self.REVOKE_TOKEN_METHOD != 'GET' \
                                     else None
            response = self.request(url, params=params, headers=headers,
                                    data=data, method=self.REVOKE_TOKEN_METHOD)
            return self.process_revoke_token_response(response)


class BaseOAuth1(OAuthAuth):
    """Consumer based mechanism OAuth authentication, fill the needed
    parameters to communicate properly with authentication service.

        AUTHORIZATION_URL       Authorization service url
        REQUEST_TOKEN_URL       Request token URL
        ACCESS_TOKEN_URL        Access token URL
    """
    AUTHORIZATION_URL = ''
    REQUEST_TOKEN_URL = ''
    REQUEST_TOKEN_METHOD = 'GET'
    OAUTH_TOKEN_PARAMETER_NAME = 'oauth_token'
    REDIRECT_URI_PARAMETER_NAME = 'redirect_uri'
    ACCESS_TOKEN_URL = ''
    UNATHORIZED_TOKEN_SUFIX = 'unauthorized_token_name'

    def auth_url(self):
        """Return redirect url"""
        token = self.set_unauthorized_token()
        return self.oauth_authorization_request(token)

    def process_error(self, data):
        if 'oauth_problem' in data:
            if data['oauth_problem'] == 'user_refused':
                raise AuthCanceled(self, 'User refused the access')
            raise AuthUnknownError(self, 'Error was ' + data['oauth_problem'])

    def auth_complete(self, *args, **kwargs):
        """Return user, might be logged in"""
        # Multiple unauthorized tokens are supported (see #521)
        self.process_error(self.data)
        token = self.get_unauthorized_token()
        try:
            access_token = self.access_token(token)
        except HTTPError as err:
            if err.response.status_code == 400:
                raise AuthCanceled(self)
            else:
                raise
        return self.do_auth(access_token, *args, **kwargs)

    def do_auth(self, access_token, *args, **kwargs):
        """Finish the auth process once the access_token was retrieved"""
        if not isinstance(access_token, dict):
            access_token = parse_qs(access_token)
        data = self.user_data(access_token)
        if data is not None and 'access_token' not in data:
            data['access_token'] = access_token
        kwargs.update({'response': data, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def get_unauthorized_token(self):
        name = self.name + self.UNATHORIZED_TOKEN_SUFIX
        unauthed_tokens = self.strategy.session_get(name, [])
        if not unauthed_tokens:
            raise AuthTokenError(self, 'Missing unauthorized token')

        data_token = self.data.get(self.OAUTH_TOKEN_PARAMETER_NAME)

        if data_token is None:
            raise AuthTokenError(self, 'Missing unauthorized token')

        token = None
        for utoken in unauthed_tokens:
            orig_utoken = utoken
            if not isinstance(utoken, dict):
                utoken = parse_qs(utoken)
            if utoken.get(self.OAUTH_TOKEN_PARAMETER_NAME) == data_token:
                self.strategy.session_set(name, list(set(unauthed_tokens) -
                                                     set([orig_utoken])))
                token = utoken
                break
        else:
            raise AuthTokenError(self, 'Incorrect tokens')
        return token

    def set_unauthorized_token(self):
        token = self.unauthorized_token()
        name = self.name + self.UNATHORIZED_TOKEN_SUFIX
        tokens = self.strategy.session_get(name, []) + [token]
        self.strategy.session_set(name, tokens)
        return token

    def unauthorized_token(self):
        """Return request for unauthorized token (first stage)"""
        params = self.request_token_extra_arguments()
        params.update(self.get_scope_argument())
        key, secret = self.get_key_and_secret()
        # decoding='utf-8' produces errors with python-requests on Python3
        # since the final URL will be of type bytes
        decoding = None if six.PY3 else 'utf-8'
        response = self.request(self.REQUEST_TOKEN_URL,
                                params=params,
                                auth=OAuth1(key, secret,
                                            callback_uri=self.redirect_uri,
                                            decoding=decoding),
                                method=self.REQUEST_TOKEN_METHOD)
        content = response.content
        if response.encoding or response.apparent_encoding:
            content = content.decode(response.encoding or
                                     response.apparent_encoding)
        else:
            content = response.content.decode()
        return content

    def oauth_authorization_request(self, token):
        """Generate OAuth request to authorize token."""
        if not isinstance(token, dict):
            token = parse_qs(token)
        params = self.auth_extra_arguments() or {}
        params.update(self.get_scope_argument())
        params[self.OAUTH_TOKEN_PARAMETER_NAME] = token.get(
            self.OAUTH_TOKEN_PARAMETER_NAME
        )
        params[self.REDIRECT_URI_PARAMETER_NAME] = self.redirect_uri
        return self.AUTHORIZATION_URL + '?' + urlencode(params)

    def oauth_auth(self, token=None, oauth_verifier=None,
                   signature_type=SIGNATURE_TYPE_AUTH_HEADER):
        key, secret = self.get_key_and_secret()
        oauth_verifier = oauth_verifier or self.data.get('oauth_verifier')
        token = token or {}
        # decoding='utf-8' produces errors with python-requests on Python3
        # since the final URL will be of type bytes
        decoding = None if six.PY3 else 'utf-8'
        return OAuth1(key, secret,
                      resource_owner_key=token.get('oauth_token'),
                      resource_owner_secret=token.get('oauth_token_secret'),
                      callback_uri=self.redirect_uri,
                      verifier=oauth_verifier,
                      signature_type=signature_type,
                      decoding=decoding)

    def oauth_request(self, token, url, params=None, method='GET'):
        """Generate OAuth request, setups callback url"""
        return self.request(url, method=method, params=params,
                            auth=self.oauth_auth(token))

    def access_token(self, token):
        """Return request for access token value"""
        return self.get_querystring(self.ACCESS_TOKEN_URL,
                                    auth=self.oauth_auth(token),
                                    method=self.ACCESS_TOKEN_METHOD)


class BaseOAuth2(OAuthAuth):
    """Base class for OAuth2 providers.

    OAuth2 draft details at:
        http://tools.ietf.org/html/draft-ietf-oauth-v2-10

    Attributes:
        AUTHORIZATION_URL       Authorization service url
        ACCESS_TOKEN_URL        Token URL
    """
    AUTHORIZATION_URL = None
    ACCESS_TOKEN_URL = None
    REFRESH_TOKEN_URL = None
    REFRESH_TOKEN_METHOD = 'POST'
    RESPONSE_TYPE = 'code'
    REDIRECT_STATE = True
    STATE_PARAMETER = True

    def state_token(self):
        """Generate csrf token to include as state parameter."""
        return self.strategy.random_string(32)

    def get_redirect_uri(self, state=None):
        """Build redirect with redirect_state parameter."""
        uri = self.redirect_uri
        if self.REDIRECT_STATE and state:
            uri = url_add_parameters(uri, {'redirect_state': state})
        return uri

    def auth_params(self, state=None):
        client_id, client_secret = self.get_key_and_secret()
        params = {
            'client_id': client_id,
            'redirect_uri': self.get_redirect_uri(state)
        }
        if self.STATE_PARAMETER and state:
            params['state'] = state
        if self.RESPONSE_TYPE:
            params['response_type'] = self.RESPONSE_TYPE
        return params

    def auth_url(self):
        """Return redirect url"""
        if self.STATE_PARAMETER or self.REDIRECT_STATE:
            # Store state in session for further request validation. The state
            # value is passed as state parameter (as specified in OAuth2 spec),
            # but also added to redirect, that way we can still verify the
            # request if the provider doesn't implement the state parameter.
            # Reuse token if any.
            name = self.name + '_state'
            state = self.strategy.session_get(name)
            if state is None:
                state = self.state_token()
                self.strategy.session_set(name, state)
        else:
            state = None

        params = self.auth_params(state)
        params.update(self.get_scope_argument())
        params.update(self.auth_extra_arguments())
        params = urlencode(params)
        if not self.REDIRECT_STATE:
            # redirect_uri matching is strictly enforced, so match the
            # providers value exactly.
            params = unquote(params)
        return self.AUTHORIZATION_URL + '?' + params

    def validate_state(self):
        """Validate state value. Raises exception on error, returns state
        value if valid."""
        if not self.STATE_PARAMETER and not self.REDIRECT_STATE:
            return None
        state = self.strategy.session_get(self.name + '_state')
        request_state = self.data.get('state') or \
                        self.data.get('redirect_state')
        if request_state and isinstance(request_state, list):
            request_state = request_state[0]

        if not request_state:
            raise AuthMissingParameter(self, 'state')
        elif not state:
            raise AuthStateMissing(self, 'state')
        elif not request_state == state:
            raise AuthStateForbidden(self)
        else:
            return state

    def auth_complete_params(self, state=None):
        client_id, client_secret = self.get_key_and_secret()
        return {
            'grant_type': 'authorization_code',  # request auth code
            'code': self.data.get('code', ''),  # server response code
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': self.get_redirect_uri(state)
        }

    def auth_headers(self):
        return {'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'}

    def request_access_token(self, *args, **kwargs):
        return self.get_json(*args, **kwargs)

    def process_error(self, data):
        if data.get('error'):
            if data['error'] == 'denied' or data['error'] == 'access_denied':
                raise AuthCanceled(self, data.get('error_description', ''))
            raise AuthFailed(self, data.get('error_description') or
                                   data['error'])
        elif 'denied' in data:
            raise AuthCanceled(self, data['denied'])

    def auth_complete(self, *args, **kwargs):
        """Completes loging process, must return user instance"""
        self.process_error(self.data)
        try:
            response = self.request_access_token(
                self.ACCESS_TOKEN_URL,
                data=self.auth_complete_params(self.validate_state()),
                headers=self.auth_headers(),
                method=self.ACCESS_TOKEN_METHOD
            )
        except HTTPError as err:
            if err.response.status_code == 400:
                raise AuthCanceled(self)
            else:
                raise
        except KeyError:
            raise AuthUnknownError(self)
        self.process_error(response)
        return self.do_auth(response['access_token'], response=response,
                            *args, **kwargs)

    def do_auth(self, access_token, *args, **kwargs):
        """Finish the auth process once the access_token was retrieved"""
        data = self.user_data(access_token, *args, **kwargs)
        response = kwargs.get('response') or {}
        response.update(data or {})
        kwargs.update({'response': response, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def refresh_token_params(self, token, *args, **kwargs):
        client_id, client_secret = self.get_key_and_secret()
        return {
            'refresh_token': token,
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret
        }

    def process_refresh_token_response(self, response, *args, **kwargs):
        return response.json()

    def refresh_token(self, token, *args, **kwargs):
        params = self.refresh_token_params(token, *args, **kwargs)
        url = self.REFRESH_TOKEN_URL or self.ACCESS_TOKEN_URL
        method = self.REFRESH_TOKEN_METHOD
        key = 'params' if method == 'GET' else 'data'
        request_args = {'headers': self.auth_headers(),
                        'method': method,
                        key: params}
        request = self.request(url, **request_args)
        return self.process_refresh_token_response(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = odnoklassniki
"""
Odnoklassniki OAuth2 and Iframe Application backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/odnoklassnikiru.html
"""
from hashlib import md5

from social.p3 import unquote
from social.backends.base import BaseAuth
from social.backends.oauth import BaseOAuth2
from social.exceptions import AuthFailed


class OdnoklassnikiOAuth2(BaseOAuth2):
    """Odnoklassniki authentication backend"""
    name = 'odnoklassniki-oauth2'
    ID_KEY = 'uid'
    ACCESS_TOKEN_METHOD = 'POST'
    AUTHORIZATION_URL = 'http://www.odnoklassniki.ru/oauth/authorize'
    ACCESS_TOKEN_URL = 'http://api.odnoklassniki.ru/oauth/token.do'
    EXTRA_DATA = [('refresh_token', 'refresh_token'),
                  ('expires_in', 'expires')]

    def get_user_details(self, response):
        """Return user details from Odnoklassniki request"""
        fullname, first_name, last_name = self.get_user_names(
            fullname=unquote(response['name']),
            first_name=unquote(response['first_name']),
            last_name=unquote(response['last_name'])
        )
        return {
            'username': response['uid'],
            'email': '',
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name
        }

    def user_data(self, access_token, *args, **kwargs):
        """Return user data from Odnoklassniki REST API"""
        data = {'access_token': access_token, 'method': 'users.getCurrentUser'}
        key, secret = self.get_key_and_secret()
        public_key = self.setting('PUBLIC_NAME')
        return odnoklassniki_api(self, data, 'http://api.odnoklassniki.ru/',
                                 public_key, secret, 'oauth')


class OdnoklassnikiApp(BaseAuth):
    """Odnoklassniki iframe app authentication backend"""
    name = 'odnoklassniki-app'
    ID_KEY = 'uid'

    def extra_data(self, user, uid, response, details):
        return dict([(key, value) for key, value in response.items()
                            if key in response['extra_data_list']])

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(
            fullname=unquote(response['name']),
            first_name=unquote(response['first_name']),
            last_name=unquote(response['last_name'])
        )
        return {
            'username': response['uid'],
            'email': '',
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name
        }

    def auth_complete(self, request, user, *args, **kwargs):
        self.verify_auth_sig()
        response = self.get_response()
        fields = ('uid', 'first_name', 'last_name', 'name') + \
                 self.setting('EXTRA_USER_DATA_LIST', ())
        data = {
            'method': 'users.getInfo',
            'uids': '{0}'.format(response['logged_user_id']),
            'fields': ','.join(fields),
        }
        client_key, client_secret = self.get_key_and_secret()
        public_key = self.setting('PUBLIC_NAME')
        details = odnoklassniki_api(self, data, response['api_server'],
                                    public_key, client_secret,
                                    'iframe_nosession')
        if len(details) == 1 and 'uid' in details[0]:
            details = details[0]
            auth_data_fields = self.setting('EXTRA_AUTH_DATA_LIST',
                                            ('api_server', 'apiconnection',
                                             'session_key', 'authorized',
                                             'session_secret_key'))

            for field in auth_data_fields:
                details[field] = response[field]
            details['extra_data_list'] = fields + auth_data_fields
            kwargs.update({'backend': self, 'response': details})
        else:
            raise AuthFailed(self, 'Cannot get user details: API error')
        return self.strategy.authenticate(*args, **kwargs)

    def get_auth_sig(self):
        secret_key = self.setting('SECRET')
        hash_source = '{0:s}{1:s}{2:s}'.format(self.data['logged_user_id'],
                                               self.data['session_key'],
                                               secret_key)
        return md5(hash_source.encode('utf-8')).hexdigest()

    def get_response(self):
        fields = ('logged_user_id', 'api_server', 'application_key',
                  'session_key', 'session_secret_key', 'authorized',
                  'apiconnection')
        return dict((name, self.data[name]) for name in fields
                        if name in self.data)

    def verify_auth_sig(self):
        correct_key = self.get_auth_sig()
        key = self.data['auth_sig'].lower()
        if correct_key != key:
            raise AuthFailed(self, 'Wrong authorization key')


def odnoklassniki_oauth_sig(data, client_secret):
    """
    Calculates signature of request data access_token value must be included
    Algorithm is described at
        http://dev.odnoklassniki.ru/wiki/pages/viewpage.action?pageId=12878032,
    search for "little bit different way"
    """
    suffix = md5(
        '{0:s}{1:s}'.format(data['access_token'],
                            client_secret).encode('utf-8')
    ).hexdigest()
    check_list = sorted(['{0:s}={1:s}'.format(key, value)
                            for key, value in data.items()
                                if key != 'access_token'])
    return md5((''.join(check_list) + suffix).encode('utf-8')).hexdigest()


def odnoklassniki_iframe_sig(data, client_secret_or_session_secret):
    """
    Calculates signature as described at:
        http://dev.odnoklassniki.ru/wiki/display/ok/
            Authentication+and+Authorization
    If API method requires session context, request is signed with session
    secret key. Otherwise it is signed with application secret key
    """
    param_list = sorted(['{0:s}={1:s}'.format(key, value)
                            for key, value in data.items()])
    return md5(
        (''.join(param_list) + client_secret_or_session_secret).encode('utf-8')
    ).hexdigest()


def odnoklassniki_api(backend, data, api_url, public_key, client_secret,
                      request_type='oauth'):
    """Calls Odnoklassniki REST API method
    http://dev.odnoklassniki.ru/wiki/display/ok/Odnoklassniki+Rest+API"""
    data.update({
        'application_key': public_key,
        'format': 'JSON'
    })
    if request_type == 'oauth':
        data['sig'] = odnoklassniki_oauth_sig(data, client_secret)
    elif request_type == 'iframe_session':
        data['sig'] = odnoklassniki_iframe_sig(data,
                                               data['session_secret_key'])
    elif request_type == 'iframe_nosession':
        data['sig'] = odnoklassniki_iframe_sig(data, client_secret)
    else:
        msg = 'Unknown request type {0}. How should it be signed?'
        raise AuthFailed(backend, msg.format(request_type))
    return backend.get_json(api_url + 'fb.do', params=data)

########NEW FILE########
__FILENAME__ = openstreetmap
"""
OpenStreetMap OAuth support.

This adds support for OpenStreetMap OAuth service. An application must be
registered first on OpenStreetMap and the settings
SOCIAL_AUTH_OPENSTREETMAP_KEY and SOCIAL_AUTH_OPENSTREETMAP_SECRET
must be defined with the corresponding values.

More info: http://wiki.openstreetmap.org/wiki/OAuth
"""
from xml.dom import minidom

from social.backends.oauth import BaseOAuth1


class OpenStreetMapOAuth(BaseOAuth1):
    """OpenStreetMap OAuth authentication backend"""
    name = 'openstreetmap'
    AUTHORIZATION_URL = 'http://www.openstreetmap.org/oauth/authorize'
    REQUEST_TOKEN_URL = 'http://www.openstreetmap.org/oauth/request_token'
    ACCESS_TOKEN_URL = 'http://www.openstreetmap.org/oauth/access_token'
    EXTRA_DATA = [
        ('id', 'id'),
        ('avatar', 'avatar'),
        ('account_created', 'account_created')
    ]

    def get_user_details(self, response):
        """Return user details from OpenStreetMap account"""
        return {
            'username': response['username'],
            'email': '',
            'fullname': '',
            'first_name': '',
            'last_name': ''
        }

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        response = self.oauth_request(
            access_token, 'http://api.openstreetmap.org/api/0.6/user/details'
        )
        try:
            dom = minidom.parseString(response.content)
        except ValueError:
            return None
        user = dom.getElementsByTagName('user')[0]
        try:
            avatar = dom.getElementsByTagName('img')[0].getAttribute('href')
        except IndexError:
            avatar = None
        return {
            'id': user.getAttribute('id'),
            'username': user.getAttribute('display_name'),
            'account_created': user.getAttribute('account_created'),
            'avatar': avatar
        }

########NEW FILE########
__FILENAME__ = open_id
from openid.consumer.consumer import Consumer, SUCCESS, CANCEL, FAILURE
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import sreg, ax, pape

from social.utils import url_add_parameters
from social.exceptions import AuthException, AuthFailed, AuthCanceled, \
                              AuthUnknownError, AuthMissingParameter
from social.backends.base import BaseAuth


# OpenID configuration
OLD_AX_ATTRS = [
    ('http://schema.openid.net/contact/email', 'old_email'),
    ('http://schema.openid.net/namePerson', 'old_fullname'),
    ('http://schema.openid.net/namePerson/friendly', 'old_nickname')
]
AX_SCHEMA_ATTRS = [
    # Request both the full name and first/last components since some
    # providers offer one but not the other.
    ('http://axschema.org/contact/email', 'email'),
    ('http://axschema.org/namePerson', 'fullname'),
    ('http://axschema.org/namePerson/first', 'first_name'),
    ('http://axschema.org/namePerson/last', 'last_name'),
    ('http://axschema.org/namePerson/friendly', 'nickname'),
]
SREG_ATTR = [
    ('email', 'email'),
    ('fullname', 'fullname'),
    ('nickname', 'nickname')
]
OPENID_ID_FIELD = 'openid_identifier'
SESSION_NAME = 'openid'


class OpenIdAuth(BaseAuth):
    """Generic OpenID authentication backend"""
    name = 'openid'
    URL = None
    USERNAME_KEY = 'username'

    def get_user_id(self, details, response):
        """Return user unique id provided by service"""
        return response.identity_url

    def get_ax_attributes(self):
        attrs = self.setting('AX_SCHEMA_ATTRS', [])
        if attrs and self.setting('IGNORE_DEFAULT_AX_ATTRS', True):
            return attrs
        return attrs + AX_SCHEMA_ATTRS + OLD_AX_ATTRS

    def get_sreg_attributes(self):
        return self.setting('SREG_ATTR') or SREG_ATTR

    def values_from_response(self, response, sreg_names=None, ax_names=None):
        """Return values from SimpleRegistration response or
        AttributeExchange response if present.

        @sreg_names and @ax_names must be a list of name and aliases
        for such name. The alias will be used as mapping key.
        """
        values = {}

        # Use Simple Registration attributes if provided
        if sreg_names:
            resp = sreg.SRegResponse.fromSuccessResponse(response)
            if resp:
                values.update((alias, resp.get(name) or '')
                                    for name, alias in sreg_names)

        # Use Attribute Exchange attributes if provided
        if ax_names:
            resp = ax.FetchResponse.fromSuccessResponse(response)
            if resp:
                for src, alias in ax_names:
                    name = alias.replace('old_', '')
                    values[name] = resp.getSingle(src, '') or values.get(name)
        return values

    def get_user_details(self, response):
        """Return user details from an OpenID request"""
        values = {'username': '', 'email': '', 'fullname': '',
                  'first_name': '', 'last_name': ''}
        # update values using SimpleRegistration or AttributeExchange
        # values
        values.update(self.values_from_response(
            response, self.get_sreg_attributes(), self.get_ax_attributes()
        ))

        fullname = values.get('fullname') or ''
        first_name = values.get('first_name') or ''
        last_name = values.get('last_name') or ''

        if not fullname and first_name and last_name:
            fullname = first_name + ' ' + last_name
        elif fullname:
            try:
                first_name, last_name = fullname.rsplit(' ', 1)
            except ValueError:
                last_name = fullname

        username_key = self.setting('USERNAME_KEY') or self.USERNAME_KEY
        values.update({'fullname': fullname, 'first_name': first_name,
                       'last_name': last_name,
                       'username': values.get(username_key) or
                                   (first_name.title() + last_name.title())})
        return values

    def extra_data(self, user, uid, response, details):
        """Return defined extra data names to store in extra_data field.
        Settings will be inspected to get more values names that should be
        stored on extra_data field. Setting name is created from current
        backend name (all uppercase) plus _SREG_EXTRA_DATA and
        _AX_EXTRA_DATA because values can be returned by SimpleRegistration
        or AttributeExchange schemas.

        Both list must be a value name and an alias mapping similar to
        SREG_ATTR, OLD_AX_ATTRS or AX_SCHEMA_ATTRS
        """
        sreg_names = self.setting('SREG_EXTRA_DATA')
        ax_names = self.setting('AX_EXTRA_DATA')
        values = self.values_from_response(response, sreg_names, ax_names)
        from_details = super(OpenIdAuth, self).extra_data(
            user, uid, {}, details
        )
        values.update(from_details)
        return values

    def auth_url(self):
        """Return auth URL returned by service"""
        openid_request = self.setup_request(self.auth_extra_arguments())
        # Construct completion URL, including page we should redirect to
        return_to = self.strategy.absolute_uri(self.redirect_uri)
        return openid_request.redirectURL(self.trust_root(), return_to)

    def auth_html(self):
        """Return auth HTML returned by service"""
        openid_request = self.setup_request(self.auth_extra_arguments())
        return_to = self.strategy.absolute_uri(self.redirect_uri)
        form_tag = {'id': 'openid_message'}
        return openid_request.htmlMarkup(self.trust_root(), return_to,
                                         form_tag_attrs=form_tag)

    def trust_root(self):
        """Return trust-root option"""
        return self.setting('OPENID_TRUST_ROOT') or \
               self.strategy.absolute_uri('/')

    def continue_pipeline(self, *args, **kwargs):
        """Continue previous halted pipeline"""
        response = self.consumer().complete(dict(self.data.items()),
                                            self.strategy.absolute_uri(
                                                self.redirect_uri
                                            ))
        kwargs.update({'response': response, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def auth_complete(self, *args, **kwargs):
        """Complete auth process"""
        response = self.consumer().complete(dict(self.data.items()),
                                            self.strategy.absolute_uri(
                                                self.redirect_uri
                                            ))
        self.process_error(response)
        kwargs.update({'response': response, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

    def process_error(self, data):
        if not data:
            raise AuthException(self, 'OpenID relying party endpoint')
        elif data.status == FAILURE:
            raise AuthFailed(self, data.message)
        elif data.status == CANCEL:
            raise AuthCanceled(self)
        elif data.status != SUCCESS:
            raise AuthUnknownError(self, data.status)

    def setup_request(self, params=None):
        """Setup request"""
        request = self.openid_request(params)
        # Request some user details. Use attribute exchange if provider
        # advertises support.
        if request.endpoint.supportsType(ax.AXMessage.ns_uri):
            fetch_request = ax.FetchRequest()
            # Mark all attributes as required, Google ignores optional ones
            for attr, alias in self.get_ax_attributes():
                fetch_request.add(ax.AttrInfo(attr, alias=alias,
                                              required=True))
        else:
            fetch_request = sreg.SRegRequest(
                optional=list(dict(self.get_sreg_attributes()).keys())
            )
        request.addExtension(fetch_request)

        # Add PAPE Extension for if configured
        preferred_policies = self.setting(
            'OPENID_PAPE_PREFERRED_AUTH_POLICIES'
        )
        preferred_level_types = self.setting(
            'OPENID_PAPE_PREFERRED_AUTH_LEVEL_TYPES'
        )
        max_age = self.setting('OPENID_PAPE_MAX_AUTH_AGE')
        if max_age is not None:
            try:
                max_age = int(max_age)
            except (ValueError, TypeError):
                max_age = None

        if max_age is not None or preferred_policies or preferred_level_types:
            pape_request = pape.Request(
                max_auth_age=max_age,
                preferred_auth_policies=preferred_policies,
                preferred_auth_level_types=preferred_level_types
            )
            request.addExtension(pape_request)
        return request

    def consumer(self):
        """Create an OpenID Consumer object for the given Django request."""
        if not hasattr(self, '_consumer'):
            self._consumer = self.create_consumer(self.strategy.openid_store())
        return self._consumer

    def create_consumer(self, store=None):
        return Consumer(self.strategy.openid_session_dict(SESSION_NAME), store)

    def uses_redirect(self):
        """Return true if openid request will be handled with redirect or
        HTML content will be returned.
        """
        return self.openid_request().shouldSendRedirect()

    def openid_request(self, params=None):
        """Return openid request"""
        try:
            return self.consumer().begin(url_add_parameters(self.openid_url(),
                                         params))
        except DiscoveryFailure as err:
            raise AuthException(self, 'OpenID discovery error: {0}'.format(
                err
            ))

    def openid_url(self):
        """Return service provider URL.
        This base class is generic accepting a POST parameter that specifies
        provider URL."""
        if self.URL:
            return self.URL
        elif OPENID_ID_FIELD in self.data:
            return self.data[OPENID_ID_FIELD]
        else:
            raise AuthMissingParameter(self, OPENID_ID_FIELD)

########NEW FILE########
__FILENAME__ = orkut
"""
Orkut OAuth backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/google.html#orkut
"""
from social.backends.google import GoogleOAuth


class OrkutOAuth(GoogleOAuth):
    """Orkut OAuth authentication backend"""
    name = 'orkut'
    DEFAULT_SCOPE = ['http://orkut.gmodules.com/social/']

    def get_user_details(self, response):
        """Return user details from Orkut account"""
        try:
            emails = response['emails'][0]['value']
        except (KeyError, IndexError):
            emails = ''

        fullname, first_name, last_name = self.get_user_names(
            fullname=response['displayName'],
            first_name=response['name']['givenName'],
            last_name=response['name']['familyName']
        )
        return {'username': response['displayName'],
                'email': emails,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from Orkut service"""
        fields = ','.join(set(['name', 'displayName', 'emails'] +
                          self.setting('EXTRA_DATA', [])))
        scope = self.DEFAULT_SCOPE + self.setting('SCOPE', [])
        params = {'method': 'people.get',
                  'id': 'myself',
                  'userId': '@me',
                  'groupId': '@self',
                  'fields': fields,
                  'scope': self.SCOPE_SEPARATOR.join(scope)}
        url = 'http://www.orkut.com/social/rpc'
        request = self.oauth_request(access_token, url, params)
        return self.get_json(request.to_url())['data']

    def oauth_request(self, token, url, params=None):
        params = params or {}
        scope = self.DEFAULT_SCOPE + self.setting('SCOPE', [])
        params['scope'] = self.SCOPE_SEPARATOR.join(scope)
        return super(OrkutOAuth, self).oauth_request(token, url, params)

########NEW FILE########
__FILENAME__ = persona
"""
Mozilla Persona authentication backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/persona.html
"""
from social.backends.base import BaseAuth
from social.exceptions import AuthFailed, AuthMissingParameter


class PersonaAuth(BaseAuth):
    """BrowserID authentication backend"""
    name = 'persona'

    def get_user_id(self, details, response):
        """Use BrowserID email as ID"""
        return details['email']

    def get_user_details(self, response):
        """Return user details, BrowserID only provides Email."""
        # {'status': 'okay',
        #  'audience': 'localhost:8000',
        #  'expires': 1328983575529,
        #  'email': 'name@server.com',
        #  'issuer': 'browserid.org'}
        email = response['email']
        return {'username': email.split('@', 1)[0],
                'email': email,
                'fullname': '',
                'first_name': '',
                'last_name': ''}

    def extra_data(self, user, uid, response, details):
        """Return users extra data"""
        return {'audience': response['audience'],
                'issuer': response['issuer']}

    def auth_complete(self, *args, **kwargs):
        """Completes loging process, must return user instance"""
        if not 'assertion' in self.data:
            raise AuthMissingParameter(self, 'assertion')

        response = self.get_json('https://browserid.org/verify', data={
            'assertion': self.data['assertion'],
            'audience': self.strategy.request_host()
        }, method='POST')
        if response.get('status') == 'failure':
            raise AuthFailed(self)
        kwargs.update({'response': response, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

########NEW FILE########
__FILENAME__ = pixelpin
from social.backends.oauth import BaseOAuth2


class PixelPinOAuth2(BaseOAuth2):
    """PixelPin OAuth authentication backend"""
    name = 'pixelpin-oauth2'
    ID_KEY = 'id'
    AUTHORIZATION_URL = 'https://login.pixelpin.co.uk/OAuth2/Flogin.aspx'
    ACCESS_TOKEN_URL = 'https://ws3.pixelpin.co.uk/index.php/api/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REQUIRES_EMAIL_VALIDATION = False
    EXTRA_DATA = [
        ('id', 'id'),
    ]

    def get_user_details(self, response):
        """Return user details from PixelPin account"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response.get('firstName'),
            last_name=response.get('lastName')
        )
        return {'username': response.get('firstName'),
                'email': response.get('email') or '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://ws3.pixelpin.co.uk/index.php/api/userdata',
            params={'access_token': access_token}
        )

########NEW FILE########
__FILENAME__ = pocket
"""
Pocket OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/pocket.html
"""
from social.backends.base import BaseAuth


class PocketAuth(BaseAuth):
    name = 'pocket'
    AUTHORIZATION_URL = 'https://getpocket.com/auth/authorize'
    ACCESS_TOKEN_URL = 'https://getpocket.com/v3/oauth/authorize'
    REQUEST_TOKEN_URL = 'https://getpocket.com/v3/oauth/request'
    ID_KEY = 'username'

    def get_json(self, url, *args, **kwargs):
        headers = {'X-Accept': 'application/json'}
        kwargs.update({'method': 'POST', 'headers': headers})
        return super(PocketAuth, self).get_json(url, *args, **kwargs)

    def get_user_details(self, response):
        return {'username': response['username']}

    def extra_data(self, user, uid, response, details):
        return response

    def auth_url(self):
        data = {
            'consumer_key': self.setting('POCKET_CONSUMER_KEY'),
            'redirect_uri': self.redirect_uri,
        }
        token = self.get_json(self.REQUEST_TOKEN_URL, data=data)['code']
        self.strategy.session_set('pocket_request_token', token)
        bits = (self.AUTHORIZATION_URL, token, self.redirect_uri)
        return '%s?request_token=%s&redirect_uri=%s' % bits

    def auth_complete(self, *args, **kwargs):
        data = {
            'consumer_key': self.setting('POCKET_CONSUMER_KEY'),
            'code': self.strategy.session_get('pocket_request_token'),
        }
        response = self.get_json(self.ACCESS_TOKEN_URL, data=data)
        kwargs.update({'response': response, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

########NEW FILE########
__FILENAME__ = podio
"""
Podio OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/podio.html
"""
from social.backends.oauth import BaseOAuth2


class PodioOAuth2(BaseOAuth2):
    """Podio OAuth authentication backend"""
    name = 'podio'
    AUTHORIZATION_URL = 'https://podio.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://podio.com/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [
        ('access_token', 'access_token'),
        ('token_type', 'token_type'),
        ('expires_in', 'expires'),
        ('refresh_token', 'refresh_token'),
    ]

    def get_user_id(self, details, response):
        return response['ref']['id']

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(
            response['profile']['name']
        )
        return {
            'username': 'user_%d' % response['user']['user_id'],
            'email': response['user']['mail'],
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name,
        }

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json('https://api.podio.com/user/status',
            headers={'Authorization': 'OAuth2 ' + access_token})

########NEW FILE########
__FILENAME__ = rdio
"""
Rdio OAuth1 and OAuth2 backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/rdio.html
"""
from social.backends.oauth import BaseOAuth1, BaseOAuth2, OAuthAuth


RDIO_API = 'https://www.rdio.com/api/1/'


class BaseRdio(OAuthAuth):
    ID_KEY = 'key'

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(
            fullname=response['displayName'],
            first_name=response['firstName'],
            last_name=response['lastName']
        )
        return {
            'username': response['username'],
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name
        }


class RdioOAuth1(BaseRdio, BaseOAuth1):
    """Rdio OAuth authentication backend"""
    name = 'rdio-oauth1'
    REQUEST_TOKEN_URL = 'http://api.rdio.com/oauth/request_token'
    AUTHORIZATION_URL = 'https://www.rdio.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'http://api.rdio.com/oauth/access_token'
    EXTRA_DATA = [
        ('key', 'rdio_id'),
        ('icon', 'rdio_icon_url'),
        ('url', 'rdio_profile_url'),
        ('username', 'rdio_username'),
        ('streamRegion', 'rdio_stream_region'),
    ]

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        params = {'method': 'currentUser',
                  'extras': 'username,displayName,streamRegion'}
        request = self.oauth_request(access_token, RDIO_API,
                                     params, method='POST')
        return self.get_json(request.url, method='POST',
                             data=request.to_postdata())['result']


class RdioOAuth2(BaseRdio, BaseOAuth2):
    name = 'rdio-oauth2'
    AUTHORIZATION_URL = 'https://www.rdio.com/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://www.rdio.com/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [
        ('key', 'rdio_id'),
        ('icon', 'rdio_icon_url'),
        ('url', 'rdio_profile_url'),
        ('username', 'rdio_username'),
        ('streamRegion', 'rdio_stream_region'),
        ('refresh_token', 'refresh_token', True),
        ('token_type', 'token_type', True),
    ]

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json(RDIO_API, method='POST', data={
            'method': 'currentUser',
            'extras': 'username,displayName,streamRegion',
            'access_token': access_token
        })['result']

########NEW FILE########
__FILENAME__ = readability
"""
Readability OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/readability.html
"""
from social.backends.oauth import BaseOAuth1


READABILITY_API = 'https://www.readability.com/api/rest/v1'


class ReadabilityOAuth(BaseOAuth1):
    """Readability OAuth authentication backend"""
    name = 'readability'
    ID_KEY = 'username'
    AUTHORIZATION_URL = '{0}/oauth/authorize/'.format(READABILITY_API)
    REQUEST_TOKEN_URL = '{0}/oauth/request_token/'.format(READABILITY_API)
    ACCESS_TOKEN_URL = '{0}/oauth/access_token/'.format(READABILITY_API)
    EXTRA_DATA = [('date_joined', 'date_joined'),
                  ('kindle_email_address', 'kindle_email_address'),
                  ('avatar_url', 'avatar_url'),
                  ('email_into_address', 'email_into_address')]

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(
            first_name=response['first_name'],
            last_name=response['last_name']
        )
        return {'username': response['username'],
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token):
        return self.get_json(READABILITY_API + '/users/_current',
                             auth=self.oauth_auth(access_token))

########NEW FILE########
__FILENAME__ = reddit
"""
Reddit OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/reddit.html
"""
import base64

from social.backends.oauth import BaseOAuth2


class RedditOAuth2(BaseOAuth2):
    """Reddit OAuth2 authentication backend"""
    name = 'reddit'
    AUTHORIZATION_URL = 'https://ssl.reddit.com/api/v1/authorize'
    ACCESS_TOKEN_URL = 'https://ssl.reddit.com/api/v1/access_token'
    ACCESS_TOKEN_METHOD = 'POST'
    REFRESH_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    SCOPE_SEPARATOR = ','
    DEFAULT_SCOPE = ['identity']
    EXTRA_DATA = [
        ('id', 'id'),
        ('link_karma', 'link_karma'),
        ('comment_karma', 'comment_karma'),
        ('refresh_token', 'refresh_token'),
        ('expires_in', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Reddit account"""
        return {'username': response.get('name'),
                'email': '', 'fullname': '',
                'first_name': '', 'last_name': ''}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://oauth.reddit.com/api/v1/me.json',
            headers={'Authorization': 'bearer ' + access_token}
        )

    def auth_headers(self):
        return {
            'Authorization': 'Basic {0}'.format(base64.urlsafe_b64encode(
                ('{0}:{1}'.format(*self.get_key_and_secret()).encode())
            ))
        }

    def refresh_token_params(self, token, redirect_uri=None, *args, **kwargs):
        params = super(RedditOAuth2, self).refresh_token_params(token)
        params['redirect_uri'] = self.redirect_uri or redirect_uri
        return params

########NEW FILE########
__FILENAME__ = runkeeper
"""
RunKeeper OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/runkeeper.html
"""
from social.backends.oauth import BaseOAuth2


class RunKeeperOAuth2(BaseOAuth2):
    """RunKeeper OAuth authentication backend"""
    name = 'runkeeper'
    AUTHORIZATION_URL = 'https://runkeeper.com/apps/authorize'
    ACCESS_TOKEN_URL = 'https://runkeeper.com/apps/token'
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [
        ('userID', 'id'),
    ]

    def get_user_id(self, details, response):
        return response['userID']

    def get_user_details(self, response):
        """Parse username from profile link"""
        username = None
        profile_url = response.get('profile')
        if len(profile_url):
            profile_url_parts = profile_url.split('http://runkeeper.com/user/')
            if len(profile_url_parts) > 1 and len(profile_url_parts[1]):
                username = profile_url_parts[1]
        fullname, first_name, last_name = self.get_user_names(
            fullname=response.get('name')
        )
        return {'username': username,
                'email': response.get('email') or '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        # We need to use the /user endpoint to get the user id, the /profile
        # endpoint contains name, user name, location, gender
        user_data = self._user_data(access_token, '/user')
        profile_data = self._user_data(access_token, '/profile')
        return dict(user_data, **profile_data)

    def _user_data(self, access_token, path):
        url = 'https://api.runkeeper.com{0}'.format(path)
        return self.get_json(url, params={'access_token': access_token})

########NEW FILE########
__FILENAME__ = shopify
"""
Shopify OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/shopify.html
"""
import imp
import six

from requests import HTTPError

from social.backends.oauth import BaseOAuth2
from social.exceptions import AuthFailed, AuthCanceled


class ShopifyOAuth2(BaseOAuth2):
    """Shopify OAuth2 authentication backend"""
    name = 'shopify'
    ID_KEY = 'shop'
    EXTRA_DATA = [
        ('shop', 'shop'),
        ('website', 'website'),
        ('expires', 'expires')
    ]

    @property
    def shopifyAPI(self):
        if not hasattr(self, '_shopify_api'):
            fp, pathname, description = imp.find_module('shopify')
            self._shopify_api = imp.load_module('shopify', fp, pathname,
                                                description)
        return self._shopify_api

    def get_user_details(self, response):
        """Use the shopify store name as the username"""
        return {
            'username': six.text_type(response.get('shop', ''), 'utf-8')
                                .replace('.myshopify.com', '')
        }

    def auth_url(self):
        key, secret = self.get_key_and_secret()
        self.shopifyAPI.Session.setup(api_key=key, secret=secret)
        scope = self.get_scope()
        state = self.state_token()
        self.strategy.session_set(self.name + '_state', state)
        redirect_uri = self.get_redirect_uri(state)
        return self.shopifyAPI.Session.create_permission_url(
            self.data.get('shop').strip(),
            scope=scope,
            redirect_uri=redirect_uri
        )

    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance"""
        self.process_error(self.data)
        access_token = None
        key, secret = self.get_key_and_secret()
        try:
            shop_url = self.data.get('shop')
            self.shopifyAPI.Session.setup(api_key=key, secret=secret)
            shopify_session = self.shopifyAPI.Session(shop_url, self.data)
            access_token = shopify_session.token
        except self.shopifyAPI.ValidationException:
            raise AuthCanceled(self)
        except HTTPError as err:
            if err.response.status_code == 400:
                raise AuthCanceled(self)
            else:
                raise
        else:
            if not access_token:
                raise AuthFailed(self, 'Authentication Failed')
        return self.do_auth(access_token, shop_url, shopify_session.url,
                            *args, **kwargs)

    def do_auth(self, access_token, shop_url, website, *args, **kwargs):
        kwargs.update({
            'backend': self,
            'response': {
                'shop': shop_url,
                'website': 'http://{0}'.format(website),
                'access_token': access_token
            }
        })
        return self.strategy.authenticate(*args, **kwargs)

########NEW FILE########
__FILENAME__ = skyrock
"""
Skyrock OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/skyrock.html
"""
from social.backends.oauth import BaseOAuth1


class SkyrockOAuth(BaseOAuth1):
    """Skyrock OAuth authentication backend"""
    name = 'skyrock'
    ID_KEY = 'id_user'
    AUTHORIZATION_URL = 'https://api.skyrock.com/v2/oauth/authenticate'
    REQUEST_TOKEN_URL = 'https://api.skyrock.com/v2/oauth/initiate'
    ACCESS_TOKEN_URL = 'https://api.skyrock.com/v2/oauth/token'
    EXTRA_DATA = [('id', 'id')]

    def get_user_details(self, response):
        """Return user details from Skyrock account"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response['firstname'],
            last_name=response['name']
        )
        return {'username': response['username'],
                'email': response['email'],
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token):
        """Return user data provided"""
        return self.get_json('https://api.skyrock.com/v2/user/get.json',
                             auth=self.oauth_auth(access_token))

########NEW FILE########
__FILENAME__ = soundcloud
"""
Soundcloud OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/soundcloud.html
"""
from social.p3 import urlencode
from social.backends.oauth import BaseOAuth2


class SoundcloudOAuth2(BaseOAuth2):
    """Soundcloud OAuth authentication backend"""
    name = 'soundcloud'
    AUTHORIZATION_URL = 'https://soundcloud.com/connect'
    ACCESS_TOKEN_URL = 'https://api.soundcloud.com/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('id', 'id'),
        ('refresh_token', 'refresh_token'),
        ('expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Soundcloud account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('full_name')
        )
        return {'username': response.get('username'),
                'email': response.get('email') or '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://api.soundcloud.com/me.json',
                             params={'oauth_token': access_token})

    def auth_url(self):
        """Return redirect url"""
        state = None
        if self.STATE_PARAMETER or self.REDIRECT_STATE:
            # Store state in session for further request validation. The state
            # value is passed as state parameter (as specified in OAuth2 spec),
            # but also added to redirect_uri, that way we can still verify the
            # request if the provider doesn't implement the state parameter.
            # Reuse token if any.
            name = self.name + '_state'
            state = self.strategy.session_get(name) or self.state_token()
            self.strategy.session_set(name, state)

        params = self.auth_params(state)
        params.update(self.get_scope_argument())
        params.update(self.auth_extra_arguments())
        return self.AUTHORIZATION_URL + '?' + urlencode(params)

########NEW FILE########
__FILENAME__ = spotify
"""
Spotify backend, docs at:
    https://developer.spotify.com/spotify-web-api/
    https://developer.spotify.com/spotify-web-api/authorization-guide/
"""
import base64

from social.backends.oauth import BaseOAuth2


class SpotifyOAuth2(BaseOAuth2):
    name = 'spotify'
    SCOPE_SEPARATOR = ' '
    ID_KEY = 'id'
    AUTHORIZATION_URL = 'https://accounts.spotify.com/authorize'
    ACCESS_TOKEN_URL = 'https://accounts.spotify.com/api/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    STATE_PARAMETER = False

    def auth_headers(self):
        return {
            'Authorization': 'Basic {0}'.format(base64.urlsafe_b64encode(
                ('{0}:{1}'.format(*self.get_key_and_secret()).encode())
            ))
        }

    def get_user_details(self, response):
        """Return user details from Spotify account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('display_name')
        )
        return {'username': response.get('id'),
                'email': response.get('email'),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': 'Bearer {0}'.format(access_token)}
        )

########NEW FILE########
__FILENAME__ = stackoverflow
"""
Stackoverflow OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/stackoverflow.html
"""
from social.backends.oauth import BaseOAuth2


class StackoverflowOAuth2(BaseOAuth2):
    """Stackoverflow OAuth2 authentication backend"""
    name = 'stackoverflow'
    ID_KEY = 'user_id'
    AUTHORIZATION_URL = 'https://stackexchange.com/oauth'
    ACCESS_TOKEN_URL = 'https://stackexchange.com/oauth/access_token'
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Stackoverflow account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('display_name')
        )
        return {'username': response.get('link').rsplit('/', 1)[-1],
                'full_name': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://api.stackexchange.com/2.1/me',
                             params={'site': 'stackoverflow',
                                     'access_token': access_token,
                                     'key': self.setting('API_KEY')}
        )['items'][0]

    def request_access_token(self, *args, **kwargs):
        return self.get_querystring(*args, **kwargs)

########NEW FILE########
__FILENAME__ = steam
"""
Steam OpenId backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/steam.html
"""
from social.backends.open_id import OpenIdAuth
from social.exceptions import AuthFailed


USER_INFO = 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?'


class SteamOpenId(OpenIdAuth):
    name = 'steam'
    URL = 'https://steamcommunity.com/openid'

    def get_user_id(self, details, response):
        """Return user unique id provided by service"""
        return self._user_id(response)

    def get_user_details(self, response):
        player = self.get_json(USER_INFO, params={
            'key': self.setting('API_KEY'),
            'steamids': self._user_id(response)
        })
        if len(player['response']['players']) > 0:
            player = player['response']['players'][0]
            details = {'username': player.get('personaname'),
                       'email': '',
                       'fullname': '',
                       'first_name': '',
                       'last_name': '',
                       'player': player}
        else:
            details = {}
        return details

    def consumer(self):
        # Steam seems to support stateless mode only, ignore store
        if not hasattr(self, '_consumer'):
            self._consumer = self.create_consumer()
        return self._consumer

    def _user_id(self, response):
        user_id = response.identity_url.rsplit('/', 1)[-1]
        if not user_id.isdigit():
            raise AuthFailed(self, 'Missing Steam Id')
        return user_id

########NEW FILE########
__FILENAME__ = stocktwits
"""
Stocktwits OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/stocktwits.html
"""
from social.backends.oauth import BaseOAuth2


class StocktwitsOAuth2(BaseOAuth2):
    """Stockwiths OAuth2 backend"""
    name = 'stocktwits'
    AUTHORIZATION_URL = 'https://api.stocktwits.com/api/2/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://api.stocktwits.com/api/2/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','
    DEFAULT_SCOPE = ['read', 'publish_messages', 'publish_watch_lists',
                     'follow_users', 'follow_stocks']

    def get_user_id(self, details, response):
        return response['user']['id']

    def get_user_details(self, response):
        """Return user details from Stocktwits account"""
        fullname, first_name, last_name = self.get_user_names(
            response['user']['name']
        )
        return {'username': response['user']['username'],
                'email': '',  # not supplied
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json(
            'https://api.stocktwits.com/api/2/account/verify.json',
            params={'access_token': access_token}
        )

########NEW FILE########
__FILENAME__ = strava
"""
Strava OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/strava.html
"""
from social.backends.oauth import BaseOAuth2


class StravaOAuth(BaseOAuth2):
    name = 'strava'
    AUTHORIZATION_URL = 'https://www.strava.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://www.strava.com/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    # Strava doesn't check for parameters in redirect_uri and directly appends
    # the auth parameters to it, ending with an URL like:
    # http://example.com/complete/strava?redirect_state=xxx?code=xxx&state=xxx
    # Check issue #259 for details.
    REDIRECT_STATE = False

    def get_user_id(self, details, response):
        return response['athlete']['id']

    def get_user_details(self, response):
        """Return user details from Strava account"""
        # because there is no usernames on strava
        username = response['athlete']['id']
        email = response['athlete'].get('email', '')
        fullname, first_name, last_name = self.get_user_names(
            first_name=response['athlete'].get('first_name', '')
        )
        return {'username': str(username),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('https://www.strava.com/api/v3/athlete',
                             params={'access_token': access_token})

########NEW FILE########
__FILENAME__ = stripe
"""
Stripe OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/stripe.html
"""
from social.backends.oauth import BaseOAuth2


class StripeOAuth2(BaseOAuth2):
    """Stripe OAuth2 authentication backend"""
    name = 'stripe'
    ID_KEY = 'stripe_user_id'
    AUTHORIZATION_URL = 'https://connect.stripe.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://connect.stripe.com/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('stripe_publishable_key', 'stripe_publishable_key'),
        ('access_token', 'access_token'),
        ('livemode', 'livemode'),
        ('token_type', 'token_type'),
        ('refresh_token', 'refresh_token'),
        ('stripe_user_id', 'stripe_user_id'),
    ]

    def get_user_details(self, response):
        """Return user details from Stripe account"""
        return {'username': response.get('stripe_user_id'),
                'email': ''}

    def auth_params(self, state=None):
        client_id, client_secret = self.get_key_and_secret()
        params = {'response_type': 'code',
                  'client_id': client_id}
        if state:
            params['state'] = state
        return params

    def auth_complete_params(self, state=None):
        client_id, client_secret = self.get_key_and_secret()
        return {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'scope': self.SCOPE_SEPARATOR.join(self.get_scope()),
            'code': self.data['code']
        }

    def auth_headers(self):
        client_id, client_secret = self.get_key_and_secret()
        return {'Accept': 'application/json',
                'Authorization': 'Bearer {0}'.format(client_secret)}

    def refresh_token_params(self, refresh_token, *args, **kwargs):
        return {'refresh_token': refresh_token,
                'grant_type': 'refresh_token'}

########NEW FILE########
__FILENAME__ = suse
"""
Open Suse OpenId backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/suse.html
"""
from social.backends.open_id import OpenIdAuth


class OpenSUSEOpenId(OpenIdAuth):
    name = 'opensuse'
    URL = 'https://www.opensuse.org/openid/user/'

    def get_user_id(self, details, response):
        """
        Return user unique id provided by service. For openSUSE
        the nickname is original.
        """
        return details['nickname']

########NEW FILE########
__FILENAME__ = taobao
from social.backends.oauth import BaseOAuth2


class TAOBAOAuth(BaseOAuth2):
    """Taobao OAuth authentication mechanism"""
    name = 'taobao'
    ID_KEY = 'taobao_user_id'
    ACCESS_TOKEN_METHOD = 'POST'
    AUTHORIZATION_URL = 'https://oauth.taobao.com/authorize'
    ACCESS_TOKEN_URL = 'https://oauth.taobao.com/token'

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        try:
            return self.get_json('https://eco.taobao.com/router/rest', params={
                'method': 'taobao.user.get',
                'fomate': 'json',
                'v': '2.0',
                'access_token': access_token
            })
        except ValueError:
            return None

    def get_user_details(self, response):
        """Return user details from Taobao account"""
        return {'username': response.get('taobao_user_nick')}

########NEW FILE########
__FILENAME__ = thisismyjam
"""
ThisIsMyJam OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/thisismyjam.html
"""
from social.backends.oauth import BaseOAuth1


class ThisIsMyJamOAuth1(BaseOAuth1):
    """ThisIsMyJam OAuth1 authentication backend"""
    name = 'thisismyjam'
    REQUEST_TOKEN_URL = 'http://www.thisismyjam.com/oauth/request_token'
    AUTHORIZATION_URL = 'http://www.thisismyjam.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'http://www.thisismyjam.com/oauth/access_token'
    REDIRECT_URI_PARAMETER_NAME = 'oauth_callback'

    def get_user_details(self, response):
        """Return user details from ThisIsMyJam account"""
        info = response.get('person')
        fullname, first_name, last_name = self.get_user_names(
            info.get('fullname')
        )
        return {
            'username': info.get('name'),
            'email': '',
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name
        }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('http://api.thisismyjam.com/1/verify.json',
                             auth=self.oauth_auth(access_token))

########NEW FILE########
__FILENAME__ = trello
"""
Trello OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/trello.html
"""
from social.backends.oauth import BaseOAuth1


class TrelloOAuth(BaseOAuth1):

    """Trello OAuth authentication backend"""
    name = 'trello'
    ID_KEY = 'username'
    AUTHORIZATION_URL = 'https://trello.com/1/OAuthAuthorizeToken'
    REQUEST_TOKEN_URL = 'https://trello.com/1/OAuthGetRequestToken'
    ACCESS_TOKEN_URL = 'https://trello.com/1/OAuthGetAccessToken'

    EXTRA_DATA = [
        ('username', 'username'),
        ('email', 'email'),
        ('fullName', 'fullName')
    ]

    def get_user_details(self, response):
        """Return user details from Trello account"""
        fullname, first_name, last_name = self.get_user_names(
            response.get('fullName')
        )
        return {'username': response.get('username'),
                'email': response.get('email'),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token):
        """Return user data provided"""
        url = 'https://trello.com/1/members/me'
        try:
            return self.get_json(url, auth=self.oauth_auth(access_token))
        except ValueError:
            return None

########NEW FILE########
__FILENAME__ = tripit
"""
Tripit OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/tripit.html
"""
from xml.dom import minidom

from social.backends.oauth import BaseOAuth1


class TripItOAuth(BaseOAuth1):
    """TripIt OAuth authentication backend"""
    name = 'tripit'
    AUTHORIZATION_URL = 'https://www.tripit.com/oauth/authorize'
    REQUEST_TOKEN_URL = 'https://api.tripit.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.tripit.com/oauth/access_token'
    EXTRA_DATA = [('screen_name', 'screen_name')]

    def get_user_details(self, response):
        """Return user details from TripIt account"""
        fullname, first_name, last_name = self.get_user_names(response['name'])
        return {'username': response['screen_name'],
                'email': response['email'],
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        dom = minidom.parseString(self.oauth_request(
            access_token,
            'https://api.tripit.com/v1/get/profile'
        ).content)
        return {
            'id': dom.getElementsByTagName('Profile')[0].getAttribute('ref'),
            'name': dom.getElementsByTagName('public_display_name')[0]
                                    .childNodes[0].data,
            'screen_name': dom.getElementsByTagName('screen_name')[0]
                                    .childNodes[0].data,
            'email': dom.getElementsByTagName('is_primary')[0]
                                    .parentNode
                                        .getElementsByTagName('address')[0]
                                            .childNodes[0].data
        }

########NEW FILE########
__FILENAME__ = tumblr
"""
Tumblr OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/tumblr.html
"""
from social.utils import first
from social.backends.oauth import BaseOAuth1


class TumblrOAuth(BaseOAuth1):
    name = 'tumblr'
    ID_KEY = 'name'
    AUTHORIZATION_URL = 'http://www.tumblr.com/oauth/authorize'
    REQUEST_TOKEN_URL = 'http://www.tumblr.com/oauth/request_token'
    REQUEST_TOKEN_METHOD = 'POST'
    ACCESS_TOKEN_URL = 'http://www.tumblr.com/oauth/access_token'

    def get_user_id(self, details, response):
        return response['response']['user'][self.ID_KEY]

    def get_user_details(self, response):
        # http://www.tumblr.com/docs/en/api/v2#user-methods
        user_info = response['response']['user']
        data = {'username': user_info['name']}
        blog = first(lambda blog: blog['primary'], user_info['blogs'])
        if blog:
            data['fullname'] = blog['title']
        return data

    def user_data(self, access_token):
        return self.get_json('http://api.tumblr.com/v2/user/info',
                             auth=self.oauth_auth(access_token))

########NEW FILE########
__FILENAME__ = twilio
"""
Amazon auth backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/twilio.html
"""
from re import sub

from social.p3 import urlencode
from social.backends.base import BaseAuth


class TwilioAuth(BaseAuth):
    name = 'twilio'
    ID_KEY = 'AccountSid'

    def get_user_details(self, response):
        """Return twilio details, Twilio only provides AccountSID as
        parameters."""
        # /complete/twilio/?AccountSid=ACc65ea16c9ebd4d4684edf814995b27e
        return {'username': response['AccountSid'],
                'email': '',
                'fullname': '',
                'first_name': '',
                'last_name': ''}

    def auth_url(self):
        """Return authorization redirect url."""
        key, secret = self.get_key_and_secret()
        callback = self.strategy.absolute_uri(self.redirect_uri)
        callback = sub(r'^https', 'http', callback)
        query = urlencode({'cb': callback})
        return 'https://www.twilio.com/authorize/{0}?{1}'.format(key, query)

    def auth_complete(self, *args, **kwargs):
        """Completes loging process, must return user instance"""
        account_sid = self.data.get('AccountSid')
        if not account_sid:
            raise ValueError('No AccountSid returned')
        kwargs.update({'response': self.data, 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)

########NEW FILE########
__FILENAME__ = twitch
"""
Twitch OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/twitch.html
"""
from social.backends.oauth import BaseOAuth2


class TwitchOAuth2(BaseOAuth2):
    """Twitch OAuth authentication backend"""
    name = 'twitch'
    ID_KEY = '_id'
    AUTHORIZATION_URL = 'https://api.twitch.tv/kraken/oauth2/authorize'
    ACCESS_TOKEN_URL = 'https://api.twitch.tv/kraken/oauth2/token'
    ACCESS_TOKEN_METHOD = 'POST'
    DEFAULT_SCOPE = ['user_read']
    REDIRECT_STATE = False

    def get_user_details(self, response):
        return {
            'username': response.get('name'),
            'email': response.get('email'),
            'first_name': '',
            'last_name': ''
        }

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json(
            'https://api.twitch.tv/kraken/user/',
            params={'oauth_token': access_token}
        )

########NEW FILE########
__FILENAME__ = twitter
"""
Twitter OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/twitter.html
"""
from social.backends.oauth import BaseOAuth1
from social.exceptions import AuthCanceled


class TwitterOAuth(BaseOAuth1):
    """Twitter OAuth authentication backend"""
    name = 'twitter'
    EXTRA_DATA = [('id', 'id')]
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authenticate'
    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'

    def process_error(self, data):
        if 'denied' in data:
            raise AuthCanceled(self)
        else:
            super(TwitterOAuth, self).process_error(data)

    def get_user_details(self, response):
        """Return user details from Twitter account"""
        fullname, first_name, last_name = self.get_user_names(response['name'])
        return {'username': response['screen_name'],
                'email': '',  # not supplied
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json(
            'https://api.twitter.com/1.1/account/verify_credentials.json',
            auth=self.oauth_auth(access_token)
        )

########NEW FILE########
__FILENAME__ = ubuntu
"""
Ubuntu One OpenId backend
"""
from social.backends.open_id import OpenIdAuth


class UbuntuOpenId(OpenIdAuth):
    name = 'ubuntu'
    URL = 'https://login.ubuntu.com'

    def get_user_id(self, details, response):
        """
        Return user unique id provided by service. For Ubuntu One
        the nickname should be original.
        """
        return details['nickname']

########NEW FILE########
__FILENAME__ = username
"""
Legacy Username backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/username.html
"""
from social.backends.legacy import LegacyAuth


class UsernameAuth(LegacyAuth):
    name = 'username'
    ID_KEY = 'username'
    EXTRA_DATA = ['username']

########NEW FILE########
__FILENAME__ = utils
from social.utils import module_member, user_is_authenticated
from social.backends.base import BaseAuth


# Cache for discovered backends.
BACKENDSCACHE = {}


def load_backends(backends, force_load=False):
    """
    Load backends defined on SOCIAL_AUTH_AUTHENTICATION_BACKENDS, backends will
    be imported and cached on BACKENDSCACHE. The key in that dict will be the
    backend name, and the value is the backend class.

    Only subclasses of BaseAuth (and sub-classes) are considered backends.

    Previously there was a BACKENDS attribute expected on backends modules,
    this is not needed anymore since it's enough with the
    AUTHENTICATION_BACKENDS setting. BACKENDS was used because backends used to
    be split on two classes the authentication backend and another class that
    dealt with the auth mechanism with the provider, those classes are joined
    now.

    A force_load boolean argument is also provided so that get_backend
    below can retry a requested backend that may not yet be discovered.
    """
    global BACKENDSCACHE
    if force_load:
        BACKENDSCACHE = {}
    if not BACKENDSCACHE:
        for auth_backend in backends:
            backend = module_member(auth_backend)
            if issubclass(backend, BaseAuth):
                BACKENDSCACHE[backend.name] = backend
    return BACKENDSCACHE


def get_backend(backends, name):
    """Returns a backend by name. Backends are stored in the BACKENDSCACHE
    cache dict. If not found, each of the modules referenced in
    AUTHENTICATION_BACKENDS is imported and checked for a BACKENDS
    definition. If the named backend is found in the module's BACKENDS
    definition, it's then stored in the cache for future access.
    """
    try:
        # Cached backend which has previously been discovered
        return BACKENDSCACHE[name]
    except KeyError:
        # Reload BACKENDS to ensure a missing backend hasn't been missed
        load_backends(backends, force_load=True)
        try:
            return BACKENDSCACHE[name]
        except KeyError:
            return None


def user_backends_data(user, backends, storage):
    """
    Will return backends data for given user, the return value will have the
    following keys:
        associated: UserSocialAuth model instances for currently associated
                    accounts
        not_associated: Not associated (yet) backend names
        backends: All backend names.

    If user is not authenticated, then 'associated' list is empty, and there's
    no difference between 'not_associated' and 'backends'.
    """
    available = list(load_backends(backends).keys())
    values = {'associated': [],
              'not_associated': available,
              'backends': available}
    if user_is_authenticated(user):
        associated = storage.user.get_social_auth_for_user(user)
        not_associated = list(set(available) -
                              set(assoc.provider for assoc in associated))
        values['associated'] = associated
        values['not_associated'] = not_associated
    return values

########NEW FILE########
__FILENAME__ = vimeo
from social.backends.oauth import BaseOAuth1, BaseOAuth2


class VimeoOAuth1(BaseOAuth1):
    """Vimeo OAuth authentication backend"""
    name = 'vimeo'
    AUTHORIZATION_URL = 'https://vimeo.com/oauth/authorize'
    REQUEST_TOKEN_URL = 'https://vimeo.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://vimeo.com/oauth/access_token'

    def get_user_id(self, details, response):
        return response.get('person', {}).get('id')

    def get_user_details(self, response):
        """Return user details from Twitter account"""
        person = response.get('person', {})
        fullname, first_name, last_name = self.get_user_names(
            person.get('display_name', '')
        )
        return {'username': person.get('username', ''),
                'email': '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json(
            'https://vimeo.com/api/rest/v2',
            params={'format': 'json', 'method': 'vimeo.people.getInfo'},
            auth=self.oauth_auth(access_token)
        )


class VimeoOAuth2(BaseOAuth2):
    """Vimeo OAuth2 authentication backend"""
    name = 'vimeo-oauth2'
    AUTHORIZATION_URL = 'https://api.vimeo.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://api.vimeo.com/oauth/access_token'
    REFRESH_TOKEN_URL = 'https://api.vimeo.com/oauth/request_token'
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','
    API_ACCEPT_HEADER = {'Accept': 'application/vnd.vimeo.*+json;version=3.0'}

    def get_redirect_uri(self, state=None):
        """
        Build redirect with redirect_state parameter.

        @Vimeo API 3 requires exact redirect uri without additional
        additional state parameter included
        """
        return self.redirect_uri

    def get_user_id(self, details, response):
        """Return user id"""
        try:
            user_id = response.get('user', {})['uri'].split('/')[-1]
        except KeyError:
            user_id = None
        return user_id

    def get_user_details(self, response):
        """Return user details from account"""
        user = response.get('user', {})
        fullname, first_name, last_name = self.get_user_names(
            user.get('name', '')
        )
        return {'username': fullname,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        return self.get_json(
            'https://api.vimeo.com/me',
            params={'access_token': access_token},
            headers=VimeoOAuth2.API_ACCEPT_HEADER,
        )

########NEW FILE########
__FILENAME__ = vk
# -*- coding: utf-8 -*-
"""
VK.com OpenAPI, OAuth2 and Iframe application OAuth2 backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/vk.html
"""
from time import time
from hashlib import md5

from social.utils import parse_qs
from social.backends.base import BaseAuth
from social.backends.oauth import BaseOAuth2
from social.exceptions import AuthTokenRevoked, AuthException


class VKontakteOpenAPI(BaseAuth):
    """VK.COM OpenAPI authentication backend"""
    name = 'vk-openapi'
    ID_KEY = 'id'

    def get_user_details(self, response):
        """Return user details from VK.com request"""
        nickname = response.get('nickname') or ''
        fullname, first_name, last_name = self.get_user_names(
            first_name=response.get('first_name', [''])[0],
            last_name=response.get('last_name', [''])[0]
        )
        return {
            'username': response['id'] if len(nickname) == 0 else nickname,
            'email': '',
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name
        }

    def user_data(self, access_token, *args, **kwargs):
        return self.data

    def auth_html(self):
        """Returns local VK authentication page, not necessary for
        VK to authenticate.
        """
        ctx = {'VK_APP_ID': self.setting('APP_ID'),
               'VK_COMPLETE_URL': self.redirect_uri}
        local_html = self.setting('LOCAL_HTML', 'vkontakte.html')
        return self.strategy.render_html(tpl=local_html, context=ctx)

    def auth_complete(self, *args, **kwargs):
        """Performs check of authentication in VKontakte, returns User if
        succeeded"""
        session_value = self.strategy.session_get(
            'vk_app_' + self.setting('APP_ID')
        )
        if 'id' not in self.data or not session_value:
            raise ValueError('VK.com authentication is not completed')

        mapping = parse_qs(session_value)
        check_str = ''.join(item + '=' + mapping[item]
                                for item in ['expire', 'mid', 'secret', 'sid'])

        key, secret = self.get_key_and_secret()
        hash = md5((check_str + secret).encode('utf-8')).hexdigest()
        if hash != mapping['sig'] or int(mapping['expire']) < time():
            raise ValueError('VK.com authentication failed: Invalid Hash')

        kwargs.update({'backend': self,
                       'response': self.user_data(mapping['mid'])})
        return self.strategy.authenticate(*args, **kwargs)

    def uses_redirect(self):
        """VK.com does not require visiting server url in order
        to do authentication, so auth_xxx methods are not needed to be called.
        Their current implementation is just an example"""
        return False


class VKOAuth2(BaseOAuth2):
    """VKOAuth2 authentication backend"""
    name = 'vk-oauth2'
    ID_KEY = 'user_id'
    AUTHORIZATION_URL = 'http://oauth.vk.com/authorize'
    ACCESS_TOKEN_URL = 'https://oauth.vk.com/access_token'
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires_in', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from VK.com account"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response.get('first_name'),
            last_name=response.get('last_name')
        )
        return {'username': response.get('screen_name'),
                'email': response.get('email', ''),
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, response, *args, **kwargs):
        """Loads user data from service"""
        request_data = ['first_name', 'last_name', 'screen_name', 'nickname',
                        'photo'] + self.setting('EXTRA_DATA', [])

        fields = ','.join(set(request_data))
        data = vk_api(self, 'users.get', {
            'access_token': access_token,
            'fields': fields,
            'uids': response.get('user_id')
        })

        if data.get('error'):
            error = data['error']
            msg = error.get('error_msg', 'Unknown error')
            if error.get('error_code') == 5:
                raise AuthTokenRevoked(self, msg)
            else:
                raise AuthException(self, msg)

        if data:
            data = data.get('response')[0]
            data['user_photo'] = data.get('photo')  # Backward compatibility
        return data


class VKAppOAuth2(VKOAuth2):
    """VK.com Application Authentication support"""
    name = 'vk-app'

    def user_profile(self, user_id, access_token=None):
        request_data = ['first_name', 'last_name', 'screen_name', 'nickname',
                        'photo'] + self.setting('EXTRA_DATA', [])
        fields = ','.join(set(request_data))
        data = {'uids': user_id, 'fields': fields}
        if access_token:
            data['access_token'] = access_token
        profiles = vk_api(self, 'getProfiles', data).get('response')
        if profiles:
            return profiles[0]

    def auth_complete(self, *args, **kwargs):
        required_params = ('is_app_user', 'viewer_id', 'access_token',
                           'api_id')
        if not all(param in self.data for param in required_params):
            return None

        auth_key = self.data.get('auth_key')

        # Verify signature, if present
        key, secret = self.get_key_and_secret()
        if auth_key:
            check_key = md5('_'.join([key,
                                      self.data.get('viewer_id'),
                                      secret]).encode('utf-8')).hexdigest()
            if check_key != auth_key:
                raise ValueError('VK.com authentication failed: invalid '
                                 'auth key')

        user_check = self.setting('USERMODE')
        user_id = self.data.get('viewer_id')
        if user_check is not None:
            user_check = int(user_check)
            if user_check == 1:
                is_user = self.data.get('is_app_user')
            elif user_check == 2:
                is_user = vk_api(self, 'isAppUser',
                                        {'uid': user_id}).get('response', 0)
            if not int(is_user):
                return None

        auth_data = {
            'auth': self,
            'backend': self,
            'request': self.strategy.request,
            'response': {
                'user_id': user_id,
            }
        }
        auth_data['response'].update(self.user_profile(user_id))
        return self.strategy.authenticate(*args, **auth_data)


def vk_api(backend, method, data):
    """
    Calls VK.com OpenAPI method, check:
        https://vk.com/apiclub
        http://goo.gl/yLcaa
    """
    # We need to perform server-side call if no access_token
    if not 'access_token' in data:
        if not 'v' in data:
            data['v'] = '3.0'

        key, secret = backend.get_key_and_secret()
        if not 'api_id' in data:
            data['api_id'] = key

        data['method'] = method
        data['format'] = 'json'
        url = 'http://api.vk.com/api.php'
        param_list = sorted(list(item + '=' + data[item] for item in data))
        data['sig'] = md5(
            (''.join(param_list) + secret).encode('utf-8')
        ).hexdigest()
    else:
        url = 'https://api.vk.com/method/' + method

    try:
        return backend.get_json(url, params=data)
    except (TypeError, KeyError, IOError, ValueError, IndexError):
        return None

########NEW FILE########
__FILENAME__ = weibo
#coding:utf8
# author:hepochen@gmail.com  https://github.com/hepochen
"""
Weibo OAuth2 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/weibo.html
"""
from social.backends.oauth import BaseOAuth2


class WeiboOAuth2(BaseOAuth2):
    """Weibo (of sina) OAuth authentication backend"""
    name = 'weibo'
    ID_KEY = 'uid'
    AUTHORIZATION_URL = 'https://api.weibo.com/oauth2/authorize'
    REQUEST_TOKEN_URL = 'https://api.weibo.com/oauth2/request_token'
    ACCESS_TOKEN_URL = 'https://api.weibo.com/oauth2/access_token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('id', 'id'),
        ('name', 'username'),
        ('profile_image_url', 'profile_image_url'),
        ('gender', 'gender')
    ]

    def get_user_details(self, response):
        """Return user details from Weibo. API URL is:
        https://api.weibo.com/2/users/show.json/?uid=<UID>&access_token=<TOKEN>
        """
        if self.setting('DOMAIN_AS_USERNAME'):
            username = response.get('domain', '')
        else:
            username = response.get('name', '')
        fullname, first_name, last_name = self.get_user_names(
            first_name=response.get('screen_name', '')
        )
        return {'username': username,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json('https://api.weibo.com/2/users/show.json',
                             params={'access_token': access_token,
                                     'uid': kwargs['response']['uid']})

########NEW FILE########
__FILENAME__ = xing
"""
XING OAuth1 backend, docs at:
    http://psa.matiasaguirre.net/docs/backends/xing.html
"""
from social.backends.oauth import BaseOAuth1


class XingOAuth(BaseOAuth1):
    """Xing OAuth authentication backend"""
    name = 'xing'
    AUTHORIZATION_URL = 'https://api.xing.com/v1/authorize'
    REQUEST_TOKEN_URL = 'https://api.xing.com/v1/request_token'
    ACCESS_TOKEN_URL = 'https://api.xing.com/v1/access_token'
    SCOPE_SEPARATOR = '+'
    EXTRA_DATA = [
        ('id', 'id'),
        ('user_id', 'user_id')
    ]

    def get_user_details(self, response):
        """Return user details from Xing account"""
        email = response.get('email', '')
        fullname, first_name, last_name = self.get_user_names(
            first_name=response['first_name'],
            last_name=response['last_name']
        )
        return {'username': first_name + last_name,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name,
                'email': email}

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        profile = self.get_json(
            'https://api.xing.com/v1/users/me.json',
            auth=self.oauth_auth(access_token)
        )['users'][0]
        return {
            'user_id': profile['id'],
            'id': profile['id'],
            'first_name': profile['first_name'],
            'last_name': profile['last_name'],
            'email': profile['active_email']
        }

########NEW FILE########
__FILENAME__ = yahoo
"""
Yahoo OpenId and OAuth1 backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/yahoo.html
"""
from social.backends.open_id import OpenIdAuth
from social.backends.oauth import BaseOAuth1


class YahooOpenId(OpenIdAuth):
    """Yahoo OpenID authentication backend"""
    name = 'yahoo'
    URL = 'http://me.yahoo.com'


class YahooOAuth(BaseOAuth1):
    """Yahoo OAuth authentication backend"""
    name = 'yahoo-oauth'
    ID_KEY = 'guid'
    AUTHORIZATION_URL = 'https://api.login.yahoo.com/oauth/v2/request_auth'
    REQUEST_TOKEN_URL = \
        'https://api.login.yahoo.com/oauth/v2/get_request_token'
    ACCESS_TOKEN_URL = 'https://api.login.yahoo.com/oauth/v2/get_token'
    EXTRA_DATA = [
        ('guid', 'id'),
        ('access_token', 'access_token'),
        ('expires', 'expires')
    ]

    def get_user_details(self, response):
        """Return user details from Yahoo Profile"""
        fullname, first_name, last_name = self.get_user_names(
            first_name=response.get('givenName'),
            last_name=response.get('familyName')
        )
        emails = [email for email in response.get('emails', [])
                        if email.get('handle')]
        emails.sort(key=lambda e: e.get('primary', False))
        return {'username': response.get('nickname'),
                'email': emails[0]['handle'] if emails else '',
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        url = 'https://social.yahooapis.com/v1/user/{0}/profile?format=json'
        return self.get_json(
            url.format(self._get_guid(access_token)),
            auth=self.oauth_auth(access_token)
        )['profile']

    def _get_guid(self, access_token):
        """
            Beause you have to provide GUID for every API request
            it's also returned during one of OAuth calls
        """
        return self.get_json(
            'https://social.yahooapis.com/v1/me/guid?format=json',
            auth=self.oauth_auth(access_token)
        )['guid']['value']

########NEW FILE########
__FILENAME__ = yammer
"""
Yammer OAuth2 production and staging backends, docs at:
    http://psa.matiasaguirre.net/docs/backends/yammer.html
"""
from social.backends.oauth import BaseOAuth2


class YammerOAuth2(BaseOAuth2):
    name = 'yammer'
    AUTHORIZATION_URL = 'https://www.yammer.com/dialog/oauth'
    ACCESS_TOKEN_URL = 'https://www.yammer.com/oauth2/access_token'
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires', 'expires'),
        ('mugshot_url', 'mugshot_url')
    ]

    def get_user_id(self, details, response):
        return response['user']['id']

    def get_user_details(self, response):
        username = response['user']['name']
        fullname, first_name, last_name = self.get_user_names(
            fullname=response['user']['full_name'],
            first_name=response['user']['first_name'],
            last_name=response['user']['last_name']
        )
        email = response['user']['contact']['email_addresses'][0]['address']
        mugshot_url = response['user']['mugshot_url']
        return {
            'username': username,
            'email': email,
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name,
            'picture_url': mugshot_url
        }


class YammerStagingOAuth2(YammerOAuth2):
    name = 'yammer-staging'
    AUTHORIZATION_URL = 'https://www.staging.yammer.com/dialog/oauth'
    ACCESS_TOKEN_URL = 'https://www.staging.yammer.com/oauth2/access_token'
    REQUEST_TOKEN_URL = 'https://www.staging.yammer.com/oauth2/request_token'

########NEW FILE########
__FILENAME__ = yandex
"""
Yandex OpenID and OAuth2 support.

This contribution adds support for Yandex.ru OpenID service in the form
openid.yandex.ru/user. Username is retrieved from the identity url.

If username is not specified, OpenID 2.0 url used for authentication.
"""
from social.p3 import urlsplit
from social.backends.open_id import OpenIdAuth
from social.backends.oauth import BaseOAuth2


class YandexOpenId(OpenIdAuth):
    """Yandex OpenID authentication backend"""
    name = 'yandex-openid'
    URL = 'http://openid.yandex.ru'

    def get_user_id(self, details, response):
        return details['email'] or response.identity_url

    def get_user_details(self, response):
        """Generate username from identity url"""
        values = super(YandexOpenId, self).get_user_details(response)
        values['username'] = values.get('username') or\
                             urlsplit(response.identity_url)\
                                    .path.strip('/')
        values['email'] = values.get('email', '')
        return values


class YandexOAuth2(BaseOAuth2):
    """Legacy Yandex OAuth2 authentication backend"""
    name = 'yandex-oauth2'
    AUTHORIZATION_URL = 'https://oauth.yandex.com/authorize'
    ACCESS_TOKEN_URL = 'https://oauth.yandex.com/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(
            response.get('real_name') or response.get('display_name') or ''
        )
        return {'username': response.get('display_name'),
                'email': response.get('default_email') or
                         response.get('emails', [''])[0],
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, response, *args, **kwargs):
        return self.get_json('https://login.yandex.ru/info',
                             params={'oauth_token': access_token,
                                     'format': 'json'})


class YaruOAuth2(BaseOAuth2):
    name = 'yaru'
    AUTHORIZATION_URL = 'https://oauth.yandex.com/authorize'
    ACCESS_TOKEN_URL = 'https://oauth.yandex.com/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(
            response.get('real_name') or response.get('display_name') or ''
        )
        return {'username': response.get('display_name'),
                'email': response.get('default_email') or
                         response.get('emails', [''])[0],
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, response, *args, **kwargs):
        return self.get_json('https://login.yandex.ru/info',
                             params={'oauth_token': access_token,
                                     'format': 'json'})

########NEW FILE########
__FILENAME__ = exceptions
class SocialAuthBaseException(ValueError):
    """Base class for pipeline exceptions."""
    pass


class WrongBackend(SocialAuthBaseException):
    def __init__(self, backend_name):
        self.backend_name = backend_name

    def __str__(self):
        return 'Incorrect authentication service "{0}"'.format(
            self.backend_name
        )


class MissingBackend(WrongBackend):
    def __str__(self):
        return 'Missing backend "{0}" entry'.format(self.backend_name)


class NotAllowedToDisconnect(SocialAuthBaseException):
    """User is not allowed to disconnect it's social account."""
    pass


class AuthException(SocialAuthBaseException):
    """Auth process exception."""
    def __init__(self, backend, *args, **kwargs):
        self.backend = backend
        super(AuthException, self).__init__(*args, **kwargs)


class AuthFailed(AuthException):
    """Auth process failed for some reason."""
    def __str__(self):
        msg = super(AuthFailed, self).__str__()
        if msg == 'access_denied':
            return 'Authentication process was canceled'
        return 'Authentication failed: {0}'.format(msg)


class AuthCanceled(AuthException):
    """Auth process was canceled by user."""
    def __str__(self):
        return 'Authentication process canceled'


class AuthUnknownError(AuthException):
    """Unknown auth process error."""
    def __str__(self):
        msg = super(AuthUnknownError, self).__str__()
        return 'An unknown error happened while authenticating {0}'.format(msg)


class AuthTokenError(AuthException):
    """Auth token error."""
    def __str__(self):
        msg = super(AuthTokenError, self).__str__()
        return 'Token error: {0}'.format(msg)


class AuthMissingParameter(AuthException):
    """Missing parameter needed to start or complete the process."""
    def __init__(self, backend, parameter, *args, **kwargs):
        self.parameter = parameter
        super(AuthMissingParameter, self).__init__(backend, *args, **kwargs)

    def __str__(self):
        return 'Missing needed parameter {0}'.format(self.parameter)


class AuthStateMissing(AuthException):
    """State parameter is incorrect."""
    def __str__(self):
        return 'Session value state missing.'


class AuthStateForbidden(AuthException):
    """State parameter is incorrect."""
    def __str__(self):
        return 'Wrong state parameter given.'


class AuthAlreadyAssociated(AuthException):
    """A different user has already associated the target social account"""
    pass


class AuthTokenRevoked(AuthException):
    """User revoked the access_token in the provider."""
    def __str__(self):
        return 'User revoke access to the token'


class AuthForbidden(AuthException):
    """Authentication for this user is forbidden"""
    def __str__(self):
        return 'Your credentials aren\'t allowed'


class InvalidEmail(AuthException):
    def __str__(self):
        return 'Email couldn\'t be validated'

########NEW FILE########
__FILENAME__ = p3
import six
# Python3 support, keep import hacks here

if six.PY3:
    from urllib.parse import parse_qs, urlparse, urlunparse, quote, \
                             urlsplit, urlencode, unquote
    from io import StringIO
else:
    try:
        from urlparse import parse_qs
    except ImportError:  # fall back for Python 2.5
        from cgi import parse_qs
    from urlparse import urlparse, urlunparse, urlsplit
    from urllib import urlencode, unquote, quote
    from StringIO import StringIO

########NEW FILE########
__FILENAME__ = disconnect
from social.exceptions import NotAllowedToDisconnect


def allowed_to_disconnect(strategy, user, name, user_storage,
                          association_id=None, *args, **kwargs):
    if not user_storage.allowed_to_disconnect(user, name, association_id):
        raise NotAllowedToDisconnect()


def get_entries(strategy, user, name, user_storage, association_id=None,
                *args, **kwargs):
    return {
        'entries': user_storage.get_social_auth_for_user(
            user, name, association_id
        )
    }


def revoke_tokens(strategy, entries, *args, **kwargs):
    revoke_tokens = strategy.setting('REVOKE_TOKENS_ON_DISCONNECT', False)
    if revoke_tokens:
        for entry in entries:
            if 'access_token' in entry.extra_data:
                backend = entry.get_backend(strategy)(strategy)
                backend.revoke_token(entry.extra_data['access_token'],
                                     entry.uid)


def disconnect(strategy, entries, user_storage, *args, **kwargs):
    for entry in entries:
        user_storage.disconnect(entry)

########NEW FILE########
__FILENAME__ = mail
from social.exceptions import InvalidEmail
from social.pipeline.partial import partial


@partial
def mail_validation(strategy, details, *args, **kwargs):
    requires_validation = strategy.backend.REQUIRES_EMAIL_VALIDATION or \
                          strategy.setting('FORCE_EMAIL_VALIDATION', False)
    if requires_validation and details.get('email'):
        data = strategy.request_data()
        if 'verification_code' in data:
            strategy.session_pop('email_validation_address')
            if not strategy.validate_email(details['email'],
                                           data['verification_code']):
                raise InvalidEmail(strategy.backend)
        else:
            strategy.send_email_validation(details['email'])
            strategy.session_set('email_validation_address', details['email'])
            return strategy.redirect(strategy.setting('EMAIL_VALIDATION_URL'))

########NEW FILE########
__FILENAME__ = partial
from functools import wraps


def save_status_to_session(strategy, pipeline_index, *args, **kwargs):
    """Saves current social-auth status to session."""
    strategy.session_set('partial_pipeline',
                         strategy.partial_to_session(pipeline_index + 1,
                                                     *args, **kwargs))


def partial(func):
    @wraps(func)
    def wrapper(strategy, pipeline_index, *args, **kwargs):
        out = func(strategy=strategy, pipeline_index=pipeline_index,
                    *args, **kwargs) or {}
        if not isinstance(out, dict):
            values = strategy.partial_to_session(pipeline_index, *args,
                                                 **kwargs)
            strategy.session_set('partial_pipeline', values)
        return out
    return wrapper

########NEW FILE########
__FILENAME__ = social_auth
from social.exceptions import AuthAlreadyAssociated, AuthException, \
                              AuthForbidden


def social_details(strategy, response, *args, **kwargs):
    return {'details': strategy.backend.get_user_details(response)}


def social_uid(strategy, details, response, *args, **kwargs):
    return {'uid': strategy.backend.get_user_id(details, response)}


def auth_allowed(strategy, details, response, *args, **kwargs):
    if not strategy.backend.auth_allowed(response, details):
        raise AuthForbidden(strategy.backend)


def social_user(strategy, uid, user=None, *args, **kwargs):
    provider = strategy.backend.name
    social = strategy.storage.user.get_social_auth(provider, uid)
    if social:
        if user and social.user != user:
            msg = 'This {0} account is already in use.'.format(provider)
            raise AuthAlreadyAssociated(strategy.backend, msg)
        elif not user:
            user = social.user
    return {'social': social,
            'user': user,
            'is_new': user is None,
            'new_association': False}


def associate_user(strategy, uid, user=None, social=None, *args, **kwargs):
    if user and not social:
        try:
            social = strategy.storage.user.create_social_auth(
                user, uid, strategy.backend.name
            )
        except Exception as err:
            if not strategy.storage.is_integrity_error(err):
                raise
            # Protect for possible race condition, those bastard with FTL
            # clicking capabilities, check issue #131:
            #   https://github.com/omab/django-social-auth/issues/131
            return social_user(strategy, uid, user, *args, **kwargs)
        else:
            return {'social': social,
                    'user': social.user,
                    'new_association': True}


def associate_by_email(strategy, details, user=None, *args, **kwargs):
    """
    Associate current auth with a user with the same email address in the DB.

    This pipeline entry is not 100% secure unless you know that the providers
    enabled enforce email verification on their side, otherwise a user can
    attempt to take over another user account by using the same (not validated)
    email address on some provider.  This pipeline entry is disabled by
    default.
    """
    if user:
        return None

    email = details.get('email')
    if email:
        # Try to associate accounts registered with the same email address,
        # only if it's a single object. AuthException is raised if multiple
        # objects are returned.
        users = list(strategy.storage.user.get_users_by_email(email))
        if len(users) == 0:
            return None
        elif len(users) > 1:
            raise AuthException(
                strategy.backend,
                'The given email address is associated with another account'
            )
        else:
            return {'user': users[0]}


def load_extra_data(strategy, details, response, uid, user, *args, **kwargs):
    social = kwargs.get('social') or strategy.storage.user.get_social_auth(
        strategy.backend.name,
        uid
    )
    if social:
        extra_data = strategy.backend.extra_data(user, uid, response, details)
        social.set_extra_data(extra_data)

########NEW FILE########
__FILENAME__ = user
from uuid import uuid4

from social.utils import slugify, module_member


USER_FIELDS = ['username', 'email']


def get_username(strategy, details, user=None, *args, **kwargs):
    if 'username' not in strategy.setting('USER_FIELDS', USER_FIELDS):
        return
    storage = strategy.storage

    if not user:
        email_as_username = strategy.setting('USERNAME_IS_FULL_EMAIL', False)
        uuid_length = strategy.setting('UUID_LENGTH', 16)
        max_length = storage.user.username_max_length()
        do_slugify = strategy.setting('SLUGIFY_USERNAMES', False)
        do_clean = strategy.setting('CLEAN_USERNAMES', True)

        if do_clean:
            clean_func = storage.user.clean_username
        else:
            clean_func = lambda val: val

        if do_slugify:
            override_slug = strategy.setting('SLUGIFY_FUNCTION')
            if override_slug:
                slug_func = module_member(override_slug)
            else:
                slug_func = slugify
        else:
            slug_func = lambda val: val

        if email_as_username and details.get('email'):
            username = details['email']
        elif details.get('username'):
            username = details['username']
        else:
            username = uuid4().hex

        short_username = username[:max_length - uuid_length]
        final_username = slug_func(clean_func(username[:max_length]))

        # Generate a unique username for current user using username
        # as base but adding a unique hash at the end. Original
        # username is cut to avoid any field max_length.
        while storage.user.user_exists(username=final_username):
            username = short_username + uuid4().hex[:uuid_length]
            final_username = slug_func(clean_func(username[:max_length]))
    else:
        final_username = storage.user.get_username(user)
    return {'username': final_username}


def create_user(strategy, details, user=None, *args, **kwargs):
    if user:
        return {'is_new': False}

    fields = dict((name, kwargs.get(name) or details.get(name))
                        for name in strategy.setting('USER_FIELDS',
                                                      USER_FIELDS))
    if not fields:
        return

    return {
        'is_new': True,
        'user': strategy.create_user(**fields)
    }


def user_details(strategy, details, user=None, *args, **kwargs):
    """Update user details using data from provider."""
    if user:
        changed = False  # flag to track changes
        protected = strategy.setting('PROTECTED_USER_FIELDS', [])
        keep = ('username', 'id', 'pk') + tuple(protected)

        for name, value in details.items():
            # do not update username, it was already generated
            # do not update configured fields if user already existed
            if name not in keep and hasattr(user, name):
                if value and value != getattr(user, name, None):
                    try:
                        setattr(user, name, value)
                        changed = True
                    except AttributeError:
                        pass

        if changed:
            strategy.storage.user.changed(user)

########NEW FILE########
__FILENAME__ = base
"""Models mixins for Social Auth"""
import re
import time
import base64
import uuid
from datetime import datetime, timedelta

import six

from openid.association import Association as OpenIdAssociation

from social.backends.utils import get_backend
from social.strategies.utils import get_current_strategy


CLEAN_USERNAME_REGEX = re.compile(r'[^\w.@+-_]+', re.UNICODE)


class UserMixin(object):
    user = ''
    provider = ''
    uid = None
    extra_data = None

    def get_backend(self, strategy=None):
        strategy = strategy or get_current_strategy()
        if strategy:
            return get_backend(strategy.backends, self.provider)

    def get_backend_instance(self, strategy=None):
        strategy = strategy or get_current_strategy()
        Backend = self.get_backend(strategy)
        if Backend:
            return Backend(strategy=strategy)

    @property
    def tokens(self):
        """Return access_token stored in extra_data or None"""
        return self.extra_data.get('access_token')

    def refresh_token(self, strategy, *args, **kwargs):
        token = self.extra_data.get('refresh_token') or \
                self.extra_data.get('access_token')
        backend = self.get_backend(strategy)
        if token and backend and hasattr(backend, 'refresh_token'):
            backend = backend(strategy=strategy)
            response = backend.refresh_token(token, *args, **kwargs)
            access_token = response.get('access_token')
            refresh_token = response.get('refresh_token')

            if access_token or refresh_token:
                if access_token:
                    self.extra_data['access_token'] = access_token
                if refresh_token:
                    self.extra_data['refresh_token'] = refresh_token
                self.save()

    def expiration_datetime(self):
        """Return provider session live seconds. Returns a timedelta ready to
        use with session.set_expiry().

        If provider returns a timestamp instead of session seconds to live, the
        timedelta is inferred from current time (using UTC timezone). None is
        returned if there's no value stored or it's invalid.
        """
        if self.extra_data and 'expires' in self.extra_data:
            try:
                expires = int(self.extra_data.get('expires'))
            except (ValueError, TypeError):
                return None

            now = datetime.utcnow()

            # Detect if expires is a timestamp
            if expires > time.mktime(now.timetuple()):
                # expires is a datetime
                return datetime.fromtimestamp(expires) - now
            else:
                # expires is a timedelta
                return timedelta(seconds=expires)

    def set_extra_data(self, extra_data=None):
        if extra_data and self.extra_data != extra_data:
            if self.extra_data:
                self.extra_data.update(extra_data)
            else:
                self.extra_data = extra_data
            return True

    @classmethod
    def changed(cls, user):
        """The given user instance is ready to be saved"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def get_username(cls, user):
        """Return the username for given user"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def user_model(cls):
        """Return the user model"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def username_max_length(cls):
        """Return the max length for username"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def clean_username(cls, value):
        return CLEAN_USERNAME_REGEX.sub('', value)

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None):
        """Return if it's safe to disconnect the social account for the
        given user"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def disconnect(cls, entry):
        """Disconnect the social account for the given user"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def user_exists(cls, *args, **kwargs):
        """
        Return True/False if a User instance exists with the given arguments.
        Arguments are directly passed to filter() manager method.
        """
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def create_user(cls, *args, **kwargs):
        """Create a user instance"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def get_user(cls, pk):
        """Return user instance for given id"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def get_users_by_email(cls, email):
        """Return users instances for given email address"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def get_social_auth(cls, provider, uid):
        """Return UserSocialAuth for given provider and uid"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        """Return all the UserSocialAuth instances for given user"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        """Create a UserSocialAuth instance for given user"""
        raise NotImplementedError('Implement in subclass')


class NonceMixin(object):
    """One use numbers"""
    server_url = ''
    timestamp = 0
    salt = ''

    @classmethod
    def use(cls, server_url, timestamp, salt):
        """Create a Nonce instance"""
        raise NotImplementedError('Implement in subclass')


class AssociationMixin(object):
    """OpenId account association"""
    server_url = ''
    handle = ''
    secret = ''
    issued = 0
    lifetime = 0
    assoc_type = ''

    @classmethod
    def oids(cls, server_url, handle=None):
        kwargs = {'server_url': server_url}
        if handle is not None:
            kwargs['handle'] = handle
        return sorted([
            (assoc.id, cls.openid_association(assoc))
                for assoc in cls.get(**kwargs)
        ], key=lambda x: x[1].issued, reverse=True)

    @classmethod
    def openid_association(cls, assoc):
        secret = assoc.secret
        if not isinstance(secret, six.binary_type):
            secret = secret.encode()
        return OpenIdAssociation(assoc.handle, base64.decodestring(secret),
                                 assoc.issued, assoc.lifetime,
                                 assoc.assoc_type)

    @classmethod
    def store(cls, server_url, association):
        """Create an Association instance"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def get(cls, *args, **kwargs):
        """Get an Association instance"""
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def remove(cls, ids_to_delete):
        """Remove an Association instance"""
        raise NotImplementedError('Implement in subclass')


class CodeMixin(object):
    email = ''
    code = ''
    verified = False

    def verify(self):
        self.verified = True
        self.save()

    @classmethod
    def generate_code(cls):
        return uuid.uuid4().hex

    @classmethod
    def make_code(cls, email):
        code = cls()
        code.email = email
        code.code = cls.generate_code()
        code.verified = False
        code.save()
        return code

    @classmethod
    def get_code(cls, code):
        raise NotImplementedError('Implement in subclass')


class BaseStorage(object):
    user = UserMixin
    nonce = NonceMixin
    association = AssociationMixin
    code = CodeMixin

    @classmethod
    def is_integrity_error(cls, exception):
        """Check if given exception flags an integrity error in the DB"""
        raise NotImplementedError('Implement in subclass')

########NEW FILE########
__FILENAME__ = django_orm
"""Django ORM models for Social Auth"""
import base64
import six

from social.storage.base import UserMixin, AssociationMixin, NonceMixin, \
                                CodeMixin, BaseStorage


class DjangoUserMixin(UserMixin):
    """Social Auth association model"""
    @classmethod
    def changed(cls, user):
        user.save()

    def set_extra_data(self, extra_data=None):
        if super(DjangoUserMixin, self).set_extra_data(extra_data):
            self.save()

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None):
        if association_id is not None:
            qs = cls.objects.exclude(id=association_id)
        else:
            qs = cls.objects.exclude(provider=backend_name)
        qs = qs.filter(user=user)

        if hasattr(user, 'has_usable_password'):
            valid_password = user.has_usable_password()
        else:
            valid_password = True
        return valid_password or qs.count() > 0

    @classmethod
    def disconnect(cls, entry):
        entry.delete()

    @classmethod
    def username_field(cls):
        return getattr(cls.user_model(), 'USERNAME_FIELD', 'username')

    @classmethod
    def user_exists(cls, *args, **kwargs):
        """
        Return True/False if a User instance exists with the given arguments.
        Arguments are directly passed to filter() manager method.
        """
        if 'username' in kwargs:
            kwargs[cls.username_field()] = kwargs.pop('username')
        return cls.user_model().objects.filter(*args, **kwargs).count() > 0

    @classmethod
    def get_username(cls, user):
        return getattr(user, cls.username_field(), None)

    @classmethod
    def create_user(cls, *args, **kwargs):
        if 'username' in kwargs:
            kwargs[cls.username_field()] = kwargs.pop('username')
        return cls.user_model().objects.create_user(*args, **kwargs)

    @classmethod
    def get_user(cls, pk):
        try:
            return cls.user_model().objects.get(pk=pk)
        except cls.user_model().DoesNotExist:
            return None

    @classmethod
    def get_users_by_email(cls, email):
        return cls.user_model().objects.filter(email__iexact=email)

    @classmethod
    def get_social_auth(cls, provider, uid):
        if not isinstance(uid, six.string_types):
            uid = str(uid)
        try:
            return cls.objects.get(provider=provider, uid=uid)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        qs = user.social_auth.all()
        if provider:
            qs = qs.filter(provider=provider)
        if id:
            qs = qs.filter(id=id)
        return qs

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        if not isinstance(uid, six.string_types):
            uid = str(uid)
        return cls.objects.create(user=user, uid=uid, provider=provider)


class DjangoNonceMixin(NonceMixin):
    @classmethod
    def use(cls, server_url, timestamp, salt):
        return cls.objects.get_or_create(server_url=server_url,
                                         timestamp=timestamp,
                                         salt=salt)[1]


class DjangoAssociationMixin(AssociationMixin):
    @classmethod
    def store(cls, server_url, association):
        # Don't use get_or_create because issued cannot be null
        try:
            assoc = cls.objects.get(server_url=server_url,
                                    handle=association.handle)
        except cls.DoesNotExist:
            assoc = cls(server_url=server_url,
                        handle=association.handle)
        assoc.secret = base64.encodestring(association.secret)
        assoc.issued = association.issued
        assoc.lifetime = association.lifetime
        assoc.assoc_type = association.assoc_type
        assoc.save()

    @classmethod
    def get(cls, *args, **kwargs):
        return cls.objects.filter(*args, **kwargs)

    @classmethod
    def remove(cls, ids_to_delete):
        cls.objects.filter(pk__in=ids_to_delete).delete()


class DjangoCodeMixin(CodeMixin):
    @classmethod
    def get_code(cls, code):
        try:
            return cls.objects.get(code=code)
        except cls.DoesNotExist:
            return None


class BaseDjangoStorage(BaseStorage):
    user = DjangoUserMixin
    nonce = DjangoNonceMixin
    association = DjangoAssociationMixin
    code = DjangoCodeMixin

########NEW FILE########
__FILENAME__ = mongoengine_orm
import base64
import six

from mongoengine import DictField, IntField, StringField, \
                        EmailField, BooleanField
from mongoengine.queryset import OperationError

from social.storage.base import UserMixin, AssociationMixin, NonceMixin, \
                                CodeMixin, BaseStorage


UNUSABLE_PASSWORD = '!'  # Borrowed from django 1.4


class MongoengineUserMixin(UserMixin):
    """Social Auth association model"""
    user = None
    provider = StringField(max_length=32)
    uid = StringField(max_length=255, unique_with='provider')
    extra_data = DictField()

    def str_id(self):
        return str(self.id)

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        qs = cls.objects
        if provider:
            qs = qs.filter(provider=provider)
        if id:
            qs = qs.filter(id=id)
        return qs.filter(user=user.id)

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        if not isinstance(type(uid), six.string_types):
            uid = str(uid)
        return cls.objects.create(user=user.id, uid=uid, provider=provider)

    @classmethod
    def username_max_length(cls):
        username_field = cls.username_field()
        field = getattr(cls.user_model(), username_field)
        return field.max_length

    @classmethod
    def username_field(cls):
        return getattr(cls.user_model(), 'USERNAME_FIELD', 'username')

    @classmethod
    def create_user(cls, *args, **kwargs):
        kwargs['password'] = UNUSABLE_PASSWORD
        if 'email' in kwargs:
            # Empty string makes email regex validation fail
            kwargs['email'] = kwargs['email'] or None
        return cls.user_model().objects.create(*args, **kwargs)

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None):
        if association_id is not None:
            qs = cls.objects.filter(id__ne=association_id)
        else:
            qs = cls.objects.filter(provider__ne=backend_name)
        qs = qs.filter(user=user)

        if hasattr(user, 'has_usable_password'):
            valid_password = user.has_usable_password()
        else:
            valid_password = True

        return valid_password or qs.count() > 0

    @classmethod
    def changed(cls, user):
        user.save()

    def set_extra_data(self, extra_data=None):
        if super(MongoengineUserMixin, self).set_extra_data(extra_data):
            self.save()

    @classmethod
    def disconnect(cls, entry):
        entry.delete()

    @classmethod
    def user_exists(cls, *args, **kwargs):
        """
        Return True/False if a User instance exists with the given arguments.
        Arguments are directly passed to filter() manager method.
        """
        if 'username' in kwargs:
            kwargs[cls.username_field()] = kwargs.pop('username')
        return cls.user_model().objects.filter(*args, **kwargs).count() > 0

    @classmethod
    def get_username(cls, user):
        return getattr(user, cls.username_field(), None)

    @classmethod
    def get_user(cls, pk):
        try:
            return cls.user_model().objects.get(id=pk)
        except cls.user_model().DoesNotExist:
            return None

    @classmethod
    def get_users_by_email(cls, email):
        return cls.user_model().objects.filter(email__iexact=email)

    @classmethod
    def get_social_auth(cls, provider, uid):
        if not isinstance(uid, six.string_types):
            uid = str(uid)
        try:
            return cls.objects.get(provider=provider, uid=uid)
        except cls.DoesNotExist:
            return None


class MongoengineNonceMixin(NonceMixin):
    """One use numbers"""
    server_url = StringField(max_length=255)
    timestamp = IntField()
    salt = StringField(max_length=40)

    @classmethod
    def use(cls, server_url, timestamp, salt):
        return cls.objects.get_or_create(server_url=server_url,
                                         timestamp=timestamp,
                                         salt=salt)[1]


class MongoengineAssociationMixin(AssociationMixin):
    """OpenId account association"""
    server_url = StringField(max_length=255)
    handle = StringField(max_length=255)
    secret = StringField(max_length=255)  # Stored base64 encoded
    issued = IntField()
    lifetime = IntField()
    assoc_type = StringField(max_length=64)

    @classmethod
    def store(cls, server_url, association):
        # Don't use get_or_create because issued cannot be null
        try:
            assoc = cls.objects.get(server_url=server_url,
                                    handle=association.handle)
        except cls.DoesNotExist:
            assoc = cls(server_url=server_url,
                        handle=association.handle)
        assoc.secret = base64.encodestring(association.secret)
        assoc.issued = association.issued
        assoc.lifetime = association.lifetime
        assoc.assoc_type = association.assoc_type
        assoc.save()

    @classmethod
    def get(cls, *args, **kwargs):
        return cls.objects.filter(*args, **kwargs)

    @classmethod
    def remove(cls, ids_to_delete):
        cls.objects.filter(pk__in=ids_to_delete).delete()


class MongoengineCodeMixin(CodeMixin):
    email = EmailField()
    code = StringField(max_length=32)
    verified = BooleanField(default=False)

    @classmethod
    def get_code(cls, code):
        try:
            return cls.objects.get(code=code)
        except cls.DoesNotExist:
            return None


class BaseMongoengineStorage(BaseStorage):
    user = MongoengineUserMixin
    nonce = MongoengineNonceMixin
    association = MongoengineAssociationMixin
    code = MongoengineCodeMixin

    @classmethod
    def is_integrity_error(cls, exception):
        return exception.__class__ is OperationError and \
               'E11000' in exception.message

########NEW FILE########
__FILENAME__ = sqlalchemy_orm
"""SQLAlchemy models for Social Auth"""
import base64
import six

from sqlalchemy.exc import IntegrityError

from social.storage.base import UserMixin, AssociationMixin, NonceMixin, \
                                CodeMixin, BaseStorage


class SQLAlchemyMixin(object):
    COMMIT_SESSION = True

    @classmethod
    def _session(cls):
        raise NotImplementedError('Implement in subclass')

    @classmethod
    def _query(cls):
        return cls._session().query(cls)

    @classmethod
    def _new_instance(cls, model, *args, **kwargs):
        return cls._save_instance(model(*args, **kwargs))

    @classmethod
    def _save_instance(cls, instance):
        cls._session().add(instance)
        if cls.COMMIT_SESSION:
            cls._session().commit()
        return instance

    def save(self):
        self._save_instance(self)


class SQLAlchemyUserMixin(SQLAlchemyMixin, UserMixin):
    """Social Auth association model"""
    @classmethod
    def changed(cls, user):
        cls._save_instance(user)

    def set_extra_data(self, extra_data=None):
        if super(SQLAlchemyUserMixin, self).set_extra_data(extra_data):
            self._save_instance(self)

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None):
        if association_id is not None:
            qs = cls._query().filter(cls.id != association_id)
        else:
            qs = cls._query().filter(cls.provider != backend_name)
        qs = qs.filter(cls.user == user)

        if hasattr(user, 'has_usable_password'):  # TODO
            valid_password = user.has_usable_password()
        else:
            valid_password = True
        return valid_password or qs.count() > 0

    @classmethod
    def disconnect(cls, entry):
        cls._session().delete(entry)
        cls._session().commit()

    @classmethod
    def user_query(cls):
        return cls._session().query(cls.user_model())

    @classmethod
    def user_exists(cls, *args, **kwargs):
        """
        Return True/False if a User instance exists with the given arguments.
        Arguments are directly passed to filter() manager method.
        """
        return cls.user_query().filter_by(*args, **kwargs).count() > 0

    @classmethod
    def get_username(cls, user):
        return getattr(user, 'username', None)

    @classmethod
    def create_user(cls, *args, **kwargs):
        return cls._new_instance(cls.user_model(), *args, **kwargs)

    @classmethod
    def get_user(cls, pk):
        return cls.user_query().get(pk)

    @classmethod
    def get_users_by_email(cls, email):
        return cls.user_query().filter_by(email=email)

    @classmethod
    def get_social_auth(cls, provider, uid):
        if not isinstance(uid, six.string_types):
            uid = str(uid)
        try:
            return cls._query().filter_by(provider=provider,
                                          uid=uid)[0]
        except IndexError:
            return None

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        qs = cls._query().filter_by(user_id=user.id)
        if provider:
            qs = qs.filter_by(provider=provider)
        if id:
            qs = qs.filter_by(id=id)
        return qs

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        if not isinstance(uid, six.string_types):
            uid = str(uid)
        return cls._new_instance(cls, user=user, uid=uid, provider=provider)


class SQLAlchemyNonceMixin(SQLAlchemyMixin, NonceMixin):
    @classmethod
    def use(cls, server_url, timestamp, salt):
        kwargs = {'server_url': server_url, 'timestamp': timestamp,
                  'salt': salt}
        try:
            return cls._query().filter_by(**kwargs)[0]
        except IndexError:
            return cls._new_instance(cls, **kwargs)


class SQLAlchemyAssociationMixin(SQLAlchemyMixin, AssociationMixin):
    @classmethod
    def store(cls, server_url, association):
        # Don't use get_or_create because issued cannot be null
        try:
            assoc = cls._query().filter_by(server_url=server_url,
                                           handle=association.handle)[0]
        except IndexError:
            assoc = cls(server_url=server_url,
                        handle=association.handle)
        assoc.secret = base64.encodestring(association.secret)
        assoc.issued = association.issued
        assoc.lifetime = association.lifetime
        assoc.assoc_type = association.assoc_type
        cls._save_instance(assoc)

    @classmethod
    def get(cls, *args, **kwargs):
        return cls._query().filter_by(*args, **kwargs)

    @classmethod
    def remove(cls, ids_to_delete):
        cls._query().filter(cls.id.in_(ids_to_delete)).delete(
            synchronize_session='fetch'
        )


class SQLAlchemyCodeMixin(SQLAlchemyMixin, CodeMixin):
    @classmethod
    def get_code(cls, code):
        return cls._query().filter(cls.code == code).first()


class BaseSQLAlchemyStorage(BaseStorage):
    user = SQLAlchemyUserMixin
    nonce = SQLAlchemyNonceMixin
    association = SQLAlchemyAssociationMixin
    code = SQLAlchemyCodeMixin

    @classmethod
    def is_integrity_error(cls, exception):
        return exception.__class__ is IntegrityError

########NEW FILE########
__FILENAME__ = store
import time

try:
    import cPickle as pickle
except ImportError:
    import pickle

from openid.store.interface import OpenIDStore as BaseOpenIDStore
from openid.store.nonce import SKEW


class OpenIdStore(BaseOpenIDStore):
    """Storage class"""
    def __init__(self, strategy):
        """Init method"""
        super(OpenIdStore, self).__init__()
        self.strategy = strategy
        self.storage = strategy.storage
        self.assoc = self.storage.association
        self.nonce = self.storage.nonce
        self.max_nonce_age = 6 * 60 * 60  # Six hours

    def storeAssociation(self, server_url, association):
        """Store new assocition if doesn't exist"""
        self.assoc.store(server_url, association)

    def removeAssociation(self, server_url, handle):
        """Remove association"""
        associations_ids = list(dict(self.assoc.oids(server_url,
                                                     handle)).keys())
        if associations_ids:
            self.assoc.remove(associations_ids)

    def expiresIn(self, assoc):
        if hasattr(assoc, 'getExpiresIn'):
            return assoc.getExpiresIn()
        else:  # python3-openid 3.0.2
            return assoc.expiresIn

    def getAssociation(self, server_url, handle=None):
        """Return stored assocition"""
        associations, expired = [], []
        for assoc_id, association in self.assoc.oids(server_url, handle):
            expires = self.expiresIn(association)
            if expires > 0:
                associations.append(association)
            elif expires == 0:
                expired.append(assoc_id)

        if expired:  # clear expired associations
            self.assoc.remove(expired)

        if associations:  # return most recet association
            return associations[0]

    def useNonce(self, server_url, timestamp, salt):
        """Generate one use number and return *if* it was created"""
        if abs(timestamp - time.time()) > SKEW:
            return False
        return self.nonce.use(server_url, timestamp, salt)


class OpenIdSessionWrapper(dict):
    pickle_instances = (
        '_yadis_services__openid_consumer_',
        '_openid_consumer_last_token'
    )

    def __getitem__(self, name):
        value = super(OpenIdSessionWrapper, self).__getitem__(name)
        if name in self.pickle_instances:
            value = pickle.loads(value)
        return value

    def __setitem__(self, name, value):
        if name in self.pickle_instances:
            value = pickle.dumps(value, 0)
        super(OpenIdSessionWrapper, self).__setitem__(name, value)

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

########NEW FILE########
__FILENAME__ = base
import time
import random
import hashlib

import six

from social.utils import setting_name, module_member
from social.store import OpenIdStore, OpenIdSessionWrapper
from social.pipeline import DEFAULT_AUTH_PIPELINE, DEFAULT_DISCONNECT_PIPELINE


class BaseTemplateStrategy(object):
    def __init__(self, strategy):
        self.strategy = strategy

    def render(self, tpl=None, html=None, context=None):
        if not tpl and not html:
            raise ValueError('Missing template or html parameters')
        context = context or {}
        if tpl:
            return self.render_template(tpl, context)
        else:
            return self.render_string(html, context)

    def render_template(self, tpl, context):
        raise NotImplementedError('Implement in subclass')

    def render_string(self, html, context):
        raise NotImplementedError('Implement in subclass')


class BaseStrategy(object):
    ALLOWED_CHARS = 'abcdefghijklmnopqrstuvwxyz' \
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                    '0123456789'
    # well-known serializable types
    SERIALIZABLE_TYPES = (dict, list, tuple, set, bool, type(None)) + \
                         six.integer_types + six.string_types + \
                         (six.text_type, six.binary_type,)

    def __init__(self, backend=None, storage=None, request=None,
                 tpl=BaseTemplateStrategy, backends=None, *args, **kwargs):
        self.tpl = tpl(self)
        self.request = request
        self.storage = storage
        self.backends = backends
        self.backend = backend(strategy=self, *args, **kwargs) \
                            if backend else None

    def setting(self, name, default=None, backend=None):
        names = [setting_name(name), name]
        backend = backend or getattr(self, 'backend', None)
        if backend:
            names.insert(0, setting_name(backend.name, name))
        for name in names:
            try:
                return self.get_setting(name)
            except (AttributeError, KeyError):
                pass
        return default

    def start(self):
        # Clean any partial pipeline info before starting the process
        self.clean_partial_pipeline()
        if self.backend.uses_redirect():
            return self.redirect(self.backend.auth_url())
        else:
            return self.html(self.backend.auth_html())

    def complete(self, *args, **kwargs):
        return self.backend.auth_complete(*args, **kwargs)

    def continue_pipeline(self, *args, **kwargs):
        return self.backend.continue_pipeline(*args, **kwargs)

    def disconnect(self, user, association_id=None, *args, **kwargs):
        return self.backend.disconnect(
            user=user, association_id=association_id,
            *args, **kwargs
        )

    def authenticate(self, *args, **kwargs):
        kwargs['strategy'] = self
        kwargs['storage'] = self.storage
        kwargs['backend'] = self.backend
        return self.backend.authenticate(*args, **kwargs)

    def create_user(self, *args, **kwargs):
        return self.storage.user.create_user(*args, **kwargs)

    def get_user(self, *args, **kwargs):
        return self.storage.user.get_user(*args, **kwargs)

    def session_setdefault(self, name, value):
        self.session_set(name, value)
        return self.session_get(name)

    def openid_session_dict(self, name):
        # Many frameworks are switching the session serialization from Pickle
        # to JSON to avoid code execution risks. Flask did this from Flask
        # 0.10, Django is switching to JSON by default from version 1.6.
        #
        # Sadly python-openid stores classes instances in the session which
        # fails the JSON serialization, the classes are:
        #
        #   openid.yadis.manager.YadisServiceManager
        #   openid.consumer.discover.OpenIDServiceEndpoint
        #
        # This method will return a wrapper over the session value used with
        # openid (a dict) which will automatically keep a pickled value for the
        # mentioned classes.
        return OpenIdSessionWrapper(self.session_setdefault(name, {}))

    def to_session_value(self, val):
        return val

    def from_session_value(self, val):
        return val

    def partial_to_session(self, next, backend, request=None, *args, **kwargs):
        user = kwargs.get('user')
        social = kwargs.get('social')
        clean_kwargs = {
            'response': kwargs.get('response') or {},
            'details': kwargs.get('details') or {},
            'username': kwargs.get('username'),
            'uid': kwargs.get('uid'),
            'is_new': kwargs.get('is_new') or False,
            'new_association': kwargs.get('new_association') or False,
            'user': user and user.id or None,
            'social': social and {
                'provider': social.provider,
                'uid': social.uid
            } or None
        }
        clean_kwargs.update(kwargs)
        # Clean any MergeDict data type from the values
        clean_kwargs.update((name, dict(value))
                                for name, value in clean_kwargs.items()
                                    if isinstance(value, dict))
        return {
            'next': next,
            'backend': backend.name,
            'args': tuple(map(self.to_session_value, args)),
            'kwargs': dict((key, self.to_session_value(val))
                                for key, val in clean_kwargs.items()
                                   if isinstance(val, self.SERIALIZABLE_TYPES))
        }

    def partial_from_session(self, session):
        kwargs = session['kwargs'].copy()
        user = kwargs.get('user')
        social = kwargs.get('social')
        if isinstance(social, dict):
            kwargs['social'] = self.storage.user.get_social_auth(**social)
        if user:
            kwargs['user'] = self.storage.user.get_user(user)
        return (
            session['next'],
            session['backend'],
            list(map(self.from_session_value, session['args'])),
            dict((key, self.from_session_value(val))
                    for key, val in kwargs.items())
        )

    def clean_partial_pipeline(self, name='partial_pipeline'):
        self.session_pop(name)

    def openid_store(self):
        return OpenIdStore(self)

    def get_pipeline(self):
        return self.setting('PIPELINE', DEFAULT_AUTH_PIPELINE)

    def get_disconnect_pipeline(self):
        return self.setting('DISCONNECT_PIPELINE', DEFAULT_DISCONNECT_PIPELINE)

    def random_string(self, length=12, chars=ALLOWED_CHARS):
        # Implementation borrowed from django 1.4
        try:
            random.SystemRandom()
        except NotImplementedError:
            key = self.setting('SECRET_KEY', '')
            seed = '{0}{1}{2}'.format(random.getstate(), time.time(), key)
            random.seed(hashlib.sha256(seed.encode()).digest())
        return ''.join([random.choice(chars) for i in range(length)])

    def absolute_uri(self, path=None):
        uri = self.build_absolute_uri(path)
        if uri and self.setting('REDIRECT_IS_HTTPS'):
            uri = uri.replace('http://', 'https://')
        return uri

    def get_language(self):
        """Return current language"""
        return ''

    def send_email_validation(self, email):
        email_validation = self.setting('EMAIL_VALIDATION_FUNCTION')
        send_email = module_member(email_validation)
        code = self.storage.code.make_code(email)
        send_email(self, code)
        return code

    def validate_email(self, email, code):
        verification_code = self.storage.code.get_code(code)
        if not verification_code or verification_code.code != code:
            return False
        else:
            verification_code.verify()
            return True

    def render_html(self, tpl=None, html=None, context=None):
        """Render given template or raw html with given context"""
        return self.tpl.render(tpl, html, context)

    # Implement the following methods on strategies sub-classes

    def redirect(self, url):
        """Return a response redirect to the given URL"""
        raise NotImplementedError('Implement in subclass')

    def get_setting(self, name):
        """Return value for given setting name"""
        raise NotImplementedError('Implement in subclass')

    def html(self, content):
        """Return HTTP response with given content"""
        raise NotImplementedError('Implement in subclass')

    def request_data(self, merge=True):
        """Return current request data (POST or GET)"""
        raise NotImplementedError('Implement in subclass')

    def request_host(self):
        """Return current host value"""
        raise NotImplementedError('Implement in subclass')

    def session_get(self, name, default=None):
        """Return session value for given key"""
        raise NotImplementedError('Implement in subclass')

    def session_set(self, name, value):
        """Set session value for given key"""
        raise NotImplementedError('Implement in subclass')

    def session_pop(self, name):
        """Pop session value for given key"""
        raise NotImplementedError('Implement in subclass')

    def build_absolute_uri(self, path=None):
        """Build absolute URI with given (optional) path"""
        raise NotImplementedError('Implement in subclass')

########NEW FILE########
__FILENAME__ = cherrypy_strategy
import six
import cherrypy

from social.strategies.base import BaseStrategy, BaseTemplateStrategy


class CherryPyJinja2TemplateStrategy(BaseTemplateStrategy):
    def __init__(self, strategy):
        self.strategy = strategy
        self.env = cherrypy.tools.jinja2env

    def render_template(self, tpl, context):
        return self.env.get_template(tpl).render(context)

    def render_string(self, html, context):
        return self.env.from_string(html).render(context)


class CherryPyStrategy(BaseStrategy):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('tpl', CherryPyJinja2TemplateStrategy)
        return super(CherryPyStrategy, self).__init__(*args, **kwargs)

    def get_setting(self, name):
        return cherrypy.config[name]

    def request_data(self, merge=True):
        if merge:
            data = cherrypy.request.params
        elif cherrypy.request.method == 'POST':
            data = cherrypy.body.params
        else:
            data = cherrypy.request.params
        return data

    def request_host(self):
        return cherrypy.request.base

    def redirect(self, url):
        raise cherrypy.HTTPRedirect(url)

    def html(self, content):
        return content

    def authenticate(self, *args, **kwargs):
        kwargs['strategy'] = self
        kwargs['storage'] = self.storage
        kwargs['backend'] = self.backend
        return self.backend.authenticate(*args, **kwargs)

    def session_get(self, name, default=None):
        return cherrypy.session.get(name, default)

    def session_set(self, name, value):
        cherrypy.session[name] = value

    def session_pop(self, name):
        cherrypy.session.pop(name, None)

    def session_setdefault(self, name, value):
        return cherrypy.session.setdefault(name, value)

    def build_absolute_uri(self, path=None):
        return cherrypy.url(path or '')

    def is_response(self, value):
        return isinstance(value, six.string_types) or \
               isinstance(value, cherrypy.CherryPyException)

########NEW FILE########
__FILENAME__ = django_strategy
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Model
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import authenticate
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist, RequestContext, loader
from django.utils.datastructures import MergeDict
from django.utils.translation import get_language

from social.strategies.base import BaseStrategy, BaseTemplateStrategy


class DjangoTemplateStrategy(BaseTemplateStrategy):
    def render_template(self, tpl, context):
        template = loader.get_template(tpl)
        return template.render(RequestContext(self.strategy.request, context))

    def render_string(self, html, context):
        template = loader.get_template_from_string(html)
        return template.render(RequestContext(self.strategy.request, context))


class DjangoStrategy(BaseStrategy):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('tpl', DjangoTemplateStrategy)
        super(DjangoStrategy, self).__init__(*args, **kwargs)
        if self.request:
            self.session = self.request.session
        else:
            self.session = {}

    def get_setting(self, name):
        return getattr(settings, name)

    def request_data(self, merge=True):
        if not self.request:
            return {}
        if merge:
            data = self.request.REQUEST
        elif self.request.method == 'POST':
            data = self.request.POST
        else:
            data = self.request.GET
        return data

    def request_host(self):
        if self.request:
            return self.request.get_host()

    def redirect(self, url):
        return redirect(url)

    def html(self, content):
        return HttpResponse(content, content_type='text/html;charset=UTF-8')

    def render_html(self, tpl=None, html=None, context=None):
        if not tpl and not html:
            raise ValueError('Missing template or html parameters')
        context = context or {}
        try:
            template = loader.get_template(tpl)
        except TemplateDoesNotExist:
            template = loader.get_template_from_string(html)
        return template.render(RequestContext(self.request, context))

    def authenticate(self, *args, **kwargs):
        kwargs['strategy'] = self
        kwargs['storage'] = self.storage
        kwargs['backend'] = self.backend
        return authenticate(*args, **kwargs)

    def session_get(self, name, default=None):
        return self.session.get(name, default)

    def session_set(self, name, value):
        self.session[name] = value
        if hasattr(self.session, 'modified'):
            self.session.modified = True

    def session_pop(self, name):
        return self.session.pop(name, None)

    def session_setdefault(self, name, value):
        return self.session.setdefault(name, value)

    def build_absolute_uri(self, path=None):
        if self.request:
            return self.request.build_absolute_uri(path)
        else:
            return path

    def random_string(self, length=12, chars=BaseStrategy.ALLOWED_CHARS):
        try:
            from django.utils.crypto import get_random_string
        except ImportError:  # django < 1.4
            return super(DjangoStrategy, self).random_string(length, chars)
        else:
            return get_random_string(length, chars)

    def to_session_value(self, val):
        """Converts values that are instance of Model to a dictionary
        with enough information to retrieve the instance back later."""
        if isinstance(val, Model):
            val = {
                'pk': val.pk,
                'ctype': ContentType.objects.get_for_model(val).pk
            }
        if isinstance(val, MergeDict):
            val = dict(val)
        return val

    def from_session_value(self, val):
        """Converts back the instance saved by self._ctype function."""
        if isinstance(val, dict) and 'pk' in val and 'ctype' in val:
            ctype = ContentType.objects.get_for_id(val['ctype'])
            ModelClass = ctype.model_class()
            val = ModelClass.objects.get(pk=val['pk'])
        return val

    def get_language(self):
        """Return current language"""
        return get_language()

########NEW FILE########
__FILENAME__ = flask_strategy
from flask import current_app, request, redirect, make_response, session, \
                  render_template, render_template_string

from social.utils import build_absolute_uri
from social.strategies.base import BaseStrategy, BaseTemplateStrategy


class FlaskTemplateStrategy(BaseTemplateStrategy):
    def render_template(self, tpl, context):
        return render_template(tpl, **context)

    def render_string(self, html, context):
        return render_template_string(html, **context)


class FlaskStrategy(BaseStrategy):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('tpl', FlaskTemplateStrategy)
        super(FlaskStrategy, self).__init__(*args, **kwargs)

    def get_setting(self, name):
        return current_app.config[name]

    def request_data(self, merge=True):
        if merge:
            data = request.form.copy()
            data.update(request.args)
        elif request.method == 'POST':
            data = request.form
        else:
            data = request.args
        return data

    def request_host(self):
        return request.host

    def redirect(self, url):
        return redirect(url)

    def html(self, content):
        response = make_response(content)
        response.headers['Content-Type'] = 'text/html;charset=UTF-8'
        return response

    def session_get(self, name, default=None):
        return session.get(name, default)

    def session_set(self, name, value):
        session[name] = value

    def session_pop(self, name):
        return session.pop(name, None)

    def session_setdefault(self, name, value):
        return session.setdefault(name, value)

    def build_absolute_uri(self, path=None):
        return build_absolute_uri(request.host_url, path)

########NEW FILE########
__FILENAME__ = pyramid_strategy
from webob.multidict import NoVars

from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render

from social.utils import build_absolute_uri
from social.strategies.base import BaseStrategy, BaseTemplateStrategy


class PyramidTemplateStrategy(BaseTemplateStrategy):
    def render_template(self, tpl, context):
        return render(tpl, context, request=self.strategy.request)

    def render_string(self, html, context):
        return render(html, context, request=self.strategy.request)


class PyramidStrategy(BaseStrategy):
    def redirect(self, url):
        """Return a response redirect to the given URL"""
        return HTTPFound(location=url)

    def get_setting(self, name):
        """Return value for given setting name"""
        return self.request.registry.settings[name]

    def html(self, content):
        """Return HTTP response with given content"""
        return Response(body=content)

    def request_data(self, merge=True):
        """Return current request data (POST or GET)"""
        if self.request.method == 'POST':
            if merge:
                data = self.request.POST.copy()
                if not isinstance(self.request.GET, NoVars):
                    data.update(self.request.GET)
            else:
                data = self.request.POST
        else:
            data = self.request.GET
        return data

    def request_host(self):
        """Return current host value"""
        return self.request.host

    def session_get(self, name, default=None):
        """Return session value for given key"""
        return self.request.session.get(name, default)

    def session_set(self, name, value):
        """Set session value for given key"""
        self.request.session[name] = value

    def session_pop(self, name):
        """Pop session value for given key"""
        return self.request.session.pop(name, None)

    def build_absolute_uri(self, path=None):
        """Build absolute URI with given (optional) path"""
        return build_absolute_uri(self.request.host_url, path)

########NEW FILE########
__FILENAME__ = tornado_strategy
import json

from tornado.template import Loader, Template

from social.utils import build_absolute_uri
from social.strategies.base import BaseStrategy, BaseTemplateStrategy


class TornadoTemplateStrategy(BaseTemplateStrategy):
    def render_template(self, tpl, context):
        path, tpl = tpl.rsplit('/', 1)
        return Loader(path).load(tpl).generate(**context)

    def render_string(self, html, context):
        return Template(html).generate(**context)


class TornadoStrategy(BaseStrategy):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('tpl', TornadoTemplateStrategy)
        self.request_handler = kwargs.get('request_handler')
        super(TornadoStrategy, self).__init__(*args, **kwargs)

    def get_setting(self, name):
        return self.request_handler.settings[name]

    def request_data(self, merge=True):
        return self.request.arguments.copy()

    def request_host(self):
        return self.request.host

    def redirect(self, url):
        return self.request_handler.redirect(url)

    def html(self, content):
        self.request_handler.write(content)

    def session_get(self, name, default=None):
        return self.request_handler.get_secure_cookie(name, value=default)

    def session_set(self, name, value):
        self.request_handler.set_secure_cookie(name, str(value))

    def session_pop(self, name):
        value = self.request_handler.get_secure_cookie(name)
        self.request_handler.set_secure_cookie(name, '')
        return value

    def session_setdefault(self, name, value):
        pass

    def build_absolute_uri(self, path=None):
        return build_absolute_uri('{0}://{1}'.format(self.request.protocol,
                                                     self.request.host),
                                  path)

    def partial_to_session(self, next, backend, request=None, *args, **kwargs):
        return json.dumps(super(TornadoStrategy, self).partial_to_session(
            next, backend, request=request, *args, **kwargs
        ))

    def partial_from_session(self, session):
        if session:
            return super(TornadoStrategy, self).partial_to_session(
                json.loads(session)
            )

########NEW FILE########
__FILENAME__ = utils
from social.utils import module_member
from social.exceptions import MissingBackend
from social.backends.utils import get_backend


# Current strategy getter cache, currently only used by Django to set a method
# to get the current strategy which is latter used by backends get_user()
# method to retrieve the user saved in the session. Backends need an strategy
# to properly access the storage, but Django does not know about that when
# creates the backend instance, this method workarounds the problem.
_current_strategy_getter = None


def get_strategy(backends, strategy, storage, request=None, backend=None,
                 *args, **kwargs):
    if backend:
        Backend = get_backend(backends, backend)
        if not Backend:
            raise MissingBackend(backend)
    else:
        Backend = None
    Strategy = module_member(strategy)
    Storage = module_member(storage)
    return Strategy(Backend, Storage, request, backends=backends,
                    *args, **kwargs)


def set_current_strategy_getter(func):
    global _current_strategy_getter
    _current_strategy_getter = func


def get_current_strategy():
    global _current_strategy_getter
    if _current_strategy_getter is not None:
        return _current_strategy_getter()

########NEW FILE########
__FILENAME__ = webpy_strategy
import web

from social.strategies.base import BaseStrategy, BaseTemplateStrategy


class WebpyTemplateStrategy(BaseTemplateStrategy):
    def render_template(self, tpl, context):
        return web.template.render(tpl)(**context)

    def render_string(self, html, context):
        return web.template.Template(html)(**context)


class WebpyStrategy(BaseStrategy):
    def __init__(self, *args, **kwargs):
        self.session = web.web_session
        kwargs.setdefault('tpl', WebpyTemplateStrategy)
        super(WebpyStrategy, self).__init__(*args, **kwargs)

    def get_setting(self, name):
        return getattr(web.config, name)

    def request_data(self, merge=True):
        if merge:
            data = web.input(_method='both')
        elif web.ctx.method == 'POST':
            data = web.input(_method='post')
        else:
            data = web.input(_method='get')
        return data

    def request_host(self):
        return self.request.host

    def redirect(self, url):
        return web.seeother(url)

    def html(self, content):
        web.header('Content-Type', 'text/html;charset=UTF-8')
        return content

    def render_html(self, tpl=None, html=None, context=None):
        if not tpl and not html:
            raise ValueError('Missing template or html parameters')
        context = context or {}
        if tpl:
            tpl = web.template.frender(tpl)
        else:
            tpl = web.template.Template(html)
        return tpl(**context)

    def session_get(self, name, default=None):
        return self.session.get(name, default)

    def session_set(self, name, value):
        self.session[name] = value

    def session_pop(self, name):
        return self.session.pop(name, None)

    def session_setdefault(self, name, value):
        return self.session.setdefault(name, value)

    def build_absolute_uri(self, path=None):
        path = path or ''
        if path.startswith('http://') or path.startswith('https://'):
            return path
        return web.ctx.protocol + '://' + web.ctx.host + path

########NEW FILE########
__FILENAME__ = actions
import json
import requests
import unittest

from sure import expect
from httpretty import HTTPretty

from social.utils import parse_qs, module_member
from social.p3 import urlparse
from social.actions import do_auth, do_complete

from social.tests.models import TestStorage, User, TestUserSocialAuth, \
                                TestNonce, TestAssociation
from social.tests.strategy import TestStrategy


class BaseActionTest(unittest.TestCase):
    user_data_url = 'https://api.github.com/user'
    login_redirect_url = '/success'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'login': 'foobar',
        'id': 1,
        'avatar_url': 'https://github.com/images/error/foobar_happy.gif',
        'gravatar_id': 'somehexcode',
        'url': 'https://api.github.com/users/foobar',
        'name': 'monalisa foobar',
        'company': 'GitHub',
        'blog': 'https://github.com/blog',
        'location': 'San Francisco',
        'email': 'foo@bar.com',
        'hireable': False,
        'bio': 'There once was...',
        'public_repos': 2,
        'public_gists': 1,
        'followers': 20,
        'following': 0,
        'html_url': 'https://github.com/foobar',
        'created_at': '2008-01-14T04:33:35Z',
        'type': 'User',
        'total_private_repos': 100,
        'owned_private_repos': 100,
        'private_gists': 81,
        'disk_usage': 10000,
        'collaborators': 8,
        'plan': {
            'name': 'Medium',
            'space': 400,
            'collaborators': 10,
            'private_repos': 20
        }
    })

    def setUp(self):
        HTTPretty.enable()
        User.reset_cache()
        TestUserSocialAuth.reset_cache()
        TestNonce.reset_cache()
        TestAssociation.reset_cache()
        self.backend = module_member('social.backends.github.GithubOAuth2')
        self.strategy = TestStrategy(self.backend, TestStorage)
        self.user = None

    def tearDown(self):
        self.backend = None
        self.strategy = None
        self.user = None
        User.reset_cache()
        User.set_active(True)
        TestUserSocialAuth.reset_cache()
        TestNonce.reset_cache()
        TestAssociation.reset_cache()
        HTTPretty.disable()

    def do_login(self, after_complete_checks=True, user_data_body=None,
                 expected_username=None):
        self.strategy.set_settings({
            'SOCIAL_AUTH_GITHUB_KEY': 'a-key',
            'SOCIAL_AUTH_GITHUB_SECRET': 'a-secret-key',
            'SOCIAL_AUTH_LOGIN_REDIRECT_URL': self.login_redirect_url,
            'SOCIAL_AUTH_AUTHENTICATION_BACKENDS': (
                'social.backends.github.GithubOAuth2',
            )
        })
        start_url = do_auth(self.strategy).url
        target_url = self.strategy.build_absolute_uri(
            '/complete/github/?code=foobar'
        )

        start_query = parse_qs(urlparse(start_url).query)
        location_url = target_url + ('?' in target_url and '&' or '?') + \
                       'state=' + start_query['state']
        location_query = parse_qs(urlparse(location_url).query)

        HTTPretty.register_uri(HTTPretty.GET, start_url, status=301,
                               location=location_url)
        HTTPretty.register_uri(HTTPretty.GET, location_url, status=200,
                               body='foobar')

        response = requests.get(start_url)
        expect(response.url).to.equal(location_url)
        expect(response.text).to.equal('foobar')

        HTTPretty.register_uri(HTTPretty.GET,
                               uri=self.backend.ACCESS_TOKEN_URL,
                               status=200,
                               body=self.access_token_body or '',
                               content_type='text/json')

        if self.user_data_url:
            user_data_body = user_data_body or self.user_data_body or ''
            HTTPretty.register_uri(HTTPretty.GET, self.user_data_url,
                                   body=user_data_body,
                                   content_type='text/json')
        self.strategy.set_request_data(location_query)
        redirect = do_complete(
            self.strategy,
            user=self.user,
            login=lambda strategy, user, social_user:
                    strategy.session_set('username', user.username)
        )
        if after_complete_checks:
            expect(self.strategy.session_get('username')).to.equal(
                expected_username or self.expected_username
            )
            expect(redirect.url).to.equal(self.login_redirect_url)
        return redirect

    def do_login_with_partial_pipeline(self, before_complete=None):
        self.strategy.set_settings({
            'SOCIAL_AUTH_GITHUB_KEY': 'a-key',
            'SOCIAL_AUTH_GITHUB_SECRET': 'a-secret-key',
            'SOCIAL_AUTH_LOGIN_REDIRECT_URL': self.login_redirect_url,
            'SOCIAL_AUTH_AUTHENTICATION_BACKENDS': (
                'social.backends.github.GithubOAuth2',
            ),
            'SOCIAL_AUTH_PIPELINE': (
                'social.pipeline.social_auth.social_details',
                'social.pipeline.social_auth.social_uid',
                'social.pipeline.social_auth.auth_allowed',
                'social.pipeline.partial.save_status_to_session',
                'social.tests.pipeline.ask_for_password',
                'social.pipeline.social_auth.social_user',
                'social.pipeline.user.get_username',
                'social.pipeline.user.create_user',
                'social.pipeline.social_auth.associate_user',
                'social.pipeline.social_auth.load_extra_data',
                'social.tests.pipeline.set_password',
                'social.pipeline.user.user_details'
            )
        })
        start_url = do_auth(self.strategy).url
        target_url = self.strategy.build_absolute_uri(
            '/complete/github/?code=foobar'
        )

        start_query = parse_qs(urlparse(start_url).query)
        location_url = target_url + ('?' in target_url and '&' or '?') + \
                       'state=' + start_query['state']
        location_query = parse_qs(urlparse(location_url).query)

        HTTPretty.register_uri(HTTPretty.GET, start_url, status=301,
                               location=location_url)
        HTTPretty.register_uri(HTTPretty.GET, location_url, status=200,
                               body='foobar')

        response = requests.get(start_url)
        expect(response.url).to.equal(location_url)
        expect(response.text).to.equal('foobar')

        HTTPretty.register_uri(HTTPretty.GET,
                               uri=self.backend.ACCESS_TOKEN_URL,
                               status=200,
                               body=self.access_token_body or '',
                               content_type='text/json')

        if self.user_data_url:
            HTTPretty.register_uri(HTTPretty.GET, self.user_data_url,
                                   body=self.user_data_body or '',
                                   content_type='text/json')
        self.strategy.set_request_data(location_query)

        def _login(strategy, user, social_user):
            strategy.session_set('username', user.username)

        redirect = do_complete(self.strategy, user=self.user, login=_login)
        url = self.strategy.build_absolute_uri('/password')
        expect(redirect.url).to.equal(url)
        HTTPretty.register_uri(HTTPretty.GET, redirect.url, status=200,
                               body='foobar')
        HTTPretty.register_uri(HTTPretty.POST, redirect.url, status=200)

        password = 'foobar'
        requests.get(url)
        requests.post(url, data={'password': password})
        data = parse_qs(HTTPretty.last_request.body)
        expect(data['password']).to.equal(password)
        self.strategy.session_set('password', data['password'])

        if before_complete:
            before_complete()
        redirect = do_complete(self.strategy, user=self.user, login=_login)
        expect(self.strategy.session_get('username')).to.equal(
            self.expected_username
        )
        expect(redirect.url).to.equal(self.login_redirect_url)

########NEW FILE########
__FILENAME__ = test_associate
import json
from sure import expect

from social.exceptions import AuthAlreadyAssociated

from social.tests.models import User
from social.tests.actions.actions import BaseActionTest


class AssociateActionTest(BaseActionTest):
    expected_username = 'foobar'

    def setUp(self):
        super(AssociateActionTest, self).setUp()
        self.user = User(username='foobar', email='foo@bar.com')

    def test_associate(self):
        self.do_login()
        expect(len(self.user.social)).to.equal(1)
        expect(self.user.social[0].provider).to.equal('github')

    def test_associate_with_partial_pipeline(self):
        self.do_login_with_partial_pipeline()
        expect(len(self.user.social)).to.equal(1)
        expect(self.user.social[0].provider).to.equal('github')


class MultipleAccountsTest(AssociateActionTest):
    alternative_user_data_body = json.dumps({
        'login': 'foobar2',
        'id': 2,
        'avatar_url': 'https://github.com/images/error/foobar2_happy.gif',
        'gravatar_id': 'somehexcode',
        'url': 'https://api.github.com/users/foobar2',
        'name': 'monalisa foobar2',
        'company': 'GitHub',
        'blog': 'https://github.com/blog',
        'location': 'San Francisco',
        'email': 'foo@bar.com',
        'hireable': False,
        'bio': 'There once was...',
        'public_repos': 2,
        'public_gists': 1,
        'followers': 20,
        'following': 0,
        'html_url': 'https://github.com/foobar2',
        'created_at': '2008-01-14T04:33:35Z',
        'type': 'User',
        'total_private_repos': 100,
        'owned_private_repos': 100,
        'private_gists': 81,
        'disk_usage': 10000,
        'collaborators': 8,
        'plan': {
            'name': 'Medium',
            'space': 400,
            'collaborators': 10,
            'private_repos': 20
        }
    })

    def test_multiple_social_accounts(self):
        self.do_login()
        self.do_login(user_data_body=self.alternative_user_data_body)
        expect(len(self.user.social)).to.equal(2)
        expect(self.user.social[0].provider).to.equal('github')
        expect(self.user.social[1].provider).to.equal('github')


class AlreadyAssociatedErrorTest(BaseActionTest):
    def setUp(self):
        super(AlreadyAssociatedErrorTest, self).setUp()
        self.user1 = User(username='foobar', email='foo@bar.com')
        self.user = None

    def tearDown(self):
        super(AlreadyAssociatedErrorTest, self).tearDown()
        self.user1 = None
        self.user = None

    def test_already_associated_error(self):
        self.user = self.user1
        self.do_login()
        self.user = User(username='foobar2', email='foo2@bar2.com')
        self.do_login.when.called_with().should.throw(
            AuthAlreadyAssociated,
            'This github account is already in use.'
        )

########NEW FILE########
__FILENAME__ = test_disconnect
import requests

from sure import expect
from httpretty import HTTPretty

from social.actions import do_disconnect
from social.exceptions import NotAllowedToDisconnect
from social.utils import parse_qs

from social.tests.models import User
from social.tests.actions.actions import BaseActionTest


class DisconnectActionTest(BaseActionTest):
    def test_not_allowed_to_disconnect(self):
        self.do_login()
        user = User.get(self.expected_username)
        do_disconnect.when.called_with(self.strategy, user).should.throw(
            NotAllowedToDisconnect
        )

    def test_disconnect(self):
        self.do_login()
        user = User.get(self.expected_username)
        user.password = 'password'
        do_disconnect(self.strategy, user)
        expect(len(user.social)).to.equal(0)

    def test_disconnect_with_partial_pipeline(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_DISCONNECT_PIPELINE': (
                'social.pipeline.partial.save_status_to_session',
                'social.tests.pipeline.ask_for_password',
                'social.tests.pipeline.set_password',
                'social.pipeline.disconnect.allowed_to_disconnect',
                'social.pipeline.disconnect.get_entries',
                'social.pipeline.disconnect.revoke_tokens',
                'social.pipeline.disconnect.disconnect'
            )
        })
        self.do_login()
        user = User.get(self.expected_username)
        redirect = do_disconnect(self.strategy, user)

        url = self.strategy.build_absolute_uri('/password')
        expect(redirect.url).to.equal(url)
        HTTPretty.register_uri(HTTPretty.GET, redirect.url, status=200,
                               body='foobar')
        HTTPretty.register_uri(HTTPretty.POST, redirect.url, status=200)

        password = 'foobar'
        requests.get(url)
        requests.post(url, data={'password': password})
        data = parse_qs(HTTPretty.last_request.body)
        expect(data['password']).to.equal(password)
        self.strategy.session_set('password', data['password'])

        redirect = do_disconnect(self.strategy, user)
        expect(len(user.social)).to.equal(0)

########NEW FILE########
__FILENAME__ = test_login
from sure import expect

from social.tests.models import User
from social.tests.actions.actions import BaseActionTest


class LoginActionTest(BaseActionTest):
    def test_login(self):
        self.do_login()

    def test_login_with_partial_pipeline(self):
        self.do_login_with_partial_pipeline()

    def test_fields_stored_in_session(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_FIELDS_STORED_IN_SESSION': ['foo', 'bar']
        })
        self.strategy.set_request_data({'foo': '1', 'bar': '2'})
        self.do_login()
        expect(self.strategy.session_get('foo')).to.equal('1')
        expect(self.strategy.session_get('bar')).to.equal('2')

    def test_redirect_value(self):
        self.strategy.set_request_data({'next': '/after-login'})
        redirect = self.do_login(after_complete_checks=False)
        expect(redirect.url).to.equal('/after-login')

    def test_login_with_invalid_partial_pipeline(self):
        def before_complete():
            partial = self.strategy.session_get('partial_pipeline')
            partial['backend'] = 'foobar'
            self.strategy.session_set('partial_pipeline', partial)
        self.do_login_with_partial_pipeline(before_complete)

    def test_new_user(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_NEW_USER_REDIRECT_URL': '/new-user'
        })
        redirect = self.do_login(after_complete_checks=False)
        expect(redirect.url).to.equal('/new-user')

    def test_inactive_user(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_INACTIVE_USER_URL': '/inactive'
        })
        User.set_active(False)
        redirect = self.do_login(after_complete_checks=False)
        expect(redirect.url).to.equal('/inactive')

    def test_invalid_user(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_LOGIN_ERROR_URL': '/error',
            'SOCIAL_AUTH_PIPELINE': (
                'social.pipeline.social_auth.social_details',
                'social.pipeline.social_auth.social_uid',
                'social.pipeline.social_auth.auth_allowed',
                'social.pipeline.social_auth.social_user',
                'social.pipeline.user.get_username',
                'social.pipeline.user.create_user',
                'social.pipeline.social_auth.associate_user',
                'social.pipeline.social_auth.load_extra_data',
                'social.pipeline.user.user_details',
                'social.tests.pipeline.remove_user'
            )
        })
        redirect = self.do_login(after_complete_checks=False)
        expect(redirect.url).to.equal('/error')

########NEW FILE########
__FILENAME__ = base
import unittest
import requests

from sure import expect
from httpretty import HTTPretty

from social.utils import module_member, parse_qs
from social.backends.utils import user_backends_data, load_backends
from social.tests.strategy import TestStrategy
from social.tests.models import User, TestUserSocialAuth, TestNonce, \
                                TestAssociation, TestCode, TestStorage


class BaseBackendTest(unittest.TestCase):
    backend = None
    backend_path = None
    name = None
    complete_url = ''
    raw_complete_url = '/complete/{0}'

    def setUp(self):
        HTTPretty.enable()
        self.backend = module_member(self.backend_path)
        self.strategy = TestStrategy(self.backend, TestStorage)
        self.name = self.backend.name.upper().replace('-', '_')
        self.complete_url = self.strategy.build_absolute_uri(
            self.raw_complete_url.format(self.backend.name)
        )
        backends = (self.backend_path,
                    'social.tests.backends.test_broken.BrokenBackendAuth')
        self.strategy.set_settings({
            'SOCIAL_AUTH_AUTHENTICATION_BACKENDS': backends
        })
        self.strategy.set_settings(self.extra_settings())
        # Force backends loading to trash PSA cache
        load_backends(backends, force_load=True)
        User.reset_cache()
        TestUserSocialAuth.reset_cache()
        TestNonce.reset_cache()
        TestAssociation.reset_cache()
        TestCode.reset_cache()

    def tearDown(self):
        HTTPretty.disable()
        self.backend = None
        self.strategy = None
        self.name = None
        self.complete_url = None
        User.reset_cache()
        TestUserSocialAuth.reset_cache()
        TestNonce.reset_cache()
        TestAssociation.reset_cache()
        TestCode.reset_cache()

    def extra_settings(self):
        return {}

    def do_start(self):
        raise NotImplementedError('Implement in subclass')

    def do_login(self):
        user = self.do_start()
        username = self.expected_username
        expect(user.username).to.equal(username)
        expect(self.strategy.session_get('username')).to.equal(username)
        expect(self.strategy.get_user(user.id)).to.equal(user)
        expect(self.strategy.backend.get_user(user.id)).to.equal(user)
        user_backends = user_backends_data(
            user,
            self.strategy.get_setting('SOCIAL_AUTH_AUTHENTICATION_BACKENDS'),
            self.strategy.storage
        )
        expect(len(list(user_backends.keys()))).to.equal(3)
        expect('associated' in user_backends).to.equal(True)
        expect('not_associated' in user_backends).to.equal(True)
        expect('backends' in user_backends).to.equal(True)
        expect(len(user_backends['associated'])).to.equal(1)
        expect(len(user_backends['not_associated'])).to.equal(1)
        expect(len(user_backends['backends'])).to.equal(2)
        return user

    def pipeline_settings(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_PIPELINE': (
                'social.pipeline.social_auth.social_details',
                'social.pipeline.social_auth.social_uid',
                'social.pipeline.social_auth.auth_allowed',
                'social.pipeline.partial.save_status_to_session',
                'social.tests.pipeline.ask_for_password',
                'social.tests.pipeline.ask_for_slug',
                'social.pipeline.social_auth.social_user',
                'social.pipeline.user.get_username',
                'social.pipeline.social_auth.associate_by_email',
                'social.pipeline.user.create_user',
                'social.pipeline.social_auth.associate_user',
                'social.pipeline.social_auth.load_extra_data',
                'social.tests.pipeline.set_password',
                'social.tests.pipeline.set_slug',
                'social.pipeline.user.user_details'
            )
        })

    def pipeline_handlers(self, url):
        HTTPretty.register_uri(HTTPretty.GET, url, status=200, body='foobar')
        HTTPretty.register_uri(HTTPretty.POST, url, status=200)

    def pipeline_password_handling(self, url):
        password = 'foobar'
        requests.get(url)
        requests.post(url, data={'password': password})

        data = parse_qs(HTTPretty.last_request.body)
        expect(data['password']).to.equal(password)
        self.strategy.session_set('password', data['password'])
        return password

    def pipeline_slug_handling(self, url):
        slug = 'foo-bar'
        requests.get(url)
        requests.post(url, data={'slug': slug})

        data = parse_qs(HTTPretty.last_request.body)
        expect(data['slug']).to.equal(slug)
        self.strategy.session_set('slug', data['slug'])
        return slug

    def do_partial_pipeline(self):
        url = self.strategy.build_absolute_uri('/password')
        self.pipeline_settings()
        redirect = self.do_start()
        expect(redirect.url).to.equal(url)
        self.pipeline_handlers(url)

        password = self.pipeline_password_handling(url)
        data = self.strategy.session_pop('partial_pipeline')
        idx, backend, xargs, xkwargs = self.strategy.partial_from_session(data)
        expect(backend).to.equal(self.backend.name)
        redirect = self.strategy.continue_pipeline(pipeline_index=idx,
                                                   *xargs, **xkwargs)

        url = self.strategy.build_absolute_uri('/slug')
        expect(redirect.url).to.equal(url)
        self.pipeline_handlers(url)
        slug = self.pipeline_slug_handling(url)

        data = self.strategy.session_pop('partial_pipeline')
        idx, backend, xargs, xkwargs = self.strategy.partial_from_session(data)
        expect(backend).to.equal(self.backend.name)
        user = self.strategy.continue_pipeline(pipeline_index=idx,
                                               *xargs, **xkwargs)

        expect(user.username).to.equal(self.expected_username)
        expect(user.slug).to.equal(slug)
        expect(user.password).to.equal(password)
        return user

########NEW FILE########
__FILENAME__ = legacy
import requests

from sure import expect
from httpretty import HTTPretty

from social.utils import parse_qs
from social.tests.backends.base import BaseBackendTest


class BaseLegacyTest(BaseBackendTest):
    form = ''
    response_body = ''

    def setUp(self):
        super(BaseLegacyTest, self).setUp()
        self.strategy.set_settings({
            'SOCIAL_AUTH_{0}_FORM_URL'.format(self.name):
                self.strategy.build_absolute_uri(
                    '/login/{0}'.format(self.backend.name)
                )
        })

    def extra_settings(self):
        return {'SOCIAL_AUTH_{0}_FORM_URL'.format(self.name):
                    '/login/{0}'.format(self.backend.name)}

    def do_start(self):
        start_url = self.strategy.build_absolute_uri(self.strategy.start().url)
        HTTPretty.register_uri(
            HTTPretty.GET,
            start_url,
            status=200,
            body=self.form.format(self.complete_url)
        )
        HTTPretty.register_uri(
            HTTPretty.POST,
            self.complete_url,
            status=200,
            body=self.response_body,
            content_type='application/x-www-form-urlencoded'
        )
        response = requests.get(start_url)
        expect(response.text).to.equal(self.form.format(self.complete_url))
        response = requests.post(
            self.complete_url,
            data=parse_qs(self.response_body)
        )
        self.strategy.set_request_data(parse_qs(response.text))
        return self.strategy.complete()

########NEW FILE########
__FILENAME__ = oauth
import requests

from sure import expect
from httpretty import HTTPretty

from social.p3 import urlparse
from social.utils import parse_qs

from social.tests.models import User
from social.tests.backends.base import BaseBackendTest


class BaseOAuthTest(BaseBackendTest):
    backend = None
    backend_path = None
    user_data_body = None
    user_data_url = ''
    user_data_content_type = 'application/json'
    access_token_body = None
    access_token_status = 200
    expected_username = ''

    def extra_settings(self):
        return {'SOCIAL_AUTH_' + self.name + '_KEY': 'a-key',
                'SOCIAL_AUTH_' + self.name + '_SECRET': 'a-secret-key'}

    def _method(self, method):
        return {'GET': HTTPretty.GET,
                'POST': HTTPretty.POST}[method]

    def handle_state(self, start_url, target_url):
        try:
            if self.backend.STATE_PARAMETER or self.backend.REDIRECT_STATE:
                query = parse_qs(urlparse(start_url).query)
                target_url = target_url + ('?' in target_url and '&' or '?')
                if 'state' in query or 'redirect_state' in query:
                    name = 'state' in query and 'state' or 'redirect_state'
                    target_url += '{0}={1}'.format(name, query[name])
        except AttributeError:
            pass
        return target_url

    def auth_handlers(self, start_url):
        target_url = self.handle_state(start_url,
                                       self.strategy.build_absolute_uri(
                                           self.complete_url
                                       ))
        HTTPretty.register_uri(HTTPretty.GET,
                               start_url,
                               status=301,
                               location=target_url)
        HTTPretty.register_uri(HTTPretty.GET,
                               target_url,
                               status=200,
                               body='foobar')
        HTTPretty.register_uri(self._method(self.backend.ACCESS_TOKEN_METHOD),
                               uri=self.backend.ACCESS_TOKEN_URL,
                               status=self.access_token_status,
                               body=self.access_token_body or '',
                               content_type='text/json')
        if self.user_data_url:
            HTTPretty.register_uri(HTTPretty.GET,
                                   self.user_data_url,
                                   body=self.user_data_body or '',
                                   content_type=self.user_data_content_type)
        return target_url

    def do_start(self):
        start_url = self.strategy.start().url
        target_url = self.auth_handlers(start_url)
        response = requests.get(start_url)
        expect(response.url).to.equal(target_url)
        expect(response.text).to.equal('foobar')
        self.strategy.set_request_data(parse_qs(urlparse(target_url).query))
        return self.strategy.complete()


class OAuth1Test(BaseOAuthTest):
    request_token_body = None
    raw_complete_url = '/complete/{0}/?oauth_verifier=bazqux&' \
                                      'oauth_token=foobar'

    def request_token_handler(self):
        HTTPretty.register_uri(self._method(self.backend.REQUEST_TOKEN_METHOD),
                               self.backend.REQUEST_TOKEN_URL,
                               body=self.request_token_body,
                               status=200)

    def do_start(self):
        self.request_token_handler()
        return super(OAuth1Test, self).do_start()


class OAuth2Test(BaseOAuthTest):
    raw_complete_url = '/complete/{0}/?code=foobar'
    refresh_token_body = ''

    def refresh_token_arguments(self):
        return {}

    def do_refresh_token(self):
        self.do_login()
        HTTPretty.register_uri(self._method(self.backend.REFRESH_TOKEN_METHOD),
                               self.backend.REFRESH_TOKEN_URL or
                               self.backend.ACCESS_TOKEN_URL,
                               status=200,
                               body=self.refresh_token_body)
        user = list(User.cache.values())[0]
        social = user.social[0]
        social.refresh_token(strategy=self.strategy,
                             **self.refresh_token_arguments())
        return user, social

########NEW FILE########
__FILENAME__ = open_id
# -*- coding: utf-8 -*-
import sys
import requests
from openid import oidutil

PY3 = sys.version_info[0] == 3

if PY3:
    from html.parser import HTMLParser
    HTMLParser  # placate pyflakes
else:
    from HTMLParser import HTMLParser

from httpretty import HTTPretty

sys.path.insert(0, '..')

from social.utils import parse_qs, module_member
from social.backends.utils import load_backends

from social.tests.backends.base import BaseBackendTest
from social.tests.models import TestStorage, User, TestUserSocialAuth, \
                                TestNonce, TestAssociation
from social.tests.strategy import TestStrategy


# Patch to remove the too-verbose output until a new version is released
oidutil.log = lambda *args, **kwargs: None


class FormHTMLParser(HTMLParser):
    form = {}
    inputs = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.form.update(attrs)
        elif tag == 'input' and 'name' in attrs:
            self.inputs[attrs['name']] = attrs['value']


class OpenIdTest(BaseBackendTest):
    backend_path = None
    backend = None
    access_token_body = None
    user_data_body = None
    user_data_url = ''
    expected_username = ''
    settings = None
    partial_login_settings = None
    raw_complete_url = '/complete/{0}/'

    def setUp(self):
        HTTPretty.enable()
        self.backend = module_member(self.backend_path)
        name = self.backend.name
        self.complete_url = self.raw_complete_url.format(name)
        self.strategy = TestStrategy(self.backend, TestStorage,
                                     redirect_uri=self.complete_url)
        self.strategy.set_settings({
            'SOCIAL_AUTH_AUTHENTICATION_BACKENDS': (
                self.backend_path,
                'social.tests.backends.test_broken.BrokenBackendAuth'
            )
        })
        # Force backends loading to trash PSA cache
        load_backends(
            self.strategy.get_setting('SOCIAL_AUTH_AUTHENTICATION_BACKENDS'),
            force_load=True
        )

    def tearDown(self):
        self.strategy = None
        User.reset_cache()
        TestUserSocialAuth.reset_cache()
        TestNonce.reset_cache()
        TestAssociation.reset_cache()
        HTTPretty.disable()

    def get_form_data(self, html):
        parser = FormHTMLParser()
        parser.feed(html)
        return parser.form, parser.inputs

    def openid_url(self):
        return self.strategy.backend.openid_url()

    def post_start(self):
        pass

    def do_start(self):
        HTTPretty.register_uri(HTTPretty.GET,
                               self.openid_url(),
                               status=200,
                               body=self.discovery_body,
                               content_type='application/xrds+xml')
        start = self.strategy.start()
        self.post_start()
        form, inputs = self.get_form_data(start)
        HTTPretty.register_uri(HTTPretty.POST,
                               form.get('action'),
                               status=200,
                               body=self.server_response)
        response = requests.post(form.get('action'), data=inputs)
        self.strategy.set_request_data(parse_qs(response.content))
        HTTPretty.register_uri(HTTPretty.POST,
                               form.get('action'),
                               status=200,
                               body='is_valid:true\n')
        return self.strategy.complete()

########NEW FILE########
__FILENAME__ = test_amazon
import json

from social.tests.backends.oauth import OAuth2Test


class AmazonOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.amazon.AmazonOAuth2'
    user_data_url = 'https://www.amazon.com/ap/user/profile'
    expected_username = 'FooBar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'user_id': 'amzn1.account.ABCDE1234',
        'email': 'foo@bar.com',
        'name': 'Foo Bar'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class AmazonOAuth2BrokenServerResponseTest(OAuth2Test):
    backend_path = 'social.backends.amazon.AmazonOAuth2'
    user_data_url = 'https://www.amazon.com/ap/user/profile'
    expected_username = 'FooBar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'Request-Id': '02GGTU7CWMNFTV3KH3J6',
        'Profile': {
            'Name': 'Foo Bar',
            'CustomerId': 'amzn1.account.ABCDE1234',
            'PrimaryEmail': 'foo@bar.com'
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_angel
import json

from social.tests.backends.oauth import OAuth2Test


class AngelOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.angel.AngelOAuth2'
    user_data_url = 'https://api.angel.co/1/me/'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'facebook_url': 'http://www.facebook.com/foobar',
        'bio': None,
        'name': 'Foo Bar',
        'roles': [],
        'github_url': None,
        'angellist_url': 'https://angel.co/foobar',
        'image': 'https://graph.facebook.com/foobar/picture?type=square',
        'linkedin_url': None,
        'locations': [],
        'twitter_url': None,
        'what_ive_built': None,
        'dribbble_url': None,
        'behance_url': None,
        'blog_url': None,
        'aboutme_url': None,
        'follower_count': 0,
        'online_bio_url': None,
        'id': 101010
    })
    expected_username = 'foobar'

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_behance
import json

from social.tests.backends.oauth import OAuth2Test


class BehanceOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.behance.BehanceOAuth2'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'valid': 1,
        'user': {
            'username': 'foobar',
            'city': 'Foo City',
            'first_name': 'Foo',
            'last_name': 'Bar',
            'display_name': 'Foo Bar',
            'url': 'http://www.behance.net/foobar',
            'country': 'Fooland',
            'company': '',
            'created_on': 1355152329,
            'state': '',
            'fields': [
                'Programming',
                'Web Design',
                'Web Development'
            ],
            'images': {
                '32': 'https://www.behance.net/assets/img/profile/'
                      'no-image-32.jpg',
                '50': 'https://www.behance.net/assets/img/profile/'
                      'no-image-50.jpg',
                '115': 'https://www.behance.net/assets/img/profile/'
                       'no-image-138.jpg',
                '129': 'https://www.behance.net/assets/img/profile/'
                       'no-image-138.jpg',
                '138': 'https://www.behance.net/assets/img/profile/'
                       'no-image-138.jpg',
                '78': 'https://www.behance.net/assets/img/profile/'
                      'no-image-78.jpg'
            },
            'id': 1010101,
            'occupation': 'Software Developer'
        }
    })
    expected_username = 'foobar'

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_bitbucket
import json
from httpretty import HTTPretty

from social.p3 import urlencode
from social.exceptions import AuthForbidden
from social.tests.backends.oauth import OAuth1Test


class BitbucketOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.bitbucket.BitbucketOAuth'
    user_data_url = 'https://bitbucket.org/api/1.0/users/foo@bar.com'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    emails_body = json.dumps([{
        'active': True,
        'email': 'foo@bar.com',
        'primary': True
    }])
    user_data_body = json.dumps({
        'user': {
            'username': 'foobar',
            'first_name': 'Foo',
            'last_name': 'Bar',
            'display_name': 'Foo Bar',
            'is_team': False,
            'avatar': 'https://secure.gravatar.com/avatar/'
                      '5280f15cedf540b544eecc30fcf3027c?'
                      'd=https%3A%2F%2Fd3oaxc4q5k2d6q.cloudfront.net%2Fm%2F'
                      '9e262ba34f96%2Fimg%2Fdefault_avatar%2F32%2F'
                      'user_blue.png&s=32',
            'resource_uri': '/1.0/users/foobar'
        }
    })

    def test_login(self):
        HTTPretty.register_uri(HTTPretty.GET,
                               'https://bitbucket.org/api/1.0/emails/',
                               status=200, body=self.emails_body)
        self.do_login()

    def test_partial_pipeline(self):
        HTTPretty.register_uri(HTTPretty.GET,
                               'https://bitbucket.org/api/1.0/emails/',
                               status=200, body=self.emails_body)
        self.do_partial_pipeline()


class BitbucketOAuth1FailTest(BitbucketOAuth1Test):
    emails_body = json.dumps([{
        'active': False,
        'email': 'foo@bar.com',
        'primary': True
    }])

    def test_login(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_BITBUCKET_VERIFIED_EMAILS_ONLY': True
        })
        super(BitbucketOAuth1FailTest, self).test_login \
            .when.called_with().should.throw(AuthForbidden)

    def test_partial_pipeline(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_BITBUCKET_VERIFIED_EMAILS_ONLY': True
        })
        super(BitbucketOAuth1FailTest, self).test_partial_pipeline \
            .when.called_with().should.throw(AuthForbidden)

########NEW FILE########
__FILENAME__ = test_box
import json

from sure import expect

from social.tests.backends.oauth import OAuth2Test


class BoxOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.box.BoxOAuth2'
    user_data_url = 'https://api.box.com/2.0/users/me'
    expected_username = 'sean+awesome@box.com'
    access_token_body = json.dumps({
        'access_token': 'T9cE5asGnuyYCCqIZFoWjFHvNbvVqHjl',
        'expires_in': 3600,
        'restricted_to': [],
        'token_type': 'bearer',
        'refresh_token': 'J7rxTiWOHMoSC1isKZKBZWizoRXjkQzig5C6jFgCVJ9bU'
                         'nsUfGMinKBDLZWP9BgR'
    })
    user_data_body = json.dumps({
        'type': 'user',
        'id': '181216415',
        'name': 'sean rose',
        'login': 'sean+awesome@box.com',
        'created_at': '2012-05-03T21:39:11-07:00',
        'modified_at': '2012-11-14T11:21:32-08:00',
        'role': 'admin',
        'language': 'en',
        'space_amount': 11345156112,
        'space_used': 1237009912,
        'max_upload_size': 2147483648,
        'tracking_codes': [],
        'can_see_managed_users': True,
        'is_sync_enabled': True,
        'status': 'active',
        'job_title': '',
        'phone': '6509241374',
        'address': '',
        'avatar_url': 'https://www.box.com/api/avatar/large/181216415',
        'is_exempt_from_device_limits': False,
        'is_exempt_from_login_verification': False,
        'enterprise': {
            'type': 'enterprise',
            'id': '17077211',
            'name': 'seanrose enterprise'
        }
    })
    refresh_token_body = json.dumps({
        'access_token': 'T9cE5asGnuyYCCqIZFoWjFHvNbvVqHjl',
        'expires_in': 3600,
        'restricted_to': [],
        'token_type': 'bearer',
        'refresh_token': 'J7rxTiWOHMoSC1isKZKBZWizoRXjkQzig5C6jFgCVJ9b'
                         'UnsUfGMinKBDLZWP9BgR'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

    def refresh_token_arguments(self):
        uri = self.strategy.build_absolute_uri('/complete/box/')
        return {'redirect_uri': uri}

    def test_refresh_token(self):
        user, social = self.do_refresh_token()
        expect(social.extra_data['access_token']).to.equal(
            'T9cE5asGnuyYCCqIZFoWjFHvNbvVqHjl'
        )

########NEW FILE########
__FILENAME__ = test_broken
import unittest

from social.backends.base import BaseAuth


class BrokenBackendAuth(BaseAuth):
    name = 'broken'


class BrokenBackendTest(unittest.TestCase):
    def setUp(self):
        self.backend = BrokenBackendAuth()

    def tearDown(self):
        self.backend = None

    def test_auth_url(self):
        self.backend.auth_url.when.called_with().should.throw(
            NotImplementedError,
            'Implement in subclass'
        )

    def test_auth_html(self):
        self.backend.auth_html.when.called_with().should.throw(
            NotImplementedError,
            'Implement in subclass'
        )

    def test_auth_complete(self):
        self.backend.auth_complete.when.called_with().should.throw(
            NotImplementedError,
            'Implement in subclass'
        )

    def test_get_user_details(self):
        self.backend.get_user_details.when.called_with(None).should.throw(
            NotImplementedError,
            'Implement in subclass'
        )

########NEW FILE########
__FILENAME__ = test_clef
import json

from social.tests.backends.oauth import OAuth2Test


class ClefOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.clef.ClefOAuth2'
    user_data_url = 'https://clef.io/api/v1/info'
    expected_username = '123456789'
    access_token_body = json.dumps({
        'access_token': 'foobar'
    })
    user_data_body = json.dumps({
        'info': {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com'
        },
        'clef_id': '123456789'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_coinbase
import json

from social.tests.backends.oauth import OAuth2Test


class CoinbaseOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.coinbase.CoinbaseOAuth2'
    user_data_url = 'https://coinbase.com/api/v1/users'
    expected_username = 'SatoshiNakamoto'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'users': [
            {
                'user': {
                    'id': "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    'name': "Satoshi Nakamoto",
                    'email': "satoshi@nakamoto.com",
                    'pin': None,
                    'time_zone': "Eastern Time (US & Canada)",
                    'native_currency': "USD",
                    'buy_level': 2,
                    'sell_level': 2,
                    'balance': {
                        'amount': "1000000",
                        'currency': "BTC"
                    },
                    'buy_limit': {
                        'amount': "50.00000000",
                        'currency': "BTC"
                    },
                    'sell_limit': {
                        'amount': "50.00000000",
                        'currency': "BTC"
                    }
                }
            }
        ]
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_dailymotion
import json

from social.tests.backends.oauth import OAuth2Test


class DailymotionOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.dailymotion.DailymotionOAuth2'
    user_data_url = 'https://api.dailymotion.com/me/'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'id': 'foobar',
        'screenname': 'foobar'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_disqus
import json

from social.tests.backends.oauth import OAuth2Test


class DisqusOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.disqus.DisqusOAuth2'
    user_data_url = 'https://disqus.com/api/3.0/users/details.json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'code': 0,
        'response': {
            'username': 'foobar',
            'numFollowers': 0,
            'isFollowing': False,
            'numFollowing': 0,
            'name': 'Foo Bar',
            'numPosts': 0,
            'url': '',
            'isAnonymous': False,
            'rep': 1.231755,
            'about': '',
            'isFollowedBy': False,
            'connections': {},
            'emailHash': '5280f14cedf530b544aecc31fcfe0240',
            'reputation': 1.231755,
            'avatar': {
                'small': {
                    'permalink': 'https://disqus.com/api/users/avatars/'
                                 'foobar.jpg',
                    'cache': 'https://securecdn.disqus.com/uploads/'
                             'users/453/4556/avatar32.jpg?1285535379'
                },
                'isCustom': False,
                'permalink': 'https://disqus.com/api/users/avatars/foobar.jpg',
                'cache': 'https://securecdn.disqus.com/uploads/users/453/'
                         '4556/avatar92.jpg?1285535379',
                'large': {
                    'permalink': 'https://disqus.com/api/users/avatars/'
                                 'foobar.jpg',
                    'cache': 'https://securecdn.disqus.com/uploads/users/'
                             '453/4556/avatar92.jpg?1285535379'
                }
            },
            'profileUrl': 'http://disqus.com/foobar/',
            'numLikesReceived': 0,
            'isPrimary': True,
            'joinedAt': '2010-09-26T21:09:39',
            'id': '1010101',
            'location': ''
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_dropbox
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class DropboxOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.dropbox.DropboxOAuth'
    user_data_url = 'https://api.dropbox.com/1/account/info'
    expected_username = '10101010'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_body = json.dumps({
        'referral_link': 'https://www.dropbox.com/referrals/foobar',
        'display_name': 'Foo Bar',
        'uid': 10101010,
        'country': 'US',
        'quota_info': {
            'shared': 138573,
            'quota': 2952790016,
            'normal': 157327
        },
        'email': 'foo@bar.com'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_dummy
import json
import datetime
import time

from sure import expect
from httpretty import HTTPretty

from social.actions import do_disconnect
from social.backends.oauth import BaseOAuth2
from social.exceptions import AuthForbidden

from social.tests.models import User
from social.tests.backends.oauth import OAuth2Test


class DummyOAuth2(BaseOAuth2):
    name = 'dummy'
    AUTHORIZATION_URL = 'http://dummy.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'http://dummy.com/oauth/access_token'
    REVOKE_TOKEN_URL = 'https://dummy.com/oauth/revoke'
    REVOKE_TOKEN_METHOD = 'GET'
    EXTRA_DATA = [
        ('id', 'id'),
        ('expires', 'expires'),
        ('empty', 'empty', True),
        'url'
    ]

    def get_user_details(self, response):
        """Return user details from Github account"""
        return {'username': response.get('username'),
                'email': response.get('email', ''),
                'first_name': response.get('first_name', ''),
                'last_name': response.get('last_name', '')}

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        return self.get_json('http://dummy.com/user', params={
            'access_token': access_token
        })


class DummyOAuth2Test(OAuth2Test):
    backend_path = 'social.tests.backends.test_dummy.DummyOAuth2'
    user_data_url = 'http://dummy.com/user'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'id': 1,
        'username': 'foobar',
        'url': 'http://dummy.com/user/foobar',
        'first_name': 'Foo',
        'last_name': 'Bar',
        'email': 'foo@bar.com'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

    def test_tokens(self):
        user = self.do_login()
        expect(user.social[0].tokens).to.equal('foobar')

    def test_revoke_token(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_REVOKE_TOKENS_ON_DISCONNECT': True
        })
        self.do_login()
        user = User.get(self.expected_username)
        user.password = 'password'
        backend = self.backend
        HTTPretty.register_uri(self._method(backend.REVOKE_TOKEN_METHOD),
                               backend.REVOKE_TOKEN_URL,
                               status=200)
        do_disconnect(self.strategy, user)


class WhitelistEmailsTest(DummyOAuth2Test):
    def test_valid_login(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_WHITELISTED_EMAILS': ['foo@bar.com']
        })
        self.do_login()

    def test_invalid_login(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_WHITELISTED_EMAILS': ['foo2@bar.com']
        })
        self.do_login.when.called_with().should.throw(AuthForbidden)


class WhitelistDomainsTest(DummyOAuth2Test):
    def test_valid_login(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_WHITELISTED_DOMAINS': ['bar.com']
        })
        self.do_login()

    def test_invalid_login(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_WHITELISTED_EMAILS': ['bar2.com']
        })
        self.do_login.when.called_with().should.throw(AuthForbidden)


DELTA = datetime.timedelta(days=1)


class ExpirationTimeTest(DummyOAuth2Test):
    user_data_body = json.dumps({
        'id': 1,
        'username': 'foobar',
        'url': 'http://dummy.com/user/foobar',
        'first_name': 'Foo',
        'last_name': 'Bar',
        'email': 'foo@bar.com',
        'expires': time.mktime((datetime.datetime.utcnow() +
                                DELTA).timetuple())
    })

    def test_expires_time(self):
        user = self.do_login()
        social = user.social[0]
        expiration = social.expiration_datetime()
        expect(expiration <= DELTA).to.equal(True)

########NEW FILE########
__FILENAME__ = test_email
from social.tests.backends.legacy import BaseLegacyTest


class EmailTest(BaseLegacyTest):
    backend_path = 'social.backends.email.EmailAuth'
    expected_username = 'foo'
    response_body = 'email=foo@bar.com'
    form = """
    <form method="post" action="{0}">
        <input name="email" type="text">
        <button>Submit</button>
    </form>
    """

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_evernote
from requests import HTTPError

from social.p3 import urlencode
from social.exceptions import AuthCanceled

from social.tests.backends.oauth import OAuth1Test


class EvernoteOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.evernote.EvernoteOAuth'
    expected_username = '101010'
    access_token_body = urlencode({
        'edam_webApiUrlPrefix': 'https://sandbox.evernote.com/shard/s1/',
        'edam_shard': 's1',
        'oauth_token': 'foobar',
        'edam_expires': '1395118279645',
        'edam_userId': '101010',
        'edam_noteStoreUrl': 'https://sandbox.evernote.com/shard/s1/notestore'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class EvernoteOAuth1CanceledTest(EvernoteOAuth1Test):
    access_token_status = 401

    def test_login(self):
        self.do_login.when.called_with().should.throw(AuthCanceled)

    def test_partial_pipeline(self):
        self.do_partial_pipeline.when.called_with().should.throw(AuthCanceled)


class EvernoteOAuth1ErrorTest(EvernoteOAuth1Test):
    access_token_status = 500

    def test_login(self):
        self.do_login.when.called_with().should.throw(HTTPError)

    def test_partial_pipeline(self):
        self.do_partial_pipeline.when.called_with().should.throw(HTTPError)

########NEW FILE########
__FILENAME__ = test_facebook
import json

from social.p3 import urlencode
from social.exceptions import AuthUnknownError

from social.tests.backends.oauth import OAuth2Test


class FacebookOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.facebook.FacebookOAuth2'
    user_data_url = 'https://graph.facebook.com/me'
    expected_username = 'foobar'
    access_token_body = urlencode({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'username': 'foobar',
        'first_name': 'Foo',
        'last_name': 'Bar',
        'verified': True,
        'name': 'Foo Bar',
        'gender': 'male',
        'updated_time': '2013-02-13T14:59:42+0000',
        'link': 'http://www.facebook.com/foobar',
        'id': '110011001100010'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class FacebookOAuth2WrongUserDataTest(FacebookOAuth2Test):
    user_data_body = 'null'

    def test_login(self):
        self.do_login.when.called_with().should.throw(AuthUnknownError)

    def test_partial_pipeline(self):
        self.do_partial_pipeline.when.called_with().should.throw(
            AuthUnknownError
        )

########NEW FILE########
__FILENAME__ = test_fitbit
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class FitbitOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.fitbit.FitbitOAuth'
    expected_username = 'foobar'
    access_token_body = urlencode({
        'oauth_token_secret': 'a-secret',
        'encoded_user_id': '101010',
        'oauth_token': 'foobar'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_url = 'https://api.fitbit.com/1/user/-/profile.json'
    user_data_body = json.dumps({
        'user': {
            'weightUnit': 'en_US',
            'strideLengthWalking': 0,
            'displayName': 'foobar',
            'weight': 62.6,
            'foodsLocale': 'en_US',
            'heightUnit': 'en_US',
            'locale': 'en_US',
            'gender': 'NA',
            'memberSince': '2011-12-26',
            'offsetFromUTCMillis': -25200000,
            'height': 0,
            'timezone': 'America/Los_Angeles',
            'dateOfBirth': '',
            'encodedId': '101010',
            'avatar': 'http://www.fitbit.com/images/profile/'
                      'defaultProfile_100_male.gif',
            'waterUnit': 'en_US',
            'distanceUnit': 'en_US',
            'glucoseUnit': 'en_US',
            'strideLengthRunning': 0
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_flickr
from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class FlickrOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.flickr.FlickrOAuth'
    expected_username = 'foobar'
    access_token_body = urlencode({
        'oauth_token_secret': 'a-secret',
        'username': 'foobar',
        'oauth_token': 'foobar',
        'user_nsid': '10101010@N01'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_foursquare
import json

from social.tests.backends.oauth import OAuth2Test


class FoursquareOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.foursquare.FoursquareOAuth2'
    user_data_url = 'https://api.foursquare.com/v2/users/self'
    expected_username = 'FooBar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'notifications': [{
            'item': {
                'unreadCount': 0
            },
            'type': 'notificationTray'
        }],
        'meta': {
            'errorType': 'deprecated',
            'code': 200,
            'errorDetail': 'Please provide an API version to avoid future '
                           'errors.See http://bit.ly/vywCav'
        },
        'response': {
            'user': {
                'photo': 'https://is0.4sqi.net/userpix_thumbs/'
                         'BYKIT01VN4T4BISN.jpg',
                'pings': False,
                'homeCity': 'Foo, Bar',
                'id': '1010101',
                'badges': {
                    'count': 0,
                    'items': []
                },
                'friends': {
                    'count': 1,
                    'groups': [{
                        'count': 0,
                        'items': [],
                        'type': 'friends',
                        'name': 'Mutual friends'
                    }, {
                        'count': 1,
                        'items': [{
                            'bio': '',
                            'gender': 'male',
                            'firstName': 'Baz',
                            'relationship': 'friend',
                            'photo': 'https://is0.4sqi.net/userpix_thumbs/'
                                     'BYKIT01VN4T4BISN.jpg',
                            'lists': {
                                'groups': [{
                                    'count': 1,
                                    'items': [],
                                    'type': 'created'
                                }]
                            },
                            'homeCity': 'Baz, Qux',
                            'lastName': 'Qux',
                            'tips': {
                                'count': 0
                            },
                            'id': '10101010'
                        }],
                        'type': 'others',
                        'name': 'Other friends'
                    }]
                },
                'referralId': 'u-1010101',
                'tips': {
                    'count': 0
                },
                'type': 'user',
                'todos': {
                    'count': 0
                },
                'bio': '',
                'relationship': 'self',
                'lists': {
                    'groups': [{
                        'count': 1,
                        'items': [],
                        'type': 'created'
                    }]
                },
                'photos': {
                    'count': 0,
                    'items': []
                },
                'checkinPings': 'off',
                'scores': {
                    'max': 0,
                    'checkinsCount': 0,
                    'goal': 50,
                    'recent': 0
                },
                'checkins': {
                    'count': 0
                },
                'firstName': 'Foo',
                'gender': 'male',
                'contact': {
                    'email': 'foo@bar.com'
                },
                'lastName': 'Bar',
                'following': {
                    'count': 0
                },
                'requests': {
                    'count': 0
                },
                'mayorships': {
                    'count': 0,
                    'items': []
                }
            }
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_github
import json

from httpretty import HTTPretty

from social.exceptions import AuthFailed

from social.tests.backends.oauth import OAuth2Test


class GithubOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.github.GithubOAuth2'
    user_data_url = 'https://api.github.com/user'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'login': 'foobar',
        'id': 1,
        'avatar_url': 'https://github.com/images/error/foobar_happy.gif',
        'gravatar_id': 'somehexcode',
        'url': 'https://api.github.com/users/foobar',
        'name': 'monalisa foobar',
        'company': 'GitHub',
        'blog': 'https://github.com/blog',
        'location': 'San Francisco',
        'email': 'foo@bar.com',
        'hireable': False,
        'bio': 'There once was...',
        'public_repos': 2,
        'public_gists': 1,
        'followers': 20,
        'following': 0,
        'html_url': 'https://github.com/foobar',
        'created_at': '2008-01-14T04:33:35Z',
        'type': 'User',
        'total_private_repos': 100,
        'owned_private_repos': 100,
        'private_gists': 81,
        'disk_usage': 10000,
        'collaborators': 8,
        'plan': {
            'name': 'Medium',
            'space': 400,
            'collaborators': 10,
            'private_repos': 20
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class GithubOAuth2NoEmailTest(GithubOAuth2Test):
    user_data_body = json.dumps({
        'login': 'foobar',
        'id': 1,
        'avatar_url': 'https://github.com/images/error/foobar_happy.gif',
        'gravatar_id': 'somehexcode',
        'url': 'https://api.github.com/users/foobar',
        'name': 'monalisa foobar',
        'company': 'GitHub',
        'blog': 'https://github.com/blog',
        'location': 'San Francisco',
        'email': '',
        'hireable': False,
        'bio': 'There once was...',
        'public_repos': 2,
        'public_gists': 1,
        'followers': 20,
        'following': 0,
        'html_url': 'https://github.com/foobar',
        'created_at': '2008-01-14T04:33:35Z',
        'type': 'User',
        'total_private_repos': 100,
        'owned_private_repos': 100,
        'private_gists': 81,
        'disk_usage': 10000,
        'collaborators': 8,
        'plan': {
            'name': 'Medium',
            'space': 400,
            'collaborators': 10,
            'private_repos': 20
        }
    })

    def test_login(self):
        url = 'https://api.github.com/user/emails'
        HTTPretty.register_uri(HTTPretty.GET, url, status=200,
                               body=json.dumps(['foo@bar.com']),
                               content_type='application/json')
        self.do_login()

    def test_login_next_format(self):
        url = 'https://api.github.com/user/emails'
        HTTPretty.register_uri(HTTPretty.GET, url, status=200,
                               body=json.dumps([{'email': 'foo@bar.com'}]),
                               content_type='application/json')
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class GithubOrganizationOAuth2Test(GithubOAuth2Test):
    backend_path = 'social.backends.github.GithubOrganizationOAuth2'

    def auth_handlers(self, start_url):
        url = 'https://api.github.com/orgs/foobar/members/foobar'
        HTTPretty.register_uri(HTTPretty.GET, url, status=204, body='')
        return super(GithubOrganizationOAuth2Test, self).auth_handlers(
            start_url
        )

    def test_login(self):
        self.strategy.set_settings({'SOCIAL_AUTH_GITHUB_ORG_NAME': 'foobar'})
        self.do_login()

    def test_partial_pipeline(self):
        self.strategy.set_settings({'SOCIAL_AUTH_GITHUB_ORG_NAME': 'foobar'})
        self.do_partial_pipeline()


class GithubOrganizationOAuth2FailTest(GithubOAuth2Test):
    backend_path = 'social.backends.github.GithubOrganizationOAuth2'

    def auth_handlers(self, start_url):
        url = 'https://api.github.com/orgs/foobar/members/foobar'
        HTTPretty.register_uri(HTTPretty.GET, url, status=404,
                               body='{"message": "Not Found"}',
                               content_type='application/json')
        return super(GithubOrganizationOAuth2FailTest, self).auth_handlers(
            start_url
        )

    def test_login(self):
        self.strategy.set_settings({'SOCIAL_AUTH_GITHUB_ORG_NAME': 'foobar'})
        self.do_login.when.called_with().should.throw(AuthFailed)

    def test_partial_pipeline(self):
        self.strategy.set_settings({'SOCIAL_AUTH_GITHUB_ORG_NAME': 'foobar'})
        self.do_partial_pipeline.when.called_with().should.throw(AuthFailed)

########NEW FILE########
__FILENAME__ = test_google
import json
import datetime

from httpretty import HTTPretty

from social.p3 import urlencode
from social.actions import do_disconnect

from social.tests.models import User
from social.tests.backends.oauth import OAuth1Test, OAuth2Test
from social.tests.backends.open_id import OpenIdTest


class GoogleOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.google.GoogleOAuth2'
    user_data_url = 'https://www.googleapis.com/plus/v1/people/me'
    expected_username = 'foo'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'aboutMe': 'About me text',
        'cover': {
            'coverInfo': {
                'leftImageOffset': 0,
                'topImageOffset': 0
            },
            'coverPhoto': {
                'height': 629,
                'url': 'https://lh5.googleusercontent.com/-ui-GqpNh5Ms/'
                       'AAAAAAAAAAI/AAAAAAAAAZw/a7puhHMO_fg/photo.jpg',
                'width': 940
            },
            'layout': 'banner'
        },
        'displayName': 'Foo Bar',
        'emails': [{
            'type': 'account',
            'value': 'foo@bar.com'
        }],
        'etag': '"e-tag string"',
        'gender': 'male',
        'id': '101010101010101010101',
        'image': {
            'url': 'https://lh5.googleusercontent.com/-ui-GqpNh5Ms/'
                   'AAAAAAAAAAI/AAAAAAAAAZw/a7puhHMO_fg/photo.jpg',
        },
        'isPlusUser': True,
        'kind': 'plus#person',
        'language': 'en',
        'name': {
            'familyName': 'Bar',
            'givenName': 'Foo'
        },
        'objectType': 'person',
        'occupation': 'Software developer',
        'organizations': [{
            'name': 'Org name',
            'primary': True,
            'type': 'school'
        }],
        'placesLived': [{
            'primary': True,
            'value': 'Anyplace'
        }],
        'url': 'https://plus.google.com/101010101010101010101',
        'urls': [{
            'label': 'http://foobar.com',
            'type': 'otherProfile',
            'value': 'http://foobar.com',
        }],
        'verified': False
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

    def test_with_unique_user_id(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_GOOGLE_OAUTH2_USE_UNIQUE_USER_ID': True
        })
        self.do_login()


class GoogleOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.google.GoogleOAuth'
    user_data_url = 'https://www.googleapis.com/userinfo/email'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_body = urlencode({
        'email': 'foobar@gmail.com',
        'isVerified': 'true',
        'id': '101010101010101010101'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

    def test_with_unique_user_id(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_GOOGLE_OAUTH_USE_UNIQUE_USER_ID': True
        })
        self.do_login()

    def test_with_anonymous_key_and_secret(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_GOOGLE_OAUTH_KEY': None,
            'SOCIAL_AUTH_GOOGLE_OAUTH_SECRET': None
        })
        self.do_login()


JANRAIN_NONCE = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')


class GoogleOpenIdTest(OpenIdTest):
    backend_path = 'social.backends.google.GoogleOpenId'
    expected_username = 'FooBar'
    discovery_body = ''.join([
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<xrds:XRDS xmlns:xrds="xri://$xrds" xmlns="xri://$xrd*($v*2.0)">',
        '<XRD>',
          '<Service priority="0">',
            '<Type>http://specs.openid.net/auth/2.0/signon</Type>',
            '<Type>http://openid.net/srv/ax/1.0</Type>',
            '<Type>'
              'http://specs.openid.net/extensions/ui/1.0/mode/popup'
            '</Type>',
            '<Type>http://specs.openid.net/extensions/ui/1.0/icon</Type>',
            '<Type>http://specs.openid.net/extensions/pape/1.0</Type>',
            '<URI>https://www.google.com/accounts/o8/ud</URI>',
          '</Service>',
          '<Service priority="10">',
            '<Type>http://specs.openid.net/auth/2.0/signon</Type>',
            '<Type>http://openid.net/srv/ax/1.0</Type>',
            '<Type>'
              'http://specs.openid.net/extensions/ui/1.0/mode/popup'
            '</Type>',
            '<Type>http://specs.openid.net/extensions/ui/1.0/icon</Type>',
            '<Type>http://specs.openid.net/extensions/pape/1.0</Type>',
            '<URI>https://www.google.com/accounts/o8/ud?source=mail</URI>',
          '</Service>',
          '<Service priority="10">',
            '<Type>http://specs.openid.net/auth/2.0/signon</Type>',
            '<Type>http://openid.net/srv/ax/1.0</Type>',
            '<Type>'
              'http://specs.openid.net/extensions/ui/1.0/mode/popup'
            '</Type>',
            '<Type>http://specs.openid.net/extensions/ui/1.0/icon</Type>',
            '<Type>http://specs.openid.net/extensions/pape/1.0</Type>',
            '<URI>'
              'https://www.google.com/accounts/o8/ud?source=gmail.com'
            '</URI>',
          '</Service>',
          '<Service priority="10">',
            '<Type>http://specs.openid.net/auth/2.0/signon</Type>',
            '<Type>http://openid.net/srv/ax/1.0</Type>',
            '<Type>'
              'http://specs.openid.net/extensions/ui/1.0/mode/popup'
            '</Type>',
            '<Type>http://specs.openid.net/extensions/ui/1.0/icon</Type>',
            '<Type>http://specs.openid.net/extensions/pape/1.0</Type>',
            '<URI>'
              'https://www.google.com/accounts/o8/ud?source=googlemail.com'
            '</URI>',
          '</Service>',
          '<Service priority="10">',
            '<Type>http://specs.openid.net/auth/2.0/signon</Type>',
            '<Type>http://openid.net/srv/ax/1.0</Type>',
            '<Type>'
              'http://specs.openid.net/extensions/ui/1.0/mode/popup'
            '</Type>',
            '<Type>http://specs.openid.net/extensions/ui/1.0/icon</Type>',
            '<Type>http://specs.openid.net/extensions/pape/1.0</Type>',
            '<URI>https://www.google.com/accounts/o8/ud?source=profiles</URI>',
          '</Service>',
        '</XRD>',
      '</xrds:XRDS>'
    ])
    server_response = urlencode({
        'janrain_nonce': JANRAIN_NONCE,
        'openid.assoc_handle': 'assoc-handle',
        'openid.claimed_id': 'https://www.google.com/accounts/o8/id?'
                             'id=some-google-id',
        'openid.ext1.mode': 'fetch_response',
        'openid.ext1.type.email': 'http://axschema.org/contact/email',
        'openid.ext1.type.first_name': 'http://axschema.org/namePerson/first',
        'openid.ext1.type.last_name': 'http://axschema.org/namePerson/last',
        'openid.ext1.type.old_email': 'http://schema.openid.net/contact/email',
        'openid.ext1.value.email': 'foo@bar.com',
        'openid.ext1.value.first_name': 'Foo',
        'openid.ext1.value.last_name': 'Bar',
        'openid.ext1.value.old_email': 'foo@bar.com',
        'openid.identity': 'https://www.google.com/accounts/o8/id?'
                           'id=some-google-id',
        'openid.mode': 'id_res',
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.ns.ext1': 'http://openid.net/srv/ax/1.0',
        'openid.op_endpoint': 'https://www.google.com/accounts/o8/ud',
        'openid.response_nonce': JANRAIN_NONCE + 'by95cT34vX7p9g',
        'openid.return_to': 'http://myapp.com/complete/google/?'
                            'janrain_nonce=' + JANRAIN_NONCE,
        'openid.sig': 'brT2kmu3eCzb1gQ1pbaXdnWioVM=',
        'openid.signed': 'op_endpoint,claimed_id,identity,return_to,'
                         'response_nonce,assoc_handle,ns.ext1,ext1.mode,'
                         'ext1.type.old_email,ext1.value.old_email,'
                         'ext1.type.first_name,ext1.value.first_name,'
                         'ext1.type.last_name,ext1.value.last_name,'
                         'ext1.type.email,ext1.value.email'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class GoogleRevokeTokenTest(GoogleOAuth2Test):
    def test_revoke_token(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_GOOGLE_OAUTH2_REVOKE_TOKENS_ON_DISCONNECT': True
        })
        self.do_login()
        user = User.get(self.expected_username)
        user.password = 'password'
        backend = self.backend
        HTTPretty.register_uri(self._method(backend.REVOKE_TOKEN_METHOD),
                               backend.REVOKE_TOKEN_URL,
                               status=200)
        do_disconnect(self.strategy, user)

########NEW FILE########
__FILENAME__ = test_instagram
import json

from social.tests.backends.oauth import OAuth2Test


class InstagramOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.instagram.InstagramOAuth2'
    user_data_url = 'https://api.instagram.com/v1/users/self'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer',
        'meta': {
            'code': 200
        },
        'data': {
            'username': 'foobar',
            'bio': '',
            'website': '',
            'profile_picture': 'http://images.instagram.com/profiles/'
                               'anonymousUser.jpg',
            'full_name': '',
            'counts': {
                'media': 0,
                'followed_by': 2,
                'follows': 0
            },
            'id': '101010101'
        },
        'user': {
            'username': 'foobar',
            'bio': '',
            'website': '',
            'profile_picture': 'http://images.instagram.com/profiles/'
                               'anonymousUser.jpg',
            'full_name': '',
            'id': '101010101'
        }
    })
    user_data_body = json.dumps({
        'meta': {
            'code': 200
        },
        'data': {
            'username': 'foobar',
            'bio': '',
            'website': '',
            'profile_picture': 'http://images.instagram.com/profiles/'
                               'anonymousUser.jpg',
            'full_name': '',
            'counts': {
                'media': 0,
                'followed_by': 2,
                'follows': 0
            },
            'id': '101010101'
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_kakao
import json

from social.tests.backends.oauth import OAuth2Test


class KakaoOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.kakao.KakaoOAuth2'
    user_data_url = 'https://kapi.kakao.com/v1/user/me'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar'
    })
    user_data_body = json.dumps({
        'id': '101010101',
        'properties': {
            'nickname': 'foobar',
            'thumbnail_image': 'http://mud-kage.kakao.co.kr/14/dn/btqbh1AKmRf/ujlHpQhxtMSbhKrBisrxe1/o.jpg',
            'profile_image': 'http://mud-kage.kakao.co.kr/14/dn/btqbjCnl06Q/wbMJSVAUZB7lzSImgGdsoK/o.jpg'
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_linkedin
import json

from social.p3 import urlencode

from social.tests.backends.oauth import OAuth1Test, OAuth2Test


class BaseLinkedinTest(object):
    user_data_url = 'https://api.linkedin.com/v1/people/~:' \
                        '(first-name,id,last-name)'
    expected_username = 'FooBar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'lastName': 'Bar',
        'id': '1010101010',
        'firstName': 'Foo'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class LinkedinOAuth1Test(BaseLinkedinTest, OAuth1Test):
    backend_path = 'social.backends.linkedin.LinkedinOAuth'
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })


class LinkedinOAuth2Test(BaseLinkedinTest, OAuth2Test):
    backend_path = 'social.backends.linkedin.LinkedinOAuth2'

########NEW FILE########
__FILENAME__ = test_live
import json

from social.tests.backends.oauth import OAuth2Test


class LiveOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.live.LiveOAuth2'
    user_data_url = 'https://apis.live.net/v5.0/me'
    expected_username = 'FooBar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'first_name': 'Foo',
        'last_name': 'Bar',
        'name': 'Foo Bar',
        'locale': 'en_US',
        'gender': None,
        'emails': {
            'personal': None,
            'account': 'foobar@live.com',
            'business': None,
            'preferred': 'foobar@live.com'
        },
        'link': 'https://profile.live.com/',
        'updated_time': '2013-03-17T05:51:30+0000',
        'id': '1010101010101010'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_livejournal
# import json
import datetime

from httpretty import HTTPretty

from social.p3 import urlencode
from social.exceptions import AuthMissingParameter

from social.tests.backends.open_id import OpenIdTest


JANRAIN_NONCE = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')


class LiveJournalOpenIdTest(OpenIdTest):
    backend_path = 'social.backends.livejournal.LiveJournalOpenId'
    expected_username = 'foobar'
    discovery_body = ''.join([
      '<xrds:XRDS xmlns:xrds="xri://$xrds" xmlns="xri://$xrd*($v*2.0)">',
        '<XRD>',
          '<Service priority="0">',
            '<Type>http://specs.openid.net/auth/2.0/signon</Type>',
            '<URI>http://www.livejournal.com/openid/server.bml</URI>',
            '<LocalID>http://foobar.livejournal.com/</LocalID>',
          '</Service>',
        '</XRD>',
      '</xrds:XRDS>'
    ])
    server_response = urlencode({
        'janrain_nonce': JANRAIN_NONCE,
        'openid.mode': 'id_res',
        'openid.claimed_id': 'http://foobar.livejournal.com/',
        'openid.identity': 'http://foobar.livejournal.com/',
        'openid.op_endpoint': 'http://www.livejournal.com/openid/server.bml',
        'openid.return_to': 'http://myapp.com/complete/livejournal/?'
                            'janrain_nonce=' + JANRAIN_NONCE,
        'openid.response_nonce': JANRAIN_NONCE + 'wGp2rj',
        'openid.assoc_handle': '1364932966:ZTiur8sem3r2jzZougMZ:4d1cc3b44e',
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.signed': 'mode,claimed_id,identity,op_endpoint,return_to,'
                         'response_nonce,assoc_handle',
        'openid.sig': 'Z8MOozVPTOBhHG5ZS1NeGofxs1Q=',
    })
    server_bml_body = '\n'.join([
        'assoc_handle:1364935340:ZhruPQ7DJ9eGgUkeUA9A:27f8c32464',
        'assoc_type:HMAC-SHA1',
        'dh_server_public:WzsRyLomvAV3vwvGUrfzXDgfqnTF+m1l3JWb55fyHO7visPT4tmQ'
        'iTjqFFnSVAtAOvQzoViMiZQisxNwnqSK4lYexoez1z6pP5ry3pqxJAEYj60vFGvRztict'
        'Eo0brjhmO1SNfjK1ppjOymdykqLpZeaL5fsuLtMCwTnR/JQZVA=',
        'enc_mac_key:LiOEVlLJSVUqfNvb5zPd76nEfvc=',
        'expires_in:1207060',
        'ns:http://specs.openid.net/auth/2.0',
        'session_type:DH-SHA1',
        ''
    ])

    def openid_url(self):
        return super(LiveJournalOpenIdTest, self).openid_url() + '/data/yadis'

    def post_start(self):
        self.strategy.remove_from_request_data('openid_lj_user')

    def _setup_handlers(self):
        HTTPretty.register_uri(
            HTTPretty.POST,
            'http://www.livejournal.com/openid/server.bml',
            headers={'Accept-Encoding': 'identity',
                     'Content-Type': 'application/x-www-form-urlencoded'},
            status=200,
            body=self.server_bml_body
        )
        HTTPretty.register_uri(
            HTTPretty.GET,
            'http://foobar.livejournal.com/',
            headers={
                'Accept-Encoding': 'identity',
                'Accept': 'text/html; q=0.3,'
                          'application/xhtml+xml; q=0.5,'
                          'application/xrds+xml'
            },
            status=200,
            body=self.discovery_body
        )

    def test_login(self):
        self.strategy.set_request_data({'openid_lj_user': 'foobar'})
        self._setup_handlers()
        self.do_login()

    def test_partial_pipeline(self):
        self.strategy.set_request_data({'openid_lj_user': 'foobar'})
        self._setup_handlers()
        self.do_partial_pipeline()

    def test_failed_login(self):
        self._setup_handlers()
        self.do_login.when.called_with().should.throw(
            AuthMissingParameter
        )

########NEW FILE########
__FILENAME__ = test_mapmyfitness
import json

from social.tests.backends.oauth import OAuth2Test


class MapMyFitnessOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.mapmyfitness.MapMyFitnessOAuth2'
    user_data_url = 'https://oauth2-api.mapmyapi.com/v7.0/user/self/'
    expected_username = 'FredFlinstone'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'Bearer',
        'expires_in': 4000000,
        'refresh_token': 'bambaz',
        'scope': 'read'
    })
    user_data_body = json.dumps({
        'last_name': 'Flinstone',
        'weight': 91.17206637,
        'communication': {
            'promotions': True,
            'newsletter': True,
            'system_messages': True
        },
        'height': 1.778,
        'token_type': 'Bearer',
        'id': 112233,
        'date_joined': '2011-08-26T06:06:19+00:00',
        'first_name': 'Fred',
        'display_name': 'Fred Flinstone',
        'display_measurement_system': 'imperial',
        'expires_in': 4000000,
        '_links': {
            'stats': [
                {
                    'href': '/v7.0/user_stats/112233/?aggregate_by_period=month',
                    'id': '112233',
                    'name': 'month'
                },
                {
                    'href': '/v7.0/user_stats/112233/?aggregate_by_period=year',
                    'id': '112233',
                    'name': 'year'
                },
                {
                    'href': '/v7.0/user_stats/112233/?aggregate_by_period=day',
                    'id': '112233',
                    'name': 'day'
                },
                {
                    'href': '/v7.0/user_stats/112233/?aggregate_by_period=week',
                    'id': '112233',
                    'name': 'week'
                },
                {
                    'href': '/v7.0/user_stats/112233/?aggregate_by_period=lifetime',
                    'id': '112233',
                    'name': 'lifetime'
                }
            ],
            'friendships': [
                {
                    'href': '/v7.0/friendship/?from_user=112233'
                }
            ],
            'privacy': [
                {
                    'href': '/v7.0/privacy_option/3/',
                    'id': '3',
                    'name': 'profile'
                },
                {
                    'href': '/v7.0/privacy_option/3/',
                    'id': '3',
                    'name': 'workout'
                },
                {
                    'href': '/v7.0/privacy_option/3/',
                    'id': '3',
                    'name': 'activity_feed'
                },
                {
                    'href': '/v7.0/privacy_option/1/',
                    'id': '1',
                    'name': 'food_log'
                },
                {
                    'href': '/v7.0/privacy_option/3/',
                    'id': '3',
                    'name': 'email_search'
                },
                {
                    'href': '/v7.0/privacy_option/3/',
                    'id': '3',
                    'name': 'route'
                }
            ],
            'image': [
                {
                    'href': '/v7.0/user_profile_photo/112233/',
                    'id': '112233',
                    'name': 'user_profile_photo'
                }
            ],
            'documentation': [
                {
                    'href': 'https://www.mapmyapi.com/docs/User'
                }
            ],
            'workouts': [
                {
                    'href': '/v7.0/workout/?user=112233&order_by=-start_datetime'
                }
            ],
            'deactivation': [
                {
                    'href': '/v7.0/user_deactivation/'
                }
            ],
            'self': [
                {
                    'href': '/v7.0/user/112233/',
                    'id': '112233'
                }
            ]
        },
        'location': {
            'country': 'US',
            'region': 'NC',
            'locality': 'Bedrock',
            'address': '150 Dinosaur Ln'
        },
        'last_login': '2014-02-23T22:36:52+00:00',
        'email': 'fredflinstone@gmail.com',
        'username': 'FredFlinstone',
        'sharing': {
            'twitter': False,
            'facebook': False
        },
        'scope': 'read',
        'refresh_token': 'bambaz',
        'last_initial': 'S.',
        'access_token': 'foobar',
        'gender': 'M',
        'time_zone': 'America/Denver',
        'birthdate': '1983-04-15'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_mixcloud
import json

from social.tests.backends.oauth import OAuth2Test


class MixcloudOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.mixcloud.MixcloudOAuth2'
    user_data_url = 'https://api.mixcloud.com/me/'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'username': 'foobar',
        'cloudcast_count': 0,
        'following_count': 0,
        'url': 'http://www.mixcloud.com/foobar/',
        'pictures': {
            'medium': 'http://images-mix.netdna-ssl.com/w/100/h/100/q/85/'
                      'images/graphics/33_Profile/default_user_600x600-v4.png',
            '320wx320h': 'http://images-mix.netdna-ssl.com/w/320/h/320/q/85/'
                         'images/graphics/33_Profile/'
                         'default_user_600x600-v4.png',
            'extra_large': 'http://images-mix.netdna-ssl.com/w/600/h/600/q/85/'
                           'images/graphics/33_Profile/'
                           'default_user_600x600-v4.png',
            'large': 'http://images-mix.netdna-ssl.com/w/300/h/300/q/85/'
                     'images/graphics/33_Profile/default_user_600x600-v4.png',
            '640wx640h': 'http://images-mix.netdna-ssl.com/w/640/h/640/q/85/'
                         'images/graphics/33_Profile/'
                         'default_user_600x600-v4.png',
            'medium_mobile': 'http://images-mix.netdna-ssl.com/w/80/h/80/q/75/'
                             'images/graphics/33_Profile/'
                             'default_user_600x600-v4.png',
            'small': 'http://images-mix.netdna-ssl.com/w/25/h/25/q/85/images/'
                     'graphics/33_Profile/default_user_600x600-v4.png',
            'thumbnail': 'http://images-mix.netdna-ssl.com/w/50/h/50/q/85/'
                         'images/graphics/33_Profile/'
                         'default_user_600x600-v4.png'
        },
        'is_current_user': True,
        'listen_count': 0,
        'updated_time': '2013-03-17T06:26:31Z',
        'following': False,
        'follower': False,
        'key': '/foobar/',
        'created_time': '2013-03-17T06:26:31Z',
        'follower_count': 0,
        'favorite_count': 0,
        'name': 'foobar'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_podio
import json

from social.tests.backends.oauth import OAuth2Test


class PodioOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.podio.PodioOAuth2'
    user_data_url = 'https://api.podio.com/user/status'
    expected_username = 'user_1010101010'
    access_token_body = json.dumps({
        'token_type': 'bearer',
        'access_token': '11309ea9016a4ad99f1a3bcb9bc7a9d1',
        'refresh_token': '52d01df8b9ac46a4a6be1333d9f81ef2',
        'expires_in': 28800,
        'ref': {
            'type': 'user',
            'id': 1010101010,
        }
    })
    user_data_body = json.dumps({
        'user': {
            'user_id': 1010101010,
            'activated_on': '2012-11-22 09:37:21',
            'created_on': '2012-11-21 12:23:47',
            'locale': 'en_GB',
            'timezone': 'Europe/Copenhagen',
            'mail': 'foo@bar.com',
            'mails': [
                {'disabled': False,
                 'mail': 'foobar@example.com',
                 'primary': False,
                 'verified': True
                 },
                {'disabled': False,
                 'mail': 'foo@bar.com',
                 'primary': True,
                 'verified': True
                }
            ],
            # more properties ...
        },
        'profile': {
            'last_seen_on': '2013-05-16 12:21:13',
            'link': 'https://podio.com/users/1010101010',
            'name': 'Foo Bar',
            # more properties ...
        }
        # more properties ...
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_readability
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class ReadabilityOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.readability.ReadabilityOAuth'
    user_data_url = 'https://www.readability.com/api/rest/v1/users/_current'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_body = json.dumps({
        'username': 'foobar',
        'first_name': 'Foo',
        'last_name': 'Bar',
        'has_active_subscription': False,
        'tags': [],
        'is_publisher': False,
        'email_into_address': 'foobar+sharp@inbox.readability.com',
        'kindle_email_address': None,
        'avatar_url': 'https://secure.gravatar.com/avatar/'
                      '5280f15cedf540b544eecc30fcf3027c?d='
                      'https://www.readability.com/media/images/'
                      'avatar.png&s=36',
        'date_joined': '2013-03-18 02:51:02'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_reddit
import json

from sure import expect

from social.tests.backends.oauth import OAuth2Test


class RedditOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.reddit.RedditOAuth2'
    user_data_url = 'https://oauth.reddit.com/api/v1/me.json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'name': 'foobar',
        'created': 1203420772.0,
        'access_token': 'foobar-token',
        'created_utc': 1203420772.0,
        'expires_in': 3600.0,
        'link_karma': 34,
        'token_type': 'bearer',
        'comment_karma': 167,
        'over_18': True,
        'is_gold': False,
        'is_mod': True,
        'scope': 'identity',
        'has_verified_email': False,
        'id': '33bma',
        'refresh_token': 'foobar-refresh-token'
    })
    user_data_body = json.dumps({
        'name': 'foobar',
        'created': 1203420772.0,
        'created_utc': 1203420772.0,
        'link_karma': 34,
        'comment_karma': 167,
        'over_18': True,
        'is_gold': False,
        'is_mod': True,
        'has_verified_email': False,
        'id': '33bma'
    })
    refresh_token_body = json.dumps({
        'access_token': 'foobar-new-token',
        'token_type': 'bearer',
        'expires_in': 3600.0,
        'refresh_token': 'foobar-new-refresh-token',
        'scope': 'identity'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

    def refresh_token_arguments(self):
        uri = self.strategy.build_absolute_uri('/complete/reddit/')
        return {'redirect_uri': uri}

    def test_refresh_token(self):
        user, social = self.do_refresh_token()
        expect(social.extra_data['access_token']).to.equal('foobar-new-token')

########NEW FILE########
__FILENAME__ = test_skyrock
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class SkyrockOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.skyrock.SkyrockOAuth'
    user_data_url = 'https://api.skyrock.com/v2/user/get.json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
    })
    user_data_body = json.dumps({
        'locale': 'en_US',
        'city': '',
        'has_blog': False,
        'web_messager_enabled': True,
        'email': 'foo@bar.com',
        'username': 'foobar',
        'firstname': 'Foo',
        'user_url': '',
        'address1': '',
        'address2': '',
        'has_profile': False,
        'allow_messages_from': 'everybody',
        'is_online': False,
        'postalcode': '',
        'lang': 'en',
        'id_user': 10101010,
        'name': 'Bar',
        'gender': 0,
        'avatar_url': 'http://www.skyrock.com/img/avatars/default-0.jpg',
        'nb_friends': 0,
        'country': 'US',
        'birth_date': '1980-06-10'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_soundcloud
import json

from social.tests.backends.oauth import OAuth2Test


class SoundcloudOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.soundcloud.SoundcloudOAuth2'
    user_data_url = 'https://api.soundcloud.com/me.json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'website': None,
        'myspace_name': None,
        'public_favorites_count': 0,
        'followings_count': 0,
        'full_name': 'Foo Bar',
        'id': 10101010,
        'city': None,
        'track_count': 0,
        'playlist_count': 0,
        'discogs_name': None,
        'private_tracks_count': 0,
        'followers_count': 0,
        'online': True,
        'username': 'foobar',
        'description': None,
        'subscriptions': [],
        'kind': 'user',
        'quota': {
            'unlimited_upload_quota': False,
            'upload_seconds_left': 7200,
            'upload_seconds_used': 0
        },
        'website_title': None,
        'primary_email_confirmed': False,
        'permalink_url': 'http://soundcloud.com/foobar',
        'private_playlists_count': 0,
        'permalink': 'foobar',
        'upload_seconds_left': 7200,
        'country': None,
        'uri': 'https://api.soundcloud.com/users/10101010',
        'avatar_url': 'https://a1.sndcdn.com/images/'
                      'default_avatar_large.png?ca77017',
        'plan': 'Free'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_stackoverflow
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth2Test


class StackoverflowOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.stackoverflow.StackoverflowOAuth2'
    user_data_url = 'https://api.stackexchange.com/2.1/me'
    expected_username = 'foobar'
    access_token_body = urlencode({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'items': [{
            'user_id': 101010,
            'user_type': 'registered',
            'creation_date': 1278525551,
            'display_name': 'foobar',
            'profile_image': 'http: //www.gravatar.com/avatar/'
                             '5280f15cedf540b544eecc30fcf3027c?'
                             'd=identicon&r=PG',
            'reputation': 547,
            'reputation_change_day': 0,
            'reputation_change_week': 0,
            'reputation_change_month': 0,
            'reputation_change_quarter': 65,
            'reputation_change_year': 65,
            'age': 22,
            'last_access_date': 1363544705,
            'last_modified_date': 1354035327,
            'is_employee': False,
            'link': 'http: //stackoverflow.com/users/101010/foobar',
            'location': 'Fooland',
            'account_id': 101010,
            'badge_counts': {
                'gold': 0,
                'silver': 3,
                'bronze': 6
            }
        }],
        'quota_remaining': 9997,
        'quota_max': 10000,
        'has_more': False
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_steam
import json
import datetime

from httpretty import HTTPretty

from social.p3 import urlencode
from social.exceptions import AuthFailed

from social.tests.backends.open_id import OpenIdTest


INFO_URL = 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?'
JANRAIN_NONCE = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')


class SteamOpenIdTest(OpenIdTest):
    backend_path = 'social.backends.steam.SteamOpenId'
    expected_username = 'foobar'
    discovery_body = ''.join([
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<xrds:XRDS xmlns:xrds="xri://$xrds" xmlns="xri://$xrd*($v*2.0)">',
        '<XRD>',
          '<Service priority="0">',
             '<Type>http://specs.openid.net/auth/2.0/server</Type>',
             '<URI>https://steamcommunity.com/openid/login</URI>',
          '</Service>',
        '</XRD>',
      '</xrds:XRDS>'
    ])
    user_discovery_body = ''.join([
      '<?xml version="1.0" encoding="UTF-8"?>',
        '<xrds:XRDS xmlns:xrds="xri://$xrds" xmlns="xri://$xrd*($v*2.0)">',
          '<XRD>',
            '<Service priority="0">',
              '<Type>http://specs.openid.net/auth/2.0/signon</Type>		',
              '<URI>https://steamcommunity.com/openid/login</URI>',
            '</Service>',
          '</XRD>',
      '</xrds:XRDS>'
    ])
    server_response = urlencode({
        'janrain_nonce': JANRAIN_NONCE,
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'id_res',
        'openid.op_endpoint': 'https://steamcommunity.com/openid/login',
        'openid.claimed_id': 'https://steamcommunity.com/openid/id/123',
        'openid.identity': 'https://steamcommunity.com/openid/id/123',
        'openid.return_to': 'http://myapp.com/complete/steam/?'
                            'janrain_nonce=' + JANRAIN_NONCE,
        'openid.response_nonce': JANRAIN_NONCE +
                                 'oD4UZ3w9chOAiQXk0AqDipqFYRA=',
        'openid.assoc_handle': '1234567890',
        'openid.signed': 'signed,op_endpoint,claimed_id,identity,return_to,'
                         'response_nonce,assoc_handle',
        'openid.sig': '1az53vj9SVdiBwhk8%2BFQ68R2plo=',
    })
    player_details = json.dumps({
        'response': {
            'players': [{
                'steamid': '123',
                'primaryclanid': '1234',
                'timecreated': 1360768416,
                'personaname': 'foobar',
                'personastate': 0,
                'communityvisibilitystate': 3,
                'profileurl': 'http://steamcommunity.com/profiles/123/',
                'avatar': 'http://media.steampowered.com/steamcommunity/'
                          'public/images/avatars/fe/fef49e7fa7e1997310d7'
                          '05b2a6158ff8dc1cdfeb.jpg',
                'avatarfull': 'http://media.steampowered.com/steamcommunity/'
                              'public/images/avatars/fe/fef49e7fa7e1997310d7'
                              '05b2a6158ff8dc1cdfeb_full.jpg',
                'avatarmedium': 'http://media.steampowered.com/steamcommunity/'
                                'public/images/avatars/fe/fef49e7fa7e1997310d7'
                                '05b2a6158ff8dc1cdfeb_medium.jpg',
                'lastlogoff': 1360790014
            }]
        }
    })

    def _login_setup(self, user_url=None):
        self.strategy.set_settings({
            'SOCIAL_AUTH_STEAM_API_KEY': '123abc'
        })
        HTTPretty.register_uri(HTTPretty.POST,
                               'https://steamcommunity.com/openid/login',
                               status=200,
                               body=self.server_response)
        HTTPretty.register_uri(
            HTTPretty.GET,
            user_url or 'https://steamcommunity.com/openid/id/123',
            status=200,
            body=self.user_discovery_body
        )
        HTTPretty.register_uri(HTTPretty.GET,
                               INFO_URL,
                               status=200,
                               body=self.player_details)

    def test_login(self):
        self._login_setup()
        self.do_login()

    def test_partial_pipeline(self):
        self._login_setup()
        self.do_partial_pipeline()


class SteamOpenIdMissingSteamIdTest(SteamOpenIdTest):
    server_response = urlencode({
        'janrain_nonce': JANRAIN_NONCE,
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'id_res',
        'openid.op_endpoint': 'https://steamcommunity.com/openid/login',
        'openid.claimed_id': 'https://steamcommunity.com/openid/BROKEN',
        'openid.identity': 'https://steamcommunity.com/openid/BROKEN',
        'openid.return_to': 'http://myapp.com/complete/steam/?'
                            'janrain_nonce=' + JANRAIN_NONCE,
        'openid.response_nonce': JANRAIN_NONCE +
                                 'oD4UZ3w9chOAiQXk0AqDipqFYRA=',
        'openid.assoc_handle': '1234567890',
        'openid.signed': 'signed,op_endpoint,claimed_id,identity,return_to,'
                         'response_nonce,assoc_handle',
        'openid.sig': '1az53vj9SVdiBwhk8%2BFQ68R2plo=',
    })

    def test_login(self):
        self._login_setup(user_url='https://steamcommunity.com/openid/BROKEN')
        self.do_login.when.called_with().should.throw(AuthFailed)

    def test_partial_pipeline(self):
        self._login_setup(user_url='https://steamcommunity.com/openid/BROKEN')
        self.do_partial_pipeline.when.called_with().should.throw(AuthFailed)

########NEW FILE########
__FILENAME__ = test_stocktwits
import json

from social.tests.backends.oauth import OAuth2Test


class StocktwitsOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.stocktwits.StocktwitsOAuth2'
    user_data_url = 'https://api.stocktwits.com/api/2/account/verify.json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'response': {
            'status': 200
        },
        'user': {
            'username': 'foobar',
            'name': 'Foo Bar',
            'classification': [],
            'avatar_url': 'http://avatars.stocktwits.net/images/'
                          'default_avatar_thumb.jpg',
            'avatar_url_ssl': 'https://s3.amazonaws.com/st-avatars/images/'
                              'default_avatar_thumb.jpg',
            'id': 101010,
            'identity': 'User'
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class StocktwitsOAuth2UsernameAlternativeTest(StocktwitsOAuth2Test):
    user_data_body = json.dumps({
        'response': {
            'status': 200
        },
        'user': {
            'username': 'foobar',
            'name': 'Foobar',
            'classification': [],
            'avatar_url': 'http://avatars.stocktwits.net/images/'
                          'default_avatar_thumb.jpg',
            'avatar_url_ssl': 'https://s3.amazonaws.com/st-avatars/images/'
                              'default_avatar_thumb.jpg',
            'id': 101010,
            'identity': 'User'
        }
    })

########NEW FILE########
__FILENAME__ = test_strava
import json

from social.tests.backends.oauth import OAuth2Test


class StravaOAuthTest(OAuth2Test):
    backend_path = 'social.backends.strava.StravaOAuth'
    user_data_url = 'https://www.strava.com/api/v3/athlete'
    expected_username = '227615'
    access_token_body = json.dumps({
      "access_token": "83ebeabdec09f6670863766f792ead24d61fe3f9",
      "athlete": {
        "id": 227615,
        "resource_state": 3,
        "firstname": "John",
        "lastname": "Applestrava",
        "profile_medium": "http://pics.com/227615/medium.jpg",
        "profile": "http://pics.com/227615/large.jpg",
        "city": "San Francisco",
        "state": "California",
        "country": "United States",
        "sex": "M",
        "friend": "null",
        "follower": "null",
        "premium": "true",
        "created_at": "2008-01-01T17:44:00Z",
        "updated_at": "2013-09-04T20:00:50Z",
        "follower_count": 273,
        "friend_count": 19,
        "mutual_friend_count": 0,
        "date_preference": "%m/%d/%Y",
        "measurement_preference": "feet",
        "email": "john@applestrava.com",
        "clubs": [],
        "bikes": [],
        "shoes": []
      }
    })
    user_data_body = json.dumps({
      "id": 227615,
      "resource_state": 2,
      "firstname": "John",
      "lastname": "Applestrava",
      "profile_medium": "http://pics.com/227615/medium.jpg",
      "profile": "http://pics.com/227615/large.jpg",
      "city": "San Francisco",
      "state": "CA",
      "country": "United States",
      "sex": "M",
      "friend": "null",
      "follower": "accepted",
      "premium": "true",
      "created_at": "2011-03-19T21:59:57Z",
      "updated_at": "2013-09-05T16:46:54Z",
      "approve_followers": "false"
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_stripe
import json

from social.tests.backends.oauth import OAuth2Test


class StripeOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.stripe.StripeOAuth2'
    access_token_body = json.dumps({
        'stripe_publishable_key': 'pk_test_foobar',
        'access_token': 'foobar',
        'livemode': False,
        'token_type': 'bearer',
        'scope': 'read_only',
        'refresh_token': 'rt_foobar',
        'stripe_user_id': 'acct_foobar'
    })
    expected_username = 'acct_foobar'

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_taobao
import json

from social.tests.backends.oauth import OAuth2Test


class TaobaoOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.taobao.TAOBAOAuth'
    user_data_url = 'https://eco.taobao.com/router/rest'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
        })
    user_data_body = json.dumps({
        'w2_expires_in': 0,
        'taobao_user_id': '1',
        'taobao_user_nick': 'foobar',
        'w1_expires_in': 1800,
        're_expires_in': 0,
        'r2_expires_in': 0,
        'expires_in': 86400,
        'r1_expires_in': 1800
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_thisismyjam
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class ThisIsMyJameOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.thisismyjam.ThisIsMyJamOAuth1'
    user_data_url = 'http://api.thisismyjam.com/1/verify.json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_body = json.dumps({
        'id': 10101010,
        'person': {
            'name': 'foobar',
            'fullname': 'Foo Bar'
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_tripit
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class TripitOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.tripit.TripItOAuth'
    user_data_url = 'https://api.tripit.com/v1/get/profile'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_content_type = 'text/xml'
    user_data_body = \
        '<Response>' \
            '<timestamp>1363590451</timestamp>' \
            '<num_bytes>1040</num_bytes>' \
            '<Profile ref="ignore-me">' \
                '<ProfileEmailAddresses>' \
                    '<ProfileEmailAddress>' \
                        '<address>foobar@gmail.com</address>' \
                        '<is_auto_import>false</is_auto_import>' \
                        '<is_confirmed>true</is_confirmed>' \
                        '<is_primary>true</is_primary>' \
                        '<is_auto_inbox_eligible>' \
                            'true' \
                        '</is_auto_inbox_eligible>' \
                    '</ProfileEmailAddress>' \
                '</ProfileEmailAddresses>' \
                '<is_client>true</is_client>' \
                '<is_pro>false</is_pro>' \
                '<screen_name>foobar</screen_name>' \
                '<public_display_name>Foo Bar</public_display_name>' \
                '<profile_url>people/foobar</profile_url>' \
                '<home_city>Foo, Barland</home_city>' \
                '<activity_feed_url>' \
                    'https://www.tripit.com/feed/activities/private/' \
                    'ignore-this/activities.atom' \
                '</activity_feed_url>' \
                '<alerts_feed_url>' \
                    'https://www.tripit.com/feed/alerts/private/' \
                    'ignore-this/alerts.atom' \
                '</alerts_feed_url>' \
                '<ical_url>' \
                    'webcal://www.tripit.com/feed/ical/private/' \
                    'ignore-this/tripit.ics' \
                '</ical_url>' \
            '</Profile>' \
        '</Response>'

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()


class TripitOAuth1UsernameAlternativesTest(TripitOAuth1Test):
    user_data_body = \
        '<Response>' \
            '<timestamp>1363590451</timestamp>' \
            '<num_bytes>1040</num_bytes>' \
            '<Profile ref="ignore-me">' \
                '<ProfileEmailAddresses>' \
                    '<ProfileEmailAddress>' \
                        '<address>foobar@gmail.com</address>' \
                        '<is_auto_import>false</is_auto_import>' \
                        '<is_confirmed>true</is_confirmed>' \
                        '<is_primary>true</is_primary>' \
                        '<is_auto_inbox_eligible>' \
                            'true' \
                        '</is_auto_inbox_eligible>' \
                    '</ProfileEmailAddress>' \
                '</ProfileEmailAddresses>' \
                '<is_client>true</is_client>' \
                '<is_pro>false</is_pro>' \
                '<screen_name>foobar</screen_name>' \
                '<public_display_name>Foobar</public_display_name>' \
                '<profile_url>people/foobar</profile_url>' \
                '<home_city>Foo, Barland</home_city>' \
                '<activity_feed_url>' \
                    'https://www.tripit.com/feed/activities/private/' \
                    'ignore-this/activities.atom' \
                '</activity_feed_url>' \
                '<alerts_feed_url>' \
                    'https://www.tripit.com/feed/alerts/private/' \
                    'ignore-this/alerts.atom' \
                '</alerts_feed_url>' \
                '<ical_url>' \
                    'webcal://www.tripit.com/feed/ical/private/' \
                    'ignore-this/tripit.ics' \
                '</ical_url>' \
            '</Profile>' \
        '</Response>'

########NEW FILE########
__FILENAME__ = test_tumblr
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class TumblrOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.tumblr.TumblrOAuth'
    user_data_url = 'http://api.tumblr.com/v2/user/info'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_body = json.dumps({
        'meta': {
            'status': 200,
            'msg': 'OK'
        },
        'response': {
            'user': {
                'following': 1,
                'blogs': [{
                    'updated': 0,
                    'description': '',
                    'drafts': 0,
                    'title': 'Untitled',
                    'url': 'http://foobar.tumblr.com/',
                    'messages': 0,
                    'tweet': 'N',
                    'share_likes': True,
                    'posts': 0,
                    'primary': True,
                    'queue': 0,
                    'admin': True,
                    'followers': 0,
                    'ask': False,
                    'facebook': 'N',
                    'type': 'public',
                    'facebook_opengraph_enabled': 'N',
                    'name': 'foobar'
                }],
                'default_post_format': 'html',
                'name': 'foobar',
                'likes': 0
            }
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_twitch
import json
from social.tests.backends.oauth import OAuth2Test


class TwitchOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.twitch.TwitchOAuth2'
    user_data_url = 'https://api.twitch.tv/kraken/user/'
    expected_username = 'test_user1'
    access_token_body = json.dumps({
        'access_token': 'foobar',
    })
    user_data_body = json.dumps({
        'type': 'user',
        'name': 'test_user1',
        'created_at': '2011-06-03T17:49:19Z',
        'updated_at': '2012-06-18T17:19:57Z',
        '_links': {
            'self': 'https://api.twitch.tv/kraken/users/test_user1'
        },
        'logo': 'http://static-cdn.jtvnw.net/jtv_user_pictures/'
                'test_user1-profile_image-62e8318af864d6d7-300x300.jpeg',
        '_id': 22761313,
        'display_name': 'test_user1',
        'email': 'asdf@asdf.com',
        'partnered': True,
        'bio': 'test bio woo I\'m a test user'
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_twitter
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class TwitterOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.twitter.TwitterOAuth'
    user_data_url = 'https://api.twitter.com/1.1/account/' \
                        'verify_credentials.json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_body = json.dumps({
        'follow_request_sent': False,
        'profile_use_background_image': True,
        'id': 10101010,
        'description': 'Foo bar baz qux',
        'verified': False,
        'entities': {
            'description': {
                'urls': []
            }
        },
        'profile_image_url_https': 'https://twimg0-a.akamaihd.net/'
                                   'profile_images/532018826/'
                                   'n587119531_1939735_9305_normal.jpg',
        'profile_sidebar_fill_color': '252429',
        'profile_text_color': '666666',
        'followers_count': 77,
        'profile_sidebar_border_color': '181A1E',
        'location': 'Fooland',
        'default_profile_image': False,
        'listed_count': 4,
        'status': {
            'favorited': False,
            'contributors': None,
            'retweeted_status': {
                'favorited': False,
                'contributors': None,
                'truncated': False,
                'source': 'web',
                'text': '"Foo foo foo foo',
                'created_at': 'Fri Dec 21 18:12:00 +0000 2012',
                'retweeted': True,
                'in_reply_to_status_id': None,
                'coordinates': None,
                'id': 101010101010101010,
                'entities': {
                    'user_mentions': [],
                    'hashtags': [],
                    'urls': []
                },
                'in_reply_to_status_id_str': None,
                'place': None,
                'id_str': '101010101010101010',
                'in_reply_to_screen_name': None,
                'retweet_count': 8,
                'geo': None,
                'in_reply_to_user_id_str': None,
                'in_reply_to_user_id': None
            },
            'truncated': False,
            'source': 'web',
            'text': 'RT @foo: "Foo foo foo foo',
            'created_at': 'Fri Dec 21 18:24:10 +0000 2012',
            'retweeted': True,
            'in_reply_to_status_id': None,
            'coordinates': None,
            'id': 101010101010101010,
            'entities': {
                'user_mentions': [{
                    'indices': [3, 10],
                    'id': 10101010,
                    'screen_name': 'foo',
                    'id_str': '10101010',
                    'name': 'Foo'
                }],
                'hashtags': [],
                'urls': []
            },
            'in_reply_to_status_id_str': None,
            'place': None,
            'id_str': '101010101010101010',
            'in_reply_to_screen_name': None,
            'retweet_count': 8,
            'geo': None,
            'in_reply_to_user_id_str': None,
            'in_reply_to_user_id': None
        },
        'utc_offset': -10800,
        'statuses_count': 191,
        'profile_background_color': '1A1B1F',
        'friends_count': 151,
        'profile_background_image_url_https': 'https://twimg0-a.akamaihd.net/'
                                              'images/themes/theme9/bg.gif',
        'profile_link_color': '2FC2EF',
        'profile_image_url': 'http://a0.twimg.com/profile_images/532018826/'
                             'n587119531_1939735_9305_normal.jpg',
        'is_translator': False,
        'geo_enabled': False,
        'id_str': '74313638',
        'profile_background_image_url': 'http://a0.twimg.com/images/themes/'
                                        'theme9/bg.gif',
        'screen_name': 'foobar',
        'lang': 'en',
        'profile_background_tile': False,
        'favourites_count': 2,
        'name': 'Foo',
        'notifications': False,
        'url': None,
        'created_at': 'Tue Sep 15 00:26:17 +0000 2009',
        'contributors_enabled': False,
        'time_zone': 'Buenos Aires',
        'protected': False,
        'default_profile': False,
        'following': False
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_username
from social.tests.backends.legacy import BaseLegacyTest


class UsernameTest(BaseLegacyTest):
    backend_path = 'social.backends.username.UsernameAuth'
    expected_username = 'foobar'
    response_body = 'username=foobar'
    form = """
    <form method="post" action="{0}">
        <input name="username" type="text">
        <button>Submit</button>
    </form>
    """

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_utils
import unittest
from sure import expect

from social.tests.models import TestStorage
from social.tests.strategy import TestStrategy
from social.backends.utils import load_backends, get_backend
from social.backends.github import GithubOAuth2


class BaseBackendUtilsTest(unittest.TestCase):
    def setUp(self):
        self.strategy = TestStrategy(storage=TestStorage)

    def tearDown(self):
        self.strategy = None


class LoadBackendsTest(BaseBackendUtilsTest):
    def test_load_backends(self):
        loaded_backends = load_backends((
            'social.backends.github.GithubOAuth2',
            'social.backends.facebook.FacebookOAuth2',
            'social.backends.flickr.FlickrOAuth'
        ), force_load=True)
        keys = list(loaded_backends.keys())
        keys.sort()
        expect(keys).to.equal(['facebook', 'flickr', 'github'])

        backends = ()
        loaded_backends = load_backends(backends, force_load=True)
        expect(len(list(loaded_backends.keys()))).to.equal(0)


class GetBackendTest(BaseBackendUtilsTest):
    def test_get_backend(self):
        backend = get_backend((
            'social.backends.github.GithubOAuth2',
            'social.backends.facebook.FacebookOAuth2',
            'social.backends.flickr.FlickrOAuth'
        ), 'github')
        expect(backend).to.equal(GithubOAuth2)

    def test_get_missing_backend(self):
        backend = get_backend((
            'social.backends.github.GithubOAuth2',
            'social.backends.facebook.FacebookOAuth2',
            'social.backends.flickr.FlickrOAuth'
        ), 'foobar')
        expect(backend).to.equal(None)

########NEW FILE########
__FILENAME__ = test_vk
#coding: utf-8
from __future__ import unicode_literals

import json

from social.tests.backends.oauth import OAuth2Test


class VKOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.vk.VKOAuth2'
    user_data_url = 'https://api.vk.com/method/users.get'
    expected_username = 'durov'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'response': [{
            'uid': '1',
            'first_name': 'Павел',
            'last_name': 'Дуров',
            'screen_name': 'durov',
            'nickname': '',
            'photo': "http:\/\/cs7003.vk.me\/v7003815\/22a1\/xgG9fb-IJ3Y.jpg"
        }]
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_xing
import json

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class XingOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.xing.XingOAuth'
    user_data_url = 'https://api.xing.com/v1/users/me.json'
    expected_username = 'FooBar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer',
        'user_id': '123456_abcdef'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    user_data_body = json.dumps({
        'users': [{
            'id': '123456_abcdef',
            'first_name': 'Foo',
            'last_name': 'Bar',
            'display_name': 'Foo Bar',
            'page_name': 'Foo_Bar',
            'permalink': 'https://www.xing.com/profile/Foo_Bar',
            'gender': 'm',
            'birth_date': {
                'day': 12,
                'month': 8,
                'year': 1963
            },
            'active_email': 'foo@bar.com',
            'time_zone': {
                'name': 'Europe/Copenhagen',
                'utc_offset': 2.0
            },
            'premium_services': ['SEARCH', 'PRIVATEMESSAGES'],
            'badges': ['PREMIUM', 'MODERATOR'],
            'wants': 'Nothing',
            'haves': 'Skills',
            'interests': 'Foo Foo',
            'organisation_member': 'ACM, GI',
            'languages': {
                'de': 'NATIVE',
                'en': 'FLUENT',
                'fr': None,
                'zh': 'BASIC'
            },
            'private_address': {
                'city': 'Foo',
                'country': 'DE',
                'zip_code': '20357',
                'street': 'Bar',
                'phone': '12|34|1234560',
                'fax': '||',
                'province': 'Foo',
                'email': 'foo@bar.com',
                'mobile_phone': '12|3456|1234567'
            },
            'business_address': {
                'city': 'Foo',
                'country': 'DE',
                'zip_code': '20357',
                'street': 'Bar',
                'phone': '12|34|1234569',
                'fax': '12|34|1234561',
                'province': 'Foo',
                'email': 'foo@bar.com',
                'mobile_phone': '12|345|12345678'
            },
            'web_profiles': {
                'qype': ['http://qype.de/users/foo'],
                'google_plus': ['http://plus.google.com/foo'],
                'blog': ['http://blog.example.org'],
                'homepage': ['http://example.org', 'http://other-example.org']
            },
            'instant_messaging_accounts': {
                'skype': 'foobar',
                'googletalk': 'foobar'
            },
            'professional_experience': {
                'primary_company': {
                    'name': 'XING AG',
                    'title': 'Softwareentwickler',
                    'company_size': '201-500',
                    'tag': None,
                    'url': 'http://www.xing.com',
                    'career_level': 'PROFESSIONAL_EXPERIENCED',
                    'begin_date': '2010-01',
                    'description': None,
                    'end_date': None,
                    'industry': 'AEROSPACE'
                },
                'non_primary_companies': [{
                    'name': 'Ninja Ltd.',
                    'title': 'DevOps',
                    'company_size': None,
                    'tag': 'NINJA',
                    'url': 'http://www.ninja-ltd.co.uk',
                    'career_level': None,
                    'begin_date': '2009-04',
                    'description': None,
                    'end_date': '2010-07',
                    'industry': 'ALTERNATIVE_MEDICINE'
                }, {
                    'name': None,
                    'title': 'Wiss. Mitarbeiter',
                    'company_size': None,
                    'tag': 'OFFIS',
                    'url': 'http://www.uni.de',
                    'career_level': None,
                    'begin_date': '2007',
                    'description': None,
                    'end_date': '2008',
                    'industry': 'APPAREL_AND_FASHION'
                }, {
                    'name': None,
                    'title': 'TEST NINJA',
                    'company_size': '201-500',
                    'tag': 'TESTCOMPANY',
                    'url': None,
                    'career_level': 'ENTRY_LEVEL',
                    'begin_date': '1998-12',
                    'description': None,
                    'end_date': '1999-05',
                    'industry': 'ARTS_AND_CRAFTS'
                }],
                'awards': [{
                    'name': 'Awesome Dude Of The Year',
                    'date_awarded': 2007,
                    'url': None
                }]
            },
            'educational_background': {
                'schools': [{
                    'name': 'Foo University',
                    'degree': 'MSc CE/CS',
                    'notes': None,
                    'subject': None,
                    'begin_date': '1998-08',
                    'end_date': '2005-02'
                }],
                'qualifications': ['TOEFLS', 'PADI AOWD']
            },
            'photo_urls': {
                'large': 'http://www.xing.com/img/users/e/3/d/'
                         'f94ef165a.123456,1.140x185.jpg',
                'mini_thumb': 'http://www.xing.com/img/users/e/3/d/'
                              'f94ef165a.123456,1.18x24.jpg',
                'thumb': 'http://www.xing.com/img/users/e/3/d/'
                         'f94ef165a.123456,1.30x40.jpg',
                'medium_thumb': 'http://www.xing.com/img/users/e/3/d/'
                                'f94ef165a.123456,1.57x75.jpg',
                'maxi_thumb': 'http://www.xing.com/img/users/e/3/d/'
                              'f94ef165a.123456,1.70x93.jpg'
            }
        }]
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_yahoo
import json
from httpretty import HTTPretty

from social.p3 import urlencode
from social.tests.backends.oauth import OAuth1Test


class YahooOAuth1Test(OAuth1Test):
    backend_path = 'social.backends.yahoo.YahooOAuth'
    user_data_url = 'https://social.yahooapis.com/v1/user/a-guid/profile?' \
                    'format=json'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    request_token_body = urlencode({
        'oauth_token_secret': 'foobar-secret',
        'oauth_token': 'foobar',
        'oauth_callback_confirmed': 'true'
    })
    guid_body = json.dumps({
        'guid': {
            'uri': 'https://social.yahooapis.com/v1/me/guid',
            'value': 'a-guid'
        }
    })
    user_data_body = json.dumps({
        'profile': {
            'bdRestricted': True,
            'memberSince': '2007-12-11T14:40:30Z',
            'image': {
                'width': 192,
                'imageUrl': 'http://l.yimg.com/dh/ap/social/profile/'
                            'profile_b192.png',
                'size': '192x192',
                'height': 192
            },
            'created': '2013-03-18T04:15:08Z',
            'uri': 'https://social.yahooapis.com/v1/user/a-guid/profile',
            'isConnected': False,
            'profileUrl': 'http://profile.yahoo.com/a-guid',
            'guid': 'a-guid',
            'nickname': 'foobar'
        }
    })

    def test_login(self):
        HTTPretty.register_uri(
            HTTPretty.GET,
            'https://social.yahooapis.com/v1/me/guid?format=json',
            status=200,
            body=self.guid_body
        )
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_yammer
import json

from social.tests.backends.oauth import OAuth2Test


class YammerOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.yammer.YammerOAuth2'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': {
            'user_id': 1010101010,
            'view_groups': True,
            'modify_messages': True,
            'network_id': 101010,
            'created_at': '2013/03/17 16:39:56 +0000',
            'view_members': True,
            'authorized_at': '2013/03/17 16:39:56 +0000',
            'view_subscriptions': True,
            'view_messages': True,
            'modify_subscriptions': True,
            'token': 'foobar',
            'expires_at': None,
            'network_permalink': 'foobar.com',
            'view_tags': True,
            'network_name': 'foobar.com'
        },
        'user': {
            'last_name': 'Bar',
            'web_url': 'https://www.yammer.com/foobar/users/foobar',
            'expertise': None,
            'full_name': 'Foo Bar',
            'timezone': 'Pacific Time (US & Canada)',
            'mugshot_url': 'https://mug0.assets-yammer.com/mugshot/images/'
                           '48x48/no_photo.png',
            'guid': None,
            'network_name': 'foobar',
            'id': 1010101010,
            'previous_companies': [],
            'first_name': 'Foo',
            'stats': {
                'following': 0,
                'followers': 0,
                'updates': 1
            },
            'hire_date': None,
            'state': 'active',
            'location': None,
            'department': 'Software Development',
            'type': 'user',
            'show_ask_for_photo': True,
            'job_title': 'Software Developer',
            'interests': None,
            'kids_names': None,
            'activated_at': '2013/03/17 16:27:50 +0000',
            'verified_admin': 'false',
            'can_broadcast': 'false',
            'schools': [],
            'admin': 'false',
            'network_domains': ['foobar.com'],
            'name': 'foobar',
            'external_urls': [],
            'url': 'https://www.yammer.com/api/v1/users/1010101010',
            'settings': {
                'xdr_proxy': 'https://xdrproxy.yammer.com'
            },
            'summary': None,
            'network_id': 101010,
            'contact': {
                'phone_numbers': [],
                'im': {
                    'username': '',
                    'provider': ''
                },
                'email_addresses': [{
                    'type': 'primary',
                    'address': 'foo@bar.com'
                }],
                'has_fake_email': False
            },
            'birth_date': '',
            'mugshot_url_template': 'https://mug0.assets-yammer.com/mugshot/'
                                    'images/{width}x{height}/no_photo.png',
            'significant_other': None
        },
        'network': {
            'show_upgrade_banner': False,
            'header_text_color': '#FFFFFF',
            'is_org_chart_enabled': True,
            'name': 'foobar.com',
            'is_group_enabled': True,
            'header_background_color': '#396B9A',
            'created_at': '2012/12/26 16:52:35 +0000',
            'profile_fields_config': {
                'enable_work_phone': True,
                'enable_mobile_phone': True,
                'enable_job_title': True
            },
            'permalink': 'foobar.com',
            'paid': False,
            'id': 101010,
            'is_chat_enabled': True,
            'web_url': 'https://www.yammer.com/foobar.com',
            'moderated': False,
            'community': False,
            'type': 'network',
            'navigation_background_color': '#38699F',
            'navigation_text_color': '#FFFFFF'
        }
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = test_yandex
import json

from social.tests.backends.oauth import OAuth2Test


class YandexOAuth2Test(OAuth2Test):
    backend_path = 'social.backends.yandex.YandexOAuth2'
    user_data_url = 'https://login.yandex.ru/info'
    expected_username = 'foobar'
    access_token_body = json.dumps({
        'access_token': 'foobar',
        'token_type': 'bearer'
    })
    user_data_body = json.dumps({
        'display_name': 'foobar',
        'real_name': 'Foo Bar',
        'sex': None,
        'id': '101010101',
        'default_email': 'foobar@yandex.com',
        'emails': ['foobar@yandex.com']
    })

    def test_login(self):
        self.do_login()

    def test_partial_pipeline(self):
        self.do_partial_pipeline()

########NEW FILE########
__FILENAME__ = models
import base64

from social.storage.base import UserMixin, NonceMixin, AssociationMixin, \
                                CodeMixin, BaseStorage


class BaseModel(object):
    @classmethod
    def next_id(cls):
        cls.NEXT_ID += 1
        return cls.NEXT_ID - 1

    @classmethod
    def get(cls, key):
        return cls.cache.get(key)

    @classmethod
    def reset_cache(cls):
        cls.cache = {}


class User(BaseModel):
    NEXT_ID = 1
    cache = {}
    _is_active = True

    def __init__(self, username, email=None):
        self.id = User.next_id()
        self.username = username
        self.email = email
        self.password = None
        self.slug = None
        self.social = []
        self.extra_data = {}
        self.save()

    def is_active(self):
        return self._is_active

    @classmethod
    def set_active(cls, is_active=True):
        cls._is_active = is_active

    def set_password(self, password):
        self.password = password

    def save(self):
        User.cache[self.username] = self


class TestUserSocialAuth(UserMixin, BaseModel):
    NEXT_ID = 1
    cache = {}
    cache_by_uid = {}

    def __init__(self, user, provider, uid, extra_data=None):
        self.id = TestUserSocialAuth.next_id()
        self.user = user
        self.provider = provider
        self.uid = uid
        self.extra_data = extra_data or {}
        self.user.social.append(self)
        TestUserSocialAuth.cache_by_uid[uid] = self

    def save(self):
        pass

    @classmethod
    def reset_cache(cls):
        cls.cache = {}
        cls.cache_by_uid = {}

    @classmethod
    def changed(cls, user):
        pass

    @classmethod
    def get_username(cls, user):
        return user.username

    @classmethod
    def user_model(cls):
        return User

    @classmethod
    def username_max_length(cls):
        return 1024

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None):
        return user.password or len(user.social) > 1

    @classmethod
    def disconnect(cls, entry):
        cls.cache.pop(entry.id, None)
        entry.user.social = [s for s in entry.user.social if entry != s]

    @classmethod
    def user_exists(cls, username):
        return User.cache.get(username) is not None

    @classmethod
    def create_user(cls, username, email=None):
        return User(username=username, email=email)

    @classmethod
    def get_user(cls, pk):
        for username, user in User.cache.items():
            if user.id == pk:
                return user

    @classmethod
    def get_social_auth(cls, provider, uid):
        social_user = cls.cache_by_uid.get(uid)
        if social_user and social_user.provider == provider:
            return social_user

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        return user.social

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        return cls(user=user, provider=provider, uid=uid)

    @classmethod
    def get_users_by_email(cls, email):
        return [user for user in User.cache.values() if user.email == email]


class TestNonce(NonceMixin, BaseModel):
    NEXT_ID = 1
    cache = {}

    def __init__(self, server_url, timestamp, salt):
        self.id = TestNonce.next_id()
        self.server_url = server_url
        self.timestamp = timestamp
        self.salt = salt

    @classmethod
    def use(cls, server_url, timestamp, salt):
        nonce = TestNonce(server_url, timestamp, salt)
        TestNonce.cache[server_url] = nonce
        return nonce


class TestAssociation(AssociationMixin, BaseModel):
    NEXT_ID = 1
    cache = {}

    def __init__(self, server_url, handle):
        self.id = TestAssociation.next_id()
        self.server_url = server_url
        self.handle = handle

    def save(self):
        TestAssociation.cache[(self.server_url, self.handle)] = self

    @classmethod
    def store(cls, server_url, association):
        assoc = TestAssociation.cache.get((server_url, association.handle))
        if assoc is None:
            assoc = TestAssociation(server_url=server_url,
                                    handle=association.handle)
        assoc.secret = base64.encodestring(association.secret)
        assoc.issued = association.issued
        assoc.lifetime = association.lifetime
        assoc.assoc_type = association.assoc_type
        assoc.save()

    @classmethod
    def get(cls, server_url=None, handle=None):
        result = []
        for assoc in TestAssociation.cache.values():
            if server_url and assoc.server_url != server_url:
                continue
            if handle and assoc.handle != handle:
                continue
            result.append(assoc)
        return result

    @classmethod
    def remove(cls, ids_to_delete):
        assoc = filter(lambda a: a.id in ids_to_delete,
                       TestAssociation.cache.values())
        for a in list(assoc):
            TestAssociation.cache.pop((a.server_url, a.handle), None)


class TestCode(CodeMixin, BaseModel):
    NEXT_ID = 1
    cache = {}

    @classmethod
    def get_code(cls, code):
        for c in cls.cache.values():
            if c.code == code:
                return c


class TestStorage(BaseStorage):
    user = TestUserSocialAuth
    nonce = TestNonce
    association = TestAssociation
    code = TestCode

########NEW FILE########
__FILENAME__ = pipeline
from social.pipeline.partial import partial


def ask_for_password(strategy, *args, **kwargs):
    if strategy.session_get('password'):
        return {'password': strategy.session_get('password')}
    else:
        return strategy.redirect(strategy.build_absolute_uri('/password'))


@partial
def ask_for_slug(strategy, *args, **kwargs):
    if strategy.session_get('slug'):
        return {'slug': strategy.session_get('slug')}
    else:
        return strategy.redirect(strategy.build_absolute_uri('/slug'))


def set_password(strategy, user, *args, **kwargs):
    user.set_password(kwargs['password'])


def set_slug(strategy, user, *args, **kwargs):
    user.slug = kwargs['slug']


def remove_user(strategy, user, *args, **kwargs):
    return {'user': None}

########NEW FILE########
__FILENAME__ = strategy
from social.strategies.base import BaseStrategy, BaseTemplateStrategy


TEST_URI = 'http://myapp.com'
TEST_HOST = 'myapp.com'


class Redirect(object):
    def __init__(self, url):
        self.url = url


class TestTemplateStrategy(BaseTemplateStrategy):
    def render_template(self, tpl, context):
        return tpl

    def render_string(self, html, context):
        return html


class TestStrategy(BaseStrategy):
    def __init__(self, *args, **kwargs):
        self._request_data = {}
        self._settings = {}
        self._session = {}
        kwargs.setdefault('tpl', TestTemplateStrategy)
        super(TestStrategy, self).__init__(*args, **kwargs)

    def redirect(self, url):
        return Redirect(url)

    def get_setting(self, name):
        """Return value for given setting name"""
        return self._settings[name]

    def html(self, content):
        """Return HTTP response with given content"""
        return content

    def render_html(self, tpl=None, html=None, context=None):
        """Render given template or raw html with given context"""
        return tpl or html

    def request_data(self, merge=True):
        """Return current request data (POST or GET)"""
        return self._request_data

    def request_host(self):
        """Return current host value"""
        return TEST_HOST

    def session_get(self, name, default=None):
        """Return session value for given key"""
        return self._session.get(name, default)

    def session_set(self, name, value):
        """Set session value for given key"""
        self._session[name] = value

    def session_pop(self, name):
        """Pop session value for given key"""
        return self._session.pop(name, None)

    def build_absolute_uri(self, path=None):
        """Build absolute URI with given (optional) path"""
        path = path or ''
        if path.startswith('http://') or path.startswith('https://'):
            return path
        return TEST_URI + path

    def set_settings(self, values):
        self._settings.update(values)

    def set_request_data(self, values):
        self._request_data.update(values)

    def remove_from_request_data(self, name):
        self._request_data.pop(name, None)

    def authenticate(self, *args, **kwargs):
        user = super(TestStrategy, self).authenticate(*args, **kwargs)
        if isinstance(user, self.storage.user.user_model()):
            self.session_set('username', user.username)
        return user

    def get_pipeline(self):
        return self.setting('PIPELINE', (
            'social.pipeline.social_auth.social_details',
            'social.pipeline.social_auth.social_uid',
            'social.pipeline.social_auth.auth_allowed',
            'social.pipeline.social_auth.social_user',
            'social.pipeline.user.get_username',
            'social.pipeline.social_auth.associate_by_email',
            'social.pipeline.user.create_user',
            'social.pipeline.social_auth.associate_user',
            'social.pipeline.social_auth.load_extra_data',
            'social.pipeline.user.user_details'))

########NEW FILE########
__FILENAME__ = test_exceptions
import unittest
from sure import expect

from social.exceptions import SocialAuthBaseException, WrongBackend, \
                              AuthFailed, AuthTokenError, \
                              AuthMissingParameter, AuthStateMissing, \
                              NotAllowedToDisconnect, AuthException, \
                              AuthCanceled, AuthUnknownError, \
                              AuthStateForbidden, AuthAlreadyAssociated, \
                              AuthTokenRevoked


class BaseExceptionTestCase(unittest.TestCase):
    exception = None
    expected_message = ''

    def test_exception_message(self):
        if self.exception is None and self.expected_message == '':
            return
        try:
            raise self.exception
        except SocialAuthBaseException as err:
            expect(str(err)).to.equal(self.expected_message)


class WrongBackendTest(BaseExceptionTestCase):
    exception = WrongBackend('foobar')
    expected_message = 'Incorrect authentication service "foobar"'


class AuthFailedTest(BaseExceptionTestCase):
    exception = AuthFailed('foobar', 'wrong_user')
    expected_message = 'Authentication failed: wrong_user'


class AuthFailedDeniedTest(BaseExceptionTestCase):
    exception = AuthFailed('foobar', 'access_denied')
    expected_message = 'Authentication process was canceled'


class AuthTokenErrorTest(BaseExceptionTestCase):
    exception = AuthTokenError('foobar', 'Incorrect tokens')
    expected_message = 'Token error: Incorrect tokens'


class AuthMissingParameterTest(BaseExceptionTestCase):
    exception = AuthMissingParameter('foobar', 'username')
    expected_message = 'Missing needed parameter username'


class AuthStateMissingTest(BaseExceptionTestCase):
    exception = AuthStateMissing('foobar')
    expected_message = 'Session value state missing.'


class NotAllowedToDisconnectTest(BaseExceptionTestCase):
    exception = NotAllowedToDisconnect()
    expected_message = ''


class AuthExceptionTest(BaseExceptionTestCase):
    exception = AuthException('foobar', 'message')
    expected_message = 'message'


class AuthCanceledTest(BaseExceptionTestCase):
    exception = AuthCanceled('foobar')
    expected_message = 'Authentication process canceled'


class AuthUnknownErrorTest(BaseExceptionTestCase):
    exception = AuthUnknownError('foobar', 'some error')
    expected_message = 'An unknown error happened while ' \
                       'authenticating some error'


class AuthStateForbiddenTest(BaseExceptionTestCase):
    exception = AuthStateForbidden('foobar')
    expected_message = 'Wrong state parameter given.'


class AuthAlreadyAssociatedTest(BaseExceptionTestCase):
    exception = AuthAlreadyAssociated('foobar')
    expected_message = ''


class AuthTokenRevokedTest(BaseExceptionTestCase):
    exception = AuthTokenRevoked('foobar')
    expected_message = 'User revoke access to the token'

########NEW FILE########
__FILENAME__ = test_pipeline
import json

from sure import expect

from social.exceptions import AuthException

from social.tests.models import TestUserSocialAuth, TestStorage, User
from social.tests.strategy import TestStrategy
from social.tests.actions.actions import BaseActionTest


class IntegrityError(Exception):
    pass


class UnknownError(Exception):
    pass


class IntegrityErrorUserSocialAuth(TestUserSocialAuth):
    @classmethod
    def create_social_auth(cls, user, uid, provider):
        raise IntegrityError()

    @classmethod
    def get_social_auth(cls, provider, uid):
        if not hasattr(cls, '_called_times'):
            cls._called_times = 0
        cls._called_times += 1
        if cls._called_times == 2:
            user = list(User.cache.values())[0]
            return IntegrityErrorUserSocialAuth(user, provider, uid)
        else:
            return super(IntegrityErrorUserSocialAuth, cls).get_social_auth(
                provider, uid
            )


class IntegrityErrorStorage(TestStorage):
    user = IntegrityErrorUserSocialAuth

    @classmethod
    def is_integrity_error(cls, exception):
        """Check if given exception flags an integrity error in the DB"""
        return isinstance(exception, IntegrityError)


class UnknownErrorUserSocialAuth(TestUserSocialAuth):
    @classmethod
    def create_social_auth(cls, user, uid, provider):
        raise UnknownError()


class UnknownErrorStorage(IntegrityErrorStorage):
    user = UnknownErrorUserSocialAuth


class IntegrityErrorOnLoginTest(BaseActionTest):
    def setUp(self):
        super(IntegrityErrorOnLoginTest, self).setUp()
        self.strategy = TestStrategy(self.backend, IntegrityErrorStorage)

    def test_integrity_error(self):
        self.do_login()


class UnknownErrorOnLoginTest(BaseActionTest):
    def setUp(self):
        super(UnknownErrorOnLoginTest, self).setUp()
        self.strategy = TestStrategy(self.backend, UnknownErrorStorage)

    def test_unknown_error(self):
        self.do_login.when.called_with().should.throw(UnknownError)


class EmailAsUsernameTest(BaseActionTest):
    expected_username = 'foo@bar.com'

    def test_email_as_username(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL': True
        })
        self.do_login()


class RandomUsernameTest(BaseActionTest):
    user_data_body = json.dumps({
        'id': 1,
        'avatar_url': 'https://github.com/images/error/foobar_happy.gif',
        'gravatar_id': 'somehexcode',
        'url': 'https://api.github.com/users/foobar',
        'name': 'monalisa foobar',
        'company': 'GitHub',
        'blog': 'https://github.com/blog',
        'location': 'San Francisco',
        'email': 'foo@bar.com',
        'hireable': False,
        'bio': 'There once was...',
        'public_repos': 2,
        'public_gists': 1,
        'followers': 20,
        'following': 0,
        'html_url': 'https://github.com/foobar',
        'created_at': '2008-01-14T04:33:35Z',
        'type': 'User',
        'total_private_repos': 100,
        'owned_private_repos': 100,
        'private_gists': 81,
        'disk_usage': 10000,
        'collaborators': 8,
        'plan': {
            'name': 'Medium',
            'space': 400,
            'collaborators': 10,
            'private_repos': 20
        }
    })

    def test_random_username(self):
        self.do_login(after_complete_checks=False)


class SluggedUsernameTest(BaseActionTest):
    expected_username = 'foo-bar'
    user_data_body = json.dumps({
        'login': 'Foo Bar',
        'id': 1,
        'avatar_url': 'https://github.com/images/error/foobar_happy.gif',
        'gravatar_id': 'somehexcode',
        'url': 'https://api.github.com/users/foobar',
        'name': 'monalisa foobar',
        'company': 'GitHub',
        'blog': 'https://github.com/blog',
        'location': 'San Francisco',
        'email': 'foo@bar.com',
        'hireable': False,
        'bio': 'There once was...',
        'public_repos': 2,
        'public_gists': 1,
        'followers': 20,
        'following': 0,
        'html_url': 'https://github.com/foobar',
        'created_at': '2008-01-14T04:33:35Z',
        'type': 'User',
        'total_private_repos': 100,
        'owned_private_repos': 100,
        'private_gists': 81,
        'disk_usage': 10000,
        'collaborators': 8,
        'plan': {
            'name': 'Medium',
            'space': 400,
            'collaborators': 10,
            'private_repos': 20
        }
    })

    def test_random_username(self):
        self.strategy.set_settings({
            'SOCIAL_AUTH_CLEAN_USERNAMES': False,
            'SOCIAL_AUTH_SLUGIFY_USERNAMES': True
        })
        self.do_login()


class RepeatedUsernameTest(BaseActionTest):
    def test_random_username(self):
        User(username='foobar')
        self.do_login(after_complete_checks=False)
        expect(self.strategy.session_get('username').startswith('foobar')) \
                .to.equal(True)


class AssociateByEmailTest(BaseActionTest):
    def test_multiple_accounts_with_same_email(self):
        user = User(username='foobar1')
        user.email = 'foo@bar.com'
        self.do_login(after_complete_checks=False)
        expect(self.strategy.session_get('username').startswith('foobar')) \
                .to.equal(True)


class MultipleAccountsWithSameEmailTest(BaseActionTest):
    def test_multiple_accounts_with_same_email(self):
        user1 = User(username='foobar1')
        user2 = User(username='foobar2')
        user1.email = 'foo@bar.com'
        user2.email = 'foo@bar.com'
        self.do_login.when.called_with(after_complete_checks=False)\
            .should.throw(AuthException)

########NEW FILE########
__FILENAME__ = test_storage
import six
import random
import unittest

from sure import expect

from social.strategies.base import BaseStrategy
from social.storage.base import UserMixin, NonceMixin, AssociationMixin, \
                                CodeMixin, BaseStorage

from social.tests.models import User


class BrokenUser(UserMixin):
    pass


class BrokenAssociation(AssociationMixin):
    pass


class BrokenNonce(NonceMixin):
    pass


class BrokenCode(CodeMixin):
    pass


class BrokenStrategy(BaseStrategy):
    pass


class BrokenStrategyWithSettings(BrokenStrategy):
    def get_setting(self, name):
        raise AttributeError()


class BrokenStorage(BaseStorage):
    pass


class BrokenUserTests(unittest.TestCase):
    def setUp(self):
        self.user = BrokenUser

    def tearDown(self):
        self.user = None

    def test_get_username(self):
        self.user.get_username.when.called_with(User('foobar')).should.throw(
            NotImplementedError, 'Implement in subclass'
        )

    def test_user_model(self):
        self.user.user_model.when.called_with().should.throw(
            NotImplementedError, 'Implement in subclass'
        )

    def test_username_max_length(self):
        self.user.username_max_length.when.called_with().should.throw(
            NotImplementedError, 'Implement in subclass'
        )

    def test_get_user(self):
        self.user.get_user.when.called_with(1).should.throw(
            NotImplementedError, 'Implement in subclass'
        )

    def test_get_social_auth(self):
        self.user.get_social_auth.when.called_with('foo', 1).should.throw(
            NotImplementedError, 'Implement in subclass'
        )

    def test_get_social_auth_for_user(self):
        self.user.get_social_auth_for_user.when.called_with(User('foobar')) \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_create_social_auth(self):
        self.user.create_social_auth.when \
            .called_with(User('foobar'), 1, 'foo') \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_disconnect(self):
        self.user.disconnect\
            .when.called_with(BrokenUser())\
            .should.throw(NotImplementedError, 'Implement in subclass')


class BrokenAssociationTests(unittest.TestCase):
    def setUp(self):
        self.association = BrokenAssociation

    def tearDown(self):
        self.association = None

    def test_store(self):
        self.association.store.when \
            .called_with('http://foobar.com', BrokenAssociation()) \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_get(self):
        self.association.get.when.called_with() \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_remove(self):
        self.association.remove.when.called_with([1, 2, 3]) \
            .should.throw(NotImplementedError, 'Implement in subclass')


class BrokenNonceTests(unittest.TestCase):
    def setUp(self):
        self.nonce = BrokenNonce

    def tearDown(self):
        self.nonce = None

    def test_use(self):
        self.nonce.use.when \
            .called_with('http://foobar.com', 1364951922, 'foobar123') \
            .should.throw(NotImplementedError, 'Implement in subclass')


class BrokenCodeTest(unittest.TestCase):
    def setUp(self):
        self.code = BrokenCode

    def tearDown(self):
        self.code = None

    def test_get_code(self):
        self.code.get_code.when \
            .called_with('foobar') \
            .should.throw(NotImplementedError, 'Implement in subclass')


class BrokenStrategyTests(unittest.TestCase):
    def setUp(self):
        self.strategy = BrokenStrategy(storage=BrokenStorage)

    def tearDown(self):
        self.strategy = None

    def test_redirect(self):
        self.strategy.redirect.when \
            .called_with('http://foobar.com') \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_get_setting(self):
        self.strategy.get_setting.when \
            .called_with('foobar') \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_html(self):
        self.strategy.html.when \
            .called_with('<p>foobar</p>') \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_request_data(self):
        self.strategy.request_data.when \
            .called_with() \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_request_host(self):
        self.strategy.request_host.when \
            .called_with() \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_session_get(self):
        self.strategy.session_get.when \
            .called_with('foobar') \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_session_set(self):
        self.strategy.session_set.when \
            .called_with('foobar', 123) \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_session_pop(self):
        self.strategy.session_pop.when \
            .called_with('foobar') \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_build_absolute_uri(self):
        self.strategy.build_absolute_uri.when \
            .called_with('/foobar') \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_render_html_with_tpl(self):
        self.strategy.render_html.when \
            .called_with('foobar.html', context={}) \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_render_html_with_html(self):
        self.strategy.render_html.when \
            .called_with(html='<p>foobar</p>', context={}) \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_render_html_with_none(self):
        self.strategy.render_html.when \
            .called_with() \
            .should.throw(ValueError, 'Missing template or html parameters')

    def test_is_integrity_error(self):
        self.strategy.storage.is_integrity_error.when \
            .called_with(None) \
            .should.throw(NotImplementedError, 'Implement in subclass')

    def test_random_string(self):
        expect(isinstance(self.strategy.random_string(), six.string_types)) \
                .to.equal(True)

    def test_random_string_without_systemrandom(self):
        def SystemRandom():
            raise NotImplementedError()

        orig_random = getattr(random, 'SystemRandom', None)
        random.SystemRandom = SystemRandom

        strategy = BrokenStrategyWithSettings(storage=BrokenStorage)
        expect(isinstance(strategy.random_string(), six.string_types)) \
                .to.equal(True)
        random.SystemRandom = orig_random

########NEW FILE########
__FILENAME__ = test_utils
import sys
import unittest

from mock import Mock
from sure import expect

from social.utils import sanitize_redirect, user_is_authenticated, \
                         user_is_active, slugify, build_absolute_uri, \
                         partial_pipeline_data


PY3 = sys.version_info[0] == 3


class SanitizeRedirectTest(unittest.TestCase):
    def test_none_redirect(self):
        expect(sanitize_redirect('myapp.com', None)).to.equal(None)

    def test_empty_redirect(self):
        expect(sanitize_redirect('myapp.com', '')).to.equal(None)

    def test_dict_redirect(self):
        expect(sanitize_redirect('myapp.com', {})).to.equal(None)

    def test_invalid_redirect(self):
        expect(sanitize_redirect('myapp.com',
                                 {'foo': 'bar'})).to.equal(None)

    def test_wrong_path_redirect(self):
        expect(sanitize_redirect(
            'myapp.com',
            'http://notmyapp.com/path/'
        )).to.equal(None)

    def test_valid_absolute_redirect(self):
        expect(sanitize_redirect(
            'myapp.com',
            'http://myapp.com/path/'
        )).to.equal('http://myapp.com/path/')

    def test_valid_relative_redirect(self):
        expect(sanitize_redirect('myapp.com', '/path/')).to.equal('/path/')


class UserIsAuthenticatedTest(unittest.TestCase):
    def test_user_is_none(self):
        expect(user_is_authenticated(None)).to.equal(False)

    def test_user_is_not_none(self):
        expect(user_is_authenticated(object())).to.equal(True)

    def test_user_has_is_authenticated(self):
        class User(object):
            is_authenticated = True
        expect(user_is_authenticated(User())).to.equal(True)

    def test_user_has_is_authenticated_callable(self):
        class User(object):
            def is_authenticated(self):
                return True
        expect(user_is_authenticated(User())).to.equal(True)


class UserIsActiveTest(unittest.TestCase):
    def test_user_is_none(self):
        expect(user_is_active(None)).to.equal(False)

    def test_user_is_not_none(self):
        expect(user_is_active(object())).to.equal(True)

    def test_user_has_is_active(self):
        class User(object):
            is_active = True
        expect(user_is_active(User())).to.equal(True)

    def test_user_has_is_active_callable(self):
        class User(object):
            def is_active(self):
                return True
        expect(user_is_active(User())).to.equal(True)


class SlugifyTest(unittest.TestCase):
    def test_slugify_formats(self):
        if PY3:
            expect(slugify('FooBar')).to.equal('foobar')
            expect(slugify('Foo Bar')).to.equal('foo-bar')
            expect(slugify('Foo (Bar)')).to.equal('foo-bar')
        else:
            expect(slugify('FooBar'.decode('utf-8'))).to.equal('foobar')
            expect(slugify('Foo Bar'.decode('utf-8'))).to.equal('foo-bar')
            expect(slugify('Foo (Bar)'.decode('utf-8'))).to.equal('foo-bar')


class BuildAbsoluteURITest(unittest.TestCase):
    def setUp(self):
        self.host = 'http://foobar.com'

    def tearDown(self):
        self.host = None

    def test_path_none(self):
        expect(build_absolute_uri(self.host)).to.equal(self.host)

    def test_path_empty(self):
        expect(build_absolute_uri(self.host, '')).to.equal(self.host)

    def test_path_http(self):
        expect(build_absolute_uri(self.host, 'http://barfoo.com')) \
              .to.equal('http://barfoo.com')

    def test_path_https(self):
        expect(build_absolute_uri(self.host, 'https://barfoo.com')) \
              .to.equal('https://barfoo.com')

    def test_host_ends_with_slash_and_path_starts_with_slash(self):
        expect(build_absolute_uri(self.host + '/', '/foo/bar')) \
              .to.equal('http://foobar.com/foo/bar')

    def test_absolute_uri(self):
        expect(build_absolute_uri(self.host, '/foo/bar')) \
              .to.equal('http://foobar.com/foo/bar')


class PartialPipelineData(unittest.TestCase):
    def test_kwargs_included_in_result(self):
        strategy = self._strategy()
        kwargitem = ('foo', 'bar')
        _, xkwargs = partial_pipeline_data(strategy, None,
                                           *(), **dict([kwargitem]))
        xkwargs.should.have.key(kwargitem[0]).being.equal(kwargitem[1])

    def test_update_user(self):
        user = object()
        strategy = self._strategy(session_kwargs={'user': None})
        _, xkwargs = partial_pipeline_data(strategy, user)
        xkwargs.should.have.key('user').being.equal(user)

    def _strategy(self, session_kwargs=None):
        backend = Mock()
        backend.name = 'mock-backend'

        strategy = Mock()
        strategy.request = None
        strategy.backend = backend
        strategy.session_get.return_value = object()
        strategy.partial_from_session.return_value = \
            (0, backend.name, [], session_kwargs or {})
        return strategy

########NEW FILE########
__FILENAME__ = utils
import re
import sys
import unicodedata
import collections
import six

from social.p3 import urlparse, urlunparse, urlencode, \
                      parse_qs as battery_parse_qs


SETTING_PREFIX = 'SOCIAL_AUTH'


def import_module(name):
    __import__(name)
    return sys.modules[name]


def module_member(name):
    mod, member = name.rsplit('.', 1)
    module = import_module(mod)
    return getattr(module, member)


def url_add_parameters(url, params):
    """Adds parameters to URL, parameter will be repeated if already present"""
    if params:
        fragments = list(urlparse(url))
        value = parse_qs(fragments[4])
        value.update(params)
        fragments[4] = urlencode(value)
        url = urlunparse(fragments)
    return url


def to_setting_name(*names):
    return '_'.join([name.upper().replace('-', '_') for name in names if name])


def setting_name(*names):
    return to_setting_name(*((SETTING_PREFIX,) + names))


def sanitize_redirect(host, redirect_to):
    """
    Given the hostname and an untrusted URL to redirect to,
    this method tests it to make sure it isn't garbage/harmful
    and returns it, else returns None, similar as how's it done
    on django.contrib.auth.views.
    """
    if redirect_to:
        try:
            # Don't redirect to a different host
            netloc = urlparse(redirect_to)[1] or host
        except (TypeError, AttributeError):
            pass
        else:
            if netloc == host:
                return redirect_to


def user_is_authenticated(user):
    if user and hasattr(user, 'is_authenticated'):
        if isinstance(user.is_authenticated, collections.Callable):
            authenticated = user.is_authenticated()
        else:
            authenticated = user.is_authenticated
    elif user:
        authenticated = True
    else:
        authenticated = False
    return authenticated


def user_is_active(user):
    if user and hasattr(user, 'is_active'):
        if isinstance(user.is_active, collections.Callable):
            is_active = user.is_active()
        else:
            is_active = user.is_active
    elif user:
        is_active = True
    else:
        is_active = False
    return is_active


# This slugify version was borrowed from django revision a61dbd6
def slugify(value):
    """Converts to lowercase, removes non-word characters (alphanumerics
    and underscores) and converts spaces to hyphens. Also strips leading
    and trailing whitespace."""
    value = unicodedata.normalize('NFKD', value) \
                       .encode('ascii', 'ignore') \
                       .decode('ascii')
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)


def first(func, items):
    """Return the first item in the list for what func returns True"""
    for item in items:
        if func(item):
            return item


def parse_qs(value):
    """Like urlparse.parse_qs but transform list values to single items"""
    return drop_lists(battery_parse_qs(value))


def drop_lists(value):
    out = {}
    for key, val in value.items():
        val = val[0]
        if isinstance(key, six.binary_type):
            key = six.text_type(key, 'utf-8')
        if isinstance(val, six.binary_type):
            val = six.text_type(val, 'utf-8')
        out[key] = val
    return out


def partial_pipeline_data(strategy, user=None, *args, **kwargs):
    partial = strategy.session_get('partial_pipeline', None)
    if partial:
        idx, backend, xargs, xkwargs = strategy.partial_from_session(partial)
        if backend == strategy.backend.name:
            kwargs.setdefault('pipeline_index', idx)
            if user:  # don't update user if it's None
                kwargs.setdefault('user', user)
            kwargs.setdefault('request', strategy.request)
            xkwargs.update(kwargs)
            return xargs, xkwargs
        else:
            strategy.clean_partial_pipeline()


def build_absolute_uri(host_url, path=None):
    """Build absolute URI with given (optional) path"""
    path = path or ''
    if path.startswith('http://') or path.startswith('https://'):
        return path
    if host_url.endswith('/') and path.startswith('/'):
        path = path[1:]
    return host_url + path


def constant_time_compare(val1, val2):
    """
    Returns True if the two strings are equal, False otherwise.
    The time taken is independent of the number of characters that match.
    This code was borrowed from Django 1.5.4-final
    """
    if len(val1) != len(val2):
        return False
    result = 0
    if six.PY3 and isinstance(val1, bytes) and isinstance(val2, bytes):
        for x, y in zip(val1, val2):
            result |= x ^ y
    else:
        for x, y in zip(val1, val2):
            result |= ord(x) ^ ord(y)
    return result == 0


def is_url(value):
    return value and \
           (value.startswith('http://') or
            value.startswith('https://') or
            value.startswith('/'))


def setting_url(strategy, *names):
    for name in names:
        if is_url(name):
            return name
        else:
            value = strategy.setting(name)
            if is_url(value):
                return value

########NEW FILE########
