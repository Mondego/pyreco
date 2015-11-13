__FILENAME__ = api_test
import codecs
from datetime import datetime
import sys
from TwitterAPI import TwitterAPI, TwitterOAuth, TwitterRestPager


try:
    # python 3
    sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)
except:
    # python 2
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)


# SAVE YOUR APPLICATION CREDENTIALS IN TwitterAPI/credentials.txt.
o = TwitterOAuth.read_file()

# Using OAuth1...
api = TwitterAPI(
    o.consumer_key,
    o.consumer_secret,
    o.access_token_key,
    o.access_token_secret)

# Using OAuth2...
#api = TwitterAPI(o.consumer_key, o.consumer_secret, auth_type="oAuth2")


TEST_NUMBER = 0


try:
    if TEST_NUMBER == 0:

        # VERIFY YOUR CREDS
        r = api.request('account/verify_credentials')
        print(r.text)

    if TEST_NUMBER == 1:

        # POST A TWEET
        r = api.request('statuses/update',
                        {'status': 'the time is now %s' % datetime.now()})
        print(r.status_code)

    if TEST_NUMBER == 2:

        # GET 5 TWEETS CONTAINING 'ZZZ'
        for item in api.request('search/tweets', {'q': 'zzz', 'count': 5}):
            print(item['text'] if 'text' in item else item)

    if TEST_NUMBER == 3:

        # STREAM TWEETS FROM AROUND NYC
        for item in api.request('statuses/filter', {'locations': '-74,40,-73,41'}):
            print(item['text'] if 'text' in item else item)

    if TEST_NUMBER == 4:

        # GET TWEETS FROM THE PAST WEEK OR SO CONTAINING 'LOVE'
        pager = TwitterRestPager(api, 'search/tweets', {'q': 'love'})
        for item in pager.get_iterator():
            print(item['text'] if 'text' in item else item)

except Exception as e:
    print(e)

########NEW FILE########
__FILENAME__ = how_to_connect
from TwitterAPI import TwitterAPI


CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN_KEY = ''
ACCESS_TOKEN_SECRET = ''


# If you are behind a firewall you may need to provide proxy server
# authentication.
proxy_url = None  # Example: 'https://USERNAME:PASSWORD@PROXYSERVER:PORT'

# Using OAuth 1.0 to authenticate you have access all Twitter endpoints.
# Using OAuth 2.0 to authenticate you lose access to user specific endpoints (ex. statuses/update),
# but you get higher rate limits.
api = TwitterAPI(
    CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET,
    auth_type='oAuth1',
    proxy_url=proxy_url)
#api = TwitterAPI(CONSUMER_KEY, CONSUMER_SECRET, auth_type='oAuth2', proxy_url=proxy_url)


r = api.request('application/rate_limit_status')


# Print HTTP status code (=200 when no errors).
print(r.status_code)

# Print the raw response.
print(r.text)

# Parse the JSON response.
j = r.response.json()
print(j['resources']['search'])

########NEW FILE########
__FILENAME__ = oauth_test
import requests
from requests_oauthlib import OAuth1
from urlparse import parse_qs
from TwitterAPI import TwitterAPI


consumer_key = '<YOUR APPLICATION KEY>'
consumer_secret = '<YOUR APPLICATION SECRET>'


# obtain request token
oauth = OAuth1(consumer_key, consumer_secret)
r = requests.post(
    url='https://api.twitter.com/oauth/request_token',
    auth=oauth)
credentials = parse_qs(r.content)
request_key = credentials.get('oauth_token')[0]
request_secret = credentials.get('oauth_token_secret')[0]


# obtain authorization from resource owner
print(
    'Go here to authorize:\n  https://api.twitter.com/oauth/authorize?oauth_token=%s' %
    request_key)
verifier = raw_input('Enter your authorization code: ')


# obtain access token
oauth = OAuth1(
    consumer_key,
    consumer_secret,
    request_key,
    request_secret,
    verifier=verifier)
r = requests.post(url='https://api.twitter.com/oauth/access_token', auth=oauth)
credentials = parse_qs(r.content)
access_token_key = credentials.get('oauth_token')[0]
access_token_secret = credentials.get('oauth_token_secret')[0]


# access resource
api = TwitterAPI(
    consumer_key,
    consumer_secret,
    access_token_key,
    access_token_secret)
for item in api.request('statuses/filter', {'track': 'zzz'}):
    print(item['text'])

########NEW FILE########
__FILENAME__ = page_tweets
from TwitterAPI import TwitterAPI, TwitterRestPager


SEARCH_TERM = 'pizza'


CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN_KEY = ''
ACCESS_TOKEN_SECRET = ''


api = TwitterAPI(
    CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET)

pager = TwitterRestPager(api, 'search/tweets', {'q': SEARCH_TERM})

for item in pager.get_iterator():
    print(item['text'] if 'text' in item else item)

########NEW FILE########
__FILENAME__ = post_image
from TwitterAPI import TwitterAPI


TWEET_TEXT = 'some tweet text'
IMAGE_PATH = './some_image.png'


CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN_KEY = ''
ACCESS_TOKEN_SECRET = ''


api = TwitterAPI(
    CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET)

file = open(IMAGE_PATH, 'rb')
data = file.read()
r = api.request('statuses/update_with_media',
                {'status': TWEET_TEXT},
                {'media[]': data})

print('SUCCESS' if r.status_code == 200 else 'FAILURE')

########NEW FILE########
__FILENAME__ = post_tweet
from TwitterAPI import TwitterAPI


TWEET_TEXT = "Ce n'est pas un tweet tweet."


CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN_KEY = ''
ACCESS_TOKEN_SECRET = ''


api = TwitterAPI(
    CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET)

r = api.request('statuses/update', {'status': TWEET_TEXT})

print('SUCCESS' if r.status_code == 200 else 'FAILURE')

########NEW FILE########
__FILENAME__ = search_tweets
from TwitterAPI import TwitterAPI


SEARCH_TERM = 'pizza'


CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN_KEY = ''
ACCESS_TOKEN_SECRET = ''


api = TwitterAPI(
    CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET)

r = api.request('search/tweets', {'q': SEARCH_TERM})

for item in r:
    print(item['text'] if 'text' in item else item)

print('\nQUOTA: %s' % r.get_rest_quota())

########NEW FILE########
__FILENAME__ = stream_tweets
from TwitterAPI import TwitterAPI


TRACK_TERM = 'pizza'


CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN_KEY = ''
ACCESS_TOKEN_SECRET = ''


api = TwitterAPI(
    CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET)

r = api.request('statuses/filter', {'track': TRACK_TERM})

for item in r:
    print(item['text'] if 'text' in item else item)

########NEW FILE########
__FILENAME__ = BearerAuth
__author__ = "Andrea Biancini, Jonas Geduldig"
__date__ = "January 3, 2014"
__license__ = "MIT"

import base64
from .constants import *
import requests


class BearerAuth(requests.auth.AuthBase):

    """Request bearer access token for oAuth2 authentication.

    :param consumer_key: Twitter application consumer key
    :param consumer_secret: Twitter application consumer secret
    :param proxies: Dictionary of proxy URLs (see documentation for python-requests).
    """

    def __init__(self, consumer_key, consumer_secret, proxies=None):
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self.proxies = proxies
        self._bearer_token = self._get_access_token()

    def _get_access_token(self):
        token_url = '%s://%s.%s/%s' % (PROTOCOL,
                                       REST_SUBDOMAIN,
                                       DOMAIN,
                                       OAUTH2_TOKEN_ENDPOINT)
        auth = self._consumer_key + ':' + self._consumer_secret
        b64_bearer_token_creds = base64.b64encode(auth.encode('utf8'))
        params = {'grant_type': 'client_credentials'}
        headers = {}
        headers['User-Agent'] = USER_AGENT
        headers['Authorization'] = 'Basic ' + \
            b64_bearer_token_creds.decode('utf8')
        headers[
            'Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
        try:
            response = requests.post(
                token_url,
                params=params,
                headers=headers,
                proxies=self.proxies)
            data = response.json()
            return data['access_token']
        except Exception as e:
            raise Exception(
                'Error while requesting bearer access token: %s' %
                e)

    def __call__(self, r):
        auth_list = [
            self._consumer_key,
            self._consumer_secret,
            self._bearer_token]
        if all(auth_list):
            r.headers['Authorization'] = "Bearer %s" % self._bearer_token
            return r
        else:
            raise Exception('Not enough keys passed to Bearer token manager.')

########NEW FILE########
__FILENAME__ = cli
"""
	A Command-Line Interface to Twitter's REST API and Streaming API.
	-----------------------------------------------------------------
	
	Run this command line script with any Twitter endpoint.  The json-formatted
	response is printed to the console.  The script works with both Streaming API and
	REST API endpoints.

	IMPORTANT: Before using this script, you must enter your Twitter application's OAuth
	credentials in TwitterAPI/credentials.txt.  Log into http://dev.twitter.com to create
	your application.
	
	Examples:

	::
	
		python -u -m TwitterAPI.cli -endpoint search/tweets -parameters q=zzz
		python -u -m TwitterAPI.cli -endpoint statuses/filter -parameters track=zzz
		
	These examples print the raw json response.  You can also print one or more fields
	from the response, for instance the tweet 'text' field, like this:
	
	::
	
		python -u -m TwitterAPI.cli -endpoint statuses/filter -parameters track=zzz -fields text
		
	Documentation for all Twitter endpoints is located at:
		 https://dev.twitter.com/docs/api/1.1
"""

__author__ = "Jonas Geduldig"
__date__ = "June 7, 2013"
__license__ = "MIT"

import argparse
import codecs
from pprint import PrettyPrinter
import sys
from .TwitterOAuth import TwitterOAuth
from .TwitterAPI import TwitterAPI


def _search(name, obj):
    """Breadth-first search for name in the JSON response and return value."""
    q = []
    q.append(obj)
    while q:
        obj = q.pop(0)
        if hasattr(obj, '__iter__'):
            isdict = isinstance(obj, dict)
            if isdict and name in obj:
                return obj[name]
            for k in obj:
                q.append(obj[k] if isdict else k)
    else:
        return None


def _to_dict(param_list):
    """Convert a list of key=value to dict[key]=value"""
    if param_list:
        return {
            name: value for (
                name,
                value) in [
                param.split('=') for param in param_list]}
    else:
        return None


if __name__ == '__main__':
    # print UTF-8 to the console
    try:
        # python 3
        sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)
    except:
        # python 2
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)

    parser = argparse.ArgumentParser(
        description='Request any Twitter Streaming or REST API endpoint')
    parser.add_argument(
        '-oauth',
        metavar='FILENAME',
        type=str,
        help='file containing OAuth credentials')
    parser.add_argument(
        '-endpoint',
        metavar='ENDPOINT',
        type=str,
        help='Twitter endpoint',
        required=True)
    parser.add_argument(
        '-parameters',
        metavar='NAME_VALUE',
        type=str,
        help='parameter NAME=VALUE',
        nargs='+')
    parser.add_argument(
        '-fields',
        metavar='FIELD',
        type=str,
        help='print a top-level field in the json response',
        nargs='+')
    args = parser.parse_args()

    try:
        params = _to_dict(args.parameters)
        oauth = TwitterOAuth.read_file(args.oauth)

        api = TwitterAPI(
            oauth.consumer_key,
            oauth.consumer_secret,
            oauth.access_token_key,
            oauth.access_token_secret)
        response = api.request(args.endpoint, params)

        pp = PrettyPrinter()
        for item in response.get_iterator():
            if 'message' in item:
                print('ERROR %s: %s' % (item['code'], item['message']))
            elif not args.fields:
                pp.pprint(item)
            else:
                for name in args.fields:
                    value = _search(name, item)
                    if value:
                        print('%s: %s' % (name, value))

    except KeyboardInterrupt:
        print('\nTerminated by user')

    except Exception as e:
        print('*** STOPPED %s' % str(e))

########NEW FILE########
__FILENAME__ = constants
"""
	Constants For All Twitter Endpoints
	-----------------------------------
	
	Version 1.1, Streaming API and REST API.
	
	URLs for each endpoint are composed of the following pieces:
		PROTOCOL://{subdomain}.DOMAIN/VERSION/{resource}?{parameters}
"""

__author__ = "Jonas Geduldig"
__date__ = "February 3, 2012"
__license__ = "MIT"


PROTOCOL = 'https'

DOMAIN = 'twitter.com'

VERSION = '1.1'

USER_AGENT = 'python-TwitterAPI'

STREAMING_SOCKET_TIMEOUT = 90  # 90 seconds per Twitter's recommendation

STREAMING_ENDPOINTS = {
		# resource:                                ( subdomain )

		'statuses/filter':                         ('stream',),
		'statuses/firehose':                       ('stream',),
		'statuses/sample':                         ('stream',),
		'site':                                    ('sitestream',),
		'user':                                    ('userstream',)
}

REST_SUBDOMAIN = 'api'

REST_SOCKET_TIMEOUT = 5

OAUTH2_TOKEN_ENDPOINT = 'oauth2/token'

REST_ENDPOINTS = {
		# resource:                                ( method )

		'statuses/destroy/:PARAM':                 ('POST',),  # ID
		'statuses/home_timeline':                  ('GET',),
		'statuses/mentions_timeline':              ('GET',),
		'statuses/oembed':                         ('GET',),
		'statuses/retweets_of_me':                 ('GET',),
		'statuses/retweet/:PARAM':                 ('POST',),  # ID
		'statuses/retweets/:PARAM':                ('GET',),   # ID
		'statuses/show/:PARAM':                    ('GET',),   # ID
		'statuses/user_timeline':                  ('GET',),
		'statuses/update':                         ('POST',),
		'statuses/update_with_media':              ('POST',),

		'search/tweets':                           ('GET',),

		'direct_messages':                         ('GET',),
		'direct_messages/destroy':                 ('POST',),
		'direct_messages/new':                     ('POST',),
		'direct_messages/sent':                    ('GET',),
		'direct_messages/show':                    ('GET',),

		'friends/ids':                             ('GET',),
		'friends/list':                            ('GET',),

		'followers/ids':                           ('GET',),
		'followers/list':                          ('GET',),

		'friendships/create':                      ('POST',),
		'friendships/destroy':                     ('POST',),
		'friendships/incoming':                    ('GET',),
		'friendships/lookup':                      ('GET',),
		'friendships/no_retweets/ids':             ('GET',),
		'friendships/outgoing':                    ('GET',),
		'friendships/show':                        ('GET',),
		'friendships/update':                      ('POST',),

		'account/remove_profile_banner':           ('POST',),
		'account/settings':                        ('GET',),
		'account/update_delivery_device':          ('POST',),
		'account/update_profile':                  ('POST',),
		'account/update_profile_background_image': ('POST',),
		'account/update_profile_banner':           ('POST',),
		'account/update_profile_colors':           ('POST',),
		'account/update_profile_image':            ('POST',),
		'account/verify_credentials':              ('GET',),

		'blocks/create':                           ('POST',),
		'blocks/destroy':                          ('POST',),
		'blocks/ids':                              ('GET',),
		'blocks/list':                             ('GET',),

		'users/contributees':                      ('GET',),
		'users/contributors':                      ('GET',),
		'users/lookup':                            ('GET',),
		'users/profile_banner':                    ('get'),
		'users/report_spam':                       ('POST',),
		'users/search':                            ('GET',),
		'users/show':                              ('GET',),
		'users/suggestions':                       ('GET',),
		'users/suggestions/:PARAM':                ('GET',),  # SLUG
		'users/suggestions/:PARAM/members':        ('GET',),  # SLUG

		'favorites/create':                        ('POST',),
		'favorites/destroy':                       ('POST',),
		'favorites/list':                          ('GET',),

		'lists/create':                            ('POST',),
		'lists/destroy':                           ('POST',),
		'lists/list':                              ('GET',),
		'lists/members':                           ('GET',),
		'lists/members/create':                    ('POST',),
		'lists/members/create_all':                ('POST',),
		'lists/members/destroy':                   ('POST',),
		'lists/members/destroy_all':               ('POST',),
		'lists/members/show':                      ('GET',),
		'lists/memberships':                       ('GET',),
		'lists/show':                              ('GET',),
		'lists/statuses':                          ('GET',),
		'lists/subscribers':                       ('GET',),
		'lists/subscribers/create':                ('POST',),
		'lists/subscribers/destroy':               ('POST',),
		'lists/subscribers/show':                  ('GET',),
		'lists/subscriptions':                     ('GET',),
		'lists/update':                            ('POST',),

		'saved_searches/create':                   ('POST',),
		'saved_searches/destroy/:PARAM':           ('POST',),  # ID
		'saved_searches/list':                     ('GET',),
		'saved_searches/show/:PARAM':              ('GET',),   # ID

		'geo/id/:PARAM':                           ('GET',),   # PLACE_ID
		'geo/place':                               ('POST',),
		'geo/reverse_geocode':                     ('GET',),
		'geo/search':                              ('GET',),
		'geo/similar_places':                      ('GET',),

		'trends/available':                        ('GET',),
		'trends/closest':                          ('GET',),
		'trends/place':                            ('GET',),

		'help/configuration':                      ('GET',),
		'help/languages':                          ('GET',),
		'help/privacy':                            ('GET',),
		'help/tos':                                ('GET',),

		'application/rate_limit_status':           ('GET',)
}

########NEW FILE########
__FILENAME__ = TwitterAPI
__author__ = "Jonas Geduldig"
__date__ = "June 7, 2013"
__license__ = "MIT"

from .constants import *
import json
from requests_oauthlib import OAuth1
from .BearerAuth import BearerAuth as OAuth2
from datetime import datetime
import requests


class TwitterAPI(object):

    """Access REST API or Streaming API resources.

    :param consumer_key: Twitter application consumer key
    :param consumer_secret: Twitter application consumer secret
    :param access_token_key: Twitter application access token key
    :param access_token_secret: Twitter application access token secret
    :param auth_type: "oAuth1" (default) or "oAuth2"
    :param proxy_url: HTTPS proxy URL (ex. "https://USER:PASSWORD@SERVER:PORT")
    """

    def __init__(
            self,
            consumer_key=None,
            consumer_secret=None,
            access_token_key=None,
            access_token_secret=None,
            auth_type='oAuth1',
            proxy_url=None):
        """Initialize with your Twitter application credentials"""
        self.proxies = {'https': proxy_url} if proxy_url else None
        if auth_type is 'oAuth1':
            if not all([consumer_key, consumer_secret, access_token_key, access_token_secret]):
                raise Exception('Missing authentication parameter.')
            self.auth = OAuth1(
                consumer_key,
                consumer_secret,
                access_token_key,
                access_token_secret)
        elif auth_type is 'oAuth2':
            if not all([consumer_key, consumer_secret]):
                raise Exception("Missing authentication parameter.")
            self.auth = OAuth2(
                consumer_key,
                consumer_secret,
                proxies=self.proxies)

    def _prepare_url(self, subdomain, path):
        return '%s://%s.%s/%s/%s.json' % (PROTOCOL,
                                          subdomain,
                                          DOMAIN,
                                          VERSION,
                                          path)

    def _get_endpoint(self, resource):
        """Substitute any parameters in the resource path with :PARAM."""
        if ':' in resource:
            parts = resource.split('/')
            # embedded parameters start with ':'
            parts = [k if k[0] != ':' else ':PARAM' for k in parts]
            endpoint = '/'.join(parts)
            resource = resource.replace(':', '')
            return (resource, endpoint)
        else:
            return (resource, resource)

    def request(self, resource, params=None, files=None):
        """Request a Twitter REST API or Streaming API resource.

        :param resource: A valid Twitter endpoint (ex. "search/tweets")
        :param params: Dictionary with endpoint parameters or None (default)
        :param files: Dictionary with multipart-encoded file or None (default)

        :returns: TwitterAPI.TwitterResponse object
        """
        session = requests.Session()
        session.auth = self.auth
        session.headers = {'User-Agent': USER_AGENT}
        resource, endpoint = self._get_endpoint(resource)
        if endpoint in STREAMING_ENDPOINTS:
            session.stream = True
            method = 'GET' if params is None else 'POST'
            url = self._prepare_url(STREAMING_ENDPOINTS[endpoint][0], resource)
            timeout = STREAMING_SOCKET_TIMEOUT
        elif endpoint in REST_ENDPOINTS:
            session.stream = False
            method = REST_ENDPOINTS[endpoint][0]
            url = self._prepare_url(REST_SUBDOMAIN, resource)
            timeout = REST_SOCKET_TIMEOUT
        else:
            raise Exception('"%s" is not valid endpoint' % resource)
        r = session.request(
            method,
            url,
            params=params,
            timeout=timeout,
            files=files,
            proxies=self.proxies)
        return TwitterResponse(r, session.stream)


class TwitterResponse(object):

    """Response from either a REST API or Streaming API resource call.

    :param response: The requests.Response object returned by the API call
    :param stream: Boolean connection type (True if a streaming connection)
    """

    def __init__(self, response, stream):
        self.response = response
        self.stream = stream

    @property
    def headers(self):
        """:returns: Dictionary of API response header contents."""
        return self.response.headers

    @property
    def status_code(self):
        """:returns: HTTP response status code."""
        return self.response.status_code

    @property
    def text(self):
        """:returns: Raw API response text."""
        return self.response.text

    def get_iterator(self):
        """:returns: TwitterAPI.StreamingIterator or TwitterAPI.RestIterator."""
        if self.stream:
            return StreamingIterator(self.response)
        else:
            return RestIterator(self.response)

    def __iter__(self):
        for item in self.get_iterator():
            yield item

    def get_rest_quota(self):
        """:returns: Quota information in the response header.  Valid only for REST API responses."""
        remaining, limit, reset = None, None, None
        if self.response:
            if 'x-rate-limit-remaining' in self.response.headers:
                remaining = int(
                    self.response.headers['x-rate-limit-remaining'])
                if remaining == 0:
                    limit = int(self.response.headers['x-rate-limit-limit'])
                    reset = int(self.response.headers['x-rate-limit-reset'])
                    reset = datetime.fromtimestamp(reset)
        return {'remaining': remaining, 'limit': limit, 'reset': reset}


class RestIterator(object):

    """Iterate statuses, errors or other iterable objects in a REST API response.

    :param response: The request.Response from a Twitter REST API request
    """

    def __init__(self, response):
        resp = response.json()
        if 'errors' in resp:
            self.results = resp['errors']
        elif 'statuses' in resp:
            self.results = resp['statuses']
        elif hasattr(resp, '__iter__') and not isinstance(resp, dict):
            if len(resp) > 0 and 'trends' in resp[0]:
                self.results = resp[0]['trends']
            else:
                self.results = resp
        else:
            self.results = (resp,)

    def __iter__(self):
        """Return a tweet status as a JSON object."""
        for item in self.results:
            yield item


class StreamingIterator(object):

    """Iterate statuses or other objects in a Streaming API response.

    :param response: The request.Response from a Twitter Streaming API request
    """

    def __init__(self, response):
        self.results = response.iter_lines(1)

    def __iter__(self):
        """Return a tweet status as a JSON object."""
        for item in self.results:
            if item:
                yield json.loads(item.decode('utf-8'))

########NEW FILE########
__FILENAME__ = TwitterOAuth
__author__ = "Jonas Geduldig"
__date__ = "February 7, 2013"
__license__ = "MIT"

import os


class TwitterOAuth:

    """Optional class for retrieving Twitter credentials stored in a text file.

    :param consumer_key: Twitter application consumer key
    :param consumer_secret: Twitter application consumer secret
    :param access_token_key: Twitter application access token key
    :param access_token_secret: Twitter application access token secret
    """

    def __init__(
            self,
            consumer_key,
            consumer_secret,
            access_token_key,
            access_token_secret):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token_key = access_token_key
        self.access_token_secret = access_token_secret

    @classmethod
    def read_file(cls, file_name=None):
        """Read OAuth credentials from a text file.  File format:

                consumer_key=YOUR_CONSUMER_KEY

                consumer_secret=YOUR_CONSUMER_SECRET

                access_token_key=YOUR_ACCESS_TOKEN

                access_token_secret=YOUR_ACCESS_TOKEN_SECRET

        :param file_name: File containing credentials or None (default) reads credentials
                          from TwitterAPI/credentials.txt
        """
        if file_name is None:
            path = os.path.dirname(__file__)
            file_name = os.path.join(path, 'credentials.txt')

        with open(file_name) as f:
            oauth = {}
            for line in f:
                if '=' in line:
                    name, value = line.split('=', 1)
                    oauth[name.strip()] = value.strip()
            return TwitterOAuth(
                oauth['consumer_key'],
                oauth['consumer_secret'],
                oauth['access_token_key'],
                oauth['access_token_secret'])

########NEW FILE########
__FILENAME__ = TwitterRestPager
__author__ = "Jonas Geduldig"
__date__ = "June 8, 2013"
__license__ = "MIT"

import time


class TwitterRestPager(object):

    """Continuous (stream-like) pagination of response from Twitter REST API resource.

    :param api: An authenticated TwitterAPI object
    :param resource: String with the resource path (ex. search/tweets)
    :param params: Dictionary of resource parameters
    """

    def __init__(self, api, resource, params=None):
        self.api = api
        self.resource = resource
        self.params = params

    def get_iterator(self, wait=5, new_tweets=False):
        """Iterate response from Twitter REST API resource.  Resource is called
        in a loop to retrieve consecutive pages of results.

        :param wait: Integer number (default=5) of seconds wait between requests.
                     Depending on the resource, appropriate values are 5 or 60 seconds.
        :param new_tweets: Boolean determining the search direction
                           False (default) retrieves old results.
                           True retrieves current results.

        :returns: JSON objects containing statuses, errors or other return info.
        """
        elapsed = 0
        while True:
            # get one page of results
            start = time.time()
            req = self.api.request(self.resource, self.params)
            iter = req.get_iterator()
            if new_tweets:
                iter.results = reversed(iter.results)

            # yield each item in the page
            id = None
            for item in iter:
                if 'id' in item:
                    id = item['id']
                yield item

            # sleep before getting another page of results
            elapsed = time.time() - start
            pause = wait - elapsed if elapsed < wait else 0
            time.sleep(pause)

            # use the first or last tweet id to limit (depending on the newer/older direction)
            # the next request
            if id is None:
                continue
            elif new_tweets:
                self.params['since_id'] = str(id)
            else:
                self.params['max_id'] = str(id - 1)

########NEW FILE########
