__FILENAME__ = app
from google.appengine.ext.webapp.util import run_wsgi_app
from models import DropboxUser
from oauth.oauth import OAuthToken
from simpledav.wsgi import WSGIApplication
from views import AuthHandler, DropboxDAVHandler, dropbox_client

auth_handler = AuthHandler()

class DropboxWebDAVApplication(WSGIApplication):
    def handle_request(self, environ, request, response):
        method = environ['REQUEST_METHOD']
        
        if True:# or (method == 'GET' or method == 'POST') and request.path == '/':
            return self.handle_main(environ, request, response)
        
        # Check authentication
        (email, password) = self.get_credentials(request)
        
        if email:
            user = DropboxUser.find_by_email(email)
            
            if user and user.is_password_valid(password):
                self._handler.client = dropbox_client(OAuthToken.from_string(user.access_token))
                return super(DropboxWebDAVApplication,self).handle_request(environ,request,response)
            else:
                return self.request_authentication(response)
        else:
            return self.request_authentication(response)
    
    def handle_main(self, environ, request, response):
        method = environ['REQUEST_METHOD']
        auth_handler.initialize(request, response)
        handler_method = getattr(auth_handler,method.lower())
        handler_method()

application = DropboxWebDAVApplication(debug=True,handler_cls=DropboxDAVHandler)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

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
    def load_config(self, file):
        """
        Loads a configuration .ini file, and then pulls out the 'auth' key
        to make a dict you can pass to Authenticator().
        """
        config = SafeConfigParser()
        config.read(file)
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
        assert self.trusted_access_token_url, "You must set the trusted_access_token_url."
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

from dropbox import rest
import urllib
import urllib2
import poster
import httplib
import hashlib
from django.utils import simplejson as json
import logging
from poster.encode import MultipartParam

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
        The api_host and content_host are normally 'api.getdropbox.com' and
        'api-content.getdropbox.com' and will use the same port.
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
        self.port = port


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


    def put_file(self, root, to_path, file_obj, file_name=None):
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
        
        name = file_name if file_name else file_obj.name
        params = { "file" : name, }

        url, headers, params = self.request(self.content_host, "POST", path, params, None)

        params['file'] = file_obj
        data, mp_headers = poster.encode.multipart_encode([MultipartParam('file', fileobj=file_obj, filename=name)])
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

        path = "/files/%s%s" % (root, path)

        params = {'file_limit': file_limit,
                  'list': "true" if list else "false",
                  'status_in_response': status_in_response}

        url, headers, params = self.request(self.api_host, "GET", path, params, callback)

        return self.api_rest.GET(url, headers)

    def links(self, root, path):
        assert root in ["dropbox", "sandbox"]
        path = "/links/%s%s" % (root, path)
        return self.build_full_url(self.api_host, path)


    def event_metadata(self, root, user, ns_and_jids):
        """
        When you register your consumer key with Dropbox you can indicate a URL
        as the "pingback url".  Dropbox will perform a POST to this url giving
        you a JSON structure of all user_id:namespace_id:journal_id combinations
        from events people have made in sandboxes you care about.  The
        event_metadata call is how you take this JSON structure and get an
        abbreviated metadata for the events consisting of:

            {u'1895063': {u'4080130': {u'148574034': 
                {u'path': u'/tohere', u'is_dir': True, u'mtime': -1, u'latest': True, u'size': -1}}}}

        This is the mapping back of user_id:namespace_id:journal_id => metadata.
        In the metadata you get a hash containing just path, is_dir, mtime,
        latest, and size.

        If the file was deleted then mtime is -1.  If the file is not latest
        (latest:False) then there's a more recent record you should get.
        """
        assert user and ns_and_jids, "All parameters required."
        assert root in ['sandbox', 'dropbox']
        
        params = {'target_events': json.dumps({user: ns_and_jids}), 'root': root}
        url, headers, params = self.request(self.api_host, "POST",
                                        "/event_metadata", params, None)
        return self.api_rest.POST(url, params, headers)

    def event_content_is_available(self, md):
        """
        Given a metadata hash this will tell you if the file will be available
        (probably) when you go to do an event_content.
        """
        return 'error' not in md and md['latest'] == True and md['size'] != -1 and md['is_dir'] == False


    def event_content(self, root, uid, nsid, jid):
        """
        While event_metadata will give you batches of metadata for pingback
        events, the event_content call will give you an exact file for any
        tuple of user_id:namespace_id:journal_id.  You make this GET request
        to event_content setting a single "target_event=uid:nsid:jid" parameter,
        and returned to you is the contents of the file.  Additionally, you get
        an HTTP header of X-Dropbox-Metadata (case insensitive) that has the
        same metadata json as what you'd get for the one record from
        event_metadata.

        If the file is deleted, not the latest, or some reason not accessible,
        you'll get a 404, but the x-dropbox-metadata will still be there so you
        can determine why and update your records.
        """
        assert uid != None and nsid != None and jid != None, "All parameters are required."
        assert root in ['sandbox', 'dropbox']

        params = {'target_event': "%d:%d:%d" % (int(uid), int(nsid), int(jid)), 'root': root}
        url, headers, params = self.request(self.content_host, "GET",
                                            "/event_content", params, None)

        resp = self.content_rest.request("GET", url, headers=headers, raw_response=True)
        resp.headers = dict(resp.getheaders())

        if 'x-dropbox-metadata' in resp.headers:
            resp.headers['x-dropbox-metadata'] = json.loads(resp.headers['x-dropbox-metadata'])

        return resp


    def build_url(self, url, params=None):
        """Used internally to build the proper URL from parameters and the API_VERSION."""
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
from django.utils import simplejson as json
import urllib


class RESTClient(object):
    """
    An abstraction on performing JSON REST requests that is used internally
    by the Dropbox Client API.  It provides just enough gear to make requests
    and get responses as JSON data.

    It is not designed well for file uploads.
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
__FILENAME__ = models
from google.appengine.ext import db
import hashlib

class DropboxUser(db.Model):
    email = db.StringProperty()
    password = db.StringProperty() # stored as a one-way hash
    access_token = db.StringProperty()

    @classmethod
    def find_by_dropbox_userid(cls, dropbox_userid):
        return cls.all().filter('dropbox_userid =', dropbox_userid).get()
    
    @classmethod
    def find_by_email(cls, email):
        return cls.all().filter('email =', email).get()

    def set_password(self, password):
        self.password = hashlib.md5(password).hexdigest()
    
    def is_password_valid(self, password):
        hash = hashlib.md5(password).hexdigest()
        return hash == self.password

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

def _strify(s):
    """If s is a unicode string, encode it to UTF-8 and return the results,
    otherwise return str(s), or None if s is None"""
    if s is None:
        return None
    if isinstance(s, unicode):
        return s.encode("utf-8")
    return str(s)

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
        self.value = _strify(value)
        if filename is None:
            self.filename = None
        else:
            if isinstance(filename, unicode):
                # Encode with XML entities
                self.filename = filename.encode("ascii", "xmlcharrefreplace")
            else:
                self.filename = str(filename)
            self.filename = self.filename.encode("string_escape").\
                    replace('"', '\\"')
        self.filetype = _strify(filetype)

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

    def __cmp__(self, other):
        attrs = ['name', 'value', 'filename', 'filetype', 'filesize', 'fileobj']
        myattrs = [getattr(self, a) for a in attrs]
        oattrs = [getattr(other, a) for a in attrs]
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
                fileobj=open(filename, "rb"))

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
                filename = getattr(value, 'name', None)
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

    ``params`` should be a sequence of (name, value) pairs or MultipartParam
    objects, or a mapping of names to values.
    Values are either strings parameter values, or file-like objects to use as
    the parameter value.  The file-like objects must support .read() and either
    .fileno() or both .seek() and .tell().

    If ``boundary`` is set, then it as used as the MIME boundary.  Otherwise
    a randomly generated boundary will be used.  In either case, if the
    boundary string appears in the parameter values a ValueError will be
    raised.

    Returns a tuple of `datagen`, `headers`, where `datagen` is a
    generator that will yield blocks of data that make up the encoded
    parameters, and `headers` is a dictionary with the assoicated
    Content-Type and Content-Length headers.

    Examples:

    >>> datagen, headers = multipart_encode( [("key", "value1"), ("key", "value2")] )
    >>> s = "".join(datagen)
    >>> assert "value2" in s and "value1" in s

    >>> p = MultipartParam("key", "value2")
    >>> datagen, headers = multipart_encode( [("key", "value1"), p] )
    >>> s = "".join(datagen)
    >>> assert "value2" in s and "value1" in s

    >>> datagen, headers = multipart_encode( {"key": "value1"} )
    >>> s = "".join(datagen)
    >>> assert "value2" not in s and "value1" in s

    """
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

>>> opener = poster.streaminghttp.register_openers()

>>> s = "Test file data"
>>> f = StringIO(s)

>>> req = urllib2.Request("http://localhost:5000", f, \
        {'Content-Length': len(s)})
"""

import httplib, urllib2, socket
from httplib import NotConnected

__all__ = ['StreamingHTTPConnection', 'StreamingHTTPRedirectHandler',
        'StreamingHTTPHandler', 'register_openers']

if hasattr(httplib, 'HTTPS'):
    __all__.extend(['StreamingHTTPSHandler', 'StreamingHTTPSConnection'])

class _StreamingHTTPMixin:
    """Mixin class for HTTP and HTTPS connections that implements a streaming
    send method."""
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
            blocksize = 8192
            if hasattr(value, 'read') :
                if self.debuglevel > 0:
                    print "sendIng a read()able"
                data = value.read(blocksize)
                while data:
                    self.sock.sendall(data)
                    data = value.read(blocksize)
            elif hasattr(value, 'next'):
                if self.debuglevel > 0:
                    print "sendIng an iterable"
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
            newheaders = dict((k, v) for k, v in req.headers.items()
                              if k.lower() not in (
                                  "content-length", "content-type")
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
        """Open a StreamingHTTPConnection for the given request"""
        return self.do_open(StreamingHTTPConnection, req)

    def http_request(self, req):
        """Handle a HTTP request.  Make sure that Content-Length is specified
        if we're using an interable value"""
        # Make sure that if we're using an iterable object as the request
        # body, that we've also specified Content-Length
        if req.has_data():
            data = req.get_data()
            if hasattr(data, 'read') or hasattr(data, 'next'):
                if not req.has_header('Content-length'):
                    raise ValueError(
                            "No Content-Length specified for iterable body")
        return urllib2.HTTPHandler.do_request_(self, req)

if hasattr(httplib, 'HTTPS'):
    class StreamingHTTPSConnection(_StreamingHTTPMixin,
            httplib.HTTPSConnection):
        """Subclass of `httplib.HTTSConnection` that overrides the `send()`
        method to support iterable body objects"""

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
    opener object.

    Returns the created OpenerDirector object."""
    handlers = [StreamingHTTPHandler, StreamingHTTPRedirectHandler]
    if hasattr(httplib, "HTTPS"):
        handlers.append(StreamingHTTPSHandler)

    opener = urllib2.build_opener(*handlers)

    urllib2.install_opener(opener)

    return opener

########NEW FILE########
__FILENAME__ = views
from datetime import datetime
from dropbox import auth, client
from email.utils import parsedate_tz, mktime_tz
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from models import DropboxUser
from oauth.oauth import OAuthToken
from simpledav.models import Resource
from simpledav.views import DAVHandler
from urllib import pathname2url
from urlparse import urlparse
from xml.etree import ElementTree as ET
import mimetypes
import os

# load the configuration file and make an authenticator
dropbox_ini_path = os.path.join(os.path.dirname(__file__), 'dropbox.ini')
dropbox_config = auth.Authenticator.load_config(dropbox_ini_path)
dropbox_auth = auth.Authenticator(dropbox_config)

# Either dropbox or sandbox
ROOT = "dropbox"

def site_root():
    scheme = "http" if "Development" in os.environ['SERVER_SOFTWARE'] else "https"
    return scheme + "://" + os.environ['HTTP_HOST']

def dropbox_client(access_token):
    return client.DropboxClient(dropbox_config['server'], dropbox_config['content_server'], 
                                80, dropbox_auth, access_token)

class AuthHandler(webapp.RequestHandler):
    def get(self):
        if self.request.GET.has_key('oauth_token'):
            self.dropbox_auth_callback()
        else:
            self.index()

    def post(self):
        if self.request.POST.get('action') == 'setup':
            self.setup()
        elif self.request.POST.get('action') == 'setpass':
            self.set_dropdav_password()

    def index(self):
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, {}))
    
    def setup(self):
        # get a fresh request token
        token = dropbox_auth.obtain_request_token()
        self.response.headers['Set-Cookie'] = 'token=%s' % token # we'll need it later
        
        # make the user log in at dropbox.com and authorize this token
        self.redirect(dropbox_auth.build_authorize_url(token,callback=site_root()))
    
    def dropbox_auth_callback(self):
        # now use the authorized token to grab an access token
        token = OAuthToken.from_string(self.request.cookies['token'])
        access_token = dropbox_auth.obtain_access_token(token, "")
        self.response.headers['Set-Cookie'] = 'token=' # erase the auth token
        
        # lookup your account info
        client = dropbox_client(access_token)
        account_info = client.account_info().data
        
        template_params = {
            'access_token':access_token.to_string(),
            'email':account_info['email'],
        }
        
        # prompt you to fill in the account credentials for our system
        path = os.path.join(os.path.dirname(__file__), 'password.html')
        self.response.out.write(template.render(path, template_params))
    
    def set_dropdav_password(self):
        access_token = OAuthToken.from_string(self.request.POST.get('access_token'))
        password = self.request.POST.get('password')
        
        # lookup your account info again to confirm
        client = dropbox_client(access_token)
        account_info = client.account_info().data
        email = account_info['email']
        
        user = DropboxUser.find_by_email(email)
        
        if not user:
            user = DropboxUser(email=email)
                    
        # create or update your user entry in our system
        user.access_token = access_token.to_string()
        user.set_password(password)
        user.put()

        # prompt you to fill in the account credentials for our system
        path = os.path.join(os.path.dirname(__file__), 'success.html')
        self.response.out.write(template.render(path, {'email':email,'server':site_root()}))

class DropboxDAVHandler(DAVHandler):
    def export_meta_entry(self,meta_entry,href=None):
        # make a fake Resource to ease our exporting
        modified = datetime.fromtimestamp(mktime_tz(parsedate_tz(meta_entry['modified']))) if meta_entry.has_key('modified') else datetime.utcnow()
        
        return Resource(
            path = meta_entry['path'].strip('/'),
            is_collection = meta_entry['is_dir'],
            content_length = meta_entry['bytes'],
            created = modified,
            modified = modified,
            
            
        ).export_response(href=href)
    
    def propfind(self):
        path = '/' + self.request_path
        depth = self.request.headers.get('depth','0')
        
        if depth != '0' and depth != '1':
            return self.response.set_status(403,'Forbidden')
        
        metadata = self.client.metadata(ROOT,path).data
        
        if not metadata:
            return self.response.set_status(404,"Not Found")
        
        root = ET.Element('D:multistatus',{'xmlns:D':'DAV:'})
        root.append(self.export_meta_entry(metadata,href=self.request.path)) # first response's href contains exactly what you asked for (relative path)
        
        if metadata.has_key('contents') and depth == '1':
            for entry in metadata['contents']:
                abs_path = site_root() + pathname2url(self._prefix + entry['path'].strip('/').encode('utf-8'))
                root.append(self.export_meta_entry(entry,href=abs_path))

        self.response.headers['Content-Type'] = 'text/xml; charset="utf-8"'
        self.response.set_status(207,'Multi-Status')
        ET.ElementTree(root).write(self.response.out, encoding='utf-8')
    
    def get(self):
        path = '/' + self.request_path
        
        file = self.client.get_file(ROOT,path)
        
        if not file:
            return self.response.set_status(404,"Not Found")
        
        mimetype = mimetypes.guess_type(path,strict=False)[0]
        
        # deliver the file data
        self.response.headers['Content-Type'] = mimetype if mimetype else 'application/octet-stream'
        self.response.out.write(file.read())

    def put(self):
        path = '/' + self.request_path
        self.client.put_file(ROOT, os.path.dirname(path), self.request.body_file, file_name=os.path.basename(path))
        self.response.set_status(201,'Created')

    def mkcol(self):
        path = '/' + self.request_path
        self.client.file_create_folder(ROOT,path)
        self.response.set_status(201,'Created')
    
    def delete(self):
        path = '/' + self.request_path
        self.client.file_delete(ROOT,path)
    
    def move(self):
        path = '/' + self.request_path
        destination = self.request.headers['Destination'] # exception if not present
        
        destination_path = '/' + self.url_to_path(urlparse(destination).path)
        
        if path == destination_path:
            return self.response.set_status(403,"Forbidden")
        
        self.client.file_move(ROOT,path,destination_path)
        self.response.set_status(201)

########NEW FILE########
