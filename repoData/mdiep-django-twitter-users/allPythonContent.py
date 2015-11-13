__FILENAME__ = backends

from django.contrib.auth.models import User

from twitter_users.models import TwitterInfo
from twitter_users import settings

class TwitterBackend(object):
    def authenticate(self, twitter_id=None, username=None, token=None, secret=None):
        # find or create the user
        try:
            info = TwitterInfo.objects.get(id=twitter_id)
            # make sure the screen name is current
            if info.name != username:
                info.name = username
                info.save()
            user = info.user
        except TwitterInfo.DoesNotExist:
            email    = "%s@twitter.com" % username
            user     = User.objects.create_user(settings.USERS_FORMAT % username, email)
            user.save()
            info = TwitterInfo(user=user, name=username, id=twitter_id, token=token, secret=secret)
            info.save()
        return user
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = models

from django.db import models
from django.contrib.auth.models import User

class TwitterInfo(models.Model):
    user = models.OneToOneField(User)
    
    name    = models.CharField(max_length=15)
    id      = models.BigIntegerField(primary_key=True)
    
    token   = models.CharField(max_length=100)
    secret  = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = oauth

import oauth2
import urllib

from twitter_users import settings

# not sure why this is necessary, but oauth2 does this, so I'm following its lead
try:
    from urlparse import parse_qs, parse_qsl
except ImportError:
    from cgi import parse_qs, parse_qsl

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'

class Consumer(oauth2.Consumer):
    pass

class Token(object):
    def __init__(self, consumer):
        self.consumer = consumer
    
    def _get_token(self, url, token=None, method='POST', **parameters):
        client            = oauth2.Client(self.consumer, token)
        response, content = client.request(url,
            method  = method,
            body    = urllib.urlencode(parameters)
        )
        
        if response['status'] != '200':
            return None;
        
        return content

class RequestToken(Token):
    def __init__(self, consumer, callback_url=None):
        super(RequestToken, self).__init__(consumer)
        
        parameters = {}
        if callback_url is not None:
            parameters['oauth_callback'] = callback_url
        
        token_content = self._get_token(REQUEST_TOKEN_URL, **parameters)
        self.token    = oauth2.Token.from_string(token_content)
    
    @property
    def authorization_url(self):
        request = oauth2.Request.from_consumer_and_token(
            self.consumer,
            self.token,
            http_url = AUTHORIZATION_URL
        )
        request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), self.consumer, self.token)
        return request.to_url()

class AccessToken(Token):
    def __init__(self, consumer, oauth_token, oauth_verifier):
        super(AccessToken, self).__init__(consumer)
        
        # parse the access token by hand to get access to the additional
        # parameters that Twitter passes back, like the user id and screen name
        token_content = self._get_token(ACCESS_TOKEN_URL, oauth_token=oauth_token, oauth_verifier=oauth_verifier)
        self.params   = parse_qs(token_content)
    
    @property
    def token(self):
        return self.params['oauth_token'][0]
    
    @property
    def secret(self):
        return self.params['oauth_token_secret'][0]
    
    @property
    def user_id(self):
        return self.params['user_id'][0]
    
    @property
    def username(self):
        return self.params['screen_name'][0]

########NEW FILE########
__FILENAME__ = settings

from django.conf import settings

# Required
KEY                  = settings.TWITTER_KEY
SECRET               = settings.TWITTER_SECRET

# Optional
LOGIN_REDIRECT_VIEW  = getattr(settings, 'LOGIN_REDIRECT_VIEW', None)
LOGIN_REDIRECT_URL   = settings.LOGIN_REDIRECT_URL # Django supplies a default value

LOGOUT_REDIRECT_VIEW = getattr(settings, 'LOGOUT_REDIRECT_VIEW', None)
LOGOUT_REDIRECT_URL  = getattr(settings, 'LOGOUT_REDIRECT_URL',  '/')

PROFILE_MODULE       = getattr(settings, 'AUTH_PROFILE_MODULE',
                                         'twitter_users.models.UserProfile')
USERS_FORMAT         = getattr(settings, 'TWITTER_USERS_FORMAT', '%s')


########NEW FILE########
__FILENAME__ = urls

from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('twitter_users.views',
    url(r'^login/?$',           'twitter_login',    name='twitter-login'),
    url(r'^login/callback/?$',  'twitter_callback', name='twitter-callback'),
    url(r'^logout/?$',          'twitter_logout',   name='twitter-logout'),
)


########NEW FILE########
__FILENAME__ = views

import re

from django.core.urlresolvers import reverse, NoReverseMatch
from django.http import HttpResponseRedirect

from django.contrib.auth import authenticate, login, logout

from twitter_users import oauth
from twitter_users import settings

def is_safe_redirect(redirect_to):
    if ' ' in redirect_to:
        return False
    # exclude http://foo.com URLs, but not paths with GET parameters that
    # have URLs in them (/?foo=http://foo.com)
    elif '//' in redirect_to and re.match(r'[^\?]*//', redirect_to):
        return False
    return True

def twitter_login(request, redirect_field_name='next'):
    # construct the callback URL
    try:
        protocol      = 'https' if request.is_secure() else 'http'
        host          = request.get_host()
        path          = reverse('twitter-callback')
        callback_url  = protocol + '://' + host + path
    except NoReverseMatch:
        callback_url  = None
    
    # get a request token from Twitter
    consumer      = oauth.Consumer(settings.KEY, settings.SECRET)
    request_token = oauth.RequestToken(consumer, callback_url=callback_url)
    
    # save the redirect destination
    request.session['redirect_to'] = request.REQUEST.get(redirect_field_name, None)
    
    # redirect to Twitter for authorization
    return HttpResponseRedirect(request_token.authorization_url)

def twitter_callback(request):
    oauth_token    = request.GET['oauth_token']
    oauth_verifier = request.GET['oauth_verifier']
    
    # get an access token from Twitter
    consumer           = oauth.Consumer(settings.KEY, settings.SECRET)
    access_token       = oauth.AccessToken(consumer, oauth_token, oauth_verifier)
    
    # actually log in
    user = authenticate(twitter_id  = access_token.user_id,
                        username    = access_token.username,
                        token       = access_token.token,
                        secret      = access_token.secret)
    login(request, user)
    
    # redirect to the authenticated view
    redirect_to = request.session['redirect_to']
    if not redirect_to or not is_safe_redirect(redirect_to):
        try:
            redirect_to = reverse(settings.LOGIN_REDIRECT_VIEW, args=[user.id])
        except NoReverseMatch:
            redirect_to = settings.LOGIN_REDIRECT_URL
    
    return HttpResponseRedirect(redirect_to)

def twitter_logout(request, redirect_field_name='next'):
    if request.user.is_authenticated():
        # get the redirect destination
        redirect_to = request.REQUEST.get(redirect_field_name, None)
        if not redirect_to or not is_safe_redirect(redirect_to):
            try:
                redirect_to = reverse(settings.LOGOUT_REDIRECT_VIEW, args=[request.user.id])
            except NoReverseMatch:
                redirect_to = settings.LOGOUT_REDIRECT_URL
        
        logout(request)
    else:
        redirect_to = '/'
    
    return HttpResponseRedirect(redirect_to)


########NEW FILE########
