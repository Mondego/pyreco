__FILENAME__ = appengine_config
from gaesessions import SessionMiddleware

# suggestion: generate your own random key using os.urandom(64)
# WARNING: Make sure you run os.urandom(64) OFFLINE and copy/paste the output to
# this file.  If you use os.urandom() to *dynamically* generate your key at
# runtime then any existing sessions will become junk every time you start,
# deploy, or update your app!
import os
COOKIE_KEY = 'do not use this key'

def webapp_add_wsgi_middleware(app):
  from google.appengine.ext.appstats import recording
  app = SessionMiddleware(app, cookie_key=COOKIE_KEY)
  app = recording.appstats_wsgi_middleware(app)
  return app

########NEW FILE########
__FILENAME__ = cleanup_sessions
from gaesessions import delete_expired_sessions
while not delete_expired_sessions():
    pass

########NEW FILE########
__FILENAME__ = main
from datetime import datetime
import os
import urllib

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from google.appengine.api import urlfetch
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from gaesessions import get_current_session

# configure the RPX iframe to work with the server were on (dev or real)
ON_LOCALHOST = ('Development' == os.environ['SERVER_SOFTWARE'][:11])
if ON_LOCALHOST:
    import logging
    if os.environ['SERVER_PORT'] == '80':
        BASE_URL = 'localhost'
    else:
        BASE_URL = 'localhost:%s' % os.environ['SERVER_PORT']
else:
    BASE_URL = 'your-app-id.appspot.com'
LOGIN_IFRAME = '<iframe src="http://gae-sesssions-demo.rpxnow.com/openid/embed?token_url=http%3A%2F%2F' + BASE_URL + '%2Frpx_response" scrolling="no" frameBorder="no" allowtransparency="true" style="width:400px;height:240px"></iframe>'

def redirect_with_msg(h, msg, dst='/'):
    get_current_session()['msg'] = msg
    h.redirect(dst)

# create our own simple users model to track our user's data
class MyUser(db.Model):
    email           = db.EmailProperty()
    display_name    = db.TextProperty()
    past_view_count = db.IntegerProperty(default=0) # just for demo purposes ...

class RPXTokenHandler(webapp.RequestHandler):
    """Receive the POST from RPX with our user's login information."""
    def post(self):
        token = self.request.get('token')
        url = 'https://rpxnow.com/api/v2/auth_info'
        args = {
            'format': 'json',
            'apiKey': 'df117e092c656c1bbd79e3e0fdb2a63ba9e3fc99',
            'token': token
        }
        r = urlfetch.fetch(url=url,
                           payload=urllib.urlencode(args),
                           method=urlfetch.POST,
                           headers={'Content-Type':'application/x-www-form-urlencoded'})
        json_data = json.loads(r.content)

        # close any active session the user has since he is trying to login
        session = get_current_session()
        if session.is_active():
            session.terminate()

        if json_data['stat'] == 'ok':
            # extract some useful fields
            info = json_data['profile']
            oid = info['identifier']
            email = info.get('email', '')
            try:
                display_name = info['displayName']
            except KeyError:
                display_name = email.partition('@')[0]

            # get the user's record (ignore TransactionFailedError for the demo)
            user = MyUser.get_or_insert(oid, email=email, display_name=display_name)

            # start a session for the user (old one was terminated)
            session['me'] = user
            session['pvsli'] = 0 # pages viewed since logging in

            redirect_with_msg(self, 'success!')
        else:
            redirect_with_msg(self, 'your login attempt FAILED!')

class MainPage(webapp.RequestHandler):
    def render_template(self, file, template_vals):
        path = os.path.join(os.path.dirname(__file__), 'templates', file)
        self.response.out.write(template.render(path, template_vals))

    def get(self):
        session = get_current_session()
        d = dict(login_form=LOGIN_IFRAME)
        if session.has_key('msg'):
            d['msg'] = session['msg']
            del session['msg'] # only show the message once

        if session.has_key('pvsli'):
            session['pvsli'] += 1
            d['user'] = session['me']
            d['num_now'] = session['pvsli']
        self.render_template("index.html", d)

class LogoutPage(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        if session.has_key('me'):
            # update the user's record with total views
            user = session['me']
            user.past_view_count += session['pvsli']
            user.put()
            session.terminate()
            redirect_with_msg(self, 'Logout complete: goodbye ' + user.display_name)
        else:
            redirect_with_msg(self, "How silly, you weren't logged in")

application = webapp.WSGIApplication([('/', MainPage),
                                      ('/logout', LogoutPage),
                                      ('/rpx_response', RPXTokenHandler),
                                     ])

def main(): run_wsgi_app(application)
if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = appengine_config
from gaesessions import SessionMiddleware

# suggestion: generate your own random key using os.urandom(64)
# WARNING: Make sure you run os.urandom(64) OFFLINE and copy/paste the output to
# this file.  If you use os.urandom() to *dynamically* generate your key at
# runtime then any existing sessions will become junk every time you start,
# deploy, or update your app!
import os
COOKIE_KEY = 'do not use this key'

def webapp_add_wsgi_middleware(app):
  from google.appengine.ext.appstats import recording
  app = SessionMiddleware(app, cookie_key=COOKIE_KEY)
  app = recording.appstats_wsgi_middleware(app)
  return app

########NEW FILE########
__FILENAME__ = main
import os

from google.appengine.api import users
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from gaesessions import get_current_session

def redirect_with_msg(h, msg, dst='/'):
    get_current_session()['msg'] = msg
    h.redirect(dst)

def render_template(h, file, template_vals):
    path = os.path.join(os.path.dirname(__file__), 'templates', file)
    h.response.out.write(template.render(path, template_vals))

# create our own simple users model to track our user's data
class MyUser(db.Model):
    user = db.UserProperty()
    past_view_count = db.IntegerProperty(default=0) # just for demo purposes ...

class LoginHandler(webapp.RequestHandler):
    """Receive the POST from RPX with our user's login information."""
    def get(self):
        user = users.get_current_user()
        if not user:
            return redirect_with_msg(self, 'Try logging in first.')

        # close any active session the user has since he is trying to login
        session = get_current_session()
        if session.is_active():
            session.terminate()

        # get the user's record (ignore TransactionFailedError for the demo)
        user = MyUser.get_or_insert(user.user_id(), user=user)

        # start a session for the user (old one was terminated)
        session['me'] = user
        session['pvsli'] = 0 # pages viewed since logging in
        redirect_with_msg(self, 'success!')

class MainPage(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        d = dict(login_url=users.create_login_url("/login_response"))
        if session.has_key('msg'):
            d['msg'] = session['msg']
            del session['msg'] # only show the message once

        if session.has_key('pvsli'):
            session['pvsli'] += 1
            d['myuser'] = session['me']
            d['num_now'] = session['pvsli']
        render_template(self, "index.html", d)

class Page2(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        d = {}
        if session.has_key('pvsli'):
            session['pvsli'] += 1
            d['myuser'] = session['me']
            d['num_now'] = session['pvsli']
        render_template(self, "page2.html", d)

class LogoutPage(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        if session.has_key('me'):
            # update the user's record with total views
            myuser = session['me']
            myuser.past_view_count += session['pvsli']
            myuser.put()
            session.terminate()
            redirect_with_msg(self, 'Logout complete: goodbye ' + myuser.user.nickname())
        else:
            redirect_with_msg(self, "How silly, you weren't logged in")

application = webapp.WSGIApplication([('/', MainPage),
                                      ('/2', Page2),
                                      ('/logout', LogoutPage),
                                      ('/login_response', LoginHandler),
                                     ])

def main(): run_wsgi_app(application)
if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = conf
# gae-sessions documentation build configuration file

import sys, os
sys.path.append(os.path.abspath('../'))

extensions = ['sphinx.ext.autodoc']
templates_path = []
source_suffix = '.rst'
master_doc = 'docindex'
project = u'gae-sessions'
copyright = u'2011, David Underhill'
release = version = '1.07'
exclude_trees = ['_build']

pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = []
htmlhelp_basename = 'gae-sessionsdoc'

latex_documents = [
  ('index', 'gae-sessions.tex', u'gae-sessions Documentation',
   u'David Underhill', 'manual'),
]

########NEW FILE########
__FILENAME__ = generate_cov_report
def generate_coverage():
    import coverage
    cov = coverage.coverage()
    cov.load()
    cov.start()
    import gaesessions, main, SessionTester  # our nose tests miss the import lines
    cov.stop()
    cov.save()
    cov.html_report(directory="covhtml", omit_prefixes=["/usr","webtest"])

if __name__ == '__main__': generate_coverage()

########NEW FILE########
__FILENAME__ = main
from base64 import b64decode, b64encode
import logging
import pickle

from google.appengine.api import memcache
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from gaesessions import get_current_session, Session, SessionMiddleware, SessionModel, delete_expired_sessions

logger = logging.getLogger('SERVER')
logger.setLevel(logging.DEBUG)

def trim_output_str(s, max_len=512):
    if len(s) > max_len:
        return s[:max_len] + '...'
    else:
        return s

class TestModel(db.Model):
    s = db.StringProperty()
    i = db.IntegerProperty()
    f = db.FloatProperty()

    def __cmp__(self, o):
        c = cmp(self.s, o.s)
        if c != 0: return c
        c = cmp(self.i, o.i)
        if c != 0: return c
        return cmp(self.f, o.f)

    def __repr__(self):
        return 'TestModel%s' % self.key().id_or_name()

# note: these entities are about 900B when stored as a protobuf
def make_entity(i):
    """Create the entity just like it would be in the datastore (so our tests don't actually go to the datastore)."""
    return TestModel(key=db.Key.from_path('TestModel', str(i)), s="a"*500, i=i, f=i*10.0)

class SessionState(object):
    def __init__(self, sid, data, dirty, in_mc, in_db):
        self.sid = sid
        if not data:
            self.data = {}  # treat None and empty dictionary the same
        else:
            self.data = data
        self.in_mc = in_mc
        self.in_db = in_db  # whether it is in the db AND accessible (i.e., db is up)

    def __cmp__(self, s):
        c = cmp(self.sid, s.sid)
        if c != 0: return c
        c = cmp(self.data, s.data)
        if c != 0: return c
        c = cmp(self.in_mc, s.in_mc)
        if c != 0: return c
        return cmp(self.in_db, s.in_db)

    def __str__(self):
        return 'sid=%s in_mc=%s in_db=%s data=%s' % (self.sid, self.in_mc, self.in_db, self.data)

def make_ss(session):
    sid = session.sid
    if not sid:
        in_mc = in_db = False
    else:
        pdump = memcache.get(sid)
        if pdump and session.data==Session._Session__decode_data(pdump):
            in_mc = True
        else:
            in_mc = False

        try:
            sm = SessionModel.get_by_key_name(sid)
            if sm and session.data==Session._Session__decode_data(sm.pdump):
                in_db = True
            else:
                in_db = False
                if sm:
                    logger.info('in db, but stale: current=%s db=%s' % (session.data, Session._Session__decode_data(sm.pdump)))
                else:
                    logger.info('session not in db at all')
        except Exception, e:
            logging.warn('db failed: %s => %s' % (type(e), e))
            in_db = False  # db failure (perhaps it is down)
    return SessionState(sid, session.data, session.dirty, in_mc, in_db)

class CleanupExpiredSessions(webapp.RequestHandler):
    def get(self):
        num_before = SessionModel.all().count()
        delete_expired_sessions()
        num_after = SessionModel.all().count()
        self.response.out.write('%d,%d' % (num_before, num_after))

class DeleteAll(webapp.RequestHandler):
    def get(self):
        memcache.flush_all()
        db.delete(SessionModel.all(keys_only=True).fetch(1000))

class FlushMemcache(webapp.RequestHandler):
    def get(self):
        memcache.flush_all()
        self.response.out.write('ok')

class RPCHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('ok')

    def post(self):
        try:
            api_statuses = pickle.loads(b64decode(self.request.get('api_statuses')))
        except Exception, e:
            logger.error('failed to unpickle api_statuses: %s' % e)
            return self.error(500)
        logger.info("api statuses: %s" % api_statuses)

        try:
            rpcs = pickle.loads(b64decode(self.request.get('rpcs')))
        except Exception, e:
            logger.error('failed to unpickle RPCs: %s' % e)
            return self.error(500)
        logger.info("rpcs: %s" % trim_output_str(str(rpcs)))

        # TODO: apply the API statuses; remember to unapply before returning too

        session = get_current_session()
        outputs = []
        for fname,args,kwargs in rpcs:
            try:
                f = getattr(session, fname)
                try:
                    output = f(*args, **kwargs)
                except Exception, e:
                    output = '%s-%s' % (type(e), e)
                outputs.append(output)
                logger.info(trim_output_str('%s(%s, %s) => %s (type:%s)' % (fname, args, kwargs, output, type(output))))
            except Exception, e:
                logger.error(trim_output_str('failed to execute RPC: %s(session, *%s, **%s) - %s' % (fname,args,kwargs,e)))
                return self.error(500)
        self.request.environ['test_outputs'] = outputs
        logger.info('END OF REQUEST HANDLER')

class GetSession(webapp.RequestHandler):
    def get(self):
        s = Session(sid=self.request.get('sid'), cookie_key='dontcare')
        s.ensure_data_loaded()
        self.response.out.write(b64encode(pickle.dumps(s.data)))

class TestingMiddleware(object):
    """Dumps session state and environ['test_outputs'] into the response if the
    'test_outputs' key is set.  This middleware should wrap the sessions
    middleware so that the dumped session state is the final state (i.e., after
    the middleware has finished and no more changes are being made to it).
    """
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        # On app engine and the dev server, os.environ also contains HTTP_COOKIE
        # and gae-sessions relies on this so we copy it over for this test.
        # (running with nose-gae and webtest this doesn't happen)
        import os
        os.environ['HTTP_COOKIE'] = environ.get('HTTP_COOKIE', '')

        def my_start_response(status, headers, exc_info=None):
            ret = start_response(status, headers, exc_info)
            if environ.has_key('test_outputs'):
                outputs = environ['test_outputs']
                resp = (outputs, make_ss(get_current_session()))
                # add to the response ...
                content = b64encode(pickle.dumps(resp))
                ret(content)
                headers.append(('Content-Length', len(content)))
            return ret

        return self.app(environ, my_start_response)

def make_application(**kwargs):
    app = webapp.WSGIApplication([('/',               RPCHandler),
                                  ('/flush_memcache', FlushMemcache),
                                  ('/cleanup',        CleanupExpiredSessions),
                                  ('/get_by_sid',     GetSession),
                                  ('/delete_all',     DeleteAll),
                                  ], debug=True)
    return TestingMiddleware(SessionMiddleware(app, **kwargs))

DEFAULT_COOKIE_KEY = '\xedd\xa7\x83\xf2\xd3\xdc%!U8s\x10\x19\xae\x8f\xce\x82\x94\x92\x9c\xf4`\xb4\xca\xcb\x91.\x0eIA~\xc5\xc0\xd5\xaeeIJ\xaf\x88}=\xc8\x96\xed.\xcb\xe7C\x81\xa3\r\xca\xeb\x1c\xfc\xa4V\xc5l\xf7+\xec'
def main(): run_wsgi_app(make_application(cookie_key=DEFAULT_COOKIE_KEY))
if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = SessionTester
from base64 import b64decode, b64encode
import logging
from nose.tools import assert_equal
import pickle
import time
from webtest import TestApp
from main import DEFAULT_COOKIE_KEY, make_application, SessionState, trim_output_str
from gaesessions import Session, SID_LEN, SIG_LEN

logging.getLogger().name = 'seslib'  # root logger is only used by gae-sessions itself
logger = logging.getLogger('TESTER')
logger.setLevel(logging.DEBUG)

def session_method(f):
    """Decorator which returns a function which calls the original function,
    records its output, and adds the function+args to the list of calls to be
    duplicated on the test web server too.
    """
    def stub(*args, **kwargs):
        myself = args[0]
        if myself.rpcs is None:
            raise RuntimeError("you must start a request before you can call a session method")
        rpc = (f.__name__, args[1:], kwargs)
        myself.rpcs.append(rpc)
        try:
            output = f(*args, **kwargs)
            caught_exception = None
        except Exception, e:
            output = '%s-%s' % (type(e), e)
            caught_exception = e
        myself.outputs.append(output)
        logger.info(trim_output_str('rpc enqueud: %s(%s, %s)' % (f.__name__,args[1:],kwargs)))
        if caught_exception:
            raise caught_exception
        else:
            return output
    return stub

# matches any sid
ANY_SID = object()

class AppWithMultipleClients(TestApp):
    def __init__(self, *args, **kwargs):
        super(AppWithMultipleClients, self).__init__(*args, **kwargs)
        self.client_cookies = {}
        self.current_client = None

    def set_client(self, client):
        self.current_client = client
        self.cookies = self.client_cookies.get(client, {})

    def get_cookies(self, client):
        return self.client_cookies.get(client, {})

    def set_cookies(self, client, cookies):
        self.client_cookies[client] = cookies

    def do_request(self, req, status, expect_errors):
        ret = super(AppWithMultipleClients, self).do_request(req, status, expect_errors)
        self.client_cookies[self.current_client] = self.cookies
        return ret

class SessionTester(object):
    """Manages testing a session by executing a mocked version of a Session and
    the "real thing" (being run by main.py) and then verifying that they output
    the same information and end up in the same state.

    st may be a reference to another SessionTester.  If so, they will share the
    same instance of the webapp => same datastore and all.  Cookies will be
    unique to each SessionTester instance, so each is like a separate client.

    If st is None, then a new webapp is initialized and the datastore and
    memcache are cleared.
    """
    def __init__(self, st=None, **kwargs):
        if not kwargs.has_key('cookie_key') and st is None:
            kwargs['cookie_key'] = DEFAULT_COOKIE_KEY
        if st is None:
            self.app = AppWithMultipleClients(make_application(**kwargs))
            assert self.app.get('/delete_all').status[:3] == '200'
            self.app_args = kwargs
        else:
            self.app = st.app  # share the same webapp, but we'll use our own cookies
            self.app_args = st.app_args
            assert len(kwargs)==0, "no args should be passed other than st if st is given"

        self.ss = self.new_session_state()
        self.rpcs = None          # calls on Session object waiting to be made remotely
        self.outputs = None       # outputs of local procedure calls
        self.api_statuses = None  # whether various APIs are up or down

        # extra checks; if None, then don't do them
        self.check_expir = None
        self.check_sid_is_not = None

        # if the session gets big and goes to db but then shrinks and
        # goes back to cookie-only, it is ok if it still in the db after
        # that, though our mock will say it shouldn't be.  If this is
        # true, self.ss.in_mc/db will be set to True if the remote ss
        # has in_mc/in_db as True.
        self.ok_if_in_mc_remotely = False
        self.ok_if_in_db_remotely = False
        self.data_should_be_in_cookie = False

    def get_cookies(self):
        return self.app.get_cookies(self)

    def set_cookies(self, cookies):
        return self.app.set_cookies(self, cookies)

    def new_session_state(self):
        self.ss = SessionState(None, {}, False, False, False)
        self.ok_if_in_mc_remotely = False
        self.ok_if_in_db_remotely = False
        self.data_should_be_in_cookie = False
        self.dirty = False
        self.keys_in_mc_only = {}
        return self.ss

    def start_request(self, mc_can_read=True, mc_can_write=True, db_can_read=True, db_can_write=True):
        """Initiates a new batch of session operations which will all be
        performed within one request and then checked when
        finish_request_and_check() is called.
        """
        if self.rpcs:
            raise RuntimeError("tried to start a request before finishing the previous request")

        self.api_statuses = dict(mc_can_rd=mc_can_read, mc_can_wr=mc_can_write,
                                 db_can_rd=db_can_read, db_can_wr=db_can_write)
        self.rpcs = []
        self.outputs = []

        # if the old session expired, start a blank slate
        if self._get_expiration() <= int(time.time()):
            self.new_session_state()

    def finish_request_and_check(self, expect_failure=False):
        """Executes the set of RPCs requested since start_request() was called
        and checks to see if the response is successful and matches the
        expected Session state.  Outputs of each RPC are also compared with the
        expected outputs.
        """
        if self.rpcs is None:
            raise RuntimeError("tried to finish a request before starting a request")

        # like the real thing, call save() at the end of a request
        self.save()

        logger.info(trim_output_str('Running request: rpcs=%s' % self.rpcs))
        self.app.set_client(self)
        resp = self.app.post('/', dict(rpcs=b64encode(pickle.dumps(self.rpcs)), api_statuses=b64encode(pickle.dumps(self.api_statuses))))
        assert resp.status[:3] == '200', 'did not get code 200 back: %s' % resp
        remote_outputs, remote_ss = pickle.loads(b64decode(resp.body))

        if self.ok_if_in_db_remotely and remote_ss.in_db:
            self.ss.in_db = remote_ss.in_db
        if self.ok_if_in_mc_remotely and remote_ss.in_mc:
            self.ss.in_mc = remote_ss.in_mc
        if self.ss.sid == ANY_SID:
            self.ss.sid = remote_ss.sid

        # expire the memcache if it is past the expir time (this doesn't handle
        # expiration mid-usage, but the test cases workaround that)
        has_expired_now = self._get_expiration() <= int(time.time())
        if has_expired_now:
            self.ss.in_mc = False

        if expect_failure:
            assert remote_ss.in_db is False, "failure expected: data should not be in the datastore"
            assert remote_ss.in_mc is False, "failure expected: data should not be in memcache"
            self.api_statuses = self.outputs = self.rpcs = None
            logger.info('Request completed (expected failure and got it)')
            return

        assert self.ss == remote_ss, 'mismatch b/w local and remote states:\n\tlocal:  %s\n\tremote: %s' % (self.ss, remote_ss)
        assert len(remote_outputs)==len(self.outputs), 'internal test error: number outputs should be the same'
        assert len(remote_outputs)==len(self.rpcs), 'internal test error: number outputs should be the same as the number of RPCs'
        for i in xrange(len(remote_outputs)):
            l, r = self.outputs[i], remote_outputs[i]
            assert l==r, 'output for rpc #%d (%s) does not match:\n\tlocal:  %s\n\tremote: %s' % (i, self.rpcs[i], l, r)
        logger.info('state (local and remote): %s' % trim_output_str(str(self.ss)))

        # extra checks we sometimes need to do
        if self.check_expir:
            expir_remote = int(remote_ss.sid.split('_')[0])
            assert self.check_expir==expir_remote, "remote expiration %s does match the expected expiration %s" % (expir_remote, self.check_expir)
            self.check_expir = None
        if self.check_sid_is_not:
            assert self.check_sid_is_not != remote_ss.sid, 'remote sid should not be %s' % remote_ss.sid

        self.__check_cookies()
        self.api_statuses = self.outputs = self.rpcs = None
        logger.info('Request completed')

    def __check_cookies(self):
        # check the cookie to make sure it specifies a SID and is signed properly
        cookies = self.app.cookies
        if len(cookies)==0:
            if self.ss.sid:
                assert False, 'no cookie data received but we expected SID to be present'
            else:
                return # no session + no cookie_data = correct!
        keys = cookies.keys()
        keys.sort()
        aggr = ''.join(cookies[k] for k in keys)
        sig = aggr[:SIG_LEN]
        sid = aggr[SIG_LEN:SIG_LEN+SID_LEN]
        data = aggr[SIG_LEN+SID_LEN:]
        pdump = b64decode(data)
        if sid is '':
            sid = None
        assert self.ss.sid == sid, 'cookie specifies SID %s but we expected %s' % (sid, self.ss.sid)
        if not sid:
            assert sig is '', "sig should not be present if there is no sid"
        else:
            exp_sig = Session._Session__compute_hmac(self.app_args['cookie_key'], sid, pdump)
            assert sig==exp_sig, 'cookie received with invalid sig %s (expected %s)' % (sig, exp_sig)

        # check the cookies' data too
        if self.data_should_be_in_cookie:
            if pdump:
                data = Session._Session__decode_data(pdump)
            else:
                data = None
            assert self.ss.data==data, 'cookie does not contain the correct data:\n\tlocal:  %s\n\tcookie: %s' % (self.ss.data, data)
        else:
            assert len(pdump)==0, "cookie specifies data but there shouldn't be any"

    def noop(self):
        """Starts and finishes a request which does nothing to the session."""
        self.start_request()
        self.finish_request_and_check()

    def flush_memcache(self):
        """Deletes everything from memcache."""
        self.ok_if_in_mc_remotely = False
        self.ss.in_mc = False
        if self.app_args['no_datastore'] and not self.data_should_be_in_cookie:
            # session is gone
            self.check_sid_is_not = self.ss.sid
            self.new_session_state()

        # remove anything that was only in memcache
        if not self.data_should_be_in_cookie:
            for k in self.keys_in_mc_only.iterkeys():
                self.ss.data.pop(k, None)
        self.keys_in_mc_only.clear()

        resp = self.get_url('/flush_memcache')
        assert 'ok' in resp.body

    def verify_active_sessions_in_db(self, num_before, num_after=None):
        """Expires any old sessions and checks that there were num_before
        sessions before old ones were expired, and num_after after old ones
        were expired.  If only num_before is specified, then we check that the
        number if sessions is that number before and after expiring old sessions."""
        if num_after is None:
            num_after = num_before
        resp = self.get_url('/cleanup')
        expected = '%d,%d' % (num_before,num_after)
        assert_equal(resp.body, expected)

    def get_url(self, url):
        """Wrapper around TestApp.get() which sets the cookies up for the requester."""
        self.app.set_client(self)
        return self.app.get(url)

    # **************************************************************************
    # helpers for our mocks of Session methods
    def __set_in_mc_db_to_true_if_ok(self, force_persist=False):
        enc_len = len(Session._Session__encode_data(self.ss.data))
        if enc_len * 4 / 3 <= self.app_args['cookie_only_threshold']:
            self.ss.in_db = self.ss.in_mc = False  # cookie-only
            self.data_should_be_in_cookie = True
            if not force_persist:
                return
        else:
            self.data_should_be_in_cookie = False
        # once its into mc, it will stay there until terminate() or a flush_all()
        self.ok_if_in_mc_remotely = True

        if self.dirty and self.dirty is not Session.DIRTY_BUT_DONT_PERSIST_TO_DB:
            self.ss.in_db = not self.app_args['no_datastore'] and self.api_statuses['db_can_wr'] and self.api_statuses['db_can_rd']
            if self.ss.in_db:
                self.ok_if_in_db_remotely = True  # once its in, it will stay there until terminate()
                self.keys_in_mc_only.clear()  # pushed them all to the db
        elif self.dirty is Session.DIRTY_BUT_DONT_PERSIST_TO_DB:
            self.ss.in_db = False

        self.ss.in_mc = self.api_statuses['mc_can_wr'] and self.api_statuses['mc_can_rd']

    def __start(self, expiration_ts=None):
        self.ss.data = {}
        self.ss.sid = ANY_SID
        self.dirty = True
        self.__set_in_mc_db_to_true_if_ok()
        if expiration_ts:
            self.check_expir = int(expiration_ts)

    # mocks for all the 'public' methods on Session
    @session_method
    def make_cookie_headers(self):
        raise NotImplementedError("we don't test this directly")

    @session_method
    def is_active(self):
        return self.ss.sid is not None

    @session_method
    def ensure_data_loaded(self):
        pass  # our data is always loaded

    @session_method
    def get_expiration(self):
        return self._get_expiration()
    def _get_expiration(self):
        try:
            return int(self.ss.sid.split('_')[0])
        except:
            return 0

    @session_method
    def regenerate_id(self, expiration_ts=None):
        if self.ss.sid:
            self.check_sid_is_not = self.ss.sid
            if expiration_ts is None:
                self.check_expir = int(self.ss.sid.split('_')[0])
            else:
                self.check_expir = expiration_ts
            self.ss.sid = ANY_SID
            self.dirty = True

    @session_method
    def start(self, expiration_ts=None):
        self.__start(expiration_ts)

    @session_method
    def terminate(self, clear_data=True):
        self.ss.sid = None
        self.ss.data = {}
        self.dirty = False
        self.ss.in_db = False
        self.ss.in_mc = False
        self.data_should_be_in_cookie = False

    @session_method
    def save(self, persist_even_if_using_cookie=False):
        if self.ss.sid and self.dirty:
            self.__set_in_mc_db_to_true_if_ok(persist_even_if_using_cookie)
        self.dirty = False

    @session_method
    def clear(self):
        self.ss.data.clear()
        if self.ss.sid:
            self.dirty = True

    @session_method
    def get(self, key, default=None):
        return self.ss.data.get(key, default)

    @session_method
    def has_key(self, key):
        return self.ss.data.has_key(key)

    @session_method
    def pop(self, key, default=None):
        self.dirty = True
        return self.ss.data.pop(key, default)

    @session_method
    def pop_quick(self, key, default=None):
        if not self.dirty:
            self.dirty = Session.DIRTY_BUT_DONT_PERSIST_TO_DB
        self.keys_in_mc_only.pop(key, None)
        return self.ss.data.pop(key, default)

    @session_method
    def set_quick(self, key, value):
        if not self.ss.sid:
            self.__start()
        if not self.dirty:
            self.dirty = Session.DIRTY_BUT_DONT_PERSIST_TO_DB
        self.keys_in_mc_only[key] = True
        self.ss.data.__setitem__(key, value)
    @session_method
    def __getitem__(self, key):
        return self.ss.data.__getitem__(key)

    @session_method
    def __setitem__(self, key, value):
        if not self.ss.sid:
            self.__start()
        self.ss.data.__setitem__(key, value)
        self.dirty = True

    @session_method
    def __delitem__(self, key):
        self.ss.data.__delitem__(key)
        self.dirty = True

    @session_method
    def __iter__(self):
        raise NotImplementedError("doesn't fit into our test framework - the correct return value cannot be pickled")

    @session_method
    def __contains__(self, key):
        return self.ss.data.__contains__(key)

    @session_method
    def __str__(self):
        if self.ss.sid:
            return "SID=%s %s" % (self.ss.sid, self.ss.data)
        else:
            return "uninitialized session"

########NEW FILE########
__FILENAME__ = test_gaesessions
from base64 import b64decode, b64encode
import logging
import pickle
import time

from google.appengine.ext import db
from nose.tools import assert_equal, assert_not_equal, assert_raises

from main import make_entity
from gaesessions import COOKIE_NAME_PREFIX, SessionMiddleware, SID_LEN, SIG_LEN
from SessionTester import SessionTester

# Tests (each on a variety of configurations):
#   0) Correct session usage and memcache loss
#   1) Session expiration
#   2) Bad cookie data (e.g., sig invalid due to data changed by user)
#   3) API downtime (future work)

logger = logging.getLogger('TESTS ')
logger.setLevel(logging.DEBUG)

def test_middleware():
    """Tests that the middleware requires cookie_key when it should."""
    logging.debug("cookie_key is required and needs to be reasonably long")
    assert_raises(ValueError, SessionMiddleware, None, None)
    assert_raises(ValueError, SessionMiddleware, None, cookie_key='blah')
    SessionMiddleware(None, cookie_only_threshold=10, cookie_key='blah'*8)
    SessionMiddleware(None, cookie_only_threshold=0, cookie_key="still need a key"*4)

def test_sessions():
    """Run a variety of tests on various session configurations (includes
    whether or not to use the datastore and the cookie only threshold).
    """
    CHECKS = (check_correct_usage, check_expiration, check_bad_cookie, check_various_session_sizes)
    for no_datastore in (False, True):
        if no_datastore:
            test_db = 'without'
        else:
            test_db = 'with'
        for cot in (0, 10*1024, 2**30):
            if cot == 0:
                test_cookie = 'no data stored in cookies'
            elif cot == 2**30:
                test_cookie = 'data only stored in cookies'
            else:
                test_cookie = 'store data in cookies when its encoded size<=%dB' % cot
            for check in CHECKS:
                logger.debug('\n\n' + '*'*50)
                logger.debug('Running %s %s datastore and %s' % (check.__name__, test_db, test_cookie))
                yield check, no_datastore, cot

# helper function which checks how many sessions we should have in the db
# given the current test's configuration
def generic_expected_num_sessions_in_db_if_db_used(st, no_datastore, cookie_only_threshold,
                                                   num, num_above_cookie_thresh=0, num_after=None):
    if not no_datastore:
        if cookie_only_threshold == 0:
            st.verify_active_sessions_in_db(num,num_after)
        else:
            st.verify_active_sessions_in_db(num_above_cookie_thresh, num_after)
    else:
        st.verify_active_sessions_in_db(0)  # cookie or memcache only

def check_correct_usage(no_datastore, cookie_only_threshold):
    """Checks correct usage of session including in the face of memcache data loss."""
    def minitest_divider(test):
        logger.debug('\n\n' + '-'*50)
        logger.debug(test + ' (nd=%s cot=%s)' % (no_datastore, cookie_only_threshold))

    st = SessionTester(no_datastore=no_datastore, cookie_only_threshold=cookie_only_threshold)
    expected_num_sessions_in_db_if_db_used = lambda a,b=0 : generic_expected_num_sessions_in_db_if_db_used(st, no_datastore, cookie_only_threshold, a, b)
    st.verify_active_sessions_in_db(0)

    minitest_divider('try doing nothing (no session should be started)')
    st.noop()
    st.verify_active_sessions_in_db(0)

    minitest_divider('start a session with a single write')
    st.start_request()
    str(st)
    assert st.get_expiration()==0, "no session yet => no expiration yet"
    assert st.is_active() is False
    st['x'] = 7
    assert st.is_active() is True
    st.finish_request_and_check()
    expected_num_sessions_in_db_if_db_used(1)

    minitest_divider('start another session')
    st2 = SessionTester(st=st)
    st2.start_request()
    assert not st2.is_active()
    assert st2.get('x') is None, "shouldn't get other session's data"
    assert not st2.is_active(), "still shouldn't be active - nothing set yet"
    st2['x'] = 'st2x'
    assert st2.is_active()
    st2.finish_request_and_check()
    expected_num_sessions_in_db_if_db_used(2)

    minitest_divider('each session should get a unique sid')
    assert st2.ss.sid != st.ss.sid

    minitest_divider('we should still have the values we set earlier')
    st.start_request()
    str(st)
    assert_equal(st['x'], 7)
    st.finish_request_and_check()
    st2.start_request()
    assert_equal(st2['x'], 'st2x')
    st2.finish_request_and_check()

    minitest_divider("check get session by sid, save(True), and terminate()")
    if cookie_only_threshold == 0:
        data1 = st.ss.data
        data2 = st2.ss.data
    else:
        # data is being stored in cookie-only form => won't be in the db
        data1 = data2 = {}
    resp = st.get_url('/get_by_sid?sid=%s' % st.ss.sid)
    assert_equal(pickle.loads(b64decode(resp.body)), data1)
    resp = st2.get_url('/get_by_sid?sid=%s' % st2.ss.sid)
    assert_equal(pickle.loads(b64decode(resp.body)), data2)
    expected_num_sessions_in_db_if_db_used(2)
    st.start_request()
    st['y'] = 9    # make the session dirty
    st.save(True)  # force it to persist to the db even though it normally wouldn't
    st.finish_request_and_check()

    # now the data should be in the db
    resp = st.get_url('/get_by_sid?sid=%s' % st.ss.sid)
    assert_equal(pickle.loads(b64decode(resp.body)), st.ss.data)
    expected_num_sessions_in_db_if_db_used(2, 1)
    st.start_request()
    st.terminate()  # remove it from the db
    st.finish_request_and_check()
    expected_num_sessions_in_db_if_db_used(1)

    minitest_divider("should be able to terminate() and then start a new session all in one request")
    st.start_request()
    st['y'] = 'yy'
    assert_equal(st.get('y'), 'yy')
    st.terminate()
    assert_raises(KeyError, st.__getitem__, 'y')
    st['x'] = 7
    st.finish_request_and_check()
    expected_num_sessions_in_db_if_db_used(2)

    minitest_divider("regenerating SID test")
    initial_sid = st.ss.sid
    st.start_request()
    initial_expir = st.get_expiration()
    st.regenerate_id()
    assert_equal(st['x'], 7, "data should not be affected")
    st.finish_request_and_check()
    assert_not_equal(initial_sid, st.ss.sid, "regenerated sid should be different")
    assert_equal(initial_expir, st._get_expiration(), "expiration should not change")
    st.start_request()
    assert_equal(st['x'], 7, "data should not be affected")
    st.finish_request_and_check()
    expected_num_sessions_in_db_if_db_used(2)

    minitest_divider("regenerating SID test w/new expiration time")
    initial_sid = st.ss.sid
    st.start_request()
    initial_expir = st.get_expiration()
    new_expir = initial_expir + 120  # something new
    st.regenerate_id(expiration_ts=new_expir)
    assert_equal(st['x'], 7, "data should not be affected")
    st.finish_request_and_check()
    assert_not_equal(initial_sid, st.ss.sid, "regenerated sid should be different")
    assert_equal(new_expir, st._get_expiration(), "expiration should be what we asked for")
    st.start_request()
    assert_equal(st['x'], 7, "data should not be affected")
    st.finish_request_and_check()
    expected_num_sessions_in_db_if_db_used(2)

    minitest_divider("check basic dictionary operations")
    st.start_request()
    st['s'] = 'aaa'
    st['i'] = 99
    st['f'] = 4.37
    assert_equal(st.pop('s'), 'aaa')
    assert_equal(st.pop('s'), None)
    assert_equal(st.pop('s', 'nil'), 'nil')
    assert st.has_key('i')
    assert not st.has_key('s')
    assert_equal(st.get('i'), 99)
    assert_equal(st.get('ii'), None)
    assert_equal(st.get('iii', 3), 3)
    assert_equal(st.get('f'), st['f'])
    del st['f']
    assert_raises(KeyError, st.__getitem__, 'f')
    assert 'f' not in st
    assert 'i' in st
    assert_equal(st.get('x'), 7)
    st.clear()
    assert 'i' not in st
    assert 'x' not in st
    st.finish_request_and_check()

    minitest_divider("add complex data (models and objects) to the session")
    st.start_request()
    st['model'] = make_entity(0)
    st['dict'] = dict(a='alpha', c='charlie', e='echo')
    st['list'] = ['b', 'd', 'f']
    st['set'] = set([2, 3, 5, 7, 11, 13, 17, 19])
    st['tuple'] = (7, 7, 1985)
    st.finish_request_and_check()
    st.start_request()
    st.clear()
    st.finish_request_and_check()

    minitest_divider("test quick methods: basic usage")
    st.start_request()
    st.set_quick('msg', 'mc only!')
    assert_equal('mc only!', st['msg'])
    st.finish_request_and_check()
    st.start_request()
    assert_equal('mc only!', st.pop_quick('msg'))
    assert_raises(KeyError, st.__getitem__, 'msg')
    st.finish_request_and_check()

    minitest_divider("test quick methods: flush memcache (value will be lost if not using cookies)")
    st.start_request()
    st.set_quick('a', 1)
    st.set_quick('b', 2)
    st.finish_request_and_check()
    st.flush_memcache()
    st.start_request()
    if cookie_only_threshold > 0:
        assert_equal(st['a'], 1)
        assert_equal(st['b'], 2)
    else:
        assert_raises(KeyError, st.__getitem__, 'a')
        assert_raises(KeyError, st.__getitem__, 'b')
    st.finish_request_and_check()

    minitest_divider("test quick methods: flush memcache should have no impact if another mutator is also used (and this ISNT memcache-only)")
    st.start_request()
    st['x'] =  24
    st.set_quick('a', 1)
    st.finish_request_and_check()
    st.flush_memcache()
    st.start_request()
    if no_datastore and cookie_only_threshold == 0:
        assert_raises(KeyError, st.__getitem__, 'a')
        assert_raises(KeyError, st.__getitem__, 'x')
    else:
        assert_equal(st['a'], 1)
        assert_equal(st['x'], 24)
    st.set_quick('msg', 'hello')
    st['z'] = 99
    st.finish_request_and_check()

MAX_COOKIE_ONLY_SIZE_TO_TEST = 59 * 1024
def check_various_session_sizes(no_datastore, cookie_only_threshold):
    for log2_data_sz_bytes in xrange(10,22):
        if log2_data_sz_bytes == 20:
            # maximum data size is 1MB *including* overhead, so just try up to
            # about the maximum size not including overhead (overhead based on,
            # actual data but for this test it looks like about 5%).
            data_sz_bytes = 2**log2_data_sz_bytes - 50*1024
        elif log2_data_sz_bytes == 16 and cookie_only_threshold>2**15:
            # the minimums recommended for cookie storage is 20 cookies of 4KB
            # each.  64KB of data plus overhead is just a notch above this, so
            # shrink this test just a tad for cookie-only sessions to get about
            # 20 full cookies  - about 59KB of raw data for this test.
            data_sz_bytes = MAX_COOKIE_ONLY_SIZE_TO_TEST
        else:
            data_sz_bytes = 2**log2_data_sz_bytes
        logging.info("trying session with %dB (~%.1fKB) (before encoding)" % (data_sz_bytes, data_sz_bytes/1024.0))

        if cookie_only_threshold<data_sz_bytes or data_sz_bytes<=MAX_COOKIE_ONLY_SIZE_TO_TEST:
            st = SessionTester(no_datastore=no_datastore, cookie_only_threshold=cookie_only_threshold)
            st.start_request()
            st['v'] = 'x' * data_sz_bytes
            expect_fail = (log2_data_sz_bytes >= 21)
            st.finish_request_and_check(expect_failure=expect_fail)
        else:
            logging.info("skipped - too big for cookie-only data")

def check_expiration(no_datastore, cookie_only_threshold):
    st = SessionTester(no_datastore=no_datastore, cookie_only_threshold=cookie_only_threshold)
    expected_num_sessions_in_db_if_db_used = lambda a,c : generic_expected_num_sessions_in_db_if_db_used(st, no_datastore, cookie_only_threshold, a, 0, c)

    # generate some sessions
    num_to_start = 20
    sessions_which_expire_shortly = (1, 3, 8, 9, 11)
    sts = []
    for i in xrange(num_to_start):
        stnew = SessionTester(st=st)
        sts.append(stnew)
        stnew.start_request()
        if i in sessions_which_expire_shortly:
            stnew.start(expiration_ts=time.time()-1)
        else:
            stnew.start(expiration_ts=time.time()+600)
        stnew.finish_request_and_check()

    # try accessing an expired session
    st_expired = sts[sessions_which_expire_shortly[0]]
    st_expired.start_request()
    assert not st_expired.is_active()
    st_expired.finish_request_and_check()

    if cookie_only_threshold > 0:
        return  # no need to see if cleaning up db works - nothing there for this case

    # check that after cleanup only unexpired ones are left in the db
    num_left = num_to_start - len(sessions_which_expire_shortly)
    expected_num_sessions_in_db_if_db_used(num_to_start-1, num_left)  # -1 b/c we manually expired one above

def check_bad_cookie(no_datastore, cookie_only_threshold):
    for test in (check_bad_sid, check_manip_cookie_data, check_bogus_data, check_bogus_data2):
        logger.info('preparing for %s' % test.__name__)
        st = SessionTester(no_datastore=no_datastore, cookie_only_threshold=cookie_only_threshold)
        st.start_request()
        st['x'] = 7
        st.finish_request_and_check()
        logger.info('running %s' % test.__name__)
        test(st, st.get_cookies())
        st.new_session_state()
        st.start_request()
        assert not st.is_active()  # due to invalid sig
        st.finish_request_and_check()

def check_bad_sid(st, cookies):
    cv = cookies[COOKIE_NAME_PREFIX + '00']
    sid = cv[SIG_LEN:SIG_LEN+SID_LEN]
    bad_sid = ''.join(reversed(sid))
    cookies[COOKIE_NAME_PREFIX + '00'] = cv[:SIG_LEN]+bad_sid+cv[SID_LEN+SIG_LEN:]

def check_manip_cookie_data(st, cookies):
    cv = cookies[COOKIE_NAME_PREFIX + '00']
    cookies[COOKIE_NAME_PREFIX + '00'] = cv[:SIG_LEN+SID_LEN] + b64encode(pickle.dumps(dict(evil='fail'),2))

def check_bogus_data(st, cookies):
    cv = cookies[COOKIE_NAME_PREFIX + '00']
    cookies[COOKIE_NAME_PREFIX + '00'] = cv[:SIG_LEN+SID_LEN] + "==34@#K$$;))" # invalid "base64"

def check_bogus_data2(st, cookies):
    cookies[COOKIE_NAME_PREFIX + '00'] = "blah"

def test_cookies_deleted_when_session_storage_moved_to_backend():
    logger.info("make a session with data stored in the cookie")
    st = SessionTester(no_datastore=False, cookie_only_threshold=14*1024)
    st.start_request()
    st['junk'] = 'x'  * 9000  # fits in the cookie
    st.finish_request_and_check()
    assert not st.ss.in_mc

    logger.info("force the session to be stored on the backend (too big for app engine headers)")
    st.start_request()
    st['junk'] = 'x'  * 16000  # does NOT fit in the cookie
    st.finish_request_and_check()
    assert st.ss.in_mc

def main():
    """Run nose tests and generate a coverage report."""
    import coverage
    import nose
    import os
    from shutil import rmtree
    rmtree('./covhtml', ignore_errors=True)
    try:
        os.remove('./.coverage')
    except Exception,e:
        pass

    # run nose in its own process because the .coverage file isn't written
    # until the process terminates and we need to read it
    nose.run()

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = lint
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# Also licenced under the Apache License, 2.0: http://opensource.org/licenses/apache2.0.php
# Licensed to PSF under a Contributor Agreement
"""
Middleware to check for obedience to the WSGI specification.

Some of the things this checks:

* Signature of the application and start_response (including that
  keyword arguments are not used).

* Environment checks:

  - Environment is a dictionary (and not a subclass).

  - That all the required keys are in the environment: REQUEST_METHOD,
    SERVER_NAME, SERVER_PORT, wsgi.version, wsgi.input, wsgi.errors,
    wsgi.multithread, wsgi.multiprocess, wsgi.run_once

  - That HTTP_CONTENT_TYPE and HTTP_CONTENT_LENGTH are not in the
    environment (these headers should appear as CONTENT_LENGTH and
    CONTENT_TYPE).

  - Warns if QUERY_STRING is missing, as the cgi module acts
    unpredictably in that case.

  - That CGI-style variables (that don't contain a .) have
    (non-unicode) string values

  - That wsgi.version is a tuple

  - That wsgi.url_scheme is 'http' or 'https' (@@: is this too
    restrictive?)

  - Warns if the REQUEST_METHOD is not known (@@: probably too
    restrictive).

  - That SCRIPT_NAME and PATH_INFO are empty or start with /

  - That at least one of SCRIPT_NAME or PATH_INFO are set.

  - That CONTENT_LENGTH is a positive integer.

  - That SCRIPT_NAME is not '/' (it should be '', and PATH_INFO should
    be '/').

  - That wsgi.input has the methods read, readline, readlines, and
    __iter__

  - That wsgi.errors has the methods flush, write, writelines

* The status is a string, contains a space, starts with an integer,
  and that integer is in range (> 100).

* That the headers is a list (not a subclass, not another kind of
  sequence).

* That the items of the headers are tuples of strings.

* That there is no 'status' header (that is used in CGI, but not in
  WSGI).

* That the headers don't contain newlines or colons, end in _ or -, or
  contain characters codes below 037.

* That Content-Type is given if there is content (CGI often has a
  default content type, but WSGI does not).

* That no Content-Type is given when there is no content (@@: is this
  too restrictive?)

* That the exc_info argument to start_response is a tuple or None.

* That all calls to the writer are with strings, and no other methods
  on the writer are accessed.

* That wsgi.input is used properly:

  - .read() is called with zero or one argument

  - That it returns a string

  - That readline, readlines, and __iter__ return strings

  - That .close() is not called

  - No other methods are provided

* That wsgi.errors is used properly:

  - .write() and .writelines() is called with a string

  - That .close() is not called, and no other methods are provided.

* The response iterator:

  - That it is not a string (it should be a list of a single string; a
    string will work, but perform horribly).

  - That .next() returns a string

  - That the iterator is not iterated over until start_response has
    been called (that can signal either a server or application
    error).

  - That .close() is called (doesn't raise exception, only prints to
    sys.stderr, because we only know it isn't called when the object
    is garbage collected).
"""

import re
import sys
from types import DictType, StringType, TupleType, ListType
import warnings

header_re = re.compile(r'^[a-zA-Z][a-zA-Z0-9\-_]*$')
bad_header_value_re = re.compile(r'[\000-\037]')

class WSGIWarning(Warning):
    """
    Raised in response to WSGI-spec-related warnings
    """

def middleware(application, global_conf=None):

    """
    When applied between a WSGI server and a WSGI application, this
    middleware will check for WSGI compliancy on a number of levels.
    This middleware does not modify the request or response in any
    way, but will throw an AssertionError if anything seems off
    (except for a failure to close the application iterator, which
    will be printed to stderr -- there's no way to throw an exception
    at that point).
    """
    
    def lint_app(*args, **kw):
        assert len(args) == 2, "Two arguments required"
        assert not kw, "No keyword arguments allowed"
        environ, start_response = args

        check_environ(environ)

        # We use this to check if the application returns without
        # calling start_response:
        start_response_started = []

        def start_response_wrapper(*args, **kw):
            assert len(args) == 2 or len(args) == 3, (
                "Invalid number of arguments: %s" % args)
            assert not kw, "No keyword arguments allowed"
            status = args[0]
            headers = args[1]
            if len(args) == 3:
                exc_info = args[2]
            else:
                exc_info = None

            check_status(status)
            check_headers(headers)
            check_content_type(status, headers)
            check_exc_info(exc_info)

            start_response_started.append(None)
            return WriteWrapper(start_response(*args))

        environ['wsgi.input'] = InputWrapper(environ['wsgi.input'])
        environ['wsgi.errors'] = ErrorWrapper(environ['wsgi.errors'])

        iterator = application(environ, start_response_wrapper)
        assert iterator is not None and iterator != False, (
            "The application must return an iterator, if only an empty list")

        check_iterator(iterator)

        return IteratorWrapper(iterator, start_response_started)

    return lint_app

class InputWrapper(object):

    def __init__(self, wsgi_input):
        self.input = wsgi_input

    def read(self, *args):
        assert len(args) <= 1
        v = self.input.read(*args)
        assert type(v) is type("")
        return v

    def readline(self, *args):
        v = self.input.readline(*args)
        assert type(v) is type("")
        return v

    def readlines(self, *args):
        assert len(args) <= 1
        lines = self.input.readlines(*args)
        assert type(lines) is type([])
        for line in lines:
            assert type(line) is type("")
        return lines
    
    def __iter__(self):
        while 1:
            line = self.readline()
            if not line:
                return
            yield line

    def close(self):
        assert 0, "input.close() must not be called"

class ErrorWrapper(object):

    def __init__(self, wsgi_errors):
        self.errors = wsgi_errors

    def write(self, s):
        assert type(s) is type("")
        self.errors.write(s)

    def flush(self):
        self.errors.flush()

    def writelines(self, seq):
        for line in seq:
            self.write(line)

    def close(self):
        assert 0, "errors.close() must not be called"

class WriteWrapper(object):

    def __init__(self, wsgi_writer):
        self.writer = wsgi_writer

    def __call__(self, s):
        assert type(s) is type("")
        self.writer(s)

class PartialIteratorWrapper(object):

    def __init__(self, wsgi_iterator):
        self.iterator = wsgi_iterator

    def __iter__(self):
        # We want to make sure __iter__ is called
        return IteratorWrapper(self.iterator)

class IteratorWrapper(object):

    def __init__(self, wsgi_iterator, check_start_response):
        self.original_iterator = wsgi_iterator
        self.iterator = iter(wsgi_iterator)
        self.closed = False
        self.check_start_response = check_start_response

    def __iter__(self):
        return self

    def next(self):
        assert not self.closed, (
            "Iterator read after closed")
        v = self.iterator.next()
        if self.check_start_response is not None:
            assert self.check_start_response, (
                "The application returns and we started iterating over its body, but start_response has not yet been called")
            self.check_start_response = None
        return v
        
    def close(self):
        self.closed = True
        if hasattr(self.original_iterator, 'close'):
            self.original_iterator.close()

    def __del__(self):
        if not self.closed:
            sys.stderr.write(
                "Iterator garbage collected without being closed")
        assert self.closed, (
            "Iterator garbage collected without being closed")

def check_environ(environ):
    assert type(environ) is DictType, (
        "Environment is not of the right type: %r (environment: %r)"
        % (type(environ), environ))
    
    for key in ['REQUEST_METHOD', 'SERVER_NAME', 'SERVER_PORT',
                'wsgi.version', 'wsgi.input', 'wsgi.errors',
                'wsgi.multithread', 'wsgi.multiprocess',
                'wsgi.run_once']:
        assert key in environ, (
            "Environment missing required key: %r" % key)

    for key in ['HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH']:
        assert key not in environ, (
            "Environment should not have the key: %s "
            "(use %s instead)" % (key, key[5:]))

    if 'QUERY_STRING' not in environ:
        warnings.warn(
            'QUERY_STRING is not in the WSGI environment; the cgi '
            'module will use sys.argv when this variable is missing, '
            'so application errors are more likely',
            WSGIWarning)

    for key in environ.keys():
        if '.' in key:
            # Extension, we don't care about its type
            continue
        assert type(environ[key]) is StringType, (
            "Environmental variable %s is not a string: %r (value: %r)"
            % (key, type(environ[key]), environ[key]))
        
    assert type(environ['wsgi.version']) is TupleType, (
        "wsgi.version should be a tuple (%r)" % environ['wsgi.version'])
    assert environ['wsgi.url_scheme'] in ('http', 'https'), (
        "wsgi.url_scheme unknown: %r" % environ['wsgi.url_scheme'])

    check_input(environ['wsgi.input'])
    check_errors(environ['wsgi.errors'])

    # @@: these need filling out:
    if environ['REQUEST_METHOD'] not in (
        'GET', 'HEAD', 'POST', 'OPTIONS','PUT','DELETE','TRACE'):
        warnings.warn(
            "Unknown REQUEST_METHOD: %r" % environ['REQUEST_METHOD'],
            WSGIWarning)

    assert (not environ.get('SCRIPT_NAME')
            or environ['SCRIPT_NAME'].startswith('/')), (
        "SCRIPT_NAME doesn't start with /: %r" % environ['SCRIPT_NAME'])
    assert (not environ.get('PATH_INFO')
            or environ['PATH_INFO'].startswith('/')), (
        "PATH_INFO doesn't start with /: %r" % environ['PATH_INFO'])
    if environ.get('CONTENT_LENGTH'):
        assert int(environ['CONTENT_LENGTH']) >= 0, (
            "Invalid CONTENT_LENGTH: %r" % environ['CONTENT_LENGTH'])

    if not environ.get('SCRIPT_NAME'):
        assert environ.has_key('PATH_INFO'), (
            "One of SCRIPT_NAME or PATH_INFO are required (PATH_INFO "
            "should at least be '/' if SCRIPT_NAME is empty)")
    assert environ.get('SCRIPT_NAME') != '/', (
        "SCRIPT_NAME cannot be '/'; it should instead be '', and "
        "PATH_INFO should be '/'")

def check_input(wsgi_input):
    for attr in ['read', 'readline', 'readlines', '__iter__']:
        assert hasattr(wsgi_input, attr), (
            "wsgi.input (%r) doesn't have the attribute %s"
            % (wsgi_input, attr))

def check_errors(wsgi_errors):
    for attr in ['flush', 'write', 'writelines']:
        assert hasattr(wsgi_errors, attr), (
            "wsgi.errors (%r) doesn't have the attribute %s"
            % (wsgi_errors, attr))

def check_status(status):
    assert type(status) is StringType, (
        "Status must be a string (not %r)" % status)
    # Implicitly check that we can turn it into an integer:
    status_code = status.split(None, 1)[0]
    assert len(status_code) == 3, (
        "Status codes must be three characters: %r" % status_code)
    status_int = int(status_code)
    assert status_int >= 100, "Status code is invalid: %r" % status_int
    if len(status) < 4 or status[3] != ' ':
        warnings.warn(
            "The status string (%r) should be a three-digit integer "
            "followed by a single space and a status explanation"
            % status, WSGIWarning)

def check_headers(headers):
    assert type(headers) is ListType, (
        "Headers (%r) must be of type list: %r"
        % (headers, type(headers)))
    header_names = {}
    for item in headers:
        assert type(item) is TupleType, (
            "Individual headers (%r) must be of type tuple: %r"
            % (item, type(item)))
        assert len(item) == 2
        name, value = item
        assert name.lower() != 'status', (
            "The Status header cannot be used; it conflicts with CGI "
            "script, and HTTP status is not given through headers "
            "(value: %r)." % value)
        header_names[name.lower()] = None
        assert '\n' not in name and ':' not in name, (
            "Header names may not contain ':' or '\\n': %r" % name)
        assert header_re.search(name), "Bad header name: %r" % name
        assert not name.endswith('-') and not name.endswith('_'), (
            "Names may not end in '-' or '_': %r" % name)
        assert not bad_header_value_re.search(value), (
            "Bad header value: %r (bad char: %r)"
            % (value, bad_header_value_re.search(value).group(0)))

def check_content_type(status, headers):
    code = int(status.split(None, 1)[0])
    # @@: need one more person to verify this interpretation of RFC 2616
    #     http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
    NO_MESSAGE_BODY = (201, 204, 304)
    NO_MESSAGE_TYPE = (204, 304)
    for name, value in headers:
        if name.lower() == 'content-type':
            if code not in NO_MESSAGE_TYPE:
                return
            assert 0, (("Content-Type header found in a %s response, "
                        "which must not return content.") % code)
    if code not in NO_MESSAGE_BODY:
        assert 0, "No Content-Type header found in headers (%s)" % headers

def check_exc_info(exc_info):
    assert exc_info is None or type(exc_info) is type(()), (
        "exc_info (%r) is not a tuple: %r" % (exc_info, type(exc_info)))
    # More exc_info checks?

def check_iterator(iterator):
    # Technically a string is legal, which is why it's a really bad
    # idea, because it may cause the response to be returned
    # character-by-character
    assert not isinstance(iterator, str), (
        "You should not return a string as your application iterator, "
        "instead return a single-item list containing that string.")

def make_middleware(application, global_conf):
    # @@: global_conf should be taken out of the middleware function,
    # and isolated here
    return middleware(application)

make_middleware.__doc__ = __doc__

__all__ = ['middleware', 'make_middleware']

########NEW FILE########
