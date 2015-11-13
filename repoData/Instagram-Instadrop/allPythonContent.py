__FILENAME__ = debug
def set_trace():
    import pdb, sys
    debugger = pdb.Pdb(stdin=sys.__stdin__,
        stdout=sys.__stdout__)
    debugger.set_trace(sys._getframe().f_back)

########NEW FILE########
__FILENAME__ = auth
"""
The dropbox.auth module is responsible for making OAuth work for the Dropbox
Client API.  It glues together all the separate parts of the Python OAuth
reference implementation and gives a nicer API to it.  You'll pass a
configure dropbox.auth.Authenticator object to dropbox.client.DropboxClient
in order to work with the API.
"""

import httplib
import urllib
from django.utils import simplejson as json
from oauth import oauth
from ConfigParser import SafeConfigParser

REALM="No Realm"
HTTP_DEBUG_LEVEL=0

class SimpleOAuthClient(oauth.OAuthClient):
    """
    An implementation of the oauth.OAuthClient class providing OAuth services
    for the Dropbox Client API.  You shouldn't have to use this, but if you need
    to implement your own OAuth, then this is where to look.

    One setting of interest is the HTTP_DEBUG_LEVEL, which you can set to a
    larger number to get detailed HTTP output.
    """
    def __init__(self, server, port=httplib.HTTP_PORT, request_token_url='', access_token_url='', authorization_url=''):
        self.server = server
        self.port = port
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authorization_url = authorization_url
        self.connection = httplib.HTTPConnection(self.server, int(self.port))
        self.connection.set_debuglevel(HTTP_DEBUG_LEVEL)

    def fetch_request_token(self, oauth_request):
        """Called by oauth to fetch the request token from Dropbox.  Returns an OAuthToken."""
        self.connection.request(oauth_request.http_method,
                                self.request_token_url,
                                headers=oauth_request.to_header())
        response = self.connection.getresponse()
        data = response.read()
        assert response.status == 200, "Invalid response code %d : %r" % (response.status, data)
        return oauth.OAuthToken.from_string(data)

    def fetch_access_token(self, oauth_request, trusted_url=None):
        """Used to get a access token from Drobpox using the headers.  Returns an OauthToken."""
        url = trusted_url if trusted_url else self.access_token_url

        self.connection.request(oauth_request.http_method, url,
                                headers=oauth_request.to_header()) 

        response = self.connection.getresponse()
        assert response.status == 200, "Invalid response code %d" % response.status
        if trusted_url:
            token = json.loads(response.read())
            token['token'] = str(token['token'])
            token['secret'] = str(token['secret'])
            return oauth.OAuthToken(token['token'], token['secret'])
        else:
            return oauth.OAuthToken.from_string(response.read())

    def authorize_token(self, oauth_request):
        """
        This is not used in the Drobpox API.
        """
        raise NotImplementedError("authorize_token is not implemented via OAuth.")

    def access_resource(self, oauth_request):
        """
        Not used by the Dropbox API.
        """
        raise NotImplementedError("access_resource is not implemented via OAuth.")




class Authenticator(object):
    """
    The Authenticator puts a thin gloss over the oauth.oauth Python library
    so that the dropbox.client.DropboxClient doesn't need to know much about
    your configuration and OAuth operations.

    It uses a configuration file in the standard .ini format that ConfigParser
    understands.  A sample configuration is included in config/testing.ini
    which you should copy and put in your own consumer keys and secrets.

    Because different installations may want to store these configurations
    differently, you aren't required to configure an Authenticator via 
    the .ini method.  As long as you configure it with a dict with the 
    same keys you'll be fine.
    """
    
    def __init__(self, config):
        """
        Configures the Authenticator with all the required settings in config.
        Typically you'll use Authenticator.load_config() to load these from
        a .ini file and then pass the returned dict to here.
        """
        self.client = SimpleOAuthClient(config['server'],
                                        config['port'],
                                        config['request_token_url'], 
                                        config['access_token_url'], 
                                        config['authorization_url'])

        self.trusted_access_token_url = config.get('trusted_access_token_url', None)

        self.consumer = oauth.OAuthConsumer(config['consumer_key'],
                                            config['consumer_secret'])

        self.signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()

        self.config = config


    @classmethod
    def load_config(self, filename):
        """
        Loads a configuration .ini file, and then pulls out the 'auth' key
        to make a dict you can pass to Authenticator().
        """
        config = SafeConfigParser()
        config_file = open(filename, "r")
        config.readfp(config_file)
        return dict(config.items('auth'))

    def build_authorize_url(self, req_token, callback=None):
        """
        When you send a user to authorize a request token you created, you need
        to make the URL correctly.  This is the method you use.  It will
        return a URL that you can then redirect a user at so they can login to
        Dropbox and approve this request key.
        """
        if callback:
            oauth_callback = "&%s" % urllib.urlencode({'oauth_callback': callback})
        else:
            oauth_callback = ""

        return "%s?oauth_token=%s%s" % (self.config['authorization_url'], req_token.key, oauth_callback)

    
    def obtain_request_token(self):
        """
        This is your first step in the OAuth process.  You call this to get a
        request_token from the Dropbox server that you can then use with
        Authenticator.build_authorize_url() to get the user to authorize it.
        After it's authorized you use this token with
        Authenticator.obtain_access_token() to get an access token.

        NOTE:  You should only need to do this once for each user, and then you
        store the access token for that user for later operations.
        """
        self.oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                   http_url=self.client.request_token_url)

        self.oauth_request.sign_request(self.signature_method_hmac_sha1, self.consumer, None)

        token = self.client.fetch_request_token(self.oauth_request)

        return token


    def obtain_access_token(self, token, verifier):
        """
        After you get a request token, and then send the user to the authorize
        URL, you can use the authorized access token with this method to get the
        access token to use for future operations.  Store this access token with 
        the user so that you can reuse it on future operations.

        The verifier parameter is not currently used, but will be enforced in
        the future to follow the 1.0a version of OAuth.  Make it blank for now.
        """
        self.oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                       token=token,
                                        http_url=self.client.access_token_url,
                                        verifier=verifier)
        self.oauth_request.sign_request(self.signature_method_hmac_sha1, self.consumer, token)

        token = self.client.fetch_access_token(self.oauth_request)

        return token

    def obtain_trusted_access_token(self, user_name, user_password):
        """
        This is for trusted partners using a constrained device such as a mobile
        or other embedded system.  It allows them to use the user's password
        directly to obtain an access token, rather than going through all the
        usual OAuth steps.
        """
        assert user_name, "The user name is required."
        assert user_password, "The user password is required."
        assert self.trusted_access_token_url, "You must set trusted_access_token_url in your config file."
        parameters = {'email': user_name, 'password': user_password}
        params = urllib.urlencode(parameters)
        assert params, "Didn't get a valid params."

        url = self.trusted_access_token_url + "?" + params
        self.oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, http_url=url, parameters=parameters)
        self.oauth_request.sign_request(self.signature_method_hmac_sha1,
                                        self.consumer, None)
        token = self.client.fetch_access_token(self.oauth_request, url)
        return token

    def build_access_headers(self, method, token, resource_url, parameters, callback=None):
        """
        This is used internally to build all the required OAuth parameters and
        signatures to make an OAuth request.  It's provided for debugging
        purposes.
        """
        params = parameters.copy()

        if callback:
            params['oauth_callback'] = callback

        self.oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, 
                                    token=token, http_method=method,
                                    http_url=resource_url,
                                                                        parameters=parameters)

        self.oauth_request.sign_request(self.signature_method_hmac_sha1, self.consumer, token)
        return self.oauth_request.to_header(), params


########NEW FILE########
__FILENAME__ = client
"""
The main client API you'll be working with most often.  You'll need to
configure a dropbox.client.Authenticator for this to work, but otherwise
it's fairly self-explanatory.
"""

import rest
import urllib
import urllib2
import poster
import httplib

API_VERSION=0
HASH_BLOCK_SIZE=10*1024

class DropboxClient(object):
    """
    The main access point of doing REST calls on Dropbox.  You use it
    by first creating and configuring a dropbox.auth.Authenticator,
    and then configuring a DropboxClient to talk to the service.  The
    DropboxClient then does all the work of properly calling each API
    with the correct OAuth authentication.
    """


    def __init__(self, api_host, content_host, port, auth, token):
        """
        The api_host and content_host are normally 'api.dropbox.com' and
        'api-content.dropbox.com' and will use the same port.
        The auth is a dropbox.client.Authenticator that is properly configured.
        The token is a valid OAuth `access token` that you got using
        dropbox.client.Authenticator.obtain_access_token.
        """
        self.api_rest = rest.RESTClient(api_host, port)
        self.content_rest = rest.RESTClient(content_host, port)
        self.auth = auth
        self.token = token
        self.api_host = api_host
        self.content_host = content_host
        self.api_host = api_host
        self.port = int(port)


    def request(self, host, method, target, params, callback):
        """
        This is an internal method used to properly craft the url, headers, and
        params for a Dropbox API request.  It is exposed for you in case you
        need craft other API calls not in this library or you want to debug it.

        It is only expected to work for GET or POST parameters.
        """
        assert method in ['GET','POST'], "Only 'GET' and 'POST' are allowed for method."

        base = self.build_full_url(host, target)
        headers, params = self.auth.build_access_headers(method, self.token, base, params, callback)

        if method == "GET":
            url = self.build_url(target, params)
        else:
            url = self.build_url(target)

        return url, headers, params


    def account_info(self, status_in_response=False, callback=None):
        """
        Retrieve information about the user's account.

        * callback. Optional. The server will wrap its response of format inside a call to the argument specified by callback. Value must contains only alphanumeric characters and underscores.
        * status_in_response. Optional. Some clients (e.g., Flash) cannot handle HTTP status codes well. If this parameter is set to true, the service will always return a 200 status and report the relevant status code via additional information in the response body. Default is false.
        """

        params = {'status_in_response': status_in_response}

        url, headers, params = self.request(self.api_host, "GET", "/account/info", params, callback)

        return self.api_rest.GET(url, headers)


    def put_file(self, root, to_path, file_obj):
        """
        Retrieve or upload file contents relative to the user's Dropbox root or
        the application's sandbox directory within the user's Dropbox.

        * root is one of "dropbox" or "sandbox", most clients will use "sandbox".
        * to_path is the `directory` path to put the file (NOT the full path).
        * file_obj is an open and ready to read file object that will be uploaded.

        The filename is taken from the file_obj name currently, so you can't
        have the local file named differently than it's target name.  This may
        change in future versions.

        Finally, this function is not terribly efficient due to Python's
        HTTPConnection requiring all of the file be read into ram for the POST.
        Future versions will avoid this problem.
        """
        assert root in ["dropbox", "sandbox"]

        path = "/files/%s%s" % (root, to_path)

        params = { "file" : file_obj.name, }

        url, headers, params = self.request(self.content_host, "POST", path, params, None)

        params['file'] = file_obj
        data, mp_headers = poster.encode.multipart_encode(params)
        if 'Content-Length' in mp_headers:
            mp_headers['Content-Length'] = str(mp_headers['Content-Length'])
        headers.update(mp_headers)

        conn = httplib.HTTPConnection(self.content_host, self.port)
        conn.request("POST", url, "".join(data), headers)

        resp = rest.RESTResponse(conn.getresponse())
        conn.close()
        file_obj.close()

        return resp


    def get_file(self, root, from_path):
        """
        Retrieves a file from the given root ("dropbox" or "sandbox") based on
        from_path as the `full path` to the file.  Unlike the other calls, this
        one returns a raw HTTPResponse with the connection open.  You should
        do your read and any processing you need and then close it.
        """
        assert root in ["dropbox", "sandbox"]

        path = "/files/%s%s" % (root, from_path)

        url, headers, params = self.request(self.content_host, "GET", path, {}, None)
        return self.content_rest.request("GET", url, headers=headers, raw_response=True)


    def file_copy(self, root, from_path, to_path, callback=None):
        """
        Copy a file or folder to a new location.

        * callback. Optional. The server will wrap its response of format inside a call to the argument specified by callback. Value must contains only alphanumeric characters and underscores.
        * from_path. Required. from_path specifies either a file or folder to be copied to the location specified by to_path. This path is interpreted relative to the location specified by root.
        * root. Required. Specify the root relative to which from_path and to_path are specified. Valid values are dropbox and sandbox.
        * to_path. Required. to_path specifies the destination path including the new name for file or folder. This path is interpreted relative to the location specified by root.
        """
        assert root in ["dropbox", "sandbox"]

        params = {'root': root, 'from_path': from_path, 'to_path': to_path}

        url, headers, params = self.request(self.api_host, "POST", "/fileops/copy", params, callback)

        return self.api_rest.POST(url, params, headers)


    def file_create_folder(self, root, path, callback=None):
        """
        Create a folder relative to the user's Dropbox root or the user's application sandbox folder.

        * callback. Optional. The server will wrap its response of format inside a call to the argument specified by callback. Value must contains only alphanumeric characters and underscores.
        * path. Required. The path to the new folder to create, relative to root.
        * root. Required. Specify the root relative to which path is specified. Valid values are dropbox and sandbox.
        """
        assert root in ["dropbox", "sandbox"]
        params = {'root': root, 'path': path}

        url, headers, params = self.request(self.api_host, "POST", "/fileops/create_folder", params, callback)

        return self.api_rest.POST(url, params, headers)


    def file_delete(self, root, path, callback=None):
        """
        Delete a file or folder.

        * callback. Optional. The server will wrap its response of format inside a call to the argument specified by callback. Value must contains only alphanumeric characters and underscores.
        * path. Required. path specifies either a file or folder to be deleted. This path is interpreted relative to the location specified by root.
        * root. Required. Specify the root relative to which path is specified. Valid values are dropbox and sandbox.
        """
        assert root in ["dropbox", "sandbox"]

        params = {'root': root, 'path': path}

        url, headers, params = self.request(self.api_host, "POST", "/fileops/delete", params,
                                           callback)

        return self.api_rest.POST(url, params, headers)


    def file_move(self, root, from_path, to_path, callback=None):
        """
        Move a file or folder to a new location.

        * callback. Optional. The server will wrap its response of format inside a call to the argument specified by callback. Value must contains only alphanumeric characters and underscores.
        * from_path. Required. from_path specifies either a file or folder to be copied to the location specified by to_path. This path is interpreted relative to the location specified by root.
        * root. Required. Specify the root relative to which from_path and to_path are specified. Valid values are dropbox and sandbox.
        * to_path. Required. to_path specifies the destination path including the new name for file or folder. This path is interpreted relative to the location specified by root.
        """
        assert root in ["dropbox", "sandbox"]

        params = {'root': root, 'from_path': from_path, 'to_path': to_path}

        url, headers, params = self.request(self.api_host, "POST", "/fileops/move", params, callback)

        return self.api_rest.POST(url, params, headers)


    def metadata(self, root, path, file_limit=10000, hash=None, list=True, status_in_response=False, callback=None):
        """
        The metadata API location provides the ability to retrieve file and
        folder metadata and manipulate the directory structure by moving or
        deleting files and folders.

        * callback. Optional. The server will wrap its response of format inside a call to the argument specified by callback. Value must contains only alphanumeric characters and underscores.
        * file_limit. Optional. Default is 10000. When listing a directory, the service will not report listings containing more than file_limit files and will instead respond with a 406 (Not Acceptable) status response.
        * hash. Optional. Listing return values include a hash representing the state of the directory's contents. If you provide this argument to the metadata call, you give the service an opportunity to respond with a "304 Not Modified" status code instead of a full (potentially very large) directory listing. This argument is ignored if the specified path is associated with a file or if list=false.
        * list. Optional. The strings true and false are valid values. true is the default. If true, this call returns a list of metadata representations for the contents of the directory. If false, this call returns the metadata for the directory itself.
        * status_in_response. Optional. Some clients (e.g., Flash) cannot handle HTTP status codes well. If this parameter is set to true, the service will always return a 200 status and report the relevant status code via additional information in the response body. Default is false.
        """

        assert root in ["dropbox", "sandbox"]

        path = "/metadata/%s%s" % (root, path)

        params = {'file_limit': file_limit,
                  'list': "true" if list else "false",
                  'status_in_response': status_in_response}
        if hash is not None:
            params['hash'] = hash

        url, headers, params = self.request(self.api_host, "GET", path, params, callback)

        return self.api_rest.GET(url, headers)

    def links(self, root, path):
        assert root in ["dropbox", "sandbox"]
        path = "/links/%s%s" % (root, path)
        return self.build_full_url(self.api_host, path)


    def build_url(self, url, params=None):
        """Used internally to build the proper URL from parameters and the API_VERSION."""
        if type(url) == unicode:
            url = url.encode("utf8")
        target_path = urllib2.quote(url)

        if params:
            return "/%d%s?%s" % (API_VERSION, target_path, urllib.urlencode(params))
        else:
            return "/%d%s" % (API_VERSION, target_path)


    def build_full_url(self, host, target):
        """Used internally to construct the complete URL to the service."""
        port = "" if self.port == 80 else ":%d" % self.port
        base_full_url = "http://%s%s" % (host, port)
        return base_full_url + self.build_url(target)


    def account(self, email='', password='', first_name='', last_name='', source=None):
        params = {'email': email, 'password': password,
                  'first_name': first_name, 'last_name': last_name}

        url, headers, params = self.request(self.api_host, "POST", "/account",
                                            params, None)

        return self.api_rest.POST(url, params, headers)


    def thumbnail(self, root, from_path, size='small'):
        assert root in ["dropbox", "sandbox"]
        assert size in ['small','medium','large']

        path = "/thumbnails/%s%s" % (root, from_path)

        url, headers, params = self.request(self.content_host, "GET", path,
                                            {'size': size}, None)
        return self.content_rest.request("GET", url, headers=headers, raw_response=True)


########NEW FILE########
__FILENAME__ = rest
"""
A simple JSON REST request abstraction that is used by the
dropbox.client module.  You shouldn't need to use this directly
unless you're implementing unsupport methods.
"""


import httplib
import urllib
from django.utils import simplejson as json


class RESTClient(object):
    """
    An abstraction on performing JSON REST requests that is used internally
    by the Dropbox Client API.  It provides just enough gear to make requests
    and get responses as JSON data.

    It is not designed well for file u.
    """
    
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def request(self, method, url, post_params=None, headers=None, raw_response=False):
        """
        Given the method and url this will make a JSON REST request to the
        configured self.host:self.port and returns a RESTResponse for you.
        If you pass in a dict for post_params then it will urlencode them
        into the body.  If you give in a headers dict then it will add
        those to the request headers.

        The raw_response parameter determines if you get a RESTResponse or a 
        raw HTTPResponse object.  In some cases, like getting a file, you 
        don't want any JSON decoding or extra processing.  In that case set
        this to True and you'll get a plain HTTPResponse.
        """
        params = post_params or {}
        headers = headers or {}

        if params:
            body = urllib.urlencode(params)
        else:
            body = None

        if body:
            headers["Content-type"] = "application/x-www-form-urlencoded"

        conn = httplib.HTTPConnection(self.host, self.port)
        conn.request(method, url, body, headers)

        if raw_response:
            return conn.getresponse()
        else:
            resp = RESTResponse(conn.getresponse())
            conn.close()

        return resp

    def GET(self, url, headers=None):
        """Convenience method that just does a GET request."""
        return self.request("GET", url, headers=headers)

    def POST(self, url, params, headers=None):
        """Convenience method that just does a POST request."""
        return self.request("POST", url, post_params=params, headers=headers)


class RESTResponse(object):
    """
    Returned by dropbox.rest.RESTClient wrapping the base http response
    object to make it more convenient.  It contains the attributes
    http_response, status, reason, body, headers.  If the body can
    be parsed into json, then you get a data attribute too, otherwise
    it's set to None.
    """
    
    def __init__(self, http_resp):
        self.http_response = http_resp
        self.status = http_resp.status
        self.reason = http_resp.reason
        self.body = http_resp.read()
        self.headers = dict(http_resp.getheaders())

        try:
            self.data = json.loads(self.body)
        except ValueError:
            # looks like this isn't json, data is None
            self.data = None




########NEW FILE########
__FILENAME__ = handlers
from google.appengine.ext import webapp

import settings

from dropbox import auth as dropbox_auth
from instadrop.models import Profile
from lilcookies import LilCookies


class DropboxAuth(webapp.RequestHandler):
    def get(self):
        cookieutil = LilCookies(self, settings.COOKIE_SECRET)
        ig_user_id = cookieutil.get_secure_cookie(name = "ig_user_id")

        dba = dropbox_auth.Authenticator(settings.DROPBOX_CONFIG)
        req_token = dba.obtain_request_token()

        profiles = Profile.all()
        profiles.filter("ig_user_id =", ig_user_id)
        profile = profiles.get()

        if not profile:
            self.redirect("/connect")
            return

        profile.db_oauth_token_key = req_token.key
        profile.db_oauth_token_secret = req_token.secret
        profile.put()

        authorize_url = dba.build_authorize_url(
                req_token,
                callback = settings.DROPBOX_CALLBACK)

        self.redirect(authorize_url)


class DropboxDisconnect(webapp.RequestHandler):
    def get(self):
        cookieutil = LilCookies(self, settings.COOKIE_SECRET)
        ig_user_id = cookieutil.get_secure_cookie(name = "ig_user_id")

        profiles = Profile.all()
        profiles.filter("ig_user_id =", ig_user_id)
        profile = profiles.get()

        if profile:
            profile.db_access_token_key = None
            profile.db_oauth_token_secret = None
            profile.put()

        self.redirect("/")


class DropboxCallback(webapp.RequestHandler):
    def get(self):
        from oauth import oauth

        dba = dropbox_auth.Authenticator(settings.DROPBOX_CONFIG)

        token = self.request.get("oauth_token")
        profile = Profile.all().filter("db_oauth_token_key =", token).get()

        if not profile:
            self.redirect("/connect")
            return

        oauth_token = oauth.OAuthToken(
                                       key = profile.db_oauth_token_key,
                                       secret = profile.db_oauth_token_secret)

        verifier = settings.DROPBOX_CONFIG['verifier']
        access_token = dba.obtain_access_token(oauth_token, verifier)

        profile.db_access_token_key = access_token.key
        profile.db_access_token_secret = access_token.secret
        profile.put()

        self.redirect("/connect")
########NEW FILE########
__FILENAME__ = helper
def load_config(config_file):
    from dropbox import auth
    return auth.Authenticator.load_config(config_file)


def authenticated_client(profile):
    import settings
    from dropbox import auth
    from dropbox.client import DropboxClient
    from oauth import oauth

    dba = auth.Authenticator(settings.DROPBOX_CONFIG)

    access_token = oauth.OAuthToken(
            key = profile.db_access_token_key,
            secret = profile.db_access_token_secret)

    client = DropboxClient(
        settings.DROPBOX_CONFIG['server'],
        settings.DROPBOX_CONFIG['content_server'],
        settings.DROPBOX_CONFIG['port'],
        dba,
        access_token)

    return client
########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri
        
if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [ 
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))
            
        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()

    

########NEW FILE########
__FILENAME__ = handlers
from google.appengine.ext import webapp

import settings

from lilcookies import LilCookies
from instadrop.models import Profile


class WelcomeHandler(webapp.RequestHandler):
    def get(self):
        cookieutil = LilCookies(self, settings.COOKIE_SECRET)
        ig_user_id = cookieutil.get_secure_cookie(name = "ig_user_id")

        profiles = Profile.all()
        profiles.filter("ig_user_id =", ig_user_id)
        profile = profiles.get()

        if profile and profile.fully_connected():
            self.render_template("connected.html")
        else:
            self.render_template("not_connected.html", {
                "profile": profile,
                "client_id": settings.INSTAGRAM_CONFIG["client_id"]
            })


class ConnectHandler(webapp.RequestHandler):
    def get(self):
        cookieutil = LilCookies(self, settings.COOKIE_SECRET)
        ig_user_id = cookieutil.get_secure_cookie(name = "ig_user_id")


        profiles = Profile.all()
        profiles.filter("ig_user_id =", ig_user_id)
        profile = profiles.get()

        if profile and profile.db_access_token_key and \
                       profile.db_access_token_secret:
            self.redirect("/")
        elif profile and not (profile.db_access_token_key or
                              profile.db_access_token_secret):
            self.redirect("/dropbox/auth")
        else:
            self.redirect("/instagram/auth")

########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import db


class Profile(db.Model):
    full_name = db.StringProperty()
    ig_user_id = db.StringProperty()
    ig_username = db.StringProperty()
    ig_access_token = db.StringProperty()
    db_oauth_token_key = db.StringProperty()
    db_oauth_token_secret = db.StringProperty()
    db_access_token_key = db.StringProperty()
    db_access_token_secret = db.StringProperty()

    def dropbox_connected(self):
        return (self.db_access_token_key and self.db_access_token_secret)


    def instagram_connected(self):
        return (self.ig_access_token and self.ig_user_id)


    def fully_connected(self):
        return (self.dropbox_connected() and self.instagram_connected())
########NEW FILE########
__FILENAME__ = handlers
from google.appengine.ext import webapp

import settings

from instagram.client import InstagramAPI

from instadrop.models import Profile
from lilcookies import LilCookies


class InstagramAuth(webapp.RequestHandler):
    def get(self):
        api = InstagramAPI(**settings.INSTAGRAM_CONFIG)
        self.redirect(api.get_authorize_url())


class InstagramDisconnect(webapp.RequestHandler):
    def get(self):
        cookieutil = LilCookies(self, settings.COOKIE_SECRET)
        ig_user_id = cookieutil.get_secure_cookie(name = "ig_user_id")

        profiles = Profile.all()
        profiles.filter("ig_user_id =", ig_user_id)
        profile = profiles.get()

        if profile:
            profile.delete()

        self.redirect("/")


class InstagramCallback(webapp.RequestHandler):
    def get(self):
        instagram_client = InstagramAPI(**settings.INSTAGRAM_CONFIG)

        code = self.request.get("code")
        access_token = instagram_client.exchange_code_for_access_token(code)

        instagram_client = InstagramAPI(access_token = access_token)

        user = instagram_client.user("self")

        profiles = Profile.all()
        profiles.filter("ig_user_id = ", user.id)
        profile = (profiles.get() or Profile())

        profile.full_name = (user.full_name or user.username)
        profile.ig_user_id = user.id
        profile.ig_username = user.username
        profile.ig_access_token = access_token
        profile.put()

        cookieutil = LilCookies(self, settings.COOKIE_SECRET)
        cookieutil.set_secure_cookie(
                name = "ig_user_id",
                value = user.id,
                expires_days = 365)

        self.redirect("/connect")

class InstagramLoadUser(webapp.RequestHandler):
    def get(self):
        ig_user_id = self.request.get("ig_user_id")

        if not ig_user_id:
            self.redirect("/connect")

        instagram_client = InstagramAPI(**settings.INSTAGRAM_CONFIG)

        access_token = instagram_client.exchange_user_id_for_access_token(ig_user_id)

        instagram_client = InstagramAPI(access_token = access_token)

        user = instagram_client.user("self")

        profiles = Profile.all()
        profiles.filter("ig_user_id = ", user.id)
        profile = (profiles.get() or Profile())

        profile.full_name = (user.full_name or user.username)
        profile.ig_user_id = user.id
        profile.ig_username = user.username
        profile.ig_access_token = access_token
        profile.put()

        cookieutil = LilCookies(self, settings.COOKIE_SECRET)
        cookieutil.set_secure_cookie(
                name = "ig_user_id",
                value = user.id,
                expires_days = 365)

        self.redirect("/")


class InstagramSubscribe(webapp.RequestHandler):
    def get(self):
        from urllib import urlencode
        from httplib2 import Http

        subscriptions_url = "https://api.instagram.com/v1/subscriptions"

        data = {
            "client_id": settings.INSTAGRAM_CONFIG["client_id"],
            "client_secret": settings.INSTAGRAM_CONFIG["client_secret"],
            "callback_url": settings.INSTAGRAM_PUSH_CALLBACK,
            "aspect": "media",
            "object": "user"
        }

        http_object = Http(timeout = 20)
        response, content = http_object.request(
                subscriptions_url, "POST", urlencode(data))


class InstagramPushCallback(webapp.RequestHandler):
    def get(self):
        challenge = self.request.get("hub.challenge")
        self.response.out.write(challenge)


    def post(self):
        import hashlib
        import hmac
        import logging
        from StringIO import StringIO
        from time import time
        from urllib2 import urlopen
        from django.utils import simplejson
        from dropbox import helper as dropbox_helper

        payload = self.request.body

        # verify payload
        signature = self.request.headers['X-Hub-Signature']
        client_secret = settings.INSTAGRAM_CONFIG['client_secret']
        hashing_obj= hmac.new(client_secret.encode("utf-8"),
            msg = payload.encode("utf-8"),
            digestmod = hashlib.sha1)
        digest = hashing_obj.hexdigest()

        if digest != signature:
            logging.info("Digest and signature differ. (%s, %s)"
                % (digest, signature))
            return

        changes = simplejson.loads(payload)
        for change in changes:
            profiles = Profile.all()
            profiles.filter("ig_user_id =", change['object_id'])
            profile = profiles.get()

            if not profile:
                logging.info("Cannot find profile %s", change['object_id'])
                continue

            instagram_client = InstagramAPI(
                    access_token = profile.ig_access_token)

            media, _ = instagram_client.user_recent_media(count = 1)
            media = media[0]

            media_file = urlopen(media.images['standard_resolution'].url)
            media_data = media_file.read()

            dropbox_file = StringIO(media_data)
            dropbox_file.name = ("%s.jpg" % int(time()))

            dropbox_client = dropbox_helper.authenticated_client(profile)
            dropbox_client.put_file(
                settings.DROPBOX_CONFIG['root'],
                "/Instagram Photos/",
                dropbox_file)

########NEW FILE########
__FILENAME__ = bind
import urllib
from oauth2 import OAuth2Request
import re
import simplejson
re_path_template = re.compile('{\w+}')

def encode_string(value):
    return value.encode('utf-8') \
                        if isinstance(value, unicode) else str(value)

class InstagramClientError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message

    def __str__(self):
        return self.error_message

class InstagramAPIError(Exception):
    
    def __init__(self, status_code, error_type, error_message, *args, **kwargs):
        self.status_code = status_code
        self.error_type = error_type
        self.error_message = error_message

    def __str__(self):
        return "(%s) %s-%s" % (self.status_code, self.error_type, self.error_message)

def bind_method(**config):

    class InstagramAPIMethod(object):

        path = config['path']
        method = config.get('method', 'GET')
        accepts_parameters = config.get("accepts_parameters", [])
        requires_target_user = config.get('requires_target_user', False)
        paginates = config.get('paginates', False)
        root_class = config.get('root_class', None)
        response_type = config.get("response_type", "list")

        def __init__(self, api, *args, **kwargs):
            self.api = api
            self.as_generator = kwargs.pop("as_generator", False)
            self.max_pages = kwargs.pop("max_pages", 3)
            self.parameters = {}
            self._build_parameters(args, kwargs)
            self._build_path() 

        def _build_parameters(self, args, kwargs):
            # via tweepy https://github.com/joshthecoder/tweepy/
            for index, value in enumerate(args):
                if value is None:
                    continue

                try:
                    self.parameters[self.accepts_parameters[index]] = encode_string(value)
                except IndexError:
                    raise InstagramClientError("Too many arguments supplied")

            for key, value in kwargs.iteritems():
                if value is None:
                    continue
                if key in self.parameters:
                    raise InstagramClientError("Parameter %s already supplied" % key)
                self.parameters[key] = encode_string(value)
            if 'user_id' in self.accepts_parameters and not 'user_id' in self.parameters \
               and not self.requires_target_user:
                self.parameters['user_id'] = 'self'

        def _build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                try:
                    value = urllib.quote(self.parameters[name])
                except KeyError:
                    raise Exception('No parameter value found for path variable: %s' % name)
                del self.parameters[name]

                self.path = self.path.replace(variable, value)
            self.path = self.path + '.%s' % self.api.format

        def _do_api_request(self, url, method="GET", body=None, headers={}):
            response, content = OAuth2Request(self.api).make_request(url, method=method, body=body, headers=headers)
            if response['status'] == '503':
                raise InstagramAPIError(response['status'], "Rate limited", "Your client is making too many request per second")
            content_obj = simplejson.loads(content)
            response_objects = []
            status_code = content_obj['meta']['code']
            if status_code == 200:
                if self.response_type == 'list':
                    for entry in content_obj['data']:
                        obj = self.root_class.object_from_dictionary(entry)
                        response_objects.append(obj)
                elif self.response_type == 'entry':
                    response_objects = self.root_class.object_from_dictionary(content_obj['data'])
                return response_objects, content_obj.get('pagination', {}).get('next_url') 
            else:
                raise InstagramAPIError(status_code, content_obj['meta']['error_type'], content_obj['meta']['error_message'])

        def _paginator_with_url(self, url, method="GET", body=None, headers={}):
            pages_read = 0
            while url and pages_read < self.max_pages:
                 response_objects, url = self._do_api_request(url, method, body, headers)
                 pages_read += 1
                 yield response_objects, url 
            return

        def execute(self):
            url, method, body, headers = OAuth2Request(self.api).prepare_request(self.method, self.path, self.parameters)
            if self.as_generator:
                return self._paginator_with_url(url, method, body, headers)
            else:
                content, next = self._do_api_request(url, method, body, headers)
            if self.paginates:
                return content, next
            else:
                return content


    def _call(api, *args, **kwargs):
        method = InstagramAPIMethod(api, *args, **kwargs)
        return method.execute()

    return _call

########NEW FILE########
__FILENAME__ = client
import oauth2
from bind import bind_method
from models import Media, User, Location, Tag, Comment, Relationship

MEDIA_ACCEPT_PARAMETERS = ["count", "max_id"]
SEARCH_ACCEPT_PARAMETERS = ["q", "count"]

SUPPORTED_FORMATS = ['json']

class InstagramAPI(oauth2.OAuth2API):
        
    host = "api.instagram.com"
    base_path = "/v1"
    access_token_field = "access_token"
    authorize_url = "https://api.instagram.com/oauth/authorize"
    access_token_url = "https://api.instagram.com/oauth/access_token"
    protocol = "https"
    api_name = "Instagram"

    def __init__(self, *args, **kwargs):
        format = kwargs.get('format', 'json')
        if format in SUPPORTED_FORMATS:
            self.format = format
        else:
            raise Exception("Unsupported format")
        super(InstagramAPI, self).__init__(*args, **kwargs)


    media_popular = bind_method(
                path = "/media/popular",
                accepts_parameters = MEDIA_ACCEPT_PARAMETERS,
                root_class = Media)

    media_search = bind_method(
                path = "/media/search",
                accepts_parameters = SEARCH_ACCEPT_PARAMETERS + ['lat', 'lng', 'min_timestamp', 'max_timestamp'],
                root_class = Media)
    
    media_likes = bind_method(
                path = "/media/{media_id}/likes",
                accepts_parameters = ['media_id'],
                root_class = User)

    like_media = bind_method(
                path = "/media/{media_id}/likes",
                method = "POST",
                accepts_parameters = ['media_id'],
                response_type = "empty")

    unlike_media = bind_method(
                path = "/media/{media_id}/likes",
                method = "DELETE",
                accepts_parameters = ['media_id'],
                response_type = "empty")

    create_media_comment = bind_method(
                path = "/media/{media_id}/comments",
                method = "POST",
                accepts_parameters = ['media_id', 'text'],
                response_type = "entry",
                root_class = Comment)

    delete_comment = bind_method(
                path = "/media/{media_id}/comments/{comment_id}",
                method = "DELETE",
                accepts_parameters = ['media_id', 'comment_id'],
                response_type = "empty")

    media_comments = bind_method(
                path = "/media/{media_id}/comments",
                method = "GET",
                accepts_parameters = ['media_id'],
                response_type = "list",
                root_class = Comment)

    media = bind_method(
                path = "/media/{media_id}",
                accepts_parameters = ['media_id'],
                response_type = "entry", 
                root_class = Media)

    user_media_feed = bind_method(
                path = "/users/self/feed",
                accepts_parameters = MEDIA_ACCEPT_PARAMETERS,
                root_class = Media,
                paginates = True)

    user_recent_media = bind_method(
                path = "/users/{user_id}/media/recent",
                accepts_parameters = MEDIA_ACCEPT_PARAMETERS + ['user_id'],
                root_class = Media,
                paginates = True)

    user_search = bind_method(
                path = "/users/search",
                accepts_parameters = SEARCH_ACCEPT_PARAMETERS,
                root_class = User)

    user_follows = bind_method(
                path = "/users/{user_id}/follows/users",
                accepts_parameters = ["user_id"],
                root_class = User)

    user_followed_by = bind_method(
                path = "/users/{user_id}/followed-by/users",
                accepts_parameters = ["user_id"],
                root_class = User)

    user = bind_method(
                path = "/users/{user_id}",
                accepts_parameters = ["user_id"],
                root_class = User,
                response_type = "entry")
    
    location_recent_media = bind_method(
                path = "/locations/{location_id}/media/recent",
                accepts_parameters = MEDIA_ACCEPT_PARAMETERS + ['location_id'],
                root_class = Media,
                paginates = True)

    location_search = bind_method(
                path = "/locations/search",
                accepts_parameters = SEARCH_ACCEPT_PARAMETERS + ['lat', 'lng', 'foursquare_id'],
                root_class = Location)

    location = bind_method(
                path = "/locations/{location_id}",
                accepts_parameters = ["location_id"],
                root_class = Location,
                response_type = "entry")

    tag_recent_media = bind_method(
                path = "/tags/{tag_name}/media/recent",
                accepts_parameters = MEDIA_ACCEPT_PARAMETERS + ['tag_name'],
                root_class = Media,
                paginates = True)

    tag_search = bind_method(
                path = "/tags/search",
                accepts_parameters = SEARCH_ACCEPT_PARAMETERS,
                root_class = Tag,
                paginates = True)

    tag = bind_method(
                path = "/tags/{tag_name}",
                accepts_parameters = ["tag_name"],
                root_class = Tag,
                response_type = "entry")

    user_follows = bind_method(
                path = "/users/self/follows",
                root_class = User,
                paginates = True)

    user_followed_by = bind_method(
                path = "/users/self/followed-by",
                root_class = User,
                paginates = True)

    user_incoming_requests = bind_method(
                path = "/users/self/requested-by",
                root_class = User)

    change_user_relationship = bind_method(
                path = "/users/{user_id}/relationship",
                root_class = Relationship,
                accepts_parameters = ["user_id", "action"],
                paginates = True,
                requires_target_user = True,
                response_type = "entry")

    def _make_relationship_shortcut(action):
        def _inner(self, *args, **kwargs):
            return self.change_user_relationship(user_id=kwargs.get("user_id"),
                                                 action=action)
        return _inner

    follow_user = _make_relationship_shortcut('follow')
    unfollow_user = _make_relationship_shortcut('unfollow')
    block_user = _make_relationship_shortcut('block')
    unblock_user = _make_relationship_shortcut('unblock')
    approve_user_request = _make_relationship_shortcut('approve')
    ignore_user_request = _make_relationship_shortcut('ignore')

########NEW FILE########
__FILENAME__ = helper
from datetime import datetime

def timestamp_to_datetime(ts):
    return datetime.utcfromtimestamp(float(ts))

########NEW FILE########
__FILENAME__ = models
from helper import timestamp_to_datetime

class ApiModel(object):

    @classmethod
    def object_from_dictionary(cls, entry):
        # make dict keys all strings
        entry_str_dict = dict([(str(key), value) for key,value in entry.items()])
        return cls(**entry_str_dict)

class Image(ApiModel):

    def __init__(self, url, width, height):
        self.url = url
        self.height = height
        self.width = width

class Media(ApiModel):

    def __init__(self, id=None, **kwargs):
        self.id = id
        for key,value in kwargs.iteritems():
            setattr(self, key, value)

    def get_standard_resolution_url(self):
        return self.images['standard_resolution'].url

    @classmethod
    def object_from_dictionary(cls, entry):
        new_media = Media(id=entry['id'])

        new_media.user = User.object_from_dictionary(entry['user'])
        new_media.images = {}
        for version,version_info in entry['images'].iteritems():
            new_media.images[version] = Image.object_from_dictionary(version_info)

        if 'user_has_liked' in entry:
            new_media.user_has_liked = entry['user_has_liked']
        new_media.like_count = entry['likes']['count']

        new_media.comment_count = entry['comments']['count']
        new_media.comments = []
        for comment in entry['comments']['data']:
            new_media.comments.append(Comment.object_from_dictionary(comment))

        new_media.created_time = timestamp_to_datetime(entry['created_time'])

        if entry['location']:
            new_media.location = Location.object_from_dictionary(entry['location'])

        new_media.link = entry['link']

        return new_media

class Tag(ApiModel):
    def __init__(self, name, **kwargs):
        self.name = name
        for key,value in kwargs.iteritems():
            setattr(self, key, value)

    def __str__(self):
        return "Tag %s" % self.name

class Comment(ApiModel):
    def __init__(self, *args, **kwargs):
        for key,value in kwargs.iteritems():
            setattr(self, key, value)

    @classmethod
    def object_from_dictionary(cls, entry):
        user = User.object_from_dictionary(entry['from'])
        text = entry['text']
        created_at = timestamp_to_datetime(entry['created_time'])
        id = entry['id']
        return Comment(id=id, user=user, text=text, created_at=created_at)

    def __unicode__(self):
        print "%s said \"%s\"" % (self.user.username, self.message)

class Point(ApiModel):
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

class Location(ApiModel):
    def __init__(self, id, *args, **kwargs):
        self.id = id
        for key,value in kwargs.iteritems():
            setattr(self, key, value)

    @classmethod
    def object_from_dictionary(cls, entry):
        point = None
        if entry['latitude']:
            point = Point(entry['latitude'],
                          entry['longitude'])
        location = cls(entry['id'],
                       point,
                       name=entry['name'])
        return location

class User(ApiModel):

    def __init__(self, id, *args, **kwargs):
        self.id = id
        for key,value in kwargs.iteritems():
            setattr(self, key, value)

    def __str__(self):
        return "User %s" % self.username

class Relationship(ApiModel):

    def __init__(self, incoming_status="none", outgoing_status="none"):
        self.incoming_status = incoming_status
        self.outgoing_status = outgoing_status



########NEW FILE########
__FILENAME__ = oauth2
import simplejson
import urllib
from httplib2 import Http
import mimetypes


class OAuth2AuthExchangeError(Exception):
    def __init__(self, description):
        self.description = description

    def __str__(self):
        return self.description

class OAuth2API(object):
    host = None
    base_path = None
    authorize_url = None
    access_token_url = None
    redirect_uri = None
    # some providers use "oauth_token"
    access_token_field = "access_token"
    protocol = "https"
    # override with 'Instagram', etc
    api_name = "Generic API"

    def __init__(self, client_id=None, client_secret=None, access_token=None, redirect_uri=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.redirect_uri = redirect_uri

    def get_authorize_url(self, scope=None):
        req = OAuth2AuthExchangeRequest(self)
        return req.get_authorize_url(scope = scope)

    def get_authorize_login_url(self, scope=None):
        """ scope should be a tuple or list of requested scope access levels """
        req = OAuth2AuthExchangeRequest(self)
        return req.get_authorize_login_url(scope = scope)

    def exchange_code_for_access_token(self, code):
        req = OAuth2AuthExchangeRequest(self)
        return req.exchange_for_access_token(code = code)

    def exchange_user_id_for_access_token(self, user_id):
        req = OAuth2AuthExchangeRequest(self)
        return req.exchange_for_access_token(user_id = user_id)

    def exchange_xauth_login_for_access_token(self, username, password, scope=None):
        """ scope should be a tuple or list of requested scope access levels """
        req = OAuth2AuthExchangeRequest(self)
        return req.exchange_for_access_token(username = username, password = password,
                                             scope = scope)

class OAuth2AuthExchangeRequest(object):
    def __init__(self, api):
        self.api = api

    def _url_for_authorize(self, scope=None):
        client_params = {
            "client_id": self.api.client_id,
            "response_type": "code",
            "redirect_uri": self.api.redirect_uri
        }
        if scope:
            client_params.update(scope = ' '.join(scope))
        url_params = urllib.urlencode(client_params)
        return "%s?%s" % (self.api.authorize_url, url_params)

    def _data_for_exchange(self, code=None, username=None, password=None, scope=None, user_id=None):
        client_params = {
            "client_id": self.api.client_id,
            "client_secret": self.api.client_secret,
            "redirect_uri": self.api.redirect_uri,
            "grant_type": "authorization_code"
        }
        if code:
            client_params.update(code=code)
        elif username and password:
            client_params.update(username = username,
                                 password = password,
                                 grant_type = "password")
            if scope:
                client_params.update(scope = ' '.join(scope))
        elif user_id:
            client_params.update(user_id = user_id)
        return urllib.urlencode(client_params)

    def get_authorize_url(self, scope=None):
        return self._url_for_authorize(scope = scope)

    def get_authorize_login_url(self, scope=None):
        http_object = Http()

        url = self._url_for_authorize(scope = scope)
        response, content = http_object.request(url)
        if response['status'] != '200':
            raise OAuth2AuthExchangeError("The server returned a non-200 response for URL %s" % url)
        redirected_to = response['content-location']
        return redirected_to

    def exchange_for_access_token(self, code=None, username=None, password=None, scope=None, user_id=None):
        data = self._data_for_exchange(code, username, password, scope = scope, user_id = user_id)
        http_object = Http()
        url = self.api.access_token_url
        response, content = http_object.request(url, method="POST", body=data)
        parsed_content = simplejson.loads(content)
        if int(response['status']) != 200:
            raise OAuth2AuthExchangeError(parsed_content.get("message", ""))
        return parsed_content['access_token']


class OAuth2Request(object):
    def __init__(self, api):
        self.api = api

    def url_for_get(self, path, parameters):
        return self._full_url_with_params(path, parameters)

    def get_request(self, path, **kwargs):
        return self.make_request(self.prepare_request("GET", path, kwargs))

    def post_request(self, path, **kwargs):
        return self.make_request(self.prepare_request("POST", path, kwargs))

    def _full_url(self, path):
        return "%s://%s%s%s%s" % (self.api.protocol, self.api.host, self.api.base_path, path, self._auth_query())

    def _full_url_with_params(self, path, params):
        return (self._full_url(path) + self._full_query_with_params(params))

    def _full_query_with_params(self, params):
        params = ("&" + urllib.urlencode(params)) if params else ""
        return params

    def _auth_query(self):
        if self.api.access_token:
            return ("?%s=%s" % (self.api.access_token_field, self.api.access_token))
        elif self.api.client_id:
            return ("?client_id=%s" % (self.api.client_id))

    def _post_body(self, params):
        return urllib.urlencode(params)

    def _encode_multipart(params, files):
        boundary = "MuL7Ip4rt80uND4rYF0o"

        def get_content_type(file_name):
            return mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        def encode_field(field_name):
            return ("--" + boundary,
                    'Content-Disposition: form-data; name="%s"' % (field_name),
                    "", str(params[field_name]))

        def encode_file(field_name):
            file_name, file_handle = files[field_name]
            return ("--" + boundary,
                    'Content-Disposition: form-data; name="%s"; filename="%s"' % (field_name, file_name),
                    "Content-Type: " + get_content_type(file_name),
                    "", file_handle.read())

        lines = []
        for field in params:
            lines.extend(encode_field(field))
        for field in files:
            lines.extend(encode_file(field))
        lines.extend(("--%s--" % (boundary), ""))
        body = "\r\n".join (lines)

        headers = {"Content-Type": "multipart/form-data; boundary=" + boundary,
                   "Content-Length": str(len(body))}

        return body, headers

    def prepare_request(self, method, path, params):
        url = body = None
        headers = {}

        if not params.get('files'):
            if method == "POST":
                body = self._post_body(params)
                headers = {'Content-type': 'application/x-www-form-urlencoded'}
                url = self._full_url(path)
            else:
                url = self._full_url_with_params(path, params)
        else:
            body, headers = encode_multipart(params, params['files'])
            url = self._full_url(path)

        return url, method, body, headers

    def make_request(self, url, method="GET", body=None, headers={}):
        if not 'User-Agent' in headers:
            headers.update({"User-Agent":"%s Python Client" % self.api.api_name})
        http_obj = Http()
        return http_obj.request(url, method, body=body, headers=headers)

########NEW FILE########
__FILENAME__ = lilcookies
import Cookie
import datetime
import time
import email.utils
import calendar
import base64
import hashlib
import hmac
import re
import logging

# Ripped from the Tornado Framework's web.py
# http://github.com/facebook/tornado/commit/39ac6d169a36a54bb1f6b9bf1fdebb5c9da96e09
#
# Example: 
# from vendor.prayls.lilcookies import LilCookies
# cookieutil = LilCookies(self, application_settings['cookie_secret'])
# cookieutil.set_secure_cookie(name = 'mykey', value = 'myvalue', expires_days= 365*100)
# cookieutil.get_secure_cookie(name = 'mykey')
class LilCookies:

  @staticmethod
  def _utf8(s):
    if isinstance(s, unicode):
      return s.encode("utf-8")
    assert isinstance(s, str)
    return s

  @staticmethod
  def _time_independent_equals(a, b):
    if len(a) != len(b):
      return False
    result = 0
    for x, y in zip(a, b):
      result |= ord(x) ^ ord(y)
    return result == 0

  @staticmethod
  def _signature_from_secret(cookie_secret, *parts):
    """ Takes a secret salt value to create a signature for values in the `parts` param."""
    hash = hmac.new(cookie_secret, digestmod=hashlib.sha1)
    for part in parts: hash.update(part)
    return hash.hexdigest()

  @staticmethod
  def _signed_cookie_value(cookie_secret, name, value):
    """ Returns a signed value for use in a cookie.  
    
    This is helpful to have in its own method if you need to re-use this function for other needs. """
    timestamp = str(int(time.time()))
    value = base64.b64encode(value)
    signature = LilCookies._signature_from_secret(cookie_secret, name, value, timestamp)
    return "|".join([value, timestamp, signature])

  @staticmethod
  def _verified_cookie_value(cookie_secret, name, signed_value):
    """Returns the un-encrypted value given the signed value if it validates, or None."""
    value = signed_value
    if not value: return None
    parts = value.split("|")
    if len(parts) != 3: return None
    signature = LilCookies._signature_from_secret(cookie_secret, name, parts[0], parts[1])
    if not LilCookies._time_independent_equals(parts[2], signature):
      logging.warning("Invalid cookie signature %r", value)
      return None
    timestamp = int(parts[1])
    if timestamp < time.time() - 31 * 86400:
      logging.warning("Expired cookie %r", value)
      return None
    try:
      return base64.b64decode(parts[0])
    except:
      return None

  def __init__(self, handler, cookie_secret):
    """You must specify the cookie_secret to use any of the secure methods. 
    It should be a long, random sequence of bytes to be used as the HMAC 
    secret for the signature.
    """
    if len(cookie_secret) < 45: 
      raise ValueError("LilCookies cookie_secret should at least be 45 characters long, but got `%s`" % cookie_secret)
    self.handler = handler
    self.request = handler.request
    self.response = handler.response
    self.cookie_secret = cookie_secret
  
  def cookies(self):
    """A dictionary of Cookie.Morsel objects."""
    if not hasattr(self, "_cookies"):
      self._cookies = Cookie.BaseCookie()
      if "Cookie" in self.request.headers:
        try:
          self._cookies.load(self.request.headers["Cookie"])
        except:
          self.clear_all_cookies()
    return self._cookies

  def get_cookie(self, name, default=None):
    """Gets the value of the cookie with the given name, else default."""
    if name in self.cookies():
      return self._cookies[name].value
    return default

  def set_cookie(self, name, value, domain=None, expires=None, path="/",
           expires_days=None, **kwargs):
    """Sets the given cookie name/value with the given options.

    Additional keyword arguments are set on the Cookie.Morsel
    directly.
    See http://docs.python.org/library/cookie.html#morsel-objects
    for available attributes.
    """
    name = LilCookies._utf8(name)
    value = LilCookies._utf8(value)
    if re.search(r"[\x00-\x20]", name + value):
      # Don't let us accidentally inject bad stuff
      raise ValueError("Invalid cookie %r: %r" % (name, value))
    if not hasattr(self, "_new_cookies"):
      self._new_cookies = []
    new_cookie = Cookie.BaseCookie()
    self._new_cookies.append(new_cookie)
    new_cookie[name] = value
    if domain:
      new_cookie[name]["domain"] = domain
    if expires_days is not None and not expires:
      expires = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)
    if expires:
      timestamp = calendar.timegm(expires.utctimetuple())
      new_cookie[name]["expires"] = email.utils.formatdate(
        timestamp, localtime=False, usegmt=True)
    if path:
      new_cookie[name]["path"] = path
    for k, v in kwargs.iteritems():
      new_cookie[name][k] = v
    
    # The 2 lines below were not in Tornado.  Instead, they output all their cookies to the headers at once before a response flush.
    for vals in new_cookie.values():
      self.response.headers._headers.append(('Set-Cookie', vals.OutputString(None)))

  def clear_cookie(self, name, path="/", domain=None):
    """Deletes the cookie with the given name."""
    expires = datetime.datetime.utcnow() - datetime.timedelta(days=365)
    self.set_cookie(name, value="", path=path, expires=expires,
            domain=domain)

  def clear_all_cookies(self):
    """Deletes all the cookies the user sent with this request."""
    for name in self.cookies().iterkeys():
      self.clear_cookie(name)

  def set_secure_cookie(self, name, value, expires_days=30, **kwargs):
    """Signs and timestamps a cookie so it cannot be forged.

    To read a cookie set with this method, use get_secure_cookie().
    """
    value = LilCookies._signed_cookie_value(self.cookie_secret, name, value)
    self.set_cookie(name, value, expires_days=expires_days, **kwargs)

  def get_secure_cookie(self, name, value=None):
    """Returns the given signed cookie if it validates, or None."""
    if value is None: value = self.get_cookie(name)
    return LilCookies._verified_cookie_value(self.cookie_secret, name, value)

  def _cookie_signature(self, *parts):
    return LilCookies._signature_from_secret(self.cookie_secret)

########NEW FILE########
__FILENAME__ = main
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app


from google.appengine.dist import use_library
use_library('django', '0.96')


from instadrop.handlers import WelcomeHandler, ConnectHandler
from instagram.handlers import (InstagramAuth, InstagramCallback, \
                                InstagramSubscribe, InstagramPushCallback, \
                                InstagramDisconnect, InstagramLoadUser)
from dropbox.handlers import DropboxAuth, DropboxCallback, DropboxDisconnect


from patches import webapp_patches # TODO make this better/automated


application = webapp.WSGIApplication([
    ("/", WelcomeHandler),
    ("/connect", ConnectHandler),
    ("/instagram/auth", InstagramAuth),
    ("/instagram/callback", InstagramCallback),
    ("/instagram/subscribe", InstagramSubscribe),
    ("/instagram/push_callback", InstagramPushCallback),
    ("/instagram/disconnect", InstagramDisconnect),
    ("/instagram/load_user", InstagramLoadUser),
    ("/dropbox/auth", DropboxAuth),
    ("/dropbox/callback", DropboxCallback),
    ("/dropbox/disconnect", DropboxDisconnect)], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
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
__FILENAME__ = webapp_patches
import os
import inspect
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template


def _render_template(self, template_path, context={}):
    path = os.path.join(os.path.dirname(
        inspect.getfile(self.__class__)),
        "templates/" + template_path)
    self.response.out.write(template.render(path, context))
webapp.RequestHandler.render_template = _render_template

########NEW FILE########
__FILENAME__ = encode
"""multipart/form-data encoding module

This module provides functions that faciliate encoding name/value pairs
as multipart/form-data suitable for a HTTP POST or PUT request.

multipart/form-data is the standard way to upload files over HTTP"""

__all__ = ['gen_boundary', 'encode_and_quote', 'MultipartParam',
        'encode_string', 'encode_file_header', 'get_body_size', 'get_headers',
        'multipart_encode']

try:
    import uuid
    def gen_boundary():
        """Returns a random string to use as the boundary for a message"""
        return uuid.uuid4().hex
except ImportError:
    import random, sha
    def gen_boundary():
        """Returns a random string to use as the boundary for a message"""
        bits = random.getrandbits(160)
        return sha.new(str(bits)).hexdigest()

import urllib, re, os, mimetypes

def encode_and_quote(data):
    """If ``data`` is unicode, return urllib.quote_plus(data.encode("utf-8"))
    otherwise return urllib.quote_plus(data)"""
    if data is None:
        return None

    if isinstance(data, unicode):
        data = data.encode("utf-8")
    return urllib.quote_plus(data)

class MultipartParam(object):
    """Represents a single parameter in a multipart/form-data request

    ``name`` is the name of this parameter.

    If ``value`` is set, it must be a string or unicode object to use as the
    data for this parameter.

    If ``filename`` is set, it is what to say that this parameter's filename
    is.  Note that this does not have to be the actual filename any local file.

    If ``filetype`` is set, it is used as the Content-Type for this parameter.
    If unset it defaults to "text/plain; charset=utf8"

    If ``filesize`` is set, it specifies the length of the file ``fileobj``

    If ``fileobj`` is set, it must be a file-like object that supports
    .read().

    Both ``value`` and ``fileobj`` must not be set, doing so will
    raise a ValueError assertion.

    If ``fileobj`` is set, and ``filesize`` is not specified, then
    the file's size will be determined first by stat'ing ``fileobj``'s
    file descriptor, and if that fails, by seeking to the end of the file,
    recording the current position as the size, and then by seeking back to the
    beginning of the file.
    """
    def __init__(self, name, value=None, filename=None, filetype=None,
                        filesize=None, fileobj=None):
        self.name = encode_and_quote(name)
        if value is None:
            self.value = None
        else:
            if isinstance(value, unicode):
                self.value = value.encode("utf-8")
            else:
                self.value = str(value)
        if filename is None:
            self.filename = None
        else:
            if isinstance(filename, unicode):
                self.filename = filename.encode("utf-8").encode("string_escape").replace('"', '\\"')
            else:
                self.filename = filename.encode("string_escape").replace('"', '\\"')

        if filetype is None:
            self.filetype = None
        elif isinstance(filetype, unicode):
            self.filetype = filetype.encode("utf-8")
        else:
            self.filetype = str(filetype)
        self.filesize = filesize
        self.fileobj = fileobj

        if self.value is not None and self.fileobj is not None:
            raise ValueError("Only one of value or fileobj may be specified")

        if fileobj is not None and filesize is None:
            # Try and determine the file size
            try:
                self.filesize = os.fstat(fileobj.fileno()).st_size
            except (OSError, AttributeError):
                try:
                    fileobj.seek(0, 2)
                    self.filesize = fileobj.tell()
                    fileobj.seek(0)
                except:
                    raise ValueError("Could not determine filesize")

    def __cmp__(self, o):
        attrs = ['name', 'value', 'filename', 'filetype', 'filesize', 'fileobj']
        myattrs = [getattr(self, a) for a in attrs]
        oattrs = [getattr(o, a) for a in attrs]
        return cmp(myattrs, oattrs)

    @classmethod
    def from_file(cls, paramname, filename):
        """Returns a new MultipartParam object constructed from the local
        file at ``filename``.

        ``filesize`` is determined by os.path.getsize(``filename``)

        ``filetype`` is determined by mimetypes.guess_type(``filename``)[0]

        ``filename`` is set to os.path.basename(``filename``)
        """

        return cls(paramname, filename=os.path.basename(filename),
                filetype=mimetypes.guess_type(filename)[0],
                filesize=os.path.getsize(filename),
                fileobj=open(filename, "r"))

    @classmethod
    def from_params(cls, params):
        """Returns a list of MultipartParam objects from a sequence of
        name, value pairs, MultipartParam instances, 
        or from a mapping of names to values

        The values may be strings or file objects."""
        if hasattr(params, 'items'):
            params = params.items()

        retval = []
        for item in params:
            if isinstance(item, cls):
                retval.append(item)
                continue
            name, value = item
            if hasattr(value, 'read'):
                # Looks like a file object
                filename = getattr(value, 'name')
                if filename is not None:
                    filetype = mimetypes.guess_type(filename)[0]
                else:
                    filetype = None

                retval.append(cls(name=name, filename=filename,
                    filetype=filetype, fileobj=value))
            else:
                retval.append(cls(name, value))
        return retval

    def encode_hdr(self, boundary):
        """Returns the header of the encoding of this parameter"""
        boundary = encode_and_quote(boundary)

        headers = ["--%s" % boundary]

        if self.filename:
            disposition = 'form-data; name="%s"; filename="%s"' % (self.name,
                    self.filename)
        else:
            disposition = 'form-data; name="%s"' % self.name

        headers.append("Content-Disposition: %s" % disposition)

        if self.filetype:
            filetype = self.filetype
        else:
            filetype = "text/plain; charset=utf-8"

        headers.append("Content-Type: %s" % filetype)

        if self.filesize is not None:
            headers.append("Content-Length: %i" % self.filesize)
        else:
            headers.append("Content-Length: %i" % len(self.value))

        headers.append("")
        headers.append("")

        return "\r\n".join(headers)

    def encode(self, boundary):
        """Returns the string encoding of this parameter"""
        if self.value is None:
            value = self.fileobj.read()
        else:
            value = self.value

        if re.search("^--%s$" % re.escape(boundary), value, re.M):
            raise ValueError("boundary found in encoded string")

        return "%s%s\r\n" % (self.encode_hdr(boundary), value)

    def iter_encode(self, boundary, blocksize=4096):
        """Yields the encoding of this parameter
        If self.fileobj is set, then blocks of ``blocksize`` bytes are read and
        yielded."""
        if self.value is not None:
            yield self.encode(boundary)
        else:
            yield self.encode_hdr(boundary)
            last_block = ""
            encoded_boundary = "--%s" % encode_and_quote(boundary)
            boundary_exp = re.compile("^%s$" % re.escape(encoded_boundary),
                    re.M)
            while True:
                block = self.fileobj.read(blocksize)
                if not block:
                    yield "\r\n"
                    break
                last_block += block
                if boundary_exp.search(last_block):
                    raise ValueError("boundary found in file data")
                last_block = last_block[-len(encoded_boundary)-2:]
                yield block

    def get_size(self, boundary):
        """Returns the size in bytes that this param will be when encoded
        with the given boundary."""
        if self.filesize is not None:
            valuesize = self.filesize
        else:
            valuesize = len(self.value)

        return len(self.encode_hdr(boundary)) + 2 + valuesize

def encode_string(boundary, name, value):
    """Returns ``name`` and ``value`` encoded as a multipart/form-data
    variable.  ``boundary`` is the boundary string used throughout
    a single request to separate variables."""

    return MultipartParam(name, value).encode(boundary)

def encode_file_header(boundary, paramname, filesize, filename=None,
        filetype=None):
    """Returns the leading data for a multipart/form-data field that contains
    file data.

    ``boundary`` is the boundary string used throughout a single request to
    separate variables.
    
    ``paramname`` is the name of the variable in this request.

    ``filesize`` is the size of the file data.

    ``filename`` if specified is the filename to give to this field.  This
    field is only useful to the server for determining the original filename.
    
    ``filetype`` if specified is the MIME type of this file.
    
    The actual file data should be sent after this header has been sent.
    """

    return MultipartParam(paramname, filesize=filesize, filename=filename,
            filetype=filetype).encode_hdr(boundary)

def get_body_size(params, boundary):
    """Returns the number of bytes that the multipart/form-data encoding
    of ``params`` will be."""
    size = sum(p.get_size(boundary) for p in MultipartParam.from_params(params))
    return size + len(boundary) + 6

def get_headers(params, boundary):
    """Returns a dictionary with Content-Type and Content-Length headers
    for the multipart/form-data encoding of ``params``."""
    headers = {}
    boundary = urllib.quote_plus(boundary)
    headers['Content-Type'] = "multipart/form-data; boundary=%s" % boundary
    headers['Content-Length'] = get_body_size(params, boundary)
    return headers

def multipart_encode(params, boundary=None):
    """Encode ``params`` as multipart/form-data.

    ``params`` should be a dictionary where the keys represent parameter names,
    and the values are either parameter values, or file-like objects to
    use as the parameter value.  The file-like objects must support .read()
    and either .fileno() or both .seek() and .tell().

    If ``boundary`` is set, then it as used as the MIME boundary.  Otherwise
    a randomly generated boundary will be used.  In either case, if the
    boundary string appears in the parameter values a ValueError will be
    raised.

    Returns a tuple of `datagen`, `headers`, where `datagen` is a
    generator that will yield blocks of data that make up the encoded
    parameters, and `headers` is a dictionary with the assoicated
    Content-Type and Content-Length headers."""
    if boundary is None:
        boundary = gen_boundary()
    else:
        boundary = urllib.quote_plus(boundary)

    headers = get_headers(params, boundary)
    params = MultipartParam.from_params(params)

    def yielder():
        """generator function to yield multipart/form-data representation
        of parameters"""
        for param in params:
            for block in param.iter_encode(boundary):
                yield block
        yield "--%s--\r\n" % boundary

    return yielder(), headers

########NEW FILE########
__FILENAME__ = streaminghttp
"""Streaming HTTP uploads module.

This module extends the standard httplib and urllib2 objects so that
iterable objects can be used in the body of HTTP requests.

In most cases all one should have to do is call :func:`register_openers()`
to register the new streaming http handlers which will take priority over
the default handlers, and then you can use iterable objects in the body
of HTTP requests.

**N.B.** You must specify a Content-Length header if using an iterable object
since there is no way to determine in advance the total size that will be
yielded, and there is no way to reset an interator.

Example usage:

>>> from StringIO import StringIO
>>> import urllib2, poster.streaminghttp

>>> poster.streaminghttp.register_openers()

>>> s = "Test file data"
>>> f = StringIO(s)

>>> req = urllib2.Request("http://localhost:5000", f, {'Content-Length': len(s)})
"""

import httplib, urllib2, socket
from httplib import NotConnected

__all__ = ['StreamingHTTPConnection', 'StreamingHTTPRedirectHandler',
        'StreamingHTTPHandler', 'register_openers']

if hasattr(httplib, 'HTTPS'):
    __all__.extend(['StreamingHTTPSHandler', 'StreamingHTTPSConnection'])

class _StreamingHTTPMixin:
    def send(self, value):
        """Send ``value`` to the server.
        
        ``value`` can be a string object, a file-like object that supports
        a .read() method, or an iterable object that supports a .next()
        method.
        """
        # Based on python 2.6's httplib.HTTPConnection.send()
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise NotConnected()

        # send the data to the server. if we get a broken pipe, then close
        # the socket. we want to reconnect when somebody tries to send again.
        #
        # NOTE: we DO propagate the error, though, because we cannot simply
        #       ignore the error... the caller will know if they can retry.
        if self.debuglevel > 0:
            print "send:", repr(value)
        try:
            blocksize=8192
            if hasattr(value,'read') :
                if self.debuglevel > 0: print "sendIng a read()able"
                data=value.read(blocksize)
                while data:
                    self.sock.sendall(data)
                    data=value.read(blocksize)
            elif hasattr(value,'next'):
                if self.debuglevel > 0: print "sendIng an iterable"
                for data in value:
                    self.sock.sendall(data)
            else:
                self.sock.sendall(value)
        except socket.error, v:
            if v[0] == 32:      # Broken pipe
                self.close()
            raise

class StreamingHTTPConnection(_StreamingHTTPMixin, httplib.HTTPConnection):
    """Subclass of `httplib.HTTPConnection` that overrides the `send()` method
    to support iterable body objects"""

class StreamingHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    """Subclass of `urllib2.HTTPRedirectHandler` that overrides the
    `redirect_request` method to properly handle redirected POST requests

    This class is required because python 2.5's HTTPRedirectHandler does
    not remove the Content-Type or Content-Length headers when requesting
    the new resource, but the body of the original request is not preserved.
    """

    handler_order = urllib2.HTTPRedirectHandler.handler_order - 1

    # From python2.6 urllib2's HTTPRedirectHandler
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Return a Request or None in response to a redirect.

        This is called by the http_error_30x methods when a
        redirection response is received.  If a redirection should
        take place, return a new Request to allow http_error_30x to
        perform the redirect.  Otherwise, raise HTTPError if no-one
        else should try to handle this url.  Return None if you can't
        but another Handler might.
        """
        m = req.get_method()
        if (code in (301, 302, 303, 307) and m in ("GET", "HEAD")
            or code in (301, 302, 303) and m == "POST"):
            # Strictly (according to RFC 2616), 301 or 302 in response
            # to a POST MUST NOT cause a redirection without confirmation
            # from the user (of urllib2, in this case).  In practice,
            # essentially all clients do redirect in this case, so we
            # do the same.
            # be conciliant with URIs containing a space
            newurl = newurl.replace(' ', '%20')
            newheaders = dict((k,v) for k,v in req.headers.items()
                              if k.lower() not in ("content-length", "content-type")
                             )
            return urllib2.Request(newurl,
                           headers=newheaders,
                           origin_req_host=req.get_origin_req_host(),
                           unverifiable=True)
        else:
            raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)

class StreamingHTTPHandler(urllib2.HTTPHandler):
    """Subclass of `urllib2.HTTPHandler` that uses
    StreamingHTTPConnection as its http connection class."""

    handler_order = urllib2.HTTPHandler.handler_order - 1

    def http_open(self, req):
        return self.do_open(StreamingHTTPConnection, req)

    def http_request(self, req):
        # Make sure that if we're using an iterable object as the request
        # body, that we've also specified Content-Length
        if req.has_data():
            data = req.get_data()
            if not hasattr(data, 'read') and hasattr(data, 'next'):
                if not req.has_header('Content-length'):
                    raise ValueError(
                            "No Content-Length specified for iterable body")
        return urllib2.HTTPHandler.do_request_(self, req)

if hasattr(httplib, 'HTTPS'):
    class StreamingHTTPSConnection(_StreamingHTTPMixin, httplib.HTTPSConnection):
        """Subclass of `httplib.HTTSConnection` that overrides the `send()` method
        to support iterable body objects"""

    class StreamingHTTPSHandler(urllib2.HTTPSHandler):
        """Subclass of `urllib2.HTTPSHandler` that uses
        StreamingHTTPSConnection as its http connection class."""

        handler_order = urllib2.HTTPSHandler.handler_order - 1

        def https_open(self, req):
            return self.do_open(StreamingHTTPSConnection, req)

        def https_request(self, req):
            # Make sure that if we're using an iterable object as the request
            # body, that we've also specified Content-Length
            if req.has_data():
                data = req.get_data()
                if not hasattr(data, 'read') and hasattr(data, 'next'):
                    if not req.has_header('Content-length'):
                        raise ValueError(
                                "No Content-Length specified for iterable body")
            return urllib2.HTTPSHandler.do_request_(self, req)


def register_openers():
    """Register the streaming http handlers in the global urllib2 default
    opener object."""
    handlers = [StreamingHTTPHandler, StreamingHTTPRedirectHandler]
    if hasattr(httplib, "HTTPS"):
        handlers.append(StreamingHTTPSHandler)

    urllib2.install_opener(urllib2.build_opener(*handlers))

########NEW FILE########
