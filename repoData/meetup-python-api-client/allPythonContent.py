__FILENAME__ = app
#!/usr/bin/env python
from __future__ import with_statement

"""
    Simple, partial test of client. Obtains an access token for the given consumer
    credentials. The authorized application will appear on this page:
    http://www.meetup.com/account/oauth_apps/
"""

import ConfigParser

import meetup_api_client as mac
from meetup_api_client import *

from optparse import OptionParser
import webbrowser
import sys

def config_client(config_name=None):
    return get_client(get_config(config_name)[1])

def get_config(name=None):
    name = name or 'app.cfg'

    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.read(name)
    
    if config.has_section('internal'):
        # you probably don't need to worry about this!
        mac.__dict__.update(config.items('internal'))

    return name, config
    
def get_client(config):
    consumer_key, consumer_secret = get_token(config, 'consumer')
    if config.has_section('access'):
        access_key, access_secret = get_token(config, 'access')
        return mac.MeetupOAuth(consumer_key, consumer_secret, access_key=access_key, access_secret=access_secret)
    else:
        return mac.MeetupOAuth(consumer_key, consumer_secret)

def get_token(config, name): return config.get(name, 'key'), config.get(name, 'secret')
def set_token(config, name, key, secret):
    config.add_section(name)
    config.set(name, 'key', key)
    config.set(name, 'secret', secret)

if __name__ == '__main__':
    option = OptionParser('%prog [options] [consumer-key] [consumer-secret]')
    option.add_option('--config', dest='config', 
        help='read & write settings to CONFIG, default is app.cfg')
    option.add_option('--verifier', dest='verifier', 
        help='oauth_callback for request-token request, defaults to oob')
    option.add_option('--callback', dest='callback', default='oob',
        help='oauth_verifier, required to gain access token')
    option.add_option('--authenticate', dest='authenticate', action='store_true',
        help='pass in to use authentication end point')
    (options, args) = option.parse_args()
    
    config_name, config = get_config(options.config)
    
    if not config.has_section('consumer'):
        if len(args) is 2:
            consumer_key, consumer_secret = args
            set_token(config, 'consumer', consumer_key, consumer_secret)
        else: option.error('please pass in consumer-key and consumer-secret')

    mucli = get_client(config)
    
    def access_granted():
        print """\
    access-key:     %s
    accses-secret:  %s
    
    Congratulations, you've got an access token! Try it out in an interpreter.
              """ % get_token(config, 'access')

    if config.has_section('access'):
        access_granted()
    else:
        if config.has_section('request'):
            if not options.verifier:
                sys.exit("To complete the process you must supply a --verifier")
            request_key, request_secret = get_token(config, 'request')
            oauth_session = mucli.new_session(request_key=request_key, request_secret=request_secret)
            print "    member_id:      %s" % oauth_session.fetch_access_token(options.verifier)
            set_token(config, 'access', oauth_session.access_token.key, oauth_session.access_token.secret)
            access_granted()
        else:
            oauth_session = mucli.new_session()
            oauth_session.fetch_request_token(callback=options.callback)
        
            set_token(config, 'request', oauth_session.request_token.key, oauth_session.request_token.secret)

            if (options.authenticate):
                url = oauth_session.get_authenticate_url()
            else:
                url = oauth_session.get_authorize_url()
            print "Opening a browser on the authorization page: %s" % url
            webbrowser.open(url)
        
   
    with open(config_name, 'wb') as c:
        config.write(c)

########NEW FILE########
__FILENAME__ = meetup_api_client
#!/usr/bin/env python
from __future__ import with_statement

import datetime
import time
import cgi
import types
import logging
from urllib import urlencode
from urllib2 import HTTPError, HTTPErrorProcessor, urlopen, Request, build_opener

import oauth
import MultipartPostHandler as mph

# This is an example of a client wrapper that you can use to
# make calls to the Meetup.com API. It requires that you have 
# a JSON parsing module available.

API_JSON_ENCODING = 'utf-8'

try:
    try:
        import cjson
        parse_json = lambda s: cjson.decode(s.decode(API_JSON_ENCODING), True)
    except ImportError:
        try:
            import json
            parse_json = lambda s: json.loads(s.decode(API_JSON_ENCODING))
        except ImportError:
            import simplejson
            parse_json = lambda s: simplejson.loads(s.decode(API_JSON_ENCODING))
except:
    print "Error - your system is missing support for a JSON parsing library."

GROUPS_URI = 'groups'
EVENTS_URI = 'events'
CITIES_URI = 'cities'
TOPICS_URI = 'topics'
PHOTOS_URI = 'photos'
MEMBERS_URI = 'members'
RSVPS_URI = 'rsvps'
RSVP_URI = 'rsvp'
COMMENTS_URI = 'comments'
PHOTO_URI = 'photo'
MEMBER_PHOTO_URI = '2/member_photo'

API_BASE_URL = 'http://api.meetup.com/'
OAUTH_BASE_URL = 'http://www.meetup.com/'


signature_method_plaintext = oauth.OAuthSignatureMethod_PLAINTEXT()
signature_method_hmac = oauth.OAuthSignatureMethod_HMAC_SHA1()

# TODO : restrict which URL parameters can be used in each of the API calls 
# TODO : screen bad queries before they go to the server 
# TODO : take care of bug with the JSON quoting (done)
# TODO : add the tests
# TODO : load the meta data from JSON (done)
# TODO : parse the 'updated' into a real python date object with strptime()
# TODO : add __str__ funcs for the objects that get created

class MeetupHTTPErrorProcessor(HTTPErrorProcessor):
    def http_response(self, request, response):
        try:
            return HTTPErrorProcessor.http_response(self, request, response)
        except HTTPError, e:
            error_json = parse_json(e.read())
            if e.code == 401:
                raise UnauthorizedError(error_json)
            elif e.code in ( 400, 500 ):
                raise BadRequestError(error_json)
            else:
                raise ClientException(error_json)

class Meetup(object):
    opener = build_opener(MeetupHTTPErrorProcessor)
    def __init__(self, api_key):
        """Initializes a new session with an api key that will be added
        to subsequent api calls"""
        self.api_key = api_key
        self.opener.addheaders = [('Accept-Charset', 'utf-8')]

    def post_rsvp(self, **args):
        return self._post(RSVP_URI, **args)

    def post_photo(self, **args):
        return self._post_multipart(PHOTO_URI, **args)

    def post_member_photo(self, **args):
        return self._post_multipart(MEMBER_PHOTO_URI, **args)

    def args_str(self, url_args):
        if self.api_key:
            url_args['key'] = self.api_key
        return urlencode(url_args)

    def _fetch(self, uri, **url_args):
        args = self.args_str(url_args)
        url = API_BASE_URL + uri + '/' + "?" + args
        logging.debug("requesting %s" % (url))
        return parse_json(self.opener.open(url).read())

    def _post(self, uri, **params):
        args = self.args_str(params)
        url = API_BASE_URL + uri + '/'
        logging.debug("posting %s to %s" % (args, url))
        return self.opener.open(url, data=args).read()

    def _post_multipart(self, uri, **params):
        params['key'] = self.api_key

        opener = build_opener(mph.MultipartPostHandler)
        url = API_BASE_URL + uri + '/'
        logging.debug("posting multipart %s to %s" % (params, url))
        return opener.open(url, params).read()

"""Add read methods to Meetup class dynamically (avoiding boilerplate)"""
READ_METHODS = ['groups', 'events', 'topics', 'cities', 'members', 'rsvps',
                'photos', 'comments', 'activity']
def _generate_read_method(name):
    def read_method(self, **args):
        return API_Response(self._fetch(name, **args), name)
    return read_method
for method in READ_METHODS:
    read_method = types.MethodType(_generate_read_method(method), None, Meetup)
    setattr(Meetup, 'get_' + method, read_method)

class NoToken(Exception):
    def __init__(self, description):
        self.description = description

    def __str__(self):
        return "NoRequestToken: %s" % (self.description)


class MeetupOAuthSession:
    def __init__(self, consumer, request_token, access_token):
        self.consumer = consumer
        self.request_token = request_token
        self.access_token = access_token

    def fetch_request_token(self, callback="oob", signature_method=signature_method_hmac):
        oauth_req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer, http_url=(OAUTH_BASE_URL + 'oauth/request/'), callback=callback)
        oauth_req.sign_request(signature_method, self.consumer, None)
        token_string = urlopen(Request(oauth_req.http_url, headers=oauth_req.to_header())).read()
        self.request_token = oauth.OAuthToken.from_string(token_string)

    def get_authorize_url(self, oauth_callback=None):
        if oauth_callback:
            callbackUrl = "&" + urlencode({"oauth_callback":oauth_callback})
        else:
            callbackUrl = ""
        return OAUTH_BASE_URL + "authorize/?oauth_token=%s%s" % (self.request_token.key, callbackUrl)

    def get_authenticate_url(self, oauth_callback=None):
        if oauth_callback:
            callbackUrl = "&" + urlencode({"oauth_callback":oauth_callback})
        else:
            callbackUrl = ""
        return OAUTH_BASE_URL + "authenticate/?oauth_token=%s%s" % (self.request_token.key, callbackUrl)

    def fetch_access_token(self, oauth_verifier, signature_method=signature_method_hmac, request_token=None):
        temp_request_token = request_token or self.request_token
        if not temp_request_token:
            raise NoToken("You must provide a request token to exchange for an access token")
        oauth_req = oauth.OAuthRequest.from_consumer_and_token(self.consumer, token=temp_request_token, 
            http_url=OAUTH_BASE_URL + 'oauth/access/', verifier=oauth_verifier)
        oauth_req.sign_request(signature_method, self.consumer, temp_request_token)
        token_string = urlopen(Request(oauth_req.http_url, headers=oauth_req.to_header())).read()
        self.access_token = oauth.OAuthToken.from_string(token_string)
        return cgi.parse_qs(token_string)['member_id'][0]

class MeetupOAuth(Meetup):

    def __init__(self, oauth_consumer_key, oauth_consumer_secret, access_key=None, access_secret=None):
        self.oauth_consumer_key = oauth_consumer_key
        self.oauth_consumer_secret = oauth_consumer_secret
        self.consumer = oauth.OAuthConsumer(self.oauth_consumer_key, self.oauth_consumer_secret)
        self.oauth_session = None
        if access_key and access_secret:
            self.oauth_session = self.new_session(access_key=access_key, access_secret=access_secret)

    def new_session(self, request_key=None, request_secret=None, access_key=None, access_secret=None):
        if request_secret and request_key:
            request_token = oauth.OAuthToken(request_key, request_secret)
        else: 
            request_token = None
        if access_secret and access_key:
            access_token = oauth.OAuthToken(access_key, access_secret)
        else: 
            access_token = None
        return MeetupOAuthSession(self.consumer, request_token, access_token)

    def _sign(self, uri, sess, oauthreq, signature_method, http_method='GET', **params):
        # the oauthreq parameter name is deprecated, please use sess or bind the session in __init__
        session = self.oauth_session or sess or oauthreq
        if not session:
            raise BadRequestError("MeetupOAuth client requires either a bound MeetupOAuthSession or one in the `sess` argument.")
        if not session.access_token:
            raise BadRequestError("Current MeetupOAuthSession does not have an access_token.")
        
        oauth_access = oauth.OAuthRequest.from_consumer_and_token(self.consumer, 
                                                                  http_method=http_method,
                                                                  token = session.access_token,
                                                                  http_url=API_BASE_URL + uri + "/",
                                                                  parameters=params)
        oauth_access.sign_request(signature_method, self.consumer, session.access_token)
        return oauth_access

    def _fetch(self, uri, sess=None, oauthreq=None, signature_method=signature_method_hmac, **url_args):
        oauth_access = self._sign(uri, sess, oauthreq, signature_method, **url_args)
        url = oauth_access.to_url()

        logging.debug("requesting %s" % (url))
        return parse_json(self.opener.open(url).read())

    def _post(self, uri, sess=None, oauthreq=None, signature_method=signature_method_hmac, **params):
        oauth_access = self._sign(uri, sess, oauthreq, signature_method, http_method='POST', **params)
        url, data = oauth_access.get_normalized_http_url(), oauth_access.to_postdata()

        logging.debug("posting %s to %s" % (data, url))
        return self.opener.open(url, data=data).read()

    def _post_multipart(self, uri, sess=None, oauthreq=None, signature_method=signature_method_hmac, **params):
        oauth_access = self._sign(uri, sess, oauthreq, signature_method, http_method='POST')
        url, headers = oauth_access.get_normalized_http_url(), oauth_access.to_header()

        opener = build_opener(mph.MultipartPostHandler)
        logging.debug("posting multipart %s to %s" % (params, url))
        return opener.open(Request(url, params, headers=headers)).read()


class API_Response(object):
    def __init__(self, json, uritype):
         """Creates an object to act as container for API return val. Copies metadata from JSON"""
         self.meta = json['meta']
         uriclasses = {GROUPS_URI:Group,
                       EVENTS_URI:Event,
                       TOPICS_URI:Topic,
                       CITIES_URI:City, 
                       MEMBERS_URI:Member,
                       PHOTOS_URI:Photo,
                       RSVPS_URI:Rsvp,
                       COMMENTS_URI:Comment}
         self.results = [uriclasses[uritype](item) for item in json['results']]

    def __str__(self):
        return 'meta: ' + str(self.meta) + '\n' + str(self.results)

class API_Item(object):
    """Base class for an item in a result set returned by the API."""

    datafields = [] #override
    def __init__(self, properties):
         """load properties that are relevant to all items (id, etc.)"""
         for field in self.datafields:
             self.__setattr__(field, properties[field])
         self.json = properties

    def __repr__(self):
         return self.__str__();

class Member(API_Item):
    datafields = ['bio', 'name', 'link','id','photo_url', 'zip','lat','lon','city','state','country','joined','visited']
    
    def get_groups(self, apiclient, **extraparams):
        extraparams.update({'member_id':self.id})
        return apiclient.get_groups(extraparams);

    def __str__(self):
        return "Member %s (url: %s)" % (self.name, self.link)

class Photo(API_Item):
    datafields = ['albumtitle', 'link', 'member_url', 'descr', 'created', 'photo_url', 'photo_urls', 'thumb_urls']

    def __str__(self):
        return "Photo located at %s posted by member at %s: (%s)" % (self.link, self.member_url, self.descr)


class Event(API_Item):
    datafields = ['id', 'name', 'updated', 'time', 'photo_url', 'event_url', 'description', 'status', \
        'rsvpcount', 'no_rsvpcount', 'maybe_rsvpcount', \
        'venue_id', 'venue_name', 'venue_phone', 'venue_address1', 'venue_address3', 'venue_address2', 'venue_city', 'venue_state', 'venue_zip', \
        'venue_map', 'venue_lat', 'venue_lon', 'venue_visibility', 'utc_rsvp_open_time']

    def __str__(self):
        return 'Event %s named %s at %s (url: %s)' % (self.id, self.name, self.time, self.event_url)

    def get_rsvps(self, apiclient, **extraparams):
        extraparams['event_id'] = self.id
        return apiclient.get_rsvps(**extraparams)

class Rsvp(API_Item):
    datafields = ['name', 'link', 'comment','zip','coord','lon','city','state','country','response','guests','answers','updated','created']

    def __str__(self):
        return 'Rsvp by %s (%s) with comment: %s' % (self.name, self.link, self.comment)

class Group(API_Item):
    datafields = [ 'id','name','group_urlname','link','updated',\
                   'members','created','photo_url',\
                   'description','zip','lat','lon',\
                   'city','state','country','organizerProfileURL', \
                   'topics']
    
    def __str__(self):
         return "%s (%s)" % (self.name, self.link)

    def get_events(self, apiclient, **extraparams):
        extraparams['group_id'] = self.id
        return apiclient.get_events(**extraparams)

    def get_photos(self, apiclient, **extraparams):
        extraparams['group_id'] = self.id
        return apiclient.get_photos(**extraparams)

    def get_members(self, apiclient, **extraparams):
        extraparams['group_id'] = self.id
        return apiclient.get_members(**extraparams)

class City(API_Item):
    datafields = ['city','country','state','zip','members','lat','lon']

    def __str__(self):
         return "%s %s, %s, %s, with %s members" % (self.city, self.zip, self.country, self.state, self.members)

    def get_groups(self,apiclient,  **extraparams):
        extraparams.update({'city':self.city, 'country':self.country})
        if self.country=='us': extraparams['state'] = self.state
        return apiclient.get_groups(**extraparams)

    def get_events(self,apiclient,  **extraparams):
        extraparams.update({'city':self.city, 'country':self.country})
        if self.country=='us': extraparams['state'] = self.state
        return apiclient.get_events(**extraparams) 

class Topic(API_Item):
    datafields = ['id','name','description','link','updated',\
                  'members','urlkey']
    
    def __str__(self):
         return "%s with %s members (%s)" % (self.name, self.members,
                                             self.urlkey)

    def get_groups(self, apiclient, **extraparams):
         extraparams['topic'] = self.urlkey
         return apiclient.get_groups(**extraparams)
    
    def get_photos(self, apiclient, **extraparams):
         extraparams['topic_id'] = self.id
         return apiclient.get_photos(**extraparams)

class Comment(API_Item):
    datafields = ['name','link','comment','photo_url',\
                  'created','lat','lon','country','city','state']
    
    def __str__(self):
         return "Comment from %s (%s)" % (self.name, self.link)

########################################

class ClientException(Exception):
    """
         Base class for generic errors returned by the server
    """
    def __init__(self, error_json):
         self.description = error_json['details']
         self.problem = error_json['problem']

    def __str__(self):
         return "%s: %s" % (self.problem, self.description)

class UnauthorizedError(ClientException):
    pass;

class BadRequestError(ClientException):
    pass;


########NEW FILE########
__FILENAME__ = MultipartPostHandler
#!/usr/bin/python

####
# 02/2006 Will Holcomb <wholcomb@gmail.com>
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
"""
Usage:
  Enables the use of multipart/form-data for posting forms

Inspirations:
  Upload files in python:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306
  urllib2_file:
    Fabien Seisen: <fabien@seisen.org>

Example:
  import MultipartPostHandler, urllib2, cookielib

  cookies = cookielib.CookieJar()
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),
                                MultipartPostHandler.MultipartPostHandler)
  params = { "username" : "bob", "password" : "riviera",
             "file" : open("filename", "rb") }
  opener.open("http://wwww.bobsite.com/upload/", params)

Further Example:
  The main function of this file is a sample which downloads a page and
  then uploads it to the W3C validator.
"""

import urllib
import urllib2
import mimetools, mimetypes
import os, stat

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

# Controls how sequences are uncoded. If true, elements may be given multiple values by
#  assigning a sequence.
doseq = 1

class MultipartPostHandler(urllib2.BaseHandler):
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is not None and type(data) != str:
            v_files = []
            v_vars = []
            try:
                 for(key, value) in data.items():
                     if type(value) == file:
                         v_files.append((key, value))
                     else:
                         v_vars.append((key, value))
            except TypeError:
                systype, value, traceback = sys.exc_info()
                raise TypeError, "not a valid non-string sequence or mapping object", traceback

            if len(v_files) == 0:
                data = urllib.urlencode(v_vars, doseq)
            else:
                boundary, data = self.multipart_encode(v_vars, v_files)
                contenttype = 'multipart/form-data; boundary=%s' % boundary
                if(request.has_header('Content-Type')
                   and request.get_header('Content-Type').find('multipart/form-data') != 0):
                    print "Replacing %s with %s" % (request.get_header('content-type'), 'multipart/form-data')
                request.add_unredirected_header('Content-Type', contenttype)

            request.add_data(data)
        return request

    def multipart_encode(vars, files, boundary = None, buffer = None):
        if boundary is None:
            boundary = mimetools.choose_boundary()
        if buffer is None:
            buffer = ''
        for(key, value) in vars:
            buffer += '--%s\r\n' % boundary
            buffer += 'Content-Disposition: form-data; name="%s"' % key
            buffer += '\r\n\r\n' + value + '\r\n'
        for(key, fd) in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = os.path.basename(fd.name)
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            buffer += '--%s\r\n' % boundary
            buffer += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename)
            buffer += 'Content-Type: %s\r\n' % contenttype
            # buffer += 'Content-Length: %s\r\n' % file_size
            fd.seek(0)
            buffer += '\r\n' + fd.read() + '\r\n'
        buffer += '--%s--\r\n\r\n' % boundary
        return boundary, buffer
    multipart_encode = Callable(multipart_encode)

    https_request = http_request

def main():
    import tempfile, sys

    validatorURL = "http://validator.w3.org/check"
    opener = urllib2.build_opener(MultipartPostHandler)

    def validateFile(url):
        temp = tempfile.mkstemp(suffix=".html")
        os.write(temp[0], opener.open(url).read())
        params = { "ss" : "0",            # show source
                   "doctype" : "Inline",
                   "uploaded_file" : open(temp[1], "rb") }
        print opener.open(validatorURL, params).read()
        os.remove(temp[1])

    if len(sys.argv[1:]) > 0:
        for arg in sys.argv[1:]:
            validateFile(arg)
    else:
        validateFile("http://www.google.com")

if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key

########NEW FILE########
