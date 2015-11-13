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
__FILENAME__ = wp2tumblr
# coding: utf-8
"""
    wp2tumblr
    ~~~~~~

    A simple tool to import a Wordpress XML file into Tumblr

    :copyright: (c) 2014 by Jon Thornton.
    :license: BSD, see LICENSE for more details.
"""

import datetime
from xml.dom import minidom
# import types

from flask import Flask
from flask import g, session, request, url_for, flash
from flask import redirect, render_template
from flask_oauthlib.client import OAuth
import pytumblr


app = Flask(__name__)
app.config.from_envvar('WP2TUMBLR_SETTINGS')

POST_STATES = {
    'publish': 'published',
    'draft': 'draft',
    'pending': 'draft',
    'private': 'private',
    'future': 'queue'
}

oauth = OAuth(app)

tumblr_oauth = oauth.remote_app(
    'tumblr',
    app_key='TUMBLR',
    request_token_url='http://www.tumblr.com/oauth/request_token',
    access_token_url='http://www.tumblr.com/oauth/access_token',
    authorize_url='http://www.tumblr.com/oauth/authorize',
    base_url='https://api.tumblr.com/v2/',
)




@tumblr_oauth.tokengetter
def get_tumblr_token():
    if 'tumblr_oauth' in session:
        resp = session['tumblr_oauth']
        return resp['oauth_token'], resp['oauth_token_secret']


@app.route('/oauthorized')
@tumblr_oauth.authorized_handler
def oauthorized(resp):
    if resp is None:
        flash('You denied the request to sign in.')
    else:
        session['tumblr_oauth'] = resp

    return redirect(url_for('index'))

@app.before_request
def before_request():
    g.tumblr = None

    if 'tumblr_oauth' in session:
        g.tumblr = pytumblr.TumblrRestClient(
            app.config['TUMBLR_CONSUMER_KEY'],
            app.config['TUMBLR_CONSUMER_SECRET'],
            session['tumblr_oauth']['oauth_token'],
            session['tumblr_oauth']['oauth_token_secret'],
        )



@app.route('/login')
def login():
    return tumblr_oauth.authorize()


@app.route('/logout')
def logout():
    flash('You\'ve logged out')
    session.pop('tumblr_oauth', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    userinfo = None
    if g.tumblr:
        userinfo = g.tumblr.info()
    return render_template('index.html', userinfo = userinfo)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if g.tumblr is None:
        return redirect(url_for('login'))

    tumblog_name = request.form.get('tumblog_name') or request.args.get('tumblog_name')
    if not tumblog_name:
        return redirect(url_for('index'))

    bloginfo = g.tumblr.blog_info(tumblog_name)
    if 'meta' in bloginfo and bloginfo['meta']['status'] != 200:
        flash('Invalid blog name')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # try:
        post_count = do_import(tumblog_name, request.files['wordpress_xml'])
        # except Exception, detail:
        #     print 'XML file must be well-formed. You\'ll need to edit the file to fix the problem.'
        #     print detail

        if 'LOG_FILE' in app.config:
            userinfo = g.tumblr.info()

            with open(app.config['LOG_FILE'], 'a') as f:
                f.write('%s\t%s\t%s\t%s\t%d posts\n' % (
                    datetime.datetime.now().isoformat(),
                    userinfo['user']['name'],
                    bloginfo['blog']['title'],
                    bloginfo['blog']['url'],
                    post_count)
                )

        flash('%d posts from your Wordpress blog have been imported into %s!' % (post_count, tumblog_name))
        return redirect(url_for('index'))

    return render_template('upload.html', bloginfo=bloginfo, tumblog_name=tumblog_name)


def do_import(tumblog_name, xml_file):
    dom = minidom.parse(xml_file)

    post_count = 0
    for item in dom.getElementsByTagName('item'):

        # only import posts, not pages or other stuff
        if item.getElementsByTagName('wp:post_type')[0].firstChild.nodeValue != 'post':
            continue

        if len(item.getElementsByTagName('title')[0].childNodes) == 0:
            continue

        post = {
            'type': 'text',
            'title': item.getElementsByTagName('title')[0].firstChild.nodeValue.strip().encode('utf-8', 'xmlcharrefreplace'),
            'date': item.getElementsByTagName('pubDate')[0].firstChild.nodeValue,
            'state': POST_STATES.get(item.getElementsByTagName('wp:status')[0].firstChild.nodeValue)
        }

        if post['state'] is None:
            continue

        content = item.getElementsByTagName('content:encoded')[0].firstChild

        if content.__class__.__name__ != 'CDATASection':
            continue

        post['body'] = item.getElementsByTagName('content:encoded')[0].firstChild.nodeValue.encode('utf-8', 'xmlcharrefreplace')

        if app.debug:
            print post["title"]
        else:
            g.tumblr.create_text(tumblog_name,
                                type=post['type'],
                                title=post['title'],
                                body=post['body'],
                                date=post['date'],
                                state=post['state'])

        post_count += 1

    return post_count

if __name__ == '__main__':
    app.run()

########NEW FILE########
