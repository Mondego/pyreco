__FILENAME__ = appengine_config
from gaesessions import SessionMiddleware
import endpoints

# Make webapp.template use django 1.2
webapp_django_version = '1.2'

def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, no_datastore=True, cookie_key=endpoints.COOKIE_KEY)
    return app
########NEW FILE########
__FILENAME__ = auth
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from django.utils import simplejson as json
from gaesessions import get_current_session

import logging
import endpoints
import os
import urllib

def get_params():
    return {
              'scope':endpoints.SCOPE,
              'state':'/profile',
              'redirect_uri': endpoints.REDIRECT_URI,
              'response_type': endpoints.RESPONSE_TYPE,
              'client_id':endpoints.CLIENT_ID
            }
                   
                 
def get_target_url():
    params = get_params()
    return endpoints.AUTH_ENDPOINT + '?' + urllib.urlencode(params)

def validate_access_token(access_token):    
        # check the token audience using exact match (TOKENINFO)
        url = endpoints.TOKENINFO_ENDPOINT + '?access_token=' + access_token
    
        tokeninfo = json.loads(urlfetch.fetch(url).content)
        
        if('error' in tokeninfo) or (tokeninfo['audience'] != endpoints.CLIENT_ID):
            logging.warn('invalid access token = %s' % access_token)
            return False
        else:
            return True

class LogoutHandler(webapp.RequestHandler):
    def get(self):      
        session = get_current_session()
        session.terminate()
        
        #need to clean this up...
        logouturl = 'https://accounts.google.com/o/oauth2/auth?scope=https://www.googleapis.com/auth/userinfo.email+https://www.googleapis.com/auth/userinfo.profile&state=/profile&redirect_uri=http://localhost:8092/oauthcallback&response_type=token&client_id=812741506391.apps.googleusercontent.com'
        logoutparams = {'continue': logouturl}
        
        logging.info("encoded params == %s" % urllib.urlencode(logoutparams))
        
        self.redirect('https://accounts.google.com/logout?service=lso&%s' % urllib.urlencode(logoutparams))

class CallbackHandler(webapp.RequestHandler):
    def get(self):
        template_info = {
                          'catchtoken_uri' : endpoints.CATCHTOKEN_URI
                        }
        self.response.out.write(template.render('templates/scripthandler.html', template_info))
        
class CatchTokenHandler(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        a_t = self.request.get('access_token')
        
        if not validate_access_token(a_t):
            self.error(400)
        
        session.regenerate_id()
        session['access_token'] = a_t

class CodeHandler(webapp.RequestHandler):
    def get(self):
        a_c = self.request.get('code')
        logging.warn("Code: %s" % a_c)
        ac_payload = {
            'code':a_c,
            'client_id':endpoints.CLIENT_ID,
            'client_secret':endpoints.CLIENT_SECRET,
            'redirect_uri': endpoints.REDIRECT_URI,
            'grant_type':'authorization_code'
        }
        
        encoded_payload = urllib.urlencode(ac_payload)
        
        logging.info('encoded payload: %s' % encoded_payload)
        
        ac_result = json.loads(urlfetch.fetch(url=endpoints.CODE_ENDPOINT,
                                              payload=encoded_payload,
                                              method=urlfetch.POST,
                                              headers={'Content-Type':'application/x-www-form-urlencoded'}).content)
                                              
        logging.info('auth code exchange result: %s' % ac_result)                                      
        
        a_t = ac_result['access_token']
        if not validate_access_token(a_t):
            self.error(400)
        
        session = get_current_session()
        session.regenerate_id()
        session['access_token'] = a_t
        
        self.redirect('/profile')
            
        
class ProfileHandler(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        template_info = {'target_url' : get_target_url()}
        
        if ('access_token' in session):
            # we need to validate the access_token (long-lived sessions, token might have timed out)
            if(validate_access_token(session['access_token'])):            
                # get the user profile information (USERINFO)
                userinfo = json.loads(urlfetch.fetch(endpoints.USERINFO_ENDPOINT,
                                                    headers={'Authorization': 'Bearer ' + session['access_token']}).content)
                
                template_info = {
                                  'target_url' : get_target_url(),
                                  'userinfo' : userinfo
                                }
        
        self.response.out.write(template.render('templates/profileview.html', template_info))
########NEW FILE########
__FILENAME__ = endpoints
import os

# Google's OAuth 2.0 endpoints
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
CODE_ENDPOINT = "https://accounts.google.com/o/oauth2/token"
TOKENINFO_ENDPOINT = "https://accounts.google.com/o/oauth2/tokeninfo"
USERINFO_ENDPOINT = 'https://www.googleapis.com/oauth2/v1/userinfo'
SCOPE = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
LOGOUT_URI = 'https://accounts.google.com/logout'

# client ID / secret & cookie key
CLIENT_ID = 'updatetoyourclientid'
CLIENT_SECRET = 'updatetoyourclientsecret'
COOKIE_KEY = 'createacookiekey - probably using os.urandom(64)'

is_secure = os.environ.get('HTTPS') == 'on'
protocol = {False: 'http', True: 'https'}[is_secure]

ROOT_URI = protocol +'://' + os.environ["HTTP_HOST"]

RESPONSE_TYPE='token'

if (RESPONSE_TYPE == 'token'):
    REDIRECT_URI = ROOT_URI + '/oauthcallback'
elif (RESPONSE_TYPE == 'code'):
    REDIRECT_URI = ROOT_URI + '/code'
else:
    REDIRECT_URI = ROOT_URI + '/code'

CATCHTOKEN_URI = ROOT_URI + '/catchtoken'    






########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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
#
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

import auth

class GotoRootHandler(webapp.RequestHandler):
    def get(self):
        self.redirect('/profile')

def main():
    application = webapp.WSGIApplication([('/oauthcallback', auth.CallbackHandler),
                                          ('/catchtoken', auth.CatchTokenHandler),
                                          ('/profile', auth.ProfileHandler),
                                          ('/logout', auth.LogoutHandler),
                                          ('/code', auth.CodeHandler),
                                          ('/.*', GotoRootHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()

########NEW FILE########
