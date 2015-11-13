__FILENAME__ = async_dropbox
#!/usr/bin/env python
#
# Copyright 2011 Dropbox.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tornado.auth
import urllib
from tornado.httpclient import AsyncHTTPClient

class DropboxMixin(tornado.auth.OAuthMixin):
    """Dropbox OAuth authentication.

    Uses the app settings dropbox_consumer_key and dropbox_consumer_secret.

    Usage::

        class DropboxLoginHandler(RequestHandler, DropboxMixin):
            @asynchronous
            def get(self):
                if self.get_argument("oauth_token", None):
                    self.get_authenticated_user(self._on_auth)
                    return
                self.authorize_redirect()

            def _on_auth(self, user):
                if not user:
                    raise tornado.web.HTTPError(500, "Dropbox auth failed")
                # save the user using e.g. set_secure_cookie
    """
    _OAUTH_VERSION = "1.0"
    # note www vs api.dropbox.com in authorize url
    _OAUTH_REQUEST_TOKEN_URL = "https://api.dropbox.com/1/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "https://api.dropbox.com/1/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://www.dropbox.com/1/oauth/authorize"

    def dropbox_request(self, subdomain, path, callback, access_token,
                        post_args=None, put_body=None, **args):
        """Fetches the given API operation.

        The request is defined by a combination of subdomain (either
        "api" or "api-content") and path (such as "/1/metadata/sandbox/").
        See the Dropbox REST API docs for details:
        https://www.dropbox.com/developers/reference/api

        For GET requests, arguments should be passed as keyword arguments
        to dropbox_request.  For POSTs, arguments should be passed
        as a dictionary in `post_args`.  For PUT, data should be passed
        as `put_body`

        Example usage::

            class MainHandler(tornado.web.RequestHandler,
                              async_dropbox.DropboxMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                def get(self):
                    self.dropbox_request(
                        "api", "/1/metadata/sandbox/"
                        access_token=self.current_user["access_token"],
                        callback=self._on_metadata)

                def _on_metadata(self, response):
                    response.rethrow()
                    metadata = json.loads(response.body)
                    self.render("main.html", metadata=metadata)
        """
        url = "https://%s.dropbox.com%s" % (subdomain, path)
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            assert not (put_body and post_args)
            if put_body is not None:
                method = "PUT"
            elif post_args is not None:
                method = "POST"
            else:
                method = "GET"
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method)
            args.update(oauth)
        if args: url += "?" + urllib.urlencode(args)
        http = AsyncHTTPClient()
        if post_args is not None:
            http.fetch(url, method=method, body=urllib.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, method=method, body=put_body, callback=callback)

    def _oauth_consumer_token(self):
        return dict(
            key=self.settings["dropbox_consumer_key"],
            secret=self.settings["dropbox_consumer_secret"],
            )

    def _oauth_get_user(self, access_token, callback):
        callback(dict(
                access_token=access_token,
                uid=self.get_argument('uid'),
                ))

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

import json
import os

from tornado.escape import utf8
from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line, parse_config_file
from tornado.web import RequestHandler, Application, asynchronous, authenticated, HTTPError

from async_dropbox import DropboxMixin

define('port', default=8888)
define('flagfile', default='config.flags')
define('debug', default=False)
define('cookie_secret', default="3f8c0458deffeb471fc4142c1c0ad232")

# These don't have defaults; see README for details.
define('dropbox_consumer_key')
define('dropbox_consumer_secret')

class BaseHandler(RequestHandler):
    def get_current_user(self):
        if self.get_secure_cookie("user"):
            return json.loads(self.get_secure_cookie("user"))
        else:
            return None

    def get_access_token(self):
        # json turns this into unicode strings, but we need bytes for oauth
        # signatures.
        return dict((utf8(k), utf8(v)) for (k, v) in self.current_user["access_token"].iteritems())

class RootHandler(BaseHandler, DropboxMixin):
    @authenticated
    @asynchronous
    def get(self):
        self.dropbox_request('api', '/1/metadata/sandbox/', self.on_metadata,
                             self.get_access_token(),
                             list="true")
    
    def on_metadata(self, response):
        response.rethrow()
        metadata = json.load(response.buffer)
        self.render("index.html", metadata=metadata)

class DeleteHandler(BaseHandler, DropboxMixin):
    @authenticated
    @asynchronous
    def get(self):
        # This really shouldn't be a GET, but the point is to demonstrate
        # the dropbox api rather than demonstrate good web practices...
        self.dropbox_request(
            'api', '/1/fileops/delete', self.on_delete,
            self.get_access_token(),
            post_args=dict(
                root='sandbox',
                path=self.get_argument('path')))

    def on_delete(self, response):
        response.rethrow()
        self.redirect('/')

class CreateHandler(BaseHandler, DropboxMixin):
    @authenticated
    @asynchronous
    def post(self):
        self.dropbox_request(
            'api-content',
            '/1/files_put/sandbox/%s' % self.get_argument('filename'),
            self.on_put_done,
            self.get_access_token(),
            put_body="Hi, I'm a text file!")

    def on_put_done(self, response):
        response.rethrow()
        self.redirect('/')

class DropboxLoginHandler(BaseHandler, DropboxMixin):
    @asynchronous
    def get(self):
        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self._on_auth)
            return
        self.authorize_redirect(callback_uri=self.request.full_url())

    def _on_auth(self, user):
        if not user:
            raise HTTPError(500, "Dropbox auth failed")
        self.set_secure_cookie("user", json.dumps(user))
        self.redirect('/')

class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect("/")

def main():
    parse_command_line()
    parse_config_file(options.flagfile)

    settings = dict(
        login_url='/login',
        debug=options.debug,
        template_path=os.path.join(os.path.dirname(__file__), 'templates'),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),

        cookie_secret=options.cookie_secret,
        dropbox_consumer_key=options.dropbox_consumer_key,
        dropbox_consumer_secret=options.dropbox_consumer_secret,
        )
    app = Application([
            ('/', RootHandler),
            ('/delete', DeleteHandler),
            ('/create', CreateHandler),
            ('/login', DropboxLoginHandler),
            ('/logout', LogoutHandler),
            ], **settings)
    app.listen(options.port)
    IOLoop.instance().start()

if __name__ == '__main__':
    main()

########NEW FILE########
