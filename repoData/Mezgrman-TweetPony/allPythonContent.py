__FILENAME__ = simple_tweet
#!/usr/bin/env python
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

"""
This script asks for something to tweet.
"""

from _common import get_api
import tweetpony

def main():
	api = get_api()
	if not api:
		return
	tweet = raw_input("Hello, %s! Compose a tweet: " % api.user.screen_name)
	try:
		status = api.update_status(status = tweet)
	except tweetpony.APIError as err:
		print "Oh no! Your tweet could not be sent. Twitter returned error #%i and said: %s" % (err.code, err.description)
	else:
		print "Yay! Your tweet has been sent! View it here: https://twitter.com/%s/status/%s" % (status.user.screen_name, status.id_str)

if __name__ == "__main__":
	main()
########NEW FILE########
__FILENAME__ = stream
#!/usr/bin/env python
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

"""
This script starts a user stream and displays new tweets.
"""

from _common import get_api
import tweetpony

class StreamProcessor(tweetpony.StreamProcessor):
	def on_status(self, status):
		print "%s: %s" % (status.user.screen_name, status.text)
		return True

def main():
	api = get_api()
	if not api:
		return
	processor = StreamProcessor(api)
	try:
		api.user_stream(processor = processor)
	except KeyboardInterrupt:
		pass

if __name__ == "__main__":
	main()
########NEW FILE########
__FILENAME__ = trends
#!/usr/bin/env python
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

"""
This script fetches the current trending topics locations and displays the trends for the location the user selected.
"""

from _common import get_api
import tweetpony

def main():
	api = get_api()
	if not api:
		return
	try:
		locations = api.trend_locations()
	except tweetpony.APIError as err:
		print "Could not fetch the trend locations. Twitter returned error #%i and said: %s" % (err.code, err.description)
		return
	for location in locations:
		if location.placeType.code in [12, 19]: # Country (12) or Worldwide (19)
			print "%(woeid)i %(name)s" % location
		else: # Town (7) or other place type
			print "%(woeid)i %(name)s, %(country)s" % location
	selected_id = raw_input("Enter the number of the region you want to see the trends for: ")
	try:
		selected_trends = api.trends(id = selected_id)
	except tweetpony.APIError as err:
		print "Could not fetch the trends. Twitter returned error #%i and said: %s" % (err.code, err.description)
	else:
		print "\nHere are the trends!"
		print "=" * 25
		for trend in selected_trends:
			print trend.name

if __name__ == "__main__":
	main()
########NEW FILE########
__FILENAME__ = user_details
#!/usr/bin/env python
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

"""
This script asks for a username and displays that user's profile data.
"""

from _common import get_api
import tweetpony

def main():
	api = get_api()
	if not api:
		return
	username = raw_input("Username to lookup (leave blank for your own): ").strip()
	if username == "":
		username = api.user.screen_name
	try:
		user = api.get_user(screen_name = username)
	except tweetpony.APIError as err:
		print "Oh no! The user's profile could not be loaded. Twitter returned error #%i and said: %s" % (err.code, err.description)
	else:
		for key, value in user.iteritems():
			if key in ['entities', 'json', 'status']:
				continue
			line = "%s " % key.replace("_", " ").capitalize()
			line += "." * (50 - len(line)) + " "
			line += unicode(value)
			print line

if __name__ == "__main__":
	main()
########NEW FILE########
__FILENAME__ = _common
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

"""
This file contains functions used by more than one example script.
"""

import json
import os
import tweetpony

def authenticate():
	try:
		api = tweetpony.API(tweetpony.CONSUMER_KEY, tweetpony.CONSUMER_SECRET)
		url = api.get_auth_url()
		print "Visit this URL to obtain your verification code: %s" % url
		verifier = raw_input("Input your code: ")
		api.authenticate(verifier)
	except tweetpony.APIError as err:
		print "Oh no! You could not be authenticated. Twitter returned error #%i and said: %s" % (err.code, err.description)
	else:
		auth_data = {'access_token': api.access_token, 'access_token_secret': api.access_token_secret}
		with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".auth_data.json"), 'w') as f:
			f.write(json.dumps(auth_data))
		print "Hello, @%s! You have been authenticated. You can now run the other example scripts without having to authenticate every time." % api.user.screen_name

def get_api():
	if not os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".auth_data.json")):
		authenticate()
	with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".auth_data.json"), 'r') as f:
		auth_data = json.loads(f.read())
	try:
		api = tweetpony.API(tweetpony.CONSUMER_KEY, tweetpony.CONSUMER_SECRET, auth_data['access_token'], auth_data['access_token_secret'])
	except tweetpony.APIError as err:
		print "Oh no! You could not be authenticated. Twitter returned error #%i and said: %s" % (err.code, err.description)
	else:
		return api
	return False
########NEW FILE########
__FILENAME__ = api
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

import base64
import binascii
import hashlib
import hmac
import json
import random
try:
	import requests
except ImportError:
	raise ImportError("It seems like you don't have the 'requests' module installed which is required for TweetPony to work. Please install it first.")
import time
import urllib
import urlparse
from threading import Thread

from endpoints import *
from error import *
from models import *
from utils import quote

class ArgList(tuple):
	def __getitem__(self, index):
		if index > len(self) - 1:
			return None
		else:
			return tuple.__getitem__(self, index)

class KWArgDict(dict):
	def __getitem__(self, key):
		if key not in self.keys():
			return None
		else:
			return dict.__getitem__(self, key)

class API(object):
	def __init__(self, consumer_key, consumer_secret, access_token = None, access_token_secret = None, host = "api.twitter.com", root = "/1.1/", oauth_host = "api.twitter.com", oauth_root = "/oauth/", secure = True, timeout = None, load_user = True, json_in_models = False):
		self.consumer_key = consumer_key
		self.consumer_secret = consumer_secret
		self.access_token = access_token
		self.access_token_secret = access_token_secret
		self.host = host
		self.root = root
		self.oauth_host = oauth_host
		self.oauth_root = oauth_root
		self.secure = secure
		self.timeout = timeout
		self.load_user = load_user
		self._endpoint = None
		self._multipart = False
		self.json_in_models = json_in_models
		self.request_token = None
		self.request_token_secret = None
		self.user = self.verify_credentials() if self.load_user and self.access_token and self.access_token_secret else DummyUser()
	
	def __getattr__(self, attr):
		if attr.startswith("__"):
			return object.__getattr__(self, attr)
		self._endpoint = attr
		return self.api_call
	
	def set_access_token(self, access_token, access_token_secret):
		self.access_token = access_token
		self.access_token_secret = access_token_secret
		if self.load_user:
			self.verify()
	
	def verify(self):
		self.user = self.verify_credentials()
	
	def set_request_token(self, request_token, request_token_secret):
		self.request_token = request_token
		self.request_token_secret = request_token_secret
	
	def parse_qs(self, qs):
		return dict([(key, values[0]) for key, values in urlparse.parse_qs(qs).iteritems()])
	
	def oauth_generate_nonce(self):
		return base64.b64encode(hashlib.sha1(str(random.getrandbits(256))).digest(), random.choice(['rA','aZ','gQ','hH','hG','aR','DD'])).rstrip('==')
	
	def get_oauth_header_data(self, callback_url = None):
		auth_data = {
			'oauth_consumer_key': self.consumer_key,
			'oauth_nonce': self.oauth_generate_nonce(),
			'oauth_signature_method': "HMAC-SHA1",
			'oauth_timestamp': str(int(time.time())),
			'oauth_version': "1.0",
		}
		if callback_url:
			auth_data['oauth_callback'] = callback_url
		if self.access_token:
			auth_data['oauth_token'] = self.access_token
		elif self.request_token:
			auth_data['oauth_token'] = self.request_token
		return auth_data
	
	def generate_oauth_header(self, auth_data):
		return {'Authorization': "OAuth %s" % ", ".join(['%s="%s"' % item for item in auth_data.items()])}
	
	def get_oauth_header(self, method, url, callback_url = None, get = None, post = None):
		if not self._multipart:
			get_data = (get or {}).items()
			post_data = (post or {}).items()
		else:
			get_data = []
			post_data = []
		auth_data = self.get_oauth_header_data(callback_url = callback_url).items()
		data = [(quote(key, safe = "~"), quote(value, safe = "~")) for key, value in get_data + post_data + auth_data]
		data = sorted(sorted(data), key = lambda item: item[0].upper())
		param_string = []
		for key, value in data:
			param_string.append("%s=%s" % (key, value))
		param_string = "&".join(param_string)
		signature_base = []
		signature_base.append(method.upper())
		signature_base.append(quote(url, safe = "~"))
		signature_base.append(quote(param_string, safe = "~"))
		signature_base = "&".join(signature_base)
		if self.request_token:
			token_secret = quote(self.request_token_secret, safe = "~")
		elif self.access_token:
			token_secret = quote(self.access_token_secret, safe = "~")
		else:
			token_secret = ""
		signing_key = "&".join([quote(self.consumer_secret, safe = "~"), token_secret])
		signature = hmac.new(signing_key, signature_base, hashlib.sha1)
		signature = quote(binascii.b2a_base64(signature.digest())[:-1], safe = "~")
		auth_data.append(('oauth_signature', signature))
		return self.generate_oauth_header(dict(auth_data))
	
	def build_request_url(self, root, endpoint, get_data = None, host = None):
		host = host or self.host
		scheme = "https" if self.secure else "http"
		url = "%s://%s%s%s" % (scheme, host, root, endpoint)
		if get_data:
			qs = urllib.urlencode(get_data)
			url += "?%s" % qs
		return url
	
	def do_request(self, method, url, callback_url = None, get = None, post = None, files = None, stream = False, is_json = True):
		if files == {}:
			files = None
		self._multipart = files is not None
		header = self.get_oauth_header(method, url, callback_url, get, post)
		if get:
			full_url = url + "?" + urllib.urlencode(get)
		else:
			full_url = url
		"""# DEBUG
		info = "=" * 50 + "\n"
		info += "Method:    %s\n" % method
		info += "URL:       %s\n" % full_url
		info += "Headers:   %s\n" % str(header)
		info += "GET data:  %s\n" % str(get)
		info += "POST data: %s\n" % str(post)
		info += "Files:     %s\n" % str(files)
		info += "Streaming: %s\n" % str(stream)
		info += "JSON:      %s\n" % str(is_json)
		info += "=" * 50
		print info
		# END DEBUG"""
		try:
			if method.upper() == "POST":
				response = requests.post(full_url, data = post, files = files, headers = header, stream = stream, timeout = self.timeout)
			else:
				response = requests.get(full_url, data = post, files = files, headers = header, stream = stream, timeout = self.timeout)
		except Exception as exc:
			raise APIError(code = -1, description = unicode(exc))
		"""# DEBUG
		print ("\nResponse:  %s\n" % response.text) + "=" * 50
		# END DEBUG"""
		if response.status_code != 200:
			try:
				data = response.json()
				try:
					raise APIError(code = data['errors'][0]['code'], description = data['errors'][0]['message'], body = response.text or None)
				except TypeError:
					raise APIError(code = -1, description = data['errors'])
			except APIError:
				raise
			except:
				description = " ".join(response.headers['status'].split()[1:]) if response.headers.get('status', None) else "Unknown Error"
				raise APIError(code = response.status_code, description = description, body = response.text or None)
		if stream:
			return response
		if is_json:
			try:
				return response.json()
			except:
				return response.text
		else:
			return response.text
	
	def get_request_token(self, callback_url = None):
		url = self.build_request_url(self.oauth_root, 'request_token')
		resp = self.do_request("POST", url, callback_url, is_json = False)
		token_data = self.parse_qs(resp)
		self.set_request_token(token_data['oauth_token'], token_data['oauth_token_secret'])
		return (self.request_token, self.request_token_secret, token_data.get('oauth_callback_confirmed'))
	
	def get_auth_url(self, callback_url = None, force_login = False, screen_name = None, token = None):
		self.set_request_token(None, None)
		if token is None:
			token, secret, callback_confirmed = self.get_request_token(callback_url)
		if callback_url and not callback_confirmed:
			raise APIError(code = -1, description = "OAuth callback not confirmed")
		data = {'oauth_token': token}
		if force_login:
			data['force_login'] = 'true'
		if screen_name:
			data['screen_name'] = screen_name
		return self.build_request_url(self.oauth_root, 'authenticate', data)
	
	def authenticate(self, verifier):
		url = self.build_request_url(self.oauth_root, 'access_token')
		resp = self.do_request("POST", url, post = {'oauth_verifier': verifier}, is_json = False)
		token_data = self.parse_qs(resp)
		self.set_request_token(None, None)
		self.set_access_token(token_data['oauth_token'], token_data['oauth_token_secret'])
		return ((self.access_token, self.access_token_secret), token_data['user_id'], token_data['screen_name'])
	
	def parse_param(self, key, value):
		if type(value) == bool:
			value = "true" if value else "false"
		elif type(value) == list:
			value = ",".join([str(val) for val in value])
		elif type(value) not in [str, unicode] and value is not None:
			value = unicode(value)
		return (key, value)
	
	def parse_params(self, params):
		files = {}
		_params = dict(params.items())
		for key, value in params.iteritems():
			if value in [None, []]:
				del _params[key]
			if key in ['image', 'media', 'banner']:
				if type(value) is file:
					try:
						value.seek(0)
					except ValueError:
						pass
				elif type(value) in [str, unicode]:
					value = open(value, 'rb')
				del _params[key]
				if key == 'media':
					key = 'media[]'
				files[key] = value
		params = _params
		parsed_params = dict([self.parse_param(key, value) for key, value in params.iteritems()])
		return (parsed_params, files)
	
	def parse_stream_entity(self, entity):
		try:
			data = json.loads(entity)
		except ValueError:
			return None
		keys = data.keys()
		if 'delete' in keys:
			instance = DeletionEvent.from_json(data['delete'])
		elif 'scrub_geo' in keys:
			instance = LocationDeletionEvent.from_json(data['scrub_geo'])
		elif 'limit' in keys:
			instance = LimitEvent.from_json(data['limit'])
		elif 'status_withheld' in keys:
			instance = WithheldStatusEvent.from_json(data['status_withheld'])
		elif 'user_withheld' in keys:
			instance = WithheldUserEvent.from_json(data['user_withheld'])
		elif 'disconnect' in keys:
			instance = DisconnectEvent.from_json(data['disconnect'])
		elif 'friends' in keys:
			instance = IDCollection.from_json(data['friends'])
		elif 'target' in keys:
			instance = Event.from_json(data)
		elif 'direct_message' in keys:
			instance = Message.from_json(data['direct_message'])
		else:
			instance = Status.from_json(data)
		return instance
	
	def api_call(self, *args, **kwargs):
		if self._endpoint not in ENDPOINTS and self._endpoint not in STREAM_ENDPOINTS:
			raise NotImplementedError("API endpoint for method '%s' not found." % self._endpoint)
		
		stream = self._endpoint in STREAM_ENDPOINTS
		if stream:
			endpoints = STREAM_ENDPOINTS
			processor = kwargs.get('processor', StreamProcessor(self))
			if 'processor' in kwargs.keys():
				del kwargs['processor']
		else:
			endpoints = ENDPOINTS
		
		args = ArgList(args)
		kwargs, files = self.parse_params(kwargs)
		kwargs = KWArgDict(kwargs)
		data = endpoints[self._endpoint]
		
		missing_params = []
		url_params = []
		for param in data['url_params']:
			p = kwargs.get(param)
			if p is None:
				missing_params.append(param)
			else:
				url_params.append(p)
				del kwargs[param]
		if missing_params:
			raise ParameterError("Missing URL parameters: %s" % ", ".join(missing_params))
		
		missing_params = []
		for param in data['required_params']:
			p = files.get(param) or kwargs.get(param)
			if p is None:
				missing_params.append(param)
		if missing_params:
			raise ParameterError("Missing required parameters: %s" % ", ".join(missing_params))
		
		unsupported_params = []
		for param in kwargs.keys():
			if param not in data['url_params'] + data['required_params'] + data['optional_params']:
				unsupported_params.append(param)
		for param in files.keys():
			if param not in data['url_params'] + data['required_params'] + data['optional_params']:
				unsupported_params.append(param)
		if unsupported_params:
			raise ParameterError("Unsupported parameters specified: %s" % ", ".join(unsupported_params))
		
		if data['url_params'] != []:
			endpoint = data['endpoint'] % tuple(url_params)
		else:
			endpoint = data['endpoint']
		
		if data['post']:
			get_data = None
			post_data = kwargs
		else:
			get_data = kwargs
			post_data = None
		
		if 'host' in data:
			url = self.build_request_url(self.root, endpoint, host = data['host'])
		else:
			url = self.build_request_url(self.root, endpoint)
		
		resp = self.do_request("POST" if data['post'] else "GET", url, get = get_data, post = post_data, files = files, stream = stream)
		if stream:
			for line in resp.iter_lines(chunk_size = 1):
				if not line:
					continue
				entity = self.parse_stream_entity(line)
				entity.connect_api(self)
				if processor.process_entity(entity) == False:
					break
		else:
			if data['model'] is None:
				return resp
			else:
				model = data['model'].from_json(resp)
				model.connect_api(self)
				return model

class StreamProcessor:
	def __init__(self, api):
		self.api = api
	
	def process_entity(self, entity):
		t = type(entity)
		if t == Status:
			return self.on_status(entity)
		elif t == Message:
			return self.on_message(entity)
		elif t == Event:
			return self.on_event(entity)
		elif t == DeletionEvent:
			return self.on_delete(entity)
		elif t == LocationDeletionEvent:
			return self.on_geo_delete(entity)
		elif t == LimitEvent:
			return self.on_limit(entity)
		elif t == WithheldStatusEvent:
			return self.on_withheld_status(entity)
		elif t == WithheldUserEvent:
			return self.on_withheld_user(entity)
		elif t == DisconnectEvent:
			return self.on_disconnect(entity)
		elif t == IDCollection:
			return self.on_friends(entity)
		else:
			return self.on_unknown_entity(entity)
		return True
	
	def on_status(self, status):
		return True
	
	def on_message(self, message):
		return True
	
	def on_event(self, event):
		return True
	
	def on_delete(self, event):
		return True
	
	def on_geo_delete(self, event):
		return True
	
	def on_limit(self, event):
		return True
	
	def on_withheld_status(self, event):
		return True
	
	def on_withheld_user(self, event):
		return True
	
	def on_disconnect(self, event):
		return True
	
	def on_friends(self, friends):
		return True
	
	def on_unknown_entity(self, entity):
		return True

class BufferedStreamProcessor(StreamProcessor):
	def __init__(self, api, max_items = 25):
		StreamProcessor.__init__(self, api)
		self.buffer = []
		self.max_items = max_items
		self.source_running = True
		self.buffer_running = True
		self.buffer_processor = Thread(target = self.process_buffer)
		self.buffer_processor.start()
	
	def process_entity(self, entity):
		if not self.source_running:
			while self.buffer_running:
				time.sleep(0.1)
			return False
		if not self.max_items or (self.max_items and len(self.buffer) < self.max_items):
			self.buffer.append(entity)
		elif self.max_items and len(self.buffer) >= self.max_items:
			self.source_running = False
		return True
	
	def process_buffer(self):
		while self.buffer_running:
			if not self.buffer:
				if self.source_running:
					time.sleep(0.1)
				else:
					self.buffer_running = False
				continue
			entity = self.buffer.pop(0)
			result = StreamProcessor.process_entity(self, entity)
			if not result:
				self.source_running = False
			time.sleep(1)

if __name__ == '__main__':
	print "Rainbow Dash ist best pony! :3"

########NEW FILE########
__FILENAME__ = endpoints
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

from models import *

ENDPOINTS = {
	'mentions': {
		'endpoint': "statuses/mentions_timeline.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['count', 'since_id', 'max_id', 'trim_user', 'contributor_details', 'include_entities'],
		'model': StatusCollection,
	},
	'user_timeline': {
		'endpoint': "statuses/user_timeline.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'since_id', 'count', 'max_id', 'trim_user', 'exclude_replies', 'contributor_details', 'include_rts'],
		'model': StatusCollection,
	},
	'home_timeline': {
		'endpoint': "statuses/home_timeline.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['count', 'since_id', 'max_id', 'trim_user', 'exclude_replies', 'contributor_details', 'include_entities'],
		'model': StatusCollection,
	},
	'retweets_of_me': {
		'endpoint': "statuses/retweets_of_me.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['count', 'since_id', 'max_id', 'trim_user', 'include_entities', 'include_user_entities'],
		'model': StatusCollection,
	},
	'retweets': {
		'endpoint': "statuses/retweets/%s.json",
		'post': False,
		'url_params': ['id'],
		'required_params': [],
		'optional_params': ['count', 'trim_user'],
		'model': StatusCollection,
	},
	'get_status': {
		'endpoint': "statuses/show/%s.json",
		'post': False,
		'url_params': ['id'],
		'required_params': [],
		'optional_params': ['trim_user', 'include_my_retweet', 'include_entities'],
		'model': Status,
	},
	'delete_status': {
		'endpoint': "statuses/destroy/%s.json",
		'post': True,
		'url_params': ['id'],
		'required_params': [],
		'optional_params': ['trim_user'],
		'model': Status,
	},
	'update_status': {
		'endpoint': "statuses/update.json",
		'post': True,
		'url_params': [],
		'required_params': ['status'],
		'optional_params': ['in_reply_to_status_id', 'lat', 'long', 'place_id', 'display_coordinates', 'trim_user'],
		'model': Status,
	},
	'retweet': {
		'endpoint': "statuses/retweet/%s.json",
		'post': True,
		'url_params': ['id'],
		'required_params': [],
		'optional_params': ['trim_user'],
		'model': Status,
	},
	'update_status_with_media': {
		'endpoint': "statuses/update_with_media.json",
		'post': True,
		'url_params': [],
		'required_params': ['status', 'media[]'],
		'optional_params': ['possibly_sensitive', 'in_reply_to_status_id', 'lat', 'long', 'place_id', 'display_coordinates'],
		'model': Status,
	},
	'oembed': {
		'endpoint': "statuses/oembed.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['id', 'url', 'maxwidth', 'hide_media', 'hide_thread', 'omit_script', 'align', 'related', 'lang'],
		'model': OEmbed,
	},
	'search_tweets': {
		'endpoint': "search/tweets.json",
		'post': False,
		'url_params': [],
		'required_params': ['q'],
		'optional_params': ['geocode', 'lang', 'locale', 'result_type', 'count', 'until', 'since_id', 'max_id', 'include_entities'],
		'model': SearchResult,
	},
	'received_messages': {
		'endpoint': "direct_messages.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['since_id', 'max_id', 'count', 'page', 'include_entities', 'skip_status'],
		'model': MessageCollection,
	},
	'sent_messages': {
		'endpoint': "direct_messages/sent.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['since_id', 'max_id', 'count', 'page', 'include_entities'],
		'model': MessageCollection,
	},
	'get_message': {
		'endpoint': "direct_messages/show.json",
		'post': False,
		'url_params': [],
		'required_params': ['id'],
		'optional_params': [],
		'model': Message,
	},
	'delete_message': {
		'endpoint': "direct_messages/destroy.json",
		'post': True,
		'url_params': [],
		'required_params': ['id'],
		'optional_params': ['include_entities'],
		'model': Message,
	},
	'send_message': {
		'endpoint': "direct_messages/new.json",
		'post': True,
		'url_params': [],
		'required_params': ['text'],
		'optional_params': ['user_id', 'screen_name'],
		'model': Message,
	},
	'no_retweets_ids': {
		'endpoint': "friendships/no_retweets/ids.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['stringify_ids'],
		'model': None,
	},
	'friends_ids': {
		'endpoint': "friends/ids.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'cursor', 'stringify_ids'],
		'model': CursoredIDCollection,
	},
	'followers_ids': {
		'endpoint': "followers/ids.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'cursor', 'stringify_ids'],
		'model': CursoredIDCollection,
	},
	'get_friendships': {
		'endpoint': "friendships/lookup.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id'],
		'model': SimpleRelationshipCollection,
	},
	'received_follower_requests': {
		'endpoint': "friendships/incoming.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['cursor', 'stringify_ids'],
		'model': CursoredIDCollection,
	},
	'sent_follower_requests': {
		'endpoint': "friendships/outgoing.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['cursor', 'stringify_ids'],
		'model': CursoredIDCollection,
	},
	'follow': {
		'endpoint': "friendships/create.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id', 'follow'],
		'model': User,
	},
	'unfollow': {
		'endpoint': "friendships/destroy.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id'],
		'model': User,
	},
	'update_friendship': {
		'endpoint': "friendships/update.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id', 'device', 'retweets'],
		'model': Relationship,
	},
	'get_friendship': {
		'endpoint': "friendships/show.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['source_id', 'source_screen_name', 'target_id', 'target_screen_name'],
		'model': Relationship,
	},
	'friends': {
		'endpoint': "friends/list.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'cursor', 'skip_status', 'include_user_entities'],
		'model': CursoredUserCollection,
	},
	'followers': {
		'endpoint': "followers/list.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'cursor', 'skip_status', 'include_user_entities'],
		'model': CursoredUserCollection,
	},
	'get_settings': {
		'endpoint': "account/settings.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': Settings,
	},
	'verify_credentials': {
		'endpoint': "account/verify_credentials.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['include_entities', 'skip_status'],
		'model': User,
	},
	'update_settings': {
		'endpoint': "account/settings.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['trend_location_woeid', 'sleep_time_enabled', 'start_sleep_time', 'end_sleep_time', 'time_zone', 'lang'],
		'model': Settings,
	},
	'update_delivery_device': {
		'endpoint': "account/update_delivery_device.json",
		'post': True,
		'url_params': [],
		'required_params': ['device'],
		'optional_params': ['include_entities'],
		'model': None,
	},
	'update_profile': {
		'endpoint': "account/update_profile.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['name', 'url', 'location', 'description', 'include_entities', 'skip_status'],
		'model': User,
	},
	'update_background': {
		'endpoint': "account/update_profile_background_image.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['image', 'tile', 'include_entities', 'skip_status', 'use'],
		'model': User,
	},
	'update_colors': {
		'endpoint': "account/update_profile_colors.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['profile_background_color', 'profile_link_color', 'profile_sidebar_border_color', 'profile_sidebar_fill_color', 'profile_text_color', 'include_entities', 'skip_status'],
		'model': User,
	},
	'update_profile_image': {
		'endpoint': "account/update_profile_image.json",
		'post': True,
		'url_params': [],
		'required_params': ['image'],
		'optional_params': ['include_entities', 'skip_status'],
		'model': User,
	},
	'blocks': {
		'endpoint': "blocks/list.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['include_entities', 'skip_status', 'cursor'],
		'model': CursoredUserCollection,
	},
	'blocks_ids': {
		'endpoint': "blocks/ids.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['stringify_ids', 'cursor'],
		'model': CursoredIDCollection,
	},
	'block': {
		'endpoint': "blocks/create.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id', 'include_entities', 'skip_status'],
		'model': User,
	},
	'unblock': {
		'endpoint': "blocks/destroy.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id', 'include_entities', 'skip_status'],
		'model': User,
	},
	'get_users': {
		'endpoint': "users/lookup.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id', 'include_entities'],
		'model': UserCollection,
	},
	'get_user': {
		'endpoint': "users/show.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'include_entities'],
		'model': User,
	},
	'search_users': {
		'endpoint': "users/search.json",
		'post': False,
		'url_params': [],
		'required_params': ['q'],
		'optional_params': ['page', 'count', 'include_entities'],
		'model': UserCollection,
	},
	'get_contributees': {
		'endpoint': "users/contributees.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'include_entities', 'skip_status'],
		'model': UserCollection,
	},
	'get_contributors': {
		'endpoint': "users/contributors.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'include_entities', 'skip_status'],
		'model': UserCollection,
	},
	'remove_profile_banner': {
		'endpoint': "account/remove_profile_banner.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': None,
	},
	'update_profile_banner': {
		'endpoint': "account/update_profile_banner.json",
		'post': True,
		'url_params': [],
		'required_params': ['banner'],
		'optional_params': ['width', 'height', 'offset_left', 'offset_top'],
		'model': None,
	},
	'get_profile_banner': {
		'endpoint': "users/profile_banner.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name'],
		'model': Sizes,
	},
	'get_suggestion_category': {
		'endpoint': "users/suggestions/%s.json",
		'post': False,
		'url_params': ['slug'],
		'required_params': [],
		'optional_params': ['lang'],
		'model': Category,
	},
	'get_suggestion_categories': {
		'endpoint': "users/suggestions.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['lang'],
		'model': CategoryCollection,
	},
	'suggested_users': {
		'endpoint': "users/suggestions/%s/members.json",
		'post': False,
		'url_params': ['slug'],
		'required_params': [],
		'optional_params': [],
		'model': UserCollection,
	},
	'favorites': {
		'endpoint': "favorites/list.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'count', 'since_id', 'max_id', 'include_entities'],
		'model': StatusCollection,
	},
	'unfavorite': {
		'endpoint': "favorites/destroy.json",
		'post': True,
		'url_params': [],
		'required_params': ['id'],
		'optional_params': ['include_entities'],
		'model': Status,
	},
	'favorite': {
		'endpoint': "favorites/create.json",
		'post': True,
		'url_params': [],
		'required_params': ['id'],
		'optional_params': ['include_entities'],
		'model': Status,
	},
	'lists': {
		'endpoint': "lists/list.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name'],
		'model': ListCollection,
	},
	'list_timeline': {
		'endpoint': "lists/statuses.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'owner_screen_name', 'owner_id', 'since_id', 'max_id', 'count', 'include_entities', 'include_rts'],
		'model': StatusCollection,
	},
	'remove_from_list': {
		'endpoint': "lists/members/destroy.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'user_id', 'screen_name', 'owner_screen_name', 'owner_id'],
		'model': List,
	},
	'list_memberships': {
		'endpoint': "lists/memberships.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'cursor', 'filter_to_owned_lists'],
		'model': CursoredListCollection,
	},
	'list_subscribers': {
		'endpoint': "lists/subscribers.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'owner_screen_name', 'owner_id', 'cursor', 'include_entities', 'skip_status'],
		'model': CursoredUserCollection,
	},
	'follow_list': {
		'endpoint': "lists/subscribers/create.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['owner_screen_name', 'owner_id', 'list_id', 'slug'],
		'model': List,
	},
	'user_follows_list': {
		'endpoint': "lists/subscribers/show.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['owner_screen_name', 'owner_id', 'list_id', 'slug', 'user_id', 'screen_name', 'include_entities', 'skip_status'],
		'model': User,
	},
	'unfollow_list': {
		'endpoint': "lists/subscribers/destroy.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['owner_screen_name', 'owner_id', 'list_id', 'slug'],
		'model': List,
	},
	'batch_add_to_list': {
		'endpoint': "lists/memberships/create_all.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'user_id', 'screen_name', 'owner_screen_name', 'owner_id'],
		'model': None,
	},
	'user_in_list': {
		'endpoint': "list/members/show.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'user_id', 'screen_name', 'owner_screen_name', 'owner_id', 'include_entities'],
		'model': User,
	},
	'list_members': {
		'endpoint': "lists/members.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'owner_screen_name', 'owner_id', 'cursor', 'include_entities', 'skip_status'],
		'model': CursoredUserCollection,
	},
	'add_to_list': {
		'endpoint': "lists/members/create.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'user_id', 'screen_name', 'owner_screen_name', 'owner_id'],
		'model': List,
	},
	'delete_list': {
		'endpoint': "lists/destroy.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['owner_screen_name', 'owner_id', 'list_id', 'slug'],
		'model': List,
	},
	'update_list': {
		'endpoint': "lists/update.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'name', 'mode', 'description', 'owner_screen_name', 'owner_id'],
		'model': List,
	},
	'create_list': {
		'endpoint': "lists/create.json",
		'post': True,
		'url_params': [],
		'required_params': ['name'],
		'optional_params': ['mode', 'description'],
		'model': List,
	},
	'get_list': {
		'endpoint': "lists/show.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'owner_screen_name', 'owner_id'],
		'model': List,
	},
	'subscribed_lists': {
		'endpoint': "lists/subscriptions.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['user_id', 'screen_name', 'count', 'cursor'],
		'model': CursoredListCollection,
	},
	'batch_remove_from_list': {
		'endpoint': "lists/memberships/destroy_all.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['list_id', 'slug', 'user_id', 'screen_name', 'owner_screen_name', 'owner_id'],
		'model': None,
	},
	'saved_searches': {
		'endpoint': "saved_searches/list.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': SavedSearchCollection,
	},
	'get_saved_search': {
		'endpoint': "saved_searches/show/%s.json",
		'post': False,
		'url_params': ['id'],
		'required_params': [],
		'optional_params': [],
		'model': SavedSearch,
	},
	'create_saved_search': {
		'endpoint': "saved_searches/create.json",
		'post': True,
		'url_params': [],
		'required_params': ['query'],
		'optional_params': [],
		'model': SavedSearch,
	},
	'delete_saved_search': {
		'endpoint': "saved_searches/destroy/%s.json",
		'post': True,
		'url_params': ['id'],
		'required_params': [],
		'optional_params': [],
		'model': SavedSearch,
	},
	'get_place': {
		'endpoint': "geo/id/%s.json",
		'post': False,
		'url_params': ['place_id'],
		'required_params': [],
		'optional_params': [],
		'model': Place,
	},
	'reverse_geocode': {
		'endpoint': "geo/reverse_geocode.json",
		'post': False,
		'url_params': [],
		'required_params': ['lat', 'long'],
		'optional_params': ['accuracy', 'granularity', 'max_results'],
		'model': PlaceSearchResult,
	},
	'search_places': {
		'endpoint': "geo/search.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['lat', 'long', 'query', 'ip', 'granularity', 'accuracy', 'max_results', 'contained_within'],
		'model': PlaceSearchResult,
	},
	'similar_places': {
		'endpoint': "geo/similar_places.json",
		'post': False,
		'url_params': [],
		'required_params': ['lat', 'long', 'name'],
		'optional_params': ['contained_within'],
		'model': PlaceSearchResult,
	},
	'create_place': {
		'endpoint': "geo/place.json",
		'post': True,
		'url_params': [],
		'required_params': ['name', 'contained_within', 'token', 'lat', 'long'],
		'optional_params': [],
		'model': Place,
	},
	'trends': {
		'endpoint': "trends/place.json",
		'post': False,
		'url_params': [],
		'required_params': ['id'],
		'optional_params': ['exclude'],
		'model': Trends,
	},
	'trend_locations': {
		'endpoint': "trends/available.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': TrendLocationCollection,
	},
	'closest_trend_locations': {
		'endpoint': "trends/closest.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['lat', 'long'],
		'model': TrendLocationCollection,
	},
	'report_spam': {
		'endpoint': "users/report_spam.json",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['screen_name', 'user_id'],
		'model': User,
	},
	'configuration': {
		'endpoint': "help/configuration.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': APIConfiguration,
	},
	'languages': {
		'endpoint': "help/languages.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': LanguageCollection,
	},
	'privacy_policy': {
		'endpoint': "help/privacy.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': PrivacyPolicy,
	},
	'terms_of_service': {
		'endpoint': "help/tos.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': [],
		'model': TermsOfService,
	},
	'rate_limit_status': {
		'endpoint': "application/rate_limit_status.json",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['resources'],
		'model': RateLimitStatus,
	},
}

STREAM_ENDPOINTS = {
	'filter_stream': {
		'endpoint': "statuses/filter.json",
		'host': "stream.twitter.com",
		'post': True,
		'url_params': [],
		'required_params': [],
		'optional_params': ['follow', 'track', 'locations', 'stall_warnings', 'language', 'filter_level'],
	},
	'sample_stream': {
		'endpoint': "statuses/sample.json",
		'host': "stream.twitter.com",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['stall_warnings', 'language', 'filter_level'],
	},
	'firehose_stream': {
		'endpoint': "statuses/firehose.json",
		'host': "stream.twitter.com",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['count', 'stall_warnings', 'language', 'filter_level'],
	},
	'user_stream': {
		'endpoint': "user.json",
		'host': "userstream.twitter.com",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['stall_warnings', 'with', 'replies', 'track', 'locations', 'language'],
	},
	'site_stream': {
		'endpoint': "site.json",
		'host': "sitestream.twitter.com",
		'post': False,
		'url_params': [],
		'required_params': [],
		'optional_params': ['follow', 'stall_warnings', 'with', 'replies'],
	},
}

########NEW FILE########
__FILENAME__ = error
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

class APIError(Exception):
	def __init__(self, code, description, body = None):
		self.code = code
		self.description = description
		self.body = body
	
	def __str__(self):
		return "#%i: %s" % (self.code, self.description)

class ParameterError(Exception):
	def __init__(self, description):
		self.description = description
	
	def __str__(self):
		return self.description
########NEW FILE########
__FILENAME__ = metadata
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

name = "TweetPony"
version = "1.2.13"
description = "A Twitter library for Python"
license = "AGPLv3"
author = "Julian Metzler"
author_email = "contact@mezgrman.de"
requires = ['requests']
url = "https://github.com/Mezgrman/TweetPony"
keywords = "twitter library api wrapper pony"

########NEW FILE########
__FILENAME__ = models
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

import json
import locale
import utils
from datetime import datetime
from error import ParameterError

def strptime(string, fmt = '%a %b %d %H:%M:%S +0000 %Y'):
	locale.setlocale(locale.LC_TIME, 'C')
	value = datetime.strptime(string, fmt)
	locale.setlocale(locale.LC_TIME, '')
	return value

class DummyAPI:
	def __getattr__(self, name):
		raise NotImplementedError("This model does not have an API instance associated with it.")

class DummyUser:
	def __getattr__(self, name):
		raise NotImplementedError("This API instance does not have verified credentials and thus did not load the authenticating user's profile.")

class AttrDict(dict):
	def __init__(self, data = None):
		if data is not None:
			for key, value in data.iteritems():
				if type(value) == dict:
					value = AttrDict(value)
				elif type(value) == list:
					for i in range(len(value)):
						if type(value[i]) == dict:
							value[i] = AttrDict(value[i])
						elif type(value[i]) == list:
							for n in range(len(value[i])):
								if type(value[i][n]) == dict:
									value[i][n] = AttrDict(value[i][n])
				self[key] = value
	
	def __getattr__(self, name):
		try:
			return self.__getitem__(name)
		except KeyError:
			raise AttributeError

class Model(AttrDict):
	api = DummyAPI()
	
	def __getattr__(self, name):
		try:
			return self.__getitem__(name)
		except:
			return AttrDict.__getattr__(self, name)
	
	@classmethod
	def from_json(cls, data):
		self = cls(data)
		self['json'] = json.dumps(data)
		return self
	
	def connect_api(self, api):
		self.api = api
		if not api.json_in_models:
			del self['json']

class ModelCollection(list):
	model = Model
	
	@classmethod
	def from_json(cls, data):
		self = cls()
		for item in data:
			self.append(self.model.from_json(item))
		return self
	
	def connect_api(self, api):
		for item in self:
			if hasattr(item, 'connect_api'):
				item.connect_api(api)
	
	def __iter__(self):
		self._iterator = list.__iter__(self)
		return self._iterator
	
	def next(self):
		return self._iterator.next()

class MixedModelCollection(Model):
	model_key = 'models'
	collection = ModelCollection
	
	@classmethod
	def from_json(cls, data):
		if type(data) is list and len(data) == 1:
			data = data[0]
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == self.model_key:
				value = self.collection.from_json(value)
			self[key] = value
		return self
	
	def connect_api(self, api):
		for item in self.get(self.model_key, []):
			if hasattr(item, 'connect_api'):
				item.connect_api(api)

	def __len__(self):
		return len(self.get(self.model_key, []))

	def __getitem__(self, descriptor):
		if type(descriptor) in [str, unicode]:
			return Model.__getitem__(self, descriptor)
		else:
			return self.get(self.model_key, []).__getitem__(descriptor)
	
	def __iter__(self):
		return self.get(self.model_key, []).__iter__()
	
	def next(self):
		return self.get(self.model_key, []).next()

class CursoredModelCollection(MixedModelCollection):
	pass

########################################################

class Status(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		tmp = cls()
		for key, value in self.iteritems():
			if key == 'created_at':
				value = strptime(value)
			elif key == 'user':
				value = User.from_json(value)
			elif key == 'retweeted_status':
				value = Status.from_json(value)
			elif key == 'source':
				try:
					tmp[u'source_url'] = value.split('"')[1]
					value = value.split(">")[1].split("<")[0]
				except IndexError:
					tmp[u'source_url'] = None
			tmp[key] = value
		self = tmp
		return self
	
	def clean_text(self):
		return self.text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
	
	def favorite(self):
		return self.api.favorite(id = self.id)
	
	def unfavorite(self):
		return self.api.unfavorite(id = self.id)
	
	def retweet(self):
		return self.api.retweet(id = self.id)
	
	def delete(self):
		return self.api.delete_status(id = self.id)
	
	def reply(self, text, reply_all = False, **kwargs):
		if reply_all:
			text = utils.optimize_mentions([self.user.screen_name] + [entity.screen_name for entity in self.entities.user_mentions], text)
		else:
			text = utils.optimize_mentions([self.user.screen_name], text)
		return self.api.update_status(status = text, in_reply_to_status_id = self.id, **kwargs)
	
	def retweets(self, **kwargs):
		return self.api.retweets(id = self.id, **kwargs)

class User(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == 'created_at':
				value = strptime(value)
			elif key == 'status':
				value = Status.from_json(value)
			self[key] = value
		return self
	
	def follow(self, **kwargs):
		return self.api.follow(user_id = self.id, **kwargs)
	
	def unfollow(self):
		return self.api.unfollow(user_id = self.id)
	
	def mention(self, text, **kwargs):
		text = utils.optimize_mentions([self.screen_name], text)
		return self.api.update_status(status = text, **kwargs)
	
	def add_to_list(self, list_id = None, slug = None, owner_screen_name = None, owner_id = None):
		if (list_id is None and slug is None) or (list_id is None and owner_screen_name is None and owner_id is None):
			raise ParameterError("You must specify either a list ID or a slug in combination with either the owner's screen name or their user ID.")
		return self.api.add_to_list(user_id = self.id, list_id = list_id, slug = slug, owner_screen_name = owner_screen_name, owner_id = owner_id)
	
	def remove_from_list(self, list_id = None, slug = None, owner_screen_name = None, owner_id = None):
		if (list_id is None and slug is None) or (list_id is None and owner_screen_name is None and owner_id is None):
			raise ParameterError("You must specify either a list ID or a slug in combination with either the owner's screen name or their user ID.")
		return self.api.remove_from_list(user_id = self.id, list_id = list_id, slug = slug, owner_screen_name = owner_screen_name, owner_id = owner_id)
	
	def block(self):
		return self.api.block(user_id = self.id)
	
	def unblock(self):
		return self.api.unblock(user_id = self.id)
	
	def report_spam(self):
		return self.api.report_spam(user_id = self.id)
	
	def send_message(self, text):
		return self.api.send_message(user_id = self.id, text = text)
	
	def friendship(self, target_id = None, target_screen_name = None):
		if target_id is None and target_screen_name is None:
			target_id = self.api.user.id
		return self.api.get_friendship(source_id = self.id, target_id = target_id, target_screen_name = target_screen_name)
	
	def followers(self, **kwargs):
		return self.api.followers(user_id = self.id, **kwargs)
	
	def friends(self, **kwargs):
		return self.api.friends(user_id = self.id, **kwargs)
	
	def followers_ids(self, **kwargs):
		return self.api.followers_ids(user_id = self.id, **kwargs)
	
	def friends_ids(self, **kwargs):
		return self.api.friends_ids(user_id = self.id, **kwargs)
	
	def lists(self):
		return self.api.lists(user_id = self.id)
	
	def list_memberships(self):
		return self.api.list_memberships(user_id = self.id)
	
	def favorites(self):
		return self.api.favorites(user_id = self.id)

class Message(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == 'created_at':
				value = strptime(value)
			elif key == 'sender' or key == 'recipient':
				value = User.from_json(value)
			self[key] = value
		return self
	
	def delete(self):
		return self.api.delete_message(id = self.id)
	
	def reply(self, text):
		return self.api.send_message(user_id = self.sender.id, text = text)

class OEmbed(Model):
	pass

class Relationship(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data['relationship']))
		self['following'] = self['source']['following']
		self['followed_by'] = self['source']['followed_by']
		return self

class SimpleRelationship(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		tmp = cls()
		for key, value in self.iteritems():
			if key == 'connections':
				tmp['followed_by'] = 'followed_by' in value
				tmp['following'] = 'following' in value
				tmp['following_requested'] = 'following_requested' in value
			tmp[key] = value
		self = tmp
		return self

class Settings(Model):
	pass

class Sizes(Model):
	pass

class List(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == 'created_at':
				value = strptime(value)
			elif key == 'user':
				value = User.from_json(value)
			self[key] = value
		return self
	
	def delete(self):
		return self.api.delete_list(list_id = self.id)
	
	def update(self, name = None, mode = None, description = None):
		return self.api.update_list(list_id = self.id, name = name, mode = mode, description = description)
	
	def add_user(self, user_id = None, screen_name = None):
		return self.api.add_to_list(list_id = self.id, user_id = user_id, screen_name = screen_name)
	
	def remove_user(self, user_id = None, screen_name = None):
		return self.api.remove_from_list(list_id = self.id, user_id = user_id, screen_name = screen_name)
	
	def add_users(self, user_id = None, screen_name = None):
		return self.api.batch_add_to_list(list_id = self.id, user_id = user_id, screen_name = screen_name)
	
	def remove_users(self, user_id = None, screen_name = None):
		return self.api.batch_remove_from_list(list_id = self.id, user_id = user_id, screen_name = screen_name)

class SavedSearch(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == 'created_at':
				value = strptime(value)
			self[key] = value
		return self
	
	def results(self, **kwargs):
		return self.api.search_tweets(q = self.query, **kwargs)
	
	def delete(self):
		return self.api.delete_saved_search(id = self.id)

class Place(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == 'contained_within':
				value = [Place.from_json(item) for item in value]
			self[key] = value
		return self
	
	def similar(self, lat, long, **kwargs):
		return self.api.similar_places(lat = lat, long = long, name = self.name, **kwargs)

class PlaceSearchResult(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == 'result':
				value['places'] = PlaceCollection.from_json(value['places'])
			self[key] = value
		return self

class Trend(Model):
	pass

class TrendLocation(Model):
	pass

class APIConfiguration(Model):
	pass

class Language(Model):
	pass

class RateLimitStatus(Model):
	pass

class Event(Model):
	@classmethod
	def from_json(cls, data):
		self = cls(Model.from_json(data))
		for key, value in self.iteritems():
			if key == 'target' or key == 'source':
				value = User.from_json(value)
			self[key] = value
		if 'favorite' in self['event']:
			self['target_object'] = Status.from_json(self['target_object'])
		elif self['event'].startswith('list_'):
			self['target_object'] = List.from_json(self['target_object'])
		return self

class DeletionEvent(Model):
	pass

class LocationDeletionEvent(Model):
	pass

class LimitEvent(Model):
	pass

class WithheldStatusEvent(Model):
	pass

class WithheldUserEvent(Model):
	pass

class DisconnectEvent(Model):
	pass

class PrivacyPolicy(str):
	@classmethod
	def from_json(cls, data):
		self = cls(data['privacy'].encode('utf-8'))
		return self
	
	def connect_api(self, api):
		pass

class TermsOfService(str):
	@classmethod
	def from_json(cls, data):
		self = cls(data['tos'].encode('utf-8'))
		return self
	
	def connect_api(self, api):
		pass

class StatusCollection(ModelCollection):
	model = Status

class UserCollection(ModelCollection):
	model = User

class MessageCollection(ModelCollection):
	model = Message

class IDCollection(list):
	@classmethod
	def from_json(cls, data):
		self = cls(data)
		return self
	
	def connect_api(self, api):
		pass

class RelationshipCollection(ModelCollection):
	model = Relationship

class SimpleRelationshipCollection(ModelCollection):
	model = SimpleRelationship

class ListCollection(ModelCollection):
	model = List

class SavedSearchCollection(ModelCollection):
	model = SavedSearch

class PlaceCollection(ModelCollection):
	model = Place

class TrendCollection(ModelCollection):
	model = Trend

class TrendLocationCollection(ModelCollection):
	model = TrendLocation

class LanguageCollection(ModelCollection):
	model = Language

class SearchResult(MixedModelCollection):
	model_key = 'statuses'
	collection = StatusCollection

class Category(MixedModelCollection):
	model_key = 'users'
	collection = UserCollection

class Trends(MixedModelCollection):
	model_key = 'trends'
	collection = TrendCollection

class CursoredIDCollection(CursoredModelCollection):
	model_key = 'ids'
	collection = IDCollection

class CursoredUserCollection(CursoredModelCollection):
	model_key = 'users'
	collection = UserCollection

class CursoredListCollection(CursoredModelCollection):
	model_key = 'lists'
	collection = ListCollection

class CategoryCollection(ModelCollection):
	model = Category

########NEW FILE########
__FILENAME__ = utils
# Copyright (C) 2013 Julian Metzler
# See the LICENSE file for the full license.

import re
from urllib import quote as _quote

def optimize_mentions(usernames, text):
	username = re.compile(r'(?:^|[^\w]+)(?P<name>@\w+)')
	existing_mentions = username.findall(text.lower())
	missing_mentions = [name for name in usernames if name.lower() not in existing_mentions]
	text = "%s %s" % (" ".join(["@%s" % name for name in missing_mentions]), text)
	return text

def quote(text, *args, **kwargs):
	t = type(text)
	if t is str:
		converted_text = text
	elif t is unicode:
		converted_text = str(text.encode('utf-8'))
	else:
		try:
			converted_text = str(text)
		except:
			converted_text = text
	return _quote(converted_text, *args, **kwargs)

########NEW FILE########
