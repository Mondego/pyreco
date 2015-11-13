__FILENAME__ = decorators
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from models import User

def wants_user(f):
	def decorated(*args, **kwargs):
		try: args[0].user = User.objects.get(pk=args[0].session['user_id'])
		except: args[0].user = None
		return f(*args, **kwargs)
	return decorated

def needs_user(url):
	def decorated1(f):
		@wants_user
		def decorated2(*args, **kwargs):
			if not args[0].user: return HttpResponseRedirect(reverse(url))
			else: return f(*args, **kwargs)
		return decorated2
	return decorated1

########NEW FILE########
__FILENAME__ = models
from django.db import models
from oauth import oauth
import re, httplib, simplejson
from utils import *

class User(models.Model):
	username = models.CharField(max_length=40)
	email = models.EmailField()
	oauth_token = models.CharField(max_length=200)
	oauth_token_secret = models.CharField(max_length=200)

	def validate(self):
		errors = []
		if self.username and not re.compile('^[a-zA-Z0-9_]{1,40}$').match( \
			self.username):
			errors += ['username']
		if self.email and not re.compile( \
			'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$').match( \
			self.email):
			errors += ['email']
		return errors

	# django.core.context_processors.auth assumes that an object attached
	# to request.user is always a django.contrib.auth.models.User, which
	# is completely broken but easy to work around
	def get_and_delete_messages(self): pass

	def token(self):
		return oauth.OAuthToken(self.oauth_token, self.oauth_token_secret)

	def is_authorized(self): return is_authorized(self.token())

	def tweet(self, status):
		return api(
			'https://twitter.com/statuses/update.json',
			self.token(),
			http_method='POST',
			status=status
		)
########NEW FILE########
__FILENAME__ = utils
# Taken almost verbatim from Henrik Lied's django-twitter-oauth app
# http://github.com/henriklied/django-twitter-oauth

from django.conf import settings
from django.utils import simplejson as json
from oauth import oauth
import httplib

signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

TWITTERAUTH_KEY = getattr(settings, 'TWITTERAUTH_KEY', 'OH HAI')
TWITTERAUTH_SECRET = getattr(settings, 'TWITTERAUTH_SECRET', 'OH NOES')

def consumer():
	try: return consumer._consumer
	except AttributeError:
		consumer._consumer = oauth.OAuthConsumer(TWITTERAUTH_KEY, TWITTERAUTH_SECRET)
		return consumer._consumer

def connection():
	try: return connection._connection
	except AttributeError:
		connection._connection = httplib.HTTPSConnection('twitter.com')
		return connection._connection

def oauth_request(
	url,
	token,
	parameters=None,
	signature_method=signature_method,
	http_method='GET'
):
	req = oauth.OAuthRequest.from_consumer_and_token(
		consumer(), token=token, http_url=url,
		parameters=parameters, http_method=http_method
	)
	req.sign_request(signature_method, consumer(), token)
	return req

def oauth_response(req):
	connection().request(req.http_method, req.to_url())
	return connection().getresponse().read()

def get_unauthorized_token(signature_method=signature_method):
	req = oauth.OAuthRequest.from_consumer_and_token(
		consumer(), http_url='https://twitter.com/oauth/request_token'
	)
	req.sign_request(signature_method, consumer(), None)
	return oauth.OAuthToken.from_string(oauth_response(req))

def get_authorization_url(token, signature_method=signature_method):
	req = oauth.OAuthRequest.from_consumer_and_token(
		consumer(), token=token,
		http_url='http://twitter.com/oauth/authorize'
	)
	req.sign_request(signature_method, consumer(), token)
	return req.to_url()

def get_authorized_token(token, signature_method=signature_method):
	req = oauth.OAuthRequest.from_consumer_and_token(
		consumer(), token=token,
		http_url='https://twitter.com/oauth/access_token'
	)
	req.sign_request(signature_method, consumer(), token)
	return oauth.OAuthToken.from_string(oauth_response(req))

def api(url, token, http_method='GET', **kwargs):
	try:
		return json.loads(oauth_response(oauth_request(
			url, token, http_method=http_method, parameters=kwargs
		)))
	except: pass
	return None

def is_authorized(token):
	return api('https://twitter.com/account/verify_credentials.json',
		token)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.core.urlresolvers import reverse
from oauth import oauth
from utils import *
from models import User
from decorators import wants_user, needs_user

@needs_user('auth_login')
def info(req):
	if 'POST' == req.method:
		req.user.email = req.POST['email']
		errors = req.user.validate()
		if not errors: req.user.save()
		return render_to_response('info.html', {
			'user': req.user,
			'errors': errors
		})
	return render_to_response('info.html', {'user': req.user})

@wants_user
def login(req):
	if req.user: return HttpResponseRedirect('auth_info')
	token = get_unauthorized_token()
	req.session['token'] = token.to_string()
	return HttpResponseRedirect(get_authorization_url(token))

def callback(req):
	token = req.session.get('token', None)
	if not token:
		return render_to_response('callback.html', {
			'token': True
		})
	token = oauth.OAuthToken.from_string(token)
	if token.key != req.GET.get('oauth_token', 'no-token'):
		return render_to_response('callback.html', {
			'mismatch': True
		})
	token = get_authorized_token(token)

	# Actually login
	obj = is_authorized(token)
	if obj is None:
		return render_to_response('callback.html', {
			'username': True
		})
	try: user = User.objects.get(username=obj['screen_name'])
	except: user = User(username=obj['screen_name'])
	user.oauth_token = token.key
	user.oauth_token_secret = token.secret
	user.save()
	req.session['user_id'] = user.id
	del req.session['token']

	return HttpResponseRedirect(reverse('auth_info'))

@wants_user
def logout(req):
	if req.user is not None:
		req.user.oauth_token = ''
		req.user.oauth_token_secret = ''
		req.user.save()
	req.session.flush()
	return render_to_response('logout.html', {})
########NEW FILE########
