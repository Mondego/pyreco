__FILENAME__ = interactive_console
#!/usr/bin/python

import pytumblr
import yaml
import os
import urlparse
import code
import oauth2 as oauth

def new_oauth(yaml_path):
    '''
    Return the consumer and oauth tokens with three-legged OAuth process and
    save in a yaml file in the user's home directory.
    '''

    print 'Retrieve consumer key and consumer secret from http://www.tumblr.com/oauth/apps'
    consumer_key = raw_input('Paste the consumer key here: ')
    consumer_secret = raw_input('Paste the consumer secret here: ')

    request_token_url = 'http://www.tumblr.com/oauth/request_token'
    authorize_url = 'http://www.tumblr.com/oauth/authorize'
    access_token_url = 'http://www.tumblr.com/oauth/access_token'

    consumer = oauth.Consumer(consumer_key, consumer_secret)
    client = oauth.Client(consumer)

    # Get request token
    resp, content = client.request(request_token_url, "POST")
    request_token =  urlparse.parse_qs(content)

    # Redirect to authentication page
    print '\nPlease go here and authorize:\n%s?oauth_token=%s' % (authorize_url, request_token['oauth_token'][0])
    redirect_response = raw_input('Allow then paste the full redirect URL here:\n')

    # Retrieve oauth verifier
    url = urlparse.urlparse(redirect_response)
    query_dict = urlparse.parse_qs(url.query)
    oauth_verifier = query_dict['oauth_verifier'][0]

    # Request access token
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'][0])
    token.set_verifier(oauth_verifier)
    client = oauth.Client(consumer, token)

    resp, content = client.request(access_token_url, "POST")
    access_token = urlparse.parse_qs(content)

    tokens = {
        'consumer_key': consumer_key,
        'consumer_secret': consumer_secret,
        'oauth_token': access_token['oauth_token'][0],
        'oauth_token_secret': access_token['oauth_token_secret'][0]
    }

    yaml_file = open(yaml_path, 'w+')
    yaml.dump(tokens, yaml_file, indent=2)
    yaml_file.close()

    return tokens

if __name__ == '__main__':
    yaml_path = os.path.expanduser('~') + '/.tumblr'

    if not os.path.exists(yaml_path):
        tokens = new_oauth(yaml_path)
    else:
        yaml_file = open(yaml_path, "r")
        tokens = yaml.safe_load(yaml_file)
        yaml_file.close()

    client = pytumblr.TumblrRestClient(
        tokens['consumer_key'],
        tokens['consumer_secret'],
        tokens['oauth_token'],
        tokens['oauth_token_secret']
    )

    print 'pytumblr client created. You may run pytumblr commands prefixed with "client".\n'

    code.interact(local=dict(globals(), **{'client': client}))

########NEW FILE########
__FILENAME__ = helpers
def validate_params(valid_options, params):
    """
    Helps us validate the parameters for the request

    :param valid_options: a list of strings of valid options for the
                          api request
    :param params: a dict, the key-value store which we really only care about
                   the key which has tells us what the user is using for the
                   API request

    :returns: None or throws an exception if the validation fails
    """
    #crazy little if statement hanging by himself :(
    if not params:
        return

    #We only allow one version of the data parameter to be passed
    data_filter = ['data', 'source', 'external_url', 'embed']
    multiple_data = filter(lambda x: x in data_filter, params.keys())
    if len(multiple_data) > 1:
        raise Exception("You can't mix and match data parameters")

    #No bad fields which are not in valid options can pass
    disallowed_fields = filter(lambda x: x not in valid_options, params.keys())
    if disallowed_fields:
        field_strings = ",".join(disallowed_fields)
        raise Exception("%s are not allowed fields" % field_strings)

def validate_blogname(fn):
    """
    Decorator to validate the blogname and let you pass in a blogname like:
        client.blog_info('codingjester')
    or
        client.blog_info('codingjester.tumblr.com')
    or
        client.blog_info('blog.johnbunting.me')

    and query all the same blog.
    """
    def add_dot_tumblr(*args, **kwargs):
        if (len(args) > 1 and ("." not in args[1])):
            args = list(args)
            args[1] += ".tumblr.com"
        return fn(*args, **kwargs)
    return add_dot_tumblr

########NEW FILE########
__FILENAME__ = request
import urllib
import urllib2
import time
import json

from urlparse import parse_qsl
import oauth2 as oauth
from httplib2 import RedirectLimit

class TumblrRequest(object):
    """
    A simple request object that lets us query the Tumblr API
    """

    def __init__(self, consumer_key, consumer_secret="", oauth_token="", oauth_secret="", host="http://api.tumblr.com"):
        self.host = host
        self.consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
        self.token = oauth.Token(key=oauth_token, secret=oauth_secret)

    def get(self, url, params):
        """
        Issues a GET request against the API, properly formatting the params

        :param url: a string, the url you are requesting
        :param params: a dict, the key-value of all the paramaters needed
                       in the request
        :returns: a dict parsed of the JSON response
        """
        url = self.host + url
        if params:
            url = url + "?" + urllib.urlencode(params)

        client = oauth.Client(self.consumer, self.token)
        try:
            client.follow_redirects = False
            resp, content = client.request(url, method="GET", redirections=False)
        except RedirectLimit, e:
            resp, content = e.args

        return self.json_parse(content)

    def post(self, url, params={}, files=[]):
        """
        Issues a POST request against the API, allows for multipart data uploads

        :param url: a string, the url you are requesting
        :param params: a dict, the key-value of all the parameters needed
                       in the request
        :param files: a list, the list of tuples of files

        :returns: a dict parsed of the JSON response
        """
        url = self.host + url
        try:
            if files:
                return self.post_multipart(url, params, files)
            else:
                client = oauth.Client(self.consumer, self.token)
                resp, content = client.request(url, method="POST", body=urllib.urlencode(params))
                return self.json_parse(content)
        except urllib2.HTTPError, e:
            return self.json_parse(e.read())

    def json_parse(self, content):
        """
        Wraps and abstracts content validation and JSON parsing
        to make sure the user gets the correct response.
        
        :param content: The content returned from the web request to be parsed as json
        
        :returns: a dict of the json response
        """
        try:
            data = json.loads(content)
        except ValueError, e:
            data = {'meta': { 'status': 500, 'msg': 'Server Error'}, 'response': {"error": "Malformed JSON or HTML was returned."}}
        
        #We only really care about the response if we succeed
        #and the error if we fail
        if data['meta']['status'] in [200, 201, 301]:
            return data['response']
        else:
            return data

    def post_multipart(self, url, params, files):
        """
        Generates and issues a multipart request for data files

        :param url: a string, the url you are requesting
        :param params: a dict, a key-value of all the parameters
        :param files:  a list, the list of tuples for your data

        :returns: a dict parsed from the JSON response
        """
        #combine the parameters with the generated oauth params
        params = dict(params.items() + self.generate_oauth_params().items())
        faux_req = oauth.Request(method="POST", url=url, parameters=params)
        faux_req.sign_request(oauth.SignatureMethod_HMAC_SHA1(), self.consumer, self.token)
        params = dict(parse_qsl(faux_req.to_postdata()))

        content_type, body = self.encode_multipart_formdata(params, files)
        headers = {'Content-Type': content_type, 'Content-Length': str(len(body))}

        #Do a bytearray of the body and everything seems ok
        r = urllib2.Request(url, bytearray(body), headers)
        content = urllib2.urlopen(r).read()
        return self.json_parse(content)

    def encode_multipart_formdata(self, fields, files):
        """
        Properly encodes the multipart body of the request

        :param fields: a dict, the parameters used in the request
        :param files:  a list of tuples containing information about the files

        :returns: the content for the body and the content-type value
        """
        import mimetools
        import mimetypes
        BOUNDARY = mimetools.choose_boundary()
        CRLF = '\r\n'
        L = []
        for (key, value) in fields.items():
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % mimetypes.guess_type(filename)[0] or 'application/octet-stream')
            L.append('Content-Transfer-Encoding: binary')
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body

    def generate_oauth_params(self):
        """
        Generates the oauth parameters needed for multipart/form requests

        :returns: a dictionary of the proper headers that can be used
                  in the request
        """
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'oauth_token': self.token.key,
            'oauth_consumer_key': self.consumer.key
        }
        return params

########NEW FILE########
__FILENAME__ = test_pytumblr
import nose
import unittest
import mock
import json
import io
from httpretty import HTTPretty, httprettified
import pytumblr
from urlparse import parse_qs


class TumblrRestClientTest(unittest.TestCase):
    """
    """

    def setUp(self):
        with open('tests/tumblr_credentials.json', 'r') as f:
            credentials = json.loads(f.read())
        self.client = pytumblr.TumblrRestClient(credentials['consumer_key'], credentials['consumer_secret'], credentials['oauth_token'], credentials['oauth_token_secret'])

    @httprettified
    def test_dashboard(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/user/dashboard',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"posts": [] } }')

        response = self.client.dashboard()
        assert response['posts'] == []

    @httprettified
    def test_posts(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/posts',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"posts": [] } }')

        response = self.client.posts('codingjester.tumblr.com')
        assert response['posts'] == []

    @httprettified
    def test_posts_with_type(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/seejohnrun.tumblr.com/posts/photo',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"posts": [] } }')

        response = self.client.posts('seejohnrun', 'photo')
        assert response['posts'] == []

    @httprettified
    def test_posts_with_type_and_arg(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/seejohnrun.tumblr.com/posts/photo?limit=1',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"posts": [] } }')

        args = { 'limit': 1 }
        response = self.client.posts('seejohnrun', 'photo', **args)
        assert response['posts'] == []

    @httprettified
    def test_blogInfo(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/info',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"blog": {} } }')

        response = self.client.blog_info('codingjester.tumblr.com')
        assert response['blog'] == {}

    @httprettified
    def test_followers(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/followers',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"users": [] } }')

        response = self.client.followers('codingjester.tumblr.com')
        assert response['users'] == []

    @httprettified
    def test_blogLikes(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/likes',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"liked_posts": [] } }')

        response = self.client.blog_likes('codingjester.tumblr.com')
        assert response['liked_posts'] == []

    @httprettified
    def test_queue(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/posts/queue',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"posts": [] } }')

        response = self.client.queue('codingjester.tumblr.com')
        assert response['posts'] == []

    @httprettified
    def test_drafts(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/posts/draft',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"posts": [] } }')

        response = self.client.drafts('codingjester.tumblr.com')
        assert response['posts'] == []

    @httprettified
    def test_submissions(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/posts/submission',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": {"posts": [] } }')

        response = self.client.submission('codingjester.tumblr.com')
        assert response['posts'] == []

    @httprettified
    def test_follow(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/user/follow',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.follow("codingjester.tumblr.com")
        assert response == []

        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert HTTPretty.last_request.method == "POST"
        assert experimental_body['url'][0] == 'codingjester.tumblr.com'

    @httprettified
    def test_unfollow(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/user/unfollow',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.unfollow("codingjester.tumblr.com")
        assert response == []

        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert HTTPretty.last_request.method == "POST"
        assert experimental_body['url'][0] == 'codingjester.tumblr.com'

    @httprettified
    def test_reblog(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/seejohnrun.tumblr.com/post/reblog',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.reblog('seejohnrun', id='123', reblog_key="adsfsadf", state='coolguy', tags=['hello', 'world'])
        assert response == []

        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert HTTPretty.last_request.method == 'POST'
        assert experimental_body['id'][0] == '123'
        assert experimental_body['reblog_key'][0] == 'adsfsadf'
        assert experimental_body['state'][0] == 'coolguy'
        assert experimental_body['tags'][0] == 'hello,world'

    @httprettified
    def test_edit_post(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/seejohnrun.tumblr.com/post/edit',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.edit_post('seejohnrun', id='123', state='coolguy', tags=['hello', 'world'])
        assert response == []

        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert HTTPretty.last_request.method == 'POST'
        assert experimental_body['id'][0] == '123'
        assert experimental_body['state'][0] == 'coolguy'
        assert experimental_body['tags'][0] == 'hello,world'

    @httprettified
    def test_like(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/user/like',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.like('123', "adsfsadf")
        assert response == []

        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert HTTPretty.last_request.method == "POST"
        assert experimental_body['id'][0] == '123'
        assert experimental_body['reblog_key'][0] == 'adsfsadf'

    @httprettified
    def test_unlike(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/user/unlike',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.unlike('123', "adsfsadf")
        assert response == []

        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert HTTPretty.last_request.method == "POST"
        assert experimental_body['id'][0] == '123'
        assert experimental_body['reblog_key'][0] == 'adsfsadf'

    @httprettified
    def test_info(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/user/info',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.info()
        assert response == []

    @httprettified
    def test_likes(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/user/likes',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.likes()
        assert response == []

    @httprettified
    def test_following(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/user/following',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.following()
        assert response == []

    @httprettified
    def test_tagged(self):
        HTTPretty.register_uri(HTTPretty.GET, 'http://api.tumblr.com/v2/tagged?tag=food',
                               body='{"meta": {"status": 200, "msg": "OK"}, "response": []}')

        response = self.client.tagged('food')
        assert response == []

    @httprettified
    def test_create_text(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_text('codingjester.tumblr.com', body="Testing")
        assert response == []

    @httprettified
    def test_create_link(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_link('codingjester.tumblr.com', url="http://google.com", tags=['omg', 'nice'])
        assert response == []

        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert HTTPretty.last_request.method == "POST"
        assert experimental_body['tags'][0] == "omg,nice"

    @httprettified
    def test_no_tags(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/seejohnrun.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_link('seejohnrun.tumblr.com', tags=[])
        experimental_body = parse_qs(HTTPretty.last_request.body)
        assert 'tags' not in experimental_body

    @httprettified
    def test_create_quote(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_quote('codingjester.tumblr.com', quote="It's better to love and lost, than never have loved at all.")
        assert response == []

    @httprettified
    def test_create_chat(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_chat('codingjester.tumblr.com', conversation="JB: Testing is rad.\nJC: Hell yeah.")
        assert response == []

    @httprettified
    def test_create_photo(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_photo('codingjester.tumblr.com', source="http://media.tumblr.com/image.jpg")
        assert response == []

        #with mock.patch('__builtin__.open') as my_mock:
        #    my_mock.return_value.__enter__ = lambda s: s
        #    my_mock.return_value.__exit__ = mock.Mock()
        #    my_mock.return_value.read.return_value = 'some data'
        #    response = self.client.create_photo('codingjester.tumblr.com', data="/Users/johnb/Desktop/gozer_avatar.jpgdf")
        #    assert response['meta']['status'] == 201
        #    assert response['meta']['msg'] == "OK"

        #response = self.client.create_photo('codingjester.tumblr.com', data=["/Users/johnb/Desktop/gozer_avatar.jpg", "/Users/johnb/Desktop/gozer_avatar.jpg"])
        #assert response['meta']['status'] == 201
        #assert response['meta']['msg'] == "OK"

    @httprettified
    def test_create_audio(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_audio('codingjester.tumblr.com', external_url="http://media.tumblr.com/audio.mp3")
        assert response == []

    @httprettified
    def test_create_video(self):
        HTTPretty.register_uri(HTTPretty.POST, 'http://api.tumblr.com/v2/blog/codingjester.tumblr.com/post',
                               body='{"meta": {"status": 201, "msg": "OK"}, "response": []}')

        response = self.client.create_video('codingjester.tumblr.com', embed="blahblahembed")
        assert response == []

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
